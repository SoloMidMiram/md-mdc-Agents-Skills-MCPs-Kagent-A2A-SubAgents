# kagent Educational Roadmap

This document is a learning path for the local `kagent` lab. **Project direction**
is defined in [Project North Star](../north-star.md) (2026-08-07): prove A2A
workflows first; Cursor I3 is interoperability proof, not the education spine.

It separates what you can observe today from what still requires A2A dispatch and
real MCP-backed tool execution.

It is intentionally educational. The project-wide engineering roadmap remains in
`docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md`.

Canonical supporting documents:

- **north star:** `docs/north-star.md`
- educational-lane boundary: `docs/architecture/EDUCATIONAL-LANES-ARCHITECTURE.md`
- problem workflow: `docs/runbooks/educational-problem-manual.md`
- capability definitions: `docs/reference/kagent-capability-matrix.md`
- current evidence/status: `evidence/kagent/README.md`
- E1–E5 examples: `docs/runbooks/kagent-a2a-examples.md`
- documentation placement rules: `docs/DOCUMENTATION-ORGANIZATION.md`

## Where You Are Now

The canonical status is maintained in
[the kagent evidence index](../../evidence/kagent/README.md), not in this
roadmap. At the current checkpoint:

- L0-L5 and I0-I2 are Proven;
- Candidate B passed the strict controller preflight;
- I3 remains Blocked at Cursor tool discovery (`tool_discovery` /
  `KAGENT_MCP_TOOLS_NOT_EXPOSED`) — **interop proof, not an education gate**;
- L6, L7, and I4 remain Not proven; I5 remains Not attempted; and
- direct MCP success remains server evidence only.

**Immediate priority (2026-08-07):** Lane A A2A education — execute E1
(planner-only) and E2 (supervisor → planner → reviewer) after PR #3 merges.
I3 close-out continues in Lane C as a parallel interoperability track.

Use this distinction throughout the lab: an accepted agent, a passing controller
helper, and a tool-invoking agent are three different evidence claims.

## Phase 2 / PR2 — LiteLLM gateway checkpoint (2026-08-20)

This is intentionally smaller than the later A2A education and MCP tool-loop
work. The gateway registry remains owned and frozen in the adjacent LLMLite
repository; MCPtest consumes the `agent-coder` alias through one kagent
`ModelConfig`.

| Slice | Status | Evidence or boundary |
|---|---|---|
| Architecture separation | **Done** | `docs/north-star.md` and lane architecture |
| Contract docs | **Done** | capability matrix, documentation ownership, runbook |
| Schema draft | **Done** | LLMLite-owned `models/gateway_manifest.yaml` v1.2 |
| Gateway runtime | **Proven** | LiteLLM `/v1/models` and chat probe returned HTTP 200 |
| kagent → LiteLLM | **Proven for gateway path** | `agent-coder` returned a non-empty response through the no-tool smoke agent |
| Single-agent file review | **Later** | `read_file` is a separate tool-enabled slice, not PR2 |
| A2A / multiple agents | **Later** | No Agent-tool delegation in PR2 |
| Local models | **Frozen** | Cloud-only `agent-coder`; no fallback to Ollama |

The retained PR2 record does not contain the agent-card result (`card.accepted`
and `card.deploymentReady` are null in the helper capture). The gateway/model
success is therefore proven, but the complete five-gate single-agent acceptance
must not be called complete until a `both` run captures the card and task in one
record. Use [the PR2 gateway runbook](../runbooks/kagent-litellm-gateway.md).

## Single-tool slice — tool-loop evidence gate (2026-08-21)

The one-tool slice (`litellm-gateway-tool-agent` + `k8s_get_resources`) only
proves what the retained evidence actually observed. The evidence helper
(`capture-a2a-evidence.py`) now fails closed: a run passes only when the stream
reaches `completed`, yields a non-empty final answer, **and** contains at least
one tool call whose `id` exactly matches a tool result `id`
(`matched_tool_pairs >= 1`). Completion plus non-empty text alone is no longer
sufficient. This does **not** promote L6, which remains Not proven until a
direct A2A task → `k8s_get_resources` → same-task returned names → `kubectl`
match is evidenced.

| Gate | Tool-loop run001 |
|---|---|
| Tool invoked (exact call/result pair) | Proven (`matched_tool_pairs=1`) |
| Agent answered after the tool | Proven |
| L6 promotion | Not proven (direct A2A→MCP→kubectl correlation still required) |

## Hardened Implementation Roadmap

The target is an **A2A educational core** with measured multi-agent workflows,
read-only tool execution when needed, and later Cursor/Codex comparative evaluation.

```text
A2A educational core (planner, reviewer, supervisor, docs agents)
  ├─ Cursor interoperability (client under test, not gatekeeper)
  ├─ Codex interoperability (first coding worker)
  └─ worker/orchestrator experiments
→ read-only tool execution (Lane S)
→ measured multi-agent workflows (Lane A)
→ Cursor/Codex comparative evaluation (Lanes C, B)
```

**Current integration model** (not Cursor ←A2A→ Codex initially):

```text
Cursor or Codex (optional, later)
  -> kagent controller /mcp (when used)
  -> list_agents / invoke_agent
  -> kagent A2A agents (planner, reviewer, supervisor, docs)
  -> optional approved read-only MCP tool
  -> measured workflow output
```

DeepSeek inside kagent powers planner/reviewer/docs/supervisor roles. Codex is
the first automatable external coding worker (PR #7). Cursor is an interactive
northbound client; I3 remains Blocked and does not block Lane A.

No custom IDE-to-A2A bridge is planned. A new gateway is allowed only after a
dated compatibility record proves that the native controller contract cannot
satisfy a required gate.

### Delivery Gate 0 — publish the roadmap baseline

This was a publication gate, not the historical `phase_0_observe` learning
phase. It preserved the six-document roadmap correction on the
`feat/kagent-native-mcp-federation` branch before Phase 7 implementation.

Published commit:

```text
docs(kagent): harden remaining phase and PR roadmap
```

The coherent commit contained exactly:

- `README.md`;
- `docs/onboarding/GETTING-STARTED.md`;
- `docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md`;
- `docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md`;
- `docs/runbooks/local-kagent-a2a-lab.md`; and
- `evidence/kagent/README.md`.

The authorized publication sequence was:

```powershell
git status --short
git diff --check
uv run ruff check scripts/kagent tests/kagent
uv run pytest -q tests/kagent
pwsh -NoProfile -File `
  .agents/skills/sync-educational-slice/scripts/audit-slice.ps1 `
  -RepoRoot . -RequireEmptyStaging
git add README.md `
  docs/onboarding/GETTING-STARTED.md `
  docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md `
  docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md `
  docs/runbooks/local-kagent-a2a-lab.md `
  evidence/kagent/README.md
git commit -m "docs(kagent): harden remaining phase and PR roadmap"
git push
```

Before publication, Gate 0 required `git diff --check`, Ruff, the deterministic
kagent pytest suite, the documentation ownership/link audit, and an empty
staging-area check before intentional staging. Staging, committing, pushing,
and updating the hosted PR required explicit user authorization.

**Published:** Gate 0 completed at `090ad52` on 2026-08-05
(`docs(kagent): harden remaining phase and PR roadmap`), preceded by test
harden `178ce58` (`test(kagent): stabilize Windows redirect loopback
fixture`). Exact-SHA `quality.yml` passed on both the push run
[30979059299](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/actions/runs/30979059299)
and the pull_request run
[30979061019](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/actions/runs/30979061019).
The green baseline run does not replace the final post-I3 evidence run, and it
promotes no capability: I3 remains Blocked until the human Cursor trace
qualifies or a dated Blocked addendum records the reason.

### Dependency and safety chain (revised 2026-08-07)

```text
Delivery Gate 0 (published)
  |
  +-- PR #3 / Phase 6: federation foundation (I0-I2; I3 Blocked recorded)
  |
  +-- PR #4 / Lane A: A2A role examples              |
  |                                                  |
  +-- PR #5 / Lane S: read-only MCP surface --------+
          |                                          |
          +-- PR #6 / Lane B: benchmarks + OTel      |
          |         |                                |
          |         +-- PR #7: Codex worker adapter  |
          |         +-- PR #8: Cursor interop spike  |
          |                                          |
          +-- PR #9: telegram capstone <-------------+
```

Lane A (PR #4) may start after PR #3 without waiting for I3, L6, or I4.
PR #4 (education) and PR #5 (safety) may proceed in parallel after #3.
PR #9 depends on PR #5 and PR #7.

For one operator, preferred execution order after PR #3: **#4 → #6 → #7 → #9**,
with **#5** and **#8** in parallel where safe. I3/L6/I4 close-out remains in
Lane C as deferred capability experiments — see
[Deferred capability experiments](#deferred-capability-experiments-l6-i3-i4).

The proposed PR numbers are delivery units, not claims that hosted PRs already
exist. Each unit must remain independently reviewable.

| Delivery unit | Branch | State | Entry gate | Exit gate | Explicit non-claim |
|---------------|--------|-------|------------|-----------|--------------------|
| PR #3 / Phase 6 | `feat/kagent-native-mcp-federation` | Active — merge foundation | Gate 0 published; I0-I2 proven | I0-I2 evidenced; I3 Blocked recorded accurately; final SHA passes `quality.yml` | **Do not mark I3 Proven**; code merged ≠ capability proven |
| PR #4 / Lane A | `edu/kagent-a2a-role-examples` | Active | PR #3 merged | Planner, reviewer, supervisor manifests; E1–E2 runnable | Does not prove MCP tools, I3, I4, or L6 |
| PR #5 / Lane S | `feat/kagent-readonly-mcp-surface` | Planned | PR #3 merged | Default-deny discovery; only `k8s_get_resources`; RBAC least privilege | Does not prove I3, I4, L6, or A2A education |
| PR #6 / Lane B | `eval/kagent-a2a-benchmarks` | Planned | PR #4 | Harness + OTel + baselines B0–B8 | Does not promote L6/I4 by itself |
| PR #7 / Lane A/C | `feat/codex-worker-adapter` | Planned | PR #4, #6 | Codex local runner bridges planner→worker→reviewer (E4 subset) | Codex is not initially an A2A peer agent |
| PR #8 / Lane C | `spike/cursor-worker-interop` | Planned | PR #4, #6 | Cursor client vs worker decision documented | Does not require I3 Proven |
| PR #9 / capstone | `edu/telegram-orchestrated-capstone` | Planned | PR #5, PR #7 | E5 full workflow with evidence | Production readiness |

### PR #3 / Phase 6 — federation foundation (governance addendum 2026-08-07)

PR #3 delivers native federation foundation code and honest capability records:

- **Merge when:** I0–I2 are proven and I3-Cursor Blocked is recorded accurately.
- **Do not mark I3 Proven** on merge. I3 acceptance moves to a future Lane C PR.
- I3 human trace capture remains valuable interoperability evidence but is **not**
  a merge blocker for Lane A education.

Historical no-tool I3 close-out procedure (when pursued in Lane C):

1. Use the qualified Candidate B profile and controller port-forward per runbook.
2. Capture sanitized proof: inventory, `context_id` presence, second-call forwarding.
3. Run postflight; restore default profile; stop owned port-forward processes.
4. Append a dated evidence addendum; never rewrite earlier observations.

Close-out remains binary: qualifying trace → I3 promotion **review**; or dated
Blocked addendum. Either result leaves I4, L6, I5, and L7 unchanged unless
separately evidenced.

### Proposed PR #5 / Lane S — make read-only discovery intrinsic

Start with a bounded implementation spike. Inspect candidate runtime help and
live `tools/list`; do not assume a flag or image is safe from its name. Select
the smallest maintainable option in this order:

1. a pinned upstream runtime that natively exposes an exact allowlist;
2. a small default-deny filtering MCP facade in front of the pinned runtime; or
3. a minimal lab server implementing only the required read operation.

For the first example, discovery should expose only `k8s_get_resources`.
Extend `mcp_session_smoke.py` or add a similarly bounded inventory mode so the
test can compare the complete paginated tool set, not merely find one expected
tool. Fail on any extra tool and on mutation-oriented names such as `create`,
`update`, `patch`, `delete`, `apply`, `exec`, `scale`, `rollout`, `cordon`, or
`drain`.

Defer `k8s_get_available_api_resources`, `k8s_describe_resource`,
`k8s_get_events`, and `k8s_get_pod_logs` until the one-tool path is proven.
Each later addition needs its own schema review, inventory update, RBAC review,
negative tests, and bounded live evidence; it is not inherited automatically
from the first tool.

Keep Kubernetes authorization as defense in depth. Reduce the current broad
read-only ClusterRole toward the resources, verbs, and namespace needed by the
pod-listing demo when the selected runtime permits it; document any unavoidable
cluster-scoped discovery access. Verify negative permissions with
`kubectl auth can-i` and retain strict manifest and required security scans.

Phase 7A completion requires deterministic tests, one live exact inventory,
restrictive RBAC, a dated safety record, and a final pushed SHA with hosted
Quality. Tool discovery hardening alone promotes no capability.

### Proposed PR #4 / Lane A — A2A role examples (E1–E3)

Deliver educational agent manifests and harness stubs under
`deploy/samples/kagent-a2a/` and `scripts/kagent/experiments/`:

- **E1:** planner-only A2A (human → planner)
- **E2:** supervisor → planner → reviewer (agent-as-tool)
- **E3:** docs validator with sanitized repo bundle

Runbook: `docs/runbooks/kagent-a2a-examples.md`. DeepSeek inside kagent powers
in-cluster roles. No Cursor/Codex required for E1–E2.

Exit gate: E1 and E2 execute with dated evidence in
`evidence/kagent/experiments/`; deterministic offline tests pass.

### Proposed PR #6 / Lane B — benchmarks and observability

Implement `benchmark_a2a.py` and `collect_trace.py` with baselines B0–B8 and
metrics documented in [Project North Star](../north-star.md). Export kagent OTel
to Jaeger with separate client/controller/A2A/agent/LLM/tool latency.

Exit gate: at least B0–B3 paired runs recorded; harness is deterministic offline.

### Proposed PR #7 / Lane A/C — Codex worker adapter

Bridge in-cluster planner/reviewer to an out-of-cluster Codex local runner for
E4 (planner → Codex → reviewer). Codex is invoked via adapter, not as an initial
A2A peer. Benchmark baseline B5.

Exit gate: one measured E4 subset with dated evidence; adapter fail-closed on
missing worker.

### Proposed PR #8 / Lane C — Cursor interop spike

Evaluate Cursor as northbound client vs potential worker role. I3 Blocked status
may persist; spike documents decision without requiring symmetry with Codex.

### Proposed PR #9 — telegram capstone (E5)

Full E5 workflow after read-only MCP (PR #4) and Codex worker (PR #7).

### Deferred capability experiments (L6, I3, I4)

These remain **strict, separate experiments**. They do not block Lane A education.

#### L6 — direct A2A tool proof (formerly PR #5 / Phase 7B)

Use a tool-enabled agent profile. The Candidate B I3 `systemMessage` forbids
tool calls and must not leak into this phase. Keep the transaction fixed to:

```text
message/stream
  -> kagent/k8s-a2a-agent
  -> kagent-tool-server / k8s_get_resources
  -> resourceType=pod, namespace=kagent
  -> pod names returned through the same A2A task
  -> independent kubectl name match
```

The existing `agent_mcp_trace.py` producer is appropriate for this L6 gate
because it owns the direct A2A dispatch and correlates its own task. One fresh
exit 0 is the promotion threshold; three consecutive successes are recommended
only as an operational-confidence check. Preserve failed attempts and add a new
dated record rather than editing Phase 5E history.

Command shape:

```powershell
python scripts/kagent/agent_mcp_trace.py `
  --controller http://127.0.0.1:8083 `
  --output json

kubectl get pods -n kagent `
  -o jsonpath="{range .items[*]}{.metadata.name}{'\n'}{end}"
```

This phase proves terminal A2A-to-tool execution only. It does not prove that a
Cursor or Codex invocation caused that task. **Schedule after or parallel to
Lane A** — not as project spine.

#### I4 — same-invocation IDE join (formerly PR #6 / Phase 7C)

This phase first closes an observability gap in the current implementation:
`agent_mcp_trace.py` creates a new direct A2A task, while controller
`invoke_agent` returns bounded text and `context_id`. Running those two commands
separately cannot prove the same IDE invocation.

Before the live demo, implement a fail-closed external-invocation evidence path
that does **not** dispatch a second task. It must ingest or capture a sanitized
join from the Cursor MCP call to the controller/A2A task identifier and then to
the tool marker, returned resource names, and `kubectl` result. A local recorder
or bounded controller/agent log capture is acceptable only if it preserves the
native `/mcp` behavior, records no secrets or raw context identifiers, and has
deterministic tests for missing, duplicated, stale, and mismatched join keys.

Investigate the join in this order:

1. Cursor-visible MCP tool-call input and output details;
2. a transparent local MCP recording proxy between Cursor and the controller;
3. bounded controller-side sanitized request logging; or
4. a kagent trace/event hook that exposes the invocation-to-task binding.

If Cursor cannot expose the required join, prefer option 2 as the acceptance
fallback. It must be a pass-through recorder for the native controller MCP
contract, not a new task/session translator or custom IDE-to-A2A bridge. Its
evidence must still join the recorded MCP request to controller/agent task
evidence; recording only `invoke_agent` arguments is insufficient for I4.

If no stable join key can be observed, record I4 Blocked and stop. A separate
`agent_mcp_trace.py` success, a matching answer by coincidence, or a prompt-only
correlation token is not enough. Direct A2A L6 ≠ Cursor/Codex I4.

#### I5/L7 — repeatable native workflow (formerly PR #7 / Phase 8)

Only after Phase 7C succeeds, add the learner workflow:

- pin the chart, controller, runtime image, Python, Cursor, and Codex versions;
- provide idempotent bootstrap and readiness waits;
- track port-forward process ownership and stop both wrappers and actual
  `kubectl` children;
- verify Cursor first, then Codex parity against the same read-only contract;
- exercise restart and recovery; and
- remove sample resources, temporary provider configuration and secrets, and
  owned port-forwards without touching unrelated cluster state.

Codex parity must retain the committed controller-tool allowlist, approval
prompt, and bounded timeouts:

```text
Codex
  -> kagent-controller /mcp
  -> list_agents / invoke_agent
  -> the already proven read-only Kubernetes result path
```

I5 and L7 require a dated run from a fresh Docker Desktop environment. A run on
the already repaired development machine is rehearsal, not promotion evidence.

### What not to do next

- Do not treat Cursor I3 as the mandatory spine before A2A education.
- Do not assume Cursor ←A2A→ Codex as the first integration model.
- Do not jump from roadmap publication directly to a Cursor pod-listing demo.
- Do not use a separate `agent_mcp_trace.py` run as fake Cursor evidence.
- Do not broaden discovery beyond the single approved tool for convenience.
- Do not mark I3 Proven when merging PR #3 foundation code.
- Do not stage, commit, push, undraft, or merge until the applicable gate is
  complete and the user has authorized that external state change.

## First Practice: Observe and Measure

This first practice teaches the kagent control plane without requiring real MCP
tool execution.

### 1. Run the health checker

```powershell
.\scripts\kagent\check-kagent-health.ps1
```

Expected learning:

- pod readiness shows whether the kagent control plane is healthy
- agent status shows whether agents are accepted and ready
- RemoteMCPServer status shows whether backing MCP endpoints are reachable
- service hints show which port-forwards to run next

What this proves:

- kagent is reconciled enough for observation and card/acceptance testing

What this does not prove:

- A2A task dispatch
- real MCP tool invocation

### 2. Inspect pods, agents, and RemoteMCPServer resources

```powershell
kubectl get pods -n kagent
kubectl get agent -n kagent
kubectl get remotemcpserver -n kagent
kubectl describe remotemcpserver kagent-tool-server -n kagent
```

Expected learning:

- pods are the running control-plane and workload processes
- agents are kagent custom resources reconciled by the controller
- RemoteMCPServer resources are references to MCP endpoints
- `Accepted=True` on `kagent-tool-server` means the controller can reach and discover its real MCP server; it still does not prove agent-mediated invocation

What this proves:

- the resources exist and their current status is observable

What this does not prove:

- the target MCP service exists
- the declared tools can actually be invoked

### 3. Open the kagent UI

Run this in a terminal that can stay open:

```powershell
kubectl port-forward -n kagent svc/kagent-ui 8080:8080
```

Then open:

```text
http://localhost:8080
```

Expected learning:

- the UI is a view over the local kagent control plane
- UI reachability is useful evidence, but it is not task-execution evidence

What this proves:

- the UI service is reachable through the port-forward

What this does not prove:

- A2A dispatch
- MCP tool execution

### 4. Fetch the sample agent details

Run this in a second terminal:

```powershell
kubectl port-forward -n kagent svc/kagent-controller 8083:8083
```

Then fetch the card/details:

```powershell
python scripts/kagent/test-a2a-agent.py card
curl.exe http://localhost:8083/api/agents/kagent/k8s-a2a-agent
```

Expected learning:

- the sample agent is visible through the controller REST API
- the card/details show accepted state, deployment readiness, model, and skills
- this is the current reliable educational endpoint

What this proves:

- the controller can return agent metadata
- the sample agent is configured and discoverable

What this does not prove:

- JSON-RPC task dispatch works
- the tools named in the agent can be called

### 5. Observe `RemoteMCPServer Accepted=False`

Historical state before applying the phase 4 runtime:

```text
kagent-tool-server ... Accepted=False
```

Why this was expected in phases 0-2:

- `deploy/base/kagent/kagent-tool-server.yaml` points to `http://kagent-tool-server.kagent:8000/mcp`
- no real MCP server was deployed at that address during phases 0-2
- those phases only needed the resource to exist for card and acceptance inspection

After phase 4, `kagent-tool-server` is expected to be `Accepted=True`. An
`Accepted=False` result now means the runtime or its Service needs diagnosis.

When this becomes unacceptable:

- any phase that claims real MCP tool execution
- any phase that claims the agent can use `k8s_get_resources`
- any health profile named `FullMcpExecution`

## phase_N Roadmap

| Phase | Purpose | Commands | What to observe | Success evidence | What it does not prove yet |
|-------|---------|----------|-----------------|------------------|----------------------------|
| `phase_0_observe` | Learn the kagent control plane and current resource health. | `.\scripts\kagent\check-kagent-health.ps1`; `kubectl get pods -n kagent`; `kubectl get agent -n kagent`; `kubectl get events -n kagent --sort-by=.lastTimestamp` | pods, agents, events, service hints, summary counts | health checker exits 0 for the card lab; pods and agents are visible | A2A task dispatch or MCP tool execution |
| `phase_1_ui_and_card` | Learn UI and controller REST inspection. | `kubectl port-forward -n kagent svc/kagent-ui 8080:8080`; `kubectl port-forward -n kagent svc/kagent-controller 8083:8083`; `python scripts/kagent/test-a2a-agent.py card`; `curl.exe http://localhost:8083/api/agents/kagent/k8s-a2a-agent` | UI reachability, accepted agent details, skills, model metadata | UI opens; card/details return `Accepted: True` and `DeploymentReady: True` | task dispatch or tool invocation |
| `phase_2_degraded_mcp_understanding` | Understand why `RemoteMCPServer Accepted=False` was expected before the phase 4 runtime. | `kubectl get remotemcpserver -n kagent`; `kubectl describe remotemcpserver kagent-tool-server -n kagent`; inspect `deploy/base/kagent/kagent-tool-server.yaml` | historical target URL, accepted condition, and missing service | learner can explain why `Accepted=False` was acceptable for card labs only | full MCP execution |
| `phase_3_truthful_a2a_dispatch` | Separate `card`, `probe`, `task`, and `both` into truthful learning gates. | `python scripts/kagent/test-a2a-agent.py card`; `python scripts/kagent/test-a2a-agent.py probe`; `python scripts/kagent/test-a2a-agent.py task`; `python scripts/kagent/test-a2a-agent.py both` | which paths inspect metadata, which paths test protocol support, which paths must fail on unavailable dispatch | `task` fails when dispatch is unavailable; `probe` reports neutrally; `both` passes only when card and task pass | MCP tool execution |
| `phase_4_real_mcp_server` | Deploy a lightweight in-cluster MCP server behind `kagent-tool-server`. | `kubectl apply -f deploy/base/kagent/kagent-tool-server-runtime.yaml` (reusable base); `kubectl get remotemcpserver -n kagent` checks acceptance | service, endpoint, tool discovery, RemoteMCPServer acceptance | `RemoteMCPServer/kagent-tool-server` reached `Accepted=True` on 2026-07-16 (94 tools discovered) | that the agent has invoked a tool |
| `phase_5_real_agentic_work` | Attempt to prove A2A task dispatch (L4) and agent -> MCP tool invocation (L6). | Existing helper (`card`/`task`/`probe`/`both`); A2A `message/send` with spec-compliant payloads; direct MCP initialize smoke test; UI inspection | task request, agent response, tool result | `message/send` is registered but fails internally; direct MCP initialize succeeds but `tools/call` fails; L4 and L6 remain unproven | repeatable workshop setup |
| `phase_5b_direct_mcp_session` | Close the direct-client MCP session-reuse problem without implying agent mediation. | `python scripts/kagent/mcp_session_smoke.py --url http://127.0.0.1:8000/mcp --output json --resource-type pod --resource-namespace kagent` | initialize, initialized notification, discovered schema, session-reusing tool call, cleanup | exit 0; 18 pods matched `kubectl`; direct MCP invocation proven | L4 A2A dispatch or L6 agent-mediated invocation |
| `phase_5c_truthful_health_profiles` | Teach that “healthy” depends on the capability under test via named profiles. | Run `.\scripts\kagent\check-kagent-health.ps1 -Profile <Profile>` separately for `CardLab`, `DirectMcpServer`, `A2ADispatch`, and `FullMcpExecution` | distinct pass/fail decisions from the same cluster | CardLab/DirectMcpServer pass; A2ADispatch/FullMcpExecution fail truthfully ([phase 5c](../../evidence/kagent/educational-practice-phase-5c-health-profiles.md)) | L4 or L6 becoming proven |
| `phase_5d_trustworthy_a2a` | Prove L4 with pinned `message/stream` and strict JSON evidence. | `python scripts/kagent/test-a2a-agent.py task --output json`; `.\scripts\kagent\check-kagent-health.ps1 -Profile A2ADispatch` | SSE status-update with non-empty taskId; health JSON gate | L4 proven ([phase 5d](../../evidence/kagent/educational-practice-phase-5d-trustworthy-a2a.md)); A2ADispatch exit 0 | L6 agent-mediated MCP |
| `phase_5e_agent_mediated_mcp` | Correlate one A2A task → MCP `k8s_get_resources` → same-task returned names → kubectl match under nested schema 1.0. | `python scripts/kagent/agent_mcp_trace.py --output json`; FullMcpExecution profile | agreeing transport/protocol/dispatch; exact task/server/tool/arguments; bounded source proof; computed freshness; recomputed name match | Hardened helper/schema/tests shipped; retained live exit 1 — L6 Not proven ([phase 5e](../../evidence/kagent/educational-practice-phase-5e-agent-mediated-mcp.md)) | Live L6 without one fresh exit 0 |
| `phase_5f_integrity_and_protocol_hardening` | Close reproducible fail-closed defects before relying on stricter health or A2A evidence gates. | Targeted Pester and pytest cases for missing CRDs and multiline SSE; repository hygiene checks | strict health profiles reject a missing `RemoteMCPServer` CRD; multi-line SSE `data:` fields form one JSON payload; local debug captures are not tracked | fixes and deterministic regression tests are merged; hosted CI status is recorded only for the exact committed head | L6, IDE discovery, or a green run at an unverified SHA |
| `phase_6_native_mcp_federation` | Verify bounded no-tool Cursor delegation through the controller's native MCP contract. | exact controller preflight; human Cursor tool trace; exact postflight; profile and process rollback | reviewed tools, singleton agent inventory, bounded responses, and observable second-call `context_id` forwarding | I0-I2 are Proven; Candidate B strict preflight qualified; I3 remains Blocked pending the human trace ([phase 6B-6D closure](../../evidence/kagent/educational-practice-phase-6b-6d-closure.md)) | L6 tool invocation, I4, or an alternate gateway |
| `phase_7a_readonly_surface_hardening` | Make MCP discovery default-deny and keep Kubernetes authorization least privilege. | complete paginated `tools/list` inventory; forbidden-name test; RBAC negative checks; strict Kubernetes validation; required policy scan | discovery exposes only `k8s_get_resources`; mutation-capable tools are absent; unnecessary permissions are removed or justified | dated safety record, deterministic tests, live inventory, and final-SHA hosted Quality pass | I3, I4, L6, repeatability, or write authority |
| `phase_7b_correlated_l6` | Prove one direct A2A task invoked the approved tool and returned matching Kubernetes names. | tool-enabled agent profile; `agent_mcp_trace.py --output json`; `FullMcpExecution`; independent `kubectl` query | same A2A task identity; correct server/tool/arguments; bounded source proof; returned names; `kubectl` match | one fresh qualifying L6 record; three consecutive passes are operational confidence only | I4, because the helper owns a direct A2A dispatch rather than an IDE invocation |
| `phase_7c_correlated_i4` | Join one real Cursor `invoke_agent` call to qualifying same-task L6 output. | external-invocation capture/ingestion that does not dispatch another task; Cursor trace; same-task tool/result proof; independent `kubectl` | one stable join from IDE request to A2A task, MCP marker, returned names, and cross-check | one qualifying I4 record that also satisfies L6 for that invocation | L7 repeatability, production readiness, reverse delegation, or write authority |
| `phase_8_repeatable_native_runtime` | Make the proven native read-only IDE path reproducible for a fresh learner. | idempotent bootstrap; tracked port-forwards; start/check/stop/restart; Cursor and Codex acceptance; cleanup | pinned prerequisites; both-client acceptance; recovery; no owned orphaned processes or lab resources | clean Docker Desktop run reaches I5 and L7 targets with dated evidence and final-SHA hosted Quality | production readiness or a write-enabled profile |

## Strategic Upper-Layer Grid

The canonical L0-L7 definitions and promotion rules are maintained in
`docs/reference/kagent-capability-matrix.md`. The current decision for each level
is maintained in `evidence/kagent/README.md`; this roadmap owns phase sequencing.

## Rules Before Real MCP/Agentic Work

### Boundaries

- Do not call `Accepted=True` agent status "tool execution."
- Do not let `probe` success imply `task` success.
- Do not promote `RemoteMCPServer Accepted=False` beyond card and acceptance labs.
- Keep card/metadata inspection separate from task dispatch.
- Keep task dispatch separate from MCP tool invocation.
- Treat direct A2A helpers as protocol-conformance and evidence diagnostics.
  Cursor and Codex use the controller's native `/mcp` surface when the pinned
  contract exposes the required agent tools.

### Promotion Rules

- A phase can only depend on evidence from the previous phase if that evidence is observable and recorded.
- Do not move from L3 to L4 until `task` mode has truthful pass/fail semantics.
- Do not move from L4 to L5 until a real MCP server manifest and service are separate from the sample agent.
- Do not move from L5 to L6 until a task response proves a real tool was invoked.

### Validation Gates

- Add health-check profiles before making stricter requirements global.
- `CardLab` may allow unrelated RemoteMCPServer `Accepted=False`.
- `DirectMcpServer` requires target acceptance plus session-reusing direct tool evidence.
- `A2ADispatch` must require truthful task dispatch behavior.
- `FullMcpExecution` must derive A2A and agent-mediated tool gates from the same
  Phase 5E task; any separately supplied A2A record must have the same task id.
  Direct MCP alone is insufficient.

### Naming Rules

- Use `card` only for metadata/card retrieval.
- Use `probe` only for method support discovery.
- Use `task` only for actual dispatch attempts.
- Use `both` only when both card validation and task dispatch are required.
- Do not name a function `fetch_agent_card` if it sends a task payload.

### Deploy Taxonomy

- `deploy/base/` contains reusable primitives such as `RemoteMCPServer` definitions.
- `deploy/samples/` contains educational starter agents and examples.
- Real MCP server manifests must be separate from sample A2A agent manifests.
- Environment-specific assembly belongs in future overlays, not in the sample manifest.

### Evidence Requirements

- Capture evidence for completed phases under `evidence/` or in the relevant runbook.
- Evidence must include the command, observed output summary, date, and capability level proven.
- Do not reuse L2 or L3 evidence to claim L5 or L6.
- Record unexpected implementation failures with
  `docs/templates/educational-problem-record.md`; promote only proven recurring
  diagnostics into this roadmap or the runbook.

Completed phases are recorded in `evidence/kagent/educational-practice-phase-0-2.md`.
The implementation review is recorded in
`evidence/kagent/educational-practice-phase-0-2-review.md`.
Truthful A2A dispatch gate evidence is recorded in
`evidence/kagent/educational-practice-phase-3.md`.
Real MCP server design and L5 acceptance evidence is recorded in
`evidence/kagent/educational-practice-phase-4.md`.
The MCP server design decision record is at
`evidence/kagent/educational-practice-phase-4a-design.md`.
A2A dispatch check and agentic work attempt for L4/L6 is recorded in
`evidence/kagent/educational-practice-phase-5.md` (L4 and L6 remain unproven).
The direct-client session follow-up is recorded in
`evidence/kagent/educational-practice-phase-5b-direct-mcp.md`; it proves direct
MCP invocation only.
Truthful health profiles are recorded in
`evidence/kagent/educational-practice-phase-5c-health-profiles.md`.
Trustworthy A2A dispatch (L4) is recorded in
`evidence/kagent/educational-practice-phase-5d-trustworthy-a2a.md`.
Correlated agent-mediated MCP attempt (L6 Not proven) is recorded in
`evidence/kagent/educational-practice-phase-5e-agent-mediated-mcp.md`.

## Roadmap Maintenance

The completed slice history is recorded by the dated evidence links above. The
active work, dependencies, PR boundaries, and stop conditions live only in the
Hardened Implementation Roadmap in this document. Do not append a second
numbered backlog below the phase table.

The ranked flaw ledger remains in
[the evidence index](../../evidence/kagent/README.md). That ledger owns current
status and observed gaps; this roadmap owns their implementation order. The
repository-wide stable-release ordering remains in
[Implemented State and Roadmap](IMPLEMENTED-STATE-AND-ROADMAP.md).

When a phase changes state:

1. preserve the live output as a dated record or addendum;
2. run a capability review before changing any decision;
3. update the evidence index, this phase table, the repository roadmap, and the
   runbook only where their owned facts changed;
4. keep `REPO_MANIFEST.yaml` unchanged unless a new canonical file was added;
5. push the final candidate SHA and require `quality.yml` on that exact SHA
   before undrafting, merging, tagging, or claiming hosted Quality.
