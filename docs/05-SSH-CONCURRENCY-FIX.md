# SSH Concurrency Fix — Remote Lab Infrastructure

> **Last updated:** 2026-06-25
> **Context:** The remote Playwright MCP lab (see `03-REMOTE-PLAYWRIGHT-LAB.md`) requires reliable multi-window SSH access to the lab server at `91.107.165.253`. This document chronicles the full history of connection defects — from root cause through multiple rounds of fixes — and their resolutions.

---

## Table of Contents

- [1. Problem Statement](#1-problem-statement)
- [2. Environment](#2-environment)
- [3. Diagnosis Log (Timeline)](#3-diagnosis-log-timeline)
  - [3.1 2026-06-23: First MaxStartups Discovery](#31-2026-06-23-first-maxstartups-discovery)
  - [3.2 2026-06-25: Recurrence — Scanners Overwhelm Limit](#32-2026-06-25-recurrence--scanners-overwhelm-limit)
  - [3.3 2026-06-25: Local Auto-Healthcheck Discovered](#33-2026-06-25-local-auto-healthcheck-discovered)
  - [3.4 2026-06-25: ControlMaster Conflict Discovered](#34-2026-06-25-controlmaster-conflict-discovered)
  - [3.5 2026-06-25: Server Reboot + fail2ban Install](#35-2026-06-25-server-reboot--fail2ban-install)
- [4. Cumulative Changes](#4-cumulative-changes)
  - [4.1 Server-Side Changes](#41-server-side-changes)
  - [4.2 Local SSH Config Changes](#42-local-ssh-config-changes)
  - [4.3 VS Code Configuration](#43-vs-code-configuration)
  - [4.4 SSH Key Management](#44-ssh-key-management)
- [5. Final Server State](#5-final-server-state)
- [6. How to Use](#6-how-to-use)
- [7. Rollback Instructions](#7-rollback-instructions)
- [8. Remaining Risks](#8-remaining-risks)

---

## 1. Problem Statement

Only **one** VS Code Remote-SSH window could connect to the lab server at `91.107.165.253`. A second VS Code window would hang indefinitely at:

```
debug1: Local version string SSH-2.0-OpenSSH_for_Windows_9.5
```

No remote protocol banner was received — the connection stalled before SSH authentication began. The root cause evolved across multiple sessions as each fix revealed deeper layers.

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
| fail2ban | 1.0.2 (installed 2026-06-25) |
| Local OS | Windows 10.0.26200 |
| Remote OS | Ubuntu (VM) |

### Original SSH Config (pre-fix)

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

## 3. Diagnosis Log (Timeline)

### 3.1 2026-06-23: First MaxStartups Discovery

**Symptom:** `ssh -vvv` showed `Local version string SSH-2.0-OpenSSH_for_Windows_9.5` but no remote banner.

**Evidence:** Raw TCP probe returned:

```
> $tcp.Connect('91.107.165.253', 22)
"Exceeded MaxStartups"
```

**Confirmation on server:**
```bash
$ /usr/sbin/sshd -T | grep maxstartups
maxstartups 10:30:100

$ pgrep -af 'sshd -D'
1566689 sshd: /usr/sbin/sshd -D [listener] 25 of 10-100 startups
```

**Fix Applied:** `MaxStartups` raised from `10:30:100` (default) to `100:30:200`.

**Result at the time:** Two concurrent SSH sessions verified working.

**Root cause classification at this point:** `SSHD_MAXSTARTUPS_LIMIT`

---

### 3.2 2026-06-25: Recurrence — Scanners Overwhelm Limit

**Symptom:** Could not connect at all through any path. SOCKS5 proxy (xray) was running, TCP through SOCKS5 reached the server, but no SSH banner was returned.

**Discovery:** The increased `MaxStartups 100:30:200` was not enough — exposed server attracted **more than 100 concurrent scanner connections**, keeping all slots saturated 24/7.

**Debug output:**
```
SOCKS5 reply: 0 (connection accepted)
No SSH banner received — server saturated
```

**Fix:**
1. Provider VM reboot to clear all pre-auth connections
2. Installed **fail2ban** to block repeat offenders
3. Added **PerSourceMaxStartups 30** so no single IP can flood the slots

**Execution of reboot + install:**
```bash
# Immediately after reboot:
apt update && apt install -y fail2ban

# Configure fail2ban:
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
logpath = %(sshd_log)s
EOF

systemctl restart fail2ban

# Add per-source rate limiting:
echo 'PerSourceMaxStartups 30' >> /etc/ssh/sshd_config
systemctl restart ssh
```

---

### 3.3 2026-06-25: Local Auto-Healthcheck Discovered

**Discovery:** A scheduled task `SSH-myserver-healthcheck` ran **every 5 minutes** and opened an SSH connection to verify reachability.

**Evidence:**
```
Task: SSH-myserver-healthcheck
Script: C:\Users\cebit.ir\.ssh\ssh-healthcheck.ps1
Runs: Every 5 minutes, via powershell.exe
Last run: 2026-06-25 at 09:49
Log: C:\Users\cebit.ir\.ssh\healthcheck.log (659 lines)
```

The script:
1. Checks if xray SOCKS5 is listening on `127.0.0.1:10808`
2. If proxy is up → runs `ssh myserver "echo ok"`
3. Logs result

**Assessment:** Not the primary cause of saturation (sends 1 SSH attempt every 5 minutes), but it added unnecessary load during recovery attempts and could time out while holding a slot.

**Fix:** Task **disabled**:
```powershell
Disable-ScheduledTask -TaskName "SSH-myserver-healthcheck"
```

---

### 3.4 2026-06-25: ControlMaster Conflict Discovered

**Discovery:** After adding `ControlMaster auto` to the global `Host *` block, SSH connections through the proxy path (`myserver-proxy`) failed with:

```
getsockname failed: Not a socket
Entering interactive session.
Read from remote host 91.107.165.253: Unknown error
```

**Root cause:** OpenSSH for Windows 9.5 has an incompatibility between `ControlMaster` and `ProxyCommand`. The control socket tries to getpeername/getsockname on the proxy's pipe, which is not a real socket — causing the connection to immediately abort after authentication.

**Fix:** Commented out the entire `Host *` ControlMaster block. Connection multiplexing is now handled by VS Code's own mechanism.

**Config change:**
```ssh-config
# Host *
#     ControlMaster auto
#     ControlPath ~/.ssh/control-%r@%h:%p
#     ControlPersist 15m
```

---

### 3.5 2026-06-25: Server Reboot + fail2ban Install

The server was rebooted from the provider dashboard to clear all pre-auth connections. Immediately after:

1. Connected via `myserver-proxy` (old key `vscode-myserver`)
2. Installed fail2ban (`apt install fail2ban`)
3. Added `PerSourceMaxStartups 30` to `sshd_config`
4. Added new `windows-laptop` key to `~/.ssh/authorized_keys`
5. Restarted SSH service (`systemctl restart ssh`)

**Verification after all fixes:**
```
$ fail2ban-client status sshd
Status for the jail: sshd
|- Currently failed: 1
|- Total failed:     1
`- Actions
   |- Currently banned: 0
   |- Total banned:     0

$ /usr/sbin/sshd -T | grep -i 'maxstartup\|persource'
maxstartups 100:30:200
persourcemaxstartups 30
persourcenetblocksize 32:128
```

---

### 3.6 2026-06-27: Unlimited Retry Loop — Corrected Fix

**Symptom:** VS Code Remote-SSH kept retrying a failed connection indefinitely, opening concurrent tunnels ("like a mad man"). Error: `Unauthorized client refused: auth mismatch` on port 17863.

**Wrong fix attempted (2026-06-27 earlier):** Changed `remote.SSH.maxReconnectionAttempts` from `0` to `3`. This made retries WORSE because `0` means "disable reconnection" (with a known bug where the first retry always fires), while `3` means "allow 3 actual reconnection attempts".

**Root cause:**

1. **Auth mismatch:** The remote `.vscode-server` directory on `91.107.165.253` contains a stale connection secret/password that doesn't match the local VS Code client. This is the root error — the SSH transport works, but the VS Code remote server process rejects the tunnel connection.
2. **VS Code resolver loop:** When the remote server returns `auth mismatch`, VS Code treats it as a recoverable error and the resolver enters a retry loop — spawning a new SSH tunnel for each attempt.
3. **Atomic retry bug:** `remote.SSH.maxReconnectionAttempts: 0` has a [known bug](https://github.com/microsoft/vscode-remote-release/issues/8910) where the first reconnection attempt fires before the setting is checked. With `0` this means exactly 1 rogue retry then stop. With `3` this means 4 total attempts.

**Correct fix applied:**

| Layer | Setting | Value | Purpose |
|-------|---------|-------|---------|
| VS Code workspace | `maxReconnectionAttempts` | `0` | Disable reconnection (1 buggy retry then stop) |
| VS Code workspace | `connectTimeout` | `15` | Fail fast per tunnel attempt |
| VS Code workspace | `useLocalServer` | `false` | No local daemon multiplexing |
| VS Code workspace | `useExecServer` | `false` | Fresh remote code-server per window |
| VS Code workspace | `showLoginTerminal` | `true` | Surface SSH debug output |
| VS Code workspace | `enableDynamicForwarding` | `true` | Avoid terminal-width wrapping bug (#5818) |
| SSH all hosts | `ConnectionAttempts` | `1` | Each SSH invocation tries exactly once |
| SSH all hosts | `ConnectTimeout` | `15` | Fail fast per SSH attempt |

**Files modified:**

- `.vscode/settings.json` — all 6 VS Code Remote-SSH settings above
- `%USERPROFILE%\.ssh\config` — `ConnectionAttempts 1`, `ConnectTimeout 15` on all 4 Host blocks

**Recovery command (run this in a terminal):**

```powershell
# Kill the stale VS Code server on the remote host
ssh myserver-proxy "rm -rf ~/.vscode-server"
```

Or from VS Code: `Ctrl+Shift+P` → `Remote-SSH: Kill VS Code Server on Host...` → select `myserver-proxy`.

**Expected behavior after fix:** The initial connection attempt will fail within ~15s (fast). VS Code will fire one unavoidable buggy retry. Then the connection failure is surfaced to the user. No more indefinite retry storms or concurrent tunnels.

---

## 4. Cumulative Changes

### 4.1 Server-Side Changes

| Setting | File | Before | After |
|---------|------|--------|-------|
| MaxStartups | `/etc/ssh/sshd_config` | `#MaxStartups 10:30:100` (default) | `MaxStartups 100:30:200` |
| MaxSessions | `/etc/ssh/sshd_config` | `#MaxSessions 10` (default) | `MaxSessions 50` |
| PerSourceMaxStartups | `/etc/ssh/sshd_config` | not set | `PerSourceMaxStartups 30` |
| fail2ban SSH jail | `/etc/fail2ban/jail.local` | not installed | enabled, maxretry=5, bantime=3600 |
| authorized_keys | `~/.ssh/authorized_keys` | 1 key: `vscode-myserver` | 4 keys (vscode-myserver, ide-ssh, windows-laptop, RSA default) |

**Backups created:**
- `/etc/ssh/sshd_config.backup-` (Jun 4, original)

### 4.2 Local SSH Config Changes

**File:** `%USERPROFILE%\.ssh\config`

**Added aliases:**
```ssh-config
Host myserver-direct
    HostName 91.107.165.253
    User root
    Port 22
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    ProxyCommand none
    ServerAliveInterval 15
    ServerAliveCountMax 3

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

**ControlMaster — added then removed:**
```ssh-config
# Connection sharing — REJECTED (Windows OpenSSH 9.5 incompatibility with ProxyCommand)
# Host *
#     ControlMaster auto
#     ControlPath ~/.ssh/control-%r@%h:%p
#     ControlPersist 15m
```

**Changed settings:**
| Option | Value | Reason |
|--------|-------|--------|
| `ConnectTimeout` | 30 → 15 (in some aliases) | Fail faster when saturated |
| `ServerAliveInterval` | 10–15 | Keep idle sessions alive |

**Backups:**
- `%USERPROFILE%\.ssh\backup-20260623-155306\config` — original config
- `%USERPROFILE%\.ssh\backup-20260623-155306\proxy_fallback.bat` — original script

### 4.3 VS Code Configuration

**File:** `%APPDATA%\Code\User\settings.json`

Added:
```json
{
    "remote.SSH.path": "C:\\Windows\\System32\\OpenSSH\\ssh.exe",
    "remote.SSH.useLocalServer": false,
    "remote.SSH.useExecServer": false,
    "remote.SSH.showLoginTerminal": true,
    "remote.SSH.enableDynamicForwarding": true,
    "remote.SSH.maxReconnectionAttempts": 0,
    "remote.SSH.remotePlatform": {
        "myserver-direct": "linux",
        "myserver-proxy": "linux",
        "myserver": "linux"
    }
}
```

**Key choices:**
- `useLocalServer: false` — prevents VS Code from multiplexing connections through a local daemon, avoiding single-point-of-failure
- `useExecServer: false` — ensures a fresh remote `code-server` per window
- `showLoginTerminal: true` — exposes SSH debug output for troubleshooting
- `maxReconnectionAttempts: 0` — prevents VS Code from repeatedly retrying a failed Remote-SSH connection

### 4.4 SSH Key Management

#### Key Generation History

| Key Name | Fingerprint | Status | Notes |
|----------|-------------|--------|-------|
| `vscode-myserver` | `SHA256:7dn+...` | ✅ Backed up at `key-backup-20260625-094112/` | Original key, works |
| `ide-ssh` | `SHA256:UmUY...` | ❌ Private key lost | Can be deleted from dashboard |
| `windows-laptop` | `SHA256:Y4kp...` | ✅ **Currently active** | Generated 2026-06-25 |

#### Best Practice Adopted

- **One key per device** (not per project). The single `id_ed25519` key on this Windows laptop is added to every server that needs access.
- Keys are labeled with a descriptive comment (e.g., `windows-laptop`).
- Old keys are backed up before replacement.

#### Local Key Backups

```
%USERPROFILE%\.ssh\
├── id_ed25519            ← Current: windows-laptop
├── id_ed25519.pub        ← Current: windows-laptop
├── key-backup-20260625-094112\
│   ├── id_ed25519        ← Old: vscode-myserver
│   └── id_ed25519.pub    ← Old: vscode-myserver
```

#### Server authorized_keys (as of 2026-06-25)

```
SHA256:UmUYYwHk5Jl8mPk+kVyofLa4mhHA2EXgqTX7puHb954 ide-ssh         (from dashboard)
SHA256:7dn+P1qcfTHtwwLz/+QfPuiiq3SJLhkvrl2UnKwjtCU vscode-myserver  (original)
SHA256:Y4kp0ZbEddb9nLaZZGxP+MpiEdnts8dwP5xuxw9ur1M windows-laptop   (current)
SHA256:AmD7Nr0oJDPUveR70Y7MNSGhg9168ZWcbsIkyNOk1QI (RSA default)
```

#### Healthcheck Task

| Property | Value |
|----------|-------|
| Name | `SSH-myserver-healthcheck` |
| Status | ❌ **Disabled** |
| Script | `%USERPROFILE%\.ssh\ssh-healthcheck.ps1` |
| Interval | Was every 5 minutes |
| Re-enable | `Enable-ScheduledTask -TaskName "SSH-myserver-healthcheck"` |

---

## 5. Final Server State

```
$ /usr/sbin/sshd -T | grep -i 'maxstartup\|persource'
maxstartups 100:30:200
persourcemaxstartups 30
persourcenetblocksize 32:128

$ fail2ban-client status sshd
Status for the jail: sshd
|- Currently failed: 1
|- Total failed:     1
`- Actions
   |- Currently banned: 0
   |- Total banned:     0
   `- Banned IP list: (empty so far)
```

---

## 6. How to Use

### Quick Start

```powershell
# Via proxy (SOCKS5) — use this if direct route is blocked
ssh myserver-proxy

# In VS Code: Cmd+Shift+P → Remote-SSH: Connect to Host → myserver-proxy
```

### Which Alias to Use

| Situation | Alias | Notes |
|-----------|-------|-------|
| Normal work (through xray) | `myserver-proxy` | Routes through SOCKS5, requires xray running |
| Direct (no proxy) | `myserver-direct` | Only if firewall allows direct port 22 |
| Original config | `myserver` | Preserved, uses `proxy_fallback.bat` |

### CLI Concurrency Test

```powershell
$j1 = Start-Job -ScriptBlock { ssh -o "BatchMode=yes" myserver-proxy "hostname; sleep 10" }
$j2 = Start-Job -ScriptBlock { ssh -o "BatchMode=yes" myserver-proxy "hostname; sleep 10" }
Start-Sleep 5
Receive-Job $j1
Receive-Job $j2
Remove-Job $j1, $j2
```

### Multi-Root Workspace (Alternative)

File: `C:\Users\cebit.ir\.ssh\reports\remote-workspace.code-workspace`

Contains three folders in a single window:
- `/opt/bots/v2raych`
- `/opt/bots/chat.bimeh`
- `/root/cursor-automation`

---

## 7. Rollback Instructions

### Server-Side Rollback

```bash
# 1. Restore sshd_config from backup
cp -a /etc/ssh/sshd_config.backup- /etc/ssh/sshd_config

# 2. Validate
/usr/sbin/sshd -t

# 3. Restart SSH
systemctl restart ssh

# 4. Remove fail2ban (if desired)
apt remove --purge fail2ban -y

# 5. Remove PerSourceMaxStartups
sed -i '/^PerSourceMaxStartups/d' /etc/ssh/sshd_config
systemctl restart ssh
```

### Local SSH Config Rollback

```powershell
# Option A: Full rollback from backup
Copy-Item "$env:USERPROFILE\.ssh\backup-20260623-155306\config" "$env:USERPROFILE\.ssh\config" -Force

# Option B: Manual edits
# - Remove the three added Host blocks (myserver-direct, myserver-proxy)
# - Remove the commented ControlMaster block
# - Keep only the original two entries
```

### VS Code Settings Rollback

Remove these keys from `%APPDATA%\Code\User\settings.json`:
- `remote.SSH.path`
- `remote.SSH.useLocalServer`
- `remote.SSH.useExecServer`
- `remote.SSH.showLoginTerminal`
- `remote.SSH.enableDynamicForwarding`
- `remote.SSH.maxReconnectionAttempts`

### Re-enable Healthcheck Task

```powershell
Enable-ScheduledTask -TaskName "SSH-myserver-healthcheck"
```

---

## 8. Remaining Risks

1. **fail2ban needs to accumulate bans** — Currently 0 banned IPs. It takes time for repeat offenders to hit the threshold. Until then, scanners may still consume slots.

2. **`ide-ssh` key on provider dashboard** — Can be safely deleted. The private key was lost during key rotation. Both `vscode-myserver` (backed up) and `windows-laptop` (current) are on the server's `authorized_keys`.

3. **Proxy path may be intermittent** — The `myserver-proxy` alias depends on the xray SOCKS5 proxy being running and responsive. If xray is down, no connection is possible.

4. **No ControlMaster** — Connection multiplexing was disabled due to a Windows OpenSSH 9.5 bug. Each VS Code window creates a fully independent TCP connection.

5. **Server IP is publicly exposed** — fail2ban and PerSourceMaxStartups mitigate but don't eliminate the risk. Consider:
   - Cloud firewall ACLs to restrict source IPs
   - Moving SSH to a non-default port
   - fail2ban can be tuned to shorter findtime / lower maxretry

6. **Two-window VS Code test not fully performed** — CLI concurrency is verified, but the final two-window VS Code Remote-SSH test requires human GUI confirmation.

---

## References

- Full diagnostic report: `C:\Users\cebit.ir\.ssh\reports\remote_ssh_concurrency_report.md`
- Server sshd_config backup: `/etc/ssh/sshd_config.backup-`
- Local config backup: `%USERPROFILE%\.ssh\backup-20260623-155306\`
- Local key backup: `%USERPROFILE%\.ssh\key-backup-20260625-094112\`
- Related lab doc: `03-REMOTE-PLAYWRIGHT-LAB.md`
