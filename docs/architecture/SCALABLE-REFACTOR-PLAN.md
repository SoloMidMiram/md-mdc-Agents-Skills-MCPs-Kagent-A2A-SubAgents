# Scalable Refactor Plan

This document describes how the repository should evolve so it stays logical as
more runtimes, agents, and validation paths are added.

It is a target architecture, not a claim that every change below is already
implemented.

## Current Structural Problems

### History and current state are mixed

The repo currently uses historical plan documents, implementation notes, and
current runbooks in the same reading path. That makes it hard to answer:

- what works now
- what is only design
- what is old context

### Docs are grouped mostly by chronology

The numbered docs help tell the story of how the repo evolved, but they are not
the cleanest structure for scaling. A larger repo needs purpose-based grouping.

### Deploy assets are not yet runtime-oriented

`deploy/` currently contains a useful starter A2A manifest, but the repo does
not yet make a clear distinction between:

- sample manifests
- reusable base manifests
- environment overlays
- policy constraints

### Validation is spread across multiple concepts

The repo has strong validation scripts, but the user journey still requires too
much manual interpretation to know:

- what to run first
- what constitutes success
- what to do when a component is only partially healthy

## Target Information Architecture

Keep the numbered concept docs, but stop making them the only primary path.
Shift the repository toward this logical model:

```text
docs/
  onboarding/
  runbooks/
  architecture/
  reference/
  archive/
```

Recommended mapping:

- `onboarding/`
  - quick start
  - reading order
  - current implemented state
- `runbooks/`
  - local Playwright lab
  - remote Docker lab
  - local kagent lab
  - troubleshooting
- `architecture/`
  - MCP mental model
  - host and agent model
  - scalable target architecture
- `reference/`
  - config templates
  - host capability matrix
  - version matrix
- `archive/`
  - old plan documents
  - superseded implementation notes

You do not need to move every file immediately. The first scalable step is to
document this target and route new material into it deliberately.

## Target Runtime Model

The repo should be understood as four stacked layers:

### Layer 1: Host configuration

Purpose:

- configure VS Code, Cursor, Codex, Continue
- register MCP servers
- keep user-level templates portable

Current home:

- `config/templates/`
- host-specific docs

### Layer 2: Browser runtime

Purpose:

- local Playwright usage
- remote Docker browser runtime
- browser validation workflows

Current home:

- `docs/02-LOCAL-PLAYWRIGHT-LAB.md`
- `docs/03-REMOTE-PLAYWRIGHT-LAB.md`
- `server/`

### Layer 3: Cluster runtime

Purpose:

- local Kubernetes validation
- `kagent` installation
- A2A agent experiments

Current home:

- `docs/06-LOCAL-KAGENT-A2A-LAB.md`
- `deploy/base/kagent/`

### Layer 4: Validation and operations

Purpose:

- verify configs
- run evaluation suites
- perform health checks
- capture repeatable recovery steps

Current home:

- `scripts/evaluation/`
- `scripts/kubernetes/`
- `scripts/security/`

## Recommended Repository Organization

### Keep as-is

These areas already make sense:

- `.github/`
- `.project-ai/`
- `config/`
- `scripts/`
- `server/`

### Strengthen

These areas need clearer ownership:

- `docs/`
- `deploy/`

### Recommended `deploy/` model

Target structure:

```text
deploy/
  samples/
    kagent/
  base/
    kagent/
  overlays/
    local/
    lab/
  policies/
```

Guideline:

- `samples/` contains educational or starter manifests
- `base/` contains reusable primitives
- `overlays/` contains environment-specific assembly
- `policies/` contains validation and security constraints

Today, `deploy/base/kagent/k8s-a2a-agent.yaml` behaves more like a sample than a
true reusable base asset. If more manifests are added, move this kind of file
into `deploy/samples/kagent/`.

## Refactor Priorities

### Priority 1: Clarify ownership

Add and maintain one source of truth for:

- current implemented state
- current reading path
- current known gaps

That should be `README.md`, `docs/GETTING-STARTED.md`, and
`docs/07-IMPLEMENTED-STATE-AND-ROADMAP.md`.

### Priority 2: Convert runbooks into operations

Add or evolve:

- `docs/operations.md`
- `docs/diagnostics.md`

Use them for:

- validated command sequences
- health checks
- recurring failure signatures
- repair procedures

### Priority 3: Reduce accidental coupling

Avoid forcing every doc to serve all four roles:

- narrative
- status
- operations
- architecture

Each document should do one main job.

### Priority 4: Close the local cluster loop

Before expanding `kagent` scope:

1. get all required local `kagent` pods healthy
2. make the sample A2A agent accepted and ready
3. validate the agent card retrieval path
4. only then add more agents or cross-runtime integrations

## What “Scalable and Logical” Means Here

For this repository, scalable does not mean “more files.” It means:

- current-state docs are easy to find
- historical docs stop blocking understanding
- host setup, browser runtime, cluster runtime, and validation are clearly separated
- sample assets are not mislabeled as reusable base assets
- runbooks describe observed reality, not yesterday's assumptions

## Recommended Sequence

1. Update the current-state docs first.
2. Keep the existing files in place, but add purpose-based routing.
3. Move sample cluster assets into a `samples/` area when more manifests appear.
4. Add operations and diagnostics docs for recurring commands.
5. Archive superseded plan-heavy docs once the current-state path is sufficient.
