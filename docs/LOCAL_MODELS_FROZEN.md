# Local / Ollama models frozen (2026-08-20)

**Do not invoke local models** until the user explicitly lifts this freeze.

This is the **repository-wide** freeze policy. It binds all working surfaces
(lab scripts, manifests, CI, and any IDE/agent that acts in the repo). The
`.cursor/rules/no-local-models.mdc` rule is Cursor's enforcement point for this
policy; a local freeze deviation must be recorded in the relevant evidence, not
silently re-scoped to one tool.

## Frozen aliases / backends
- `agent-fast`, `agent-review`
- Any `local-*` alias (`local-qwen3-14b`, `local-gpt-oss`, `local-qwen-coder`, …)
- Any `ollama/*` or `ollama_chat/*` LiteLLM backend

## Allowed for live lab smokes / A2A / evals
- Cloud aliases only, preferably `agent-coder` → DeepSeek (`deepseek-chat`)
- Other cloud models already in LiteLLM (OpenAI, Arvan, etc.) if needed

## If cloud fails
Write **BLOCKED** evidence with the error. Do **not** fall back to Ollama/local.

## Why
Local models are too heavy for iterative lab runs on this workstation. Networking through LiteLLM is proven; remaining work uses cloud for speed and non-empty content.

