# EDU-02 offline documentation-review lab

From the repository root, with Python 3.12 or newer:

```powershell
python -m scripts.kagent.experiments.edu02_lab
```

No dependency installation, credentials, network access, workers, or model calls
are needed. The command prints JSON to stdout and exits zero when the expected
demonstration succeeds. Invalid inputs or unexpected outcomes exit one with a
diagnostic on stderr. It writes no report files.

The broken guide refers to `#instal`; its heading is `Install`. The report cites
physical line 3 and its exact excerpt. The deterministic planner selects the
broken fixture, the reviewer runs the checker and rejects it, the revised planner
selects the pre-authored fixed fixture, and the reviewer checks and approves it.
Expect four subtasks, one revision, and a final approve verdict. This demonstrates
selection of a supplied correction, not autonomous editing.

Both fixtures have checked-in SHA-256 manifests. Loading preserves UTF-8 bytes,
then uses `docs_bundle.validate_bundle()`; citations use
`docs_bundle.validate_findings()`. Fixture attributes pin LF in Windows checkouts.
To intentionally edit a fixture, update its recorded digest separately and review
both changes. The runner never repairs a mismatched digest.

The checker supports plain ASCII ATX headings with single spaces and inline
same-document links with simple ASCII labels and lowercase hyphenated anchors.
Heading anchors lowercase text and replace spaces with hyphens. Fenced code is
ignored. Duplicate headings, rich heading syntax, cross-file and reference links,
and other detected unsupported syntax are unresolved questions, not successful
checks. This is a fixture-oriented subset, not a general Markdown parser or a
claim-truth validator.

The report includes bundle digests, validated results, ordered stages, and the
coordinator decision and artifacts. Stable IDs and sorted JSON keys make repeated
runs byte-identical on the same platform. No time or machine paths enter it.
`origin: synthetic` and `capabilityPromotion: false` apply to the entire report.
The coordinator and live A2A capabilities are unchanged.

Validation:

```powershell
uv run pytest -q tests/kagent/experiments/test_edu02_lab.py tests/kagent/experiments/test_docs_bundle.py tests/kagent/experiments/test_e2r_orchestration.py
uv run ruff check scripts/kagent/experiments/edu02_lab.py tests/kagent/experiments/test_edu02_lab.py
```


## Publication verification (2026-11-16)

Base: 78bb511e3dd4ab44614ecde9905d4d1631d680d4. Windows Python 3.14.3
and WSL Linux Python 3.14.4 produced identical parsed JSON. Stdout newlines
may differ by platform; compare parsed JSON including digests and excerpts.

The non-SDK experiment suite passes 136 tests. Existing coordinator tests reject
malformed reviewer artifacts, duplicate task IDs, deadline exhaustion and a second
revise. Bundle tests cover invalid digests, paths and excerpts; lab tests cover
fixture tampering and a still-broken correction.

Mypy with identical --no-incremental --follow-imports=skip options on the
base-extracted and candidate coordinator reports identical diagnostics: line 77
(no-any-return due to skipped imports) and line 88 (arg-type). The ordinary
candidate check reports line 88. The coordinator is unchanged.

This first slice leaves issue #36 gaps: relative cross-file links, stable finding
IDs, learner extension instructions, full hosted validation and independent
acceptance. Keep #36 open. No L6, I3, I4, runner qualification or measured
coding-quality claim is made.

Canonical owners: evidence index and both roadmaps remain unchanged because no
capability or accepted milestone changes. PR #38 stays independent. Manifest,
runbook and experiment README are updated; historical evidence is unchanged.
