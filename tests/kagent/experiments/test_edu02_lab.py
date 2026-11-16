import asyncio
import hashlib
import json
import shutil
import subprocess
import sys

import pytest

from scripts.kagent.experiments import edu02_lab as lab
from scripts.kagent.experiments.contracts import ContractError


def test_replay():
    report = asyncio.run(lab.replay())
    assert report == asyncio.run(lab.replay())
    assert report["origin"] == "synthetic"
    assert report["capabilityPromotion"] is False
    assert report["decision"]["verdict"] == "approve"
    assert report["decision"]["revisions"] == 1
    tasks = report["decision"]["subtasks"]
    assert len(tasks) == 4
    assert len({task["request_id"] for task in tasks}) == 4
    assert [tasks[i]["artifact"]["verdict"] for i in (1, 3)] == ["revise", "approve"]
    (finding,) = report["results"]["broken"]["findings"]
    assert finding["startLine"] == 3
    assert finding["excerpt"] == "See [Install](#instal).\n"
    assert report["results"]["fixed"]["findings"] == []


@pytest.mark.parametrize("ending", ["\n", "\r\n", ""])
def test_exact_citation(ending):
    result = lab.check({"a.md": "# Heading\n[Missing](#absent)" + ending})
    assert result["findings"][0]["excerpt"] == "[Missing](#absent)" + ending
    assert result["findings"][0]["startLine"] == 2


def test_supported_and_fenced():
    result = lab.check({"a.md": "# One Two\n[Link](#one-two)\n```md\n[Bad](#none)\n```\n"})
    assert not result["findings"]
    assert not result["unresolvedQuestions"]


@pytest.mark.parametrize(
    "content",
    [
        "# *Rich*\n",
        "[Other](other.md)\n",
        "Heading\n===\n",
        "# Same\n# Same\n",
        "```\n",
        "[Ref][name]\n",
    ],
)
def test_unsupported_is_not_clean(content):
    assert lab.check({"a.md": content})["unresolvedQuestions"]


def test_tampered_fixture(tmp_path):
    shutil.copytree(lab.FIXTURES, tmp_path / "fixtures")
    root = tmp_path / "fixtures"
    (root / "fixed" / "guide.md").write_bytes(b"# Tampered\n")
    with pytest.raises(ContractError, match="digest"):
        asyncio.run(lab.replay(root))


def test_still_broken_rejected(tmp_path):
    shutil.copytree(lab.FIXTURES, tmp_path / "fixtures")
    root = tmp_path / "fixtures"
    content = (root / "broken" / "guide.md").read_bytes()
    (root / "fixed" / "guide.md").write_bytes(content)
    manifest_path = root / "fixed" / "bundle.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["files"][0]["content"] = content.decode()
    manifest["files"][0]["sha256"] = hashlib.sha256(content).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    report = asyncio.run(lab.replay(root))
    assert report["decision"]["verdict"] == "reject"
    assert report["decision"]["revisions"] == 1


def test_cli_bytes():
    command = [sys.executable, "-m", "scripts.kagent.experiments.edu02_lab"]
    first = subprocess.run(command, capture_output=True, check=True)
    second = subprocess.run(command, capture_output=True, check=True)
    assert first.stdout == second.stdout
    assert not first.stderr
    assert json.loads(first.stdout)["decision"]["verdict"] == "approve"


@pytest.mark.parametrize("mutation", ["digest", "path", "duplicate", "json"])
def test_invalid_bundle(tmp_path, mutation):
    shutil.copytree(lab.FIXTURES, tmp_path / "fixtures")
    root = tmp_path / "fixtures"
    path = root / "broken" / "bundle.json"
    raw = path.read_text()
    data = json.loads(raw)
    if mutation == "digest":
        data["files"][0]["sha256"] = "0" * 64
        raw = json.dumps(data)
    elif mutation == "path":
        data["files"][0]["path"] = "../escape.md"
        raw = json.dumps(data)
    elif mutation == "duplicate":
        raw = raw.replace(
            '"schemaVersion": "1.0"', '"schemaVersion": "1.0", "schemaVersion": "1.0"'
        )
    else:
        raw = "{"
    path.write_text(raw)
    with pytest.raises(ContractError):
        asyncio.run(lab.replay(root))


def test_main_failure(monkeypatch, capsys):
    async def failure():
        raise ContractError("invalid content digest")

    monkeypatch.setattr(lab, "replay", failure)
    assert lab.main() == 1
    output = capsys.readouterr()
    assert not output.out
    assert "invalid content digest" in output.err


def test_offline(monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError("network access")

    async def run():
        with monkeypatch.context() as patch:
            patch.setattr(socket.socket, "connect", forbidden)
            patch.setattr(socket, "getaddrinfo", forbidden)
            return await lab.replay()

    assert asyncio.run(run())["decision"]["verdict"] == "approve"
