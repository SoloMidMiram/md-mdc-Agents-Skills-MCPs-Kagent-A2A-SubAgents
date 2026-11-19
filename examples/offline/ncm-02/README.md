# NCM-02 offline evaluator controls

This read-only tuning dry run takes the private, frozen corpus directory as an
explicit argument. The corpus is not part of the repository. Use Python
3.12 or newer.

```powershell
python -m scripts.kagent.experiments.ncm02_evaluator <local-frozen-ncm02-corpus>
python -m pytest -q tests/kagent/experiments/test_ncm02_evaluator.py
```

The command verifies both freeze identities and all referenced SHA-256
digests, including independent annotations and the retained raw/extractive
baseline files. It checks the tuning, observed holdout and final source
memberships for shared case IDs, normalized paths and exact or normalized
source-content digests. This is a bounded structural leakage check. The
held-out gold files are hashed for integrity. Only tuning gold is parsed.

The tuning dry run uses the existing cold-shelf case, one retained 192-byte
extractive output and six authored positive/negative controls at the same cap.
The uncompressed source is checked against the retained raw baseline and kept
intact as the reference and fallback. Exact excerpts and the presence of IDs
are diagnostics. Evidence-bound semantic annotations determine missing critical
facts, reversals and unsupported assertions. E3 checks the actual cited lines.
A fabricated ID, missing condition, stale anchor or unresolved review rejects.
Rejected controls fall back to the verified raw input and remain in the
coverage denominator. Report candidate and delivered bytes separately, since
the delivered candidate includes its citation envelope.

Expected dry-run results are two accepted and five rejected controls, with
five raw fallbacks. These are calibration controls, so their coverage is
not benchmark coverage. The protocol's 512-byte primary arm and 192, 1024
and 2048-byte comparisons stay frozen. No final holdout is scored.

## Consumer-token identity

The pinned tokenizer is GPT-2 revision
`607a30d783dfa663caf39e06633721c8d4cfcd7e`, with local `tokenizer.json`
SHA-256 `8414cab924d8b9b33013f0d221c5862f365ee9be39c5c2bfae8a5a9e970478a6`.
Use an already authorized local `tokenizers==0.22.1` and
`--tokenizer-json <pinned-local-asset>` to count the delivered envelope
and raw input without adding special tokens. The command verifies both the
asset and version, and leaves token counts null when the option is omitted.
The pin is a benchmark convention and does not establish the tokenizer used
by a future consumer or model. No dependency is added to repository locks.

Independent semantic review for the full tuning sweep and separate
authorization for real inference remain outstanding. Genuine NCM output,
runtime measurements, and benchmark disposition stay null.
