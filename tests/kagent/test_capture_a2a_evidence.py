"""Deterministic tests for the fail-closed tool-loop evidence gate."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/kagent/capture-a2a-evidence.py"
SPEC = importlib.util.spec_from_file_location("capture_a2a_evidence", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
sys.modules[MODULE.__name__] = MODULE

PROMPT = "List pods using k8s_get_resources and summarize."

CALL_ID = "call_00_testmatch"
GOOD_ARGS = {"namespace": "kagent", "resource_type": "pod"}
WRONG_ARGS = {"namespace": "kagent", "resource_type": "deployment"}


def _status(msg_parts: list[dict], state: str | None = None, task_id: str = "task1") -> dict:
    return {
        "jsonrpc": "2.0",
        "id": "req1",
        "result": {
            "kind": "status-update",
            "taskId": task_id,
            "status": {"state": state, "message": {"parts": msg_parts}},
        },
    }


def _artifact(texts: list[str], task_id: str = "task1") -> dict:
    return {
        "jsonrpc": "2.0",
        "id": "req1",
        "result": {
            "kind": "artifact-update",
            "taskId": task_id,
            "artifact": {"parts": [{"kind": "text", "text": t} for t in texts]},
        },
    }


def _call(data: dict) -> dict:
    return {"kind": "data", "data": data}


def _tool_call(
    call_id: str = CALL_ID,
    *,
    name: str = "k8s_get_resources",
    args: dict | None = None,
) -> dict:
    if args is None:
        args = GOOD_ARGS
    return _call({"id": call_id, "name": name, "args": args})


def _tool_result(
    call_id: str = CALL_ID,
    *,
    name: str = "k8s_get_resources",
    output: str = "NAME  READY\npod-1  1/1",
) -> dict:
    return _call({"id": call_id, "name": name, "response": {"output": output}})


def _completed_with_pair(final_text: str) -> list[dict]:
    return [
        _status([{"kind": "text", "text": "I'll check."}], state="working"),
        _status([_tool_call()], state="working"),
        _status([_tool_result()], state="working"),
        _artifact([final_text]),
        _status([], state="completed"),
    ]


def test_passes_when_completed_with_exact_call_result_pair() -> None:
    summary = MODULE.summarize_events(
        _completed_with_pair("There are 1 pods."), PROMPT, request_id="req1"
    )
    assert summary["matched_tool_pairs"] == 1
    assert summary["passed"] is True


def test_fails_closed_on_completion_without_tool_result() -> None:
    events = [
        _status([{"kind": "text", "text": "I'll check."}], state="working"),
        # A tool call is present but no correlated result with a matching id.
        _status([_tool_call()], state="working"),
        _artifact(["There are 1 pods."]),
        _status([], state="completed"),
    ]
    summary = MODULE.summarize_events(events, PROMPT, request_id="req1")
    assert summary["matched_tool_pairs"] == 0
    assert summary["passed"] is False


def test_fails_closed_when_no_tool_call_at_all() -> None:
    events = [
        _status([{"kind": "text", "text": "No tool here."}], state="working"),
        _artifact(["Done."]),
        _status([], state="completed"),
    ]
    summary = MODULE.summarize_events(events, PROMPT, request_id="req1")
    assert summary["tool_mentioned_in_stream"] is False
    assert summary["passed"] is False


def test_fails_closed_when_tool_name_only_in_text() -> None:
    events = [
        _status(
            [{"kind": "text", "text": "I used k8s_get_resources earlier."}],
            state="working",
        ),
        _artifact(["Done."]),
        _status([], state="completed"),
    ]
    summary = MODULE.summarize_events(events, PROMPT, request_id="req1")
    assert summary["tool_mentioned_in_stream"] is False
    assert summary["matched_tool_pairs"] == 0
    assert summary["passed"] is False


def test_fails_closed_on_mismatched_call_result_ids() -> None:
    events = [
        _status([_tool_call(call_id="call_aaaa")], state="working"),
        _status([_tool_result(call_id="call_bbbb")], state="working"),
        _artifact(["There are 1 pods."]),
        _status([], state="completed"),
    ]
    summary = MODULE.summarize_events(events, PROMPT, request_id="req1")
    assert summary["matched_tool_pairs"] == 0
    assert summary["passed"] is False


def test_fails_closed_when_tool_name_wrong() -> None:
    events = [
        _status([_tool_call(name="k8s_apply_manifest")], state="working"),
        _status([_tool_result()], state="working"),
        _artifact(["There are 1 pods."]),
        _status([], state="completed"),
    ]
    summary = MODULE.summarize_events(events, PROMPT, request_id="req1")
    assert summary["matched_tool_pairs"] == 0
    assert summary["passed"] is False


def test_fails_closed_when_arguments_wrong() -> None:
    events = [
        _status([_tool_call(args=WRONG_ARGS)], state="working"),
        _status([_tool_result()], state="working"),
        _artifact(["There are 1 pods."]),
        _status([], state="completed"),
    ]
    summary = MODULE.summarize_events(events, PROMPT, request_id="req1")
    assert summary["matched_tool_pairs"] == 0
    assert summary["passed"] is False


def test_fails_closed_when_tool_result_empty() -> None:
    events = [
        _status([_tool_call()], state="working"),
        _status([_tool_result(output="")], state="working"),
        _artifact(["There are 1 pods."]),
        _status([], state="completed"),
    ]
    summary = MODULE.summarize_events(events, PROMPT, request_id="req1")
    assert summary["matched_tool_pairs"] == 0
    assert summary["passed"] is False


def test_fails_closed_when_task_id_missing() -> None:
    events = [
        _status([_tool_call()], state="working", task_id=""),
        _status([_tool_result()], state="working", task_id=""),
        _artifact(["There are 1 pods."], task_id=""),
        _status([], state="completed", task_id=""),
    ]
    summary = MODULE.summarize_events(events, PROMPT, request_id="req1")
    assert not summary["task_id"]
    assert summary["passed"] is False


def test_fails_closed_when_stream_not_completed() -> None:
    events = [
        _status([_tool_call()], state="working"),
        _status([_tool_result()], state="working"),
        _artifact(["partial result"]),
    ]
    summary = MODULE.summarize_events(events, PROMPT, request_id="req1")
    assert summary["final_state"] == "working"
    assert summary["passed"] is False


def test_completion_cannot_borrow_tool_pair_from_another_task():
    events = _completed_with_pair("There are 1 pods.")
    events[-1]["result"]["taskId"] = "other-task"
    assert MODULE.summarize_events(events, PROMPT, request_id="req1")["passed"] is False


def test_working_commentary_cannot_substitute_for_final_answer():
    events = _completed_with_pair("There are 1 pods.")
    del events[-2]
    assert MODULE.summarize_events(events, PROMPT, request_id="req1")["passed"] is False


def test_foreign_request_id_fails_closed():
    events = _completed_with_pair("There are 1 pods.")
    events[-1]["id"] = "other-request"
    assert MODULE.summarize_events(events, PROMPT, request_id="req1")["passed"] is False


def test_capture_writes_full_answer_and_keeps_bounded_preview(monkeypatch, tmp_path):
    import io
    import json

    answer = "x" * 600 + " end"

    class Response(io.BytesIO):
        status = 200

    def urlopen(request, **kwargs):
        request_id = json.loads(request.data)["id"]
        events = _completed_with_pair(answer)
        for event in events:
            event["id"] = request_id
        return Response("".join(f"data: {json.dumps(e)}\n\n" for e in events).encode())

    monkeypatch.setattr(MODULE.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(
        sys, "argv", ["capture", "--agent", "agent", "--prompt", PROMPT, "--out-dir", str(tmp_path)]
    )
    assert MODULE.main() == 0
    assert answer in (tmp_path / "final-answer.md").read_text(encoding="utf-8")
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["final_answer_preview"] == answer[:500]
    assert answer not in json.dumps(summary)


def test_capture_assembles_artifact_replacement_and_append():
    events = _completed_with_pair("stale")
    first, replacement, append = [
        _artifact([text]) for text in ("stale", "Pods: ", "pod-1 is ready.")
    ]
    for event in (first, replacement, append):
        event["result"]["artifact"]["artifactId"] = "answer"
    append["result"]["append"] = True
    events[-2:-1] = [first, replacement, append]
    summary = MODULE.summarize_events(events, PROMPT, request_id="req1")
    assert summary["passed"]
    assert summary["final_answer"] == "Pods: pod-1 is ready."
