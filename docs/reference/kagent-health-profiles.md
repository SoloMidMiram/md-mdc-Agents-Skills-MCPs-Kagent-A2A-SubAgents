# kagent Health Profiles

Canonical definitions for capability-gated health checks in the local kagent
educational lab. Executable implementation:
`scripts/kagent/check-kagent-health.ps1` and `scripts/kagent/KagentHealth.psm1`.

## Why profiles exist

The same cluster can be healthy for card/metadata work and unhealthy for A2A
dispatch or agent-mediated tool execution. A single permissive “healthy” result
overclaims. Profiles make the capability under test explicit.

## Profiles

| Profile | Requires | Expected on current lab | Automated decision when pass |
|---------|----------|-------------------------|------------------------------|
| `CardLab` (default) | Namespace reachable; pods Running with complete positive readiness; agents Accepted=True and Ready=True | Pass | Current card-lab readiness |
| `DirectMcpServer` | CardLab + `kagent-tool-server` Accepted=True + sanitized direct MCP smoke JSON (`exitCode=0`, `sessionId=present`, `toolCallSucceeded=true`, tool `k8s_get_resources`, `error=null`) | Pass | The supplied direct-smoke contract and current acceptance gates pass |
| `A2ADispatch` | CardLab + accepted/completed task or message dispatch with non-empty identifier | Pass when helper JSON proves dispatch (phase 5d) | Structured dispatch gate; L6 still unproven |
| `FullMcpExecution` | CardLab + tool-server Accepted=True + one Phase 5E task whose embedded A2A dispatch and agent-mediated tool/result/source evidence all validate | Fail until live correlated tool proof exists ([phase 5e](../../evidence/kagent/educational-practice-phase-5e-agent-mediated-mcp.md)) | Single-task transport/protocol/dispatch/freshness/target/source/tool/result gates; L6 still Not proven live |

Unrelated RemoteMCPServer degradation (for example `kagent-grafana-mcp`) is
informational for `CardLab` and must not fail that profile.

Profile evaluation recomputes freshness and validates target, source-file
content, task-to-tool correlation, and result arrays. A pass validates the
supplied educational contract; promotion in the canonical evidence index still
requires a dated live record and human review of the sanitized response/source
proof. It does not turn deterministic fixtures into live L6 evidence.

## CLI

```powershell
.\scripts\kagent\check-kagent-health.ps1 -Profile CardLab -OutputFormat Human

.\scripts\kagent\check-kagent-health.ps1 `
  -Profile DirectMcpServer `
  -DirectMcpResultPath .\direct.json `
  -OutputFormat Json

.\scripts\kagent\check-kagent-health.ps1 `
  -Profile A2ADispatch `
  -ControllerUrl http://127.0.0.1:8083

.\scripts\kagent\check-kagent-health.ps1 `
  -Profile FullMcpExecution `
  -ControllerUrl http://127.0.0.1:8083 `
  -AgentToolEvidencePath .\agent-tool.json
```

## Exit codes

| Code | Meaning |
|-----:|---------|
| 0 | Selected profile passed |
| 1 | One or more capability gates failed |
| 2 | Invalid arguments, missing required evidence, or malformed evidence |
| 3 | Collector/transport failure (kubectl missing, controller unreachable) |

A known unsupported capability is a gate failure (exit 1), not a script crash.

## Evidence contracts

### Direct MCP (`DirectMcpServer`)

Accept sanitized JSON from `mcp_session_smoke.py` only. Required fields:

- `exitCode` numeric `0`
- `sessionId` exactly `"present"` (never a raw session id)
- `toolCallSucceeded` true
- `tool` equals `k8s_get_resources`
- `error` null

Initialization alone is not a pass.

The current schema does not bind the JSON to a target cluster, URL, namespace,
or freshness window. Produce it in the same validation run and retain the dated
source record; schema-level provenance is a tracked follow-up.

**Session cleanup semantics:** The smoke script exits non-zero when session
cleanup fails (e.g. DELETE returns 500 or a transport error). This prevents
silent session leaks. HTTP 405 (Method Not Allowed) is a declared compatibility
policy -- the server explicitly signals it does not support DELETE, which is
benign and does not fail the gate.

**Non-claim:** Direct MCP success does not prove L4 or L6.

### Agent-mediated (`FullMcpExecution`)

Consume versioned nested JSON from `agent_mcp_trace.py --output json` (or an
equivalent file). See
[kagent-agent-mediated-mcp-evidence.md](kagent-agent-mediated-mcp-evidence.md).

Required for a helper-contract pass: exact nested schema 1.0; one embedded A2A
transport/protocol/dispatch with agreeing request/task/state fields;
`success=true`; `toolInvocation.observed=true` for `k8s_get_resources` /
`kagent-tool-server` with normalized `pod`/`kagent` arguments; A2A task id
matching the correlated tool id; recomputed `result.matched=true` and
`returnedThroughA2A=true`; computed freshness <= 900s; observed
`docker-desktop` target; and a canonical repo-contained source JSON whose
timestamp, target, identifiers, marker proof, and result arrays match the outer
record. The complete decision and live helper exit must agree.

`FullMcpExecution` sends only the Phase 5E dispatch and derives its A2A gate
from that record. If a caller also supplies Phase 5D A2A evidence, its task id
must equal the Phase 5E task id.

Reject `evidenceKind = "direct-mcp-tool-call"` and other shortcuts such as
RemoteMCPServer acceptance alone, agent Accepted=True alone, tools/list, L4
dispatch alone, or probe success.

**Non-claim:** A profile pass is promotion-eligible evidence only after a dated
live correlated record; Phase 5E live attempt remains L6 Not proven.

### A2A dispatch (`A2ADispatch`)

Consume versioned JSON from `test-a2a-agent.py --output json` only. See
[kagent-a2a-dispatch-evidence.md](kagent-a2a-dispatch-evidence.md).

Required for a helper-contract pass: exact `schemaVersion == 1.0`; agreement
among helper exit, decision, transport, protocol, and dispatch fields; a 2xx
`message/stream` response with matching JSON-RPC ID and no error; and a
non-empty `taskOrMessageId` with an accepted exact response shape. The
collector never inserts a missing schema version.

**Non-claim:** Profile pass does not prove L6.

## Architecture

- `KagentHealth.psm1` — pure parsing and profile evaluation (no kubectl)
- `check-kagent-health.ps1` — collection, evidence loading, optional A2A /
  agent-mcp helper invocation, human/JSON output, exit code
- `agent_mcp_trace.py` — nested L6 evidence producer for FullMcpExecution

## Related

- Agent-mediated evidence schema: `docs/reference/kagent-agent-mediated-mcp-evidence.md`
- A2A evidence schema: `docs/reference/kagent-a2a-dispatch-evidence.md`
- Capability levels: `docs/reference/kagent-capability-matrix.md`
- Status index: `evidence/kagent/README.md`
- Runbook: `docs/runbooks/local-kagent-a2a-lab.md`
