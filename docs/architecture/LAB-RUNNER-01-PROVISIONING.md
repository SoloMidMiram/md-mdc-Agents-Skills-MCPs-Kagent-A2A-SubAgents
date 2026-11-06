# LAB-RUNNER-01 — Provisioning and independent qualification specification

Prepared 2026-11-06. **Specification only: no runner exists, no infrastructure is provisioned, and model calls remain disabled.** The practical-lab foundation is a review candidate; coding improvement and merge readiness remain on hold. This document is a non-authoritative implementation handoff, not another product roadmap.

## Infrastructure decision record — 2026-11-06

| Field | Decision / actual state |
|---|---|
| Accountable owner | **SoloMidMiram**, assigned by the maintainer in this chat; responsible for provisioning, isolation and teardown |
| Host class | Dedicated ephemeral Linux virtual server, with one fresh VM instance per execution |
| Host identifier | **LAB_RUNNER_HOST** (placeholder); illustrative address `lab-runner.example.invalid` is deliberately non-routable |
| Provider/account/region | **TBD**; no resource or account has been selected or authorized for spending |
| Access and image identity | **TBD**; never substitute this placeholder into a real connection command |
| Authentication/network/isolation | **NOT QUALIFIED**; no access details or independent evidence supplied |
| Non-scored smoke / nine frozen cells | **NOT RUN / BLOCKED**; assigning an owner does not unblock execution |

The virtual-server placeholder was explicitly requested by SoloMidMiram. It is a
documentation value, not a provisioned endpoint. Replace it only after the owner
supplies a real environment and independently verified identities. Do not copy
credentials, account configuration or conversations into this document.

### Separate evidence gates

**Security qualification** must independently demonstrate filesystem denial,
approved model connectivity, denied unapproved networking, credential separation,
launch identity and verified teardown. Its inputs, verifier and actual results
belong in a dated security record.

**Experimental qualification** must demonstrate one real non-scored smoke task,
correlated terminal trace/usage, bounded patch and independent evaluation, followed
by the nine frozen runs. Its task/arm/results belong in separate experimental
records. Neither evidence class substitutes for the other; model calls remain
disabled until security qualification passes. No record is prefilled as successful.

## 1. Deliverable and boundary

Implement one separately reviewed isolated runner and the three pre-pilot harness corrections in a small draft PR stacked on frozen #18, source `caa7d80e8512bc886c98393e322fc3df7f1f8ea2`, tree `9e6630b0c422d928b90216d367605d0f24a27d1a`. Preserve the three tasks, manually selected inputs, condition order, budgets and model configuration. Do not modify #18 or relabel its nine blocked cells as executed.

The current harness has three pre-pilot gaps: launcher JSON is only self-attestation; exit 0 alone marks completion; a clean status does not establish frozen commit/tree identity. These are observed code boundaries, not evidence that blocked runs executed unsafely.

No snapshots, ranked discovery, Context7, kagent, approval receipts, MCP delivery, local-model fallback or automatic integration. Prepared arms compare formatting/provenance of the same manual selections, not automatic source discovery.

## 2. Provisioning contract

Use an independently provisioned ephemeral Linux VM per smoke/subject execution. Initial allocation: two virtual CPUs, 4 GiB RAM and 20 GiB ephemeral storage; this is an initial test allocation, not a performance or pricing claim. Cloud provider, subscription and spending authorization remain the infrastructure owner's responsibility; this specification authorizes no resource creation.

Pin the base image by immutable provider/image identity and digest, initially matching the qualified Ubuntu 26.04.1 environment. Record architecture, kernel, image build, runtime package hashes and CPU/memory allocation. Any change requires qualification before scored runs. VM teardown follows every run, including timeout/failure; a new subject never reuses a previous VM/disk or session.

Separate four trust domains:

1. **Controller:** freezes inputs, creates VM, verifies identities, streams approved input, retains artifacts and enforces lifecycle limits. It never exposes the parent checkout or host home.
2. **Subject VM:** contains only the exported historical source tree, its fresh local Git history, approved prompt/context, pinned read-only runtime and isolated writable temporary area. No host mounts, shared folders, original object packs, SSH agent, metadata credentials, container socket or cloud control-plane identity.
3. **Model/authentication boundary:** a dedicated, independently controlled model-access path holds account credentials outside subject tools. Provision only the minimum session-scoped connectivity needed for the pinned cloud model. Do not copy the full host CODEX_HOME, auth store, config, chats or environment. The chosen supported authentication flow must be demonstrated before qualification; if it cannot separate credentials from untrusted commands, keep execution BLOCKED rather than weaken this contract or silently switch billing/model.
4. **Evaluator:** runs after subject shutdown, outside its VM, with hidden tests/reference fixes/results. It receives the sealed patch and neutral run ID, not the context arm. It evaluates untrusted patches in a separate disposable test environment with no account/cloud credentials and no external network.

Install and freeze dependencies before timing subjects. Pin Codex CLI 0.164.0, model gpt-6.1-sol, medium reasoning, and the Python/Git/dependency identities used by the trial. No automatic upgrades. Record the resolved model identity when available; alias stability is a limitation, not a guaranteed immutable model snapshot. No prior session, user customization, MCP server, web search or repository remote is available. Read-only runtime libraries/tools are allowed; “subject-only” does not mean denying the OS/runtime files needed to execute them.

Default-deny VM egress at a boundary outside subject control. Permit only the approved model-access path; the access path restricts model/account/session scope and request budget. Deny direct Internet, arbitrary HTTP CONNECT, alternative providers, DNS bypass, link-local metadata, private networks, controller/evaluator endpoints and inbound connections. Host/model credential policy must be separately reviewed. Allowed model connectivity must be tested positively; network denial alone is not a working runner.

## 3. Independent qualification

The launcher cannot qualify itself by returning matching JSON. An independently operated verifier supplies unpredictable canaries and executes direct probe programs under the **same UID, mounts, filesystem restrictions, network policy, launcher configuration and dependency image as subject tools**. Prompts asking an agent not to read a file are not probes.

Retain verifier commands, actual exits, sanitized stdout/stderr, expected observations and independent infrastructure evidence. Place canaries representing parent repository, #17 repair, hidden evaluator, other experiments, private host data and unapproved configuration outside the permitted boundary. Prove that each is unreadable using absolute paths, traversal, symlink/hardlink attempts where applicable, environment discovery and available proc/device/mount surfaces. Do not populate the subject with actual private host files merely to test denial. Reject both content access and accidental metadata/credential exposure beyond the declared runtime allowance.

Test network denial with independently controlled endpoints and access-path logs: forbidden public/private/link-local/DNS routes must fail, while the authorized model request succeeds. Include a disallowed model/provider request and a direct bypass attempt. Independently verify no unintended MCP/config loading. Missing tools or an unavailable test endpoint mean NOT RUN/BLOCKED, not a successful denial.

Bind qualification evidence to immutable image/configuration digests, network-policy identity, credential mechanism, CLI/runtime identities, verifier identity/time and a fresh controller nonce. The verifier retains the original evidence outside the runner. The controller accepts evidence only through this independent trust path and checks its binding; a report created by the launcher or a file placed by the subject is not sufficient. Qualify containment independently of model-generated assertions.

Repeat a lightweight live boundary probe on every fresh VM. Image/configuration/network/auth changes, evidence mismatch, failed canary, unavailable verifier or missing teardown evidence block dispatch. No self-attestation fallback.

## 4. Execution identity and terminal validation

Immediately before dispatch, validate all of the following from controller-frozen inputs, not values supplied by the subject:

- Original historical tree is exactly #13 `c6021d456bbcce20fec817470aa5237907d7728a`; fresh local commit and tree equal the prepared run's recorded identities. Clean status alone is insufficient.
- Every tracked path, byte digest and mode matches the frozen export; include tracked paths matching ignore patterns. Reject unexpected files outside the explicit approved input/runtime/temporary allowances, index stages/flags, alternate object stores, grafts/replace refs, extra refs, remotes and injected configuration/hooks.
- Task, prompt, selected excerpts, packet/brief, model/settings, timeout and allowed-path definitions match their frozen digests. Keep allowed input placement identical except for the assigned arm.
- The transferred VM copy matches the controller's copy. Verify again after VM setup and directly at launch; seal/read-protect the input bundle so setup cannot race identity validation. If changes are detected, stop rather than resnapshot silently.

Use one fresh controller nonce per attempt. Bind VM identity, execution ID, neutral cell ID, frozen request digest, subject commit/tree, environment/configuration digests and captured event-channel identity into an immutable controller record. A retry gets a new attempt identity; never overwrite an ambiguous attempt or retry it silently.

Require process exit 0 **and** a valid pinned Codex JSONL execution before calling a run completed. Parse every nonempty stdout line strictly as UTF-8 JSON; retain malformed output and reject instead of dropping it. Require exactly one fresh thread identity, the expected started lifecycle, a nonempty final agent response and exactly one successful terminal completion with well-typed nonnegative usage. Reject missing/duplicate/conflicting completion, any failure event, truncated streams, wrong-thread/resumed sessions, unsupported terminal shapes and usage inconsistencies. Do not invent per-event run/turn IDs that CLI 0.164.0 does not expose: the trusted controller binds the entire stream to the nonce/request/process, and the non-scored smoke freezes the actual emitted schema.

Retain raw JSONL/stderr, final response, usage, monotonic start/end times, process exit and terminal-verification verdict with digests. Invalid terminal output is failed/invalid execution, never a valid empty patch. If process closure is ambiguous, classify it unknown/blocked and reconcile before any retry. On timeout, terminate the complete VM/process tree at 600 seconds, verify cessation and teardown, and retain partial artifacts. Do not treat killing only the controller's child process as proof of subject termination.

Accept patches only from the recorded subject execution. Transfer into a new controller-owned artifact directory; verify inventory, sizes and digests, reject traversal/symlink escapes and out-of-scope paths, and preserve failed exports. Only scripts/context/build_packet.py is an allowed coding change. Modifying tests/configuration or hidden artifacts invalidates scope. Seal artifacts before the independent evaluator consumes them. Completion and test correctness remain separate decisions.

## 5. Qualification sequence and gates

1. Infrastructure owner provisions runner/controller/evaluator and the restricted authentication/network path. Record exact image/config identities and approved access; no source/model run yet.
2. Independently run filesystem/network/configuration adversarial qualification. All required positive and negative controls must actually execute and pass. Publish sanitized proof references, not secrets.
3. Run deterministic harness negatives: forged qualification, stale evidence, clean-but-wrong commit/tree, modified input/index/configuration, transfer races, missing/duplicate terminal events, malformed JSON, failure-plus-exit-zero, usage mismatch, timeout/orphan and teardown/export failure. Each must block completion/scoring.
4. Execute **one non-scored smoke** on a fresh source-only disposable task that does not expose historical fixes or hidden tests. Demonstrate authorized model connectivity, actual pinned CLI/model operation, terminal correlation, a bounded patch, usage capture, external test evaluation and verified teardown. Record smoke charges/usage separately; do not count it among nine cells. If it fails, keep the scored pilot blocked.
5. Obtain independent qualification review, then create a new attempt set for the nine frozen cells. Retain the previous blocked ledger unchanged. Execute sequentially with fresh VMs and ten-minute limits. Preserve counterbalanced order, failed/timeout/invalid cells and unknown billing fields.
6. Score task-specific hidden regressions plus common positive controls. Retain unrelated historical defect results separately; do not require each focused task to repair all three bugs. Report actual patches, correctness, citations/coverage where independently assessed, tokens and preparation/execution/evaluation effort. No API-price estimate is labeled as a ChatGPT account charge.

One execution per cell permits exploratory conclusions only. Do not claim source-discovery quality, generalized coding superiority or cost savings without supporting measurements.

## 6. Reviewable implementation split and handoff

LAB-RUNNER-01 draft should contain: launch identity validator; strict terminal parser/controller binding; replacement of self-attestation acceptance with independent qualification verification; the VM launcher/teardown adapter for the chosen provisioned environment; adversarial tests; and a sanitized qualification/smoke record. Keep OS-specific provisioning outside the context builder. CI runs deterministic validator tests only, never paid smoke/pilot jobs automatically.

Current status: **NOT IMPLEMENTED / NOT QUALIFIED**. SoloMidMiram owns the infrastructure handoff; no infrastructure access has been supplied. No genuine smoke or nine-cell coding result exists. Next required input is a real independently provisioned Linux environment meeting this contract; the exact provider/account/access and credential mechanism must be supplied before deployment code or live qualification can be completed. No cloud spend, resource mutation, reviewer notification or model call is authorized by this specification alone.

Integration remains #16 → #9 → main, followed by reconciliation of the independent #10 → #13 → #17 → #18 stack. New CI results do not promote any PR to merge readiness. This specification leaves #18's protocol/results and all existing PRs unchanged.
