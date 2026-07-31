# kagent Capability Matrix

This file is the canonical definition of the kagent educational capability
levels. Current decisions and evidence links live in `evidence/kagent/README.md`.

| Level | Required evidence | Allowed claim | Insufficient evidence |
|-------|-------------------|---------------|-----------------------|
| L0 Config exists | Relevant manifests and scripts exist | Resources are defined | Repository files alone do not prove deployment |
| L1 Control plane healthy | Pods, services, and controller health are observable | Control plane is available | Agent readiness or tool operation |
| L2 Agent accepted/ready | Agent condition is accepted and workload is ready | Agent reconciles successfully | A2A dispatch |
| L3 Card/details observable | REST details or agent card is returned and validated | Metadata, skills, and model are observable | Task acceptance |
| L4 A2A dispatch works | A valid task/message is accepted or completed through A2A | A task crossed the A2A boundary | Endpoint registration or protocol errors |
| L5 RemoteMCPServer accepted | Target RemoteMCPServer is `Accepted=True` and tools are discovered | Controller can reach and inspect the MCP endpoint | Any tool was invoked |
| L6 Agent tool invocation proven | An A2A request causes the agent to call a real MCP tool and return tool-derived output | One end-to-end agentic tool path works | Direct MCP initialize/call, logs showing configuration, or L5 |
| L7 Repeatable workshop | Fresh documented setup reaches its target with cleanup and evidence capture | Lab can be replayed by a new learner | A one-machine snapshot |

## Promotion Rules

- Levels are independent evidence gates; a higher numbered observation does not
  automatically prove missing lower gates.
- A direct MCP tool call is useful server evidence but is outside L0-L7 unless it
  is performed through the agent path required by L6.
- Every promotion requires a dated evidence record containing the successful
  request and response or command and exit status.
- A health-profile pass validates its configured gates; it does not replace a
  dated live promotion review. Evidence-backed L4/L6 promotion additionally
  requires a recognized response shape and a correlated task, agent, tool
  trace/result, target environment, observation time, and bounded source proof.
  L6 must derive dispatch and tool/result evidence from the same task and
  independently recompute freshness and result matching. L6 machine evidence uses
  [kagent-agent-mediated-mcp-evidence.md](kagent-agent-mediated-mcp-evidence.md).
- A failed attempt stays `Not proven`; it is not a partial pass.
