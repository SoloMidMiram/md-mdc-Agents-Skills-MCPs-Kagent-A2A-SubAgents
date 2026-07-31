# B06: Review malformed source capture

## Scenario
`agent_mcp_trace.py` has a source-capture truncation issue:

```python
text = text[:MAX_SOURCE_CHARS] + "\n…truncated…\n"
```

This produces output that is not valid JSON. The `FullMcpExecution` consumer opens `sourceEvidencePath` and calls `json.loads`, which will reject the truncated string.

## Task
Review this approach. What is wrong with the current truncation? Propose a fix that preserves valid JSON output.
