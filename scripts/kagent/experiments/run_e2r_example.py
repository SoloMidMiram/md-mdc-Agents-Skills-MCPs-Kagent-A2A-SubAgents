"""Adapt the shared educational A2A runner to the E2-R coordinator."""

import asyncio
import json
from threading import Event
from time import monotonic
from typing import Any

from scripts.kagent.experiments.e2r_orchestration import (
    ContractError,
    Decision,
    Subtask,
    coordinate,
)
from scripts.kagent.experiments.run_a2a_example import run_example


async def run_e2r_example(
    request: str, *, controller: str, namespace: str, timeout: float
) -> Decision:
    """Run E2-R through the existing runner and its wire-correlation checks."""

    async def invoke(agent: str, payload: dict[str, Any], remaining: float) -> Subtask:
        stopped = Event()
        deadline = monotonic() + remaining

        def before_dispatch() -> float:
            budget = deadline - monotonic()
            if stopped.is_set() or budget <= 0:
                raise ContractError("E2-R stopped before dispatch")
            return budget

        try:
            result = await asyncio.to_thread(
                run_example,
                agent=agent,
                prompt=json.dumps(payload, ensure_ascii=False),
                controller=controller,
                namespace=namespace,
                example=None,
                timeout=remaining,
                skip_contract=False,
                before_dispatch=before_dispatch,
            )
        finally:
            stopped.set()
        if not result.pass_ or result.namespace != namespace:
            raise ContractError("A2A example did not pass for the expected namespace")
        return Subtask(
            agent=result.agent,
            state=result.dispatch_state or "",
            request_id=result.request_id or "",
            task_id=result.task_id or "",
            artifact=result.artifact,
            message_id=result.message_id,
        )

    return await coordinate(request, invoke, timeout=timeout)
