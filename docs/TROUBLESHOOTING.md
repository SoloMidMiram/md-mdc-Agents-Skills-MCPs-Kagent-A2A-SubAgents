# Troubleshooting Matrix

A comprehensive guide to diagnosing and resolving common issues in the Playwright MCP laboratory.

---

## How to Use This Guide

Each issue entry follows this structure:

| Field | Description |
|-------|-------------|
| **Symptom** | What you observe |
| **Probable Layer** | Network, Browser, MCP, Client, or Infrastructure |
| **Diagnostic Commands** | What to run to narrow down the cause |
| **Interpretation** | What the diagnostic results mean |
| **Safe Repair** | How to fix the issue without data loss |
| **Verification** | How to confirm the fix worked |

---

## 1. Node Not Found

| Field | Details |
|-------|---------|
| **Symptom** | `node --version` returns "command not found" |
| **Probable Layer** | Client (laptop/server) |
| **Diagnostic Commands** | `where.exe node` (Windows) or `which node` (Linux); `$env:PATH` |
| **Interpretation** | Node.js is not installed or not in the system PATH. |
| **Safe Repair** | Install Node.js 18+ from [nodejs.org](https://nodejs.org) (LTS recommended). Use the official installer; do not use a package manager unless you already manage Node with one. Verify the installer added Node to PATH. |
| **Verification** | `node --version` returns v18.x.x or higher. |

---

## 2. Node Older Than 18

| Field | Details |
|-------|---------|
| **Symptom** | `node --version` returns v16.x.x or older |
| **Probable Layer** | Client (laptop/server) |
| **Diagnostic Commands** | `node --version`; `npm --version` |
| **Interpretation** | Playwright MCP requires Node.js >= 18. Older versions are incompatible. |
| **Safe Repair** | Download and install the latest LTS from [nodejs.org](https://nodejs.org). The installer replaces existing Node.js. If using nvm-windows: `nvm install 22` / `nvm use 22`. If using fnm: `fnm install 22`. |
| **Verification** | `node --version` returns v18.x.x or higher. |

---

## 3. npx Not Found

| Field | Details |
|-------|---------|
| **Symptom** | `npx --version` returns "command not found" |
| **Probable Layer** | Client (laptop/server) |
| **Diagnostic Commands** | `where.exe npx` (Windows); `which npx` (Linux); `npm --version` |
| **Interpretation** | npx is bundled with npm. If npm is installed but npx is missing, the installation may be corrupted or very old. |
| **Safe Repair** | Reinstall Node.js from the official installer (includes both npm and npx). Or: `npm install -g npx` (less common). |
| **Verification** | `npx --version` returns a version number. |

---

## 4. Package Download Blocked by Proxy

| Field | Details |
|-------|---------|
| **Symptom** | `npx -y "@playwright/mcp@latest" --help` hangs or fails with network/ETIMEOUT errors |
| **Probable Layer** | Network |
| **Diagnostic Commands** | `npm config get proxy`; `npm config get https-proxy`; `curl -I https://registry.npmjs.org` |
| **Interpretation** | Corporate proxy or firewall is blocking npm registry access. |
| **Safe Repair** | Configure npm proxy: `npm config set proxy http://proxy.company.com:8080` and `npm config set https-proxy http://proxy.company.com:8080`. Add `--registry` to npx if needed. Use `NODE_TLS_REJECT_UNAUTHORIZED=0` only for testing (not secure). |
| **Verification** | `npx -y "@playwright/mcp@latest" --help` succeeds within a reasonable time. |

---

## 5. Browser Fails to Launch

| Field | Details |
|-------|---------|
| **Symptom** | `browser_navigate` tool call returns an error about browser process failure |
| **Probable Layer** | Browser |
| **Diagnostic Commands** | Check MCP server logs (Codex/Cursor output); try launching `npx @playwright/mcp@latest` alone in terminal; check `--no-sandbox` flag on Linux |
| **Interpretation** | Playwright auto-installs Chromium on first run, but may fail due to missing system dependencies (Linux) or permission issues. |
| **Safe Repair** | On Linux: `sudo apt-get install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libdbus-1-3 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2`. Add `--no-sandbox` flag. On Windows: ensure sufficient disk space. |
| **Verification** | Browser opens visibly (headed mode) or tool returns success (headless). |

---

## 6. Browser Profile Already in Use

| Field | Details |
|-------|---------|
| **Symptom** | `browser_navigate` or launch fails with profile-locked error |
| **Probable Layer** | MCP Server / Browser |
| **Diagnostic Commands** | Check if another Codex/Cursor session is running; check `--user-data-dir` paths for lock files |
| **Interpretation** | Two MCP clients are trying to use the same persistent browser profile simultaneously. This is not supported — a browser profile can only be used by one process at a time. |
| **Safe Repair** | Use separate `--user-data-dir` paths for each client (e.g., codex-mcp-profile, cursor-mcp-profile, vscode-mcp-profile). Or use `--isolated` for disposable sessions. |
| **Verification** | Both clients can run browser tests independently. |

---

## 7. MCP Server Appears Configured but Tools Are Absent

| Field | Details |
|-------|---------|
| **Symptom** | `codex mcp list` shows playwright-local, but `/mcp` in the IDE shows no tools |
| **Probable Layer** | MCP Host |
| **Diagnostic Commands** | Restart the IDE session; check `codex mcp list` output; inspect `~/.codex/config.toml`; check if `npx` completed without errors |
| **Interpretation** | MCP servers are loaded at session start. If the server was added after the current session started, the tools will not appear until restart. |
| **Safe Repair** | Restart the Codex/Cursor/VS Code session. Verify the server starts without errors in the IDE output panel. |
| **Verification** | `/mcp` in the IDE shows browser tools: `browser_navigate`, `browser_click`, `browser_getAccessibilitySnapshot`, etc. |

---

## 8. Cursor Starts MCP on the Wrong Machine

| Field | Details |
|-------|---------|
| **Symptom** | Browser runs on the remote SSH host instead of the local laptop (or vice versa) |
| **Probable Layer** | MCP Host / Remote SSH |
| **Diagnostic Commands** | Check which Cursor window the MCP was added in (local vs Remote-SSH); inspect `~/.cursor/mcp.json` location; check `code-tunnel` status |
| **Interpretation** | Cursor's MCP configuration is scoped to the window where it was added. A Remote-SSH window executes MCP commands on the remote host. |
| **Safe Repair** | Add the local Playwright MCP server while in a normal local Cursor window, not a Remote-SSH window. For remote setup, add it in the remote context intentionally. |
| **Verification** | `browser_navigate https://api.ipify.org` — the IP matches the expected machine (laptop or server). |

---

## 9. VS Code Remote SSH Starts MCP Remotely

| Field | Details |
|-------|---------|
| **Symptom** | Browser unexpectedly runs on the SSH remote host |
| **Probable Layer** | MCP Host / Remote SSH |
| **Diagnostic Commands** | Check `.vscode/mcp.json` location (local workspace vs remote workspace); check VS Code's MCP output channel |
| **Interpretation** | VS Code Remote SSH uses separate settings scopes. Local `.vscode/mcp.json` runs on the local machine. Remote `.vscode/mcp.json` or remote user settings run on the remote host. |
| **Safe Repair** | Move the MCP config to the correct scope. For local testing: use local workspace `.vscode/mcp.json`. For remote testing: use remote workspace settings. |
| **Verification** | Browser public IP matches expected machine. |

---

## 10. Port 8931 Already Occupied

| Field | Details |
|-------|---------|
| **Symptom** | Docker container fails to start; `ss -lntp | grep 8931` shows another process on that port |
| **Probable Layer** | Infrastructure |
| **Diagnostic Commands** | `ss -lntp | grep 8931` (Linux) or `netstat -aon | findstr :8931` (Windows) |
| **Interpretation** | Another process (or previous container instance) is already using port 8931. |
| **Safe Repair** | Stop the existing process: `docker compose down` in the project directory, or kill the process using the port explicitly. Or change the host port in `compose.yaml` (e.g., `127.0.0.1:8932:8931`) and update the tunnel accordingly. |
| **Verification** | `ss -lntp | grep 8931` shows only the new docker-proxy process. |

---

## 11. SSH Tunnel Exits

| Field | Details |
|-------|---------|
| **Symptom** | MCP tools fail with connection refused; the SSH terminal shows "Connection closed" |
| **Probable Layer** | Network |
| **Diagnostic Commands** | Re-run `ssh -N -L 8931:127.0.0.1:8931 myserver -v` for verbose output; check server reachability: `ping myserver` |
| **Interpretation** | SSH session timed out, network interruption, or server rejected the connection. |
| **Safe Repair** | Re-establish the tunnel. Consider using `ssh -N -L 8931:127.0.0.1:8931 myserver -o ServerAliveInterval=60` to keep idle tunnels alive. Use a terminal multiplexer (tmux, screen) to detach the session. |
| **Verification** | `curl http://127.0.0.1:8931/mcp` returns a response. |

---

## 12. HTTP Endpoint Returns Unexpected Status

| Field | Details |
|-------|---------|
| **Symptom** | `curl http://127.0.0.1:8931/mcp` returns 404, 500, or connection timeout |
| **Probable Layer** | MCP Server / Network |
| **Diagnostic Commands** | `curl -v http://127.0.0.1:8931/mcp`; `docker compose logs playwright-mcp`; check if container is running: `docker compose ps` |
| **Interpretation** | The endpoint may be unreachable, the container may have crashed, or the port mapping may be incorrect. |
| **Safe Repair** | 404: Check the URL path (must end in `/mcp`). Check if using SSE transport (port only) vs Streamable HTTP. Check `--port` and `--host` command arguments. 500: Check container logs for MCP errors. Connection timeout: Check port binding and firewall. |
| **Verification** | `curl -v http://127.0.0.1:8931/mcp` returns a valid response (even if it's an error about missing JSON-RPC headers). |

---

## 13. Container Starts and Immediately Exits

| Field | Details |
|-------|---------|
| **Symptom** | `docker compose ps` shows the container as "Exited"; `docker compose logs` shows an error |
| **Probable Layer** | Infrastructure |
| **Diagnostic Commands** | `docker compose logs playwright-mcp`; `docker compose ps -a` |
| **Interpretation** | The Playwright MCP process fails to start, typically due to missing dependencies, incorrect command arguments, or Chromium launch failure. |
| **Safe Repair** | Check command arguments carefully. Ensure `--headless`, `--browser chromium`, `--port 8931`. Ensure `--no-sandbox` is present for Docker. Pull the pinned image again with `docker compose pull`. If the image is not found, verify the image tag. |
| **Verification** | `docker compose ps` shows "Up" status. `docker compose logs` shows the MCP server listening. |

---

## 14. Chromium Sandbox Error

| Field | Details |
|-------|---------|
| **Symptom** | Container logs show "Failed to move to new namespace" or sandbox-related errors |
| **Probable Layer** | Browser |
| **Diagnostic Commands** | `docker compose logs playwright-mcp`; check for "sandbox" in error messages |
| **Interpretation** | Chromium's sandbox requires kernel capabilities that are not available inside an unprivileged container. |
| **Safe Repair** | Add `--no-sandbox` to the command arguments. This is standard for containerized Playwright and documented by Microsoft. Alternative: run the container with `--security-opt seccomp=unconfined` (but `--no-sandbox` is the recommended approach). |
| **Verification** | Container starts and stays running. Browser tests succeed. |

---

## 15. DNS Works on Laptop but Not Server

| Field | Details |
|-------|---------|
| **Symptom** | `browser_navigate https://example.com` works locally but fails on the server with DNS errors |
| **Probable Layer** | Network |
| **Diagnostic Commands** | On server: `nslookup example.com`; `cat /etc/resolv.conf`; `curl -I https://example.com` |
| **Interpretation** | The server's DNS configuration differs from the laptop. Docker containers also have their own DNS resolution (typically via host's DNS or 127.0.0.11). |
| **Safe Repair** | Ensure the server has working DNS: `sudo systemd-resolve --flush-caches` or update `/etc/resolv.conf`. For Docker, ensure `dns:` is configured in `compose.yaml` if needed. |
| **Verification** | `curl -I https://example.com` succeeds on the server. `docker compose run playwright-mcp curl -I https://example.com` succeeds inside the container. |

---

## 16. Application Reachable from Host but Not Container

| Field | Details |
|-------|---------|
| **Symptom** | `curl http://localhost:PORT` works on the server but `browser_navigate http://localhost:PORT` fails in Playwright |
| **Probable Layer** | Network |
| **Diagnostic Commands** | Inside container: `docker exec playwright-mcp curl http://host.docker.internal:PORT`; check network mode |
| **Interpretation** | The container's `localhost` is not the host's `localhost`. The container cannot reach host services via `localhost` unless they are on the same Docker network or the host uses `host.docker.internal`. |
| **Safe Repair** | Use `host.docker.internal` for the host address. Or connect the container to the application's Docker network and use the service name. Or use `network_mode: host` (less secure, not recommended for production). |
| **Verification** | Browser can reach the application from inside the container. |

---

## 17. Stale `latest` Package Changes Behavior

| Field | Details |
|-------|---------|
| **Symptom** | Tests that worked yesterday fail today without any local changes |
| **Probable Layer** | MCP Server |
| **Diagnostic Commands** | `npm view "@playwright/mcp" version` — compare with pinned version |
| **Interpretation** | `@playwright/mcp@latest` changed. A new version was published with different behavior, new tools, removed tools, or changed defaults. |
| **Safe Repair** | Pin to the exact tested version: replace `@playwright/mcp@latest` with `@playwright/mcp@0.0.76` (or whatever version was tested). Update all configuration files (Codex, Cursor, VS Code, compose.yaml). Re-test before upgrading. |
| **Verification** | All configurations use the pinned version. Tests pass consistently. |

---

## 18. Conflicting Local and Remote Server Names

| Field | Details |
|-------|---------|
| **Symptom** | `codex mcp list` shows both `playwright-local` and `playwright-remote`; browser tools behave unpredictably |
| **Probable Layer** | MCP Host |
| **Diagnostic Commands** | `codex mcp list`; inspect `~/.codex/config.toml` for duplicate server entries |
| **Interpretation** | Two MCP servers with overlapping capabilities may cause the client to use the wrong one. If both are named similarly, tool calls may go to the wrong endpoint. |
| **Safe Repair** | Use distinct, descriptive names. Remove unused servers: `codex mcp remove playwright-local` if testing remotely. Use the IDE's MCP picker to select which server to use. |
| **Verification** | Only the intended MCP server appears in the list. Browser tools connect to the correct endpoint. |

---

## Quick Diagnostic Flowchart

```
Tools not working?
├── Is Node.js >= 18 installed?
│   ├── NO  → Install Node.js LTS
│   └── YES → Is npx working?
│       ├── NO  → Reinstall Node.js
│       └── YES → Can npx download @playwright/mcp?
│           ├── NO  → Check proxy/firewall
│           └── YES → Is MCP server configured?
│               ├── NO  → Add MCP server configuration
│               └── YES → Restart IDE session
│                   └── Tools still missing?
│                       ├── Check IDE output for launch errors
│                       ├── Check browser dependencies (Linux)
│                       └── Check file permissions / profile locks
│
Browser starts but tests fail?
├── Profile locked? → Use --isolated or separate profiles
├── Wrong machine? → Check localhost/remote SSH context
├── Port conflict? → Check port 8931 availability
├── Container exits? → Check --no-sandbox and logs
└── DNS/network? → Verify from server and container
```
