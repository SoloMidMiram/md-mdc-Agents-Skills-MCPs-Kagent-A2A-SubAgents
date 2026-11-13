#!/usr/bin/env python3
"""Capture A2A SSE stream and extract tool-loop / final text for evidence (no secrets)."""

from __future__ import annotations

import argparse
import json
import urllib.request
import uuid
from pathlib import Path


def parse_sse(body: str) -> list[dict]:
    """Parse an SSE body into a list of JSON payload dictionaries."""
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
    return events


def summarize_events(events: list[dict], prompt: str, *, request_id: str) -> dict:
    """Build the fail-closed evidence summary from a stream of A2A events."""
    texts: list[str] = []
    tool_calls: list[dict] = []
    tool_results: list[dict] = []
    final_state = None
    task_id = None
    correlated = bool(request_id)

    for ev in events:
        result = ev.get("result") if isinstance(ev, dict) else None
        if (
            not isinstance(result, dict)
            or ev.get("jsonrpc") != "2.0"
            or ev.get("id") != request_id
            or "error" in ev
        ):
            correlated = False
            continue
        event_task = result.get("id") if result.get("kind") == "task" else result.get("taskId")
        if not isinstance(event_task, str) or not event_task.strip():
            correlated = False
            continue
        if task_id is None:
            task_id = event_task
        elif task_id != event_task:
            correlated = False
            continue
        kind = result.get("kind")
        if kind == "status-update":
            status = result.get("status") or {}
            state = status.get("state")
            if state:
                final_state = state
            msg = status.get("message") or {}
            for part in msg.get("parts") or []:
                if not isinstance(part, dict):
                    continue
                if (
                    state == "completed"
                    and part.get("kind") == "text"
                    and isinstance(part.get("text"), str)
                ):
                    texts.append(part["text"])
                # Tool call / result correlation by id.
                # A call is a data part with name+id and no response; the matching
                # result is a data part with the same id and a response payload.
                if part.get("kind") == "data" and isinstance(part.get("data"), dict):
                    data = part["data"]
                    if data.get("name") and data.get("id"):
                        if "response" in data:
                            tool_results.append(data)
                        else:
                            tool_calls.append(data)
        elif kind == "artifact-update":
            art = result.get("artifact") or {}
            for part in art.get("parts") or []:
                if (
                    isinstance(part, dict)
                    and part.get("kind") == "text"
                    and isinstance(part.get("text"), str)
                ):
                    texts.append(part["text"])

    # Structured correlation (no heuristic string search). A qualifying pair is a
    # `k8s_get_resources` call bound to resource_type=pod / namespace=kagent whose
    # id exactly matches a result carrying a non-empty response output.
    def _qualified_call(call: dict) -> bool:
        args = call.get("args")
        return (
            call.get("name") == "k8s_get_resources"
            and isinstance(args, dict)
            and args.get("resource_type") == "pod"
            and args.get("namespace") == "kagent"
        )

    def _qualified_result(result: dict) -> bool:
        response = result.get("response")
        if not isinstance(response, dict):
            return False
        output = response.get("output")
        return result.get("name") == "k8s_get_resources" and bool(output)

    call_ids = {c["id"] for c in tool_calls if isinstance(c.get("id"), str) and _qualified_call(c)}
    result_ids = {
        r["id"] for r in tool_results if isinstance(r.get("id"), str) and _qualified_result(r)
    }
    matched_pairs = len(call_ids & result_ids)

    tool_mentioned = bool(tool_calls) or bool(tool_results)

    agent_texts = [t for t in texts if t and t.strip() and t.strip() != prompt]
    final_answer = agent_texts[-1] if agent_texts else ""

    return {
        "task_id": task_id,
        "final_state": final_state,
        "tool_mentioned_in_stream": tool_mentioned,
        "matched_tool_pairs": matched_pairs,
        "tool_calls": tool_calls[:20],
        "tool_results": tool_results[:20],
        "final_answer_preview": final_answer[:500],
        # Fail closed: completion plus text alone is not enough. Require a
        # non-empty task id, terminal completion, at least one exact
        # name/args/result-correlated tool pair, and a non-empty final answer.
        "passed": (
            correlated
            and bool(task_id)
            and final_state == "completed"
            and matched_pairs >= 1
            and bool(final_answer)
        ),
    }


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

    events = parse_sse(body)

    task = {
        "prompt": args.prompt,
        "agent": args.agent,
        "request_id": req_id,
        "http_status": http_status,
        "event_count": len(events),
    }
    (out / "task.json").write_text(json.dumps(task, indent=2), encoding="utf-8")

    summary = summarize_events(events, args.prompt, request_id=req_id)
    task_id = summary["task_id"]
    final_state = summary["final_state"]
    tool_mentioned = summary["tool_mentioned_in_stream"]
    matched_pairs = summary["matched_tool_pairs"]
    final_answer = summary["final_answer_preview"] if summary["passed"] else ""

    (out / "tool-call.json").write_text(
        json.dumps(
            {
                "tool_mentioned_in_stream": tool_mentioned,
                "calls": summary["tool_calls"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (out / "tool-result.json").write_text(
        json.dumps({"results": summary["tool_results"]}, indent=2), encoding="utf-8"
    )
    (out / "final-answer.md").write_text(
        f"# Final answer\n\n- agent: `{args.agent}`\n- taskId: `{task_id}`\n"
        f"- final_state: `{final_state}`\n- tool_mentioned: `{tool_mentioned}`\n"
        f"- matched_tool_pairs: `{matched_pairs}`\n\n## Text\n\n{final_answer}\n",
        encoding="utf-8",
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
