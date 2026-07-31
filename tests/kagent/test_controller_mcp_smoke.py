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


def _agents(*, include_target: bool = True) -> list[dict[str, str]]:
    agents = [{"ref": "kagent/observability-agent"}]
    if include_target:
        agents.append({"ref": "kagent/k8s-a2a-agent"})
    return agents


def _handler(
    *,
    tools: list[dict[str, Any]] | None = None,
    include_target: bool = True,
    agent_text: str = controller.DEFAULT_EXPECTED_RESPONSE,
    malformed_tools: bool = False,
    timeout_on_invoke: bool = False,
):
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
                return _response(
                    {
                        "jsonrpc": "2.0",
                        "id": payload["id"],
                        "result": {
                            "structuredContent": {"agents": _agents(include_target=include_target)}
                        },
                    }
                )
            assert tool_name == "invoke_agent"
            if timeout_on_invoke:
                raise mcp.TransportError("timeout: simulated")
            assert payload["params"]["arguments"] == {
                "agent": "kagent/k8s-a2a-agent",
                "task": controller.DEFAULT_TASK,
            }
            return _response(
                {
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {
                        "structuredContent": {
                            "agent": "kagent/k8s-a2a-agent",
                            "context_id": "must-not-appear-in-output",
                            "text": agent_text,
                        }
                    },
                }
            )
        raise AssertionError(f"unexpected MCP method {name!r}")

    return handler


def _run(transport: FakeTransport, **kwargs: Any) -> controller.ControllerMcpResult:
    return controller.ControllerMcpClient(controller.ControllerMcpConfig(**kwargs), transport).run()


def test_success_requires_exact_tools_target_response_and_session_continuation() -> None:
    transport = FakeTransport(_handler())
    result = _run(transport)

    assert result.exit_code == mcp.ExitCode.SUCCESS
    assert result.session_id_present
    assert result.controller_tools == ["invoke_agent", "list_agents"]
    assert result.target_agent_found
    assert result.invoke_agent_succeeded
    assert result.same_session_continuation_http_status == 200
    assert result.continuation_target_present
    assert result.cleanup == "method-not-allowed"
    rendered = json.dumps(result.to_sanitized_dict())
    assert "session-secret" not in rendered
    assert "must-not-appear-in-output" not in rendered
    calls_with_session = [
        request for request in transport.requests[1:] if request["method"] == "POST"
    ]
    assert all(
        request["headers"]["Mcp-Session-Id"] == "session-secret" for request in calls_with_session
    )


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


def test_controller_url_rejects_userinfo_and_non_mcp_path() -> None:
    userinfo = _run(FakeTransport(_handler()), url="http://user:pass@127.0.0.1:8083/mcp")
    wrong_path = _run(FakeTransport(_handler()), url="http://127.0.0.1:8083/api")
    assert userinfo.exit_code == mcp.ExitCode.USAGE
    assert wrong_path.exit_code == mcp.ExitCode.USAGE
    assert "controller URL" in (userinfo.error or "")
