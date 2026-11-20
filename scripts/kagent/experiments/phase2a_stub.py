"""Replay a deterministic, artifact-only A2A task on a Linux loopback socket."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import signal
import socket
import subprocess
import sys
from contextlib import suppress
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

CASES = ("valid", "malformed", "wrong-task", "unsupported")
PROMPT = "Return the fixed synthetic patch artifact."
PATCH = "--- a/example.txt\n+++ b/example.txt\n@@ -1 +1 @@\n-old\n+new\n"
PATCH_FORMAT = re.compile(
    r"--- a/example\.txt\n\+\+\+ b/example\.txt\n@@ -1 \+1 @@\n-[^\r\n]+\n\+[^\r\n]+\n"
)
TIMEOUT = 5
WORKER_LISTEN_TIMEOUT = 30


@dataclass
class TerminalRecord:
    decision: str = "BLOCKED"
    reason: str = "unsupported_backend"
    evidence: str = "synthetic/non-qualified"
    request_id: str | None = None
    message_id: str | None = None
    task_id: str | None = None
    artifact_id: str | None = None
    worker_pid: int | None = None
    worker_exit_code: int | None = None
    process_group_gone: bool | None = None


def serve_once(fd: int, case: str) -> None:
    """Serve the one fixed request. The worker has no subprocess or tool path."""

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            size = int(self.headers.get("Content-Length", "0"))
            if self.path != "/" or not 0 < size <= 4096:
                self.send_error(400)
                return
            request = json.loads(self.rfile.read(size))
            message = request["params"]["message"]
            if request["method"] != "message/stream" or message["parts"] != [
                {"kind": "text", "text": PROMPT},
            ]:
                self.send_error(400)
                return

            message_id = message["messageId"]
            task_id = f"task-{message_id}"
            context_id = f"context-{message_id}"
            events = [
                {
                    "kind": "status-update",
                    "contextId": context_id,
                    "taskId": task_id,
                    "status": {"state": "working"},
                    "final": False,
                },
                {
                    "kind": "artifact-update",
                    "contextId": context_id,
                    "taskId": "other-task" if case == "wrong-task" else task_id,
                    "lastChunk": True,
                    "artifact": {
                        "artifactId": f"patch-{message_id}",
                        "metadata": {"messageId": message_id},
                        "parts": [
                            {
                                "kind": "data",
                                "data": {
                                    "schemaVersion": "1.0",
                                    "format": "unified-diff",
                                    "patch": 42 if case == "malformed" else PATCH,
                                },
                            }
                        ],
                    },
                },
                {
                    "kind": "status-update",
                    "contextId": context_id,
                    "taskId": task_id,
                    "status": {"state": "completed"},
                    "final": True,
                },
            ]
            body = "".join(
                "data: "
                + json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": event})
                + "\n\n"
                for event in events
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    with HTTPServer(("127.0.0.1", 0), Handler, bind_and_activate=False) as server:
        server.socket.close()
        server.socket = socket.socket(fileno=fd)
        # The controller can still be importing the pinned SDK after spawn.
        # Its shorter request and teardown deadlines start after that import.
        server.timeout = WORKER_LISTEN_TIMEOUT
        server.handle_request()


def valid_patch(data: dict[str, Any]) -> bool:
    patch = data.get("patch")
    return (
        set(data) == {"schemaVersion", "format", "patch"}
        and data["schemaVersion"] == "1.0"
        and data["format"] == "unified-diff"
        and isinstance(patch, str)
        and len(patch) <= 4096
        and PATCH_FORMAT.fullmatch(patch) is not None
    )


async def dispatch(endpoint: str, record: TerminalRecord) -> None:
    import httpx
    from a2a.types import AgentCapabilities, AgentCard, DataPart, TaskArtifactUpdateEvent
    from a2a_sdk_interop import (
        DispatchError,
        DispatchObservation,
        KagentCard,
        dispatch_read_only_task,
    )

    card = AgentCard(
        name="offline-patch-stub",
        description="Fixed synthetic patch replay",
        url=endpoint,
        version="1.0",
        protocol_version="0.3.0",
        capabilities=AgentCapabilities(streaming=True),
        default_input_modes=["text/plain"],
        default_output_modes=["application/json"],
        skills=[],
    )
    profile = KagentCard(card, endpoint, card.name, True, True, None, None, (), "0.3.0", "fixed")
    artifacts: list[TaskArtifactUpdateEvent] = []

    def observe(result: Any) -> None:
        if isinstance(result, TaskArtifactUpdateEvent):
            artifacts.append(result)

    observation: DispatchObservation | None
    async with httpx.AsyncClient(trust_env=False, timeout=TIMEOUT) as client:
        try:
            observation = await dispatch_read_only_task(
                client,
                profile,
                prompt=PROMPT,
                requested_protocol_version="0.3.0",
                timeout=TIMEOUT,
                observe_event=observe,
            )
        except DispatchError as exc:
            observation = exc.observation
            record.decision, record.reason = "REJECT", "protocol_failure"
        if observation is not None:
            record.request_id = observation.request_id
            record.message_id = observation.message_id
            record.task_id = observation.task_id
        if record.decision == "REJECT":
            return

    record.decision, record.reason = "REJECT", "artifact_correlation"
    if len(artifacts) != 1 or not record.request_id or not record.message_id:
        return
    event = artifacts[0]
    if (
        event.task_id != record.task_id
        or event.context_id != f"context-{record.message_id}"
        or event.artifact.artifact_id != f"patch-{record.message_id}"
        or event.artifact.metadata != {"messageId": record.message_id}
        or event.last_chunk is not True
        or event.append is True
    ):
        return
    record.artifact_id = event.artifact.artifact_id
    record.reason = "artifact_schema"
    parts = event.artifact.parts
    if len(parts) == 1 and isinstance(parts[0].root, DataPart) and valid_patch(parts[0].root.data):
        record.decision, record.reason = "ACCEPT", "correlated_schema_valid_artifact"


def finish_worker(worker: subprocess.Popen[bytes], record: TerminalRecord) -> None:
    try:
        record.worker_exit_code = worker.wait(timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        record.decision, record.reason = "BLOCKED", "worker_exit_timeout"

    try:
        os.killpg(worker.pid, 0)
    except ProcessLookupError:
        record.process_group_gone = True
        if record.worker_exit_code == 0:
            return
        record.decision, record.reason = "BLOCKED", "worker_exit_failed"
        return

    # Signal the group, including any unexpected descendants. A forced cleanup
    # never qualifies as successful replay.
    record.decision, record.reason = "BLOCKED", "worker_teardown_failed"
    record.process_group_gone = False
    with suppress(ProcessLookupError):
        os.killpg(worker.pid, signal.SIGKILL)
    record.worker_exit_code = worker.wait(timeout=TIMEOUT)
    try:
        os.killpg(worker.pid, 0)
    except ProcessLookupError:
        record.process_group_gone = True


def replay(case: str) -> TerminalRecord:
    record = TerminalRecord()
    if case not in CASES[:-1]:
        return record
    if sys.platform != "linux":
        record.reason = "linux_process_groups_required"
        return record
    record.reason = "pinned_sdk_required"
    try:
        if version("a2a-sdk") != "0.3.26":
            return record
    except PackageNotFoundError:
        return record

    record.reason = "worker_start_failed"
    script = Path(__file__).resolve()
    try:
        with TemporaryDirectory(prefix="phase2a-stub-") as directory:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
                listener.bind(("127.0.0.1", 0))
                listener.listen(1)
                port = listener.getsockname()[1]
                fd = listener.fileno()
                worker = subprocess.Popen(
                    [sys.executable, "-I", "-S", str(script), "--worker", str(fd), case],
                    cwd=directory,
                    env={},
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                    pass_fds=(fd,),
                )
            record.worker_pid = worker.pid
            try:
                record.reason = "dispatch_failed"
                asyncio.run(dispatch(f"http://127.0.0.1:{port}/", record))
            finally:
                try:
                    finish_worker(worker, record)
                except (OSError, subprocess.TimeoutExpired):
                    record.decision, record.reason = "BLOCKED", "worker_teardown_unverified"
                    record.process_group_gone = False
    except (OSError, subprocess.TimeoutExpired):
        record.decision = "BLOCKED"
    return record


def main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        serve_once(int(sys.argv[2]), sys.argv[3])
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=CASES)
    record = replay(parser.parse_args().case)
    print(json.dumps(asdict(record), sort_keys=True))
    return {"ACCEPT": 0, "REJECT": 1, "BLOCKED": 2}[record.decision]


if __name__ == "__main__":
    raise SystemExit(main())
