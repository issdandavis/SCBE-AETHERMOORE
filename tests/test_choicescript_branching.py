"""Tests for ChoiceScript Branching Engine — multi-path workflow exploration."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "workflows", "n8n"))

from choicescript_branching_engine import (
    BranchingEngine,
    Choice,
    ExploreResult,
    ExploreStrategy,
    NodeType,
    SafeContextEval,
    SceneGraph,
    build_content_publishing_graph,
    build_research_pipeline_graph,
    build_training_funnel_graph,
)


class TestSceneGraph:
    def test_create_basic_graph(self):
        g = SceneGraph("test")
        g.add_scene("start", action="noop")
        g.add_finish("end")
        g.add_goto("start", "end")
        assert len(g.scenes) == 2
        assert g.scenes["start"].goto_target == "end"

    def test_add_choices(self):
        g = SceneGraph("test")
        g.add_scene("start")
        g.add_choice("start", [
            Choice("a", condition="True"),
            Choice("b", condition="x > 5"),
        ])
        assert len(g.scenes["start"].choices) == 2
        assert g.scenes["start"].node_type == NodeType.CHOICE

    def test_reachable_from(self):
        g = SceneGraph("test")
        g.add_scene("start")
        g.add_scene("a", action="noop")
        g.add_scene("b", action="noop")
        g.add_scene("orphan", action="noop")
        g.add_choice("start", [Choice("a"), Choice("b")])
        reachable = g.reachable_from("start")
        assert "a" in reachable
        assert "b" in reachable
        assert "orphan" not in reachable

    def test_to_choicescript_export(self):
        g = build_research_pipeline_graph("test topic")
        cs = g.to_choicescript()
        assert "*title research_pipeline" in cs
        assert "*choice" in cs
        assert "*goto" in cs

    def test_to_n8n_workflow_export(self):
        g = build_research_pipeline_graph("test")
        wf = g.to_n8n_workflow()
        assert wf["name"].startswith("SCBE Branch:")
        assert len(wf["nodes"]) > 0
        assert any(n["type"] == "n8n-nodes-base.webhook" for n in wf["nodes"])

    def test_to_dict(self):
        g = SceneGraph("test")
        g.add_scene("start", action="noop")
        d = g.to_dict()
        assert d["name"] == "test"
        assert "start" in d["scenes"]


class TestSafeContextEval:
    def test_true_default(self):
        assert SafeContextEval.evaluate("True", {}) is True

    def test_false(self):
        assert SafeContextEval.evaluate("False", {}) is False

    def test_comparison(self):
        assert SafeContextEval.evaluate("x > 5", {"x": 10}) is True
        assert SafeContextEval.evaluate("x > 5", {"x": 2}) is False

    def test_dot_access(self):
        ctx = {"topic": {"domain": "academic"}}
        assert SafeContextEval.evaluate("topic.domain == 'academic'", ctx) is True

    def test_invalid_expression(self):
        # Should return False on error, not raise
        assert SafeContextEval.evaluate("import os", {}) is False

    def test_empty_expression(self):
        assert SafeContextEval.evaluate("", {}) is True


class TestBranchingEngine:
    def test_first_match_strategy(self):
        g = SceneGraph("test")
        g.add_scene("start")
        g.add_scene("a", action="noop")
        g.add_scene("b", action="noop")
        g.add_choice("start", [Choice("a"), Choice("b")])
        g.add_finish("a")
        g.add_finish("b")

        engine = BranchingEngine()
        result = engine.explore_sync(g, strategy=ExploreStrategy.FIRST_MATCH)
        assert len(result.paths) == 1
        assert "a" in result.paths[0].scenes_visited

    def test_all_paths_strategy(self):
        g = SceneGraph("test")
        g.add_scene("start")
        g.add_scene("a", action="noop")
        g.add_scene("b", action="noop")
        g.add_choice("start", [Choice("a"), Choice("b")])
        g.add_finish("a")
        g.add_finish("b")

        engine = BranchingEngine()
        result = engine.explore_sync(g, strategy=ExploreStrategy.ALL_PATHS)
        assert len(result.paths) == 2
        visited = set()
        for p in result.paths:
            visited.update(p.scenes_visited)
        assert "a" in visited
        assert "b" in visited

    def test_cycle_detection(self):
        g = SceneGraph("test")
        g.add_scene("start", action="noop")
        g.add_goto("start", "start")  # self-loop

        engine = BranchingEngine()
        result = engine.explore_sync(g)
        assert any("cycle" in (p.error or "") for p in result.paths)

    def test_missing_scene_handled(self):
        g = SceneGraph("test")
        g.add_scene("start")
        g.add_choice("start", [Choice("nonexistent")])

        engine = BranchingEngine()
        result = engine.explore_sync(g)
        assert any("not_found" in (p.error or "") for p in result.paths)

    def test_conditional_branching(self):
        g = SceneGraph("test")
        g.add_scene("start")
        g.add_scene("yes_path", action="noop")
        g.add_scene("no_path", action="noop")
        g.add_choice("start", [
            Choice("yes_path", condition="x > 5"),
            Choice("no_path", condition="x <= 5"),
        ])
        g.add_finish("yes_path")
        g.add_finish("no_path")

        engine = BranchingEngine()
        result = engine.explore_sync(g, context={"x": 10}, strategy=ExploreStrategy.ALL_PATHS)
        # Only yes_path should be valid
        assert len(result.paths) == 1
        assert "yes_path" in result.paths[0].scenes_visited

    def test_coverage_calculation(self):
        g = build_research_pipeline_graph("test")
        engine = BranchingEngine()
        result = engine.explore_sync(g, strategy=ExploreStrategy.ALL_PATHS)
        assert result.coverage > 0.0
        assert result.total_scenes == len(g.scenes)

    def test_scored_strategy(self):
        g = SceneGraph("test")
        g.add_scene("start")
        g.add_scene("low", action="noop")
        g.add_scene("high", action="noop")
        g.add_choice("start", [
            Choice("low", weight=1.0),
            Choice("high", weight=10.0),
        ])
        g.add_finish("low")
        g.add_finish("high")

        engine = BranchingEngine()
        result = engine.explore_sync(g, strategy=ExploreStrategy.SCORED)
        # Scored picks highest weight first
        assert result.paths[0].scenes_visited[-1] == "high"

    def test_set_vars(self):
        g = SceneGraph("test")
        g.add_scene("start", action="noop", set_vars={"computed": "len('hello')"})
        g.add_finish("start")

        engine = BranchingEngine()
        result = engine.explore_sync(g)
        # The var should be set in context (even if we can't directly check it,
        # the engine shouldn't crash)
        assert len(result.paths) == 1
        assert result.paths[0].terminal is True


class TestPrebuiltGraphs:
    def test_research_pipeline_runs(self):
        g = build_research_pipeline_graph("quantum error correction")
        engine = BranchingEngine()
        result = engine.explore_sync(g, strategy=ExploreStrategy.ALL_PATHS)
        assert result.graph_name == "research_pipeline"
        assert len(result.paths) > 0
        assert result.coverage > 0.5

    def test_content_publisher_runs(self):
        g = build_content_publishing_graph()
        engine = BranchingEngine()
        result = engine.explore_sync(g, strategy=ExploreStrategy.ALL_PATHS)
        assert result.graph_name == "content_publisher"
        assert len(result.paths) >= 4  # 4 platforms

    def test_training_funnel_runs(self):
        g = build_training_funnel_graph()
        engine = BranchingEngine()
        result = engine.explore_sync(g, strategy=ExploreStrategy.ALL_PATHS)
        assert result.graph_name == "training_funnel"
        assert len(result.paths) >= 3  # 3 ingest paths

    def test_research_best_path_exists(self):
        g = build_research_pipeline_graph("hyperbolic geometry")
        engine = BranchingEngine()
        result = engine.explore_sync(g, strategy=ExploreStrategy.ALL_PATHS)
        assert result.best_path is not None
        assert result.best_path.score > 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
