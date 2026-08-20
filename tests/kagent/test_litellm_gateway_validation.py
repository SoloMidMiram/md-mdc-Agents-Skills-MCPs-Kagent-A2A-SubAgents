"""Offline tests for the bounded PR2 LiteLLM gateway validator."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/kagent/validate-litellm-gateway.py"
SPEC = importlib.util.spec_from_file_location("validate_litellm_gateway", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
sys.modules[MODULE.__name__] = MODULE


def test_repository_phase2_artifacts_are_bounded() -> None:
    errors = MODULE.validate(
        ROOT / "deploy/samples/kagent/litellm-gateway-model-config.yaml",
        ROOT / "deploy/samples/kagent/litellm-gateway-smoke-agent.yaml",
        ROOT / "evidence/runtime/kagent-litellm-success.md",
    )
    assert errors == []


def test_validator_rejects_tools_in_phase2_agent(tmp_path: Path) -> None:
    source = (ROOT / "deploy/samples/kagent/litellm-gateway-smoke-agent.yaml").read_text(
        encoding="utf-8"
    )
    bad = source.replace(
        "    a2aConfig:\n",
        "    tools:\n      - type: McpServer\n    a2aConfig:\n",
        1,
    )
    path = tmp_path / "agent.yaml"
    path.write_text(bad, encoding="utf-8")
    errors = MODULE.validate_agent(path)
    assert any("must declare no tools" in error for error in errors)
