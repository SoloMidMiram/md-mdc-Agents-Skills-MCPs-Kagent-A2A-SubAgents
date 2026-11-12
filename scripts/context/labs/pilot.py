"""Offline lab capture and fail-closed historical coding pilot. No model calls in CI."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import time
import zipfile
from pathlib import Path

BASE = "c6021d456bbcce20fec817470aa5237907d7728a"
BUILDER = "fe3aea3f0aba9ea2cd040194dd898c91391b3240"
TREE = "8e64b24580268f294a8947bcdc8370a98e569cf1"
ROOT = Path(__file__).resolve().parents[3]
BOUNDARY_SPEC = importlib.util.spec_from_file_location(
    "runner_boundaries", Path(__file__).with_name("boundaries.py")
)
boundaries = importlib.util.module_from_spec(BOUNDARY_SPEC)
BOUNDARY_SPEC.loader.exec_module(boundaries)
ORDERS = (
    ("ordinary", "manual", "ctx"),
    ("manual", "ctx", "ordinary"),
    ("ctx", "ordinary", "manual"),
)
TASKS = (
    "Repair physical source-line citations when UTF-8 content contains Unicode separators. "
    "Preserve schema 1.0, valid inputs and source integrity.",
    "Prevent selected edited or missing working files hidden by Git index flags from passing "
    "context validation. Preserve legitimate checkout normalization and read-only behavior.",
    "Make valid Unicode context JSON stdout work under restrictive console encodings. "
    "Preserve schema 1.0, deterministic output and file-output behavior.",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(value, indent=2, ensure_ascii=True) + "\n")


def call(args: list[str], cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, timeout=timeout, check=False)


def git(repo: Path, *args: str) -> bytes:
    result = call(["git", "--no-optional-locks", "-C", str(repo), *args], repo)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors="replace"))
    return result.stdout


def fresh_source(repo: Path, target: Path) -> str:
    """Export only ancestor source bytes; never share descendant Git objects."""
    target.mkdir()
    raw = git(repo, "-c", "core.autocrlf=false", "archive", "--format=zip", BASE)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for entry in archive.infolist():
            relative = Path(entry.filename)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("unsafe archive path")
        archive.extractall(target)
    git(target, "init", "-q")
    git(target, "config", "core.autocrlf", "false")
    git(target, "config", "core.longpaths", "true")
    # Original history includes tracked files matching its own ignore patterns.
    git(target, "add", "--force", ".")
    expected_tree = git(repo, "rev-parse", f"{BASE}^{{tree}}").strip()
    if git(target, "write-tree").strip() != expected_tree:
        raise ValueError("exported source tree differs from historical baseline")
    git(
        target,
        "-c",
        "user.name=CTX Lab",
        "-c",
        "user.email=lab@example.invalid",
        "-c",
        "core.hooksPath=",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-qm",
        "source only",
    )
    # Disable descendant-facing MCP config in the run invocation, not by editing the source tree.
    return git(target, "rev-parse", "HEAD").decode().strip()


def manifest_path(root: Path) -> Path:
    return root / "manifest.json"


def load(root: Path, expected_manifest_sha256: str | None = None) -> dict:
    raw = manifest_path(root).read_bytes()
    if expected_manifest_sha256 is not None and digest(raw) != expected_manifest_sha256:
        raise ValueError("manifest anchor mismatch")
    data = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=boundaries.unique_object,
        parse_constant=boundaries.reject_constant,
    )
    if data.get("version") != "1.0" or len(data.get("runs", [])) != 9:
        raise ValueError("invalid pilot manifest")
    if [r["id"] for r in data["runs"]] != [f"r{i:02}" for i in range(1, 10)]:
        raise ValueError("invalid run IDs")
    expected = {
        "model": "gpt-6.1-sol",
        "reasoning": "medium",
        "cli": "0.164.0",
        "timeout_seconds": 600,
        "upstream": BASE,
        "builder": BUILDER,
        "tree": TREE,
    }
    if any(data.get(key) != value for key, value in expected.items()):
        raise ValueError("frozen configuration changed")
    if [(r["challenge"], r["condition"]) for r in data["runs"]] != [
        (i, arm) for i, order in enumerate(ORDERS) for arm in order
    ]:
        raise ValueError("run order/condition mismatch")
    for name, expected in data["inputs"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or digest(path.read_bytes()) != expected:
            raise ValueError("input digest mismatch")
    return data


def prepare(repo: Path, output: Path) -> str:
    if output.resolve().is_relative_to(repo.resolve()):
        raise ValueError("artifacts must be outside the source checkout")
    output.mkdir()  # Refuse existing directory, including an interrupted preparation.
    started = time.perf_counter()
    if git(
        repo,
        "diff",
        "--name-only",
        TREE,
        "--",
        "scripts/context/build_packet.py",
        "tests/context/fixtures/lab-01.json",
    ).strip():
        raise ValueError("CTX-01R builder or LAB-01 fixture differs from qualified source")
    runs, inputs = [], {}
    builder = repo / "scripts/context/build_packet.py"
    for challenge, order in enumerate(ORDERS):
        # All prepared arms select the same pre-fix implementation excerpt.
        raw = git(repo, "cat-file", "blob", f"{BASE}:scripts/context/build_packet.py")
        lines = raw.decode("utf-8").splitlines()
        spans = ((68, 113), (68, 100), (145, len(lines)))
        first, last = spans[challenge]
        spec = {
            "schema_version": "1.0",
            "source_revision": BASE,
            "task": TASKS[challenge],
            "sources": [
                {
                    "id": "implementation",
                    "path": "scripts/context/build_packet.py",
                    "start_line": first,
                    "end_line": last,
                    "sha256": digest(raw),
                }
            ],
            "claims": [],
            "unknowns": ["Root cause and correct patch are not supplied."],
            "exclusions": ["Do not alter tests or unrelated files; do not publish changes."],
        }
        # Selected baseline source must match the pinned revision during construction.
        selection = output / f"selection-{challenge}"
        fresh_source(repo, selection)
        # Builder checks old source SHA; add ancestor objects only in preparer's private clone.
        obj = (repo / ".git/objects").resolve().as_posix()
        (selection / ".git/objects/info/alternates").write_bytes((obj + "\n").encode())
        spec_file = output / f"spec-{challenge}.json"
        save(spec_file, spec)
        packet_file = output / f"packet-{challenge}.json"
        result = call(
            [
                sys.executable,
                str(builder),
                "--repo",
                str(selection),
                "--spec",
                str(spec_file),
                "--output",
                str(packet_file),
            ],
            repo,
        )
        if result.returncode:
            raise ValueError(
                "packet construction failed: " + result.stderr.decode(errors="replace")
            )
        brief = output / f"brief-{challenge}.txt"
        brief.write_text(
            "Agent-authored hand-selected brief; not human preparation.\n"
            f"Revision {BASE}; scripts/context/build_packet.py:{first}-{last}; "
            f"full-blob SHA256 {digest(raw)}\n" + "\n".join(lines[first - 1 : last]) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        for arm in order:
            run_id = f"r{len(runs) + 1:02}"
            subject = output / run_id
            local = fresh_source(repo, subject)
            identity_path = output / f"{run_id}-identity.json"
            save(identity_path, boundaries.subject_identity(subject))
            inputs[identity_path.name] = digest(identity_path.read_bytes())
            prompt = output / f"{run_id}-prompt.txt"
            context = (
                brief.read_text(encoding="utf-8")
                if arm == "manual"
                else packet_file.read_text(encoding="utf-8")
                if arm == "ctx"
                else ""
            )
            prompt.write_text(
                TASKS[challenge] + "\nOnly repair scripts/context/build_packet.py. "
                "Run visible context tests; preserve unrelated files.\n" + context,
                encoding="utf-8",
                newline="\n",
            )
            runs.append(
                {
                    "id": run_id,
                    "challenge": challenge,
                    "condition": arm,
                    "local_commit": local,
                    "prompt": prompt.name,
                    "identity": identity_path.name,
                }
            )
            record(output, run_id, "prepared", local_commit=local)
            for path in (prompt, brief, spec_file, packet_file):
                inputs[path.name] = digest(path.read_bytes())
    protocol = {
        "version": "1.0",
        "upstream": BASE,
        "builder": BUILDER,
        "tree": TREE,
        "model": "gpt-6.1-sol",
        "reasoning": "medium",
        "cli": "0.164.0",
        "timeout_seconds": 600,
        "preparation_seconds": time.perf_counter() - started,
        "manual_author": "agent",
        "runs": runs,
        "inputs": inputs,
    }
    save(manifest_path(output), protocol)
    return digest(manifest_path(output).read_bytes())


def record(root: Path, run_id: str, state: str, **fields: object) -> None:
    save(root / f"{run_id}-{state}.json", {"state": state, **fields})


def run(root: Path, launcher: Path | None, expected_manifest_sha256=None) -> None:
    data = load(root)
    terminal = ("running", "blocked", "completed", "failed", "timeout", "evaluated")
    if any(any(root.glob(f"r??-{state}.json")) for state in terminal) or any(
        root.glob("r??.patch")
    ):
        raise ValueError("run attempt already recorded; prepare a fresh pilot")
    # Launcher is trusted infrastructure, not an agent-authored assertion/receipt.
    # No ordinary host execution is offered as a fallback.
    reason = (
        "No trusted read-isolating launcher installed; ordinary host can read evaluator/repair."
    )
    if launcher is None:
        for item in data["runs"]:
            record(root, item["id"], "blocked", reason=reason, model_calls=0)
        return
    # No launcher-provided proof is sufficient. The independent verifier and its
    # trust path have not been implemented/qualified; never execute the supplied file.
    for item in data["runs"]:
        try:
            validate_launch(root, item, expected_manifest_sha256)
            reason = "Independent qualification trust path unavailable; launcher not executed"
        except (OSError, ValueError) as exc:
            reason = f"Launch identity rejected: {exc}"
        record(root, item["id"], "blocked", reason=reason, model_calls=0)


def validate_launch(root: Path, item: dict, expected_manifest_sha256: str) -> dict:
    if not isinstance(expected_manifest_sha256, str) or len(expected_manifest_sha256) != 64:
        raise ValueError("external manifest anchor required")
    # Recheck all frozen context/spec/prompt/identity digests.
    data = load(root, expected_manifest_sha256)
    if item not in data["runs"] or "identity" not in item:
        raise ValueError("missing frozen launch identity; prepare a new attempt set")
    name = item["identity"]
    if name not in data["inputs"] or item["prompt"] not in data["inputs"]:
        raise ValueError("unsealed identity or prompt")
    for path in (name, item["prompt"]):
        if digest((root / path).read_bytes()) != data["inputs"][path]:
            raise ValueError("frozen launch input mismatch")
    expected = json.loads((root / name).read_text(encoding="utf-8"))
    if expected.get("subject_commit") != item["local_commit"]:
        raise ValueError("manifest subject identity mismatch")
    return boundaries.validate_identity(root / item["id"], expected)


def validate_setup_boundary(root: Path, item: dict, probe, expected_manifest_sha256: str) -> dict:
    """Controller helper for offline race tests; this does not authorize execution."""
    before = validate_launch(root, item, expected_manifest_sha256)
    probe()
    after = validate_launch(root, item, expected_manifest_sha256)
    if before != after:
        raise ValueError("identity drift during setup")
    return after


def evaluate(root: Path, evaluator: Path) -> None:
    data = load(root)
    for item in data["runs"]:
        run_id = item["id"]
        blocked = root / f"{run_id}-blocked.json"
        if blocked.exists():
            record(root, run_id, "evaluated", outcome="blocked", correctness=None)
            continue
        terminal = [root / f"{run_id}-{s}.json" for s in ("completed", "failed", "timeout")]
        found = [p for p in terminal if p.exists()]
        if len(found) != 1:
            raise ValueError(f"{run_id}: no unique terminal execution; evaluator not launched")
        execution = json.loads(found[0].read_text(encoding="utf-8"))
        patch = root / f"{run_id}.patch"
        if digest(patch.read_bytes()) != execution["patch_sha256"]:
            raise ValueError("patch digest mismatch")
        # Even a plausible terminal file cannot establish independent qualification.
        # Keep failed/timeout/unqualified executions out of the scoring path.
        record(root, run_id, "evaluated", outcome="unqualified_execution", correctness=None)
        continue


def summarize(root: Path) -> dict:
    data = load(root)
    rows = []
    for item in data["runs"]:
        path = root / f"{item['id']}-evaluated.json"
        if not path.exists():
            raise ValueError("incomplete evaluation; no successful summary")
        result = json.loads(path.read_text(encoding="utf-8"))
        if result.get("correctness") is not None or result.get("outcome") not in {
            "blocked",
            "unqualified_execution",
        }:
            raise ValueError("scoring disabled until independent execution qualification")
        captures = [root / f"{item['id']}-{s}.json" for s in ("completed", "failed", "timeout")]
        capture = next(
            (json.loads(p.read_text(encoding="utf-8")) for p in captures if p.exists()), {}
        )
        rows.append(
            {
                **item,
                **capture,
                **result,
                "cash_cost": None,
                "usage": capture.get("usage"),
                "elapsed_seconds": capture.get("elapsed_seconds"),
                "citation_validity": result.get("citation_validity"),
                "critical_source_coverage": result.get("critical_source_coverage"),
                "unsupported_claims": result.get("unsupported_claims"),
            }
        )
    result = {
        "runs": rows,
        "scored_runs": sum(r["correctness"] is not None for r in rows),
        "cash_cost": "unknown",
        "conclusion": "Exploratory only; no statistical superiority claim.",
    }
    save(root / "summary.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run", "evaluate", "summarize"))
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--launcher", type=Path)
    parser.add_argument("--expected-manifest-sha256")
    parser.add_argument("--evaluator", type=Path)
    args = parser.parse_args()
    try:
        root = args.artifacts.resolve()
        if args.command == "prepare":
            print(prepare(args.repo.resolve(), root))
        elif args.command == "run":
            run(root, args.launcher, args.expected_manifest_sha256)
        elif args.command == "evaluate":
            evaluate(root, args.evaluator or Path("not-configured"))
        else:
            print(json.dumps(summarize(root), indent=2))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"CTX lab rejected: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
