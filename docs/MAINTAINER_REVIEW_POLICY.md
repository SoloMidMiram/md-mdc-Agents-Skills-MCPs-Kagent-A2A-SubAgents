# Solo-Maintainer Review and Merge Policy

SoloMidMiram is the sole human maintainer and final authority for source merges. For ordinary source integration, the owner’s recorded acceptance satisfies the maintainer sign-off. A second human reviewer is optional.

## Technical review and verification

1. Inspect the current diff, head SHA, target branch, dependencies, and proposed merge order.
2. Obtain a technical assessment from a separate AI review session or applicable automated review tools. AI feedback is advisory technical evidence. Record GitHub review states separately.
3. Resolve material findings or document their disposition and rationale. Verify applicable tests, security checks, and CI for the integration candidate. Missing required evidence blocks acceptance.
4. Record the PR number, reviewed head SHA, target branch, CI or validation evidence, findings and their disposition, residual risks, and the owner’s decision with rationale. Revalidate affected evidence if the head or integration target changes.

## Owner decision

- **ACCEPT FOR SOURCE MERGE** means the applicable source-integration requirements are satisfied and the owner authorizes merging the recorded candidate.
- **REVISE** means material findings require changes.
- **BLOCKED** means a required verification, security, or integration condition remains open.

Agents should prepare an evidence-based recommendation and identify actual blockers. When this policy applies, continue the acceptance assessment with the available technical evidence and route the decision to the owner. Agents require explicit owner authorization to merge.

## Operational authorization and qualification

Deployment, live network operations, credential use, cloud spending, security qualification, capability promotion, and production release retain their own requirements. Required technical evidence remains mandatory for each applicable gate.

Runner isolation and security qualification, live A2A execution, and capability promotion retain their applicable evidence and authorization requirements. A documentation-only runner PR can be accepted for source integration while runner qualification is pending.
