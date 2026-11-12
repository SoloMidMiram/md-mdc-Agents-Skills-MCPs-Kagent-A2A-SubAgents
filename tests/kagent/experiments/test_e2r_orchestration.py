"""Exercise the bounded coordinator without transport or model calls."""

import asyncio
from dataclasses import replace

import pytest

from scripts.kagent.experiments.e2r_orchestration import (
    PLANNER,
    REVIEWER,
    ContractError,
    Subtask,
    coordinate,
)

PLAN = {
    "goal": "example",
    "constraints": [],
    "files": [],
    "acceptance_criteria": [],
    "tests": [],
    "risks": [],
}


def task(agent, index, verdict="approve"):
    artifact = (
        PLAN
        if agent == PLANNER
        else {
            "verdict": verdict,
            "findings": [],
            "missing_requirements": [],
            "required_changes": [],
        }
    )
    return Subtask(agent, "completed", f"r{index}", f"t{index}", artifact, f"m{index}")


@pytest.mark.parametrize(
    ("reviews", "expected"),
    [
        (["approve"], "approve"),
        (["revise", "approve"], "approve"),
        (["revise", "revise"], "reject"),
    ],
)
def test_sequence(reviews, expected):
    calls = []
    budgets = []

    async def invoke(agent, payload, remaining):
        index = len(calls)
        calls.append((agent, payload))
        budgets.append(remaining)
        return task(agent, index, reviews[index // 2])

    decision = asyncio.run(coordinate("original", invoke, timeout=1))
    assert decision.verdict == expected
    assert decision.revisions == len(reviews) - 1
    assert [agent for agent, _ in calls] == [PLANNER, REVIEWER] * len(reviews)
    assert all(payload["request"] == "original" for _, payload in calls)
    assert budgets == sorted(budgets, reverse=True)
    assert [result.message_id for result in decision.subtasks] == [
        f"m{i}" for i in range(len(calls))
    ]
    if len(reviews) == 2:
        assert calls[2][1]["feedback"]["verdict"] == "revise"


@pytest.mark.parametrize(
    ("index", "change"),
    [
        (0, {"artifact": None}),
        (1, {"artifact": None}),
        (2, {"artifact": None}),
        (1, {"agent": PLANNER}),
        (1, {"state": "working"}),
        (1, {"task_id": "t0"}),
        (1, {"request_id": ""}),
        (1, {"message_id": "m0"}),
        (1, {"artifact": {"verdict": "unknown"}}),
    ],
)
def test_invalid_result_stops_dispatch(index, change):
    calls = []

    async def invoke(agent, payload, remaining):
        position = len(calls)
        calls.append(agent)
        result = task(agent, position, "revise")
        return replace(result, **change) if position == index else result

    with pytest.raises(ContractError):
        asyncio.run(coordinate("original", invoke, timeout=1))
    assert len(calls) == index + 1


@pytest.mark.parametrize("cancel", [False, True])
def test_interrupted_invocation_cannot_approve(cancel):
    async def invoke(agent, payload, remaining):
        if cancel:
            raise asyncio.CancelledError
        await asyncio.Event().wait()

    expected = asyncio.CancelledError if cancel else TimeoutError
    with pytest.raises(expected):
        asyncio.run(coordinate("original", invoke, timeout=0.02))


def test_adapter_reuses_runner_and_preserves_correlated_ids(monkeypatch):
    from scripts.kagent.experiments import run_e2r_example
    from scripts.kagent.experiments.run_a2a_example import ExampleRunResult

    calls = []

    def fake_runner(**kwargs):
        agent = kwargs["agent"]
        result = task(agent, len(calls))
        calls.append(kwargs)
        return ExampleRunResult(
            example="example",
            agent=agent,
            namespace=kwargs["namespace"],
            controller=kwargs["controller"],
            task_id=result.task_id,
            dispatch_state=result.state,
            duration_ms=0,
            pass_=True,
            reason="fixture",
            request_id=result.request_id,
            artifact=result.artifact,
            message_id=result.message_id,
        )

    monkeypatch.setattr(run_e2r_example, "run_example", fake_runner)
    decision = asyncio.run(
        run_e2r_example.run_e2r_example(
            "original", controller="http://localhost", namespace="lab", timeout=1
        )
    )
    assert decision.verdict == "approve"
    assert [entry.request_id for entry in decision.subtasks] == ["r0", "r1"]
    assert [entry.task_id for entry in decision.subtasks] == ["t0", "t1"]
    assert [entry.message_id for entry in decision.subtasks] == ["m0", "m1"]
    assert all(call["skip_contract"] is False for call in calls)
