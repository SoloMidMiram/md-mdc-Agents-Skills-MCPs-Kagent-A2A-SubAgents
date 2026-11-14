"""Capture real packet replay and explicitly synthetic corruption controls."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from pilot import ROOT, call, digest, git, save


def replay(output: Path) -> None:
    spec = ROOT / "tests/context/fixtures/lab-01.json"
    request = json.loads(spec.read_text(encoding="utf-8"))
    builder = ROOT / "scripts/context/build_packet.py"
    outputs = []
    for name in ("packet-a.json", "packet-b.json"):
        command = [
            sys.executable,
            str(builder),
            "--repo",
            str(ROOT),
            "--spec",
            str(spec),
            "--output",
            str(output / name),
        ]
        result = call(command, ROOT)
        save(output / f"{name}.command.json", {"argv": command, "exit": result.returncode})
        if result.returncode:
            raise ValueError(result.stderr.decode(errors="replace"))
        outputs.append((output / name).read_bytes())
    if outputs[0] != outputs[1]:
        raise ValueError("nondeterministic packet")
    packet = json.loads(outputs[0])
    for source, evidence in zip(request["sources"], packet["evidence"], strict=True):
        raw = git(ROOT, "cat-file", "blob", f"{request['source_revision']}:{source['path']}")
        if hashlib.sha256(raw).hexdigest() != source["sha256"]:
            raise ValueError("citation hash mismatch")
        # Independent byte scanner: LF alone delimits source lines.
        lines, start = [], 0
        for end, char in enumerate(raw):
            if char == 10:
                line = raw[start:end]
                lines.append(line[:-1] if line.endswith(b"\r") else line)
                start = end + 1
        if start < len(raw):
            lines.append(raw[start:])
        excerpt = b"\n".join(lines[source["start_line"] - 1 : source["end_line"]]).decode("utf-8")
        if excerpt != evidence["excerpt"]:
            raise ValueError("citation excerpt mismatch")
    save(
        output / "replay.json",
        {
            "sources_valid": len(packet["evidence"]),
            "source_revision": request["source_revision"],
            "builder_tree": git(ROOT, "rev-parse", "HEAD^{tree}").decode().strip(),
            "packet_sha256": digest(outputs[0]),
            "identical": True,
        },
    )


def corruption(output: Path) -> None:
    synthetic = output / "synthetic"
    synthetic.mkdir()
    results = []
    for kind in ("hash", "span", "edit", "delete", "assume", "skip", "utf8"):
        repo = synthetic / kind
        repo.mkdir()
        git(repo, "init", "-q")
        git(repo, "config", "core.autocrlf", "false")
        raw = b"first\nsecond\n" if kind != "utf8" else b"\xff\n"
        source = repo / "source.txt"
        source.write_bytes(raw)
        git(repo, "add", "source.txt")
        git(
            repo,
            "-c",
            "user.name=Lab",
            "-c",
            "user.email=lab@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "synthetic source",
        )
        spec = {
            "schema_version": "1.0",
            "source_revision": git(repo, "rev-parse", "HEAD").decode().strip(),
            "task": "Read source",
            "sources": [
                {
                    "id": "s",
                    "path": "source.txt",
                    "start_line": 1,
                    "end_line": 1,
                    "sha256": digest(raw),
                }
            ],
            "claims": [],
            "unknowns": [],
            "exclusions": [],
        }
        if kind == "hash":
            spec["sources"][0]["sha256"] = "0" * 64
        if kind == "span":
            spec["sources"][0]["end_line"] = 99
        if kind in ("assume", "skip"):
            git(
                repo,
                "update-index",
                "--assume-unchanged" if kind == "assume" else "--skip-worktree",
                "source.txt",
            )
        if kind in ("edit", "assume", "skip"):
            source.write_bytes(b"changed\n")
        if kind == "delete":
            source.unlink()
        request = repo / "request.json"
        save(request, spec)
        index = (repo / ".git/index").read_bytes()
        selected = source.read_bytes() if source.exists() else None
        command = [
            sys.executable,
            str(ROOT / "scripts/context/build_packet.py"),
            "--repo",
            str(repo),
            "--spec",
            str(request),
        ]
        for mode in ("stdout", "absent", "sentinel"):
            target = repo / f"{mode}.json"
            if mode == "sentinel":
                target.write_bytes(b"sentinel")
            argv = command if mode == "stdout" else [*command, "--output", str(target)]
            result = call(argv, repo)
            valid = result.returncode == 2 and result.stdout == b""
            valid &= (
                target.read_bytes() == b"sentinel" if mode == "sentinel" else not target.exists()
            )
            valid &= (repo / ".git/index").read_bytes() == index
            valid &= (source.read_bytes() if source.exists() else None) == selected
            results.append(
                {
                    "synthetic": True,
                    "case": kind,
                    "mode": mode,
                    "argv": argv,
                    "exit": result.returncode,
                    "stderr": result.stderr.decode(errors="replace"),
                    "passed": valid,
                }
            )
    save(output / "corruption.json", results)
    if not all(r["passed"] for r in results):
        raise ValueError("corruption control failed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("replay", "corruption"))
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    try:
        output = args.artifacts.resolve()
        if output.is_relative_to(ROOT):
            raise ValueError("artifacts must be outside source checkout")
        output.mkdir()
        (replay if args.command == "replay" else corruption)(output)
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"lab failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
