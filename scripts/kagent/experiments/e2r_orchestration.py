"""Bounded offline planner/reviewer orchestration over correlated task results."""

from __future__ import annotations

import asyncio
import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

from scripts.kagent.experiments.contracts import (
    ContractError,
    validate_planner_artifact,
    validate_reviewer_artifact,
)

PLANNER = "planner-agent"
REVIEWER = "reviewer-agent"


@dataclass(frozen=True)
class Subtask:
    """Result from a runner that verifies wire request and task correlation."""

    agent: str
    state: str
    request_id: str
    task_id: str
    artifact: dict[str, Any] | None
    message_id: str | None = None


@dataclass(frozen=True)
class Decision:
    verdict: Literal["approve", "reject"]
    revisions: int
    subtasks: tuple[Subtask, ...]


type Invoke = Callable[[str, dict[str, Any], float], Awaitable[Subtask]]


async def coordinate(request: str, invoke: Invoke, *, timeout: float) -> Decision:
    """Run at most four correlated subtasks within one monotonic deadline."""
    if not math.isfinite(timeout) or timeout <= 0:
        raise ContractError("timeout must be finite and positive")

    clock = asyncio.get_running_loop().time
    deadline = clock() + timeout
    subtasks: list[Subtask] = []
    seen: dict[str, set[str]] = {
        "request_id": set(),
        "task_id": set(),
        "message_id": set(),
    }

    async def call(agent: str, payload: dict[str, Any]) -> dict[str, Any]:
        remaining = deadline - clock()
        if remaining <= 0:
            raise TimeoutError("orchestration deadline expired")
        result = await invoke(agent, payload, remaining)
        if clock() >= deadline:
            raise TimeoutError("orchestration deadline expired")
        if result.agent != agent or result.state != "completed":
            raise ContractError("subtask must complete under the expected agent identity")
        for field, identities in seen.items():
            identity = getattr(result, field)
            if field == "message_id" and identity is None:
                continue
            if not isinstance(identity, str) or not identity.strip() or identity in identities:
                raise ContractError(f"missing or duplicate subtask {field}")
            identities.add(identity)
        if result.artifact is None:
            raise ContractError("subtask artifact is missing")
        subtasks.append(result)
        validator = validate_planner_artifact if agent == PLANNER else validate_reviewer_artifact
        return validator(result.artifact)

    async with asyncio.timeout_at(deadline):
        plan = await call(PLANNER, {"request": request})
        review = await call(REVIEWER, {"request": request, "proposed_plan": plan})
        if review["verdict"] == "approve":
            return Decision("approve", 0, tuple(subtasks))

        plan = await call(PLANNER, {"request": request, "plan": plan, "feedback": review})
        review = await call(REVIEWER, {"request": request, "proposed_plan": plan})
        verdict = "approve" if review["verdict"] == "approve" else "reject"
        return Decision(verdict, 1, tuple(subtasks))
