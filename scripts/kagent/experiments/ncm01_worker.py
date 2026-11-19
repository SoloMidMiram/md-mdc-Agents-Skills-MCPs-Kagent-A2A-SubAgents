"""Bounded offline summarization for the NCM-01 experiment."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
from typing import Protocol

from scripts.kagent.experiments.contracts import ContractError

MAX_INPUT_BYTES = 8192
MAX_OUTPUT_BYTES = 512
MAX_TIMEOUT_SECONDS = 5.0
FIXTURE = (
    "A synthetic review found a stale context digest.\n"
    "The reviewer must reject stale digests and request a fresh packet."
)
FAKE_SUMMARY = "Reject the stale context digest and request a fresh packet."


class Backend(Protocol):
    async def __call__(self, text: str, *, max_output_bytes: int) -> str:
        """Return a complete summary and propagate cancellation promptly."""


class SummaryError(ContractError):
    """A bounded worker failure with a stable diagnostic code."""


def _check_text(text: object, limit: int, field: str) -> None:
    if not isinstance(text, str) or not text:
        raise SummaryError(f"invalid_{field}")
    if len(text) > limit:
        raise SummaryError(f"oversize_{field}")
    try:
        size = len(text.encode("utf-8"))
    except UnicodeError:
        raise SummaryError(f"invalid_{field}") from None
    if size > limit:
        raise SummaryError(f"oversize_{field}")
    if not text.strip() or "\x00" in text:
        raise SummaryError(f"invalid_{field}")


class Worker:
    """Admit one call at a time on a single event loop."""

    def __init__(self, backend: Backend | None) -> None:
        self._backend = backend
        self._busy = False

    async def summarize(
        self,
        text: str,
        *,
        max_output_bytes: int = MAX_OUTPUT_BYTES,
        timeout: float = MAX_TIMEOUT_SECONDS,
    ) -> str:
        _check_text(text, MAX_INPUT_BYTES, "input")
        if type(max_output_bytes) is not int or not 1 <= max_output_bytes <= MAX_OUTPUT_BYTES:
            raise SummaryError("invalid_output_limit")
        if (
            type(timeout) not in (int, float)
            or not 0 < timeout <= MAX_TIMEOUT_SECONDS
            or not math.isfinite(timeout)
        ):
            raise SummaryError("invalid_timeout")
        if self._backend is None:
            raise SummaryError("missing_model")
        if self._busy:
            raise SummaryError("worker_busy")

        self._busy = True
        task = asyncio.current_task()
        cancellation_count = task.cancelling() if task else 0
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        try:
            async with asyncio.timeout_at(deadline):
                output = await self._backend(text, max_output_bytes=max_output_bytes)
        except Exception as exc:
            if task and task.cancelling() > cancellation_count:
                raise asyncio.CancelledError from None
            if loop.time() >= deadline:
                raise SummaryError("timeout") from None
            if isinstance(exc, SummaryError) and str(exc) in (
                "no_complete_line_fits",
                "unknown_fake_fixture",
                "oversize_output",
            ):
                raise
            raise SummaryError("backend_failure") from None
        else:
            if task and task.cancelling() > cancellation_count:
                raise asyncio.CancelledError
            if loop.time() >= deadline:
                raise SummaryError("timeout")
        finally:
            self._busy = False
        _check_text(output, max_output_bytes, "output")
        return output


async def fake_backend(text: str, *, max_output_bytes: int) -> str:
    """Return the predeclared answer for the single synthetic smoke fixture."""
    if text != FIXTURE:
        raise SummaryError("unknown_fake_fixture")
    _check_text(FAKE_SUMMARY, max_output_bytes, "output")
    return FAKE_SUMMARY


async def extractive_baseline(text: str, *, max_output_bytes: int) -> str:
    """Select the longest fitting prefix of complete nonblank LF-delimited lines."""
    lines: list[str] = []
    budget = max_output_bytes
    for line in text.split("\n"):
        if not line.strip():
            continue
        cost = len(line.encode("utf-8")) + bool(lines)
        if cost > budget:
            break
        budget -= cost
        lines.append(line)
    if not lines:
        raise SummaryError("no_complete_line_fits")
    return "\n".join(lines)


async def smoke() -> dict[str, object]:
    return {
        "origin": "synthetic",
        "capabilityPromotion": False,
        "inputSha256": hashlib.sha256(FIXTURE.encode("utf-8")).hexdigest(),
        "fakeSummary": await Worker(fake_backend).summarize(FIXTURE),
        "extractiveSummary": await Worker(extractive_baseline).summarize(
            FIXTURE, max_output_bytes=64
        ),
        "realRun": {"status": "blocked", "reason": "requires separate authorization"},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--missing-model", action="store_true")
    args = parser.parse_args()
    try:
        if args.missing_model:
            asyncio.run(Worker(None).summarize(FIXTURE))
        print(json.dumps(asyncio.run(smoke()), sort_keys=True, indent=2))
        return 0
    except SummaryError as exc:
        parser.exit(1, f"NCM-01 failed: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
