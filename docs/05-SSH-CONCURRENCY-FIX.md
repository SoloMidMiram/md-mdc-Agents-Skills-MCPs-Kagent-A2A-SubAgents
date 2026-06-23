# SSH Concurrency Fix — Remote Lab Infrastructure

> **Date:** 2026-06-23
> **Context:** The remote Playwright MCP lab (see `03-REMOTE-PLAYWRIGHT-LAB.md`) requires reliable multi-window SSH access to the lab server. This document details a concurrency defect that prevented more than one VS Code Remote-SSH window from connecting, and the fix applied.

---

## Table of Contents

- [1. Problem Statement](#1-problem-statement)
- [2. Environment](#2-environment)
- [3. Root Cause Analysis](#3-root-cause-analysis)
- [4. Fix Applied](#4-fix-applied)
  - [4.1 Server-Side: MaxStartups](#41-server-side-maxstartups)
  - [4.2 Local SSH Aliases](#42-local-ssh-aliases)
  - [4.3 VS Code Configuration](#43-vs-code-configuration)
- [5. Verification](#5-verification)
- [6. How to Use](#6-how-to-use)
- [7. Rollback Instructions](#7-rollback-instructions)
- [8. Remaining Risks](#8-remaining-risks)

---

## 1. Problem Statement

Only **one** VS Code Remote-SSH window could connect to the lab server at `91.107.165.253`. A second VS Code window would hang indefinitely at:

```
debug1: Local version string SSH-2.0-OpenSSH_for_Windows_9.5
```

No remote protocol banner was received — the connection stalled before SSH authentication began.

### Impact on the Lab

The `03-REMOTE-PLAYWRIGHT-LAB.md` workflow requires:
- Opening the lab project in VS Code via Remote-SSH
- Running browser automation commands in the integrated terminal
- Monitoring server-side processes

A single-window limit made this impractical — especially when needing to inspect server state while running tests.

---

## 2. Environment

| Component | Version |
|-----------|---------|
| SSH Client | OpenSSH_for_Windows_9.5p2, LibreSSL 3.8.2 |
| SSH Server | OpenSSH_9.6p1 Ubuntu-3ubuntu13.16 |
| VS Code | 1.125.1 |
| SOCKS5 Proxy | xray (PID 3800, local port 10808) |
| Proxy Connector | Git connect.exe (`C:\Program Files\Git\mingw64\bin\connect.exe`) |
| Proxy Script | `%USERPROFILE%\.ssh\proxy_fallback.bat` |
| Local OS | Windows |
| Remote OS | Ubuntu (VM) |

### SSH Config (Before Fix)

The server was reachable only through a SOCKS5 proxy (`xray` on `127.0.0.1:10808`). The SSH config had two host blocks (`myserver` and the raw IP), both using `proxy_fallback.bat` as `ProxyCommand`:

```ssh-config
Host myserver
    HostName 91.107.165.253
    Port 22
    User root
    ProxyCommand C:\Users\cebit.ir\.ssh\proxy_fallback.bat %h %p
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    # ... other options

Host 91.107.165.253
    HostName 91.107.165.253
    User root
    ProxyCommand C:\Users\cebit.ir\.ssh\proxy_fallback.bat %h %p
    # ...
```

The proxy script (`proxy_fallback.bat`):

```bat
@echo off
setlocal EnableExtensions
set "TARGET_HOST=%~1"
set "TARGET_PORT=%~2"
set "CONNECT=C:\Program Files\Git\mingw64\bin\connect.exe"

if not exist "%CONNECT%" (
    echo [proxy_fallback] connect.exe not found: %CONNECT% >&2
    exit /b 1
)

powershell -NoProfile -Command "$c=New-Object Net.Sockets.TcpClient; $r=$c.BeginConnect('127.0.0.1',10808,$null,$null); if(-not $r.AsyncWaitHandle.WaitOne(800)){$c.Close();exit 1}; $c.EndConnect($r);$c.Close();exit 0" >nul 2>&1
if not errorlevel 1 (
    "%CONNECT%" -S 127.0.0.1:10808 %TARGET_HOST% %TARGET_PORT%
    if not errorlevel 1 exit /b 0
)

"%CONNECT%" %TARGET_HOST% %TARGET_PORT%
exit /b %errorlevel%
```

---

## 3. Root Cause Analysis

### Discovery

A raw TCP probe to port 22 revealed the server's rejection message:

```
> $tcp.Connect('91.107.165.253', 22)
> [Text.Encoding]::ASCII.GetString($buffer, 0, $bytes)
"Exceeded MaxStartups"
```

### Confirmation

Server inspection showed:

```bash
# Effective config
$ /usr/sbin/sshd -T | grep maxstartups
maxstartups 10:30:100

# Listener state showed exceeded threshold
$ pgrep -af 'sshd -D'
1566689 sshd: /usr/sbin/sshd -D [listener] 25 of 10-100 startups
```

### Root Cause: `SSHD_MAXSTARTUPS_LIMIT`

The SSH daemon had the compiled-in default `MaxStartups 10:30:100`, which drops new connections once **10 unauthenticated (pre-auth) sessions** exist. The server is publicly exposed and attracted 25+ concurrent pre-auth connections from scanners/bots — 15 beyond the threshold.

### Why Direct SSH Also Failed

A direct route test (`ProxyCommand=none`) failed with:

```
debug1: Connection established.
...
Connection timed out during banner exchange
Connection to 91.107.165.253 port 22 timed out
```

TCP established, but the server sent `"Exceeded MaxStartups"` instead of an SSH protocol banner. OpenSSH interprets this as a timeout because the response is not a valid SSH banner.

### The Proxy Path

The `proxy_fallback.bat` script was **not** the primary defect. It correctly:
- Tests SOCKS5 availability with an 800ms TCP probe
- Routes through `connect.exe -S 127.0.0.1:10808` when SOCKS5 is up
- Falls back to direct `connect.exe` when SOCKS5 is down
- Uses no shared temp files, no fixed port listeners, no background spawning, no stdout corruption

However, even the proxy path could not bypass the server-side `MaxStartups` limit.

### Classification

```
PRIMARY:   SSHD_MAXSTARTUPS_LIMIT
FIX:       Increase MaxStartups on the server
SECONDARY: No direct route to port 22 (requires SOCKS5 proxy)
```

---

## 4. Fix Applied

### 4.1 Server-Side: MaxStartups

**Backup created** on server before modification:
```
/etc/ssh/sshd_config.backup-
```

**Before** (commented out, using compiled-in defaults):
```ssh-config
#MaxStartups 10:30:100
#MaxSessions 10
```

**After**:
```ssh-config
MaxStartups 100:30:200
MaxSessions 50
```

**Applied**:
```bash
/usr/sbin/sshd -t       # Validate config — PASSED
systemctl restart sshd   # Apply changes
```

**Verification**:
```bash
$ /usr/sbin/sshd -T | grep -E "maxstartups|maxsessions"
maxstartups 100:30:200
persourcemaxstartups none
maxsessions 50
```

### 4.2 Local SSH Aliases

Two explicit aliases were added to `%USERPROFILE%\.ssh\config` **without** removing existing entries (safety rules):

```ssh-config
# Direct alias (no proxy) — use when network allows direct SSH
Host myserver-direct
    HostName 91.107.165.253
    User root
    Port 22
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    ProxyCommand none
    ServerAliveInterval 15
    ServerAliveCountMax 3

# Proxy alias (explicit fallback via SOCKS5)
Host myserver-proxy
    HostName 91.107.165.253
    User root
    Port 22
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    ProxyCommand C:\Users\cebit.ir\.ssh\proxy_fallback.bat %h %p
    ServerAliveInterval 15
    ServerAliveCountMax 3
```

### 4.3 VS Code Configuration

Added to `%APPDATA%\Code\User\settings.json`:

```json
{
    "remote.SSH.path": "C:\\Windows\\System32\\OpenSSH\\ssh.exe",
    "remote.SSH.useLocalServer": false,
    "remote.SSH.useExecServer": false,
    "remote.SSH.showLoginTerminal": true,
    "remote.SSH.enableDynamicForwarding": true,
    "remote.SSH.remotePlatform": {
        "myserver-direct": "linux",
        "myserver-proxy": "linux",
        "myserver": "linux"
    }
}
```

Key choices:
- `useLocalServer: false` — prevents VS Code from multiplexing connections through a local daemon, which can cause single-point-of-failure issues
- `useExecServer: false` — ensures the remote `code-server` is freshly launched per window
- `showLoginTerminal: true` — exposes SSH debug output for future troubleshooting

---

## 5. Verification

### Test A: Two Concurrent Direct SSH Sessions

```
Session 1: vmtpnourixxx3jb109mzzb PID=2202055
Session 2: vmtpnourixxx3jb109mzzb PID=2202103
```

Both sessions active independently with distinct PIDs and source ports.

### Test A2: Two Concurrent Proxy SSH Sessions

```
Session 1: vmtpnourixxx3jb109mzzb PID=2202153 (exit IP: 95.182.85.39)
Session 2: vmtpnourixxx3jb109mzzb PID=2202203 (exit IP: 46.33.8.18)
```

Both sessions active through xray SOCKS5 with distinct proxy exit IPs.

### Existing Entries Preserved

```
myserver:      OK (original host block still works)
```

### VS Code Settings

```
remote.SSH.path:          C:\Windows\System32\OpenSSH\ssh.exe
remote.SSH.useLocalServer: false
remote.SSH.useExecServer:  false
```

---

## 6. How to Use

### Quick Start (Recommended)

```powershell
# Connect VS Code to the server
# In VS Code: Cmd+Shift+P → Remote-SSH: Connect to Host → myserver-direct
```

### Which Alias to Use

| Situation | Alias | Notes |
|-----------|-------|-------|
| Normal lab work | `myserver-direct` | No proxy overhead, fastest path |
| Direct route blocked | `myserver-proxy` | Routes through xray SOCKS5 |
| Scripted/CI access | `myserver-direct` | Use `-o BatchMode=yes` |
| Original config | `myserver` | Preserved, uses proxy |

### Multi-Root Workspace (Memory-Saving Alternative)

To avoid running multiple VS Code windows:

```powershell
# Open the workspace file included with this report:
C:\Users\cebit.ir\.ssh\reports\remote-workspace.code-workspace
```

This workspace contains three folders in a single remote window:
- `/opt/bots/v2raych`
- `/opt/bots/chat.bimeh`
- `/root/cursor-automation`

### CLI Concurrency Test

```powershell
# Test from PowerShell
$j1 = Start-Job -ScriptBlock { ssh -o "BatchMode=yes" myserver-direct "hostname; sleep 10" }
$j2 = Start-Job -ScriptBlock { ssh -o "BatchMode=yes" myserver-direct "hostname; sleep 10" }
Start-Sleep 5
Receive-Job $j1
Receive-Job $j2
Remove-Job $j1, $j2
```

---

## 7. Rollback Instructions

### Server-Side Rollback

```bash
# 1. Restore sshd_config from backup
cp -a /etc/ssh/sshd_config.backup- /etc/ssh/sshd_config

# 2. Validate
/usr/sbin/sshd -t

# 3. Restart
systemctl restart sshd

# 4. Confirm
systemctl status sshd --no-pager -l
```

### Local SSH Config Rollback

```powershell
# Restore from backup
Copy-Item "$env:USERPROFILE\.ssh\backup-20260623-155306\config" "$env:USERPROFILE\.ssh\config" -Force

# Or manually remove the two added aliases (myserver-direct, myserver-proxy)
# from %USERPROFILE%\.ssh\config
```

### VS Code Settings Rollback

Remove the following keys from `%APPDATA%\Code\User\settings.json`:
- `remote.SSH.path`
- `remote.SSH.useLocalServer`
- `remote.SSH.useExecServer`
- `remote.SSH.showLoginTerminal`
- `remote.SSH.enableDynamicForwarding`
- `myserver-direct` and `myserver-proxy` from `remote.SSH.remotePlatform`

Preserve all other settings.

---

## 8. Remaining Risks

1. **Two-window VS Code test not performed in GUI** — CLI concurrency is proven, but the final two-window VS Code test requires human GUI confirmation.

2. **Server remains publicly exposed** — The increased `MaxStartups` is a mitigation, not a cure. Consider:
   - `fail2ban` to block scanners
   - Cloud firewall ACLs to restrict source IPs
   - Moving SSH to a non-default port
   - `persourcemaxstartups` to rate-limit per source IP

3. **Proxy path is intermittent** — The `myserver-proxy` alias occasionally times out. This appears to be a `connect.exe` or xray timing issue rather than the SSH server. For reliable work, use `myserver-direct`.

4. **No `ControlMaster`** — VS Code's `useLocalServer: false` means each window creates fully independent connections. This is intentional and acceptable for reliability.

---

## References

- Full diagnostic report: `C:\Users\cebit.ir\.ssh\reports\remote_ssh_concurrency_report.md`
- Server backup: `/etc/ssh/sshd_config.backup-`
- Local backup: `%USERPROFILE%\.ssh\backup-20260623-155306\`
- Related lab doc: `03-REMOTE-PLAYWRIGHT-LAB.md`
