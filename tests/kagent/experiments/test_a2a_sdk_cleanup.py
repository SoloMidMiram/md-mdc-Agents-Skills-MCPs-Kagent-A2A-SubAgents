"""Real SDK transport cleanup failures must not become successful execution."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from test_a2a_sdk_interop import _card_payload, interop


def test_response_close_exception_preserves_hooks_and_redacts_error():
    closed = []

    class CloseFailure(httpx.AsyncByteStream):
        def __init__(self, request_id):
            self.request_id = request_id

        async def __aiter__(self):
            event = {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "result": {
                    "kind": "status-update",
                    "taskId": "task-cleanup",
                    "contextId": "context-cleanup",
                    "status": {"state": "completed"},
                    "final": True,
                },
            }
            yield ("data: " + json.dumps(event) + "\n\n").encode()

        async def aclose(self):
            closed.append(True)
            raise RuntimeError("token=cleanup-sensitive-marker")

    async def scenario():
        async def handler(request):
            request_id = json.loads(request.content)["id"]
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                stream=CloseFailure(request_id),
            )

        async def caller_hook(response):
            pass

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), event_hooks={"response": [caller_hook]}
        ) as client:
            card = interop.build_official_agent_card(
                _card_payload(), endpoint="http://test:8083/api/a2a/kagent/k8s-a2a-agent"
            )
            with pytest.raises(interop.DispatchError) as error:
                await interop.dispatch_read_only_task(
                    client, card, prompt="ACK", requested_protocol_version="0.3.0", timeout=5
                )
            assert closed == [True]
            assert client.event_hooks["response"] == [caller_hook]
            assert error.value.observation.outcome == "invalid"
            assert error.value.observation.task_id == "task-cleanup"
            assert "cleanup-sensitive-marker" not in str(error.value)
            report = interop._report_base(interop._parser().parse_args([]))
            interop._apply_observation(report, error.value.observation)
            assert report["outcomes"]["executionCompleted"] is False
            assert report["decision"]["passed"] is False

    asyncio.run(scenario())
