# Educational Lanes Architecture

This architecture lets the Playwright MCP and kagent educational projects grow
without destabilizing the repository's agentic-coding and release-gated core.
It describes ownership and promotion boundaries, not a production deployment.

## Architecture Goals

- Keep normal agentic coding, host configuration, and validation dependable.
- Let educational exercises fail intentionally and evolve quickly.
- Share concepts and proven utilities without coupling the two labs together.
- Prevent local cluster, browser, or learner-specific assumptions from entering
  the stable path without explicit promotion.
- Turn implementation problems into reusable knowledge without making every
  one-off failure a permanent rule.

## Three Zones

| Zone | Purpose | Primary artifacts | Change standard |
|------|---------|-------------------|-----------------|
| Stable core | Agentic coding contracts, host registration, rollback, quality and security gates | `AGENTS.md`, `constraints.md`, `config/templates/`, stable scripts and tests | Backward-compatible, tested, release-gated |
| Playwright education | Browser concepts, safe interaction exercises, local/remote runtime learning | Playwright runbooks, `server/`, `evidence/local/`, evaluation datasets | Reproducible exercise with cleanup and explicit safety boundary |
| kagent education | Kubernetes, A2A, MCP discovery and agent-mediated execution learning | kagent roadmap/runbook, `deploy/`, `scripts/kagent/`, `evidence/kagent/` | Capability-gated and local-cluster scoped |

The Playwright stable host installer belongs to the stable core. Playwright
*exercises* belong to the educational lane. This distinction prevents an
experimental exercise from weakening installer or rollback guarantees.

## Dependency Rule

Dependencies point inward toward stable contracts:

```text
Playwright education ─┐
                      ├──> stable interfaces and validation
kagent education ─────┘

stable core -X-> learner state, live browser state, or local cluster state
Playwright education -X-> kagent education implementation details
kagent education -X-> Playwright education implementation details
```

Both lanes may use shared terminology, templates, and validation helpers. They
must not import each other's environment assumptions. A cross-lane example is a
third integration experiment until it earns its own contract.

## Stable-Core Protection Rules

1. Educational scripts must default to a local, disposable, or read-only scope.
2. Stable tests must not depend on a live website, browser session, Docker
   Desktop cluster, cloud subscription, secret, or learner evidence file.
3. Lab failures must not be hidden by weakening stable tests or policies.
4. Samples live under `deploy/samples/`; reusable primitives live under
   `deploy/base/`; environment assembly belongs in overlays.
5. Generated output belongs in ignored result directories or dated evidence,
   never in source/config directories.
6. Stable interfaces may be consumed by labs; lab-specific behavior cannot be
   added to the stable interface without the promotion process below.
7. Live-environment status is evidence, not configuration and not a test oracle.

## Educational Project Contract

Every exercise or phase should define:

- learning objective;
- prerequisites and version assumptions;
- allowed side effects and safety boundary;
- exact commands or agent prompt;
- observable pass and fail criteria;
- what the result proves and does not prove;
- evidence destination;
- cleanup or rollback;
- escalation path when the exercise exposes a product defect.

Playwright exercises use exercise-level gates. kagent uses the canonical L0-L7
capability gates. Both use the same problem-record workflow.

## Change and Promotion Flow

```text
idea -> isolated exercise -> observed evidence -> repeatable diagnosis
     -> automated regression -> stable-interface review -> promotion
```

A lab artifact may enter the stable core only when all of these are true:

1. the behavior is useful outside one exercise;
2. inputs, outputs, side effects, and failure semantics are documented;
3. deterministic tests do not require live learner state;
4. security and rollback implications are reviewed;
5. stable validation passes unchanged;
6. the roadmap and `REPO_MANIFEST.yaml` identify the new owner;
7. a durable decision is recorded when the boundary or architecture changes.

Until then, keep the artifact explicitly labeled `lab`.

## Review Cadence

Do not block every new exercise on a full repository review. Use three review
sizes:

| Review | When | Scope |
|--------|------|-------|
| Exercise check | Before each example | Contract fields, safety, cleanup, evidence path |
| Lane review | When adding a phase, dependency, or reusable helper | Lane roadmap, neighboring exercises, regression coverage |
| Architecture review | Before changing stable interfaces, security boundaries, deployment ownership, or cross-lane dependencies | This architecture, constraints, decision record, release gates |

## Ownership Map

| Question | Canonical source |
|----------|------------------|
| Where should a document go? | `docs/DOCUMENTATION-ORGANIZATION.md` |
| How are educational lanes isolated? | This document |
| How do I record and resolve a problem? | `docs/runbooks/educational-problem-manual.md` |
| What is currently proven for kagent? | `evidence/kagent/README.md` |
| What are kagent capability levels? | `docs/reference/kagent-capability-matrix.md` |
| What protects the stable path? | `constraints.md` and release acceptance plan |
