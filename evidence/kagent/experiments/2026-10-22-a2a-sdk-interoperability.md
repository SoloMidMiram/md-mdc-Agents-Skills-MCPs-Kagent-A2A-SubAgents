# Official Python A2A SDK interoperability experiment

**Observed:** 2026-10-22, UTC  
**Branch:** `feature/a2a-python-sdk-interoperability`  
**Scope:** isolated client, tests, dependency lock, and evidence only

## Result

The SDK adapter and its deterministic interoperability test pass, but the
live gate is **Blocked** in this environment: no controller listener was
available on `127.0.0.1:8083`, and `kubectl` is not installed to establish the
repository's documented port-forward. Consequently this record does not claim
live Agent Card discovery or live end-to-end A2A success.

The experiment does prove the unsupported-version gate and the SDK-backed SSE
correlation behavior against an in-memory HTTP transport. That synthetic result
is not a live kagent result.

## Existing path inspected

The repository documentation and evidence identify the existing target as
`kagent/k8s-a2a-agent` behind controller/UI `0.9.11`:

- Agent details/Card endpoint: `GET /api/agents/kagent/k8s-a2a-agent`.
- A2A endpoint: `POST /api/a2a/kagent/k8s-a2a-agent`.
- Working method: JSON-RPC `message/stream` with `Accept: text/event-stream`.
- Existing evidence accepts `submitted`, `working`, `completed`, or
  `input_required` with a non-empty task ID as dispatch evidence.
- Existing Phase 5E evidence explicitly says this does not prove an MCP tool
  invocation or L6.

The SDK client keeps that endpoint and method unchanged. It adapts the
kagent-specific details response into the official `a2a.types.AgentCard`,
validates the protocol family, and only then invokes the official SDK
`A2AClient`.

## Isolated client and evidence

| Item | Value |
|---|---|
| Python | 3.13.15 in `.venv/a2a-sdk` |
| SDK | `a2a-sdk==0.3.26` |
| Direct task | `message/stream` through the official SDK |
| Prompt intent | Read-only pod-name query in namespace `kagent` |
| Runtime/config changes | None in this experiment; no Kubernetes or IDE file was edited |
| MCP observation | Not collected; the client does not inspect tool logs or MCP results |

The lock file pins the SDK and all installed transitive dependencies. It is
separate from the repository's normal `pyproject.toml` dependency group.

## Verification commands and results

```text
uv venv --clear --python 3.13 .venv/a2a-sdk
→ PASS

uv pip compile --python-version 3.13 scripts/kagent/experiments/a2a_sdk_requirements.in \
  --output-file scripts/kagent/experiments/a2a_sdk_requirements.lock
→ PASS

uv pip sync --python .venv/a2a-sdk/bin/python \
  scripts/kagent/experiments/a2a_sdk_requirements.lock
→ PASS

uvx ruff check scripts/kagent/experiments/a2a_sdk_interop.py \
  tests/kagent/experiments/test_a2a_sdk_interop.py
→ PASS

TMPDIR=/tmp .venv/a2a-sdk/bin/python -m pytest -q -s \
  tests/kagent/experiments/test_a2a_sdk_interop.py
→ PASS: 6 passed

Bundled capability-review validator: unavailable because `pwsh` is not
installed. A Python JSON shape/count check passed for the companion review
record.
```

The six tests cover card discovery/adaptation, the kagent protocol fallback, explicit
unsupported-version rejection before dispatch, and an official SDK SSE round
trip with one task ID, `submitted → working → completed`, matching JSON-RPC
response IDs, and no protocol errors.

## Live attempt

Read-only endpoint checks were attempted first:

```text
curl --noproxy '*' --silent --show-error --max-time 5 \
  http://127.0.0.1:8083/health
→ exit 7: Failed to connect to 127.0.0.1 port 8083

curl --noproxy '*' --silent --show-error --max-time 5 \
  http://127.0.0.1:8083/api/agents/kagent/k8s-a2a-agent
→ exit 7: Failed to connect to 127.0.0.1 port 8083

kubectl config current-context
→ unavailable: kubectl is not installed
```

The bounded SDK command was then run once. It performed no A2A task because
card discovery failed first:

```text
TMPDIR=/tmp .venv/a2a-sdk/bin/python \
  scripts/kagent/experiments/a2a_sdk_interop.py \
  --controller http://127.0.0.1:8083 --output json
→ exit 3
```

Sanitized structured result:

```json
{
  "claims": {
    "a2aCommunication": false,
    "agentCardDiscovery": false,
    "mcpToolExecution": false,
    "mcpToolExecutionEvidence": "not collected by this SDK client"
  },
  "compatibility": {
    "requestedProtocolVersion": "0.3.0",
    "validatedBeforeDispatch": false
  },
  "decision": {
    "exitCode": 3,
    "passed": false,
    "reason": "Agent Card request failed: ConnectError: All connection attempts failed"
  },
  "response": {
    "errors": [
      {
        "type": "TransportError",
        "message": "Agent Card request failed: ConnectError: All connection attempts failed"
      }
    ],
    "statusTransitions": []
  }
}
```

## Capability classification

| Claim | Classification | Basis |
|---|---|---|
| Existing Agent Card can be discovered live by this client | **Blocked** | Controller listener unavailable; no card response was obtained |
| Official SDK request/response works against the existing kagent agent | **Not proven** | Only the in-memory SDK transport passed; no live task was sent |
| Unsupported protocol versions fail explicitly before dispatch | **Proven** | Deterministic test rejected `requested=1.0`, `advertised=0.3.0`, and dispatch was not called |
| A2A task ID/status correlation is recorded | **Proven synthetically** | SDK test records wire request ID, message ID, one task ID, transitions, response IDs, and errors |
| A2A request caused MCP tool execution | **Not attempted / not proven** | This client intentionally collects no MCP or controller tool trace |

This report does not change the repository's existing L4/L6 status. In
particular, Agent Card discovery, A2A transport success, and actual MCP tool
execution remain separate claims.
