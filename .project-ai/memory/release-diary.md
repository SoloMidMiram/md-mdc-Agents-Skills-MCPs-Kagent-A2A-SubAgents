# Release Diary

Record release outcomes, notable changes, and lessons learned.

---

## 2026-06-24 — Initial Repository Scaffold

**Version:** 0.1.0
**Notable changes:**
- Established project structure with agent customization files
- Added Python tool stack (uv, ruff, pytest, mypy)
- Added Kubernetes validation tooling (kubeconform, kube-linter)
- Documented in README.md and GETTING-STARTED.md

---

## 2026-07-09 — laptop-stable v0.1

**Version:** laptop-stable-v0.1
**Release commit:** cdb7dc0
**Notable changes:**
- Global Playwright MCP installer passes production-path Pester suite (73/73 passed, 0 failed)
- Full round-trip verified: install → verify (exit 0) → rollback → verify (exit 1)
- CI workflow configured: JSON validation, PSScriptAnalyzer, integration scaffold, Pester -CI
- Local kagent lab documented but not yet release-gated
- Recorded in docs/laptop-stable-acceptance-plan.md and docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md

---

## 2026-07-10 — laptop-stable v0.1.1 (pending)

**Version:** laptop-stable-v0.1.1
**Release commit:** TBD — after CI pass
**Status:** PENDING — local gates pass; CI verification in progress

**Notable changes:**
- Fixed UTF-16 encoding in onboarding docs → UTF-8 (HEAD had 7k+ NUL bytes)
- Acceptance plan: honest `READY_FOR_PATCH_TAG` status; v0.1 historical at `cdb7dc0`
- README: Current State notes both tags; stub naming `0x-*` → `01-*`–`07-*`
- Added bridge manifests: GLOSSARY.md, REPO_MANIFEST.yaml, constraints.md
- Removed deprecated `ruff.lint.run` from `.vscode/settings.json`
- Removed stale "encoding artifacts" note from IMPLEMENTED-STATE-AND-ROADMAP.md
