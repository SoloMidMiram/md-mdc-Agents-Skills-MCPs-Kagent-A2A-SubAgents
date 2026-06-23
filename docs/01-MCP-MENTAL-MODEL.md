# MCP Mental Model

The **Microsoft Playwright MCP** (Model-Client-Protocol) is a layered browser automation architecture that separates browser control from the client UI. This document builds the conceptual foundation required before any tool installation or automation work.

> **Core statement to understand:** *Cursor does not contain Playwright. Cursor starts or contacts an MCP server, and that MCP server controls a browser.*

---

## Key Concepts

### MCP Protocol
Defines the interaction between an MCP host (client) and an MCP server. It is a protocol, not a piece of software. There is no single central "MCP installation."

### MCP Host / Client
The UI tool or agent that initiates control commands. Examples: **Cursor**, **Codex**, **VS Code**, **kagent**.
- The host does NOT contain browser automation.
- The host sends JSON-RPC messages to the MCP server.

### MCP Server
Runs Playwright MCP and exposes browser control **tools** to the client. Examples: **Playwright MCP**, any service implementing the MCP protocol.
- The server controls the browser.
- The server is installed where its capability belongs (laptop, server, container).

### Browser
The actual **Chromium/Chrome** (or Firefox, WebKit) instance controlled by Playwright MCP.
- The browser runs where the MCP server runs.
- Playwright MCP auto-installs the browser binary on first launch.

### Transports
| Transport | How it works | When to use |
|-----------|-------------|-------------|
| **STDIO** | MCP is launched as a child process. Communication via stdin/stdout. | Local learning, single-user setup. No open port needed. |
| **HTTP** | MCP runs as a network service. Communication via HTTP/SSE. | Server, Docker, Kubernetes. Requires a reachable endpoint. |

### Profiles
| Mode | Behavior | Use Case |
|------|----------|----------|
| Persistent (`--user-data-dir`) | Cookies, local storage, and state survive between sessions. | Login workflows, stateful testing. |
| Isolated (`--isolated`) | Temporary profile kept in memory; no disk writes. | Repeatable tests, CI/CD, multi-client. |

**Important:** A persistent profile can only be used by one browser process at a time. Two MCP hosts (e.g., Cursor and Codex) will conflict if they share the same profile.

---

## Roles and Locations

| Component | Role | Typical Environment |
|-----------|------|--------------------|
| Cursor / Codex / VS Code | MCP Host / Client | Laptop or Workstation |
| kagent | MCP Host / Agent Host | Kubernetes or Local |
| Playwright MCP | MCP Server | Laptop, Server, or Container |
| Chromium / Chrome | Actual Browser | Same environment as MCP Server |
| STDIO Transport | Child process communication | Local / Laptop |
| HTTP Transport | Networked communication | Server or Kubernetes Pod |
| SSH Tunnel | Secured traffic relay | Between laptop and server |
| Docker | Packages browser + MCP runtime | Server |

---

## Traffic Flow Examples

### Local STDIO (Stage 0-1)
```
Codex (MCP Host)
  │ starts as child process via npx
  ▼ STDIO (no open port)
Playwright MCP (MCP Server on laptop)
  │ launches browser on laptop
  ▼
Chromium (visible browser on laptop)
```

### Remote HTTP (Stage 2)
```
Codex (MCP Host on laptop)
  │ SSH tunnel (encrypted)
  ▼ HTTP to localhost:8931
Playwright MCP (MCP Server on server)
  │ launches browser on server
  ▼
Chromium (headless browser on server)
```

### Kubernetes / kagent (Stage 3 — future)
```
kagent (MCP Host in cluster)
  │ ClusterIP Service
  ▼ HTTP to playwright-mcp:8931
Playwright MCP (MCP Server in pod)
  │ launches browser in same pod
  ▼
Chromium (headless browser in pod)
```

---

## Foundational Principles

1. **No central MCP installation.** MCP is a protocol. Each MCP server is installed where its capability belongs.
2. **Browser runs where the MCP server runs.** Not where the client UI runs.
3. **npx is an execution tool, not the MCP server.** `npx -y @playwright/mcp` downloads and runs the MCP package.
4. **Playwright MCP and Chromium are separate processes/components.** The MCP server is a Node.js process; the browser is Chromium.
5. **STDIO does not need an open port.** Communication happens through stdin/stdout of a child process.
6. **HTTP MCP does need a reachable endpoint.** The client must be able to make HTTP connections to the server's address.
7. **localhost changes meaning** across laptop, server, container, and pod. They are four different networks.
8. **Profiles cannot be shared** between two MCP hosts simultaneously. Each client needs its own profile or `--isolated` mode.
9. **Cursor local settings and Remote-SSH settings can start processes on different machines.** Always check which machine will execute `npx`.
10. **Playwright MCP is not a security boundary.** The endpoint must not be exposed publicly without network-level protection (SSH tunnel, VPN, firewall).

---

## Why This Matters Before Deployment

| Scenario | Common Mistake | Correct Understanding |
|----------|---------------|----------------------|
| "I added Playwright to Cursor." | Assumes Cursor now contains Playwright. | Cursor configures an MCP server that runs Playwright. |
| "The browser is on my laptop." | Assumes all browsers run locally. | The browser runs where the MCP server runs. |
| "I can reach localhost:8931 from anywhere." | Assumes localhost is universal. | Laptop localhost ≠ server localhost ≠ container localhost. |
| "Two editors can share the same profile." | Assumes profiles are concurrent. | Profiles lock; use `--isolated` or separate paths. |
| "MCP is secure because it's a protocol." | Assumes protocol-level safety. | Network-level protection (SSH tunnel) is required. |

---

## Key Vocabulary

| Term | Definition |
|------|------------|
| **MCP** | Model-Client-Protocol — a protocol for AI agents to interact with tools. |
| **MCP Host** | The client application (Cursor, Codex, VS Code). |
| **MCP Server** | A service that exposes tools via the MCP protocol (e.g., Playwright MCP). |
| **Tool** | A capability exposed by an MCP server (e.g., `browser_navigate`). |
| **Transport** | The communication channel between host and server (STDIO or HTTP). |
| **JSON-RPC** | The message format used in MCP communication. |
| **Browser Snapshot** | Accessibility tree returned by Playwright, not a screenshot. |
| **Approval** | Mechanism where the user must approve certain tool calls before execution. |

---

## Success Criteria

Before moving to server deployment or Kubernetes, you should be able to explain:

1. Why `npx` is not the MCP server itself.
2. Why Playwright MCP and Chromium are separate processes/components.
3. Why STDIO does not need an open port.
4. Why an HTTP MCP server does need a reachable endpoint.
5. Why a server-side browser sees a different network than your laptop.
6. Why Cursor local settings and Remote-SSH settings can start processes on different machines.
7. Why two MCP clients can conflict over one persistent browser profile.
8. Why `localhost` changes meaning across laptop, server, container, and pod.
9. Why an MCP endpoint must not be exposed publicly without protection.
10. Why Playwright complements Kubernetes tools rather than replacing them.