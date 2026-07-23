"""Deterministic tests for scripts/kagent/mcp_session_smoke.py."""

from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "scripts" / "kagent"
sys.path.insert(0, str(SCRIPT_DIR))

import mcp_session_smoke as smoke  # noqa: E402


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
    ) -> smoke.HttpResponse:
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


def _json_headers(**extra: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    headers.update(extra)
    return headers


def _init_ok(
    *,
    session_header_name: str = "Mcp-Session-Id",
    session_id: str = "mcp-session-test-1",
    protocol_version: str = "2024-11-05",
    req_id: int = 1,
) -> smoke.HttpResponse:
    body = {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": protocol_version,
            "capabilities": {"tools": {"listChanged": True}},
            "serverInfo": {"name": "fake", "version": "0"},
        },
    }
    return smoke.HttpResponse(
        status=200,
        headers=_json_headers(**{session_header_name: session_id}),
        body=json.dumps(body).encode(),
        content_type="application/json",
    )


def _tool_def(
    *,
    name: str = "k8s_get_resources",
    required: list[str] | None = None,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    props = (
        properties
        if properties is not None
        else {
            "resource_type": {"type": "string"},
            "namespace": {"type": "string"},
        }
    )
    return {
        "name": name,
        "description": "fake",
        "inputSchema": {
            "type": "object",
            "properties": props,
            "required": required if required is not None else ["resource_type"],
        },
    }


def _list_ok(
    tools: list[dict[str, Any]], *, req_id: int, next_cursor: str | None = None
) -> smoke.HttpResponse:
    result: dict[str, Any] = {"tools": tools}
    if next_cursor is not None:
        result["nextCursor"] = next_cursor
    body = {"jsonrpc": "2.0", "id": req_id, "result": result}
    return smoke.HttpResponse(
        status=200,
        headers=_json_headers(),
        body=json.dumps(body).encode(),
        content_type="application/json",
    )


def _call_ok(req_id: int, text: str = "NAME  READY\npod-a  1/1\n") -> smoke.HttpResponse:
    body = {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {"content": [{"type": "text", "text": text}], "isError": False},
    }
    return smoke.HttpResponse(
        status=200,
        headers=_json_headers(),
        body=json.dumps(body).encode(),
        content_type="application/json",
    )


def _scripted_success_handler(
    *,
    session_header_name: str = "Mcp-Session-Id",
    initialized_status: int = 202,
    delete_status: int = 200,
    tools: list[dict[str, Any]] | None = None,
    list_pages: list[list[dict[str, Any]]] | None = None,
    call_response: smoke.HttpResponse | None = None,
):
    state = {"list_page": 0}
    if list_pages is not None:
        tool_pages = list_pages
    elif tools is not None:
        tool_pages = [tools]
    else:
        tool_pages = [[_tool_def()]]

    def handler(method, url, headers, body, timeout):
        if method == "DELETE":
            return smoke.HttpResponse(
                status=delete_status,
                headers={},
                body=b"",
                content_type="",
            )
        assert method == "POST"
        payload = json.loads(body.decode()) if body else {}
        name = payload.get("method")
        if name == "initialize":
            return _init_ok(session_header_name=session_header_name, req_id=payload["id"])
        if name == "notifications/initialized":
            assert headers.get("Mcp-Session-Id") == "mcp-session-test-1"
            return smoke.HttpResponse(status=initialized_status, headers={}, body=b"")
        if name == "tools/list":
            page_idx = state["list_page"]
            state["list_page"] += 1
            if page_idx >= len(tool_pages):
                raise AssertionError("tools/list page out of range")
            page = tool_pages[page_idx]
            next_cursor = f"c{page_idx + 1}" if page_idx + 1 < len(tool_pages) else None
            return _list_ok(page, req_id=payload["id"], next_cursor=next_cursor)
        if name == "tools/call":
            if call_response is not None:
                raw = json.loads(call_response.body.decode())
                raw["id"] = payload["id"]
                return smoke.HttpResponse(
                    status=call_response.status,
                    headers=dict(call_response.headers),
                    body=json.dumps(raw).encode(),
                    content_type=call_response.content_type,
                )
            return _call_ok(payload["id"])
        raise AssertionError(f"unexpected method {name}")

    return handler


def test_initialize_success_captures_session() -> None:
    transport = FakeTransport(_scripted_success_handler())
    cfg = smoke.SessionConfig(arguments={"resource_type": "pod"})
    result = smoke.McpSessionClient(cfg, transport).run()
    assert result.exit_code == smoke.ExitCode.SUCCESS
    assert result.session_id_present
    assert result.negotiated_protocol_version == "2024-11-05"
    assert result.initialized_http_status == 202
    assert result.tool_call_succeeded


def test_session_header_case_insensitive() -> None:
    transport = FakeTransport(_scripted_success_handler(session_header_name="mcp-session-id"))
    cfg = smoke.SessionConfig(arguments={"resource_type": "pod"})
    result = smoke.McpSessionClient(cfg, transport).run()
    assert result.exit_code == smoke.ExitCode.SUCCESS


def test_missing_session_id_fails() -> None:
    def handler(method, url, headers, body, timeout):
        payload = json.loads(body.decode())
        body_obj = {
            "jsonrpc": "2.0",
            "id": payload["id"],
            "result": {"protocolVersion": "2024-11-05", "capabilities": {}, "serverInfo": {}},
        }
        return smoke.HttpResponse(
            status=200,
            headers=_json_headers(),
            body=json.dumps(body_obj).encode(),
            content_type="application/json",
        )

    result = smoke.McpSessionClient(smoke.SessionConfig(), FakeTransport(handler)).run()
    assert result.exit_code == smoke.ExitCode.PROTOCOL_OR_TOOL
    assert "Mcp-Session-Id" in (result.error or "")


def test_initialize_non_2xx() -> None:
    def handler(method, url, headers, body, timeout):
        return smoke.HttpResponse(status=500, headers={}, body=b"err", content_type="text/plain")

    result = smoke.McpSessionClient(smoke.SessionConfig(), FakeTransport(handler)).run()
    assert result.exit_code == smoke.ExitCode.PROTOCOL_OR_TOOL
    assert "initialize HTTP 500" in (result.error or "")


def test_initialize_malformed_json() -> None:
    def handler(method, url, headers, body, timeout):
        return smoke.HttpResponse(
            status=200,
            headers=_json_headers(**{"Mcp-Session-Id": "s1"}),
            body=b"{not-json",
            content_type="application/json",
        )

    result = smoke.McpSessionClient(smoke.SessionConfig(), FakeTransport(handler)).run()
    assert result.exit_code == smoke.ExitCode.PROTOCOL_OR_TOOL
    assert "malformed" in (result.error or "")


def test_initialize_jsonrpc_error() -> None:
    def handler(method, url, headers, body, timeout):
        payload = json.loads(body.decode())
        body_obj = {
            "jsonrpc": "2.0",
            "id": payload["id"],
            "error": {"code": -32600, "message": "invalid"},
        }
        return smoke.HttpResponse(
            status=200,
            headers=_json_headers(**{"Mcp-Session-Id": "s1"}),
            body=json.dumps(body_obj).encode(),
            content_type="application/json",
        )

    result = smoke.McpSessionClient(smoke.SessionConfig(), FakeTransport(handler)).run()
    assert result.exit_code == smoke.ExitCode.PROTOCOL_OR_TOOL
    assert "JSON-RPC error" in (result.error or "")


def test_unsupported_negotiated_protocol_version() -> None:
    def handler(method, url, headers, body, timeout):
        return _init_ok(protocol_version="1999-01-01")

    result = smoke.McpSessionClient(smoke.SessionConfig(), FakeTransport(handler)).run()
    assert result.exit_code == smoke.ExitCode.PROTOCOL_OR_TOOL
    assert "unsupported negotiated" in (result.error or "")


def test_tools_call_reuses_exact_session_id() -> None:
    transport = FakeTransport(_scripted_success_handler())
    cfg = smoke.SessionConfig(arguments={"resource_type": "pod"})
    result = smoke.McpSessionClient(cfg, transport).run()
    assert result.exit_code == smoke.ExitCode.SUCCESS
    call_reqs = [
        r
        for r in transport.requests
        if r["body"] and json.loads(r["body"]).get("method") == "tools/call"
    ]
    assert len(call_reqs) == 1
    assert call_reqs[0]["headers"]["Mcp-Session-Id"] == "mcp-session-test-1"


def test_tools_call_http_failure() -> None:
    base = _scripted_success_handler()

    def handler(method, url, headers, body, timeout):
        if method == "DELETE":
            return smoke.HttpResponse(status=200, headers={}, body=b"")
        payload = json.loads(body.decode())
        if payload.get("method") == "tools/call":
            return smoke.HttpResponse(
                status=400, headers={}, body=b"nope", content_type="text/plain"
            )
        return base(method, url, headers, body, timeout)

    result = smoke.McpSessionClient(
        smoke.SessionConfig(arguments={"resource_type": "pod"}), FakeTransport(handler)
    ).run()
    assert result.exit_code == smoke.ExitCode.PROTOCOL_OR_TOOL
    assert "tools/call HTTP 400" in (result.error or "")


def test_tools_call_jsonrpc_error() -> None:
    def make_call(req_id: int) -> smoke.HttpResponse:
        body = {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32000, "message": "boom"},
        }
        return smoke.HttpResponse(
            status=200,
            headers=_json_headers(),
            body=json.dumps(body).encode(),
            content_type="application/json",
        )

    base = _scripted_success_handler()

    def handler(method, url, headers, body, timeout):
        if method == "DELETE":
            return smoke.HttpResponse(status=200, headers={}, body=b"")
        payload = json.loads(body.decode())
        if payload.get("method") == "tools/call":
            return make_call(payload["id"])
        return base(method, url, headers, body, timeout)

    result = smoke.McpSessionClient(
        smoke.SessionConfig(arguments={"resource_type": "pod"}), FakeTransport(handler)
    ).run()
    assert result.exit_code == smoke.ExitCode.PROTOCOL_OR_TOOL
    assert "tools/call JSON-RPC error" in (result.error or "")


def test_tools_call_malformed_payload() -> None:
    base = _scripted_success_handler()

    def handler(method, url, headers, body, timeout):
        if method == "DELETE":
            return smoke.HttpResponse(status=200, headers={}, body=b"")
        payload = json.loads(body.decode())
        if payload.get("method") == "tools/call":
            return smoke.HttpResponse(
                status=200,
                headers=_json_headers(),
                body=b"{bad",
                content_type="application/json",
            )
        return base(method, url, headers, body, timeout)

    result = smoke.McpSessionClient(
        smoke.SessionConfig(arguments={"resource_type": "pod"}), FakeTransport(handler)
    ).run()
    assert result.exit_code == smoke.ExitCode.PROTOCOL_OR_TOOL
    assert "malformed" in (result.error or "")


def test_tools_call_success_summary() -> None:
    transport = FakeTransport(_scripted_success_handler())
    result = smoke.McpSessionClient(
        smoke.SessionConfig(arguments={"resource_type": "pod"}), transport
    ).run()
    assert result.exit_code == smoke.ExitCode.SUCCESS
    assert result.resource_summary.get("count", 0) >= 1


def test_timeout_maps_to_transport_exit() -> None:
    def handler(method, url, headers, body, timeout):
        raise smoke.TransportError("timeout: timed out")

    result = smoke.McpSessionClient(smoke.SessionConfig(), FakeTransport(handler)).run()
    assert result.exit_code == smoke.ExitCode.TRANSPORT


def test_sanitized_output_omits_session_and_headers(capsys: pytest.CaptureFixture[str]) -> None:
    transport = FakeTransport(_scripted_success_handler())
    cfg = smoke.SessionConfig(arguments={"resource_type": "pod"}, output="json")
    client = smoke.McpSessionClient(cfg, transport)
    result = client.run()
    smoke.emit_result(result, output="json", quiet=False)
    out = capsys.readouterr().out
    assert "mcp-session-test-1" not in out
    assert "Authorization" not in out
    data = json.loads(out)
    assert data["sessionId"] == "present"


def test_close_delete_after_success() -> None:
    transport = FakeTransport(_scripted_success_handler(delete_status=200))
    result = smoke.McpSessionClient(
        smoke.SessionConfig(arguments={"resource_type": "pod"}), transport
    ).run()
    assert result.exit_code == smoke.ExitCode.SUCCESS
    assert result.cleanup == "deleted"
    assert any(r["method"] == "DELETE" for r in transport.requests)


def test_close_delete_after_failure_when_session_issued() -> None:
    base = _scripted_success_handler()

    def handler(method, url, headers, body, timeout):
        if method == "DELETE":
            return smoke.HttpResponse(status=200, headers={}, body=b"")
        payload = json.loads(body.decode())
        if payload.get("method") == "tools/list":
            return smoke.HttpResponse(status=500, headers={}, body=b"x", content_type="text/plain")
        return base(method, url, headers, body, timeout)

    transport = FakeTransport(handler)
    result = smoke.McpSessionClient(smoke.SessionConfig(), transport).run()
    assert result.exit_code == smoke.ExitCode.PROTOCOL_OR_TOOL
    assert any(r["method"] == "DELETE" for r in transport.requests)
    assert result.cleanup == "deleted"


def test_cleanup_http_500_after_success() -> None:
    """Main succeeded, DELETE returns 500 -- exit code promoted to failure."""
    transport = FakeTransport(_scripted_success_handler(delete_status=500))
    result = smoke.McpSessionClient(
        smoke.SessionConfig(arguments={"resource_type": "pod"}), transport
    ).run()
    assert result.exit_code == smoke.ExitCode.PROTOCOL_OR_TOOL
    assert result.cleanup == "failed"
    assert result.error is not None


def test_cleanup_transport_error_after_success() -> None:
    """Main succeeded, DELETE raises TransportError -- exit code promoted to failure."""
    base = _scripted_success_handler()

    def handler(method, url, headers, body, timeout):
        if method == "DELETE":
            raise smoke.TransportError("cleanup connection refused")
        return base(method, url, headers, body, timeout)

    transport = FakeTransport(handler)
    result = smoke.McpSessionClient(
        smoke.SessionConfig(arguments={"resource_type": "pod"}), transport
    ).run()
    assert result.exit_code == smoke.ExitCode.PROTOCOL_OR_TOOL
    assert result.cleanup == "failed"


def test_cleanup_timeout_after_success() -> None:
    """Main succeeded, DELETE raises timeout -- exit code promoted to failure."""
    base = _scripted_success_handler()

    def handler(method, url, headers, body, timeout):
        if method == "DELETE":
            raise smoke.TransportError("timeout: timed out")
        return base(method, url, headers, body, timeout)

    transport = FakeTransport(handler)
    result = smoke.McpSessionClient(
        smoke.SessionConfig(arguments={"resource_type": "pod"}), transport
    ).run()
    assert result.exit_code == smoke.ExitCode.PROTOCOL_OR_TOOL
    assert result.cleanup == "failed"


def test_cleanup_failure_preserves_primary_failure() -> None:
    """Main operation fails AND cleanup fails -- preserve original exit code and error."""
    base = _scripted_success_handler()

    def handler(method, url, headers, body, timeout):
        if method == "DELETE":
            return smoke.HttpResponse(status=500, headers={}, body=b"")
        payload = json.loads(body.decode())
        if payload.get("method") == "tools/list":
            return smoke.HttpResponse(status=500, headers={}, body=b"x", content_type="text/plain")
        return base(method, url, headers, body, timeout)

    transport = FakeTransport(handler)
    result = smoke.McpSessionClient(smoke.SessionConfig(), transport).run()
    # Primary failure was PROTOCOL_OR_TOOL, cleanup failure does not overwrite
    assert result.exit_code == smoke.ExitCode.PROTOCOL_OR_TOOL
    assert result.cleanup == "failed"
    # Error should be the primary error, not "session cleanup failed"
    assert result.error is not None
    assert "cleanup" not in (result.error or "").lower()


def test_cleanup_no_session_no_failure() -> None:
    """No session established -- cleanup is no-op, no manufactured failure."""

    def handler(method, url, headers, body, timeout):
        raise smoke.TransportError("network unreachable")

    cfg = smoke.SessionConfig(arguments={"resource_type": "pod"}, timeout=1)
    result = smoke.McpSessionClient(cfg, FakeTransport(handler)).run()
    assert result.cleanup == "not-applicable"
    # Should preserve the primary error (transport failure), not manufacture one
    assert result.error is not None


def test_main_cleanup_failure_exit_code() -> None:
    """CLI entry point returns non-zero when cleanup fails after success."""
    handler = _scripted_success_handler(delete_status=500)

    class Patched(smoke.DirectUrlTransport):
        def request(self, method, url, *, headers, body=None, timeout=5):
            return handler(method, url, headers, body, timeout)

    original = smoke.DirectUrlTransport
    smoke.DirectUrlTransport = Patched  # type: ignore[misc, assignment]
    try:
        code = smoke.main(
            [
                "--url",
                "http://127.0.0.1:8000/mcp",
                "--arguments-json",
                '{"resource_type":"pod"}',
                "--output",
                "json",
                "--quiet",
            ]
        )
        assert code == smoke.ExitCode.PROTOCOL_OR_TOOL
    finally:
        smoke.DirectUrlTransport = original  # type: ignore[misc]


def test_quiet_and_json_cli(capsys: pytest.CaptureFixture[str]) -> None:
    transport = FakeTransport(_scripted_success_handler())
    cfg = smoke.SessionConfig(arguments={"resource_type": "pod"}, output="json", quiet=True)
    result = smoke.McpSessionClient(cfg, transport).run()
    smoke.emit_result(result, output="json", quiet=True)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["toolCallSucceeded"] is True
    assert data["exitCode"] == 0


def test_invalid_cli_fails_before_network() -> None:
    code = smoke.main(["--url", "http://example.com/mcp", "--timeout", "5"])
    assert code == smoke.ExitCode.USAGE


def test_initialized_202() -> None:
    transport = FakeTransport(_scripted_success_handler(initialized_status=202))
    result = smoke.McpSessionClient(
        smoke.SessionConfig(arguments={"resource_type": "pod"}), transport
    ).run()
    assert result.initialized_http_status == 202
    assert result.initialized_compatibility_deviation is False


def test_initialized_rejection_stops_before_tools_list() -> None:
    base = _scripted_success_handler(initialized_status=400)
    transport = FakeTransport(base)
    result = smoke.McpSessionClient(smoke.SessionConfig(), transport).run()
    assert result.exit_code == smoke.ExitCode.PROTOCOL_OR_TOOL
    methods = [
        json.loads(r["body"]).get("method")
        for r in transport.requests
        if r["method"] == "POST" and r["body"]
    ]
    assert "tools/list" not in methods
    assert "tools/call" not in methods


def test_tools_list_target_missing() -> None:
    transport = FakeTransport(_scripted_success_handler(tools=[_tool_def(name="other_tool")]))
    result = smoke.McpSessionClient(
        smoke.SessionConfig(arguments={"resource_type": "pod"}), transport
    ).run()
    assert result.exit_code == smoke.ExitCode.PROTOCOL_OR_TOOL
    assert "not advertised" in (result.error or "")


def test_tools_list_pagination() -> None:
    pages = [
        [_tool_def(name="other")],
        [_tool_def(name="k8s_get_resources")],
    ]
    transport = FakeTransport(_scripted_success_handler(list_pages=pages))
    result = smoke.McpSessionClient(
        smoke.SessionConfig(arguments={"resource_type": "pod"}), transport
    ).run()
    assert result.exit_code == smoke.ExitCode.SUCCESS
    list_calls = [
        r
        for r in transport.requests
        if r["body"] and json.loads(r["body"]).get("method") == "tools/list"
    ]
    assert len(list_calls) == 2


def test_tools_list_exceeds_max_pages() -> None:
    pages = [[_tool_def(name=f"t{i}")] for i in range(smoke.MAX_TOOLS_LIST_PAGES + 1)]
    transport = FakeTransport(_scripted_success_handler(list_pages=pages))
    result = smoke.McpSessionClient(smoke.SessionConfig(tool="missing"), transport).run()
    assert result.exit_code == smoke.ExitCode.PROTOCOL_OR_TOOL
    assert "max pages" in (result.error or "")


def test_required_schema_property_missing() -> None:
    transport = FakeTransport(
        _scripted_success_handler(tools=[_tool_def(required=["resource_type", "namespace"])])
    )
    result = smoke.McpSessionClient(
        smoke.SessionConfig(arguments={"resource_type": "pod"}), transport
    ).run()
    assert result.exit_code == smoke.ExitCode.PROTOCOL_OR_TOOL
    assert "missing required" in (result.error or "")


def test_jsonrpc_id_mismatch() -> None:
    msg = {"jsonrpc": "2.0", "id": 999, "result": {"ok": True}}
    with pytest.raises(smoke.ProtocolError, match="id mismatch"):
        smoke.decode_mcp_response("application/json", json.dumps(msg).encode(), expected_id=1)


def test_sse_multiline_data() -> None:
    raw = b'data: {"jsonrpc":"2.0","id":3,\ndata: "result":{"ok":true}}\n\n'
    # Proper multi-line: two data lines that join into one JSON
    raw = (
        b'data: {"jsonrpc": "2.0", "id": 3,\n'
        b'data: "result": {"content": [{"type": "text", "text": "ok"}], "isError": false}}\n\n'
    )
    message = smoke.parse_sse_jsonrpc(raw, expected_id=3)
    assert message["id"] == 3
    assert message["result"]["isError"] is False


def test_sse_notification_then_response() -> None:
    raw = (
        b'data: {"jsonrpc":"2.0","method":"notifications/progress"}\n\n'
        b'data: {"jsonrpc":"2.0","id":2,"result":{"ok":true}}\n\n'
    )
    message = smoke.parse_sse_jsonrpc(raw, expected_id=2)
    assert message["result"]["ok"] is True


def test_sse_ends_before_response() -> None:
    raw = b'data: {"jsonrpc":"2.0","method":"notifications/progress"}\n\n'
    with pytest.raises(smoke.ProtocolError, match="ended before matching"):
        smoke.parse_sse_jsonrpc(raw, expected_id=1)


def test_sse_wrong_response_id() -> None:
    raw = b'data: {"jsonrpc":"2.0","id":9,"result":{}}\n\n'
    with pytest.raises(smoke.ProtocolError, match="id mismatch"):
        smoke.parse_sse_jsonrpc(raw, expected_id=1)


def test_json_content_type_with_charset() -> None:
    body = {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}
    message = smoke.decode_mcp_response(
        "application/json; charset=utf-8",
        json.dumps(body).encode(),
        expected_id=1,
    )
    assert message["result"]["ok"] is True


def test_redirect_refused() -> None:
    class RedirectHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1/elsewhere")
            self.end_headers()

        def log_message(self, format: str, *args: Any) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        transport = smoke.DirectUrlTransport()
        with pytest.raises(smoke.ProtocolError, match="redirect refused"):
            transport.request(
                "POST",
                f"http://127.0.0.1:{port}/mcp",
                headers={"Content-Type": "application/json"},
                body=b"{}",
                timeout=5,
            )
    finally:
        server.shutdown()


def test_invalid_session_id_non_ascii() -> None:
    with pytest.raises(smoke.ProtocolError, match="visible ASCII"):
        smoke.capture_session_id({"Mcp-Session-Id": "sess-\u2603"})
    with pytest.raises(smoke.ProtocolError, match="visible ASCII"):
        smoke.capture_session_id({"Mcp-Session-Id": "sess internal-space"})


def test_delete_405_unsupported_cleanup() -> None:
    transport = FakeTransport(_scripted_success_handler(delete_status=405))
    result = smoke.McpSessionClient(
        smoke.SessionConfig(arguments={"resource_type": "pod"}), transport
    ).run()
    assert result.exit_code == smoke.ExitCode.SUCCESS
    assert result.cleanup == "unsupported"


def test_http_error_vs_transport_exception() -> None:
    def http_fail(method, url, headers, body, timeout):
        return smoke.HttpResponse(status=503, headers={}, body=b"", content_type="")

    http_result = smoke.McpSessionClient(smoke.SessionConfig(), FakeTransport(http_fail)).run()
    assert http_result.exit_code == smoke.ExitCode.PROTOCOL_OR_TOOL

    def conn_fail(method, url, headers, body, timeout):
        raise smoke.TransportError("connection refused")

    conn_result = smoke.McpSessionClient(smoke.SessionConfig(), FakeTransport(conn_fail)).run()
    assert conn_result.exit_code == smoke.ExitCode.TRANSPORT


def test_simulate_missing_initialized_skips_notification() -> None:
    transport = FakeTransport(_scripted_success_handler())
    cfg = smoke.SessionConfig(
        arguments={"resource_type": "pod"},
        simulate_missing_initialized=True,
    )
    smoke.McpSessionClient(cfg, transport).run()
    methods = [
        json.loads(r["body"]).get("method")
        for r in transport.requests
        if r["method"] == "POST" and r["body"]
    ]
    assert "notifications/initialized" not in methods
    # Without initialized, server may still accept in our fake — success is ok for skip behavior.
    assert "initialize" in methods


def test_config_from_args_rejects_bad_json() -> None:
    parser = smoke.build_parser()
    args = parser.parse_args(["--arguments-json", "not-json"])
    with pytest.raises(smoke.UsageError):
        smoke.config_from_args(args)


def test_integration_urllib_json_and_session_header() -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode())
            if payload.get("method") == "initialize":
                body = {
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "serverInfo": {"name": "i", "version": "0"},
                    },
                }
                data = json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Mcp-Session-Id", "mcp-session-integration")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if payload.get("method") == "notifications/initialized":
                assert self.headers.get("Mcp-Session-Id") == "mcp-session-integration"
                self.send_response(202)
                self.end_headers()
                return
            if payload.get("method") == "tools/list":
                body = {
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {"tools": [_tool_def()]},
                }
                data = json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if payload.get("method") == "tools/call":
                assert self.headers.get("Mcp-Session-Id") == "mcp-session-integration"
                body = {
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {
                        "content": [{"type": "text", "text": "NAME\np1\n"}],
                        "isError": False,
                    },
                }
                data = json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            self.send_response(500)
            self.end_headers()

        def do_DELETE(self) -> None:
            self.send_response(405)
            self.end_headers()

        def log_message(self, format: str, *args: Any) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        cfg = smoke.SessionConfig(
            url=f"http://127.0.0.1:{port}/mcp",
            arguments={"resource_type": "pod"},
        )
        result = smoke.McpSessionClient(cfg).run()
        assert result.exit_code == smoke.ExitCode.SUCCESS
        assert result.cleanup == "unsupported"
        assert result.session_id_present
    finally:
        server.shutdown()


def test_integration_sse_tools_call() -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode())
            method = payload.get("method")
            if method == "initialize":
                body = {
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "serverInfo": {"name": "i", "version": "0"},
                    },
                }
                data = json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Mcp-Session-Id", "sse-session")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if method == "notifications/initialized":
                self.send_response(202)
                self.end_headers()
                return
            if method == "tools/list":
                body = {
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {"tools": [_tool_def()]},
                }
                data = json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if method == "tools/call":
                event = (
                    'data: {"jsonrpc":"2.0","method":"notifications/progress"}\n\n'
                    f'data: {{"jsonrpc":"2.0","id":{payload["id"]},'
                    '"result":{"content":[{"type":"text","text":"NAME\\nx\\n"}],'
                    '"isError":false}}\n\n'
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(event)))
                self.end_headers()
                self.wfile.write(event)
                return
            self.send_response(500)
            self.end_headers()

        def do_DELETE(self) -> None:
            self.send_response(200)
            self.end_headers()

        def log_message(self, format: str, *args: Any) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        cfg = smoke.SessionConfig(
            url=f"http://127.0.0.1:{port}/mcp",
            arguments={"resource_type": "pod"},
        )
        result = smoke.McpSessionClient(cfg).run()
        assert result.exit_code == smoke.ExitCode.SUCCESS
        assert result.cleanup == "deleted"
    finally:
        server.shutdown()


def test_main_success_exit_code() -> None:
    # Patch client path via running against fake by monkeypatching DirectUrlTransport
    handler = _scripted_success_handler()

    class Patched(smoke.DirectUrlTransport):
        def request(self, method, url, *, headers, body=None, timeout=5):
            return handler(method, url, headers, body, timeout)

    original = smoke.DirectUrlTransport
    smoke.DirectUrlTransport = Patched  # type: ignore[misc, assignment]
    try:
        code = smoke.main(
            [
                "--url",
                "http://127.0.0.1:8000/mcp",
                "--arguments-json",
                '{"resource_type":"pod"}',
                "--output",
                "json",
                "--quiet",
            ]
        )
        assert code == 0
    finally:
        smoke.DirectUrlTransport = original  # type: ignore[misc]
