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
  test invocation; a green
  hosted run against the committed workflow is still pending
- fail-closed Kubernetes manifest validation (`scripts/kubernetes/validate.ps1
  -Strict`) and Trivy policy scanning (`scripts/security/scan.ps1 -Required`)
  with pinned validator installation (kubeconform v0.6.7, kube-linter v0.7.1,
  Trivy v0.61.1) and deterministic Pester failure-path tests
  (`KagentToolingValidation.Tests.ps1`); a green hosted run against the
  committed workflow is still pending
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
- agent-governance R1-R3/S1-S2 benchmark scoring and H1-H3 shadow measurement;
  artifacts exist, but no independently assessed comparison or ten-event hook
  sample supports promotion or blocking yet

### Not yet closed

- L6 agent-mediated MCP invocation (live tool marker + kubectl match)
- L7 bootstrap, cleanup, and fresh-install evidence
- root `docs/01-*.md`–`docs/07-*.md` stubs remain as compatibility redirects; full removal pending consumer bookmark updates

## Practical Roadmap

The order below is the project priority order. Do not move a later lab phase
ahead of the release-truthfulness work unless the stable Playwright lane is
explicitly out of scope for that change.

### Phase 0: Release truthfulness (immediate blocker)

Goal: make the `laptop-stable-v0.1.1` release evidence match what CI and the
repository can actually prove.

Why this comes first: the stable path is the current usable product. It should
not be tagged until every release gate can fail truthfully and the exact release
commit has a green workflow run.

Jobs:

1. Fix `scripts/integrations/verify-integration-scaffold.ps1` so every detected hard failure is accumulated and exits non-zero.
2. Replace the staged-only secret scan with a scan over tracked repository files or a dedicated scanner such as Gitleaks.
3. Align the PyYAML/Python dependency contract across code, tests, README, and `docs/laptop-stable-acceptance-plan.md`.
4. Push the corrected release commit and confirm `quality.yml` passes for that exact SHA.
5. Record the workflow evidence and release SHA in `docs/laptop-stable-acceptance-plan.md`.
6. Tag `laptop-stable-v0.1.1` only after the acceptance plan contains that evidence.

Exit evidence:

- `verify-integration-scaffold.ps1` returns exit code 1 when required files, required Playwright entries, invalid config, or hard policy checks fail.
- Secret scanning covers committed repository content, not only staged local files.
- The dependency behavior documented in the acceptance plan matches installer behavior.
- A green GitHub Actions run exists for the exact release commit.
- The acceptance plan links or records the successful run and commit SHA.

### Phase 1: A2A task dispatch

Goal: separate card inspection, protocol probing, and real task dispatch into
truthful gates.

Why this comes second: the local kagent lab already proves cluster health and
agent acceptance. The next useful capability is proving whether a task can cross
the A2A boundary.

Jobs:

1. (DONE) Make `task` fail for unavailable dispatch and keep `probe` neutral.
2. (DONE) Keep `card` scoped to validated REST details and make `both` require card plus task success.
3. (DONE) Select and pin controller 0.9.11 `message/stream` with SSE dispatch.
4. (DONE) Record a successful request and strictly validated status-update
   response before documenting the working L4 flow.

Exit evidence:

- `card` passes when the agent card/details are reachable and the agent is accepted/ready.
- `probe` reports method support without being used as a dispatch success gate.
- `task` fails for `-32601` and passes only when a task is accepted or completed.
- The runbook shows the exact command and expected successful response shape.

### Phase 2: Real MCP execution behind kagent

Goal: move from accepted agents to real MCP-backed tool execution.

Why this comes third: RemoteMCPServer acceptance and tool invocation should be
tested only after task dispatch semantics are truthful.

Jobs:

1. (DONE) Deploy a lightweight MCP server behind the `kagent-tool-server` service.
2. (DONE) Make `RemoteMCPServer/kagent-tool-server` reach `Accepted=True`.
3. (DONE) Add capability-gated health profiles (`CardLab`, `DirectMcpServer`,
   `A2ADispatch`, `FullMcpExecution`) with deterministic tests and live phase 5c
   evidence. Direct MCP success does not satisfy FullMcpExecution.
4. (DONE) Structured A2A output and exact L4 response-shape validation
   (phase 5d).
5. (DONE) Nested agent-mediated evidence schema, `agent_mcp_trace.py`, and
   single-task FullMcpExecution gates (phase 5e), including observed-target,
   freshness, source-content, tool-argument, result-array, and exit agreement.
   Live L6 remains Not proven.
6. Prove one live end-to-end path: task reaches agent, agent invokes a real MCP
   tool, and kubectl-matched names return through the correlated task.

Exit evidence:

- `kubectl get remotemcpserver -n kagent` shows the target server accepted.
- The health checker FullMcpExecution profile fails truthfully until live
  correlated agent-mediated evidence exists.
- A recorded command shows an A2A task invoking one real MCP tool through the
  agent path (`agent_mcp_trace.py` exit 0).

### Phase 3: Repeatable kagent install

Goal: turn the current local lab into a reproducible setup.

Why this comes fourth: bootstrap automation is useful, but it should automate a
known-good flow after dispatch and execution requirements are clearer.

Jobs:

1. Reduce the local `kagent` path to a one-command install from a known Helm chart version.
2. Pin known-good kagent, Helm chart, CRD, and sample manifest versions.
3. Add a bootstrap script that verifies the `docker-desktop` context, installs CRDs/controller/UI, and deploys the base and sample manifests predictably.
4. (DONE) Improve `scripts/kagent/check-kagent-health.ps1` with profiles
   `CardLab`, `DirectMcpServer`, `A2ADispatch`, and `FullMcpExecution`
   (`scripts/kagent/KagentHealth.psm1`).
5. (DONE) Fix pod readiness parsing so valid multi-container readiness such as `2/2` is accepted instead of only matching `1/1`.
6. Document rollback or cleanup steps for the local cluster lab.

Exit evidence:

- A fresh Docker Desktop Kubernetes context can reach the documented kagent state through the bootstrap path.
- The health checker profile selected in the runbook matches the user's current lab goal.
- Pod readiness checks compare ready and total container counts numerically.

### Phase 4: Repository stabilization

Goal: reduce documentation drift and make the repo easier to trust as it grows.

Why this comes last: it should consolidate proven behavior and current
priorities, not replace missing executable evidence.

Jobs:

1. (DONE) Define placement and maintenance rules in `docs/DOCUMENTATION-ORGANIZATION.md`.
2. (DONE) Create canonical L0-L7 definitions in `docs/reference/kagent-capability-matrix.md`.
3. (DONE) Create `evidence/kagent/README.md` as the current status and ranked flaw ledger.
4. (DONE) Define stable-core isolation and promotion rules for both educational lanes in `docs/architecture/EDUCATIONAL-LANES-ARCHITECTURE.md`.
5. (DONE) Add a shared problem manual, reflection template, and educational-project entry map.
6. (DONE locally; hosted confirmation pending) Add locked deterministic kagent
   Python checks, pin Pester, and explicitly run the kagent PowerShell suite in
   the quality workflow.
7. (DONE locally; hosted confirmation pending) Add fail-closed, pinned
   Kubernetes manifest and Trivy policy validation to hosted CI, with
   deterministic failure-path tests.
8. Keep `README.md` short and current-state oriented.
9. Update or demote stale architecture docs so authoritative files describe current structure or clearly mark target-only content.
10. Add automated validation for `REPO_MANIFEST.yaml`: path existence, allowed purpose/status values, authority consistency, and historical files not marked authoritative.
11. Continue replacing duplicated runtime snapshots with canonical evidence links.
12. Retire root compatibility stubs only after consumers update bookmarks.

Exit evidence:

- Manifest validation runs locally or in CI.
- The architecture plan is either current and authoritative or explicitly historical/target-only.
- The maturity matrix reflects the same stable/lab/planned boundaries as the README and this roadmap.
- Root compatibility stubs are removed only after their consumers have a replacement path.

## Recommended Next Steps

If the goal is immediate usefulness:

1. finish Phase 0 before tagging `laptop-stable-v0.1.1`
2. keep using the Playwright host setup as the stable path
3. use `docs/runbooks/local-kagent-a2a-lab.md` for the active cluster lab
4. run `scripts/kagent/check-kagent-health.ps1` to verify cluster health
5. use `python scripts/kagent/test-a2a-agent.py card` to validate the A2A agent card

If the goal is repo scalability:

1. complete the evidence-producing phases before adding another planning layer
2. update or demote stale architecture docs
3. add manifest and maturity-matrix validation
4. stop adding new behavior to historical plan documents
