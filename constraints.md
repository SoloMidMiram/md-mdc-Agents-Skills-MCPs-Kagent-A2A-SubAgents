# Project Constraints

Non-negotiables distilled from the agent contract, release gates, and deploy
policies. These apply during manual work, automation, and CI.

---

## Source of truth precedence

1. Repository code and tests
2. `pyproject.toml`
3. Deployment manifests
4. Architecture decisions (`.project-ai/memory/architecture-decisions.md`)
5. Memory documents (`.project-ai/memory/`) — evidence summaries, **not** authority

**Reference:** `AGENTS.md`

---

## CI invariants

- Do **not** weaken tests, security checks, or Kubernetes policies to obtain
  a passing CI run.
- CI must pass (`quality.yml`) before any `laptop-stable-*` tag is created.
- Pre-commit linters (black, isort, ruff) are enforced; their fixes must be
  applied locally, not disabled.

**Reference:** `.github/workflows/quality.yml`, `.pre-commit-config.yaml`

---

## Stable path vs lab path

- **Stable path** = Playwright MCP host registration (install, verify,
  rollback, Pester suite). This is the only release-gated path.
- **Lab path** = kagent / A2A on `docker-desktop`. Documented and working
  locally but explicitly **outside** the laptop-stable gate. No CI dependency.
- New lab features must not break stable path CI.
- Stable tests and configuration must not depend on live browser state, learner
  evidence, live websites, Docker Desktop cluster state, or lab-only secrets.
- Educational helpers enter the stable core only through the promotion gate in
  `docs/architecture/EDUCATIONAL-LANES-ARCHITECTURE.md`.

**Reference:** `docs/laptop-stable-acceptance-plan.md` (Non-Blocking section),
`docs/architecture/EDUCATIONAL-LANES-ARCHITECTURE.md`

---

## Installer invariants

- `scripts/install-global-playwright-mcp.ps1` must be **idempotent** —
  running it twice on a correct state must produce no backups and exit 0.
- `-WhatIf` must produce no side effects (no backup directory).
- Rollback must restore the original file byte-for-byte (SHA-256 verified).
- Source files must never be overwritten; only target host configs are
  mutated (with rollback backup).

**Reference:** Pester test suite (gates B–C in acceptance plan)

---

## Deploy taxonomy

- `deploy/base/` — reusable shared resources. Not standalone.
- `deploy/samples/` — standalone example manifests. Not authoritative.
- Do not use base manifests directly in production without environment
  overlay.

**Reference:** `deploy/README.md`

---

## Memory discipline

Write to `.project-ai/memory/` only when:

- a problem occurred more than once;
- a durable architectural decision was made;
- a diagnostic procedure was proven;
- a Kubernetes or security risk is reusable across future tasks.

**Reference:** `AGENTS.md`

---

## Ontology deferral

Full ontology (JSON Schema / OWL / Pydantic domain model) is deferred until:

1. `laptop-stable-v0.1.1` is tagged and CI is green.
2. Purpose-based doc routing is settled (numbered stubs retired).
3. Deploy taxonomy is implemented or explicitly scoped out.
4. Two or more registries need cross-linking with an automated consumer.
5. The vocabulary ("4 targets / 5 surfaces", layer names, gate names) is
   stable for at least one release cycle.

Until then, `docs/reference/GLOSSARY.md` + `REPO_MANIFEST.yaml` provide a
lightweight machine-readable bridge.

**Reference:** `docs/reference/GLOSSARY.md`, `REPO_MANIFEST.yaml`
