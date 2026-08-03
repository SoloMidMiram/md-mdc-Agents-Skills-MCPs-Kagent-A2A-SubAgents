#!/usr/bin/env python3
"""Fail-closed DeepSeek provider qualification for the local kagent lab.

This is provider qualification only. It never proves IDE delegation, Kubernetes
tool use, I3, I4, L6, or L7. The helper reads an API key from an environment
variable, but its result intentionally contains only candidate names, status
codes, elapsed time, and fixed failure categories.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import urlparse

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_API_KEY_ENV = "DEEPSEEK_API_KEY"
CANDIDATE_MODELS = ("deepseek-v4-flash", "deepseek-v4-pro")
MAX_RESPONSE_BYTES = 1024 * 1024


class ExitCode:
    SUCCESS = 0
    QUALIFICATION_FAILED = 1
    USAGE = 2


class UsageError(ValueError):
    """Raised for a configuration that must not make a provider request."""


@dataclass(frozen=True)
class HttpResponse:
    status: int | None
    body: bytes = b""
    error_category: str | None = None


class Transport(Protocol):
    def post(
        self, url: str, *, headers: dict[str, str], body: bytes, timeout: float
    ) -> HttpResponse: ...


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Treat redirects as a failed provider response instead of following them."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


class UrllibTransport:
    """Small stdlib transport that never keeps response headers or error text."""

    def post(
        self, url: str, *, headers: dict[str, str], body: bytes, timeout: float
    ) -> HttpResponse:
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        opener = urllib.request.build_opener(NoRedirectHandler)
        try:
            with opener.open(request, timeout=timeout) as response:
                return HttpResponse(
                    status=response.status, body=response.read(MAX_RESPONSE_BYTES + 1)
                )
        except urllib.error.HTTPError as exc:
            return HttpResponse(status=exc.code, error_category="http-error")
        except (urllib.error.URLError, TimeoutError, OSError):
            return HttpResponse(status=None, error_category="transport-error")


@dataclass(frozen=True)
class ProbeStep:
    passed: bool
    http_status: int | None
    latency_ms: int
    reason: str | None = None

    def to_sanitized_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "httpStatus": self.http_status,
            "latencyMs": self.latency_ms,
        }


@dataclass(frozen=True)
class CandidateResult:
    model: str
    no_tool: ProbeStep
    tool_call: ProbeStep | None = None

    @property
    def qualified(self) -> bool:
        return self.no_tool.passed and self.tool_call is not None and self.tool_call.passed

    def to_sanitized_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "noTool": self.no_tool.to_sanitized_dict(),
            "toolCall": self.tool_call.to_sanitized_dict() if self.tool_call else None,
            "qualified": self.qualified,
        }


@dataclass
class ProviderProbeResult:
    candidates: list[CandidateResult] = field(default_factory=list)
    selected_model: str | None = None
    credential_present: bool = True

    @property
    def exit_code(self) -> int:
        if not self.credential_present:
            return ExitCode.USAGE
        return ExitCode.SUCCESS if self.selected_model else ExitCode.QUALIFICATION_FAILED

    def to_sanitized_dict(self) -> dict[str, Any]:
        return {
            "candidates": [candidate.to_sanitized_dict() for candidate in self.candidates],
            "selectedModel": self.selected_model,
            "exitCode": self.exit_code,
        }


def validate_base_url(value: str) -> str:
    """Return a bare HTTPS API origin with no userinfo or query components."""
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.params
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
    ):
        raise UsageError("base URL must be a bare HTTPS API origin")
    return f"https://{parsed.netloc}"


def chat_completions_url(base_url: str) -> str:
    return f"{validate_base_url(base_url)}/chat/completions"


def _post_json(
    transport: Transport,
    url: str,
    api_key: str,
    payload: dict[str, Any],
    timeout: float,
) -> tuple[HttpResponse, int]:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    started = time.monotonic()
    response = transport.post(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        body=body,
        timeout=timeout,
    )
    return response, round((time.monotonic() - started) * 1000)


def _decode_success(response: HttpResponse) -> tuple[dict[str, Any] | None, str | None]:
    if response.error_category is not None:
        return None, response.error_category
    if response.status is None or not 200 <= response.status < 300:
        return None, "http-error"
    if len(response.body) > MAX_RESPONSE_BYTES:
        return None, "response-too-large"
    try:
        decoded = json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, "invalid-json"
    if not isinstance(decoded, dict):
        return None, "invalid-shape"
    return decoded, None


def _first_message(decoded: dict[str, Any]) -> dict[str, Any] | None:
    choices = decoded.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    return message if isinstance(message, dict) else None


def _no_tool_payload(model: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Return a concise non-empty acknowledgement and do not call a tool.",
            },
            {"role": "user", "content": "Acknowledge this provider qualification request."},
        ],
        "thinking": {"type": "disabled"},
        "temperature": 0,
        "max_tokens": 64,
        "stream": False,
    }


def _tool_call_payload(model: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": "Use the requested function and no other function."},
            {"role": "user", "content": "Call echo_probe with value ok."},
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "echo_probe",
                    "description": "Return the fixed provider-qualification marker.",
                    "parameters": {
                        "type": "object",
                        "properties": {"value": {"type": "string", "enum": ["ok"]}},
                        "required": ["value"],
                        "additionalProperties": False,
                    },
                },
            }
        ],
        "tool_choice": {"type": "function", "function": {"name": "echo_probe"}},
        "thinking": {"type": "disabled"},
        "temperature": 0,
        "max_tokens": 64,
        "stream": False,
    }


def _probe_no_tool(
    transport: Transport, url: str, model: str, api_key: str, timeout: float
) -> ProbeStep:
    response, latency_ms = _post_json(transport, url, api_key, _no_tool_payload(model), timeout)
    decoded, error = _decode_success(response)
    if error is not None:
        return ProbeStep(False, response.status, latency_ms, error)
    if decoded is None:
        return ProbeStep(False, response.status, latency_ms, "invalid-shape")
    message = _first_message(decoded)
    if not message or message.get("tool_calls"):
        return ProbeStep(False, response.status, latency_ms, "unexpected-tool-call")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        return ProbeStep(False, response.status, latency_ms, "unexpected-content")
    return ProbeStep(True, response.status, latency_ms)


def _probe_tool_call(
    transport: Transport, url: str, model: str, api_key: str, timeout: float
) -> ProbeStep:
    response, latency_ms = _post_json(transport, url, api_key, _tool_call_payload(model), timeout)
    decoded, error = _decode_success(response)
    if error is not None:
        return ProbeStep(False, response.status, latency_ms, error)
    if decoded is None:
        return ProbeStep(False, response.status, latency_ms, "invalid-shape")
    message = _first_message(decoded)
    if not message:
        return ProbeStep(False, response.status, latency_ms, "invalid-shape")
    tool_calls = message.get("tool_calls")
    if (
        not isinstance(tool_calls, list)
        or len(tool_calls) != 1
        or not isinstance(tool_calls[0], dict)
    ):
        return ProbeStep(False, response.status, latency_ms, "unexpected-tool-call")
    function = tool_calls[0].get("function")
    if not isinstance(function, dict) or function.get("name") != "echo_probe":
        return ProbeStep(False, response.status, latency_ms, "unexpected-tool-call")
    arguments = function.get("arguments")
    if not isinstance(arguments, str):
        return ProbeStep(False, response.status, latency_ms, "invalid-tool-arguments")
    try:
        parsed_arguments = json.loads(arguments)
    except json.JSONDecodeError:
        return ProbeStep(False, response.status, latency_ms, "invalid-tool-arguments")
    if parsed_arguments != {"value": "ok"}:
        return ProbeStep(False, response.status, latency_ms, "unexpected-tool-arguments")
    return ProbeStep(True, response.status, latency_ms)


def qualify_candidates(
    transport: Transport,
    *,
    base_url: str,
    api_key: str,
    timeout: float = 30.0,
    candidates: tuple[str, ...] = CANDIDATE_MODELS,
) -> ProviderProbeResult:
    """Return the first candidate that passes the no-tool and tool-call checks."""
    if not api_key.strip():
        return ProviderProbeResult(credential_present=False)
    url = chat_completions_url(base_url)
    result = ProviderProbeResult()
    for model in candidates:
        no_tool = _probe_no_tool(transport, url, model, api_key, timeout)
        tool_call = (
            _probe_tool_call(transport, url, model, api_key, timeout) if no_tool.passed else None
        )
        candidate = CandidateResult(model=model, no_tool=no_tool, tool_call=tool_call)
        result.candidates.append(candidate)
        if candidate.qualified:
            result.selected_model = model
            return result
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.timeout <= 0:
            raise UsageError("timeout must be positive")
        result = qualify_candidates(
            UrllibTransport(),
            base_url=args.base_url,
            api_key=os.environ.get(args.api_key_env, ""),
            timeout=args.timeout,
        )
    except UsageError as exc:
        print(json.dumps({"error": str(exc), "exitCode": ExitCode.USAGE}, sort_keys=True))
        return ExitCode.USAGE
    print(json.dumps(result.to_sanitized_dict(), sort_keys=True))
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
