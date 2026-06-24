# Repository engineering rules

Before modifying code:

1. Read `AGENTS.md`.
2. Read relevant files under `.project-ai/memory/`.
3. Inspect existing tests and configuration.
4. Do not introduce a new dependency when the standard library or an existing
   dependency already solves the problem.

After modifying Python:

- run Ruff;
- run mypy on affected modules;
- run relevant pytest tests;
- run Bandit when security-sensitive code changes;
- update `.project-ai/memory/recurring-bugs.md` only for a demonstrated recurring
  pattern.

After modifying Kubernetes files:

- validate rendered manifests;
- run kubeconform;
- run kube-linter;
- confirm resource requests and limits;
- confirm readiness and liveness probes where applicable;
- update `.project-ai/memory/kubernetes-risks.md` only when a reusable lesson
  was discovered.

Never claim a command passed unless its output was observed.
Do not create memory entries for ordinary one-time fixes.
