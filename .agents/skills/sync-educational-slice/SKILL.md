---
name: sync-educational-slice
description: >
  Synchronize implementation changes, evidence, canonical docs, links,
  manifest, and commit draft for an educational phase or correction. Use
  after an educational implementation, evidence review, or documentation
  correction needs repository-wide ownership and mapping synchronization.
disable-model-invocation: true
---

# Sync Educational Slice

## Purpose
Synchronize a new educational phase addition or correction across all canonical repository owners. This skill ensures that every change is consistently reflected in evidence, roadmaps, the manifest, and documentation -- without creating duplicate planning documents or rewriting historical evidence.

## Prerequisites
- The slice has been implemented and tested (code, scripts, tests pass locally).
- The applicable evidence record has been captured and reviewed.
- The intended target branch and current local/remote state are known.

## Procedure

### 1. Identify the slice
Determine what changed:
- A new educational phase (evidence record + scripts + tests)?
- A correction to existing behavior (code fix + updated evidence)?
- A documentation update only?

### 2. Update canonical owners in order
Assess every owner in this sequence independently. Record an owner as
`not_applicable` when it does not need a change; do not stop because an earlier
owner is unchanged.

1. **Evidence index** -- `evidence/kagent/README.md`
   - Update the latest verified status table if a level decision changed.
   - Add a new record link to the record index.
   - Update the major open flaws list if the slice closes or changes a flaw.

2. **Roadmap** -- `docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md`
   - Update the phase_N roadmap table: mark items Done, update purpose/evidence.
   - Update the "next implementation slices" list.
   - Update the "major flaws to close" list.

3. **Repository roadmap** -- `docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md`
   - Update the current implemented state section for the affected area.
   - Update the known gaps or phase completion sections.

4. **Manifest** -- `REPO_MANIFEST.yaml`
   - Add any new canonical files with correct `purpose`, `status`, and `authority`.
   - Do **not** add generated output, gitignored results, or temporary files.

5. **Runbook** -- applicable `docs/runbooks/` file (e.g. `local-kagent-a2a-lab.md`)
   - Update commands, expected output, or phase references only if the operational path changed.

6. **Onboarding links** -- applicable `docs/onboarding/` or `README.md`
   - Update links to point to the new or updated canonical files.
   - Do not copy volatile counts or runtime snapshots into onboarding text.

### 3. Verify invariants
- No second roadmap, status ledger, or documentation-placement guide was created.
- No evidence record was rewritten. If a re-interpretation is needed, **append a dated addendum** to the record; do not edit the original content.
- All new canonical files are listed in `REPO_MANIFEST.yaml`.

### 4. Run applicable validation
```powershell
# Python code and tests
uv run ruff check scripts/kagent tests/kagent
uv run pytest -q tests/kagent

# Deterministic ownership/link/staging audit
pwsh -NoProfile -File `
  .agents/skills/sync-educational-slice/scripts/audit-slice.ps1 `
  -RepoRoot <repo-root> `
  -RequireEmptyStaging
```

The bundled audit fails closed for duplicate or missing manifest mappings,
unmapped dirty canonical-source paths, broken active Markdown links, and
unexpected staging. It does not decide whether a document belongs to the
correct authority owner; review that against
`docs/DOCUMENTATION-ORGANIZATION.md`.

### 5. Prepare publication hygiene
- Do not stage, commit, push, or open a PR unless the user explicitly requests
  that external state change.
- When a commit draft is in scope, list each dirty path exactly once in a
  coherent whole-file group.
- Keep generated, ignored, temporary, and unrelated files out of the draft.
- Verify the index is empty when the task does not authorize staging.

### 6. Output summary
```yaml
slice:
  description: "<what changed>"
  files_updated:
    - path: "<repo-root-relative path>"
      change: "<added|modified>"
  verification:
    ruff: "<pass|fail>"
    pytest: "<pass|fail>"
    manifest_check: "<pass|fail>"
    links: "<pass|fail|not_applicable>"
    staging_empty: "<true|false>"
    audit_slice: "<pass|fail>"
  owners:
    evidence_index: "<updated|unchanged|not_applicable>"
    educational_roadmap: "<updated|unchanged|not_applicable>"
    repository_roadmap: "<updated|unchanged|not_applicable>"
    manifest: "<updated|unchanged|not_applicable>"
    runbook: "<updated|unchanged|not_applicable>"
    onboarding: "<updated|unchanged|not_applicable>"
  invariants_verified:
    - "no second roadmap created: true"
    - "no evidence rewritten: true"
    - "all new files in manifest: true"
```

## Exit criteria
- Every affected canonical owner is updated.
- No duplicate planning documents were created.
- No evidence record was retroactively edited.
- Validation passes for the changed files.
- The diff contains only in-scope changes.

## What this skill does NOT do
- Decide whether a capability should be promoted (use `review-kagent-capability` first).
- Execute live cluster commands.
- Push or merge changes.
- Create pull requests.
- Automatically trigger on file edits.
