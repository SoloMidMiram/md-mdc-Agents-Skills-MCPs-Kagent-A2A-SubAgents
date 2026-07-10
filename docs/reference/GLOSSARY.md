# Glossary

Canonical definitions for terms used across the repository.
Each entry links to its authoritative source.

---

## Host

An editor or CLI tool that acts as an MCP host (client). A host discovers and
invokes MCP tools exposed by MCP servers.

**Examples:** VS Code, Cursor, Codex CLI, Continue

**Authority:** `config/templates/*`, `scripts/McpConfigTargets.ps1`

---

## Config target

One of the four host-specific configuration file formats and locations that
the installer writes to. Each target uses a different file format and path.

| Target | Config file | Format |
|--------|-------------|--------|
| VS Code | `%APPDATA%\Code\User\mcp.json` | JSON |
| Cursor | `%USERPROFILE%\.cursor\mcp.json` | JSON |
| Codex CLI | `%USERPROFILE%\.codex\config.toml` | TOML |
| Continue | `%USERPROFILE%\.continue\config.yaml` | YAML |

**Authority:** `scripts/McpConfigTargets.ps1`, `scripts/install-global-playwright-mcp.ps1`

---

## Runtime surface

A (host, editor) pair where an MCP server runs. There are **4 config targets**
and **5 runtime surfaces** because Continue runs as a plugin inside both VS
Code and Cursor.

| # | Runtime surface | Editor | Config target |
|---|----------------|--------|---------------|
| 1 | Codex CLI | Codex CLI | Codex (`config.toml`) |
| 2 | VS Code native Copilot | VS Code | VS Code (`mcp.json`) |
| 3 | Cursor native agent | Cursor | Cursor (`mcp.json`) |
| 4 | Continue in VS Code | VS Code | Continue (`config.yaml`) |
| 5 | Continue in Cursor | Cursor | Continue (`config.yaml`) |

**Authority:** `evidence/global/global-validation-matrix.md`

---

## MCP server

A process that exposes tools via the Model Context Protocol. Each MCP server
has a name, package, command, and config entry in every target host.

**Primary server in this repo:** `playwright-global` (`@playwright/mcp@0.0.76`)

**Authority:** `config/templates/*`, `docs/runbooks/local-playwright-lab.md`

---

## Stable path

The production-tested, release-gated path. Currently: user-level Playwright
MCP host registration across all 4 config targets (install / verify / rollback
round-trip with Pester validation and CI).

**Authority:** `docs/laptop-stable-acceptance-plan.md`

---

## Lab path

An active experimentation path that is documented but **not** release-gated.
May work on a specific machine but lacks one-command install or CI validation.

**Current lab path:** kagent / A2A on `docker-desktop` Kubernetes.

**Authority:** `docs/runbooks/local-kagent-a2a-lab.md`, `docs/laptop-stable-acceptance-plan.md` (Non-Blocking section)

---

## Laptop-stable gate

The set of acceptance criteria (gates A–D) that a release must pass. Local
gates (B–D, installer round-trip, Pester suite, WhatIf safety) are verified
before a tag; Gate A (CI) must pass on the release commit.

**Authority:** `docs/laptop-stable-acceptance-plan.md`

---

## Layer

A logical tier in the runtime model used by the scalable refactor plan and
tooling registry. Layers group capabilities by scope (local browser, Azure
cloud, Kubernetes agent, etc.).

**Authority:** `docs/architecture/SCALABLE-REFACTOR-PLAN.md`, `config/integrations/tooling-registry.yaml`

---

## Activation gate

A condition that must be met before a capability is usable. Recorded in the
tooling registry and integration docs. Examples: package pinned, extension
installed, Azure signed in.

**Authority:** `docs/integrations/ACTIVATION-GATES.md`

---

## Evidence level

A status label in the global validation matrix describing how thoroughly a
runtime surface has been tested.

| Level | Meaning |
|-------|---------|
| `STRUCTURAL_PASS` | Config parses and expected fields exist |
| `DISCOVERY_PASS` | Host lists or discovers the MCP server |
| `FUNCTIONAL_PASS` | A real MCP tool invocation succeeded |

**Authority:** `evidence/global/global-validation-matrix.md`

---

## Base vs sample deploy

Deploy assets divided by purpose:

- **`deploy/base/`** — reusable shared resources (e.g. `RemoteMCPServer` manifest)
  that multiple agents or environments import.
- **`deploy/samples/`** — standalone example manifests (e.g. `k8s-a2a-agent.yaml`)
  for learning or one-off deployment.

**Authority:** `deploy/README.md`
