import asyncio
import json
import subprocess
import sys

import pytest

from scripts.kagent.experiments import edu03_lab as lab
from scripts.kagent.experiments.contracts import ContractError


@pytest.mark.parametrize(("case", "verdict"), [("correct", "approve"), ("misleading", "reject")])
def test_replay(case, verdict):
    result = asyncio.run(lab.replay(case))
    assert result == asyncio.run(lab.replay(case))
    assert result["origin"] == "synthetic" and result["capabilityPromotion"] is False
    assert result["patchSha256"] == lab.digest(lab.patch_bytes(case))
    assert result["decision"]["verdict"] == verdict
    assert all(row["expected"] == row["observed"] for row in result["checks"]["visible"])
    assert all(row["expected"] == row["observed"] for row in result["checks"]["heldout"]) == (
        case == "correct"
    )
    for task in result["decision"]["subtasks"][1::2]:
        assert task["artifact"]["findings"][0] == f"evidence_sha256={result['evidenceSha256']}"


def test_unpatched_base_fails_visible_test(tmp_path):
    results = lab.evaluate(tmp_path, lab.BASE)
    assert results["visible"][0]["observed"] == 1000
    assert results["visible"][0]["expected"] == 900


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda p: p.replace(b"b/discount.py", b"b/../discount.py"), "allowlist"),
        (lambda p: p.replace(b"b/discount.py", b"b/visible.json"), "allowlist"),
        (lambda p: p.replace(b"@@", b"##", 1), "hunk header"),
        (lambda p: p.replace(b"quantity > 10", b"quantity > 11"), "context"),
        (lambda p: p + b"another file\n", "malformed patch body"),
        (lambda p: p * 10, "oversize"),
        (lambda _p: lab.patch_bytes("misleading"), "frozen candidate"),
    ],
)
def test_rejects_untrusted_patch(mutate, message):
    async def worker(root, patch):
        (root / lab.PATCH).write_bytes(mutate(patch))

    with pytest.raises(ContractError, match=message):
        asyncio.run(lab.replay("correct", worker=worker))


@pytest.mark.parametrize("control", ["test_mutation", "untracked", "redirect"])
def test_untrusted_worker_inventory(control, tmp_path):
    async def worker(root, patch):
        await lab.fixture_worker(root, patch)
        if control == "test_mutation":
            (root / lab.VISIBLE).write_bytes(b"[]")
        elif control == "untracked":
            (root / "extra.py").write_bytes(b"x = 1\n")
        else:
            external = tmp_path / "outside"
            external.write_bytes(patch)
            (root / lab.PATCH).unlink()
            try:
                (root / lab.PATCH).symlink_to(external)
            except OSError:
                pytest.skip("symlinks unavailable")

    with pytest.raises(ContractError, match="worker"):
        asyncio.run(lab.replay("correct", worker=worker))


def test_evaluation_uses_separate_root(monkeypatch):
    source = lab.evaluate
    observed = []

    async def worker(root, patch):
        observed.append(root)
        assert {p.name for p in root.iterdir()} == {lab.MODULE, lab.VISIBLE}
        await lab.fixture_worker(root, patch)

    def evaluator(root, changed):
        assert root != observed[0] and not observed[0].exists()
        assert not list(root.iterdir())
        observed.append(root)
        return source(root, changed)

    monkeypatch.setattr(lab, "evaluate", evaluator)
    asyncio.run(lab.replay("correct", worker=worker))
    assert len(observed) == 2 and all(not path.exists() for path in observed)


def test_fabricated_success_rejected():
    def fabricate(expected):
        return {**expected, "verdict": "approve", "findings": ["evidence_sha256=fabricated"]}

    with pytest.raises(ContractError, match="does not match evaluator"):
        asyncio.run(lab.replay("misleading", reviewer=fabricate))


@pytest.mark.parametrize("swallow", [False, True])
def test_deadline_does_not_accept_late_patch(swallow):
    observed = []

    async def worker(root, patch):
        observed.append(root)
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            if not swallow:
                raise
            await lab.fixture_worker(root, patch)

    with pytest.raises(TimeoutError):
        asyncio.run(lab.replay("correct", worker=worker, timeout=0.01))
    assert observed and not observed[0].exists()


@pytest.mark.parametrize("swallow", [False, True])
def test_caller_cancellation_cleans_up(swallow):
    async def run():
        ready = asyncio.Event()
        observed = []

        async def worker(root, patch):
            observed.append(root)
            ready.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                if not swallow:
                    raise
                await lab.fixture_worker(root, patch)

        task = asyncio.create_task(lab.replay("correct", worker=worker))
        await ready.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert observed and not observed[0].exists()

    asyncio.run(run())


def test_worker_failure_cleans_up():
    observed = []

    async def worker(root, _patch):
        observed.append(root)
        raise OSError("fixture failure")

    with pytest.raises(ContractError, match="fixture worker failed"):
        asyncio.run(lab.replay("correct", worker=worker))
    assert observed and not observed[0].exists()


def test_learner_cli():
    command = [sys.executable, "-m", lab.__name__]
    first = subprocess.check_output(command)
    assert first == subprocess.check_output(command)
    correct, misleading = json.loads(first)
    assert correct["decision"]["verdict"] == "approve"
    assert misleading["decision"]["verdict"] == "reject"
