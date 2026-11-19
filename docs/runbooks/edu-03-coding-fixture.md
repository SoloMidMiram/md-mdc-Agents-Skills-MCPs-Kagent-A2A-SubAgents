# EDU-03 offline patch replay

From a fresh checkout with Python 3.12 or newer:

```powershell
python -m scripts.kagent.experiments.edu03_lab
python -m scripts.kagent.experiments.edu03_lab --case misleading
python -m pytest -q tests/kagent/experiments/test_edu03_lab.py
```

The fixture grants a 10% discount at ten units or more to members. Both
patches pass the visible ten-unit member check. The correct patch preserves
membership eligibility. The misleading patch fails the trusted nonmember
cases at ten and eleven and receives an E2-R rejection after one revision.
An expected rejection is a successful replay. Worker failure, deadline
exhaustion, or invalid evidence fails the CLI.

The controller freezes the patch before invoking the deterministic worker.
It checks the original file bytes, patch size, allowlisted path, matching hunk
context, and frozen digest. It removes the worker root before creating the
separate evaluator root. Only the verified patched source crosses that boundary.
A digest binds observed test results to the reviewer evidence. E3 verifies the
supplied worker input bundle. E2-R checks planner/reviewer artifacts, while
patch production and evaluation run outside the coordinator. The evaluator
executes only the known synthetic module. Disposable roots establish fixture
custody. The harness makes no adversarial isolation or native teardown claim.

## Fresh-checkout learner exercise

1. Run the default command twice and compare the JSON. The misleading case
   still passes the visible check at 900 cents. Its held-out nonmember
   observations are 900 and 990 cents. The expected values are 1000 and 1100.
2. Compare patch SHA-256, changed path, and evaluator evidence SHA-256 between
   cases. The same visible result accompanies different reviewer decisions.
3. Run the test command with `-k "fabricated or worker_inventory or untrusted_patch"`
   for fail-closed evidence and scope checks. The full test file also exercises
   deadlines, caller cancellation, and fixture worker failure.

Reports declare `origin: synthetic`, `capabilityPromotion: false`, and a null
model. Temporary paths and timings are excluded for deterministic replay.
The frozen evaluation contracts and evidence schemas remain unchanged.
