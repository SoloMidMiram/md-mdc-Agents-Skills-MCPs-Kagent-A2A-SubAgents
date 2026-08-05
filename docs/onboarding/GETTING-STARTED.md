# Introduction to the MCPtest Laboratory

## What This Repo Is

This repository is a portable MCP learning and implementation lab. It combines:

- host-level MCP setup for VS Code, Cursor, Codex CLI, and Continue
- Playwright browser automation labs
- Docker-based remote browser runtime docs
- a local Kubernetes and `kagent` A2A lab

## What Works Today

| Capability | Status |
|-----------|--------|
| Playwright MCP host registration | Working and documented |
| Local browser automation exercises | Working and documented |
| Remote browser Docker scaffold | Implemented; needs a Linux server to use remotely |
| AI tooling scaffold and host guidance | Implemented |
| Local `kagent` namespace and UI | Lab path implemented; use the evidence index for dated runtime state |
| A2A sample agent and tool-server manifests | Committed; L4/L5 and I0-I2 are Proven in the canonical evidence index |
| kagent health and A2A verification scripts | Available for cluster inspection and agent card validation |

## Current Local kagent Reality

The repo is past design-only kagent documentation. The authoritative dated
status, capability decisions, implemented corrections, and open flaw ledger are
maintained in `evidence/kagent/README.md`. In summary, L0-L5 and I0-I2 are
Proven. I3-Cursor remains Blocked — see `evidence/kagent/README.md` for the
current failure stage, dated evidence, and next acceptance action. L6, L7, and
I4 remain Not proven; I5 is Not attempted.

Use these documents in order for cluster work:

1. `evidence/kagent/README.md`
2. `docs/reference/kagent-capability-matrix.md`
3. `docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md`
4. `docs/runbooks/local-kagent-a2a-lab.md`

## Quick Start

```powershell
git clone https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents.git
cd md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents
.\scripts\install-global-playwright-mcp.ps1
.\scripts\verify-global-playwright-mcp.ps1
codex mcp list
```

Then use:

- `docs/reference/portable-settings-bundle.md` for the full machine setup path
- `docs/onboarding/EDUCATIONAL-PROJECTS.md` to choose and safely extend an educational lane
- `docs/onboarding/AGENT-GOVERNANCE-ROADMAP.md` before adding repository rules, skills, or hooks
- `docs/runbooks/local-playwright-lab.md` for safe browser exercises
- `docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md` for the phased kagent learning path
- `docs/runbooks/local-kagent-a2a-lab.md` for the active local cluster lab

## Reading Order

1. `docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md`
2. `docs/onboarding/AGENT-GOVERNANCE-ROADMAP.md`
3. `docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md`
4. `docs/01-MCP-MENTAL-MODEL.md`
5. `docs/reference/portable-settings-bundle.md`
6. `docs/runbooks/local-playwright-lab.md`
7. `docs/runbooks/remote-playwright-lab.md`
8. `docs/runbooks/local-kagent-a2a-lab.md`
9. `docs/architecture/SCALABLE-REFACTOR-PLAN.md`
10. `docs/integrations/`
11. `docs/04-KAGENT-INTEGRATION.md`
12. `docs/runbooks/troubleshooting.md`

## Key Concepts

### MCP Is Not Inside The Editor

The editor is the MCP host. The MCP server is a separate process or endpoint.
That separation explains most configuration and networking behavior in this
repo.

### Each Host Owns Its Own Config

| Host | Config path | Format |
|------|-------------|--------|
| VS Code | `%APPDATA%\Code\User\mcp.json` | JSON |
| Cursor | `%USERPROFILE%\.cursor\mcp.json` | JSON |
| Codex | `%USERPROFILE%\.codex\config.toml` | TOML |
| Continue | `%USERPROFILE%\.continue\config.yaml` | YAML |

### "Global" Means Per-Host User-Level Registration

This repo uses "global" to mean the MCP server is registered in each supported
host at the user level. It does not mean Windows or Docker provides one shared
registry for all tools.

## Directory Map

```text
F:\Git\MCPtest\
|-- .github\         CI, prompts, agents, repo instructions
|-- .project-ai\     Durable memory and templates
|-- .vscode\         Workspace settings and tasks
|-- config\          Host templates and integration placeholders
|-- deploy\          Local cluster manifests
|-- docs\            Onboarding, runbooks, architecture, and reference docs
|-- evidence\        Validation evidence
|-- scripts\         Install, verify, quality, and k8s scripts
`-- server\          Remote Playwright Docker runtime
```

> **Last updated:** 2026-08-04
> **Source repo:** `F:\Git\MCPtest`

Reference documents:

- [Glossary](../reference/GLOSSARY.md) — canonical definitions for terms
- [Documentation organization](../DOCUMENTATION-ORGANIZATION.md) — placement and maintenance rules
- [Educational lanes architecture](../architecture/EDUCATIONAL-LANES-ARCHITECTURE.md) — stable-core isolation and promotion rules
- [Agent governance roadmap](AGENT-GOVERNANCE-ROADMAP.md) — evaluate and promote repository rules, skills, and hooks
- [Educational problem manual](../runbooks/educational-problem-manual.md) — diagnose, document, reflect, and promote lessons
- [Project constraints](../../constraints.md) — non-negotiables and invariants
- [REPO_MANIFEST.yaml](../../REPO_MANIFEST.yaml) — flat index of repo artifacts
