import asyncio
import json
import subprocess
import sys

import pytest

from scripts.kagent.experiments import ncm01_worker as lab


def test_smoke_repeats():
    result = asyncio.run(lab.smoke())
    assert asyncio.run(lab.smoke()) == result
    assert result["fakeSummary"] == lab.FAKE_SUMMARY
    assert result["extractiveSummary"] == lab.FIXTURE.split("\n")[0]
    assert result["origin"] == "synthetic"
    assert result["capabilityPromotion"] is False
    assert result["realRun"] == {
        "status": "blocked",
        "reason": "requires separate authorization",
    }


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "invalid_input"),
        (" \n", "invalid_input"),
        ("\x00", "invalid_input"),
        ("\ud800", "invalid_input"),
        ("\u00e9" * 4097, "oversize_input"),
    ],
)
def test_bad_input_is_rejected_before_dispatch(text, message):
    async def unexpected(*args, **kwargs):
        pytest.fail("invalid input dispatched")

    with pytest.raises(lab.SummaryError, match=message):
        asyncio.run(lab.Worker(unexpected).summarize(text))


@pytest.mark.parametrize(
    ("output", "message"),
    [
        ("", "invalid_output"),
        (" \n", "invalid_output"),
        ({"summary": "wrong type"}, "invalid_output"),
        ("\ud800", "invalid_output"),
        ("\u00e9" * 3, "oversize_output"),
    ],
)
def test_bad_output_is_rejected(output, message):
    async def backend(text, *, max_output_bytes):
        assert text == lab.FIXTURE
        assert max_output_bytes == 5
        return output

    with pytest.raises(lab.SummaryError, match=message):
        asyncio.run(lab.Worker(backend).summarize(lab.FIXTURE, max_output_bytes=5))


def test_baseline_never_cuts_a_line():
    worker = lab.Worker(lab.extractive_baseline)
    assert asyncio.run(worker.summarize("\u00e9!\nMore text", max_output_bytes=3)) == "\u00e9!"
    with pytest.raises(lab.SummaryError, match="no_complete_line_fits"):
        asyncio.run(worker.summarize("\u00e9!", max_output_bytes=2))


@pytest.mark.parametrize("late", [False, True])
def test_deadline_blocks_late_output_and_cleans_up(late):
    async def run():
        cleaned = asyncio.Event()

        async def backend(text, *, max_output_bytes):
            if text == "next":
                return "ready"
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                if late:
                    return "late"
                raise
            finally:
                cleaned.set()

        worker = lab.Worker(backend)
        with pytest.raises(lab.SummaryError, match=r"^timeout$"):
            await worker.summarize(lab.FIXTURE, timeout=0.01)
        assert cleaned.is_set()
        assert await worker.summarize("next") == "ready"

    asyncio.run(run())


@pytest.mark.parametrize("suppress", [False, True])
def test_busy_and_caller_cancellation(suppress):
    async def run():
        entered = asyncio.Event()
        calls = []

        async def backend(text, *, max_output_bytes):
            calls.append(text)
            if text == "held":
                entered.set()
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    if not suppress:
                        raise
            return "ready"

        worker = lab.Worker(backend)
        task = asyncio.create_task(worker.summarize("held"))
        await entered.wait()
        with pytest.raises(lab.SummaryError, match="worker_busy"):
            await worker.summarize("blocked")
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert await worker.summarize("next") == "ready"
        assert calls == ["held", "next"]

    asyncio.run(run())


def test_backend_failure_is_sanitized():
    async def backend(text, *, max_output_bytes):
        raise TimeoutError("sensitive backend payload")

    with pytest.raises(lab.SummaryError, match=r"^backend_failure$"):
        asyncio.run(lab.Worker(backend).summarize(lab.FIXTURE))


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), 5.01, True])
def test_invalid_timeout(timeout):
    with pytest.raises(lab.SummaryError, match="invalid_timeout"):
        asyncio.run(lab.Worker(lab.fake_backend).summarize(lab.FIXTURE, timeout=timeout))


def test_cli_and_missing_model():
    command = [sys.executable, "-m", "scripts.kagent.experiments.ncm01_worker"]
    passed = subprocess.run(command, capture_output=True, check=True)
    assert json.loads(passed.stdout) == asyncio.run(lab.smoke())
    assert not passed.stderr
    failed = subprocess.run([*command, "--missing-model"], capture_output=True, check=False)
    assert failed.returncode == 1
    assert not failed.stdout
    assert b"missing_model" in failed.stderr


def test_timeout_retains_admission_until_backend_cleanup():
    async def run():
        cleaning = asyncio.Event()
        release = asyncio.Event()
        calls = []

        async def backend(text, *, max_output_bytes):
            calls.append(text)
            if text == "held":
                try:
                    await asyncio.Future()
                finally:
                    cleaning.set()
                    await release.wait()
            return "ready"

        worker = lab.Worker(backend)
        task = asyncio.create_task(worker.summarize("held", timeout=0.01))
        try:
            await asyncio.wait_for(cleaning.wait(), timeout=2)
            assert not task.done()
            with pytest.raises(lab.SummaryError, match="worker_busy"):
                await worker.summarize("blocked")
            assert calls == ["held"]
        finally:
            release.set()
            with pytest.raises(lab.SummaryError, match=r"^timeout$"):
                await asyncio.wait_for(task, timeout=2)

        assert await worker.summarize("next") == "ready"
        assert calls == ["held", "next"]

    asyncio.run(run())


def test_caller_cancellation_wins_over_backend_cleanup_error():
    async def run():
        entered = asyncio.Event()

        async def backend(text, *, max_output_bytes):
            entered.set()
            try:
                await asyncio.Future()
            except asyncio.CancelledError:
                raise RuntimeError("cleanup detail") from None

        task = asyncio.create_task(lab.Worker(backend).summarize("held"))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run())
