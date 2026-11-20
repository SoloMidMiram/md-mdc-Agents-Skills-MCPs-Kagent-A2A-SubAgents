#!/usr/bin/env python3
"""Bounded interoperability experiment for the official Python A2A SDK.

The pinned kagent 0.9.11 controller exposes its agent details at
``/api/agents/{namespace}/{agent}``, not at the standard well-known Agent Card
URL.  This module adapts that read-only details response into the official
``a2a.types.AgentCard`` model, validates the A2A protocol family, and then uses
the official SDK client for one ``message/stream`` request.

This experiment deliberately proves communication only.  It does not inspect
controller or agent logs and therefore never claims that an MCP tool ran.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
import sys
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from urllib.parse import urlparse

DEFAULT_CONTROLLER = "http://127.0.0.1:8083"
DEFAULT_NAMESPACE = "kagent"
DEFAULT_AGENT = "k8s-a2a-agent"
DEFAULT_PROTOCOL_VERSION = "0.3.0"
DEFAULT_PROMPT = "Reply ACK. Do not call tools."
MAX_RESPONSE_TEXT = 2_000
MAX_CAPTURED_RESPONSE_BYTES = 1_048_576
MAX_EVENTS = 1024
FAILED_STATES = frozenset({"failed", "canceled", "rejected"})
KNOWN_STATES = FAILED_STATES | {
    "submitted",
    "working",
    "completed",
    "input-required",
    "auth-required",
}
SENSITIVE = re.compile(
    r"authorization|bearer\s|api[-_ ]?key|token|password|secret|credential|"
    r"master[-_ ]?key|session[-_ ]?id|kubeconfig|-----BEGIN.*PRIVATE KEY",
    re.IGNORECASE,
)


def _safe_text(value: str) -> str:
    def origin(match: re.Match[str]) -> str:
        try:
            parsed = urlparse(match[0])
            host = parsed.hostname or ""
            if ":" in host:
                host = f"[{host}]"
            return f"{parsed.scheme}://{host}" + (f":{parsed.port}" if parsed.port else "")
        except ValueError:
            return "[redacted-url]"

    text = re.sub(r"https?://[^\s<>\"']+", origin, value)
    return "[redacted]" if SENSITIVE.search(text) else text[:MAX_RESPONSE_TEXT]


def _safe_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[redacted]" if SENSITIVE.search(key) else _safe_json(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_safe_json(item) for item in value]
    return _safe_text(value) if isinstance(value, str) else value


class UsageError(Exception):
    """The experiment was invoked with invalid local input."""


class CardError(Exception):
    """The kagent Agent Card could not be discovered or normalized."""


class ProtocolCompatibilityError(Exception):
    """The requested A2A protocol family is not advertised by the card."""


class TransportError(Exception):
    """The controller could not be reached or returned an unusable response."""


class DispatchError(Exception):
    """The SDK could not complete the A2A dispatch or correlation gate."""

    def __init__(
        self,
        message: str,
        *,
        observation: DispatchObservation | None = None,
        outcome: str = "invalid",
    ) -> None:
        super().__init__(_safe_text(message))
        self.observation = observation
        self.outcome = outcome


@dataclass(frozen=True)
class KagentCard:
    """The normalized card plus the evidence-safe fields used by this client."""

    card: Any
    endpoint: str
    agent_name: str
    accepted: bool
    deployment_ready: bool
    model: str | None
    model_provider: str | None
    skill_ids: tuple[str, ...]
    protocol_version: str
    protocol_version_source: str


@dataclass
class WireTrace:
    """Bounded wire metadata captured without retaining request/response bodies."""

    request_id: str | None = None
    message_id: str | None = None
    method: str | None = None
    http_status: int | None = None
    response_content_type: str | None = None
    response_ids: list[str | None] = field(default_factory=list)
    response_error_codes: list[int | None] = field(default_factory=list)
    response_event_count: int = 0
    wire_error: bool = False
    capture_truncated: bool = False
    task_id: str | None = None
    dispatch_accepted: bool = False
    _response_bytes: bytearray = field(default_factory=bytearray, repr=False)

    def append_response_bytes(self, chunk: bytes) -> None:
        remaining = MAX_CAPTURED_RESPONSE_BYTES - len(self._response_bytes)
        if len(chunk) > remaining:
            self.capture_truncated = True
            raise ValueError("bounded response capture exceeded")
        if remaining > 0:
            self._response_bytes.extend(chunk[:remaining])

    def finalize_response(self) -> None:
        """Extract only JSON-RPC IDs/error codes from the captured SSE stream."""
        if not self._response_bytes:
            return
        normalized = bytes(self._response_bytes).decode("utf-8", errors="replace")
        for block in normalized.replace("\r\n", "\n").replace("\r", "\n").split("\n\n"):
            data_lines = [
                line[5:].lstrip() for line in block.splitlines() if line.startswith("data:")
            ]
            payload = "\n".join(data_lines).strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                event = json.loads(payload)
            except json.JSONDecodeError:
                self.wire_error = True
                continue
            if not isinstance(event, dict):
                self.wire_error = True
                continue
            self.response_event_count += 1
            matched = bool(self.request_id) and event.get("id") == self.request_id
            self.response_ids.append(self.request_id if matched else None)
            if (
                not matched
                or event.get("jsonrpc") != "2.0"
                or ("result" in event) == ("error" in event)
            ):
                self.wire_error = True
            result = event.get("result")
            if isinstance(result, dict):
                kind = result.get("kind")
                task_id = result.get("id") if kind == "task" else result.get("taskId")
                if (
                    not isinstance(kind, str)
                    or kind not in {"task", "status-update", "artifact-update"}
                    or not isinstance(task_id, str)
                    or not task_id.strip()
                    or (self.task_id is not None and task_id != self.task_id)
                ):
                    self.wire_error = True
                elif matched:
                    self.task_id = task_id
                    status = result.get("status")
                    if (
                        isinstance(status, dict)
                        and isinstance(status.get("state"), str)
                        and status.get("state")
                        in {
                            "submitted",
                            "working",
                            "completed",
                            "input-required",
                            "auth-required",
                        }
                    ):
                        self.dispatch_accepted = True
            error = event.get("error")
            if isinstance(error, dict):
                code = error.get("code")
                self.response_error_codes.append(code if isinstance(code, int) else None)
        self._response_bytes.clear()


@dataclass(frozen=True)
class StatusTransition:
    kind: str
    task_id: str | None
    state: str | None
    final: bool | None


@dataclass(frozen=True)
class DispatchObservation:
    request_id: str | None
    message_id: str
    task_id: str | None
    status_transitions: tuple[StatusTransition, ...]
    response_text: str
    final_state: str | None
    response_ids: tuple[str | None, ...]
    response_error_codes: tuple[int | None, ...]
    response_event_count: int
    http_status: int | None
    outcome: str = "incomplete"
    dispatch_accepted: bool = False
    wire_valid: bool = False


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first_text(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _protocol_family(value: str) -> str:
    text = value.strip()
    match = re.fullmatch(r"(\d+)\.(\d+)(?:\.\d+)?", text)
    if match is None:
        raise ProtocolCompatibilityError(f"invalid A2A protocol version {value!r}")
    return f"{match.group(1)}.{match.group(2)}"


def validate_protocol_compatibility(advertised: str, requested: str) -> str:
    """Return the wire version after checking major/minor compatibility."""
    advertised_family = _protocol_family(advertised)
    requested_family = _protocol_family(requested)
    if advertised_family != requested_family:
        raise ProtocolCompatibilityError(
            f"unsupported A2A protocol version: requested={requested}, advertised={advertised}"
        )
    return requested_family


def validate_controller_url(value: str) -> str:
    controller = value.strip().rstrip("/")
    parsed = urlparse(controller)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UsageError("controller URL must be an http(s) URL with a host")
    if parsed.username is not None or parsed.password is not None:
        raise UsageError("controller URL must not include userinfo")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise UsageError("controller URL must not include a path, query, or fragment")
    if parsed.port is None:
        raise UsageError("controller URL must include an explicit port")
    return controller


def build_card_url(controller: str, namespace: str, agent: str) -> str:
    return f"{controller.rstrip('/')}/api/agents/{namespace}/{agent}"


def build_a2a_url(controller: str, namespace: str, agent: str) -> str:
    return f"{controller.rstrip('/')}/api/a2a/{namespace}/{agent}"


def _protocol_from_kagent_data(data: dict[str, Any], fallback: str | None) -> tuple[str, str]:
    agent = _mapping(data.get("agent"))
    spec = _mapping(agent.get("spec"))
    declarative = _mapping(spec.get("declarative"))
    a2a_config = _mapping(declarative.get("a2aConfig"))
    explicit = _first_text(
        data.get("protocolVersion"),
        data.get("protocol_version"),
        a2a_config.get("protocolVersion"),
        a2a_config.get("protocol_version"),
    )
    if explicit:
        return explicit, "agent-card"
    if fallback:
        return fallback, "kagent-controller-compatibility-profile"
    raise CardError("Agent Card does not advertise protocolVersion")


def build_official_agent_card(
    payload: dict[str, Any],
    *,
    endpoint: str,
    fallback_protocol_version: str | None = DEFAULT_PROTOCOL_VERSION,
) -> KagentCard:
    """Validate kagent details and adapt them into the official SDK card type."""
    if not isinstance(payload, dict):
        raise CardError("Agent Card must be an object")
    if (error := payload.get("error")) is not None and error is not False:
        raise CardError("Agent Card endpoint returned an error")
    data = _mapping(payload.get("data"))
    if not data:
        raise CardError("Agent Card response is missing data")
    if data.get("accepted") is not True or data.get("deploymentReady") is not True:
        raise CardError("agent is not both accepted and deployment-ready")

    agent = _mapping(data.get("agent"))
    metadata = _mapping(agent.get("metadata"))
    spec = _mapping(agent.get("spec"))
    declarative = _mapping(spec.get("declarative"))
    a2a_config = _mapping(declarative.get("a2aConfig"))
    namespace = _first_text(metadata.get("namespace"))
    name = _first_text(metadata.get("name"))
    if not namespace or not name:
        raise CardError("Agent Card must identify its namespace and agent")
    agent_name = f"{namespace}/{name}"
    raw_skills = a2a_config.get("skills", [])
    if not isinstance(raw_skills, list):
        raise CardError("Agent Card skills must be a list")
    protocol_version, protocol_source = _protocol_from_kagent_data(data, fallback_protocol_version)
    wire_family = _protocol_family(protocol_version)

    from a2a.types import AgentCapabilities, AgentCard, AgentSkill

    skills: list[Any] = []
    skill_ids: list[str] = []
    for raw_skill in raw_skills:
        if not isinstance(raw_skill, dict):
            raise CardError("Agent Card skill must be an object")
        skill = _mapping(raw_skill)
        for key in ("tags", "examples", "inputModes", "outputModes"):
            values = skill.get(key, [])
            if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
                raise CardError("Agent Card skill fields must be lists of strings")
        skill_id = _first_text(skill.get("id"))
        if not skill_id:
            raise CardError("Agent Card skill lacks its identity")
        skill_ids.append(skill_id)
        skills.append(
            AgentSkill(
                id=skill_id,
                name=_first_text(skill.get("name")) or skill_id,
                description=_first_text(skill.get("description")) or "kagent skill",
                tags=[str(tag) for tag in skill.get("tags", []) if isinstance(tag, str)],
                examples=[
                    str(example)
                    for example in skill.get("examples", [])
                    if isinstance(example, str)
                ]
                or None,
                input_modes=[
                    str(mode) for mode in skill.get("inputModes", []) if isinstance(mode, str)
                ]
                or ["text"],
                output_modes=[
                    str(mode) for mode in skill.get("outputModes", []) if isinstance(mode, str)
                ]
                or ["text"],
            )
        )

    card = AgentCard(
        name=name,
        description=_first_text(spec.get("description"), data.get("description"))
        or "kagent read-only Kubernetes inspection agent",
        url=endpoint,
        version=_first_text(data.get("version")) or "kagent-controller-0.9.11",
        protocol_version=protocol_version,
        preferred_transport="JSONRPC",
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        default_input_modes=["text"],
        default_output_modes=["text"],
        skills=skills,
    )
    if _protocol_family(card.protocol_version or "") != wire_family:
        raise CardError("normalized Agent Card protocol version is inconsistent")
    return KagentCard(
        card=card,
        endpoint=endpoint,
        agent_name=agent_name,
        accepted=True,
        deployment_ready=True,
        model=_first_text(data.get("model")),
        model_provider=_first_text(data.get("modelProvider"), data.get("model_provider")),
        skill_ids=tuple(skill_ids),
        protocol_version=protocol_version,
        protocol_version_source=protocol_source,
    )


async def discover_agent_card(
    http_client: Any,
    *,
    controller: str,
    namespace: str,
    agent: str,
    fallback_protocol_version: str | None,
) -> KagentCard:
    endpoint = build_a2a_url(controller, namespace, agent)
    try:
        response = await http_client.get(
            build_card_url(controller, namespace, agent),
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # httpx exception types vary by supported SDK dependency
        raise TransportError(f"Agent Card request failed: {type(exc).__name__}: {exc}") from exc
    if not isinstance(payload, dict):
        raise CardError("Agent Card response must be a JSON object")
    card = build_official_agent_card(
        payload,
        endpoint=endpoint,
        fallback_protocol_version=fallback_protocol_version,
    )
    if card.agent_name != f"{namespace}/{agent}":
        raise CardError("Agent Card identity does not match the requested target")
    return card


def _event_state(event: Any) -> str | None:
    status = getattr(event, "status", None)
    state = getattr(status, "state", None)
    value = getattr(state, "value", state)
    return str(value) if value is not None else None


def _event_task_id(event: Any) -> str | None:
    value = getattr(event, "task_id", None) or getattr(event, "id", None)
    return str(value) if value else None


def _message_text(message: Any) -> str:
    parts = getattr(message, "parts", None) or []
    texts: list[str] = []
    for part in parts:
        root = getattr(part, "root", part)
        text = getattr(root, "text", None)
        if isinstance(text, str) and text:
            texts.append(text)
    return " ".join(texts)


def _event_text(event: Any) -> str:
    status = getattr(event, "status", None)
    text = _message_text(getattr(status, "message", None)) if status is not None else ""
    if text:
        return text
    return " ".join(
        filter(
            None,
            [
                _message_text(event),
                _message_text(getattr(event, "artifact", None)),
                *(_message_text(item) for item in (getattr(event, "artifacts", None) or [])),
            ],
        )
    )


class _TraceInterceptor:
    """SDK interceptor that records the actual JSON-RPC request id on the wire."""

    def __init__(self, trace: WireTrace) -> None:
        self.trace = trace

    async def intercept(
        self,
        method_name: str,
        request_payload: dict[str, Any],
        http_kwargs: dict[str, Any],
        agent_card: Any,
        context: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if method_name == "message/stream":
            self.trace.method = method_name
            request_id = request_payload.get("id")
            self.trace.request_id = (
                request_id if isinstance(request_id, str) and request_id.strip() else None
            )
            params = _mapping(request_payload.get("params"))
            message = _mapping(params.get("message"))
            if message.get("messageId") is not None:
                self.trace.message_id = str(message["messageId"])
        return request_payload, http_kwargs


def _install_response_recorder(http_client: Any, trace: WireTrace) -> Callable[[], None]:
    import httpx

    class RecordingStream(httpx.AsyncByteStream):
        def __init__(self, wrapped: Any) -> None:
            self.wrapped = wrapped

        async def __aiter__(self) -> AsyncIterator[bytes]:
            async for chunk in self.wrapped:
                trace.append_response_bytes(chunk)
                yield chunk

        async def aclose(self) -> None:
            await self.wrapped.aclose()

    async def response_hook(response: Any) -> None:
        if response.request.method != "POST":
            return
        try:
            request = json.loads(response.request.content)
        except (ValueError, UnicodeError):
            return
        if not isinstance(request, dict) or request.get("id") != trace.request_id:
            return
        trace.http_status = response.status_code
        trace.response_content_type = response.headers.get("content-type")
        response.stream = RecordingStream(response.stream)

    hooks = http_client.event_hooks.setdefault("response", [])
    hooks.append(response_hook)

    def remove() -> None:
        if response_hook in hooks:
            hooks.remove(response_hook)

    return remove


async def dispatch_read_only_task(
    http_client: Any,
    card: KagentCard,
    *,
    prompt: str,
    requested_protocol_version: str,
    timeout: float,
    observe_event: Callable[[Any], None] | None = None,
) -> DispatchObservation:
    """Send one task through the official SDK after validating the card version.

    The optional observer sees provisional typed results. Use them only after
    this function returns successfully with complete wire validation.
    """
    if not math.isfinite(timeout) or timeout <= 0:
        raise UsageError("timeout must be finite and positive")
    deadline = asyncio.get_running_loop().time() + timeout
    wire_version = validate_protocol_compatibility(
        card.protocol_version, requested_protocol_version
    )
    from a2a.client import A2AClient
    from a2a.client.errors import A2AClientTimeoutError
    from a2a.client.middleware import ClientCallInterceptor
    from a2a.types import (
        Message,
        MessageSendParams,
        Part,
        Role,
        SendStreamingMessageRequest,
        TextPart,
    )

    trace = WireTrace()
    recorder = _TraceInterceptor(trace)

    class SDKTraceInterceptor(ClientCallInterceptor):
        async def intercept(
            self,
            method_name: str,
            request_payload: dict[str, Any],
            http_kwargs: dict[str, Any],
            agent_card: Any,
            context: Any,
        ) -> tuple[dict[str, Any], dict[str, Any]]:
            return await recorder.intercept(
                method_name, request_payload, http_kwargs, agent_card, context
            )

    interceptor = SDKTraceInterceptor()
    message_id = str(uuid.uuid4())
    request = SendStreamingMessageRequest(
        id=str(uuid.uuid4()),
        params=MessageSendParams(
            message=Message(
                role=Role.user,
                message_id=message_id,
                parts=[Part(root=TextPart(text=prompt))],
            )
        ),
    )
    client = A2AClient(
        http_client, agent_card=card.card, url=card.endpoint, interceptors=[interceptor]
    )
    transitions: list[StatusTransition] = []
    task_ids: list[str] = []
    response_text = ""
    outcome = "incomplete"
    terminal = False
    failure: str | None = None
    cancelled: asyncio.CancelledError | None = None
    remove_hook = _install_response_recorder(http_client, trace)
    stream = client.send_message_streaming(
        request,
        http_kwargs={
            "timeout": timeout,
            "headers": {"A2A-Version": wire_version, "Accept": "text/event-stream"},
        },
    )
    try:
        async with asyncio.timeout_at(deadline):
            async for event in stream:
                # A2AClient reconstructs yielded envelope IDs. WireTrace validates
                # the original HTTP envelopes instead of trusting those SDK IDs.
                result = getattr(getattr(event, "root", None), "result", None)
                kind = str(getattr(result, "kind", ""))
                task_id = _event_task_id(result)
                state = _event_state(result)
                final = getattr(result, "final", None)
                if len(transitions) >= MAX_EVENTS:
                    raise DispatchError("bounded event inventory exceeded")
                if kind not in {"task", "status-update", "artifact-update"}:
                    raise DispatchError("stream result is not a supported task event")
                if not isinstance(task_id, str) or not task_id.strip():
                    raise DispatchError("task-bearing event lacks a nonempty task ID")
                if SENSITIVE.search(task_id):
                    raise DispatchError("task identifier contains sensitive diagnostic content")
                if task_ids and task_id != task_ids[0]:
                    raise DispatchError("stream contains mixed task IDs")
                if terminal:
                    raise DispatchError("task-bearing event followed terminal completion")
                if kind != "artifact-update" and state not in KNOWN_STATES:
                    raise DispatchError("task status is missing or unsupported")
                if observe_event is not None:
                    observe_event(result)
                task_ids.append(task_id)
                transitions.append(
                    StatusTransition(
                        kind, task_id, state, final if isinstance(final, bool) else None
                    )
                )
                response_text = (response_text + " " + _safe_text(_event_text(result)))[
                    -MAX_RESPONSE_TEXT:
                ]
                if state in FAILED_STATES:
                    outcome = state
                    raise DispatchError(f"A2A execution {state}", outcome=state)
                if state == "completed":
                    if kind == "status-update" and final is not True:
                        outcome = "incomplete"
                        raise DispatchError(
                            "completed status lacks final stream closure", outcome="incomplete"
                        )
                    terminal = True
                    outcome = "completed"
                elif kind == "status-update" and final is True:
                    outcome = "incomplete"
                    raise DispatchError(
                        "stream closed without completed execution", outcome="incomplete"
                    )
    except asyncio.CancelledError as exc:
        outcome = "canceled"
        cancelled = exc
    except TimeoutError:
        outcome = "timed_out"
        failure = "overall A2A operation deadline exceeded"
    except DispatchError as exc:
        failure = str(exc)
        outcome = exc.outcome
    except Exception as exc:
        # Preserve the SDK's dedicated inactivity-timeout classification.
        status_code = getattr(exc, "status_code", None)
        outcome = (
            "timed_out"
            if isinstance(exc, A2AClientTimeoutError) or status_code == 408
            else ("transport_failed" if isinstance(status_code, int) else "invalid")
        )
        failure = f"A2A SDK dispatch failed: {type(exc).__name__}: {_safe_text(str(exc))}"
    finally:
        remove_hook()
        try:
            await stream.aclose()
        finally:
            trace.finalize_response()

    wire_valid = bool(trace.response_ids) and not trace.wire_error and not trace.capture_truncated
    if failure is None and cancelled is None:
        if not wire_valid or trace.response_error_codes:
            outcome = "invalid"
            failure = "A2A wire response correlation or protocol validation failed"
        elif not terminal or outcome != "completed":
            outcome = "incomplete"
            failure = "A2A stream ended without completed execution"
    observation = DispatchObservation(
        request_id=trace.request_id,
        message_id=trace.message_id or message_id,
        task_id=task_ids[0] if task_ids else None,
        status_transitions=tuple(transitions),
        response_text=_safe_text(response_text.strip()),
        final_state=next((item.state for item in reversed(transitions) if item.state), None),
        response_ids=tuple(trace.response_ids),
        response_error_codes=tuple(trace.response_error_codes),
        response_event_count=trace.response_event_count,
        http_status=trace.http_status,
        outcome=outcome,
        dispatch_accepted=trace.dispatch_accepted,
        wire_valid=wire_valid,
    )
    if cancelled is not None:
        cancelled.__dict__["observation"] = observation
        raise cancelled
    if failure is not None:
        raise DispatchError(failure, observation=observation, outcome=outcome)
    return observation


def _sanitize_error(exc: BaseException) -> dict[str, str]:
    return {"type": type(exc).__name__, "message": _safe_text(str(exc))[:400]}


def _apply_observation(report: dict[str, Any], observation: DispatchObservation) -> None:
    report["request"].update(
        {
            "jsonrpc": "2.0",
            "method": "message/stream",
            "requestId": observation.request_id,
            "messageId": observation.message_id,
        }
    )
    report["response"].update(
        {
            "httpStatus": observation.http_status,
            "responseEventCount": observation.response_event_count,
            "errorCodes": list(observation.response_error_codes),
            "statusTransitions": [item.__dict__ for item in observation.status_transitions],
            "finalState": observation.final_state,
            "text": observation.response_text,
        }
    )
    report["correlation"] = {
        "taskId": observation.task_id,
        "taskIdsAcrossTransitions": list(
            dict.fromkeys(item.task_id for item in observation.status_transitions if item.task_id)
        ),
        "sameTaskIdAcrossTransitions": bool(observation.status_transitions)
        and all(item.task_id == observation.task_id for item in observation.status_transitions),
        "responseIds": list(observation.response_ids),
        "responseIdsMatchRequest": bool(observation.response_ids)
        and all(item == observation.request_id for item in observation.response_ids),
        "wireValid": observation.wire_valid,
    }
    report["outcomes"] = {
        "transportEstablished": observation.http_status is not None,
        "dispatchAccepted": observation.dispatch_accepted,
        "execution": observation.outcome,
        "executionCompleted": observation.outcome == "completed" and observation.wire_valid,
    }
    report["claims"]["a2aCommunication"] = observation.dispatch_accepted and observation.wire_valid


def _report_base(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "schemaVersion": "1.0",
        "schemaName": "kagent-sdk-interoperability",
        "observedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "client": {
            "sdk": "a2a-sdk",
            "sdkVersion": "0.3.26",
            "python": sys.version.split()[0],
        },
        "target": {
            "namespace": args.namespace,
            "agent": args.agent,
            "controller": args.controller,
            "cardEndpoint": build_card_url(args.controller, args.namespace, args.agent),
            "a2aEndpoint": build_a2a_url(args.controller, args.namespace, args.agent),
        },
        "discovery": {},
        "compatibility": {
            "requestedProtocolVersion": args.protocol_version,
            "validatedBeforeDispatch": False,
        },
        "request": {
            "promptSha256": sha256(args.prompt.encode("utf-8")).hexdigest(),
            "readOnlyIntent": True,
        },
        "response": {"statusTransitions": [], "errors": []},
        "correlation": {},
        "outcomes": {
            "transportEstablished": False,
            "dispatchAccepted": False,
            "execution": "not_attempted",
            "executionCompleted": False,
        },
        "nonClaims": ["L6", "I3", "I4", "L7"],
        "claims": {
            "agentCardDiscovery": False,
            "a2aCommunication": False,
            "mcpToolExecution": False,
            "mcpToolExecutionEvidence": "not collected by this SDK client",
        },
        "decision": {"passed": False, "exitCode": 1, "reason": "not attempted"},
    }


async def execute(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    report = _report_base(args)
    try:
        controller = validate_controller_url(args.controller)
        args.controller = controller
        requested_family = _protocol_family(args.protocol_version)
        if not math.isfinite(args.timeout) or args.timeout <= 0:
            raise UsageError("timeout must be finite and positive")
        for name in (args.namespace, args.agent):
            if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?", name):
                raise UsageError("namespace and agent must be valid resource names")
        deadline = asyncio.get_running_loop().time() + args.timeout
        import httpx

        async with httpx.AsyncClient(
            timeout=args.timeout,
            headers={"A2A-Version": requested_family},
            trust_env=False,
        ) as http_client:
            async with asyncio.timeout_at(deadline):
                card = await discover_agent_card(
                    http_client,
                    controller=controller,
                    namespace=args.namespace,
                    agent=args.agent,
                    fallback_protocol_version=args.card_protocol_fallback,
                )
            report["discovery"] = {
                "succeeded": True,
                "agentName": card.agent_name,
                "accepted": card.accepted,
                "deploymentReady": card.deployment_ready,
                "model": card.model,
                "modelProvider": card.model_provider,
                "skillIds": list(card.skill_ids),
                "protocolVersion": card.protocol_version,
                "protocolVersionSource": card.protocol_version_source,
            }
            report["claims"]["agentCardDiscovery"] = True
            wire_version = validate_protocol_compatibility(
                card.protocol_version, args.protocol_version
            )
            report["compatibility"].update(
                {
                    "advertisedProtocolVersion": card.protocol_version,
                    "wireProtocolVersion": wire_version,
                    "protocolVersionSource": card.protocol_version_source,
                    "compatible": True,
                    "validatedBeforeDispatch": True,
                }
            )
            observation = await dispatch_read_only_task(
                http_client,
                card,
                prompt=args.prompt,
                requested_protocol_version=args.protocol_version,
                timeout=max(0.0, deadline - asyncio.get_running_loop().time()),
            )
            _apply_observation(report, observation)
            report["decision"] = {
                "passed": True,
                "exitCode": 0,
                "reason": "Agent Card, wire correlation, and completed SDK execution validated",
            }
            return _safe_json(report), 0
    except ProtocolCompatibilityError as exc:
        report["compatibility"].update({"compatible": False, "validatedBeforeDispatch": True})
        report["response"]["errors"].append(_sanitize_error(exc))
        report["outcomes"]["execution"] = "invalid"
        report["decision"] = {
            "passed": False,
            "exitCode": 1,
            "reason": f"protocol compatibility gate failed: {_safe_text(str(exc))}",
        }
        return _safe_json(report), 1
    except (UsageError, ValueError) as exc:
        report["response"]["errors"].append(_sanitize_error(exc))
        report["outcomes"]["execution"] = "invalid"
        report["decision"] = {"passed": False, "exitCode": 2, "reason": _safe_text(str(exc))}
        return _safe_json(report), 2
    except TimeoutError as exc:
        report["response"]["errors"].append(_sanitize_error(exc))
        report["outcomes"]["execution"] = "timed_out"
        report["decision"] = {
            "passed": False,
            "exitCode": 3,
            "reason": "overall operation deadline exceeded during discovery",
        }
        return _safe_json(report), 3
    except TransportError as exc:
        report["response"]["errors"].append(_sanitize_error(exc))
        report["outcomes"]["execution"] = "transport_failed"
        report["decision"] = {"passed": False, "exitCode": 3, "reason": _safe_text(str(exc))}
        return _safe_json(report), 3
    except (CardError, DispatchError) as exc:
        if isinstance(exc, DispatchError) and exc.observation is not None:
            _apply_observation(report, exc.observation)
        else:
            report["outcomes"]["execution"] = "invalid"
        report["response"]["errors"].append(_sanitize_error(exc))
        report["decision"] = {"passed": False, "exitCode": 1, "reason": _safe_text(str(exc))}
        return _safe_json(report), 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--controller", default=DEFAULT_CONTROLLER)
    parser.add_argument("--namespace", default=DEFAULT_NAMESPACE)
    parser.add_argument("--agent", default=DEFAULT_AGENT)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--protocol-version", default=DEFAULT_PROTOCOL_VERSION)
    parser.add_argument(
        "--card-protocol-fallback",
        default=DEFAULT_PROTOCOL_VERSION,
        help=(
            "Compatibility profile used only when kagent's details response omits protocolVersion."
        ),
    )
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--output", choices=("human", "json"), default="human")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report, exit_code = asyncio.run(execute(args))
    except Exception as exc:  # keep the CLI machine-readable on unexpected SDK failures
        report = _report_base(args)
        report["response"]["errors"].append(_sanitize_error(exc))
        report["decision"] = {"passed": False, "exitCode": 1, "reason": _safe_text(str(exc))}
        report["outcomes"]["execution"] = "invalid"
        exit_code = 1
    report = _safe_json(report)
    if args.output == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"A2A SDK interoperability: {report['decision']['reason']}")
        if report.get("correlation", {}).get("taskId"):
            print(f"Task: {report['correlation']['taskId']}")
        for transition in report["response"].get("statusTransitions", []):
            print(f"  {transition['kind']}: {transition.get('state')}")
        print("MCP tool execution proven: False")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
