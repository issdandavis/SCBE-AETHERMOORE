"""Tests for tiered_council_dispatch with mocked HTTP and harness registry."""

from __future__ import annotations

import os
from typing import Any
from unittest import mock

import pytest

from src.agent_comms import harness_providers as _harness
from src.agent_comms.tiered_council import CostTier, length_floor_rubric
from src.agent_comms.tiered_council_dispatch import (
    SCHEMA_VERSION,
    CouncilDispatchConfig,
    build_council_providers,
    dispatch_tiered_council,
    make_openai_compat_adapter,
    truncated_payload_for_logging,
)


def _fake_harness(
    provider_id: str,
    family: str,
    pricing_tier: str,
    *,
    base_url: str = "http://test/v1",
    api_key_env: tuple[str, ...] = (),
    default_model: str = "test-model",
    local: bool = False,
) -> _harness.HarnessProvider:
    return _harness.HarnessProvider(
        provider=provider_id,
        family=family,
        base_url=base_url,
        api_key_env=api_key_env,
        default_model=default_model,
        tool_adapter="raw_json_only",
        local=local,
        pricing_tier=pricing_tier,
        capabilities=("chat",),
    )


def _registry_with(
    *providers: _harness.HarnessProvider,
) -> dict[str, _harness.HarnessProvider]:
    return {p.provider: p for p in providers}


def _good_openai_response(text: str, prompt_tokens: int = 10, completion_tokens: int = 20) -> dict[str, Any]:
    return {
        "choices": [{"message": {"role": "assistant", "content": text}}],
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
    }


def test_build_council_providers_marks_local_available_without_keys() -> None:
    registry = _registry_with(
        _fake_harness("ollama", "local-openai-compatible", "free-local", local=True, base_url="http://127.0.0.1/v1"),
        _fake_harness("groq", "remote-openai-compatible", "free-tier", api_key_env=("GROQ_API_KEY",)),
    )
    with mock.patch.dict(os.environ, {}, clear=True):
        providers = build_council_providers(registry_provider=lambda: registry)
    by_id = {p.id: p for p in providers}
    assert by_id["ollama"].available is True  # local-no-auth
    assert by_id["ollama"].tier == CostTier.LOCAL_FREE
    assert by_id["groq"].available is False
    assert by_id["groq"].tier == CostTier.REMOTE_FREE


def test_build_council_providers_uses_token_when_present() -> None:
    registry = _registry_with(
        _fake_harness("groq", "remote-openai-compatible", "free-tier", api_key_env=("GROQ_API_KEY",)),
    )
    with mock.patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=True):
        providers = build_council_providers(registry_provider=lambda: registry)
    assert providers[0].available is True
    assert providers[0].reason == "ok"


def test_adapter_success_extracts_text_and_tokens() -> None:
    registry = _registry_with(
        _fake_harness("ollama", "local-openai-compatible", "free-local", local=True, base_url="http://127.0.0.1/v1"),
    )
    captured: dict[str, Any] = {}

    def fake_http(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        return _good_openai_response("hello world", prompt_tokens=12, completion_tokens=34)

    adapter = make_openai_compat_adapter(
        config=CouncilDispatchConfig(),
        http=fake_http,
        registry_provider=lambda: registry,
    )
    call = adapter("ollama", "say hi", {})

    assert call.ok
    assert call.response == "hello world"
    assert call.prompt_tokens == 12
    assert call.completion_tokens == 34
    assert call.cents == 0.0  # free-local
    assert captured["payload"]["model"] == "test-model"
    assert captured["payload"]["messages"][0]["content"] == "say hi"
    assert "Authorization" not in captured["headers"]


def test_adapter_attaches_bearer_when_token_present() -> None:
    registry = _registry_with(
        _fake_harness("groq", "remote-openai-compatible", "free-tier", api_key_env=("GROQ_API_KEY",)),
    )
    captured: dict[str, Any] = {}

    def fake_http(url: str, payload: dict[str, Any], headers: dict[str, str], _t: float) -> dict[str, Any]:
        captured["headers"] = headers
        return _good_openai_response("ok")

    adapter = make_openai_compat_adapter(
        config=CouncilDispatchConfig(),
        http=fake_http,
        registry_provider=lambda: registry,
    )
    with mock.patch.dict(os.environ, {"GROQ_API_KEY": "secret-token"}, clear=True):
        call = adapter("groq", "ping", {})
    assert call.ok
    assert captured["headers"]["Authorization"] == "Bearer secret-token"


def test_adapter_missing_credentials_returns_error_call() -> None:
    registry = _registry_with(
        _fake_harness("groq", "remote-openai-compatible", "free-tier", api_key_env=("GROQ_API_KEY",)),
    )

    def fake_http(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("http should not be called when creds are missing")

    adapter = make_openai_compat_adapter(
        config=CouncilDispatchConfig(),
        http=fake_http,
        registry_provider=lambda: registry,
    )
    with mock.patch.dict(os.environ, {}, clear=True):
        call = adapter("groq", "ping", {})
    assert call.ok is False
    assert call.error == "missing_credentials"


def test_adapter_unknown_provider_returns_error_call() -> None:
    registry = _registry_with(
        _fake_harness("ollama", "local-openai-compatible", "free-local", local=True, base_url="http://127.0.0.1/v1"),
    )
    adapter = make_openai_compat_adapter(
        config=CouncilDispatchConfig(),
        http=lambda *a, **k: _good_openai_response("nope"),
        registry_provider=lambda: registry,
    )
    call = adapter("nonexistent", "ping", {})
    assert call.ok is False
    assert call.error is not None and call.error.startswith("unknown_harness_provider:")


def test_adapter_empty_response_marked_as_error() -> None:
    registry = _registry_with(
        _fake_harness("ollama", "local-openai-compatible", "free-local", local=True, base_url="http://127.0.0.1/v1"),
    )
    adapter = make_openai_compat_adapter(
        config=CouncilDispatchConfig(),
        http=lambda *a, **k: {"choices": [{"message": {"content": ""}}], "usage": {}},
        registry_provider=lambda: registry,
    )
    call = adapter("ollama", "ping", {})
    assert call.ok is False
    assert call.error == "empty_response"


def test_dispatch_tiered_council_solves_at_local_free() -> None:
    registry = _registry_with(
        _fake_harness("ollama", "local-openai-compatible", "free-local", local=True, base_url="http://127.0.0.1/v1"),
        _fake_harness("groq", "remote-openai-compatible", "free-tier", api_key_env=("GROQ_API_KEY",)),
    )

    def fake_http(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return _good_openai_response("Detailed local answer that easily passes the rubric threshold check.")

    payload = dispatch_tiered_council(
        task="please explain X",
        budget_cents=5.0,
        config=CouncilDispatchConfig(
            rubric=length_floor_rubric(40),
            team_size_per_tier=1,
        ),
        http=fake_http,
        registry_provider=lambda: registry,
    )
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["solved"] is True
    assert payload["final_tier"] == int(CostTier.LOCAL_FREE)
    assert payload["total_cents"] == 0.0
    assert "Detailed local answer" in payload["final_answer"]


def test_dispatch_tiered_council_escalates_when_local_insufficient() -> None:
    registry = _registry_with(
        _fake_harness("ollama", "local-openai-compatible", "free-local", local=True, base_url="http://127.0.0.1/v1"),
        _fake_harness("groq", "remote-openai-compatible", "free-tier", api_key_env=("GROQ_API_KEY",)),
    )

    def fake_http(url: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        if "127.0.0.1" in url:
            return _good_openai_response("x")  # too short, fails rubric
        return _good_openai_response("Remote answer with way more depth and length to clear the threshold.")

    with mock.patch.dict(os.environ, {"GROQ_API_KEY": "test"}, clear=True):
        payload = dispatch_tiered_council(
            task="explain",
            budget_cents=5.0,
            config=CouncilDispatchConfig(
                rubric=length_floor_rubric(40),
                team_size_per_tier=1,
            ),
            http=fake_http,
            registry_provider=lambda: registry,
        )

    assert payload["solved"] is True
    assert payload["final_tier"] == int(CostTier.REMOTE_FREE)
    joined = " | ".join(payload["escalation_path"])
    assert "tier0" in joined
    assert "tier1" in joined


def test_dispatch_payload_contains_attempts_and_metadata() -> None:
    registry = _registry_with(
        _fake_harness("ollama", "local-openai-compatible", "free-local", local=True, base_url="http://127.0.0.1/v1"),
    )

    payload = dispatch_tiered_council(
        task="ping",
        budget_cents=1.0,
        config=CouncilDispatchConfig(
            rubric=length_floor_rubric(10),
            team_size_per_tier=1,
        ),
        http=lambda *a, **k: _good_openai_response("answer that is long enough"),
        registry_provider=lambda: registry,
        metadata={"task_type": "general", "series_id": "abc"},
    )
    assert payload["metadata"] == {"task_type": "general", "series_id": "abc"}
    assert isinstance(payload["attempts"], list)
    assert payload["attempts"][0]["tier"] == int(CostTier.LOCAL_FREE)
    assert payload["attempts"][0]["members"][0]["provider_id"] == "ollama"


def test_truncation_helper_caps_long_answers() -> None:
    payload = {
        "final_answer": "x" * 5000,
        "attempts": [
            {
                "members": [{"response": "y" * 5000}],
                "synthesis_call": {"response": "z" * 5000},
                "best_response": "x" * 5000,
            }
        ],
    }
    truncated = truncated_payload_for_logging(payload, max_response_chars=100)
    assert len(truncated["final_answer"]) < 1000
    assert "[truncated" in truncated["final_answer"]
    assert "[truncated]" in truncated["attempts"][0]["members"][0]["response"]
    assert "[truncated]" in truncated["attempts"][0]["synthesis_call"]["response"]
    assert "[truncated]" in truncated["attempts"][0]["best_response"]


@pytest.mark.parametrize(
    "data, expected_text, expected_in, expected_out",
    [
        ({}, "", 0, 0),
        ({"choices": []}, "", 0, 0),
        (
            {"choices": [{"message": {"content": "hi"}}], "usage": {"prompt_tokens": 3, "completion_tokens": 5}},
            "hi",
            3,
            5,
        ),
        (
            {"choices": [{"message": {"content": [{"text": "a"}, {"text": "b"}]}}], "usage": {}},
            "ab",
            0,
            0,
        ),
        ({"choices": [{"text": "fallback"}], "usage": {}}, "fallback", 0, 0),
    ],
)
def test_extract_openai_chat_response_shapes(
    data: dict, expected_text: str, expected_in: int, expected_out: int
) -> None:
    from src.agent_comms.tiered_council_dispatch import _extract_openai_chat_response

    text, prompt_tokens, completion_tokens = _extract_openai_chat_response(data)
    assert text == expected_text
    assert prompt_tokens == expected_in
    assert completion_tokens == expected_out
