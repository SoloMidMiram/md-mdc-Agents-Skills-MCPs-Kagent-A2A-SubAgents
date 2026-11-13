"""Deterministic tests for the native kagent controller MCP federation helper."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "scripts" / "kagent"
sys.path.insert(0, str(SCRIPT_DIR))

import controller_mcp_smoke as controller  # noqa: E402
import mcp_session_smoke as mcp  # noqa: E402

RAW_CONTEXT_ID = "ctx-secret-must-not-appear"
IDE_SAFE_INVENTORY = ROOT / "config" / "kagent" / "ide-safe-agent-inventory.txt"


class FakeTransport:
    def __init__(self, handler) -> None:
        self.handler = handler
        self.requests: list[dict[str, Any]] = []

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: bytes | None = None,
        timeout: float,
    ) -> mcp.HttpResponse:
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "body": body,
                "timeout": timeout,
            }
        )
        return self.handler(method, url, headers, body, timeout)


def _response(body: dict[str, Any], *, headers: dict[str, str] | None = None) -> mcp.HttpResponse:
    return mcp.HttpResponse(
        status=200,
        headers={"Content-Type": "application/json", **(headers or {})},
        body=json.dumps(body).encode(),
        content_type="application/json",
    )


def _tools(*, privileged: bool = False) -> list[dict[str, Any]]:
    tools = [
        {
            "name": "list_agents",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "invoke_agent",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent": {"type": "string"},
                    "task": {"type": "string"},
                    "context_id": {"type": "string"},
                },
                "required": ["agent", "task"],
                "additionalProperties": False,
            },
        },
    ]
    if privileged:
        tools.append({"name": "delete_agent", "inputSchema": {"type": "object"}})
    return tools


def _agents(
    *,
    include_target: bool = True,
    extras: list[str] | None = None,
    include_observability: bool = True,
    duplicates: list[str] | None = None,
) -> list[dict[str, str]]:
    agents: list[dict[str, str]] = []
    if include_observability:
        agents.append({"ref": "kagent/observability-agent"})
    if include_target:
        agents.append({"ref": "kagent/k8s-a2a-agent"})
    for ref in extras or []:
        agents.append({"ref": ref})
    for ref in duplicates or []:
        agents.append({"ref": ref})
    return agents


def _handler(
    *,
    tools: list[dict[str, Any]] | None = None,
    include_target: bool = True,
    agent_text: str = controller.DEFAULT_EXPECTED_RESPONSE,
    continuation_text: str = controller.DEFAULT_CONTINUATION_EXPECTED_RESPONSE,
    malformed_tools: bool = False,
    timeout_on_invoke: bool = False,
    context_id: Any = RAW_CONTEXT_ID,
    omit_context_id: bool = False,
    reject_continuation: bool = False,
    changed_context_on_continuation: bool = False,
    extras: list[str] | None = None,
    include_observability: bool = True,
    duplicates: list[str] | None = None,
    leak_context_into_continuation: bool = False,
    postflight_extras: list[str] | None = None,
    postflight_include_observability: bool | None = None,
):
    invoke_count = {"n": 0}
    list_count = {"n": 0}

    def handler(method, _url, headers, body, _timeout):
        if method == "DELETE":
            assert headers["Mcp-Session-Id"] == "session-secret"
            return mcp.HttpResponse(status=405, headers={}, body=b"", content_type="")
        payload = json.loads((body or b"{}").decode())
        name = payload.get("method")
        if name == "initialize":
            return _response(
                {
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {"name": "kagent-agents", "version": "0.9.11"},
                    },
                },
                headers={"Mcp-Session-Id": "session-secret"},
            )
        assert headers["Mcp-Session-Id"] == "session-secret"
        if name == "notifications/initialized":
            return mcp.HttpResponse(status=202, headers={}, body=b"", content_type="")
        if name == "tools/list":
            result: dict[str, Any] = (
                {"tools": "bad"} if malformed_tools else {"tools": tools or _tools()}
            )
            return _response({"jsonrpc": "2.0", "id": payload["id"], "result": result})
        if name == "tools/call":
            tool_name = payload["params"]["name"]
            if tool_name == "list_agents":
                list_count["n"] += 1
                call_extras = extras
                call_observability = include_observability
                if list_count["n"] > 1 and (
                    postflight_extras is not None or postflight_include_observability is not None
                ):
                    if postflight_extras is not None:
                        call_extras = postflight_extras
                    if postflight_include_observability is not None:
                        call_observability = postflight_include_observability
                return _response(
                    {
                        "jsonrpc": "2.0",
                        "id": payload["id"],
                        "result": {
                            "structuredContent": {
                                "agents": _agents(
                                    include_target=include_target,
                                    extras=call_extras,
                                    include_observability=call_observability,
                                    duplicates=duplicates,
                                )
                            }
                        },
                    }
                )
            assert tool_name == "invoke_agent"
            if timeout_on_invoke:
                raise mcp.TransportError("timeout: simulated")
            invoke_count["n"] += 1
            arguments = payload["params"]["arguments"]
            if invoke_count["n"] == 1:
                assert arguments == {
                    "agent": "kagent/k8s-a2a-agent",
                    "task": controller.DEFAULT_TASK,
                }
                structured: dict[str, Any] = {
                    "agent": "kagent/k8s-a2a-agent",
                    "text": agent_text,
                }
                if not omit_context_id:
                    structured["context_id"] = context_id
                return _response(
                    {
                        "jsonrpc": "2.0",
                        "id": payload["id"],
                        "result": {"structuredContent": structured},
                    }
                )
            assert invoke_count["n"] == 2
            assert arguments.get("agent") == "kagent/k8s-a2a-agent"
            assert arguments.get("task") == controller.DEFAULT_CONTINUATION_TASK
            assert "context_id" in arguments
            if reject_continuation:
                return _response(
                    {
                        "jsonrpc": "2.0",
                        "id": payload["id"],
                        "result": {"isError": True, "content": [{"type": "text", "text": "no"}]},
                    }
                )
            if changed_context_on_continuation:
                continued_context = "different-context-id"
            else:
                continued_context = arguments["context_id"]
            follow_text = continuation_text
            if leak_context_into_continuation and isinstance(continued_context, str):
                # Store leaked id in a sanitized result leaf so the hybrid detector fires.
                follow_text = f"{continuation_text} ctx={continued_context}"
            return _response(
                {
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {
                        "structuredContent": {
                            "agent": "kagent/k8s-a2a-agent",
                            "context_id": continued_context,
                            "text": follow_text,
                        }
                    },
                }
            )
        raise AssertionError(f"unexpected MCP method {name!r}")

    return handler


def _run(transport: FakeTransport, **kwargs: Any) -> controller.ControllerMcpResult:
    return controller.ControllerMcpClient(controller.ControllerMcpConfig(**kwargs), transport).run()


def _exact_inventory_config(**kwargs: Any) -> dict[str, Any]:
    relative, refs, digest = controller.load_expected_inventory(str(IDE_SAFE_INVENTORY))
    base = {
        "strict_agent_inventory": True,
        "expected_inventory_path": str(IDE_SAFE_INVENTORY),
        "expected_inventory_relative_path": relative,
        "expected_inventory_refs": refs,
        "expected_inventory_canonical_sha256": digest,
    }
    base.update(kwargs)
    return base


def test_default_task_requests_exact_acceptance_token() -> None:
    assert controller.DEFAULT_EXPECTED_RESPONSE == controller.ACCEPTANCE_TOKEN
    assert f"Reply exactly: {controller.ACCEPTANCE_TOKEN}" in controller.DEFAULT_TASK
    assert controller.DEFAULT_TASK.startswith("Reply exactly:")
    # Trailing period after the token would make the task ask for a different string.
    assert f"Reply exactly: {controller.ACCEPTANCE_TOKEN}." not in controller.DEFAULT_TASK


def test_default_continuation_task_requests_exact_continuation_token() -> None:
    assert controller.DEFAULT_CONTINUATION_EXPECTED_RESPONSE == controller.CONTINUATION_TOKEN
    assert f"Reply exactly: {controller.CONTINUATION_TOKEN}" in controller.DEFAULT_CONTINUATION_TASK
    assert controller.DEFAULT_CONTINUATION_TASK.startswith("Reply exactly:")
    assert (
        f"Reply exactly: {controller.CONTINUATION_TOKEN}."
        not in controller.DEFAULT_CONTINUATION_TASK
    )


def test_success_requires_exact_tools_target_response_and_mcp_session_reuse() -> None:
    transport = FakeTransport(_handler())
    result = _run(transport)

    assert result.exit_code == mcp.ExitCode.SUCCESS
    assert result.session_id_present
    assert result.controller_tools == ["invoke_agent", "list_agents"]
    assert result.target_agent_found
    assert result.invoke_agent_succeeded
    assert result.agent_context_id == "present"
    assert result.agent_context_continuation_succeeded
    assert result.same_mcp_session_reuse_http_status == 200
    assert result.mcp_session_reuse_target_present
    assert result.cleanup == "method-not-allowed"
    assert result.strict_preflight_qualified is True
    assert result.observation_only is False
    rendered = json.dumps(result.to_sanitized_dict())
    assert "session-secret" not in rendered
    assert RAW_CONTEXT_ID not in rendered
    assert "sameSessionContinuationHttpStatus" not in rendered
    assert "continuationTargetPresent" not in rendered
    assert "sameMcpSessionReuseHttpStatus" in rendered
    assert "mcpSessionReuseTargetPresent" in rendered
    assert result.to_sanitized_dict()["strictPreflightQualified"] is True
    assert result.to_sanitized_dict()["observationOnly"] is False


def test_short_context_id_does_not_false_fail_on_sanitized_output() -> None:
    for short_id in ("a", "1"):
        result = _run(FakeTransport(_handler(context_id=short_id)))
        assert result.exit_code == mcp.ExitCode.SUCCESS
        assert result.agent_context_id == "present"
        assert result.agent_context_continuation_succeeded


def test_exact_leaf_short_context_id_leak_fails() -> None:
    result = _run(FakeTransport(_handler(context_id="a")))
    assert result.exit_code == mcp.ExitCode.SUCCESS
    # Inject exact leaf after a successful capture path via detector unit helper.
    payload = result.to_sanitized_dict()
    payload["agentResponse"] = "a"
    assert controller.sanitized_output_leaks_context_id(payload, "a")


def test_embedded_length_boundary_for_leak_detector() -> None:
    short7 = "abcdefg"
    long8 = "abcdefgh"
    assert not controller.sanitized_output_leaks_context_id(
        {"error": f"provider failure for context {short7}"}, short7
    )
    assert controller.sanitized_output_leaks_context_id(
        {"error": f"provider failure for context {long8}"}, long8
    )
    assert controller.sanitized_output_leaks_context_id({"nested": {"x": long8}}, long8)
    assert controller.sanitized_output_leaks_context_id({"x": short7}, short7)


def test_long_context_embedded_in_continuation_response_fails_closed() -> None:
    result = _run(FakeTransport(_handler(leak_context_into_continuation=True)))
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert "leaked agent context identifier" in (result.error or "")
    assert RAW_CONTEXT_ID not in (result.error or "")
    assert RAW_CONTEXT_ID not in json.dumps(result.to_sanitized_dict())
    assert not result.agent_context_continuation_succeeded


def test_whitespace_only_context_id_fails_closed() -> None:
    result = _run(FakeTransport(_handler(context_id="   ")))
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert "non-empty string" in (result.error or "")


def test_controller_unavailable_is_transport_failure() -> None:
    def unavailable(*_args, **_kwargs):
        raise mcp.TransportError("connection refused")

    result = _run(FakeTransport(unavailable))
    assert result.exit_code == mcp.ExitCode.TRANSPORT
    assert "connection refused" in (result.error or "")


def test_wrong_port_is_transport_failure() -> None:
    def unavailable(_method, url, *_args):
        assert url == "http://127.0.0.1:8084/mcp"
        raise mcp.TransportError("connection refused")

    result = _run(FakeTransport(unavailable), url="http://127.0.0.1:8084/mcp")
    assert result.exit_code == mcp.ExitCode.TRANSPORT


def test_malformed_tools_response_fails_closed() -> None:
    result = _run(FakeTransport(_handler(malformed_tools=True)))
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert "result.tools" in (result.error or "")


def test_missing_target_agent_fails_closed() -> None:
    result = _run(FakeTransport(_handler(include_target=False)))
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert "k8s-a2a-agent" in (result.error or "")


def test_invocation_timeout_is_transport_failure() -> None:
    result = _run(FakeTransport(_handler(timeout_on_invoke=True)))
    assert result.exit_code == mcp.ExitCode.TRANSPORT
    assert "timeout" in (result.error or "")


def test_unexpected_privileged_tool_fails_closed() -> None:
    result = _run(FakeTransport(_handler(tools=_tools(privileged=True))))
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert "unexpected privileged" in (result.error or "")


def test_agent_response_must_match_bounded_no_tool_contract() -> None:
    result = _run(FakeTransport(_handler(agent_text="provider unavailable")))
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert not result.invoke_agent_succeeded
    assert result.agent_response == "provider unavailable"
    assert "bounded no-tool" in (result.error or "")
    assert not result.agent_context_continuation_succeeded


def test_controller_url_rejects_userinfo_and_non_mcp_path() -> None:
    userinfo = _run(FakeTransport(_handler()), url="http://user:pass@127.0.0.1:8083/mcp")
    wrong_path = _run(FakeTransport(_handler()), url="http://127.0.0.1:8083/api")
    assert userinfo.exit_code == mcp.ExitCode.USAGE
    assert wrong_path.exit_code == mcp.ExitCode.USAGE
    assert "controller URL" in (userinfo.error or "")


def test_missing_context_id_fails_closed() -> None:
    result = _run(FakeTransport(_handler(omit_context_id=True)))
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert "missing context_id" in (result.error or "")
    assert result.agent_context_id == "missing"
    assert not result.agent_context_continuation_succeeded
    assert RAW_CONTEXT_ID not in (result.error or "")
    assert RAW_CONTEXT_ID not in json.dumps(result.to_sanitized_dict())


def test_empty_context_id_fails_closed() -> None:
    result = _run(FakeTransport(_handler(context_id="")))
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert "non-empty string" in (result.error or "")
    assert not result.agent_context_continuation_succeeded


def test_non_string_context_id_fails_closed() -> None:
    result = _run(FakeTransport(_handler(context_id=123)))
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert "non-empty string" in (result.error or "")
    assert not result.agent_context_continuation_succeeded


def test_second_invocation_rejects_context_fails_closed() -> None:
    result = _run(FakeTransport(_handler(reject_continuation=True)))
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert result.invoke_agent_succeeded
    assert result.agent_context_id == "present"
    assert not result.agent_context_continuation_succeeded
    assert "error result" in (result.error or "")
    rendered = json.dumps(result.to_sanitized_dict())
    assert RAW_CONTEXT_ID not in rendered
    assert RAW_CONTEXT_ID not in (result.error or "")
    assert RAW_CONTEXT_ID not in json.dumps(result.to_sanitized_dict())


def test_second_response_differs_from_expected_fails_closed() -> None:
    result = _run(FakeTransport(_handler(continuation_text="wrong follow-up")))
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert result.continuation_agent_response == "wrong follow-up"
    assert not result.agent_context_continuation_succeeded
    assert "context continuation" in (result.error or "")


def test_changed_context_id_on_continuation_fails_closed() -> None:
    result = _run(FakeTransport(_handler(changed_context_on_continuation=True)))
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert not result.agent_context_continuation_succeeded
    assert "changed context_id" in (result.error or "")
    assert "different-context-id" not in (result.error or "")
    assert RAW_CONTEXT_ID not in (result.error or "")
    assert RAW_CONTEXT_ID not in json.dumps(result.to_sanitized_dict())


def test_raw_context_id_not_in_serialized_output_or_error_text() -> None:
    result = _run(FakeTransport(_handler()))
    assert result.exit_code == mcp.ExitCode.SUCCESS
    rendered = json.dumps(result.to_sanitized_dict(), sort_keys=True)
    assert RAW_CONTEXT_ID not in rendered
    assert result.error is None


def test_mcp_session_reuse_and_agent_context_continuation_are_separate_fields() -> None:
    result = _run(FakeTransport(_handler()))
    payload = result.to_sanitized_dict()
    assert payload["agentContextContinuationSucceeded"] is True
    assert payload["mcpSessionReuseTargetPresent"] is True
    assert payload["sameMcpSessionReuseHttpStatus"] == 200


def test_strict_inventory_rejects_unexpected_agents() -> None:
    result = _run(
        FakeTransport(_handler()),
        strict_agent_inventory=True,
        approved_agents=("kagent/k8s-a2a-agent",),
    )
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert result.unexpected_agents == ["kagent/observability-agent"]
    assert "unexpected agents" in (result.error or "")


def test_strict_inventory_accepts_approved_multi_agent_set() -> None:
    result = _run(
        FakeTransport(_handler()),
        strict_agent_inventory=True,
        approved_agents=("kagent/k8s-a2a-agent", "kagent/observability-agent"),
    )
    assert result.exit_code == mcp.ExitCode.SUCCESS
    assert result.inventory_policy == "strict-approved"
    assert result.discovered_agent_count == 2
    assert result.unexpected_agents == []


def test_strict_inventory_missing_target_fails_closed() -> None:
    result = _run(
        FakeTransport(_handler(include_target=False)),
        strict_agent_inventory=True,
        approved_agents=("kagent/k8s-a2a-agent", "kagent/observability-agent"),
    )
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert "k8s-a2a-agent" in (result.error or "")


def test_strict_inventory_requires_approved_agents() -> None:
    result = _run(FakeTransport(_handler()), strict_agent_inventory=True, approved_agents=())
    assert result.exit_code == mcp.ExitCode.USAGE
    assert "approved-agent" in (result.error or "")


def test_parse_approved_agents_rejects_duplicates_and_malformed() -> None:
    try:
        controller.parse_approved_agents(["kagent/k8s-a2a-agent", "kagent/k8s-a2a-agent"])
        raise AssertionError("expected duplicate rejection")
    except controller.UsageError as exc:
        assert "duplicate" in str(exc)
    try:
        controller.parse_approved_agents(["not-a-valid-ref"])
        raise AssertionError("expected malformed rejection")
    except controller.UsageError as exc:
        assert "invalid agent reference" in str(exc)
    parsed = controller.parse_approved_agents(["kagent/k8s-a2a-agent,kagent/observability-agent"])
    assert parsed == ("kagent/k8s-a2a-agent", "kagent/observability-agent")


def test_default_inventory_ignores_extra_discovered_agents() -> None:
    result = _run(FakeTransport(_handler(extras=["kagent/helm-agent"])))
    assert result.exit_code == mcp.ExitCode.SUCCESS
    assert result.inventory_policy == "target-presence"
    assert result.discovered_agent_count == 3


def test_exact_inventory_singleton_passes() -> None:
    result = _run(
        FakeTransport(_handler(include_observability=False)),
        **_exact_inventory_config(),
    )
    assert result.exit_code == mcp.ExitCode.SUCCESS
    assert result.inventory_policy == "exact-file"
    assert result.inventory_matched is True
    assert result.discovered_agent_count == 1
    assert result.unexpected_agents == []
    assert result.missing_expected_agents == []
    assert result.duplicate_discovered_agents == []
    payload = result.to_sanitized_dict()
    assert payload["expectedInventoryPath"] == "config/kagent/ide-safe-agent-inventory.txt"
    assert payload["expectedInventoryCanonicalSha256"] == controller.canonical_inventory_digest(
        ["kagent/k8s-a2a-agent"]
    )


def test_exact_inventory_rejects_unexpected_agent() -> None:
    result = _run(FakeTransport(_handler()), **_exact_inventory_config())
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert result.unexpected_agents == ["kagent/observability-agent"]
    assert "exact inventory" in (result.error or "")


def test_exact_inventory_rejects_missing_expected() -> None:
    result = _run(
        FakeTransport(_handler(include_target=False, include_observability=False)),
        **_exact_inventory_config(),
    )
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert "k8s-a2a-agent" in (result.error or "")


def test_exact_inventory_rejects_duplicate_discovered_refs() -> None:
    result = _run(
        FakeTransport(_handler(include_observability=False, duplicates=["kagent/k8s-a2a-agent"])),
        **_exact_inventory_config(),
    )
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert result.duplicate_discovered_agents == ["kagent/k8s-a2a-agent"]
    assert "duplicate agent references" in (result.error or "")


def test_exact_inventory_mutually_exclusive_with_approved_agent() -> None:
    result = _run(
        FakeTransport(_handler(include_observability=False)),
        approved_agents=("kagent/k8s-a2a-agent",),
        **_exact_inventory_config(),
    )
    assert result.exit_code == mcp.ExitCode.USAGE
    assert "cannot be combined" in (result.error or "")


def test_load_expected_inventory_rejects_path_outside_config_kagent(tmp_path: Path) -> None:
    outside = tmp_path / "agents.txt"
    outside.write_text("kagent/k8s-a2a-agent\n", encoding="utf-8")
    try:
        controller.load_expected_inventory(str(outside))
        raise AssertionError("expected path rejection")
    except controller.UsageError as exc:
        assert "config/kagent" in str(exc)


def test_load_expected_inventory_rejects_dotdot_segments() -> None:
    try:
        controller.load_expected_inventory("config/kagent/../kagent/ide-safe-agent-inventory.txt")
        raise AssertionError("expected .. rejection")
    except controller.UsageError as exc:
        assert ".." in str(exc)


def test_canonical_digest_independent_of_ordering_and_comments(tmp_path: Path) -> None:
    target = ROOT / "config" / "kagent" / "_tmp_digest_test.txt"
    try:
        target.write_text(
            "# comment\n\nkagent/k8s-a2a-agent\n",
            encoding="utf-8",
            newline="\n",
        )
        _, refs_a, digest_a = controller.load_expected_inventory(str(target))
        target.write_text(
            "kagent/k8s-a2a-agent\r\n# trailing\r\n",
            encoding="utf-8",
            newline="",
        )
        _, refs_b, digest_b = controller.load_expected_inventory(str(target))
        assert refs_a == refs_b == ("kagent/k8s-a2a-agent",)
        assert digest_a == digest_b
    finally:
        if target.exists():
            target.unlink()


def test_extract_agent_context_id_fail_closed_cases() -> None:
    try:
        controller.extract_agent_context_id({"agent": "x"})
        raise AssertionError("expected missing context_id")
    except mcp.ProtocolError as exc:
        assert "missing context_id" in str(exc)
    try:
        controller.extract_agent_context_id({"context_id": ""})
        raise AssertionError("expected empty context_id")
    except mcp.ProtocolError as exc:
        assert "non-empty string" in str(exc)
    try:
        controller.extract_agent_context_id({"context_id": "  "})
        raise AssertionError("expected whitespace context_id")
    except mcp.ProtocolError as exc:
        assert "non-empty string" in str(exc)
    assert controller.extract_agent_context_id({"context_id": "ok"}) == "ok"


def _observe_config(**kwargs: Any) -> dict[str, Any]:
    return _exact_inventory_config(observe_only=True, **kwargs)


def test_observe_only_requires_expected_inventory() -> None:
    result = _run(FakeTransport(_handler(include_observability=False)), observe_only=True)
    assert result.exit_code == mcp.ExitCode.USAGE
    assert "--observe-only requires --expected-inventory" in (result.error or "")
    assert result.observation_only is True
    assert result.strict_preflight_qualified is False


def test_observe_only_keeps_gates_but_skips_exact_text() -> None:
    transport = FakeTransport(
        _handler(
            include_observability=False,
            agent_text="kagent native MCP acceptance.",
        )
    )
    result = _run(transport, **_observe_config())
    assert result.exit_code == mcp.ExitCode.SUCCESS
    assert result.observation_only is True
    assert result.strict_preflight_qualified is False
    assert result.invoke_agent_succeeded is True
    assert result.agent_context_id == "present"
    assert result.agent_context_continuation_succeeded is False
    assert result.continuation_http_status is None
    assert result.agent_response == "kagent native MCP acceptance."
    assert result.response_truncated is False
    assert RAW_CONTEXT_ID not in json.dumps(result.to_sanitized_dict())


def test_observe_only_rejects_unexpected_tools() -> None:
    result = _run(
        FakeTransport(_handler(tools=_tools(privileged=True), include_observability=False)),
        **_observe_config(),
    )
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert "unexpected privileged" in (result.error or "")
    assert result.strict_preflight_qualified is False


def test_observe_only_rejects_inventory_mismatch() -> None:
    result = _run(FakeTransport(_handler()), **_observe_config())
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert result.unexpected_agents == ["kagent/observability-agent"]
    assert "exact inventory" in (result.error or "")
    assert result.strict_preflight_qualified is False


def test_observe_only_rejects_missing_context_id() -> None:
    result = _run(
        FakeTransport(_handler(include_observability=False, omit_context_id=True)),
        **_observe_config(),
    )
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert "missing context_id" in (result.error or "")
    assert result.agent_context_id == "missing"
    assert result.strict_preflight_qualified is False


def test_observe_only_rejects_empty_response_text() -> None:
    result = _run(
        FakeTransport(_handler(include_observability=False, agent_text="")),
        **_observe_config(),
    )
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert "empty response text" in (result.error or "")
    assert not result.invoke_agent_succeeded
    assert result.strict_preflight_qualified is False


def test_observe_only_rejects_overlong_response() -> None:
    overlong = "x" * (controller.MAX_OBSERVATION_RESPONSE_CHARS + 1)
    result = _run(
        FakeTransport(_handler(include_observability=False, agent_text=overlong)),
        **_observe_config(),
    )
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert "exceeds bounded length" in (result.error or "")
    assert result.response_truncated is True
    assert len(result.agent_response) <= controller.MAX_OBSERVATION_RESPONSE_CHARS
    assert overlong not in result.agent_response
    assert overlong not in json.dumps(result.to_sanitized_dict())
    assert result.strict_preflight_qualified is False


def test_observe_only_makes_exactly_one_invoke_call() -> None:
    transport = FakeTransport(
        _handler(
            include_observability=False,
            agent_text="kagent native MCP acceptance.",
        )
    )
    result = _run(transport, **_observe_config())
    assert result.exit_code == mcp.ExitCode.SUCCESS
    invoke_calls: list[dict[str, Any]] = []
    for request in transport.requests:
        if request["method"] != "POST" or not request["body"]:
            continue
        payload = json.loads(request["body"].decode())
        if payload.get("method") != "tools/call":
            continue
        if payload.get("params", {}).get("name") == "invoke_agent":
            invoke_calls.append(payload["params"]["arguments"])
    assert len(invoke_calls) == 1
    assert "context_id" not in invoke_calls[0]
    assert invoke_calls[0]["task"] == controller.DEFAULT_TASK
    assert result.agent_context_continuation_succeeded is False


def test_observe_only_postflight_inventory_change_fails() -> None:
    result = _run(
        FakeTransport(
            _handler(
                include_observability=False,
                agent_text="kagent native MCP acceptance.",
                postflight_include_observability=True,
            )
        ),
        **_observe_config(),
    )
    assert result.exit_code == mcp.ExitCode.PROTOCOL_OR_TOOL
    assert "unexpected agents" in (result.error or "")
    assert result.invoke_agent_succeeded is True
    assert result.strict_preflight_qualified is False


def test_observe_only_sanitized_output_marks_observation_and_no_leak() -> None:
    result = _run(
        FakeTransport(
            _handler(
                include_observability=False,
                agent_text="kagent native MCP acceptance.",
            )
        ),
        **_observe_config(),
    )
    assert result.exit_code == mcp.ExitCode.SUCCESS
    payload = result.to_sanitized_dict()
    rendered = json.dumps(payload, sort_keys=True)
    assert payload["observationOnly"] is True
    assert payload["strictPreflightQualified"] is False
    assert payload["responseTruncated"] is False
    assert RAW_CONTEXT_ID not in rendered
    assert "session-secret" not in rendered
