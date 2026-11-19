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
    for field in ("request_id", "task_id", "message_id"):
        assert len({task[field] for task in tasks}) == 4
    assert [tasks[i]["artifact"]["verdict"] for i in (1, 3)] == ["revise", "approve"]
    (finding,) = report["results"]["broken"]["findings"]
    assert finding["startLine"] == 3
    assert finding["findingId"] in tasks[1]["artifact"]["findings"][0]
    assert finding["excerpt"] == "See [Install](runbook.md#instal).\n"
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
        "# One\n    [Indented](#one)\n",
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


@pytest.mark.parametrize("mutation", ["digest", "path", "duplicate", "duplicate-path", "json"])
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
    elif mutation == "duplicate-path":
        data["files"].append(data["files"][0])
        raw = json.dumps(data)
    else:
        raw = "{"
    path.write_text(raw)
    with pytest.raises(ContractError):
        asyncio.run(lab.replay(root))


def test_main_failure(monkeypatch, capsys):
    async def failure(**kwargs):
        raise ContractError("invalid content digest")

    monkeypatch.setattr(lab, "replay", failure)
    assert lab.main([]) == 1
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


def test_cross_file_resolution_and_stable_ids():
    files = {
        "docs/guide.md": (
            "Caf\u00e9 [Setup](../runbook.md#setup) [A](missing.md#a) "
            "[Repeat](./missing.md#a) [B](missing.md#b)\r\n"
        ),
        "runbook.md": "# Setup\r\n",
    }
    result = lab.check(files)
    assert result == lab.check(dict(reversed(list(files.items()))))
    assert not result["unresolvedQuestions"]
    first, second = result["findings"]
    assert first["excerpt"] == second["excerpt"] == files["docs/guide.md"]
    assert first["findingId"] != second["findingId"]
    files["unrelated.md"] = "# Added\n"
    assert lab.check(files) == result


@pytest.mark.parametrize(
    "link,reason",
    [
        ("[Escapes](../runbook.md#setup)", "escapes"),
        ("[Ambiguous](runbook.md#setup)", "ambiguous"),
        ("[Remote](https://example.com/runbook.md#setup)", "unsupported"),
        ("[Encoded](runbook.md#s%65tup)", "unsupported"),
        ("![Image](runbook.md#setup)", "unsupported"),
    ],
)
def test_invalid_targets_are_unresolved(link, reason):
    result = lab.check({"guide.md": link, "runbook.md": "# Setup\n# SETUP\n"})
    assert not result["findings"]
    assert any(reason in question for question in result["unresolvedQuestions"])
    assert not result["passedChecks"]


def test_finding_bound():
    content = "[Missing](#absent)\n" * (lab.MAX_DIAGNOSTICS + 1)
    with pytest.raises(ContractError, match="diagnostic limit"):
        lab.check({"guide.md": content})


@pytest.mark.parametrize(
    ("case", "verdict", "steps"), [("fixed", "approve", 2), ("broken", "reject", 4)]
)
def test_case_cli(case, verdict, steps):
    completed = subprocess.run(
        [sys.executable, "-m", "scripts.kagent.experiments.edu02_lab", "--case", case],
        capture_output=True,
        check=True,
    )
    report = json.loads(completed.stdout)
    assert report["decision"]["verdict"] == verdict
    assert len(report["stages"]) == steps
    assert not completed.stderr


@pytest.mark.parametrize(
    ("fault", "error", "message"),
    [
        ("excerpt", ContractError, "excerpt"),
        ("artifact", ContractError, "missing keys"),
        ("duplicate", ContractError, "duplicate"),
        ("deadline", TimeoutError, None),
    ],
)
def test_replay_rejects_corrupt_evidence(monkeypatch, fault, error, message):
    from dataclasses import replace

    validate = lab.docs_bundle.validate_findings
    coordinate = lab.orchestration.coordinate

    def validate_with_fault(result, files):
        if fault == "excerpt" and result["findings"]:
            result["findings"][0]["excerpt"] = "Fabricated citation"
        return validate(result, files)

    async def coordinate_with_fault(request, invoke, *, timeout):
        async def inject(agent, payload, remaining):
            if fault == "deadline":
                await asyncio.Event().wait()
            subtask = await invoke(agent, payload, remaining)
            if agent == lab.orchestration.REVIEWER:
                if fault == "artifact":
                    return replace(subtask, artifact={"verdict": "approve"})
                if fault == "duplicate":
                    return replace(subtask, task_id="edu02-task-1")
            return subtask

        return await coordinate(request, inject, timeout=0.01 if fault == "deadline" else timeout)

    monkeypatch.setattr(lab.docs_bundle, "validate_findings", validate_with_fault)
    monkeypatch.setattr(lab.orchestration, "coordinate", coordinate_with_fault)
    with pytest.raises(error, match=message):
        asyncio.run(lab.replay())


def test_fixture_rejects_symlink_before_reading(tmp_path):
    root = tmp_path / "fixtures"
    shutil.copytree(lab.FIXTURES, root)
    target = tmp_path / "external.md"
    source = root / "broken" / "runbook.md"
    source.rename(target)
    try:
        source.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    with pytest.raises(ContractError, match="fixture path redirects"):
        lab.load_fixture("broken", root)
