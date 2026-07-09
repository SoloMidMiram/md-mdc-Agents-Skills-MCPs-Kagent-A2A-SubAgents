# AI Tooling Guide

This document describes the VS Code-native agent customization files
and how they interact with the broader MCP tooling laboratory.

## File Hierarchy

When a host agent processes a request, it loads guidance from these surfaces (not all hosts support all surfaces):

1. `AGENTS.md` — repo-level agent operating contract (this repo treats AGENTS.md as the shared contract across hosts)
2. `.github/copilot-instructions.md` — repository-wide instructions (VS Code Copilot)
3. `.github/instructions/*.instructions.md` — file-pattern-specific rules (VS Code Copilot)

Other hosts (Cursor, Codex, Continue) have their own loading orders — this section documents the VS Code path specifically.

## Agent Model Matrix

This matrix separates the five agent surfaces available in this repo and explains which hosts use them.

| Surface | Defined In | Scope | Portable? |
|---------|-----------|-------|-----------|
| **Host config** | Per-tool user config files (`mcp.json`, `config.toml`, `config.yaml`) | Each host independently | Yes — copy user-level files |
| **Shared repo rules / instructions** | `AGENTS.md`, `.github/copilot-instructions.md`, `.github/instructions/*` | All hosts that support repo-level guidance | Yes — included in Git |
| **Continue slash-command personas** | `%USERPROFILE%\.continue\config.yaml` under `slashCommands:` | Continue only | Yes — copy `config.yaml` |
| **VS Code custom agents** | `.github/agents/*.agent.md` | VS Code Copilot only | Yes — included in Git |
| **Cursor scope** | `%USERPROFILE%\.cursor\mcp.json` + shared repo rules | Cursor (MCP + repo rules); no repo-defined persona surface | MCP config: yes, copy user file |

**Cursor parity note:** Cursor supports shared repo rules (AGENTS.md is the shared contract) and MCP tools (`mcp.json`), but does not have a native equivalent of Continue slash-command personas or VS Code `.github/agents/*` specialist agent files. Cursor's agent surface is MCP servers + repo-level rules + user-level Cursor rules, not repo-defined persona definitions.

## Customization Files

| File | Scope | Purpose |
|------|-------|---------|
| `AGENTS.md` | All hosts (this repo treats AGENTS.md as the shared contract) | Cross-editor operating contract |
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
