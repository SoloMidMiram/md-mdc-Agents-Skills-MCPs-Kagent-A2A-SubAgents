# Implement the Next Educational Reliability Stage

This is a portable implementation request. In Cursor Agent, explicitly attach
or reference this file (for example, ask Cursor to implement
`@.github/prompts/implement-next-educational-stage.prompt.md`). It is not an
auto-loaded Cursor persona or rule.

Implement the next local, non-production stage for the Playwright and kagent
educational lanes while preserving the stable agentic-coding core.

Read first:

1. `AGENTS.md`
2. `constraints.md`
3. `docs/onboarding/EDUCATIONAL-PROJECTS.md`
4. `docs/architecture/EDUCATIONAL-LANES-ARCHITECTURE.md`
5. `docs/runbooks/educational-problem-manual.md`
6. `evidence/kagent/README.md`
7. `docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md`

## Objective

Close the local P1 reliability gaps that can be implemented and tested without
upgrading the live kagent controller or claiming L4/L6:

1. add named `CardLab`, `A2ADispatch`, and `FullMcpExecution` profiles to
   `scripts/kagent/check-kagent-health.ps1`;
2. add committed regression tests for the A2A helper's card, probe, task, error,
   transport, and exit-code semantics;
3. make Kubernetes manifest validation distinguish “validators unavailable”
   from a real pass, with an explicit strict/CI mode that fails when required
   validators are missing;
4. add a reusable direct MCP smoke helper that performs `initialize`, captures
   the `Mcp-Session-Id`, and calls `k8s_get_resources` with the session reused;
5. record any encountered problem using
   `docs/templates/educational-problem-record.md`.

## Boundaries

- Do not install, upgrade, or mutate the live kagent controller or Helm release.
- Do not touch production or cloud resources.
- Do not weaken RBAC, security checks, tests, or stable installer guarantees.
- Do not make stable tests depend on a browser, website, Docker Desktop, live
  cluster, secret, or learner evidence.
- Keep live-cluster checks opt-in and separate from deterministic unit tests.
- Direct MCP success is server evidence only; never mark L4 or L6 proven.
- Preserve the current truthful behavior: `task` and `both` fail when dispatch
  fails, while `probe` reports support without claiming dispatch success.

## Required Design

### Health profiles

- Default to the current backward-compatible card-lab behavior.
- `CardLab`: require healthy pods and accepted/ready agents; report degraded
  unrelated RemoteMCPServers without failing.
- `A2ADispatch`: include the CardLab checks and require a successful dispatch
  evidence check, not merely method registration.
- `FullMcpExecution`: require the target `kagent-tool-server` accepted plus an
  explicit agent-mediated tool evidence input; do not infer L6 from acceptance.
- Separate parsing/decision logic from `kubectl` execution enough to test it
  without a live cluster.

### Tests

- Prefer deterministic tests with fixtures/mocks.
- Test `Accepted=False`, `DeploymentReady=False`, missing fields, `-32601`,
  `-32603`, HTTP errors, transport exceptions, and valid success responses.
- Test pod readiness ratios including `1/1`, `2/2`, `1/2`, `0/1`, and malformed
  values.
- Assert exit codes, not only printed text.

### MCP smoke helper

- Make namespace, service URL, resource type, and timeout configurable.
- Print sanitized request stage, HTTP status, and concise result.
- Exit non-zero for missing session ID, HTTP/protocol error, or failed tool call.
- Clean up any temporary Kubernetes resource it creates.

## Documentation and Evidence

- Update the runbook only for commands that are actually implemented.
- Update `evidence/kagent/README.md` with implementation status, but do not claim
  a live capability unless a dated live run proves it.
- If no live cluster run occurs, label the work “implemented, live validation
  pending.”
- Add new canonical artifacts to `REPO_MANIFEST.yaml`.

## Validation

Run and report the commands actually available in the environment:

```powershell
git diff --check
python -m ruff check .
python -m compileall scripts
pytest -q
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\evaluation\run-evaluation.ps1 -CI
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\kubernetes\validate.ps1 -Strict
```

If a prerequisite such as Pester, kubeconform, or kube-linter is missing, report
that as a distinct environment blocker. Do not present the skipped validation as
a pass and do not install dependencies without authorization.

## Deliverable

Return:

- files changed and why;
- tests and exact exit codes;
- profiles and their gate semantics;
- direct MCP smoke status;
- capabilities proven versus still unproven;
- problem records created;
- remaining P0/P1/P2 gaps.
