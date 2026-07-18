# Review: kagent Educational Practice Phases 0-2

## Review Summary

The implementation matches the educational roadmap for `phase_0_observe`,
`phase_1_ui_and_card`, and `phase_2_degraded_mcp_understanding`.

The evidence correctly proves capability levels L0 through L3 and avoids
claiming L4 through L7. The work stays inside the planned educational scope:
observe the kagent control plane, inspect accepted agents, fetch agent
metadata/card details, and understand why `RemoteMCPServer Accepted=False` is
expected before a backing MCP server exists.

## Plan Compliance

| Planned item | Review result | Evidence |
|--------------|---------------|----------|
| Run health checker | Complete | `check-kagent-health.ps1` exit 0; 17/17 pods ready; 11/11 agents accepted+ready |
| Inspect pods and agents | Complete | `kubectl get pods`; `kubectl get agent` outputs summarized |
| Inspect RemoteMCPServer status | Complete | both RemoteMCPServers present; 0 accepted |
| Open or verify kagent UI | Complete for HTTP reachability | UI service returned HTTP 200 through port-forward |
| Fetch sample agent details | Complete | `test-a2a-agent.py card` and REST API returned accepted/deployment-ready metadata |
| Explain `RemoteMCPServer Accepted=False` | Complete | DNS lookup failure documented for `kagent-tool-server.kagent` |
| Apply L0-L7 grid | Complete | L0-L3 proven; L4-L7 explicitly not proven |
| Honor guardrails | Complete | no task/tool execution claim is made from agent acceptance or card success |

## Capability Decision

| Level | Decision | Reason |
|-------|----------|--------|
| L0 Config exists | Proven | manifests and kagent scripts exist |
| L1 Control plane healthy | Proven | all pods running/ready and health checker exits 0 |
| L2 Agent accepted/ready | Proven | all 11 agents are Accepted=True and Ready=True |
| L3 Agent details/card observable | Proven | REST/card inspection returns full metadata |
| L4 A2A task dispatch works | Not proven | task dispatch was not tested here and is known to be unresolved |
| L5 RemoteMCPServer accepted | Not proven | both RemoteMCPServers are Accepted=False |
| L6 Tool invocation proven | Not proven | no MCP tool invocation evidence exists |
| L7 Repeatable workshop/install path | Not proven | no bootstrap or cleanup automation was exercised |

## Guardrail Review

- Agent `Accepted=True` is treated as reconciliation evidence only.
- Card and REST metadata success are not treated as task success.
- `RemoteMCPServer Accepted=False` is kept inside the card/acceptance lab boundary.
- The evidence does not reuse L2 or L3 results to imply L5 or L6.
- The runbook restart-count update is a good durability improvement because it avoids stale exact restart numbers.

## Review Notes

The only adjustment made during review was wording around the UI check. HTTP 200
proves the service endpoint is reachable through port-forward. It does not, by
itself, prove rendered UI behavior unless a browser snapshot, screenshot, or
manual rendered-page observation is recorded.

This does not block phases 0-2 because the educational plan only requires UI
reachability for this practice. Future UI-render validation should capture
browser evidence explicitly if it is used as a stronger claim.

## Next Action

Proceed to `phase_3_truthful_a2a_dispatch`:

1. Make `task` fail when dispatch is unavailable.
2. Keep `probe` informational and neutral.
3. Keep `card` scoped to metadata/card retrieval.
4. Make `both` pass only when both card validation and real task dispatch pass.
5. Record the result in a new evidence file before claiming L4.
