# A2A protocol laboratory

Use the pinned Python 3.13.15 and A2A SDK 0.3.26 environment from the [SDK experiment setup](../../scripts/kagent/experiments/README-a2a-sdk.md#isolated-environment). The exercises use in-memory HTTPX or a loopback HTTP/SSE fixture. They require no live controller, Kubernetes credentials, model, or MCP server.

Set the executable and test directory from the repository root (POSIX shell):

```sh
SDK_PYTHON=.venv/a2a-sdk/bin/python
T=tests/kagent/experiments
```

On Windows, use `.venv/a2a-sdk/Scripts/python.exe` and PowerShell variable syntax.

| Exercise | Run after `"$SDK_PYTHON" -m pytest -q` | Expected observation |
| --- | --- | --- |
| 1. Agent Card | `"$T/test_a2a_sdk_interop.py::test_agent_card_discovery_uses_existing_kagent_endpoint"` | The fixture returns the kagent card, which the adapter represents as an SDK Agent Card. |
| 2. Protocol compatibility | `"$T/test_a2a_sdk_transport.py::test_real_card_protocol_rejection_prevents_post"` | The client rejects an unsupported advertised version before the POST. |
| 3. JSON-RPC correlation | `"$T/test_a2a_sdk_transport.py::test_real_sdk_rejects_invalid_or_incomplete_stream[wrong_rpc]"` | The stream fails even when the event has plausible task data. |
| 4. Message and task identity | `"$T/test_a2a_sdk_interop.py::test_official_sdk_stream_records_task_and_status_correlation"` | The fixture observes the outbound message ID in the POST and the client reports the server task ID. |
| 5. SSE parsing and streaming | `"$T/test_a2a_sdk_transport.py::test_real_sdk_rejects_invalid_or_incomplete_stream[trailing_malformed]"` | A malformed trailing event prevents acceptance of the stream. |
| 6. Submitted and working | `"$T/test_a2a_sdk_transport.py::test_real_sdk_loopback_lifecycle"` | The real SDK reports submitted, working, and completed in order with one task identity. |
| 7. Terminal completion | `"$T/test_a2a_sdk_repairs.py::test_protocol_specific_terminal_shapes"` | The observer handles a completed Task and a final completed status update as distinct event shapes. |
| 8. Artifact extraction | `"$T/test_a2a_sdk_repairs.py::test_protocol_specific_terminal_shapes[artifact_then_status]"` | The observer extracts ACK from the artifact and completes only after the final status update. |
| 9. Failure and interruption | `"$T/test_a2a_sdk_transport.py" -k "rejects_invalid_or_incomplete_stream or timeout or cancellation"` | Failed, canceled, rejected, invalid, and incomplete streams cannot produce success. Timeouts fail, and caller cancellation propagates. |
| 10. Cleanup | `"$T/test_a2a_sdk_repairs.py::test_owned_hook_and_tasks_are_cleaned_on_every_exit" "$T/test_a2a_sdk_cleanup.py"` | Cleanup removes the observer-owned hook and preserves unrelated hooks, including when response close raises. |

The JSON-RPC request ID correlates the POST envelope with wire responses. The outbound message ID identifies the user message. The server task ID identifies the execution observed across task and update events. The pinned SDK yields parsed result objects to the caller. The recorder captures JSON-RPC response IDs at the HTTP response layer because those IDs are outside the yielded result objects.

A submitted or working update shows dispatch progress. A completed Task carries terminal state directly. A status update must report completed and set its final flag. An artifact update can finish an artifact without finishing the task. The loopback checks establish client behavior under the fixtures, while deployment readiness, live controller behavior, and MCP invocation require their own evidence.

The SDK report uses native schema 1.0. The educational example runner emits schema 1.1 under its own artifact contract. Run all four modules together for SDK qualification:

```sh
"$SDK_PYTHON" -m pytest -q "$T/test_a2a_sdk_interop.py" \
  "$T/test_a2a_sdk_transport.py" "$T/test_a2a_sdk_repairs.py" "$T/test_a2a_sdk_cleanup.py"
```
