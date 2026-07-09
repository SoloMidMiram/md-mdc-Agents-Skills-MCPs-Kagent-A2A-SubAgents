# Recurring Bugs

Document recurring defect patterns here with root cause and prevention strategy.

---

- Ruff editor warning repeated in VS Code workspace settings
  - Root cause: legacy `ruff.lint.run` remained in `.vscode/settings.json` after
    Ruff native-server migration.
  - Prevention: keep Ruff configuration in `pyproject.toml`, remove deprecated
    workspace settings, and use the workspace Python bundle/bootstrap script for
    repeatable editor setup.

- VS Code Remote-SSH repeated retry loop on failed connections
  - Root cause: Remote-SSH can keep retrying a failed host indefinitely. The
    `remote.SSH.maxReconnectionAttempts: 0` setting has a known bug (VS Code
    issue #8910) where the first reconnection retry always fires regardless.
    Combined with SSH-side `ConnectionAttempts` (default 5 on this machine),
    each VS Code session would spawn up to 5 SSH connection attempts with 30s
    timeouts. The "auth mismatch" error (stale `.vscode-server` secret on
    remote) triggers a retry storm because the resolver loops on that error.
  - Prevention (VS Code settings in `.vscode/settings.json`):
    * `remote.SSH.maxReconnectionAttempts`: `0` — disable reconnection (after
      the unavoidable first buggy retry, it stops).
    * `remote.SSH.connectTimeout`: `15` — fail fast per tunnel attempt.
    * `remote.SSH.useLocalServer`: `false` — prevent local daemon multiplexing.
    * `remote.SSH.useExecServer`: `false` — fresh remote code-server per window.
    * `remote.SSH.showLoginTerminal`: `true` — surface SSH debug output.
    * `remote.SSH.enableDynamicForwarding`: `true` — avoid terminal-width
      wrapping bug that corrupts the connection token (see issue #5818).
  - Prevention (SSH config in `%USERPROFILE%\\.ssh\\config`):
    * `ConnectionAttempts 1` on every Host block — each SSH invocation tries
      exactly once.
    * `ConnectTimeout 15` on every Host block — fail fast per attempt.
  - Recovery (auth mismatch / stale server):
    * Run `Remote-SSH: Kill VS Code Server on Host` from the command palette.
    * Or `ssh myserver-proxy "rm -rf ~/.vscode-server"` then reconnect.
