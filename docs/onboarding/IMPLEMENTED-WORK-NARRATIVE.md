# Implemented Work Narrative

**Review date:** 2026-07-16

This narrative describes what this repository has already implemented and what
the completed work means. It is intentionally not a roadmap. Open work,
unfinished experiments, and next engineering slices remain in
`docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md`.

## Executive State

The repository has moved from a broad tooling experiment into a project with a
usable stable center and a clearly separated lab lane.

The stable center is the user-level `playwright-global` MCP registration path
for VS Code, Cursor, Codex CLI, and Continue. That path includes installation,
verification, rollback, templates, safety checks, Pester coverage, and CI
configuration.

The lab lane is the local `kagent` and A2A environment on Docker Desktop
Kubernetes. It has running controller/UI infrastructure, accepted agents, sample
manifests, health inspection scripts, and REST-based agent-card validation.

The most important completed job is not just adding files. It is the separation
of release-gated laptop configuration from experimental Kubernetes/A2A work.
That separation gives the project a usable core without pretending the whole
agent stack is production-ready.

## Implemented Stable Lane

### Multi-host Playwright MCP registration

The installer path registers the same `playwright-global` MCP server across four
configuration targets:

- VS Code user MCP config
- Cursor user MCP config
- Codex CLI config
- Continue config

The implementation centralizes target metadata in
`scripts/McpConfigTargets.ps1`, including desired command, package, arguments,
format, server key, and typed state names. That gives the installer, verifier,
and rollback script one shared model instead of separate hard-coded behavior.

The target package is pinned as `@playwright/mcp@0.0.76`, invoked through `npx`
with `--isolated`.

### Convergent installer behavior

`scripts/install-global-playwright-mcp.ps1` implements a convergent install
flow. It inspects every target before mutation, builds a plan, and only creates
a backup when at least one target needs a file creation, entry creation, or
stale-entry update.

Implemented states include:

- missing file
- missing entry
- correct entry
- stale entry
- malformed file
- missing parser dependency

The script fails before mutation when a target is malformed or when required
validation dependencies are unavailable. That is a conservative choice for
user-level editor configuration, where partial writes would be riskier than a
hard stop.

The `-WhatIf` path is also implemented as a real dry run. It reports planned
changes without creating a backup directory or mutating config files.

### Verification and rollback

`scripts/verify-global-playwright-mcp.ps1` validates that all configured targets
contain the expected `playwright-global` entry.

`scripts/rollback-global-playwright-mcp.ps1` restores backed-up files using a
manifest with SHA-256 hashes. The rollback design also records tombstones for
files that did not exist before install, allowing rollback to delete installer-
created files instead of leaving behind new user config.

That is a strong practice for tools that mutate a developer's home-directory
configuration. The implementation treats rollback as part of the product, not
as an afterthought.

### Production-path Pester coverage

The evaluation suite exercises real scripts against temporary config roots. It
covers JSON, TOML, and YAML config paths; creation; stale replacement;
idempotence; malformed input; rollback round trips; missing entries; and
non-mutating `-WhatIf` behavior.

This is better than testing only helper functions. The tests validate the user
workflow the project actually ships: install, verify, rollback, and verify
again.

### CI configuration

`.github/workflows/quality.yml` is implemented for push and pull request runs
on Windows. It installs Node.js, Python, Codex CLI, Pester, PSScriptAnalyzer,
and PyYAML; validates JSON templates; runs PowerShell static analysis; checks
the integration scaffold; runs the evaluation suite; and uploads evaluation
artifacts.

The CI workflow is therefore present and shaped around the actual stable lane.
The project still distinguishes "CI configured" from "a specific release commit
has a green workflow run" in the acceptance plan.

## Implemented Documentation Structure

The repository now has a purpose-based documentation shape:

- `docs/onboarding/` for first-read and current-state documents
- `docs/runbooks/` for operational lab instructions
- `docs/reference/` for reusable matrices, glossary, and settings details
- `docs/architecture/` for target structure and separation plans
- `docs/integrations/` for AI tooling activation and host capability material
- `docs/archive/` for historical planning and review artifacts

The README has become a usable entry point rather than a dense project dump. It
points to the stable path first, then the lab path, then the repository map and
reading order.

`constraints.md` records project invariants: stable path versus lab path, CI
rules, installer behavior, deploy taxonomy, and memory discipline.

`REPO_MANIFEST.yaml` adds a flat index over important artifacts with purpose,
status, and authority fields. This gives the repo a lightweight bridge between
human documentation and future machine validation.

## Implemented Runtime and Lab Work

### Local Playwright path

The local Playwright learning path is documented through runbooks and evidence.
It includes local browser automation exercises, console/network inspection,
clicking, accessibility snapshots, and validation evidence under
`evidence/local/` and `evidence/global/`.

The strongest runtime evidence is for Codex CLI, where the validation matrix
records structural, discovery, and functional success for `playwright-global`.
The other host surfaces have structural validation recorded and are kept
separate from functional validation.

That distinction is good practice. It prevents config correctness from being
overstated as full runtime success in every editor.

### Remote browser scaffold

The `server/` directory implements a Docker Compose scaffold for a remote
Playwright browser runtime. The related runbook documents the operational model
and SSH tunnel workflow.

This is implemented as a scaffold rather than part of the laptop-stable release
gate, which is the right boundary. It is useful repo material, but it has
different infrastructure assumptions than local host registration.

### kagent and A2A local lab

The local `kagent` lane is documented and partially executable:

- `deploy/base/kagent/` contains reusable shared kagent resources.
- `deploy/samples/kagent/` contains sample A2A agent manifests.
- `scripts/kagent/check-kagent-health.ps1` inspects pods, agents,
  RemoteMCPServer resources, events, and service endpoints.
- `scripts/kagent/test-a2a-agent.py` checks controller reachability, fetches
  agent details through the REST API, probes A2A JSON-RPC methods, and reports
  the controller behavior.

The implemented lab evidence records a local Docker Desktop kagent namespace
with running pods, accepted and ready agents, UI reachability, and REST
agent-card access.

The lab lane is valuable because it proves local reconciliation and inspection
paths. It is also correctly described as lab work, not as the stable release
gate.

## Implemented Tooling Scaffold

The repository includes a Python and PowerShell tooling scaffold:

- `pyproject.toml` for Python project metadata and linting configuration
- `.pre-commit-config.yaml` for local quality hooks
- `scripts/quality/` for Python quality entry points
- `scripts/kubernetes/validate.ps1` for Kubernetes asset validation
- `scripts/security/scan.ps1` for security-oriented checks
- `config/integrations/` for Azure and Foundry placeholder integration files
- `docs/integrations/` for activation gates and integration runbook material

These pieces show that the repo is preparing for broader AI tooling integration
without forcing those integrations into the stable Playwright installer gate.

## Critique of the Implemented State

The implemented work is strongest where executable evidence exists. The
installer, verifier, rollback, and Pester suite form the most credible part of
the project because they test the same paths a user runs.

The documentation is much better organized than a single plan-heavy pile, but it
still carries duplicated status language across README, acceptance plan,
validation matrix, manifest, and roadmap. That increases the chance of drift.
The new manifest helps, but only if future changes keep it aligned with the
repo.

The project now uses a healthier maturity boundary: structural validation,
discovery validation, and functional validation are not the same thing. That
boundary should remain visible anywhere the project describes support across
multiple hosts.

The kagent lab is useful and real, but its completed evidence is about local
cluster health, agent acceptance, and REST inspection. It should continue to be
read as a lab lane until the roadmap closes the protocol and tool-execution
items.

The release acceptance material is careful about local gates and release tags.
The important critique is evidentiary: "configured in CI" and "green on the
release commit" are different states. The project already records that
distinction, and the release narrative should keep treating it as a hard line.

## Good Practices Already Present

- Stable and experimental lanes are separated instead of sharing one acceptance
  boundary.
- Host configuration is modeled centrally in `McpConfigTargets.ps1`.
- Installer behavior is convergent and idempotent.
- Dry-run behavior is implemented as a real non-mutating path.
- Malformed configuration fails before mutation.
- Rollback uses SHA-256 verification and tombstones for installer-created files.
- Tests exercise production paths, not only helper functions.
- The docs now have purpose-based locations and a practical reading order.
- The README identifies what is usable today before pointing to future work.
- The capability matrix separates structural, discovery, and functional
  validation.
- Deploy assets distinguish reusable base resources from sample manifests.
- The repo has explicit constraints that prevent lab work from destabilizing the
  stable laptop path.

## What This Project Has Earned

The project has earned the label "stable Playwright MCP configuration tool plus
local agent tooling lab."

It has not tried to make every experimental part release-critical, and that is
the main reason the current shape is workable. The completed work is useful
because the stable lane is small enough to test and the lab lane is visible
enough to learn from.

For outstanding work, use the roadmap in
`docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md`.
