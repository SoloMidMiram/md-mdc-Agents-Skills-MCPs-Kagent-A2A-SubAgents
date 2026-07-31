# B05: Audit manifest and commit grouping

## Scenario
A new file was added: `docs/runbooks/kagent-advanced-troubleshooting.md`. It is not listed in `REPO_MANIFEST.yaml`. Additionally, the existing entry for `docs/runbooks/local-kagent-a2a-lab.md` appears twice in the manifest with different `authority` values.

## Files
- `docs/runbooks/kagent-advanced-troubleshooting.md` -- not in manifest
- `REPO_MANIFEST.yaml` -- contains a duplicate entry for `docs/runbooks/local-kagent-a2a-lab.md`

## Task
Identify the manifest issues and propose the correct fix. What must be done before committing?
