# Phase 6B–6D Closure Attempt

**Observed:** 2026-07-31, Asia/Tehran  
**Environment:** Docker Desktop Kubernetes context `docker-desktop`, namespace `kagent`  
**Controller:** Helm chart / image lineage for kagent `0.9.11`  
**Branch:** `feat/kagent-native-mcp-federation`

This record covers the Phase 6B–6D closure cycle. It does not rewrite
[educational-practice-phase-6-native-mcp-federation.md](educational-practice-phase-6-native-mcp-federation.md),
which remains the immutable OpenAI-403-era observation.

## Deterministic work shipped this cycle

- Hybrid context-id leak detector (`MIN_EMBEDDED_SECRET_LENGTH = 8`) in
  `scripts/kagent/controller_mcp_smoke.py`, with short-id and embedded-long-id tests.
- Exact inventory profile:
  `config/kagent/ide-safe-agent-inventory.txt` (singleton `kagent/k8s-a2a-agent`),
  `--expected-inventory` under `config/kagent/` only, canonical SHA-256,
  mutual exclusion with `--approved-agent`, fail on duplicate discovered refs.
- Target-specific Ollama manifests:
  `deploy/samples/kagent/ide-safe-ollama-model-config.yaml`,
  merge/rollback patches under `config/kagent/` (not `deploy/`, so kubeconform
  does not treat partial patches as resources).
- Runbook/capability-matrix updates for Minimal-profile isolation, Ollama
  reachability, Cursor tool-trace context proof, and preflight/postflight.

## Live observations (sanitized)

### Agent inventory

```text
kubectl get agents -A
```

Returned multiple Accepted/Ready Agents in `kagent`, including demo agents
(`observability-agent`, `helm-agent`, `k8s-agent`, and others) in addition to
`k8s-a2a-agent`. Exact singleton inventory
(`config/kagent/ide-safe-agent-inventory.txt`) therefore cannot pass until the
lab is reset to a Minimal profile and only the reviewed target Agent remains
Accepted/Ready cluster-wide.

No Agent resources were deleted by the helper. No Minimal-profile reinstall was
completed in this attempt (would be a deliberate cluster reset).

### Ollama host

- Client version observed: `0.23.0`.
- Host started with `OLLAMA_HOST=0.0.0.0:11434`; local
  `GET http://127.0.0.1:11434/api/version` returned JSON with that version.
- `ollama pull qwen2.5:7b-instruct` failed before download:
  `lookup registry.ollama.ai: no such host`.
- Local `ollama list` showed other previously pulled models; the pinned
  `qwen2.5:7b-instruct` digest was **not** obtained.

### Cluster reachability probe

Temporary Pod `ollama-probe` (`curlimages/curl:8.5.0`) did not become Ready
within 60s (`timed out waiting for the condition`). In-cluster
`/api/version` and `/api/tags` checks were therefore **not** completed.
Probe Pod was deleted.

### ModelConfig

```text
kubectl apply -f deploy/samples/kagent/ide-safe-ollama-model-config.yaml
```

`ModelConfig/ide-safe-ollama-model-config` reconciled with
`Accepted=True`, `observedGeneration=1`, provider `Ollama`, model
`qwen2.5:7b-instruct`, host `http://host.docker.internal:11434`.

**Agent was not patched** to this ModelConfig because the pinned model was not
pulled and in-cluster reachability was not verified. Shared
`default-model-config` remains in use on `k8s-a2a-agent`
(`modelConfig: default-model-config`, generation/observedGeneration both `1`).

### Python exact-inventory diagnostic

Not run to success: discoverable inventory is not the committed singleton, and
the provider path for a bounded no-tool response remains blocked.

### Cursor I3

Not attempted after the provider/inventory blockers. No Cursor tool-call trace
for `context_id` forwarding was captured.

## 2026-07-31 capability decisions after the initial attempt

This table is the decision at the time of the initial attempt. The 2026-08-02
addendum is the current singleton-inventory observation; the later dated
addendum records the DeepSeek qualification without rewriting either history.

| Level | Decision | Notes |
|-------|----------|-------|
| I0–I2 | Proven | Unchanged; prior phase 6 record |
| I3 / I3-Cursor | **Blocked** | Exact inventory not singleton; pinned Ollama model not pulled (registry DNS); cluster Ollama probe incomplete; no Cursor tool-trace context proof |
| I3-Codex | Not proven | Not attempted |
| I4 | Not proven | Out of scope |
| I5 | Not attempted | Out of scope |
| L6 / L7 | Not proven | Out of scope |

## Blocked-exit decision

Per the Phase 6B–6D plan: after one properly documented Ollama/Cursor attempt,
**PR #3 remains draft**. I3 stays in PR scope. This cycle does **not** auto-narrow
the PR to an I0–I2 foundation and does not merge.

Failure boundary summary:

1. Before `invoke_agent`: exact inventory cannot pass while demo Agents remain
   Accepted/Ready cluster-wide.
2. Before Agent patch: `qwen2.5:7b-instruct` pull failed (registry DNS);
   in-cluster Ollama probe Pod not Ready.
3. Cursor I3 not reached.

## Explicit non-claims

- Helper/unit tests do not prove I3.
- ModelConfig Accepted does not prove model execution.
- Local Ollama `/api/version` does not prove cluster reachability.
- No Kubernetes tool execution, I4, or L6 was attempted.

## 2026-08-02 addendum — local Minimal inventory reset and provider retry

**Observed:** 2026-08-02, Asia/Tehran
**Environment:** Docker Desktop Kubernetes context `docker-desktop`, namespace
`kagent`
**Scope:** local-only Phase 6B/6C retry; Phase 7 remained deferred

This addendum records a new observation without changing the 2026-07-31
snapshot above. Pre-reset recovery copies were retained outside the repository;
no credentials, raw MCP identifiers, or raw `context_id` values were recorded.

### Phase 6B — exact singleton inventory

The ten Helm-managed demo Agent CRs were explicitly deleted from the local
Docker Desktop cluster. Their reconciled Deployments were observed deleted.
The reviewed resources were then reapplied:

```text
deploy/base/kagent/kagent-tool-server.yaml
deploy/base/kagent/kagent-tool-server-runtime.yaml
deploy/samples/kagent/k8s-a2a-agent.yaml
```

After reconciliation, `kubectl get agents -A` returned exactly
`kagent/k8s-a2a-agent`. The target Agent reported
`generation=2`, `observedGeneration=2`, `Accepted=True`, and `Ready=True`.
The committed IDE-safe inventory prerequisite is therefore satisfied. No demo
agent was added to the allowlist.

### Phase 6C — pinned Ollama provider retry

- Ollama `0.23.0` was running and its effective listener was
  `0.0.0.0:11434`; the user-level `OLLAMA_HOST` variable was unset.
- The local cache did not contain `qwen2.5:7b-instruct`.
- A new `ollama pull qwen2.5:7b-instruct` attempt failed before download
  because the Ollama registry hostname could not be resolved by DNS. No model
  digest was obtained.

The model prerequisite therefore failed before the in-cluster
`host.docker.internal` probe and bounded provider/function-call qualification.
`k8s-a2a-agent` was not patched to the IDE-safe Ollama ModelConfig and remains
on `default-model-config`.

### Phase 6D and status decision

The exact-inventory controller smoke diagnostic and the Cursor UI acceptance
were not attempted: both require the bounded provider response that Phase 6C
could not establish. No controller `invoke_agent`, Kubernetes tool request, or
Cursor `context_id` trace was captured.

| Level | Decision | Notes |
|-------|----------|-------|
| I0–I2 | Proven | Unchanged. |
| I3 / I3-Cursor | **Blocked** | Singleton inventory is now satisfied; the pinned Ollama model remains unavailable because registry DNS failed, so no Cursor context-continuation trace can be collected. |
| I3-Codex | Not proven | Not attempted. |
| I4 | Not proven | No IDE-to-Kubernetes correlation was attempted. |
| I5 | Not attempted | No workshop acceptance was attempted. |
| L6 / L7 | Not proven | No agent-mediated Kubernetes tool execution or repeatability evidence was attempted. |

**Blocked exit:** retain PR #3 as a draft. Do not substitute an unspecified
hosted provider, start Phase 7, or promote any capability until an approved
provider/model route permits a fresh I3-Cursor acceptance.

## 2026-08-03 addendum — DeepSeek fallback qualification

**Observed:** 2026-08-03, Asia/Tehran
**Environment:** Docker Desktop Kubernetes context `docker-desktop`, namespace
`kagent`; controller `0.9.11`
**Scope:** local-only provider and no-tool-preflight preparation; Phase 7
remained deferred

The user-scoped `DEEPSEEK_API_KEY` was present but never read into evidence or
repository files. The new stdlib-only provider helper emitted only model names,
HTTP statuses, latency, and pass/fail decisions.

### Direct provider qualification

`deepseek-v4-flash` qualified against the OpenAI-compatible DeepSeek endpoint:

| Check | HTTP | Latency | Result |
|-------|------|---------|--------|
| bounded no-tool response | 200 | 10125 ms | Pass |
| dummy function-schema response | 200 | 4766 ms | Pass |

`deepseek-v4-pro` was not requested because the ordered Flash candidate passed.
The initial non-thinking probe used too-small budgets and produced no final
content; the helper was corrected to explicitly disable thinking and retain a
bounded 64-token budget. This is direct provider qualification only, not Agent
or IDE evidence.

### Target profile and controller preparation

- The local-only `kagent-deepseek` Secret was created from the user environment
  without displaying or reading back its value.
- `ModelConfig/ide-safe-deepseek-model-config` was Accepted with provider
  `OpenAI` and model `deepseek-v4-flash`.
- Patching only `k8s-a2a-agent` to that profile reached current-generation
  `Accepted=True` and `Ready=True`.
- The first exact-inventory controller diagnostic confirmed the reviewed tool
  set and singleton inventory, then received the bounded answer with a terminal
  period; the existing default exact string therefore failed closed.
- A punctuation-adjusted retry encountered a controller-to-Agent EOF during
  rollout. The Agent was restored to `default-model-config`. A final retry
  after rollout/endpoints was not executed because the local command-approval
  service timed out twice before running it.

No Cursor UI trace, successful agent-context continuation, or Kubernetes tool
request was captured.

| Level | Decision | Notes |
|-------|----------|-------|
| I0–I2 | Proven | Unchanged. |
| I3 / I3-Cursor | **Blocked** | Direct DeepSeek Flash qualification and the singleton inventory passed, but the bounded controller preflight has not qualified and no Cursor `context_id` trace exists. |
| I3-Codex | Not proven | Not attempted. |
| I4 | Not proven | No IDE-to-Kubernetes correlation was attempted. |
| I5 | Not attempted | No workshop acceptance was attempted. |
| L6 / L7 | Not proven | No agent-mediated Kubernetes tool execution or repeatability evidence was attempted. |

**Explicit non-claims:** DeepSeek HTTP 200, ModelConfig acceptance, Agent
readiness, controller tool discovery, and direct provider function-schema
qualification do not prove I3, I4, L6, or L7. Phase 7 remains deferred.

## 2026-08-04 addendum — observe-only preflight + DeepSeek strict retry

**Observed:** 2026-08-04, Asia/Tehran
**Environment:** Docker Desktop Kubernetes context `docker-desktop`, namespace
`kagent`; controller `0.9.11`
**Scope:** Phase 6D observe-only helper + local DeepSeek no-tool preflight
retry; Phase 7 remained deferred

### Helper shipped this slice

- `--observe-only` on `scripts/kagent/controller_mcp_smoke.py` keeps exact tools,
  singleton inventory (including postflight same-session re-check), non-empty
  bounded first reply (160-char cap), and non-empty `context_id`; skips
  exact-text equality and context continuation.
- Sanitized markers: `observationOnly`, `strictPreflightQualified` (true only
  for full strict success), `responseTruncated`.
- Deterministic tests cover USAGE without inventory, exact-text skip, tool /
  inventory / empty / overlong / missing-context failures, exactly one
  `invoke_agent`, and postflight inventory drift.
- Runbook documents observation before strict retry and forbids changing helper
  default expected-response constants from a single live observation.

### Live attempt (sanitized)

Prerequisites (metadata only): `kagent-deepseek` key name `DEEPSEEK_API_KEY`
present; `ide-safe-deepseek-model-config` `Accepted=True`. Agent pre-state was
`modelConfig=default-model-config`, generation/observedGeneration `8`,
`Accepted=True`/`Ready=True`.

Applied DeepSeek ModelConfig (unchanged) and patched only `k8s-a2a-agent` to
`ide-safe-deepseek-model-config`. Post-patch: generation/observedGeneration
`9`, `Accepted=True`/`Ready=True`, rollout complete, EndpointSlice ready.
Controller port-forward `8083:8083` was started for the helper and stopped
afterward.

| Step | Exit | Notes |
|------|------|-------|
| observe-only exact inventory | 0 | `observationOnly=true`, `strictPreflightQualified=false`, `agentResponse=kagent native MCP acceptance`, `agentContextId=present`, continuation skipped, postflight inventory matched |
| strict exact inventory with explicit CLI expected text from observation | 1 | First `invoke_agent` returned the task text echoed with a terminal period (`…acceptance. Do not call…`), so exact-text equality failed closed; no continuation; `strictPreflightQualified=false` |

Agent remained `Accepted=True`/`Ready=True` during the failure. Controller log
tail showed successful MCP `invoke_agent` handling plus unrelated recurring
`kagent-grafana-mcp` Forbidden noise; no Secret values were read.

Immediate rollback restored `default-model-config` (generation/observedGeneration
`10`, `Accepted=True`/`Ready=True`). No Cursor UI trace was attempted. No
Kubernetes tool was requested. Helper defaults were not changed.

| Level | Decision | Notes |
|-------|----------|-------|
| I0–I2 | Proven | Unchanged. |
| I3 / I3-Cursor | **Blocked** | Observe-only controller diagnostic passed under DeepSeek Flash, but the strict no-tool preflight (exact text + context continuation) did not qualify because the model reply was non-deterministic; no Cursor `context_id` tool-trace proof exists. |
| I3-Codex | Not proven | Not attempted. |
| I4 | Not proven | No IDE-to-Kubernetes correlation was attempted. |
| I5 | Not attempted | No workshop acceptance was attempted. |
| L6 / L7 | Not proven | No agent-mediated Kubernetes tool execution or repeatability evidence was attempted. |

**Explicit non-claims:** observe-only exit 0 and `strictPreflightQualified`
false do not prove I3. A strict Python helper success would still be controller
preflight only, not I3-Cursor acceptance. Phase 7 remains deferred.
