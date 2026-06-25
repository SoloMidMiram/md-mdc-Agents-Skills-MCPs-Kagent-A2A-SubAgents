# Laptop-Stable Acceptance Plan

> **Derived from:** Static QA review of commit `cdaa760`
> **Status:** `CORE_PLAN_IMPLEMENTED_MOSTLY` → `LAPTOP_STABLE_V0_1_READY` after CI pass

---

## Goal

Move from production-path-tested coverage to **laptop-stable v0.1**: the installer can be run on a new Windows machine, register `playwright-global` across all 4 config targets, and roll back cleanly — with CI affirmatively proving it.

---

## Current Status (at cdaa760)

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
| PyYAML dependency | ⚠️ **Pinned** | CI installs PyYAML; local `Get-ConfigState` skips gracefully if missing |
| Documented test counts | ⚠️ **Static** | README says "70 tests" — derived from Pester run, not hardcoded per-file |
| Dataset structural tests | ✅ Done | Assert file exists, entry non-null, fields match expected |
| Old plan doc | ✅ Archived | `docs/laptop-stable-implementation-plan.md` → replaced by this file |
| Corrupted review verdict | ✅ Archived | Moved to `docs/archive/` |
| Terminology normalized | ✅ Done | "4 config targets / 5 runtime surfaces" used consistently |
| Remote Docker runtime | ❌ Deferred | Requires Linux server; non-blocking for laptop-stable |
| SSH/kagent/A2A | ❌ Future | Design only; non-blocking for laptop-stable |

---

## Acceptance Gates

### Gate A — CI affirmatively passes

| # | Check | How Verified |
|---|-------|-------------|
| A1 | JSON templates are valid | CI step validates `config/templates/*.json` |
| A2 | PSScriptAnalyzer produces no errors | CI step `Invoke-ScriptAnalyzer -Severity Error` |
| A3 | Pester evaluation suite passes | CI step `run-evaluation.ps1 -CI` — exit code 0 |
| A4 | PyYAML installed in CI | CI step `pip install pyyaml` |
| A5 | Evaluation artifacts uploaded | CI step `actions/upload-artifact` |
| A6 | Workflow runs on `push` and `pull_request` | ✅ Already configured |

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
| D3 | Dataset structural tests validate content | `functional.Tests.ps1` • asserts file exists, entry non-null, fields match |
| D4 | PSScriptAnalyzer passes | CI workflow step |

---

## Non-Blocking (Deferred)

These are explicitly excluded from the laptop-stable v0.1 gate:

- **Remote Docker browser** (`server/compose.yaml`) — requires Linux server
- **SSH tunnel concurrency** (`docs/05-SSH-CONCURRENCY-FIX.md`) — server-side hardening, operational, not install-time correctness
- **kagent / Kubernetes MCP** (`docs/04-KAGENT-INTEGRATION.md`) — design only
- **A2A delegation** — design only
- **Functional MCP invocation across all 5 surfaces** — requires interactive editor sessions; structural/production-path tests prove config correctness
- **Node.js version upgrade** (23 → 24 LTS) — deploy-time, not install-time
- **Dev container reproducibility** (pip install uv) — Linux dev environment, not Windows target

---

## Release Checklist

When all acceptance gates above pass:

1. Run `.\scripts\evaluation\run-evaluation.ps1` — confirm 0 failures
2. Run `.\scripts\install-global-playwright-mcp.ps1 -WhatIf` — confirm plan matches expectation
3. Run `.\scripts\install-global-playwright-mcp.ps1` — confirm backup + install
4. Run `.\scripts\verify-global-playwright-mcp.ps1` — confirm exit 0
5. Run `.\scripts\rollback-global-playwright-mcp.ps1 -BackupDir <latest> -Force` — confirm restore
6. Run `.\scripts\verify-global-playwright-mcp.ps1` — confirm exit 1 after rollback
7. Confirm CI workflow passes for the release commit
8. Tag the commit as `laptop-stable-v0.1`

---

## Evidence Requirements

| Artifact | Location | Format |
|----------|----------|--------|
| Pester test results | `scripts/evaluation/results/evaluation-results.xml` | NUnit XML |
| Evaluation report | `scripts/evaluation/results/evaluation-report.md` | Markdown |
| CI workflow run | GitHub Actions for the release commit | Link |
| Verification output | Terminal log | Text |
