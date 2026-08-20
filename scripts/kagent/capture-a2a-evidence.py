#!/usr/bin/env python3
"""Capture A2A SSE stream and extract tool-loop / final text for evidence (no secrets)."""
from __future__ import annotations

import argparse
import json
import re
import uuid
import urllib.request
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--agent", required=True)
    p.add_argument("--prompt", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--timeout", type=float, default=300.0)
    p.add_argument("--controller", default="http://127.0.0.1:8083")
    p.add_argument("--namespace", default="kagent")
    args = p.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    url = f"{args.controller.rstrip('/')}/api/a2a/{args.namespace}/{args.agent}"
    req_id = str(uuid.uuid4())
    payload = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "message/stream",
        "params": {
            "message": {
                "role": "user",
                "kind": "message",
                "messageId": str(uuid.uuid4()),
                "parts": [{"kind": "text", "text": args.prompt}],
            }
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=args.timeout) as resp:
        body = resp.read(2_000_000).decode("utf-8", errors="replace")
        http_status = resp.status

    (out / "raw-sse.txt").write_text(body, encoding="utf-8")

    events: list[dict] = []
    for block in body.replace("\r\n", "\n").split("\n\n"):
        data_lines = [ln[5:].lstrip() for ln in block.splitlines() if ln.startswith("data:")]
        if not data_lines:
            continue
        payload_txt = "\n".join(data_lines).strip()
        if not payload_txt or payload_txt == "[DONE]":
            continue
        try:
            events.append(json.loads(payload_txt))
        except json.JSONDecodeError:
            continue

    task = {
        "prompt": args.prompt,
        "agent": args.agent,
        "request_id": req_id,
        "http_status": http_status,
        "event_count": len(events),
    }
    (out / "task.json").write_text(json.dumps(task, indent=2), encoding="utf-8")

    texts: list[str] = []
    tool_calls: list[dict] = []
    tool_results: list[dict] = []
    final_state = None
    task_id = None

    for ev in events:
        result = ev.get("result") if isinstance(ev, dict) else None
        if not isinstance(result, dict):
            continue
        kind = result.get("kind")
        if kind == "status-update":
            task_id = result.get("taskId") or task_id
            status = result.get("status") or {}
            state = status.get("state")
            if state:
                final_state = state
            msg = status.get("message") or {}
            for part in msg.get("parts") or []:
                if not isinstance(part, dict):
                    continue
                if part.get("kind") == "text" and isinstance(part.get("text"), str):
                    texts.append(part["text"])
                # function/tool call shapes vary; capture functionCall / toolCall / data
                for key in ("functionCall", "toolCall", "function_call", "tool_call"):
                    if key in part:
                        tool_calls.append(part[key])
                if part.get("kind") in {"data", "file"} and "tool" in json.dumps(part).lower():
                    tool_results.append(part)
            meta = result.get("metadata") or {}
            blob = json.dumps(result)
            if "functionCall" in blob or "tool_call" in blob or "k8s_get_resources" in blob:
                if "k8s_get_resources" in blob and result not in tool_calls:
                    tool_calls.append({"raw_kind": kind, "snippet": blob[:2000]})
            if "tool_response" in blob.lower() or "functionResponse" in blob:
                tool_results.append({"raw_kind": kind, "snippet": blob[:4000]})
        elif kind == "artifact-update":
            art = result.get("artifact") or {}
            for part in art.get("parts") or []:
                if isinstance(part, dict) and part.get("kind") == "text":
                    texts.append(str(part.get("text")))

    # Heuristic: detect tool name mentions in stream
    joined = body
    tool_mentioned = "k8s_get_resources" in joined or "functionCall" in joined or "tool_call" in joined

    agent_texts = [t for t in texts if t and t.strip() and t.strip() != args.prompt]
    final_answer = agent_texts[-1] if agent_texts else ""

    (out / "tool-call.json").write_text(
        json.dumps(
            {
                "tool_mentioned_in_stream": tool_mentioned,
                "calls": tool_calls[:20],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (out / "tool-result.json").write_text(
        json.dumps({"results": tool_results[:20]}, indent=2), encoding="utf-8"
    )
    (out / "final-answer.md").write_text(
        f"# Final answer\n\n- agent: `{args.agent}`\n- taskId: `{task_id}`\n"
        f"- final_state: `{final_state}`\n- tool_mentioned: `{tool_mentioned}`\n\n"
        f"## Text\n\n{final_answer}\n",
        encoding="utf-8",
    )
    summary = {
        "task_id": task_id,
        "final_state": final_state,
        "tool_mentioned_in_stream": tool_mentioned,
        "final_answer_preview": final_answer[:500],
        "passed": final_state == "completed" and bool(final_answer),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
