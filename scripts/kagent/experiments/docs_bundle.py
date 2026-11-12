"""Validate supplied E3 documentation without reading files or following links."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from scripts.kagent.experiments.contracts import ContractError

MAX_FILES = 16
MAX_FILE_BYTES = 32_768
MAX_TOTAL_BYTES = 131_072
# JSON escaping can expand each input byte to at most six characters.
MAX_JSON_BYTES = 6 * MAX_TOTAL_BYTES + 16_384


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("duplicate JSON field")
        result[key] = value
    return result


def _shape(value: Any, fields: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.keys() != fields:
        raise ContractError("unexpected object fields")
    return value


def _utf8(value: Any) -> bytes:
    if not isinstance(value, str):
        raise ContractError("expected text")
    try:
        return value.encode("utf-8")
    except UnicodeError as exc:
        raise ContractError("expected valid UTF-8 text") from exc


def validate_bundle(raw: str) -> dict[str, str]:
    """Return the verified in-memory contents indexed by relative POSIX path."""
    if not isinstance(raw, str) or len(raw) > MAX_JSON_BYTES or len(_utf8(raw)) > MAX_JSON_BYTES:
        raise ContractError("bundle JSON exceeds size limit")
    try:
        parsed = json.loads(raw, object_pairs_hook=_object)
    except (ValueError, RecursionError) as exc:
        raise ContractError("invalid bundle JSON") from exc
    bundle = _shape(parsed, {"schemaVersion", "bundleId", "files"})
    identity = _utf8(bundle["bundleId"])
    if bundle["schemaVersion"] != "1.0" or not identity.strip() or len(identity) > 128:
        raise ContractError("invalid bundle version or identity")
    files = bundle["files"]
    if not isinstance(files, list) or not 1 <= len(files) <= MAX_FILES:
        raise ContractError("invalid bundle file count")

    verified: dict[str, str] = {}
    total = 0
    for value in files:
        file = _shape(value, {"path", "content", "sha256"})
        path = file["path"]
        if (
            len(_utf8(path)) > 512
            or any(part in {"", ".", ".."} for part in path.split("/"))
            or any(char in path for char in ("\\", ":", "\x00"))
            or path in verified
        ):
            raise ContractError("invalid or duplicate relative POSIX path")
        content = _utf8(file["content"])
        total += len(content)
        if len(content) > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
            raise ContractError("bundle contents exceed size limit")
        if hashlib.sha256(content).hexdigest() != file["sha256"]:
            raise ContractError("invalid content digest")
        verified[path] = file["content"]
    return verified


def parse_findings(raw: str, files: dict[str, str]) -> dict[str, Any]:
    if len(raw) > MAX_JSON_BYTES or len(_utf8(raw)) > MAX_JSON_BYTES:
        raise ContractError("findings JSON exceeds size limit")
    try:
        parsed = json.loads(raw, object_pairs_hook=_object)
    except (ValueError, RecursionError) as exc:
        raise ContractError("invalid findings JSON") from exc
    return validate_findings(parsed, files)


def validate_findings(response: Any, files: dict[str, str]) -> dict[str, Any]:
    """Verify each finding against exact lines in the supplied bundle."""
    output = _shape(response, {"summary", "findings", "passedChecks", "unresolvedQuestions"})
    if not _utf8(output["summary"]).strip():
        raise ContractError("summary is required")
    for field in ("passedChecks", "unresolvedQuestions"):
        if not isinstance(output[field], list) or any(
            not _utf8(entry).strip() for entry in output[field]
        ):
            raise ContractError(f"invalid {field}")
    findings = output["findings"]
    if not isinstance(findings, list):
        raise ContractError("findings must be a list")
    for value in findings:
        finding = _shape(value, {"severity", "category", "path", "startLine", "endLine", "excerpt"})
        if finding["severity"] not in ("info", "warning", "error") or finding["category"] not in (
            "missing_internal_target",
            "unsupported_claim",
            "contradicted_claim",
        ):
            raise ContractError("invalid finding severity or category")
        path = finding["path"]
        if not isinstance(path, str) or path not in files:
            raise ContractError("citation path is absent from bundle")
        lines = files[path].splitlines(keepends=True)
        start, end = finding["startLine"], finding["endLine"]
        if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(lines):
            raise ContractError("citation line range is invalid")
        if finding["excerpt"] != "".join(lines[start - 1 : end]):
            raise ContractError("citation excerpt does not match")
    return output
