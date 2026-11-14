# CTX-LABS-01: context corruption controls

Run from a checkout containing CTX-01R:

```powershell
uv run --frozen --group dev python scripts/context/labs/examples.py corruption --artifacts <external-new-directory>
```

This creates synthetic disposable repositories outside source control. Seven corruption categories cover wrong hash, invalid span, edit, deletion, assume-unchanged, skip-worktree and invalid UTF-8. Each is exercised in stdout, absent-output and existing-sentinel modes (21 controls). Fixture preparation deliberately changes files before invoking the builder; construction itself must leave selected bytes and index bytes unchanged.

Expected wrapper exit 0 only when every builder invocation exits 2, stdout is empty, absent output remains absent and sentinel is preserved. corruption.json retains argv, actual exit, diagnostic and assertions. synthetic/ holds inputs and repos. Failed controls or existing output directories reject; retain failure records and use a fresh directory, never overwrite evidence.

These are negative demonstrations, not real coding outcomes. [Packet lab](ctx-labs-01-packets.md) supplies the positive control.
