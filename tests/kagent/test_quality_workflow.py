"""Require complete, isolated SDK CI coverage and reject skipped qualifications."""

from __future__ import annotations

import copy
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = yaml.safe_load((ROOT / ".github/workflows/quality.yml").read_text())
# Discover against the repository even when pytest is launched from another cwd.
SDK_MODULES = {
    p.relative_to(ROOT).as_posix()
    for p in (ROOT / "tests/kagent/experiments").glob("test_a2a_sdk_*.py")
}


def require_partition(workflow: dict) -> None:
    jobs = workflow["jobs"]
    root_steps = jobs["kagent-python"]["steps"]
    sdk_job = jobs["kagent-sdk"]
    sdk_steps = sdk_job["steps"]
    root_run = next(
        s["run"] for s in root_steps if s.get("name") == "Run deterministic Python tests"
    )
    sdk_run = next(
        s["run"]
        for s in sdk_steps
        if s.get("name") == "Require pinned runtime and execute every SDK case"
    )
    excluded = set(re.findall(r"--ignore=([^\s]+)", root_run))
    selected = set(re.findall(r"tests/kagent/experiments/test_a2a_sdk_\w+\.py", sdk_run))
    assert SDK_MODULES and excluded == selected == SDK_MODULES
    assert "uv run pytest -q" in root_run and "--ignore-glob" not in root_run
    assert "continue-on-error" not in sdk_job
    assert not any(s.get("continue-on-error", False) for s in sdk_steps)
    assert sdk_run.index('version("a2a-sdk") == "0.3.26"') < sdk_run.index("-m pytest")
    assert "(3, 13, 15)" in sdk_run and "a2a, httpx" in sdk_run
    assert "||" not in sdk_run
    assert any(s.get("with", {}).get("python-version") == "3.13.15" for s in sdk_steps)
    install = next(
        s["run"] for s in sdk_steps if s.get("name") == "Create isolated SDK environment"
    )
    assert "a2a_sdk_requirements.lock" in install and "uv pip sync" in install
    assert 'uv pip check --python "$RUNNER_TEMP/a2a-sdk/bin/python"' in install
    typing = next(s for s in sdk_steps if s.get("name", "").startswith("Type-check"))
    assert typing["env"]["UV_PROJECT_ENVIRONMENT"] == "${{ runner.temp }}/a2a-root-dev"
    assert '--python-executable "$RUNNER_TEMP/a2a-sdk/bin/python"' in typing["run"]


def test_quality_workflow_partition() -> None:
    require_partition(WORKFLOW)


@pytest.mark.parametrize("lane", ["root", "sdk"])
def test_missing_lane_module_fails(lane: str) -> None:
    workflow = copy.deepcopy(WORKFLOW)
    job = workflow["jobs"]["kagent-python" if lane == "root" else "kagent-sdk"]
    step = next(s for s in job["steps"] if "-q" in s.get("run", ""))
    module = sorted(SDK_MODULES)[0]
    step["run"] = step["run"].replace(("--ignore=" if lane == "root" else "") + module, "")
    with pytest.raises(AssertionError):
        require_partition(workflow)


@pytest.mark.parametrize(
    "outcome", ["valid", "skipped", "failure", "error", "missing-module", "empty"]
)
def test_sdk_result_gate(tmp_path: Path, outcome: str) -> None:
    suite = ET.Element("testsuite")
    for index, module in enumerate(sorted(SDK_MODULES)):
        if outcome == "empty" or (outcome == "missing-module" and index == 0):
            continue
        case = ET.SubElement(suite, "testcase", classname=Path(module).stem, name="fixture")
        if index == 0 and outcome in {"skipped", "failure", "error"}:
            ET.SubElement(case, outcome)
    report = tmp_path / "report.xml"
    ET.ElementTree(suite).write(report)
    run = next(
        s["run"]
        for s in WORKFLOW["jobs"]["kagent-sdk"]["steps"]
        if s.get("name", "").startswith("Require pinned")
    )
    gate = run.split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    result = subprocess.run(
        [sys.executable, "-B", "-c", gate, str(report)], cwd=ROOT, capture_output=True, text=True
    )
    assert (result.returncode == 0) is (outcome == "valid"), result.stderr
