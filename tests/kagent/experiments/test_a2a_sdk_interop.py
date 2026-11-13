"""Tests for the isolated official Python A2A SDK interoperability experiment."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("a2a")
httpx = pytest.importorskip("httpx")

ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = ROOT / "scripts" / "kagent" / "experiments" / "a2a_sdk_interop.py"
spec = importlib.util.spec_from_file_location("a2a_sdk_interop", SCRIPT_PATH)
assert spec is not None and spec.loader is not None
interop = importlib.util.module_from_spec(spec)
sys.modules["a2a_sdk_interop"] = interop
spec.loader.exec_module(interop)


def _card_payload(protocol_version: str | None = "0.3.0") -> dict[str, Any]:
    data: dict[str, Any] = {
        "accepted": True,
        "deploymentReady": True,
        "model": "test-model",
        "modelProvider": "test-provider",
        "agent": {
            "metadata": {"namespace": "kagent", "name": "k8s-a2a-agent"},
            "spec": {
                "description": "read-only test agent",
                "declarative": {
                    "a2aConfig": {
                        "skills": [
                            {
                                "id": "get-resources-skill",
                                "name": "Get Resources",
                                "description": "Read resources",
                                "tags": ["k8s"],
                            }
                        ]
                    }
                },
            },
        },
    }
    if protocol_version is not None:
        data["protocolVersion"] = protocol_version
    return {"error": False, "data": data}


def test_card_is_adapted_to_official_sdk_model() -> None:
    card = interop.build_official_agent_card(
        _card_payload(),
        endpoint="http://127.0.0.1:8083/api/a2a/kagent/k8s-a2a-agent",
    )

    assert card.agent_name == "kagent/k8s-a2a-agent"
    assert card.card.name == "k8s-a2a-agent"
    assert card.card.protocol_version == "0.3.0"
    assert card.skill_ids == ("get-resources-skill",)
    assert card.protocol_version_source == "agent-card"


def test_agent_card_discovery_uses_existing_kagent_endpoint() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/agents/kagent/k8s-a2a-agent"
        return httpx.Response(200, json=_card_payload(), request=request)

    async def scenario() -> Any:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            return await interop.discover_agent_card(
                http_client,
                controller="http://test:8083",
                namespace="kagent",
                agent="k8s-a2a-agent",
                fallback_protocol_version="0.3.0",
            )

    card = asyncio.run(scenario())
    assert card.agent_name == "kagent/k8s-a2a-agent"
    assert card.card.url == "http://test:8083/api/a2a/kagent/k8s-a2a-agent"


def test_controller_profile_fills_kagent_card_protocol_gap() -> None:
    card = interop.build_official_agent_card(
        _card_payload(protocol_version=None),
        endpoint="http://127.0.0.1:8083/api/a2a/kagent/k8s-a2a-agent",
        fallback_protocol_version="0.3.0",
    )

    assert card.protocol_version == "0.3.0"
    assert card.protocol_version_source == "kagent-controller-compatibility-profile"


def test_unsupported_protocol_version_is_explicit() -> None:
    with pytest.raises(interop.ProtocolCompatibilityError, match="unsupported"):
        interop.validate_protocol_compatibility("0.3.0", "1.0")


def test_unsupported_version_stops_before_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    args = interop._parser().parse_args(["--protocol-version", "1.0", "--output", "json"])
    card = interop.build_official_agent_card(
        _card_payload(),
        endpoint="http://127.0.0.1:8083/api/a2a/kagent/k8s-a2a-agent",
    )
    dispatched = False

    async def fake_discovery(*args: Any, **kwargs: Any) -> Any:
        return card

    async def fake_dispatch(*args: Any, **kwargs: Any) -> Any:
        nonlocal dispatched
        dispatched = True
        raise AssertionError("dispatch must not run after protocol rejection")

    monkeypatch.setattr(interop, "discover_agent_card", fake_discovery)
    monkeypatch.setattr(interop, "dispatch_read_only_task", fake_dispatch)
    report, exit_code = asyncio.run(interop.execute(args))

    assert exit_code == 1
    assert dispatched is False
    assert report["compatibility"]["validatedBeforeDispatch"] is True
    assert "unsupported A2A protocol version" in report["decision"]["reason"]


def test_official_sdk_stream_records_task_and_status_correlation() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        request_id = body["id"]
        assert body["jsonrpc"] == "2.0"
        assert body["method"] == "message/stream"
        assert request.headers["A2A-Version"] == "0.3"
        assert body["params"]["message"]["messageId"]
        events = [
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "kind": "status-update",
                    "contextId": "ctx-test",
                    "taskId": "task-test",
                    "final": False,
                    "status": {"state": "submitted"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "kind": "status-update",
                    "contextId": "ctx-test",
                    "taskId": "task-test",
                    "final": False,
                    "status": {"state": "working"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "kind": "status-update",
                    "contextId": "ctx-test",
                    "taskId": "task-test",
                    "final": True,
                    "status": {"state": "completed"},
                },
            },
        ]
        content = "".join(f"data: {json.dumps(event)}\n\n" for event in events)

        class Stream(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield content.encode()

            async def aclose(self) -> None:
                return None

        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=Stream(),
            request=request,
        )

    async def scenario() -> Any:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as http_client:
            card = interop.build_official_agent_card(
                _card_payload(),
                endpoint="http://test/api/a2a/kagent/k8s-a2a-agent",
            )
            return await interop.dispatch_read_only_task(
                http_client,
                card,
                prompt="List pods",
                requested_protocol_version="0.3.0",
                timeout=5.0,
            )

    observation = asyncio.run(scenario())
    assert observation.task_id == "task-test"
    assert [item.state for item in observation.status_transitions] == [
        "submitted",
        "working",
        "completed",
    ]
    assert observation.request_id
    assert observation.response_ids == (observation.request_id,) * 3
    assert observation.response_error_codes == ()
    assert observation.http_status == 200
