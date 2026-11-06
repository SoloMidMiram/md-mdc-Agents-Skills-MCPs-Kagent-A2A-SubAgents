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

### Context-first priority and runner gate — 2026-11-06

The selected priority is a measurable context-first coding assistant. See
[North Star](../north-star.md) for direction; this document retains cross-lane
ordering. A2A-first remains the dated educational direction, not the current
product spine. No L/I capability is promoted by this priority change.

- **Draft implementation:** #17 at `fe3aea3f0aba9ea2cd040194dd898c91391b3240`
  repairs schema 1.0 packet integrity; #18 at
  `caa7d80e8512bc886c98393e322fc3df7f1f8ea2` provides runnable labs and a frozen
  pilot. Hosted checks qualify their tested scope, not merge readiness.
- **Locally verified demonstrations:** six-source packet replay and synthetic
  fail-closed controls. [Results](../../reports/context-labs-01-results.md)
  preserve actual results and limitations; these are not coding-improvement data.
- **Immediate prerequisite:** LAB-RUNNER-01 security qualification, then one
  non-scored experimental smoke, then nine frozen EVAL-01 cells. SoloMidMiram
  owns provisioning/isolation/teardown. The virtual server is only a placeholder;
  see [provisioning specification](../architecture/LAB-RUNNER-01-PROVISIONING.md).
- **Blocked:** real execution environment, authentication, network/filesystem
  restrictions, exact launch identity and teardown proof. No smoke/model calls
  or scored coding results exist; no performance benefit is claimed.
- **Deferred:** snapshots, ranking/discovery, Context7 and further kagent feature
  expansion until the current runner/evaluation gates are qualified.

Integration remains #16 → #9 → main, then reconciliation of the independent
#10 → #13 → #17 → #18 stack. Preserve review history and requalify changed
parents. Independent human review and maintainer acceptance remain open.

Authority and freshness are separate: code/tests govern behavior at named
revisions; dated evidence governs its observed environment/time; direction
documents select priorities. A newer summary cannot strengthen an older result.

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
  exact pre-merge head `94031ff`. That revision is now part of merged PR #1
  and remains historical CI context rather than an active merge gate.
- fail-closed Kubernetes manifest validation (`scripts/kubernetes/validate.ps1
  -Strict`) and Trivy policy scanning (`scripts/security/scan.ps1 -Required`)
  with pinned validator installation (kubeconform v0.6.7, kube-linter v0.7.1,
  Trivy v0.72.0) and deterministic Pester failure-path tests
  (`KagentToolingValidation.Tests.ps1`). Those jobs passed in hosted Quality run
  30621076867 at `f18b906`, including the required Trivy policy scan.
- `kagent-controller` REST API exposes agent card on port 8083
- PR2 gateway slice: `deploy/samples/kagent/litellm-gateway-model-config.yaml`
  points kagent only at LiteLLM `http://host.docker.internal:4000/v1`, alias
  `agent-coder`, and Secret key `LITELLM_MASTER_KEY`; the no-tool smoke agent is
  isolated in `deploy/samples/kagent/litellm-gateway-smoke-agent.yaml`
- dated runtime evidence proves LiteLLM `/v1/models`, chat completion, and a
  non-empty kagent response through `agent-coder`; the retained card gate is
  still missing and `read_file` remains a later tool-enabled slice

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

The parallel native IDE track is I0-I2 Proven, I3 Blocked, I4 Not proven, and
I5 Not attempted. I3-Cursor remains Blocked — see `evidence/kagent/README.md`
for the current failure stage, dated evidence, and next acceptance action. The
authoritative decision and blocker wording live there.

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
- current-head baseline hygiene is in place locally (`pyyaml==6.0.3` direct in the `dev` group; coverage/quality paths target `scripts/kagent`; quality wrappers fail-closed); selecting the immutable release SHA and recording same-SHA hosted Quality remain open. Full-quality debt (Mypy, coverage below 80%, Bandit Low findings, and a 2026-08-01 pip-audit timeout) is recorded in `docs/laptop-stable-acceptance-plan.md` and is not a Gate 0 pass claim
- local `kagent` installation path (not yet reduced to a one-command install flow)
- A2A dispatch uses the pinned controller 0.9.11 `message/stream` SSE path;
  legacy blocking `tasks/sendTask` and `message/send` remain unsuitable
- native read-only MCP tool exposure; the current pinned image relies on RBAC for write denial
- live correlated L6 tool observation (schema/helper exist; live still Not proven)
- IDE-to-A2A correlation capture: `agent_mcp_trace.py` currently creates its own
  direct A2A task, so running it beside Cursor cannot prove that Cursor caused
  that same task; Phase 7C needs an external-invocation evidence mode or another
  fail-closed join before I4 can be reviewed
- the deployed controller's client-facing MCP schema is recorded: `/mcp` exposes
  only `list_agents` and `invoke_agent`, and `k8s-a2a-agent` is discoverable
  (I0-I2 Proven); Candidate B strict preflight is recorded, while the current
  I3-Cursor decision and remaining live-evidence gate are maintained in
  `evidence/kagent/README.md`
- the PR2 gateway record still needs one retained `both` capture containing the
  agent card result before the full five-gate single-agent acceptance can be
  marked complete
- agent-governance R1-R3/S1-S2 benchmark scoring and H1-H3 shadow measurement;
  artifacts exist, but no independently assessed comparison or ten-event hook
  sample supports promotion or blocking yet

### Not yet closed

- L6 agent-mediated MCP invocation (live tool marker + kubectl match)
- successful bounded Cursor/Codex delegation and correlated read-only acceptance
  through the controller's MCP endpoint
- L7 bootstrap, cleanup, and fresh-install evidence
- root `docs/01-*.md`–`docs/07-*.md` stubs remain as compatibility redirects; full removal pending consumer bookmark updates

## Practical Roadmap

This table coordinates repository delivery. The stable release checklist owns
release mechanics, the kagent educational roadmap owns detailed phase/PR work,
and the evidence index owns capability decisions. Proposed PR numbers below are
planning units and do not assert that a hosted PR exists.

| Order | Delivery unit | State | Depends on | Completion evidence |
|-------|---------------|-------|------------|---------------------|
| 0 | **Current-head release baseline** — select one immutable release SHA and run the full hosted workflow from `docs/laptop-stable-acceptance-plan.md`. | Open | Existing deterministic suites | Candidate SHA, local results, and same-SHA hosted Quality are recorded. |
| 1 | **Stable Playwright patch release** — complete Windows install → verify → rollback → verify and tag `laptop-stable-v0.1.1`. | Open | 0 | Target-host acceptance and exact-SHA hosted Quality pass; the tag points to that SHA. |
| 2 | **Kagent Delivery Gate 0 / roadmap-baseline publication** — preserved the six coherent documentation updates on the PR #3 branch before Phase 7 implementation. | **Published** at `090ad52` (`docs(kagent): harden remaining phase and PR roadmap`); no capability decision changes | Six-file roadmap diff, empty staging area, clean required validation, and preceding test harden `178ce58` | Pushed SHA `090ad52` with exact-SHA `quality.yml` green: push run [30979059299](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/actions/runs/30979059299) and pull_request run [30979061019](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/actions/runs/30979061019); no capability decision changes. |
| 3 | RECON-01 / federation and gateway integration | Local rehearsal only | Verified hosted heads | Stable IDs, preserved evidence, cloud-only examples, exact candidate checks. |
| 4 | EVID-01 / evidence integrity | Active | RECON-01 | Negative regressions and validated recorder/harness; no capability promotion. |
| 5 | A2A-01 / pinned SDK validation | Next | EVID-01 | SDK 0.3.26 isolated tests, then bounded live result or Blocked record. |
| 6 | CTX-01 / cited context; SAFE-01 / exact MCP surface | Planned | EVID-01; A2A-01 for transport | Source-linked context; exact server-side safety before tools. |
| 7 | WORKER-01, EVAL-01, OPS-01 | Planned | Validated contracts and required safety | Bounded worker, comparable measurements, owned cleanup. |

North Star's A2A-first direction supersedes Cursor-I3-first ordering. I3 remains
Blocked and proceeds independently; I4 still requires I3 plus same-invocation
L6 evidence. See [integration workstreams](../reference/integration-workstreams.md)
for historical proposed-number mappings. No cluster mutation is authorized here.

### Architecture decision for the IDE lane

The deployed local controller is pinned to `0.9.11`; its native `/mcp` endpoint
was recorded at `http://127.0.0.1:8083/mcp` with exactly `list_agents` and
`invoke_agent`. Use that surface as the only IDE-facing integration layer.
Do not build a custom Cursor/Codex-to-A2A bridge unless a future dated live
record establishes that the pinned native contract cannot satisfy a required
capability.

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

1. Complete the remaining current-head checklist items: name one immutable
   candidate SHA, record local deterministic results for it, and trigger full
   `quality.yml` for that exact SHA (PyYAML and coverage contracts are already
   declared).
2. Perform the Windows acceptance round trip against that SHA and tag
   `laptop-stable-v0.1.1` only if every required gate passes.
3. Gate 0 is published at `090ad52` (`docs(kagent): harden remaining phase
   and PR roadmap`) with exact-SHA `quality.yml` green on both the push and
   pull_request runs. Any later I3 evidence commit creates a new final SHA and
   needs its own hosted run.
4. Complete RECON-01, then EVID-01 and A2A-01. Preserve the independent
   Cursor I3 blocker; do not make it the prerequisite for A2A education.
5. Follow stable workstream dependencies for CTX-01, SAFE-01, WORKER-01,
   EVAL-01, and OPS-01. Direct MCP and separate helper tasks do not prove I4.
