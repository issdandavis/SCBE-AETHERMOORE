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
        score = router.score_complexity("Summarize the main points of this article about AI safety")
        assert score == TaskComplexity.MEDIUM

class TestModelSelection:
    def test_cheapest_for_low(self):
        router = OctoArmorRouter()
        model = router.select_model(TaskComplexity.LOW, role="DR")
        assert model.provider in (ModelProvider.HAIKU, ModelProvider.FLASH)

    def test_strongest_for_high(self):
        router = OctoArmorRouter()
        model = router.select_model(TaskComplexity.HIGH, role="KO")
        assert model.provider in (ModelProvider.OPUS, ModelProvider.SONNET)

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

class TestCascade:
    def test_cascade_on_rate_limit(self):
        router = OctoArmorRouter()
        router.mark_rate_limited(ModelProvider.OPUS)
        model = router.select_model(TaskComplexity.HIGH, role="KO")
        assert model.provider != ModelProvider.OPUS

    def test_cascade_clears_after_window(self):
        router = OctoArmorRouter()
        router.mark_rate_limited(ModelProvider.OPUS, window_sec=0)
        model = router.select_model(TaskComplexity.HIGH, role="KO")
        assert model.provider == ModelProvider.OPUS

    def test_all_limited_raises(self):
        router = OctoArmorRouter()
        for p in ModelProvider:
            router.mark_rate_limited(p)
        with pytest.raises(RuntimeError, match="All models rate-limited"):
            router.select_model(TaskComplexity.LOW, role="DR")
