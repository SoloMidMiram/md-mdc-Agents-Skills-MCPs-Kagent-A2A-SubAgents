#!/usr/bin/env python3
"""Validate the bounded PR2 kagent -> LiteLLM gateway slice offline.

This validator does not contact Kubernetes, LiteLLM, or a model provider. It
checks the intended artifact boundary and can audit a dated evidence record.
Live card/task execution remains an operator step in the runbook.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_CONFIG = ROOT / "deploy/samples/kagent/litellm-gateway-model-config.yaml"
DEFAULT_AGENT = ROOT / "deploy/samples/kagent/litellm-gateway-smoke-agent.yaml"
DEFAULT_EVIDENCE = ROOT / "evidence/runtime/kagent-litellm-success.md"


def _load_one(path: Path) -> dict[str, Any]:
    docs = [doc for doc in yaml.safe_load_all(path.read_text(encoding="utf-8")) if doc is not None]
    if len(docs) != 1 or not isinstance(docs[0], dict):
        raise ValueError(f"{path}: expected exactly one YAML object")
    return docs[0]


def validate_model_config(path: Path) -> list[str]:
    doc = _load_one(path)
    errors: list[str] = []
    raw = path.read_text(encoding="utf-8")
    if doc.get("kind") != "ModelConfig":
        errors.append(f"{path}: kind must be ModelConfig")
    spec = doc.get("spec") if isinstance(doc.get("spec"), dict) else {}
    if spec.get("provider") != "OpenAI":
        errors.append(f"{path}: provider must be OpenAI-compatible")
    if spec.get("model") != "agent-coder":
        errors.append(f"{path}: model must be agent-coder")
    if spec.get("apiKeySecret") != "kagent-litellm":
        errors.append(f"{path}: apiKeySecret must be kagent-litellm")
    if spec.get("apiKeySecretKey") != "LITELLM_MASTER_KEY":
        errors.append(f"{path}: apiKeySecretKey must be LITELLM_MASTER_KEY")
    openai = spec.get("openAI") if isinstance(spec.get("openAI"), dict) else {}
    if openai.get("baseUrl") != "http://host.docker.internal:4000/v1":
        errors.append(f"{path}: openAI.baseUrl must target the LiteLLM /v1 endpoint")
    for forbidden in ("OPENAI_API_KEY", "DEEPSEEK_API_KEY", "OLLAMA_HOST"):
        if forbidden in raw:
            errors.append(f"{path}: provider credential/host {forbidden} must stay behind LiteLLM")
    return errors


def validate_agent(path: Path) -> list[str]:
    doc = _load_one(path)
    errors: list[str] = []
    raw = path.read_text(encoding="utf-8")
    if doc.get("kind") != "Agent":
        errors.append(f"{path}: kind must be Agent")
    spec = doc.get("spec") if isinstance(doc.get("spec"), dict) else {}
    declarative = spec.get("declarative") if isinstance(spec.get("declarative"), dict) else {}
    if declarative.get("modelConfig") != "litellm-gateway-model-config":
        errors.append(f"{path}: declarative.modelConfig must be litellm-gateway-model-config")
    if declarative.get("tools"):
        errors.append(f"{path}: PR2 smoke agent must declare no tools")
    if spec.get("tools"):
        errors.append(f"{path}: PR2 smoke agent must not declare top-level tools")
    if declarative.get("a2aConfig") is None:
        errors.append(f"{path}: a2aConfig skill metadata is required for the card gate")
    forbidden = ("McpServer", "read_file", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "OLLAMA_HOST")
    for term in forbidden:
        if term in raw:
            errors.append(f"{path}: PR2 smoke agent must not contain {term}")
    return errors


def validate_evidence(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    required = {
        "agent-coder": "LiteLLM alias",
        "http://host.docker.internal:4000/v1": "LiteLLM endpoint",
        "ModelConfig": "ModelConfig excerpt",
        "Pod curl probe": "pod probe result",
        "A2A request harness execution": "agent completion result",
    }
    return [f"{path}: missing {label}" for needle, label in required.items() if needle not in text]


def validate(model_config: Path, agent: Path, evidence: Path | None) -> list[str]:
    errors = validate_model_config(model_config) + validate_agent(agent)
    if evidence is not None:
        errors.extend(validate_evidence(evidence))
    return errors


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-config", type=Path, default=DEFAULT_MODEL_CONFIG)
    parser.add_argument("--agent", type=Path, default=DEFAULT_AGENT)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable result")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        errors = validate(args.model_config, args.agent, args.evidence)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        errors = [str(exc)]
    result = {"passed": not errors, "errors": errors}
    if args.json:
        print(json.dumps(result, indent=2))
    elif errors:
        print("[FAIL] PR2 artifact validation")
        for error in errors:
            print(f"- {error}")
    else:
        print("[PASS] PR2 artifact and evidence-shape validation")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
