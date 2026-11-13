# Laptop-Stable Acceptance Plan

> **Derived from:** Static QA review of commit `cdaa760`
> **Tag history:**
> - `laptop-stable-v0.1` @ `cdb7dc0` — initial release (2026-07-09)
> - **`laptop-stable-v0.1.1`** — pending (this stabilization SHA after CI)
> **Status:** `RELEASE_SHA_NOT_SELECTED` — historical hosted Quality runs are
> useful context, but the patch still requires an exact green `quality.yml` run
> and target-host round-trip evidence for the selected release SHA.

---

## Goal

Move from production-path-tested coverage to **laptop-stable v0.1**: the installer can be run on a new Windows machine, register `playwright-global` across all 4 config targets, and roll back cleanly — with CI affirmatively proving it.  
This document now tracks the **v0.1.1 patch** (UTF-8 onboarding, narrative sync, bridge manifests).

---

## Current Status

| Domain | Status | Evidence |
|--------|--------|----------|
| Shared config manifest | ✅ Done | `McpConfigTargets.ps1` — 4 targets, typed states |
| Typed state detection | ✅ Done | `FILE_MISSING`, `FILE_MALFORMED`, `ENTRY_MISSING`, `ENTRY_CORRECT`, `ENTRY_STALE`, `DEPENDENCY_MISSING` |
| JSON install path | ✅ Tested | Production-path tests: create, stale update, absent container |
| TOML install path | ✅ Tested | Production-path tests: create, stale update with section preservation |
| YAML install path | ✅ Tested | Production-path tests: create, stale update, trailing sections preserved |
| Malformed file detection | ✅ Tested | JSON, TOML, YAML — all exit 1 before mutation |
| Rollback round-trip | ✅ Tested | Real scripts: install → verify → rollback, SHA-256 verified |
| Verify exit codes | ✅ Tested | Exits 0 on correct, 1 on missing |
| WhatIf non-mutating | ✅ Tested | No backup directory created |
| CI workflow | ✅ Configured | PSScriptAnalyzer, JSON validation, Pester evaluation, artifact upload |
| PyYAML dependency contract | ✅ **Implemented** | `pyyaml==6.0.3` is a direct pinned development dependency; workflow YAML validation uses `uv sync --frozen --group dev` / `uv run`. The Windows evaluation job still installs `pyyaml==6.0.3` via pip for Pester/config YAML paths that do not use the uv environment. |
| Documented test counts | ✅ **Updated** | README says "73+ tests" — Pester-verified aggregate, not hardcoded per-file |
| Dataset structural tests | ✅ **Done** | ConfigRoot isolation + child `pwsh` installer; Package scope in Describe; hosted Quality green |
| Old plan doc | ✅ Archived | `docs/laptop-stable-implementation-plan.md` → replaced by this file |
| Corrupted review verdict | ✅ Archived | Moved to `docs/archive/` |
| Terminology normalized | ✅ Done | "4 config targets / 5 runtime surfaces" used consistently |
| Remote Docker runtime | ❌ Deferred | Requires Linux server; non-blocking for laptop-stable |
| SSH/kagent/A2A | ❌ Deferred | Lab active; outside laptop-stable v0.1 gate |

---

## Acceptance Gates

### Gate A — CI affirmatively passes

| # | Check | How Verified |
|---|-------|-------------|
| A1 | ✅ **Done** | CI step validates `config/templates/*.json` |
| A2 | ✅ **Done** | CI step `Invoke-ScriptAnalyzer -Severity Error` |
| A3 | ✅ **Done** | CI step `run-evaluation.ps1 -CI` — exit 0 on clean runner; hosted Quality SUCCESS @ `46a1d7d` (ConfigRoot + Package Describe scope) |
| A4 | ✅ **Contract declared** | `pyyaml==6.0.3` is declared in the `dev` group; `uv.lock` pins it; the kagent-python job validates workflow YAML through the frozen uv environment. Hosted green Quality on the eventual release SHA remains Gate A overall. |
| A5 | ✅ **Done** | CI step `actions/upload-artifact` |
| A6 | ✅ **Done** | Workflow runs on `push` and `pull_request` |

**Laptop-stable requires:** A passing CI run on the release commit.

### Gate B — Production installer correctness

| # | Check | How Verified |
|---|-------|-------------|
| B1 | JSON create: empty container | `production-path.Tests.ps1` • `Creates entry from scratch in JSON target` |
| B2 | JSON create: absent container key | `production-path.Tests.ps1` • `Creates entry when server container key is absent (JSON)` |
| B3 | JSON create: other servers preserved | `production-path.Tests.ps1` • `Creates entry when server key exists but playwright-global is absent (JSON)` |
| B4 | JSON stale update | `production-path.Tests.ps1` • `Corrects stale command in JSON entry` |
| B5 | TOML create | Covered by `Exits 0 when all entries correct` (fixture deploy + verify) |
| B6 | TOML stale update, other sections preserved | `production-path.Tests.ps1` • `Replaces stale TOML section, preserves other sections` |
| B7 | YAML create, trailing sections preserved | `production-path.Tests.ps1` • `Creates entry in YAML with trailing sections preserved` |
| B8 | YAML stale update, other entries preserved | `production-path.Tests.ps1` • `Replaces stale YAML entry, preserves other entries` |
| B9 | YAML: playwright-global is last entry | `production-path.Tests.ps1` |
| B10 | YAML: comments before/after mcpServers | `production-path.Tests.ps1` |
| B11 | YAML: unrecognized trailing sections preserved | `production-path.Tests.ps1` |
| B12 | TOML: stale section in middle, multiple following | Covered by B6 |
| B13 | Second run idempotent (no backup) | `production-path.Tests.ps1` • `Second run with correct entries reports no changes` |

### Gate C — Safety and error handling

| # | Check | How Verified |
|---|-------|-------------|
| C1 | Malformed JSON → exit 1, no mutation | `production-path.Tests.ps1` • malformed JSON tests |
| C2 | Malformed TOML → exit 1, no mutation | `production-path.Tests.ps1` • malformed TOML tests |
| C3 | Malformed YAML → exit 1, no mutation | `production-path.Tests.ps1` • malformed YAML tests |
| C4 | Missing PyYAML → skip validation, not crash | `Get-ConfigState` catches `ModuleNotFoundError` |
| C5 | -WhatIf creates no files | `functional.Tests.ps1` • `WhatIf mode does not create backup directory` |
| C6 | Backup uses SHA-256 manifest | `infrastructure.Tests.ps1` • backup/restore round-trip |
| C7 | Rollback restores byte-for-byte | `production-path.Tests.ps1` • full round-trip test |

### Gate D — Verification and reporting

| # | Check | How Verified |
|---|-------|-------------|
| D1 | Verifier exits 0 when all correct | `production-path.Tests.ps1` • `Exits 0 when all entries correct` |
| D2 | Verifier exits 1 when entry missing | `production-path.Tests.ps1` • `Exits 1 when entry is missing` |
| D3 | Dataset structural tests validate installer `-ConfigRoot` output | `functional.Tests.ps1` • isolated workspace + four host asserts |
| D4 | PSScriptAnalyzer passes | CI workflow step |

---

## Non-Blocking (Deferred)

These are explicitly excluded from the laptop-stable v0.1 gate:

- **Remote Docker browser** (`server/compose.yaml`) — requires Linux server
- **SSH tunnel concurrency** (`docs/05-SSH-CONCURRENCY-FIX.md`) — server-side hardening, operational, not install-time correctness
- **kagent / Kubernetes MCP** (`docs/runbooks/local-kagent-a2a-lab.md`) — lab active (not production baseline)
- **A2A task dispatch** — historical L4 uses the existing `message/stream` helper; REST card discovery alone is metadata, and legacy `tasks/sendTask` is not the qualified path. See the canonical evidence index.
- **Functional MCP invocation across all 5 surfaces** — requires interactive editor sessions; structural/production-path tests prove config correctness
- **Node.js version upgrade** (23 → 24 LTS) — deploy-time, not install-time
- **Dev container reproducibility** (pip install uv) — Linux dev environment, not Windows target

---

## Current-Head Baseline Checklist

RECON-02 is a source integration candidate, not the stable release candidate.
The checkmarks below retain the earlier checklist and do not certify this
combined head. Its dated qualification record and final PR identify the actual
commands and unresolved formatting/typing debt.


This is a short preparation gate, not a second roadmap and not release
evidence. Complete it before selecting the patch SHA.

| Check | Required result |
|-------|-----------------|
| PyYAML contract | ✅ Direct pinned `pyyaml==6.0.3` in the `dev` group; frozen uv environment imports it for workflow YAML validation. Windows pip install retained for Pester/config validation. |
| Coverage scope | ✅ `tool.coverage.run.source` and `scripts/quality/python-full.ps1` target `scripts/kagent` (no `src/` package yet). |
| Gate 0 local bar | ✅ Frozen `uv sync --group dev`, PyYAML import, `ruff check` on `scripts/kagent`/`tests/kagent`, `ruff format --check .`, `pytest -q tests/kagent`, `audit-slice -RequireEmptyStaging`, and `git diff --check`. |
| Exact candidate | ⬜ One immutable commit SHA is named as the release candidate. |
| Local deterministic checks | ⬜ Ruff, Python tests, Pester evaluation, strict Kubernetes validation, required Trivy scan, and integration-scaffold checks have recorded results for that SHA. |
| Hosted confirmation | ⬜ All required `quality.yml` jobs are green for that same SHA; historical runs do not substitute. |

Do not tag from this checklist alone: Gate B's Windows target-host round trip is
still required.

### Full-quality wrapper (not a Gate 0 pass criterion)

`scripts/quality/python-full.ps1` and `scripts/quality/python-fast.ps1` are
fail-closed (`$LASTEXITCODE` checked after every native step). The full wrapper
is **not** currently green and must not be treated as a release gate until the
debts below are cleared. Observed on 2026-08-01 (local Windows, Python 3.12.12):

| Check | Observed result |
|-------|-----------------|
| Mypy (`uv run mypy scripts/kagent`) | Exit 1 — 26 errors in 3 files |
| Coverage | Total 79.88% under `fail_under` 80 with `precision = 2`. After that config: `uv run pytest -q tests/kagent --cov=scripts/kagent` exits 1; `uv run coverage report --precision=2 --fail-under=80` exits 2. `python-full.ps1` runs the explicit coverage-report step after pytest. |
| Bandit (`uv run bandit -r scripts/kagent -q`) | Exit 1 — 14 Low / 0 Medium / 0 High |
| Pip-audit (`uv run pip-audit` via `python-full.ps1`) | Timed out in the observed environment on 2026-08-01; not classified as flaky without repeat evidence |

Gate 0 acceptance remains the checklist bar above. Do not claim the full-quality
gate passes.

## Current security and quality qualification boundary

Use [dependency-security.md](runbooks/dependency-security.md). Dependency locks,
complete third-party inventories, advisory source freshness and exact-head CI
must be qualified before acceptance. Image advisory scans are distinct from the
required repository policy and do not establish zero upstream image CVEs.

The quality wrappers now fail closed and target the actual `scripts/kagent`
code, with coverage precision 2 and the unchanged 80% threshold. This correction
does not certify the full quality wrapper or erase existing typing/coverage
work. Its actual outcome must be recorded; a security-only pass is not a stable
release approval. Target-host install/verify/rollback remains a separate gate.

## Release Checklist

When all acceptance gates above pass:

1. ✅ Run `.\scripts\evaluation\run-evaluation.ps1` — **79+ passed, 0 failed** locally (5 skipped optional hosts; includes ConfigRoot structural isolation). **Local validation only — not CI evidence until Quality is green.**
2. ✅ Run `.\scripts\install-global-playwright-mcp.ps1 -WhatIf` — plan correct, no mutation
3. ✅ Run `.\scripts\install-global-playwright-mcp.ps1` — backup + install (backup dir `20260709-125005`)
4. ✅ Run `.\scripts\verify-global-playwright-mcp.ps1` — exit 0, all 4 targets correct
5. ✅ Run `.\scripts\rollback-global-playwright-mcp.ps1 -BackupDir <latest> -Force` — restore confirmed
6. ✅ Run `.\scripts\verify-global-playwright-mcp.ps1` — exit 1 (Cursor entry correctly absent after rollback)
7. [ ] Record the selected immutable release SHA in the current-head baseline
   checklist above.
8. [ ] Confirm every required `quality.yml` job passes for that exact commit —
   verify at https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/actions/workflows/quality.yml after push.
9. [ ] Tag that exact commit as `laptop-stable-v0.1.1`.

> **Tag note:** `laptop-stable-v0.1` remains at `cdb7dc0` (historical). The next tag is `v0.1.1`.

---

## Evidence Requirements

| Artifact | Location | Format |
|----------|----------|--------|
| Pester test results | `scripts/evaluation/results/evaluation-results.xml` | NUnit XML |
| Evaluation report | `scripts/evaluation/results/evaluation-report.md` | Markdown |
| CI workflow run | GitHub Actions for the release commit | Link |
| Verification output | Terminal log | Text |

## RECON-02 quality debt (2026-11-03)

Keep the November 1 main-security observations visible: three formatting
changes and strict mypy's 257 errors in six unchanged source/test files were
outside the newly enforced CI gates. Main's coverage observation was 80.40%
at the unchanged 80% threshold; the older 79.88% row above is dated history.
The combined tree must receive its own measurements; neither debt nor an old
coverage result disappears because the two security PRs pass independently.
See [combined qualification](../reports/reconciliation/recon-02-20261103.json).

Combined Windows measurements: `ruff format --check .` passes all 27 files;
the three former main differences match the already-reviewed #9/#15 content,
not an unrecorded formatting repair in RECON-02. Strict mypy over
`scripts/kagent tests/kagent` reports 433 errors in 18 files (24 checked), all
of whose Python inputs match #15. Root-only coverage with the four SDK modules
excluded is 76.06% and fails the unchanged 80% threshold; all 305 root tests
still pass. Strict SDK/auditor/new-contract typing passes independently. These
measurements are retained debt, outside the existing required Quality jobs;
they must not be described as a green full-quality wrapper or release gate.
