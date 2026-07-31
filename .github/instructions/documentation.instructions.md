---
name: Documentation
description: Documentation standards for the repository
applyTo: "docs/**/*.md,*.md"
---

# Documentation rules

- Keep `README.md` current with the project's purpose and quick-start.
- Document architecture decisions in `.project-ai/memory/architecture-decisions.md` with a unique number and date.
- Follow `docs/DOCUMENTATION-ORGANIZATION.md` for ownership and placement.
- Keep operational and diagnostic procedures in the applicable `docs/runbooks/` file.
- Use `docs/runbooks/educational-problem-manual.md` and its template for Playwright or kagent implementation problems.
- Keep transient observations in `evidence/`; promote only proven, reusable knowledge into runbooks or rules.
- Use Markdown with clear headings, code blocks, and lists.
- Prefer diagrams as Mermaid code blocks where practical.
- Update documentation as part of the same pull request as the code change.
