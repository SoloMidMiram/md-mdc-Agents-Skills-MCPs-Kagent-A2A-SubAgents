# From roadmap to practical agent labs

Proposed learning plan, prepared 2026-10-25. Each issue teaches one capability,
produces something runnable, and leaves a reusable component. Each lab must pass
independently before becoming part of a larger workflow.

This plan complements the [existing roadmap](IMPLEMENTED-STATE-AND-ROADMAP.md)
and [planning-ID crosswalk](../reference/integration-workstreams.md). The
[capability matrix](../reference/kagent-capability-matrix.md) defines proof;
the [evidence index](../../evidence/kagent/README.md) records dated decisions.
This document does not promote any capability or resolve any PR.

## Organize work by purpose

| Type | Purpose | Example |
|---|---|---|
| Engineering issue | Deliver a reusable capability | CTX-01 context packet builder |
| Learning lab | Understand a concept through execution | LAB-01 L4 versus L6 investigation |
| Acceptance gate | Prove a specific capability under stated conditions | A2A-01 live official-SDK interoperability |

Every engineering issue must link to at least one lab. Every lab must identify
its capability, prerequisites, executable steps, expected artifact, pass rule,
and explicit limits. Acceptance gates may be checklists within an issue rather
than duplicate issues. A planning ID is not a GitHub issue number.

## Proposed backlog

| Order | ID and proposed title | Deliverable and acceptance | Lab | Priority |
|---|---|---|---|---|
| 0 | RECON-01: Qualify and reconcile PR #9 | Pin main and PR heads, reconcile included work, run required checks at the candidate SHA, and record each PR disposition and remaining approvals | LAB-01 | P0 |
| 1 | CTX-01: Build source-grounded context packets | Offline builder emits task, repository revision, source paths/line spans, evidence excerpts, claims, unknowns, and scope; rejects missing or stale source references | LAB-01 | P0 |
| 2 | CTX-02: Add Context7 documentation retrieval | Child of CTX-01; retain library identity, requested/resolved version, source, retrieval time, and excerpts; fail explicitly when documentation cannot be verified | LAB-02 | P0 |
| 3 | EVAL-01: Compare manual context against generated context | Replayable A/B task with fixed starting revision, model/settings, tool permissions, budget and acceptance tests; retain patches, outcomes, cost/time and failures | LAB-03 | P0 |
| 4 | A2A-01: Validate official SDK against live Kagent | Reuse existing SDK candidate; capture bounded dispatch, task identity, response/terminal state, versions and trace using the official SDK against a live approved target | LAB-04 | P0 |
| 5 | EDU-01: Execute planner/reviewer learning examples | Replay existing E1/E2 implementations with recorded inputs, outputs, task identities and assertions | LAB-04 | P1 |
| 6 | SAFE-01: Expose native read-only MCP tools | Validate exact tool schemas, allowed targets and inventory; demonstrate permitted calls and rejected disallowed calls, backed by server permissions | LAB-02, LAB-05 | P1 |
| 7 | WORKER-01: Add a bounded coding worker | Planner → worker → reviewer on an isolated task; bounded tools, patch/test artifacts, stop conditions and human approval before applying changes outside the sandbox | LAB-05 | P1 |
| 8 | OPS-01: Repeatable setup and cleanup | A new learner completes setup, target lab, restart and ownership-aware cleanup with dated evidence | LAB-05 replay | P2 |

The reported seven open PRs (#3–#9), no open non-PR issues, and draft PR #9
with successful offline CI are inputs from the proposal, not freshly verified
GitHub state. RECON-01 must refresh them before publishing issues or declaring
an integrated baseline. Offline CI does not establish live interoperability.

Reconcile these boundaries with the existing crosswalk before creating issues:

- CTX-01 becomes the offline core; CTX-02 supplies its optional external docs.
- Reuse PR #9's contents only after checking its exact head and file inventory.
  Existing EDU-01 and A2A-01 code/evidence should be qualified, not reimplemented.
- Preserve the existing EVID-01 recorder-integrity prerequisite before accepting
  new experiment evidence; it is not erased by this shorter backlog.
- SAFE-01 precedes tool-enabled LAB-02/LAB-05 runs. Initial LAB-02 may use only
  the approved Context7 surface while native Kagent exposure is qualified later.
- This order prioritizes context experiments; it is a proposed sequencing change
  to the educational roadmap, not an implicit replacement of existing decisions.

## Progress through independent experiments

| Lab | Experiment and retained artifact | What passing proves | What it does not prove |
|---|---|---|---|
| [LAB-01](../runbooks/lab-01-l4-versus-l6.md) | Offline evidence investigation; cited answer and helper-test output | Agent distinguishes recorded dispatch from missing same-task MCP evidence | Fresh L4/L6 runtime operation |
| LAB-02 | Retrieve pinned library docs through Context7; retain actual model-initiated MCP request/response and provenance | Documentation retrieval through the observed MCP surface | Native Kagent exposure, A2A delegation or L6 |
| LAB-03 | Same small coding task with manual/generated context; retain isolated patches and evaluation records | Measured difference for the tested task/configuration | General improvement across tasks or models |
| LAB-04 | Official-SDK bounded task, then existing planner/reviewer E1/E2; retain per-task identities and orchestration joins | Observed SDK interoperability and the exercised orchestration | MCP tool execution unless separately traced on the same task |
| LAB-05 | Compose qualified context, delegation and read-only tools around a bounded worker; retain reviewed patch and tests | The specific integrated workflow under its tested permissions | L6, I4 or L7 without their independent evidence gates |

LAB-02 through LAB-05 are specifications, not ready-to-run lab claims. Their
engineering issues must supply commands, fixtures and acceptance artifacts before
learners advance. Start now with LAB-01; use its manually assembled sources as
CTX-01's first fixture. Keep L6/I4 promotion as explicit gates rather than
expanding the first context-builder implementation to include live orchestration.

For LAB-03, predeclare scoring and record failed runs. Keep hidden acceptance
tests out of both agent inputs; both arms may receive source evidence but neither receives the expected patch. Repeat paired runs before generalizing;
record context preparation cost separately and in the total cost.

## Issue body contract

Each issue should include:

1. Type, stable ID, parent/dependencies, linked lab and reused code/PR inventory.
2. Learning objective and concrete real-world use.
3. Exact starting revision, environment and allowed operations.
4. Runnable deliverable and retained evidence paths.
5. Observable acceptance criteria, negative cases and non-claims.
6. Cleanup, ownership, stop conditions and any external approval gate.

Completion requires the deliverable and linked lab to pass. A blocked live gate
must remain blocked even when its offline implementation and tests are complete.

## First retained execution

[LAB-01 result, 2026-10-25](../../evidence/labs/lab-01/2026-10-25/README.md)
records the explicitly fetched baseline, complete agent responses, a fresh
success-only direct-MCP negative control, and independent evaluation. The
expansion is LAB-01 manual investigation → CTX-01 automatic assembly of that
same evidence → EVAL-01 manual versus generated context. Only RECON-01 and
CTX-01 are to become issues at this milestone; the other entries stay proposed.
