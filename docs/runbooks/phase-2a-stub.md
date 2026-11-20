# Phase 2A deterministic patch replay

This runbook implements the stub scope approved in #53 and tracked in #54.
It uses the repository's pinned A2A SDK 0.3.26 over HTTP/SSE on an ephemeral
IPv4 loopback endpoint. Run it on Linux, including WSL, with Python 3.13.15.
The harness uses a dedicated Linux process group and verifies its removal.

## Setup and replay

Dependency setup can download the pinned interpreter and wheels. Replay itself
uses only loopback and runs with the existing offline package set.

```bash
uv venv --python 3.13.15 .venv/a2a-sdk
uv pip sync --require-hashes --python .venv/a2a-sdk/bin/python \
  scripts/kagent/experiments/a2a_sdk_requirements.lock
.venv/a2a-sdk/bin/python scripts/kagent/experiments/phase2a_stub.py valid
.venv/a2a-sdk/bin/python scripts/kagent/experiments/phase2a_stub.py malformed
.venv/a2a-sdk/bin/python scripts/kagent/experiments/phase2a_stub.py unsupported
.venv/a2a-sdk/bin/python -m pytest -q tests/kagent/experiments/test_a2a_sdk_phase2a.py
```

| Scenario | Terminal status | Exit code |
| --- | --- | --- |
| `valid` | `ACCEPT` after correlated completion, static artifact validation, and teardown | 0 |
| `malformed` | `REJECT` after correlated completion and teardown | 1 |
| `unsupported` | `BLOCKED` before worker startup or dispatch | 2 |

Each command emits one JSON record. Retain the request, message, task, and
artifact IDs and the process group teardown evidence with the run. A missing
worker, unsupported host, or unverifiable teardown produces `BLOCKED`.

## Evidence scope

All records are labeled synthetic and non-qualified. The worker handles one
fixed synthetic request from a disposable directory with an empty environment.
The patch travels as untrusted data and is validated in memory. No generated
code or tests execute. The replay establishes protocol behavior only.
Patch correctness, model-backed Phase 2A, qualified isolation, EVAL-01 scoring,
and capability promotion are outside this runbook.
