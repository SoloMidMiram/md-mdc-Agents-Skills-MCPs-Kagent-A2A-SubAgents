# kagent A2A Experiment Evidence

Dated records from `scripts/kagent/experiments/record_experiment.py` after
`run_a2a_example.py` runs.

**Non-claims by default:** L6, I3, I4, MCP tool invocation, Codex/Cursor interop.

Temporary run JSON (gitignored pattern: do not commit secrets) may live under
`tmp/` during local smokes.

## 2026-08-07 — PR #4 implementation smoke (environmental blocker)

Three agents deployed (`planner-agent`, `reviewer-agent`, `supervisor-agent`).
Each direct/supervisor A2A dispatch accepted a task id, but tasks **failed** at
the DeepSeek HTTP call due to cluster DNS errors reaching `api.deepseek.com`.

| Example | Task ID (prefix) | Pass | Blocker |
|---------|------------------|------|---------|
| e1-planner | `019fdddc-9936` | false | CoreDNS / egress to DeepSeek |
| phase2-reviewer | `019fdddc-d015` | false | CoreDNS / egress to DeepSeek |
| e2-supervisor | `019fdddc-f6f0` | false | CoreDNS / egress to DeepSeek |

Re-run after cluster DNS/egress is healthy; expect JSON artifacts when LLM calls succeed.
