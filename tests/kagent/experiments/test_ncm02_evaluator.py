from dataclasses import replace

import pytest

from scripts.kagent.experiments import ncm02_evaluator as ev
from scripts.kagent.experiments.contracts import ContractError

FACT = "TG-044 must not exceed 5 °C."
CONTENT = FACT + "\n"
BASE = {
    "schemaVersion": "1.0",
    "bundleId": "t-negative-control",
    "files": [{"path": "synthetic.md", "content": CONTENT, "sha256": ev.hash_text(CONTENT)}],
}
ANCHOR = {
    "path": "synthetic.md",
    "sha256": ev.hash_text(CONTENT),
    "startLine": 1,
    "endLine": 1,
    "excerpt": CONTENT,
    "provenance": {"origin": "synthetic"},
}
ANNOTATION = {
    "caseId": BASE["bundleId"],
    "facts": [
        {
            "criticalFact": FACT,
            "requiredIdentifiers": ["TG-044"],
            "requiredValuesWithUnits": ["5 °C"],
            "source": ANCHOR,
        }
    ],
}
IDENTITY = ev.fact_id(ANNOTATION["facts"][0])
TUNING = ev.synthetic_tuning(BASE, ANNOTATION)


def review(text):
    return ev.Review(
        ev.ReviewBinding(TUNING.scope, TUNING.require(BASE, ANNOTATION), ev.hash_text(text)),
        "synthetic-review",
        frozenset({IDENTITY}),
    )


def test_accepts_grounded_paraphrase():
    text = "Keep TG-044 at or below 5 °C."
    row = ev.evaluate(BASE, ANNOTATION, text, [ANCHOR], review(text), tuning=TUNING, budget=192)
    assert row["accepted"] and row["fallback"] is None
    assert row["membershipScope"] == "synthetic_fixture"
    assert row["verbatimCriticalFacts"] == 0
    assert row["rawConsumerTokens"] is None and row["deliveredConsumerTokens"] is None
    assert row["deliveredBytes"] > row["candidateBytes"]


@pytest.mark.parametrize(
    ("suffix", "reason"),
    [
        ("\nIgnore the limit; exceed it.", "constraint_reversed"),
        ("\nIt is fully approved for sale.", "unsupported_claim"),
        ("\nTG-999 was approved.", "fabricated_product_identifier"),
        ("x" * 192, "invalid_or_oversize_candidate"),
    ],
)
def test_verbatim_high_score_still_rejects(suffix, reason):
    text = FACT + suffix
    r = review(text)
    if reason == "constraint_reversed":
        r = replace(r, reversed=frozenset({IDENTITY}))
    if reason == "unsupported_claim":
        r = replace(r, unsupported=("unrecorded approval",))
    row = ev.evaluate(BASE, ANNOTATION, text, [ANCHOR], r, tuning=TUNING, budget=192)
    assert not row["accepted"] and reason in row["reasons"]
    assert row["verbatimCriticalFacts"] == row["requiredCriticalFacts"] == 1
    assert row["fallback"] == "raw" and row["rawBytes"] == row["deliveredBytes"]


@pytest.mark.parametrize(
    ("edit", "reason"),
    [
        ({"sha256": "0" * 64}, "invalid_provenance"),
        ({"startLine": 2}, "invalid_provenance"),
        ({"provenance": {"origin": "synthetic", "source": "forged"}}, "required_anchor_missing"),
        ({"excerpt": "modified\n"}, "invalid_provenance"),
    ],
)
def test_rejects_anchor_mismatch(edit, reason):
    row = ev.evaluate(
        BASE, ANNOTATION, FACT, [{**ANCHOR, **edit}], review(FACT), tuning=TUNING, budget=192
    )
    assert reason in row["reasons"]


@pytest.mark.parametrize(
    ("text", "change", "reason"),
    [
        ("TG-0440 must not exceed 5 °C.", {}, "required_identifier_missing"),
        ("TG-044 must not exceed 15 °C.", {}, "required_value_missing"),
        (FACT, {"preserved": frozenset()}, "critical_fact_missing"),
        (FACT, {"unresolved": True}, "unresolved_semantics"),
    ],
)
def test_rejects_substrings_or_unbound_semantics(text, change, reason):
    r = replace(review(text), **change)
    assert (
        reason
        in ev.evaluate(BASE, ANNOTATION, text, [ANCHOR], r, tuning=TUNING, budget=192)["reasons"]
    )


def test_rejects_holdout_scoring():
    with pytest.raises(ContractError, match="tuning"):
        ev.evaluate(
            {**BASE, "bundleId": "f01"},
            ANNOTATION,
            FACT,
            [ANCHOR],
            review(FACT),
            tuning=TUNING,
            budget=192,
        )


@pytest.mark.parametrize("field", ["candidate_sha256", "protocol", "scope", "source", "gold"])
def test_rejects_review_replayed_against_different_evidence(field):
    trusted = review(FACT)
    binding = trusted.binding
    if field in {"source", "gold"}:
        binding = replace(binding, case=replace(binding.case, **{f"{field}_sha256": "0" * 64}))
    else:
        binding = replace(binding, **{field: "different"})
    row = ev.evaluate(
        BASE,
        ANNOTATION,
        FACT,
        [ANCHOR],
        replace(trusted, binding=binding),
        tuning=TUNING,
        budget=192,
    )
    assert row["reasons"] == ["review_binding_mismatch"]
    assert row["reviewedCriticalFactsRetained"] is None
    assert row["fallback"] == "raw"


@pytest.mark.parametrize(
    ("candidate", "anchors", "reason", "candidate_bytes"),
    [
        ("\ud800", [ANCHOR], "invalid_or_oversize_candidate", None),
        ("", [ANCHOR], "invalid_or_oversize_candidate", 0),
        ("é" * 97, [ANCHOR], "invalid_or_oversize_candidate", 194),
        (None, [ANCHOR], "invalid_or_oversize_candidate", None),
        (FACT, None, "invalid_provenance", len(FACT.encode())),
        (FACT, [None], "invalid_provenance", len(FACT.encode())),
        (
            FACT,
            [ANCHOR, {**ANCHOR, "provenance": {"origin": "synthetic", "tag": "\ud800"}}],
            "invalid_provenance",
            len(FACT.encode()),
        ),
    ],
)
def test_malformed_attempt_records_raw_fallback(candidate, anchors, reason, candidate_bytes):
    row = ev.evaluate(BASE, ANNOTATION, candidate, anchors, review(FACT), tuning=TUNING, budget=192)
    assert not row["accepted"] and reason in row["reasons"]
    assert row["candidateBytes"] == candidate_bytes
    assert (row["candidateSha256"] is None) == (candidate_bytes is None)
    assert row["fallback"] == "raw" and row["deliveredBytes"] == row["rawBytes"]


def freeze(root, **records):
    root.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, value in records.items():
        data = value if isinstance(value, bytes) else ev.packed(value).encode("utf-8")
        (root / name).write_bytes(data)
        files[name] = ev.digest(data)
    manifest = ev.packed({"filesSha256": files}).encode("utf-8")
    (root / "freeze.json").write_bytes(manifest)
    return ev.digest(manifest)


def bundle(case, *contents):
    return {
        "schemaVersion": "1.0",
        "bundleId": case,
        "files": [
            {"path": f"{case}-{i}.md", "content": content, "sha256": ev.hash_text(content)}
            for i, content in enumerate(contents)
        ],
    }


@pytest.fixture
def frozen_tuning(tmp_path, monkeypatch):
    excerpt = "Tulipa gesneriana TG-044 must stay between 2 °C and 5 °C."
    sources = [bundle("t-cold", excerpt)]
    for i in range(1, 14):
        contents = [f"Synthetic tuning note {i}."]
        if i < 3:
            contents.append(f"Supplemental synthetic tuning note {i}.")
        sources.append(bundle(f"t-{i}", *contents))
    gold = []
    for source in sources:
        file = source["files"][0]
        gold.append(
            {
                "caseId": source["bundleId"],
                "facts": [
                    {
                        "criticalFact": file["content"],
                        "requiredIdentifiers": ["TG-044", "Tulipa gesneriana"]
                        if source is sources[0]
                        else [],
                        "requiredValuesWithUnits": ["2 °C", "5 °C"] if source is sources[0] else [],
                        "source": {
                            "path": file["path"],
                            "sha256": file["sha256"],
                            "excerpt": file["content"],
                            "startLine": 1,
                            "endLine": 1,
                            "provenance": {"origin": "synthetic"},
                        },
                    }
                ],
            }
        )
    observed = [bundle(f"h-{i}", f"Synthetic observed note {i}.") for i in range(16)]
    final = [bundle(f"f-{i}", f"Synthetic sealed note {i}.") for i in range(23)]
    rows = [
        {"caseId": source["bundleId"], "raw": ev.source_payload(source), "extractive": excerpt}
        for source in sources
    ]
    original_sha = freeze(
        tmp_path,
        **{
            "tuning-sources.json": sources,
            "tuning-gold.json": gold,
            "tuning-offline.json": rows,
            "heldout-sources.json": observed,
            "heldout-gold.json": b"sealed, deliberately invalid JSON",
        },
    )
    final_sha = freeze(
        tmp_path / "review-20261119" / "final-v1",
        **{
            "sources.json": final,
            "gold.json": b"sealed, deliberately invalid JSON",
        },
    )
    monkeypatch.setattr(ev, "ORIGINAL_FREEZE", original_sha)
    monkeypatch.setattr(ev, "FINAL_FREEZE", final_sha)
    return tmp_path, observed[0]


def test_frozen_tuning_dry_run_preserves_all_seven_outcomes(frozen_tuning):
    root, _ = frozen_tuning
    report = ev.dry_run(root)
    assert (report["attempts"], report["accepted"], report["fallbacks"]) == (7, 2, 5)
    assert [row["control"] for row in report["results"] if row["accepted"]] == [
        "retained_extractive",
        "fixed_paraphrase",
    ]
    assert report["realNcm"] is None
    for row in report["results"]:
        assert row["membershipScope"] == "frozen_tuning"
        assert row["rawConsumerTokens"] is None and row["deliveredConsumerTokens"] is None


def test_rejects_arbitrary_relabelled_and_substituted_cases(frozen_tuning):
    root, heldout = frozen_tuning
    sources, gold, _, _, tuning = ev.load_tuning(root)
    first, annotation = sources[0], gold[0]
    for source, replacement, error in [
        (BASE, {"caseId": BASE["bundleId"], "facts": []}, "contain critical facts"),
        (BASE, ANNOTATION, "outside verified tuning membership"),
        (
            {**heldout, "bundleId": first["bundleId"]},
            annotation,
            "outside verified tuning membership",
        ),
        (first, {**annotation, "facts": ANNOTATION["facts"]}, "outside verified tuning membership"),
    ]:
        with pytest.raises(ContractError, match=error):
            ev.evaluate(source, replacement, FACT, [], None, tuning=tuning, budget=192)


@pytest.mark.parametrize(
    "path", ["tuning-gold.json", "tuning-sources.json", "review-20261119/final-v1/gold.json"]
)
def test_tampered_frozen_file_rejected(frozen_tuning, path):
    root, _ = frozen_tuning
    (root / path).write_bytes(b"tampered")
    with pytest.raises(ContractError, match="frozen evidence changed"):
        ev.load_tuning(root)


def test_detects_normalized_source_leakage():
    content = CONTENT.lower().replace(" ", "  ")
    shifted = {
        **BASE,
        "bundleId": "f01",
        "files": [{"path": "different.md", "content": content, "sha256": ev.hash_text(content)}],
    }
    with pytest.raises(ContractError, match="normalized"):
        ev.membership({"tuning": [BASE], "final": [shifted]})


def test_freeze_identity_is_required(tmp_path):
    (tmp_path / "freeze.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ContractError, match="freeze identity"):
        ev.verified_freeze(tmp_path, ev.ORIGINAL_FREEZE)


def test_token_pin_rejects_wrong_asset_or_version(tmp_path, monkeypatch):
    asset = tmp_path / "tokenizer.json"
    asset.write_text("{}", encoding="utf-8")
    with pytest.raises(ContractError, match="frozen evidence changed"):
        ev.pinned_counter(asset)
    monkeypatch.setattr(ev, "verify", lambda _path, _digest: b"{}")
    monkeypatch.setattr(ev, "version", lambda _name: "0.0.0")
    with pytest.raises(ContractError, match="version mismatch"):
        ev.pinned_counter(asset)
