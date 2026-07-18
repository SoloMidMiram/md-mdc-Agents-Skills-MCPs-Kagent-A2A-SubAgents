# Architecture Decisions

Record durable architecture decisions here with date, context, and rationale.

---

## 2026-06-24 — Project Scaffold Initialization

**Context:** Established the repository scaffold with VS Code Copilot customization files,
Python/Kubernetes tool stacks, and `.project-ai/memory/`.

**Decision:**
- Use `.github/copilot-instructions.md` for repository-wide agent rules
- Use `.github/instructions/*.instructions.md` for file-pattern-specific rules
- Use `.project-ai/memory/` for durable memory separate from agent instructions
- Use `uv` as the Python project manager
- Use `ruff` for linting and formatting
- Use `kubeconform` + `kube-linter` for Kubernetes validation
- Use `trivy` for security scanning

**Status:** Accepted

---

## 2026-07-17 — Isolate Educational Lanes from the Stable Core

**Context:** The repository contains a release-gated Playwright host-registration
core plus two evolving educational lanes: Playwright browser exercises and the
kagent/A2A/MCP lab. Lab assumptions and intentionally failing examples must not
become dependencies of normal agentic coding or stable validation.

**Decision:**

- Treat stable core, Playwright education, and kagent education as three zones.
- Allow educational lanes to consume stable contracts, but forbid stable tests
  and configuration from depending on live learner, browser, website, or cluster state.
- Require a documented promotion gate before lab helpers enter the stable core.
- Capture educational problems as evidence first; promote them to runbooks,
  rules, tests, or architecture decisions only when repeatable and proven.
- Use `docs/architecture/EDUCATIONAL-LANES-ARCHITECTURE.md` as the boundary design
  and `docs/runbooks/educational-problem-manual.md` as the diagnostic workflow.

**Status:** Accepted
