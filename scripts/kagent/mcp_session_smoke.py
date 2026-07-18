#!/usr/bin/env python3
"""Direct MCP session smoke helper for the local kagent educational lab.

Lifecycle (mandatory success path):
  initialize -> notifications/initialized -> tools/list -> tools/call -> DELETE

Proves direct MCP tool invocation only. Does not prove L4 A2A or L6 agent-mediated use.

Usage:
    kubectl port-forward -n kagent svc/kagent-tool-server 8000:8000
    python scripts/kagent/mcp_session_smoke.py --url http://127.0.0.1:8000/mcp
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import urlparse

DEFAULT_URL = "http://127.0.0.1:8000/mcp"
DEFAULT_TOOL = "k8s_get_resources"
DEFAULT_PROTOCOL_VERSION = "2024-11-05"
SUPPORTED_PROTOCOL_VERSIONS = frozenset({"2024-11-05", "2025-03-26", "2025-06-18"})
CLIENT_INFO = {"name": "kagent-lab-mcp-session", "version": "1.0.0"}
MAX_SESSION_ID_LEN = 256
MAX_TOOLS_LIST_PAGES = 5
MAX_SSE_EVENTS = 64
MAX_SSE_BYTES = 1_048_576
SESSION_HEADER = "Mcp-Session-Id"
ACCEPT_HEADER = "application/json, text/event-stream"
TRANSPORT_OBSERVATION = "observed-streamable-http-compatibility"

# Convenience CLI flags map to schema property names when present.
CONVENIENCE_ARG_MAP = {
    "resource_type": "resource_type",
    "resource_namespace": "namespace",
}


class ExitCode:
    SUCCESS = 0
    PROTOCOL_OR_TOOL = 1
    USAGE = 2
    TRANSPORT = 3


class ProtocolError(Exception):
    """MCP lifecycle, JSON-RPC, schema, or tool failure."""


class TransportError(Exception):
    """DNS, connection, or timeout failure."""


class UsageError(Exception):
    """CLI validation or unsafe URL."""


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    content_type: str = ""


@dataclass
class SessionConfig:
    url: str = DEFAULT_URL
    tool: str = DEFAULT_TOOL
    arguments: dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0
    protocol_version: str = DEFAULT_PROTOCOL_VERSION
    output: str = "summary"
    quiet: bool = False
    allow_remote_url: bool = False
    simulate_missing_initialized: bool = False
    resource_type: str | None = None
    resource_namespace: str | None = None


@dataclass
class StageResult:
    exit_code: int
    requested_protocol_version: str = ""
    negotiated_protocol_version: str = ""
    transport_observation: str = TRANSPORT_OBSERVATION
    session_id_present: bool = False
    initialized_http_status: int | None = None
    initialized_compatibility_deviation: bool = False
    tool: str = ""
    tool_call_succeeded: bool = False
    resource_summary: dict[str, Any] = field(default_factory=dict)
    cleanup: str = "not-applicable"
    error: str | None = None
    schema_properties: list[str] = field(default_factory=list)

    def to_sanitized_dict(self) -> dict[str, Any]:
        return {
            "requestedProtocolVersion": self.requested_protocol_version,
            "negotiatedProtocolVersion": self.negotiated_protocol_version,
            "transportObservation": self.transport_observation,
            "sessionId": "present" if self.session_id_present else "missing",
            "initializedHttpStatus": self.initialized_http_status,
            "initializedCompatibilityDeviation": self.initialized_compatibility_deviation,
            "tool": self.tool,
            "toolCallSucceeded": self.tool_call_succeeded,
            "resourceSummary": self.resource_summary,
            "cleanup": self.cleanup,
            "schemaProperties": self.schema_properties,
            "error": self.error,
            "exitCode": self.exit_code,
        }


class Transport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: bytes | None = None,
        timeout: float,
    ) -> HttpResponse: ...


class DirectUrlTransport:
    """stdlib urllib transport that does not follow redirects."""

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: bytes | None = None,
        timeout: float,
    ) -> HttpResponse:
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        opener = urllib.request.build_opener(NoRedirectHandler)
        try:
            with opener.open(req, timeout=timeout) as resp:
                raw = resp.read(MAX_SSE_BYTES + 1)
                if len(raw) > MAX_SSE_BYTES:
                    raise ProtocolError(f"response exceeds {MAX_SSE_BYTES} bytes")
                hdrs = {k: v for k, v in resp.headers.items()}
                ctype = resp.headers.get("Content-Type", "") or ""
                return HttpResponse(
                    status=getattr(resp, "status", 200),
                    headers=hdrs,
                    body=raw,
                    content_type=ctype,
                )
        except urllib.error.HTTPError as exc:
            raw = exc.read(MAX_SSE_BYTES + 1) if exc.fp is not None else b""
            if len(raw) > MAX_SSE_BYTES:
                raise ProtocolError(f"response exceeds {MAX_SSE_BYTES} bytes") from exc
            hdrs = {k: v for k, v in exc.headers.items()} if exc.headers else {}
            ctype = hdrs.get("Content-Type", "") or hdrs.get("content-type", "")
            return HttpResponse(status=exc.code, headers=hdrs, body=raw, content_type=ctype)
        except TimeoutError as exc:
            raise TransportError(f"timeout: {exc}") from exc
        except urllib.error.URLError as exc:
            raise TransportError(str(exc.reason if hasattr(exc, "reason") else exc)) from exc
        except OSError as exc:
            raise TransportError(str(exc)) from exc


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProtocolError(f"redirect refused: HTTP {code}")


def capture_session_id(headers: dict[str, str]) -> str:
    """Return validated Mcp-Session-Id (case-insensitive) or raise ProtocolError."""
    value: str | None = None
    for key, raw in headers.items():
        if key.lower() == SESSION_HEADER.lower():
            value = raw
            break
    if value is None or value.strip() == "":
        raise ProtocolError("missing Mcp-Session-Id response header")
    session_id = value.strip()
    if len(session_id) > MAX_SESSION_ID_LEN:
        raise ProtocolError("Mcp-Session-Id exceeds maximum length")
    if not re.fullmatch(r"[\x21-\x7E]+", session_id):
        raise ProtocolError("Mcp-Session-Id must be visible ASCII")
    return session_id


def _is_json_content_type(content_type: str) -> bool:
    base = content_type.split(";", 1)[0].strip().lower()
    return base in {"application/json", "application/json-rpc"} or base.endswith("+json")


def _is_sse_content_type(content_type: str) -> bool:
    base = content_type.split(";", 1)[0].strip().lower()
    return base == "text/event-stream"


def parse_sse_jsonrpc(raw: bytes, expected_id: Any) -> dict[str, Any]:
    """Parse SSE events; return the JSON-RPC message matching expected_id."""
    if len(raw) > MAX_SSE_BYTES:
        raise ProtocolError(f"SSE payload exceeds {MAX_SSE_BYTES} bytes")
    text = raw.decode("utf-8", errors="replace")
    events: list[str] = []
    data_lines: list[str] = []
    event_count = 0

    def flush() -> None:
        nonlocal event_count
        if not data_lines:
            return
        event_count += 1
        if event_count > MAX_SSE_EVENTS:
            raise ProtocolError(f"SSE event count exceeds {MAX_SSE_EVENTS}")
        events.append("\n".join(data_lines))
        data_lines.clear()

    for line in text.splitlines():
        if line == "":
            flush()
            continue
        if line.startswith(":"):
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
            continue
        # event:, id:, retry: — ignore for matching
    flush()

    matched: dict[str, Any] | None = None
    for payload in events:
        if not payload.strip():
            continue
        try:
            message = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ProtocolError(f"malformed SSE JSON: {exc}") from exc
        if not isinstance(message, dict):
            raise ProtocolError("SSE JSON-RPC message must be an object")
        if "id" not in message:
            # notification — skip
            continue
        if message.get("id") == expected_id:
            matched = message
            break
        raise ProtocolError(
            f"JSON-RPC response id mismatch: expected {expected_id!r}, got {message.get('id')!r}"
        )
    if matched is None:
        raise ProtocolError("SSE stream ended before matching JSON-RPC response")
    return matched


def decode_mcp_response(content_type: str, raw: bytes, expected_id: Any) -> dict[str, Any]:
    """Decode JSON or SSE MCP HTTP body into a JSON-RPC object matching expected_id."""
    stripped = raw.lstrip()
    if _is_sse_content_type(content_type) or (
        not content_type and (stripped.startswith(b"event:") or stripped.startswith(b"data:"))
    ):
        return parse_sse_jsonrpc(raw, expected_id)
    if not content_type or _is_json_content_type(content_type):
        if not raw.strip():
            raise ProtocolError("empty JSON-RPC response body")
        try:
            message = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProtocolError(f"malformed JSON-RPC body: {exc}") from exc
        if not isinstance(message, dict):
            raise ProtocolError("JSON-RPC response must be an object")
        if message.get("id") != expected_id:
            actual_id = message.get("id")
            raise ProtocolError(
                f"JSON-RPC response id mismatch: expected {expected_id!r}, got {actual_id!r}"
            )
        return message
    raise ProtocolError(f"unsupported Content-Type: {content_type!r}")


def discover_tool_schema(tools: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for tool in tools:
        if tool.get("name") == name:
            return tool
    raise ProtocolError(f"tool not advertised by tools/list: {name}")


def validate_arguments_against_schema(args: dict[str, Any], input_schema: dict[str, Any]) -> None:
    if not isinstance(input_schema, dict):
        raise ProtocolError("tool inputSchema must be an object")
    required = input_schema.get("required") or []
    if not isinstance(required, list):
        raise ProtocolError("inputSchema.required must be a list")
    properties = input_schema.get("properties") or {}
    if properties and not isinstance(properties, dict):
        raise ProtocolError("inputSchema.properties must be an object")
    missing = [key for key in required if key not in args]
    if missing:
        raise ProtocolError(f"missing required tool arguments: {', '.join(missing)}")
    if properties:
        unknown = [key for key in args if key not in properties]
        if unknown:
            raise ProtocolError(f"arguments not in inputSchema.properties: {', '.join(unknown)}")


def summarize_tool_result(result: dict[str, Any]) -> dict[str, Any]:
    """Build a short sanitized resource summary from a tools/call result."""
    content = result.get("content")
    text_blobs: list[str] = []
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str):
                    text_blobs.append(text)
    joined = "\n".join(text_blobs)
    lines = [line for line in joined.splitlines() if line.strip()]
    names: list[str] = []
    if lines:
        # kubectl-style table: skip header row starting with NAME
        data_lines = lines[1:] if lines[0].upper().startswith("NAME") else lines
        for line in data_lines:
            first = line.split()[0] if line.split() else ""
            if first and first.upper() not in {"NAME", "NAMESPACE"}:
                names.append(first)
    if not names:
        names = re.findall(r'"name"\s*:\s*"([^"]+)"', joined)
    return {
        "count": len(names) if names else max(0, len(lines) - 1) if lines else 0,
        "sampleNames": names[:5],
        "textChars": min(len(joined), 10_000),
    }


def is_loopback_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname
    if host is None:
        return False
    if host.lower() in {"localhost"}:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def validate_url(url: str, *, allow_remote_url: bool) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise UsageError("url must use http or https")
    if not parsed.netloc:
        raise UsageError("url must include a host")
    if parsed.scheme == "http" and not is_loopback_url(url) and not allow_remote_url:
        raise UsageError("non-loopback http URL requires --allow-remote-url")


def merge_convenience_arguments(
    base: dict[str, Any],
    *,
    resource_type: str | None,
    resource_namespace: str | None,
    input_schema: dict[str, Any],
) -> dict[str, Any]:
    properties = input_schema.get("properties") or {}
    merged = dict(base)
    convenience = {
        "resource_type": resource_type,
        "resource_namespace": resource_namespace,
    }
    for flag_name, value in convenience.items():
        if value is None:
            continue
        prop = CONVENIENCE_ARG_MAP[flag_name]
        if prop not in properties:
            raise ProtocolError(
                f"--{flag_name.replace('_', '-')} not applicable: schema has no property {prop!r}"
            )
        merged[prop] = value
    return merged


class McpSessionClient:
    def __init__(self, config: SessionConfig, transport: Transport | None = None) -> None:
        self.config = config
        self.transport = transport or DirectUrlTransport()
        self._session_id: str | None = None
        self._next_id = 1
        self.result = StageResult(exit_code=ExitCode.PROTOCOL_OR_TOOL, tool=config.tool)

    def _alloc_id(self) -> int:
        req_id = self._next_id
        self._next_id += 1
        return req_id

    def _headers(self, *, with_session: bool) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": ACCEPT_HEADER,
        }
        if with_session:
            if not self._session_id:
                raise ProtocolError("session id required but missing")
            headers[SESSION_HEADER] = self._session_id
        return headers

    def _post_json(
        self,
        payload: dict[str, Any],
        *,
        with_session: bool,
        expect_jsonrpc_id: Any | None,
        allow_empty: bool = False,
    ) -> tuple[HttpResponse, dict[str, Any] | None]:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        try:
            resp = self.transport.request(
                "POST",
                self.config.url,
                headers=self._headers(with_session=with_session),
                body=body,
                timeout=self.config.timeout,
            )
        except ProtocolError:
            raise
        except TransportError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise TransportError(str(exc)) from exc

        if resp.status < 200 or resp.status >= 300:
            return resp, None
        if allow_empty and not resp.body.strip():
            return resp, None
        if expect_jsonrpc_id is None:
            return resp, None
        message = decode_mcp_response(resp.content_type, resp.body, expect_jsonrpc_id)
        return resp, message

    def run(self) -> StageResult:
        cfg = self.config
        self.result.requested_protocol_version = cfg.protocol_version
        self.result.tool = cfg.tool
        try:
            validate_url(cfg.url, allow_remote_url=cfg.allow_remote_url)
            if cfg.protocol_version not in SUPPORTED_PROTOCOL_VERSIONS:
                raise ProtocolError(
                    f"requested protocol version not in supported set: {cfg.protocol_version}"
                )
            self._initialize()
            self._send_initialized()
            tool_def = self._list_tools()
            input_schema = tool_def.get("inputSchema")
            if not isinstance(input_schema, dict):
                raise ProtocolError("tool is missing inputSchema object")
            props = input_schema.get("properties") or {}
            if isinstance(props, dict):
                self.result.schema_properties = sorted(props.keys())
            arguments = merge_convenience_arguments(
                cfg.arguments,
                resource_type=cfg.resource_type,
                resource_namespace=cfg.resource_namespace,
                input_schema=input_schema,
            )
            validate_arguments_against_schema(arguments, input_schema)
            self._call_tool(arguments)
            self.result.exit_code = ExitCode.SUCCESS
        except UsageError as exc:
            self.result.exit_code = ExitCode.USAGE
            self.result.error = str(exc)
        except TransportError as exc:
            self.result.exit_code = ExitCode.TRANSPORT
            self.result.error = str(exc)
        except ProtocolError as exc:
            self.result.exit_code = ExitCode.PROTOCOL_OR_TOOL
            self.result.error = str(exc)
        finally:
            self.result.cleanup = self.close()
            self.result.session_id_present = self._session_id is not None
        return self.result

    def _initialize(self) -> None:
        req_id = self._alloc_id()
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "initialize",
            "params": {
                "protocolVersion": self.config.protocol_version,
                "capabilities": {},
                "clientInfo": CLIENT_INFO,
            },
        }
        resp, message = self._post_json(payload, with_session=False, expect_jsonrpc_id=req_id)
        if resp.status < 200 or resp.status >= 300:
            raise ProtocolError(f"initialize HTTP {resp.status}")
        assert message is not None
        if "error" in message:
            err = message["error"]
            raise ProtocolError(f"initialize JSON-RPC error: {err}")
        result = message.get("result")
        if not isinstance(result, dict):
            raise ProtocolError("initialize missing result object")
        negotiated = result.get("protocolVersion")
        if not isinstance(negotiated, str) or not negotiated:
            raise ProtocolError("initialize result missing protocolVersion")
        if negotiated not in SUPPORTED_PROTOCOL_VERSIONS:
            raise ProtocolError(f"unsupported negotiated protocolVersion: {negotiated}")
        self.result.negotiated_protocol_version = negotiated
        self._session_id = capture_session_id(resp.headers)
        self.result.session_id_present = True

    def _send_initialized(self) -> None:
        if self.config.simulate_missing_initialized:
            return
        payload = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        resp, _ = self._post_json(
            payload,
            with_session=True,
            expect_jsonrpc_id=None,
            allow_empty=True,
        )
        self.result.initialized_http_status = resp.status
        if resp.status < 200 or resp.status >= 300:
            raise ProtocolError(f"notifications/initialized rejected: HTTP {resp.status}")
        if resp.status != 202:
            self.result.initialized_compatibility_deviation = True
        if resp.body.strip():
            # Notification should be empty; non-empty 2xx is a deviation but not fatal if 2xx.
            self.result.initialized_compatibility_deviation = True

    def _list_tools(self) -> dict[str, Any]:
        tools: list[dict[str, Any]] = []
        cursor: str | None = None
        for _ in range(MAX_TOOLS_LIST_PAGES):
            req_id = self._alloc_id()
            params: dict[str, Any] = {}
            if cursor is not None:
                params["cursor"] = cursor
            payload = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "tools/list",
                "params": params,
            }
            resp, message = self._post_json(payload, with_session=True, expect_jsonrpc_id=req_id)
            if resp.status < 200 or resp.status >= 300:
                raise ProtocolError(f"tools/list HTTP {resp.status}")
            assert message is not None
            if "error" in message:
                raise ProtocolError(f"tools/list JSON-RPC error: {message['error']}")
            result = message.get("result")
            if not isinstance(result, dict):
                raise ProtocolError("tools/list missing result object")
            page = result.get("tools")
            if not isinstance(page, list):
                raise ProtocolError("tools/list result.tools must be a list")
            for item in page:
                if isinstance(item, dict):
                    tools.append(item)
            next_cursor = result.get("nextCursor")
            if not next_cursor:
                break
            if not isinstance(next_cursor, str):
                raise ProtocolError("tools/list nextCursor must be a string")
            cursor = next_cursor
        else:
            raise ProtocolError(f"tools/list exceeded max pages ({MAX_TOOLS_LIST_PAGES})")
        return discover_tool_schema(tools, self.config.tool)

    def _call_tool(self, arguments: dict[str, Any]) -> None:
        req_id = self._alloc_id()
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/call",
            "params": {"name": self.config.tool, "arguments": arguments},
        }
        resp, message = self._post_json(payload, with_session=True, expect_jsonrpc_id=req_id)
        if resp.status < 200 or resp.status >= 300:
            raise ProtocolError(f"tools/call HTTP {resp.status}")
        assert message is not None
        if "error" in message:
            raise ProtocolError(f"tools/call JSON-RPC error: {message['error']}")
        result = message.get("result")
        if not isinstance(result, dict):
            raise ProtocolError("tools/call missing result object")
        if result.get("isError") is True:
            raise ProtocolError("tools/call result.isError is true")
        self.result.resource_summary = summarize_tool_result(result)
        self.result.tool_call_succeeded = True

    def close(self) -> str:
        if self._session_id is None:
            return "not-applicable"
        headers = {
            "Accept": ACCEPT_HEADER,
            SESSION_HEADER: self._session_id,
        }
        try:
            resp = self.transport.request(
                "DELETE",
                self.config.url,
                headers=headers,
                body=None,
                timeout=self.config.timeout,
            )
        except (TransportError, ProtocolError, OSError) as exc:
            _diag(f"session DELETE failed: {exc}")
            return "failed"
        if resp.status == 405:
            return "unsupported"
        if 200 <= resp.status < 300:
            return "deleted"
        _diag(f"session DELETE unexpected HTTP {resp.status}")
        return "failed"


def _diag(message: str) -> None:
    print(message, file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Direct MCP session smoke test (initialize, session reuse, tools/call)."
    )
    parser.add_argument("--url", default=DEFAULT_URL, help=f"MCP endpoint (default: {DEFAULT_URL})")
    parser.add_argument("--tool", default=DEFAULT_TOOL, help=f"Tool name (default: {DEFAULT_TOOL})")
    parser.add_argument(
        "--arguments-json",
        default="{}",
        help="JSON object of tool arguments (validated against tools/list inputSchema)",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout seconds")
    parser.add_argument(
        "--protocol-version",
        default=DEFAULT_PROTOCOL_VERSION,
        help=f"Requested MCP protocol version (default: {DEFAULT_PROTOCOL_VERSION})",
    )
    parser.add_argument(
        "--output",
        choices=["summary", "json"],
        default="summary",
        help="Output format (default: summary)",
    )
    parser.add_argument("--quiet", action="store_true", help="Minimal stderr diagnostics")
    parser.add_argument(
        "--allow-remote-url",
        action="store_true",
        help="Allow non-loopback http URLs",
    )
    parser.add_argument(
        "--simulate-missing-initialized",
        action="store_true",
        help="Teaching/negative-test: skip notifications/initialized",
    )
    parser.add_argument(
        "--resource-type",
        default=None,
        help="Convenience arg if schema has property resource_type",
    )
    parser.add_argument(
        "--resource-namespace",
        default=None,
        help="Convenience arg if schema has property namespace",
    )
    return parser


def config_from_args(args: argparse.Namespace) -> SessionConfig:
    if args.timeout <= 0:
        raise UsageError("--timeout must be positive")
    try:
        arguments = json.loads(args.arguments_json)
    except json.JSONDecodeError as exc:
        raise UsageError(f"--arguments-json is not valid JSON: {exc}") from exc
    if not isinstance(arguments, dict):
        raise UsageError("--arguments-json must be a JSON object")
    validate_url(args.url, allow_remote_url=args.allow_remote_url)
    return SessionConfig(
        url=args.url,
        tool=args.tool,
        arguments=arguments,
        timeout=args.timeout,
        protocol_version=args.protocol_version,
        output=args.output,
        quiet=args.quiet,
        allow_remote_url=args.allow_remote_url,
        simulate_missing_initialized=args.simulate_missing_initialized,
        resource_type=args.resource_type,
        resource_namespace=args.resource_namespace,
    )


def emit_result(result: StageResult, *, output: str, quiet: bool) -> None:
    payload = result.to_sanitized_dict()
    if output == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    if quiet:
        status = "PASS" if result.exit_code == ExitCode.SUCCESS else "FAIL"
        print(f"[{status}] exit={result.exit_code} cleanup={result.cleanup}", file=sys.stderr)
        if result.error:
            print(f"error: {result.error}", file=sys.stderr)
        return
    lines = [
        f"requestedProtocolVersion={result.requested_protocol_version}",
        f"negotiatedProtocolVersion={result.negotiated_protocol_version or '?'}",
        f"sessionId={'present' if result.session_id_present else 'missing'}",
        f"initializedHttpStatus={result.initialized_http_status}",
        f"tool={result.tool} succeeded={result.tool_call_succeeded}",
        f"resourceSummary={json.dumps(result.resource_summary, sort_keys=True)}",
        f"cleanup={result.cleanup}",
        f"exitCode={result.exit_code}",
    ]
    if result.error:
        lines.append(f"error={result.error}")
    print("\n".join(lines), file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = config_from_args(args)
    except UsageError as exc:
        _diag(f"[FAIL] {exc}")
        return ExitCode.USAGE
    client = McpSessionClient(config)
    result = client.run()
    emit_result(result, output=config.output, quiet=config.quiet)
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
