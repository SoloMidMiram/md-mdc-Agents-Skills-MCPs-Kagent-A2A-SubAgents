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


@pytest.fixture
def launch_fixture(subject, tmp_path):
    target, expected = subject
    target.rename(tmp_path / "r01")
    pilot.save(tmp_path / "identity.json", expected)
    (tmp_path / "prompt.txt").write_bytes(b"frozen")
    runs = [
        {"id": f"r{n + 1:02}", "challenge": i, "condition": arm}
        for n, (i, arm) in enumerate((i, a) for i, order in enumerate(pilot.ORDERS) for a in order)
    ]
    runs[0].update(
        identity="identity.json", prompt="prompt.txt", local_commit=expected["subject_commit"]
    )
    data = dict(
        version="1.0",
        model="gpt-6.1-sol",
        reasoning="medium",
        cli="0.164.0",
        timeout_seconds=600,
        upstream=pilot.BASE,
        builder=pilot.BUILDER,
        tree=pilot.TREE,
        runs=runs,
        inputs={
            name: pilot.digest((tmp_path / name).read_bytes())
            for name in ("identity.json", "prompt.txt")
        },
    )
    pilot.save(tmp_path / "manifest.json", data)
    # Controller memory captures finalized bytes before any adversarial mutation.
    anchor = pilot.digest((tmp_path / "manifest.json").read_bytes())
    return tmp_path, runs[0], anchor


@pytest.mark.parametrize("change", ["source", "prompt", "coordinated"])
def test_setup_drift_and_changed_prompt(launch_fixture, change):
    root, item, anchor = launch_fixture
    assert pilot.validate_launch(root, item, anchor)

    def mutate():
        destination = root / "r01/README.md" if change == "source" else root / "prompt.txt"
        destination.write_bytes(b"race")
        if change == "coordinated":
            data = json.loads((root / "manifest.json").read_bytes())
            data["inputs"]["prompt.txt"] = pilot.digest(destination.read_bytes())
            (root / "manifest.json").write_text(json.dumps(data))

    with pytest.raises(ValueError):
        pilot.validate_setup_boundary(root, item, mutate, anchor)


@pytest.mark.parametrize("anchor", [None, "", "0" * 64])
def test_bad_anchor_rejected(launch_fixture, anchor):
    root, item, _ = launch_fixture
    with pytest.raises(ValueError):
        pilot.validate_launch(root, item, anchor)
    with pytest.raises(ValueError):
        pilot.validate_setup_boundary(root, item, lambda: pytest.fail("setup executed"), anchor)


def test_unchanged_setup(launch_fixture):
    root, item, anchor = launch_fixture
    before = {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
    assert pilot.validate_setup_boundary(root, item, lambda: None, anchor)
    assert before == {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}


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


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_constants_in_unchecked_field(value):
    events = trace()
    events[0]["unchecked"] = value
    with pytest.raises(ValueError, match="constant"):
        b.validate_terminal(raw(events), 0, binding(), binding())


@pytest.mark.parametrize(
    "change",
    [
        "blob",
        "pack",
        "idx",
        "delete",
        "modify",
        "directory",
        "metadata",
        "head",
        "attributes",
        "empty",
    ],
)
def test_storage_and_hierarchy(subject, change):
    target, expected = subject
    objects = target / ".git/objects"
    if change == "blob":
        fixture = target.parent / "blob"
        fixture.write_bytes(b"unreachable regression")
        pilot.git(target, "hash-object", "-w", str(fixture))
    elif change in {"pack", "idx"}:
        (objects / "pack" / ("extra." + change)).write_bytes(b"injected")
    elif change in {"delete", "modify"}:
        obj = next(p for p in objects.glob("??/*") if p.is_file())
        obj.chmod(0o600)
        if change == "delete":
            obj.unlink()
        else:
            obj.write_bytes(b"modified")
    elif change == "directory":
        (objects / "empty/nested").mkdir(parents=True)
    elif change == "metadata":
        (target / ".git/unknown").mkdir()
    elif change == "head":
        with (target / ".git/HEAD").open("ab") as stream:
            stream.write(b"\n")
    elif change == "attributes":
        (target / ".git/info/attributes").write_bytes(b"*.txt text\n")
    else:
        (target / ".venv/empty/nested").mkdir(parents=True)
    with pytest.raises((ValueError, OSError)):
        b.validate_identity(target, expected)


@pytest.mark.parametrize("operation", ["scandir", "read_bytes", "lstat"])
def test_inspection_failure(subject, operation):
    target, expected = subject
    owner = b.os if operation == "scandir" else Path
    with (
        patch.object(owner, operation, side_effect=PermissionError("injected")),
        pytest.raises(PermissionError),
    ):
        b.validate_identity(target, expected)


@pytest.mark.parametrize("kind", ["symlink", "fifo", "socket", "junction"])
def test_special_entries(tmp_path, kind):
    import os
    import socket
    import subprocess

    root = tmp_path / "inventory"
    root.mkdir()
    destination = root / "special"
    connection = None
    if kind == "fifo":
        if os.name == "nt":
            pytest.skip("Windows does not provide mkfifo")
        os.mkfifo(destination)
    elif kind == "socket":
        if os.name == "nt":
            pytest.skip("Unix socket filesystem validation runs on Ubuntu")
        connection = socket.socket(socket.AF_UNIX)
        connection.bind(str(destination))
    elif kind == "junction":
        if os.name != "nt":
            pytest.skip("Windows junction only")
        outside = tmp_path / "outside"
        outside.mkdir()
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(destination), str(outside)], capture_output=True
        )
        if result.returncode:
            pytest.skip("junction unavailable: " + result.stderr.decode(errors="replace"))
    else:
        try:
            destination.symlink_to(tmp_path / "absent")
        except OSError as exc:
            pytest.skip(f"symlink privilege unavailable: {exc}")
    try:
        with pytest.raises(ValueError, match="unsupported"):
            b.inventory_tree(root)
    finally:
        if connection is not None:
            connection.close()
        if kind == "junction":
            destination.rmdir()


@pytest.mark.parametrize("change", ["inject", "pack", "idx", "delete"])
def test_real_unreachable_pack(subject, change):
    import subprocess

    target, _ = subject
    blob = target.parent / "unreachable"
    blob.write_bytes(b"packed unreachable fixture")
    oid = pilot.git(target, "hash-object", "-w", str(blob)).strip()
    expected = b.subject_identity(target)
    result = subprocess.run(
        ["git", "-C", str(target), "pack-objects", ".git/objects/pack/pack"],
        input=oid + b"\n",
        capture_output=True,
        check=True,
    )
    pack = target / ".git/objects/pack" / ("pack-" + result.stdout.decode().strip() + ".pack")
    if change != "inject":
        expected = b.subject_identity(target)
        path = pack.with_suffix(".idx") if change == "idx" else pack
        path.chmod(0o600)
        if change == "delete":
            path.unlink()
        else:
            raw = path.read_bytes()
            path.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
    with pytest.raises((ValueError, OSError)):
        b.validate_identity(target, expected)


def test_missing_anchor_argument(launch_fixture):
    root, item, _ = launch_fixture
    with pytest.raises(TypeError):
        pilot.validate_launch(root, item)
    with pytest.raises(TypeError):
        pilot.validate_setup_boundary(root, item, lambda: None)


def test_legacy_seal_requires_preparation(subject):
    target, seal = subject
    seal.pop("objects_sha256")
    with pytest.raises(ValueError, match="fresh attempt"):
        b.validate_identity(target, seal)
