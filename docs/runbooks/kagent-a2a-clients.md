# Cursor / Codex as A2A clients — wiring guide

This is a wiring guide, not an interoperability proof. It documents how to
invoke the already-proven multi-agent A2A path from an IDE agent terminal. No
real Cursor or Codex session has completed the I3/I4 pinning trace yet.

## Goal

```
Cursor or Codex (terminal)
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

Use `scripts/kagent/test-a2a-agent.py` from a Cursor Agent / Codex terminal
tool. No extra MCP server required.

### B. Cursor MCP → kagent controller (optional)

Point a small MCP server (or the existing controller MCP smoke) at:

- Health: `GET http://127.0.0.1:8083/health`
- A2A: `POST http://127.0.0.1:8083/api/a2a/kagent/supervisor-agent` with `message/stream`

Keep secrets out of MCP config: only controller URL + agent name. The LiteLLM
master key stays in the cluster Secret `kagent-litellm`.

Existing smoke references:

- `scripts/kagent/controller_mcp_smoke.py`
- `scripts/kagent/mcp_session_smoke.py`

### C. Codex

Same A2A JSON-RPC as above. Prefer the supervisor for multi-agent runs.

## Client checklist

1. LiteLLM up with `-BindHost 0.0.0.0`
2. `kubectl -n kagent port-forward svc/kagent-controller 8083:8083`
3. Agents Ready: `supervisor-agent`, `planner-agent`, `reviewer-agent`
4. Invoke the cloud alias only (`agent-coder`)
5. Timeout ≥ 300s for the supervisor

## Evidence classification

| Claim | Decision |
|-------|----------|
| Multi-agent A2A execution (supervisor → planner → reviewer) | Proven (L4) — `evidence/a2a/run001/` |
| Cursor/Codex wiring guide | Documented (this runbook) |
| Real Cursor/Codex interoperability | Not attempted / Not proven |
| IDE-federation I3 | Blocked; I4 unproven |

## Evidence

- Gateway path: `evidence/runtime/kagent-litellm-success.md`
- Multi-agent A2A run: `evidence/a2a/run001/`
