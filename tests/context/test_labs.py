"""Synthetic harness controls; not evidence of coding-agent performance."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/context/labs/pilot.py"
SPEC = importlib.util.spec_from_file_location("pilot", SCRIPT)
pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pilot)


@pytest.fixture
def prepared(tmp_path):
    prompt = tmp_path / "prompt.txt"
    prompt.write_bytes(b"task")
    rows = [
        {"id": f"r{3 * i + j + 1:02}", "challenge": i, "condition": arm}
        for i, order in enumerate(pilot.ORDERS)
        for j, arm in enumerate(order)
    ]
    pilot.save(
        tmp_path / "manifest.json",
        {
            "version": "1.0",
            "runs": rows,
            "inputs": {"prompt.txt": pilot.digest(b"task")},
            "model": "gpt-6.1-sol",
            "reasoning": "medium",
            "cli": "0.164.0",
            "timeout_seconds": 600,
            "upstream": pilot.BASE,
            "builder": pilot.BUILDER,
            "tree": pilot.TREE,
        },
    )
    return tmp_path


def test_exclusive_capture(prepared):
    with pytest.raises(FileExistsError):
        pilot.save(prepared / "manifest.json", {})


def test_input_tampering_rejected(prepared):
    (prepared / "prompt.txt").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="digest"):
        pilot.load(prepared)


def test_malformed_manifest(prepared):
    (prepared / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="manifest"):
        pilot.load(prepared)


def test_nine_blocked_not_scored(prepared):
    pilot.run(prepared, None)
    assert len(list(prepared.glob("r??-blocked.json"))) == 9
    pilot.evaluate(prepared, Path("not-executed"))
    result = pilot.summarize(prepared)
    assert result["scored_runs"] == 0
    assert all(r["correctness"] is None and r["usage"] is None for r in result["runs"])
    with pytest.raises(ValueError, match="already"):
        pilot.run(prepared, None)


def test_incomplete_summary_rejected(prepared):
    with pytest.raises(ValueError, match="incomplete"):
        pilot.summarize(prepared)


def test_interrupted_run_not_evaluated(prepared):
    pilot.record(prepared, "r01", "running")
    with pytest.raises(ValueError, match="terminal"):
        pilot.evaluate(prepared, Path("not-executed"))


def test_timeout_is_not_success(tmp_path):
    with pytest.raises(subprocess.TimeoutExpired):
        pilot.call([sys.executable, "-c", "import time; time.sleep(2)"], tmp_path, timeout=0.1)


def test_invalid_patch_digest_rejected(prepared):
    pilot.record(prepared, "r01", "completed", patch_sha256="wrong")
    (prepared / "r01.patch").write_bytes(b"bad patch")
    with pytest.raises(ValueError, match="patch digest"):
        pilot.evaluate(prepared, Path("not-executed"))


def test_failed_terminal_without_patch_not_accepted(prepared):
    pilot.record(prepared, "r01", "failed", patch_sha256="bad")
    with pytest.raises(FileNotFoundError):
        pilot.evaluate(prepared, Path("not-executed"))


def test_missing_usage_remains_unknown(prepared):
    pilot.run(prepared, None)
    pilot.evaluate(prepared, Path("unused"))
    result = pilot.summarize(prepared)
    assert result["cash_cost"] == "unknown"
    assert all(row["cash_cost"] is None for row in result["runs"])
    assert json.loads((prepared / "summary.json").read_text())["scored_runs"] == 0


def test_model_substitution_rejected(prepared):
    path = prepared / "manifest.json"
    data = json.loads(path.read_text())
    data["model"] = "another-model"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="configuration"):
        pilot.load(prepared)


def test_subject_tree_matches_original_without_descendants(tmp_path):
    target = tmp_path / "subject"
    pilot.fresh_source(ROOT, target)
    assert pilot.git(target, "rev-parse", "HEAD^{tree}") == pilot.git(
        ROOT, "rev-parse", f"{pilot.BASE}^{{tree}}"
    )
    assert pilot.git(target, "remote").strip() == b""
    result = pilot.call(["git", "cat-file", "-e", pilot.BUILDER], target)
    assert result.returncode != 0
