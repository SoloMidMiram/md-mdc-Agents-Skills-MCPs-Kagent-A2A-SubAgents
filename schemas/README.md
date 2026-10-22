# Capability schemas (LLMLite owns; MCPtest intends to consume)

LLMLite owns `capability_results.schema.json` and emits probe reports against it.
**This repo (MCPtest) intends to consume reports and apply selection policy
only.** No MCPtest in-repo schema consumer exists yet; the consumer boundary
below is the planned contract, not a shipped implementation.

## Status (2026-08-20)

| Artifact | Location | Status |
|----------|----------|--------|
| Results schema (owned) | LLMLite repo `schemas/capability_results.schema.json` | Owned by LLMLite; MCPtest pins `schema_version: "1.0"` |
| Boolean summary | LLMLite repo `schemas/capability-report.schema.json` | Optional coarse shape |

The LLMLite repository is a **local development checkout**; no published remote
URL or stable ref is pinned in this repo. Replace the relative path with the
LLMLite repository URL plus a stable ref once one is published.

Consumers pin `schema_version: "1.0"` as an **intended compatibility pin only**
and treat drift as a breaking change.

## Ownership rule

- LLMLite: owns `capability_results.schema.json` + emits reports
- MCPtest: intends to consume reports + apply selection policy (no consumer shipped)
- litellm-router: aliases only (no capability schema)

## Non-claims

This PR is documentation only. It contains no report loader, no schema
validator, no selection-policy implementation, and no runtime capability proof.
MCPtest is the **intended** consumer, not an implemented one.

LLMLite's own L0–L7 capability fields do **not** automatically promote or change
the canonical kagent L0–L7 matrix in
`docs/reference/kagent-capability-matrix.md`. The two capability taxonomies are
independent.
