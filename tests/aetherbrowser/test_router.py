"""Tests for the OctoArmor model router."""

import pytest
from src.aetherbrowser.router import OctoArmorRouter, ModelProvider, TaskComplexity


class TestComplexityScoring:
    def test_simple_task(self):
        router = OctoArmorRouter()
        score = router.score_complexity("What time is it?")
        assert score == TaskComplexity.LOW

    def test_complex_task(self):
        router = OctoArmorRouter()
        score = router.score_complexity(
            "Compare the security models of 5 competitors, analyze their governance "
            "frameworks, and produce a structured report with citations"
        )
        assert score == TaskComplexity.HIGH

    def test_medium_task(self):
        router = OctoArmorRouter()
        score = router.score_complexity(
            "Summarize the main points of this article about AI safety"
        )
        assert score == TaskComplexity.MEDIUM


class TestModelSelection:
    def test_cheapest_for_low(self):
        router = OctoArmorRouter()
        model = router.select_model(TaskComplexity.LOW, role="DR")
        assert model.provider == ModelProvider.LOCAL
        assert model.selection_reason == "local_first_low_complexity"

    def test_strongest_for_high(self):
        router = OctoArmorRouter(
            enabled_providers={
                ModelProvider.LOCAL: True,
                ModelProvider.HAIKU: True,
                ModelProvider.SONNET: True,
                ModelProvider.OPUS: True,
                ModelProvider.FLASH: True,
                ModelProvider.GROK: False,
                ModelProvider.HUGGINGFACE: False,
            }
        )
        model = router.select_model(TaskComplexity.HIGH, role="KO")
        assert model.provider in (ModelProvider.OPUS, ModelProvider.SONNET)
        assert model.selection_reason == "preferred_provider"

    def test_default_preferences(self):
        router = OctoArmorRouter()
        prefs = router.get_preferences()
        assert prefs["KO"] == ModelProvider.OPUS
        assert prefs["AV"] == ModelProvider.FLASH
        assert prefs["DR"] == ModelProvider.HAIKU

    def test_custom_preference(self):
        router = OctoArmorRouter(preferences={"KO": ModelProvider.SONNET})
        prefs = router.get_preferences()
        assert prefs["KO"] == ModelProvider.SONNET

    def test_request_scoped_preference_override_wins(self):
        router = OctoArmorRouter(
            enabled_providers={provider: True for provider in ModelProvider}
        )
        model = router.select_model(
            TaskComplexity.LOW,
            role="KO",
            preference_overrides={"KO": "sonnet"},
        )
        assert model.provider == ModelProvider.SONNET
        assert model.selection_reason == "preference_override"

    def test_request_scoped_preference_respects_disabled_cascade(self):
        router = OctoArmorRouter(
            enabled_providers={
                ModelProvider.LOCAL: True,
                ModelProvider.HAIKU: False,
                ModelProvider.SONNET: False,
                ModelProvider.OPUS: False,
                ModelProvider.FLASH: False,
                ModelProvider.GROK: False,
                ModelProvider.HUGGINGFACE: False,
            }
        )
        with pytest.raises(RuntimeError, match="auto-cascade disabled"):
            router.select_model(
                TaskComplexity.HIGH,
                role="KO",
                preference_overrides={"KO": "sonnet"},
                allow_fallback=False,
            )


class TestCascade:
    def test_cascade_on_rate_limit(self):
        router = OctoArmorRouter(
            enabled_providers={
                ModelProvider.LOCAL: True,
                ModelProvider.HAIKU: True,
                ModelProvider.SONNET: True,
                ModelProvider.OPUS: True,
                ModelProvider.FLASH: True,
                ModelProvider.GROK: True,
                ModelProvider.HUGGINGFACE: True,
            }
        )
        router.mark_rate_limited(ModelProvider.OPUS)
        model = router.select_model(TaskComplexity.HIGH, role="KO")
        assert model.provider != ModelProvider.OPUS

    def test_cascade_clears_after_window(self):
        router = OctoArmorRouter(
            enabled_providers={
                ModelProvider.LOCAL: True,
                ModelProvider.HAIKU: True,
                ModelProvider.SONNET: True,
                ModelProvider.OPUS: True,
                ModelProvider.FLASH: True,
                ModelProvider.GROK: True,
                ModelProvider.HUGGINGFACE: True,
            }
        )
        router.mark_rate_limited(ModelProvider.OPUS, window_sec=0)
        model = router.select_model(TaskComplexity.HIGH, role="KO")
        assert model.provider == ModelProvider.OPUS

    def test_all_limited_raises(self):
        router = OctoArmorRouter(
            enabled_providers={provider: True for provider in ModelProvider}
        )
        for p in ModelProvider:
            router.mark_rate_limited(p)
        with pytest.raises(
            RuntimeError, match="All models rate-limited or unavailable"
        ):
            router.select_model(TaskComplexity.LOW, role="DR")

    def test_provider_status_reports_missing_env(self):
        router = OctoArmorRouter(
            enabled_providers={
                ModelProvider.LOCAL: True,
                ModelProvider.HAIKU: False,
                ModelProvider.SONNET: False,
                ModelProvider.OPUS: False,
                ModelProvider.FLASH: False,
                ModelProvider.GROK: False,
                ModelProvider.HUGGINGFACE: False,
            }
        )
        status = router.provider_status_snapshot()
        assert status["local"]["available"] is True
        assert status["local"]["family"] == "local"
        assert status["haiku"]["available"] is False

    def test_provider_status_reports_huggingface_family(self):
        router = OctoArmorRouter(
            enabled_providers={provider: True for provider in ModelProvider}
        )
        status = router.provider_status_snapshot()
        assert status["huggingface"]["family"] == "huggingface"
