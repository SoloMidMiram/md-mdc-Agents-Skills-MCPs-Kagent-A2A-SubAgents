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

---

## 2026-07-31 — Prefer kagent's Embedded MCP Agent Surface

**Context:** The local pinned kagent controller `0.9.11` exposes a Streamable
HTTP MCP endpoint at its controller service. A live observation established the
native `list_agents` and `invoke_agent` contract, making a separate client-to-
A2A translation layer redundant.

**Decision:**

- Cursor and Codex integrate through the controller's native Streamable HTTP
  MCP endpoint when the pinned version exposes the compatible contract.
- The northbound contract is limited to reviewed `list_agents` and
  `invoke_agent` tools; Codex uses an explicit tool allowlist and both clients
  retain normal approval controls.
- A custom A2A-to-MCP gateway, agent directory, Cursor-specific adapter,
  duplicate task/session translator, reverse delegation, and autonomous cluster
  mutation are prohibited unless a dated live compatibility record proves that
  the native endpoint cannot satisfy a required capability.
- Direct A2A helpers remain protocol-conformance and evidence diagnostics. They
  are not the default Cursor/Codex integration seam.

**Status:** Accepted

---

## 2026-08-07 — A2A-First North Star (Priority Pivot)

**Context:** The project previously sequenced kagent work as Cursor I3 → read-only
MCP → direct A2A L6 → Cursor I4 → Codex parity. Cursor I3 tool-discovery
blockers delayed bounded multi-agent learning. Capability evidence (I0–I2 Proven,
I3 Blocked) remains accurate; only priority and sequencing change.

**Decision:**

- **North star:** First prove and measure useful A2A workflows inside kagent.
  Then attach Codex and Cursor as interchangeable clients/workers and compare them.
- Organize kagent work into four planning lanes: A (A2A education), S (safety/MCP),
  C (client interop), B (benchmarking). Lanes are not new capability numbering.
- Lane A (planner, reviewer, supervisor, docs agents; E1–E5) is the default
  priority after PR #3 foundation merges.
- Cursor I3 remains useful interoperability proof but is **not** the project spine
  and does not block A2A education.
- PR #3 merges with I0–I2 proven and I3 limitation recorded; **do not mark I3
  Proven** on merge. I3 acceptance moves to a future Lane C PR.
- L6 and I4 remain strict, separate experiments; neither blocks basic A2A education.
- Codex is the first automatable external coding worker; Cursor is an interactive
  northbound client. Architectural symmetry is not required.
- Current model: Cursor/Codex → MCP → kagent controller → A2A → kagent agents.
  Codex/Cursor as A2A workers is a later experiment.

**Status:** Accepted

**Reference:** `docs/north-star.md`, `docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md`
