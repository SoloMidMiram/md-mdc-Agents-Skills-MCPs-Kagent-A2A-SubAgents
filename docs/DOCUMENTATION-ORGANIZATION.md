# Documentation Organization Guide

This guide defines where repository knowledge belongs and how documentation
claims are kept consistent. It is the canonical rule for documentation
placement; `REPO_MANIFEST.yaml` remains the machine-readable artifact map.

## Document Classes

| Location | Purpose | May contain current status? |
|----------|---------|-----------------------------|
| `docs/onboarding/` | Entry points, learning order, and roadmaps | Summaries that link to canonical evidence |
| `docs/runbooks/` | Commands, expected results, recovery, and cleanup | Only operational expectations and dated links |
| `docs/reference/` | Stable definitions, matrices, and contracts | Yes, when explicitly designated canonical |
| `docs/architecture/` | Decisions, boundaries, and design rationale | No transient runtime counts |
| `evidence/<lane>/` | Dated observations and command results | Yes; this is the authority for observed runtime state |
| `reports/` | Dated, non-authoritative cross-cutting review snapshots | Only dated observations that link to canonical owners |
| `docs/archive/` | Superseded plans and historical material | No current claims or TODO ownership |

Educational lane boundaries and promotion rules are defined in
`docs/architecture/EDUCATIONAL-LANES-ARCHITECTURE.md`. Educational implementation
problems follow `docs/runbooks/educational-problem-manual.md`.

## Sources of Truth

For repository behavior, use this precedence:

1. code, tests, and deployment manifests;
2. `pyproject.toml` and other executable configuration;
3. architecture decisions;
4. dated evidence;
5. summaries and onboarding prose.

For the kagent lane specifically:

- `docs/reference/kagent-capability-matrix.md` defines L0-L7;
- `evidence/kagent/README.md` records the latest proven status and open flaws;
- `docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md` owns phase order and promotion gates;
- `docs/runbooks/local-kagent-a2a-lab.md` owns executable lab instructions.

## Writing Rules

1. Give every document one primary job.
2. Put volatile counts, dates, versions, and observed conditions in evidence.
3. Link to canonical status instead of copying it into multiple documents.
4. Label observations with a date and environment.
5. Separate `Proven`, `Not proven`, `Blocked`, and `Not attempted`.
6. Never promote indirect evidence: readiness is not dispatch, MCP acceptance is
   not invocation, and a direct MCP call is not an agent-mediated call.
7. A runbook command must state its expected exit behavior and what it proves.
8. Open work belongs in the applicable roadmap; evidence may describe a flaw but
   must not become a second backlog.
9. Superseded documents move to `docs/archive/` or become short redirects.
10. Every new canonical document must be added to `REPO_MANIFEST.yaml`.
11. Do not turn a one-off educational failure into a repository-wide rule; use
    the problem manual's evidence and promotion criteria.

## Evidence Record Contract

Every new evidence record must include:

- date, timezone, environment, and relevant component versions;
- exact command or interaction;
- exit code or protocol response;
- concise observed result;
- capability level proved, if any;
- explicit non-claims;
- links to raw sanitized output when output is too large for the record.

An evidence index may summarize records, but it must not strengthen their claims.

## Change Checklist

When behavior or observed state changes:

1. update code/manifests and tests;
2. capture or update dated evidence;
3. update the canonical capability/status index;
4. update roadmap completion and remaining gates;
5. update runbook commands only if the operational path changed;
6. update onboarding links, avoiding copied runtime snapshots;
7. update `REPO_MANIFEST.yaml`;
8. run link, formatting, and relevant code/manifest validation.

## Naming

- Use lowercase kebab-case for new general documentation files.
- Keep established uppercase roadmap names until a deliberate migration.
- Name dated evidence directories `YYYY-MM-DD` when raw captures are introduced.
- Use `README.md` only as an index inside a focused directory.

## New-File Placement Rules

Choose a file's owner before choosing its name. Use the first matching row:

| File describes or implements | Location | Manifest policy |
|------------------------------|----------|-----------------|
| Repository-wide operating constraint | `AGENTS.md`, `constraints.md`, or scoped `.github/instructions/` | Always list canonical contracts |
| First-read navigation or learning sequence | `docs/onboarding/` | List canonical maps and roadmaps |
| Commands, recovery, cleanup, or diagnostics | `docs/runbooks/` | List maintained runbooks |
| Durable design boundary or rationale | `docs/architecture/` plus an architecture decision when durable | List authoritative architecture |
| Stable definition, matrix, or contract | `docs/reference/` | List canonical references |
| Copyable document/problem scaffold | `docs/templates/` | List reusable templates |
| Reusable agent request or workflow prompt | `.github/prompts/` | List when maintained as a repository artifact |
| Executable implementation logic | `scripts/<domain>/` or the applicable source package | List major entry points; require tests |
| Deterministic test or fixture | `tests/` or the owning test suite's `fixtures/` | Usually covered by suite entry; never store as evidence |
| Reusable deployment primitive | `deploy/base/<runtime>/` | List canonical manifests |
| Learner/sample deployment | `deploy/samples/<runtime>/` | Mark `lab`, never authoritative for production |
| Environment-specific assembly | `deploy/overlays/<environment>/` | List maintained overlays |
| Dated observed result | `evidence/<lane>/` | Index canonical summaries; individual records are non-authoritative |
| Dated cross-cutting review snapshot | `reports/` | List deliberately retained snapshots as non-authoritative; never use them as a status owner |
| Generated output or cache | ignored results/cache directory | Never add to manifest or commit |
| Disposable planning/staging note | ignored root/local temp path such as `PRECOMMIT-DRAFT.md` | Never add to manifest or commit |

Before creating a new file, answer:

1. What single question does it own?
2. Is that question already owned by another file?
3. Is it source, test, procedure, architecture, reference, evidence, generated
   output, or temporary planning?
4. Is it stable, lab, deferred, or historical?
5. Is it canonical? If yes, what existing file will link to it and what duplicate
   claim will be removed?
6. Does it require a test, evidence index update, roadmap item, or manifest entry?

Do not create a second roadmap, status ledger, or troubleshooting manual for the
same lane. Extend the canonical owner or add a narrowly scoped record that links
back to it.
