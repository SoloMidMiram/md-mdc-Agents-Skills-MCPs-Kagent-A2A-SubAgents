# PR2: kagent → LiteLLM → cloud model

**Date:** 2026-08-20  
**Status:** GATEWAY PASS; card gate pending in this record  
**Policy:** Local/Ollama aliases frozen — see `docs/LOCAL_MODELS_FROZEN.md`

## Path proven

```
kagent pod / A2A agent
  → http://host.docker.internal:4000/v1  (LiteLLM bind 0.0.0.0:4000)
  → alias agent-coder
  → DeepSeek (cloud)
```

`172.18.0.1:4000` fails from pods on Docker Desktop; use `host.docker.internal`.

## ModelConfig (excerpt)

```yaml
apiVersion: kagent.dev/v1alpha2
kind: ModelConfig
metadata:
  name: litellm-gateway-model-config
  namespace: kagent
spec:
  provider: OpenAI
  model: agent-coder
  apiKeySecret: kagent-litellm
  apiKeySecretKey: LITELLM_MASTER_KEY
  openAI:
    baseUrl: http://host.docker.internal:4000/v1
```

Secret `kagent-litellm` holds **only** `LITELLM_MASTER_KEY` (no provider keys).

## Pod curl probe (chat completions)

Pod: `curl-litellm-probe` — **Succeeded, exit 0**

- `GET /v1/models` via `host.docker.internal:4000` → HTTP 200
- `POST /v1/chat/completions` model=`agent-coder` → HTTP 200, content=`GATEWAY_OK` (~2.2s)
- No local fallback used

## Single-agent acceptance gates

| Gate | Current evidence | Decision |
|---|---|---|
| Agent exists | `litellm-gateway-smoke-agent` pod initialized the OpenAI-compatible model | Proven for this run |
| Agent card available | The captured helper JSON has `card.accepted=null` and `card.deploymentReady=null` | **Not captured** |
| Task submitted | `message/stream` returned `submitted` and `working` | Proven for this run |
| Model responds | `agent-coder` returned `PR2_GATEWAY_OK` | Proven for this run |
| Result returned | The stream reached terminal `completed` and included the response | Proven for this run |

The gateway and model-response path is a PASS. The complete five-gate
single-agent acceptance is not yet a PASS because the card result was not
captured in the retained helper record. Do not promote the missing card gate
from the task result.

## A2A request harness execution

Agent: `litellm-gateway-smoke-agent`  
Init log: `Initialized OpenAI model model=agent-coder baseUrl=http://host.docker.internal:4000/v1`

Task stream (redacted; no secrets):

| Event | State / content |
|-------|-----------------|
| status-update | `submitted` |
| status-update | `working` |
| status-update | agent text: `PR2_GATEWAY_OK` |
| artifact-update | `PR2_GATEWAY_OK` |
| status-update | `completed` (final) |

Raw SSE task ID: `01a01f71-e5f8-777b-a25d-c78667baab2e`  
Raw SSE: `evidence/runtime/a2a-raw-sse.txt`  
Separate official helper record: `evidence/runtime/kagent-litellm-task.json`  
Official helper task ID: `01a01f73-d909-740f-9834-49ba84567c4a`  
Official helper result: **PASS** (`state=completed`, exit 0) after skipping `artifact-update` SSE events in `test-a2a-agent.py`. The two task IDs are separate successful captures, not one correlated transaction.
The helper JSON is a local ignored capture; this Markdown file is the canonical
sanitized evidence summary.

## Alias used

- **agent-coder** (LiteLLM → DeepSeek cloud)
- Frozen (not used): `agent-fast`, `agent-review`, any `local-*` / `ollama/*`

## Host binding note

LiteLLM must listen with `-BindHost 0.0.0.0` so Docker Desktop pods reach the host gateway via `host.docker.internal:4000`.

## Re-run (PowerShell)

```powershell
# Ensure LiteLLM: start.ps1 -BindHost 0.0.0.0  (litellm-router)
# Port-forward controller if needed: kubectl -n kagent port-forward svc/kagent-controller 8083:8083

kubectl apply -f F:\Git\MCPtest\deploy\samples\kagent\litellm-gateway-model-config.yaml
kubectl -n kagent delete pod curl-litellm-probe --ignore-not-found
kubectl apply -f F:\Git\MCPtest\deploy\samples\kagent\curl-litellm-probe.yaml
kubectl -n kagent logs -f curl-litellm-probe

cd F:\Git\MCPtest
python scripts/kagent/test-a2a-agent.py task `
  --agent litellm-gateway-smoke-agent `
  --timeout 180 `
  --prompt "Reply with exactly: PR2_GATEWAY_OK" `
  --output json
```
