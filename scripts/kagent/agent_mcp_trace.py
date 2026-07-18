#!/usr/bin/env python3
"""Correlate A2A dispatch with agent-mediated MCP tool execution (L6 educational gate).

Proves (or truthfully fails to prove):
  A2A message/stream → accepted task → MCP tool invocation → A2A-returned names
  → kubectl cross-check

Does not prove L4 alone as L6. Direct MCP is never sufficient.

Usage:
    python scripts/kagent/agent_mcp_trace.py --controller http://127.0.0.1:8083 --output json
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
A2A_PATH = Path(__file__).resolve().parent / "test-a2a-agent.py"
_spec = importlib.util.spec_from_file_location("kagent_test_a2a_agent", A2A_PATH)
assert _spec is not None and _spec.loader is not None
a2a = importlib.util.module_from_spec(_spec)
sys.modules["kagent_test_a2a_agent"] = a2a
_spec.loader.exec_module(a2a)

SCHEMA_VERSION = "1.0"
EVIDENCE_KIND = "agent-mediated-mcp"
DEFAULT_CONTROLLER = "http://127.0.0.1:8083"
DEFAULT_NAMESPACE = "kagent"
DEFAULT_AGENT = "k8s-a2a-agent"
DEFAULT_MCP_SERVER = "kagent-tool-server"
DEFAULT_TOOL = "k8s_get_resources"
DEFAULT_CLUSTER = "docker-desktop"
DEFAULT_PROMPT = (
    "List pods in namespace kagent using the configured Kubernetes MCP tool. "
    "Return only pod names and the namespace."
)
MAX_FRESHNESS_SECONDS = 900
FUTURE_SKEW_SECONDS = 120
MAX_LOG_LINES = 200
MAX_SOURCE_CHARS = 12_000
POD_NAME_RE = re.compile(r"\b([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)\b")

# Heuristic kinds / keys that indicate a tool or function call in A2A payloads.
TOOL_PART_KINDS = frozenset(
    {
        "function",
        "function_call",
        "functionCall",
        "tool",
        "tool_call",
        "toolCall",
        "data",
    }
)


class ExitCode:
    SUCCESS = 0
    GATE = 1
    USAGE = 2
    TRANSPORT = 3


LogCollector = Callable[[str, str, int], list[str]]
KubectlCollector = Callable[[str], list[str]]
ContextCollector = Callable[[], str]


@dataclass
class TraceReport:
    observed_at: str = ""
    cluster_context: str = DEFAULT_CLUSTER
    namespace: str = DEFAULT_NAMESPACE
    agent: str = DEFAULT_AGENT
    controller: str = DEFAULT_CONTROLLER
    mcp_server: str = DEFAULT_MCP_SERVER
    method: str = a2a.DISPATCH_METHOD
    http_status: int | None = None
    response_id_matched: bool = False
    request_id: str | None = None
    task_or_message_id: str | None = None
    accepted_state: str | None = None
    tool_observed: bool = False
    correlated_id: str | None = None
    tool_name: str | None = None
    tool_server: str | None = None
    arguments_summary: dict[str, str] = field(
        default_factory=lambda: {"resourceType": "pod", "namespace": DEFAULT_NAMESPACE}
    )
    source_kind: str | None = None
    source_reference: str | None = None
    source_proof: dict[str, Any] | None = None
    log_searches: list[dict[str, Any]] = field(default_factory=list)
    returned_through_a2a: bool = False
    tool_names: list[str] = field(default_factory=list)
    cross_check_names: list[str] = field(default_factory=list)
    matched: bool = False
    source_evidence_path: str = ""
    freshness_seconds: int = 0
    max_freshness_seconds: int = MAX_FRESHNESS_SECONDS
    target_bound: bool = False
    task_trace_correlated: bool = False
    decision_passed: bool = False
    exit_code: int = ExitCode.GATE
    reason: str = ""
    l4_accepted: bool = False

    def to_sanitized_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "evidenceKind": EVIDENCE_KIND,
            "observedAt": self.observed_at,
            "target": {
                "clusterContext": self.cluster_context,
                "namespace": self.namespace,
                "agent": self.agent,
                "controller": a2a.sanitize_controller_origin(self.controller),
                "mcpServer": self.mcp_server,
            },
            "a2a": {
                "method": self.method,
                "requestId": a2a.sanitize_request_id(self.request_id),
                "taskOrMessageId": self.task_or_message_id,
                "acceptedState": self.accepted_state,
                "transport": {
                    "succeeded": self.http_status is not None,
                    "httpStatus": self.http_status,
                },
                "protocol": {
                    "jsonRpc": "2.0",
                    "requestId": a2a.sanitize_request_id(self.request_id),
                    "responseIdMatched": self.response_id_matched,
                    "error": None,
                },
                "dispatch": {
                    "accepted": self.l4_accepted,
                    "taskOrMessageId": self.task_or_message_id,
                    "state": self.accepted_state,
                },
            },
            "toolInvocation": {
                "observed": self.tool_observed,
                "correlatedTaskOrMessageId": self.correlated_id,
                "server": self.tool_server,
                "tool": self.tool_name,
                "argumentsSummary": dict(self.arguments_summary),
                "source": {
                    "kind": self.source_kind,
                    "reference": a2a.sanitize_text(self.source_reference, limit=240),
                },
            },
            "result": {
                "returnedThroughA2A": self.returned_through_a2a,
                "toolDerivedResourceNames": list(self.tool_names),
                "crossCheckResourceNames": list(self.cross_check_names),
                "matched": self.matched,
            },
            "provenance": {
                "sourceEvidencePath": self.source_evidence_path,
                "freshnessSeconds": self.freshness_seconds,
                "maxFreshnessSeconds": self.max_freshness_seconds,
                "targetBound": self.target_bound,
                "taskTraceCorrelated": self.task_trace_correlated,
            },
            "decision": {
                "passed": self.decision_passed,
                "exitCode": self.exit_code,
                "reason": self.reason,
            },
            # Flat aliases for older consumers / health mapping
            "success": self.decision_passed,
            "a2aTaskOrMessageId": self.task_or_message_id,
            "agentName": self.agent,
            "agentNamespace": self.namespace,
            "toolName": self.tool_name,
            "toolDerivedResultSummary": (
                f"pods={len(self.tool_names)}" if self.tool_names else None
            ),
            "crossCheckDescription": (
                f"kubectl pods={len(self.cross_check_names)} matched={self.matched}"
            ),
            "sourceEvidencePath": self.source_evidence_path,
        }


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_iso() -> str:
    return utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso_utc(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def normalize_pod_name(name: str) -> str | None:
    text = name.strip().lower()
    if not text or len(text) > 253:
        return None
    # Drop common non-pod tokens
    if text in {
        "pod",
        "pods",
        "namespace",
        "kagent",
        "name",
        "status",
        "running",
        "ready",
        "age",
        "list",
        "using",
        "configured",
        "kubernetes",
        "mcp",
        "tool",
        "return",
        "only",
        "and",
        "the",
        "in",
        "kagent-tool-server",
        "k8s_get_resources",
        "k8s_get_available_api_resources",
        "resource_type",
        "resource-type",
        "functioncall",
        "toolcall",
        "message",
        "status-update",
        "docker-desktop",
    }:
        return None
    if text.startswith("k8s_get"):
        return None
    if not re.fullmatch(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?", text):
        return None
    return text


def extract_pod_names_from_text(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for match in POD_NAME_RE.finditer(text.lower()):
        name = normalize_pod_name(match.group(1))
        if name is None or name in seen:
            continue
        # Prefer names that look like workload pods (contain a dash)
        if "-" not in name and not name.endswith("-agent"):
            continue
        seen.add(name)
        found.append(name)
    return found


def _walk(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk(item)


def scan_events_for_tool(
    events: list[dict[str, Any]],
    *,
    task_id: str,
    expected_tool: str,
    expected_server: str,
) -> tuple[bool, str | None, list[str], dict[str, Any] | None]:
    """Return a strictly task/server/tool/argument-bound protocol observation."""

    marker_index: int | None = None
    marker_part_index: int | None = None
    marker_proof: dict[str, Any] | None = None

    for event_index, obj in enumerate(events):
        result = obj.get("result") if isinstance(obj, dict) else None
        if not isinstance(result, dict) or result.get("taskId") != task_id:
            continue
        status = result.get("status") if isinstance(result.get("status"), dict) else {}
        message = status.get("message") if isinstance(status.get("message"), dict) else {}
        if message.get("role") not in {"agent", "tool", "model"}:
            continue
        parts = message.get("parts") if isinstance(message.get("parts"), list) else []
        for part_index, part in enumerate(parts):
            marker = _normalize_tool_marker(part)
            if marker is None:
                continue
            if (
                marker["tool"] != expected_tool
                or marker["server"] != expected_server
                or marker["resourceType"] != "pod"
                or marker["namespace"] != DEFAULT_NAMESPACE
            ):
                continue
            marker_index = event_index
            marker_part_index = part_index
            marker_proof = {
                "kind": "protocol-result",
                "eventIndex": event_index,
                "partIndex": part_index,
                "taskOrMessageId": task_id,
                "server": marker["server"],
                "tool": marker["tool"],
                "argumentsSummary": {
                    "resourceType": marker["resourceType"],
                    "namespace": marker["namespace"],
                },
                "partKind": str(part.get("kind", "")),
            }
            break
        if marker_proof is not None:
            break

    if marker_proof is None or marker_index is None or marker_part_index is None:
        return False, None, [], None

    names = _extract_names_after_protocol_marker(
        events,
        task_id,
        marker_index,
        marker_part_index,
    )
    reference = f"protocol-result:event={marker_index}:part={marker_part_index}"
    marker_proof["reference"] = reference
    return True, reference, names, marker_proof


def _normalize_tool_marker(part: Any) -> dict[str, str] | None:
    if not isinstance(part, dict) or part.get("kind") not in TOOL_PART_KINDS:
        return None
    data = part.get("data") if isinstance(part.get("data"), dict) else {}
    tool = part.get("name") or part.get("tool") or data.get("tool") or data.get("name")
    server = part.get("server") or data.get("server")
    args = part.get("args") or part.get("arguments") or data.get("args") or data.get("arguments")
    if not isinstance(args, dict):
        args = data
    resource_type = (
        args.get("resourceType")
        or args.get("resource_type")
        or args.get("resource-type")
    )
    namespace = args.get("namespace") or args.get("resourceNamespace")
    if not all(isinstance(v, str) and v.strip() for v in (tool, server, resource_type, namespace)):
        return None
    return {
        "tool": tool.strip(),
        "server": server.strip(),
        "resourceType": resource_type.strip().lower(),
        "namespace": namespace.strip(),
    }


def _extract_names_after_protocol_marker(
    events: list[dict[str, Any]],
    task_id: str,
    start_index: int,
    start_part_index: int,
) -> list[str]:
    names: list[str] = []
    for event_index, obj in enumerate(events[start_index:], start=start_index):
        result = obj.get("result") if isinstance(obj, dict) else None
        if not isinstance(result, dict) or result.get("taskId") != task_id:
            continue
        status = result.get("status") if isinstance(result.get("status"), dict) else {}
        message = status.get("message") if isinstance(status.get("message"), dict) else {}
        if message.get("role") not in {"agent", "tool", "model"}:
            continue
        parts = message.get("parts") or []
        if event_index == start_index:
            parts = parts[start_part_index + 1 :]
        for part in parts:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                names.extend(extract_pod_names_from_text(part["text"]))
    return sorted(set(names))


def _extract_terminal_agent_names(
    events: list[dict[str, Any]], task_id: str
) -> list[str]:
    names: list[str] = []
    for obj in events:
        result = obj.get("result") if isinstance(obj, dict) else None
        if not isinstance(result, dict) or result.get("taskId") != task_id:
            continue
        status = result.get("status") if isinstance(result.get("status"), dict) else {}
        if str(status.get("state", "")).lower() != "completed":
            continue
        message = status.get("message") if isinstance(status.get("message"), dict) else {}
        if message.get("role") not in {"agent", "tool", "model"}:
            continue
        for part in message.get("parts") or []:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                names.extend(extract_pod_names_from_text(part["text"]))
    return sorted(set(names))


def scan_logs_for_tool(
    lines: list[str],
    *,
    task_id: str,
    expected_tool: str,
    expected_server: str,
) -> tuple[bool, str | None, dict[str, Any] | None, dict[str, Any]]:
    task_matches = 0
    tool_matches = 0
    correlated_matches = 0
    for line in lines:
        if task_id in line:
            task_matches += 1
        if expected_tool in line:
            tool_matches += 1
        if not (task_id in line and expected_tool in line and expected_server in line):
            continue
        marker = _normalize_log_marker(
            line,
            task_id=task_id,
            expected_tool=expected_tool,
            expected_server=expected_server,
        )
        if (
            marker is None
            or marker["resourceType"] != "pod"
            or marker["namespace"] != DEFAULT_NAMESPACE
        ):
            continue
        correlated_matches += 1
        sanitized = a2a.sanitize_text(line, limit=400) or "log-line"
        digest = hashlib.sha256(sanitized.encode("utf-8")).hexdigest()
        reference = f"log:sha256:{digest[:16]}"
        proof = {
            "kind": "log",
            "taskOrMessageId": task_id,
            "server": expected_server,
            "tool": expected_tool,
            "argumentsSummary": {
                "resourceType": marker["resourceType"],
                "namespace": marker["namespace"],
            },
            "reference": reference,
            "sanitizedLine": sanitized,
            "sha256": digest,
        }
        summary = {
            "succeeded": True,
            "lineCount": len(lines),
            "taskMatches": task_matches,
            "toolMatches": tool_matches,
            "correlatedMatches": correlated_matches,
            "error": None,
        }
        return True, reference, proof, summary
    summary = {
        "succeeded": True,
        "lineCount": len(lines),
        "taskMatches": task_matches,
        "toolMatches": tool_matches,
        "correlatedMatches": correlated_matches,
        "error": None,
    }
    return False, None, None, summary


def _normalize_log_marker(
    line: str,
    *,
    task_id: str,
    expected_tool: str,
    expected_server: str,
) -> dict[str, str] | None:
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None
    scalar_values = {
        value.strip()
        for node in _walk(obj)
        if isinstance(node, dict)
        for value in node.values()
        if isinstance(value, str) and value.strip()
    }
    if not {task_id, expected_tool, expected_server}.issubset(scalar_values):
        return None
    for node in _walk(obj):
        if not isinstance(node, dict):
            continue
        resource_type = node.get("resourceType") or node.get("resource_type")
        namespace = node.get("namespace") or node.get("resourceNamespace")
        if isinstance(resource_type, str) and isinstance(namespace, str):
            return {
                "resourceType": resource_type.strip().lower(),
                "namespace": namespace.strip(),
            }
    return None


def default_log_collector(namespace: str, deploy_name: str, tail: int) -> list[str]:
    cmd = [
        "kubectl",
        "logs",
        "-n",
        namespace,
        f"deploy/{deploy_name}",
        f"--tail={tail}",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise a2a.TransportFailure(f"kubectl logs failed: {exc}", error_kind="connection") from exc
    if proc.returncode != 0:
        raise a2a.TransportFailure(
            f"kubectl logs for deploy/{deploy_name} exit {proc.returncode}",
            error_kind="connection",
        )
    return [ln for ln in proc.stdout.splitlines() if ln.strip()][:tail]


def default_kubectl_context() -> str:
    try:
        proc = subprocess.run(
            ["kubectl", "config", "current-context"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise a2a.TransportFailure(
            f"kubectl current-context failed: {exc}", error_kind="connection"
        ) from exc
    context = proc.stdout.strip()
    if proc.returncode != 0 or not context:
        raise a2a.TransportFailure(
            f"kubectl current-context exit {proc.returncode}", error_kind="connection"
        )
    return context


def default_kubectl_pod_names(namespace: str) -> list[str]:
    cmd = [
        "kubectl",
        "get",
        "pods",
        "-n",
        namespace,
        "-o",
        r"jsonpath={range .items[*]}{.metadata.name}{'\n'}{end}",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise a2a.TransportFailure(
            f"kubectl get pods failed: {exc}",
            error_kind="connection",
        ) from exc
    if proc.returncode != 0:
        raise a2a.TransportFailure(
            f"kubectl get pods exit {proc.returncode}",
            error_kind="connection",
        )
    names: list[str] = []
    for line in proc.stdout.splitlines():
        n = normalize_pod_name(line.strip())
        if n:
            names.append(n)
    return sorted(set(names))


def names_match(tool_names: list[str], kubectl_names: list[str]) -> bool:
    tool_set = set(tool_names)
    kube_set = set(kubectl_names)
    if not tool_set or not kube_set:
        return False
    # All tool-derived names must exist in cluster; require non-empty overlap
    if not tool_set.issubset(kube_set):
        return False
    return len(tool_set & kube_set) > 0


def write_source_capture(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True)
    if len(text) > MAX_SOURCE_CHARS:
        text = text[:MAX_SOURCE_CHARS] + "\n…truncated…\n"
    path.write_text(text, encoding="utf-8")
    try:
        rel = path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        rel = str(path)
    return rel


def run_trace(
    *,
    controller: str,
    namespace: str,
    agent: str,
    prompt: str,
    cluster_context: str,
    source_out: Path,
    transport: Any | None = None,
    log_collector: LogCollector | None = None,
    kubectl_collector: KubectlCollector | None = None,
    context_collector: ContextCollector | None = None,
    skip_logs: bool = False,
    timeout: float = 90.0,
) -> TraceReport:
    report = TraceReport(
        observed_at=utc_now_iso(),
        cluster_context=cluster_context,
        namespace=namespace,
        agent=agent,
        controller=controller.rstrip("/"),
        mcp_server=DEFAULT_MCP_SERVER,
    )
    injected_transport = transport is not None
    transport = transport or a2a.DirectUrlTransport()
    log_collector = log_collector or default_log_collector
    kubectl_collector = kubectl_collector or default_kubectl_pod_names
    context_collector = context_collector or (
        (lambda: cluster_context) if injected_transport else default_kubectl_context
    )
    events: list[dict[str, Any]] = []

    def finish() -> TraceReport:
        _finalize_provenance(report, source_out, events)
        return report

    try:
        report.cluster_context = context_collector()
        a2a.check_connectivity(transport, report.controller)
        url = a2a.build_a2a_url(report.controller, namespace, agent)
        request_id, http_status, events = a2a.collect_dispatch_stream(
            transport, url, prompt, timeout=timeout
        )
        report.request_id = request_id
        report.http_status = http_status
        try:
            task_id, state, _kind = a2a.select_dispatch_from_events(request_id, events)
            report.response_id_matched = True
            report.task_or_message_id = task_id
            report.accepted_state = state
            report.l4_accepted = True
        except a2a.GateError as exc:
            report.exit_code = ExitCode.GATE
            report.reason = f"A2A dispatch gate failed: {exc}"
            report.decision_passed = False
            # Still attempt to extract taskId from any status-update for diagnostics
            for obj in events:
                res = obj.get("result") if isinstance(obj, dict) else None
                if isinstance(res, dict) and isinstance(res.get("taskId"), str):
                    report.task_or_message_id = res["taskId"]
                    break
            return finish()

        observed, ref, tool_names, proof = scan_events_for_tool(
            events,
            task_id=task_id,
            expected_tool=DEFAULT_TOOL,
            expected_server=DEFAULT_MCP_SERVER,
        )
        source_kind = "protocol-result" if observed else None

        if not observed and not skip_logs:
            successful_searches = 0
            for deployment, label in (
                (agent, "agent-log"),
                ("kagent-controller", "controller-log"),
            ):
                try:
                    lines = log_collector(namespace, deployment, MAX_LOG_LINES)
                    successful_searches += 1
                    ok, log_ref, log_proof, summary = scan_logs_for_tool(
                        lines,
                        task_id=task_id,
                        expected_tool=DEFAULT_TOOL,
                        expected_server=DEFAULT_MCP_SERVER,
                    )
                    summary["source"] = label
                    report.log_searches.append(summary)
                    if ok:
                        observed = True
                        source_kind = label
                        ref = log_ref
                        proof = log_proof
                        if proof is not None:
                            proof["kind"] = label
                        tool_names = _extract_terminal_agent_names(events, task_id)
                        break
                except a2a.TransportFailure as exc:
                    report.log_searches.append(
                        {
                            "source": label,
                            "succeeded": False,
                            "lineCount": 0,
                            "taskMatches": 0,
                            "toolMatches": 0,
                            "correlatedMatches": 0,
                            "error": a2a.sanitize_text(str(exc), limit=160),
                        }
                    )
            if not observed and successful_searches == 0:
                raise a2a.TransportFailure(
                    "all bounded agent/controller log collectors failed",
                    error_kind="connection",
                )

        report.tool_observed = observed
        report.source_proof = proof
        report.tool_name = str(proof.get("tool")) if observed and proof else None
        report.tool_server = str(proof.get("server")) if observed and proof else None
        report.correlated_id = (
            str(proof.get("taskOrMessageId")) if observed and proof else None
        )
        report.source_kind = source_kind
        report.source_reference = ref
        report.task_trace_correlated = bool(
            observed and report.correlated_id == report.task_or_message_id
        )

        if observed and tool_names:
            report.tool_names = tool_names
            report.returned_through_a2a = True
        elif observed:
            # Tool seen but no extractable names from A2A → not returned through A2A
            report.returned_through_a2a = False

        report.cross_check_names = kubectl_collector(namespace)
        report.matched = names_match(report.tool_names, report.cross_check_names)

        report.target_bound = (
            report.cluster_context == cluster_context == DEFAULT_CLUSTER
            and report.namespace == DEFAULT_NAMESPACE
            and report.agent == DEFAULT_AGENT
            and report.mcp_server == DEFAULT_MCP_SERVER
        )

        if not observed:
            report.exit_code = ExitCode.GATE
            report.decision_passed = False
            report.reason = (
                "no observable MCP tool invocation correlated to A2A task "
                f"(L4 accepted={report.l4_accepted} state={report.accepted_state})"
            )
            return finish()

        if not report.task_trace_correlated:
            report.exit_code = ExitCode.GATE
            report.decision_passed = False
            report.reason = "task/trace ID mismatch between dispatch and tool observation"
            return finish()

        if not report.returned_through_a2a or not report.tool_names:
            report.exit_code = ExitCode.GATE
            report.decision_passed = False
            report.reason = "tool invocation observed but result not returned through A2A"
            return finish()

        if not report.matched:
            report.exit_code = ExitCode.GATE
            report.decision_passed = False
            report.reason = "kubectl cross-check mismatch for tool-derived pod names"
            return finish()

        if not report.target_bound:
            report.exit_code = ExitCode.GATE
            report.decision_passed = False
            report.reason = "target binding failed"
            return finish()

        report.exit_code = ExitCode.SUCCESS
        report.decision_passed = True
        report.reason = "correlated agent-mediated MCP evidence with matching cross-check"
        return finish()

    except a2a.TransportFailure as exc:
        report.exit_code = ExitCode.TRANSPORT
        report.decision_passed = False
        report.reason = f"transport failure: {exc}"
        return finish()
    except a2a.GateError as exc:
        report.exit_code = ExitCode.GATE
        report.decision_passed = False
        report.reason = str(exc)
        return finish()
    except a2a.UsageFailure as exc:
        report.exit_code = ExitCode.USAGE
        report.decision_passed = False
        report.reason = str(exc)
        return finish()


def _finalize_provenance(
    report: TraceReport, source_out: Path, events: list[dict[str, Any]]
) -> None:
    # Freshness relative to observedAt (always ~0 for freshly produced reports)
    try:
        observed = parse_iso_utc(report.observed_at)
        report.freshness_seconds = max(0, int((utc_now() - observed).total_seconds()))
    except ValueError:
        report.freshness_seconds = MAX_FRESHNESS_SECONDS + 1

    capture = {
        "schemaVersion": SCHEMA_VERSION,
        "evidenceKind": EVIDENCE_KIND,
        "observedAt": report.observed_at,
        "taskOrMessageId": report.task_or_message_id,
        "requestId": a2a.sanitize_request_id(report.request_id),
        "toolObserved": report.tool_observed,
        "sourceKind": report.source_kind,
        "target": {
            "clusterContext": report.cluster_context,
            "namespace": report.namespace,
            "agent": report.agent,
            "controller": a2a.sanitize_controller_origin(report.controller),
            "mcpServer": report.mcp_server,
        },
        "toolEvidence": report.source_proof,
        "resultEvidence": {
            "returnedThroughA2A": report.returned_through_a2a,
            "toolDerivedResourceNames": list(report.tool_names),
            "crossCheckResourceNames": list(report.cross_check_names),
            "matched": report.matched,
        },
        "logSearches": list(report.log_searches),
        "eventCount": len(events),
        # Sanitized: no full bodies; only kinds/states/taskIds
        "eventSummaries": [
            {
                "kind": (e.get("result") or {}).get("kind")
                if isinstance(e.get("result"), dict)
                else None,
                "state": ((e.get("result") or {}).get("status") or {}).get("state")
                if isinstance(e.get("result"), dict)
                else None,
                "taskId": (e.get("result") or {}).get("taskId")
                if isinstance(e.get("result"), dict)
                else None,
            }
            for e in events[:32]
            if isinstance(e, dict)
        ],
    }
    report.source_evidence_path = write_source_capture(source_out, capture)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Correlate A2A task with agent-mediated MCP tool use")
    p.add_argument("--controller", default=DEFAULT_CONTROLLER)
    p.add_argument("--namespace", default=DEFAULT_NAMESPACE)
    p.add_argument("--agent", default=DEFAULT_AGENT)
    p.add_argument("--prompt", default=DEFAULT_PROMPT)
    p.add_argument("--cluster-context", default=DEFAULT_CLUSTER)
    p.add_argument(
        "--source-out",
        default=str(ROOT / "evidence" / "kagent" / "tmp" / "agent-mcp-trace-latest.json"),
    )
    p.add_argument("--output", choices=["human", "json"], default="json")
    p.add_argument("--skip-logs", action="store_true")
    p.add_argument("--timeout", type=float, default=90.0)
    return p.parse_args(argv)


def emit_human(report: TraceReport) -> None:
    data = report.to_sanitized_dict()
    d = data["decision"]
    tag = "[PASS]" if d["passed"] else "[FAIL]"
    print(f"{tag} {d['reason']} (exit={d['exitCode']})")
    print(f"  taskOrMessageId={data['a2a']['taskOrMessageId']}")
    print(f"  toolObserved={data['toolInvocation']['observed']}")
    print(f"  matched={data['result']['matched']}")


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        if not args.controller.strip():
            raise a2a.UsageFailure("controller is required")
        report = run_trace(
            controller=args.controller,
            namespace=args.namespace,
            agent=args.agent,
            prompt=args.prompt,
            cluster_context=args.cluster_context,
            source_out=Path(args.source_out),
            skip_logs=args.skip_logs,
            timeout=args.timeout,
        )
    except a2a.UsageFailure as exc:
        print(f"[FAIL] usage: {exc}", file=sys.stderr)
        return ExitCode.USAGE

    if args.output == "json":
        print(json.dumps(report.to_sanitized_dict(), indent=2))
    else:
        emit_human(report)
    return int(report.exit_code)


if __name__ == "__main__":
    sys.exit(main())
