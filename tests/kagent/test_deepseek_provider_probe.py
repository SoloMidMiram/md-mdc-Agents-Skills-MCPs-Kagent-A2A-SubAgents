"""Deterministic tests for the bounded DeepSeek provider qualification helper."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "scripts" / "kagent"
sys.path.insert(0, str(SCRIPT_DIR))

import deepseek_provider_probe as probe  # noqa: E402

SECRET = "deepseek-secret-must-not-appear"


class FakeTransport:
    def __init__(self, responses: list[probe.HttpResponse]) -> None:
        self.responses = responses
        self.requests: list[dict[str, Any]] = []

    def post(
        self, url: str, *, headers: dict[str, str], body: bytes, timeout: float
    ) -> probe.HttpResponse:
        self.requests.append(
            {"url": url, "headers": dict(headers), "payload": json.loads(body), "timeout": timeout}
        )
        return self.responses.pop(0)


def _no_tool_response(content: str = "acknowledged") -> probe.HttpResponse:
    return probe.HttpResponse(
        status=200,
        body=json.dumps({"choices": [{"message": {"content": content}}]}).encode(),
    )


def _tool_response(arguments: str = '{"value":"ok"}') -> probe.HttpResponse:
    return probe.HttpResponse(
        status=200,
        body=json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {"function": {"name": "echo_probe", "arguments": arguments}}
                            ]
                        }
                    }
                ]
            }
        ).encode(),
    )


def test_first_candidate_is_selected_and_sanitized_output_omits_key() -> None:
    transport = FakeTransport([_no_tool_response(), _tool_response()])

    result = probe.qualify_candidates(
        transport, base_url=probe.DEFAULT_BASE_URL, api_key=SECRET, timeout=1
    )

    assert result.exit_code == probe.ExitCode.SUCCESS
    assert result.selected_model == "deepseek-v4-flash"
    assert [request["payload"]["model"] for request in transport.requests] == [
        "deepseek-v4-flash",
        "deepseek-v4-flash",
    ]
    assert all(
        request["payload"]["thinking"] == {"type": "disabled"} for request in transport.requests
    )
    assert transport.requests[0]["headers"]["Authorization"] == f"Bearer {SECRET}"
    rendered = json.dumps(result.to_sanitized_dict(), sort_keys=True)
    assert SECRET not in rendered
    assert "Authorization" not in rendered
    assert "acknowledged" not in rendered


def test_pro_is_only_tried_after_flash_fails() -> None:
    transport = FakeTransport(
        [
            _no_tool_response(""),
            _no_tool_response(),
            _tool_response(),
        ]
    )

    result = probe.qualify_candidates(transport, base_url=probe.DEFAULT_BASE_URL, api_key=SECRET)

    assert result.exit_code == probe.ExitCode.SUCCESS
    assert result.selected_model == "deepseek-v4-pro"
    assert [request["payload"]["model"] for request in transport.requests] == [
        "deepseek-v4-flash",
        "deepseek-v4-pro",
        "deepseek-v4-pro",
    ]


def test_invalid_tool_call_shape_fails_closed() -> None:
    transport = FakeTransport(
        [
            _no_tool_response(),
            _tool_response('{"value":"wrong"}'),
            _no_tool_response(""),
        ]
    )

    result = probe.qualify_candidates(transport, base_url=probe.DEFAULT_BASE_URL, api_key=SECRET)

    assert result.exit_code == probe.ExitCode.QUALIFICATION_FAILED
    assert result.selected_model is None
    assert result.candidates[0].tool_call is not None
    assert result.candidates[0].tool_call.reason == "unexpected-tool-arguments"


def test_missing_credential_returns_usage_without_requests() -> None:
    transport = FakeTransport([])

    result = probe.qualify_candidates(transport, base_url=probe.DEFAULT_BASE_URL, api_key="")

    assert result.exit_code == probe.ExitCode.USAGE
    assert result.credential_present is False
    assert transport.requests == []


def test_rejects_non_origin_base_url() -> None:
    transport = FakeTransport([])

    try:
        probe.qualify_candidates(
            transport,
            base_url="https://user:password@api.deepseek.com/v1?secret=value",
            api_key=SECRET,
        )
    except probe.UsageError as exc:
        assert "base URL" in str(exc)
    else:
        raise AssertionError("expected invalid provider origin to fail")
