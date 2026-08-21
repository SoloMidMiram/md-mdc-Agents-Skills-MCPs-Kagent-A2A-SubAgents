# Client surface: Cursor/Codex → kagent A2A (PR6 evidence note)

**Status:** DONE (docs + wiring guide; live A2A unchanged)  
**Date:** 2026-08-20  
**Cloud-only:** yes (`agent-coder`)

## Path

Cursor/Codex → (terminal or MCP) → kagent controller `:8083` → `supervisor-agent` → LiteLLM `agent-coder`

## Docs

- `docs/runbooks/kagent-a2a-clients.md`
- `docs/LOCAL_MODELS_FROZEN.md`

## Re-run smoke from an IDE agent

```powershell
cd F:\Git\MCPtest
python scripts/kagent/test-a2a-agent.py task `
  --agent supervisor-agent `
  --timeout 360 `
  --prompt "Plan and review: minimal hello-world FastAPI health endpoint." `
  --output json
```
