# Problem: A2A dispatch compatibility (controller 0.9.11)

**Date:** 2026-07-17
**Lane:** kagent educational lab
**Status:** Compatibility path resolved for L4 via `message/stream`; blocking
methods remain unsuitable

## Symptom

Educational helper reported A2A dispatch failure:

- `tasks/sendTask` → JSON-RPC `-32601` method not found
- `message/send` → JSON-RPC `-32603` (decode/proxy errors)
- Health collector scraped human `[PASS]` / `code=-32601` text
- `print_task_result` treated any response without `error` as success (`{}` unsafe)

## Observed facts

- Controller: `ghcr.io/kagent-dev/kagent/controller:0.9.11`
- First-party UI client sends `message/stream` with `Accept: text/event-stream`
  to `/a2a/{ns}/{agent}` (maps to controller `/api/a2a/...`)
- Live full `MessageSendParams` stream returns SSE `status-update` objects with
  non-empty `taskId` and states `submitted` → `working` (later may `failed` on
  model quota)
- Empty-param probes of `message/stream` still return `-32603`

## Root cause

Client/method mismatch: lab helper used unsupported or blocking JSON-RPC methods
while the installed controller/UI path is streaming `message/stream`. Separately,
success detection was text-based and accepted empty objects.

## Fix applied (no cluster upgrade)

1. Pin dispatch to `message/stream` + SSE parsing.
2. Accept confirmed `status-update` / task / message shapes only.
3. Emit versioned JSON evidence (`schemaVersion` 1.0).
4. Health profile consumes JSON; requires non-empty `taskOrMessageId`.
5. Fail-closed review rejects any malformed, mismatched-ID, or JSON-RPC-error
   event in a stream and requires helper exit/decision/transport/protocol/
   dispatch consistency with exact schema 1.0.

Evidence: `evidence/kagent/educational-practice-phase-5d-trustworthy-a2a.md`.

## Upgrade note (not executed)

If a future lab needs blocking `message/send` or `tasks/send` without SSE:

1. Pin current: controller/ui `0.9.11`.
2. Choose a published chart/image pair that documents the desired method.
3. Record exact `helm upgrade` / image digests and a rollback to `0.9.11`.
4. Obtain explicit user approval before changing cluster resources.

No Helm/CRD/controller upgrade was performed for Phase 5D.

## Remaining promotion blocker

Compatibility and L4 response validation are resolved. Freshness, target
binding, source existence, and A2A task-to-agent-to-MCP trace correlation are
still P0 requirements before L6 can be promoted.
