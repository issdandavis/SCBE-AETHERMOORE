"""
@file ai_ports.py
@module spiral-word-app/ai_ports
@layer Layer 12, Layer 13
@component Pluggable AI Integration Ports

Configurable AI provider integrations with SCBE governance hooks.
Each provider is a callable that takes a prompt and returns generated text.
New providers are registered via register_provider() or config.

Supported out-of-the-box:
- OpenAI (GPT-4, etc.)
- Anthropic (Claude)
- Custom HTTP endpoints
- Echo (testing/dev)
"""

import json
import logging
import os
from typing import Callable, Dict, Optional

logger = logging.getLogger("spiralword.ai_ports")


# Type alias for AI provider callables
AIProvider = Callable[[str, Optional[dict]], str]


class AIPortRegistry:
    """
    Registry of pluggable AI providers.

    Each port is a (name -> callable) mapping. The callable signature is:
        provider(prompt: str, options: dict | None) -> str

    Governance checks are applied before dispatching to any provider.
    """

    def __init__(self):
        self._providers: Dict[str, AIProvider] = {}
        self._default: Optional[str] = None
        # Register built-in providers
        self._register_builtins()

    def _register_builtins(self):
        """Register built-in provider adapters."""
        self.register("echo", _echo_provider)
        self.register("openai", _openai_provider)
        self.register("anthropic", _anthropic_provider)
        self.register("custom", _custom_provider)
        self._default = "echo"

    def register(self, name: str, provider: AIProvider):
        """Register a new AI provider."""
        self._providers[name] = provider
        logger.info("Registered AI port: %s", name)

    def set_default(self, name: str):
        if name not in self._providers:
            raise ValueError(f"Unknown provider: {name}")
        self._default = name

    def list_providers(self) -> list:
        return list(self._providers.keys())

    def call(
        self,
        prompt: str,
        provider: str = None,
        options: dict = None,
    ) -> str:
        """
        Call an AI provider with governance pre-check.

        Args:
            prompt: The user/AI prompt.
            provider: Provider name (uses default if None).
            options: Provider-specific options (model, temperature, etc.).

        Returns:
            Generated text from the AI provider.
        """
        from governance import classify_intent, check_governance

        name = provider or self._default
        if name not in self._providers:
            raise ValueError(f"Unknown AI provider: {name}. Available: {self.list_providers()}")

        # L12: Intent classification
        tongue, confidence = classify_intent(prompt)
        logger.info("AI call: provider=%s tongue=%s conf=%.2f", name, tongue, confidence)

        # L13: Governance gate
        allowed, reason = check_governance("edit", prompt)
        if not allowed:
            logger.warning("AI call blocked by governance: %s", reason)
            return f"[BLOCKED] {reason}"

        # Dispatch to provider
        try:
            result = self._providers[name](prompt, options)
            return result
        except Exception:
            logger.exception("AI provider %s failed", name)
            return f"[ERROR] Provider {name} failed"


# ---------------------------------------------------------------------------
# Built-in Provider Implementations
# ---------------------------------------------------------------------------


def _echo_provider(prompt: str, options: dict = None) -> str:
    """Echo provider for testing. Returns the prompt back."""
    return f"[echo] {prompt}"


def _openai_provider(prompt: str, options: dict = None) -> str:
    """
    OpenAI provider (GPT-4, etc.).

    Requires OPENAI_API_KEY in environment.
    Options: model (default gpt-4), temperature, max_tokens.
    """
    try:
        import openai
    except ImportError:
        return "[ERROR] openai package not installed. Run: pip install openai"

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "[ERROR] OPENAI_API_KEY not set in environment"

    opts = options or {}
    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=opts.get("model", "gpt-4"),
        messages=[{"role": "user", "content": prompt}],
        temperature=opts.get("temperature", 0.7),
        max_tokens=opts.get("max_tokens", 1024),
    )
    return response.choices[0].message.content


def _anthropic_provider(prompt: str, options: dict = None) -> str:
    """
    Anthropic provider (Claude).

    Requires ANTHROPIC_API_KEY in environment.
    Options: model (default claude-sonnet-4-20250514), max_tokens.
    """
    try:
        import anthropic
    except ImportError:
        return "[ERROR] anthropic package not installed. Run: pip install anthropic"

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "[ERROR] ANTHROPIC_API_KEY not set in environment"

    opts = options or {}
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=opts.get("model", "claude-sonnet-4-20250514"),
        max_tokens=opts.get("max_tokens", 1024),
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def _custom_provider(prompt: str, options: dict = None) -> str:
    """
    Custom HTTP endpoint provider.

    Set CUSTOM_AI_ENDPOINT in environment.
    Sends POST with {"prompt": ..., "options": ...}, expects {"text": ...}.
    """
    try:
        import httpx
    except ImportError:
        return "[ERROR] httpx package not installed. Run: pip install httpx"

    endpoint = os.environ.get("CUSTOM_AI_ENDPOINT")
    if not endpoint:
        return "[ERROR] CUSTOM_AI_ENDPOINT not set in environment"

    opts = options or {}
    response = httpx.post(
        endpoint,
        json={"prompt": prompt, "options": opts},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json().get("text", "")


# Module-level registry
ai_ports = AIPortRegistry()
