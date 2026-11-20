# v0.1.0 · Offline A2A practice

Draft for maintainer approval.

- **Synthetic educational evidence.** EDU-02 demonstrates offline documentation
  review, revision and rejection. EDU-03 demonstrates deterministic patch custody
  and independent evaluation of a checked-in coding fixture. Fresh Windows and
  Ubuntu WSL runs matched, including the intentional rejection cases.
- **Observed protocol behavior.** The pinned A2A SDK tests exercised protocol
  loopback in hosted Quality.
- **Unproven runtime capabilities.** Live delegation to a model-backed coding
  worker, real patch correctness, adversarial isolation and native runner
  teardown remain unverified. The release does not qualify #20 or contribute
  results to EVAL-01.

During fresh-checkout validation, `uv run --no-sync --offline pytest` exited
with code 2 because collection could not import the repository's `scripts`
namespace. Run tests from the repository root using
`uv run --no-sync --offline python -m pytest`, the verified invocation on Windows
and Ubuntu WSL.

Start with the [offline quickstart](../../../README.md#offline-a2a-practice).
See the [replay evidence](replay-evidence.md) for the candidate, commands,
observed outcomes and limitations.
