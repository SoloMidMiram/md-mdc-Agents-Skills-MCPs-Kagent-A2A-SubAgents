# Cursor / Codex as A2A clients (PR6)

Cloud-only. Local models frozen — see `docs/LOCAL_MODELS_FROZEN.md`.

## Goal

```
Cursor or Codex
  → MCP tool surface (this lab)
  → kagent supervisor-agent (A2A)
  → planner / reviewer (A2A Agent tools)
  → LiteLLM alias agent-coder (cloud)
```

Do **not** break the working A2A path. This adds a client surface and docs.

## Working A2A (already proven)

| Piece | Value |
|-------|--------|
| Controller | `http://127.0.0.1:8083` (port-forward `svc/kagent-controller`) |
| Supervisor | `supervisor-agent` |
| ModelConfig | `litellm-gateway-model-config` → `agent-coder` @ `host.docker.internal:4000/v1` |
| Helper | `python scripts/kagent/test-a2a-agent.py task --agent supervisor-agent --timeout 360` |

## MCP wiring options

### A. Direct A2A from a script (lab default)

Use `scripts/kagent/test-a2a-agent.py` or `scripts/kagent/capture-a2a-evidence.py` from Cursor Agent / Codex terminal tools. No extra MCP server required.

### B. Cursor MCP → kagent controller (optional)

Point a small MCP server (or existing controller MCP smoke) at:

- Health: `GET http://127.0.0.1:8083/health`
- A2A: `POST http://127.0.0.1:8083/api/a2a/kagent/supervisor-agent` with `message/stream`

Keep secrets out of MCP config: only controller URL + agent name. LiteLLM master key stays in the cluster Secret `kagent-litellm`.

Existing smoke references:

- `scripts/kagent/controller_mcp_smoke.py`
- `scripts/kagent/mcp_session_smoke.py`

### C. Codex

Same A2A JSON-RPC as above. Prefer supervisor for multi-agent; use `litellm-gateway-tool-agent` for single-tool loops.

## Client checklist

1. LiteLLM up with `-BindHost 0.0.0.0`
2. `kubectl -n kagent port-forward svc/kagent-controller 8083:8083`
3. Agents Ready: `supervisor-agent`, `planner-agent`, `reviewer-agent`
4. Invoke cloud alias only (`agent-coder`)
5. Timeout ≥ 300s for supervisor

## Evidence

- PR2: `evidence/runtime/kagent-litellm-success.md`
- PR3: `evidence/kagent/tool-loop-run001/`
- PR4: `evidence/a2a/run001/`
