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


def review(text):
    return ev.Review(
        BASE["bundleId"], ev.hash_text(text), "synthetic-review", frozenset({IDENTITY})
    )


def test_accepts_grounded_paraphrase():
    text = "Keep TG-044 at or below 5 °C."
    row = ev.evaluate(BASE, ANNOTATION, text, [ANCHOR], review(text), budget=192)
    assert row["accepted"] and row["fallback"] is None
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
    row = ev.evaluate(BASE, ANNOTATION, text, [ANCHOR], r, budget=192)
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
    row = ev.evaluate(BASE, ANNOTATION, FACT, [{**ANCHOR, **edit}], review(FACT), budget=192)
    assert reason in row["reasons"]


@pytest.mark.parametrize(
    ("text", "change", "reason"),
    [
        ("TG-0440 must not exceed 5 °C.", {}, "required_identifier_missing"),
        ("TG-044 must not exceed 15 °C.", {}, "required_value_missing"),
        (FACT, {"preserved": frozenset()}, "critical_fact_missing"),
        (FACT, {"unresolved": True}, "unresolved_semantics"),
        (FACT, {"candidate_sha256": "0" * 64}, "review_binding_mismatch"),
    ],
)
def test_rejects_substrings_or_unbound_semantics(text, change, reason):
    r = replace(review(text), **change)
    assert reason in ev.evaluate(BASE, ANNOTATION, text, [ANCHOR], r, budget=192)["reasons"]


def test_rejects_holdout_scoring():
    with pytest.raises(ContractError, match="tuning"):
        ev.evaluate(
            {**BASE, "bundleId": "f01"}, ANNOTATION, FACT, [ANCHOR], review(FACT), budget=192
        )


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
