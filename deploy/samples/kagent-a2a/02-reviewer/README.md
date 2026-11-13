# Phase 2 — Reviewer Agent

Active runs use only LiteLLM `agent-coder`; see `docs/LOCAL_MODELS_FROZEN.md`.
A cloud failure is Blocked; local/Ollama fallback is forbidden.

## Learning objective

Prove a direct A2A dispatch to a reviewer agent that validates a planner JSON
artifact. The client coordinates planner output → reviewer input (not yet
supervisor delegation).

## Prerequisites

- E1 planner agent deployed and proven
- `reviewer-agent` manifest applied after `planner-agent`

## Input

JSON prompt body:

```json
{
  "request": "Plan a minimal hello-world Telegram bot.",
  "proposed_plan": { "...planner artifact..." }
}
```

## Agents involved

- `reviewer-agent` (namespace `kagent`)

## Allowed tools

None.

## Expected output

```json
{
  "verdict": "approve",
  "findings": [],
  "missing_requirements": [],
  "required_changes": []
}
```

(`verdict` may be `revise`.)

## Pass criteria

- Reviewer agent Accepted/Ready
- Direct A2A dispatch succeeds with valid reviewer JSON

## Fail criteria

- Invalid input JSON, missing task ID, or contract validation failure

## What it proves

- Second independent A2A role with a distinct output contract
- Manual two-hop workflow (client coordinates planner → reviewer)

## What it does NOT prove

- Supervisor agent-as-tool delegation (see `03-supervisor/`)
- L6, I3, I4, MCP, Codex

## Evidence location

`evidence/kagent/experiments/YYYY-MM-DD-phase2-reviewer-<run-id>.json`

## Cleanup

```powershell
kubectl delete -f deploy/samples/kagent-a2a/02-reviewer/reviewer-agent.yaml
```

## Commands

```powershell
# After E1 planner smoke — save planner JSON to a prompt file, then:
python scripts/kagent/experiments/run_a2a_example.py `
  --agent reviewer-agent `
  --prompt-file evidence/kagent/experiments/tmp/planner-prompt.json `
  --output json
```
