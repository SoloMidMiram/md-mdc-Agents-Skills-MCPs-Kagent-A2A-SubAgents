# E1 — Planner Agent

Active runs use only LiteLLM `agent-coder`; see `docs/LOCAL_MODELS_FROZEN.md`.
A cloud failure is Blocked; local/Ollama fallback is forbidden.

## Learning objective

Prove a single bounded A2A dispatch to an in-cluster planner agent that returns a
structured JSON plan without MCP tools or external clients.

## Prerequisites

- Local kagent lab on `docker-desktop` ([local kagent A2A lab](../../../../docs/runbooks/local-kagent-a2a-lab.md))
- Cloud-only `agent-coder` qualified via the LiteLLM gateway runbook
- `litellm-gateway-model-config` applied and Accepted

## Input

Default prompt:

```text
Plan a minimal hello-world Telegram bot.
```

## Agents involved

- `planner-agent` (namespace `kagent`)

## Allowed tools

None. `tools` omitted from manifest.

## Expected output

JSON object with keys: `goal`, `constraints`, `files`, `acceptance_criteria`,
`tests`, `risks`.

## Pass criteria

- Agent `Accepted` and deployment ready
- One `message/stream` dispatch succeeds
- Task ID present
- Output validates against planner contract

## Fail criteria

- Missing task ID, provider error, timeout, or non-JSON output

## What it proves

- Lane A single-agent A2A education baseline (E1)
- DeepSeek-backed bounded planning inside kagent

## What it does NOT prove

- L6 MCP tool invocation
- I3/I4 Cursor interop
- Multi-agent delegation (see `03-supervisor/`)
- Codex or external workers

## Evidence location

`evidence/kagent/experiments/YYYY-MM-DD-e1-planner-<run-id>.json`

## Cleanup

```powershell
kubectl delete -f deploy/samples/kagent-a2a/01-planner/planner-agent.yaml
```

## Commands

```powershell
kubectl apply -f deploy/samples/kagent/litellm-gateway-model-config.yaml
kubectl apply -f deploy/samples/kagent-a2a/01-planner/planner-agent.yaml
python scripts/kagent/experiments/run_a2a_example.py `
  --agent planner-agent `
  --prompt "Plan a minimal hello-world Telegram bot." `
  --output json
```
