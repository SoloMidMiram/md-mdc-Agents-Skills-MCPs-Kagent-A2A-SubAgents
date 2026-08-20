# Capability schemas (LLMLite owns; MCPtest consumes)

LLMLite owns `capability_results.schema.json` and emits probe reports against it.
**This repo (MCPtest) consumes reports and applies selection policy only.**

## Status (2026-08-20)

| Artifact | Location | Status |
|----------|----------|--------|
| Results schema (owned) | `F:/Git/arvancloudai_Api/schemas/capability_results.schema.json` | Owned by LLMLite; MCPtest pins `schema_version: "1.0"` |
| Boolean summary | `F:/Git/arvancloudai_Api/schemas/capability-report.schema.json` | Coarse PR5 shape; optional |

Consumers pin `schema_version: "1.0"` from the LLMLite-owned path and treat
drift as a breaking change.

## Ownership rule

- LLMLite: owns `capability_results.schema.json` + emits reports
- MCPtest: consumes reports + applies selection policy
- litellm-router: aliases only (no capability schema)
