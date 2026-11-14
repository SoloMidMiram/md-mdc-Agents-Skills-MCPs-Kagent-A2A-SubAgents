# Project North Star

The current direction is a measurable context-first coding assistant. The
repaired CTX-01 builder and #18's offline labs are integrated in main.
Actual coding improvement remains unmeasured.

The next prerequisite is independent LAB-RUNNER-01 security qualification,
followed by a separately authorized non-scored smoke and the nine frozen
EVAL-01 runs. The [implemented-state roadmap](onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md)
owns cross-lane ordering. The [runner specification](architecture/LAB-RUNNER-01-PROVISIONING.md)
owns provisioning requirements. I3 remains independent.

**Effective:** 2026-11-06 reconciliation of the selected context-first priority

**Status:** Current direction; August A2A-first retained below as historical product priority
**Canonical owners:** This document (direction); `docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md` (phase/PR sequencing); `evidence/kagent/README.md` (capability decisions)

---

## North Star

**Build trustworthy task context, then measure whether it improves real coding
outcomes under controlled conditions.** No model calls are warranted before the
runner is independently qualified. No snapshot/discovery/Context7/kagent feature
expansion is the immediate milestone. Preserve cloud-only model policy and
existing capability definitions; no CI result supplies integration approval.

Historical August 7 direction: first prove and measure useful A2A workflows
inside kagent, then attach Codex and Cursor as clients/workers and compare them.
The remainder of this document records that educational architecture and its
dated rationale. It remains an independent laboratory, not the current product
priority. Security evidence and experimental outcome evidence are separate.

The Cursor I3 gate remains useful as interoperability proof. It must not block A2A education or the primary learning path.

---

## What Changed (2026-08-07)

### Old spine (retired as project gate)

```text
Cursor I3 → read-only MCP → direct A2A L6 → Cursor I4 → Codex parity
```

This sequence treated Cursor context-forwarding (I3) as the mandatory spine. That ordering delayed bounded multi-agent learning while a client-side tool-discovery blocker remained open.

### New spine

```text
A2A educational core (planner, reviewer, supervisor, docs agents)
  ├─ Cursor interoperability (one client under test, not gatekeeper)
  ├─ Codex interoperability (first coding worker)
  └─ worker/orchestrator experiments
→ read-only tool execution
→ measured multi-agent workflows
→ Cursor/Codex comparative evaluation
```

### Important distinction

- **Not** "Cursor ←A2A→ Codex" initially.
- **Current model:** Cursor/Codex → MCP → kagent controller → A2A → kagent agents.
- The kagent supervisor can delegate via Agent tools (A2A).
- Codex/Cursor as A2A workers is a **later, separate experiment** (not the first integration seam).

Historical I0–I2 evidence and the I3-Cursor Blocked decision are preserved in `evidence/kagent/README.md`. This pivot changes **priority and sequencing**, not proven capability status.

---

## Four Planning Lanes

These lanes organize work. They are **not** new capability numbering — keep L0–L7 and I0–I5 as defined in `docs/reference/kagent-capability-matrix.md`.

| Lane | Question | Primary artifacts |
|------|----------|-------------------|
| **A — A2A Education** | Can kagent agents delegate useful bounded work? | `deploy/samples/kagent-a2a/`, `scripts/kagent/experiments/`, E1–E5 examples |
| **S — Safety / MCP** | Can agents use only explicitly approved tools? | SAFE-01 read-only surface, RBAC, default-deny discovery |
| **C — Client Interop** | Can Cursor and Codex enter the same workflow reliably? | Controller `/mcp`, I-track evidence, client configs |
| **B — Benchmarking** | Latency, reliability, cost, quality per architecture? | `scripts/kagent/experiments/benchmark_a2a.py`, baselines B0–B8, OTel traces |

These historical lanes remain useful educational planning categories. Lane A's
former default priority does not override the current context-first runner gate.

---

## Runtime Model

```text
Human or IDE client (Cursor / Codex)
  → MCP (controller native /mcp when used)
  → kagent controller
  → A2A dispatch
  → kagent agents (planner, reviewer, supervisor, docs)
  → optional read-only MCP tools (approved allowlist)
  → measured workflow output
```

**DeepSeek** serves inside kagent for planner, reviewer, docs, and supervisor roles — a third independent reasoning system alongside Cursor and Codex.

**Client vs worker roles (asymmetric by design):**

| System | Role | Notes |
|--------|------|-------|
| Codex | Automatable coding worker (first external worker) | WORKER-01 adapter; local runner outside K8s for early experiments |
| Cursor | Interactive northbound client | I3 remains Blocked at tool discovery; interoperability proof, not education gate |
| DeepSeek (in kagent) | In-cluster planner/reviewer/docs/supervisor | Bounded A2A roles before external worker attachment |

Cursor and Codex do not require architectural symmetry.

---

## Educational Example Sequence (E1–E5)

| Example | Flow | Excludes |
|---------|------|----------|
| **E1** | human → A2A → planner | MCP, K8s tools, Cursor, Codex |
| **E2** | supervisor → planner → reviewer (agent-as-tool) | External clients, MCP mutation |
| **E3** | docs validator with sanitized repo bundle | Live cluster mutation |
| **E4** | planner → coding worker → reviewer | Full capstone orchestration |
| **E5** | telegram capstone full workflow | — (integrates prior examples) |

Runnable instructions: `docs/runbooks/kagent-a2a-examples.md`.  
Manifests: `deploy/samples/kagent-a2a/01-planner` through `05-telegram-capstone`.

---

## First Three Experiments to Execute

1. **Planner-only A2A** — E1; proves bounded single-agent dispatch without MCP or external clients.
2. **Planner → reviewer via supervisor** — E2; proves agent-as-tool delegation inside kagent.
3. **Planner → Codex → reviewer** — E4 subset; Codex runs outside K8s via local runner; reviewer remains in-cluster.

These precede Cursor I3 close-out, direct A2A L6 tool proof, and I4 correlation work unless a dated record shows a hard dependency.

---

## Proposed Directory Structure

```text
deploy/samples/kagent-a2a/
  01-planner/ … 05-telegram-capstone/   # role manifests per example
scripts/kagent/experiments/
  run_a2a_example.py, record_experiment.py, contracts.py  # EDU-01 Lane A
  benchmark_a2a.py, collect_trace.py                      # EVAL-01 (planned)
tests/kagent/experiments/               # deterministic harness tests
docs/runbooks/kagent-a2a-examples.md    # E1–E5 procedures
evidence/kagent/experiments/            # dated experiment records
```

E1–E2 manifests and harness are implemented on branch `edu/kagent-a2a-role-examples`.

---

## PR Roadmap (revised from commit `543f83d` baseline)

Stable workstream IDs identify planned work; hosted PR numbers identify actual reviews. See [integration workstreams](reference/integration-workstreams.md).

| PR | Branch | Purpose | Depends on |
|----|--------|---------|------------|
| **#3** (current) | `feat/kagent-native-mcp-federation` | Native federation foundation; I0–I2 proven; honest I3 blocker recorded | Gate 0 (`090ad52`) |
| **EDU-01** | `edu/kagent-a2a-role-examples` | Planner, reviewer, supervisor manifests; E1–E2 harness (Lane A) | #3 |
| **SAFE-01** | `feat/kagent-readonly-mcp-surface` | Default-deny one-tool safety (Lane S) | #3 |
| **EVAL-01** | `eval/kagent-a2a-benchmarks` | Benchmark harness + OTel + paired baselines B0–B8 (Lane B) | EDU-01 |
| **WORKER-01** | `feat/codex-worker-adapter` | Codex coding-worker bridge (Lane A/C) | EDU-01, EVAL-01 |
| **INTEROP-01** | `spike/cursor-worker-interop` | Cursor client vs worker decision (Lane C) | EDU-01, EVAL-01 |
| **CAPSTONE-01** | `edu/telegram-orchestrated-capstone` | Full E5 capstone | SAFE-01, WORKER-01 |

### PR #3 governance (2026-08-07 addendum)

- Merge when **I0–I2 are proven** and the **I3-Cursor limitation is recorded accurately**.
- **Code merged ≠ capability proven.** Do not mark I3 Proven on merge.
- I3 acceptance moves to a **future PR** (Lane C), parallel to Lane A education.
- L6 and I4 remain separate experiments; neither blocks basic A2A education.

Detailed phase gates: `docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md`.

---

## Benchmark Plan (Lane B)

### Baselines B0–B8

| ID | Architecture |
|----|----------------|
| B0 | Direct DeepSeek API |
| B1 | DeepSeek through one kagent A2A agent |
| B2 | kagent supervisor → planner |
| B3 | supervisor → planner → reviewer |
| B4 | Codex direct implementation |
| B5 | kagent planner → Codex → kagent reviewer |
| B6 | Cursor direct implementation |
| B7 | Cursor → kagent planner → Cursor implementation |
| B8 | True A2A worker adapter when available |

### Metrics to capture

Transport latency, streaming behavior, time-to-completion, A2A task success rate, context continuation fidelity, reliability (retries/failures), agent hop count, MCP call count, token usage, estimated cost, test pass rate, revision cycles, reviewer finding count, schema compliance, recovery behavior after partial failure.

### Observability

Use kagent OpenTelemetry → Jaeger. Separate spans or labels for:

- client (Cursor/Codex/human)
- controller
- A2A transport
- per-agent execution
- LLM inference
- MCP tool calls

---

## Strict Separations (unchanged)

| Experiment | Track | Blocks A2A education? |
|------------|-------|------------------------|
| Direct A2A L6 (agent-mediated MCP tool) | L6 | **No** |
| IDE-to-Kubernetes correlation (I4) | I4 | **No** |
| Cursor I3 context continuation | I3 | **No** (was incorrectly treated as spine) |

Direct A2A L6 ≠ Cursor/Codex I4. A helper-owned `agent_mcp_trace.py` dispatch does not prove I4.

---

## Related Documents

| Document | Role |
|----------|------|
| `docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md` | Phase table, PR exit gates, lab procedures |
| `docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md` | Repo-wide delivery ordering |
| `docs/architecture/EDUCATIONAL-LANES-ARCHITECTURE.md` | Stable-core vs lab boundaries |
| `docs/reference/kagent-capability-matrix.md` | L0–L7 and I0–I5 definitions |
| `evidence/kagent/README.md` | Current capability decisions |
| `docs/runbooks/kagent-a2a-examples.md` | E1–E5 run procedures |

---

## Historical Note

Gate 0 roadmap baseline remains at `090ad52` (2026-08-05). This north-star addendum (2026-08-07) revises **priority and sequencing** only. Dated phase evidence under `evidence/kagent/` is not rewritten.
