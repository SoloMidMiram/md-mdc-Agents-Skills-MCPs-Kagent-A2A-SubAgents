"""Replay a synthetic documentation review using only verified local fixtures."""

from __future__ import annotations

import asyncio
import json
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
LINK = re.compile(r"\[[A-Za-z0-9 ]+\]\(#([a-z0-9]+(?:-[a-z0-9]+)*)\)")


def check(files: dict[str, str]) -> dict[str, Any]:
    """Check the deliberately small lab dialect; cite physical LF lines."""
    findings: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for path, content in sorted(files.items()):
        anchors: set[str] = set()
        links: list[tuple[int, str, str]] = []
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
            heading = HEADING.fullmatch(line)
            if heading:
                anchor = heading[1].lower().replace(" ", "-")
                if anchor in anchors:
                    unresolved.append(f"{path}:{number}: duplicate heading")
                anchors.add(anchor)
                continue
            matches = list(LINK.finditer(line))
            remainder = LINK.sub("", line)
            if any(char in remainder for char in "#[]`<>*_\\") or (
                line and set(line) <= set("=- ")
            ):
                unresolved.append(f"{path}:{number}: unsupported Markdown syntax")
            links.extend((number, excerpt, match[1]) for match in matches)
        if fence:
            unresolved.append(f"{path}: unclosed code fence")
        for number, excerpt, anchor in links:
            if anchor not in anchors:
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
    result = {
        "summary": f"{len(findings)} missing heading references.",
        "findings": findings,
        "passedChecks": [] if findings or unresolved else ["Supported heading references resolve."],
        "unresolvedQuestions": unresolved,
    }
    return docs_bundle.validate_findings(result, files)


def load_fixture(name: str, root: Path = FIXTURES) -> tuple[dict[str, str], dict[str, str]]:
    """Read exact bytes; expected digests are checked-in, never recalculated here."""
    raw = (root / name / "bundle.json").read_bytes().decode("utf-8")
    files = docs_bundle.validate_bundle(raw)
    if set(files) != {"guide.md"}:
        raise ContractError("fixture path must be guide.md")
    if (root / name / "guide.md").read_bytes() != files["guide.md"].encode("utf-8"):
        raise ContractError("fixture content differs from digest-verified bundle")
    manifest = json.loads(raw)
    return files, {item["path"]: item["sha256"] for item in manifest["files"]}


async def replay(root: Path = FIXTURES) -> dict[str, Any]:
    bundles = {name: load_fixture(name, root) for name in ("broken", "fixed")}
    results: dict[str, Any] = {}
    stages: list[dict[str, Any]] = []

    async def invoke(
        agent: str, payload: dict[str, Any], remaining: float
    ) -> orchestration.Subtask:
        index = len(stages) + 1
        if agent == orchestration.PLANNER:
            selected = "fixed" if "feedback" in payload else "broken"
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
                    f"{selected}:{f['path']}:{f['startLine']}: missing heading target"
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

    decision = await orchestration.coordinate("EDU-02 offline review", invoke, timeout=10)
    return {
        "schemaVersion": "1.0",
        "origin": "synthetic",
        "capabilityPromotion": False,
        "bundles": {name: {"digests": digests} for name, (_, digests) in bundles.items()},
        "results": results,
        "stages": stages,
        "decision": asdict(decision),
    }


def main() -> int:
    try:
        report = asyncio.run(replay())
        results, decision = report["results"], report["decision"]
        if not (
            len(results["broken"]["findings"]) == 1
            and not results["broken"]["unresolvedQuestions"]
            and not results.get("fixed", {}).get("findings", [None])
            and not results["fixed"]["unresolvedQuestions"]
            and decision["verdict"] == "approve"
            and decision["revisions"] == 1
            and len(decision["subtasks"]) == 4
        ):
            raise ContractError("unexpected lab outcome")
        print(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True))
        return 0
    except (ContractError, OSError, ValueError, KeyError, TypeError, TimeoutError) as exc:
        print(f"EDU-02 failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
