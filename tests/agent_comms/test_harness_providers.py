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
    assert {
        "ollama",
        "lmstudio",
        "vllm",
        "llamacpp",
        "groq",
        "gemini",
        "together",
        "moonshot",
        "kimi",
        "kimi_code",
        "nvidia",
    }.issubset(providers)
    assert providers["ollama"].pricing_tier == "free-local"
    assert providers["gemini"].chat_url == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    assert providers["groq"].chat_url == "https://api.groq.com/openai/v1/chat/completions"
    assert providers["fireworks"].chat_url == "https://api.fireworks.ai/inference/v1/chat/completions"
    assert providers["nvidia"].chat_url == "https://integrate.api.nvidia.com/v1/chat/completions"
    assert providers["nvidia"].default_model == "qwen/qwen3-coder-480b-a35b-instruct"
    assert providers["kimi"].chat_url == "https://api.kimi.com/coding/v1/chat/completions"
    assert providers["kimi"].default_model == "kimi-for-coding"
    assert providers["kimi"].pricing_tier == "membership-credits"
    assert "agentic-coding" in providers["kimi"].capabilities
    assert providers["moonshot"].chat_url == "https://api.moonshot.ai/v1/chat/completions"
    assert providers["moonshot"].default_model == "kimi-k2.6"
    assert "tools-json" in providers["together"].capabilities
    assert "large-models" in providers["nvidia"].capabilities


def test_resolve_new_remote_provider_aliases() -> None:
    provider, model = resolve_provider_model("groq:llama-3.3-70b-versatile")
    assert provider.provider == "groq"
    assert model == "llama-3.3-70b-versatile"

    provider, model = resolve_provider_model("gemini:gemini-2.5-flash")
    assert provider.provider == "gemini"
    assert model == "gemini-2.5-flash"

    provider, model = resolve_provider_model("kimi:kimi-for-coding")
    assert provider.provider == "kimi"
    assert model == "kimi-for-coding"


def test_kimi_lane_switch_requires_signal() -> None:
    verdict = evaluate_lane_switch(["ollama:a", "kimi:kimi-for-coding"])

    assert verdict.ok is False
    assert verdict.signal_required is True
    assert verdict.cost == 5
    assert verdict.lane_path == ("ollama", "kimi")

    signaled = evaluate_lane_switch(
        ["ollama:a", "kimi:kimi-for-coding"],
        signal="provider-pair:ollama->kimi:agentic-coding",
    )

    assert signaled.ok is True
