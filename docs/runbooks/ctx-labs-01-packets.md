# CTX-LABS-01: pinned evidence packets

Status: development lab stacked on CTX-01R; no merge/capability approval.
Prerequisites: full-history checkout containing #17, Python >=3.12 and frozen development dependencies.
From the repository root, choose a new absolute output directory outside the checkout:

```powershell
uv run --frozen --group dev python scripts/context/labs/examples.py replay --artifacts <external-new-directory>
```

Expected exit 0, two byte-identical UTF-8 packets and replay.json recording all six independently resolved Git hashes/physical-LF excerpts. Source revision is a53bfb62f0421a7c28234f871af2bf449a11491f. Original fixture and evidence remain unchanged. Git blob SHA-256 covers raw committed bytes.

Artifacts: packet-a.json, packet-b.json, command records and replay.json. Missing history, dirty selected sources, stale hashes/spans or existing output directory reject with exit 2. Nothing is overwritten. This proves reproducible context packaging, not coding improvement, approval or MCP delivery. See [corruption controls](ctx-labs-01-corruption.md) and [pilot](ctx-labs-01-pilot.md).
