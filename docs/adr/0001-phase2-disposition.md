# ADR 0001 · Phase 2 disposition after offline v0.1.0

**Decision for maintainer acceptance in REL-01 #50.** Sequence Phase 2A before
Phase 2B. This decision takes effect when SoloMidMiram approves the acceptance
PR and records the reconciliation in [#50](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/issues/50).
Implementation starts after the v0.1.0 tag. This ADR grants no run authorization.

## Phase 2A · Artifact-only A2A demonstration

Use the existing A2A protocol for a real delegation to a local worker process.
The worker returns a model-produced patch for static validation in a disposable,
unqualified workspace. Generated code and generated tests are never executed in
Phase 2A. Carry this wording into the worker runbook.

Enforce the Phase 2A contract before a run.

- Use only approved public or synthetic task material as inputs.
- Prevent model access to unrelated repositories, host files and credentials.
  Keep model authentication outside the model-accessible workspace.
- Prohibit model-controlled shell commands and arbitrary tool execution.
- Treat returned patches as untrusted data. The controller, worker and evaluator
  must never execute generated code or generated tests.
- Verify teardown of the full worker process tree.
- Record `BLOCKED` if the backend cannot enforce these restrictions.

Before a run, record the named maintainer's explicit approval, named cloud
provider, cloud-only `agent-coder` model alias and concrete spend cap per run
in the issue. Record `BLOCKED` if authorization is incomplete or the cloud
backend is unavailable. Local-model fallback is prohibited.

Acceptance requires intact task and artifact correlation, a schema-valid patch
artifact for a completed demonstration, a terminal `ACCEPT`, `REJECT` or
`BLOCKED` record, verified worker process-tree teardown and a runbook that
labels the evidence non-qualified. A blocked attempt records the absent
evidence and does not establish successful delegation. The gate measures
protocol behavior.
Patch correctness and EVAL-01 scoring are outside its scope.

## Phase 2B · Qualified execution

Executing generated code or its tests requires independently qualified
isolation under [#20](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/issues/20)
and separate operational authorization. The Phase 2A evidence cannot satisfy
that gate or count toward [#21](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/issues/21).
