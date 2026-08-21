# Capability schemas (LLMLite owns; MCPtest intends to consume)

LLMLite owns `capability_results.schema.json` and emits probe reports against it.
**This repo (MCPtest) intends to consume reports and apply selection policy
only.** No MCPtest in-repo schema consumer exists yet; the consumer boundary
below is the planned contract, not a shipped implementation.

## Status (2026-08-20)

| Artifact | Location | Status |
|----------|----------|--------|
| Results schema (owned) | LLMLite repo `schemas/capability_results.schema.json` | Owned by LLMLite; MCPtest pins `schema_version: "1.0"` |
| Boolean summary | LLMLite repo `schemas/capability-report.schema.json` | Coarse PR5 shape; optional |

Consumers would pin `schema_version: "1.0"` from the LLMLite-owned path and
treat drift as a breaking change.

## Ownership rule

- LLMLite: owns `capability_results.schema.json` + emits reports
- MCPtest: intends to consume reports + apply selection policy (no consumer shipped)
- litellm-router: aliases only (no capability schema)

