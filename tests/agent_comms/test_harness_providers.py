from __future__ import annotations

from src.agent_comms import evaluate_lane_switch, parse_model_ref, provider_registry, resolve_provider_model


def test_parse_provider_model_ref_preserves_model_colons() -> None:
    provider, model = parse_model_ref("ollama:qwen2.5-coder:7b")

    assert provider == "ollama"
    assert model == "qwen2.5-coder:7b"


def test_resolve_plain_model_uses_default_provider(monkeypatch) -> None:
    monkeypatch.setenv("GEOSEAL_HARNESS_PROVIDER", "lmstudio")

    provider, model = resolve_provider_model("local-coder")

    assert provider.provider == "lmstudio"
    assert model == "local-coder"


def test_same_provider_lane_switch_is_free() -> None:
    verdict = evaluate_lane_switch(["ollama:a", "ollama:b"])

    assert verdict.ok is True
    assert verdict.signal_required is False
    assert verdict.cost == 0
    assert verdict.reason == "same_lane"


def test_cross_provider_lane_switch_requires_signal() -> None:
    verdict = evaluate_lane_switch(["ollama:a", "deepseek:b"])

    assert verdict.ok is False
    assert verdict.signal_required is True
    assert verdict.cost > 0
    assert verdict.reason == "missing_or_invalid_signal"


def test_cross_provider_lane_switch_accepts_proper_signal() -> None:
    verdict = evaluate_lane_switch(
        ["ollama:a", "deepseek:b"],
        signal="provider-pair:ollama->deepseek:compare-local-vs-remote",
    )

    assert verdict.ok is True
    assert verdict.signal_required is True
    assert verdict.signal_present is True
    assert verdict.reason == "properly_signaled"


def test_provider_registry_covers_local_free_and_remote_free_tier_lanes() -> None:
    providers = provider_registry()

    assert len(providers) >= 18
    assert {"ollama", "lmstudio", "vllm", "llamacpp", "groq", "gemini", "together", "moonshot"}.issubset(providers)
    assert providers["ollama"].pricing_tier == "free-local"
    assert providers["gemini"].chat_url == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    assert providers["groq"].chat_url == "https://api.groq.com/openai/v1/chat/completions"
    assert providers["fireworks"].chat_url == "https://api.fireworks.ai/inference/v1/chat/completions"
    assert "tools-json" in providers["together"].capabilities


def test_resolve_new_remote_provider_aliases() -> None:
    provider, model = resolve_provider_model("groq:llama-3.3-70b-versatile")
    assert provider.provider == "groq"
    assert model == "llama-3.3-70b-versatile"

    provider, model = resolve_provider_model("gemini:gemini-2.5-flash")
    assert provider.provider == "gemini"
    assert model == "gemini-2.5-flash"
