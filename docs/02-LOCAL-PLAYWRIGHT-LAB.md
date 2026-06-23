# Local Playwright MCP Laboratory

This document covers local (laptop/desktop) setup and learning exercises for Playwright MCP using a visible browser.

---

## Prerequisites

- Node.js >= 18 (verified: v23.0.0)
- npm and npx (verified: 10.9.0)
- Git (verified: 2.45.2)
- Codex IDE (verified: CLI 0.142.0)
- One of: Cursor, VS Code (optional for local setup)
- A stable internet connection for package downloads

---

## Setup Instructions

### 1. Add Playwright MCP to Codex

```powershell
# Add the MCP server with a pinned version and isolated profile
codex mcp add playwright-local -- npx -y "@playwright/mcp@0.0.76" --user-data-dir "$env:USERPROFILE\AppData\Local\ms-playwright\codex-mcp-profile"
```

Replace `0.0.76` with the latest tested version from `npm view "@playwright/mcp" version`.

### 2. Verify Configuration

```powershell
codex mcp list
```

Expected output: `playwright-local` with command `npx` and the specified arguments.

### 3. Restart Codex Session

MCP tools are loaded when a new Codex session starts. You must open a fresh Codex window or restart the session.

---

## Learning Exercises

### Exercise 1: Read-Only Navigation

**Objective:** Learn how to open a page and read its structure without making any changes.

**Prompt to Agent:**
```
Use only the playwright-local MCP browser tools for this exercise.
1. Open https://example.com.
2. Describe the page using the accessibility information returned by Playwright.
3. Explain which browser tool you use at every step.
4. List all visible headings, links, and semantic structure.
5. Do not click anything, fill forms, or navigate to another domain.
6. Close the browser when finished.
```

**Expected Tools:** `browser_navigate`, `browser_getAccessibilitySnapshot`, `browser_getPageInfo`

**Safety Restrictions:** Do not click any links, submit forms, or modify data.

**Pass Criteria:** You can describe the page title, headings, and links from accessibility information alone.

**Evidence to Save:** Console output showing page structure, tool names, and descriptions.

**Likely Failures:**
- Browser fails to launch (Chromium not downloaded yet — Playwright MCP auto-installs it)
- Network timeout (slow connection)

**Cleanup:** Ensure `browser_close` is called before finishing.

---

### Exercise 2: Accessibility Structure Inspection

**Objective:** Use Playwright tools to explore a page's accessible elements.

**Prompt to Agent:**
```
Use only the playwright-local MCP browser tools for this exercise.
1. Open https://example.com.
2. Use the accessible snapshot tool to get a detailed breakdown of all elements.
3. Identify the role, name, and description of each element.
4. Do not click anything or submit forms.
5. Close the browser when finished.
```

**Expected Tools:** `browser_navigate`, `browser_getAccessibilitySnapshot`

**Safety Restrictions:** Read-only. Do not navigate to untrusted domains.

**Pass Criteria:** You receive a structured list of all interactive and informational elements.

---

### Exercise 3: Safe Clicking and Navigation

**Objective:** Perform a controlled interaction after evaluating safety.

**Prompt to Agent:**
```
Use only the playwright-local MCP browser tools for this exercise.
1. Open https://example.com.
2. Read the page structure.
3. Identify a link that is safe to click (e.g., "More information").
4. Explain why it is safe.
5. Click the link.
6. Describe the new page state.
7. Navigate back to the original page.
8. Close the browser when finished.
```

**Expected Tools:** `browser_navigate`, `browser_getAccessibilitySnapshot`, `browser_click`, `browser_goBack`

**Safety Restrictions:** Only click links on the original domain. Do not fill forms.

**Pass Criteria:** Successful round-trip navigation with state description after each step.

---

### Exercise 4: Console Error Inspection

**Objective:** Check a page for JavaScript errors and warnings.

**Prompt to Agent:**
```
Use only the playwright-local MCP browser tools for this exercise.
1. Open https://example.com.
2. Retrieve browser console messages.
3. Report: warnings, errors, and info messages separately.
4. Do not click anything or submit forms.
5. Close the browser when finished.
```

**Expected Tools:** `browser_navigate`, `browser_getConsoleMessages`

**Safety Restrictions:** Read-only diagnostics.

**Pass Criteria:** A structured report of console messages with severity level.

---

### Exercise 5: Network Request Inspection

**Objective:** Monitor network requests made by a page.

**Prompt to Agent:**
```
Use only the playwright-local MCP browser tools for this exercise.
1. Open https://example.com.
2. List all network requests initiated by the page.
3. Report: URLs, status codes, and request types.
4. Identify any failed requests.
5. Do not click anything or submit forms.
6. Close the browser when finished.
```

**Expected Tools:** `browser_navigate`, `browser_getNetworkRequests`

**Safety Restrictions:** Read-only diagnostics.

**Pass Criteria:** Complete request list with status codes and identification of any failures.

---

### Exercise 6: Persistent Profile vs. --isolated

**Objective:** Understand how browser state persistence works.

**Prompt to Agent (Persistent Profile):**
```
Use only the playwright-local MCP browser tools for this exercise.
1. Open https://example.com using the persistent profile (no --isolated flag).
2. Report whether localStorage or cookies are available.
3. Close the browser.
```

**Prompt to Agent (Isolated Profile):**
```
Use only the playwright-local MCP browser tools for this exercise.
1. Open https://example.com using --isolated mode.
2. Report the browser state.
3. Close the browser.
```

**Expected Tools:** `browser_navigate`, `browser_getPageInfo`, `browser_close`

**Safety Restrictions:** Do not save credentials or sensitive data.

**Pass Criteria:** Understand that persistent profiles retain state between sessions while isolated mode resets on every launch.

---

### Exercise 7: Element-Not-Found Failure

**Objective:** Diagnose what happens when an element does not exist.

**Prompt to Agent:**
```
Use only the playwright-local MCP browser tools for this exercise.
1. Open https://example.com.
2. Attempt to click a non-existent element (e.g., id="does-not-exist").
3. Report the exact error message and tool response.
4. Do not navigate to other domains.
5. Close the browser when finished.
```

**Expected Tools:** `browser_navigate`, `browser_click` (with invalid selector)

**Safety Restrictions:** Intentionally cause expected failure for learning.

**Pass Criteria:** See a meaningful timeout or not-found error message from Playwright.

---

### Exercise 8: Navigation Timeout

**Objective:** Observe behavior when a page takes too long to load.

**Prompt to Agent:**
```
Use only the playwright-local MCP browser tools for this exercise.
1. Attempt to navigate to http://localhost:1 (closed port).
2. Report the exact error and timeout behavior.
3. Explain which tool failed and why.
4. Close the browser when finished.
```

**Expected Tools:** `browser_navigate`

**Safety Restrictions:** Only use localhost or clearly unreachable addresses.

**Pass Criteria:** See a navigation failure with actionable error message.

---

### Exercise 9: DNS Failure

**Objective:** Diagnose a hostname resolution failure.

**Prompt to Agent:**
```
Use only the playwright-local MCP browser tools for this exercise.
1. Attempt to navigate to https://this-domain-does-not-exist-12345.com.
2. Report the exact error message.
3. Determine whether the failure is DNS, network, or timeout layer.
4. Close the browser when finished.
```

**Expected Tools:** `browser_navigate`

**Safety Restrictions:** Use a clearly fictitious domain to avoid accidental navigation.

**Pass Criteria:** Identify that the error is DNS resolution failure versus network timeout.

---

### Exercise 10: Compare Browser Location with MCP Client Location

**Objective:** Understand that the browser runs where the MCP server runs, not where the client UI runs.

**Prompt to Agent:**
```
Use only the playwright-local MCP browser tools for this exercise.
1. Open https://api.ipify.org?format=json to get the browser's public IP.
2. Report the IP address.
3. Explain: does this IP match your laptop's outbound IP or somewhere else?
4. Close the browser when finished.
```

**Expected Tools:** `browser_navigate`, `browser_getAccessibilitySnapshot`

**Safety Restrictions:** Read-only. No interaction beyond reading the IP.

**Pass Criteria:** Browser IP matches the laptop IP (for local MCP). This contrast will be important when testing remote browser.

---

## Configuration Templates

### Cursor (local, STDIO)

Create or update `%USERPROFILE%\.cursor\mcp.json`:

```json
{
    "mcpServers": {
        "playwright-local": {
            "command": "npx",
            "args": [
                "-y",
                "@playwright/mcp@0.0.76",
                "--user-data-dir",
                "C:\\Users\\YOUR_USER\\AppData\\Local\\ms-playwright\\cursor-mcp-profile"
            ]
        }
    }
}
```

### VS Code (local, STDIO)

Create or update `.vscode/mcp.json` in the workspace:

```json
{
    "servers": {
        "playwright-local": {
            "type": "stdio",
            "command": "npx",
            "args": [
                "-y",
                "@playwright/mcp@0.0.76",
                "--user-data-dir",
                "${userHome}\\AppData\\Local\\ms-playwright\\vscode-mcp-profile"
            ]
        }
    }
}
```

### Configuration Key Differences

| Platform | Top-Level Key | Transport Key |
|----------|--------------|---------------|
| Codex (TOML) | `[mcp_servers.playwright-local]` | `command = "npx"` |
| Cursor (JSON) | `"mcpServers"` | `"command"`, `"args"` |
| VS Code (JSON) | `"servers"` | `"type": "stdio"`, `"command"` |

**Important:** In VS Code with Remote SSH, an MCP configured in the local workspace starts on the **local machine**. An MCP configured in the remote workspace or remote user settings starts on the **remote host**. Always confirm which machine will run `npx` and host the browser.

---

## Pending Validation Prompt

If MCP tools are not yet loaded in the current Codex session, paste this after restarting:

```
Use only the playwright-local MCP browser tools for this exercise.
1. Open https://example.com.
2. Explain which browser tool you use at every step.
3. Describe the page using the accessibility information returned by Playwright.
4. Inspect console messages.
5. List network requests.
6. Do not fill forms, submit data, download files, or navigate to another domain.
7. Close the browser when finished.
```

Status: **PENDING_NEW_CODEX_SESSION** (run this after restart)
