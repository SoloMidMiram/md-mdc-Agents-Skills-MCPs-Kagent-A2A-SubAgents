# AI Tooling Guide

This document describes the VS Code-native agent customization files
and how they interact with the broader MCP tooling laboratory.

## File Hierarchy

When VS Code Copilot processes a request, it loads instructions in this order:

1. `AGENTS.md` — shared rules for all agent hosts (VS Code, Cursor, Codex, Continue)
2. `.github/copilot-instructions.md` — repository-wide rules (VS Code only)
3. `.github/instructions/*.instructions.md` — file-pattern-specific rules (VS Code only)

## Customization Files

| File | Scope | Purpose |
|------|-------|---------|
| `AGENTS.md` | All agents | Cross-editor operating contract |
| `.github/copilot-instructions.md` | VS Code | Repository engineering rules |
| `.github/instructions/python.instructions.md` | `**/*.py` | Python quality rules |
| `.github/instructions/tests.instructions.md` | `tests/**/*.py` | Testing expectations |
| `.github/instructions/kubernetes.instructions.md` | `deploy/**/*.yaml` | K8s safety rules |
| `.github/instructions/security.instructions.md` | `**/*.py, **/*.yaml` | Security expectations |
| `.github/instructions/documentation.instructions.md` | `docs/**/*.md` | Documentation standards |
| `.github/prompts/quality-gate.prompt.md` | Reusable | Quality gate workflow |
| `.github/prompts/diagnose-failure.prompt.md` | Reusable | Failure diagnosis |
| `.github/prompts/review-kubernetes.prompt.md` | Reusable | K8s review workflow |
| `.github/prompts/update-project-memory.prompt.md` | Reusable | Memory maintenance |
| `.github/agents/python-reviewer.agent.md` | Custom agent | Python code review |
| `.github/agents/kubernetes-reviewer.agent.md` | Custom agent | K8s review |
| `.github/agents/release-auditor.agent.md` | Custom agent | Release readiness |

## Agent Workflow

```
VS Code Copilot agent
    ↓
reads AGENTS.md
    ↓
loads .github/copilot-instructions.md
    ↓
loads matching .instructions.md (via applyTo globs)
    ↓
consults .project-ai/memory/
    ↓
edits files
    ↓
runs narrowest relevant VS Code task
    ↓
runs full quality gate before completion
    ↓
updates .project-ai/memory/ only when justified
    ↓
reports exact commands and results
```

## Memory Layer

`.project-ai/memory/` stores durable evidence summaries:

| File | Purpose |
|------|---------|
| `architecture-decisions.md` | Durable design choices |
| `recurring-bugs.md` | Repeated defect patterns |
| `python-risks.md` | Python gotchas |
| `kubernetes-risks.md` | Deployment risks |
| `dependency-notes.md` | Dependency constraints |
| `release-diary.md` | Release outcomes |
| `diagnostics.md` | Proven diagnostic procedures |

## Python Tool Stack

| Tool | Role |
|------|------|
| `uv` | Python project manager |
| `ruff` | Lint and format |
| `pytest` + `pytest-cov` | Tests and coverage |
| `mypy` | Type safety |
| `bandit` | Security patterns |
| `pip-audit` | Dependency vulnerabilities |
| `pre-commit` | Local quality gate |

## Kubernetes Tool Stack

| Tool | Role |
|------|------|
| `kubectl` | Cluster management |
| `kind` | Local clusters |
| `helm` | Package management |
| `kustomize` | Environment overlays |
| `kubeconform` | Schema validation |
| `kube-linter` | Best-practice linting |
| `trivy` | Vulnerability scanning |

## VS Code Quality Gates

| Task | What It Runs |
|------|-------------|
| Quality: Python fast | Ruff check + format + pytest |
| Quality: Python full | Ruff + mypy + pytest --cov + bandit + pip-audit |
| Kubernetes: Validate | kubeconform |
| Kubernetes: Lint | kube-linter |
| Security: Trivy | trivy fs vuln+secret+misconfig |
| Quality: Full repo | All of the above in sequence |
