# v0.1.0 offline replay evidence

On November 20, 2026, fresh direct HTTPS checkouts on Windows and Ubuntu WSL
replayed candidate `6e09bce113fead7e30e9be1e8a55eb72b163c649` (tree
`928259389df92027fa61dbaa1054cbb07e1e1e5e`). The expected approvals and
intentional rejections all matched, the full parsed reports were equal within
each OS and across both OSes, and both focused test groups passed after
correcting the test invocation.

| Environment | OS | Git | uv | Project Python |
| --- | --- | --- | --- | --- |
| Windows | Windows 11 build 26300, AMD64 | 2.56.1.windows.1 | 0.13.8 | 3.13.15 |
| WSL | Ubuntu 26.04 LTS on WSL2, Linux 6.18.58.1, x86_64 | 2.53.0 | 0.12.18 | 3.13.15 |

Both checkouts verified HEAD, the tree and the committed `uv.lock`. Both
`uv sync --frozen --group dev --python 3.13.15` commands exited 0. Each lab
ran twice using `uv run --no-sync --offline`. The checkouts were clean before
and after replay. The dedicated temp root contained no EDU-03 worker or
evaluator directories immediately after each invocation.

[Windows transcript](transcripts/windows-2026-11-20.txt) ·
[WSL transcript](transcripts/wsl-2026-11-20.txt)

## Command outcomes

The table omits the common `uv run --no-sync --offline` prefix. Lab exit
codes show both attempts on each platform.

| Command | Windows exits | WSL exits | Expected and observed |
| --- | --- | --- | --- |
| `python -m scripts.kagent.experiments.edu02_lab` | 0, 0 | 0, 0 | Approved after one revision |
| `python -m scripts.kagent.experiments.edu02_lab --case broken` | 0, 0 | 0, 0 | Rejected after one revision |
| `python -m scripts.kagent.experiments.edu02_lab --case fixed` | 0, 0 | 0, 0 | Approved with zero revisions and findings |
| `python -m scripts.kagent.experiments.edu03_lab` | 0, 0 | 0, 0 | Correct patch approved. Misleading patch rejected after one revision |
| `python -m scripts.kagent.experiments.edu03_lab --case misleading` | 0, 0 | 0, 0 | Rejected after one revision. Visible check passed. Both held-out nonmember checks failed |
| `python -m pytest -q` with the EDU-02 lab, docs bundle and E2-R test files | 0 | 0 | 81 passed on each OS |
| `python -m pytest -q tests/kagent/experiments/test_edu03_lab.py` | 0 | 0 | 21 passed on each OS |

## Deviations and disposition

| Observation | Classification and resolution |
| --- | --- |
| The pasted `uv run pytest` commands exited 2 on both OSes with `ModuleNotFoundError: No module named 'scripts'` during collection. | Release-blocking command defect, cleared by replaying the runbooks' `python -m pytest` form on both OSes. Keep the module entry point in the quickstart. |
| An initial Windows probe could not resolve GitHub. The subsequent direct Windows HTTPS clone succeeded. | Transient host DNS failure. No Git bundle or host configuration change was needed. |
| An initial WSL wrapper had PowerShell quoting errors. A subsequent non-login Bash wrapper did not find `uv` on PATH. | Replay wrapper errors. Invoke Bash with intact arguments and make the installed WSL `uv` available to the shell. The README states the PATH prerequisite. |
| An initial cleanup check counted non-fixture entries in the command temp root. | Replay instrumentation error. The corrected check verifies the actual `edu03-worker-*` and `edu03-evaluator-*` directory prefixes after each invocation on both systems. |

The focused replay exposed no inherited debt affecting the release path.
EDU-03 demonstrates deterministic patch custody and independent evaluation of
its synthetic fixture. Its disposable directories provide no evidence of
adversarial isolation or native runner teardown.

## R1 evidence and owner gates

| Criterion | Evidence or status |
| --- | --- |
| Merged EDU-01 provenance | [PR #33](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/pull/33), merge `78bb511`, is an ancestor of the candidate. Issues [#27–#32](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/issues?q=is%3Aissue+is%3Aclosed+EDU-01) were verified closed as completed. The pinned SDK job exercises protocol loopback and related controls. |
| Merged EDU-02 and EDU-03 provenance | [PR #46](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/pull/46) at merge `55efe3d` and [PR #48](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/pull/48) at merge `d5448ea` are candidate ancestors. [#36](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/issues/36) and [#37](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/issues/37) were verified closed as completed. |
| Fresh Windows and WSL replay | Passing commands, parsed outcomes, transcripts and limitations above. |
| Learner quickstart and Phase 2 disposition | [README](../../../README.md#offline-a2a-practice) and [ADR 0001](../../adr/0001-phase2-disposition.md), pending maintainer acceptance. |
| Hosted Quality and technical review | [Candidate push run 44684235728](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/actions/runs/44684235728) verified at the exact replay SHA, 5/5 jobs passed. The acceptance branch needs its own exact-head Quality and technical review. |
| Maintainer acceptance, tag and release notes | Pending recorded source-merge approval and separate approval of the release candidate, tag and [draft release notes](release-notes.md). |
