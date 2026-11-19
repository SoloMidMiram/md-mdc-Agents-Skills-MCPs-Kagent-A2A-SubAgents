# EDU-02 offline documentation-review lab

Run from the repository root with Python 3.12 or newer.

```powershell
python -m scripts.kagent.experiments.edu02_lab
python -m scripts.kagent.experiments.edu02_lab --case broken
python -m scripts.kagent.experiments.edu02_lab --case fixed
```

The default replay cites the misspelled `runbook.md#instal` on physical line 3 of
`guide.md`, then selects the pre-authored correction `runbook.md#install`.
Expect four subtasks, one revision and final approval. The broken-only control
revises once and rejects, and the fixed-only case approves after two subtasks.
An expected rejection is a successful demonstration and exits zero. Invalid
fixtures or unexpected outcomes exit one with a diagnostic on stderr.
The command writes only to stdout/stderr and uses no network or model.

The checker uses only verified in-memory bundle files. It accepts simple ASCII
ATX headings and inline links with plain ASCII labels and lowercase hyphenated
fragments. An omitted path refers to the containing document. POSIX-relative
`.md` targets are resolved from the containing directory, with lexical `.` and
`..` normalization inside the bundle. Paths are case-sensitive. Simple fenced
blocks are skipped. Images, reference links, rich headings, encoded targets,
escaping paths, indented Markdown and detected unsupported syntax are unresolved. Links to a
duplicate normalized heading are ambiguous. Unicode prose and CRLF citations
retain their exact bytes. The checker covers this documented fixture dialect.

Compare parsed JSON across platforms, including fixture SHA-256 values, packet
digest, exact excerpts, finding IDs, correlated subtask identities and verdicts.
A finding ID hashes the validated citation and normalized target. Identical
references to the same target on one physical line share an ID. A change to
the citation or target changes the ID. The report is synthetic and records
`capabilityPromotion: false`.

## Learner extension

In a disposable checkout, change `## Install` to `## Setup` in the fixed
`runbook.md`. A one-file edit first fails the byte/digest check. Update the
`runbook.md` entry in that case's `bundle.json` with the exact LF text and
its SHA-256, then rerun the fixed case. The broken target now prevents expected
approval. Update the fixed `guide.md` link to `runbook.md#setup` and refresh
that file's manifest entry the same way. The fixed replay approves again.
Use the digest command from the repository root for each changed file.

```powershell
Get-FileHash scripts/kagent/experiments/fixtures/edu02/fixed/runbook.md -Algorithm SHA256
python -m pytest -q tests/kagent/experiments/test_edu02_lab.py tests/kagent/experiments/test_docs_bundle.py tests/kagent/experiments/test_e2r_orchestration.py
```

## First-slice publication verification (2026-11-16)

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
