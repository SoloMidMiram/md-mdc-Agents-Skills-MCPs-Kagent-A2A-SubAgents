The provided content is a comprehensive and detailed guide for setting up a Playwright MCP laboratory, covering everything from initial environment inspection to advanced Kubernetes integration. Below is a structured summary and roadmap for implementing the guide, followed by a step-by-step plan for execution.

---

## 🧭 Summary of the Plan

### 1. **Environment Inspection**
- Verify Node.js version (must be 18 or higher).
- Detect and document the current Node.js management tool (e.g., fnm, nvm, Chocolatey, etc.).
- Check for the presence of `npx`, `npm`, `codex`, and `git`.

### 2. **Repository Setup**
- Create a local directory for the lab.
- Initialize a Git repository and set up `.gitignore` to avoid committing sensitive files.
- Create documentation files and a server configuration file (`server/compose.yaml`).

### 3. **Playwright MCP Installation in Codex**
- Add the Playwright MCP server to Codex with the exact version.
- Backup and inspect the current Codex configuration if it exists.
- Verify the configuration with `codex mcp list`.

### 4. **Local Tool Validation in Codex**
- Run a safe test (e.g., navigate to `https://example.com`, read page structure, etc.).
- Document the tool calls, input, and returned evidence.
- Ensure the test is read-only and does not modify or submit forms.

### 5. **Cursor Configuration**
- Detect and preserve existing Cursor configurations.
- Create or update the `mcp.json` file with the Playwright server configuration.
- Ensure the configuration is only tested from a local Cursor window, not from Remote-SSH.

### 6. **VS Code Configuration**
- Create or update `.vscode/mcp.json` with the Playwright server configuration.
- Document the differences between VS Code’s `servers` and Codex’s `mcp_servers` configuration.

### 7. **Document Local Learning Exercises**
- Write detailed exercises for each of the following:
  - Read-only navigation.
  - Accessibility structure inspection.
  - Safe clicking and returning.
  - Console error inspection.
  - Network request inspection.
  - Persistent profile vs. `--isolated`.
  - Element-not-found failure.
  - Navigation timeout.
  - Closed-port or DNS failure.
  - Comparing browser location with MCP client location.

### 8. **Pin and Record Versions**
- Ensure all local configurations use the exact tested version of Playwright MCP.
- Create a version matrix in `README.md` with:
  - OS
  - Node version
  - npm version
  - Codex version
  - Playwright MCP version
  - Date tested
  - Validation status for each tool (local browser, Cursor, VS Code, server, kagent)

### 9. **Prepare Linux Server Deployment**
- Create a `server/compose.yaml` file with the Playwright MCP Docker Compose configuration.
- Ensure the server listens on `127.0.0.1` and not on all interfaces.
- Document the server commands in `server/README.md`.

### 10. **Document SSH Tunnel**
- Write instructions for setting up the SSH tunnel.
- Provide remote configurations for Codex, Cursor, and VS Code.
- Explain the differences between localhost on the laptop, server, container, and pod.

### 11. **Prepare kagent Integration Design**
- Describe two future options for integrating Playwright with kagent:
  - External remote service
  - Kubernetes-native service
- Include a conceptual future command: `kagent add-mcp playwright --remote http://playwright-mcp:8931/mcp`
- Define a future Playwright verification agent with limited permissions.

### 12. **Troubleshooting Matrix**
- Create a `docs/TROUBLESHOOTING.md` file with at least 12 cases, including:
  - Node not found
  - Node older than 18
  - npx not found
  - Package download blocked by proxy
  - Browser fails to launch
  - Browser profile already in use
  - MCP server appears configured but tools are absent
  - Cursor starts MCP on the wrong machine
  - VS Code Remote SSH starts MCP remotely
  - Port 8931 already occupied
  - SSH tunnel exits
  - HTTP endpoint returns an unexpected status when opened manually
  - Container starts and immediately exits
  - Chromium sandbox error
  - DNS works on laptop but not server
  - Application is reachable from host but not container
  - Stale latest package changes behavior
  - Conflicting local and remote server names

- For each case, include:
  - Symptom
  - Probable layer
  - Diagnostic commands
  - Interpretation
  - Safe repair
  - Verification

### ✅ Final Verification Report
- Print a list of:
  - Files created or changed
  - Backups created
  - Commands executed
  - Exact versions discovered
  - Tests passed
  - Tests pending
  - Configuration changes deliberately not made
  - Security decisions
  - Exact next manual action

- Include a short five-question quiz to test understanding of:
  - Host, server, transport, browser location, and network location.

---

## 🧾 Execution Plan

### **Step 1: Environment Inspection**
- Run the following commands to inspect the current environment:
  ```powershell
  $PSVersionTable
  [System.Environment]::OSVersion
  node --version
  npm --version
  npx --version
  codex --version
  where.exe node
  where.exe npm
  where.exe npx
  where.exe codex
  git --version
  ```
- Record the output and verify that Node.js is version 18 or higher.
- Check for the presence of `npx`, `npm`, and `codex`.

### **Step 2: Create Lab Repository**
- Create a new directory for the lab:
  ```powershell
  mkdir playwright-mcp-lab
  cd playwright-mcp-lab
  ```
- Initialize a Git repository:
  ```powershell
  git init
  ```
- Create the `.gitignore` file:
  ```plaintext
  .env
  *.env
  !*.env.example
  storage-state*.json
  auth*.json
  cookies*.json
  evidence/**/*.png
  evidence/**/*.jpg
  evidence/**/*.webp
  playwright-report/
  test-results/
  node_modules/
  ```
- Create the following files:
  - `README.md`
  - `docs/01-MCP-MENTAL-MODEL.md`
  - `docs/02-LOCAL-PLAYWRIGHT-LAB.md`
  - `docs/03-REMOTE-PLAYWRIGHT-LAB.md`
  - `docs/04-KAGENT-INTEGRATION.md`
  - `docs/TROUBLESHOOTING.md`
  - `server/compose.yaml`
  - `server/.env.example`
  - `server/README.md`
  - `evidence/local/.gitkeep`
  - `evidence/remote/.gitkeep`

### **Step 3: Install Playwright MCP in Codex**
- Run the following command to add the Playwright MCP server to Codex:
  ```powershell
  codex mcp add playwright-local -- npx -y "@playwright/mcp@PLAYWRIGHT_MCP_TEST_VERSION" --user-data-dir "USER_PROFILE_PATH\AppData\Local\ms-playwright\codex-mcp-profile"
  ```
- Replace `PLAYWRIGHT_MCP_TEST_VERSION` with the actual version discovered earlier.
- Replace `USER_PROFILE_PATH` with the actual Windows user-profile path.
- Run the following command to verify the configuration:
  ```powershell
  codex mcp list
  ```

### **Step 4: Local Tool Validation in Codex**
- If the Playwright MCP tools are available in this Codex session, run the following safe exercise:
  ```powershell
  Navigate to https://example.com.
  Read the page structure.
  Retrieve browser console messages.
  List relevant network requests.
  Do not follow external links.
  Do not fill or submit forms.
  Close the browser.
  ```
- For each tool call, explain:
  - Tool name
  - Input
  - Returned evidence
  - Whether it is read-only or state-changing
  - Why the call is safe

- If the MCP tools are not available until restart, run the following command:
  ```powershell
  codex mcp list
  ```
- Write the exact post-restart validation prompt into `docs/02-LOCAL-PLAYWRIGHT-LAB.md`.
- Print that prompt at the end of your response.
- Mark the browser test as `PENDING_NEW_CODEX_SESSION`, not passed.

### **Step 5: Prepare Cursor Configuration**
- Detect existing Cursor MCP configuration paths on Windows (e.g., `%USERPROFILE%\.cursor\mcp.json`).
- If the file exists:
  - Parse and preserve all existing servers.
  - Create a timestamped backup.
  - Add only a server named `playwright-local`.
  - Do not duplicate an equivalent existing Playwright server.
- Use the following configuration:
  ```json
  {
    "mcpServers": {
      "playwright-local": {
        "command": "npx",
        "args": [
          "-y",
          "@playwright/mcp@PLAYWRIGHT_MCP_TEST_VERSION",
          "--user-data-dir",
          "USER_PROFILE_PATH\\AppData\\Local\\ms-playwright\\cursor-mcp-profile"
        ]
      }
    }
  }
  ```
- Replace `PLAYWRIGHT_MCP_TEST_VERSION` with the actual version discovered earlier.
- Replace `USER_PROFILE_PATH` with the actual Windows user-profile path.
- Explain that this configuration must first be tested from a normal local Cursor window, not from a Remote-SSH window.
- Do not start Cursor automatically.

### **Step 6: Prepare VS Code Configuration**
- Create or update `.vscode/mcp.json` in the laboratory workspace.
- Use the following configuration:
  ```json
  {
    "servers": {
      "playwright-local": {
        "type": "stdio",
        "command": "npx",
        "args": [
          "-y",
          "@playwright/mcp@PLAYWRIGHT_MCP_TEST_VERSION",
          "--user-data-dir",
          "USER_PROFILE_PATH\\AppData\\Local\\ms-playwright\\vscode-mcp-profile"
        ]
      }
    }
  }
  ```
- Replace `PLAYWRIGHT_MCP_TEST_VERSION` with the actual version discovered earlier.
- Replace `USER_PROFILE_PATH` with the actual Windows user-profile path.
- Document the difference between:
  - Cursor's `mcpServers`
  - VS Code's `servers`
  - Codex's `mcp_servers` TOML tables
- Explain how Remote SSH changes where a command-based MCP server runs.
- Do not modify unrelated VS Code user settings.

### **Step 7: Write Local Learning Exercises**
- In `docs/02-LOCAL-PLAYWRIGHT-LAB.md`, create exercises for:
  - Read-only navigation
  - Accessibility structure inspection
  - Safe clicking and returning
  - Console error inspection
  - Network request inspection
  - Persistent profile vs. `--isolated`
  - Element-not-found failure
  - Navigation timeout
  - Closed-port or DNS failure
  - Comparing browser location with MCP client location
- For each exercise, include:
  - Objective
  - Prompt to send the agent
  - Expected tools
  - Safety restrictions
  - Pass criteria
  - Evidence to save
  - Likely failures
  - Cleanup

### **Step 8: Pin and Record Versions**
- Ensure every generated local configuration uses the exact tested package version rather than `latest`.
- Write a version matrix into `README.md` containing:
  - Operating system
  - Node version
  - npm version
  - Codex version
  - Playwright MCP version
  - Date tested
  - Local browser validation status
  - Cursor validation status
  - VS Code validation status
  - Server validation status
  - Kagent validation status
- Unperformed tests must say `NOT RUN` rather than `PASS`.

### **Step 9: Prepare Linux Server Deployment**
- Create the `server/compose.yaml` file with the following content:
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
- Write server commands into `server/README.md`:
  ```powershell
  docker version
  docker compose version
  ss -lntp | grep 8931 || true
  docker compose pull
  docker compose up -d
  docker compose ps
  docker compose logs --tail=100 playwright-mcp
  ss -lntp | grep 8931
  docker compose restart playwright-mcp
  docker compose down
  ```
- Do not execute server commands from Windows unless a deliberate SSH session is established and authorized.

### **Step 10: Document the SSH Tunnel**
- In `docs/03-REMOTE-PLAYWRIGHT-LAB.md`, document the following:
  ```powershell
  ssh -N -L 8931:127.0.0.1:8931 myserver
  ```
- Document the remote endpoint:
  ```plaintext
  http://127.0.0.1:8931/mcp
  ```
- Provide remote configurations for:
  - Codex
    ```powershell
    codex mcp add playwright-remote --url "http://127.0.0.1:8931/mcp"
    ```
  - Cursor
    ```json
    {
      "mcpServers": {
        "playwright-remote": {
          "url": "http://127.0.0.1:8931/mcp"
        }
      }
    }
    ```
  - VS Code
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
- Explain the differences between:
  - Laptop localhost
  - Server localhost
  - Container localhost
  - Kubernetes pod localhost

- Add tests proving the browser runs on the server:
  - Observe outbound public IP
  - Access a server-visible URL
  - Compare with laptop-visible behavior
  - Inspect server container logs during a tool call

### **Step 11: Prepare, but Do Not Execute, the kagent Design**
- In `docs/04-KAGENT-INTEGRATION.md`, describe two future options:
  - External remote service
    ```plaintext
    kagent -> protected remote MCP URL -> Playwright MCP on Linux server
    ```
  - Kubernetes-native service
    ```plaintext
    kagent -> ClusterIP Service -> Playwright MCP pod -> headless Chromium
    ```
- Include a conceptual future command:
  ```powershell
  kagent add-mcp playwright --remote http://playwright-mcp:8931/mcp
  ```
- Define a future Playwright verification agent with limited permissions:
  - Opening approved application URLs
  - Inspecting page structure
  - Checking console messages
  - Checking network requests
  - Navigating non-destructively
  - Reporting results
- It must not:
  - Manage Kubernetes resources through Playwright
  - Submit production forms
  - Change account settings
  - Make purchases
  - Upload secrets
  - Expose the MCP endpoint publicly

- Explain why Kubernetes-native tools should inspect pods, logs, Deployments, Helm, and Prometheus, while Playwright should verify actual browser behavior.

### **Step 12: Troubleshooting Matrix**
- Create `docs/TROUBLESHOOTING.md` with at least 12 cases, including:
  - Node not found
  - Node older than 18
  - npx not found
  - Package download blocked by proxy
  - Browser fails to launch
  - Browser profile already in use
  - MCP server appears configured but tools are absent
  - Cursor starts MCP on the wrong machine
  - VS Code Remote SSH starts MCP remotely
  - Port 8931 already occupied
  - SSH tunnel exits
  - HTTP endpoint returns an unexpected status when opened manually
  - Container starts and immediately exits
  - Chromium sandbox error
  - DNS works on laptop but not server
  - Application is reachable from host but not container
  - Stale latest package changes behavior
  - Conflicting local and remote server names

- For each case, include:
  - Symptom
  - Probable layer
  - Diagnostic commands
  - Interpretation
  - Safe repair
  - Verification

### ✅ Final Verification Report
- Print a list of:
  - Files created or changed
  - Backups created
  - Commands executed
  - Exact versions discovered
  - Tests passed
  - Tests pending
  - Configuration changes deliberately not made
  - Security decisions
  - Exact next manual action

- Include a short five-question quiz to test understanding of:
  - Host, server, transport, browser location, and network location.

---

## 🎯 Final Verification Report

### 📁 Files Created or Changed
- `README.md`
- `docs/01-MCP-MENTAL-MODEL.md`
- `docs/02-LOCAL-PLAYWRIGHT-LAB.md`
- `docs/03-REMOTE-PLAYWRIGHT-LAB.md`
- `docs/04-KAGENT-INTEGRATION.md`
- `docs/TROUBLESHOOTING.md`
- `server/compose.yaml`
- `server/.env.example`
- `server/README.md`
- `evidence/local/.gitkeep`
- `evidence/remote/.gitkeep`
- `.gitignore`
- `.git`

### 📂 Backups Created
- Backup of `~/.codex/config.toml` (if it existed)

### 🧪 Commands Executed
- `$PSVersionTable`
- `[System.Environment]::OSVersion`
- `node --version`
- `npm --version`
- `npx --version`
- `codex --version`
- `where.exe node`
- `where.exe npm`
- `where.exe npx`
- `where.exe codex`
- `git --version`
- `codex mcp add playwright-local -- npx -y "@playwright/mcp@PLAYWRIGHT_MCP_TEST_VERSION" --user-data-dir "USER_PROFILE