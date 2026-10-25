"""Build bounded, revision-pinned context from a human-authored evidence specification."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

MAX_BYTES = 2_000_000


class PacketError(ValueError):
    """The requested packet cannot be grounded in the supplied source revision."""


def git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, check=False, timeout=30
    )
    if result.returncode:
        raise PacketError(f"Git operation failed: {args[0]}")
    return result.stdout


def text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PacketError(f"{label} must be a non-empty string")
    return value


def strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or len(value) > 100:
        raise PacketError(f"{label} must be a list of at most 100 strings")
    return [text(item, label) for item in value]


def source_path(value: Any) -> str:
    path = text(value, "source path")
    parts = PurePosixPath(path).parts
    if (
        not parts
        or path != "/".join(parts)
        or PurePosixPath(path).is_absolute()
        or any(part in {".", "..", ".git"} for part in parts)
        or re.search(r"[\\:*?\[\]\x00-\x1f]", path)
    ):
        raise PacketError("source path must be a canonical repository-relative file path")
    return path


def build_packet(repo: Path, spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict) or spec.get("schema_version") != "1.0":
        raise PacketError("spec schema_version must be 1.0")
    repo = Path(git(repo, "rev-parse", "--show-toplevel").decode().strip())
    revision = spec.get("source_revision")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise PacketError("source_revision must be a full lowercase commit SHA")
    if git(repo, "rev-parse", "--verify", f"{revision}^{{commit}}").decode().strip() != revision:
        raise PacketError("source_revision must identify a commit")
    task = text(spec.get("task"), "task")
    unknowns = strings(spec.get("unknowns"), "unknowns")
    exclusions = strings(spec.get("exclusions"), "exclusions")
    sources = spec.get("sources")
    if not isinstance(sources, list) or not 1 <= len(sources) <= 100:
        raise PacketError("sources must contain 1 to 100 entries")
    evidence = []
    ids: set[str] = set()
    total_bytes = 0
    for source in sources:
        if not isinstance(source, dict):
            raise PacketError("each source must be an object")
        source_id = text(source.get("id"), "source id")
        if source_id in ids:
            raise PacketError("duplicate source id")
        ids.add(source_id)
        path = source_path(source.get("path"))
        # Literal pathspec prevents a filename from turning into a glob or Git magic.
        pathspec = f":(literal){path}"
        entry = git(repo, "ls-tree", revision, "--", pathspec).decode().strip()
        if not entry or entry.split()[0] not in {"100644", "100755"}:
            raise PacketError(f"source is missing or is not a regular tracked file: {path}")
        if git(repo, "diff", "--name-only", revision, "--", pathspec).strip():
            raise PacketError(f"source working copy differs from pinned revision: {path}")
        size = int(git(repo, "cat-file", "-s", f"{revision}:{path}"))
        total_bytes += size
        if total_bytes > MAX_BYTES:
            raise PacketError("source byte budget exceeded")
        data = git(repo, "show", f"{revision}:{path}")
        digest = hashlib.sha256(data).hexdigest()
        if source.get("sha256") != digest:
            raise PacketError(f"source hash mismatch: {path}")
        lines = data.decode("utf-8").splitlines()
        start, end = source.get("start_line"), source.get("end_line")
        if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(lines):
            raise PacketError(f"invalid line range: {path}")
        evidence.append(
            {
                "id": source_id,
                "path": path,
                "start_line": start,
                "end_line": end,
                "sha256": digest,
                "excerpt": "\n".join(lines[start - 1 : end]),
            }
        )
    claims = spec.get("claims")
    if not isinstance(claims, list) or len(claims) > 100:
        raise PacketError("claims must be a list of at most 100 entries")
    checked_claims = []
    for claim in claims:
        if not isinstance(claim, dict) or claim.get("kind") not in {"recorded", "inference"}:
            raise PacketError("claims must declare recorded or inference kind")
        refs = strings(claim.get("source_ids"), "claim source_ids")
        if not refs or not set(refs) <= ids:
            raise PacketError("claim references missing source IDs")
        checked_claims.append(
            {
                "statement": text(claim.get("statement"), "claim"),
                "kind": claim["kind"],
                "source_ids": refs,
            }
        )
    return {
        "schema_version": "1.0",
        "source_revision": revision,
        "task": task,
        "evidence": evidence,
        "claims": checked_claims,
        "unknowns": unknowns,
        "exclusions": exclusions,
        "validation_scope": (
            "source integrity and citation resolution; claim truth is not evaluated"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.spec.stat().st_size > MAX_BYTES:
            raise PacketError("spec byte budget exceeded")
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
        packet = build_packet(args.repo, spec)
        rendered = json.dumps(packet, ensure_ascii=False, indent=2) + "\n"
        if args.output is None:
            print(rendered, end="")
        else:
            # Validate everything before opening output; never overwrite existing artifacts.
            with args.output.open("x", encoding="utf-8", newline="\n") as output:
                output.write(rendered)
        return 0
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"context packet rejected: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
