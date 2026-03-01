"""
CSTM — Mass Tester
====================

Automated testing tools for branching narrative StoryGraphs, inspired by
ChoiceScript's randomtest/quicktest but built for our own engine.

Components
----------
- ``Randomtest``  — Monte Carlo mass-play with coverage tracking
- ``Quicktest``   — Exhaustive branch forking for dead code detection
- ``CoverageReport`` — Aggregated statistics from test runs
- ``GraphAnalysis``  — Dominator trees, bottleneck detection, path stats

All algorithms operate on CSTM StoryGraph DAGs.  No external dependencies.
"""

from __future__ import annotations

import hashlib
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from .models import Choice, Scene, StoryGraph


# ---------------------------------------------------------------------------
#  Coverage data structures
# ---------------------------------------------------------------------------

@dataclass
class CoverageReport:
    """Aggregated test coverage statistics."""

    total_scenes: int = 0
    reached_scenes: int = 0
    scene_hit_counts: Dict[str, int] = field(default_factory=dict)
    choice_hit_counts: Dict[str, int] = field(default_factory=dict)
    dead_ends: List[str] = field(default_factory=list)
    unreachable: List[str] = field(default_factory=list)
    path_lengths: List[int] = field(default_factory=list)
    ending_distribution: Dict[str, int] = field(default_factory=dict)
    iterations: int = 0
    duration_seconds: float = 0.0

    @property
    def coverage_pct(self) -> float:
        if self.total_scenes == 0:
            return 0.0
        return (self.reached_scenes / self.total_scenes) * 100.0

    @property
    def mean_path_length(self) -> float:
        if not self.path_lengths:
            return 0.0
        return sum(self.path_lengths) / len(self.path_lengths)

    @property
    def cold_choices(self) -> List[Tuple[str, int]]:
        """Choices selected less than 1% of iterations."""
        threshold = max(self.iterations * 0.01, 1)
        return [
            (cid, count) for cid, count in self.choice_hit_counts.items()
            if count < threshold
        ]

    def summary(self) -> Dict[str, Any]:
        return {
            "coverage_pct": round(self.coverage_pct, 1),
            "total_scenes": self.total_scenes,
            "reached_scenes": self.reached_scenes,
            "unreachable_count": len(self.unreachable),
            "dead_end_count": len(self.dead_ends),
            "iterations": self.iterations,
            "mean_path_length": round(self.mean_path_length, 1),
            "min_path_length": min(self.path_lengths) if self.path_lengths else 0,
            "max_path_length": max(self.path_lengths) if self.path_lengths else 0,
            "cold_choices": len(self.cold_choices),
            "ending_count": len(self.ending_distribution),
            "duration_seconds": round(self.duration_seconds, 2),
        }


# ---------------------------------------------------------------------------
#  Randomtest — Monte Carlo mass-play
# ---------------------------------------------------------------------------

class Randomtest:
    """
    Play through a StoryGraph N times with random choice selection.

    Inspired by ChoiceScript's randomtest with "avoid used options" mode.

    Usage::

        rt = Randomtest(iterations=10000, seed=42)
        report = rt.run(story_graph)
        print(report.summary())
    """

    def __init__(
        self,
        iterations: int = 10000,
        seed: int = 42,
        avoid_used_options: bool = True,
        max_steps_per_run: int = 500,
    ) -> None:
        self.iterations = iterations
        self.seed = seed
        self.avoid_used_options = avoid_used_options
        self.max_steps_per_run = max_steps_per_run

    def run(
        self,
        graph: StoryGraph,
        stats: Optional[Dict[str, float]] = None,
    ) -> CoverageReport:
        """Execute mass playtesting. Returns coverage report."""
        rng = random.Random(self.seed)
        start_time = time.monotonic()

        scene_hits: Dict[str, int] = defaultdict(int)
        choice_hits: Dict[str, int] = defaultdict(int)
        path_lengths: List[int] = []
        endings: Dict[str, int] = defaultdict(int)
        dead_ends: Set[str] = set()

        entries = graph.entry_points
        if not entries:
            return CoverageReport(
                total_scenes=graph.total_scenes(),
                dead_ends=["NO_ENTRY_POINT"],
            )

        for _ in range(self.iterations):
            current_id = entries[0]
            run_stats = dict(stats) if stats else {}
            steps = 0

            while steps < self.max_steps_per_run:
                scene_hits[current_id] += 1
                try:
                    scene = graph.get_scene(current_id)
                except KeyError:
                    dead_ends.add(current_id)
                    break

                if scene.is_exit:
                    endings[current_id] += 1
                    break

                choices = graph.get_available_choices(current_id, run_stats)
                if not choices:
                    dead_ends.add(current_id)
                    break

                # Select choice (avoid-used-options biases toward least-used)
                selected = self._select_choice(choices, choice_hits, rng)
                choice_hits[selected.choice_id] += 1

                # Apply stat effects
                for stat_key, delta in selected.stat_effects.items():
                    run_stats[stat_key] = run_stats.get(stat_key, 0.0) + delta

                current_id = selected.next_scene_id
                steps += 1

            path_lengths.append(steps)

        duration = time.monotonic() - start_time
        all_scene_ids = set(s.scene_id for s in graph.all_scenes())

        return CoverageReport(
            total_scenes=graph.total_scenes(),
            reached_scenes=len(set(scene_hits.keys()) & all_scene_ids),
            scene_hit_counts=dict(scene_hits),
            choice_hit_counts=dict(choice_hits),
            dead_ends=sorted(dead_ends),
            unreachable=sorted(all_scene_ids - set(scene_hits.keys())),
            path_lengths=path_lengths,
            ending_distribution=dict(endings),
            iterations=self.iterations,
            duration_seconds=duration,
        )

    def _select_choice(
        self,
        choices: List[Choice],
        hit_counts: Dict[str, int],
        rng: random.Random,
    ) -> Choice:
        """Select a choice, biasing toward least-used options."""
        if not self.avoid_used_options or len(choices) == 1:
            return rng.choice(choices)

        # Find minimum hit count among available choices
        counts = [hit_counts.get(c.choice_id, 0) for c in choices]
        min_count = min(counts)

        # Pick randomly among least-used
        least_used = [c for c, n in zip(choices, counts) if n == min_count]
        return rng.choice(least_used)


# ---------------------------------------------------------------------------
#  Quicktest — exhaustive branch forking
# ---------------------------------------------------------------------------

class Quicktest:
    """
    Exhaustive reachability analysis via recursive state forking.

    At every branch point, forks execution to explore all paths.
    Detects dead code, missing scenes, and impossible branches.

    Usage::

        qt = Quicktest()
        report = qt.run(story_graph)
        if report.unreachable:
            print(f"Dead code: {report.unreachable}")
    """

    def __init__(self, max_depth: int = 200) -> None:
        self.max_depth = max_depth

    def run(
        self,
        graph: StoryGraph,
        initial_stats: Optional[Dict[str, float]] = None,
    ) -> CoverageReport:
        """Run exhaustive branch exploration."""
        start_time = time.monotonic()

        scene_hits: Dict[str, int] = defaultdict(int)
        choice_hits: Dict[str, int] = defaultdict(int)
        dead_ends: Set[str] = set()
        endings: Dict[str, int] = defaultdict(int)
        path_lengths: List[int] = []
        visited_states: Set[str] = set()

        entries = graph.entry_points
        if not entries:
            return CoverageReport(
                total_scenes=graph.total_scenes(),
                dead_ends=["NO_ENTRY_POINT"],
            )

        stats = dict(initial_stats) if initial_stats else {}
        self._explore(
            graph, entries[0], stats, 0,
            scene_hits, choice_hits, dead_ends, endings,
            path_lengths, visited_states,
        )

        duration = time.monotonic() - start_time
        all_scene_ids = set(s.scene_id for s in graph.all_scenes())

        return CoverageReport(
            total_scenes=graph.total_scenes(),
            reached_scenes=len(set(scene_hits.keys()) & all_scene_ids),
            scene_hit_counts=dict(scene_hits),
            choice_hit_counts=dict(choice_hits),
            dead_ends=sorted(dead_ends),
            unreachable=sorted(all_scene_ids - set(scene_hits.keys())),
            path_lengths=path_lengths,
            ending_distribution=dict(endings),
            iterations=len(path_lengths),
            duration_seconds=duration,
        )

    def _explore(
        self,
        graph: StoryGraph,
        scene_id: str,
        stats: Dict[str, float],
        depth: int,
        scene_hits: Dict[str, int],
        choice_hits: Dict[str, int],
        dead_ends: Set[str],
        endings: Dict[str, int],
        path_lengths: List[int],
        visited: Set[str],
    ) -> None:
        """Recursive branch explorer."""
        if depth > self.max_depth:
            return

        # State dedup: scene_id + sorted stats hash
        stats_key = hashlib.md5(
            f"{scene_id}:{sorted(stats.items())}".encode()
        ).hexdigest()[:16]
        state_key = f"{scene_id}:{stats_key}"

        if state_key in visited:
            return
        visited.add(state_key)

        scene_hits[scene_id] += 1

        try:
            scene = graph.get_scene(scene_id)
        except KeyError:
            dead_ends.add(scene_id)
            path_lengths.append(depth)
            return

        if scene.is_exit:
            endings[scene_id] += 1
            path_lengths.append(depth)
            return

        # Get all choices (both with and without stat conditions)
        all_choices = scene.choices
        available = graph.get_available_choices(scene_id, stats)

        if not all_choices:
            dead_ends.add(scene_id)
            path_lengths.append(depth)
            return

        # Fork for every choice (test both available and unavailable paths)
        for choice in all_choices:
            choice_hits[choice.choice_id] += 1
            # Apply stat effects in a copy
            new_stats = dict(stats)
            for stat_key, delta in choice.stat_effects.items():
                new_stats[stat_key] = new_stats.get(stat_key, 0.0) + delta

            self._explore(
                graph, choice.next_scene_id, new_stats, depth + 1,
                scene_hits, choice_hits, dead_ends, endings,
                path_lengths, visited,
            )


# ---------------------------------------------------------------------------
#  Graph Analysis — structural metrics
# ---------------------------------------------------------------------------

class GraphAnalysis:
    """
    Structural analysis of StoryGraph DAGs.

    Provides: dominator tree, bottleneck detection, path statistics,
    branching factor analysis, and convergence rate.
    """

    @staticmethod
    def dominators(graph: StoryGraph) -> Dict[str, Optional[str]]:
        """
        Compute immediate dominator for each scene.

        A scene D dominates scene N if every path from entry to N
        passes through D.  Uses iterative data-flow algorithm.

        Returns {scene_id: immediate_dominator_id} (entry has None).
        """
        entries = graph.entry_points
        if not entries:
            return {}

        entry = entries[0]
        all_scenes = [s.scene_id for s in graph.all_scenes()]

        # Build predecessor map
        predecessors: Dict[str, Set[str]] = defaultdict(set)
        for scene in graph.all_scenes():
            for choice in scene.choices:
                predecessors[choice.next_scene_id].add(scene.scene_id)

        # Reverse postorder via DFS
        visited_order: List[str] = []
        visited_set: Set[str] = set()

        def _dfs(node: str) -> None:
            if node in visited_set:
                return
            visited_set.add(node)
            scene = graph.get_scene(node)
            for c in scene.choices:
                if c.next_scene_id in {s.scene_id for s in graph.all_scenes()}:
                    _dfs(c.next_scene_id)
            visited_order.append(node)

        _dfs(entry)
        rpo = list(reversed(visited_order))
        node_to_idx = {n: i for i, n in enumerate(rpo)}

        # Initialize dominators
        idom: Dict[str, Optional[str]] = {n: None for n in rpo}
        idom[entry] = entry

        def _intersect(b1: str, b2: str) -> str:
            while b1 != b2:
                while node_to_idx.get(b1, 0) > node_to_idx.get(b2, 0):
                    b1 = idom.get(b1) or entry
                while node_to_idx.get(b2, 0) > node_to_idx.get(b1, 0):
                    b2 = idom.get(b2) or entry
            return b1

        # Iterate until stable
        changed = True
        while changed:
            changed = False
            for node in rpo[1:]:  # Skip entry
                preds = [p for p in predecessors.get(node, set()) if idom.get(p) is not None]
                if not preds:
                    continue
                new_idom = preds[0]
                for p in preds[1:]:
                    new_idom = _intersect(new_idom, p)
                if idom.get(node) != new_idom:
                    idom[node] = new_idom
                    changed = True

        # Entry dominates itself — report as None for clarity
        idom[entry] = None
        return idom

    @staticmethod
    def bottlenecks(graph: StoryGraph) -> List[str]:
        """
        Find bottleneck scenes — scenes that dominate many other scenes.

        A bottleneck is any non-entry scene that is the immediate dominator
        of 2+ other scenes, meaning all paths to those scenes must pass
        through it.
        """
        idom = GraphAnalysis.dominators(graph)
        dom_counts: Dict[str, int] = defaultdict(int)
        for scene_id, dominator in idom.items():
            if dominator is not None:
                dom_counts[dominator] += 1

        # Bottleneck = dominates 2+ scenes (excluding entry which dominates everything)
        entries = set(graph.entry_points)
        return sorted([
            sid for sid, count in dom_counts.items()
            if count >= 2 and sid not in entries
        ])

    @staticmethod
    def convergence_points(graph: StoryGraph) -> List[str]:
        """Find scenes with 2+ incoming edges (where branches reconverge)."""
        in_degree: Dict[str, int] = defaultdict(int)
        for scene in graph.all_scenes():
            for c in scene.choices:
                in_degree[c.next_scene_id] += 1
        return sorted([sid for sid, deg in in_degree.items() if deg >= 2])

    @staticmethod
    def branching_stats(graph: StoryGraph) -> Dict[str, Any]:
        """Detailed branching statistics."""
        scenes = graph.all_scenes()
        choice_counts = [len(s.choices) for s in scenes if not s.is_exit]

        if not choice_counts:
            return {"mean": 0, "max": 0, "min": 0, "single_path": 0, "multi_branch": 0}

        return {
            "mean_branching": round(sum(choice_counts) / len(choice_counts), 2),
            "max_branching": max(choice_counts),
            "min_branching": min(choice_counts),
            "single_path_scenes": sum(1 for c in choice_counts if c == 1),
            "multi_branch_scenes": sum(1 for c in choice_counts if c >= 2),
            "total_choices": sum(choice_counts),
        }

    @staticmethod
    def all_paths(
        graph: StoryGraph,
        max_paths: int = 1000,
        max_depth: int = 100,
    ) -> List[List[str]]:
        """Enumerate all distinct paths from entry to exit (up to limit)."""
        entries = graph.entry_points
        if not entries:
            return []

        paths: List[List[str]] = []

        def _walk(scene_id: str, path: List[str], visited: Set[str]) -> None:
            if len(paths) >= max_paths or len(path) > max_depth:
                return
            if scene_id in visited:
                return

            path = path + [scene_id]
            visited = visited | {scene_id}

            try:
                scene = graph.get_scene(scene_id)
            except KeyError:
                return

            if scene.is_exit or not scene.choices:
                paths.append(path)
                return

            for choice in scene.choices:
                _walk(choice.next_scene_id, path, visited)

        _walk(entries[0], [], set())
        return paths

    @staticmethod
    def full_report(graph: StoryGraph) -> Dict[str, Any]:
        """Complete structural analysis of a story graph."""
        return {
            "branching": GraphAnalysis.branching_stats(graph),
            "bottlenecks": GraphAnalysis.bottlenecks(graph),
            "convergence_points": GraphAnalysis.convergence_points(graph),
            "total_scenes": graph.total_scenes(),
            "entry_points": graph.entry_points,
            "exit_points": graph.exit_points,
            "validation_errors": [
                {"code": e.code, "message": e.message, "scene_id": e.scene_id}
                for e in graph.validate()
            ],
        }
