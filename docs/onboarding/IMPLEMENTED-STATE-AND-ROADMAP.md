# Implemented State and Roadmap

This document records the current observed state of the repository and the
local validation environment.

For a narrative of completed work only, with critique and good-practice notes,
see `docs/onboarding/IMPLEMENTED-WORK-NARRATIVE.md`.

It answers four questions:

1. What is implemented now?
2. What can be used today?
3. What is only partially working?
4. What should be stabilized or refactored next?

## Current Implemented State

### Host-level MCP setup

Implemented and documented:

- VS Code user-level MCP registration
- Cursor user-level MCP registration
- Codex CLI MCP registration
- Continue MCP registration
- shared `playwright-global` naming and pinned Playwright MCP version

Primary artifacts:

- `scripts/install-global-playwright-mcp.ps1`
- `scripts/verify-global-playwright-mcp.ps1`
- `scripts/rollback-global-playwright-mcp.ps1`
- `scripts/McpConfigTargets.ps1`
- `config/templates/`

### Browser automation learning path

Implemented and documented:

- local Playwright exercises
- remote Docker browser scaffold
- SSH tunnel workflow
- troubleshooting guidance

Primary artifacts:

- `docs/runbooks/local-playwright-lab.md`
- `docs/runbooks/remote-playwright-lab.md`
- `docs/runbooks/troubleshooting.md`
- `server/compose.yaml`
- `server/README.md`

### Agent-host documentation model

Implemented and documented:

- shared repo rules in `AGENTS.md`
- VS Code-specific repo instructions
- Continue slash-command personas
- explicit host-surface separation for Cursor, Continue, VS Code, and Codex
- an agent-governance pilot with three scoped Cursor rules, two manual
  project skills with deterministic helpers, three observation-only Cursor
  hooks, and a deterministic benchmark contract

The rules and skills are implemented but not promoted. The hooks are in shadow
mode: they log sanitized classifications and validation-family state, never
block commands, and never submit a follow-up. The original generated YAML files
were empty templates rather than scored baseline/candidate runs. The repaired
JSON harness rejects incomplete or contradictory assessments; a genuine
isolated baseline/candidate comparison and ten-event hook sample remain open.

Primary artifacts:

- `AGENTS.md`
- `.github/copilot-instructions.md`
- `.github/instructions/`
- `.github/agents/`
- `.github/prompts/`
- `.cursor/rules/`
- `.cursor/hooks.json`
- `.cursor/hooks/`
- `.agents/skills/`
- `scripts/benchmark/`
- `docs/onboarding/AGENT-GOVERNANCE-ROADMAP.md`
- `docs/ai-tooling.md`

### Tooling scaffold

Implemented and documented:

- Python toolchain scaffold
- Kubernetes validation scaffold
- security scan scaffold
- Azure and Foundry placeholder integration scaffold

Primary artifacts:

- `pyproject.toml`
- `.pre-commit-config.yaml`
- `.vscode/tasks.json`
- `scripts/quality/`
- `scripts/kubernetes/validate.ps1`
- `scripts/security/scan.ps1`
- `config/integrations/`

### Local kagent path

Implemented and validated:

- local `kagent` CRDs installed
- local `kagent` controller and UI running in `docker-desktop`
- local UI reachable on `http://localhost:8080` through port-forward (HTTP 200)
- sample A2A manifest accepted and deployment-ready
- real MCP runtime at `deploy/base/kagent/kagent-tool-server-runtime.yaml`
- `RemoteMCPServer/kagent-tool-server` accepted with discovered tools (L5)
- health verification script at `scripts/kagent/check-kagent-health.ps1`
- named `CardLab`, `DirectMcpServer`, `A2ADispatch`, and `FullMcpExecution`
  health profiles with deterministic gate tests
- A2A helper with truthful `card`, `probe`, `task`, and `both` exit semantics
- structured Phase 5D A2A tests and a selected controller 0.9.11
  `message/stream` SSE compatibility path (L4 Proven)
- Phase 5E single-task agent-mediated producer and `FullMcpExecution` consumer
  with deterministic transport/protocol/dispatch, freshness, target, source,
  tool, result, and exit-consistency tests
- quality workflow configuration for a separate locked kagent Python job
  (`uv sync --frozen --group dev`, Ruff, and full pytest), the suite-compatible
  pinned Pester 3.4.0 baseline, and an explicit deterministic kagent PowerShell
  test invocation. `bc1ce58` restores PSGallery registration with
  `Register-PSRepository -Default` when absent before Pester installation on
  Windows Server 2025. Hosted Quality run 30621076867 passed at `f18b906` on
  2026-07-31, and follow-up Quality run 30621919672 passed all jobs at the
  exact pre-merge head `94031ff`. The current pre-merge documentation update is
  a docs-only delta from that verified head and remains subject to its hosted
  final confirmation before merge.
- fail-closed Kubernetes manifest validation (`scripts/kubernetes/validate.ps1
  -Strict`) and Trivy policy scanning (`scripts/security/scan.ps1 -Required`)
  with pinned validator installation (kubeconform v0.6.7, kube-linter v0.7.1,
  Trivy v0.72.0) and deterministic Pester failure-path tests
  (`KagentToolingValidation.Tests.ps1`). Those jobs passed in hosted Quality run
  30621076867 at `f18b906`, including the required Trivy policy scan.
- `kagent-controller` REST API exposes agent card on port 8083

Current capability decisions, dated observations, corrections, and major flaws
are canonical in `evidence/kagent/README.md`. L0-L5 are proven. L4 is supported
by a recorded, strictly validated `message/stream` status-update with a
non-empty task identifier. Phase 5E shipped a nested agent-mediated evidence
helper and tightened `FullMcpExecution` gates; the live attempt failed closed
without a correlated tool observation, so L6 remains Not proven. L7
repeatability is not proven.
The historical Phase 5 direct `tools/call` failed because its negotiated session
was not reused. Phase 5B subsequently proved a direct, session-reusing call with
`k8s_get_resources`; this is auxiliary server evidence only and does not prove
L4 or L6. See `evidence/kagent/educational-practice-phase-5b-direct-mcp.md`.

## How To Use What Exists Today

### Fast path: host-level browser automation

Use this when you want the stable part of the repo:

```powershell
.\scripts\install-global-playwright-mcp.ps1
.\scripts\verify-global-playwright-mcp.ps1
codex mcp list
```

Then work through:

1. `docs/01-MCP-MENTAL-MODEL.md`
2. `docs/runbooks/local-playwright-lab.md`
3. `docs/runbooks/remote-playwright-lab.md`

### Local kagent path

Use this when you want the current cluster-based learning path:

1. Read `docs/runbooks/local-kagent-a2a-lab.md`
2. Confirm the `docker-desktop` context
3. Confirm the `kagent` namespace workloads
4. Port-forward the UI service
5. Open `http://localhost:8080`
6. Inspect `kubectl get agent -n kagent`
7. Run `python scripts/kagent/test-a2a-agent.py card` to validate A2A agent card

Useful commands:

```powershell
kubectl config current-context
kubectl get pods -n kagent
kubectl get agent -n kagent
kubectl port-forward -n kagent svc/kagent-ui 8080:8080
curl.exe -s -o NUL -w "%{http_code}" http://localhost:8080
```

### Review and validation path

Use this when you are changing configuration or docs:

```powershell
.\scripts\verify-global-playwright-mcp.ps1
pwsh -ExecutionPolicy Bypass -File scripts\kubernetes\validate.ps1 -Strict
pwsh -ExecutionPolicy Bypass -File scripts\evaluation\run-evaluation.ps1
```

## Known Gaps

### Stable and repeatable

- global Playwright host registration
- local Playwright learning path
- remote browser Docker scaffold
- multi-host documentation and templates
- local kagent cluster health and agent acceptance

### Working but still rough

- release acceptance evidence for `laptop-stable-v0.1.1` still needs an exact green GitHub Actions run recorded against the release SHA
- integration scaffold verification reports findings but does not yet fail CI truthfully for every detected failure
- PyYAML/Python dependency behavior needs one documented contract across code, tests, README, and the acceptance plan
- local `kagent` installation path (not yet reduced to a one-command install flow)
- A2A dispatch uses the pinned controller 0.9.11 `message/stream` SSE path;
  legacy blocking `tasks/sendTask` and `message/send` remain unsuitable
- native read-only MCP tool exposure; the current pinned image relies on RBAC for write denial
- live correlated L6 tool observation (schema/helper exist; live still Not proven)
- the deployed controller's client-facing MCP discovery schema has not yet been
  recorded, so native Cursor/Codex agent integration remains an acceptance task
- agent-governance R1-R3/S1-S2 benchmark scoring and H1-H3 shadow measurement;
  artifacts exist, but no independently assessed comparison or ten-event hook
  sample supports promotion or blocking yet

### Not yet closed

- L6 agent-mediated MCP invocation (live tool marker + kubectl match)
- Cursor and Codex discovery, minimal dispatch, and correlated read-only
  acceptance through the controller's MCP endpoint
- L7 bootstrap, cleanup, and fresh-install evidence
- root `docs/01-*.md`–`docs/07-*.md` stubs remain as compatibility redirects; full removal pending consumer bookmark updates

## Practical Roadmap

The stable Playwright release lane remains the first priority for any release
work. The kagent lane below applies when that stable work is explicitly out of
scope. Detailed educational phase ownership, commands, and promotion gates are
kept in the [kagent educational roadmap](KAGENT-EDUCATIONAL-ROADMAP.md).

| Order | Kagent outcome | Depends on | Completion evidence |
|-------|----------------|------------|---------------------|
| 1 | **Integrity and protocol hardening** — repair strict missing-CRD exit semantics, multiline SSE parsing, local-debug-log hygiene, and current-head CI truthfulness. | Existing deterministic test suites | Regression cases pass and any hosted status is recorded for the exact head. |
| 2 | **Read-only surface and L6 closure** — make mutation tools absent from discovery, then diagnose and prove one correlated agent-mediated Kubernetes read. | 1 | Native read-only schema plus fresh `agent_mcp_trace.py` exit 0 and a `kubectl` match. |
| 3 | **Native IDE acceptance** — inspect the controller MCP schema; if it exposes suitable agent tools, configure project-scoped Cursor and Codex clients instead of building a new bridge. Basic discovery and no-tool dispatch can run after 1, alongside 2. | 1 | Dated discovery and minimal-dispatch records, with the actual tools recorded. |
| 4 | **IDE-to-Kubernetes correlation** — invoke the already proven read-only path from each IDE and retain same-task correlation. | 2 and 3 | Cursor and Codex records each bind an IDE invocation to the tool result and matching `kubectl` output. |
| 5 | **Repeatable workshop (L7)** — provide bootstrap, port-forward, configuration-template, acceptance, cleanup, and fresh-install proof. | 4 | A clean Docker Desktop run completes without undocumented repair and cleanup is verified. |

### Architecture decision for the IDE lane

Do not plan a custom Cursor/Codex-to-A2A bridge before checking the running
controller's native MCP endpoint. The deployed local controller is pinned to
`0.9.11` and its service exposes port `8083`; the next acceptance record must
perform MCP `initialize` and `tools/list` and preserve the returned schema. If
the expected agent discovery and invocation tools are present, use that surface
as the thin integration layer. If not, record the gap before evaluating an
adapter.

The initial operating contract is intentionally narrow:

- one of Cursor or Codex is the lead repository agent for a task;
- kagent receives bounded, read-only Kubernetes investigations only;
- tool-derived kagent output is labelled as such and repository edits remain
  with the lead agent; and
- any cluster mutation needs a future write-enabled profile and explicit human
  confirmation.

Reverse delegation from kagent to native Cursor/Codex agents, global installer
integration, and autonomous cluster mutation are deferred. They do not block
L6 or L7.

## Recommended Next Steps

1. Complete the two deterministic integrity repairs before treating strict
   health or streaming results as dependable gates.
2. Replace the mutation-advertising runtime before requesting an agent to use
   Kubernetes tools.
3. Capture the single live L6 record, while independently recording controller
   MCP discovery and a no-tool IDE dispatch if the endpoint supports it.
4. Build bootstrap and cleanup automation only after the full read-only IDE
   path has correlated evidence.
