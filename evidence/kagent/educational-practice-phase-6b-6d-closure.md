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
  merge patch and rollback patch for `k8s-a2a-agent`.
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

## Capability decisions after this attempt

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
