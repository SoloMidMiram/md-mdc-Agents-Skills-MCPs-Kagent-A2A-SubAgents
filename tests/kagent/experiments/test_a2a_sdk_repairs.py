"""Additional lifecycle and shape coverage absent from the preserved 47 cases."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
import test_a2a_sdk_transport as fixture
from test_a2a_sdk_interop import _card_payload, interop


def install_events(monkeypatch, factory):
    monkeypatch.setattr(fixture, "events_for", lambda mode, request_id: (factory(request_id), ""))


def full_task(request_id, state="completed"):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "kind": "task",
            "id": "task-local",
            "contextId": "ctx-local",
            "status": {"state": state},
            "artifacts": [{"artifactId": "a1", "parts": [{"kind": "text", "text": "ACK"}]}],
        },
    }


@pytest.mark.parametrize("shape", ["terminal_task", "artifact_then_status"])
def test_protocol_specific_terminal_shapes(monkeypatch, shape):
    def events(request_id):
        if shape == "terminal_task":
            return [full_task(request_id)]
        return [
            fixture.status(request_id, "working"),
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "kind": "artifact-update",
                    "taskId": "task-local",
                    "contextId": "ctx-local",
                    "artifact": {"artifactId": "a1", "parts": [{"kind": "text", "text": "ACK"}]},
                    "lastChunk": True,
                },
            },
            fixture.status(request_id, "completed", final=True),
        ]

    install_events(monkeypatch, events)
    with fixture.controller() as server:
        # Cold SDK imports count toward the overall deadline on mounted filesystems.
        observation = asyncio.run(fixture.dispatch_at(server.url, timeout=5))
    assert observation.outcome == "completed"
    assert observation.dispatch_accepted is True
    assert observation.wire_valid is True
    assert "ACK" in observation.response_text


def test_events_after_terminal_task_are_rejected(monkeypatch):
    install_events(
        monkeypatch,
        lambda request_id: [
            full_task(request_id),
            fixture.status(request_id, "failed", final=True),
        ],
    )
    with fixture.controller() as server, pytest.raises(interop.DispatchError) as error:
        asyncio.run(fixture.dispatch_at(server.url))
    assert error.value.observation.outcome == "invalid"


@pytest.mark.parametrize("state", ["input-required", "auth-required"])
def test_final_interrupted_execution_is_not_completion(monkeypatch, state):
    install_events(monkeypatch, lambda request_id: [fixture.status(request_id, state, final=True)])
    with fixture.controller() as server, pytest.raises(interop.DispatchError) as error:
        asyncio.run(fixture.dispatch_at(server.url))
    assert error.value.observation.outcome == "incomplete"
    assert error.value.observation.final_state == state
    assert error.value.observation.dispatch_accepted is True


@pytest.mark.parametrize(
    "mode,outcome",
    [
        ("failed", "failed"),
        ("canceled", "canceled"),
        ("rejected", "rejected"),
        ("incomplete", "incomplete"),
        ("missing_rpc", "invalid"),
        ("error_after_valid", "invalid"),
        ("deadline", "timed_out"),
    ],
)
def test_partial_failure_observations_remain_recordable(mode, outcome):
    with fixture.controller(mode) as server:
        args = interop._parser().parse_args(
            ["--controller", server.url, "--timeout", "0.1" if mode == "deadline" else "2"]
        )
        report, code = asyncio.run(interop.execute(args))
    assert code != 0
    assert report["decision"]["passed"] is False
    assert report["outcomes"]["execution"] == outcome
    assert report["outcomes"]["executionCompleted"] is False
    if mode != "deadline":
        assert report["outcomes"]["transportEstablished"] is True
        assert report["outcomes"]["dispatchAccepted"] is (mode != "missing_rpc")
        assert report["response"]["statusTransitions"]
    if mode == "error_after_valid":
        assert report["response"]["errorCodes"] == [-32603]
        assert report["request"]["requestId"]
    assert "synthetic-sensitive-value" not in json.dumps(report)


@pytest.mark.parametrize("mode", ["valid", "error_after_valid", "timeout", "cancel"])
def test_owned_hook_and_tasks_are_cleaned_on_every_exit(mode):
    async def scenario(server):
        async def existing_hook(response):
            return None

        async with httpx.AsyncClient(
            trust_env=False, event_hooks={"response": [existing_hook]}
        ) as client:
            card = interop.build_official_agent_card(
                _card_payload(), endpoint=server.url + "/api/a2a/kagent/k8s-a2a-agent"
            )
            previous = list(client.event_hooks["response"])
            existing_tasks = asyncio.all_tasks()
            task = asyncio.create_task(
                interop.dispatch_read_only_task(
                    client, card, prompt="ACK", requested_protocol_version="0.3.0", timeout=0.1
                )
            )
            if mode == "cancel":
                assert await asyncio.to_thread(server.entered.wait, 2)
                task.cancel()
                with pytest.raises(asyncio.CancelledError) as cancellation:
                    await task
                assert task.cancelled()
                assert cancellation.value.observation.outcome == "canceled"
            elif mode in {"error_after_valid", "timeout"}:
                with pytest.raises(interop.DispatchError):
                    await task
            else:
                await task
            assert client.event_hooks["response"] == previous
            finalizers = asyncio.all_tasks() - existing_tasks
            if finalizers:
                # Pinned SDK schedules async-generator finalization on error.
                # Wait for actual quiescence, without canceling or hiding tasks.
                _, pending = await asyncio.wait(finalizers, timeout=0.5)
                assert not pending
            assert asyncio.all_tasks() == existing_tasks

    with fixture.controller(mode) as server:
        asyncio.run(scenario(server))


def test_discovery_is_inside_operation_deadline(monkeypatch):
    original = interop.discover_agent_card

    async def delayed(*args, **kwargs):
        await asyncio.sleep(0.2)
        return await original(*args, **kwargs)

    monkeypatch.setattr(interop, "discover_agent_card", delayed)
    with fixture.controller() as server:
        args = interop._parser().parse_args(["--controller", server.url, "--timeout", "0.03"])
        report, code = asyncio.run(interop.execute(args))
    assert code == 3
    assert report["outcomes"]["execution"] == "timed_out"
    assert report["outcomes"]["dispatchAccepted"] is False
    assert server.requests == []


def test_success_text_and_cli_fallback_are_redacted(monkeypatch, capsys):
    def events(request_id):
        event = fixture.status(request_id, "completed", final=True)
        event["result"]["status"]["message"] = {
            "role": "agent",
            "messageId": "m1",
            "parts": [{"kind": "text", "text": "token=synthetic-sensitive-value"}],
        }
        return [event]

    install_events(monkeypatch, events)
    with fixture.controller() as server:
        args = interop._parser().parse_args(["--controller", server.url])
        report, code = asyncio.run(interop.execute(args))
    assert code == 0
    assert "synthetic-sensitive-value" not in json.dumps(report)

    async def unexpected(args):
        raise RuntimeError("token=synthetic-sensitive-value")

    monkeypatch.setattr(interop, "execute", unexpected)
    assert interop.main(["--output", "json"]) == 1
    assert "synthetic-sensitive-value" not in capsys.readouterr().out


@pytest.mark.parametrize("timeout", ["0", "-1", "nan", "inf"])
def test_invalid_operation_budget_fails_before_network(timeout):
    args = interop._parser().parse_args(["--timeout", timeout])
    report, code = asyncio.run(interop.execute(args))
    assert code == 2
    assert report["decision"]["passed"] is False
    assert report["outcomes"]["executionCompleted"] is False


@pytest.mark.parametrize("skills", [None, [None], [{"id": "s", "tags": None}], [{"tags": []}]])
def test_malformed_card_containers_have_controlled_errors(skills):
    payload = _card_payload()
    payload["data"]["agent"]["spec"]["declarative"]["a2aConfig"]["skills"] = skills
    with pytest.raises(interop.CardError):
        interop.build_official_agent_card(
            payload, endpoint="http://localhost:8083/api/a2a/kagent/k8s-a2a-agent"
        )
