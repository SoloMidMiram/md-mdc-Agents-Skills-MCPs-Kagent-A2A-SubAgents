# MCP Agent Tooling Laboratory

[![MCP](https://img.shields.io/badge/MCP-Model_Context_Protocol-2563EB)](#)
[![Playwright](https://img.shields.io/badge/Playwright-MCP_Server-45BA4B)](https://github.com/microsoft/playwright-mcp)
[![VS Code](https://img.shields.io/badge/VS_Code-Agent_MCP-007ACC)](#)
[![Cursor](https://img.shields.io/badge/Cursor-Agent_MCP-6C47FF)](#)
[![Codex CLI](https://img.shields.io/badge/Codex_CLI-Agent_MCP-000000)](#)
[![Continue](https://img.shields.io/badge/Continue-Agent_MCP-FF6B35)](#)
[![CI](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/actions/workflows/quality.yml/badge.svg)](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/actions/workflows/quality.yml)

Portable MCP host setup, browser automation labs, and a local `kagent` A2A lab
for VS Code, Cursor, Codex CLI, and Continue.

## Quick Start

**Next delivery:** [REL-01 #50](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/issues/50) — package the offline A2A practice release. EDU-02 #36 and EDU-03 #37 are closed completed. Release replay is complete. Acceptance and release publication remain pending. Start with the [documentation review](docs/runbooks/edu-02-documentation-review.md) and [coding fixture](docs/runbooks/edu-03-coding-fixture.md) runbooks. These are synthetic workflows, not live coding improvement evidence.

See the [release-first phase plan](docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md#release-first-execution-plan--2026-11-20). #20/#21 remain gated, #22–#25 deferred, #40–#45 optional research.

### Offline A2A practice

Use Git and uv on your shell PATH. Setup may download Python and locked
dependencies. The lab and test commands run offline using checked-in fixtures.

```text
git clone https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents.git
cd md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents
uv sync --frozen --group dev --python 3.13.15
uv run --no-sync --offline python --version
uv run --no-sync --offline python -m scripts.kagent.experiments.edu02_lab
uv run --no-sync --offline python -m scripts.kagent.experiments.edu03_lab
```

Use the [EDU-02](docs/runbooks/edu-02-documentation-review.md) and
[EDU-03](docs/runbooks/edu-03-coding-fixture.md) runbooks for the intentional
rejection cases and focused `python -m pytest` commands. See the
[v0.1.0 replay evidence](docs/releases/v0.1.0/replay-evidence.md) for the
verified commit and results.

During fresh-checkout validation, `uv run --no-sync --offline pytest` exited
with code 2 because collection could not import the repository's `scripts`
namespace. Run tests from the repository root using
`uv run --no-sync --offline python -m pytest`, the verified invocation on Windows
and Ubuntu WSL.

### Windows Playwright host setup

```powershell
git clone https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents.git
cd md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents
.\scripts\install-global-playwright-mcp.ps1 -WhatIf      # preview changes
.\scripts\install-global-playwright-mcp.ps1               # apply
.\scripts\verify-global-playwright-mcp.ps1                # confirm
codex mcp list
```

Primary docs:

- [Project north star](docs/north-star.md) — context-first priority; historical A2A direction retained
- [Getting started](docs/onboarding/GETTING-STARTED.md)
- [Educational projects map](docs/onboarding/EDUCATIONAL-PROJECTS.md)
- [Educational lanes architecture](docs/architecture/EDUCATIONAL-LANES-ARCHITECTURE.md)
- [Educational problem manual](docs/runbooks/educational-problem-manual.md)
- [kagent educational roadmap](docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md)
- [kagent evidence and current status](evidence/kagent/README.md)
- [kagent PR2 LiteLLM gateway runbook](docs/runbooks/kagent-litellm-gateway.md)
- [kagent PR2 LiteLLM runtime evidence](evidence/runtime/kagent-litellm-success.md)
- [kagent A2A educational examples](docs/runbooks/kagent-a2a-examples.md)
- [2026-08-20 evidence-based review](reports/2026-08-20-kagent-evidence-review.md)
- [documentation organization guide](docs/DOCUMENTATION-ORGANIZATION.md)
- [Implemented work narrative](docs/onboarding/IMPLEMENTED-WORK-NARRATIVE.md)
- [Implemented state and roadmap](docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md)
- [Portable settings bundle](docs/reference/portable-settings-bundle.md)
- [Glossary](docs/reference/GLOSSARY.md)
- [Project constraints](constraints.md)
- [Scalable refactor plan](docs/architecture/SCALABLE-REFACTOR-PLAN.md)

Runbooks:

- [Local Playwright lab](docs/runbooks/local-playwright-lab.md)
- [Remote Playwright lab](docs/runbooks/remote-playwright-lab.md)
- [Local kagent A2A lab](docs/runbooks/local-kagent-a2a-lab.md)
- [kagent PR2 LiteLLM gateway](docs/runbooks/kagent-litellm-gateway.md)
- [kagent A2A educational examples](docs/runbooks/kagent-a2a-examples.md)
- [SSH concurrency fix](docs/runbooks/ssh-concurrency-fix.md)
- [Troubleshooting](docs/runbooks/troubleshooting.md)

## Dependency security scope — historical RECON-02 notes

The paragraphs below record the earlier candidate qualification stage. RECON-02 and its source PRs have since been integrated into main; these dated statements must not be interpreted as current merge blockers. The live issue order is in the linked roadmap.

RECON-02 combines the reviewed root correction (#14, `17312a75`) and isolated
SDK correction (#15, `7cb921ce`) on a separate candidate branch. It preserves
both audits, generated locks, artifact hashes and the development-inclusive
Trivy policy. No existing PR branch or main is merged by preparing this tree.
Qualification belongs to this combined tree; independently passing security
heads do not establish combined acceptance. See the
[dependency security runbook](docs/runbooks/dependency-security.md),
[contradiction register](docs/reference/contradiction-register.md) and issue #11.
CTX-01 correctness and live Context7/Kagent/L6/L7/I3/I4 remain separate gates.

## Capability snapshot — dated observations and stable host setup

The runtime observations below are historical evidence, not a fresh deployment or cluster health check.

Two paths matter today:

- **Stable path**: user-level `playwright-global` registration across VS Code, Cursor, Codex, and Continue. Verified by repeatable install (`-WhatIf` first) / verify / rollback / verify round-trip, covered by 73+ Pester tests, and covered by CI configuration on push and pull_request.
  `laptop-stable-v0.1` is tagged at `cdb7dc0`; this tree targets patch `laptop-stable-v0.1.1` (UTF-8 onboarding, narrative sync, bridge manifests).
- **Educational lab path**: local `kagent` on `docker-desktop` — prove and measure
  bounded A2A workflows first, then attach Cursor and Codex as clients/workers.
  The PR2 gateway checkpoint is the smaller prerequisite path:
  `kagent ModelConfig -> LiteLLM /v1 -> agent-coder -> response`, with no MCP
  tools, no multiple agents, and no local-model fallback. Its dated evidence
  proves the gateway/model response path; the card gate remains pending.
  These runtime observations are historical, not a fresh cluster health check.
  Dated L4/L5 and I0-I2 evidence is Proven; I3-Cursor remains Blocked (interop proof, not
  education gate). L6/L7 and I4 remain Not proven. See
  [north star](docs/north-star.md) for priority and
  [evidence index](evidence/kagent/README.md) for capability decisions.

Use [docs/north-star.md](docs/north-star.md) for direction,
[docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md](docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md)
for phase/PR sequencing, [docs/runbooks/local-kagent-a2a-lab.md](docs/runbooks/local-kagent-a2a-lab.md)
for the cluster runbook, and [docs/runbooks/kagent-a2a-examples.md](docs/runbooks/kagent-a2a-examples.md)
for the E1–E5 educational examples.

## Security and branch scope — historical pre-integration notes

The original branch-specific statements below describe the period before #9/#10/#13 were merged. For current merge status and implementation queue use the live roadmap.

Use the [dependency security runbook](docs/runbooks/dependency-security.md) and
[contradiction register](docs/reference/contradiction-register.md) for the current
security qualification boundary and corrected documentation claims.

This branch starts from main `3c99181`. The SDK integration (#9), retained LAB-01
(#10) and CTX-01 builder (#13) are separate unmerged reviews. Their files and
runtime claims are not shipped here by this security correction. See issue #11
for maintainer-controlled integration; no merge, release tag or live experiment
is authorized by a passing dependency audit.

## What's Inside

### Host configuration

| Host | What it gets | Config location |
|------|--------------|-----------------|
| VS Code Copilot | 7 MCP servers and repo instructions | `%APPDATA%\Code\User\mcp.json` |
| Cursor Agent | Playwright MCP and repo contract | `%USERPROFILE%\.cursor\mcp.json` |
| Codex CLI | Playwright MCP and sandbox config | `%USERPROFILE%\.codex\config.toml` |
| Continue | Models, slash-command personas, Playwright MCP, rules | `%USERPROFILE%\.continue\config.yaml` |

### Main runtime areas

| Area | Primary artifacts | Status |
|------|-------------------|--------|
| Browser automation | `docs/runbooks/local-playwright-lab.md`, `docs/runbooks/remote-playwright-lab.md`, `server/` | Stable |
| Host configuration portability | `config/templates/`, `docs/reference/portable-settings-bundle.md` | Stable |
| AI tooling scaffold | `.vscode/settings.json`, `config/integrations/`, `docs/ai-tooling.md` | Implemented |
| Local Kubernetes and `kagent` | `docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md`, `docs/runbooks/local-kagent-a2a-lab.md`, `deploy/base/kagent/`, `deploy/samples/kagent/` | Historical L4/L5 and I0-I2 evidence; I3 Blocked; L6/L7/I4 unproven |

### Scripts

| Script | Purpose |
|--------|---------|
| `scripts/install-global-playwright-mcp.ps1` | Register Playwright in all supported hosts |
| `scripts/verify-global-playwright-mcp.ps1` | Validate host registrations |
| `scripts/rollback-global-playwright-mcp.ps1` | Restore backed-up host config |
| `scripts/bootstrap-python-workspace.ps1` | Bootstrap the local Python toolchain |
| `scripts/evaluation/run-evaluation.ps1` | Run the Pester evaluation suite |
| `scripts/kubernetes/validate.ps1` | Validate Kubernetes-related repo assets |
| `scripts/kagent/check-kagent-health.ps1` | Inspect kagent pod/agent/RemoteMCPServer health |
| `scripts/kagent/test-a2a-agent.py` | Fetch A2A agent card and test A2A dispatch |
| `scripts/kagent/validate-litellm-gateway.py` | Offline-check the PR2 ModelConfig, no-tool agent, and evidence shape |
| `scripts/kagent/apply-litellm-modelconfig.ps1` | Apply the PR2 LiteLLM Secret, ModelConfig, and smoke agent |
| `scripts/kagent/controller_mcp_smoke.py` | Verify the bounded native controller MCP contract |

## Historical kagent roadmap and educational path

The earlier A2A-first product-priority wording below is retained for technical context. Since the November 2026 direction reconciliation, the measurable context-first assistant and runner/evaluation gates are the historical November 15 research priority; offline A2A education proceeds independently.

**North star (2026-08-07):** First prove useful A2A workflows inside kagent,
then attach Cursor and Codex as interchangeable clients/workers and compare
them. Full direction: [docs/north-star.md](docs/north-star.md).

The stable Playwright release checklist remains in
[implemented state and roadmap](docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md).
kagent phase/PR sequencing lives in
[kagent educational roadmap](docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md).

Current priority order uses the existing stable workstream IDs:

1. **RECON-01 / RECON-02** — review the combined security candidate, qualify
   its actual tree and obtain explicit maintainer dispositions for #9/#3–#8.
2. **EVID-01 / A2A-01** — preserve evidence integrity and the isolated SDK
   contract; live interoperability remains a separately authorized gate.
3. **CTX-01 / SAFE-01** — keep #12/#13 correctness repairs separate from
   security integration; require the exact read-only surface before tools.
4. **WORKER-01 / EVAL-01 / OPS-01** — advance only after their accepted
   prerequisites; retain I3/I4/L6/L7 as independent evidence requirements.

Gate 0 baseline `090ad52` and the 2026-08-07 direction pivot remain historical.
Use the [integration crosswalk](docs/reference/integration-workstreams.md) and
[kagent educational roadmap](docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md)
for ownership; included ancestor PRs are not independent changes to merge twice.

## Repository Map

```text
.
|-- constraints.md              Non-negotiables and project invariants
|-- REPO_MANIFEST.yaml          Flat index of repo artifacts (machine-readable)
|-- .devcontainer/              Reproducible Linux development container
|-- .github/                    CI, prompts, agents, repo-specific instructions
|-- .project-ai/                Durable project memory and templates
|-- .vscode/                    Workspace settings, tasks, extensions
|-- config/                     Host templates and integration placeholders
|-- deploy/
|   |-- README.md                Deploy structure guide
|   |-- base/kagent/             Reusable shared resources (RemoteMCPServer)
|   `-- samples/kagent/          Sample A2A agent manifests
|-- docs/
|   |-- onboarding/              Getting started and implemented state
|   |-- runbooks/                Operational labs and troubleshooting
|   |-- reference/               Settings bundles and capability matrixes
|   |-- architecture/            Target structure and runtime separation plans
|   |-- integrations/            Host capability matrix and AI tooling plans
|   |-- archive/                 Historical plan documents (redirect source)
|   `-- 01-*.md–07-*.md          Root-level compat redirects only
|-- evidence/                   Validation evidence
|-- scripts/
|   |-- kagent/                  kagent health checks and A2A helpers
|   `-- ...                      Install, verify, evaluation, quality, k8s
`-- server/                     Remote Playwright Docker runtime
```

## Reading Order

1. `docs/onboarding/GETTING-STARTED.md`
2. `docs/north-star.md`
3. `docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md`
4. `docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md`
5. `docs/01-MCP-MENTAL-MODEL.md`
6. `docs/reference/portable-settings-bundle.md`
7. `docs/runbooks/local-playwright-lab.md`
8. `docs/runbooks/remote-playwright-lab.md`
9. `docs/runbooks/local-kagent-a2a-lab.md`
10. `docs/runbooks/kagent-a2a-examples.md`
11. `docs/architecture/SCALABLE-REFACTOR-PLAN.md`
12. `docs/integrations/AI-TOOLING-INTEGRATION-PLAN.md`
13. `docs/04-KAGENT-INTEGRATION.md`
14. `docs/runbooks/troubleshooting.md`

## Key Concepts

- MCP is not built into the editor. The editor is the host and the MCP server is a separate process.
- There is no shared cross-IDE MCP registry. Each host reads its own config format from its own location.
- "Global" in this repo means user-level registration in every supported host, not one system-wide toggle.

## License

MIT - see [LICENSE](LICENSE).

*Current-state reconciliation: 2026-11-15. Older sections retain dated historical evidence.*
