# Laptop-Stable Implementation Plan

Derived from the static QA review of commit `6ea1e6a`.

## Goal
Move from `PHASE_0_STRUCTURAL_REPAIR_PARTIAL_PASS` to `LAPTOP_STABLE_V0_1_READY`.

## Required gates
- `INSTALLER_FIXTURE_MATRIX_PASS` — Pester tests for all config formats and cases
- `INSTALL_ROLLBACK_ROUNDTRIP_PASS` — byte-for-byte restoration proven
- `WHATIF_NON_MUTATING_PASS` — `-WhatIf` creates no filesystem artifacts
- `CONTINUE_CONVERGENCE_PASS` — stale Continue entries detected and repaired

---

## Commit 1: Finish exact desired-state enforcement

### Files to change: `McpConfigTargets.ps1`, `install-*.ps1`, `verify-*.ps1`

#### 1a. McpConfigTargets.ps1 — Complete desired state for all formats

**Current gap:** `Desired = $null` for TOML and YAML targets.
`Get-ExpectedEntry` only works for JSON.
`New-BackupDir` ignores `-WhatIf`.
`Backup-ConfigTargets` passes `-WhatIf` but callers may not.

**Fix:**
- Add `DesiredCommand`, `DesiredArgs`, `DesiredType` properties to all 4 targets
- Deprecate the unstructured `Desired` hashtable in favor of named fields
- Add `-WhatIf` guard to `New-BackupDir`
- Fix `Backup-ConfigTargets` to check `-WhatIf` before creating manifest file
- Make `Get-ExpectedEntry` format-aware (not just JSON-gated)

#### 1b. install-global-playwright-mcp.ps1 — WhatIf non-mutating, lazy backup, Continue convergence

**Current gaps:**
- `New-BackupDir` called unconditionally before `-WhatIf` check
- Backup happens before change computation (noisy)
- Continue YAML: if `name: playwright-global` exists, assumes correct (stale-blind)
- JSON: assumes `$t.ServerKey` exists on the parsed object
- TOML stale-removal regex can eat adjacent sections

**Fix:**
- Phase 1: Compute all planned changes
- Phase 2: If no changes needed → report and exit without backup dir
- Phase 3: Only if changes needed → create backup dir, back up only affected files
- `-WhatIf`: never call `New-BackupDir`, show what would happen
- JSON: safe-create `$t.ServerKey` if missing
- Continue YAML: parse the specific list item, compare all fields, repair if stale
- TOML: parse via Python `tomllib` to read exact values; use line-safe regex for replacement

#### 1c. verify-global-playwright-mcp.ps1 — Separated warnings, structural TOML comparison

**Current gaps:**
- `$warnings` collection doesn't exist (all issues are `$failures`)
- TOML regex checks partial correctness only; doesn't compare command/args exactly
- `cursor` command shown as FAIL on machines without Cursor (should be warning)

**Fix:**
- Add `$warnings` collection and `Add-Warning` function
- Commands `code` and `cursor`: mark as optional (warning), not required (failure)
- TOML: use Python `tomllib` to load and compare `mcp_servers.playwright-global.command` and `.args`
- YAML: improve block extraction to not rely on `slashCommands:` marker

---

## Commit 2: Add Pester fixture tests

### New file: `scripts/McpConfigTargets.Tests.ps1`

**Test cases using temp directories:**
1. **Create**: install into empty fixture → configs created correctly
2. **No-op**: install into correct fixture → no changes reported, no backup dir
3. **Repair stale JSON**: wrong command/args → corrected, backup created
4. **Repair stale TOML**: wrong package → corrected
5. **Repair stale YAML**: existing entry wrong → corrected
6. **Continue convergence**: existing entry missing `--isolated` → repaired
7. **Rollback round-trip**: install → verify → rollback → byte-for-byte match
8. **WhatIf non-mutating**: `-WhatIf` flag → no filesystem changes
9. **Malformed JSON**: gracefully fails
10. **Missing file**: skips with message

### New file: `.github/workflows/quality.yml`
Run `PSScriptAnalyzer` and `Pester` on push.

---

## Commit 3: Correct documentation statuses

### Files to change: `README.md`, `evidence/global/global-validation-matrix.md`

**README changes:**
- Phase 5: "across all 5 hosts" → "across 4 configuration targets and 5 runtime surfaces"
- Phase 5 status: "STRUCTURALLY VERIFIED" → "STRUCTURAL_PASS (4/4 targets)"
- Phase 8/9/10/11: "✅ Implemented" → "STRUCTURAL_PASS" (add legend explaining levels)
- Devcontainer: "Reproducible Linux dev environment" → "Development environment (some versions floating)"

**Evidence matrix changes:**
- Add "Evidence provenance: machine-specific (Windows laptop cebit.ir)" header
- Add "Repo-local automated test status" section (currently empty)
- Remove "All PASS" language

---

## Commit 4: Runtime hardening validation

### Files to change: `server/compose.yaml`, `.devcontainer/devcontainer.json`

**Compose healthcheck:** Test `GET /mcp`, if it doesn't return 200, use a TCP check (`CMD-SHELL nc -z localhost 8931`)

**Devcontainer:**
- Pin PowerShell: `"version": "7.4"` (not `latest`)
- Pin K8s tools: `"version": "1.30"` (not `latest`)
- Pin uv: in Dockerfile or use `pip install uv==0.4.x` 
- Mark as "development environment with pinned Python/Node, floating others" in docs

---

## Implementation order

```
Commit 1: Exactness fixes (scripts only)
    ↓
Commit 2: Pester fixture tests + CI
    ↓
Commit 3: Documentation corrections
    ↓
Commit 4: Runtime hardening
```
