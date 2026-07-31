# Educational practice — Phase 5D: Trustworthy A2A dispatch

**Date:** 2026-07-17
**Timezone:** UTC (observedAt timestamps)
**Environment:** local Docker Desktop Kubernetes; namespace `kagent`
**Controller image:** `ghcr.io/kagent-dev/kagent/controller:0.9.11`
**UI image:** `ghcr.io/kagent-dev/kagent/ui:0.9.11`
**Agent:** `k8s-a2a-agent` (`golang-adk`)
**Helm:** CLI not available in this session; image tags used as version pin

## Objective

Replace unsafe text-based A2A success detection with structured, strictly
validated JSON, and prove L4 only via a recognized dispatch path.

## Compatibility root cause

| Observation | Classification |
|-------------|----------------|
| Helper historically called `tasks/sendTask` | Wrong method for 0.9.11 (`-32601`) |
| Blocking `message/send` returned `-32603` | Registered but decode/proxy failure on empty or blocking paths |
| kagent UI @ 0.9.11 uses `message/stream` + SSE | Confirmed first-party client path |
| Live `message/stream` with MessageSendParams | Returns SSE `status-update` events with non-empty `taskId` |

**Selected method/endpoint:** `POST /api/a2a/kagent/k8s-a2a-agent` method
`message/stream`, `Accept: text/event-stream`.

Assumption labeled previously: blocking `message/send` mismatch. Live evidence
confirmed streaming is the working path; empty-param probes of `message/stream`
still return `-32603` and must not be treated as L4.

Later stream events may reach `failed` (for example OpenAI quota). L4 requires
an accepted state (`submitted` / `working` / `completed` / `input_required`)
with a non-empty identifier somewhere in the stream — not LLM success.

## Changes

- Rewrote `scripts/kagent/test-a2a-agent.py` with `--output human|json`, exit
  categories 0/1/2/3, and strict validators.
- Health collector parses helper JSON only (no human scraping).
- `Test-A2ADispatchEvidenceObject` requires exact schema 1.0 and agreement
  across helper exit, decision, transport, protocol, and dispatch fields.
- Deterministic tests after the fail-closed review:
  `tests/kagent/test_a2a_helper.py` (43 passed).
- Pester 3.4 health suite after the fail-closed review: 47 passed.

## Live commands and exits

Controller listener on `127.0.0.1:8083` reused (existing PID; not stopped).

```text
uv run python scripts/kagent/test-a2a-agent.py card --controller http://127.0.0.1:8083 --output json
→ exit 0 (accepted + deploymentReady)

uv run python scripts/kagent/test-a2a-agent.py probe --controller http://127.0.0.1:8083 --output json
→ exit 0 (observational; tasks/sendTask -32601; message/send and empty message/stream -32603)

uv run python scripts/kagent/test-a2a-agent.py task --controller http://127.0.0.1:8083 --output json
→ exit 0
  method=message/stream
  responseIdMatched=true
  taskOrMessageId=019f7039-e57c-72bf-8aa9-eb84012cfcf1
  state=working
  responseKind=status-update

uv run python scripts/kagent/test-a2a-agent.py both --controller http://127.0.0.1:8083 --output json
→ exit 0
  taskOrMessageId=019f703a-d09d-78f3-ac38-c3642fb5b30d
  state=working

.\scripts\kagent\check-kagent-health.ps1 -Profile A2ADispatch -ControllerUrl http://127.0.0.1:8083 -OutputFormat Json
→ exit 0 (a2a-dispatch gate pass)
```

Sanitized representative SSE events from the recorded successful task (request
identifier replaced; response body reduced to the fields used by the gate):

```text
data: {"jsonrpc":"2.0","id":"<request-id>","result":{"kind":"status-update","taskId":"019f7039-e57c-72bf-8aa9-eb84012cfcf1","final":false,"status":{"state":"submitted"}}}

data: {"jsonrpc":"2.0","id":"<request-id>","result":{"kind":"status-update","taskId":"019f7039-e57c-72bf-8aa9-eb84012cfcf1","final":false,"status":{"state":"working"}}}
```

## 2026-07-17 fail-closed review addendum

The historical live observations above were preserved. The review reproduced
the image pins with these read-only commands:

```powershell
kubectl get deployment kagent-controller -n kagent -o jsonpath="{.spec.template.spec.containers[*].image}"
# ghcr.io/kagent-dev/kagent/controller:0.9.11

kubectl get deployment kagent-ui -n kagent -o jsonpath="{.spec.template.spec.containers[*].image}"
# ghcr.io/kagent-dev/kagent/ui:0.9.11
```

The selector now rejects the entire SSE response if any event is malformed,
has a mismatched response ID, contains a JSON-RPC error, or lacks an exact
recognized response shape. The health collector no longer supplies a missing
schema version or derives acceptance from a contradictory decision. No new
live task was sent during this review because no controller listener was
available on `127.0.0.1:8083`; the recorded valid dispatch remains the L4
observation.

## Capability decisions

| Level | Decision | Notes |
|-------|----------|-------|
| L4 | **Proven** | Recognized `message/stream` status-update with non-empty task id and accepted state |
| L6 | **Not proven** | No agent-mediated MCP tool result claimed in this phase |

Do not treat OpenAI quota / terminal `failed` agent messages as L4 failure when
an earlier accepted state with `taskId` was observed.

## Explicit non-claims

- Card retrieval alone is not L4.
- Probe method registration / `-32601` discovery is not L4.
- Direct MCP success is not L4 or L6.
- This phase does not prove L6 or L7.

## Related

- Schema: [kagent-a2a-dispatch-evidence.md](../../docs/reference/kagent-a2a-dispatch-evidence.md)
- Problem: [2026-07-17-a2a-dispatch-compatibility.md](problems/2026-07-17-a2a-dispatch-compatibility.md)
- Historical failure: [educational-practice-phase-5.md](educational-practice-phase-5.md) (not rewritten)
