# Educational Problem Manual

Use this manual when a Playwright or kagent educational implementation behaves
differently from its plan. The goal is to learn from the failure while keeping
the stable agentic-coding path trustworthy.

Start from `docs/templates/educational-problem-record.md`. Create the record in
the applicable evidence directory; do not immediately add a global rule.

## 1. Contain

1. Stop if the next action could affect production, external users, credentials,
   paid resources, or data outside the declared lab scope.
2. Preserve the exact error, exit code, request/response, and time.
3. Avoid broad cleanup. Record relevant processes, ports, pods, and modified
   files before changing them.
4. Confirm which zone failed: stable core, Playwright education, kagent
   education, or an external dependency.

## 2. Classify

| Class | Examples | First response |
|-------|----------|----------------|
| Environment | Missing binary, port conflict, DNS, Docker not running | Record versions and prerequisites; do not change product logic |
| Configuration | Wrong URL, schema, namespace, model, or host config | Compare with executable config and manifest authority |
| Product defect | Valid request causes internal error or incorrect exit code | Minimize reproduction and add regression coverage |
| Version incompatibility | Registered method or flag differs by version | Pin both sides and build a compatibility matrix |
| Permission/security | RBAC denial, secret access, unsafe browser state | Preserve the denial; do not broaden permissions casually |
| Documentation drift | Command, status, or claim differs from reality | Correct the canonical owner and replace copies with links |
| Expected educational failure | Deliberate missing element, timeout, unsupported gate | Record as expected and verify the lesson is clear |

## 3. Reproduce Minimally

- Remove unrelated steps while preserving the failure.
- Use a disposable browser profile, namespace, fixture, or temporary resource.
- Record expected versus actual behavior.
- Repeat once when safe. Do not call an intermittent result solved.
- Separate endpoint availability, protocol acceptance, work completion, and
  end-to-end capability; they are different gates.

## 4. Diagnose by Layer

### Playwright lane

Check in order:

1. host registration and pinned package version;
2. MCP process startup;
3. browser launch/profile isolation;
4. page navigation and network boundary;
5. accessibility snapshot or locator quality;
6. interaction side effect;
7. cleanup and browser closure.

### kagent lane

Check in order:

1. Kubernetes context and namespace;
2. pod and service readiness;
3. custom-resource reconciliation;
4. agent acceptance and deployment readiness;
5. card/details retrieval;
6. A2A protocol dispatch;
7. RemoteMCPServer acceptance;
8. actual agent-mediated tool result.

Never skip a failed lower layer by using higher-layer evidence.

## 5. Decide the Response

| Result | Action |
|--------|--------|
| One-off learner/environment issue | Keep the evidence record; improve prerequisites if unclear |
| Expected failure teaches the intended concept | Add it to the exercise's likely-failures section |
| Repeated problem with proven recovery | Add a diagnostic entry to the relevant runbook |
| Code or script defect | Fix it and add a regression test before closing the record |
| Durable architectural boundary | Add an architecture decision and update the architecture document |
| Stable-core change needed | Use the promotion gate; run stable release validation unchanged |
| External/version blocker | Pin the failing combination, document alternatives, keep capability `Not proven` |

## 6. Validate the Fix

A fix is complete only when:

- the minimal reproduction now behaves as expected;
- a negative case still fails truthfully;
- relevant stable tests remain green;
- security or Kubernetes policies were not weakened;
- cleanup succeeds;
- evidence names the exact capability proved and explicit non-claims;
- documentation is updated at its canonical owner.

## 7. Reflect and Promote Knowledge

Close every problem record with:

- root cause and contributing conditions;
- why earlier checks did not catch it;
- the smallest effective fix;
- regression or validation added;
- learner takeaway;
- whether knowledge stays evidence-only, enters a runbook, becomes a rule, or
  requires an architecture decision.

Use the repository memory only when the problem repeated, the diagnostic was
proven, or the decision is durable. This prevents temporary lab behavior from
polluting agentic-coding instructions.

## Suggested Record Locations

- Playwright exercises: `evidence/local/problems/YYYY-MM-DD-<slug>.md`
- kagent: `evidence/kagent/problems/YYYY-MM-DD-<slug>.md`
- Cross-lane experiments: `evidence/integrations/problems/YYYY-MM-DD-<slug>.md`

Create directories only when the first record exists. Do not create empty
taxonomy folders.
