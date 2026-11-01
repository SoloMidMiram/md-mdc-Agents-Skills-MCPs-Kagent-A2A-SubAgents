# Contradiction register

This is the traceable correction register, not another roadmap or capability
status index. Code/tests own implementation; pyproject/locks own dependency
inputs; the capability matrix defines evidence; the dated evidence index owns
capability decisions. Different branches and historical observations are not
automatically contradictions. Recheck refs and fresh security data before use.

Review starting state (2026-11-01): main `3c99181`, PR #9 `a53bfb6`, PR #10
`8ff9116`, PR #13 `c6021d4`; all three PRs are open drafts. The security lanes
are based on main and #9 respectively. Formal integration remains issue #11's
maintainer decision. No old evidence record was rewritten.

| ID / severity / category | Previous claim or mismatch, with source | Verified authority / consequence | Correction and validation | Ownership / residual condition |
|---|---|---|---|---|
| SEC-001 High / security | Root `uv.lock` at `3c99181`: msgpack 1.2.1. Prior scan dates cannot certify current cleanliness. | GHSA-j586-36cw-2gc2 affects versions below 1.2.3; current advisory audit identifies the pin. | uv regenerates 1.2.3 with artifact hashes; frozen install and complete-inventory advisory/Trivy scans required. | Main security lane; re-audit at final head and merge. |
| SEC-002 High / security | SDK lock at `a53bfb6`: pyasn1 0.6.4, with four current High advisories. | Reviewed fixes start at 0.6.5; the SDK client qualification remains 0.3.26. | Separate SDK lane changes only pyasn1's version, generates hashes for the 33-pin platform union and enforces installation hashes; SDK tests/typing/audits required. | SDK correction → #9, not main; no root or runtime acceptance implied. |
| SEC-003 High / branch-specific dependency state | Treating the November review's one affected root package on #9 as a complete audit of main would miss older pins. | Current OSV audit of main finds 46 advisory records (37 distinct package/advisory IDs) in six packages: certifi, filelock, msgpack, pip, urllib3, virtualenv. | Main updates those six packages plus required packaging/python-discovery compatibility pins. Unrelated package versions stay fixed; compare inventories before/after. | Main lane only. This is a branch difference, not evidence that the October record was a fresh November scan. |
| CI-001 High / false validation success | `scripts/quality/python-fast.ps1` and `python-full.ps1` at main print PASS after failed native steps. | Failure injection (`uv` exits 7) reproduced exit 0/PASS in both original wrappers. | Fail closed after each native command. Pester checks early stop/no PASS, and success only after all fast steps complete. | Main; no claim that the full wrapper's pre-existing formatting/typing debts are solved. |
| CI-002 Medium / configuration | Full wrapper and `tool.coverage.run.source` refer to absent `src`. CI imports PyYAML without direct dev ownership. | Actual Python code is `scripts/kagent`; workflow YAML validation needs PyYAML. | Correct quality paths/coverage source, retain threshold 80 with precision 2, declare existing PyYAML 6.0.3 directly. Frozen sync and applicable checks verify the inputs. | Main. Existing full-wrapper debt remains explicit, not hidden by a synthetic PASS. |
| CI-003 High / incomplete audit scope | A default Trivy filesystem pass can omit dev dependencies; the SDK `.lock` is not automatically a pip target. | Root has 51 third-party lock records and the local project; SDK now has 33 separate platform-union pins. No-applicable-package scans cannot establish security. | Main required scan includes dev deps; both lanes add inventory-checked advisory gates. SDK installation requires generated hashes. Original scanners/exit policy remain active. | Root and SDK CI lanes respectively; do not advertise global baseline acceptance from one lane's green job. |
| CI-004 Medium / Windows reproducibility | Main benchmark contracts anchor LF-only skill metadata and reject valid CRLF checkouts. | Two Windows failures reproduce against unchanged skills; #9 already has exact LF/CRLF contract repairs. | Port only those two test repairs, including 28 positive/negative cases per suite; reject suffixes and false/manual flags as before. | Main; this imports no SDK or educational feature. |
| CI-005 Medium / tool-version selection | Evaluation runner imports latest Pester despite CI installing and selecting 5.7.1. | Local Pester 6.2.0 triggers an incompatible assembly error after 5.7.1 is loaded, while the runner still exits 0. | Pin availability, install and import paths to CI's existing 5.7.1 on both lanes; rerun with 6.2.0 also installed and inspect stderr. | Shared evaluation runner; optional host skips remain unverified, never runtime passes. |
| SEC-004 Medium / platform dependency integrity | SDK lock compiled only for Linux omits pytest's Windows-only colorama dependency. | Exact Windows installation succeeds but `uv pip check` reports missing colorama. | Regenerate with uv's universal resolver and hashes; retain 31 other versions and add colorama 0.4.6 under the Windows marker. Audit the full 33-pin union on every host. | SDK lane; CPython 3.13.15: 32 installed on Linux, 33 on Windows. PyPy is not qualified. |
| DOC-001 Medium / stale capability claim | Main README plans L4 delivery and deployment of a lightweight server; release-plan row equates REST card discovery with A2A dispatch. | Main evidence index already records historical L4/L5; matrix distinguishes card metadata, dispatch and L6 agent-mediated tools. | Link canonical dated evidence, use qualified `message/stream` terminology and describe L6 as unproven. No new observation is invented. | README and stable acceptance plan on main. Historical phase files unchanged. |
| DOC-002 Low / tooling contradiction | `constraints.md` says Black/isort/Ruff hooks are enforced; actual pre-commit config uses Ruff hooks. It also says no lab CI dependency while offline helpers have CI jobs. | `.pre-commit-config.yaml` and `.github/workflows/quality.yml`. | Correct tool names and distinguish offline lab tests from a forbidden live-cluster CI dependency. | Identical correction in both security lanes for clean later integration. |
| DOC-003 Medium / publication versus acceptance | #9 roadmaps still call integration a local rehearsal; PR description says hosted CI pending, though publication and exact-head runs exist. | GitHub #9 at `a53bfb6` is published/open/draft, with successful October 25 jobs and renewed security findings. | SDK-lane current-document addendum and GitHub summaries distinguish published source, historical CI, current security qualification and missing runtime proof. | #9 / RECON-01. No undraft/merge or inherited-PR closure occurs automatically. |
| ORG-001 Low / ownership and branch context | Main lacks North Star, integration crosswalk, LAB-01 and context-builder files that exist only in unmerged branches. | Actual ancestry: main → #9 → #10 → #13; #3–#8 heads are included in #9. | Keep two narrow security PRs; do not copy the integration into main. This register lives on main; SDK docs link to it rather than creating another register. Existing IDs are retained. | Maintainer-controlled integration, with native clean-clone qualification. |
| CTX-001 High/Medium / separately owned correctness | #13's Unicode line splitting, index-flag dirty-file check and Windows stdout behavior fail 14 retained external regressions. | November acceptance review at `c6021d4`; current issue #12 owns corrections. | Record the defects and preserve separate remediation; security lanes do not modify the builder or claim its acceptance. | #12 / #13. CTX-02 and EVAL-01 remain gated. |
| FUT-001 Informational / unsupported promotion risk | A green CI/security PR can be misread as live Context7/A2A/Kagent/worker or production approval. | Capability definitions require independent dated runtime observations; SDK-native 1.0 differs from educational 1.1. | Keep historically demonstrated, freshly audited, implemented/offline-only, blocked, proposed and not-attempted claims separate in current docs and handoff. | No live operation performed here. L6/L7/I3/I4 and live SDK remain unqualified. |

## How to maintain this register

For a new contradiction record the branch/revision and exact source location,
the claimed fact, the independently inspected authority, the consequence, the
correction and the validating command/artifact. Mark real defects separately
from differently scoped/historical statements. Preserve original dated evidence;
correct its current interpretation at its canonical owner. Do not add a second
milestone numbering scheme or infer runtime approval from document synchronization.

Use the [dependency security runbook](../runbooks/dependency-security.md) for
reproducible qualification, and issue #11 for integration disposition. The
qualification record under `reports/security/` records input hashes, package
inventories and actual results; PR bodies record final-head CI URLs. Those
observations expire and must be refreshed before merge rather than becoming a
permanent claim of zero vulnerabilities.

## Retained starting-source references

The links below anchor the original claims to immutable revisions. Line numbers
refer to Git source rather than platform-dependent CRLF bytes. The qualification
record [main-20261101](../../reports/security/main-20261101.json) records commands,
input hashes and outcomes; the SDK PR supplies its separate record and final CI.

- SEC-001: [uv.lock:79](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/blob/3c99181d187262d6464bfbcd257852485eb712f1/uv.lock#L79).
- SEC-002 / SEC-004: [scripts/kagent/experiments/a2a_sdk_requirements.lock:55](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/blob/a53bfb62f0421a7c28234f871af2bf449a11491f/scripts/kagent/experiments/a2a_sdk_requirements.lock#L55).
- CI-001: [scripts/quality/python-fast.ps1:9](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/blob/3c99181d187262d6464bfbcd257852485eb712f1/scripts/quality/python-fast.ps1#L9).
- CI-002: [pyproject.toml:48](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/blob/3c99181d187262d6464bfbcd257852485eb712f1/pyproject.toml#L48).
- CI-003: [scripts/security/scan.ps1:35](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/blob/3c99181d187262d6464bfbcd257852485eb712f1/scripts/security/scan.ps1#L35).
- CI-004: [tests/benchmark/AgentGovernanceSkills.Tests.ps1:49](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/blob/3c99181d187262d6464bfbcd257852485eb712f1/tests/benchmark/AgentGovernanceSkills.Tests.ps1#L49).
- CI-005: [scripts/evaluation/run-evaluation.ps1:82](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/blob/3c99181d187262d6464bfbcd257852485eb712f1/scripts/evaluation/run-evaluation.ps1#L82).
- DOC-002: [constraints.md:25](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/blob/3c99181d187262d6464bfbcd257852485eb712f1/constraints.md#L25).
- DOC-003: [docs/north-star.md:4](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/blob/a53bfb62f0421a7c28234f871af2bf449a11491f/docs/north-star.md#L4).
