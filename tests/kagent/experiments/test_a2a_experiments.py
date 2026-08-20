"""Deterministic tests for Lane A kagent A2A experiment harness."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

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
        '{"goal":"g","constraints":[],"files":[],"acceptance_criteria":[],'
        '"tests":[],"risks":[]}'
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
