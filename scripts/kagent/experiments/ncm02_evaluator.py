"""Tuning-only NCM-02 evidence checks. No backend or holdout scoring."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from importlib.metadata import version
from pathlib import Path
from typing import Any, Literal

from scripts.kagent.experiments import docs_bundle
from scripts.kagent.experiments.contracts import ContractError

ORIGINAL_FREEZE = "82d3608ed9ac8bfe0abbbca7f58395b9bac471d3b703ca0b1ae7d44024ca1365"
FINAL_FREEZE = "8326a79c5eb739c3129c36f097766cd17549b1ea00ccd345d9dd87f283f8c27c"
TOKENIZER_REVISION = "607a30d783dfa663caf39e06633721c8d4cfcd7e"
TOKENIZER_SHA256 = "8414cab924d8b9b33013f0d221c5862f365ee9be39c5c2bfae8a5a9e970478a6"
TOKENIZER_VERSION = "0.22.1"
BUDGETS = (192, 512, 1024, 2048)
PRODUCT = re.compile(r"(?<![\w-])[A-Z]{2,8}-[0-9]{2,8}(?![\w-])")
CITATION_KEYS = ("path", "startLine", "endLine", "excerpt")
SOURCE_KEYS = (*CITATION_KEYS, "sha256", "provenance")
MAX_LOCAL_FILE = 2 * 1024 * 1024
REVIEW_PROTOCOL = "ncm02-tuning-fidelity-v1"

type Counter = Callable[[str], int]
type MembershipScope = Literal["frozen_tuning", "synthetic_fixture"]


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def hash_text(value: str) -> str:
    return digest(value.encode("utf-8"))


def packed(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def read(path: Path) -> bytes:
    if path.is_symlink() or path.is_junction() or not path.is_file():
        raise ContractError(f"invalid evidence file: {path.name}")
    with path.open("rb") as handle:
        data = handle.read(MAX_LOCAL_FILE + 1)
    if len(data) > MAX_LOCAL_FILE:
        raise ContractError(f"oversize evidence file: {path.name}")
    return data


def verified_freeze(root: Path, expected: str) -> dict[str, bytes]:
    raw = read(root / "freeze.json")
    if digest(raw) != expected:
        raise ContractError("freeze identity mismatch")
    return {name: verify(root / name, sha) for name, sha in json.loads(raw)["filesSha256"].items()}


def verify(path: Path, sha: str) -> bytes:
    data = read(path)
    if digest(data) != sha:
        raise ContractError(f"frozen evidence changed: {path.name}")
    return data


def source_payload(bundle: dict[str, Any]) -> str:
    return "\n".join(f"Source: {f['path']}\n{f['content']}" for f in bundle["files"])


def membership(splits: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    """Check source/identity overlap. This is not a semantic leakage test."""
    seen: dict[tuple[str, str], str] = {}
    counts = {}
    for split, bundles in splits.items():
        document_count = 0
        local_cases = set()
        for bundle in bundles:
            files = docs_bundle.validate_bundle(packed(bundle))
            case = bundle["bundleId"]
            if case in local_cases:
                raise ContractError("duplicate case identity")
            local_cases.add(case)
            keys = [("case", case)]
            for path, content in files.items():
                document_count += 1
                normalized = " ".join(unicodedata.normalize("NFKC", content).casefold().split())
                keys.extend(
                    (
                        ("path", path.casefold()),
                        ("bytes", hash_text(content)),
                        ("normalized", hash_text(normalized)),
                    )
                )
            for key in keys:
                if seen.setdefault(key, split) != split:
                    raise ContractError(f"cross-set membership overlap: {key[0]}")
        counts[split] = document_count
    return counts


@dataclass(frozen=True)
class CaseIdentity:
    case: str
    source_sha256: str
    gold_sha256: str


def case_identity(bundle: dict[str, Any], annotation: dict[str, Any]) -> CaseIdentity:
    case = bundle.get("bundleId")
    if not isinstance(case, str) or not case.startswith("t-") or annotation.get("caseId") != case:
        raise ContractError("only aligned tuning case IDs are accepted")
    if not isinstance(annotation.get("facts"), list) or not annotation["facts"]:
        raise ContractError("tuning gold must contain critical facts")
    return CaseIdentity(case, hash_text(packed(bundle)), hash_text(packed(annotation)))


@dataclass(frozen=True)
class _TuningMembership:
    scope: MembershipScope
    cases: tuple[CaseIdentity, ...]

    def require(self, bundle: dict[str, Any], annotation: dict[str, Any]) -> CaseIdentity:
        identity = case_identity(bundle, annotation)
        if identity not in self.cases:
            raise ContractError("source or gold is outside verified tuning membership")
        return identity


def synthetic_tuning(bundle: dict[str, Any], annotation: dict[str, Any]) -> _TuningMembership:
    """Admit a test record explicitly, outside the frozen benchmark path."""
    identity = case_identity(bundle, annotation)
    docs_bundle.validate_bundle(packed(bundle))
    for fact in annotation["facts"]:
        validate_anchor(bundle, fact["source"])
    return _TuningMembership("synthetic_fixture", (identity,))


def load_tuning(
    root: Path,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, int],
    _TuningMembership,
]:
    original = verified_freeze(root, ORIGINAL_FREEZE)
    final = verified_freeze(root / "review-20261119" / "final-v1", FINAL_FREEZE)
    # Gold for both held-out splits is integrity-checked only.
    tuning = json.loads(original["tuning-sources.json"])
    gold = json.loads(original["tuning-gold.json"])
    baseline = json.loads(original["tuning-offline.json"])
    counts = membership(
        {
            "tuning": tuning,
            "observedHoldout": json.loads(original["heldout-sources.json"]),
            "final": json.loads(final["sources.json"]),
        }
    )
    if counts != {"tuning": 16, "observedHoldout": 16, "final": 23}:
        raise ContractError("frozen document count mismatch")
    if not (len(tuning) == len(gold) == len(baseline) == 14):
        raise ContractError("tuning case count mismatch")
    identities = []
    for bundle, annotation, row in zip(tuning, gold, baseline, strict=True):
        identity = case_identity(bundle, annotation)
        if identity.case != row["caseId"]:
            raise ContractError("unaligned tuning records")
        if source_payload(bundle) != row["raw"]:
            raise ContractError("raw baseline differs from bound source")
        for fact in annotation["facts"]:
            validate_anchor(bundle, fact["source"])
        identities.append(identity)
    return tuning, gold, baseline, counts, _TuningMembership("frozen_tuning", tuple(identities))


def validate_anchor(bundle: dict[str, Any], source: Any) -> None:
    if not isinstance(source, dict):
        raise ContractError("invalid source anchor record")
    provenance = source.get("provenance")
    if (
        set(source) != set(SOURCE_KEYS)
        or not isinstance(provenance, dict)
        or (provenance.get("origin") != "synthetic")
    ):
        raise ContractError("invalid source provenance")
    files = docs_bundle.validate_bundle(packed(bundle))
    path = source.get("path")
    file = files.get(path) if isinstance(path, str) else None
    if file is None or source.get("sha256") != hash_text(file):
        raise ContractError("stale or missing source digest")
    citation = {key: source.get(key) for key in CITATION_KEYS}
    docs_bundle.validate_findings(
        {
            "summary": "Verify tuning citation",
            "unresolvedQuestions": [],
            "passedChecks": [],
            "findings": [{**citation, "category": "unsupported_claim", "severity": "info"}],
        },
        files,
    )


def pinned_counter(path: Path) -> Counter:
    asset = verify(path, TOKENIZER_SHA256)
    if version("tokenizers") != TOKENIZER_VERSION:
        raise ContractError("consumer tokenizer version mismatch")
    tokenizer = import_module("tokenizers").Tokenizer.from_str(asset.decode("utf-8"))
    return lambda text: len(tokenizer.encode(text, add_special_tokens=False).ids)


@dataclass(frozen=True)
class ReviewBinding:
    scope: MembershipScope
    case: CaseIdentity
    candidate_sha256: str
    protocol: str = REVIEW_PROTOCOL


@dataclass(frozen=True)
class Review:
    binding: ReviewBinding
    reviewed_by: str
    preserved: frozenset[str]
    reversed: frozenset[str] = frozenset()
    unsupported: tuple[str, ...] = ()
    unresolved: bool = False


def fact_id(fact: dict[str, Any]) -> str:
    return hash_text(packed(fact))


def contains(text: str, token: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(token)}(?![\w-])", text) is not None


def evaluate(
    bundle: dict[str, Any],
    annotation: dict[str, Any],
    candidate: object,
    anchors: object,
    review: Review | None,
    *,
    tuning: _TuningMembership,
    budget: int,
    counter: Counter | None = None,
) -> dict[str, Any]:
    identity = tuning.require(bundle, annotation)
    if budget not in BUDGETS:
        raise ContractError("unsupported byte budget")
    raw = source_payload(bundle)
    reasons = []
    facts = annotation["facts"]
    required = {fact_id(f) for f in facts}
    names = {identifier for f in facts for identifier in f["requiredIdentifiers"]}
    values = {value for f in facts for value in f["requiredValuesWithUnits"]}
    candidate_text = candidate if isinstance(candidate, str) else ""
    candidate_bytes = None
    if isinstance(candidate, str):
        try:
            candidate_bytes = candidate.encode("utf-8")
        except UnicodeEncodeError:
            candidate_text = ""
    candidate_sha = digest(candidate_bytes) if candidate_bytes is not None else None
    if candidate_bytes is None or not candidate_text.strip() or len(candidate_bytes) > budget:
        reasons.append("invalid_or_oversize_candidate")
    retained_names = {name for name in names if contains(candidate_text, name)}
    if names != retained_names:
        reasons.append("required_identifier_missing")
    if any(not contains(candidate_text, value) for value in values):
        reasons.append("required_value_missing")
    if set(PRODUCT.findall(candidate_text)) - set(PRODUCT.findall(raw)):
        reasons.append("fabricated_product_identifier")
    invalid_review = (
        review is None
        or candidate_sha is None
        or review.binding != ReviewBinding(tuning.scope, identity, candidate_sha)
        or not review.reviewed_by.strip()
        or bool((review.preserved | review.reversed) - required)
    )
    if invalid_review:
        reasons.append("review_binding_mismatch")
    elif review is not None:
        if required - review.preserved:
            reasons.append("critical_fact_missing")
        if review.reversed:
            reasons.append("constraint_reversed")
        if review.unsupported:
            reasons.append("unsupported_claim")
        if review.unresolved:
            reasons.append("unresolved_semantics")
    expected_anchors = {packed({key: f["source"][key] for key in SOURCE_KEYS}) for f in facts}
    observed = set()
    try:
        if not isinstance(anchors, list):
            raise ContractError("invalid anchor list")
        for anchor in anchors:
            validate_anchor(bundle, anchor)
            encoded = packed({key: anchor[key] for key in SOURCE_KEYS})
            encoded.encode("utf-8")  # Confirm that the delivered sidecar is encodable.
            observed.add(encoded)
    except (ContractError, TypeError, ValueError):
        reasons.append("invalid_provenance")
    if not expected_anchors <= observed:
        reasons.append("required_anchor_missing")
    accepted = not reasons
    delivered = packed({"text": candidate, "anchors": anchors}) if accepted else raw
    return {
        "caseId": identity.case,
        "membershipScope": tuning.scope,
        "sourceBundleSha256": identity.source_sha256,
        "goldAnnotationSha256": identity.gold_sha256,
        "reviewProtocol": REVIEW_PROTOCOL,
        "budgetBytes": budget,
        "candidateSha256": candidate_sha,
        "accepted": accepted,
        "reasons": reasons,
        "fallback": None if accepted else "raw",
        "rawSha256": hash_text(raw),
        "requiredCriticalFacts": len(required),
        "reviewedCriticalFactsRetained": (
            None
            if invalid_review or review is None or review.unresolved
            else len(review.preserved - review.reversed)
        ),
        "requiredIdentifiers": len(names),
        "retainedIdentifiers": len(retained_names),
        "verbatimCriticalFacts": sum(f["criticalFact"] in candidate_text for f in facts),
        "rawBytes": len(raw.encode("utf-8")),
        "candidateBytes": len(candidate_bytes) if candidate_bytes is not None else None,
        "deliveredBytes": len(delivered.encode("utf-8")),
        "rawConsumerTokens": counter(raw) if counter else None,
        "deliveredConsumerTokens": counter(delivered) if counter else None,
    }


def dry_run(root: Path, *, tokenizer_json: Path | None = None) -> dict[str, Any]:
    bundles, gold, rows, counts, tuning = load_tuning(root)
    counter = pinned_counter(tokenizer_json) if tokenizer_json is not None else None
    bundle, annotation, control = next(
        (a, b, c) for a, b, c in zip(bundles, gold, rows, strict=True) if a["bundleId"] == "t-cold"
    )
    identity = tuning.require(bundle, annotation)
    original = control["extractive"]
    fact = annotation["facts"][0]
    # Independently supplied synthetic labels for this one inspected tuning case.
    reviewed_excerpt = "Tulipa gesneriana TG-044 must stay between 2 °C and 5 °C."
    if fact["criticalFact"] != reviewed_excerpt or reviewed_excerpt not in original:
        raise ContractError("dry-run reviewer fixture changed")
    anchor = fact["source"]
    reviewed = frozenset({fact_id(fact)})
    cases = [
        ("retained_extractive", original, [anchor], frozenset(), (), reviewed, "extractive"),
        (
            "fixed_paraphrase",
            "Store Tulipa gesneriana TG-044 within 2 °C to 5 °C.",
            [anchor],
            frozenset(),
            (),
            reviewed,
            "synthetic",
        ),
        (
            "verbatim_plus_reversal",
            reviewed_excerpt + "\nActually, it must not stay in that range.",
            [anchor],
            reviewed,
            (),
            reviewed,
            "synthetic",
        ),
        (
            "verbatim_plus_fabrication",
            reviewed_excerpt + "\nTG-999 was delivered today.",
            [anchor],
            frozenset(),
            ("unrecorded delivery",),
            reviewed,
            "synthetic",
        ),
        (
            "ids_and_values_only",
            "Tulipa gesneriana TG-044, 2 °C, 5 °C.",
            [anchor],
            frozenset(),
            (),
            frozenset(),
            "synthetic",
        ),
        (
            "missing_identifier",
            "Tulips must stay within 2 °C to 5 °C.",
            [anchor],
            frozenset(),
            (),
            reviewed,
            "synthetic",
        ),
        (
            "stale_anchor",
            reviewed_excerpt,
            [{**anchor, "sha256": "0" * 64}],
            frozenset(),
            (),
            reviewed,
            "synthetic",
        ),
    ]
    results = [
        {
            "control": label,
            "arm": arm,
            **evaluate(
                bundle,
                annotation,
                candidate,
                anchors,
                Review(
                    ReviewBinding(tuning.scope, identity, hash_text(candidate)),
                    "predeclared-control-annotation",
                    kept,
                    reversed_ids,
                    unsupported,
                ),
                tuning=tuning,
                budget=192,
                counter=counter,
            ),
        }
        for label, candidate, anchors, reversed_ids, unsupported, kept, arm in cases
    ]
    accepted = sum(row["accepted"] for row in results)
    return {
        "origin": "synthetic",
        "capabilityPromotion": False,
        "split": "tuning",
        "documentCounts": counts,
        "originalFreezeSha256": ORIGINAL_FREEZE,
        "finalFreezeSha256": FINAL_FREEZE,
        "consumerTokenizer": {
            "revision": TOKENIZER_REVISION,
            "sha256": TOKENIZER_SHA256,
            "implementation": f"tokenizers=={TOKENIZER_VERSION}",
            "addSpecialTokens": False,
        },
        "attempts": len(results),
        "accepted": accepted,
        "rejected": len(results) - accepted,
        "fallbacks": sum(row["fallback"] is not None for row in results),
        "coverage": accepted / len(results),
        "results": results,
        "realNcm": None,
        "latencyMs": None,
        "memoryBytes": None,
        "cost": None,
        "benchmarkDecision": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus_root", type=Path)
    parser.add_argument("--tokenizer-json", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            dry_run(args.corpus_root, tokenizer_json=args.tokenizer_json), indent=2, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
