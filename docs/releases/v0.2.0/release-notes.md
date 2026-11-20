# v0.2.0 · Deterministic A2A patch replay

Draft for maintainer review.

The offline A2A practice goal is complete. This follow-up adds a deterministic
worker process that returns a fixed patch artifact over loopback HTTP/SSE using
A2A SDK 0.3.26. The harness records request, message, task, and artifact identity,
checks the artifact schema, and verifies worker process-group teardown.

The [runbook](../../runbooks/phase-2a-stub.md) covers a valid response, a
malformed artifact, and a backend blocked before dispatch. All replay evidence
is synthetic and non-qualified. The [replay transcript](replay-transcript.txt)
records the four command outcomes. Live invocation, qualified isolation, patch
correctness, and EVAL-01 scoring require separate evidence and decisions.

The deferred work in #20–#25 and optional research in #40–#45 are outside the
offline practice release. See the
[retrospective](../../onboarding/A2A-PRACTICE-RETROSPECTIVE.md) for the lessons
from the practice labs.
