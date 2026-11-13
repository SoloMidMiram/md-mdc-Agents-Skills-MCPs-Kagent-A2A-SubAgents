# Agent operating contract

## Sources of truth

1. Repository code and tests
2. `pyproject.toml`
3. Deployment manifests
4. Architecture decisions under `.project-ai/memory/architecture-decisions.md`
5. `.project-ai/memory/`

Memory documents are evidence summaries, not authority over current code.

## Required behavior

- Inspect before editing.
- Prefer the smallest coherent change.
- Do not weaken tests, security checks, or Kubernetes policies to obtain a pass.
- Separate observed facts from assumptions.
- Report commands actually executed.
- Stop when a requested operation may affect production resources.

## Memory updates

Write to `.project-ai/memory/` only when:

- a problem occurred more than once;
- a durable architectural decision was made;
- a diagnostic procedure was proven;
- a Kubernetes or security risk is reusable across future tasks.

## Source integration

Follow the [solo-maintainer review policy](docs/MAINTAINER_REVIEW_POLICY.md).
Collect technical review and applicable verification for the integration
candidate, then present a recommendation to SoloMidMiram. The owner records
acceptance and authorizes the source merge. Check the policy for separate
operational authorization and qualification requirements.
