# E2 — Supervisor Agent (multi-agent A2A)

## Learning objective

Prove genuine kagent-native multi-agent delegation: supervisor invokes
`planner-agent` and `reviewer-agent` as Agent tools over A2A.

## Prerequisites

- `planner-agent` and `reviewer-agent` Accepted/Ready
- Agent-tool CRD shape pinned in `supervisor-agent.yaml` (see manifest comment)

## Input

```text
Plan and review a minimal hello-world Telegram bot.
```

## Agents involved

- `supervisor-agent` (orchestrator)
- `planner-agent` (Agent tool)
- `reviewer-agent` (Agent tool)

## Allowed tools

Only:

```yaml
- type: Agent
  agent:
    ref: planner-agent
- type: Agent
  agent:
    ref: reviewer-agent
```

## Expected output

Composite JSON with `summary`, `plan`, `review`, and `verdict`.

## Pass criteria

- Supervisor dispatch succeeds
- Final artifact validates supervisor contract
- Operator observes both sub-agent hops (controller logs or trace)

## Fail criteria

- Supervisor accepts dispatch but returns non-JSON or empty delegation evidence
- More than one revision cycle or use of disallowed tools

## What it proves

- Lane A E2: agent-as-tool multi-hop A2A inside kagent
- Bounded supervisor orchestration rules

## What it does NOT prove

- L6 MCP tool invocation
- I3/I4 IDE correlation
- Codex worker loop or Telegram capstone

## Evidence location

`evidence/kagent/experiments/YYYY-MM-DD-e2-supervisor.json`

## Cleanup

```powershell
kubectl delete -f deploy/samples/kagent-a2a/03-supervisor/supervisor-agent.yaml
kubectl delete -f deploy/samples/kagent-a2a/02-reviewer/reviewer-agent.yaml
kubectl delete -f deploy/samples/kagent-a2a/01-planner/planner-agent.yaml
```

## Commands

```powershell
kubectl apply -f deploy/samples/kagent-a2a/03-supervisor/supervisor-agent.yaml
python scripts/kagent/experiments/run_a2a_example.py `
  --agent supervisor-agent `
  --prompt "Plan and review a minimal hello-world Telegram bot." `
  --output json
```

## Agent-tool CRD observation (2026-08-07)

```text
kubectl explain agent.spec.declarative.tools --api-version=kagent.dev/v1alpha2
```

Observed shape for Agent tools on cluster `kagent.dev/v1alpha2` (2026-08-07):

```yaml
type: Agent
agent:
  name: planner-agent
```

(`agent.ref` is not accepted on the pinned controller CRD.)
