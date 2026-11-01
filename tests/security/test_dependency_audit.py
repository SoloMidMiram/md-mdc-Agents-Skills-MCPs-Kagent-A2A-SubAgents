"""Reject false clean scans rather than trusting an auditor's summary exit alone."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "audit", ROOT / "scripts/security/audit_dependencies.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)
EXPECTED = [{"name": "example-package", "version": "1.2.3"}]


@pytest.mark.parametrize(
    "change", ["missing", "extra", "duplicate", "version", "skip", "malformed"]
)
def test_incomplete_or_changed_audit_fails(change):
    row = {"name": "example_package", "version": "1.2.3", "vulns": []}
    actual = [copy.deepcopy(row)]
    if change == "missing":
        actual = []
    elif change in {"extra", "duplicate"}:
        actual.append({**row, "name": "other" if change == "extra" else row["name"]})
    elif change == "version":
        actual[0]["version"] = "1.2.2"
    elif change == "skip":
        actual[0]["skip_reason"] = "unavailable"
    else:
        actual[0]["vulns"] = None
    with pytest.raises(ValueError):
        audit.validate_result(EXPECTED, {"dependencies": actual}, 0)


@pytest.mark.parametrize(
    "findings,exit_code,valid",
    [(0, 0, True), (1, 1, True), (1, 0, False), (0, 1, False), (0, 2, False)],
)
def test_findings_and_exit_must_agree(findings, exit_code, valid):
    result = {"dependencies": [{**EXPECTED[0], "vulns": [{"id": "CVE-example"}] * findings}]}
    if valid:
        assert audit.validate_result(EXPECTED, result, exit_code) == findings
    else:
        with pytest.raises(ValueError):
            audit.validate_result(EXPECTED, result, exit_code)


def test_uv_lock_accounts_for_local_project_and_rejects_unqualified_sources(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname="project"\n', encoding="utf-8")
    lock = tmp_path / "uv.lock"
    root = '[[package]]\nname="project"\nversion="0.1"\nsource={virtual="."}\n'
    dependency = '[[package]]\nname="example-package"\nversion="1.2.3"\nsource={registry="https://pypi.org/simple"}\n'
    lock.write_text(root + dependency, encoding="utf-8")
    assert audit.inventory(lock, uv_lock=True) == (EXPECTED, ["project"])
    lock.write_text(
        root
        + dependency.replace(
            'registry="https://pypi.org/simple"', 'git="https://example.invalid/repo"'
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        audit.inventory(lock, uv_lock=True)


@pytest.mark.parametrize(
    "invalid",
    [
        "",
        "example>=1",
        "--index-url https://example.invalid",
        "example==1; sys_platform == 'unqualified'",
        "example==1\nexample==2",
    ],
)
def test_requirements_cannot_silently_drop_unhandled_inputs(tmp_path, invalid):
    lock = tmp_path / "requirements.lock"
    lock.write_text(invalid, encoding="utf-8")
    with pytest.raises(ValueError):
        audit.inventory(lock, uv_lock=False)


def test_hashes_do_not_hide_pins(tmp_path):
    lock = tmp_path / "requirements.lock"
    lock.write_text(
        "example-package==1.2.3 \\\n    --hash=sha256:" + "a" * 64 + "\n", encoding="utf-8"
    )
    assert audit.inventory(lock, uv_lock=False) == (EXPECTED, [])


def test_windows_marker_is_audited_even_on_another_platform(tmp_path):
    lock = tmp_path / "requirements.lock"
    lock.write_text(
        "example-package==1.2.3 ; sys_platform == 'win32' \\\n    --hash=sha256:" + "a" * 64 + "\n",
        encoding="utf-8",
    )
    assert audit.inventory(lock, uv_lock=False) == (EXPECTED, [])
