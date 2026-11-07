# CTX-LABS-01: historical coding pilot

Three real defects at #13 c6021d456bbcce20fec817470aa5237907d7728a; three conditions each: ordinary exploration, agent-authored manual brief, CTX-assembled packet. Selection is manual in both prepared arms; no discovery benefit is claimed.

## Frozen protocol

Codex CLI 0.164.0, gpt-6.1-sol, medium reasoning, ChatGPT authentication, fresh sessions, sequential runs, 600-second subject limit. Do not substitute models, resume sessions, launch MCP/web/local models or expose repair/evaluator material. No paid subject runs in CI. Cash cost is unknown without attributable billing; missing usage is null, never zero.

Orders: physical lines ordinary/manual/CTX; hidden changes manual/CTX/ordinary; stdout CTX/ordinary/manual. Each gets identical task text, visible pre-fix tree and test access. Manual brief is agent-authored, not human preparation. Spec, prompt and input digests freeze before runs. No fix or held-out test enters prepared context.

```powershell
uv run --frozen --group dev python scripts/context/labs/pilot.py prepare --artifacts <new-external-pilot>
uv run --frozen --group dev python scripts/context/labs/pilot.py run --artifacts <pilot>
uv run --frozen --group dev python scripts/context/labs/pilot.py evaluate --artifacts <pilot>
uv run --frozen --group dev python scripts/context/labs/pilot.py summarize --artifacts <pilot>
```

Without qualified infrastructure all nine run records are BLOCKED, with zero model calls. Existing/partial run directories are never reused. Running records without a terminal result are incomplete; evaluate/summarize reject them. CLI rejection exits 2; inspect summary scored_runs, not process exit alone.

Source-only subjects are Git archives of #13 with fresh commits, no remote and no descendant object database. Preparers alone may access ancestor objects. The old LAB-01 fixture requires original Git history and cannot replay inside a source-only subject; this limitation is common to all arms. External evaluation restores ancestor history privately. Root source tree identity and local subject commit identity are distinct and recorded.

## Trusted infrastructure boundary

**Offline hardening only; runner qualification is not implemented.** The legacy
launcher self-attestation path is disabled. Supplying --launcher never executes
that file; it records BLOCKED before model calls. Neither matching JSON nor an
offline-valid terminal fixture is qualification or permission to score.

New preparation captures per-subject identity files and their digests in the
existing manifest. Tasks, arms, model and ordering are unchanged. Old blocked
attempts remain immutable; missing identity seals require a fresh preparation.
Identity validation checks historical tree, exact local commit, raw source
inventory, index/refs/config and all frozen prompt/context inputs. It rejects
ignored extra files, flags, alternate object stores and injected Git metadata.
The offline setup helper checks identity before and after a probe. This is
point-in-time validation, not an atomic snapshot or OS containment claim.

The strict terminal parser binds a stream to controller-owned run ID, nonce,
request digest, subject commit/tree and execution handle; it does not invent
per-event IDs absent from the CLI. Its conservative grammar uses the retained
[official non-interactive examples](https://learn.chatgpt.com/docs/non-interactive-mode)
(thread.started, turn.started, item lifecycle, turn.completed with usage).
Installed CLI package 0.164.0 was inspected without invoking authentication or a
model. Tests are synthetic. Actual runtime schema compatibility, independent
qualification, credential/network safety and teardown remain unverified until
a separately authorized smoke. Unknown/malformed events reject rather than
being dropped. Failed or unqualified execution records cannot become scores.

A future runner/controller must implement an independently trusted verifier and
reuse these validators at the real dispatch/collection boundary. No VM adapter,
provider binding or credential mechanism is delivered by this offline slice.

## Independent evaluation and retained data

Before scoring, retain held-out failures on #13 and passes on #17. After a subject exits, the trusted external evaluator receives neutral run ID, fresh candidate directory and execution metadata on stdin. It owns hidden tests outside the subject, runs negative/positive/read-only controls and returns JSON with boolean correctness; optional citation_validity, critical_source_coverage and unsupported_claims must be independently assessed or null. Missing verdicts reject. Only builder-file changes are in scope; test changes/untracked payloads reject.

Correctness uses the 28 original positive/contract cases plus the assigned defect's hidden regressions. The full 57-case cross-defect suite also runs, but unrelated pre-existing defects are retained separately rather than automatically failing a focused repair. Task identity is derived from neutral run ID; the evaluator is not given the context arm. Citation/semantic metrics remain null until independently assessed, never inferred from test success.

Retain events/stderr, final responses, patch/digests, command configuration, terminal state, tests, verdicts, timing and actual usage. Outcomes include blocked, timeout, failed, invalid_scope, invalid_patch and evaluated. A completed model call does not imply correctness. If inputs/patches drift, stop; do not silently drop failed cells. Report all nine conditions, preparation effort, cached/input/output usage and independent evaluation overhead separately. One run per cell supports an exploratory comparison only; no statistical superiority claim.

See [results](../../reports/context-labs-01-results.md). Keep #17 independently reviewable. Snapshot/discovery/approval/MCP stages remain future work.
