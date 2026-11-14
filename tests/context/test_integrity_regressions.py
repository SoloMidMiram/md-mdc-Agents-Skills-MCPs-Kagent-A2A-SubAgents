"""Portable original PR #13 integrity regressions; assertions retained from external review."""

import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

specification = importlib.util.spec_from_file_location(
    "candidate", pathlib.Path(__file__).resolve().parents[2] / "scripts/context/build_packet.py"
)
candidate = importlib.util.module_from_spec(specification)
specification.loader.exec_module(candidate)


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args]).strip()


@pytest.fixture
def repository(tmp_path):
    git(tmp_path, "init", "-q")
    for key, value in [
        ("user.name", "Review"),
        ("user.email", "review@example.invalid"),
        ("core.autocrlf", "false"),
        ("commit.gpgsign", "false"),
    ]:
        git(tmp_path, "config", key, value)
    return tmp_path


def build_spec(repo, data):
    (repo / "source.txt").write_bytes(data)
    git(repo, "add", "source.txt")
    git(repo, "commit", "-qm", "source")
    return {
        "schema_version": "1.0",
        "source_revision": git(repo, "rev-parse", "HEAD").decode(),
        "task": "Read physical source line two",
        "sources": [
            {
                "id": "s",
                "path": "source.txt",
                "sha256": hashlib.sha256(data).hexdigest(),
                "start_line": 2,
                "end_line": 2,
            }
        ],
        "claims": [],
        "unknowns": [],
        "exclusions": [],
    }


@pytest.mark.parametrize(
    "separator", ["\u2028", "\u2029", "\x85", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\r"]
)
def test_citation_uses_LF_physical_source_line(repository, separator):
    request = build_spec(repository, f"first{separator}same-line\nsecond\n".encode())
    packet = candidate.build_packet(repository, request)
    assert packet["evidence"][0]["excerpt"] == "second"


@pytest.mark.parametrize("flag", ["--assume-unchanged", "--skip-worktree"])
@pytest.mark.parametrize("change", ["edited", "missing"])
def test_dirty_or_missing_source_rejected_even_with_index_flags(repository, flag, change):
    request = build_spec(repository, b"first\nsecond\n")
    git(repository, "update-index", flag, "source.txt")
    if change == "edited":
        (repository / "source.txt").write_text("changed\n", encoding="utf-8")
    else:
        (repository / "source.txt").unlink()
    with pytest.raises(candidate.PacketError):
        candidate.build_packet(repository, request)


def test_utf8_source_can_be_emitted_to_stdout(repository):
    request = build_spec(repository, "first\n漢字\n".encode())
    path = repository / "request.json"
    path.write_text(json.dumps(request), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(pathlib.Path(candidate.__file__)),
            "--repo",
            str(repository),
            "--spec",
            str(path),
        ],
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.decode("utf-8"))["evidence"][0]["excerpt"] == "漢字"


def test_utf8_stdout_under_restrictive_encoding(repository, monkeypatch):
    monkeypatch.setenv("PYTHONIOENCODING", "ascii")
    test_utf8_source_can_be_emitted_to_stdout(repository)
