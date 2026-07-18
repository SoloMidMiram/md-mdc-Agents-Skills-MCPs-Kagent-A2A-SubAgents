"""Deterministic tests for scripts/kagent/agent_mcp_trace.py."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "kagent" / "agent_mcp_trace.py"
_spec = importlib.util.spec_from_file_location("agent_mcp_trace", SCRIPT)
assert _spec is not None and _spec.loader is not None
trace = importlib.util.module_from_spec(_spec)
sys.modules["agent_mcp_trace"] = trace
_spec.loader.exec_module(trace)

a2a = trace.a2a
FIXTURE_SRC = "tests/kagent/fixtures/agent-mediated-source.json"


class FakeTransport:
    def __init__(self, handler) -> None:
        self.handler = handler

    def request(self, method, url, *, headers, body=None, timeout=30.0):
        return self.handler(method, url, headers, body, timeout)


def _json_resp(obj: Any, *, status: int = 200, content_type: str = "application/json"):
    return a2a.HttpResponse(
        status=status,
        headers={"Content-Type": content_type},
        body=json.dumps(obj).encode() if obj is not None else b"",
        content_type=content_type,
    )


def _sse(events: list[dict[str, Any]]):
    body = "".join(f"data: {json.dumps(ev)}\n\n" for ev in events).encode()
    return a2a.HttpResponse(
        status=200,
        headers={"Content-Type": "text/event-stream"},
        body=body,
        content_type="text/event-stream",
    )


def _router(a2a_handler):
    def handler(method, url, headers, body, timeout):
        path = urlparse(url).path
        if path.endswith("/health"):
            return _json_resp({"ok": True})
        if "/api/a2a/" in path:
            return a2a_handler(method, url, headers, body, timeout)
        raise a2a.TransportFailure(f"unexpected {url}", error_kind="connection")

    return handler


def _status(
    rid: str,
    tid: str,
    state: str,
    *,
    role: str | None = None,
    text: str | None = None,
    extra_parts=None,
):
    status: dict[str, Any] = {"state": state}
    if role is not None:
        parts = list(extra_parts or [])
        if text is not None:
            parts.insert(0, {"kind": "text", "text": text})
        status["message"] = {"kind": "message", "role": role, "parts": parts, "messageId": "m1"}
    return {
        "jsonrpc": "2.0",
        "id": rid,
        "result": {
            "kind": "status-update",
            "taskId": tid,
            "final": state in {"completed", "failed"},
            "status": status,
        },
    }


def _tool_events(rid: str, tid: str, pod_names: list[str]):
    names_text = "\n".join(pod_names)
    return [
        _status(rid, tid, "submitted", role="user", text="List pods using k8s_get_resources"),
        _status(rid, tid, "working"),
        {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "kind": "status-update",
                "taskId": tid,
                "final": False,
                "status": {
                    "state": "working",
                    "message": {
                        "kind": "message",
                        "role": "agent",
                        "messageId": "m2",
                        "parts": [
                            {
                                "kind": "data",
                                "name": "k8s_get_resources",
                                "data": {
                                    "server": "kagent-tool-server",
                                    "tool": "k8s_get_resources",
                                    "arguments": {
                                        "resourceType": "pod",
                                        "namespace": "kagent",
                                    },
                                },
                            }
                        ],
                    },
                },
            },
        },
        _status(
            rid,
            tid,
            "completed",
            role="agent",
            text=f"Pods in kagent:\n{names_text}",
            extra_parts=[
                {
                    "kind": "functionCall",
                    "name": "k8s_get_resources",
                    "args": {"resource_type": "pod", "namespace": "kagent"},
                }
            ],
        ),
    ]


def _source_out(tmp_path: Path) -> Path:
    return tmp_path / "src.json"


def test_complete_correlated_evidence_passes(tmp_path: Path):
    pods = ["k8s-a2a-agent-abc", "kagent-controller-xyz"]

    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        return _sse(_tool_events(req["id"], "task-ok-1", pods))

    report = trace.run_trace(
        controller="http://127.0.0.1:8083",
        namespace="kagent",
        agent="k8s-a2a-agent",
        prompt="list",
        cluster_context="docker-desktop",
        source_out=_source_out(tmp_path),
        transport=FakeTransport(_router(a2a_handler)),
        kubectl_collector=lambda ns: pods,
        skip_logs=True,
    )
    assert report.exit_code == 0
    assert report.decision_passed is True
    assert report.tool_observed is True
    assert report.matched is True
    data = report.to_sanitized_dict()
    assert data["evidenceKind"] == "agent-mediated-mcp"
    assert data["toolInvocation"]["correlatedTaskOrMessageId"] == "task-ok-1"
    assert data["a2a"]["transport"] == {"succeeded": True, "httpStatus": 200}
    assert data["a2a"]["protocol"]["responseIdMatched"] is True
    assert data["a2a"]["dispatch"] == {
        "accepted": True,
        "taskOrMessageId": "task-ok-1",
        "state": "completed",
    }


def test_missing_tool_invocation_fails(tmp_path: Path):
    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        rid = req["id"]
        return _sse(
            [
                _status(rid, "task-2", "submitted", role="user", text="hello"),
                _status(rid, "task-2", "working"),
                _status(
                    rid,
                    "task-2",
                    "completed",
                    role="agent",
                    text="I listed pods without tools",
                ),
            ]
        )

    report = trace.run_trace(
        controller="http://127.0.0.1:8083",
        namespace="kagent",
        agent="k8s-a2a-agent",
        prompt="list",
        cluster_context="docker-desktop",
        source_out=_source_out(tmp_path),
        transport=FakeTransport(_router(a2a_handler)),
        kubectl_collector=lambda ns: ["k8s-a2a-agent-abc"],
        skip_logs=True,
    )
    assert report.exit_code == 1
    assert report.l4_accepted is True
    assert "no observable MCP tool" in report.reason


def test_model_prose_without_tool_fails(tmp_path: Path):
    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        rid = req["id"]
        return _sse(
            [
                _status(rid, "task-3", "submitted"),
                _status(
                    rid,
                    "task-3",
                    "completed",
                    role="agent",
                    text="I used k8s_get_resources and found k8s-a2a-agent-abc",
                ),
            ]
        )

    report = trace.run_trace(
        controller="http://127.0.0.1:8083",
        namespace="kagent",
        agent="k8s-a2a-agent",
        prompt="list",
        cluster_context="docker-desktop",
        source_out=_source_out(tmp_path),
        transport=FakeTransport(_router(a2a_handler)),
        kubectl_collector=lambda ns: ["k8s-a2a-agent-abc"],
        skip_logs=True,
    )
    # prose mentioning tool name without functionCall marker should fail observation
    assert report.exit_code == 1


def test_log_correlation_can_prove_tool(tmp_path: Path):
    pods = ["k8s-a2a-agent-abc"]

    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        rid = req["id"]
        # Stream has tool result names via agent text AND we also supply logs;
        # without functionCall, stream alone fails — logs provide observation,
        # but returnedThroughA2A still needs names from agent message.
        return _sse(
            [
                _status(rid, "task-log-1", "submitted"),
                _status(rid, "task-log-1", "working"),
                _status(
                    rid,
                    "task-log-1",
                    "completed",
                    role="agent",
                    text="Pods:\nk8s-a2a-agent-abc",
                ),
            ]
        )

    def logs(ns, deploy, tail):
        if deploy == "k8s-a2a-agent":
            return [
                (
                    '{"msg":"tool call","taskID":"task-log-1",'
                    '"tool":"k8s_get_resources","server":"kagent-tool-server",'
                    '"resourceType":"pod","namespace":"kagent"}'
                )
            ]
        return []

    report = trace.run_trace(
        controller="http://127.0.0.1:8083",
        namespace="kagent",
        agent="k8s-a2a-agent",
        prompt="list",
        cluster_context="docker-desktop",
        source_out=_source_out(tmp_path),
        transport=FakeTransport(_router(a2a_handler)),
        log_collector=logs,
        kubectl_collector=lambda ns: pods,
        skip_logs=False,
    )
    assert report.tool_observed is True
    assert report.exit_code == 0


def test_cross_check_mismatch_fails(tmp_path: Path):
    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        return _sse(_tool_events(req["id"], "task-x", ["missing-pod-name-zzz"]))

    report = trace.run_trace(
        controller="http://127.0.0.1:8083",
        namespace="kagent",
        agent="k8s-a2a-agent",
        prompt="list",
        cluster_context="docker-desktop",
        source_out=_source_out(tmp_path),
        transport=FakeTransport(_router(a2a_handler)),
        kubectl_collector=lambda ns: ["k8s-a2a-agent-abc"],
        skip_logs=True,
    )
    assert report.exit_code == 1
    assert "cross-check" in report.reason


def test_transport_failure_exit_3(tmp_path: Path):
    def handler(method, url, headers, body, timeout):
        raise a2a.TransportFailure("connection refused", error_kind="connection")

    report = trace.run_trace(
        controller="http://127.0.0.1:8083",
        namespace="kagent",
        agent="k8s-a2a-agent",
        prompt="list",
        cluster_context="docker-desktop",
        source_out=_source_out(tmp_path),
        transport=FakeTransport(handler),
        kubectl_collector=lambda ns: [],
        skip_logs=True,
    )
    assert report.exit_code == 3


def test_task_id_mismatch_in_logs_ignored(tmp_path: Path):
    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        rid = req["id"]
        return _sse(
            [
                _status(rid, "task-a", "submitted"),
                _status(rid, "task-a", "completed", role="agent", text="done"),
            ]
        )

    def logs(ns, deploy, tail):
        return ['{"taskID":"other-task","tool":"k8s_get_resources"}']

    report = trace.run_trace(
        controller="http://127.0.0.1:8083",
        namespace="kagent",
        agent="k8s-a2a-agent",
        prompt="list",
        cluster_context="docker-desktop",
        source_out=_source_out(tmp_path),
        transport=FakeTransport(_router(a2a_handler)),
        log_collector=logs,
        kubectl_collector=lambda ns: ["k8s-a2a-agent-abc"],
        skip_logs=False,
    )
    assert report.exit_code == 1
    assert report.tool_observed is False


def test_json_output_no_secrets(tmp_path: Path, capsys):
    pods = ["k8s-a2a-agent-abc"]

    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        return _sse(_tool_events(req["id"], "task-sec", pods))

    report = trace.run_trace(
        controller="http://127.0.0.1:8083",
        namespace="kagent",
        agent="k8s-a2a-agent",
        prompt="list",
        cluster_context="docker-desktop",
        source_out=_source_out(tmp_path),
        transport=FakeTransport(_router(a2a_handler)),
        kubectl_collector=lambda ns: pods,
        skip_logs=True,
    )
    print(json.dumps(report.to_sanitized_dict()))
    out = capsys.readouterr().out.lower()
    assert "authorization" not in out
    assert "bearer " not in out


def test_l4_without_tool_keeps_l4_flag(tmp_path: Path):
    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        rid = req["id"]
        return _sse(
            [
                _status(rid, "task-l4", "submitted"),
                _status(rid, "task-l4", "working"),
                _status(rid, "task-l4", "failed", role="agent", text="quota exceeded"),
            ]
        )

    report = trace.run_trace(
        controller="http://127.0.0.1:8083",
        namespace="kagent",
        agent="k8s-a2a-agent",
        prompt="list",
        cluster_context="docker-desktop",
        source_out=_source_out(tmp_path),
        transport=FakeTransport(_router(a2a_handler)),
        kubectl_collector=lambda ns: ["k8s-a2a-agent-abc"],
        skip_logs=True,
    )
    assert report.l4_accepted is True
    assert report.exit_code == 1
    assert report.decision_passed is False


def test_names_match_helper():
    assert trace.names_match(["a-pod-1"], ["a-pod-1", "b-pod-2"]) is True
    assert trace.names_match(["missing-x"], ["a-pod-1"]) is False
    assert trace.names_match([], ["a-pod-1"]) is False


def test_protocol_marker_requires_exact_task_role_server_and_arguments():
    rid = "req-strict"
    valid = _tool_events(rid, "task-good", ["k8s-a2a-agent-abc"])[2]
    candidates = [
        # Missing task identity.
        {**valid, "result": {**valid["result"], "taskId": ""}},
        # User-supplied structured data is not agent/tool/model evidence.
        _status(
            rid,
            "task-good",
            "working",
            role="user",
            extra_parts=valid["result"]["status"]["message"]["parts"],
        ),
    ]
    wrong_server = json.loads(json.dumps(valid))
    wrong_server["result"]["status"]["message"]["parts"][0]["data"]["server"] = "other"
    candidates.append(wrong_server)
    wrong_args = json.loads(json.dumps(valid))
    wrong_args["result"]["status"]["message"]["parts"][0]["data"]["arguments"] = {
        "resourceType": "deployment",
        "namespace": "default",
    }
    candidates.append(wrong_args)

    observed, reference, names, proof = trace.scan_events_for_tool(
        candidates,
        task_id="task-good",
        expected_tool="k8s_get_resources",
        expected_server="kagent-tool-server",
    )
    assert (observed, reference, names, proof) == (False, None, [], None)


def test_names_before_protocol_marker_are_not_attributed(tmp_path: Path):
    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        events = _tool_events(req["id"], "task-order", [])
        events.insert(
            1,
            _status(
                req["id"],
                "task-order",
                "working",
                role="agent",
                text="Pods: k8s-a2a-agent-abc",
            ),
        )
        return _sse(events)

    report = trace.run_trace(
        controller="http://127.0.0.1:8083",
        namespace="kagent",
        agent="k8s-a2a-agent",
        prompt="list",
        cluster_context="docker-desktop",
        source_out=_source_out(tmp_path),
        transport=FakeTransport(_router(a2a_handler)),
        kubectl_collector=lambda ns: ["k8s-a2a-agent-abc"],
        skip_logs=True,
    )
    assert report.tool_observed is True
    assert report.returned_through_a2a is False
    assert report.exit_code == 1


def test_names_in_earlier_part_of_marker_event_are_not_attributed():
    event = _tool_events("req-parts", "task-parts", [])[2]
    event["result"]["status"]["message"]["parts"].insert(
        0,
        {"kind": "text", "text": "Pods: k8s-a2a-agent-abc"},
    )
    observed, _, names, proof = trace.scan_events_for_tool(
        [event],
        task_id="task-parts",
        expected_tool="k8s_get_resources",
        expected_server="kagent-tool-server",
    )
    assert observed is True
    assert proof["partIndex"] == 1
    assert names == []


def test_source_capture_contains_bounded_structured_protocol_proof(tmp_path: Path):
    pods = ["k8s-a2a-agent-abc"]

    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        return _sse(_tool_events(req["id"], "task-proof", pods))

    source = _source_out(tmp_path)
    report = trace.run_trace(
        controller="http://127.0.0.1:8083",
        namespace="kagent",
        agent="k8s-a2a-agent",
        prompt="list",
        cluster_context="docker-desktop",
        source_out=source,
        transport=FakeTransport(_router(a2a_handler)),
        kubectl_collector=lambda ns: pods,
        skip_logs=True,
    )
    captured = json.loads(source.read_text(encoding="utf-8"))
    assert report.exit_code == 0
    assert captured["toolEvidence"]["taskOrMessageId"] == "task-proof"
    assert captured["toolEvidence"]["eventIndex"] == 2
    assert captured["toolEvidence"]["partIndex"] == 0
    assert captured["toolEvidence"]["argumentsSummary"] == {
        "resourceType": "pod",
        "namespace": "kagent",
    }
    assert "authorization" not in json.dumps(captured).lower()


def test_both_log_collectors_unavailable_exit_3(tmp_path: Path):
    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        return _sse(
            [
                _status(req["id"], "task-log-fail", "submitted"),
                _status(req["id"], "task-log-fail", "working"),
            ]
        )

    def failed_logs(ns, deploy, tail):
        raise a2a.TransportFailure(f"{deploy} unavailable", error_kind="connection")

    report = trace.run_trace(
        controller="http://127.0.0.1:8083",
        namespace="kagent",
        agent="k8s-a2a-agent",
        prompt="list",
        cluster_context="docker-desktop",
        source_out=_source_out(tmp_path),
        transport=FakeTransport(_router(a2a_handler)),
        log_collector=failed_logs,
        kubectl_collector=lambda ns: [],
        skip_logs=False,
    )
    assert report.exit_code == 3
    assert len(report.log_searches) == 2
    assert all(item["succeeded"] is False for item in report.log_searches)


def test_successful_log_search_without_marker_remains_gate_failure(tmp_path: Path):
    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        return _sse(
            [
                _status(req["id"], "task-no-marker", "submitted"),
                _status(req["id"], "task-no-marker", "working"),
            ]
        )

    report = trace.run_trace(
        controller="http://127.0.0.1:8083",
        namespace="kagent",
        agent="k8s-a2a-agent",
        prompt="list",
        cluster_context="docker-desktop",
        source_out=_source_out(tmp_path),
        transport=FakeTransport(_router(a2a_handler)),
        log_collector=lambda ns, deploy, tail: ["bounded search completed"],
        kubectl_collector=lambda ns: [],
        skip_logs=False,
    )
    assert report.exit_code == 1
    assert report.tool_observed is False
    assert len(report.log_searches) == 2
    assert all(item["succeeded"] is True for item in report.log_searches)


def test_actual_kubernetes_context_must_be_docker_desktop(tmp_path: Path):
    pods = ["k8s-a2a-agent-abc"]

    def a2a_handler(method, url, headers, body, timeout):
        req = json.loads(body.decode())
        return _sse(_tool_events(req["id"], "task-context", pods))

    report = trace.run_trace(
        controller="http://127.0.0.1:8083",
        namespace="kagent",
        agent="k8s-a2a-agent",
        prompt="list",
        cluster_context="docker-desktop",
        source_out=_source_out(tmp_path),
        transport=FakeTransport(_router(a2a_handler)),
        kubectl_collector=lambda ns: pods,
        context_collector=lambda: "other-context",
        skip_logs=True,
    )
    assert report.exit_code == 1
    assert report.target_bound is False
    assert "target binding" in report.reason
