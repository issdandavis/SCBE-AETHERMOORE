"""Provider registry for the GeoSeal AI-to-AI harness.

The goal is not to clone a Claude Code proxy. It is to let SCBE packets route
through many OpenAI-compatible model endpoints while preserving provider
metadata, compact prompts, and local-first defaults.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any

LOCAL_HOST_MARKERS = ("127.0.0.1", "localhost", "0.0.0.0")

LANE_SWITCH_COSTS = {
    ("ollama", "lmstudio"): 1,
    ("lmstudio", "ollama"): 1,
    ("ollama", "vllm"): 2,
    ("vllm", "ollama"): 2,
    ("ollama", "llamacpp"): 2,
    ("llamacpp", "ollama"): 2,
    ("ollama", "deepseek"): 5,
    ("deepseek", "ollama"): 5,
    ("ollama", "kimi"): 5,
    ("kimi", "ollama"): 5,
    ("ollama", "kimi_code"): 5,
    ("kimi_code", "ollama"): 5,
    ("ollama", "moonshot"): 5,
    ("moonshot", "ollama"): 5,
    ("ollama", "openrouter"): 5,
    ("openrouter", "ollama"): 5,
    ("ollama", "huggingface"): 4,
    ("huggingface", "ollama"): 4,
    ("ollama", "nvidia"): 4,
    ("nvidia", "ollama"): 4,
}


@dataclass(frozen=True)
class HarnessProvider:
    provider: str
    family: str
    base_url: str
    api_key_env: tuple[str, ...]
    default_model: str
    tool_adapter: str
    local: bool = False
    pricing_tier: str = "unknown"
    capabilities: tuple[str, ...] = ("chat",)
    docs_url: str = ""
    notes: str = ""

    @property
    def chat_url(self) -> str:
        base = self.base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        if base.endswith("/openai"):
            return f"{base}/chat/completions"
        if base.endswith("/v1"):
            return f"{base}/chat/completions"
        return f"{base}/v1/chat/completions"

    def token(self) -> str | None:
        for key in self.api_key_env:
            value = os.getenv(key)
            if value:
                return value
        if self.local or any(marker in self.base_url for marker in LOCAL_HOST_MARKERS):
            return "local-no-auth"
        return None

    def status(self) -> dict[str, Any]:
        token = self.token()
        return {
            **asdict(self),
            "chat_url": self.chat_url,
            "available": bool(token),
            "token_present": bool(token and token != "local-no-auth"),
        }


@dataclass(frozen=True)
class LaneSwitchVerdict:
    ok: bool
    signal_required: bool
    signal_present: bool
    cost: int
    lane_path: tuple[str, ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _env(name: str, default: str) -> str:
    return os.getenv(name, default).strip() or default


def provider_registry() -> dict[str, HarnessProvider]:
    """Return supported harness providers keyed by stable provider id."""

    kimi_code_provider = HarnessProvider(
        provider="kimi_code",
        family="remote-openai-compatible",
        base_url=_env("KIMI_CODE_OPENAI_BASE_URL", "https://api.kimi.com/coding/v1"),
        api_key_env=("KIMI_CODE_API_KEY", "KIMI_API_KEY"),
        default_model=_env("GEOSEAL_KIMI_CODE_MODEL", _env("GEOSEAL_KIMI_MODEL", "kimi-for-coding")),
        tool_adapter="openai_tool_call",
        local=False,
        pricing_tier="membership-credits",
        capabilities=("chat", "tools-json", "coding", "long-context", "agentic-coding"),
        docs_url="https://www.kimi.com/code/docs/en/",
        notes="Kimi Code membership API; use model kimi-for-coding.",
    )
    kimi_provider = HarnessProvider(
        provider="kimi",
        family=kimi_code_provider.family,
        base_url=kimi_code_provider.base_url,
        api_key_env=kimi_code_provider.api_key_env,
        default_model=_env("GEOSEAL_KIMI_MODEL", kimi_code_provider.default_model),
        tool_adapter=kimi_code_provider.tool_adapter,
        local=False,
        pricing_tier=kimi_code_provider.pricing_tier,
        capabilities=kimi_code_provider.capabilities,
        docs_url=kimi_code_provider.docs_url,
        notes="Kimi Code alias; use kimi:kimi-for-coding refs in the agent bus.",
    )
    moonshot_provider = HarnessProvider(
        provider="moonshot",
        family="remote-openai-compatible",
        base_url=_env("MOONSHOT_OPENAI_BASE_URL", "https://api.moonshot.ai/v1"),
        api_key_env=("MOONSHOT_API_KEY",),
        default_model=_env("GEOSEAL_MOONSHOT_MODEL", "kimi-k2.6"),
        tool_adapter="openai_tool_call",
        local=False,
        pricing_tier="paid",
        capabilities=("chat", "tools-json", "coding", "long-context", "agentic-coding"),
        docs_url="https://platform.kimi.ai/docs/api/overview",
        notes="Moonshot/Kimi OpenAI-compatible API",
    )

    return {
        "ollama": HarnessProvider(
            provider="ollama",
            family="local-openai-compatible",
            base_url=_env("OLLAMA_OPENAI_BASE_URL", "http://127.0.0.1:11434/v1"),
            api_key_env=("OLLAMA_API_KEY",),
            default_model=_env("GEOSEAL_OLLAMA_MODEL", _env("GEOSEAL_PAIR_MODEL_A", "scbe-geoseal-coder:q8")),
            tool_adapter="raw_json_only",
            local=True,
            pricing_tier="free-local",
            capabilities=("chat", "tools-raw-json", "local"),
            notes="free local default",
        ),
        "lmstudio": HarnessProvider(
            provider="lmstudio",
            family="local-openai-compatible",
            base_url=_env("LMSTUDIO_OPENAI_BASE_URL", "http://127.0.0.1:1234/v1"),
            api_key_env=("LMSTUDIO_API_KEY",),
            default_model=_env("GEOSEAL_LMSTUDIO_MODEL", "local-model"),
            tool_adapter="raw_json_only",
            local=True,
            pricing_tier="free-local",
            capabilities=("chat", "tools-raw-json", "local"),
            notes="LM Studio local server",
        ),
        "vllm": HarnessProvider(
            provider="vllm",
            family="local-openai-compatible",
            base_url=_env("VLLM_OPENAI_BASE_URL", "http://127.0.0.1:8000/v1"),
            api_key_env=("VLLM_API_KEY",),
            default_model=_env("GEOSEAL_VLLM_MODEL", "local-model"),
            tool_adapter="qwen_tool_json",
            local=True,
            pricing_tier="free-local",
            capabilities=("chat", "tools-json", "local", "server"),
            notes="vLLM OpenAI-compatible server",
        ),
        "llamacpp": HarnessProvider(
            provider="llamacpp",
            family="local-openai-compatible",
            base_url=_env("LLAMACPP_OPENAI_BASE_URL", "http://127.0.0.1:8080/v1"),
            api_key_env=("LLAMACPP_API_KEY",),
            default_model=_env("GEOSEAL_LLAMACPP_MODEL", "local-model"),
            tool_adapter="raw_json_only",
            local=True,
            pricing_tier="free-local",
            capabilities=("chat", "tools-raw-json", "local"),
            notes="llama.cpp server",
        ),
        "textgenwebui": HarnessProvider(
            provider="textgenwebui",
            family="local-openai-compatible",
            base_url=_env("TEXTGENWEBUI_OPENAI_BASE_URL", "http://127.0.0.1:5000/v1"),
            api_key_env=("TEXTGENWEBUI_API_KEY",),
            default_model=_env("GEOSEAL_TEXTGENWEBUI_MODEL", "local-model"),
            tool_adapter="raw_json_only",
            local=True,
            pricing_tier="free-local",
            capabilities=("chat", "tools-raw-json", "local"),
            notes="text-generation-webui OpenAI extension",
        ),
        "tabbyapi": HarnessProvider(
            provider="tabbyapi",
            family="local-openai-compatible",
            base_url=_env("TABBYAPI_OPENAI_BASE_URL", "http://127.0.0.1:5000/v1"),
            api_key_env=("TABBYAPI_API_KEY",),
            default_model=_env("GEOSEAL_TABBYAPI_MODEL", "local-model"),
            tool_adapter="raw_json_only",
            local=True,
            pricing_tier="free-local",
            capabilities=("chat", "tools-raw-json", "local"),
            notes="TabbyAPI local OpenAI-compatible server",
        ),
        "deepseek": HarnessProvider(
            provider="deepseek",
            family="remote-openai-compatible",
            base_url=_env("DEEPSEEK_OPENAI_BASE_URL", "https://api.deepseek.com/v1"),
            api_key_env=("DEEPSEEK_API_KEY",),
            default_model=_env("GEOSEAL_DEEPSEEK_MODEL", "deepseek-chat"),
            tool_adapter="deepseek_tool_json",
            local=False,
            pricing_tier="paid-low-cost",
            capabilities=("chat", "tools-json", "coding"),
            docs_url="https://api-docs.deepseek.com/",
            notes="DeepSeek API",
        ),
        "groq": HarnessProvider(
            provider="groq",
            family="remote-openai-compatible",
            base_url=_env("GROQ_OPENAI_BASE_URL", "https://api.groq.com/openai/v1"),
            api_key_env=("GROQ_API_KEY",),
            default_model=_env("GEOSEAL_GROQ_MODEL", "llama-3.3-70b-versatile"),
            tool_adapter="openai_tool_call",
            local=False,
            pricing_tier="free-tier",
            capabilities=("chat", "tools-json", "fast-inference"),
            docs_url="https://console.groq.com/docs/api-reference",
            notes="Groq OpenAI-compatible API",
        ),
        "together": HarnessProvider(
            provider="together",
            family="remote-openai-compatible",
            base_url=_env("TOGETHER_OPENAI_BASE_URL", "https://api.together.xyz/v1"),
            api_key_env=("TOGETHER_API_KEY",),
            default_model=_env("GEOSEAL_TOGETHER_MODEL", "zai-org/GLM-5"),
            tool_adapter="openai_tool_call",
            local=False,
            pricing_tier="paid-or-free-credits",
            capabilities=("chat", "tools-json", "open-models"),
            docs_url="https://docs.together.ai/docs/openai-api-compatibility",
            notes="Together AI OpenAI-compatible API",
        ),
        "mistral": HarnessProvider(
            provider="mistral",
            family="remote-openai-compatible",
            base_url=_env("MISTRAL_OPENAI_BASE_URL", "https://api.mistral.ai/v1"),
            api_key_env=("MISTRAL_API_KEY",),
            default_model=_env("GEOSEAL_MISTRAL_MODEL", "codestral-latest"),
            tool_adapter="openai_tool_call",
            local=False,
            pricing_tier="paid",
            capabilities=("chat", "tools-json", "coding"),
            docs_url="https://docs.mistral.ai/api/endpoint/chat",
            notes="Mistral chat completions API",
        ),
        "cerebras": HarnessProvider(
            provider="cerebras",
            family="remote-openai-compatible",
            base_url=_env("CEREBRAS_OPENAI_BASE_URL", "https://api.cerebras.ai/v1"),
            api_key_env=("CEREBRAS_API_KEY",),
            default_model=_env("GEOSEAL_CEREBRAS_MODEL", "qwen-3-coder-480b"),
            tool_adapter="openai_tool_call",
            local=False,
            pricing_tier="free-tier-or-paid",
            capabilities=("chat", "tools-json", "fast-inference"),
            docs_url="https://inference-docs.cerebras.ai/",
            notes="Cerebras Inference OpenAI-compatible API",
        ),
        "fireworks": HarnessProvider(
            provider="fireworks",
            family="remote-openai-compatible",
            base_url=_env("FIREWORKS_OPENAI_BASE_URL", "https://api.fireworks.ai/inference/v1"),
            api_key_env=("FIREWORKS_API_KEY",),
            default_model=_env("GEOSEAL_FIREWORKS_MODEL", "accounts/fireworks/models/llama-v3p1-8b-instruct"),
            tool_adapter="openai_tool_call",
            local=False,
            pricing_tier="paid",
            capabilities=("chat", "tools-json", "open-models"),
            docs_url="https://docs.fireworks.ai/tools-sdks/openai-compatibility",
            notes="Fireworks AI OpenAI-compatible API",
        ),
        "sambanova": HarnessProvider(
            provider="sambanova",
            family="remote-openai-compatible",
            base_url=_env("SAMBANOVA_OPENAI_BASE_URL", "https://api.sambanova.ai/v1"),
            api_key_env=("SAMBANOVA_API_KEY",),
            default_model=_env("GEOSEAL_SAMBANOVA_MODEL", "Meta-Llama-3.1-8B-Instruct"),
            tool_adapter="openai_tool_call",
            local=False,
            pricing_tier="free-tier-or-paid",
            capabilities=("chat", "tools-json", "fast-inference"),
            docs_url="https://cloud.sambanova.ai/",
            notes="SambaNova Cloud OpenAI-compatible API",
        ),
        "gemini": HarnessProvider(
            provider="gemini",
            family="remote-openai-compatible",
            base_url=_env("GEMINI_OPENAI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai"),
            api_key_env=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
            default_model=_env("GEOSEAL_GEMINI_MODEL", "gemini-2.5-flash"),
            tool_adapter="openai_tool_call",
            local=False,
            pricing_tier="free-tier-or-paid",
            capabilities=("chat", "tools-json", "long-context"),
            docs_url="https://ai.google.dev/gemini-api/docs/openai",
            notes="Gemini OpenAI-compatible endpoint",
        ),
        "xai": HarnessProvider(
            provider="xai",
            family="remote-openai-compatible",
            base_url=_env("XAI_OPENAI_BASE_URL", "https://api.x.ai/v1"),
            api_key_env=("XAI_API_KEY",),
            default_model=_env("GEOSEAL_XAI_MODEL", "grok-4"),
            tool_adapter="openai_tool_call",
            local=False,
            pricing_tier="paid",
            capabilities=("chat", "tools-json"),
            docs_url="https://docs.x.ai/developers/model-capabilities/legacy/chat-completions",
            notes="xAI OpenAI-compatible API",
        ),
        "moonshot": moonshot_provider,
        "kimi": kimi_provider,
        "kimi_code": kimi_code_provider,
        "openrouter": HarnessProvider(
            provider="openrouter",
            family="remote-openai-compatible",
            base_url=_env("OPENROUTER_OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
            api_key_env=("OPENROUTER_API_KEY",),
            default_model=_env("GEOSEAL_OPENROUTER_MODEL", "qwen/qwen3-coder"),
            tool_adapter="openai_tool_call",
            local=False,
            pricing_tier="aggregator-mixed",
            capabilities=("chat", "tools-json", "model-router"),
            notes="OpenRouter model gateway",
        ),
        "huggingface": HarnessProvider(
            provider="huggingface",
            family="remote-openai-compatible",
            base_url=_env("HF_ROUTER_CHAT_URL", "https://router.huggingface.co/v1/chat/completions"),
            api_key_env=("HF_TOKEN", "HUGGINGFACE_TOKEN", "HUGGING_FACE_HUB_TOKEN"),
            default_model=_env("GEOSEAL_HF_MODEL", "Qwen/Qwen2.5-Coder-7B-Instruct"),
            tool_adapter="openai_tool_call",
            local=False,
            pricing_tier="free-tier-or-paid",
            capabilities=("chat", "tools-json", "open-models"),
            docs_url="https://huggingface.co/docs/inference-providers/index",
            notes="Hugging Face Inference Router or endpoint",
        ),
        "nvidia": HarnessProvider(
            provider="nvidia",
            family="remote-openai-compatible",
            base_url=_env("NVIDIA_OPENAI_BASE_URL", "https://integrate.api.nvidia.com/v1"),
            api_key_env=("NVIDIA_API_KEY", "NVIDIA_API_KEY_1", "NVIDIA_API_KEY_2"),
            default_model=_env("GEOSEAL_NVIDIA_MODEL", "qwen/qwen3-coder-480b-a35b-instruct"),
            tool_adapter="openai_tool_call",
            local=False,
            pricing_tier="free-tier-or-paid",
            capabilities=("chat", "tools-json", "large-models", "coding", "reasoning"),
            docs_url="https://docs.api.nvidia.com/nim/reference/llm-apis",
            notes="NVIDIA API Catalog / NIM OpenAI-compatible endpoint",
        ),
        "openai": HarnessProvider(
            provider="openai",
            family="remote-openai",
            base_url=_env("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key_env=("OPENAI_API_KEY",),
            default_model=_env("GEOSEAL_OPENAI_MODEL", "gpt-4.1-mini"),
            tool_adapter="openai_tool_call",
            local=False,
            pricing_tier="paid",
            capabilities=("chat", "tools-json"),
            docs_url="https://platform.openai.com/docs/api-reference/chat",
            notes="OpenAI-compatible fallback",
        ),
    }


def default_provider_id() -> str:
    value = os.getenv("GEOSEAL_HARNESS_PROVIDER", "").strip().lower()
    return value or "ollama"


def parse_model_ref(ref: str | None, *, default_provider: str | None = None) -> tuple[str, str | None]:
    """Parse ``provider:model`` refs while preserving plain legacy model names."""

    raw = (ref or "").strip()
    provider = (default_provider or default_provider_id()).strip().lower()
    if ":" in raw:
        head, tail = raw.split(":", 1)
        if head.strip().lower() in provider_registry() and tail.strip():
            return head.strip().lower(), tail.strip()
    return provider, raw or None


def resolve_provider_model(
    model_ref: str | None,
    *,
    default_provider: str | None = None,
) -> tuple[HarnessProvider, str]:
    registry = provider_registry()
    provider_id, model = parse_model_ref(model_ref, default_provider=default_provider)
    provider = registry.get(provider_id)
    if provider is None:
        raise ValueError(f"unknown harness provider: {provider_id}")
    return provider, model or provider.default_model


def lane_switch_cost(left: str, right: str) -> int:
    if left == right:
        return 0
    return LANE_SWITCH_COSTS.get((left, right), 6)


def _signal_is_valid(signal: str | None, lane_path: tuple[str, ...]) -> bool:
    if not signal:
        return False
    cleaned = signal.strip().lower()
    if not cleaned:
        return False
    if cleaned.startswith("lane-change:") or cleaned.startswith("provider-pair:"):
        return all(provider in cleaned for provider in lane_path)
    return False


def evaluate_lane_switch(
    model_refs: list[str],
    *,
    signal: str | None = None,
) -> LaneSwitchVerdict:
    """Evaluate provider lane switching for a model pair/workflow.

    Same-provider fan-out is free. Cross-provider fan-out is allowed only when
    the caller signals the lane change, similar to a turn signal before moving
    between traffic lanes. Missing/invalid signals should be surfaced in
    MergeReport evidence and should not auto-promote.
    """

    providers = tuple(resolve_provider_model(ref)[0].provider for ref in model_refs)
    if len(providers) <= 1:
        return LaneSwitchVerdict(
            ok=True,
            signal_required=False,
            signal_present=False,
            cost=0,
            lane_path=providers,
            reason="single_lane",
        )
    cost = sum(lane_switch_cost(a, b) for a, b in zip(providers, providers[1:]))
    requires_signal = any(a != b for a, b in zip(providers, providers[1:]))
    signal_ok = _signal_is_valid(signal, providers)
    ok = (not requires_signal) or signal_ok
    reason = "properly_signaled" if ok and requires_signal else "same_lane" if ok else "missing_or_invalid_signal"
    return LaneSwitchVerdict(
        ok=ok,
        signal_required=requires_signal,
        signal_present=signal_ok,
        cost=cost,
        lane_path=providers,
        reason=reason,
    )


def compact_system_prompt(*, phase: str, tongue: str, domain: str, expected_output: str, adapter: str) -> str:
    """Small model-facing system prompt for local/free model harness mode."""

    return (
        "You are an SCBE packet worker. "
        f"phase={phase}; route={tongue}/{domain}; expected_output={expected_output}; "
        f"tool_adapter={adapter}. "
        "Reply only with the requested compact JSON or verdict. No prose."
    )


__all__ = [
    "HarnessProvider",
    "LaneSwitchVerdict",
    "compact_system_prompt",
    "default_provider_id",
    "evaluate_lane_switch",
    "lane_switch_cost",
    "parse_model_ref",
    "provider_registry",
    "resolve_provider_model",
]
