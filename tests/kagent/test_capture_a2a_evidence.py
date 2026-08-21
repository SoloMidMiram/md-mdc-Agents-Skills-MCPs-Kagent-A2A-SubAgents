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


def _status(msg_parts: list[dict], state: str | None = None) -> dict:
    part = {
        "jsonrpc": "2.0",
        "id": "req1",
        "result": {
            "kind": "status-update",
            "taskId": "task1",
            "status": {"state": state, "message": {"parts": msg_parts}},
        },
    }
    return part


def _artifact(texts: list[str]) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": "req1",
        "result": {
            "kind": "artifact-update",
            "artifact": {"parts": [{"kind": "text", "text": t} for t in texts]},
        },
    }


def _call(data: dict) -> dict:
    return {"kind": "data", "data": data}


def _completed_with_pair(final_text: str) -> list[dict]:
    return [
        _status([{"kind": "text", "text": "I'll check."}], state="working"),
        _status(
            [
                _call(
                    {
                        "id": CALL_ID,
                        "name": "k8s_get_resources",
                        "args": {"namespace": "kagent"},
                    }
                )
            ],
            state="working",
        ),
        _status(
            [
                _call(
                    {
                        "id": CALL_ID,
                        "name": "k8s_get_resources",
                        "response": {"output": "NAME  READY\npod-1  1/1"},
                    }
                )
            ],
            state="working",
        ),
        _artifact([final_text]),
        _status([], state="completed"),
    ]


def test_passes_when_completed_with_exact_call_result_pair() -> None:
    summary = MODULE.summarize_events(_completed_with_pair("There are 1 pods."), PROMPT)
    assert summary["matched_tool_pairs"] == 1
    assert summary["passed"] is True


def test_fails_closed_on_completion_without_tool_result() -> None:
    events = [
        _status([{"kind": "text", "text": "I'll check."}], state="working"),
        # A tool call is present but no correlated result with a matching id.
        _status(
            [
                _call(
                    {
                        "id": CALL_ID,
                        "name": "k8s_get_resources",
                        "args": {"namespace": "kagent"},
                    }
                )
            ],
            state="working",
        ),
        _artifact(["There are 1 pods."]),
        _status([], state="completed"),
    ]
    summary = MODULE.summarize_events(events, PROMPT)
    assert summary["matched_tool_pairs"] == 0
    assert summary["passed"] is False


def test_fails_closed_when_no_tool_call_at_all() -> None:
    events = [
        _status([{"kind": "text", "text": "No tool here."}], state="working"),
        _artifact(["Done."]),
        _status([], state="completed"),
    ]
    summary = MODULE.summarize_events(events, PROMPT)
    assert summary["tool_mentioned_in_stream"] is False
    assert summary["passed"] is False


def test_fails_closed_on_mismatched_call_result_ids() -> None:
    events = [
        _status(
            [
                _call(
                    {
                        "id": "call_aaaa",
                        "name": "k8s_get_resources",
                        "args": {"namespace": "kagent"},
                    }
                )
            ],
            state="working",
        ),
        _status(
            [
                _call(
                    {
                        "id": "call_bbbb",
                        "name": "k8s_get_resources",
                        "response": {"output": "NAME  READY\npod-1  1/1"},
                    }
                )
            ],
            state="working",
        ),
        _artifact(["There are 1 pods."]),
        _status([], state="completed"),
    ]
    summary = MODULE.summarize_events(events, PROMPT)
    assert summary["matched_tool_pairs"] == 0
    assert summary["passed"] is False


def test_fails_closed_when_stream_not_completed() -> None:
    events = [
        _status(
            [
                _call(
                    {
                        "id": CALL_ID,
                        "name": "k8s_get_resources",
                        "args": {"namespace": "kagent"},
                    }
                )
            ],
            state="working",
        ),
        _status(
            [
                _call(
                    {
                        "id": CALL_ID,
                        "name": "k8s_get_resources",
                        "response": {"output": "NAME  READY\npod-1  1/1"},
                    }
                )
            ],
            state="working",
        ),
        _artifact(["partial result"]),
    ]
    summary = MODULE.summarize_events(events, PROMPT)
    assert summary["final_state"] == "working"
    assert summary["passed"] is False
