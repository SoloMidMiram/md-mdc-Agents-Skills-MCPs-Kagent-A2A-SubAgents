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

## Native IDE-Federation Track

This parallel track describes client access to the controller's native MCP
surface. It does not renumber or replace L0-L7.

| Level | Required evidence | Allowed claim | Insufficient evidence |
|-------|-------------------|---------------|-----------------------|
| I0 Controller MCP reachable | Controller `/mcp` completes `initialize` with a negotiated protocol and session | Native MCP endpoint is reachable | Service port or REST card alone |
| I1 Controller contract known | Same session `tools/list` exposes the reviewed agent tools and no unreviewed privileged tool | Client contract is known | Documentation or a guessed tool list |
| I2 Agent discovery works | `list_agents` structured content contains the target agent reference | The target agent is discoverable | A card or REST endpoint |
| I3 IDE-to-kagent delegation works | A real IDE client (Cursor lead-client gate; Codex tracked as I3-Codex) completes bounded `invoke_agent`, receives the required agent response, and succeeds at agent-context continuation via `context_id` | A real IDE client can delegate to the approved agent through native MCP | Generic Python diagnostics alone; MCP session reuse alone; HTTP 200 paired with a provider or agent error; helper exit 0 without a dated IDE run |
| I4 IDE-to-Kubernetes delegation works | One I3 invocation joins to qualifying same-task L6 output | IDE delegation produced verified Kubernetes results | I3 alone or direct MCP evidence |
| I5 Native workflow repeatable | Fresh setup, restart, both-client acceptance, and cleanup complete | Native IDE workflow is repeatable | One running-machine snapshot; a single-client I3 pass |

`invoke_agent` is a dispatcher over agent identity. Codex/Cursor tool allowlisting
constrains which controller tools the client may call; it does not constrain which
agent refs `list_agents` can return or which agent `invoke_agent` may target.
Strict approved-agent inventory policy is therefore required for IDE acceptance.

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
- I3 does not imply L6. A dependable IDE-to-Kubernetes claim requires both I4
  and L6 evidence from the same bounded workflow.
- I3-Cursor is the lead-client gate. I3-Codex is recorded separately. I5
  requires both clients.
- Generic Python controller diagnostics are prerequisites for I0-I2 and for
  preparing an IDE run; they are not sufficient for I3.
- Native controller MCP is the preferred northbound seam. Direct A2A helpers
  remain protocol and evidence diagnostics, not the default Cursor/Codex
  integration path.
