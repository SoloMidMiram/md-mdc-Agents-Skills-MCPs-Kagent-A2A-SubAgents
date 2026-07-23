# B01: Review direct MCP success

## Scenario
You are reviewing a contribution that claims "agent-mediated MCP invocation is proven" based on a direct `mcp_session_smoke.py` run that called `tools/call` against the kagent-tool-server MCP endpoint.

## Available evidence
- `evidence/kagent/educational-practice-phase-5b-direct-mcp.md` -- documents a successful direct MCP session with `tools/list` and `tools/call` using a session-reusing helper
- `evidence/kagent/educational-practice-phase-5e-agent-mediated-mcp.md` -- documents the correlated agent-mediated attempt (exit 1, L6 Not proven)
- `evidence/kagent/README.md` -- current status index showing L6 Not proven
- `docs/reference/kagent-capability-matrix.md` -- L6 requires "An A2A request causes the agent to call a real MCP tool and return tool-derived output"

## Task
Does the available evidence support the claim that "agent-mediated MCP invocation is proven"? If not, classify the claim correctly and explain why direct MCP evidence is insufficient.
