#!/usr/bin/env python3
"""Persist a sanitized Lane A experiment record under evidence/kagent/experiments/."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
    example = str(payload.get("example", "unknown"))
    return {
        "schemaVersion": "1.0",
        "recordedAt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "example": example,
        "agents": payload.get("agents", []),
        "taskId": payload.get("taskId"),
        "durationMs": payload.get("durationMs"),
        "pass": payload.get("pass"),
        "artifactSummary": payload.get("artifactSummary", {}),
        "nonClaims": payload.get("nonClaims", []),
        "cleanup": cleanup,
        "notes": notes[:240],
        "source": {
            "controller": payload.get("target", {}).get("controller"),
            "namespace": payload.get("target", {}).get("namespace"),
            "agent": payload.get("target", {}).get("agent"),
        },
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    record = build_record(payload, cleanup=args.cleanup, notes=args.notes)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    date_prefix = datetime.now(UTC).strftime("%Y-%m-%d")
    out_path = args.output_dir / f"{date_prefix}-{record['example']}.json"
    out_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
