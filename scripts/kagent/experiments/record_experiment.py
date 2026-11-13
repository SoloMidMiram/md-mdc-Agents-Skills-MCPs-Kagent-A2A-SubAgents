#!/usr/bin/env python3
"""Persist a sanitized Lane A experiment record under evidence/kagent/experiments/."""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

_spec = importlib.util.spec_from_file_location(
    "record_contracts", Path(__file__).with_name("contracts.py")
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("experiment contracts could not be loaded")
contracts = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(contracts)

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EVIDENCE_DIR = ROOT / "evidence" / "kagent" / "experiments"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record sanitized kagent A2A experiment evidence.")
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="JSON file from run_a2a_example.py --output json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_EVIDENCE_DIR,
        help="Evidence destination directory",
    )
    parser.add_argument(
        "--cleanup",
        action="append",
        default=[],
        help="Cleanup command to include in the record (repeatable)",
    )
    parser.add_argument("--notes", default="", help="Optional operator note (sanitized length)")
    return parser.parse_args(argv)


def build_record(payload: dict[str, Any], *, cleanup: list[str], notes: str) -> dict[str, Any]:
    contracts.validate_evidence_payload(payload)
    if (
        not isinstance(notes, str)
        or not isinstance(cleanup, list)
        or any(not isinstance(command, str) for command in cleanup)
    ):
        raise contracts.ContractError("notes and cleanup must be text")
    accepted = payload["pass"] is True  # Recomputed required gates above, not truthiness.
    record = contracts.sanitize_evidence(
        {
            "schemaVersion": "1.1",
            "recordedAt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "example": payload["example"],
            "agents": payload.get("agents", []),
            "taskId": payload.get("taskId"),
            "durationMs": payload.get("durationMs"),
            "pass": accepted,
            "reason": payload["reason"],
            "artifact": payload.get("artifact"),
            "artifactSummary": payload.get("artifactSummary", {}),
            "nonClaims": sorted(set(payload["nonClaims"]) | {"L6", "I3", "I4", "L7"}),
            "cleanup": cleanup,
            "notes": contracts.sanitize_evidence(notes)[:240],
            "observation": {
                "schemaVersion": payload["schemaVersion"],
                "observedAt": payload["observedAt"],
                "requestId": payload.get("requestId"),
                "taskId": payload.get("taskId"),
                "dispatchState": payload.get("dispatchState"),
                "claimedPass": payload["pass"],
                "card": payload.get("card"),
            },
            "acceptance": {
                "passed": accepted,
                "rule": "educational-completed-artifact-v1",
                "scope": "validated source claims; not independently authenticated runtime proof",
            },
            "source": {
                "controller": payload.get("target", {}).get("controller"),
                "namespace": payload.get("target", {}).get("namespace"),
                "agent": payload.get("target", {}).get("agent"),
            },
        }
    )
    if not isinstance(record, dict):
        raise contracts.ContractError("sanitized record must be an object")
    return record


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.input.stat().st_size > 1_048_576:
            raise contracts.ContractError("input evidence exceeds 1 MiB")
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        record = build_record(payload, cleanup=args.cleanup, notes=args.notes)
        encoded = json.dumps(record, indent=2, allow_nan=False) + "\n"
        args.output_dir.mkdir(parents=True, exist_ok=True)
        date_prefix = datetime.now(UTC).strftime("%Y-%m-%d")
        out_path = (
            args.output_dir.resolve() / f"{date_prefix}-{record['example']}-{uuid4().hex}.json"
        )
        with out_path.open("x", encoding="utf-8") as destination:
            destination.write(encoded)
    except (ValueError, TypeError, OSError) as exc:
        print(f"record rejected: {contracts.sanitize_evidence(str(exc))}")
        return 2
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
