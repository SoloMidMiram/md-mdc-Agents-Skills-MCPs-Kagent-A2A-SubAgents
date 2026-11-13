"""Deterministic tests for Lane A kagent A2A experiment harness."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
EXPERIMENTS = ROOT / "scripts" / "kagent" / "experiments"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


contracts = _load_module("kagent_experiment_contracts_test", EXPERIMENTS / "contracts.py")
run_example = _load_module("kagent_run_a2a_example_test", EXPERIMENTS / "run_a2a_example.py")
record_experiment = _load_module(
    "kagent_record_experiment_test", EXPERIMENTS / "record_experiment.py"
)


def test_validate_planner_artifact_accepts_minimal() -> None:
    artifact = {
        "goal": "Build a hello-world bot",
        "constraints": [],
        "files": ["bot.py"],
        "acceptance_criteria": ["responds to /start"],
        "tests": ["pytest"],
        "risks": [],
    }
    assert contracts.validate_planner_artifact(artifact)["goal"] == "Build a hello-world bot"


def test_validate_planner_artifact_rejects_missing_key() -> None:
    with pytest.raises(contracts.ContractError, match="missing keys"):
        contracts.validate_planner_artifact({"goal": "x"})


def test_validate_reviewer_artifact_accepts_approve() -> None:
    artifact = {
        "verdict": "approve",
        "findings": [],
        "missing_requirements": [],
        "required_changes": [],
    }
    assert contracts.validate_reviewer_artifact(artifact)["verdict"] == "approve"


def test_validate_reviewer_artifact_rejects_bad_verdict() -> None:
    with pytest.raises(contracts.ContractError, match="verdict"):
        contracts.validate_reviewer_artifact(
            {
                "verdict": "maybe",
                "findings": [],
                "missing_requirements": [],
                "required_changes": [],
            }
        )


def test_extract_json_object_from_markdown_fence() -> None:
    inner = (
        '{"goal":"g","constraints":[],"files":[],"acceptance_criteria":[],"tests":[],"risks":[]}'
    )
    text = f"Here is the plan:\n```json\n{inner}\n```"
    obj = contracts.extract_json_object(text)
    assert obj["goal"] == "g"


def test_example_id_mapping() -> None:
    assert run_example._example_id_for_agent("planner-agent") == "e1-planner"
    assert run_example._example_id_for_agent("supervisor-agent") == "e2-supervisor"


def test_record_experiment_builds_sanitized_record(tmp_path: Path) -> None:
    payload = {
        "example": "e1-planner",
        "agents": ["planner-agent"],
        "taskId": "task-1",
        "durationMs": 42,
        "pass": True,
        "schemaVersion": "1.1",
        "observedAt": "2026-10-22T12:00:00Z",
        "requestId": "request-1",
        "dispatchState": "completed",
        "reason": "completed with validated artifact",
        "card": {"accepted": True, "deploymentReady": True},
        "artifact": {
            "goal": "hello",
            "constraints": [],
            "files": [],
            "acceptance_criteria": [],
            "tests": [],
            "risks": [],
        },
        "artifactSummary": {"goal": "hello"},
        "nonClaims": ["L6"],
        "target": {
            "controller": "http://127.0.0.1:8083",
            "namespace": "kagent",
            "agent": "planner-agent",
        },
    }
    record = record_experiment.build_record(
        payload, cleanup=["kubectl delete -f x.yaml"], notes="smoke"
    )
    assert record["example"] == "e1-planner"
    assert record["taskId"] == "task-1"
    assert record["cleanup"] == ["kubectl delete -f x.yaml"]
    out = tmp_path / "out.json"
    out.write_text(json.dumps(record), encoding="utf-8")
    assert json.loads(out.read_text(encoding="utf-8"))["pass"] is True


@pytest.fixture
def evidence_payload() -> dict:
    return {
        "schemaVersion": "1.1",
        "observedAt": "2026-10-22T12:00:00Z",
        "example": "e1-planner",
        "agents": ["planner-agent"],
        "target": {
            "controller": "http://127.0.0.1:8083",
            "namespace": "kagent",
            "agent": "planner-agent",
        },
        "taskId": "task-1",
        "requestId": "request-1",
        "durationMs": 42,
        "dispatchState": "completed",
        "pass": True,
        "reason": "completed",
        "card": {"accepted": True, "deploymentReady": True},
        "artifact": {
            "goal": "hello",
            "constraints": [],
            "files": [],
            "acceptance_criteria": [],
            "tests": [],
            "risks": [],
        },
        "artifactSummary": {"goal": "hello"},
        "nonClaims": ["L6", "I3", "I4", "L7"],
    }


@pytest.mark.parametrize("task_id", [None, "", " ", 4])
def test_recorder_rejects_success_without_task_id(evidence_payload: dict, task_id) -> None:
    evidence_payload["taskId"] = task_id
    with pytest.raises(ValueError):
        record_experiment.build_record(evidence_payload, cleanup=[], notes="")


@pytest.mark.parametrize("value", ["true", "yes", 1, 0, None, [], {}])
def test_recorder_rejects_invalid_success_types(evidence_payload: dict, value) -> None:
    evidence_payload["pass"] = value
    with pytest.raises(ValueError):
        record_experiment.build_record(evidence_payload, cleanup=[], notes="")


@pytest.mark.parametrize(
    "state", [None, "working", "submitted", "input_required", "failed", "canceled", "rejected"]
)
def test_recorder_rejects_incomplete_success(evidence_payload: dict, state) -> None:
    evidence_payload["dispatchState"] = state
    with pytest.raises(ValueError):
        record_experiment.build_record(evidence_payload, cleanup=[], notes="")


@pytest.mark.parametrize("field", ["artifact", "requestId", "observedAt", "card"])
def test_recorder_rejects_missing_success_proof(evidence_payload: dict, field: str) -> None:
    del evidence_payload[field]
    with pytest.raises(ValueError):
        record_experiment.build_record(evidence_payload, cleanup=[], notes="")


def test_recorder_can_record_genuine_failure(evidence_payload: dict) -> None:
    evidence_payload.update(
        {
            "pass": False,
            "taskId": None,
            "requestId": None,
            "dispatchState": None,
            "artifact": None,
            "reason": "controller unavailable",
        }
    )
    record = record_experiment.build_record(evidence_payload, cleanup=[], notes="")
    assert record["pass"] is False
    assert record["acceptance"]["passed"] is False
    assert record["observation"]["observedAt"] == evidence_payload["observedAt"]


@pytest.mark.parametrize(
    "example",
    ["custom", "../../outside", "x/../../escape", "..\\escape", "/absolute", "C:\\escape", ""],
)
def test_recorder_rejects_arbitrary_example_identifiers(evidence_payload: dict, example) -> None:
    evidence_payload["example"] = example
    with pytest.raises(ValueError):
        record_experiment.build_record(evidence_payload, cleanup=[], notes="")


def test_recorder_sanitizes_retained_evidence(evidence_payload: dict) -> None:
    evidence_payload["artifactSummary"] = {"api_key": "secret-summary"}
    evidence_payload["artifact"]["goal"] = "token=secret-goal"
    evidence_payload["target"]["controller"] = (
        "http://user:secret-password@localhost:8083/?key=secret-query"
    )
    record = record_experiment.build_record(
        evidence_payload,
        cleanup=["TOKEN=secret-cleanup"],
        notes="Authorization: Bearer secret-note",
    )
    encoded = json.dumps(record)
    for secret in [
        "secret-summary",
        "secret-goal",
        "secret-password",
        "secret-query",
        "secret-cleanup",
        "secret-note",
    ]:
        assert secret not in encoded


def test_same_day_records_do_not_overwrite(evidence_payload: dict, tmp_path: Path) -> None:
    source = tmp_path / "input.json"
    source.write_text(json.dumps(evidence_payload), encoding="utf-8")
    dest = tmp_path / "records"
    args = ["--input", str(source), "--output-dir", str(dest)]
    assert record_experiment.main(args) == 0
    first = {p.name: p.read_bytes() for p in dest.glob("*.json")}
    assert record_experiment.main(args) == 0
    assert len(list(dest.glob("*.json"))) == 2
    assert all((dest / name).read_bytes() == content for name, content in first.items())


def test_supervisor_requires_complete_composite() -> None:
    with pytest.raises(ValueError):
        contracts.validate_supervisor_artifact({"summary": "no delegation"})


@pytest.mark.parametrize("request_id,task_id", [("wrong", "task-1"), ("tasks-get-poll", "wrong")])
def test_poll_rejects_mismatched_ids(request_id: str, task_id: str) -> None:
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {"id": task_id, "status": {"state": "completed"}},
    }
    transport = SimpleNamespace(
        request=lambda *a, **k: SimpleNamespace(status=200, body=json.dumps(payload).encode())
    )
    with pytest.raises(run_example.a2a.GateError):
        run_example.poll_task_until_terminal(transport, "http://unused", "task-1", timeout=1)


def test_poll_timeout_cannot_return_nonterminal_success(monkeypatch) -> None:
    ticks = iter([0.0, 0.0, 2.0])
    monkeypatch.setattr(run_example.time, "perf_counter", lambda: next(ticks, 2.0))
    monkeypatch.setattr(run_example.time, "sleep", lambda _: None)
    payload = {
        "jsonrpc": "2.0",
        "id": "tasks-get-poll",
        "result": {"id": "task-1", "status": {"state": "working"}},
    }
    transport = SimpleNamespace(
        request=lambda *a, **k: SimpleNamespace(status=200, body=json.dumps(payload).encode())
    )
    with pytest.raises(run_example.a2a.GateError):
        run_example.poll_task_until_terminal(transport, "http://unused", "task-1", timeout=1)


@pytest.mark.parametrize(
    "state", ["canceled", "cancelled", "rejected", "working", "input_required"]
)
def test_run_rejects_noncompleted_artifacts(
    monkeypatch, evidence_payload: dict, state: str
) -> None:
    monkeypatch.setattr(
        run_example.a2a,
        "run_card",
        lambda *a: SimpleNamespace(
            card_accepted=True, card_deployment_ready=True, decision_passed=True
        ),
    )
    monkeypatch.setattr(run_example.a2a, "collect_dispatch_stream", lambda *a, **k: ("r", 200, []))
    monkeypatch.setattr(
        run_example.a2a,
        "select_dispatch_from_events",
        lambda *a: ("task-1", "working", "status-update"),
    )
    monkeypatch.setattr(
        run_example,
        "poll_task_until_terminal",
        lambda *a, **k: {
            "id": "task-1",
            "status": {
                "state": state,
                "message": {
                    "role": "agent",
                    "parts": [{"text": json.dumps(evidence_payload["artifact"])}],
                },
            },
        },
    )
    result = run_example.run_example(
        agent="planner-agent",
        prompt="test",
        controller="http://localhost:8083",
        namespace="kagent",
        example=None,
        timeout=1,
        skip_contract=False,
    )
    assert result.pass_ is False


def test_response_fallback_does_not_use_other_task_text() -> None:
    events = [
        {
            "result": {
                "taskId": "wrong",
                "status": {
                    "state": "working",
                    "message": {"role": "agent", "parts": [{"text": "wrong output"}]},
                },
            }
        }
    ]
    assert run_example.extract_response_text(events, "expected") == ""


@pytest.mark.parametrize(
    "variant", ["valid", "mixed_task", "wrong_request", "failed_stream", "skip"]
)
def test_run_correlates_stream_poll_and_artifact(monkeypatch, evidence_payload: dict, variant: str):
    event = {
        "jsonrpc": "2.0",
        "id": "request-1",
        "result": {"kind": "status-update", "taskId": "task-1", "status": {"state": "working"}},
    }
    events = [event]
    if variant == "mixed_task":
        events.append(
            {
                "jsonrpc": "2.0",
                "id": "request-1",
                "result": {
                    "kind": "status-update",
                    "taskId": "task-2",
                    "status": {"state": "completed"},
                },
            }
        )
    if variant == "wrong_request":
        event["id"] = "other-request"
    if variant == "failed_stream":
        events.append(
            {
                "jsonrpc": "2.0",
                "id": "request-1",
                "result": {
                    "kind": "status-update",
                    "taskId": "task-1",
                    "status": {"state": "failed"},
                },
            }
        )
    terminal = {
        "jsonrpc": "2.0",
        "id": "tasks-get-poll",
        "result": {
            "id": "task-1",
            "status": {
                "state": "completed",
                "message": {
                    "role": "agent",
                    "parts": [{"text": json.dumps(evidence_payload["artifact"])}],
                },
            },
        },
    }
    transport = SimpleNamespace(
        request=lambda *a, **k: SimpleNamespace(status=200, body=json.dumps(terminal).encode())
    )
    monkeypatch.setattr(run_example.a2a, "DirectUrlTransport", lambda: transport)
    monkeypatch.setattr(
        run_example.a2a,
        "run_card",
        lambda *a: SimpleNamespace(
            card_accepted=True, card_deployment_ready=True, decision_passed=True
        ),
    )
    monkeypatch.setattr(
        run_example.a2a, "collect_dispatch_stream", lambda *a, **k: ("request-1", 200, events)
    )
    result = run_example.run_example(
        agent="planner-agent",
        prompt="test",
        controller="http://localhost:8083",
        namespace="kagent",
        example=None,
        timeout=1,
        skip_contract=variant == "skip",
    )
    assert result.pass_ is (variant == "valid")
    if variant == "valid":
        record = record_experiment.build_record(result.to_dict(), cleanup=[], notes="")
        assert record["acceptance"]["passed"] is True
        assert record["observation"]["requestId"] == "request-1"


@pytest.mark.parametrize(
    "artifact",
    [None, [], {"summary": "x"}, {"summary": "x", "plan": [], "review": {}, "verdict": []}],
)
def test_supervisor_malformed_shapes_raise_contract_error(artifact) -> None:
    with pytest.raises(ValueError):
        contracts.validate_supervisor_artifact(artifact)


def test_record_io_collision_fails_without_overwriting(monkeypatch, evidence_payload, tmp_path):
    monkeypatch.setattr(record_experiment, "uuid4", lambda: SimpleNamespace(hex="fixed"))
    source = tmp_path / "input.json"
    source.write_text(json.dumps(evidence_payload), encoding="utf-8")
    dest = tmp_path / "records"
    args = ["--input", str(source), "--output-dir", str(dest)]
    assert record_experiment.main(args) == 0
    first = next(dest.glob("*.json"))
    content = first.read_bytes()
    assert record_experiment.main(args) == 2
    assert first.read_bytes() == content


def test_artifact_only_task_and_retained_stream():
    raw = (ROOT / "evidence/a2a/run001/raw-sse.txt").read_text(encoding="utf-8")
    events = run_example.a2a.parse_sse_jsonrpc_events(raw)
    update = next(e["result"] for e in events if e["result"]["kind"] == "artifact-update")
    text = run_example.extract_response_text(events, update["taskId"])
    assert contracts.validate_artifact("supervisor-agent", text)
    task = {"status": {"state": "completed"}, "artifacts": [update["artifact"]]}
    assert run_example.extract_text_from_task(task) == ("completed", text)
