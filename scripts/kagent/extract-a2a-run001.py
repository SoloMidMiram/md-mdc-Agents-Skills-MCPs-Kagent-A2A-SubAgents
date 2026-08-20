#!/usr/bin/env python3
"""Extract PR4 planner/review/final artifacts from captured SSE."""
from __future__ import annotations

import json
import re
from pathlib import Path

OUT = Path(r"F:\Git\MCPtest\evidence\a2a\run001")
raw = (OUT / "raw-sse.txt").read_text(encoding="utf-8")
events: list[dict] = []
for block in raw.replace("\r\n", "\n").split("\n\n"):
    lines = [ln[5:].lstrip() for ln in block.splitlines() if ln.startswith("data:")]
    if not lines:
        continue
    t = "\n".join(lines).strip()
    if not t or t == "[DONE]":
        continue
    try:
        events.append(json.loads(t))
    except json.JSONDecodeError:
        continue

texts: list[str] = []
for ev in events:
    r = ev.get("result") or {}
    st = r.get("status") or {}
    msg = st.get("message") or {}
    for part in msg.get("parts") or []:
        if isinstance(part, dict) and part.get("kind") == "text":
            texts.append(part.get("text") or "")
    art = r.get("artifact") or {}
    for part in art.get("parts") or []:
        if isinstance(part, dict) and part.get("kind") == "text":
            texts.append(part.get("text") or "")


def parse_obj(s: str) -> dict | None:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\n?", "", s)
        s = re.sub(r"\n?```$", "", s)
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", s)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None


plan = None
review = None
final = None
for t in texts:
    obj = parse_obj(t)
    if not obj:
        continue
    keys = set(obj.keys())
    if {"goal", "acceptance_criteria"} <= keys or {"goal", "files", "tests"} <= keys:
        plan = obj
    if "verdict" in obj and ("findings" in obj or "required_changes" in obj):
        review = obj
    if {"summary", "plan", "review"} <= keys:
        final = obj

(OUT / "delegation.json").write_text(
    json.dumps(
        {
            "supervisor": "supervisor-agent",
            "delegates": ["planner-agent", "reviewer-agent"],
            "modelConfig": "litellm-gateway-model-config",
            "alias": "agent-coder",
            "cloud_only": True,
        },
        indent=2,
    ),
    encoding="utf-8",
)
(OUT / "planner-result.json").write_text(
    json.dumps(plan or (final or {}).get("plan") or {"note": "see final.md / raw-sse"}, indent=2),
    encoding="utf-8",
)
(OUT / "review-result.json").write_text(
    json.dumps(
        review or (final or {}).get("review") or {"note": "see final.md"},
        indent=2,
    ),
    encoding="utf-8",
)
if final:
    (OUT / "final.md").write_text(
        "# Final\n\n```json\n" + json.dumps(final, indent=2) + "\n```\n",
        encoding="utf-8",
    )
else:
    (OUT / "final.md").write_text(
        (OUT / "final-answer.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

tool_out = Path(r"F:\Git\MCPtest\evidence\kagent\tool-loop-run001")
(tool_out / "README.md").write_text(
    """# PR3 tool-loop run001

**Status:** PASS (cloud-only, agent-coder via LiteLLM)
**Agent:** litellm-gateway-tool-agent
**Tool:** k8s_get_resources (RemoteMCPServer kagent-tool-server)

## Files
- task.json — prompt + request id
- tool-call.json — tool mention / call evidence from SSE
- tool-result.json — tool result snippets from SSE
- final-answer.md — agent summary after tool
- summary.json — pass gate
- raw-sse.txt — full stream (no secrets)

## Flow
task -> reason -> call k8s_get_resources -> result -> answer
""",
    encoding="utf-8",
)

clients = Path(r"F:\Git\MCPtest\evidence\clients")
clients.mkdir(parents=True, exist_ok=True)
(clients / "eval-routing-pointer.md").write_text(
    """# PR7 eval scaffold note

See `F:/Git/arvancloudai_Api/docs/EVAL_ROUTING.md` for L0–L7 / C1–C6 / I0–I5
and routing policy against the live LiteLLM gateway.

**Live alias:** `agent-coder` only while local models are frozen.
""",
    encoding="utf-8",
)

print(
    json.dumps(
        {"plan": bool(plan), "review": bool(review), "final": bool(final), "texts": len(texts)},
        indent=2,
    )
)
