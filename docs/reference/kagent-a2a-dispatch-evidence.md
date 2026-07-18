# kagent A2A Dispatch Evidence Contract

Stable machine-readable contract for trustworthy A2A dispatch checks in the
local educational lab. Executable producer: `scripts/kagent/test-a2a-agent.py`.
Consumer: `scripts/kagent/check-kagent-health.ps1` via `KagentHealth.psm1`.

Volatile live results belong in dated `evidence/kagent/` records, not here.

## Schema version

`schemaVersion`: `"1.0"`

## JSON envelope

```json
{
  "schemaVersion": "1.0",
  "action": "task",
  "observedAt": "<UTC ISO-8601>",
  "target": {
    "namespace": "kagent",
    "agent": "k8s-a2a-agent",
    "controller": "<sanitized origin>",
    "endpoint": "<path only>"
  },
  "transport": {
    "succeeded": true,
    "httpStatus": 200,
    "errorKind": null,
    "error": null
  },
  "protocol": {
    "jsonRpc": "2.0",
    "method": "message/stream",
    "requestId": "<sanitized id>",
    "responseIdMatched": true,
    "error": null
  },
  "dispatch": {
    "accepted": true,
    "taskOrMessageId": "<non-empty>",
    "state": "<recognized state>",
    "responseKind": "status-update|task|message"
  },
  "probe": {},
  "card": {
    "accepted": null,
    "deploymentReady": null
  },
  "decision": {
    "passed": true,
    "exitCode": 0,
    "reason": "<concise reason>"
  }
}
```

Never include authorization headers, secrets, kubeconfig content, raw session
IDs, or unnecessarily large response bodies.

## Pinned dispatch path (controller 0.9.11)

| Item | Value |
|------|-------|
| Endpoint | `POST /api/a2a/{namespace}/{agent}` |
| Method | `message/stream` |
| Accept | `text/event-stream` |
| Params | A2A `MessageSendParams` with `kind=text` parts |

Aligned with kagent UI `ui/src/lib/a2aClient.ts` at tag `v0.9.11`.

## Accepted response shapes

A dispatch may pass only when transport succeeded, JSON-RPC `2.0` is valid,
response `id` matches the request, there is no JSON-RPC `error`, and the
`result` matches one of:

1. **status-update** (streaming): `kind=status-update`, non-empty `taskId`,
   `status.state` in `{submitted, working, completed, input_required}`.
2. **task**: `kind=task`, non-empty `id`, and `status.state` in the same
   accepted set.
3. **message**: `kind=message`, non-empty `messageId`, `role` in
   `{agent, user}`, and a non-empty object `parts` list.

Every JSON-RPC event in one SSE response must have the matching request ID, no
JSON-RPC error, and an exact recognized response shape. One malformed,
mismatched-ID, or error event invalidates the response even if a later event is
valid. A terminal `failed` / `canceled` / `rejected` status after a previously
accepted state does not revoke L4; a stream containing only terminal states
does not pass.

## Rejected shapes

- `{}`, `null`, empty `result`
- missing or mismatched response `id`
- arbitrary objects without a recognized task/message/status-update shape
- card-only or probe-only outcomes
- method registration alone
- JSON-RPC errors including `-32601` and `-32603`
- HTTP errors, invalid JSON, timeouts, connection failures

Absence of an `error` field is never sufficient by itself.

## Exit codes

| Action | 0 | 1 | 2 | 3 |
|--------|---|---|---|---|
| `task` / `both` | recognized dispatch accepted/completed | protocol/dispatch gate failed | invalid CLI | transport failure |
| `probe` | probe completed (methods may be unsupported) | — | invalid CLI | transport failure |
| `card` | accepted and deployment-ready | card gate failed | invalid CLI | transport failure |

`probe` never claims L4.

## Health integration

`A2ADispatch` invokes the helper with `--output json` and preserves its nested
contract. A pass requires exact `schemaVersion == 1.0`; matching helper process
and `decision.exitCode` values; `decision.passed == true`; successful 2xx
transport; JSON-RPC `2.0`, `message/stream`, matching response ID, and no
protocol error; plus an accepted dispatch, recognized response kind/state, and
non-empty identifier. Missing fields and contradictory values fail closed.
Human text scraping and collector-synthesized schema fields are not evidence
protocols.
