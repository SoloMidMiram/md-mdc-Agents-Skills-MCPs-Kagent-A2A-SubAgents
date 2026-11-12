# Integration workstreams

This file owns the planning-ID crosswalk. North Star owns direction; the
educational roadmap owns sequencing; the evidence index owns capability decisions.
The rehearsed source is published in draft PR #9. Its October 25 exact-head
CI is recorded on GitHub; current security and maintainer approval remain
separate gates. See the dependency-security runbook for remediation lanes.

| Hosted PR | Head verified 2026-10-22 | Scope |
|---|---|---|
| #3 | `543f83d1787df36b3b289ea74db37fc120134421` | Federation foundation |
| #4 | `691ebaa2f4a8bdf6530d69965c4b6b766bbcbf23` | Gateway, including educational ancestry |
| #5 | `78a24e68f529d4fa4d175592f842ec4cdd9aab00` | Tool-loop evidence |
| #6 | `2e86bdeadb967c97ee34ba136ecd2ae3eb39d6c8` | A2A/client documentation |
| #7 | `eb392914e5f0facf6e292cbe5040762a6a7e82ba` | Cloud-only policy |
| #8 | `f3c3f8f3c1f11e4dda44d85074bb437b13b84303` | Intended schema ownership |

Verified main is `3c99181d187262d6464bfbcd257852485eb712f1`. PR #3 descends
from main; educational `3c08952` descends from #3; #4 contains both. PRs #5–#8
are siblings containing #4. Their hosted base settings and CI are not inferred
from ancestry. Local rehearsal order: #3, #4, #7, educational retarget `1d283b0`,
#8, #5, #6. Manifest conflicts retain both entries; roadmap/index conflicts
retain both evidence slices. No dated evidence is rewritten.

| Stable ID | Historical proposed number | Current boundary |
|---|---|---|
| RECON-01 | none | Integration and authoritative planning truth |
| EVID-01 | none | Recorder and harness integrity |
| A2A-01 | none | Isolated SDK 0.3.26 compatibility; live validation separate |
| EDU-01 | North Star #4 | E1/E2 code included through hosted #4. The [follow-on examples](../runbooks/kagent-a2a-examples.md) add E2-R, E3, and offline labs. |
| SAFE-01 | North Star #5; older roadmap #4 | Exact read-only MCP exposure |
| CTX-01 | none | Proposed cited Context7 context builder |
| EVAL-01 | North Star #6 | Proposed repeatable comparisons |
| WORKER-01 | North Star #7 | Proposed bounded local coding worker |
| INTEROP-01 | North Star #8 | Cursor client/worker investigation; I3 independent |
| CAPSTONE-01 | North Star #9 | Deferred E5 integration |
| L6 evidence gate | older roadmap #5 | Separate correlated agent tool proof |
| I4 evidence gate | older roadmap #6 | Same-invocation IDE join after I3 and L6 |
| OPS-01 | older roadmap #7 | Workshop lifecycle; I5/L7 require live acceptance |

RECON-01 precedes EVID-01, then A2A-01. CTX-01 and tools/worker work are
outside this implementation. SAFE-01 is required before tool-enabled workflows.
EVAL-01 measures comparable runs; OPS-01 supplies ownership and fresh replay.

Active examples use `litellm-gateway-model-config`, alias `agent-coder`, and the
cloud-only policy in [LOCAL_MODELS_FROZEN](../LOCAL_MODELS_FROZEN.md). Historical
Ollama/direct-provider evidence is retained; those instructions do not authorize
active execution. Cloud failure is Blocked, never local fallback.

The dirty SDK checkout stays isolated at `d086408`; its SDK files and ignored
evidence are preserved outside this worktree. No SDK dependency enters the
normal environment. Deterministic success cannot promote L6, I3, I4, or L7.

## Security reconciliation (2026-11)

Root security is corrected independently from main in
`fix/main-dependency-security-202611`. The isolated SDK correction
`fix/a2a-sdk-dependency-security-202611` targets #9's integration branch.
SDK 0.3.26 is retained; only pyasn1 changes to 0.6.5 and the exact lock gains
enforced artifact hashes. New security evidence does not replace the historical
runtime evidence or promote L6, I3, I4, L7, or live SDK interoperability.

The main-lane contradiction register owns traceable corrections. This branch
adds no duplicate roadmap or register. #10's records remain unchanged; #13 must
be replayed and still needs its separately tracked correctness fixes. Do not
close or retarget #3–#8 or merge the containing history without a maintainer
integration decision under #11. See [dependency security](../runbooks/dependency-security.md).

The single [contradiction register](contradiction-register.md) is now included
in RECON-02 through main's reviewed history. The separate original
[SDK qualification record](../../reports/security/sdk-20261101.json) remains a
dated SDK-only observation, including its inherited root blocker. The
[combined qualification](../../reports/reconciliation/recon-02-20261103.json)
records this candidate's checks. RECON-02 preserves #14/#15 as ancestors and
leaves maintainer acceptance of their original targets to issue #11. #10 and
#13 remain separate descendants requiring replay/requalification; no CTX code
or retained LAB-01 answer is imported or rewritten.
