# PR2 — kagent → LiteLLM gateway proof

This runbook owns the smallest gateway checkpoint:

```text
kagent one-agent ModelConfig → LiteLLM :4000/v1 → agent-coder → response
```

It deliberately excludes MCP tools, Agent tools, multiple agents, local/Ollama
models, and production deployment. The controller task endpoint is used only as
the existing kagent request/response transport for the smoke; this is not an
A2A multi-agent workflow.

## Ownership and freeze

- LiteLLM owns provider credentials and the gateway registry.
- MCPtest supplies only the kagent `ModelConfig`, the alias, and the
  `LITELLM_MASTER_KEY` reference.
- The frozen gateway registry is owned by the adjacent LLMLite repository at
  `F:/Git/arvancloudai_Api/models/gateway_manifest.yaml` and is currently
  schema version `1.2`. Do not copy or evolve it in MCPtest.
- Local/Ollama aliases remain frozen. Do not fall back when cloud access fails;
  record `BLOCKED` evidence.

## Prerequisites

- `docker-desktop` Kubernetes context and the `kagent` namespace;
- LiteLLM listening on `0.0.0.0:4000` with alias `agent-coder` available;
- the user-scoped `LITELLM_MASTER_KEY` environment variable;
- a controller port-forward on `127.0.0.1:8083` for the request step.

## Static validation

Run without contacting Kubernetes or LiteLLM:

```powershell
python scripts/kagent/validate-litellm-gateway.py --json
```

The validator requires one `ModelConfig`, one no-tool `Agent`, the LiteLLM
endpoint, the `agent-coder` alias, and the dated evidence fields. It rejects
MCP/Agent tools in the Phase 2 smoke manifest.

## Apply the bounded slice

The script does not print secret values and does not place provider keys in the
kagent Secret:

```powershell
python scripts/kagent/validate-litellm-gateway.py
.\scripts\kagent\apply-litellm-modelconfig.ps1
kubectl wait --for=condition=Accepted=true agent/litellm-gateway-smoke-agent -n kagent --timeout=180s
kubectl wait --for=condition=Ready=true agent/litellm-gateway-smoke-agent -n kagent --timeout=180s
kubectl rollout status deployment/litellm-gateway-smoke-agent -n kagent --timeout=180s
kubectl logs deployment/litellm-gateway-smoke-agent -n kagent --tail=80
```

Expected model initialization log:

```text
Initialized OpenAI model model=agent-coder baseUrl=http://host.docker.internal:4000/v1
```

## Verify the five gates

1. Agent exists: `kubectl get agent litellm-gateway-smoke-agent -n kagent`.
2. Card is available: fetch the card through the existing helper and retain the
   accepted skill metadata.
3. A single task is submitted with the exact bounded prompt below.
4. The model returns a non-empty response through `agent-coder`.
5. The same task returns the response to the caller.

```powershell
kubectl -n kagent port-forward svc/kagent-controller 8083:8083

python scripts/kagent/test-a2a-agent.py both `
  --agent litellm-gateway-smoke-agent `
  --timeout 180 `
  --prompt "Review this Python file: def add(a, b): return a + b" `
  --output json
```

The helper's task transport is a request harness, not evidence of MCP use,
agent-to-agent delegation, or a multi-agent workflow.

## Evidence

The current dated record is
[`evidence/runtime/kagent-litellm-success.md`](../../evidence/runtime/kagent-litellm-success.md).
It proves the gateway and model response path, but its current helper capture
does not include a card result. Therefore the record must keep the card gate
explicitly pending until a `both` run captures it; do not label the full
five-gate acceptance `PASS` from task completion alone.

Required evidence fields:

- ModelConfig excerpt;
- smoke-agent name and card result;
- sanitized pod initialization log;
- exact request and task/response result;
- alias `agent-coder` and LiteLLM endpoint;
- exit code and explicit non-claims.

## Cleanup

```powershell
kubectl delete -f deploy/samples/kagent/litellm-gateway-smoke-agent.yaml
kubectl delete -f deploy/samples/kagent/litellm-gateway-model-config.yaml
kubectl delete secret kagent-litellm -n kagent
```

Do not delete shared kagent controller, MCP server, or LiteLLM resources as part
of this educational slice.

## Explicit non-claims

- no MCP tool invocation;
- no `read_file` tool — that is a later, separate tool-enabled slice;
- no A2A Agent-tool delegation or multiple agents;
- no local/Ollama model capability;
- no L6, I4, L7, or production-readiness promotion.
