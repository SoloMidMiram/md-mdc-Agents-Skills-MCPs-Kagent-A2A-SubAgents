**LAB-01 — Repository evidence assessment**

Source revision: `a53bfb62f0421a7c28234f871af2bf449a11491f`. Both HEAD checks matched that SHA; `git status --short` returned no changes.

**L4 is proven by recorded A2A acceptance.** The repository defines L4 as a valid task/message being accepted or completed through A2A; acceptance is sufficient ([capability matrix, line 12](F:/Git/agent-labs/docs/reference/kagent-capability-matrix.md:12)). Phase 5D records:

- `message/stream`, exit `0`, `responseIdMatched=true`;
- task ID `019f7039-e57c-72bf-8aa9-eb84012cfcf1`;
- state `working`, response kind `status-update`.

These values appear at [Phase 5D, lines 58–64](F:/Git/agent-labs/evidence/kagent/educational-practice-phase-5d-trustworthy-a2a.md:58). The retained SSE examples independently show the same task ID entering `submitted` and `working` ([lines 75–82](F:/Git/agent-labs/evidence/kagent/educational-practice-phase-5d-trustworthy-a2a.md:75)). That observation crosses the L4 boundary. A later model failure does not erase the earlier acceptance; the record explicitly distinguishes acceptance from LLM success ([lines 32–34](F:/Git/agent-labs/evidence/kagent/educational-practice-phase-5d-trustworthy-a2a.md:32)).

**L6 remains unproven because the required agent-mediated tool/result chain is missing.** L6 requires an A2A request to cause the agent to invoke a real MCP tool and return tool-derived output ([capability matrix, line 14](F:/Git/agent-labs/docs/reference/kagent-capability-matrix.md:14)).

Phase 5E retained A2A acceptance, but its run recorded `toolInvocation.observed=false`, `result.matched=false`, and exit `1` ([Phase 5E, lines 58–68](F:/Git/agent-labs/evidence/kagent/educational-practice-phase-5e-agent-mediated-mcp.md:58)). No SSE/log tool marker for `k8s_get_resources` was correlated with that task, and no tool-derived names were obtained ([lines 24–27](F:/Git/agent-labs/evidence/kagent/educational-practice-phase-5e-agent-mediated-mcp.md:24)). The independent listing of 18 Kubernetes pods proves readability of the cluster; it cannot supply the missing agent output.

The implementation agrees with that distinction: missing observation, mismatched task correlation, absent A2A-returned names, and failed name matching each cause gate failure ([producer, lines 815–839](F:/Git/agent-labs/scripts/kagent/agent_mcp_trace.py:815)). Model quota is only a proposed explanation, explicitly labeled an inference, rather than a proven sole cause ([Phase 5E, lines 29–35](F:/Git/agent-labs/evidence/kagent/educational-practice-phase-5e-agent-mediated-mcp.md:29)).

The canonical index therefore correctly records **L4 Proven; L6 Not proven** ([status index, lines 25–27](F:/Git/agent-labs/evidence/kagent/README.md:25)).

**Required observation and smallest closing test**

Obtain one bounded live A2A invocation with all of the following tied to the **same task**:

1. Accepted `message/stream` dispatch with matching request ID and non-empty task ID.
2. An agent/tool/model structured protocol marker, or sanitized correlated log proof, binding that task to `kagent-tool-server`, `k8s_get_resources`, and normalized `pod`/`kagent` arguments.
3. Pod names returned through that task’s A2A output at or after the tool observation.
4. An independent Kubernetes name listing demonstrating a non-empty subset match with no extra claimed names.
5. Valid source JSON, target binding, decision/exit agreement, and recomputed freshness within 900 seconds.

These are the contract requirements at [lines 20–26](F:/Git/agent-labs/docs/reference/kagent-agent-mediated-mcp-evidence.md:20). Matching requires every returned tool-derived name to exist in the independently collected names; equal counts alone are insufficient ([producer, lines 598–606](F:/Git/agent-labs/scripts/kagent/agent_mcp_trace.py:598)).

The smallest test is one run of the existing producer against the approved local lab, followed by validation of that same captured evidence by `FullMcpExecution`. No new implementation or separate direct MCP smoke test is needed.

**Proposed only — not executed:**

```powershell
uv run python scripts/kagent/agent_mcp_trace.py `
  --controller http://127.0.0.1:8083 `
  --output json `
  --source-out evidence/kagent/tmp/lab01-agent-mcp-trace.json
```

The existing default prompt requests pods in `kagent` using the configured Kubernetes MCP tool ([producer, lines 39–47](F:/Git/agent-labs/scripts/kagent/agent_mcp_trace.py:39)); the flags are defined at [lines 924–937](F:/Git/agent-labs/scripts/kagent/agent_mcp_trace.py:924). Review the captured source and passing consumer result, then retain a dated evidence record. A profile pass alone does not automatically promote L6 ([evidence contract, lines 62–67](F:/Git/agent-labs/docs/reference/kagent-agent-mediated-mcp-evidence.md:62)). A deterministic fixture test can verify the gate but cannot replace this live observation.

**Negative control — successful direct MCP call**

**No, this record does not establish L6.**

Phase 5B records a successful direct `mcp_session_smoke.py` invocation: exit `0`, tool `k8s_get_resources`, `toolCallSucceeded=true`, and 18 returned resources ([Phase 5B, lines 24–46](F:/Git/agent-labs/evidence/kagent/educational-practice-phase-5b-direct-mcp.md:24)). Its independent `kubectl` observation also counted 18 pods ([lines 50–56](F:/Git/agent-labs/evidence/kagent/educational-practice-phase-5b-direct-mcp.md:50)). This supports direct MCP server operation with session reuse.

It does not demonstrate that an A2A request caused an agent to invoke that tool and return its output. The L6 definition explicitly lists direct MCP initialize/call as insufficient ([capability matrix, line 14](F:/Git/agent-labs/docs/reference/kagent-capability-matrix.md:14)); Phase 5B expressly records no A2A dispatch and no agent-mediated invocation ([lines 58–67](F:/Git/agent-labs/evidence/kagent/educational-practice-phase-5b-direct-mcp.md:58)). The consumer also rejects direct MCP evidence alone for `FullMcpExecution` ([consumer, lines 1146–1153](F:/Git/agent-labs/scripts/kagent/KagentHealth.psm1:1146)).

The correct decision remains **direct MCP invocation proven as server evidence; L6 Not proven**. The missing observation is the same-task A2A → agent → MCP tool → returned result correlation described above.

**Commands executed and limitations**

All commands ran in `F:/Git/agent-labs` and were read-only:

- `git rev-parse HEAD` — twice.
- `Get-Content AGENTS.md`.
- `rg -n "L4|L6|LAB-01" . --glob '!**/.git/**'`.
- A numbered `Get-Content` loop over:
  - `docs/reference/kagent-capability-matrix.md`
  - `evidence/kagent/README.md`
  - `evidence/kagent/educational-practice-phase-5d-trustworthy-a2a.md`
  - `evidence/kagent/educational-practice-phase-5e-agent-mediated-mcp.md`
  - `evidence/kagent/educational-practice-phase-5b-direct-mcp.md`
- A numbered `Get-Content` read of `docs/reference/kagent-agent-mediated-mcp-evidence.md`.
- `rg -n "def |add_argument|toolInvocation|matched|sourceEvidencePath|observed|task_id|taskId" scripts/kagent/agent_mcp_trace.py`.
- `rg -n "function Test-AgentMediatedEvidenceObject|sourceEvidencePath|matched|900|direct-mcp-tool-call" scripts/kagent/KagentHealth.psm1`.
- Numbered `Get-Content` excerpts of `agent_mcp_trace.py`: lines 35–66, 598–608, 798–846, 924–938; and `KagentHealth.psm1`: lines 1120–1184.
- `git status --short`.

No files were modified; no tests, runtime helpers, browser tools, Kubernetes commands, or network requests were executed. These conclusions assess retained repository evidence, not current cluster operation. The historical gitignored source capture was not independently inspected.

Evaluation-isolation limitation: the initial broad `rg` also emitted incidental matching snippets from benchmark case/scoring files. I did not explicitly open those files or use them as authority; subsequent inspection was restricted to repository capability definitions, dated evidence, and implementation. This exposure should be considered when grading isolation.
