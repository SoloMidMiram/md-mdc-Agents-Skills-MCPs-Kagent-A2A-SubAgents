#!/usr/bin/env python3
"""Run a single Lane A kagent A2A educational example via the shared A2A helper.

Wraps ``test-a2a-agent.py`` transport primitives — does not implement a second
A2A client.

Usage:
    python scripts/kagent/experiments/run_a2a_example.py \\
        --agent planner-agent \\
        --prompt "Plan a minimal hello-world Telegram bot." \\
        --output json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
A2A_PATH = Path(__file__).resolve().parents[1] / "test-a2a-agent.py"
_spec = importlib.util.spec_from_file_location("kagent_test_a2a_agent", A2A_PATH)
assert _spec is not None and _spec.loader is not None
a2a = importlib.util.module_from_spec(_spec)
sys.modules["kagent_test_a2a_agent"] = a2a
_spec.loader.exec_module(a2a)

EXPERIMENTS_DIR = Path(__file__).resolve().parent
_contracts_spec = importlib.util.spec_from_file_location(
    "kagent_experiment_contracts", EXPERIMENTS_DIR / "contracts.py"
)
assert _contracts_spec is not None and _contracts_spec.loader is not None
contracts = importlib.util.module_from_spec(_contracts_spec)
sys.modules["kagent_experiment_contracts"] = contracts
_contracts_spec.loader.exec_module(contracts)
ContractError = contracts.ContractError
validate_artifact = contracts.validate_artifact

SCHEMA_VERSION = "1.0"
DEFAULT_CONTROLLER = a2a.DEFAULT_CONTROLLER
DEFAULT_NAMESPACE = a2a.DEFAULT_NAMESPACE


@dataclass
class ExampleRunResult:
    example: str
    agent: str
    namespace: str
    controller: str
    task_id: str | None
    dispatch_state: str | None
    duration_ms: int
    pass_: bool
    reason: str
    artifact: dict[str, Any] | None = None
    artifact_summary: dict[str, Any] = field(default_factory=dict)
    card_accepted: bool | None = None
    card_deployment_ready: bool | None = None
    non_claims: list[str] = field(
        default_factory=lambda: ["L6", "I3", "I4", "MCP", "Codex", "Cursor"]
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "example": self.example,
            "observedAt": a2a.utc_now_iso(),
            "agents": [self.agent],
            "target": {
                "namespace": self.namespace,
                "agent": self.agent,
                "controller": a2a.sanitize_controller_origin(self.controller),
            },
            "taskId": self.task_id,
            "dispatchState": self.dispatch_state,
            "durationMs": self.duration_ms,
            "pass": self.pass_,
            "reason": self.reason,
            "card": {
                "accepted": self.card_accepted,
                "deploymentReady": self.card_deployment_ready,
            },
            "artifactSummary": self.artifact_summary,
            "nonClaims": self.non_claims,
        }


def _example_id_for_agent(agent: str) -> str:
    mapping = {
        "planner-agent": "e1-planner",
        "reviewer-agent": "phase2-reviewer",
        "supervisor-agent": "e2-supervisor",
    }
    return mapping.get(agent, agent)


def extract_text_from_task(task: dict[str, Any]) -> tuple[str, str]:
    """Return (state, concatenated agent text) from a tasks/get task object."""
    status = task.get("status") if isinstance(task.get("status"), dict) else {}
    state = str(status.get("state", "")).lower()
    message = status.get("message") if isinstance(status.get("message"), dict) else {}
    chunks: list[str] = []
    for part in message.get("parts") or []:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            chunks.append(part["text"])
    return state, "\n".join(chunks)


def poll_task_until_terminal(
    transport: a2a.Transport,
    url: str,
    task_id: str,
    *,
    timeout: float,
    poll_interval: float = 2.0,
) -> dict[str, Any]:
    """Poll ``tasks/get`` until the task reaches a terminal state."""
    deadline = time.perf_counter() + timeout
    envelope = {
        "jsonrpc": "2.0",
        "id": "tasks-get-poll",
        "method": "tasks/get",
        "params": {"id": task_id},
    }
    body = json.dumps(envelope).encode()
    last_task: dict[str, Any] | None = None
    while time.perf_counter() < deadline:
        resp = transport.request(
            "POST",
            url,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            body=body,
            timeout=min(30.0, timeout),
        )
        if resp.status >= 400:
            raise a2a.TransportFailure(f"tasks/get HTTP {resp.status}", error_kind="http_error")
        decoded = json.loads(resp.body.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise a2a.GateError("tasks/get response must be an object")
        if "error" in decoded:
            err = decoded["error"]
            raise a2a.GateError(
                f"tasks/get error code={err.get('code')}: {err.get('message', '')}"
            )
        task = decoded.get("result")
        if not isinstance(task, dict):
            raise a2a.GateError("tasks/get result must be a task object")
        last_task = task
        state, _text = extract_text_from_task(task)
        if state in {"completed", "failed", "canceled", "cancelled", "rejected"}:
            return task
        time.sleep(poll_interval)
    if last_task is None:
        raise a2a.GateError("tasks/get polling timed out before first response")
    return last_task


def extract_response_text(events: list[dict[str, Any]], task_id: str | None) -> str:
    """Collect agent text parts from terminal completed status-update events."""
    chunks: list[str] = []
    for obj in events:
        if not isinstance(obj, dict):
            continue
        result = obj.get("result")
        if not isinstance(result, dict):
            continue
        if task_id and result.get("taskId") not in {None, task_id}:
            continue
        status = result.get("status") if isinstance(result.get("status"), dict) else {}
        if str(status.get("state", "")).lower() != "completed":
            continue
        message = status.get("message") if isinstance(status.get("message"), dict) else {}
        for part in message.get("parts") or []:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                chunks.append(part["text"])
    if chunks:
        return "\n".join(chunks)

    # Fallback: any agent-role text part in stream order
    for obj in events:
        result = obj.get("result") if isinstance(obj, dict) else None
        if not isinstance(result, dict):
            continue
        status = result.get("status") if isinstance(result.get("status"), dict) else {}
        message = status.get("message") if isinstance(status.get("message"), dict) else {}
        if message.get("role") not in {"agent", "model"}:
            continue
        for part in message.get("parts") or []:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                chunks.append(part["text"])
    return "\n".join(chunks)


def summarize_artifact(agent: str, artifact: dict[str, Any]) -> dict[str, Any]:
    if agent == "planner-agent":
        return {"goal": artifact.get("goal", "")[:160]}
    if agent == "reviewer-agent":
        return {"verdict": artifact.get("verdict")}
    if agent == "supervisor-agent":
        summary: dict[str, Any] = {}
        if "verdict" in artifact:
            summary["verdict"] = artifact.get("verdict")
        if isinstance(artifact.get("plan"), dict):
            summary["planGoal"] = str(artifact["plan"].get("goal", ""))[:120]
        if isinstance(artifact.get("review"), dict):
            summary["reviewVerdict"] = artifact["review"].get("verdict")
        return summary
    return {}


def run_example(
    *,
    agent: str,
    prompt: str,
    controller: str,
    namespace: str,
    example: str | None,
    timeout: float,
    skip_contract: bool,
) -> ExampleRunResult:
    transport = a2a.DirectUrlTransport()
    example_id = example or _example_id_for_agent(agent)
    started = time.perf_counter()
    result = ExampleRunResult(
        example=example_id,
        agent=agent,
        namespace=namespace,
        controller=controller,
        task_id=None,
        dispatch_state=None,
        duration_ms=0,
        pass_=False,
        reason="not started",
    )

    card_report = a2a.run_card(
        transport,
        a2a.EvidenceReport(
            action="card",
            observed_at=a2a.utc_now_iso(),
            namespace=namespace,
            agent=agent,
            controller=controller,
        ),
    )
    result.card_accepted = card_report.card_accepted
    result.card_deployment_ready = card_report.card_deployment_ready
    if not card_report.decision_passed:
        result.duration_ms = int((time.perf_counter() - started) * 1000)
        result.reason = f"card gate failed: {card_report.reason}"
        return result

    url = a2a.build_a2a_url(controller, namespace, agent)
    try:
        request_id, _http_status, events = a2a.collect_dispatch_stream(
            transport, url, prompt, timeout=timeout
        )
        task_id, state, _kind = a2a.select_dispatch_from_events(request_id, events)
        result.task_id = task_id
        result.dispatch_state = state

        terminal_task = poll_task_until_terminal(
            transport, url, task_id, timeout=timeout
        )
        terminal_state, response_text = extract_text_from_task(terminal_task)
        result.dispatch_state = terminal_state
        if terminal_state == "failed":
            result.duration_ms = int((time.perf_counter() - started) * 1000)
            result.reason = response_text.strip() or "task failed without agent message"
            return result
        if not response_text.strip():
            response_text = extract_response_text(events, task_id)
        if not response_text.strip():
            result.duration_ms = int((time.perf_counter() - started) * 1000)
            result.reason = "dispatch accepted but no response text extracted"
            return result

        artifact: dict[str, Any] | None = None
        if not skip_contract:
            artifact = validate_artifact(agent, response_text)
            result.artifact = artifact
            result.artifact_summary = summarize_artifact(agent, artifact)

        result.duration_ms = int((time.perf_counter() - started) * 1000)
        result.pass_ = True
        result.reason = "A2A dispatch accepted with valid structured artifact"
        return result
    except (a2a.GateError, a2a.TransportFailure, ContractError) as exc:
        result.duration_ms = int((time.perf_counter() - started) * 1000)
        result.reason = str(exc)
        return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one Lane A kagent A2A example.")
    parser.add_argument("--agent", required=True, help="Agent metadata.name in namespace")
    parser.add_argument("--prompt", help="User prompt text")
    parser.add_argument("--prompt-file", type=Path, help="Read prompt from file")
    parser.add_argument("--example", help="Evidence example id override")
    parser.add_argument("--controller", default=DEFAULT_CONTROLLER)
    parser.add_argument("--namespace", default=DEFAULT_NAMESPACE)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--skip-contract",
        action="store_true",
        help="Accept dispatch without JSON contract validation",
    )
    parser.add_argument("--output", choices=("human", "json"), default="human")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.prompt_file and args.prompt:
        print("error: use only one of --prompt or --prompt-file", file=sys.stderr)
        return a2a.ExitCode.USAGE
    if args.prompt_file:
        prompt = args.prompt_file.read_text(encoding="utf-8")
    elif args.prompt:
        prompt = args.prompt
    else:
        print("error: --prompt or --prompt-file is required", file=sys.stderr)
        return a2a.ExitCode.USAGE

    try:
        controller = a2a.validate_controller_url(args.controller)
    except a2a.UsageFailure as exc:
        print(f"error: {exc}", file=sys.stderr)
        return a2a.ExitCode.USAGE

    run = run_example(
        agent=args.agent,
        prompt=prompt,
        controller=controller,
        namespace=args.namespace,
        example=args.example,
        timeout=args.timeout,
        skip_contract=args.skip_contract,
    )

    if args.output == "json":
        print(json.dumps(run.to_dict(), indent=2))
    else:
        prefix = "[PASS]" if run.pass_ else "[FAIL]"
        print(f"{prefix} {run.example} agent={run.agent} task={run.task_id}")
        print(f"  reason: {run.reason}")
        print(f"  durationMs: {run.duration_ms}")
        if run.artifact_summary:
            print(f"  artifactSummary: {json.dumps(run.artifact_summary)}")

    return a2a.ExitCode.SUCCESS if run.pass_ else a2a.ExitCode.GATE


if __name__ == "__main__":
    raise SystemExit(main())
