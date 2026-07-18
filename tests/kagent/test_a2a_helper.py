"""Deterministic tests for scripts/kagent/test-a2a-agent.py."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "kagent" / "test-a2a-agent.py"
_spec = importlib.util.spec_from_file_location("kagent_test_a2a_agent", SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
a2a = importlib.util.module_from_spec(_spec)
sys.modules["kagent_test_a2a_agent"] = a2a
_spec.loader.exec_module(a2a)


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
    ) -> a2a.HttpResponse:
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


def _json_resp(
    obj: Any, *, status: int = 200, content_type: str = "application/json"
) -> a2a.HttpResponse:
    return a2a.HttpResponse(
        status=status,
        headers={"Content-Type": content_type},
        body=json.dumps(obj).encode() if obj is not None else b"",
        content_type=content_type,
    )


def _sse_resp(events: list[dict[str, Any]], *, status: int = 200) -> a2a.HttpResponse:
    chunks = []
    for ev in events:
        chunks.append(f"data: {json.dumps(ev)}\n\n")
    body = "".join(chunks).encode()
    return a2a.HttpResponse(
        status=status,
        headers={"Content-Type": "text/event-stream"},
        body=body,
        content_type="text/event-stream",
    )


def _card_ok() -> dict[str, Any]:
    return {
        "error": False,
        "data": {
            "accepted": True,
            "deploymentReady": True,
            "model": "test",
            "modelProvider": "test",
            "agent": {
                "metadata": {"namespace": "kagent", "name": "k8s-a2a-agent"},
                "spec": {"declarative": {"a2aConfig": {"skills": []}}},
            },
        },
    }


def _card_not_ready() -> dict[str, Any]:
    data = _card_ok()
    data["data"]["deploymentReady"] = False
    return data


def _task_result(
    request_id: str, *, task_id: str = "task-abc", state: str = "submitted"
) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "id": task_id,
            "status": {"state": state},
            "kind": "task",
        },
    }


def _message_result(request_id: str, *, message_id: str = "msg-abc") -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "kind": "message",
            "messageId": message_id,
            "role": "agent",
            "parts": [{"kind": "text", "text": "ok"}],
        },
    }


def _router(mapping: dict[str, Any]):
    """Map path suffixes / health / methods to responses or callables."""

    def handler(method: str, url: str, headers: dict[str, str], body: bytes | None, timeout: float):
        path = urlparse(url).path
        if path.endswith("/health"):
            return mapping.get("health", _json_resp({"ok": True}))
        if "/api/agents/" in path:
            card = mapping.get("card", _card_ok())
            if callable(card):
                return card(method, url, headers, body, timeout)
            return _json_resp(card)
        if "/api/a2a/" in path:
            a2a_handler = mapping.get("a2a")
            if a2a_handler is None:
                raise a2a.TransportFailure("no a2a handler", error_kind="connection")
            return a2a_handler(method, url, headers, body, timeout)
        raise a2a.TransportFailure(f"unexpected url {url}", error_kind="connection")

    return handler


def _ns(**kwargs):
    return argparse_ns(**kwargs)


def argparse_ns(**kwargs):
    defaults = {
        "action": "task",
        "controller": "http://127.0.0.1:8083",
        "namespace": "kagent",
        "agent": "k8s-a2a-agent",
        "prompt": "List pods",
        "output": "json",
        "quiet": False,
    }
    defaults.update(kwargs)
    return type("Args", (), defaults)()


# --- Unit helpers ---


def test_validate_rejects_empty_object():
    with pytest.raises(a2a.GateError, match="empty object"):
        a2a.validate_jsonrpc_response("r1", {})


def test_validate_rejects_null():
    with pytest.raises(a2a.GateError, match="null"):
        a2a.validate_jsonrpc_response("r1", None)


def test_validate_rejects_empty_result():
    with pytest.raises(a2a.GateError, match="empty result"):
        a2a.validate_jsonrpc_response("r1", {"jsonrpc": "2.0", "id": "r1", "result": {}})


def test_validate_rejects_id_mismatch():
    with pytest.raises(a2a.GateError, match="mismatch"):
        a2a.validate_jsonrpc_response(
            "r1",
            {
                "jsonrpc": "2.0",
                "id": "other",
                "result": {"id": "t1", "status": {"state": "submitted"}},
            },
        )


def test_extract_rejects_missing_id():
    with pytest.raises(a2a.GateError, match="exact"):
        a2a.extract_dispatch_result({"status": {"state": "submitted"}})


def test_extract_task_and_message():
    tid, state, kind = a2a.extract_dispatch_result(
        {"kind": "task", "id": "t1", "status": {"state": "completed"}}
    )
    assert tid == "t1" and state == "completed" and kind == "task"
    mid, mstate, mkind = a2a.extract_dispatch_result(
        {
            "kind": "message",
            "messageId": "m1",
            "role": "agent",
            "parts": [{"kind": "text", "text": "ok"}],
        }
    )
    assert mid == "m1" and mstate is None and mkind == "message"


def test_extract_rejects_failed_state():
    with pytest.raises(a2a.GateError, match="not accepted"):
        a2a.extract_dispatch_result(
            {"kind": "task", "id": "t1", "status": {"state": "failed"}}
        )


@pytest.mark.parametrize(
    "result",
    [
        {"id": "t1", "status": {"state": "submitted"}},
        {"kind": "message", "messageId": "m1", "role": "agent", "parts": []},
        {"messageId": "m1", "role": "agent", "parts": [{"kind": "text"}]},
    ],
)
def test_extract_rejects_inexact_shapes(result):
    with pytest.raises(a2a.GateError, match="exact"):
        a2a.extract_dispatch_result(result)


def test_parse_sse_events():
    body = 'data: {"jsonrpc":"2.0","id":"1","result":{"ok":true}}\n\n'
    events = a2a.parse_sse_jsonrpc_events(body)
    assert len(events) == 1
    assert events[0]["id"] == "1"


def test_sanitize_redacts_authorization():
    assert a2a.sanitize_text("Authorization: Bearer secret") == "[redacted]"


def test_build_dispatch_envelope_uses_message_stream():
    env = a2a.build_dispatch_envelope("req-1", "hello")
    assert env["method"] == "message/stream"
    assert env["params"]["message"]["parts"][0]["kind"] == "text"


# --- Card ---


def test_card_accepted_and_ready():
    transport = FakeTransport(_router({"card": _card_ok()}))
    report = a2a.run(_ns(action="card"), transport=transport)
    assert report.exit_code == 0
    assert report.decision_passed is True
    assert report.card_accepted is True
    assert report.card_deployment_ready is True


def test_card_rejected_not_ready():
    transport = FakeTransport(_router({"card": _card_not_ready()}))
    report = a2a.run(_ns(action="card"), transport=transport)
    assert report.exit_code == 1
    assert report.decision_passed is False


def test_card_transport_failure():
    def handler(method, url, headers, body, timeout):
        if urlparse(url).path.endswith("/health"):
            raise a2a.TransportFailure("connection refused", error_kind="connection")
        return _json_resp({})

    transport = FakeTransport(handler)
    report = a2a.run(_ns(action="card"), transport=transport)
    assert report.exit_code == 3


# --- Probe ---


def test_probe_completes_with_unsupported_methods():
    def a2a_handler(method, url, headers, body, timeout):
        return _json_resp(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32601, "message": "Method not found"},
            }
        )

    transport = FakeTransport(_router({"a2a": a2a_handler}))
    report = a2a.run(_ns(action="probe"), transport=transport)
    assert report.exit_code == 0
    assert report.decision_passed is True
    assert "not L4" in report.reason
    for method in a2a.PROBE_METHODS:
        assert report.probe_results[method]["status"] == "unsupported"


def test_probe_transport_failure():
    def handler(method, url, headers, body, timeout):
        if urlparse(url).path.endswith("/health"):
            raise a2a.TransportFailure("unreachable", error_kind="connection")
        raise a2a.TransportFailure("unreachable", error_kind="connection")

    report = a2a.run(_ns(action="probe"), transport=FakeTransport(handler))
    assert report.exit_code == 3


# --- Task dispatch ---


def test_valid_task_sse_response():
    captured: dict[str, str] = {}

    def a2a_handler(method, url, headers, body, timeout):
        assert headers.get("Accept") == "text/event-stream"
        req = json.loads(body.decode())
        assert req["method"] == "message/stream"
        captured["id"] = req["id"]
        return _sse_resp([_task_result(req["id"], task_id="task-live-1", state="working")])

    report = a2a.run(_ns(action="task"), transport=FakeTransport(_router({"a2a": a2a_handler})))
    assert report.exit_code == 0
    assert report.task_or_message_id == "task-live-1"
    assert report.dispatch_state == "working"
    assert report.response_kind == "task"
    assert report.response_id_matched is True


def test_status_update_stream_prefers_submitted_over_failed():
    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        rid = req["id"]
        tid = "019f7036-task-id"
        events = [
            {
                "jsonrpc": "2.0",
                "id": rid,
                "result": {
                    "kind": "status-update",
                    "taskId": tid,
                    "final": False,
                    "status": {"state": "submitted"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": rid,
                "result": {
                    "kind": "status-update",
                    "taskId": tid,
                    "final": False,
                    "status": {"state": "working"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": rid,
                "result": {
                    "kind": "status-update",
                    "taskId": tid,
                    "final": True,
                    "status": {"state": "failed"},
                },
            },
        ]
        return _sse_resp(events)

    report = a2a.run(_ns(action="task"), transport=FakeTransport(_router({"a2a": a2a_handler})))
    assert report.exit_code == 0
    assert report.task_or_message_id == "019f7036-task-id"
    assert report.dispatch_state == "working"
    assert report.response_kind == "status-update"


def test_mixed_response_id_stream_fails_closed():
    events = [
        _task_result("wrong-id", task_id="wrong-task"),
        _task_result("request-1", task_id="valid-task"),
    ]
    with pytest.raises(a2a.GateError, match="mismatch"):
        a2a.select_dispatch_from_events("request-1", events)


def test_malformed_event_before_success_fails_closed():
    events = [
        {"jsonrpc": "2.0", "id": "request-1", "result": {"unexpected": True}},
        _task_result("request-1", task_id="valid-task"),
    ]
    with pytest.raises(a2a.GateError, match="exact"):
        a2a.select_dispatch_from_events("request-1", events)


def test_jsonrpc_error_before_success_fails_closed():
    events = [
        {
            "jsonrpc": "2.0",
            "id": "request-1",
            "error": {"code": -32603, "message": "internal error"},
        },
        _task_result("request-1", task_id="valid-task"),
    ]
    with pytest.raises(a2a.GateError, match="-32603"):
        a2a.select_dispatch_from_events("request-1", events)


def test_status_update_failed_only_rejected():
    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        return _sse_resp(
            [
                {
                    "jsonrpc": "2.0",
                    "id": req["id"],
                    "result": {
                        "kind": "status-update",
                        "taskId": "task-fail-only",
                        "final": True,
                        "status": {"state": "failed"},
                    },
                }
            ]
        )

    report = a2a.run(_ns(action="task"), transport=FakeTransport(_router({"a2a": a2a_handler})))
    assert report.exit_code == 1
    assert "not accepted" in report.reason


def test_valid_message_response_json():
    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        return _json_resp(_message_result(req["id"], message_id="msg-live-1"))

    report = a2a.run(_ns(action="task"), transport=FakeTransport(_router({"a2a": a2a_handler})))
    assert report.exit_code == 0
    assert report.task_or_message_id == "msg-live-1"
    assert report.response_kind == "message"


def test_empty_object_rejected():
    def a2a_handler(method, url, headers, body, timeout):
        return _json_resp({})

    report = a2a.run(_ns(action="task"), transport=FakeTransport(_router({"a2a": a2a_handler})))
    assert report.exit_code == 1
    assert report.decision_passed is False


def test_null_result_rejected():
    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        return _json_resp({"jsonrpc": "2.0", "id": req["id"], "result": None})

    report = a2a.run(_ns(action="task"), transport=FakeTransport(_router({"a2a": a2a_handler})))
    assert report.exit_code == 1


def test_missing_task_id_rejected():
    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        return _json_resp(
            {
                "jsonrpc": "2.0",
                "id": req["id"],
                "result": {"status": {"state": "submitted"}},
            }
        )

    report = a2a.run(_ns(action="task"), transport=FakeTransport(_router({"a2a": a2a_handler})))
    assert report.exit_code == 1


def test_response_id_mismatch_rejected():
    def a2a_handler(method, url, headers, body, timeout):
        return _json_resp(_task_result("wrong-id"))

    report = a2a.run(_ns(action="task"), transport=FakeTransport(_router({"a2a": a2a_handler})))
    assert report.exit_code == 1
    assert report.response_id_matched is False


def test_jsonrpc_32601():
    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        return _json_resp(
            {
                "jsonrpc": "2.0",
                "id": req["id"],
                "error": {"code": -32601, "message": "Method not found"},
            }
        )

    report = a2a.run(_ns(action="task"), transport=FakeTransport(_router({"a2a": a2a_handler})))
    assert report.exit_code == 1
    assert report.protocol_error is not None
    assert report.protocol_error["code"] == -32601


def test_jsonrpc_32603():
    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        return _json_resp(
            {
                "jsonrpc": "2.0",
                "id": req["id"],
                "error": {"code": -32603, "message": "failed to decode response"},
            }
        )

    report = a2a.run(_ns(action="task"), transport=FakeTransport(_router({"a2a": a2a_handler})))
    assert report.exit_code == 1
    assert report.protocol_error["code"] == -32603


def test_http_4xx():
    def a2a_handler(method, url, headers, body, timeout):
        return a2a.HttpResponse(status=404, headers={}, body=b"missing", content_type="text/plain")

    report = a2a.run(_ns(action="task"), transport=FakeTransport(_router({"a2a": a2a_handler})))
    assert report.exit_code == 3


def test_http_5xx():
    def a2a_handler(method, url, headers, body, timeout):
        return a2a.HttpResponse(status=502, headers={}, body=b"bad", content_type="text/plain")

    report = a2a.run(_ns(action="task"), transport=FakeTransport(_router({"a2a": a2a_handler})))
    assert report.exit_code == 3


def test_timeout_failure():
    def handler(method, url, headers, body, timeout):
        raise a2a.TransportFailure("timeout: timed out", error_kind="timeout")

    report = a2a.run(_ns(action="task"), transport=FakeTransport(handler))
    assert report.exit_code == 3
    assert report.transport_error_kind == "timeout"


def test_connection_failure():
    def handler(method, url, headers, body, timeout):
        raise a2a.TransportFailure("connection refused", error_kind="connection")

    report = a2a.run(_ns(action="task"), transport=FakeTransport(handler))
    assert report.exit_code == 3


def test_invalid_json_response():
    def a2a_handler(method, url, headers, body, timeout):
        return a2a.HttpResponse(
            status=200,
            headers={"Content-Type": "application/json"},
            body=b"not-json{",
            content_type="application/json",
        )

    report = a2a.run(_ns(action="task"), transport=FakeTransport(_router({"a2a": a2a_handler})))
    assert report.exit_code == 1


def test_both_success():
    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        return _sse_resp([_task_result(req["id"])])

    report = a2a.run(
        _ns(action="both"),
        transport=FakeTransport(_router({"card": _card_ok(), "a2a": a2a_handler})),
    )
    assert report.exit_code == 0
    assert report.action == "both"


def test_both_fails_when_task_fails():
    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        return _json_resp(
            {
                "jsonrpc": "2.0",
                "id": req["id"],
                "error": {"code": -32601, "message": "Method not found"},
            }
        )

    report = a2a.run(
        _ns(action="both"),
        transport=FakeTransport(_router({"card": _card_ok(), "a2a": a2a_handler})),
    )
    assert report.exit_code == 1
    assert "task failed" in report.reason


def test_json_output_has_schema_and_no_secrets(capsys):
    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        return _sse_resp([_task_result(req["id"])])

    args = _ns(action="task", output="json")
    report = a2a.run(args, transport=FakeTransport(_router({"a2a": a2a_handler})))
    a2a.emit_json(report)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["schemaVersion"] == "1.0"
    assert data["decision"]["exitCode"] == 0
    blob = out.lower()
    assert "authorization" not in blob
    assert "bearer " not in blob
    assert "kubeconfig" not in blob


def test_human_output(capsys):
    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        return _sse_resp([_task_result(req["id"])])

    report = a2a.run(_ns(action="task"), transport=FakeTransport(_router({"a2a": a2a_handler})))
    a2a.emit_human(report, quiet=True)
    out = capsys.readouterr().out
    assert "[PASS]" in out
    assert "exit=0" in out


def test_main_exit_codes_card_probe_task(monkeypatch):
    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode()) if body else {}
        if req.get("method") == "message/stream" and "params" in req and req["params"]:
            return _sse_resp([_task_result(req["id"])])
        return _json_resp(
            {
                "jsonrpc": "2.0",
                "id": req.get("id", 1),
                "error": {"code": -32601, "message": "Method not found"},
            }
        )

    transport = FakeTransport(_router({"card": _card_ok(), "a2a": a2a_handler}))

    monkeypatch.setattr(a2a, "DirectUrlTransport", lambda: transport)

    assert a2a.main(["card", "--output", "json"]) == 0
    assert a2a.main(["probe", "--output", "json"]) == 0
    assert a2a.main(["task", "--output", "json"]) == 0


def test_main_task_gate_failure(monkeypatch, capsys):
    def a2a_handler(method, url, headers, body, timeout):
        return _json_resp({})

    transport = FakeTransport(_router({"a2a": a2a_handler}))
    monkeypatch.setattr(a2a, "DirectUrlTransport", lambda: transport)
    code = a2a.main(["task", "--output", "json"])
    assert code == 1
    data = json.loads(capsys.readouterr().out)
    assert data["decision"]["passed"] is False


def test_no_secrets_in_sanitized_dict():
    report = a2a.EvidenceReport(
        action="task",
        transport_error="Authorization: Bearer super-secret-token",
        request_id="x" * 80,
    )
    data = report.to_sanitized_dict()
    assert data["transport"]["error"] == "[redacted]"
    assert data["protocol"]["requestId"].endswith("…")
