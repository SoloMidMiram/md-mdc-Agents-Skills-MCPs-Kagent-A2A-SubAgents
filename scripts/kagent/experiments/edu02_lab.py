"""Replay a synthetic documentation review using only verified local fixtures."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import posixpath
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from scripts.kagent.experiments import docs_bundle
from scripts.kagent.experiments import e2r_orchestration as orchestration
from scripts.kagent.experiments.contracts import ContractError

FIXTURES = Path(__file__).with_name("fixtures") / "edu02"
HEADING = re.compile(r"#{1,6} ([A-Za-z0-9]+(?: [A-Za-z0-9]+)*)")
LINK = re.compile(
    r"(?<!!)\[[A-Za-z0-9 ]+\]\("
    r"((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_-][A-Za-z0-9_.-]*\.md)?"
    r"#([a-z0-9]+(?:-[a-z0-9]+)*)\)"
)
FIXTURE_FILES = ("guide.md", "runbook.md")
MAX_DIAGNOSTICS = 128


def check(files: dict[str, str]) -> dict[str, Any]:
    """Check the deliberately small lab dialect; cite physical LF lines."""
    findings: list[dict[str, Any]] = []
    unresolved: list[str] = []
    anchors: dict[str, dict[str, int]] = {}
    links: list[tuple[str, int, str, str, str]] = []
    identities: list[tuple[str, str]] = []
    for path, content in sorted(files.items()):
        path_anchors: dict[str, int] = {}
        anchors[path] = path_anchors
        fence: str | None = None
        segments = content.split("\n")
        for number, segment in enumerate(segments, 1):
            if number == len(segments) and not segment:
                continue
            excerpt = segment + ("\n" if number < len(segments) else "")
            line = segment.removesuffix("\r")
            marker = re.fullmatch(r"(`{3,}|~{3,})([A-Za-z0-9_-]*)", line)
            if fence:
                if line == fence:
                    fence = None
                continue
            if marker:
                fence = marker[1]
                continue
            if line.strip() and line[0] in " \t":
                unresolved.append(f"{path}:{number}: unsupported indentation")
                continue
            heading = HEADING.fullmatch(line)
            if heading:
                anchor = heading[1].lower().replace(" ", "-")
                path_anchors[anchor] = path_anchors.get(anchor, 0) + 1
                if path_anchors[anchor] == 2:
                    unresolved.append(f"{path}:{number}: duplicate heading")
                continue
            matches = list(LINK.finditer(line))
            remainder = LINK.sub("", line)
            if any(char in remainder for char in "#[]`<>*_\\") or (
                line and set(line) <= set("=- ")
            ):
                unresolved.append(f"{path}:{number}: unsupported Markdown syntax")
                continue
            for relative, anchor in (match.groups() for match in matches):
                target = (
                    posixpath.normpath(posixpath.join(posixpath.dirname(path), relative))
                    if relative
                    else path
                )
                links.append((path, number, excerpt, target, anchor))
        if fence:
            unresolved.append(f"{path}: unclosed code fence")

    for path, number, excerpt, target, anchor in dict.fromkeys(links):
        if target == ".." or target.startswith("../"):
            unresolved.append(f"{path}:{number}: target escapes bundle")
            continue
        count = anchors.get(target, {}).get(anchor, 0)
        if count == 1:
            continue
        if count > 1:
            unresolved.append(f"{path}:{number}: ambiguous target {target}#{anchor}")
            continue
        findings.append(
            {
                "severity": "error",
                "category": "missing_internal_target",
                "path": path,
                "startLine": number,
                "endLine": number,
                "excerpt": excerpt,
            }
        )
        identities.append((target, anchor))
    if len(findings) + len(unresolved) > MAX_DIAGNOSTICS:
        raise ContractError("fixture exceeds diagnostic limit")
    result = {
        "summary": f"{len(findings)} missing heading references.",
        "findings": findings,
        "passedChecks": [] if findings or unresolved else ["Supported heading references resolve."],
        "unresolvedQuestions": unresolved,
    }
    docs_bundle.validate_findings(result, files)
    # Lab IDs augment the report only after the E3 citation validation.
    for finding, (target, anchor) in zip(findings, identities, strict=True):
        identity = json.dumps([finding, target, anchor], sort_keys=True, ensure_ascii=True)
        finding["findingId"] = "edu02-" + hashlib.sha256(identity.encode("ascii")).hexdigest()
    return result


def _fixture_path(path: Path) -> Path:
    if path.is_symlink() or path.is_junction():
        raise ContractError("fixture path redirects outside its checked-in location")
    return path


def load_fixture(name: str, root: Path = FIXTURES) -> tuple[dict[str, str], dict[str, str]]:
    """Read exact bytes; expected digests are checked-in, never recalculated here."""
    if name not in ("broken", "fixed"):
        raise ContractError("unknown fixture")
    fixture = _fixture_path(_fixture_path(root) / name)
    with _fixture_path(fixture / "bundle.json").open("rb") as manifest_file:
        raw = manifest_file.read(docs_bundle.MAX_JSON_BYTES + 1).decode("utf-8")
    files = docs_bundle.validate_bundle(raw)
    if set(files) != set(FIXTURE_FILES):
        raise ContractError("unexpected fixture paths")
    for path in FIXTURE_FILES:
        with _fixture_path(fixture / path).open("rb") as source_file:
            content = source_file.read(docs_bundle.MAX_FILE_BYTES + 1)
        if content != files[path].encode("utf-8"):
            raise ContractError("fixture content differs from digest-verified bundle")
    manifest = json.loads(raw)
    return files, {item["path"]: item["sha256"] for item in manifest["files"]}


async def replay(
    root: Path = FIXTURES, *, case: str = "review", timeout: float = 10
) -> dict[str, Any]:
    cases = {"review": ("broken", "fixed"), "broken": ("broken",), "fixed": ("fixed",)}
    if case not in cases:
        raise ContractError("unknown replay case")
    selected_cases = cases[case]
    bundles = {name: load_fixture(name, root) for name in selected_cases}
    results: dict[str, Any] = {}
    stages: list[dict[str, Any]] = []

    async def invoke(
        agent: str, payload: dict[str, Any], _remaining: float
    ) -> orchestration.Subtask:
        index = len(stages) + 1
        if agent == orchestration.PLANNER:
            selected = selected_cases[-1] if "feedback" in payload else selected_cases[0]
            artifact = {
                "goal": "Review supplied Markdown heading references",
                "constraints": ["offline", "synthetic"],
                "files": [selected],
                "acceptance_criteria": ["No findings or unresolved syntax"],
                "tests": ["Heading reference checker"],
                "risks": ["Limited Markdown dialect"],
            }
        else:
            selected = payload["proposed_plan"]["files"][0]
            result = check(bundles[selected][0])
            results[selected] = result
            approved = not result["findings"] and not result["unresolvedQuestions"]
            artifact = {
                "verdict": "approve" if approved else "revise",
                "findings": [
                    f"{f['findingId']} {selected}:{f['path']}:{f['startLine']}:"
                    " missing heading target"
                    for f in result["findings"]
                ],
                "missing_requirements": result["unresolvedQuestions"],
                "required_changes": []
                if approved
                else ["Select the pre-authored corrected fixture"],
            }
        stages.append({"stage": index, "agent": agent, "fixture": selected})
        return orchestration.Subtask(
            agent,
            "completed",
            f"edu02-request-{index}",
            f"edu02-task-{index}",
            artifact,
            f"edu02-message-{index}",
        )

    decision = await orchestration.coordinate("EDU-02 offline review", invoke, timeout=timeout)
    digests = {name: hashes for name, (_, hashes) in bundles.items()}
    packet = json.dumps(digests, sort_keys=True, ensure_ascii=True)
    return {
        "schemaVersion": "1.0",
        "origin": "synthetic",
        "capabilityPromotion": False,
        "bundles": {name: {"digests": hashes} for name, hashes in digests.items()},
        "packetSha256": hashlib.sha256(packet.encode("ascii")).hexdigest(),
        "results": results,
        "stages": stages,
        "decision": asdict(decision),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("review", "broken", "fixed"), default="review")
    case = parser.parse_args(argv).case
    try:
        report = asyncio.run(replay(case=case))
        results, decision = report["results"], report["decision"]
        expected = {"review": ("approve", 1), "broken": ("reject", 1), "fixed": ("approve", 0)}
        if (decision["verdict"], decision["revisions"]) != expected[case] or any(
            result["unresolvedQuestions"] or len(result["findings"]) != int(name == "broken")
            for name, result in results.items()
        ):
            raise ContractError("unexpected lab outcome")
        print(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True))
        return 0
    except (ContractError, OSError, ValueError, KeyError, TypeError, TimeoutError) as exc:
        print(f"EDU-02 failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
