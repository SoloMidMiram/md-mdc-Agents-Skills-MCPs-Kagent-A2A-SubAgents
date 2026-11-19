"""Replay two exact patch fixtures with an independent synthetic evaluator."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import runpy
from collections.abc import Awaitable, Callable
from copy import deepcopy
from dataclasses import asdict
from difflib import unified_diff
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from scripts.kagent.experiments import docs_bundle
from scripts.kagent.experiments import e2r_orchestration as orchestration
from scripts.kagent.experiments.contracts import ContractError

MODULE = "discount.py"
VISIBLE = "visible.json"
PATCH = "candidate.diff"
BASE = """def total_cents(quantity, member):
    total = quantity * 100
    return total * 90 // 100 if member and quantity > 10 else total
"""
FIXES = {
    "correct": BASE.replace("quantity > 10", "quantity >= 10"),
    "misleading": BASE.replace("member and quantity > 10", "quantity >= 10"),
}
VISIBLE_CASES = (("member_at_boundary", 10, True, 900),)
HELD_CASES = (
    ("nonmember_at_boundary", 10, False, 1000),
    ("nonmember_above_boundary", 11, False, 1100),
    ("member_below_boundary", 9, True, 900),
    ("member_above_boundary", 11, True, 990),
)
MAX_PATCH_BYTES = 1024

type Worker = Callable[[Path, bytes], Awaitable[None]]
type Reviewer = Callable[[dict[str, Any]], dict[str, Any]]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(data: Any) -> bytes:
    return json.dumps(data, ensure_ascii=True, sort_keys=True).encode("ascii")


def patch_bytes(case: str) -> bytes:
    return "".join(
        unified_diff(
            BASE.splitlines(keepends=True),
            FIXES[case].splitlines(keepends=True),
            fromfile=f"a/{MODULE}",
            tofile=f"b/{MODULE}",
        )
    ).encode("ascii")


def apply_patch(before: str, patch: bytes) -> str:
    """Apply a single whole-file fixture hunk to its exact context."""
    if len(patch) > MAX_PATCH_BYTES:
        raise ContractError("oversize patch")
    try:
        lines = patch.decode("ascii").splitlines(keepends=True)
    except UnicodeError as exc:
        raise ContractError("malformed patch") from exc
    if lines[:2] != [f"--- a/{MODULE}\n", f"+++ b/{MODULE}\n"]:
        raise ContractError("patch target outside allowlist")
    source = before.splitlines(keepends=True)
    header = f"@@ -1,{len(source)} +1,{len(source)} @@\n"
    if len(lines) < 4 or lines[2] != header:
        raise ContractError("malformed hunk header")
    old, new = [], []
    for line in lines[3:]:
        if line[:1] not in (" ", "+", "-") or not line.endswith("\n"):
            raise ContractError("malformed patch body")
        if line[0] != "+":
            old.append(line[1:])
        if line[0] != "-":
            new.append(line[1:])
    if old != source or len(new) != len(source):
        raise ContractError("hunk context or size mismatch")
    return "".join(new)


def require_inventory(root: Path, files: set[str]) -> None:
    if root.is_symlink() or root.is_junction() or not root.is_dir():
        raise ContractError("fixture root redirected")
    entries = list(root.iterdir())
    if {p.name for p in entries} != files or any(
        p.is_symlink() or p.is_junction() or not p.is_file() for p in entries
    ):
        raise ContractError("unexpected, redirected, or unauthorized worker file")


async def fixture_worker(root: Path, patch: bytes) -> None:
    (root / PATCH).write_bytes(patch)


def evaluate(root: Path, changed: str) -> dict[str, list[dict[str, Any]]]:
    # The controller has already bound changed to exact fixture bytes.
    module = root / MODULE
    module.write_bytes(changed.encode("ascii"))
    (root / VISIBLE).write_bytes(encoded(VISIBLE_CASES))
    held = root / "heldout.json"
    held.write_bytes(encoded(HELD_CASES))
    total = runpy.run_path(str(module))["total_cents"]
    results = {}
    for label, source in (("visible", root / VISIBLE), ("heldout", held)):
        results[label] = [
            {"caseId": identity, "expected": expected, "observed": total(quantity, member)}
            for identity, quantity, member, expected in json.loads(source.read_bytes())
        ]
    return results


async def replay(
    case: str,
    *,
    worker: Worker = fixture_worker,
    reviewer: Reviewer = deepcopy,
    timeout: float = 2,
) -> dict[str, Any]:
    if case not in FIXES:
        raise ContractError("unknown fixture case")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ContractError("timeout must be finite and positive")
    exact_patch = patch_bytes(case)
    frozen_digest = digest(exact_patch)
    original = {MODULE: BASE.encode("ascii"), VISIBLE: encoded(VISIBLE_CASES)}
    bundle = {
        "schemaVersion": "1.0",
        "bundleId": "edu03-worker-input",
        "files": [
            {"path": name, "content": content.decode("ascii"), "sha256": digest(content)}
            for name, content in sorted(original.items())
        ],
    }
    docs_bundle.validate_bundle(encoded(bundle).decode("ascii"))
    with TemporaryDirectory(prefix="edu03-worker-") as workspace:
        root = Path(workspace)
        for name, content in original.items():
            (root / name).write_bytes(content)
        loop = asyncio.get_running_loop()
        task = asyncio.current_task()
        cancelling = task.cancelling() if task else 0
        when = loop.time() + timeout
        try:
            async with asyncio.timeout_at(when):
                await worker(root, exact_patch)
        except TimeoutError:
            raise
        except Exception as exc:
            if task and task.cancelling() > cancelling:
                raise asyncio.CancelledError from None
            if loop.time() >= when:
                raise TimeoutError("worker deadline expired") from None
            raise ContractError("fixture worker failed") from exc
        if task and task.cancelling() > cancelling:
            raise asyncio.CancelledError
        if loop.time() >= when:
            raise TimeoutError("worker deadline expired")
        require_inventory(root, {*original, PATCH})
        for name, content in original.items():
            with (root / name).open("rb") as f:
                if f.read(len(content) + 1) != content:
                    raise ContractError("worker mutated a protected fixture")
        with (root / PATCH).open("rb") as f:
            returned = f.read(MAX_PATCH_BYTES + 1)
        changed = apply_patch(BASE, returned)
        if digest(returned) != frozen_digest or changed != FIXES[case]:
            raise ContractError("patch does not match frozen candidate")

    # Only verified patched source crosses into the separate evaluator root.
    with TemporaryDirectory(prefix="edu03-evaluator-") as evaluator:
        results = evaluate(Path(evaluator), changed)

    record = {
        "case": case,
        "baseSha256": digest(original[MODULE]),
        "patchSha256": frozen_digest,
        "resultSha256": digest(changed.encode("ascii")),
        "changedPaths": [MODULE],
        "checks": results,
    }
    failed = [
        f"{group}:{row['caseId']}"
        for group, rows in results.items()
        for row in rows
        if row["observed"] != row["expected"]
    ]
    evidence = digest(encoded(record))
    expected = {
        "verdict": "revise" if failed else "approve",
        "findings": [f"evidence_sha256={evidence}", *failed],
        "missing_requirements": [],
        "required_changes": ["Preserve membership eligibility"] if failed else [],
    }
    index = 0

    async def invoke(
        agent: str, _payload: dict[str, Any], _remaining: float
    ) -> orchestration.Subtask:
        nonlocal index
        index += 1
        if agent == orchestration.PLANNER:
            artifact = {
                "goal": "Review the frozen fixture result",
                "constraints": ["Only approve independently verified checks"],
                "files": [MODULE],
                "acceptance_criteria": ["Visible and held-out checks pass"],
                "tests": ["visible", "heldout"],
                "risks": ["Visible pass can hide nonmember failures"],
            }
        else:
            artifact = reviewer(deepcopy(expected))
            if artifact != expected:
                raise ContractError("review does not match evaluator evidence")
        return orchestration.Subtask(
            agent,
            "completed",
            f"edu03-request-{index}",
            f"edu03-task-{index}",
            artifact,
            f"edu03-message-{index}",
        )

    decision = await orchestration.coordinate("Replay an offline patch fixture", invoke, timeout=2)
    return {
        "origin": "synthetic",
        "capabilityPromotion": False,
        "evidenceSha256": evidence,
        **record,
        "decision": asdict(decision),
        "model": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=(*FIXES, "both"), default="both")
    case = parser.parse_args().case
    cases = tuple(FIXES) if case == "both" else (case,)
    print(json.dumps([asyncio.run(replay(name)) for name in cases], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
