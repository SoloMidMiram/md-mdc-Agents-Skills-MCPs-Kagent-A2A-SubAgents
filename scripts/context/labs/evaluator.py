"""Trusted post-run evaluator. Never mount this file or its tests into subjects."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def assess(candidate: Path, challenge: int | None = None) -> dict:
    started = time.perf_counter()
    # Private evaluation only: restore pinned fixture objects, not subject access.
    objects = (ROOT / ".git/objects").resolve().as_posix()
    (candidate / ".git/objects/info/alternates").write_bytes((objects + "\n").encode())
    with tempfile.TemporaryDirectory(prefix="ctx-hidden-") as folder:
        external = Path(folder)
        for name in ("test_build_packet.py", "test_integrity_regressions.py"):
            text = (ROOT / "tests/context" / name).read_text(encoding="utf-8")
            text = text.replace(
                "ROOT = Path(__file__).resolve().parents[2]", f"ROOT = Path({str(candidate)!r})"
            )
            text = text.replace(
                'pathlib.Path(__file__).resolve().parents[2] / "scripts/context/build_packet.py"',
                f"pathlib.Path({str(candidate / 'scripts/context/build_packet.py')!r})",
            )
            (external / name).write_text(text, encoding="utf-8", newline="\n")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", str(external)],
            cwd=candidate,
            capture_output=True,
            timeout=180,
            check=False,
        )
        scored = result
        if challenge is not None:
            original = subprocess.check_output(
                [
                    "git",
                    "-C",
                    str(ROOT),
                    "cat-file",
                    "blob",
                    "c6021d456bbcce20fec817470aa5237907d7728a:tests/context/test_build_packet.py",
                ]
            ).decode("utf-8")
            positives = re.findall(r"^def (test_\w+)\(", original, flags=re.MULTILINE)
            nodes = [str(external / "test_build_packet.py") + "::" + name for name in positives]
            defect = (
                ["test_citation_uses_LF_physical_source_line"],
                ["test_dirty_or_missing_source_rejected_even_with_index_flags"],
                [
                    "test_utf8_source_can_be_emitted_to_stdout",
                    "test_utf8_stdout_under_restrictive_encoding",
                ],
            )[challenge]
            nodes += [
                str(external / "test_integrity_regressions.py") + "::" + name for name in defect
            ]
            scored = subprocess.run(
                [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", *nodes],
                cwd=candidate,
                capture_output=True,
                timeout=180,
                check=False,
            )
    return {
        "correctness": scored.returncode == 0,
        "tests_exit": scored.returncode,
        "tests_log": (scored.stdout + scored.stderr).decode(errors="replace"),
        "cross_defect_exit": result.returncode,
        "cross_defect_log": (result.stdout + result.stderr).decode(errors="replace"),
        "evaluation_seconds": time.perf_counter() - started,
        "citation_validity": None,
        "critical_source_coverage": None,
        "unsupported_claims": None,
        "metric_limit": "Citation/semantic metrics need independent assessment; not test-derived.",
    }


if __name__ == "__main__":
    request = json.load(sys.stdin)
    challenge = (int(request["id"][1:]) - 1) // 3
    print(json.dumps(assess(Path(request["candidate"]).resolve(), challenge)))
