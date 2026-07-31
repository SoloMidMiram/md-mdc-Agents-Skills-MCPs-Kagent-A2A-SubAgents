---
name: review-kagent-capability
description: >
  Classify capability claims in kagent evidence, code, and documentation
  as Proven, Not proven, Blocked, or Not attempted per the capability matrix.
  Use when reviewing or proposing a kagent L0-L7 status change, evidence
  addendum, health-profile claim, or agent-mediated MCP promotion.
disable-model-invocation: true
---

# Review kagent Capability Claims

## Purpose
Classify L0-L7 claims found in kagent evidence records, code, and documentation against the canonical capability matrix. This skill is a manual governance gate -- it does not run automatically.

## Prerequisites
- Access to the evidence record(s) under review.
- Familiarity with the canonical definitions in `docs/reference/kagent-capability-matrix.md`.
- Current status index at `evidence/kagent/README.md`.

## Procedure

### 1. Gather source material
- Collect all evidence records, documentation sections, and code comments that make a capability claim.
- Open `docs/reference/kagent-capability-matrix.md` for the L0-L7 definitions and promotion rules.
- Open `evidence/kagent/README.md` for the current verified status and open flaws.
- Inspect the relevant producer, consumer, schema, and tests when a structured
  evidence object is part of the claim.
- Inspect the Git diff or history before calling a historical record edited.

### 2. Classify each claim
For each claim found, determine which level (L0-L7) it pertains to and classify:

| Classification | Meaning |
|----------------|---------|
| **Proven** | Qualifying evidence exists and meets the capability-matrix criteria |
| **Not proven** | No qualifying evidence, or available evidence fails the required criteria |
| **Blocked** | A known obstruction prevents evidence collection (record the blocker) |
| **Not attempted** | No evidence collection has been attempted |

### 3. Apply promotion rules from the capability matrix
- Direct MCP initialize/call is **not** L6 evidence.
- L5 (RemoteMCPServer accepted) is **not** L6 evidence.
- A health-profile pass does not replace a dated live promotion review.
- L6 requires: same taskId/requestId, server=kagent-tool-server, tool=k8s_get_resources, arguments=pod/kagent, same-task returned resource names, bounded source proof, kubectl match.

### 4. Flag violations
- **False promotions** -- a claim that uses direct MCP evidence for L6, or L5 acceptance for L6.
- **Edited evidence** -- a historical observation changed in the reviewed diff
  instead of receiving a dated addendum.
- **Missing non-claims** -- a document that makes a capability statement without listing what it does not prove.
- **Contradictory evidence** -- identifiers, timestamps, target data, exit
  decisions, or source content disagree.

### 5. Output a structured finding
Write JSON that follows this versioned contract:

```json
{
  "schemaVersion": "1.0",
  "review": {
    "scope": "path or bounded review scope",
    "observedAt": "2026-07-23T00:00:00Z",
    "claims": [
      {
        "level": "L6",
        "claim": "claim text",
        "classification": "Not proven",
        "sources": ["path and section or line"],
        "rationale": "why the evidence does or does not qualify",
        "promotionCriteriaChecked": true
      }
    ],
    "hardFindings": [],
    "softObservations": [],
    "verdict": {
      "claimsChecked": 1,
      "proven": 0,
      "notProven": 1,
      "blocked": 0,
      "notAttempted": 0,
      "currentStatusChanged": false,
      "summary": "Concise conclusion and explicit non-claims."
    }
  }
}
```

Run the bundled structural validator before presenting the review:

```powershell
pwsh -NoProfile -File `
  .agents/skills/review-kagent-capability/scripts/validate-review.ps1 `
  -Path <review.json>
```

The validator checks shape and count consistency. It does not decide whether
the cited evidence is truthful; that remains the reviewer's responsibility.

## Exit criteria
- Every capability claim is classified.
- False promotions are zero (hard gate).
- Each finding includes a reference to the specific evidence or text.
- Current status is changed only by qualifying evidence and a separate
  promotion decision.
- The review does not modify any evidence record.
- The bundled validator exits `0`; exit `2` means malformed or contradictory
  review structure.

## What this skill does NOT do
- Execute live kagent commands or attempt L6 evidence collection.
- Edit evidence records or documentation.
- Update the canonical status index (`evidence/kagent/README.md`).
- Replace a manual promotion review by a human.
