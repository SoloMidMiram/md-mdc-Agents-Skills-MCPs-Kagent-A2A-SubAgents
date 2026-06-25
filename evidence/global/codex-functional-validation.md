# Codex Functional Validation — `playwright-global` MCP

**Date:** 2026-06-25
**Tester:** cebit.ir (local Windows laptop)
**Environment:** Codex CLI session in `F:\Git\MCPtest`

---

## Test objective

Prove that `playwright-global` (user-level MCP registration in
`%USERPROFILE%\.codex\config.toml`) is:

1. Automatically discovered by Codex;
2. Automatically selected for browser-related tasks;
3. Capable of live browser navigation and console inspection;
4. The default browser tool — not replaced by `curl`, `rg`, or shell HTTP.

---

## Session evidence (sanitised)

### Test A — Explicit tool invocation

Codex was asked to use the Playwright MCP browser. It called:

```
mcp__playwright_global.browser_navigate
mcp__playwright_global.browser_tabs
```

The server returned live page data. Registration and server startup were
confirmed.

### Test B — Automatic tool routing

Codex was given a task that required web interaction. It **automatically
selected `mcp__playwright_global` tools** without being told to use MCP.

The relevant automatic calls were:

```
mcp__playwright_global.browser_navigate
mcp__playwright_global.browser_tabs
mcp__playwright_global.browser_console_messages
```

The browser returned live page data and console messages successfully.

---

## Verdict

```
CODEX_DISCOVERY:             PASS
CODEX_EXPLICIT_INVOCATION:   PASS
CODEX_AUTOMATIC_ROUTING:     PASS
CODEX_LIVE_NAVIGATION:       PASS
CODEX_CONSOLE_INSPECTION:    PASS
CODEX_GLOBAL_LOCAL_STATUS:   VERIFIED
```

The earlier "Codex not using MCP" observation is now understood as a
**past session-level routing result**, not evidence of a broken global
installation.

---

## Scope boundary

This proves the setup for **local Codex sessions using this Windows
Codex home** (`%USERPROFILE%\.codex\`). It does not automatically prove
the same configuration for:

- Codex running through SSH on a Linux server;
- A different Windows user account;
- WSL with a separate home directory;
- VS Code's own MCP host;
- Cursor's MCP host;
- Continue;
- A Codex session launched with a different `CODEX_HOME`.

Those are separate configuration surfaces.

---

## Status contribution

| Gate | Before | After |
|------|--------|-------|
| Codex MCP discovery | DISCOVERY_PASS | ✅ FUNCTIONAL_PASS |
| Codex automatic routing | UNKNOWN | ✅ VERIFIED |
| Overall validation verdict | `GLOBAL_PLAYWRIGHT_MCP_CONFIGURED_PENDING_VALIDATION` | Upgraded — one of five surfaces now FUNCTIONAL_PASS |
