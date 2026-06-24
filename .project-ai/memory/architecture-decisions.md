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
