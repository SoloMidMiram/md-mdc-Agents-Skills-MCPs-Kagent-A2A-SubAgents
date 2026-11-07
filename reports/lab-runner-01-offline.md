# LAB-RUNNER-01 offline hardening — 2026-11-07

Development evidence only. Based on #18 commit `caa7d80e8512bc886c98393e322fc3df7f1f8ea2`, tree `9e6630b0c422d928b90216d367605d0f24a27d1a`. Existing checkouts/staged work, schema 1.0 builder, LAB-01 fixture, locks, task definitions, arms, model, ordering and budgets are unchanged. #20 tracks runner qualification; #21 remains blocked.

## Fresh lab evidence

Frozen dependency installation: `uv sync --frozen --group dev --python <retained-CPython-3.13.15>` succeeded in a separate checkout. uv 0.13.6 installed the exact lock; no dependency update occurred. Windows environment: CPython 3.13.15, pytest 9.1.1, Ruff 0.15.22 and Git 2.56.0.windows.4.

Both existing examples commands exited 0 using new external artifact directories. Replay independently resolves six full-blob hashes and physical-LF excerpts, and produces identical packet bytes. Packet SHA-256: `902f82d137d398a94b36c4a8c3d8963b2bf9d5834a82402077701338dbd3ef45`. Corruption: 21/21 synthetic controls passed, including empty rejected stdout, absent output, sentinel preservation and unchanged selected-source/index bytes.

An initial combined suite passed 101 tests; the final combined suite passed **106 tests, zero skips/failures**, exit 0. A subsequent targeted test parametrization covers completed, failed and timeout records uniformly; its result is recorded separately in the PR. Context lint/format and whitespace passed. Ownership audit: 163 entries, zero missing/duplicate/unmapped entries; full validator exits 1 for exactly the same 65 inherited broken links as #18. All fixtures are synthetic; no captured coding-agent execution is supplied as proof.

## Offline changes

- New private-subject identity contract checks the historical tree and exact disposable commit/tree, tracked raw-byte inventory, staged modes/stages, refs and approved local configuration. It rejects unexpected ignored files, links, index flags, alternates, grafts, remote/replacement refs and injected hooks/configuration. Git inspection disables optional locks, fsmonitor/hooks and inherited Git configuration. It is read-only and remains a point-in-time check, not an atomic snapshot.
- New preparation adds identity seals to existing input digests. Existing blocked attempts are retained; missing seals require a fresh preparation. Launch and post-setup helpers recheck all inputs plus subject identity.
- Strict offline terminal parser rejects malformed UTF-8/JSON, duplicate JSON keys, absent/conflicting lifecycle events, empty final response, failure with exit zero, wrong thread, malformed usage and stale controller bindings. It binds the stream digest to controller-owned run ID/nonce/request digest/subject identity/execution handle; it does not invent fields in CLI events.
- The legacy launcher self-attestation/execution path is disabled. Supplied launcher files are never executed. Plausible terminal files, failed/timeouts or offline-valid synthetic fixtures cannot authorize evaluation/scoring. Independent qualification verification and the real dispatch boundary are still NOT IMPLEMENTED.

The conservative event subset derives from retained official non-interactive examples captured November 5 (thread.started, turn.started, item lifecycle and turn.completed usage), at [official documentation](https://learn.chatgpt.com/docs/non-interactive-mode). Installed `@openai/codex` package metadata reports 0.164.0. No authentication command, model execution or CLI upgrade was performed. Actual event-schema compatibility still requires a separately authorized smoke.

## Reproduction and retention

From the isolated checkout:

```text
uv run --frozen --group dev python scripts/context/labs/examples.py replay --artifacts <new-external-replay>
uv run --frozen --group dev python scripts/context/labs/examples.py corruption --artifacts <new-external-corruption>
uv run --frozen --group dev pytest -q tests/context --junitxml=<external-results.xml>
uv run --frozen --group dev ruff check scripts/context tests/context
uv run --frozen --group dev ruff format --check scripts/context tests/context
git diff --check
```

Raw replay/corruption results, generated identity seals, blocked-attempt records, XML/logs and digest inventory remain outside source control in the task's runner-offline-evidence directory. An incorrect shell working directory prevented one redirected test invocation from starting; the corrected invocation and its actual result are retained. Failed/partial attempts are not overwritten. No private account data is published.

## Remaining boundaries

SoloMidMiram remains owner; the virtual server is still a placeholder. No VM/provider adapter, credential arrangement, independent filesystem/network verifier, teardown proof, live smoke or scored experiment is delivered. No security qualification, performance improvement, discovery, approval or MCP delivery is claimed. Inherited broken links remain separate debt; no unrelated assertion or scanner is weakened. CI executes deterministic tests only, not models. Independent human review and parent integration remain outstanding.
