# Official Python A2A SDK interoperability experiment

This isolated experiment targets the existing `k8s-a2a-agent` through the
kagent `0.9.11` controller. It does not change a Kubernetes manifest, a model
configuration, a Cursor file, or the repository's normal Python dependency
set.

The client uses the official `a2a-sdk==0.3.26` compatibility line because the
repository's pinned controller path is the A2A `0.3`-family JSON-RPC
`message/stream` endpoint. The kagent details endpoint is adapted into the
SDK's typed `AgentCard`; the SDK's `A2AClient` performs the actual streaming
request.

This gate intentionally does not add Context7, multi-agent orchestration, or
an A2A server.

## Isolated environment

From the repository root:

```bash
uv venv --python 3.13.15 .venv/a2a-sdk
uv pip sync --require-hashes --python .venv/a2a-sdk/bin/python \
  scripts/kagent/experiments/a2a_sdk_requirements.lock
```

The lock file is generated from `a2a_sdk_requirements.in`. The virtual
environment is intentionally ignored by Git.

## Run the experiment

An existing controller listener is required; the repository runbook uses
`127.0.0.1:8083`. The prompt is bounded and read-only:

```bash
.venv/a2a-sdk/bin/python scripts/kagent/experiments/a2a_sdk_interop.py \
  --controller http://127.0.0.1:8083 \
  --output json
```

The report records the Agent Card fields, protocol gate, wire request ID,
message ID, task ID, every observed status transition, response IDs, SDK
errors, and same-task correlation. It explicitly records that MCP tool
execution was not observed: an A2A SDK response is not evidence of an MCP
tool call.

An unsupported version is rejected before dispatch:

```bash
.venv/a2a-sdk/bin/python scripts/kagent/experiments/a2a_sdk_interop.py \
  --protocol-version 1.0 --output json
```

When the card endpoint is reachable, the command exits `1` with a protocol
compatibility error and does not send a task.

## Tests

```bash
.venv/a2a-sdk/bin/python -m pytest -q \
  tests/kagent/experiments/test_a2a_sdk_interop.py
```

These tests include an SDK-backed SSE round trip using an in-memory HTTPX
transport. No cluster or Kubernetes resource is touched by the tests.

The transport qualification and repair suites additionally exercise the real
SDK against a loopback HTTP/SSE fixture:

```bash
PYTHONDONTWRITEBYTECODE=1 "$SDK_PYTHON" -m pytest -p no:cacheprovider -q \
  tests/kagent/experiments/test_a2a_sdk_interop.py \
  tests/kagent/experiments/test_a2a_sdk_transport.py \
  tests/kagent/experiments/test_a2a_sdk_repairs.py \
  tests/kagent/experiments/test_a2a_sdk_cleanup.py
```

Use the qualified external Python 3.13.15 environment and the reviewed exact
lock for this qualification. Do not install the experiment into the root
project's environment. The environment creation example above is general
setup guidance, not a request to modify an existing `.venv`.

## Acceptance and native evidence boundary

Native output is `schemaName: kagent-sdk-interoperability`, `schemaVersion:
1.0`. It is **not** an educational schema 1.1 record. Neither changing the
version string nor constructing placeholder artifacts makes it compatible
with `contracts.validate_evidence_payload`.

`outcomes.transportEstablished` means an HTTP response to the A2A POST was
observed. `outcomes.dispatchAccepted` means a correlated task status accepted
the dispatch; a later failure can retain that observation.
`outcomes.execution` distinguishes completed, failed, canceled, rejected,
timed_out, incomplete, invalid, transport_failed, and not_attempted.
Only validated wire correlation and completed execution produce exit zero
and `decision.passed: true`. `claims.a2aCommunication` concerns the native
dispatch observation; it changes no canonical legacy L4 success semantics.

Each raw JSON-RPC envelope must match the SDK's actual wire request ID.
The pinned SDK rebuilds IDs in its high-level yielded objects, so those
objects alone cannot prove wire correlation. Every task-bearing event must
carry one nonempty, consistent task ID. A completed Task is terminal without
a status-update `final` field; a completed status-update requires `final:
true`. An artifact's `lastChunk` does not prove task completion. A final
input-required/auth-required response is incomplete execution, not success.

Failures retain available task IDs, transitions, HTTP status, response IDs
(null for mismatches), and sanitized diagnostics. External asyncio
cancellation propagates with a partial `observation` attached. The overall
monotonic deadline includes discovery and dispatch. Response hooks belong to
one dispatch and are removed in its cleanup path.

A future explicit SDK evidence profile or adapter needs these fields:

| Field group | Required source or decision |
| --- | --- |
| Provenance | Native schema name/version, observation time, interpreter and SDK versions; explicit synthetic versus live origin |
| Identity | Requested namespace/agent, returned matching card identity, endpoint, advertised protocol or explicitly labeled fallback |
| Request | Actual wire JSON-RPC ID/method, message ID, prompt digest |
| Observations | HTTP status, each response-ID match, task IDs and event kinds, status/final transitions, text and error codes |
| Acceptance | Separate transport/dispatch/execution outcomes, completion requirement, wire validity, exit code and reason |
| Safety | Sanitization policy and retained-data bounds; omitted or unavailable fields remain absent |
| Scope | Explicit non-claims for MCP execution and L6, I3, I4, L7 |

Educational 1.1 requires its own genuine example, supervisor, request/result,
artifact, success, and safety observations. This client does not collect all
of them; an adapter must either obtain and validate them or reject conversion.
It must not synthesize missing identities or educational artifacts.

Credential-labeled text and sensitive keys are redacted before retention and
before truncation; URLs retain only their origin. This is bounded diagnostic
sanitization, not a detector for arbitrary unlabeled secrets. Native report
consumers must distinguish recorded observations from computed decisions.
No deterministic result qualifies live Kagent operation or promotes a level.

## Repository integration test lanes

The root development lock and SDK lock are independent. The quality workflow
runs every SDK test in its `kagent-sdk` job using Python 3.13.15 and the exact
SDK lock. It checks the installed SDK version before test collection so that
the original tests' optional imports cannot silently satisfy that gate.
The root Python job explicitly excludes these SDK-only files; together the
two required deterministic lanes cover the complete Python suite.

For the root development environment:

```bash
uv run pytest -q \
  --ignore=tests/kagent/experiments/test_a2a_sdk_interop.py \
  --ignore=tests/kagent/experiments/test_a2a_sdk_transport.py \
  --ignore=tests/kagent/experiments/test_a2a_sdk_repairs.py \
  --ignore=tests/kagent/experiments/test_a2a_sdk_cleanup.py
```

For the external SDK environment, run the three qualification files above and
`tests/kagent/experiments/test_a2a_sdk_cleanup.py`. The latter checks a real SDK
transport's response-close exception for failed acceptance, redaction, retained
task observations, and preservation of caller-owned response hooks. No official
SDK objects are patched. A green root lane alone is insufficient qualification.

The [historical SDK record](../../../evidence/kagent/experiments/2026-10-22-a2a-sdk-interoperability.md)
is preserved as originally recorded. Its claims are not a new live observation.

## Dependency security correction (2026-11)

The isolated lock upgrades only `pyasn1` 0.6.4 → 0.6.5. The SDK remains 0.3.26,
pytest remains 9.0.3 and the other 31 package versions are retained. Generated
SHA-256 hashes are now enforced at installation. Universal compilation adds
Windows-only colorama 0.4.6, fixing the previously incomplete Windows dependency
set (33 installed on Windows; 32 on CPython Linux). Both native evidence 1.0 and
educational evidence 1.1 remain unchanged and distinct.

Regenerate with the qualified uv 0.7.22 toolchain, preserving the existing lock:

```bash
uv pip compile --universal --python-version 3.13 \
  scripts/kagent/experiments/a2a_sdk_requirements.in \
  --output-file scripts/kagent/experiments/a2a_sdk_requirements.lock \
  --upgrade-package pyasn1==0.6.5 --generate-hashes
```

[Dependency security procedures](../../../docs/runbooks/dependency-security.md)
require all 33 platform-union pins to appear in the current advisory result, without skips.
An audit service failure is not a clean scan. The original SDK-only
correction does not certify #9's inherited root. RECON-02 includes the reviewed
main correction and separately qualifies its actual combined tree; it remains
a review candidate, not maintainer or runtime approval. See issue #11. No cluster,
model, MCP, Context7, worker or CTX-01 implementation is changed here.
