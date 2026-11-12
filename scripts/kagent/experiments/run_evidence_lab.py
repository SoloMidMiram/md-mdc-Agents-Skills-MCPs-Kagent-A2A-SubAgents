"""Run six synthetic observations through the live trace decision function."""

import json
from dataclasses import dataclass, replace

from scripts.kagent.agent_mcp_trace import ExitCode, TraceReport, evaluate_trace


@dataclass(frozen=True)
class Scenario:
    name: str
    expected: str
    expected_reason: str
    report: TraceReport
    origin: str = "synthetic"
    capability_promotion: bool = False


def scenarios() -> tuple[Scenario, ...]:
    complete = TraceReport(
        l4_accepted=True,
        accepted_state="submitted",
        request_id="synthetic-request",
        response_id_matched=True,
        task_or_message_id="synthetic-task",
        correlated_id="synthetic-task",
        tool_observed=True,
        returned_through_a2a=True,
        tool_names=["example-pod"],
        cross_check_names=["example-pod"],
        target_bound=True,
    )
    return (
        Scenario(
            "accepted_dispatch_only",
            "l4_only",
            "no observable MCP tool invocation",
            replace(
                complete,
                tool_observed=False,
                correlated_id=None,
                returned_through_a2a=False,
                tool_names=[],
            ),
        ),
        Scenario(
            "direct_mcp_only",
            "gate_failure",
            "no accepted A2A dispatch",
            replace(
                complete,
                l4_accepted=False,
                accepted_state=None,
                task_or_message_id=None,
                request_id=None,
                response_id_matched=False,
                returned_through_a2a=False,
            ),
        ),
        Scenario(
            "mismatched_task",
            "gate_failure",
            "task/trace ID mismatch",
            replace(complete, correlated_id="synthetic-other-task"),
        ),
        Scenario(
            "no_a2a_result",
            "gate_failure",
            "result not returned through A2A",
            replace(complete, returned_through_a2a=False, tool_names=[]),
        ),
        Scenario(
            "mismatched_cross_check",
            "gate_failure",
            "kubectl cross-check mismatch",
            replace(complete, cross_check_names=["other-pod"]),
        ),
        Scenario(
            "complete_correlation",
            "synthetic_pass",
            "correlated agent-mediated MCP evidence with matching cross-check",
            complete,
        ),
    )


def run_scenario(scenario: Scenario) -> dict[str, str | bool]:
    code, reason = evaluate_trace(scenario.report)
    if code == ExitCode.SUCCESS:
        verdict = "synthetic_pass"
    elif scenario.report.l4_accepted and not scenario.report.tool_observed:
        verdict = "l4_only"
    else:
        verdict = "gate_failure"
    return {
        "scenario": scenario.name,
        "origin": "synthetic",
        "capabilityPromotion": False,
        "expectedVerdict": scenario.expected,
        "expectedReason": scenario.expected_reason,
        "verdict": verdict,
        "reason": reason,
    }


def main() -> int:
    results = [run_scenario(scenario) for scenario in scenarios()]
    print(json.dumps(results, indent=2))
    return int(
        any(
            result["expectedVerdict"] != result["verdict"]
            or str(result["expectedReason"]) not in str(result["reason"])
            for result in results
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
