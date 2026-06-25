# Playwright MCP Server Deployment

This directory contains configuration for deploying Playwright MCP as a Docker container on a Linux server.

---

## Prerequisites

- Docker Engine (verify: `docker version`)
- Docker Compose (verify: `docker compose version`)
- Server firewall allowing outbound HTTPS (for package downloads)
- SSH access from your Windows laptop

---

## Quick Start

### 1. Transfer Files to Server

From your Windows laptop:

```powershell
# Create directory on server
ssh myserver "sudo mkdir -p /opt/playwright-mcp"

# Copy configuration files
scp compose.yaml myserver:/opt/playwright-mcp/
scp env-example.txt myserver:/opt/playwright-mcp/.env
```

Then SSH into the server:

```bash
ssh myserver
cd /opt/playwright-mcp
```

### 2. Start the Container

```bash
# Pull the pinned image
docker compose pull

# 3. Start the container
docker compose up -d

# 4. Verify it's running
docker compose ps
docker compose logs --tail=100 playwright-mcp
ss -lntp | grep 8931
```

---

## Server Commands

```bash
# Check Docker info
docker version
docker compose version

# Check if port 8931 is in use
ss -lntp | grep 8931 || true

# Start the service
docker compose up -d

# View service status
docker compose ps

# View logs (last 100 lines)
docker compose logs --tail=100 playwright-mcp

# View logs (follow mode)
docker compose logs -f playwright-mcp

# Restart the service
docker compose restart playwright-mcp

# Full container inspection
docker inspect playwright-mcp

# Stop the service (without removing images)
docker compose down

# Stop and remove images
docker compose down --rmi all

# Update the pinned image after validating a new tested version
docker compose pull
docker compose up -d
```

---

## Configuration

See `compose.yaml` for the service definition. Key settings:

| Setting | Value | Reason |
|---------|-------|--------|
| `--headless` | Enabled | No display available on a server |
| `--no-sandbox` | Enabled | Required for Chromium in Docker |
| `--isolated` | Enabled | Prevents browser state from saving to disk |
| `--host 0.0.0.0` | Inside container | Allows Docker port mapping from any container interface |
| `127.0.0.1:8931:8931` | Host binding | Only accessible from server localhost, not publicly |
| `init: true` | Enabled | Ensures proper signal handling for Node.js child processes |

---

## Security

- The MCP port is bound to **127.0.0.1** only — it is not accessible from other machines.
- Access is via SSH tunnel only (see `docs/03-REMOTE-PLAYWRIGHT-LAB.md`).
- Playwright MCP is **not a security boundary** — do not expose this endpoint publicly even behind authentication without careful consideration.
- Container does **not** mount the Docker socket, host filesystem, or run in privileged mode.

---

## Health Check

Verify the MCP endpoint is responding:

```bash
curl -v http://127.0.0.1:8931/mcp
```

Expected: Some JSON response (may be a method-not-found error over GET, which is normal — the endpoint expects POST with JSON-RPC).
