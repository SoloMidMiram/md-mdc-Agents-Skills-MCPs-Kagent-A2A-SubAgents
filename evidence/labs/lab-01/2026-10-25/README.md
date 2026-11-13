# LAB-01 retained result — 2026-10-25

**PASS with isolation qualifications**, independently graded on all nine rubric
criteria. This is one offline behavioral assessment, not fresh runtime evidence
or proof of general model reliability. L6 remains Not proven.

## Source and execution

The original checkout was `F:/Git/MCPtest`. `git ls-remote --heads origin
integration/pub-01-qualified-a2a` found the branch. Explicit fetch
`git fetch origin refs/heads/integration/pub-01-qualified-a2a:refs/remotes/origin/integration/pub-01-qualified-a2a`
succeeded. `git rev-parse origin/integration/pub-01-qualified-a2a^{commit}` resolved
`a53bfb62f0421a7c28234f871af2bf449a11491f`. `git worktree add --detach
../agent-labs a53bfb62f0421a7c28234f871af2bf449a11491f` created `F:/Git/agent-labs`;
`git status --porcelain` was empty before the exercise and before publication
files were added. Missing local remote-tracking refs had not implied remote absence.

[Captured commands](command-results.json) retain exact argv, exits, stdout and
stderr for revision, clean-state, repeated remote query and helper validation.
The initial baseline setup commands above are a session record, not a complete
raw terminal transcript. Both the initial helper run (0.29s) and captured repeat
(0.11s) passed 78 tests. Dependency installation used uv's frozen dev environment,
CPython 3.14.3 on Windows. No live A2A/MCP/controller/cluster request was made.

## Retained artifacts

- [Exact assessment prompts and exposure conditions](prompts.json).
- [Full primary answer and subject-reported command list](subject-answer.md).
- [Fresh success-only direct-MCP negative-control answer](negative-control-answer.md).
- [Independent evaluator verdict, criterion grades and citation audit](evaluator-verdict.md).
- [Source revision and SHA-256 manifest](source-manifest.json), with exact Git
  source bytes under `sources/`. The evaluator verified all six hashes.

The primary subject (`lab01_subject`), fresh negative subject (`lab01_negative`)
and evaluator (`lab01_evaluator`) were separate subagents. The latter two started
without inherited conversation. The exact model build/settings were inherited
from the host and were not independently recorded; this limits reproducibility.
Local absolute links in the verbatim answer preserve the original response.
Portable immutable sources are available at
[the pinned source tree](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/tree/a53bfb62f0421a7c28234f871af2bf449a11491f).

## Evaluation limits and errata

The primary prompt states the expected outcome and its broad repository search
exposed incidental benchmark/scoring snippets. It is not a blind evaluation.
The fresh negative subject received definitions and only successful direct-call
facts, with the source's explicit non-claims withheld. It correctly rejected L6
promotion because the same-task A2A → agent → tool → returned-result chain was absent.

The evaluator found no substantive unsupported capability claim or citation error.
One wording issue is retained rather than silently corrected: the primary's
SSE excerpt “independently show” wording describes corroboration within the same
historical record, not independent replication. Config/model-prose exclusions
are semantically covered by its proof requirements, not individually enumerated.

The complete subject tool transcript and a machine-verifiable isolation trace
were not retained. The primary's two HEAD checks are self-reported; captured
commands independently corroborate one clean revision snapshot. These limits and
all nine grades remain in the full evaluator verdict. No result is promoted to
L6, I3, I4, L7, or an A/B coding-improvement claim.

## Reuse

Use this manual source set as CTX-01's first fixture. Its automatic packet must
preserve revision, excerpts/citations, declared claims, unknowns and exclusions.
EVAL-01 can then compare manual and generated context on the same task. The rest
of the backlog stays proposed until the builder interface is tested.

See the [lab guide](../../../../docs/runbooks/lab-01-l4-versus-l6.md) and
[proposed roadmap](../../../../docs/onboarding/PRACTICAL-AGENT-LABS.md).
