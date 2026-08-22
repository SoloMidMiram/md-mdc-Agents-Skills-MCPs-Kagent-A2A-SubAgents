# Client surface: Cursor/Codex → kagent A2A

**Status:** Documented (wiring guide); no real Cursor/Codex invocation recorded
**Date:** 2026-08-20
**Cloud-only:** yes (`agent-coder`)

## Path

Cursor/Codex → (terminal or MCP) → kagent controller `:8083` → `supervisor-agent` → LiteLLM `agent-coder`

## Docs

- `docs/runbooks/kagent-a2a-clients.md`

## Evidence classification

| Claim | Decision |
|-------|----------|
| Multi-agent A2A execution | Proven (L4) — `evidence/a2a/run001/` |
| Cursor/Codex wiring guide | Documented |
| Real Cursor/Codex interoperability | Not attempted / Not proven |
| IDE-federation I3 | Blocked; I4 unproven |

## Re-run smoke from an IDE agent

```powershell
python scripts/kagent/test-a2a-agent.py task `
  --agent supervisor-agent `
  --timeout 360 `
  --prompt "Plan and review: minimal hello-world FastAPI health endpoint." `
  --output json
```
