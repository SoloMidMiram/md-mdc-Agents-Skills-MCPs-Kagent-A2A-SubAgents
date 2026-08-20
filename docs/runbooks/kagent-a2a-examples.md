# kagent A2A Educational Examples (E1–E5)

This runbook owns executable procedures for the A2A-first educational sequence
defined in [Project North Star](../north-star.md). Capability decisions remain in
`evidence/kagent/README.md`; this document owns commands and pass/fail criteria.

**Status:** E1–E2 manifests and harness ship in PR #4 (`edu/kagent-a2a-role-examples`).

---

## Prerequisites

- Local `kagent` on `docker-desktop` per [local kagent A2A lab](local-kagent-a2a-lab.md)
- L4 A2A dispatch proven (see evidence index)
- DeepSeek qualified and `ide-safe-deepseek-model-config` applied
- For E3+: read-only MCP surface from PR #5 when tool access is required
- For E4/E5: Codex local runner (PR #7) — not required for E1–E2

---

## Example Summary

| ID | Flow | Lane | Proves | Does not prove |
|----|------|------|--------|----------------|
| E1 | human → A2A → planner | A | Single-agent bounded dispatch | MCP, supervisor delegation, external workers |
| Phase 2 | planner artifact → A2A → reviewer (manual) | A | Second role + contract | Supervisor delegation |
| E2 | supervisor → planner → reviewer | A | Agent-as-tool multi-hop A2A | MCP tools, Cursor/Codex interop |
| E3 | docs validator + sanitized repo bundle | A, S | Bounded read-only validation | Cluster mutation, full capstone |
| E4 | planner → coding worker → reviewer | A, C | External worker in measured workflow | Cursor I3/I4, true A2A worker adapter (B8) |
| E5 | telegram capstone | A, S, C, B | End-to-end orchestrated workflow | Production readiness |

Manifest paths: `deploy/samples/kagent-a2a/01-planner` … `05-telegram-capstone`.

---

## Apply order (E1–E2)

```powershell
uv run python scripts/kagent/deepseek_provider_probe.py --output json
kubectl apply -f deploy/samples/kagent/ide-safe-deepseek-model-config.yaml
kubectl apply -f deploy/samples/kagent-a2a/01-planner/planner-agent.yaml
kubectl apply -f deploy/samples/kagent-a2a/02-reviewer/reviewer-agent.yaml
kubectl apply -f deploy/samples/kagent-a2a/03-supervisor/supervisor-agent.yaml
```

Wait for each agent to show `Accepted=True` and deployment ready before dispatch.

---

## E1 — Planner-only A2A

**Objective:** Dispatch one bounded planning task to a planner agent with no MCP,
no Kubernetes tool calls, and no Cursor/Codex client.

```powershell
python scripts/kagent/experiments/run_a2a_example.py `
  --agent planner-agent `
  --prompt "Plan a minimal hello-world Telegram bot." `
  --output json > evidence/kagent/experiments/tmp/e1-run.json

python scripts/kagent/experiments/record_experiment.py `
  --input evidence/kagent/experiments/tmp/e1-run.json `
  --cleanup "kubectl delete -f deploy/samples/kagent-a2a/01-planner/planner-agent.yaml"
```

**Pass:** Structured planner response; one A2A task id; exit 0.  
**Fail closed:** Missing task id, provider error, or timeout.

**Evidence:** `evidence/kagent/experiments/YYYY-MM-DD-e1-planner.json`

---

## Phase 2 — Direct reviewer (manual coordination)

**Objective:** Feed a planner artifact to `reviewer-agent` via direct A2A.

```powershell
# Build prompt file with request + proposed_plan JSON, then:
python scripts/kagent/experiments/run_a2a_example.py `
  --agent reviewer-agent `
  --prompt-file evidence/kagent/experiments/tmp/planner-prompt.json `
  --output json
```

**Pass:** Reviewer JSON with `verdict` in `{approve, revise}`.  
**Does not prove:** Supervisor agent-as-tool delegation.

---

## E2 — Supervisor → planner → reviewer

**Objective:** Supervisor delegates to planner and reviewer via agent-as-tool (A2A).

```powershell
python scripts/kagent/experiments/run_a2a_example.py `
  --agent supervisor-agent `
  --prompt "Plan and review a minimal hello-world Telegram bot." `
  --output json > evidence/kagent/experiments/tmp/e2-run.json

python scripts/kagent/experiments/record_experiment.py `
  --input evidence/kagent/experiments/tmp/e2-run.json `
  --cleanup "kubectl delete -f deploy/samples/kagent-a2a/03-supervisor/supervisor-agent.yaml" `
  --cleanup "kubectl delete -f deploy/samples/kagent-a2a/02-reviewer/reviewer-agent.yaml" `
  --cleanup "kubectl delete -f deploy/samples/kagent-a2a/01-planner/planner-agent.yaml"
```

**Pass:** Composite supervisor artifact; task id present; operator confirms sub-agent hops in controller logs.  
**Does not prove:** MCP invocation or IDE correlation.

---

## E3 — Docs validator (sanitized bundle)

**Objective:** Docs agent validates a sanitized repository bundle against a schema.

**Safety:** Bundle is read-only; no live cluster mutation. Uses Lane S allowlist when MCP is involved.

**Planned:** PR #4 docs-agent sample + PR #5 read-only tool surface.

---

## E4 — Planner → Codex → reviewer

**Objective:** In-cluster planner and reviewer bracket an out-of-cluster Codex coding worker.

```text
kagent planner (A2A) → Codex local runner → kagent reviewer (A2A)
```

Codex is **not** initially a peer A2A agent. It is invoked via the worker adapter (PR #7).

**Benchmark baseline:** B5 (see north star).

---

## E5 — Telegram capstone

**Objective:** Full orchestrated workflow integrating planner, reviewer, supervisor,
docs validation, tests, and human deploy approval.

**Depends on:** PR #5 (safety), PR #7 (Codex worker), prior E1–E4 evidence.

---

## Non-claims (all E1–E2 runs)

- L6 agent-mediated MCP tool proof
- I3 Cursor context continuation
- I4 same-invocation IDE correlation
- MCP Kubernetes tools (planner/reviewer/supervisor have `tools: none`)

---

## Related

- [Project North Star](../north-star.md)
- [Educational lanes architecture](../architecture/EDUCATIONAL-LANES-ARCHITECTURE.md)
- Sample READMEs under `deploy/samples/kagent-a2a/`
