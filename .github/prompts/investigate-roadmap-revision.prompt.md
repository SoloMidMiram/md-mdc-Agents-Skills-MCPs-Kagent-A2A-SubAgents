# Investigate Roadmap Alignment (Proposal Only)

Attach or reference this prompt in Cursor Agent (for example,
`@.github/prompts/investigate-roadmap-revision.prompt.md`). It is an
investigation and planning request only. Do **not** implement the proposal.

## Objective

Produce a decision-ready proposal that aligns the repository's stable-release
and kagent work into one dependency-ordered execution plan. The proposal must:

- preserve the canonical stable-first delivery sequence;
- keep kagent capability priorities distinct from portfolio/release priorities;
- follow A2A-first direction in `docs/north-star.md` — Lane A education is the
  default kagent priority after PR #3; Cursor I3 is Lane C interoperability
  proof, not the education spine;
- allow Lane A (A2A role examples), Lane S (read-only MCP), and Lane C (client
  interop) to proceed in parallel where dependencies allow;
- treat I3, L6, and I4 as strict, separate capability experiments that do not
  block Lane A education; and
- define how each completed or disputed prior phase is reviewed without
  retroactively rewriting evidence.

## Non-Negotiable Boundaries

- Do not edit files, create files, stage changes, commit, push, tag, or open a
  pull request.
- Do not install dependencies, modify local configuration, or invoke live
  cluster, browser, IDE, GitHub, cloud, or production operations.
- Do not promote, demote, or reinterpret a capability claim. Report only what
  the existing canonical evidence supports.
- Do not create a second roadmap, status ledger, or branch-local planning
  document. Propose changes to existing canonical owners only.
- Do not propose a custom Cursor/Codex-to-A2A bridge.
- Do not weaken tests, RBAC, security policy, Kubernetes validation, or stable
  installer acceptance requirements.

## Read-Only Sources To Inspect

Read these in order before forming recommendations:

1. `AGENTS.md`
2. `constraints.md`
3. `docs/north-star.md`
4. `docs/DOCUMENTATION-ORGANIZATION.md`
5. `docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md`
6. `docs/laptop-stable-acceptance-plan.md`
7. `docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md`
8. `evidence/kagent/README.md`
9. `docs/reference/kagent-capability-matrix.md`
10. `docs/architecture/EDUCATIONAL-LANES-ARCHITECTURE.md`
11. `.project-ai/memory/architecture-decisions.md`
12. `REPO_MANIFEST.yaml`
13. `pyproject.toml`, `uv.lock`, and `.github/workflows/quality.yml`

Use repository code, tests, manifests, and executable configuration as higher
authority than summaries. Separate observed facts from assumptions and cite the
source path for every material conclusion.

## Investigation Tasks

1. Map ownership: identify the one canonical owner for repository sequencing,
   stable release acceptance, kagent phase order, capability status, live
   evidence, and operational commands.
2. Reconcile sequencing: identify conflicts, stale wording, duplicated backlog
   entries, or phase-order ambiguity across the current sources.
3. Review prior phases: for every completed, blocked, or not-proven predecessor
   relevant to the next step, state its recorded outcome, its explicit
   non-claims, and whether the next phase's prerequisites are actually met.
4. Identify validation gaps: distinguish deterministic checks, exact-SHA hosted
   CI, target-host acceptance, and live IDE/cluster evidence. A successful
   prerequisite must never substitute for an end-to-end proof.
5. Propose only the smallest coherent documentation changes needed to make the
   roadmap unambiguous. Do not draft or apply full replacement documents unless
   a narrow excerpt is necessary to demonstrate the recommendation.

## Required Proposed Execution Order

Use this as the starting structure; refine only where the inspected sources
require it:

| Gate | Proposed outcome | Minimum validation | Explicit non-claim |
|------|------------------|--------------------|--------------------|
| 0 | Current-head baseline: explicit PyYAML contract, correct coverage scope, immutable candidate SHA, and exact-SHA Quality | frozen dependency environment, applicable deterministic checks, required hosted `quality.yml` jobs | not a release tag |
| 1 | Stable Playwright patch release | Windows install → verify → rollback → verify on the candidate SHA, plus exact-SHA CI | not kagent readiness or capability evidence |
| 2 | PR #3 federation foundation | I0–I2 proven; I3 Blocked recorded accurately; final SHA passes `quality.yml` | **Do not mark I3 Proven** on merge |
| 3a | Lane A — A2A role examples (PR #5) | E1–E2 runnable; manifests under `deploy/samples/kagent-a2a/` | not MCP tools, I3, I4, or L6 |
| 3b | Lane S — read-only MCP surface (PR #4) | default-deny discovery; only `k8s_get_resources`; restrictive RBAC | not I3, I4, L6, or A2A education |
| 3c | Lane C — Cursor I3 interop (deferred) | exact approved inventory, bounded IDE `invoke_agent`, second-call `context_id` | not education gate; not L6 or I4 |
| 4 | Strict L6 / I4 experiments (deferred) | L6: direct A2A tool proof; I4: same-invocation IDE join — separate tracks | not repeatability or write authority |
| 5 | I5/L7 workshop repeatability | fresh Docker Desktop run, restart check, supported-client acceptance, cleanup verification | not production readiness or write-enabled operation |

Lanes 3a, 3b, and 3c may proceed in parallel after Gate 2 where dependencies
allow. L6 and I4 (Gate 4) do not block Lane A education.

## Iterative Review and Revision Protocol

For each proposed gate, define this review loop:

1. **Entry review:** re-read the preceding phase's evidence and non-claims;
   confirm each dependency against its canonical owner.
2. **Execution review:** list the deterministic and live validations required,
   their expected evidence, and the authority that may accept them.
3. **Exit review:** compare the observed outcome with the gate's promotion
   criteria; identify which claims remain blocked or not proven.
4. **Revision decision:** if evidence exposes a faulty assumption, propose a
   narrow roadmap/runbook/test correction. Preserve the original evidence;
   later authorized work must append a dated addendum or new record instead of
   rewriting history.
5. **Next-gate review:** verify that the next gate's dependencies still hold;
   otherwise return to the smallest predecessor correction rather than skipping
   a gate.

## Deliverable Format

Return a proposal only, using these sections:

1. **Recommendation** — whether to update the canonical roadmap owners; state
   explicitly that no branch subroadmap is recommended.
2. **Observed facts and conflicts** — a table with source path, fact, and
   planning consequence.
3. **Proposed phased plan** — expand the required execution-order table with
   dependencies, acceptance evidence, validation commands to run later, and
   explicit non-claims.
4. **Prior-phase review matrix** — predecessor, recorded status, evidence
   owner, unmet condition, and permitted next action.
5. **Iterative review protocol** — apply the five-step loop to every gate.
6. **Proposed canonical edits** — list the existing documents, sections, and
   smallest intended changes; do not make those edits.
7. **Risks and decisions needed** — separate user decisions, environment
   blockers, and unproven hypotheses.
8. **Investigation record** — sources inspected, read-only commands run, and a
   final statement: `No files or external state were changed.`
