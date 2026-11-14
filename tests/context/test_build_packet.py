"""Behavioral contract tests for the bounded offline context builder."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/context/build_packet.py"
SPEC = importlib.util.spec_from_file_location("build_packet", SCRIPT)
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def run_git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args]).decode().strip()


@pytest.fixture
def source_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    run_git(repo, "init", "-q")
    run_git(repo, "config", "user.name", "Context Test")
    run_git(repo, "config", "user.email", "test@example.invalid")
    run_git(repo, "config", "core.autocrlf", "false")
    data = b"# Evidence\nAccepted A2A task.\nNo same-task MCP observation.\n"
    (repo / "evidence.md").write_bytes(data)
    run_git(repo, "add", "evidence.md")
    run_git(repo, "commit", "-qm", "fixture")
    spec = {
        "schema_version": "1.0",
        "source_revision": run_git(repo, "rev-parse", "HEAD"),
        "task": "Explain the missing proof.",
        "sources": [
            {
                "id": "attempt",
                "path": "evidence.md",
                "start_line": 2,
                "end_line": 3,
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        ],
        "claims": [
            {"statement": "Dispatch is recorded.", "kind": "recorded", "source_ids": ["attempt"]}
        ],
        "unknowns": ["Current runtime state."],
        "exclusions": ["No live verification."],
    }
    return repo, spec


def test_exact_excerpts_and_deterministic_output(source_repo):
    repo, spec = source_repo
    packet = builder.build_packet(repo, spec)
    assert packet == builder.build_packet(repo, spec)
    assert packet["evidence"][0]["excerpt"] == ("Accepted A2A task.\nNo same-task MCP observation.")
    assert packet["source_revision"] == spec["source_revision"]
    assert packet["unknowns"] == spec["unknowns"]
    assert packet["claims"] == spec["claims"]
    assert "claim truth is not evaluated" in packet["validation_scope"]


@pytest.mark.parametrize(
    "path",
    [
        "../secret",
        "/etc/passwd",
        "C:/secret",
        "a\\b",
        "./evidence.md",
        "a/../b",
        ".git/config",
        "*.md",
        ":(glob)*",
        "a//b",
        "a\nb",
    ],
)
def test_rejects_path_escape_and_pathspecs(source_repo, path):
    repo, spec = source_repo
    spec["sources"][0]["path"] = path
    with pytest.raises(builder.PacketError, match="canonical"):
        builder.build_packet(repo, spec)


@pytest.mark.parametrize("change", ["edit", "delete", "stage"])
def test_rejects_changed_sources(source_repo, change):
    repo, spec = source_repo
    if change == "delete":
        (repo / "evidence.md").unlink()
    else:
        (repo / "evidence.md").write_text("changed\n", encoding="utf-8")
        if change == "stage":
            run_git(repo, "add", "evidence.md")
    with pytest.raises(builder.PacketError, match="differs"):
        builder.build_packet(repo, spec)


def test_rejects_missing_file_and_directory(source_repo):
    repo, spec = source_repo
    for path in ["missing.md", "missing"]:
        spec["sources"][0]["path"] = path
        with pytest.raises(builder.PacketError, match="regular tracked file"):
            builder.build_packet(repo, spec)


def test_rejects_symlink_blob(source_repo):
    repo, spec = source_repo
    # Construct a Git symlink entry without requiring Windows symlink privileges.
    blob = run_git(repo, "rev-parse", "HEAD:evidence.md")
    run_git(repo, "update-index", "--add", "--cacheinfo", f"120000,{blob},link.md")
    run_git(repo, "commit", "-qm", "symlink")
    spec["source_revision"] = run_git(repo, "rev-parse", "HEAD")
    spec["sources"][0]["path"] = "link.md"
    with pytest.raises(builder.PacketError, match="regular tracked file"):
        builder.build_packet(repo, spec)


@pytest.mark.parametrize("start,end", [(0, 1), (3, 2), (1, 99), (True, 2), (1, "2")])
def test_rejects_unresolvable_ranges(source_repo, start, end):
    repo, spec = source_repo
    spec["sources"][0].update(start_line=start, end_line=end)
    with pytest.raises(builder.PacketError, match="line range"):
        builder.build_packet(repo, spec)


def test_rejects_hash_drift_duplicates_and_dangling_claims(source_repo):
    repo, original = source_repo
    spec = copy.deepcopy(original)
    spec["sources"][0]["sha256"] = "0" * 64
    with pytest.raises(builder.PacketError, match="hash mismatch"):
        builder.build_packet(repo, spec)
    spec = copy.deepcopy(original)
    spec["sources"].append(copy.deepcopy(spec["sources"][0]))
    with pytest.raises(builder.PacketError, match="duplicate"):
        builder.build_packet(repo, spec)
    spec = copy.deepcopy(original)
    spec["claims"][0]["source_ids"] = ["missing"]
    with pytest.raises(builder.PacketError, match="missing source IDs"):
        builder.build_packet(repo, spec)


def test_byte_budget_and_revision_are_enforced(source_repo, monkeypatch):
    repo, spec = source_repo
    spec["source_revision"] = "HEAD"
    with pytest.raises(builder.PacketError, match="full lowercase"):
        builder.build_packet(repo, spec)
    spec["source_revision"] = run_git(repo, "rev-parse", "HEAD")
    monkeypatch.setattr(builder, "MAX_BYTES", 5)
    with pytest.raises(builder.PacketError, match="budget"):
        builder.build_packet(repo, spec)


@pytest.mark.parametrize("kind", [[], {}])
def test_malformed_claim_kind_is_rejected(source_repo, kind):
    repo, spec = source_repo
    spec["claims"][0]["kind"] = kind
    with pytest.raises(builder.PacketError, match="recorded or inference"):
        builder.build_packet(repo, spec)


def test_cli_rejection_preserves_output_and_emits_no_packet(source_repo, tmp_path):
    repo, spec = source_repo
    input_path, output_path = tmp_path / "spec.json", tmp_path / "packet.json"
    output_path.write_text("keep existing", encoding="utf-8")
    input_path.write_text(json.dumps(spec), encoding="utf-8")
    command = [
        sys.executable,
        str(SCRIPT),
        "--repo",
        str(repo),
        "--spec",
        str(input_path),
        "--output",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 2
    assert result.stdout == ""
    assert output_path.read_text(encoding="utf-8") == "keep existing"
    output_path.unlink()
    spec["sources"][0]["sha256"] = "stale"
    input_path.write_text(json.dumps(spec), encoding="utf-8")
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 2
    assert not output_path.exists()


def test_real_lab01_fixture_replays_without_grading_artifacts():
    spec = json.loads((ROOT / "tests/context/fixtures/lab-01.json").read_text(encoding="utf-8"))
    packet = builder.build_packet(ROOT, spec)
    assert len(packet["evidence"]) == 6
    assert "toolCallSucceeded" in packet["evidence"][3]["excerpt"]
    assert "observed=false" in packet["evidence"][2]["excerpt"]
    assert all("evidence/labs/" not in item["path"] for item in packet["evidence"])


@pytest.mark.parametrize(
    "data,expected",
    [
        (b"first\nsecond\n", "second"),
        (b"first\r\nsecond\r\n", "second"),
        (b"first\r\nsecond\n", "second"),
        (b"first\nsecond", "second"),
        (b"first\nsecond\r", "second\r"),
        (b"first\n\n", ""),
    ],
)
def test_physical_line_endings(source_repo, data, expected):
    repo, spec = source_repo
    (repo / "evidence.md").write_bytes(data)
    run_git(repo, "add", "evidence.md")
    run_git(repo, "commit", "-qm", "line endings")
    spec["source_revision"] = run_git(repo, "rev-parse", "HEAD")
    spec["sources"][0].update(sha256=hashlib.sha256(data).hexdigest(), start_line=2, end_line=2)
    assert builder.build_packet(repo, spec)["evidence"][0]["excerpt"] == expected
    spec["sources"][0].update(start_line=3, end_line=3)
    with pytest.raises(builder.PacketError, match="line range"):
        builder.build_packet(repo, spec)


@pytest.mark.parametrize("flag", ["--assume-unchanged", "--skip-worktree"])
def test_flagged_selected_source_rejected_without_mutation(source_repo, flag):
    repo, spec = source_repo
    run_git(repo, "update-index", flag, "evidence.md")
    before = (repo / ".git/index").read_bytes()
    content = (repo / "evidence.md").read_bytes()
    flags = run_git(repo, "ls-files", "-v")
    with pytest.raises(builder.PacketError, match="index flags"):
        builder.build_packet(repo, spec)
    assert (repo / ".git/index").read_bytes() == before
    assert (repo / "evidence.md").read_bytes() == content
    assert run_git(repo, "ls-files", "-v") == flags


def test_crlf_checkout_and_unrelated_flags_are_read_only(source_repo):
    repo, spec = source_repo
    run_git(repo, "config", "core.autocrlf", "true")
    original = (repo / "evidence.md").read_bytes()
    (repo / "evidence.md").write_bytes(original.replace(b"\n", b"\r\n"))
    (repo / "unrelated.txt").write_bytes(b"other\n")
    run_git(repo, "add", "unrelated.txt")
    run_git(repo, "update-index", "--skip-worktree", "unrelated.txt")
    before = (repo / ".git/index").read_bytes()
    working = (repo / "evidence.md").read_bytes()
    assert builder.build_packet(repo, spec) == builder.build_packet(repo, spec)
    assert (repo / ".git/index").read_bytes() == before
    assert (repo / "evidence.md").read_bytes() == working


@pytest.mark.parametrize("invalid", ["utf8", "edit", "delete", "empty"])
def test_invalid_source_cli_preserves_outputs(source_repo, tmp_path, invalid):
    repo, spec = source_repo
    path = repo / "evidence.md"
    if invalid in {"utf8", "empty"}:
        data = b"\xff\n" if invalid == "utf8" else b""
        path.write_bytes(data)
        run_git(repo, "add", "evidence.md")
        run_git(repo, "commit", "-qm", "invalid source")
        spec["source_revision"] = run_git(repo, "rev-parse", "HEAD")
        spec["sources"][0]["sha256"] = hashlib.sha256(data).hexdigest()
    elif invalid == "edit":
        path.write_bytes(b"changed\n")
    else:
        path.unlink()
    request = tmp_path / "request.json"
    request.write_text(json.dumps(spec), encoding="utf-8")
    output = tmp_path / "output.json"
    index = (repo / ".git/index").read_bytes()
    for existing in (False, True):
        if existing:
            output.write_bytes(b"sentinel")
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repo",
                str(repo),
                "--spec",
                str(request),
                "--output",
                str(output),
            ],
            capture_output=True,
        )
        assert result.returncode == 2
        assert result.stdout == b""
        assert output.read_bytes() == b"sentinel" if existing else not output.exists()
        assert (repo / ".git/index").read_bytes() == index


def test_stdout_matches_utf8_file_bytes(source_repo, tmp_path, monkeypatch):
    repo, spec = source_repo
    spec["task"] = "Read 漢字"
    request = tmp_path / "request.json"
    request.write_text(json.dumps(spec), encoding="utf-8")
    output = tmp_path / "packet.json"
    command = [sys.executable, str(SCRIPT), "--repo", str(repo), "--spec", str(request)]
    monkeypatch.setenv("PYTHONIOENCODING", "ascii")
    stdout = subprocess.run(command, capture_output=True)
    file_result = subprocess.run([*command, "--output", str(output)], capture_output=True)
    assert stdout.returncode == file_result.returncode == 0
    assert stdout.stdout == output.read_bytes()
    assert json.loads(stdout.stdout.decode("utf-8"))["task"] == spec["task"]
