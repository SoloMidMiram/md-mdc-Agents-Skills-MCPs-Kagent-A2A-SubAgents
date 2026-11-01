# Dependency security qualification

This runbook owns dependency audit procedures. It does not own runtime capability
decisions: use the branch's `evidence/kagent/README.md` and capability matrix.
Record observation times, input hashes, scanner versions and advisory/database
freshness. A historical clean scan is not current acceptance.

## Branch and environment boundaries

- Main at `3c99181d187262d6464bfbcd257852485eb712f1` has only the root environment.
  Its security correction is `fix/main-dependency-security-202611` → main.
- The unmerged PR #9 candidate at `a53bfb62f0421a7c28234f871af2bf449a11491f`
  additionally owns the isolated SDK. Its correction is
  `fix/a2a-sdk-dependency-security-202611` → `integration/pub-01-qualified-a2a`.
- SDK 0.3.26, its Python 3.13.15 runtime and its test dependencies stay outside
  the root environment. The SDK branch's inherited root pin still requires the
  separate main correction before the whole integration can be accepted.
- PR #10's dated evidence stays unchanged. PR #13 requires parent-replay and its
  separate correctness fixes under issue #12; security fixes do not establish
  correct context citations or authorize CTX-02/EVAL-01/live A2A.

These SHAs describe the reviewed starting topology, not an assertion that they
are forever the newest refs. Refresh GitHub and Git before integration. Issue
#11 owns the maintainer's reconciliation and disposition decisions.

## Root lock and complete advisory inventory

Use uv 0.7.22 for the qualified lock-generation process, Python >=3.12 and the
declared dev group. The root lock contains 51 third-party packages plus the
explicit local project record. Audit every third-party record, even if it is
only a development dependency or is not installed on the current platform.

```powershell
uv sync --frozen --group dev
uv pip check --python .venv/Scripts/python.exe
uv run python scripts/security/audit_dependencies.py --uv-lock uv.lock --service osv --output ../root-audit.json
pwsh -NoProfile -File scripts/security/scan.ps1 -Required
```

On Linux use `.venv/bin/python` for the integrity command. Use a new output path
for each audit; existing artifacts are never overwritten. The audit command
recomputes the expected inventory from the lock, runs pip-audit without dependency
resolution/installation, and rejects missing, extra, skipped or changed versions
and inconsistent scanner exits. The local project is separately accounted for;
other non-registry sources require explicit qualification rather than silent
omission. Service errors exit nonzero and do not establish an audit.

The additional advisory gate is OSV for the root and PyPI for the SDK. Both are
live service queries, not Trivy database snapshots. `working_file_sha256` hashes
the actual input bytes; use Git blob hashes separately when comparing LF and
CRLF checkouts. CI retains the complete result as an artifact.

Main's corrected required Trivy policy includes development dependencies and
retains vulnerability, secret and misconfiguration scanners. The existing SDK
integration's required filesystem policy remains at its original scope until
the main correction is integrated; its explicit SDK advisory gate covers the
otherwise unmapped lock. Do not describe either lane as qualifying the other.
Keep path-scoped exceptions and severity/exit enforcement intact. Upstream image
scans are advisory, not a claim of zero image vulnerabilities.

## SDK lock, when present on the integration branch

Provision an external environment with Python **3.13.15**. The lock is compiled
universally for Python 3.13, with explicit Windows/CPython markers. Qualify
both Windows and Linux rather than inferring one platform from the other. From a root development environment that has
pip-audit installed, audit the SDK text without installing it into root:

```bash
uv pip compile --universal --python-version 3.13 \
  scripts/kagent/experiments/a2a_sdk_requirements.in \
  --output-file scripts/kagent/experiments/a2a_sdk_requirements.lock \
  --upgrade-package pyasn1==0.6.5 --generate-hashes
uv venv --python 3.13.15 "$SDK_ENV"
uv pip sync --require-hashes --python "$SDK_ENV/bin/python" \
  scripts/kagent/experiments/a2a_sdk_requirements.lock
uv pip check --python "$SDK_ENV/bin/python"
uv run python scripts/security/audit_dependencies.py \
  --requirements scripts/kagent/experiments/a2a_sdk_requirements.lock \
  --service pypi --output ../sdk-audit.json
```

Set `SDK_ENV` to a new external directory before running these commands. On
Windows use its `Scripts/python.exe`. Do not clear or repurpose an existing
qualified environment. The lock contains 33 platform-union pins (32 installed on CPython Linux; 33 on
Windows), including Windows-only colorama 0.4.6. All applicable versions must
match the reviewed lock; installation
must enforce its generated artifact hashes. The only SDK package-version change
in this lane is pyasn1 0.6.4 → 0.6.5; the other 31 pins stay fixed. Universal generation adds only Windows-specific
colorama 0.4.6, fixing the previously incomplete Windows installation.

Run all four `test_a2a_sdk_*.py` modules using that interpreter, with no skips,
and strict typing with its real SDK dependency types. Preserve the root/SDK CI
partition. Do not convert SDK-native evidence 1.0 into educational schema 1.1 by
changing a version string or synthesizing missing observations.

For an independent Trivy SDK scan, explicitly map the lock to the pip analyzer:

```bash
trivy fs --scanners vuln --file-patterns 'pip:(^|/)a2a_sdk_requirements\.lock$' \
  --list-all-pkgs --exit-code 1 scripts/kagent/experiments/a2a_sdk_requirements.lock
```

Compare the returned package inventory with all 33 platform-union pins. A scanner reporting no
findings after recognizing no applicable packages is not qualification.

## Freshness, corrections and handoff

If Trivy cannot fetch its approved database, retain the failure and leave that
gate unverified. Never relabel an older cache as current. Record UpdatedAt,
NextUpdate, download time and DB SHA-256 for accepted local results. Do not
disable TLS verification or ignore advisories to obtain a pass. A working
existing proxy may be used per process without changing global configuration.

Qualify local checks, commit the scoped corrections, then require successful
exact-head hosted jobs. A new commit needs new CI evidence. Clean-clone replay
must not depend on untracked files or a Windows worktree pointer interpreted
by Linux Git; use native Git checkouts with required history.

Security approval, source integration, stable release and live runtime approval
remain separate. No merge, local-model invocation, deployment, provider request
or capability promotion follows from these audit commands. Reverting a security
lock correction restores known affected pins; rollback requires a maintainer
decision and renewed qualification, not automatic acceptance of the old scan.
