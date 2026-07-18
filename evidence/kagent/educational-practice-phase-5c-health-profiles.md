# kagent Educational Practice: Phase 5C Health Profiles

## Meta

| Field | Value |
|-------|-------|
| Date | 2026-07-17 |
| Timezone | UTC+3:30 |
| Cluster | Docker Desktop (`docker-desktop`) |
| Namespace | `kagent` |
| Practice | `phase_5c_truthful_health_profiles` |
| PowerShell | Windows PowerShell / pwsh |
| Pester | 3.4.0 (38/38 module tests passed) |

## Commands (read-only)

```powershell
.\scripts\kagent\check-kagent-health.ps1 -Profile CardLab -OutputFormat Json

.\scripts\kagent\check-kagent-health.ps1 `
  -Profile DirectMcpServer `
  -DirectMcpResultPath evidence/kagent/tmp/direct-mcp-live.json `
  -OutputFormat Json

.\scripts\kagent\check-kagent-health.ps1 `
  -Profile A2ADispatch `
  -ControllerUrl http://127.0.0.1:8083 `
  -OutputFormat Json

.\scripts\kagent\check-kagent-health.ps1 `
  -Profile FullMcpExecution `
  -ControllerUrl http://127.0.0.1:8083 `
  -AgentToolEvidencePath evidence/kagent/tmp/insufficient-agent-evidence.json `
  -DirectMcpResultPath evidence/kagent/tmp/direct-mcp-live.json `
  -OutputFormat Json
```

Direct MCP JSON was freshly produced with `mcp_session_smoke.py` (exit 0) against
an existing local port-forward to `kagent-tool-server`.

## Decisions

| Profile | passed | exitCode | Key gate reason |
|---------|--------|----------|-----------------|
| CardLab | true | 0 | 18/18 pods ready; 11/11 agents accepted+ready |
| DirectMcpServer | true | 0 | tool-server Accepted=True; direct MCP evidence validates |
| A2ADispatch | false | 1 | `tasks/sendTask` returned -32601 method not found |
| FullMcpExecution | false | 1 | A2A dispatch failed; `evidenceKind direct-mcp-tool-call` insufficient |

`kagent-grafana-mcp Accepted=False` remained informational under CardLab.

## Capability claims

Allowed:

- CardLab passed.
- Direct MCP server profile passed.
- A2A dispatch profile failed truthfully.
- Full MCP execution profile failed truthfully.
- Profile semantics are deterministic and tested (Pester 38/38).

Blocked / non-claims:

- A2A works.
- Agent-mediated tool invocation works.
- L4 or L6 is partially proven.
- Full execution is healthy.
- Direct MCP success proves agent behavior.

## Related

- Problem record: [health profile overclaim](problems/2026-07-17-health-profile-overclaim.md)
- Reference: [kagent-health-profiles.md](../../docs/reference/kagent-health-profiles.md)
- Prior: [phase 5](educational-practice-phase-5.md), [phase 5B](educational-practice-phase-5b-direct-mcp.md)

## Review Addendum — 2026-07-17

This addendum records an independent post-implementation review; it does not
rewrite the original observations above.

- PowerShell 7.6.3 and Windows PowerShell 5.1 both parsed and imported the
  module after replacing its sole non-ASCII arrow with ASCII.
- Pester 3.4.0 passed 38/38 under both runtimes. Pester 5.7.1 is installed and
  discovered all 38 tests, but rejected their intentional legacy `Should Be`
  syntax; this is a migration boundary, not an unavailable prerequisite or a
  passing Pester 5 suite.
- Python 3.12 MCP tests passed 39/39 and Ruff reported no findings.
- Live profile rerun returned `CardLab=0`, `DirectMcpServer=0`,
  `A2ADispatch=1`, and `FullMcpExecution=1`. The negative profiles again
  observed `tasks/sendTask` `-32601`; Full additionally rejected
  `evidenceKind=direct-mcp-tool-call`.
- Human output retained `Recent Events` and `Service Endpoints` sections.
- An already-running controller port-forward was reused; the review did not
  start or stop that user-owned process and did not mutate cluster resources.

Review qualification: the direct result file satisfied the sanitized schema,
but the current schema does not enforce freshness/target provenance. Positive
A2A and Full profile promotion remains blocked on recognized response shapes,
structured helper output, and correlated target/time/task/tool evidence.
