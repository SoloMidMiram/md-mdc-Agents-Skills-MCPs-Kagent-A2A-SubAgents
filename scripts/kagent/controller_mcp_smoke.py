#!/usr/bin/env python3
"""Fail-closed native kagent controller MCP federation check.

This helper verifies the client-facing controller contract only:
initialize -> notifications/initialized -> tools/list -> list_agents ->
invoke_agent (bounded) -> invoke_agent (agent-context continuation) ->
list_agents on the same MCP session -> DELETE.

HTTP 405 on DELETE means explicit client-triggered session termination is
unsupported by the pinned controller; it does not mean the session was
deleted. Phase 8 owns lab resource cleanup separately from this MCP DELETE.

It does not prove that an invoked agent used a Kubernetes MCP tool. In
particular, a successful helper path is a diagnostic prerequisite for I3,
not I3 itself: genuine I3 requires a real IDE client plus bounded response
and agent-context continuation. L6 requires the separate same-task
agent/tool/kubectl correlation gate.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from mcp_session_smoke import (
    ACCEPT_HEADER,
    DEFAULT_PROTOCOL_VERSION,
    SESSION_HEADER,
    SUPPORTED_PROTOCOL_VERSIONS,
    DirectUrlTransport,
    ExitCode,
    HttpResponse,
    ProtocolError,
    Transport,
    TransportError,
    UsageError,
    capture_session_id,
    decode_mcp_response,
    validate_url,
)

DEFAULT_URL = "http://127.0.0.1:8083/mcp"
DEFAULT_AGENT = "kagent/k8s-a2a-agent"
DEFAULT_TASK = (
    "Reply exactly: kagent native MCP acceptance. "
    "Do not call Kubernetes, MCP, shell, or any other tool."
)
DEFAULT_EXPECTED_RESPONSE = "kagent native MCP acceptance"
DEFAULT_CONTINUATION_TASK = (
    "Reply exactly: kagent native MCP context continuation. "
    "Do not call Kubernetes, MCP, shell, or any other tool."
)
DEFAULT_CONTINUATION_EXPECTED_RESPONSE = "kagent native MCP context continuation"
CLIENT_INFO = {"name": "kagent-native-mcp-federation", "version": "1.0.0"}
EXPECTED_TOOLS = frozenset({"list_agents", "invoke_agent"})
MAX_TOOLS_LIST_PAGES = 5


@dataclass(frozen=True)
class ControllerMcpConfig:
    url: str = DEFAULT_URL
    agent: str = DEFAULT_AGENT
    task: str = DEFAULT_TASK
    expected_response: str = DEFAULT_EXPECTED_RESPONSE
    continuation_task: str = DEFAULT_CONTINUATION_TASK
    continuation_expected_response: str = DEFAULT_CONTINUATION_EXPECTED_RESPONSE
    timeout: float = 30.0
    protocol_version: str = DEFAULT_PROTOCOL_VERSION
    output: str = "summary"
    quiet: bool = False


@dataclass
class ControllerMcpResult:
    exit_code: int = ExitCode.PROTOCOL_OR_TOOL
    controller: str = ""
    requested_protocol_version: str = ""
    negotiated_protocol_version: str = ""
    server_name: str = ""
    server_version: str = ""
    session_id_present: bool = False
    initialized_http_status: int | None = None
    tools_list_http_status: int | None = None
    controller_tools: list[str] = field(default_factory=list)
    target_agent: str = ""
    target_agent_found: bool = False
    invoke_http_status: int | None = None
    invoke_agent_succeeded: bool = False
    agent_response: str = ""
    agent_context_id: str = "missing"
    agent_context_continuation_succeeded: bool = False
    continuation_http_status: int | None = None
    continuation_agent_response: str = ""
    same_mcp_session_reuse_http_status: int | None = None
    mcp_session_reuse_target_present: bool = False
    cleanup: str = "not-attempted"
    error: str | None = None

    def to_sanitized_dict(self) -> dict[str, Any]:
        return {
            "controller": self.controller,
            "requestedProtocolVersion": self.requested_protocol_version,
            "negotiatedProtocolVersion": self.negotiated_protocol_version,
            "server": {"name": self.server_name, "version": self.server_version},
            "sessionId": "present" if self.session_id_present else "missing",
            "initializedHttpStatus": self.initialized_http_status,
            "toolsListHttpStatus": self.tools_list_http_status,
            "controllerTools": self.controller_tools,
            "targetAgent": self.target_agent,
            "targetAgentFound": self.target_agent_found,
            "invokeHttpStatus": self.invoke_http_status,
            "invokeAgentSucceeded": self.invoke_agent_succeeded,
            "agentResponse": self.agent_response,
            "agentContextId": self.agent_context_id,
            "agentContextContinuationSucceeded": self.agent_context_continuation_succeeded,
            "continuationHttpStatus": self.continuation_http_status,
            "continuationAgentResponse": self.continuation_agent_response,
            "sameMcpSessionReuseHttpStatus": self.same_mcp_session_reuse_http_status,
            "mcpSessionReuseTargetPresent": self.mcp_session_reuse_target_present,
            "cleanup": self.cleanup,
            "error": self.error,
            "exitCode": self.exit_code,
        }


def _sanitized_controller(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port is not None else ""
    return f"{parsed.scheme}://{host}{port}{parsed.path}"


def _sanitize_text(text: str) -> str:
    """Keep useful agent output while never retaining URI userinfo."""
    return re.sub(r"(https?://)[^\s/@:]+:[^\s/@]+@", r"\1<redacted>@", text)


def validate_controller_url(url: str) -> None:
    """Allow only a loopback Streamable HTTP controller endpoint."""
    validate_url(url, allow_remote_url=False)
    parsed = urlparse(url)
    if parsed.username is not None or parsed.password is not None:
        raise UsageError("controller URL must not contain userinfo")
    if parsed.path != "/mcp" or parsed.params or parsed.query or parsed.fragment:
        raise UsageError("controller URL must be a bare loopback /mcp endpoint")


def extract_agent_context_id(structured: dict[str, Any]) -> str:
    """Return a non-empty context_id or raise without echoing the value."""
    if "context_id" not in structured:
        raise ProtocolError("invoke_agent structuredContent is missing context_id")
    value = structured["context_id"]
    if not isinstance(value, str):
        raise ProtocolError("invoke_agent context_id must be a non-empty string")
    if not value:
        raise ProtocolError("invoke_agent context_id must be a non-empty string")
    return value


class ControllerMcpClient:
    def __init__(self, config: ControllerMcpConfig, transport: Transport | None = None) -> None:
        self.config = config
        self.transport = transport or DirectUrlTransport()
        self._session_id: str | None = None
        self._agent_context_id: str | None = None
        self._next_id = 1
        self.result = ControllerMcpResult(
            controller=_sanitized_controller(config.url),
            requested_protocol_version=config.protocol_version,
            target_agent=config.agent,
        )

    def _alloc_id(self) -> int:
        request_id = self._next_id
        self._next_id += 1
        return request_id

    def _headers(self, *, with_session: bool) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": ACCEPT_HEADER}
        if with_session:
            if self._session_id is None:
                raise ProtocolError("MCP session id is required but missing")
            headers[SESSION_HEADER] = self._session_id
        return headers

    def _post(
        self,
        payload: dict[str, Any],
        *,
        with_session: bool,
        expected_id: int | None,
        allow_empty: bool = False,
    ) -> tuple[HttpResponse, dict[str, Any] | None]:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        response = self.transport.request(
            "POST",
            self.config.url,
            headers=self._headers(with_session=with_session),
            body=body,
            timeout=self.config.timeout,
        )
        if response.status < 200 or response.status >= 300:
            raise ProtocolError(f"{payload['method']} HTTP {response.status}")
        if allow_empty and not response.body.strip():
            return response, None
        if expected_id is None:
            return response, None
        message = decode_mcp_response(response.content_type, response.body, expected_id)
        if "error" in message:
            raise ProtocolError(f"{payload['method']} JSON-RPC error: {message['error']}")
        return response, message

    def _initialize(self) -> None:
        request_id = self._alloc_id()
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": self.config.protocol_version,
                "capabilities": {},
                "clientInfo": CLIENT_INFO,
            },
        }
        response, message = self._post(payload, with_session=False, expected_id=request_id)
        assert message is not None
        result = message.get("result")
        if not isinstance(result, dict):
            raise ProtocolError("initialize missing result object")
        negotiated = result.get("protocolVersion")
        if not isinstance(negotiated, str) or negotiated not in SUPPORTED_PROTOCOL_VERSIONS:
            raise ProtocolError("initialize returned an unsupported protocol version")
        info = result.get("serverInfo")
        if not isinstance(info, dict):
            raise ProtocolError("initialize missing serverInfo object")
        name, version = info.get("name"), info.get("version")
        if not isinstance(name, str) or not name or not isinstance(version, str) or not version:
            raise ProtocolError("initialize serverInfo requires non-empty name and version")
        self._session_id = capture_session_id(response.headers)
        self.result.negotiated_protocol_version = negotiated
        self.result.server_name = name
        self.result.server_version = version
        self.result.session_id_present = True

    def _send_initialized(self) -> None:
        response, _ = self._post(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            with_session=True,
            expected_id=None,
            allow_empty=True,
        )
        self.result.initialized_http_status = response.status

    def _list_tools(self) -> dict[str, dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        cursor: str | None = None
        for _ in range(MAX_TOOLS_LIST_PAGES):
            request_id = self._alloc_id()
            params: dict[str, Any] = {} if cursor is None else {"cursor": cursor}
            response, message = self._post(
                {"jsonrpc": "2.0", "id": request_id, "method": "tools/list", "params": params},
                with_session=True,
                expected_id=request_id,
            )
            self.result.tools_list_http_status = response.status
            assert message is not None
            payload = message.get("result")
            if not isinstance(payload, dict) or not isinstance(payload.get("tools"), list):
                raise ProtocolError("tools/list result.tools must be a list")
            for tool in payload["tools"]:
                if not isinstance(tool, dict):
                    raise ProtocolError("tools/list contains a malformed tool")
                tools.append(tool)
            next_cursor = payload.get("nextCursor")
            if next_cursor is None:
                break
            if not isinstance(next_cursor, str) or not next_cursor:
                raise ProtocolError("tools/list nextCursor must be a non-empty string")
            cursor = next_cursor
        else:
            raise ProtocolError(f"tools/list exceeded {MAX_TOOLS_LIST_PAGES} pages")

        definitions: dict[str, dict[str, Any]] = {}
        for tool in tools:
            name = tool.get("name")
            if not isinstance(name, str) or not name:
                raise ProtocolError("tools/list tool is missing name")
            if name in definitions:
                raise ProtocolError(f"tools/list repeats tool {name!r}")
            definitions[name] = tool
        self.result.controller_tools = sorted(definitions)
        if set(definitions) != EXPECTED_TOOLS:
            unexpected = sorted(set(definitions) - EXPECTED_TOOLS)
            missing = sorted(EXPECTED_TOOLS - set(definitions))
            details = []
            if missing:
                details.append(f"missing required controller tools: {', '.join(missing)}")
            if unexpected:
                details.append(
                    f"unexpected privileged or unreviewed controller tools: {', '.join(unexpected)}"
                )
            raise ProtocolError("; ".join(details))
        self._validate_controller_schemas(definitions)
        return definitions

    @staticmethod
    def _validate_controller_schemas(definitions: dict[str, dict[str, Any]]) -> None:
        list_schema = definitions["list_agents"].get("inputSchema")
        invoke_schema = definitions["invoke_agent"].get("inputSchema")
        if not isinstance(list_schema, dict) or list_schema.get("type") != "object":
            raise ProtocolError("list_agents inputSchema must be an object")
        if (
            list_schema.get("properties") != {}
            or list_schema.get("additionalProperties") is not False
        ):
            raise ProtocolError("list_agents must not accept caller-controlled arguments")
        if not isinstance(invoke_schema, dict) or invoke_schema.get("type") != "object":
            raise ProtocolError("invoke_agent inputSchema must be an object")
        properties = invoke_schema.get("properties")
        required = invoke_schema.get("required")
        if not isinstance(properties, dict) or set(properties) != {"agent", "task", "context_id"}:
            raise ProtocolError(
                "invoke_agent inputSchema properties changed from the pinned contract"
            )
        if required != ["agent", "task"] or invoke_schema.get("additionalProperties") is not False:
            raise ProtocolError(
                "invoke_agent inputSchema required fields changed from the pinned contract"
            )
        if any(
            not isinstance(properties[name], dict) or properties[name].get("type") != "string"
            for name in properties
        ):
            raise ProtocolError("invoke_agent inputSchema arguments must be strings")

    def _call_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> tuple[HttpResponse, dict[str, Any]]:
        request_id = self._alloc_id()
        response, message = self._post(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
            with_session=True,
            expected_id=request_id,
        )
        assert message is not None
        result = message.get("result")
        if not isinstance(result, dict) or result.get("isError") is True:
            raise ProtocolError(f"{name} returned an error result")
        return response, result

    @staticmethod
    def _agent_refs(result: dict[str, Any]) -> set[str]:
        structured = result.get("structuredContent")
        if not isinstance(structured, dict) or not isinstance(structured.get("agents"), list):
            raise ProtocolError("list_agents must return structuredContent.agents")
        refs: set[str] = set()
        for item in structured["agents"]:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("ref"), str)
                or not item["ref"]
            ):
                raise ProtocolError("list_agents contains an invalid agent reference")
            refs.add(item["ref"])
        return refs

    def _list_target_agent(self, *, session_reuse: bool) -> None:
        response, result = self._call_tool("list_agents", {})
        refs = self._agent_refs(result)
        present = self.config.agent in refs
        if session_reuse:
            self.result.same_mcp_session_reuse_http_status = response.status
            self.result.mcp_session_reuse_target_present = present
        else:
            self.result.target_agent_found = present
        if not present:
            raise ProtocolError(
                f"target agent {self.config.agent!r} was not returned by list_agents"
            )

    def _invoke_structured(
        self, arguments: dict[str, Any]
    ) -> tuple[HttpResponse, dict[str, Any], str]:
        response, result = self._call_tool("invoke_agent", arguments)
        structured = result.get("structuredContent")
        if not isinstance(structured, dict) or structured.get("agent") != self.config.agent:
            raise ProtocolError(
                "invoke_agent must return structuredContent for the requested agent"
            )
        text = structured.get("text")
        if not isinstance(text, str):
            raise ProtocolError("invoke_agent structuredContent.text must be a string")
        return response, structured, text

    def _invoke_agent(self) -> None:
        response, structured, text = self._invoke_structured(
            {"agent": self.config.agent, "task": self.config.task}
        )
        self.result.invoke_http_status = response.status
        self.result.agent_response = _sanitize_text(text)
        if text != self.config.expected_response:
            raise ProtocolError("invoke_agent did not return the required bounded no-tool response")
        context_id = extract_agent_context_id(structured)
        self._agent_context_id = context_id
        self.result.agent_context_id = "present"
        self.result.invoke_agent_succeeded = True

    def _continue_agent_context(self) -> None:
        if self._agent_context_id is None:
            raise ProtocolError("agent context continuation requires a captured context_id")
        response, structured, text = self._invoke_structured(
            {
                "agent": self.config.agent,
                "task": self.config.continuation_task,
                "context_id": self._agent_context_id,
            }
        )
        self.result.continuation_http_status = response.status
        self.result.continuation_agent_response = _sanitize_text(text)
        # Fail closed if the provider/agent returns an error-shaped success body.
        if text != self.config.continuation_expected_response:
            raise ProtocolError(
                "invoke_agent context continuation did not return the required bounded response"
            )
        # Re-validate context identity without echoing raw values.
        continued = extract_agent_context_id(structured)
        if continued != self._agent_context_id:
            raise ProtocolError("invoke_agent context continuation changed context_id")
        self.result.agent_context_continuation_succeeded = True

    def _close(self) -> str:
        if self._session_id is None:
            return "not-applicable"
        try:
            response = self.transport.request(
                "DELETE",
                self.config.url,
                headers=self._headers(with_session=True),
                timeout=self.config.timeout,
            )
        except (ProtocolError, TransportError):
            return "failed"
        if 200 <= response.status < 300:
            return "deleted"
        if response.status == 405:
            # Explicit client-triggered termination unsupported; session not proven deleted.
            return "method-not-allowed"
        return "failed"

    def run(self) -> ControllerMcpResult:
        try:
            validate_controller_url(self.config.url)
            if self.config.protocol_version not in SUPPORTED_PROTOCOL_VERSIONS:
                raise UsageError("unsupported requested MCP protocol version")
            if self.config.timeout <= 0:
                raise UsageError("timeout must be greater than zero")
            self._initialize()
            self._send_initialized()
            self._list_tools()
            self._list_target_agent(session_reuse=False)
            self._invoke_agent()
            self._continue_agent_context()
            self._list_target_agent(session_reuse=True)
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
            self.result.cleanup = self._close()
            if self.result.cleanup == "failed" and self.result.exit_code == ExitCode.SUCCESS:
                self.result.exit_code = ExitCode.PROTOCOL_OR_TOOL
                self.result.error = "MCP session cleanup failed"
            # Never leak a captured context identifier into serialized output.
            if self._agent_context_id is not None:
                raw = self._agent_context_id
                rendered = json.dumps(self.result.to_sanitized_dict(), sort_keys=True)
                if raw in rendered or (self.result.error and raw in self.result.error):
                    self.result.exit_code = ExitCode.PROTOCOL_OR_TOOL
                    self.result.agent_context_continuation_succeeded = False
                    self.result.error = "sanitized output leaked agent context identifier"
        return self.result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="Loopback controller MCP endpoint")
    parser.add_argument(
        "--agent", default=DEFAULT_AGENT, help="Expected namespace/name agent reference"
    )
    parser.add_argument("--task", default=DEFAULT_TASK, help="Bounded no-tool agent task")
    parser.add_argument(
        "--expected-response", default=DEFAULT_EXPECTED_RESPONSE, help="Exact expected agent text"
    )
    parser.add_argument(
        "--continuation-task",
        default=DEFAULT_CONTINUATION_TASK,
        help="Bounded no-tool follow-up task for agent-context continuation",
    )
    parser.add_argument(
        "--continuation-expected-response",
        default=DEFAULT_CONTINUATION_EXPECTED_RESPONSE,
        help="Exact expected follow-up agent text",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds")
    parser.add_argument("--protocol-version", default=DEFAULT_PROTOCOL_VERSION)
    parser.add_argument("--output", choices=("summary", "json"), default="summary")
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = ControllerMcpClient(
        ControllerMcpConfig(
            url=args.url,
            agent=args.agent,
            task=args.task,
            expected_response=args.expected_response,
            continuation_task=args.continuation_task,
            continuation_expected_response=args.continuation_expected_response,
            timeout=args.timeout,
            protocol_version=args.protocol_version,
            output=args.output,
            quiet=args.quiet,
        )
    ).run()
    if not args.quiet:
        if args.output == "json":
            print(json.dumps(result.to_sanitized_dict(), sort_keys=True))
        else:
            print(
                " ".join(
                    (
                        f"exitCode={result.exit_code}",
                        f"server={result.server_name or 'unavailable'}",
                        f"targetAgentFound={result.target_agent_found}",
                        f"invokeAgentSucceeded={result.invoke_agent_succeeded}",
                        f"agentContextContinuationSucceeded="
                        f"{result.agent_context_continuation_succeeded}",
                        f"mcpSessionReuseTargetPresent="
                        f"{result.mcp_session_reuse_target_present}",
                        f"cleanup={result.cleanup}",
                    )
                )
            )
            if result.error:
                print(f"error={result.error}")
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
