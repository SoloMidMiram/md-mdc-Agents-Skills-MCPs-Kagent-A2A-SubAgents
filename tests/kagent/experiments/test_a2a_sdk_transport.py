"""Qualification cases: real SDK over an ephemeral loopback HTTP/SSE fixture.

The six original tests are imported unchanged. No production endpoint is used.
"""

from __future__ import annotations

import asyncio
import copy
import importlib.util
import json
import sys
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from test_a2a_sdk_interop import _card_payload, interop


def status(request_id, state, *, task_id="task-local", final=False):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "kind": "status-update",
            "contextId": "ctx-local",
            "taskId": task_id,
            "final": final,
            "status": {"state": state},
        },
    }


def events_for(mode, request_id):
    events = [
        status(request_id, "submitted"),
        status(request_id, "working"),
        status(request_id, "completed", final=True),
    ]
    if mode == "wrong_rpc":
        events[-1]["id"] = "other-request"
    elif mode == "missing_rpc":
        for event in events:
            del event["id"]
    elif mode == "partially_missing_rpc":
        del events[1]["id"]
    elif mode == "empty_stream":
        events = []
    elif mode == "mixed_task":
        events[-1]["result"]["taskId"] = "other-task"
    elif mode == "missing_task":
        del events[1]["result"]["taskId"]
    elif mode == "empty_task":
        events[1]["result"]["taskId"] = ""
    elif mode == "incomplete":
        events.pop()
    elif mode == "not_final":
        events[-1]["result"]["final"] = False
    elif mode in {"failed", "canceled", "rejected", "input_required"}:
        events[-1] = status(request_id, mode, final=True)
    elif mode == "error_after_valid":
        events = [
            events[0],
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": "token=synthetic-sensitive-value"},
            },
        ]
    elif mode == "invalid_jsonrpc":
        events[-1]["jsonrpc"] = "1.0"
    elif mode == "trailing_malformed":
        return events, "data: {not-json}\n\n"
    elif mode == "oversized_tail":
        # Push an error beyond the experiment's wire-capture limit.
        padding = ":" + "x" * (interop.MAX_CAPTURED_RESPONSE_BYTES + 16) + "\n\n"
        error = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32603, "message": "late error"},
        }
        return events[:2], padding + "data: " + json.dumps(error) + "\n\n"
    return events, ""


@contextmanager
def controller(mode="valid", card=None):
    state = SimpleNamespace(
        requests=[], versions=[], entered=threading.Event(), stop=threading.Event()
    )

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def do_GET(self):
            state.requests.append(("GET", self.path, None))
            assert self.path == "/api/agents/kagent/k8s-a2a-agent"
            body = json.dumps(_card_payload() if card is None else card).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state.requests.append(("POST", self.path, body))
            state.entered.set()
            assert self.path == "/api/a2a/kagent/k8s-a2a-agent"
            assert body["method"] == "message/stream"
            state.versions.append(self.headers.get("A2A-Version"))
            assert self.headers.get("A2A-Version") in {None, "0.3"}
            request_id = body["id"]
            events, tail = events_for(mode, request_id)
            content = "".join("data: " + json.dumps(event) + "\n\n" for event in events) + tail
            try:
                if mode in {"timeout", "cancel"}:
                    state.stop.wait(0.5)
                if mode == "deadline":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Connection", "close")
                    self.end_headers()
                    for _ in range(12):
                        self.wfile.write(
                            ("data: " + json.dumps(status(request_id, "working")) + "\n\n").encode()
                        )
                        self.wfile.flush()
                        if state.stop.wait(0.025):
                            return
                    self.wfile.write(
                        (
                            "data: "
                            + json.dumps(status(request_id, "completed", final=True))
                            + "\n\n"
                        ).encode()
                    )
                    self.wfile.flush()
                    self.close_connection = True
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(content.encode())))
                self.end_headers()
                self.wfile.write(content.encode())
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass  # Expected when the real SDK cancels or times out.

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True
    )
    thread.start()
    state.url = f"http://127.0.0.1:{server.server_port}"
    try:
        yield state
    finally:
        state.stop.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()


async def dispatch_at(url, timeout=1):
    async with httpx.AsyncClient(trust_env=False, timeout=timeout) as client:
        card = await interop.discover_agent_card(
            client,
            controller=url,
            namespace="kagent",
            agent="k8s-a2a-agent",
            fallback_protocol_version="0.3.0",
        )
        return await interop.dispatch_read_only_task(
            client,
            card,
            prompt="Reply ACK. Do not call tools.",
            requested_protocol_version="0.3.0",
            timeout=timeout,
        )


def test_real_sdk_loopback_lifecycle():
    with controller() as server:
        result = asyncio.run(dispatch_at(server.url))
    assert result.task_id == "task-local"
    assert result.final_state == "completed"
    assert [item.state for item in result.status_transitions] == [
        "submitted",
        "working",
        "completed",
    ]
    assert result.response_ids == (result.request_id,) * 3
    assert [method for method, _, _ in server.requests] == ["GET", "POST"]
    assert server.versions == ["0.3"]  # Legacy helper intentionally lacks this header.


@pytest.mark.parametrize(
    "mode",
    [
        "wrong_rpc",
        "missing_rpc",
        "mixed_task",
        "missing_task",
        "empty_task",
        "incomplete",
        "not_final",
        "failed",
        "canceled",
        "rejected",
        "input_required",
        "error_after_valid",
        "invalid_jsonrpc",
        "trailing_malformed",
        "oversized_tail",
        "partially_missing_rpc",
        "empty_stream",
    ],
)
def test_real_sdk_rejects_invalid_or_incomplete_stream(mode):
    with controller(mode) as server, pytest.raises(interop.DispatchError):
        asyncio.run(dispatch_at(server.url))


@pytest.mark.parametrize("mode", ["timeout", "deadline"])
def test_real_sdk_timeout(mode):
    with controller(mode) as server, pytest.raises(interop.DispatchError):
        asyncio.run(dispatch_at(server.url, timeout=0.1))


def test_real_sdk_cancellation_propagates():
    async def scenario(server):
        task = asyncio.create_task(dispatch_at(server.url))
        assert await asyncio.to_thread(server.entered.wait, 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    with controller("cancel") as server:
        asyncio.run(scenario(server))


def test_real_sdk_connection_failure():
    with controller() as server:
        unused_url = server.url
    card = interop.build_official_agent_card(
        _card_payload(), endpoint=unused_url + "/api/a2a/kagent/k8s-a2a-agent"
    )

    async def scenario():
        async with httpx.AsyncClient(trust_env=False) as client:
            await interop.dispatch_read_only_task(
                client,
                card,
                prompt="ACK",
                requested_protocol_version="0.3.0",
                timeout=0.2,
            )

    with pytest.raises(interop.DispatchError):
        asyncio.run(scenario())


@pytest.mark.parametrize("variant", ["empty", "not_ready", "no_identity", "bad_skills"])
def test_malformed_card_is_rejected(variant):
    card = _card_payload()
    if variant == "empty":
        card = {}
    elif variant == "not_ready":
        card["data"]["accepted"] = False
    elif variant == "no_identity":
        card["data"]["agent"]["metadata"] = {}
    else:
        card["data"]["agent"]["spec"]["declarative"]["a2aConfig"]["skills"] = [
            {"id": "bad", "tags": None}
        ]
    with pytest.raises(interop.CardError):
        interop.build_official_agent_card(
            card, endpoint="http://localhost:8083/api/a2a/kagent/k8s-a2a-agent"
        )


def test_wrong_agent_card_stops_before_dispatch():
    card = _card_payload()
    card["data"]["agent"]["metadata"]["name"] = "unrequested-agent"
    with controller(card=card) as server, pytest.raises(interop.CardError):
        asyncio.run(dispatch_at(server.url))
    assert [method for method, _, _ in server.requests] == ["GET"]


@pytest.mark.parametrize("mode", ["incomplete", "failed", "error_after_valid"])
def test_failed_execution_has_no_false_success_or_secret(mode):
    with controller(mode) as server:
        args = interop._parser().parse_args(
            [
                "--controller",
                server.url,
                "--prompt",
                "Reply ACK. Do not call tools.",
                "--timeout",
                "1",
                "--output",
                "json",
            ]
        )
        report, code = asyncio.run(interop.execute(args))
    assert code != 0
    assert report["decision"]["passed"] is False
    assert report["claims"]["mcpToolExecution"] is False
    assert "synthetic-sensitive-value" not in json.dumps(report)


def test_response_hook_is_removed_after_dispatch():
    async def scenario(url):
        async with httpx.AsyncClient(trust_env=False) as client:
            card = interop.build_official_agent_card(
                _card_payload(), endpoint=url + "/api/a2a/kagent/k8s-a2a-agent"
            )
            original = len(client.event_hooks["response"])
            await interop.dispatch_read_only_task(
                client,
                card,
                prompt="ACK",
                requested_protocol_version="0.3.0",
                timeout=1,
            )
            assert len(client.event_hooks["response"]) == original

    with controller() as server:
        asyncio.run(scenario(server.url))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("mode", ["valid", "incomplete", "wrong_rpc", "error_after_valid"])
def test_legacy_helper_comparison(mode):
    root = Path(__file__).resolve().parents[3]
    legacy = load_module("qualification_legacy", root / "scripts/kagent/test-a2a-agent.py")
    with controller(mode) as server:
        request_id, _, events = legacy.collect_dispatch_stream(
            legacy.DirectUrlTransport(),
            server.url + "/api/a2a/kagent/k8s-a2a-agent",
            "ACK",
            timeout=1,
        )
    if mode in {"wrong_rpc", "error_after_valid"}:
        with pytest.raises(legacy.GateError):
            legacy.select_dispatch_from_events(request_id, events)
    else:
        task, state, _ = legacy.select_dispatch_from_events(request_id, events)
        assert task == "task-local"
        assert state == ("completed" if mode == "valid" else "working")


def test_native_sdk_report_is_not_educational_schema_11():
    root = Path(__file__).resolve().parents[3]
    contracts = load_module(
        "qualification_contracts", root / "scripts/kagent/experiments/contracts.py"
    )
    with controller() as server:
        args = interop._parser().parse_args(["--controller", server.url, "--prompt", "ACK"])
        report, code = asyncio.run(interop.execute(args))
    assert code == 0
    assert report["schemaVersion"] == "1.0"
    with pytest.raises(contracts.ContractError):
        contracts.validate_evidence_payload(report)
    renamed = copy.deepcopy(report)
    renamed["schemaVersion"] = "1.1"
    with pytest.raises(contracts.ContractError):
        contracts.validate_evidence_payload(renamed)


def test_actual_sdk_version_is_pinned():
    from importlib.metadata import version

    assert version("a2a-sdk") == "0.3.26"


@pytest.mark.parametrize("advertised", ["1.0", "0.4.0", "invalid"])
def test_real_card_protocol_rejection_prevents_post(advertised):
    with controller(card=_card_payload(advertised)) as server:
        args = interop._parser().parse_args(["--controller", server.url, "--prompt", "ACK"])
        report, code = asyncio.run(interop.execute(args))
    assert code != 0
    assert report["decision"]["passed"] is False
    assert [method for method, _, _ in server.requests] == ["GET"]


def test_failed_card_connection_is_recorded_as_failure():
    with controller() as server:
        unused_url = server.url
    args = interop._parser().parse_args(["--controller", unused_url, "--timeout", "0.2"])
    report, code = asyncio.run(interop.execute(args))
    assert code == 3
    assert report["decision"]["passed"] is False
    assert report["claims"]["agentCardDiscovery"] is False
