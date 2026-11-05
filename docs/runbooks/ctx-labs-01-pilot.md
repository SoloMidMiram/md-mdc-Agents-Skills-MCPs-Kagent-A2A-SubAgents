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

This repository does not implement a secure OS sandbox. A separately provisioned trusted Python launcher may be supplied with --launcher. Do not author it inside subject/artifact directories. It accepts one JSON request on stdin. Probe mode must actually run deny-read tests for every forbidden host location, verify dependencies, CLI version, no remotes/MCP/web and fresh-session policy under the SAME sandbox configuration used for execution. Return JSON with denied, cli and requirements exactly matching verified values. These fields are trusted infrastructure attestations, not model-generated approval receipts. A forged launcher can lie: review/deploy it independently; successful JSON parsing alone is not security proof.

Run mode receives subject, prompt, argv and timeout_seconds. Stream only Codex JSONL to stdout, diagnostics to stderr; return the subject exit. Mount only the subject and approved input; preserve account authentication without mounting parent chats/configuration/evaluators. Enforce provider-only model networking, denied host reads, preinstalled dependencies and process-tree termination at 600 seconds. The harness gives the launcher ten seconds to shut down; an unqualified launcher cannot provide this guarantee. No unrestricted host fallback is available.

## Independent evaluation and retained data

Before scoring, retain held-out failures on #13 and passes on #17. After a subject exits, the trusted external evaluator receives neutral run ID, fresh candidate directory and execution metadata on stdin. It owns hidden tests outside the subject, runs negative/positive/read-only controls and returns JSON with boolean correctness; optional citation_validity, critical_source_coverage and unsupported_claims must be independently assessed or null. Missing verdicts reject. Only builder-file changes are in scope; test changes/untracked payloads reject.

Correctness uses the 28 original positive/contract cases plus the assigned defect's hidden regressions. The full 57-case cross-defect suite also runs, but unrelated pre-existing defects are retained separately rather than automatically failing a focused repair. Task identity is derived from neutral run ID; the evaluator is not given the context arm. Citation/semantic metrics remain null until independently assessed, never inferred from test success.

Retain events/stderr, final responses, patch/digests, command configuration, terminal state, tests, verdicts, timing and actual usage. Outcomes include blocked, timeout, failed, invalid_scope, invalid_patch and evaluated. A completed model call does not imply correctness. If inputs/patches drift, stop; do not silently drop failed cells. Report all nine conditions, preparation effort, cached/input/output usage and independent evaluation overhead separately. One run per cell supports an exploratory comparison only; no statistical superiority claim.

See [results](../../reports/context-labs-01-results.md). Keep #17 independently reviewable. Snapshot/discovery/approval/MCP stages remain future work.
