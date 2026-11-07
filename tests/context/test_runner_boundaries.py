"""Synthetic offline contracts: no Codex invocation or isolation qualification."""

import copy
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "offline_pilot", ROOT / "scripts/context/labs/pilot.py"
)
pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pilot)
b = pilot.boundaries


@pytest.fixture
def subject(tmp_path):
    target = tmp_path / "subject"
    pilot.fresh_source(ROOT, target)
    return target, b.subject_identity(target)


@pytest.mark.parametrize(
    "change", ["commit", "tree", "input", "ignored", "flag", "alternate", "config", "ref"]
)
def test_launch_identity_rejects_changes(subject, change):
    target, expected = subject
    if change in {"commit", "tree"}:
        if change == "tree":
            (target / "README.md").write_bytes(b"changed\n")
            pilot.git(target, "add", "README.md")
        pilot.git(
            target,
            "-c",
            "user.name=Test",
            "-c",
            "user.email=t@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--allow-empty",
            "-qm",
            "other identity",
        )
    elif change == "input":
        (target / "README.md").write_bytes(b"changed\n")
    elif change == "ignored":
        (target / ".venv").mkdir()
        (target / ".venv/unapproved").write_bytes(b"not allowed")
    elif change == "flag":
        pilot.git(target, "update-index", "--skip-worktree", "README.md")
    elif change == "alternate":
        (target / ".git/objects/info/alternates").write_bytes(b"untrusted\n")
    elif change == "config":
        pilot.git(target, "config", "core.hooksPath", "/unexpected")
    else:
        pilot.git(target, "update-ref", "refs/heads/extra", "HEAD")
    with pytest.raises(ValueError):
        b.validate_identity(target, expected)


def test_identity_read_only(subject):
    target, expected = subject
    index = (target / ".git/index").read_bytes()
    assert b.validate_identity(target, expected) == expected
    assert (target / ".git/index").read_bytes() == index


def trace():
    return [
        {"type": "thread.started", "thread_id": "synthetic-thread"},
        {"type": "turn.started"},
        {
            "type": "item.completed",
            "item": {"id": "i1", "type": "agent_message", "text": "Synthetic answer"},
        },
        {
            "type": "turn.completed",
            "usage": {"input_tokens": 10, "cached_input_tokens": 2, "output_tokens": 3},
        },
    ]


def binding():
    return {
        "run_id": "r01",
        "nonce": "synthetic-nonce",
        "request_sha256": "a" * 64,
        "subject_commit": "b" * 40,
        "subject_tree": b.HISTORICAL_TREE,
        "execution_handle": "synthetic-process",
    }


def raw(events):
    return ("\n".join(json.dumps(e) for e in events) + "\n").encode()


def test_synthetic_terminal_valid():
    result = b.validate_terminal(raw(trace()), 0, binding(), binding())
    assert result["offline_valid"] and result["thread_id"] == "synthetic-thread"


@pytest.mark.parametrize(
    "change",
    [
        "truncated",
        "malformed",
        "no_final",
        "duplicate",
        "failure",
        "wrong_thread",
        "no_usage",
        "bool_usage",
        "negative_usage",
        "cached_usage",
        "no_start",
        "no_thread",
        "missing_terminal",
    ],
)
def test_invalid_terminal_cannot_complete(change):
    events = trace()
    if change == "no_final":
        events.pop(2)
    elif change == "duplicate":
        events.append(copy.deepcopy(events[-1]))
    elif change == "failure":
        events.insert(2, {"type": "turn.failed", "error": {"message": "synthetic"}})
    elif change == "wrong_thread":
        events[-1]["thread_id"] = "other"
    elif change == "no_usage":
        events[-1].pop("usage")
    elif change == "bool_usage":
        events[-1]["usage"]["input_tokens"] = True
    elif change == "negative_usage":
        events[-1]["usage"]["output_tokens"] = -1
    elif change == "cached_usage":
        events[-1]["usage"]["cached_input_tokens"] = 20
    elif change == "no_start":
        events.pop(1)
    elif change == "no_thread":
        events.pop(0)
    elif change == "missing_terminal":
        events.pop()
    stream = raw(events)
    if change == "truncated":
        stream = stream[:-1]
    if change == "malformed":
        stream = b"not JSON\n" + stream
    with pytest.raises(ValueError):
        b.validate_terminal(stream, 0, binding(), binding())


@pytest.mark.parametrize("key", list(b.BINDING_KEYS))
def test_stale_binding_rejected(key):
    observed = binding()
    observed[key] = "stale"
    with pytest.raises(ValueError, match="binding"):
        b.validate_terminal(raw(trace()), 0, binding(), observed)


def test_exit_failure_rejected():
    with pytest.raises(ValueError):
        b.validate_terminal(raw(trace()), 1, binding(), binding())


def test_duplicate_json_keys_rejected():
    with pytest.raises(ValueError):
        b.validate_terminal(
            b'{"type":"turn.failed","type":"turn.completed"}\n', 0, binding(), binding()
        )


@pytest.mark.parametrize("change", ["source", "prompt"])
def test_setup_drift_and_changed_prompt(subject, tmp_path, change):
    target, expected = subject
    seal = tmp_path / "identity.json"
    seal.write_text(json.dumps(expected))
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("frozen")
    item = {
        "id": "subject",
        "local_commit": expected["subject_commit"],
        "identity": seal.name,
        "prompt": prompt.name,
    }
    # Synthetic controller fixture exercises both revalidation points without dispatch.
    data = {
        "runs": [item],
        "inputs": {
            seal.name: pilot.digest(seal.read_bytes()),
            prompt.name: pilot.digest(prompt.read_bytes()),
        },
    }
    with patch.object(pilot, "load", return_value=data), pytest.raises(ValueError):
        destination = target / "README.md" if change == "source" else prompt
        pilot.validate_setup_boundary(tmp_path, item, lambda: destination.write_bytes(b"race"))


def test_forged_launcher_never_executes(tmp_path):
    launcher = tmp_path / "launcher.py"
    marker = tmp_path / "called"
    launcher.write_text(f"open({str(marker)!r}, 'w').write('called')")
    data = {"runs": [{"id": "r01"}]}
    with patch.object(pilot, "load", return_value=data):
        pilot.run(tmp_path, launcher)
    assert not marker.exists()
    assert json.loads((tmp_path / "r01-blocked.json").read_text())["model_calls"] == 0


@pytest.mark.parametrize("state", ["completed", "failed", "timeout"])
def test_plausible_completion_cannot_score_without_qualification(tmp_path, state):
    item = {"id": "r01"}
    patch_bytes = b"synthetic patch"
    (tmp_path / "r01.patch").write_bytes(patch_bytes)
    pilot.record(
        tmp_path,
        "r01",
        state,
        patch_sha256=pilot.digest(patch_bytes),
        offline_valid=True,
        exit=0,
    )
    with patch.object(pilot, "load", return_value={"runs": [item]}):
        pilot.evaluate(tmp_path, Path("must-not-execute"))
    assert json.loads((tmp_path / "r01-evaluated.json").read_text())["correctness"] is None


def test_missing_controller_binding_rejected():
    with pytest.raises(ValueError):
        b.validate_terminal(raw(trace()), 0, binding(), None)


def test_malformed_config_rejected_before_git_query(subject):
    target, expected = subject
    (target / ".git/config").write_text("not a Git config")
    with pytest.raises(ValueError, match="configuration"):
        b.validate_identity(target, expected)


def test_forged_evaluation_cannot_create_score(tmp_path):
    pilot.record(tmp_path, "r01", "evaluated", outcome="evaluated", correctness=True)
    with (
        patch.object(pilot, "load", return_value={"runs": [{"id": "r01"}]}),
        pytest.raises(ValueError, match="scoring disabled"),
    ):
        pilot.summarize(tmp_path)
