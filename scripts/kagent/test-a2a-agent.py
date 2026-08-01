#!/usr/bin/env python3
"""Trustworthy A2A agent test helper for the kagent local lab.

Actions:
    card   Fetch agent details via REST; require accepted + deploymentReady
    probe  Observational JSON-RPC method probe (never claims L4)
    task   Dispatch via pinned message/stream SSE path
    both   card then task

Usage:
    python scripts/kagent/test-a2a-agent.py card --output json
    python scripts/kagent/test-a2a-agent.py task --prompt "List pods in kagent"
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urlparse

SCHEMA_VERSION = "1.0"
DEFAULT_CONTROLLER = "http://127.0.0.1:8083"
DEFAULT_NAMESPACE = "kagent"
DEFAULT_AGENT = "k8s-a2a-agent"
DEFAULT_PROMPT = "List all pods in the kagent namespace"
DISPATCH_METHOD = "message/stream"
MAX_BODY_BYTES = 1_048_576
MAX_SSE_EVENTS = 64

ACCEPTED_TASK_STATES = frozenset({"submitted", "working", "completed", "input_required"})
KNOWN_TASK_STATES = frozenset(
    {
        "submitted",
        "working",
        "completed",
        "input_required",
        "auth_required",
        "failed",
        "canceled",
        "cancelled",
        "rejected",
    }
)
PROBE_METHODS = (
    "tasks/sendTask",
    "message/send",
    "message/stream",
    "agent/getAgentCard",
)


class ExitCode:
    SUCCESS = 0
    GATE = 1
    USAGE = 2
    TRANSPORT = 3


class GateError(Exception):
    """Protocol, card, or dispatch gate failure."""


class TransportFailure(Exception):
    """DNS, connection, timeout, or unusable HTTP."""

    def __init__(self, message: str, *, error_kind: str = "connection") -> None:
        super().__init__(message)
        self.error_kind = error_kind


class UsageFailure(Exception):
    """Invalid CLI input."""


@dataclass
class CardSkillDisplay:
    """Allowlisted skill fields from an agent card. Never retains full skill metadata."""

    name: str | None
    display_name: str | None
    description: str | None


@dataclass
class CardDisplayData:
    """Allowlisted card presentation fields. Never stores the raw card response."""

    agent_name: str | None
    accepted: bool | None
    deployment_ready: bool | None
    model: str | None
    model_provider: str | None
    skills: list[CardSkillDisplay]


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    content_type: str = ""


@dataclass
class EvidenceReport:
    action: str
    observed_at: str = ""
    namespace: str = DEFAULT_NAMESPACE
    agent: str = DEFAULT_AGENT
    controller: str = DEFAULT_CONTROLLER
    endpoint: str = ""
    transport_succeeded: bool = False
    http_status: int | None = None
    transport_error_kind: str | None = None
    transport_error: str | None = None
    jsonrpc: str | None = None
    method: str | None = None
    request_id: str | None = None
    response_id_matched: bool | None = None
    protocol_error: dict[str, Any] | None = None
    dispatch_accepted: bool | None = None
    task_or_message_id: str | None = None
    dispatch_state: str | None = None
    response_kind: str | None = None
    probe_results: dict[str, Any] = field(default_factory=dict)
    card_accepted: bool | None = None
    card_deployment_ready: bool | None = None
    card_display: CardDisplayData | None = None
    decision_passed: bool = False
    exit_code: int = ExitCode.GATE
    reason: str = ""

    def to_sanitized_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "action": self.action,
            "observedAt": self.observed_at,
            "target": {
                "namespace": self.namespace,
                "agent": self.agent,
                "controller": sanitize_controller_origin(self.controller),
                "endpoint": self.endpoint,
            },
            "transport": {
                "succeeded": self.transport_succeeded,
                "httpStatus": self.http_status,
                "errorKind": self.transport_error_kind,
                "error": sanitize_text(self.transport_error),
            },
            "protocol": {
                "jsonRpc": self.jsonrpc,
                "method": self.method,
                "requestId": sanitize_request_id(self.request_id),
                "responseIdMatched": self.response_id_matched,
                "error": sanitize_protocol_error(self.protocol_error),
            },
            "dispatch": {
                "accepted": self.dispatch_accepted,
                "taskOrMessageId": self.task_or_message_id,
                "state": self.dispatch_state,
                "responseKind": self.response_kind,
            },
            "probe": self.probe_results,
            "card": {
                "accepted": self.card_accepted,
                "deploymentReady": self.card_deployment_ready,
            },
            "decision": {
                "passed": self.decision_passed,
                "exitCode": self.exit_code,
                "reason": self.reason,
            },
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


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise GateError(f"redirect refused: HTTP {code}")


class DirectUrlTransport:
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
                raw = resp.read(MAX_BODY_BYTES + 1)
                if len(raw) > MAX_BODY_BYTES:
                    raise GateError(f"response exceeds {MAX_BODY_BYTES} bytes")
                hdrs = {k: v for k, v in resp.headers.items()}
                ctype = resp.headers.get("Content-Type", "") or ""
                return HttpResponse(
                    status=getattr(resp, "status", 200),
                    headers=hdrs,
                    body=raw,
                    content_type=ctype,
                )
        except urllib.error.HTTPError as exc:
            raw = exc.read(MAX_BODY_BYTES + 1) if exc.fp is not None else b""
            if len(raw) > MAX_BODY_BYTES:
                raise GateError(f"response exceeds {MAX_BODY_BYTES} bytes") from exc
            hdrs = {k: v for k, v in exc.headers.items()} if exc.headers else {}
            ctype = hdrs.get("Content-Type", "") or hdrs.get("content-type", "")
            return HttpResponse(status=exc.code, headers=hdrs, body=raw, content_type=ctype)
        except TimeoutError as exc:
            raise TransportFailure(f"timeout: {exc}", error_kind="timeout") from exc
        except urllib.error.URLError as exc:
            reason = exc.reason if hasattr(exc, "reason") else exc
            raise TransportFailure(str(reason), error_kind="connection") from exc
        except OSError as exc:
            raise TransportFailure(str(exc), error_kind="connection") from exc


def utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def sanitize_text(value: str | None, *, limit: int = 240) -> str | None:
    if value is None:
        return None
    text = str(value)
    lowered = text.lower()
    for needle in ("authorization", "bearer ", "kubeconfig", "api-key", "session-id"):
        if needle in lowered:
            return "[redacted]"
    if len(text) > limit:
        return text[:limit] + "…"
    return text


def sanitize_controller_origin(controller: str) -> str:
    parsed = urlparse(controller)
    if not parsed.scheme or not parsed.netloc:
        return controller.rstrip("/")
    hostname = parsed.hostname or ""
    if not hostname:
        return controller.rstrip("/")
    port = None
    try:
        port = parsed.port
    except ValueError:
        port = None
    if port is not None:
        if ":" in hostname:
            return f"{parsed.scheme}://[{hostname}]:{port}"
        return f"{parsed.scheme}://{hostname}:{port}"
    if ":" in hostname:
        return f"{parsed.scheme}://[{hostname}]"
    return f"{parsed.scheme}://{hostname}"


def sanitize_request_id(request_id: str | None) -> str | None:
    if request_id is None:
        return None
    text = str(request_id)
    if len(text) > 64:
        return text[:8] + "…"
    return text


def sanitize_protocol_error(err: dict[str, Any] | None) -> dict[str, Any] | None:
    if err is None:
        return None
    return {
        "code": err.get("code"),
        "message": sanitize_text(str(err.get("message", "")), limit=160),
    }


def validate_controller_url(value: str) -> str:
    """Return a validated controller origin or raise ``UsageFailure``."""
    controller = value.strip()
    if not controller:
        raise UsageFailure("controller URL is required")
    try:
        parsed = urlparse(controller)
    except ValueError as exc:
        raise UsageFailure(f"controller URL could not be parsed: {exc}") from exc
    if parsed.scheme not in {"http", "https"}:
        raise UsageFailure(f"controller URL scheme must be http or https, got {parsed.scheme!r}")
    if not parsed.hostname:
        raise UsageFailure(f"controller URL must have a host, got {controller!r}")
    if parsed.username is not None or parsed.password is not None:
        raise UsageFailure("controller URL must not include userinfo")
    try:
        port = parsed.port
    except ValueError as exc:
        raise UsageFailure(f"controller URL has invalid port: {exc}") from exc
    if port is None:
        raise UsageFailure("controller URL must include an explicit port")
    if parsed.path not in {"", "/"} or parsed.params:
        raise UsageFailure("controller URL must not include a path")
    if parsed.query:
        raise UsageFailure("controller URL must not include a query")
    if parsed.fragment:
        raise UsageFailure("controller URL must not include a fragment")
    return controller.rstrip("/")


def build_a2a_endpoint(base: str, namespace: str, agent: str) -> str:
    return f"/api/a2a/{namespace}/{agent}"


def build_a2a_url(base: str, namespace: str, agent: str) -> str:
    return f"{base.rstrip('/')}{build_a2a_endpoint(base, namespace, agent)}"


def build_agent_rest_url(base: str, namespace: str, agent: str) -> str:
    return f"{base.rstrip('/')}/api/agents/{namespace}/{agent}"


def build_health_url(base: str) -> str:
    return f"{base.rstrip('/')}/health"


def build_dispatch_envelope(request_id: str, prompt: str) -> dict[str, Any]:
    message_id = str(uuid.uuid4())
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": DISPATCH_METHOD,
        "params": {
            "message": {
                "messageId": message_id,
                "role": "user",
                "parts": [{"kind": "text", "text": prompt}],
                "kind": "message",
            }
        },
    }


def parse_sse_jsonrpc_events(body_text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    normalized = body_text.replace("\r\n", "\n").replace("\r", "\n")

    for block in normalized.split("\n\n"):
        data_lines = [line[5:].lstrip() for line in block.splitlines() if line.startswith("data:")]

        if not data_lines:
            continue

        payload = "\n".join(data_lines).strip()

        if not payload or payload == "[DONE]":
            continue

        try:
            obj = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise GateError(f"invalid JSON in SSE data: {exc}") from exc

        if not isinstance(obj, dict):
            raise GateError("SSE data must be a JSON object")

        events.append(obj)

        if len(events) > MAX_SSE_EVENTS:
            raise GateError(f"SSE event count exceeds {MAX_SSE_EVENTS}")

    return events


def decode_response_body(resp: HttpResponse) -> Any:
    if not resp.body:
        return None
    text = resp.body.decode("utf-8", errors="replace")
    ctype = (resp.content_type or "").lower()
    if "text/event-stream" in ctype or text.lstrip().startswith("data:"):
        return parse_sse_jsonrpc_events(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise GateError(f"invalid JSON response: {exc}") from exc


def validate_jsonrpc_response(
    request_id: str, obj: Any
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, bool]:
    """Return (result, error, id_matched). Raises GateError on malformed envelopes."""
    if obj is None:
        raise GateError("null JSON-RPC response")
    if obj == {}:
        raise GateError("empty object is not a valid JSON-RPC response")
    if not isinstance(obj, dict):
        raise GateError("JSON-RPC response must be an object")
    if obj.get("jsonrpc") != "2.0":
        raise GateError("jsonrpc must be '2.0'")
    has_result = "result" in obj
    has_error = "error" in obj
    if has_result == has_error:
        raise GateError("response must contain exactly one of result or error")
    response_id = obj.get("id")
    id_matched = response_id == request_id
    if response_id is None:
        raise GateError("missing response id")
    if not id_matched:
        raise GateError(f"response id mismatch: expected {request_id!r} got {response_id!r}")
    if has_error:
        err = obj["error"]
        if not isinstance(err, dict):
            raise GateError("error must be an object")
        return None, err, id_matched
    result = obj["result"]
    if result is None:
        raise GateError("null result rejected")
    if result == {} or result == [] or result == "":
        raise GateError("empty result rejected")
    return result, None, id_matched


def _extract_dispatch_shape(result: Any) -> tuple[str, str | None, str]:
    """Return a strictly recognized dispatch shape, including terminal task states."""
    if not isinstance(result, dict):
        raise GateError("result must be an object with a recognized task/message shape")

    # Streaming status-update (kagent 0.9.11 / A2A message/stream)
    if result.get("kind") == "status-update":
        task_id = result.get("taskId")
        status = result.get("status")
        if not isinstance(task_id, str) or not task_id.strip():
            raise GateError("status-update missing non-empty taskId")
        if not isinstance(status, dict):
            raise GateError("status-update missing status object")
        state = status.get("state")
        if not isinstance(state, str) or not state.strip():
            raise GateError("status-update status.state missing")
        state_l = state.strip().lower()
        if state_l not in KNOWN_TASK_STATES:
            raise GateError(f"unrecognized task state: {state}")
        return task_id.strip(), state_l, "status-update"

    # Task shape
    task_id = result.get("id")
    status = result.get("status")
    kind = result.get("kind")
    if isinstance(task_id, str) and task_id.strip() and isinstance(status, dict) and kind == "task":
        state = status.get("state")
        if not isinstance(state, str) or not state.strip():
            raise GateError("task status.state missing")
        state_l = state.strip().lower()
        if state_l not in KNOWN_TASK_STATES:
            raise GateError(f"unrecognized task state: {state}")
        return task_id.strip(), state_l, "task"

    # Message shape
    message_id = result.get("messageId")
    role = result.get("role")
    parts = result.get("parts")
    if (
        result.get("kind") == "message"
        and isinstance(message_id, str)
        and message_id.strip()
        and role in {"agent", "user"}
        and isinstance(parts, list)
        and parts
        and all(isinstance(part, dict) and part for part in parts)
    ):
        return message_id.strip(), None, "message"

    raise GateError("result lacks an exact task, status-update, or message shape")


def extract_dispatch_result(result: Any) -> tuple[str, str | None, str]:
    """Return an accepted dispatch result. Raises GateError for terminal task states."""
    dispatch_id, state, response_kind = _extract_dispatch_shape(result)
    if state is not None and state not in ACCEPTED_TASK_STATES:
        raise GateError(f"task state not accepted for gate pass: {state}")
    return dispatch_id, state, response_kind


def select_dispatch_from_events(
    request_id: str, events: list[dict[str, Any]]
) -> tuple[str, str | None, str]:
    """Scan SSE JSON-RPC events; return first accepted dispatch (submitted/working/...).

    Terminal failed/canceled-only streams raise GateError after recording that a
    taskId may have been seen without an accepted state.
    """
    if not events:
        raise GateError("empty SSE stream")

    seen_ids: list[str] = []
    terminal_rejects: list[str] = []
    accepted: list[tuple[str, str | None, str]] = []

    for obj in events:
        # One malformed, mismatched, or error envelope invalidates the response.
        result, err, _matched = validate_jsonrpc_response(request_id, obj)
        if err is not None:
            raise GateError(f"JSON-RPC error code={err.get('code')}: {err.get('message', '')}")
        assert result is not None
        dispatch_id, state, response_kind = _extract_dispatch_shape(result)
        seen_ids.append(dispatch_id)
        if state is None or state in ACCEPTED_TASK_STATES:
            accepted.append((dispatch_id, state, response_kind))
        elif state in {"failed", "canceled", "cancelled", "rejected"}:
            terminal_rejects.append(state)

    if accepted:
        # Prefer completed, then working, then submitted/input_required (first match)
        priority = {"completed": 0, "working": 1, "submitted": 2, "input_required": 3}
        accepted.sort(key=lambda item: priority.get(item[1] or "", 9))
        return accepted[0]

    if seen_ids and terminal_rejects:
        raise GateError(
            f"task state not accepted for gate pass: {terminal_rejects[-1]} "
            f"(taskId seen but no accepted state)"
        )

    raise GateError("result lacks recognized task or message identifier shape")


def select_dispatch_event(request_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    """Backward-compatible single-event selector used by unit tests."""
    selected = select_dispatch_from_events(request_id, events)
    for obj in events:
        result, err, _matched = validate_jsonrpc_response(request_id, obj)
        if err is not None:
            raise GateError(f"JSON-RPC error code={err.get('code')}: {err.get('message', '')}")
        assert result is not None
        try:
            candidate = extract_dispatch_result(result)
        except GateError:
            continue
        if candidate == selected:
            return obj
    raise GateError("accepted dispatch event could not be selected")


def dispatch_task(
    transport: Transport,
    url: str,
    prompt: str,
    *,
    timeout: float = 60.0,
) -> tuple[str, str | None, str, str, int]:
    """Return (task_or_message_id, state, response_kind, request_id, http_status)."""
    request_id, http_status, events = collect_dispatch_stream(
        transport, url, prompt, timeout=timeout
    )
    task_id, state, kind = select_dispatch_from_events(request_id, events)
    return task_id, state, kind, request_id, http_status


def collect_dispatch_stream(
    transport: Transport,
    url: str,
    prompt: str,
    *,
    timeout: float = 60.0,
) -> tuple[str, int, list[dict[str, Any]]]:
    """POST message/stream and return (request_id, http_status, validated event list).

    Additive helper for L6 correlation. Does not change L4 acceptance rules.
    """
    request_id = str(uuid.uuid4())
    envelope = build_dispatch_envelope(request_id, prompt)
    body = json.dumps(envelope).encode()
    resp = transport.request(
        "POST",
        url,
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        body=body,
        timeout=timeout,
    )
    if resp.status >= 400:
        raise TransportFailure(f"HTTP {resp.status}", error_kind="http_error")
    decoded = decode_response_body(resp)
    if isinstance(decoded, list):
        events = decoded
    elif isinstance(decoded, dict):
        events = [decoded]
    else:
        raise GateError("dispatch response must be JSON object or SSE event list")
    # Ensure each event is at least a dict; L4 selection remains fail-closed later
    for obj in events:
        if not isinstance(obj, dict):
            raise GateError("SSE event must be a JSON object")
    return request_id, resp.status, events


def check_connectivity(transport: Transport, base: str, *, timeout: float = 5.0) -> None:
    resp = transport.request("GET", build_health_url(base), headers={}, body=None, timeout=timeout)
    if resp.status >= 400:
        raise TransportFailure(
            f"health check HTTP {resp.status}",
            error_kind="http_error",
        )


def fetch_agent_card(
    transport: Transport, base: str, namespace: str, agent: str, *, timeout: float = 10.0
) -> dict[str, Any]:
    url = build_agent_rest_url(base, namespace, agent)
    resp = transport.request(
        "GET", url, headers={"Accept": "application/json"}, body=None, timeout=timeout
    )
    if resp.status >= 400:
        raise TransportFailure(f"HTTP {resp.status}", error_kind="http_error")
    try:
        data = json.loads(resp.body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise GateError(f"invalid JSON card response: {exc}") from exc
    if not isinstance(data, dict):
        raise GateError("card response must be an object")
    return data


def evaluate_card(card_data: dict[str, Any]) -> tuple[bool, bool]:
    err = card_data.get("error")
    if err is not None and err is not False:
        raise GateError(f"agent card error: {err}")
    if "data" not in card_data:
        raise GateError("card response missing data")
    data = card_data["data"]
    if not isinstance(data, dict):
        raise GateError("card data must be an object")
    accepted = data.get("accepted") is True
    ready = data.get("deploymentReady") is True
    return accepted, ready


def _extract_card_display(card_data: dict[str, Any]) -> CardDisplayData:
    """Extract only allowlisted display fields. Never crashes on missing or malformed data."""
    data = card_data.get("data") or {}
    if not isinstance(data, dict):
        data = {}
    agent = data.get("agent") or {} if isinstance(data.get("agent"), dict) else {}
    meta = agent.get("metadata") or {} if isinstance(agent.get("metadata"), dict) else {}
    spec = agent.get("spec") or {} if isinstance(agent.get("spec"), dict) else {}
    declarative = spec.get("declarative") or {} if isinstance(spec.get("declarative"), dict) else {}
    a2a_config = (
        declarative.get("a2aConfig") or {} if isinstance(declarative.get("a2aConfig"), dict) else {}
    )
    raw_skills = a2a_config.get("skills", [])
    if not isinstance(raw_skills, list):
        raw_skills = []

    ns = meta.get("namespace") if isinstance(meta, dict) else None
    name = meta.get("name") if isinstance(meta, dict) else None
    if ns and name and isinstance(ns, str) and isinstance(name, str):
        agent_name = f"{ns}/{name}"
    elif isinstance(name, str):
        agent_name = name
    elif isinstance(ns, str):
        agent_name = ns
    else:
        agent_name = None

    skills: list[CardSkillDisplay] = []
    for s in raw_skills:
        if isinstance(s, dict):
            skills.append(
                CardSkillDisplay(
                    name=s.get("id") or s.get("name"),
                    display_name=s.get("name"),
                    description=s.get("description"),
                )
            )
        elif isinstance(s, str):
            skills.append(CardSkillDisplay(name=s, display_name=s, description=None))

    return CardDisplayData(
        agent_name=agent_name,
        accepted=data.get("accepted"),
        deployment_ready=data.get("deploymentReady"),
        model=data.get("model"),
        model_provider=data.get("modelProvider"),
        skills=skills,
    )


def probe_methods(
    transport: Transport,
    url: str,
    *,
    timeout: float = 10.0,
) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for method in PROBE_METHODS:
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": {}}).encode()
        try:
            resp = transport.request(
                "POST",
                url,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
                body=body,
                timeout=timeout,
            )
        except TransportFailure as exc:
            results[method] = {
                "status": "transport_error",
                "errorKind": exc.error_kind,
                "error": str(exc),
            }
            continue
        if resp.status >= 400:
            results[method] = {
                "status": "http_error",
                "httpStatus": resp.status,
            }
            continue
        try:
            decoded = decode_response_body(resp)
        except GateError as exc:
            results[method] = {"status": "malformed", "error": str(exc)}
            continue
        obj: Any = decoded
        if isinstance(decoded, list):
            if not decoded:
                results[method] = {"status": "empty_stream"}
                continue
            obj = decoded[0]
        if not isinstance(obj, dict):
            results[method] = {"status": "malformed", "error": "non-object"}
            continue
        if "error" in obj and isinstance(obj["error"], dict):
            code = obj["error"].get("code")
            msg = str(obj["error"].get("message", ""))[:120]
            status = "unsupported" if code == -32601 else "error"
            results[method] = {
                "status": status,
                "code": code,
                "message": msg,
            }
        elif "result" in obj:
            results[method] = {"status": "responded"}
        else:
            results[method] = {"status": "malformed", "error": "no result or error"}
    return results


def run_card(
    transport: Transport,
    report: EvidenceReport,
    *,
    timeout: float = 10.0,
) -> EvidenceReport:
    report.endpoint = f"/api/agents/{report.namespace}/{report.agent}"
    report.method = None
    try:
        check_connectivity(transport, report.controller)
        report.transport_succeeded = True
        card = fetch_agent_card(
            transport, report.controller, report.namespace, report.agent, timeout=timeout
        )
        report.http_status = 200
        accepted, ready = evaluate_card(card)
        report.card_accepted = accepted
        report.card_deployment_ready = ready
        report.card_display = _extract_card_display(card)
        if accepted and ready:
            report.decision_passed = True
            report.exit_code = ExitCode.SUCCESS
            report.reason = "agent accepted and deployment-ready"
        else:
            report.decision_passed = False
            report.exit_code = ExitCode.GATE
            report.reason = "agent is not both accepted and deployment-ready"
    except TransportFailure as exc:
        report.transport_succeeded = False
        report.transport_error_kind = exc.error_kind
        report.transport_error = str(exc)
        report.decision_passed = False
        report.exit_code = ExitCode.TRANSPORT
        report.reason = f"transport failure: {exc}"
    except GateError as exc:
        report.decision_passed = False
        report.exit_code = ExitCode.GATE
        report.reason = str(exc)
    return report


def run_probe(
    transport: Transport,
    report: EvidenceReport,
    *,
    timeout: float = 10.0,
) -> EvidenceReport:
    report.endpoint = build_a2a_endpoint(report.controller, report.namespace, report.agent)
    url = build_a2a_url(report.controller, report.namespace, report.agent)
    try:
        check_connectivity(transport, report.controller)
        report.transport_succeeded = True
        probe = probe_methods(transport, url, timeout=timeout)
        report.probe_results = probe
        transport_fails = [
            v
            for v in probe.values()
            if isinstance(v, dict) and v.get("status") == "transport_error"
        ]
        if transport_fails and len(transport_fails) == len(probe):
            report.decision_passed = False
            report.exit_code = ExitCode.TRANSPORT
            report.reason = "all probe methods failed transport"
            report.transport_succeeded = False
            report.transport_error_kind = "connection"
            report.transport_error = "all probes transport_error"
        else:
            # Observational success even if methods unsupported
            report.decision_passed = True
            report.exit_code = ExitCode.SUCCESS
            report.reason = "probe completed (observational; not L4)"
    except TransportFailure as exc:
        report.transport_succeeded = False
        report.transport_error_kind = exc.error_kind
        report.transport_error = str(exc)
        report.decision_passed = False
        report.exit_code = ExitCode.TRANSPORT
        report.reason = f"transport failure: {exc}"
    except GateError as exc:
        report.decision_passed = False
        report.exit_code = ExitCode.GATE
        report.reason = str(exc)
    return report


def run_task(
    transport: Transport,
    report: EvidenceReport,
    prompt: str,
    *,
    timeout: float = 60.0,
) -> EvidenceReport:
    report.endpoint = build_a2a_endpoint(report.controller, report.namespace, report.agent)
    report.method = DISPATCH_METHOD
    report.jsonrpc = "2.0"
    url = build_a2a_url(report.controller, report.namespace, report.agent)
    try:
        check_connectivity(transport, report.controller)
        report.transport_succeeded = True
        task_id, state, kind, request_id, http_status = dispatch_task(
            transport, url, prompt, timeout=timeout
        )
        report.http_status = http_status
        report.request_id = request_id
        report.response_id_matched = True
        report.task_or_message_id = task_id
        report.dispatch_state = state
        report.response_kind = kind
        report.dispatch_accepted = True
        report.decision_passed = True
        report.exit_code = ExitCode.SUCCESS
        report.reason = f"recognized {kind} dispatch accepted"
    except TransportFailure as exc:
        report.transport_succeeded = False
        report.transport_error_kind = exc.error_kind
        report.transport_error = str(exc)
        report.dispatch_accepted = False
        report.decision_passed = False
        report.exit_code = ExitCode.TRANSPORT
        report.reason = f"transport failure: {exc}"
    except GateError as exc:
        report.dispatch_accepted = False
        report.decision_passed = False
        report.exit_code = ExitCode.GATE
        msg = str(exc)
        report.reason = msg
        # Capture JSON-RPC error codes when present in message
        if "JSON-RPC error code=" in msg:
            try:
                code_part = msg.split("code=", 1)[1].split(":", 1)[0]
                code = int(code_part)
                report.protocol_error = {
                    "code": code,
                    "message": msg.split(":", 1)[-1].strip() if ":" in msg else msg,
                }
            except (ValueError, IndexError):
                report.protocol_error = {"code": None, "message": msg}
        if "response id mismatch" in msg:
            report.response_id_matched = False
    return report


def emit_human(report: EvidenceReport, *, quiet: bool) -> None:
    data = report.to_sanitized_dict()
    if not quiet:
        print("=" * 60)
        print(f"A2A Agent Test: {report.namespace}/{report.agent}")
        print(f"Controller: {sanitize_controller_origin(report.controller)}")
        print(f"Action: {report.action}")
        print("=" * 60)
    decision = data["decision"]
    prefix = "[PASS]" if decision["passed"] else "[FAIL]"
    print(f"{prefix} {decision['reason']} (exit={decision['exitCode']})")
    if report.action == "probe" and report.probe_results:
        print("\n--- Probe ---")
        for method, status in report.probe_results.items():
            print(f"  {method}: {status}")
    if report.action in ("card", "both") and report.card_display is not None:
        d = report.card_display
        print(f"Agent: {d.agent_name or 'unavailable'}")
        print(f"Accepted: {d.accepted if d.accepted is not None else 'unavailable'}")
        _ready = d.deployment_ready
        ready_str = "unavailable" if _ready is None else str(_ready)
        print(f"DeploymentReady: {ready_str}")
        model_label = d.model or "unavailable"
        provider_label = d.model_provider or "unavailable"
        print(f"Model: {model_label} ({provider_label})")
        count = len(d.skills)
        print(f"Skills ({count}): {'none' if count == 0 else ''}")
        for s in d.skills:
            sid = s.name or "?"
            label = s.display_name or sid
            desc = s.description or "(no description)"
            print(f"  - {sid}: {label} - {desc}")
    if report.action in ("task", "both") and report.task_or_message_id:
        print(f"  taskOrMessageId: {report.task_or_message_id}")
        print(f"  state: {report.dispatch_state}")
        print(f"  kind: {report.response_kind}")
    if report.protocol_error:
        print(f"  protocolError: {report.protocol_error}")
    if report.transport_error:
        print(f"  transport: {report.transport_error_kind}: {report.transport_error}")


def emit_json(report: EvidenceReport) -> None:
    print(json.dumps(report.to_sanitized_dict(), indent=2, sort_keys=False))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test kagent A2A agent (trustworthy gate)")
    parser.add_argument(
        "action",
        nargs="?",
        default="both",
        choices=["card", "task", "probe", "both"],
        help="What to test (default: both)",
    )
    parser.add_argument("--controller", default=DEFAULT_CONTROLLER)
    parser.add_argument("--namespace", default=DEFAULT_NAMESPACE)
    parser.add_argument("--agent", default=DEFAULT_AGENT)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument(
        "--output",
        choices=["human", "json"],
        default="human",
        help="Output format (default: human)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal human output (not an evidence protocol)",
    )
    return parser.parse_args(argv)


def run(
    args: argparse.Namespace,
    *,
    transport: Transport | None = None,
) -> EvidenceReport:
    controller = validate_controller_url(str(args.controller or ""))
    if not args.namespace or not args.agent:
        raise UsageFailure("namespace and agent are required")

    transport = transport or DirectUrlTransport()
    observed = utc_now_iso()
    base_fields = {
        "observed_at": observed,
        "namespace": args.namespace,
        "agent": args.agent,
        "controller": controller,
    }

    if args.action == "card":
        report = EvidenceReport(action="card", **base_fields)
        return run_card(transport, report)

    if args.action == "probe":
        report = EvidenceReport(action="probe", **base_fields)
        return run_probe(transport, report)

    if args.action == "task":
        report = EvidenceReport(action="task", **base_fields)
        return run_task(transport, report, args.prompt)

    # both: card then task; fail if either fails; transport from either
    card_report = EvidenceReport(action="card", **base_fields)
    card_report = run_card(transport, card_report)
    if card_report.exit_code == ExitCode.TRANSPORT:
        card_report.action = "both"
        return card_report
    task_report = EvidenceReport(action="task", **base_fields)
    task_report = run_task(transport, task_report, args.prompt)
    combined = EvidenceReport(action="both", **base_fields)
    combined.card_accepted = card_report.card_accepted
    combined.card_deployment_ready = card_report.card_deployment_ready
    combined.card_display = card_report.card_display
    combined.endpoint = task_report.endpoint
    combined.method = task_report.method
    combined.jsonrpc = task_report.jsonrpc
    combined.request_id = task_report.request_id
    combined.response_id_matched = task_report.response_id_matched
    combined.protocol_error = task_report.protocol_error
    combined.dispatch_accepted = task_report.dispatch_accepted
    combined.task_or_message_id = task_report.task_or_message_id
    combined.dispatch_state = task_report.dispatch_state
    combined.response_kind = task_report.response_kind
    combined.http_status = task_report.http_status or card_report.http_status
    combined.transport_succeeded = (
        card_report.transport_succeeded and task_report.transport_succeeded
    )
    combined.transport_error = task_report.transport_error or card_report.transport_error
    combined.transport_error_kind = (
        task_report.transport_error_kind or card_report.transport_error_kind
    )

    if card_report.exit_code != ExitCode.SUCCESS:
        combined.decision_passed = False
        combined.exit_code = card_report.exit_code
        combined.reason = f"card failed: {card_report.reason}"
        return combined
    if task_report.exit_code != ExitCode.SUCCESS:
        combined.decision_passed = False
        combined.exit_code = task_report.exit_code
        combined.reason = f"task failed: {task_report.reason}"
        return combined
    combined.decision_passed = True
    combined.exit_code = ExitCode.SUCCESS
    combined.reason = "card ready and recognized dispatch accepted"
    return combined


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        report = run(args)
    except UsageFailure as exc:
        print(f"[FAIL] usage: {exc}", file=sys.stderr)
        return ExitCode.USAGE

    if args.output == "json":
        emit_json(report)
    else:
        emit_human(report, quiet=args.quiet)
    return int(report.exit_code)


if __name__ == "__main__":
    sys.exit(main())
