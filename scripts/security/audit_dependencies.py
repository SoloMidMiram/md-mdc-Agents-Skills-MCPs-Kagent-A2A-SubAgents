"""Audit every explicit dependency pin and reject incomplete scanner inventories."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
import subprocess
import sys
import tempfile
import tomllib
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def package_key(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def inventory(path: Path, *, uv_lock: bool) -> tuple[list[dict[str, str]], list[str]]:
    packages: list[dict[str, str]] = []
    local_projects: list[str] = []
    if uv_lock:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
        project = tomllib.loads((path.parent / "pyproject.toml").read_text(encoding="utf-8"))
        for item in payload["package"]:
            source = item["source"]
            if "registry" not in source:
                if item["name"] != project["project"]["name"] or source not in (
                    {"virtual": "."},
                    {"editable": "."},
                ):
                    raise ValueError("non-registry dependency requires explicit qualification")
                local_projects.append(item["name"])
                continue
            packages.append({"name": item["name"], "version": item["version"]})
    else:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if re.fullmatch(r"--hash=sha256:[0-9a-f]{64}(?:\s*\\)?", line):
                continue
            # Audit the union of platforms, including the qualified Windows-only pin.
            # Do not evaluate markers and silently drop an inapplicable package.
            if ";" in line:
                pin, marker = line.split(";", 1)
                marker = marker.removesuffix("\\").strip()
                qualified_markers = {
                    "sys_platform == 'win32'",
                    "platform_python_implementation != 'PyPy'",
                    "implementation_name != 'PyPy' and platform_python_implementation != 'PyPy'",
                }
                if marker not in qualified_markers:
                    raise ValueError("unqualified dependency marker")
                line = pin.strip()
            match = re.fullmatch(r"([A-Za-z0-9][A-Za-z0-9_.-]*)==([^\s;\\]+)(?:\s*\\)?", line)
            if not match:
                raise ValueError("audit input must contain exact qualified pins and SHA-256 hashes")
            packages.append({"name": match[1], "version": match[2]})
    if not packages:
        raise ValueError("dependency inventory is empty")
    names = [package_key(p["name"]) for p in packages]
    if len(set(names)) != len(names):
        raise ValueError("duplicate or multi-version package requires explicit qualification")
    return sorted(packages, key=lambda p: package_key(p["name"])), local_projects


def validate_result(expected: list[dict[str, str]], result: Any, scanner_exit: int) -> int:
    if not isinstance(result, dict) or not isinstance(result.get("dependencies"), list):
        raise ValueError("scanner did not return a dependency inventory")
    actual = result["dependencies"]
    for item in actual:
        if (
            not isinstance(item, dict)
            or "skip_reason" in item
            or not isinstance(item.get("name"), str)
            or not isinstance(item.get("version"), str)
            or not isinstance(item.get("vulns"), list)
        ):
            raise ValueError("scanner skipped or malformed a dependency")
    requested = Counter((package_key(p["name"]), p["version"]) for p in expected)
    observed = Counter((package_key(p["name"]), p["version"]) for p in actual)
    if requested != observed:
        raise ValueError("scanner inventory differs from the complete locked inventory")
    findings = sum(len(item["vulns"]) for item in actual)
    if scanner_exit != (1 if findings else 0):
        raise ValueError("scanner exit disagrees with its findings")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--uv-lock", type=Path)
    inputs.add_argument("--requirements", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--service", choices=("pypi", "osv"), default="pypi")
    args = parser.parse_args()
    path = args.uv_lock or args.requirements
    try:
        packages, local_projects = inventory(path, uv_lock=args.uv_lock is not None)
        with tempfile.TemporaryDirectory(prefix="locked-audit-") as temporary:
            pins = Path(temporary) / "requirements.txt"
            pins.write_text(
                "".join(f"{p['name']}=={p['version']}\n" for p in packages), encoding="utf-8"
            )
            process = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip_audit",
                    "--disable-pip",
                    "--no-deps",
                    "--strict",
                    "--timeout",
                    "20",
                    "--vulnerability-service",
                    args.service,
                    "--requirement",
                    str(pins),
                    "--format",
                    "json",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=300,
                check=False,
            )
        result = json.loads(process.stdout)
        findings = validate_result(packages, result, process.returncode)
        report = {
            "schema_version": "1.0",
            "observed_at": datetime.now(UTC).isoformat(),
            "input": path.as_posix(),
            "working_file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "scanner": {
                "name": "pip-audit",
                "version": importlib.metadata.version("pip-audit"),
                "service": args.service,
                "data": "live advisory-service query; not a Trivy DB snapshot",
            },
            "packages": packages,
            "local_projects": local_projects,
            "expected_count": len(packages),
            "observed_count": len(result["dependencies"]),
            "findings": findings,
            "result": result,
        }
        with args.output.open("x", encoding="utf-8", newline="\n") as destination:
            destination.write(json.dumps(report, indent=2) + "\n")
        print(f"Audited {len(packages)}/{len(packages)} third-party pins; {findings} findings")
        return 1 if findings else 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print(
            f"Dependency audit rejected ({type(exc).__name__}); no complete audit established",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
