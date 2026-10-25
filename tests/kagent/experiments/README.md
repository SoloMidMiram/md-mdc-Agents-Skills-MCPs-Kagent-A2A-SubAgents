# kagent A2A Experiment Tests

Deterministic tests for `scripts/kagent/experiments/` (contract validation and
evidence record shaping). Live cluster smokes use `run_a2a_example.py` locally
and are not required in CI.

EVID-01 regressions cover invalid evidence types, task/request mismatch, terminal
completion, full supervisor contracts, redaction, registered example identifiers,
and collision-safe output. They use only fake transports and temporary files.
