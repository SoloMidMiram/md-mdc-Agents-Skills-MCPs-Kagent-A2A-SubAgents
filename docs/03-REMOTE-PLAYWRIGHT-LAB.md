# Remote Playwright MCP Laboratory

This document covers deploying Playwright MCP on a Linux server and accessing it securely via SSH tunnel.

---

## Prerequisites

- A Linux server (Ubuntu recommended) with Docker and Docker Compose
- SSH access from your Windows laptop to the server
- Successful completion of all local Playwright MCP exercises
- Playwright MCP version pinned to a tested version

---

## Architecture

```
Windows Laptop (MCP Host)
        │
        │ SSH tunnel (encrypted)
        │ -L 8931:127.0.0.1:8931
        ▼
Linux Server (127.0.0.1:8931)
        │
        ▼
Docker Container: mcr.microsoft.com/playwright/mcp
        │
        ▼
Headless Chromium (inside container)
```

### Understanding Localhost

There are four distinct `localhost` contexts:

| Context | What it means |
|---------|---------------|
| **Laptop localhost** | Your Windows machine. MCP host (Codex/Cursor) sees this. |
| **Server localhost** | The Linux server. The Docker host sees this. |
| **Container localhost** | Inside the Docker container. Playwright MCP listens on port 8931 here. |
| **Kubernetes pod localhost** | Inside the Kubernetes pod (future). See `docs/04-KAGENT-INTEGRATION.md`. |

**Key Insight:** `http://127.0.0.1:8931/mcp` from your laptop reaches the server's port 8931 *only* through an SSH tunnel. Without the tunnel, laptop `localhost` does not reach server `localhost`.

---

## Server Deployment

### 1. Preflight Check (on the server)

```bash
uname -a
docker version
docker compose version
ss -lntp | grep 8931 || true
curl -I https://example.com
```

### 2. Create Directory and Files

```bash
sudo mkdir -p /opt/playwright-mcp
cd /opt/playwright-mcp
```

### 3. Docker Compose Configuration

Create `/opt/playwright-mcp/compose.yaml`:

```yaml
services:
  playwright-mcp:
    image: mcr.microsoft.com/playwright/mcp
    container_name: playwright-mcp
    restart: unless-stopped
    init: true
    entrypoint:
      - node
    command:
      - /app/cli.js
      - --headless
      - --browser
      - chromium
      - --no-sandbox
      - --port
      - "8931"
      - --host
      - 0.0.0.0
      - --isolated
    ports:
      - 127.0.0.1:8931:8931
```

**Security Notes:**
- `--host 0.0.0.0` inside the container: Playwright listens on all interfaces *inside* the container. This is required for Docker port mapping to work.
- `ports: 127.0.0.1:8931:8931`: Docker publishes the port **only on server localhost** (`127.0.0.1`). The server's network interface does not expose port 8931 publicly.
- `--no-sandbox`: Required when running Chromium inside a container without privileged mode. This reduces security isolation but is standard for containerized Playwright.
- `--isolated`: Prevents browser state from being saved to disk. Each session starts clean.
- **Playwright MCP is not a security boundary.** Do not rely on MCP itself for access control.

### 4. Start the Container

```bash
docker compose pull
docker compose up -d
docker compose ps
docker compose logs --tail=100 playwright-mcp
ss -lntp | grep 8931
```

### 5. Server Operations

```bash
# View logs
docker compose logs --tail=200 playwright-mcp

# Restart
docker compose restart playwright-mcp

# Health check
docker inspect playwright-mcp
ss -lntp | grep 8931

# Rollback (stop without deleting images)
docker compose down
```

---

## SSH Tunnel Setup

From your Windows laptop, open a terminal and run:

```powershell
ssh -N -L 8931:127.0.0.1:8931 myserver
```

Keep this terminal open. The tunnel forwards:
- Laptop port **8931** → Server **127.0.0.1:8931** → Docker container **8931**

### Testing the Tunnel

```powershell
# From a separate terminal on the laptop
curl http://127.0.0.1:8931/mcp
```

Expected: A JSON response from the MCP endpoint (or a 405 if the method is not allowed over GET).

---

## Remote Client Configuration

### Codex Remote Configuration

```powershell
# Remove local server if it exists
codex mcp remove playwright-local

# Add remote server
codex mcp add playwright-remote --url "http://127.0.0.1:8931/mcp"

# Verify
codex mcp list
```

### Cursor Remote Configuration

Add to `%USERPROFILE%\.cursor\mcp.json`:

```json
{
    "mcpServers": {
        "playwright-remote": {
            "url": "http://127.0.0.1:8931/mcp"
        }
    }
}
```

### VS Code Remote Configuration

Add to `.vscode/mcp.json`:

```json
{
    "servers": {
        "playwright-remote": {
            "type": "http",
            "url": "http://127.0.0.1:8931/mcp"
        }
    }
}
```

---

## Verification Tests

### Test 1: Browser Runs on Server

Ask the remote browser:
```
1. Open https://api.ipify.org?format=json.
2. Report the IP address.
3. Compare with your laptop's public IP.
```

**Pass Condition:** The IP address matches the server's outbound IP, not the laptop's IP.

### Test 2: Server-Visible Application

If an application runs on the server (e.g., via `host.docker.internal` or a Docker network):

```
1. Open http://host.docker.internal:PORT (or the application's service name).
2. Describe the page.
3. Report console messages and network requests.
```

**Pass Condition:** The browser can reach the server-local application.

### Test 3: Compare Laptop vs. Server Behavior

Run the same exercise locally and remotely and compare:
- Page load times
- Network requests (different public IP)
- Console messages
- Console logs from `docker compose logs` during the tool call

---

## Troubleshooting Tunnel

| Symptom | Likely Cause | Check |
|---------|--------------|-------|
| Connection refused on laptop :8931 | SSH tunnel not running | `ssh -N -L ...` |
| Tunnel exits immediately | SSH key issue, wrong host | `ssh -v myserver` |
| Browser shows wrong IP | Tunnel not set up, browser running locally | Ensure remote URL configured |
| Slow responses | Network latency | Check SSH connection quality |
| Container exits immediately | Docker or Chromium error | `docker compose logs playwright-mcp` |

---

## Security Reminders

- Bind MCP port to **127.0.0.1** only.
- Use SSH tunnel for remote access — do not expose the MCP endpoint publicly.
- Playwright MCP is not an authentication layer or security boundary.
- Do not mount the Docker socket or host filesystem into the container.
- Do not run the container in privileged mode.
- Do not store credentials, cookies, or storage-state files in the repository.
