"""
Tests for CSTM training_exporter and mass_tester modules.

Covers:
- TrainingExporter: SFT/DPO pair generation, JSONL export, stats
- Randomtest: Monte Carlo mass-play, coverage tracking
- Quicktest: Exhaustive branch forking, dead code detection
- GraphAnalysis: Dominators, bottlenecks, convergence, branching stats
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List

import pytest

# Ensure src/ is importable
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from symphonic_cipher.scbe_aethermoore.concept_blocks.cstm.models import (
    Choice,
    PlaythroughRecord,
    PlaythroughStep,
    Scene,
    StoryGraph,
)
from symphonic_cipher.scbe_aethermoore.concept_blocks.cstm.training_exporter import (
    DPOTriple,
    SFTPair,
    TrainingExporter,
    step_to_dpo,
    step_to_sft,
)
from symphonic_cipher.scbe_aethermoore.concept_blocks.cstm.mass_tester import (
    CoverageReport,
    GraphAnalysis,
    Quicktest,
    Randomtest,
)


# ---------------------------------------------------------------------------
#  Fixtures — reusable test story graphs
# ---------------------------------------------------------------------------

def _make_choice(cid: str, label: str, target: str,
                 tags: frozenset = frozenset(), difficulty: float = 0.0,
                 stat_effects: dict = None) -> Choice:
    return Choice(
        choice_id=cid,
        label=label,
        next_scene_id=target,
        tags=tags,
        difficulty=difficulty,
        stat_effects=stat_effects or {},
    )


def make_linear_story() -> StoryGraph:
    """A -> B -> C (linear, no branching)."""
    scenes = {
        "A": Scene(scene_id="A", title="Start", text="Begin here.",
                   choices=[_make_choice("c1", "Go forward", "B", tags=frozenset({"curious"}))],
                   is_entry=True),
        "B": Scene(scene_id="B", title="Middle", text="Middle ground.",
                   choices=[_make_choice("c2", "Continue", "C", tags=frozenset({"cautious"}))]),
        "C": Scene(scene_id="C", title="End", text="The end.", is_exit=True),
    }
    return StoryGraph(scenes, story_id="linear_test")


def make_branching_story() -> StoryGraph:
    """
    A -> B (ethical path)
    A -> C (aggressive path)
    B -> D (exit)
    C -> D (exit)
    """
    scenes = {
        "A": Scene(scene_id="A", title="Crossroads", text="Choose your path.",
                   choices=[
                       _make_choice("c_eth", "Help others", "B",
                                    tags=frozenset({"ethical", "empathetic"}), difficulty=0.3),
                       _make_choice("c_agg", "Take by force", "C",
                                    tags=frozenset({"aggressive", "risky"}), difficulty=0.7),
                   ],
                   is_entry=True),
        "B": Scene(scene_id="B", title="Kind Path", text="You helped.",
                   choices=[_make_choice("c_b_end", "Rest", "D", tags=frozenset({"stable"}))]),
        "C": Scene(scene_id="C", title="Force Path", text="You took it.",
                   choices=[_make_choice("c_c_end", "Move on", "D", tags=frozenset({"resilient"}))]),
        "D": Scene(scene_id="D", title="Ending", text="Journey's end.", is_exit=True),
    }
    return StoryGraph(scenes, story_id="branch_test")


def make_complex_story() -> StoryGraph:
    """
    A -> B, A -> C
    B -> D, B -> E
    C -> E
    D -> F (exit)
    E -> F (exit)
    Bottleneck: E (convergence point), F (exit convergence)
    """
    scenes = {
        "A": Scene(scene_id="A", title="Start", text="Begin.",
                   choices=[
                       _make_choice("c1", "Path 1", "B", tags=frozenset({"curious"})),
                       _make_choice("c2", "Path 2", "C", tags=frozenset({"cautious"})),
                   ],
                   is_entry=True),
        "B": Scene(scene_id="B", title="Fork", text="Another fork.",
                   choices=[
                       _make_choice("c3", "Left", "D", tags=frozenset({"ethical"})),
                       _make_choice("c4", "Right", "E", tags=frozenset({"risky"})),
                   ]),
        "C": Scene(scene_id="C", title="Converge", text="Leading to E.",
                   choices=[_make_choice("c5", "Forward", "E", tags=frozenset({"cooperative"}))]),
        "D": Scene(scene_id="D", title="Side exit", text="Side ending.",
                   choices=[_make_choice("c6", "Finish", "F", tags=frozenset({"stable"}))]),
        "E": Scene(scene_id="E", title="Main hub", text="Convergence.",
                   choices=[_make_choice("c7", "Final", "F", tags=frozenset({"resilient"}))]),
        "F": Scene(scene_id="F", title="End", text="Done.", is_exit=True),
    }
    return StoryGraph(scenes, story_id="complex_test")


def make_playthrough(graph: StoryGraph, path_choices: List[str]) -> PlaythroughRecord:
    """Build a PlaythroughRecord by walking the graph with specified choice IDs."""
    record = PlaythroughRecord(agent_id="test_agent", story_id=graph.story_id)
    current_id = graph.entry_points[0]

    for cid in path_choices:
        scene = graph.get_scene(current_id)
        available = list(scene.choices)
        chosen = next(c for c in available if c.choice_id == cid)
        record.add_step(
            scene_id=current_id,
            choice=chosen,
            stats={"score": 1.0},
            personality=[0.5] * 21,
            available_choices=available,
        )
        current_id = chosen.next_scene_id

    record.finalize([0.5] * 21, {"score": float(len(path_choices))})
    return record


# ===========================================================================
#  TrainingExporter Tests
# ===========================================================================

class TestSFTPairGeneration:
    """Test SFT pair generation from playthrough steps."""

    def test_step_to_sft_basic(self):
        graph = make_branching_story()
        pt = make_playthrough(graph, ["c_eth", "c_b_end"])
        step = pt.steps[0]

        pair = step_to_sft(step, "branch_test", "test_agent")
        assert pair is not None
        assert isinstance(pair, SFTPair)
        assert "Scene: A" in pair.instruction
        assert "Available choices:" in pair.instruction
        assert pair.metadata["story_id"] == "branch_test"
        assert pair.metadata["choice_id"] == "c_eth"

    def test_step_to_sft_no_choices(self):
        step = PlaythroughStep(
            scene_id="X",
            choice=_make_choice("cx", "Only", "Y"),
            available_choices=[],
        )
        pair = step_to_sft(step, "s1", "a1")
        assert pair is None

    def test_sft_includes_scene_text(self):
        graph = make_branching_story()
        pt = make_playthrough(graph, ["c_eth", "c_b_end"])
        step = pt.steps[0]

        pair = step_to_sft(step, "branch_test", "test_agent", scene_text="Choose your path.")
        assert "Choose your path." in pair.instruction

    def test_sft_pair_hash_deterministic(self):
        graph = make_branching_story()
        pt = make_playthrough(graph, ["c_eth", "c_b_end"])
        step = pt.steps[0]

        p1 = step_to_sft(step, "s1", "a1")
        p2 = step_to_sft(step, "s1", "a1")
        assert p1.metadata["pair_hash"] == p2.metadata["pair_hash"]

    def test_sft_to_dict(self):
        graph = make_linear_story()
        pt = make_playthrough(graph, ["c1", "c2"])
        pair = step_to_sft(pt.steps[0], "linear_test", "a1")
        d = pair.to_dict()
        assert "instruction" in d
        assert "response" in d
        assert "story_id" in d


class TestDPOTripleGeneration:
    """Test DPO triple generation from playthrough steps."""

    def test_step_to_dpo_basic(self):
        graph = make_branching_story()
        pt = make_playthrough(graph, ["c_eth", "c_b_end"])
        step = pt.steps[0]  # Has 2 choices, chose c_eth

        triples = step_to_dpo(step, "branch_test", "test_agent")
        assert len(triples) == 1  # One rejected alternative
        assert isinstance(triples[0], DPOTriple)
        assert triples[0].metadata["chosen_id"] == "c_eth"
        assert triples[0].metadata["rejected_id"] == "c_agg"

    def test_step_to_dpo_no_alternatives(self):
        graph = make_linear_story()
        pt = make_playthrough(graph, ["c1", "c2"])
        step = pt.steps[0]  # Only 1 choice available

        triples = step_to_dpo(step, "linear_test", "test_agent")
        assert len(triples) == 0

    def test_dpo_triple_to_dict(self):
        graph = make_branching_story()
        pt = make_playthrough(graph, ["c_eth", "c_b_end"])
        triples = step_to_dpo(pt.steps[0], "s1", "a1")
        d = triples[0].to_dict()
        assert "prompt" in d
        assert "chosen" in d
        assert "rejected" in d
        assert d["source"] == "cstm_dpo"

    def test_dpo_multiple_alternatives(self):
        """When a scene has 3+ choices, we get one triple per rejected alternative."""
        scenes = {
            "A": Scene(scene_id="A", title="Start", text="Pick.",
                       choices=[
                           _make_choice("x1", "One", "B"),
                           _make_choice("x2", "Two", "B"),
                           _make_choice("x3", "Three", "B"),
                       ],
                       is_entry=True),
            "B": Scene(scene_id="B", title="End", text="Done.", is_exit=True),
        }
        graph = StoryGraph(scenes, story_id="multi")
        record = PlaythroughRecord(agent_id="a", story_id="multi")
        record.add_step(
            scene_id="A",
            choice=scenes["A"].choices[0],
            available_choices=list(scenes["A"].choices),
        )
        triples = step_to_dpo(record.steps[0], "multi", "a")
        assert len(triples) == 2  # x2 and x3 rejected


class TestTrainingExporter:
    """Test the full TrainingExporter class."""

    def test_add_playthrough(self):
        graph = make_branching_story()
        pt = make_playthrough(graph, ["c_eth", "c_b_end"])
        exporter = TrainingExporter()
        sft_count, dpo_count = exporter.add_playthrough(pt, graph)
        assert sft_count == 2  # Two steps with choices
        assert dpo_count == 1  # Only first step has alternatives

    def test_export_sft_jsonl(self):
        graph = make_branching_story()
        pt = make_playthrough(graph, ["c_eth", "c_b_end"])
        exporter = TrainingExporter()
        exporter.add_playthrough(pt, graph)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            count = exporter.export_sft(path)
            assert count == 2
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) == 2
            data = json.loads(lines[0])
            assert "instruction" in data
            assert "response" in data
        finally:
            os.unlink(path)

    def test_export_dpo_jsonl(self):
        graph = make_branching_story()
        pt = make_playthrough(graph, ["c_eth", "c_b_end"])
        exporter = TrainingExporter()
        exporter.add_playthrough(pt, graph)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            count = exporter.export_dpo(path)
            assert count == 1
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            data = json.loads(lines[0])
            assert "prompt" in data
            assert "chosen" in data
            assert "rejected" in data
        finally:
            os.unlink(path)

    def test_export_combined(self):
        graph = make_branching_story()
        pt = make_playthrough(graph, ["c_eth", "c_b_end"])
        exporter = TrainingExporter()
        exporter.add_playthrough(pt, graph)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            count = exporter.export_combined(path)
            assert count == 3  # 2 SFT + 1 DPO
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            types = [json.loads(l)["type"] for l in lines]
            assert types.count("sft") == 2
            assert types.count("dpo") == 1
        finally:
            os.unlink(path)

    def test_stats(self):
        graph = make_branching_story()
        pt = make_playthrough(graph, ["c_eth", "c_b_end"])
        exporter = TrainingExporter()
        exporter.add_playthrough(pt, graph)
        stats = exporter.stats()
        assert stats["records_processed"] == 1
        assert stats["sft_pairs"] == 2
        assert stats["dpo_triples"] == 1
        assert stats["total_examples"] == 3
        assert stats["unique_stories"] == 1

    def test_clear(self):
        graph = make_branching_story()
        pt = make_playthrough(graph, ["c_eth", "c_b_end"])
        exporter = TrainingExporter()
        exporter.add_playthrough(pt, graph)
        exporter.clear()
        stats = exporter.stats()
        assert stats["records_processed"] == 0
        assert stats["sft_pairs"] == 0

    def test_add_multiple_playthroughs(self):
        graph = make_branching_story()
        pt1 = make_playthrough(graph, ["c_eth", "c_b_end"])
        pt2 = make_playthrough(graph, ["c_agg", "c_c_end"])
        exporter = TrainingExporter()
        exporter.add_playthroughs([pt1, pt2], {"branch_test": graph})
        stats = exporter.stats()
        assert stats["records_processed"] == 2
        assert stats["sft_pairs"] == 4  # 2 steps each


# ===========================================================================
#  Randomtest Tests
# ===========================================================================

class TestRandomtest:
    """Test Monte Carlo mass-play."""

    def test_basic_run(self):
        graph = make_linear_story()
        rt = Randomtest(iterations=100, seed=42)
        report = rt.run(graph)
        assert report.iterations == 100
        assert report.reached_scenes >= 2  # At least A and B
        assert report.total_scenes == 3

    def test_coverage_pct(self):
        graph = make_linear_story()
        rt = Randomtest(iterations=100, seed=42)
        report = rt.run(graph)
        assert report.coverage_pct > 0
        assert report.coverage_pct <= 100

    def test_branching_coverage(self):
        graph = make_branching_story()
        rt = Randomtest(iterations=1000, seed=42)
        report = rt.run(graph)
        # With 1000 iterations, should reach all 4 scenes
        assert report.reached_scenes == 4
        assert report.coverage_pct == 100.0

    def test_path_lengths(self):
        graph = make_branching_story()
        rt = Randomtest(iterations=50, seed=42)
        report = rt.run(graph)
        assert len(report.path_lengths) == 50
        assert report.mean_path_length > 0

    def test_ending_distribution(self):
        graph = make_branching_story()
        rt = Randomtest(iterations=500, seed=42)
        report = rt.run(graph)
        # D is the only exit
        assert "D" in report.ending_distribution
        assert report.ending_distribution["D"] == 500

    def test_no_entry_point(self):
        scenes = {
            "A": Scene(scene_id="A", title="Orphan", text="No entry.", is_exit=True),
        }
        graph = StoryGraph(scenes, story_id="no_entry")
        rt = Randomtest(iterations=10)
        report = rt.run(graph)
        assert "NO_ENTRY_POINT" in report.dead_ends

    def test_summary(self):
        graph = make_branching_story()
        rt = Randomtest(iterations=100, seed=42)
        report = rt.run(graph)
        summary = report.summary()
        assert "coverage_pct" in summary
        assert "iterations" in summary
        assert summary["iterations"] == 100

    def test_cold_choices(self):
        report = CoverageReport(
            iterations=1000,
            choice_hit_counts={"c1": 500, "c2": 5, "c3": 1},
        )
        cold = report.cold_choices
        # c3 (1 hit) is < 1% of 1000 = 10
        assert any(cid == "c3" for cid, _ in cold)
        assert any(cid == "c2" for cid, _ in cold)

    def test_deterministic_seed(self):
        graph = make_branching_story()
        rt1 = Randomtest(iterations=100, seed=42)
        rt2 = Randomtest(iterations=100, seed=42)
        r1 = rt1.run(graph)
        r2 = rt2.run(graph)
        assert r1.scene_hit_counts == r2.scene_hit_counts
        assert r1.choice_hit_counts == r2.choice_hit_counts


# ===========================================================================
#  Quicktest Tests
# ===========================================================================

class TestQuicktest:
    """Test exhaustive branch forking."""

    def test_basic_run(self):
        graph = make_linear_story()
        qt = Quicktest()
        report = qt.run(graph)
        assert report.reached_scenes == 3
        assert report.coverage_pct == 100.0

    def test_branching_coverage(self):
        graph = make_branching_story()
        qt = Quicktest()
        report = qt.run(graph)
        # Should explore ALL branches exhaustively
        assert report.reached_scenes == 4
        assert report.coverage_pct == 100.0
        assert len(report.unreachable) == 0

    def test_detects_unreachable(self):
        scenes = {
            "A": Scene(scene_id="A", title="Start", text="Go.",
                       choices=[_make_choice("c1", "Next", "B")], is_entry=True),
            "B": Scene(scene_id="B", title="End", text="Done.", is_exit=True),
            "C": Scene(scene_id="C", title="Orphan", text="Nobody comes here.",
                       choices=[_make_choice("c2", "Escape", "B")]),
        }
        graph = StoryGraph(scenes, story_id="orphan_test")
        qt = Quicktest()
        report = qt.run(graph)
        assert "C" in report.unreachable

    def test_complex_all_paths(self):
        graph = make_complex_story()
        qt = Quicktest()
        report = qt.run(graph)
        assert report.reached_scenes == 6
        assert report.coverage_pct == 100.0

    def test_no_entry_point(self):
        scenes = {
            "A": Scene(scene_id="A", title="Orphan", text="No entry.", is_exit=True),
        }
        graph = StoryGraph(scenes, story_id="no_entry")
        qt = Quicktest()
        report = qt.run(graph)
        assert "NO_ENTRY_POINT" in report.dead_ends

    def test_state_dedup(self):
        """Quicktest should dedup states to avoid exponential blowup."""
        graph = make_complex_story()
        qt = Quicktest()
        report = qt.run(graph)
        # Should finish quickly and not have excessive iterations
        assert report.iterations <= 20  # Reasonable upper bound


# ===========================================================================
#  GraphAnalysis Tests
# ===========================================================================

class TestGraphAnalysis:
    """Test structural analysis utilities."""

    def test_dominators_linear(self):
        graph = make_linear_story()
        idom = GraphAnalysis.dominators(graph)
        assert idom["A"] is None  # Entry
        assert idom["B"] == "A"
        assert idom["C"] == "B"

    def test_dominators_branching(self):
        graph = make_branching_story()
        idom = GraphAnalysis.dominators(graph)
        assert idom["A"] is None
        assert idom["B"] == "A"
        assert idom["C"] == "A"
        assert idom["D"] == "A"  # D dominated by A (both B and C lead to D)

    def test_bottlenecks(self):
        graph = make_complex_story()
        bottlenecks = GraphAnalysis.bottlenecks(graph)
        # In the complex graph, some non-entry scenes dominate 2+ others
        assert isinstance(bottlenecks, list)

    def test_convergence_points(self):
        graph = make_complex_story()
        convergence = GraphAnalysis.convergence_points(graph)
        # E has 2 incoming (from B and C), F has 2 incoming (from D and E)
        assert "E" in convergence
        assert "F" in convergence

    def test_branching_stats(self):
        graph = make_branching_story()
        stats = GraphAnalysis.branching_stats(graph)
        assert stats["max_branching"] == 2
        assert stats["min_branching"] == 1
        assert stats["multi_branch_scenes"] >= 1
        assert stats["total_choices"] > 0

    def test_all_paths_linear(self):
        graph = make_linear_story()
        paths = GraphAnalysis.all_paths(graph)
        assert len(paths) == 1
        assert paths[0] == ["A", "B", "C"]

    def test_all_paths_branching(self):
        graph = make_branching_story()
        paths = GraphAnalysis.all_paths(graph)
        assert len(paths) == 2
        # Both paths end at D
        for path in paths:
            assert path[-1] == "D"

    def test_all_paths_complex(self):
        graph = make_complex_story()
        paths = GraphAnalysis.all_paths(graph)
        assert len(paths) >= 3  # A-B-D-F, A-B-E-F, A-C-E-F

    def test_full_report(self):
        graph = make_branching_story()
        report = GraphAnalysis.full_report(graph)
        assert "branching" in report
        assert "bottlenecks" in report
        assert "convergence_points" in report
        assert report["total_scenes"] == 4
        assert len(report["entry_points"]) == 1

    def test_empty_graph(self):
        scenes = {
            "A": Scene(scene_id="A", title="Only", text="Just this.",
                       is_entry=True, is_exit=True),
        }
        graph = StoryGraph(scenes, story_id="single")
        stats = GraphAnalysis.branching_stats(graph)
        # No non-exit scenes
        assert stats["mean"] == 0 or stats.get("mean_branching", 0) == 0


# ===========================================================================
#  CoverageReport Tests
# ===========================================================================

class TestCoverageReport:
    """Test CoverageReport data structure."""

    def test_coverage_pct_zero(self):
        report = CoverageReport()
        assert report.coverage_pct == 0.0

    def test_coverage_pct_full(self):
        report = CoverageReport(total_scenes=10, reached_scenes=10)
        assert report.coverage_pct == 100.0

    def test_mean_path_length_empty(self):
        report = CoverageReport()
        assert report.mean_path_length == 0.0

    def test_mean_path_length(self):
        report = CoverageReport(path_lengths=[10, 20, 30])
        assert report.mean_path_length == 20.0

    def test_summary_keys(self):
        report = CoverageReport(
            total_scenes=5,
            reached_scenes=4,
            iterations=100,
            path_lengths=[3, 4, 5],
        )
        s = report.summary()
        expected_keys = {
            "coverage_pct", "total_scenes", "reached_scenes",
            "unreachable_count", "dead_end_count", "iterations",
            "mean_path_length", "min_path_length", "max_path_length",
            "cold_choices", "ending_count", "duration_seconds",
        }
        assert expected_keys == set(s.keys())
