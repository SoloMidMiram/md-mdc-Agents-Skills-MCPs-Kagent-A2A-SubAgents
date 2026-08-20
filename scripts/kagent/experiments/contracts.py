"""JSON output contracts for Lane A kagent A2A educational examples."""

from __future__ import annotations

import json
import re
from typing import Any

PLANNER_REQUIRED_KEYS = frozenset(
    {"goal", "constraints", "files", "acceptance_criteria", "tests", "risks"}
)
REVIEWER_REQUIRED_KEYS = frozenset(
    {"verdict", "findings", "missing_requirements", "required_changes"}
)
REVIEWER_VERDICTS = frozenset({"approve", "revise"})
SUPERVISOR_TOP_KEYS = frozenset({"verdict", "plan", "review", "summary"})


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
    missing = PLANNER_REQUIRED_KEYS - obj.keys()
    if missing:
        raise ContractError(f"planner artifact missing keys: {sorted(missing)}")
    if not isinstance(obj["goal"], str) or not obj["goal"].strip():
        raise ContractError("planner.goal must be a non-empty string")
    for key in ("constraints", "files", "acceptance_criteria", "tests", "risks"):
        if not isinstance(obj[key], list):
            raise ContractError(f"planner.{key} must be a list")
    return obj


def validate_reviewer_artifact(obj: dict[str, Any]) -> dict[str, Any]:
    missing = REVIEWER_REQUIRED_KEYS - obj.keys()
    if missing:
        raise ContractError(f"reviewer artifact missing keys: {sorted(missing)}")
    verdict = str(obj["verdict"]).strip().lower()
    if verdict not in REVIEWER_VERDICTS:
        raise ContractError(f"reviewer.verdict must be one of {sorted(REVIEWER_VERDICTS)}")
    for key in ("findings", "missing_requirements", "required_changes"):
        if not isinstance(obj[key], list):
            raise ContractError(f"reviewer.{key} must be a list")
    return obj


def validate_supervisor_artifact(obj: dict[str, Any]) -> dict[str, Any]:
    """Supervisor returns a composite artifact referencing plan and review."""
    if not SUPERVISOR_TOP_KEYS.intersection(obj.keys()):
        raise ContractError(
            "supervisor artifact must include at least one of: "
            f"{sorted(SUPERVISOR_TOP_KEYS)}"
        )
    if "plan" in obj:
        validate_planner_artifact(obj["plan"])
    if "review" in obj:
        validate_reviewer_artifact(obj["review"])
    if "verdict" in obj:
        verdict = str(obj["verdict"]).strip().lower()
        if verdict not in REVIEWER_VERDICTS:
            raise ContractError(f"supervisor.verdict must be one of {sorted(REVIEWER_VERDICTS)}")
    return obj


def validate_artifact(role: str, text: str) -> dict[str, Any]:
    obj = extract_json_object(text)
    if role == "planner-agent":
        return validate_planner_artifact(obj)
    if role == "reviewer-agent":
        return validate_reviewer_artifact(obj)
    if role == "supervisor-agent":
        return validate_supervisor_artifact(obj)
    raise ContractError(f"unsupported role for artifact validation: {role}")
