from dataclasses import replace

import pytest

from scripts.kagent.agent_mcp_trace import ExitCode, evaluate_trace
from scripts.kagent.experiments.run_evidence_lab import run_scenario, scenarios


@pytest.mark.parametrize("scenario", scenarios(), ids=lambda scenario: scenario.name)
def test_synthetic_observations_use_live_decision(scenario):
    result = run_scenario(scenario)
    assert result["verdict"] == scenario.expected
    assert scenario.expected_reason in result["reason"]
    assert result["origin"] == scenario.origin == "synthetic"
    assert result["capabilityPromotion"] is scenario.capability_promotion is False
    assert "schemaVersion" not in result


@pytest.mark.parametrize("field", ["task_or_message_id", "correlated_id"])
def test_missing_task_identifiers_fail_closed(field):
    report = replace(scenarios()[-1].report, **{field: None})
    assert evaluate_trace(report) == (
        ExitCode.GATE,
        "task/trace ID mismatch between dispatch and tool observation",
    )
