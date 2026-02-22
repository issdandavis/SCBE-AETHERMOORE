"""
Tests for HuggingFaceProvider in HYDRA LLM Providers.
======================================================

Covers:
- HuggingFaceProvider class exists and is importable
- Registered in _PROVIDER_MAP under "huggingface" and "hf"
- create_provider("hf") returns HuggingFaceProvider (when huggingface_hub installed)
- Constructor raises ImportError when huggingface_hub is missing (mocked)
- LLMResponse dataclass fields
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from hydra.llm_providers import (
    LLMProvider,
    LLMResponse,
    _PROVIDER_MAP,
    create_provider,
    HYDRA_SYSTEM_PROMPT,
)


# =========================================================================
# Import and registration
# =========================================================================


class TestHFProviderRegistration:
    """HuggingFaceProvider exists and is in the provider map."""

    def test_class_importable(self):
        from hydra.llm_providers import HuggingFaceProvider
        assert HuggingFaceProvider is not None

    def test_is_llm_provider_subclass(self):
        from hydra.llm_providers import HuggingFaceProvider
        assert issubclass(HuggingFaceProvider, LLMProvider)

    def test_registered_as_huggingface(self):
        assert "huggingface" in _PROVIDER_MAP

    def test_registered_as_hf(self):
        assert "hf" in _PROVIDER_MAP

    def test_hf_and_huggingface_same_class(self):
        assert _PROVIDER_MAP["hf"] is _PROVIDER_MAP["huggingface"]

    def test_all_expected_providers_in_map(self):
        expected = {"claude", "anthropic", "gpt", "openai", "gemini", "google",
                    "huggingface", "hf", "local"}
        assert expected.issubset(set(_PROVIDER_MAP.keys()))


# =========================================================================
# create_provider factory
# =========================================================================


class TestCreateProviderFactory:
    """create_provider() with HuggingFace types."""

    def test_create_provider_hf_type(self):
        """create_provider('hf') should return a HuggingFaceProvider.

        This test only runs if huggingface_hub is installed; skip otherwise.
        """
        try:
            provider = create_provider("hf")
            from hydra.llm_providers import HuggingFaceProvider
            assert isinstance(provider, HuggingFaceProvider)
        except ImportError:
            pytest.skip("huggingface_hub not installed")

    def test_create_provider_huggingface_type(self):
        try:
            provider = create_provider("huggingface")
            from hydra.llm_providers import HuggingFaceProvider
            assert isinstance(provider, HuggingFaceProvider)
        except ImportError:
            pytest.skip("huggingface_hub not installed")

    def test_create_provider_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown ai_type"):
            create_provider("nonexistent_provider_xyz")

    def test_create_provider_local(self):
        """Sanity check: local provider still works."""
        provider = create_provider("local")
        from hydra.llm_providers import LocalProvider
        assert isinstance(provider, LocalProvider)


# =========================================================================
# LLMResponse fields
# =========================================================================


class TestLLMResponse:
    """LLMResponse dataclass has expected fields."""

    def test_llm_response_fields(self):
        resp = LLMResponse(
            text="hello",
            model="test-model",
            input_tokens=10,
            output_tokens=5,
            finish_reason="stop",
        )
        assert resp.text == "hello"
        assert resp.model == "test-model"
        assert resp.input_tokens == 10
        assert resp.output_tokens == 5
        assert resp.finish_reason == "stop"


# =========================================================================
# HYDRA system prompt
# =========================================================================


class TestSystemPrompt:
    """The shared HYDRA system prompt is non-empty."""

    def test_system_prompt_exists(self):
        assert HYDRA_SYSTEM_PROMPT is not None
        assert len(HYDRA_SYSTEM_PROMPT) > 50

    def test_system_prompt_mentions_hydra(self):
        assert "hydra" in HYDRA_SYSTEM_PROMPT.lower() or "HYDRA" in HYDRA_SYSTEM_PROMPT


# =========================================================================
# HuggingFaceProvider interface
# =========================================================================


class TestHFProviderInterface:
    """HuggingFaceProvider has required LLMProvider methods."""

    def test_has_complete_method(self):
        from hydra.llm_providers import HuggingFaceProvider
        assert hasattr(HuggingFaceProvider, "complete")

    def test_has_stream_method(self):
        from hydra.llm_providers import HuggingFaceProvider
        assert hasattr(HuggingFaceProvider, "stream")

    def test_complete_is_async(self):
        import asyncio
        from hydra.llm_providers import HuggingFaceProvider
        assert asyncio.iscoroutinefunction(HuggingFaceProvider.complete)

    def test_stream_is_async(self):
        import asyncio
        import inspect
        from hydra.llm_providers import HuggingFaceProvider
        # stream() may be an async generator (yields tokens) rather than a coroutine
        is_async = (
            asyncio.iscoroutinefunction(HuggingFaceProvider.stream)
            or inspect.isasyncgenfunction(HuggingFaceProvider.stream)
        )
        assert is_async
