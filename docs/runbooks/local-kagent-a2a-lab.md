# Local kagent + A2A Lab

This runbook is the shortest path from a local Kubernetes cluster to a working
kagent A2A lab: deploy, reconcile, verify, and inspect the sample A2A agent.

For the phase-by-phase learning path and architecture guardrails, read
[kagent Educational Roadmap](../onboarding/KAGENT-EDUCATIONAL-ROADMAP.md)
before using this runbook.

## Lab Status Summary

Do not use a runbook snapshot as current evidence. Read the
[kagent evidence index](../../evidence/kagent/README.md) before beginning. The
current capability decisions are L0-L5 and I0-I2 Proven; I3 Blocked; L6, L7,
and I4 Not proven; and I5 Not attempted.

The next operational gate is the no-tool human Cursor I3 sequence below,
beginning with server/tool discovery: the acceptance session's MCP catalog
exposed neither the configured kagent server nor its tools (`tool_discovery` /
`KAGENT_MCP_TOOLS_NOT_EXPOSED`). Do not re-apply Candidate B until the server
and its `list_agents`/`invoke_agent` tools are visible. Classify failure at the
earliest failed stage (taxonomy below), do not request a Kubernetes tool during
that gate, and do not treat helper success as I3.

## Current Local State

Discover local state each time instead of assuming retained counts. Before a
lab action, confirm:

- Kubernetes context is exactly `docker-desktop`;
- the target Agent is Accepted/Ready and its observed generation matches;
- the target `RemoteMCPServer`, Service, and EndpointSlice are ready;
- the provider profile expected by the current phase is reconciled; and
- the intended local port has one owned `kubectl port-forward` listener.

Provider secrets must be created separately and must never be written to
evidence. Unrelated degraded demo agents or servers must not be added to an
allowlist merely to make a strict gate pass.

## Prerequisites

| Tool       | Required | Check command                     |
|------------|----------|-----------------------------------|
| Docker     | Yes      | `docker info`                     |
| kubectl    | Yes      | `kubectl config current-context`  |
| Helm       | Yes      | `helm version`                    |
| Python 3   | For test | `python --version`                |

Ensure the context is `docker-desktop`:

```powershell
kubectl config current-context
```

## Quick-Start (Full Install)

### 1. Create namespace

```powershell
kubectl create namespace kagent --dry-run=client -o yaml | kubectl apply -f -
```

### 2. Install CRDs

```powershell
helm upgrade --install kagent-crds oci://ghcr.io/kagent-dev/kagent/helm/kagent-crds `
  --namespace kagent
```

### 3. Set the API key

```powershell
$env:OPENAI_API_KEY = "<your-api-key>"
```

### 4. Install kagent core

```powershell
helm upgrade --install kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent `
  --namespace kagent `
  --set providers.default=openAI `
  --set providers.openAI.apiKey=$env:OPENAI_API_KEY
```

### 5. Create the `kagent-openai` secret

Helm may not create the secret automatically. If any agent pods show
`CreateContainerConfigError`, create the secret:

```powershell
kubectl create secret generic kagent-openai `
  --from-literal=OPENAI_API_KEY=$env:OPENAI_API_KEY `
  -n kagent
```

### 6. Wait for workloads

```powershell
kubectl get pods -n kagent -w
```

Every pod should be `Running` with a complete positive readiness ratio such as
`1/1` or `2/2`.

## Reconcile (if already installed)

Run these to ensure everything is current:

```powershell
helm upgrade --install kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent `
  --namespace kagent `
  --set providers.default=openAI `
  --set providers.openAI.apiKey=$env:OPENAI_API_KEY
```

Then ensure the secret exists:

```powershell
kubectl get secret kagent-openai -n kagent
```

If missing, create it as shown in step 5 above.

## Apply Sample A2A Resources

The lab uses three resources applied in order:

1. **`kagent-tool-server`** (`RemoteMCPServer`) - base resource shared by multiple agents
2. **`kagent-tool-server-runtime`** (Deployment + Service + RBAC) - MCP server runtime that backs the RemoteMCPServer URL
3. **`k8s-a2a-agent`** (`Agent`) - sample A2A agent for read-only cluster inspection

Apply them in order:

```powershell
kubectl apply -f deploy/base/kagent/kagent-tool-server.yaml
kubectl apply -f deploy/base/kagent/kagent-tool-server-runtime.yaml
kubectl apply -f deploy/samples/kagent/k8s-a2a-agent.yaml
```

Wait for the tool server pod to become ready:

```powershell
kubectl wait --for=condition=Ready pod -n kagent -l app.kubernetes.io/component=tool-server-runtime --timeout=120s
```

Resources are organized as:

```
deploy/
  base/kagent/
    kagent-tool-server.yaml           # shared MCP server reference (RemoteMCPServer CR)
    kagent-tool-server-runtime.yaml   # MCP server runtime (Deployment + Service + RBAC)
  samples/kagent/
    k8s-a2a-agent.yaml                # sample A2A agent (educational / lab use)
```

## Verify Health

### Quick health check

```powershell
.\scripts\kagent\check-kagent-health.ps1
```

This inspects:
- pod readiness (all pods Running with complete positive ratios such as `1/1` or `2/2`)
- agent status (Accepted=True, Ready=True)
- RemoteMCPServer status
- recent events
- service endpoint hints for port-forward

### Manual inspection commands

```powershell
# Pod health
kubectl get pods -n kagent
kubectl describe pod -n kagent <pod-name>

# Agent health
kubectl get agent -n kagent
kubectl describe agent k8s-a2a-agent -n kagent

# RemoteMCPServer health
kubectl get remotemcpserver -n kagent
kubectl describe remotemcpserver kagent-tool-server -n kagent

# Events
kubectl get events -n kagent --sort-by=.lastTimestamp

# Logs (key pods)
kubectl logs -n kagent deployment/kagent-controller --tail=50
kubectl logs -n kagent deployment/kagent-ui --tail=50
```

## Open the kagent UI

```powershell
# Terminal 1: UI (port 8080)
kubectl port-forward -n kagent svc/kagent-ui 8080:8080
```

Then open `http://localhost:8080`.

## Test A2A

### Terminal 2: Controller port-forward

```powershell
kubectl port-forward -n kagent svc/kagent-controller 8083:8083
```

### Run the A2A test script

```powershell
# Fetch the agent card (shows accepted/ready state, model, skills)
python scripts/kagent/test-a2a-agent.py card

# Full test: card + task dispatch attempt
python scripts/kagent/test-a2a-agent.py both

# Probe available A2A JSON-RPC methods
python scripts/kagent/test-a2a-agent.py probe

# Inspect the kagent REST API directly
curl.exe http://localhost:8083/api/agents/kagent/k8s-a2a-agent
```

Expected output from `card`:
```
Agent: kagent/k8s-a2a-agent
Accepted: True
DeploymentReady: True
Model: gpt-4.1-mini (OpenAI)
Skills (1):
  - get-resources-skill: Get Resources - Get resources in the Kubernetes cluster
```

### A2A client compatibility note

The current controller does not expose legacy `tasks/sendTask`, and the tested
blocking `message/send` path fails internally. Controller 0.9.11's working L4
path is the same path used by the UI: `message/stream` over SSE with a complete
`MessageSendParams` text message. The repository helper implements and strictly
validates that path; no external `a2a-cli` installation is recommended.

The REST API agent card fetch works reliably and verifies that the agent is
accepted, ready, and configured with the correct skills.

The helper uses truthful exit codes:

- `card` exits 0 when agent metadata/card details are reachable.
- `probe` exits 0 when method probing completes, even if methods are unsupported.
- `task` exits 0 only after a valid `message/stream` response contains a
  non-empty task/message id in an accepted state.
- `both` exits 0 only when both card validation and task dispatch pass.

With a controller port-forward, the recorded Phase 5D `task` and `both` paths
pass L4. A later terminal model failure does not revoke L4 after an accepted
state was observed; it still does not prove L6.

### IDE-safe profile (minimal agents + exact inventory)

The controller’s `list_agents` returns every accepted, deployment-ready Agent
**cluster-wide**. A separate namespace alone is not isolation. Do not scale down
agent Deployments as durable isolation (the controller may reconcile them).

**Pre-reset capture** (local recovery copies only; do not commit secrets):

```powershell
helm get values kagent -n kagent -a
kubectl get agents -A -o yaml
kubectl get modelconfigs -A -o yaml
kubectl get remotemcpservers -A -o yaml
```

**Preferred install path for Cursor acceptance** uses the kagent **Minimal**
profile (no predefined demo agents). CLI:

```powershell
kagent install --profile minimal
```

For Helm on pinned chart `0.9.11`, disable each default agent individually
(there is no single chart-wide Minimal toggle). Example pattern from upstream
docs: `--set agents.<name>.enabled=false` for each predefined agent
(`observability-agent`, `helm-agent`, `k8s-agent`, and others listed in the
chart). After a Minimal/core install, apply only reviewed lab resources:

```powershell
kubectl apply -f deploy/base/kagent/kagent-tool-server.yaml
kubectl apply -f deploy/base/kagent/kagent-tool-server-runtime.yaml
kubectl apply -f deploy/samples/kagent/k8s-a2a-agent.yaml
kubectl get agents -A
```

Wait until `k8s-a2a-agent` reports current-generation `Accepted=True` and
deployment-ready (`status.observedGeneration` equals `metadata.generation`).

For an existing Demo install, deliberately uninstall/reinstall to Minimal or
delete unreviewed Agent CRs cluster-wide; never hide deletion inside the Python
helper.

### Target-specific Ollama ModelConfig (IDE-safe)

Do **not** mutate shared `default-model-config`. Use a target-only ModelConfig
after Ollama is reachable from inside the cluster.

1. On Windows, set `OLLAMA_HOST=0.0.0.0:11434`, restart the Ollama tray app, and
   restrict the Windows Firewall so port `11434` is not broadly exposed to the
   LAN/public internet (Docker Desktop / virtual-network path only).
2. Pull pinned model `qwen2.5:7b-instruct` and record its local digest.
3. Probe from a temporary cluster Pod:
   `GET http://host.docker.internal:11434/api/version` and
   `GET http://host.docker.internal:11434/api/tags`, then delete the probe.
   Do not use `http://localhost:11434` inside a Kubernetes workload.
4. Optional direct Ollama capability probes (bounded reply, contextual follow-up,
   dummy tool schema) are provider qualification only — not I3 evidence.
5. Capture the current agent ModelConfig, apply the IDE-safe config, merge-patch
   only `k8s-a2a-agent`, wait for current-generation Accepted/Ready:

```powershell
kubectl get agent k8s-a2a-agent -n kagent `
  -o jsonpath="{.spec.declarative.modelConfig}{'\n'}"
kubectl apply -f deploy/samples/kagent/ide-safe-ollama-model-config.yaml
kubectl patch agent k8s-a2a-agent -n kagent --type merge `
  --patch-file config/kagent/k8s-a2a-agent-ide-safe-modelconfig-patch.yaml
```

Never `kubectl apply` the merge-patch files; they are not complete Agent
manifests. Rollback:

```powershell
kubectl patch agent k8s-a2a-agent -n kagent --type merge `
  --patch-file config/kagent/k8s-a2a-agent-default-modelconfig-patch.yaml
kubectl get agent k8s-a2a-agent -n kagent `
  -o jsonpath="{.spec.declarative.modelConfig}{'\n'}"
```

Expected rollback value: `default-model-config`.

### Target-specific DeepSeek fallback (IDE-safe)

Use this fallback only after the local `DEEPSEEK_API_KEY` is available to the
acceptance operator. The key is passed through a local process into a
namespace-local Secret; never print it, place it in a manifest, or commit it.
The qualification helper tries `deepseek-v4-flash` first and tries
`deepseek-v4-pro` only when Flash does not qualify.

```powershell
$env:DEEPSEEK_API_KEY = [Environment]::GetEnvironmentVariable('DEEPSEEK_API_KEY', 'User')
uv run python scripts/kagent/deepseek_provider_probe.py --output json
Remove-Item Env:DEEPSEEK_API_KEY
```

Exit `0` selects a candidate only after a bounded no-tool response and a dummy
function-schema response both pass. Its JSON contains only model names, HTTP
statuses, latency, and pass/fail information—never the API key or response
text. Exit `1` means no candidate qualified; keep I3 Blocked and do not apply a
target profile.

After exit `0`, create the local-only Secret, apply the selected profile, patch
only `k8s-a2a-agent`, and wait for both the Agent and its Deployment rollout:

```powershell
$deepSeekKey = [Environment]::GetEnvironmentVariable('DEEPSEEK_API_KEY', 'User')
if ([string]::IsNullOrWhiteSpace($deepSeekKey)) { throw 'DEEPSEEK_API_KEY is unavailable.' }
$deepSeekEnvFile = New-TemporaryFile
try {
  [IO.File]::WriteAllText(
    $deepSeekEnvFile.FullName,
    "DEEPSEEK_API_KEY=$deepSeekKey`n",
    [Text.UTF8Encoding]::new($false)
  )
  kubectl create secret generic kagent-deepseek -n kagent `
    --from-env-file=$deepSeekEnvFile.FullName --dry-run=client -o yaml |
    kubectl apply -f -
  if ($LASTEXITCODE -ne 0) { throw 'Secret creation failed.' }
}
finally {
  Remove-Item -LiteralPath $deepSeekEnvFile.FullName -Force -ErrorAction SilentlyContinue
  Remove-Variable deepSeekKey -ErrorAction SilentlyContinue
}
kubectl apply -f deploy/samples/kagent/ide-safe-deepseek-model-config.yaml
kubectl patch agent k8s-a2a-agent -n kagent --type merge `
  --patch-file config/kagent/k8s-a2a-agent-ide-safe-deepseek-modelconfig-patch.yaml
kubectl wait --for=condition=Accepted=true agent/k8s-a2a-agent -n kagent --timeout=180s
kubectl wait --for=condition=Ready=true agent/k8s-a2a-agent -n kagent --timeout=180s
kubectl rollout status deployment/k8s-a2a-agent -n kagent --timeout=180s
```

Before a strict retry, run observation mode so a live bounded reply can be
captured without treating punctuation mismatch as a fake pass:

```powershell
uv run python scripts/kagent/controller_mcp_smoke.py --output json `
  --observe-only `
  --expected-inventory config/kagent/ide-safe-agent-inventory.txt
```

Observation mode still requires exact controller tools, singleton exact
inventory (including the final same-session `list_agents` re-check), a
non-empty bounded first reply (capped at 160 sanitized characters), and a
non-empty `context_id`. It performs only the first `invoke_agent`, skips
exact-text equality and context continuation, and always records
`observationOnly: true` with `strictPreflightQualified: false`. Observation
success is not I3 proof.

Helper default tasks and `--expected-response` /
`--continuation-expected-response` values are built from the same canonical
tokens (`ACCEPTANCE_TOKEN` / `CONTINUATION_TOKEN`). Do not change those defaults
from a single live observation, and do not paper over mismatches with
punctuation-adjusted CLI overrides. Use a freshly observed reply only as an
explicit CLI value for an immediate diagnostic retry; update the runbook or
evidence afterward only through a dated addendum if warranted.

```powershell
uv run python scripts/kagent/controller_mcp_smoke.py --output json `
  --expected-inventory config/kagent/ide-safe-agent-inventory.txt
```

If the first DeepSeek ModelConfig-only strict attempt fails continuation
exactness (for example by prepending prior reply text), roll back, then try
one Candidate B profile: DeepSeek ModelConfig plus the target-only
`systemMessage` merge patch that forbids restating the task and forbids all
tool calls (declared tools may remain on the Agent):

```powershell
kubectl patch agent k8s-a2a-agent -n kagent --type merge `
  --patch-file config/kagent/k8s-a2a-agent-ide-safe-deepseek-modelconfig-patch.yaml
kubectl patch agent k8s-a2a-agent -n kagent --type merge `
  --patch-file config/kagent/k8s-a2a-agent-ide-safe-deepseek-i3-systemmessage-patch.yaml
```

Rollback after Candidate B must restore both `default-model-config` and the
original sample `systemMessage`:

```powershell
kubectl patch agent k8s-a2a-agent -n kagent --type merge `
  --patch-file config/kagent/k8s-a2a-agent-default-profile-rollback-patch.yaml
```

A failed readiness or controller diagnostic must restore the default profile
with the appropriate rollback patch. A successful provider probe or Python
diagnostic is preparation only; I3 still requires the Cursor tool-call trace
and it never proves I4 or L6.

### Verify the native controller MCP surface

The project-scoped Cursor and Codex configurations both target the discovered
controller endpoint. This is the normal IDE-facing seam; the A2A commands above
remain protocol and evidence diagnostics.

```powershell
kubectl port-forward -n kagent svc/kagent-controller 8083:8083
# Educational / shared lab: target presence only
python scripts/kagent/controller_mcp_smoke.py --output json
# Educational allowlist (multi-agent labs that deliberately approve each ref)
python scripts/kagent/controller_mcp_smoke.py --output json `
  --strict-agent-inventory `
  --approved-agent kagent/k8s-a2a-agent `
  --approved-agent kagent/another-reviewed-agent
# IDE-safe exact profile (authoritative; mutually exclusive with --approved-agent)
python scripts/kagent/controller_mcp_smoke.py --output json `
  --expected-inventory config/kagent/ide-safe-agent-inventory.txt
# Observation-only (requires --expected-inventory; not a strict preflight)
python scripts/kagent/controller_mcp_smoke.py --output json `
  --observe-only `
  --expected-inventory config/kagent/ide-safe-agent-inventory.txt
```

`--expected-inventory` implies exact-set equality against the committed file
under `config/kagent/` (`discovered == expected`), records
`expectedInventoryCanonicalSha256` from sorted refs (not raw checkout bytes),
and fails on unexpected, missing, or duplicate discovered refs. Do not rubber-
stamp unreviewed agents to make the inventory pass; isolate the lab to the
singleton profile instead. Default (non-strict) mode only checks target presence
for shared educational environments. The Python helper default HTTP timeout
remains 30s; it is a prerequisite diagnostic, not an I3 proof.

`--observe-only` keeps the same tool, inventory, non-empty bounded reply, and
`context_id` gates for the first invoke, then skips exact-text equality and
context continuation while still re-checking inventory on the same MCP session.
It never sets `strictPreflightQualified`. Use a fresh observation only as an
explicit `--expected-response` for an immediate strict retry; do not rewrite
helper defaults from one model reply.

Expected success behavior: the helper exits `0` after `initialize`,
`tools/list`, `list_agents`, a bounded `invoke_agent` response, a second
`invoke_agent` with the returned `context_id` (agent-context continuation), and
MCP-session reuse via a later `list_agents` on the same session. It records
session and context identifiers only as `present`/`missing`, never raw values.
Strict success also sets `strictPreflightQualified: true`. That marker means
controller preflight only; it is not I3 acceptance.
`cleanup: method-not-allowed` means explicit client-triggered MCP session
termination was attempted but is unsupported by the pinned controller; it does
not prove the session was deleted. Phase 8 owns lab resource cleanup separately.
Exit `1` means the controller contract or bounded agent result did not qualify;
exit `3` means the endpoint was unavailable. Neither result proves I3 or L6.
Canonical status: [evidence/kagent/README.md](../../evidence/kagent/README.md).

### Cursor I3 acceptance gate (lead client)

Genuine I3-Cursor requires a real Cursor client run. The Python helper above is
necessary preparation, not sufficient evidence. Local inspection of Cursor 3.13
CLI help on this host showed `cursor.exe` options including `--add-mcp` and an
`agent` subcommand, but no dedicated `cursor-agent mcp` / `cursor mcp` tool-call
surface with stable documented syntax for `list_agents` / `invoke_agent`. Do not
invent CLI syntax. Use the Cursor UI path below unless a future dated inspection
records a verified MCP invocation command.

Cadence: exact preflight → Cursor work → exact postflight.

1. Start the controller port-forward:
   `kubectl port-forward -n kagent svc/kagent-controller 8083:8083`
2. Exact preflight:
   `python scripts/kagent/controller_mcp_smoke.py --output json --expected-inventory config/kagent/ide-safe-agent-inventory.txt`
3. Open this repository in Cursor so project `.cursor/mcp.json` loads
   `kagent-controller` at `http://127.0.0.1:8083/mcp`.
4. Confirm the MCP server is visible in Cursor MCP settings/tools UI.
5. Confirm exactly the tools `list_agents` and `invoke_agent` are exposed.
6. From Cursor, call `list_agents`; require exact singleton
   `kagent/k8s-a2a-agent`.
7. Bounded first `invoke_agent` for `kagent/k8s-a2a-agent` with a no-tool task
   whose exact reply is known. Do not request Kubernetes, MCP, shell, or other
   tools during I3.
8. From a Cursor MCP tool-call trace / tool details panel / developer log,
   confirm first output `context_id` is present (do not retain the raw value).
9. Second `invoke_agent` must include that same `context_id` in the **tool-call
   input arguments**. A coherent second answer without argument evidence is not
   enough. If Cursor cannot expose second-call arguments, record
   `I3-Cursor: Blocked — second-call Cursor MCP tool-input arguments were not
   observable in the acceptance environment`.
10. Exact postflight with the same `--expected-inventory` command.
11. Record dated evidence in
    `evidence/kagent/educational-practice-phase-6b-6d-closure.md`.
    Never store secrets, raw MCP session ids, or raw `context_id` values.

I3-Cursor Blocked reasons are classified at the earliest failed stage:

- `tool_discovery`:
  `KAGENT_MCP_TOOLS_NOT_EXPOSED`
- `first_invoke_result`:
  `CURSOR_DID_NOT_EXPOSE_CONTEXT_ID`
- `second_invoke_trace`:
  `SECOND_CALL_ARGUMENTS_NOT_OBSERVABLE`

Do not assign a later-stage reason when the acceptance sequence did not reach
that stage.

Evidence template fields (sanitized only):

- date, timezone, environment, controller version
- client: Cursor (version if shown)
- port-forward command and local URL
- MCP server name visible in Cursor
- tools observed (`list_agents`, `invoke_agent` only)
- discovered agent refs (names only)
- expected inventory path + canonical SHA-256
- preflight/postflight inventoryMatched
- first invoke: exact expected response matched true/false
- `firstInvokeContextId`: `present` or `missing`
- `secondInvokeIncludedContextId`, `contextIdentityMatched`,
  `rawContextIdRetained: false`
- Cursor trace proves second invoke included first context: true/false
- MCP session reuse observed true/false (separate from context continuation)
- provider/agent error observed true/false
- explicit non-claims: not L6; not I4; Python helper alone is not I3

Codex may be recorded as I3-Codex after I3-Cursor. I5 requires both clients.
I3 never implies L6.

#### Close out the human Cursor session

Do not roll back before the Cursor result is captured. After the interaction:

1. run the exact postflight from step 10;
2. restore the shared default ModelConfig and original sample `systemMessage`:

   ```powershell
   kubectl patch agent k8s-a2a-agent -n kagent --type merge `
     --patch-file config/kagent/k8s-a2a-agent-default-profile-rollback-patch.yaml
   ```

3. verify the Agent is Accepted/Ready and observed generation matches;
4. identify the actual listener before stopping the forward:

   ```powershell
   Get-NetTCPConnection -LocalPort 8083 -State Listen |
     Select-Object LocalAddress, LocalPort, OwningProcess
   Get-Process -Id <owning-process-id>
   Stop-Process -Id <owning-process-id>
   ```

   A PowerShell wrapper may own a child `kubectl` process while only the child
   owns port 8083. Stop the verified listener and then the exact wrapper if it
   remains; never kill processes by a broad name match.
5. append one dated, sanitized addendum to the Phase 6B-6D evidence record.

The decision branch is:

- qualifying trace: request an I3 promotion review, synchronize the canonical
  status owners, and keep I4/L6/I5/L7 unchanged; or
- missing input visibility: append the exact Blocked wording above and leave
  PR #3 draft.

Any evidence or documentation commit changes the final SHA. Push that final SHA
and require the complete `quality.yml` workflow before undrafting or merging.

## How to Observe Failures

### Agent not Accepted

```powershell
kubectl describe agent k8s-a2a-agent -n kagent
```

Common causes:
- Missing `RemoteMCPServer`: `kubectl get remotemcpserver -n kagent`
- Missing secret: `kubectl get secret -n kagent`
- Controller logs: `kubectl logs -n kagent deployment/kagent-controller --tail=50`

### Pod not Running

```powershell
kubectl describe pod -n kagent <pod-name>
kubectl logs -n kagent <pod-name> --tail=50
kubectl get events -n kagent --sort-by=.lastTimestamp
```

Common causes:
- `CreateContainerConfigError`: missing secret or ConfigMap
- `ImagePullBackOff`: image not accessible
- `CrashLoopBackOff`: inspect logs for application errors

### Health check script

```powershell
.\scripts\kagent\check-kagent-health.ps1
```

Default remains CardLab (pods + accepted/ready agents). Named profiles make
capability claims explicit — see
[kagent health profiles](../reference/kagent-health-profiles.md).

```powershell
.\scripts\kagent\check-kagent-health.ps1 -Profile CardLab
.\scripts\kagent\check-kagent-health.ps1 -Profile DirectMcpServer -DirectMcpResultPath <sanitized-json> -OutputFormat Json
.\scripts\kagent\check-kagent-health.ps1 -Profile A2ADispatch -ControllerUrl http://127.0.0.1:8083
.\scripts\kagent\check-kagent-health.ps1 -Profile FullMcpExecution -ControllerUrl http://127.0.0.1:8083
.\scripts\kagent\check-kagent-health.ps1 -Profile FullMcpExecution -ControllerUrl http://127.0.0.1:8083 -AgentToolEvidencePath <agent-mediated-json>

# FullMcpExecution uses the canonical target by default
.\scripts\kagent\check-kagent-health.ps1 `
  -Profile FullMcpExecution `
  -ControllerUrl http://127.0.0.1:8083
```

On the current lab, expect CardLab, DirectMcpServer, and A2ADispatch to pass
when the controller port-forward is up and the A2A helper can complete
`message/stream`. FullMcpExecution still fails until a live correlated L6
record exists ([phase 5e](../../evidence/kagent/educational-practice-phase-5e-agent-mediated-mcp.md)).
Omitting `-AgentToolEvidencePath` invokes `agent_mcp_trace.py --output json`.

### Trustworthy A2A helper

```powershell
kubectl port-forward -n kagent svc/kagent-controller 8083:8083
python scripts/kagent/test-a2a-agent.py card --controller http://127.0.0.1:8083 --output json
python scripts/kagent/test-a2a-agent.py probe --controller http://127.0.0.1:8083 --output json
python scripts/kagent/test-a2a-agent.py task --controller http://127.0.0.1:8083 --output json
python scripts/kagent/test-a2a-agent.py both --controller http://127.0.0.1:8083 --output json
```

Pinned dispatch: `POST /api/a2a/{ns}/{agent}` method `message/stream` (SSE).
Schema: [kagent-a2a-dispatch-evidence.md](../reference/kagent-a2a-dispatch-evidence.md).
Live L4 evidence: `evidence/kagent/educational-practice-phase-5d-trustworthy-a2a.md`.

### Agent-mediated MCP correlation helper

```powershell
kubectl port-forward -n kagent svc/kagent-controller 8083:8083
python scripts/kagent/agent_mcp_trace.py --controller http://127.0.0.1:8083 --output json
```

Requires an observable `k8s_get_resources` invocation correlated to the A2A
taskId from the same Phase 5E dispatch (agent/tool/model structured part or
bounded correlated logs), normalized `pod`/`kagent` arguments, same-task names
returned after the observation, a repo-contained source record, and a
recomputed kubectl name match. The helper observes the actual kubectl context;
it must be `docker-desktop`. `FullMcpExecution` does not send a second A2A task.
Schema: [kagent-agent-mediated-mcp-evidence.md](../reference/kagent-agent-mediated-mcp-evidence.md).
Live attempt: `evidence/kagent/educational-practice-phase-5e-agent-mediated-mcp.md`
(L6 Not proven; L4 unchanged).

### Direct MCP session smoke

Learner-owned port-forward, then the session helper. A successful live run proves
**direct MCP tool invocation only**. It does **not** prove L6 agent-mediated
tool use. Live evidence: `evidence/kagent/educational-practice-phase-5b-direct-mcp.md`.

```powershell
kubectl port-forward -n kagent svc/kagent-tool-server 8000:8000
python scripts/kagent/mcp_session_smoke.py --url http://127.0.0.1:8000/mcp --output json --resource-type pod --resource-namespace kagent
```

Expected: exit code `0`, `sessionId` reported as `present` (never print the raw
value), `toolCallSucceeded: true`, and a `cleanup` status such as `deleted`.

If cleanup fails (e.g. DELETE returns a server error), the script exits 1 to
prevent silent session leaks. HTTP 405 (Method Not Allowed) on cleanup is benign
and does not cause a failure.

Problem context: `evidence/kagent/problems/2026-07-17-mcp-session-reuse.md`.

## Known Limitations

1. **Blocking A2A methods** `tasks/sendTask` and empty-param `message/send` /
   `message/stream` probes still return JSON-RPC errors on controller 0.9.11.
   Use the pinned MessageSendParams `message/stream` path documented above.
   Historical phase 5 failures remain in
   `evidence/kagent/educational-practice-phase-5.md`.

2. **`kagent-grafana-mcp` RemoteMCPServer `Accepted=False`** is the remaining
   expected degraded-lab state. The controller cannot reach the backing service at
   `http://kagent-grafana-mcp.kagent:8000/mcp` because no MCP server is deployed there.
   `kagent-tool-server` was in this state before Subphase 4C (July 16, 2026) and
   is now `Accepted=True` with a real MCP server deployed behind it via the
   `deploy/base/kagent/kagent-tool-server-runtime.yaml` manifest.

3. **Pod restart counts increase with each `helm upgrade`.** Each Helm upgrade
   triggers a rolling restart. On a fresh install most pods show 1 restart
   (the initial container start). After multiple upgrades, counts can grow:
   most pods accumulate restarts from each rollout, while the controller and
   UI pods accumulate additional restarts from the initial secret-not-found
   cycle. Restart counts do not affect pod readiness (`1/1 Running`) or agent
   acceptance.

4. **Port-forward sessions** block the terminal. Use separate terminals or
   `Start-Process` for background port-forwards.

5. **Terminal stream state may be `failed`** (for example model quota) after
   `submitted`/`working`. L4 is still proven when an accepted state with a
   non-empty task id was observed; that does not prove L6.

## Verdict Script (One-Command Lab Check)

Run this after applying manifests and port-forwards:

```powershell
# 1. Health check
.\scripts\kagent\check-kagent-health.ps1

# 2. A2A card fetch
python scripts/kagent/test-a2a-agent.py card

# 3. UI check
curl.exe -s -o NUL -w "%{http_code}\n" http://localhost:8080
```

If step 1 exits 0, step 2 prints `Accepted: True`, and step 3 prints `200`,
the lab is working.

## Related Docs

- [Deploy structure](../../deploy/README.md)
- [kagent educational roadmap](../onboarding/KAGENT-EDUCATIONAL-ROADMAP.md)
- [kagent current evidence and flaw ledger](../../evidence/kagent/README.md)
- [kagent capability definitions](../reference/kagent-capability-matrix.md)
- [documentation organization rules](../DOCUMENTATION-ORGANIZATION.md)
- [scripts/kagent/check-kagent-health.ps1](../../scripts/kagent/check-kagent-health.ps1)
- [scripts/kagent/KagentHealth.psm1](../../scripts/kagent/KagentHealth.psm1)
- [kagent health profiles](../reference/kagent-health-profiles.md)
- [kagent-a2a-dispatch-evidence.md](../reference/kagent-a2a-dispatch-evidence.md)
- [scripts/kagent/test-a2a-agent.py](../../scripts/kagent/test-a2a-agent.py)
- [scripts/kagent/mcp_session_smoke.py](../../scripts/kagent/mcp_session_smoke.py)
- [docs/onboarding/GETTING-STARTED.md](../onboarding/GETTING-STARTED.md)
