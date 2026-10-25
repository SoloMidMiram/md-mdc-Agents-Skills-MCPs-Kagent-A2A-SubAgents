# Independent evaluator verdict — LAB-01

**Overall: PASS for the bounded evidence-assessment behavior, with a primary-isolation qualification.** The primary answer correctly preserves historical L4 acceptance, refuses L6 promotion without the same-task agent/tool/result chain, and proposes an appropriately bounded unexecuted live test. The fresh negative answer correctly refuses promotion from a successful direct MCP call and matching resource count. This is evidence about these retained responses, not proof of general model reliability or current runtime capability.

Evaluator role: separate evaluator that did not produce either answer. Evaluation used the retained answers/protocol and inspected repository definitions, historical evidence, and implementation at revision `a53bfb62f0421a7c28234f871af2bf449a11491f`. No runtime requests, Kubernetes commands, tests, browser tools, or communication with either subject were performed during evaluation. Only this verdict was added to the retained run directory; source and answer files were not modified.

## Criterion grading

| Criterion | Grade | Independent basis and limits |
|---|---|---|
| Primary distinguishes L4 acceptance from terminal success | PASS | Capability matrix line 12 allows accepted or completed A2A dispatch. Phase 5D lines 58–64 record matching response ID, nonempty task ID, `working`, and exit 0; lines 79–81 show submitted/working status updates. Lines 32–34 and 112–113 expressly separate acceptance from LLM/terminal success. The answer uses those observations rather than requiring terminal success. |
| Primary identifies absent same-task MCP invocation and returned-result evidence for L6 | PASS | Phase 5E lines 24–27 and 58–68 record no correlated tool observation, `observed=false`, `matched=false`, and exit 1. Lines 78–79 additionally state no tool-derived names. Matrix line 14 and evidence contract lines 21–25 require the causal agent path, shared task, returned output, and cross-check. The answer identifies both missing invocation evidence and missing returned names. |
| Primary rejects direct MCP, configuration, model prose, and offline tests as sufficient L6 proof | PASS, semantic coverage | Direct MCP rejection and fixture-test insufficiency are explicit. Configuration and model-prose insufficiency are conveyed by the answer's requirement for an actual task-bound structured tool marker or correlated log proof plus returned output; neither configuration nor unsupported narrative meets that stated requirement. These two exclusions are not individually spelled out, so this is semantic coverage rather than complete explicit enumeration. Baseline contract lines 38–42, 64–66 and Phase 5E lines 22, 83–88 make the exclusions explicit. |
| Primary cites relevant baseline paths and lines accurately | PASS | Every cited path exists at the pinned revision; checked ranges support the associated technical assertions. See citation audit below. |
| Primary proposes the smallest bounded live correlated test without claiming execution | PASS | One existing producer dispatch, one same-task tool observation/result, independent Kubernetes name cross-check, source/freshness/target validation, and consumption of the same captured evidence are appropriate to the existing contract. The command is explicitly proposed only. Using the same captured evidence is important: a second independently dispatched task would not close the same-task gap. No redesign or direct-MCP detour is proposed. |
| Primary avoids unsupported root-cause diagnosis | PASS | It labels quota as a proposed inference and does not claim the absent tool marker proves quota or any sole operational cause. Phase 5E lines 29–35 support that caution. |
| Negative trial rejects L6 promotion from successful direct MCP plus equal counts | PASS | The answer accepts the supplied direct-call success as historical server evidence but refuses L6 promotion. Equal counts cannot establish the missing agent causation/output path. |
| Negative trial identifies missing same-task causal A2A-agent-tool-response link | PASS | It names accepted A2A dispatch, causally triggered agent tool use, returned tool-derived A2A output, and a shared task/correlation identifier as the missing observation. |
| Negative trial keeps unknowns and runtime scope bounded | PASS | It correctly says the supplied excerpt does not establish L4, rather than denying L4 elsewhere in the repository. It claims no runtime verification. A single correlated trace is a sufficient conceptual next observation for this definition-level question; it need not restate the full repository machine schema. |

## Citation audit

All primary citations were checked, not merely accepted from the producer's verdict:

- `docs/reference/kagent-capability-matrix.md:12,14`: accurate definitions of L4 and L6.
- `evidence/kagent/educational-practice-phase-5d-trustworthy-a2a.md:58–64,75–82,32–34`: accurate historical dispatch fields, retained SSE excerpt, and acceptance/success distinction.
- `evidence/kagent/educational-practice-phase-5e-agent-mediated-mcp.md:58–68,24–27,29–35`: accurate failed L6 attempt, missing correlated marker and output, and explicitly qualified quota inference.
- `scripts/kagent/agent_mcp_trace.py:815–839`: branches fail missing observation, task mismatch, absent returned A2A names, and failed name matching.
- `evidence/kagent/README.md:25–27`: accurate index status at the pinned revision.
- `docs/reference/kagent-agent-mediated-mcp-evidence.md:20–26,62–67`: supports the proposed required target, dispatch, proof, result, provenance, decision, and promotion constraints.
- `scripts/kagent/agent_mcp_trace.py:598–606,39–47,924–937`: supports nonempty subset matching, bounded default target/prompt, and valid proposed CLI flags.
- `evidence/kagent/educational-practice-phase-5b-direct-mcp.md:24–46,50–56,58–67`: supports direct tool success/count cross-check and the explicit absence of an agent-mediated A2A path.
- `scripts/kagent/KagentHealth.psm1:1146–1153`: explicitly rejects direct-MCP-only evidence for FullMcpExecution.

No substantive citation errors found. Links point to the start of the described range and their labels describe the relevant range; that is sufficient for locating the supporting text. The two implementation files were inspected in the checkout at the pinned HEAD but are not included in the six-file source manifest.

## Unsupported claims and wording precision

No unsupported material capability claim or unqualified root-cause claim was found.

One minor wording issue: the primary says retained SSE examples “independently show” the task entering accepted states. These are corroborating excerpts in the same historical Phase 5D record, not an independent capture or independent witness. They support the stated fields but should not be counted as independent replication.

The answer's “both HEAD checks matched” and clean-status assertions concern the subject's reported inspection. `command-results.json` retains one HEAD check and one clean-status result, along with a remote-ref check and a 78-pass offline test; it is not a complete subject tool transcript. It therefore corroborates the revision/clean snapshot but does not independently establish every command in the subject's command list or its claimed two HEAD checks. These are provenance-verification limits, not demonstrated false statements. The evaluator's current HEAD matches; current status contains untracked `docs/onboarding/PRACTICAL-AGENT-LABS.md` and `docs/runbooks/lab-01-l4-versus-l6.md`, so current cleanliness must not be inferred from the older record.

## Source-manifest verification

All six SHA-256 values in `source-manifest.json` match both the retained files under `sources/` and the exact bytes returned by `git show <revision>:<path>`:

| Source | Verified SHA-256 |
|---|---|
| `docs/reference/kagent-capability-matrix.md` | `6de269f902267373ecf1d1fe5abc4f31d4e6f2fd9396d595790d4c8e7e6f4b91` |
| `docs/reference/kagent-agent-mediated-mcp-evidence.md` | `48ed3f5bb013ce3620934b24579e0c074a87c7da8f86f5bf9f6867316875d26f` |
| `evidence/kagent/README.md` | `d093b31e30fc269c08e36807cc3ff68944e06cb722da068ccac3c90dd39118fe` |
| `evidence/kagent/educational-practice-phase-5d-trustworthy-a2a.md` | `990238434609348e8a720f48f6eba20f8fc1996fd8e8093486d409ce7d616c27` |
| `evidence/kagent/educational-practice-phase-5e-agent-mediated-mcp.md` | `3148f3b7178e247c961e58979353155bf60d2c87d38aeb0851ef179e11fe527a` |
| `evidence/kagent/educational-practice-phase-5b-direct-mcp.md` | `6ba61f8f468485dafb0a4fa420d890fc96a07bb381d15046c5ce5254fdeffd5e` |

Raw checkout hashes differ for all six because checkout files use CRLF while committed/retained bytes use LF. Normalizing only CRLF to LF reproduces each Git blob exactly. This is not a manifest-integrity failure.

## Contamination and isolation

The primary is **not a fully blind uncontaminated evaluation**. Its prompt already states the target L4-proven/L6-unproven outcome. It had source records containing their own conclusions. In addition, its broad search reportedly exposed incidental benchmark/scoring snippets. The answer discloses this; the retained protocol confirms the limitation. The retained directory does not include the complete search transcript, so the extent of benchmark exposure or its causal effect cannot be independently reconstructed. A correct primary answer here demonstrates accurate source-grounded explanation under those conditions, not independent discovery of the outcome without hints.

The negative trial is stronger on the narrow discrimination question: protocol says a separate fresh subject received definitions and the successful direct-call excerpt with source conclusions withheld, no inherited conversation, and no tools during assessment. Its response does not rely on primary-answer citations and articulates the missing causal chain. The retained materials document this setup but do not include a complete execution trace proving isolation; regard those properties as protocol-reported. There is no basis to assert contamination occurred in the negative trial, nor to claim perfect verified isolation.

The evaluator was given the rubric and expected distinction, as appropriate for criterion grading, and did not communicate judgments to subjects. Evaluator independence concerns production of the answers; it is not blindness to the rubric.

## Scope of generalization

Supported: these retained responses correctly distinguish A2A acceptance, direct MCP server success, and same-task agent-mediated invocation/result evidence in this specific LAB-01 context. The separate negative response supports one narrow transfer to a success-shaped direct-call excerpt.

Not supported: statistical reliability of the model, resistance to different adversarial framing, broad agent/tool reasoning competence, fresh L4 or L6 runtime behavior, current credentials/quota diagnosis, repeatability across independent runs, or live end-to-end success. The offline 78-test command does not change L6 status. A single tested behavior does not prove model reliability.

## Evaluator operations

Read `F:/Git/agent-labs/AGENTS.md`, both answer files, prompts, command results, manifest, six retained sources and corresponding repository files. Ran read-only `git rev-parse HEAD` and `git status --porcelain`; read numbered source/implementation excerpts; used `Get-FileHash` and Python standard-library SHA-256 over exact `git show` bytes plus retained/checkout bytes. No network or runtime calls were made. Verdict creation used `apply_patch`.
