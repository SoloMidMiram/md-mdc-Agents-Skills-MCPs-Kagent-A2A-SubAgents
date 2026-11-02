"""Preserve combined security gates and LAB-01's original pinned Git evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LAB = "8ff91163f34659531bae5f9ee34fe4ef6d427eed"
EVIDENCE = "evidence/labs/lab-01/2026-10-25"
# Parse in the declared root environment without adding an unlocked stub dependency.
WORKFLOW = json.loads(
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import json,sys,yaml; print(json.dumps(yaml.safe_load(sys.stdin.read())))",
        ],
        input=(ROOT / ".github/workflows/quality.yml").read_text(encoding="utf-8"),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
)


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def test_both_complete_audits_and_artifacts_remain_required() -> None:
    for job, selector, service, artifact in (
        ("kagent-python", "--uv-lock uv.lock", "osv", "root-dependency-audit"),
        (
            "kagent-sdk",
            "--requirements scripts/kagent/experiments/a2a_sdk_requirements.lock",
            "pypi",
            "sdk-dependency-audit",
        ),
    ):
        config = WORKFLOW["jobs"][job]
        steps: list[dict[str, Any]] = config["steps"]
        audits = [
            s
            for s in steps
            if s.get("run", "").startswith("uv run python scripts/security/audit_dependencies.py ")
        ]
        assert len(audits) == 1
        audit = audits[0]
        assert selector in audit["run"] and f"--service {service}" in audit["run"]
        assert "--output" in audit["run"] and "||" not in audit["run"]
        assert not config.get("continue-on-error") and not audit.get("continue-on-error")
        assert "if" not in audit
        uploads = [s for s in steps if s.get("with", {}).get("name") == artifact]
        assert len(uploads) == 1 and uploads[0]["if"] == "always()"
        assert uploads[0]["with"]["path"].endswith(artifact + ".json")


def test_all_conflicting_pester_contracts_keep_their_own_failure_gate() -> None:
    steps = WORKFLOW["jobs"]["evaluation"]["steps"]
    for name in (
        "Run legacy benchmark tests (Pester 3.4.0)",
        "Run skill and hook contracts (Pester 5.7.1)",
        "Verify quality wrapper failures stop validation",
    ):
        matches = [s for s in steps if s.get("name") == name]
        assert len(matches) == 1
        step = matches[0]
        assert "Invoke-Pester" in step["run"]
        assert "$result.FailedCount -gt 0" in step["run"]
        assert "$result.TotalCount -eq 0" in step["run"] and "exit 1" in step["run"]
        assert not step.get("continue-on-error") and "if" not in step


def test_original_lab01_sources_and_retained_copies_remain_reproducible() -> None:
    manifest = json.loads(git("show", f"{LAB}:{EVIDENCE}/source-manifest.json"))
    revision = manifest["revision"]
    assert revision == "a53bfb62f0421a7c28234f871af2bf449a11491f"
    assert len(manifest["sources"]) == 6
    git("merge-base", "--is-ancestor", revision, "HEAD")
    for source in manifest["sources"]:
        original = git("show", f"{revision}:{source['path']}")
        retained = git("show", f"{LAB}:{EVIDENCE}/sources/{source['path']}")
        assert original == retained
        assert hashlib.sha256(original).hexdigest() == source["sha256"]
