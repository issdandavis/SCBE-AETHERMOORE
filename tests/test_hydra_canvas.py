"""Tests for HYDRA Canvas — multi-step orchestrated workflows with model spectrum."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hydra.canvas import (
    CanvasOrchestrator,
    CanvasStep,
    KnowledgeCanvas,
    ModelColor,
    PROVIDER_SPECTRUM,
    RECIPE_REGISTRY,
    StepType,
    list_recipes,
    recipe_article,
    recipe_content_pipeline,
    recipe_research_deep,
    recipe_training_data,
    run_recipe,
)


class TestModelSpectrum:
    def test_all_providers_have_colors(self):
        for name, spec in PROVIDER_SPECTRUM.items():
            assert "color" in spec, f"Provider {name} missing color"
            assert isinstance(spec["color"], ModelColor)

    def test_colors_are_unique(self):
        colors = [s["color"] for s in PROVIDER_SPECTRUM.values()]
        assert len(colors) == len(set(colors)), "Duplicate colors in spectrum"

    def test_all_providers_have_specialties(self):
        for name, spec in PROVIDER_SPECTRUM.items():
            assert spec["specialty"], f"Provider {name} missing specialty"
            assert spec["strengths"], f"Provider {name} missing strengths"


class TestRecipes:
    def test_article_recipe_has_steps(self):
        steps = recipe_article("test topic")
        assert len(steps) >= 10

    def test_research_recipe_has_steps(self):
        steps = recipe_research_deep("test")
        assert len(steps) >= 6

    def test_content_recipe_has_per_platform_steps(self):
        steps = recipe_content_pipeline("test", platforms=["twitter", "linkedin"])
        # At least: core_draft + governance + 2*(adapt+publish) + canvas_merge = 7
        assert len(steps) >= 7

    def test_training_recipe_has_quality_gate(self):
        steps = recipe_training_data("test")
        roundabouts = [s for s in steps if s.step_type == StepType.ROUNDABOUT]
        assert len(roundabouts) >= 1

    def test_all_recipes_registered(self):
        assert "article" in RECIPE_REGISTRY
        assert "research" in RECIPE_REGISTRY
        assert "content" in RECIPE_REGISTRY
        assert "training" in RECIPE_REGISTRY

    def test_steps_have_valid_dependencies(self):
        for name, builder in RECIPE_REGISTRY.items():
            steps = builder("test")
            step_ids = {s.step_id for s in steps}
            for step in steps:
                for dep in step.depends_on:
                    assert dep in step_ids, f"Recipe '{name}' step '{step.step_id}' depends on missing '{dep}'"


class TestCanvasOrchestrator:
    def test_single_provider_execution(self):
        steps = recipe_article("test")
        orch = CanvasOrchestrator(available_providers=["claude"])
        canvas = orch.execute_recipe(steps, topic="test")
        assert canvas is not None
        assert canvas.topic == "test"
        summary = orch.summary()
        assert summary["completed"] == summary["total_steps"]
        assert summary["failed"] == 0

    def test_multi_provider_execution(self):
        steps = recipe_article("test")
        orch = CanvasOrchestrator(available_providers=["claude", "gpt", "gemini", "grok"])
        orch.execute_recipe(steps, topic="test")
        summary = orch.summary()
        assert summary["completed"] == summary["total_steps"]
        # Should use multiple colors
        assert len(summary["colors_used"]) >= 2

    def test_color_assignment(self):
        orch = CanvasOrchestrator(available_providers=["claude", "gpt", "gemini", "grok"])
        # Violet step should go to claude
        step = CanvasStep("test", StepType.DRAFT, assigned_color=ModelColor.VIOLET)
        provider = orch._assign_provider(step)
        assert provider == "claude"

        # Blue step should go to gpt
        step2 = CanvasStep("test2", StepType.DRAFT, assigned_color=ModelColor.BLUE)
        provider2 = orch._assign_provider(step2)
        assert provider2 == "gpt"

    def test_dependency_ordering(self):
        steps = [
            CanvasStep("a", StepType.RESEARCH),
            CanvasStep("b", StepType.DRAFT, depends_on=["a"]),
            CanvasStep("c", StepType.EDIT, depends_on=["b"]),
        ]
        orch = CanvasOrchestrator(available_providers=["claude"])
        orch.execute_recipe(steps, topic="test")
        # All should complete in order
        results = list(orch.results.values())
        assert all(r.status == "done" for r in results)

    def test_roundabout_execution(self):
        steps = [
            CanvasStep("draft", StepType.DRAFT),
            CanvasStep("check", StepType.ROUNDABOUT, depends_on=["draft"],
                       params={"min_quality": 0.5}),
        ]
        orch = CanvasOrchestrator(available_providers=["claude"])
        orch.execute_recipe(steps, topic="test")
        assert orch.results["check"].status == "done"

    def test_canvas_merge_collects_strokes(self):
        steps = [
            CanvasStep("a", StepType.DRAFT, assigned_color=ModelColor.VIOLET),
            CanvasStep("b", StepType.DRAFT, assigned_color=ModelColor.BLUE),
            CanvasStep("merge", StepType.CANVAS_MERGE, depends_on=["a", "b"]),
        ]
        orch = CanvasOrchestrator(available_providers=["claude", "gpt"])
        canvas = orch.execute_recipe(steps, topic="test")
        assert len(canvas.sections) >= 2
        assert len(canvas.colors_used) >= 2


class TestKnowledgeCanvas:
    def test_add_stroke(self):
        c = KnowledgeCanvas(canvas_id="test", topic="test", timestamp="now")
        c.add_stroke("violet", "Content 1", "step_a")
        c.add_stroke("blue", "Content 2", "step_b")
        assert len(c.sections) == 2
        assert "violet" in c.colors_used
        assert "blue" in c.colors_used

    def test_render(self):
        c = KnowledgeCanvas(canvas_id="test", topic="My Topic", timestamp="2026-03-06")
        c.add_stroke("violet", "Architecture analysis", "step_a")
        c.add_stroke("blue", "Draft content", "step_b")
        rendered = c.render()
        assert "My Topic" in rendered
        assert "VIOLET" in rendered
        assert "BLUE" in rendered
        assert "Architecture analysis" in rendered


class TestRunRecipe:
    def test_run_article(self):
        result = run_recipe("article", "test topic", providers=["claude"])
        assert "canvas_id" in result
        assert result["summary"]["completed"] > 0
        assert "canvas_render" in result

    def test_run_research(self):
        result = run_recipe("research", "quantum", providers=["claude", "gpt"])
        assert result["summary"]["failed"] == 0

    def test_run_unknown_recipe(self):
        result = run_recipe("nonexistent", "test")
        assert "error" in result

    def test_list_recipes(self):
        recipes = list_recipes()
        assert len(recipes) >= 4
        names = [r["name"] for r in recipes]
        assert "article" in names
        assert "research" in names


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
