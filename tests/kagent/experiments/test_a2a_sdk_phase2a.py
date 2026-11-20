"""Exercise the deterministic patch replay over real loopback HTTP/SSE."""

import builtins
import os
import sys

import pytest
from test_a2a_sdk_interop import ROOT
from test_a2a_sdk_transport import load_module

phase2a_stub = load_module("phase2a_stub", ROOT / "scripts/kagent/experiments/phase2a_stub.py")


@pytest.mark.skipif(sys.platform != "linux", reason="requires Linux process groups")
@pytest.mark.parametrize(
    ("case", "decision", "reason"),
    [
        ("valid", "ACCEPT", "correlated_schema_valid_artifact"),
        ("malformed", "REJECT", "artifact_schema"),
        ("wrong-task", "REJECT", "protocol_failure"),
    ],
)
def test_terminal_record_and_teardown(case, decision, reason):
    record = phase2a_stub.replay(case)
    assert record.decision == decision
    assert record.reason == reason
    assert record.evidence == "synthetic/non-qualified"
    assert record.worker_pid > 0
    assert record.process_group_gone is True
    assert record.worker_exit_code == 0
    with pytest.raises(ProcessLookupError):
        os.killpg(record.worker_pid, 0)
    assert record.request_id and record.message_id
    assert record.task_id == f"task-{record.message_id}"
    expected_artifact = None if case == "wrong-task" else f"patch-{record.message_id}"
    assert record.artifact_id == expected_artifact


def test_unsupported_backend_is_blocked_before_worker_start(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("unsupported backend reached worker startup or dispatch")

    monkeypatch.setattr(phase2a_stub.socket, "socket", forbidden)
    monkeypatch.setattr(phase2a_stub.subprocess, "Popen", forbidden)
    monkeypatch.setattr(phase2a_stub, "dispatch", forbidden)
    with monkeypatch.context() as execution:
        execution.setattr(builtins, "exec", forbidden)
        execution.setattr(builtins, "eval", forbidden)
        execution.setattr(builtins, "compile", forbidden)
        record = phase2a_stub.replay("unsupported")
    assert record.decision == "BLOCKED"
    assert record.reason == "unsupported_backend"
    assert record.worker_pid is None
    assert record.request_id is None
    assert record.artifact_id is None


@pytest.mark.skipif(sys.platform != "linux", reason="requires Linux process groups")
def test_teardown_verification_failure_blocks_success(monkeypatch):
    finish = phase2a_stub.finish_worker

    def fail_verification(worker, record):
        assert record.decision == "ACCEPT"
        finish(worker, record)
        raise PermissionError("synthetic teardown verification failure")

    monkeypatch.setattr(phase2a_stub, "finish_worker", fail_verification)
    record = phase2a_stub.replay("valid")
    assert record.decision == "BLOCKED"
    assert record.reason == "worker_teardown_unverified"
    assert record.process_group_gone is False
