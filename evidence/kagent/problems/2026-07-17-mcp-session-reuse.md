# Educational Problem Record: MCP session ID not reused on tools/call

## Metadata

| Field | Value |
|-------|-------|
| Date and timezone | 2026-07-16 (original failure); record dated 2026-07-17 UTC+3:30 |
| Lane | kagent |
| Exercise or phase | phase_5_real_agentic_work / Subphase 5B direct MCP smoke |
| Environment | Docker Desktop Kubernetes (`docker-desktop`), namespace `kagent` |
| Relevant versions | kagent tools image `ghcr.io/kagent-dev/kagent/tools:0.0.13`; MCP request `protocolVersion` `2024-11-05` |
| Severity | P1 |
| Status | Fixed (live confirmed 2026-07-17) |

## Intended Learning and Expected Result

Complete a direct MCP session lifecycle against `kagent-tool-server`: `initialize`,
preserve the server-issued session, then call `k8s_get_resources` successfully.
Observe that direct MCP success is server evidence only and does not prove L4 or L6.

## Actual Result

`initialize` returned HTTP 200 with a valid JSON-RPC result. The subsequent
`tools/call` for `k8s_get_resources` returned HTTP 400 because the
`Mcp-Session-Id` response header from initialize was not captured and reused.
Recorded in `evidence/kagent/educational-practice-phase-5.md` (Subphase 5B).

## Safety and Containment

- Side effects allowed: temporary in-cluster Python client pod for the phase 5 probe
- Side effects observed: temporary pod created for the smoke attempt
- Cleanup performed: temporary probe resource removed after the attempt
- Production/external impact: None

## Minimal Reproduction

```text
# Historical phase 5 pattern (session header omitted on tools/call):
POST /mcp initialize  -> HTTP 200 + Mcp-Session-Id (ignored)
POST /mcp tools/call  -> HTTP 400
```

Corrected helper (after this record's resolution):

```powershell
kubectl port-forward -n kagent svc/kagent-tool-server 8000:8000
python scripts/kagent/mcp_session_smoke.py --url http://127.0.0.1:8000/mcp
```

## Layer and Classification

- Zone/layer: kagent education / MCP Streamable HTTP client session lifecycle
- Problem class: Product defect in the educational client script (missing session reuse)
- Observed facts:
  - initialize succeeded in phase 5; tools/call without session header failed with HTTP 400
  - RemoteMCPServer remained Accepted=True (L5 unchanged)
  - live helper run (2026-07-17): negotiated `2024-11-05`, initialized HTTP 202,
    schema properties include `resource_type` and `namespace`, tools/call exit 0,
    cleanup `deleted`, kubectl pod count matched summary (18)
- Assumptions still unverified: none for the direct-MCP session path; L4/L6 remain unproven

## Root Cause

**Confirmed root cause:** the client did not capture and reuse the server-issued
session identifier on the follow-up request. A successful session-reusing
`tools/call` via `scripts/kagent/mcp_session_smoke.py` closed this hypothesis
([phase 5b](../educational-practice-phase-5b-direct-mcp.md)).

## Resolution or Workaround

Smallest correction: reusable helper `scripts/kagent/mcp_session_smoke.py` that:

1. initializes and validates the JSON-RPC result;
2. captures and validates `Mcp-Session-Id`;
3. always sends `notifications/initialized`;
4. discovers the tool via `tools/list` and validates arguments against `inputSchema`;
5. calls `tools/call` with the same session ID;
6. attempts session DELETE on close.

Deterministic tests: `tests/kagent/test_mcp_session_smoke.py`.

## Validation

| Check | Result | Evidence |
|-------|--------|----------|
| Minimal reproduction | Pass (live) | [phase 5b](../educational-practice-phase-5b-direct-mcp.md) exit 0 |
| Negative/failure case | Pass (deterministic) | missing session, initialized rejection, schema failures covered in tests |
| Stable-core regression checks | Pass | lab-only script; `uv run --python 3.12 pytest tests/kagent/test_mcp_session_smoke.py` → 39 passed |
| Security/policy checks | Pass | no RBAC broadening; loopback URL default; no secrets in output |
| Cleanup | Pass | live `cleanup: deleted`; unit coverage for 405 unsupported |

## Capability Decision

- Proven: direct MCP tool invocation with session reuse (server evidence); helper and deterministic tests
- Not proven: L4; L6
- Previous claim corrected: phase 5 “direct tools/call not proven” closed by phase 5b without rewriting phase 5

## Reflection

- Why was this difficult? Session state lives in an HTTP header, not the JSON-RPC body; a successful initialize looks complete until the next stage fails.
- Which earlier gate should have caught it? A staged MCP client that treats initialize, initialized, tools/list, and tools/call as separate gates with exit codes.
- What should a learner notice next time? Transport HTTP success ≠ JSON-RPC success ≠ tool execution; missing session is a protocol failure, not “server down.”
- Knowledge promotion: evidence + runbook command + automated tests. Not a new global AGENTS rule unless it recurs outside this lab.

## Follow-up Owner

- Canonical roadmap item: Path B direct MCP session reuse (phase 5 follow-up) — closed for direct MCP
- Files updated: phase 5b evidence, evidence index, runbook, helper, tests
- Closure condition: met for direct MCP; L4/L6 remain open
