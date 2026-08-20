# Educational Projects Map

This is the entry point for the repository's two educational subprojects. They
share learning and evidence conventions but remain isolated from each other and
from the stable agentic-coding core.

## Choose a Lane

| Lane | Learn | Start | Status/evidence |
|------|-------|-------|-----------------|
| Playwright MCP | MCP host/runtime separation, browser inspection, safe interaction, local versus remote browser execution | `docs/runbooks/local-playwright-lab.md` | `evidence/local/` and `evidence/global/global-validation-matrix.md` |
| kagent | Kubernetes control plane, agent reconciliation, A2A dispatch, MCP discovery, agentic tool evidence | `docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md` | `evidence/kagent/README.md` |

Architecture and problem handling shared by both lanes:

- `docs/north-star.md` — A2A-first project direction (2026-08-07)
- `docs/architecture/EDUCATIONAL-LANES-ARCHITECTURE.md`
- `docs/runbooks/educational-problem-manual.md`
- `docs/templates/educational-problem-record.md`

Agent customization shared by the repository:

- `docs/onboarding/AGENT-GOVERNANCE-ROADMAP.md` — phased evaluation and
  promotion of rules, skills, hooks, and related CI enforcement

## Before Continuing an Example

You do not need a complete rules review before every exercise. Confirm this
small contract:

- objective and expected observation are explicit;
- environment and versions are known;
- allowed side effects are local and bounded;
- pass, fail, and non-claim are written;
- evidence and cleanup destinations are known;
- the example does not modify a stable interface.

Review the full architecture only when the example adds a dependency, changes a
stable script/configuration, crosses educational lanes, broadens permissions, or
changes a release/security boundary.

## When a Problem Appears

1. Preserve the error and contain side effects.
2. Copy the problem-record template into the applicable evidence lane.
3. Classify and reproduce the problem minimally.
4. Fix it in the educational lane when possible.
5. Add a regression test if code behavior changed.
6. Promote the lesson to a runbook, repository rule, or architecture decision
   only when the manual's criteria are met.
7. Update the lane roadmap and canonical status only with proven outcomes.

## Protection Boundary

Educational work may consume stable host registration, validation helpers, and
templates. Stable agentic coding must not depend on live educational state.
Before a lab-specific helper moves into stable code, it must pass the promotion
gate defined in the educational-lanes architecture.
