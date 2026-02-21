"""
HYDRA LLM Providers - Real AI API Integration
===============================================

Provides concrete LLM provider implementations for the HYDRA system,
enabling any head to call real AI APIs (Claude, GPT, Gemini) or a
local OpenAI-compatible endpoint.

Each provider:
- Handles missing packages gracefully with clear install instructions
- Retries on rate limits with exponential backoff (3 retries: 1s/2s/4s)
- Injects the HYDRA system prompt by default
- Returns structured LLMResponse dataclasses

Usage:
    provider = create_provider("claude")
    response = await provider.complete("Plan a web scrape of example.com")

    async for chunk in provider.stream("Explain SCBE governance"):
        print(chunk, end="")
"""

import asyncio
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HYDRA_SYSTEM_PROMPT = (
    "You are a HYDRA agent operating under SCBE governance. "
    "Plan actions clearly. Respond with structured JSON when asked "
    "for action plans."
)

_RETRY_DELAYS = [1.0, 2.0, 4.0]  # seconds for exponential back-off


# ---------------------------------------------------------------------------
# Response dataclass
# ---------------------------------------------------------------------------

@dataclass
class LLMResponse:
    """Structured response from an LLM provider."""

    text: str
    model: str
    input_tokens: int
    output_tokens: int
    finish_reason: str


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class LLMProvider(ABC):
    """Abstract base class for HYDRA LLM providers."""

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Send a single completion request and return the full response.

        Args:
            prompt: The user/instruction prompt.
            system: Optional system prompt (defaults to HYDRA_SYSTEM_PROMPT).
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.

        Returns:
            An LLMResponse with text, token counts, and metadata.
        """
        ...

    @abstractmethod
    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream completion tokens one chunk at a time.

        Args:
            prompt: The user/instruction prompt.
            system: Optional system prompt (defaults to HYDRA_SYSTEM_PROMPT).
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.

        Yields:
            Text chunks as they arrive from the API.
        """
        ...  # pragma: no cover
        # yield is required for the type-checker to treat this as AsyncIterator
        if False:
            yield ""  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------

async def _retry_with_backoff(coro_factory, retries: int = 3):
    """Execute an async callable with exponential back-off on failure.

    Args:
        coro_factory: A zero-argument callable that returns an awaitable.
        retries: Number of retry attempts (delays taken from _RETRY_DELAYS).

    Returns:
        The result of the awaitable on success.

    Raises:
        The last exception if all retries are exhausted.
    """
    last_exc: Optional[Exception] = None
    for attempt in range(retries):
        try:
            return await coro_factory()
        except Exception as exc:
            last_exc = exc
            exc_name = type(exc).__name__
            # Detect rate-limit errors from various SDKs
            is_rate_limit = (
                "rate" in exc_name.lower()
                or "ratelimit" in exc_name.lower()
                or getattr(exc, "status_code", None) == 429
                or "429" in str(exc)
            )
            if is_rate_limit and attempt < retries - 1:
                delay = _RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)]
                print(
                    f"[LLM] Rate limited (attempt {attempt + 1}/{retries}), "
                    f"retrying in {delay}s ..."
                )
                await asyncio.sleep(delay)
            else:
                raise
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Claude (Anthropic)
# ---------------------------------------------------------------------------

class ClaudeProvider(LLMProvider):
    """LLM provider backed by the Anthropic Messages API.

    Requires:
        pip install anthropic

    Environment:
        ANTHROPIC_API_KEY - your Anthropic API key
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: Optional[str] = None,
    ):
        try:
            import anthropic  # noqa: F401
        except ImportError:
            raise ImportError(
                "The 'anthropic' package is required for ClaudeProvider.\n"
                "Install it with:  pip install anthropic"
            )

        self.model = model
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not self._api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. Provide it via the api_key "
                "parameter or set the ANTHROPIC_API_KEY environment variable."
            )

        import anthropic

        self._client = anthropic.AsyncAnthropic(api_key=self._api_key)

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Send a completion request to the Anthropic Messages API."""
        system_prompt = system if system is not None else HYDRA_SYSTEM_PROMPT

        async def _call():
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(
                block.text for block in response.content if hasattr(block, "text")
            )
            return LLMResponse(
                text=text,
                model=response.model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                finish_reason=response.stop_reason or "end_turn",
            )

        return await _retry_with_backoff(_call)

    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream tokens from the Anthropic Messages API."""
        system_prompt = system if system is not None else HYDRA_SYSTEM_PROMPT

        async with self._client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for text in stream.text_stream:
                yield text


# ---------------------------------------------------------------------------
# OpenAI / GPT
# ---------------------------------------------------------------------------

class OpenAIProvider(LLMProvider):
    """LLM provider backed by the OpenAI Chat Completions API.

    Requires:
        pip install openai

    Environment:
        OPENAI_API_KEY - your OpenAI API key
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        try:
            import openai  # noqa: F401
        except ImportError:
            raise ImportError(
                "The 'openai' package is required for OpenAIProvider.\n"
                "Install it with:  pip install openai"
            )

        self.model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self._api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Provide it via the api_key "
                "parameter or set the OPENAI_API_KEY environment variable."
            )

        import openai

        kwargs: Dict[str, Any] = {"api_key": self._api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = openai.AsyncOpenAI(**kwargs)

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Send a completion request to the OpenAI Chat API."""
        system_prompt = system if system is not None else HYDRA_SYSTEM_PROMPT
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        async def _call():
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            choice = response.choices[0]
            usage = response.usage
            return LLMResponse(
                text=choice.message.content or "",
                model=response.model,
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                finish_reason=choice.finish_reason or "stop",
            )

        return await _retry_with_backoff(_call)

    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream tokens from the OpenAI Chat API."""
        system_prompt = system if system is not None else HYDRA_SYSTEM_PROMPT
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )

        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# ---------------------------------------------------------------------------
# Google Gemini
# ---------------------------------------------------------------------------

class GeminiProvider(LLMProvider):
    """LLM provider backed by the Google GenAI SDK.

    Requires:
        pip install google-genai

    Environment:
        GOOGLE_API_KEY - your Google AI API key
    """

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        api_key: Optional[str] = None,
    ):
        try:
            from google import genai  # noqa: F401
        except ImportError:
            raise ImportError(
                "The 'google-genai' package is required for GeminiProvider.\n"
                "Install it with:  pip install google-genai"
            )

        self.model = model
        self._api_key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        if not self._api_key:
            raise ValueError(
                "GOOGLE_API_KEY is not set. Provide it via the api_key "
                "parameter or set the GOOGLE_API_KEY environment variable."
            )

        from google import genai

        self._client = genai.Client(api_key=self._api_key)

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Send a completion request to the Gemini API."""
        from google.genai import types as genai_types

        system_prompt = system if system is not None else HYDRA_SYSTEM_PROMPT

        config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
            temperature=temperature,
        )

        async def _call():
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=config,
            )
            text = response.text or ""
            # Token counts from usage_metadata when available
            usage = getattr(response, "usage_metadata", None)
            input_tokens = getattr(usage, "prompt_token_count", 0) or 0
            output_tokens = getattr(usage, "candidates_token_count", 0) or 0
            # Determine finish reason
            finish_reason = "stop"
            if response.candidates:
                raw_reason = getattr(
                    response.candidates[0], "finish_reason", None
                )
                if raw_reason is not None:
                    finish_reason = str(raw_reason)
            return LLMResponse(
                text=text,
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                finish_reason=finish_reason,
            )

        return await _retry_with_backoff(_call)

    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream tokens from the Gemini API.

        The google-genai SDK's streaming is synchronous, so we delegate
        to a thread and yield chunks as they arrive.
        """
        from google.genai import types as genai_types

        system_prompt = system if system is not None else HYDRA_SYSTEM_PROMPT

        config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
            temperature=temperature,
        )

        # google-genai stream is synchronous; bridge via queue
        queue: asyncio.Queue[Optional[str]] = asyncio.Queue()

        def _generate():
            try:
                for chunk in self._client.models.generate_content_stream(
                    model=self.model,
                    contents=prompt,
                    config=config,
                ):
                    if chunk.text:
                        asyncio.get_event_loop().call_soon_threadsafe(
                            queue.put_nowait, chunk.text
                        )
            finally:
                asyncio.get_event_loop().call_soon_threadsafe(
                    queue.put_nowait, None
                )

        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, _generate)

        while True:
            item = await queue.get()
            if item is None:
                break
            yield item


# ---------------------------------------------------------------------------
# Local (OpenAI-compatible endpoint)
# ---------------------------------------------------------------------------

class LocalProvider(LLMProvider):
    """LLM provider for local OpenAI-compatible servers (LM Studio, Ollama, vLLM, etc.).

    Requires:
        pip install openai

    Defaults to http://localhost:1234/v1 which is the LM Studio default.
    No API key is required by default (uses "local" as a placeholder).
    """

    def __init__(
        self,
        model: str = "local-model",
        base_url: str = "http://localhost:1234/v1",
        api_key: str = "local",
    ):
        try:
            import openai  # noqa: F401
        except ImportError:
            raise ImportError(
                "The 'openai' package is required for LocalProvider.\n"
                "Install it with:  pip install openai"
            )

        self.model = model
        self._base_url = base_url

        import openai

        self._client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Send a completion request to the local OpenAI-compatible endpoint."""
        system_prompt = system if system is not None else HYDRA_SYSTEM_PROMPT
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        async def _call():
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            choice = response.choices[0]
            usage = response.usage
            return LLMResponse(
                text=choice.message.content or "",
                model=response.model or self.model,
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                finish_reason=choice.finish_reason or "stop",
            )

        return await _retry_with_backoff(_call)

    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream tokens from the local OpenAI-compatible endpoint."""
        system_prompt = system if system is not None else HYDRA_SYSTEM_PROMPT
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )

        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

# Canonical mapping from short name -> provider class
_PROVIDER_MAP: Dict[str, type] = {
    "claude": ClaudeProvider,
    "anthropic": ClaudeProvider,
    "gpt": OpenAIProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "google": GeminiProvider,
    "local": LocalProvider,
}


def create_provider(
    ai_type: str,
    model: Optional[str] = None,
    **kwargs: Any,
) -> LLMProvider:
    """Factory function to create an LLM provider by short name.

    Args:
        ai_type: One of "claude", "anthropic", "gpt", "openai",
                 "gemini", "google", or "local".
        model: Optional model override (each provider has a sensible default).
        **kwargs: Additional keyword arguments forwarded to the provider
                  constructor (e.g. api_key, base_url).

    Returns:
        An initialized LLMProvider instance.

    Raises:
        ValueError: If ai_type is not recognized.

    Examples:
        >>> provider = create_provider("claude")
        >>> provider = create_provider("gpt", model="gpt-4-turbo")
        >>> provider = create_provider("local", base_url="http://gpu-box:5000/v1")
    """
    key = ai_type.strip().lower()
    cls = _PROVIDER_MAP.get(key)

    if cls is None:
        supported = ", ".join(sorted(_PROVIDER_MAP.keys()))
        raise ValueError(
            f"Unknown ai_type '{ai_type}'. Supported types: {supported}"
        )

    if model is not None:
        kwargs["model"] = model

    return cls(**kwargs)
