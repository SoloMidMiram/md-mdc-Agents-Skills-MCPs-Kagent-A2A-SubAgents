# CTX-LABS-01 development results — 2026-11-06

Non-authoritative observations, stacked on draft #17 source `fe3aea3f0aba9ea2cd040194dd898c91391b3240`. This slice does not change CTX-01R, its schema, original evidence or acceptance status. See the [lab protocol](../docs/runbooks/ctx-labs-01-pilot.md) for reproduction and infrastructure requirements.

## Verified practical results

| Experiment | Observation |
|---|---|
| Pinned LAB-01 generation | Two byte-identical packets; all six full-blob hashes and physical-line excerpts independently resolve |
| Packet compatibility | SHA-256 `902f82d137d398a94b36c4a8c3d8963b2bf9d5834a82402077701338dbd3ef45`, same as CTX-01R retained result |
| Synthetic corruption | 21/21 negative controls passed: seven categories × stdout/absent-file/sentinel-file modes |
| Source-only preparation | Nine subjects prepared; historical tree identity checked, fresh local history and no remote/descendant repair objects |
| Scored coding runs | **0 executed; all nine BLOCKED** before model calls |

Final Windows context suite: **69 passed** (57 unchanged CTX-01R cases plus 12 harness controls), exit 0. Context lint/format and diff whitespace checks passed. Reference-only external evaluation on the exact historical tree produced **19 failures / 38 passes** before repair, covering all three defect categories and the original 14 cases; the repaired builder passed **57/57**. These reference checks are not subject runs. Environment: CPython 3.13.15, pytest 9.1.1, Ruff 0.15.22, Git 2.56.0.windows.4.

The ownership validator exits 1 solely for the identical 65 inherited link findings: 162 manifest entries, no missing targets, duplicates or unmapped changes. Available CI remains responsible for hosted deterministic qualification; no hosted result is assumed here.

Source revision: `a53bfb62f0421a7c28234f871af2bf449a11491f` for LAB-01, `c6021d456bbcce20fec817470aa5237907d7728a` for historical coding subjects. Fresh subject commit IDs are preparation identities, not upstream SHAs. Manually selected briefs are agent-authored; they are not human-authored or automatically discovered.

## Nine-run ledger

| Neutral ID | Challenge | Context | State | Correctness / usage / cash cost |
|---|---|---|---|---|
| r01 | Physical lines | Ordinary | BLOCKED | Unknown |
| r02 | Physical lines | Manual brief | BLOCKED | Unknown |
| r03 | Physical lines | CTX packet | BLOCKED | Unknown |
| r04 | Hidden changes | Manual brief | BLOCKED | Unknown |
| r05 | Hidden changes | CTX packet | BLOCKED | Unknown |
| r06 | Hidden changes | Ordinary | BLOCKED | Unknown |
| r07 | UTF-8 stdout | CTX packet | BLOCKED | Unknown |
| r08 | UTF-8 stdout | Ordinary | BLOCKED | Unknown |
| r09 | UTF-8 stdout | Manual brief | BLOCKED | Unknown |

The ordinary host can read repair/evaluator artifacts, and Docker daemon access is denied. No independently provisioned read-isolating launcher is installed. The harness therefore records blocked states rather than launching subjects with prompt-only secrecy. No actual patches, response accuracy, model token usage, elapsed model effort or billed charges exist for these nine cells. There is no evidence of coding improvement or resource reduction.

The launcher interface is trusted infrastructure, not a sandbox implementation: its probe must genuinely verify host-read denial and the same restrictions used for model execution. No production-security claim is made for an unqualified adapter. Reference qualification and deterministic harness tests remain separate from subject scores.

## Artifact layout and failure retention

Raw generated artifacts remain outside the repository in the task's `ctx-labs-evidence` directory: replay packets/checks, synthetic inputs/results, manifests/prompts/briefs, nine blocked/evaluated records, command ledger, test XML/logs and reference qualifications. A digest inventory accompanies the local handoff. The small report is sanitized; raw logs with workstation paths are not published.

Preparation failures were retained. Windows Git archive conversion initially caused CRLF/source mismatch; preparation now exports with core.autocrlf=false. A subsequent exact-tree check exposed tracked files matching .gitignore; preparation force-adds exported files and verifies the historical tree hash. Deeper Windows test paths exposed Git's path-length limit; only disposable repositories receive core.longpaths=true. No global Git setting or builder validation was changed. Earlier preparations are superseded, not scored or silently deleted.

The pre-existing 65 broken-link findings remain separate debt. Snapshot support, discovery, approval receipts, MCP delivery and model/backend policy changes are outside this slice. Independent review, qualified pilot execution and parent integration acceptance remain outstanding.
