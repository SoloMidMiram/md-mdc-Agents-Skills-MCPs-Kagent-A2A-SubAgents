"""JSON output contracts for Lane A kagent A2A educational examples."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

PLANNER_REQUIRED_KEYS = frozenset(
    {"goal", "constraints", "files", "acceptance_criteria", "tests", "risks"}
)
REVIEWER_REQUIRED_KEYS = frozenset(
    {"verdict", "findings", "missing_requirements", "required_changes"}
)
REVIEWER_VERDICTS = frozenset({"approve", "revise"})
SUPERVISOR_TOP_KEYS = frozenset({"verdict", "plan", "review", "summary"})
EXAMPLE_AGENTS = {
    "e1-planner": "planner-agent",
    "phase2-reviewer": "reviewer-agent",
    "e2-supervisor": "supervisor-agent",
    "e3-docs": "docs-agent",
}
TERMINAL_STATES = frozenset({"completed", "failed", "canceled", "cancelled", "rejected"})
TASK_STATES = TERMINAL_STATES | {"submitted", "working", "input_required", "auth_required"}
SENSITIVE = re.compile(
    r"authorization|bearer\s|api[-_ ]?key|(?:access[-_ ]?)?token|password|"
    r"secret|credential|master[-_ ]?key|session[-_ ]?id|kubeconfig|-----BEGIN.*PRIVATE KEY",
    re.IGNORECASE,
)


class ContractError(ValueError):
    """Raised when an artifact does not match the educational contract."""


def extract_json_object(text: str) -> dict[str, Any]:
    """Return the first JSON object found in model text (markdown fences tolerated)."""
    stripped = text.strip()
    if not stripped:
        raise ContractError("empty response text")

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL | re.IGNORECASE)
    if fence:
        stripped = fence.group(1)

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end <= start:
        raise ContractError("response does not contain a JSON object")

    try:
        parsed = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ContractError(f"invalid JSON object: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ContractError("parsed JSON must be an object")
    return parsed


def validate_planner_artifact(obj: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise ContractError("planner artifact must be an object")
    missing = PLANNER_REQUIRED_KEYS - obj.keys()
    if missing:
        raise ContractError(f"planner artifact missing keys: {sorted(missing)}")
    if not isinstance(obj["goal"], str) or not obj["goal"].strip():
        raise ContractError("planner.goal must be a non-empty string")
    for key in ("constraints", "files", "acceptance_criteria", "tests", "risks"):
        _string_list(obj[key], f"planner.{key}")
    return obj


def validate_reviewer_artifact(obj: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise ContractError("reviewer artifact must be an object")
    missing = REVIEWER_REQUIRED_KEYS - obj.keys()
    if missing:
        raise ContractError(f"reviewer artifact missing keys: {sorted(missing)}")
    verdict = obj["verdict"]
    if not isinstance(verdict, str) or verdict not in REVIEWER_VERDICTS:
        raise ContractError(f"reviewer.verdict must be one of {sorted(REVIEWER_VERDICTS)}")
    for key in ("findings", "missing_requirements", "required_changes"):
        _string_list(obj[key], f"reviewer.{key}")
    return obj


def validate_supervisor_artifact(obj: dict[str, Any]) -> dict[str, Any]:
    """Supervisor returns a composite artifact referencing plan and review."""
    if not isinstance(obj, dict) or not SUPERVISOR_TOP_KEYS.issubset(obj):
        raise ContractError(
            f"supervisor artifact must include all of: {sorted(SUPERVISOR_TOP_KEYS)}"
        )
    _nonempty_text(obj["summary"], "supervisor.summary")
    validate_planner_artifact(obj["plan"])
    validate_reviewer_artifact(obj["review"])
    if (
        not isinstance(obj["verdict"], str)
        or obj["verdict"] not in REVIEWER_VERDICTS
        or obj["verdict"] != obj["review"]["verdict"]
    ):
        raise ContractError("supervisor verdict must agree with the review")
    return obj


def _nonempty_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field} must be non-empty text")
    return value


def _string_list(value: Any, field: str) -> None:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ContractError(f"{field} must be a list of strings")


def validate_example(example: Any, agent: Any) -> None:
    if not isinstance(example, str) or example not in EXAMPLE_AGENTS:
        raise ContractError("example must be a registered educational example identifier")
    if EXAMPLE_AGENTS[example] != agent:
        raise ContractError("example and target agent disagree")


def validate_evidence_payload(payload: Any, *, docs_files: dict[str, str] | None = None) -> None:
    """Validate source observations; a producer's pass flag is never sufficient."""
    if not isinstance(payload, dict):
        raise ContractError("evidence must be an object")
    if payload.get("schemaVersion") not in ("1.0", "1.1"):
        raise ContractError("unsupported source schemaVersion")
    if type(payload.get("pass")) is not bool:
        raise ContractError("pass must be a boolean")
    observed = _nonempty_text(payload.get("observedAt"), "observedAt")
    try:
        timestamp = datetime.fromisoformat(observed.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError("observedAt must be an ISO timestamp") from exc
    if timestamp.utcoffset() is None:
        raise ContractError("observedAt must include a timezone")
    target = payload.get("target")
    if not isinstance(target, dict):
        raise ContractError("target must be an object")
    for key in ("controller", "namespace", "agent"):
        _nonempty_text(target.get(key), f"target.{key}")
    try:
        origin = urlsplit(target["controller"])
        if origin.scheme not in {"http", "https"} or not origin.hostname:
            raise ValueError
        _ = origin.port
    except ValueError as exc:
        raise ContractError("controller must be an HTTP origin") from exc
    validate_example(payload.get("example"), target["agent"])
    if payload.get("agents") != [target["agent"]]:
        raise ContractError("agents must match the target agent")
    duration = payload.get("durationMs")
    if type(duration) is not int or duration < 0:
        raise ContractError("durationMs must be a non-negative integer")
    _nonempty_text(payload.get("reason"), "reason")
    _string_list(payload.get("nonClaims"), "nonClaims")
    state = payload.get("dispatchState")
    if state is not None and (not isinstance(state, str) or state not in TASK_STATES):
        raise ContractError("unrecognized dispatchState")
    if not payload["pass"]:
        return  # Failed card/transport/contract runs need not have a task or artifact.
    for key in ("taskId", "requestId"):
        identifier = _nonempty_text(payload.get(key), key)
        if len(identifier) > 128 or SENSITIVE.search(identifier):
            raise ContractError(f"{key} must be bounded and credential-free")
    if state != "completed":
        raise ContractError("successful evidence requires terminal completed state")
    card = payload.get("card")
    if not isinstance(card, dict) or any(
        card.get(key) is not True for key in ("accepted", "deploymentReady")
    ):
        raise ContractError("successful evidence requires accepted and ready card")
    try:
        artifact_text = json.dumps(payload.get("artifact"), allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise ContractError("artifact must contain finite JSON data") from exc
    if target["agent"] == "docs-agent":
        if docs_files is None:
            raise ContractError("E3 evidence requires the original verified bundle")
        from scripts.kagent.experiments.docs_bundle import validate_findings

        validate_findings(payload["artifact"], docs_files)
    else:
        validate_artifact(target["agent"], artifact_text)


def sanitize_evidence(value: Any) -> Any:
    """Minimize retained JSON and redact credential-labelled fields and text.

    This is bounded evidence hygiene, not a guarantee for arbitrary unlabeled secrets.
    """
    if isinstance(value, dict):
        return {
            key: "[redacted]" if SENSITIVE.search(key) else sanitize_evidence(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_evidence(item) for item in value]
    if isinstance(value, str):

        def origin_only(match: re.Match[str]) -> str:
            try:
                url = urlsplit(match[0])
                host = url.hostname or ""
                if ":" in host:
                    host = f"[{host}]"
                port = f":{url.port}" if url.port is not None else ""
                return urlunsplit((url.scheme, host + port, "", "", ""))
            except ValueError:
                return "[redacted-url]"

        text = re.sub(r"https?://[^\s<>\"']+", origin_only, value)
        return "[redacted]" if SENSITIVE.search(text) else text[:1000]
    if isinstance(value, float) and not math.isfinite(value):
        raise ContractError("non-finite evidence number")
    return value


def validate_artifact(role: str, text: str) -> dict[str, Any]:
    obj = extract_json_object(text)
    if role == "planner-agent":
        return validate_planner_artifact(obj)
    if role == "reviewer-agent":
        return validate_reviewer_artifact(obj)
    if role == "supervisor-agent":
        return validate_supervisor_artifact(obj)
    raise ContractError(f"unsupported role for artifact validation: {role}")
