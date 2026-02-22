"""
CSTM — Core Data Models
========================

Shared data structures used across all CSTM components: Scene, Choice,
StoryGraph (the narrative DAG), curriculum definitions, playthrough records,
and history entries.

Pure Python — no external dependencies.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Deque,
    Dict,
    FrozenSet,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
)


# ---------------------------------------------------------------------------
#  Story primitives
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Choice:
    """A single selectable option within a scene."""

    choice_id: str
    label: str                                      # Display text
    next_scene_id: str                              # Target scene
    condition: Optional[str] = None                 # Boolean expression over stats
    stat_effects: Dict[str, float] = field(default_factory=dict)
    tags: FrozenSet[str] = frozenset()              # e.g. {"ethical", "aggressive"}
    difficulty: float = 0.0                         # [0, 1]


@dataclass
class Scene:
    """A single node in the story DAG."""

    scene_id: str
    title: str
    text: str
    choices: List[Choice] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_entry: bool = False
    is_exit: bool = False
    scene_type: str = "narrative"   # narrative | dilemma | info | checkpoint


class ValidationError:
    """A structural issue found in a story graph."""

    def __init__(self, code: str, message: str, scene_id: Optional[str] = None):
        self.code = code
        self.message = message
        self.scene_id = scene_id

    def __repr__(self) -> str:
        loc = f" @ {self.scene_id}" if self.scene_id else ""
        return f"ValidationError({self.code}{loc}: {self.message})"


class StoryGraph:
    """Directed graph of scenes — immutable after construction."""

    def __init__(
        self,
        scenes: Dict[str, Scene],
        story_id: str,
        story_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._scenes = dict(scenes)
        self.story_id = story_id
        self.metadata = story_metadata or {}
        self._adjacency: Dict[str, List[str]] = self._build_adjacency()

    # -- construction helpers ------------------------------------------------

    def _build_adjacency(self) -> Dict[str, List[str]]:
        adj: Dict[str, List[str]] = {}
        for sid, scene in self._scenes.items():
            adj[sid] = [c.next_scene_id for c in scene.choices]
        return adj

    # -- public API ----------------------------------------------------------

    @property
    def entry_points(self) -> List[str]:
        return [s.scene_id for s in self._scenes.values() if s.is_entry]

    @property
    def exit_points(self) -> List[str]:
        return [s.scene_id for s in self._scenes.values() if s.is_exit]

    def get_scene(self, scene_id: str) -> Scene:
        return self._scenes[scene_id]

    def get_available_choices(
        self, scene_id: str, stats: Optional[Dict[str, float]] = None
    ) -> List[Choice]:
        """Return choices whose conditions are met (or unconditional)."""
        scene = self._scenes[scene_id]
        if stats is None:
            return list(scene.choices)
        # Lazy import to avoid circular dep
        from .story_engine import ConditionEvaluator
        evaluator = ConditionEvaluator()
        return [
            c for c in scene.choices
            if c.condition is None or evaluator.evaluate(c.condition, stats)
        ]

    def total_scenes(self) -> int:
        return len(self._scenes)

    def branching_factor(self) -> float:
        """Average number of outgoing edges per non-exit scene."""
        non_exit = [s for s in self._scenes.values() if not s.is_exit]
        if not non_exit:
            return 0.0
        return sum(len(s.choices) for s in non_exit) / len(non_exit)

    def shortest_path(self, from_id: str, to_id: str) -> Optional[List[str]]:
        """BFS shortest path between two scenes."""
        if from_id == to_id:
            return [from_id]
        visited: Set[str] = {from_id}
        queue: Deque[List[str]] = deque([[from_id]])
        while queue:
            path = queue.popleft()
            for neighbor in self._adjacency.get(path[-1], []):
                if neighbor == to_id:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        return None

    def all_scenes(self) -> List[Scene]:
        return list(self._scenes.values())

    def validate(self) -> List[ValidationError]:
        """Check graph structural integrity."""
        errors: List[ValidationError] = []

        # Must have at least one entry and one exit
        if not self.entry_points:
            errors.append(ValidationError("NO_ENTRY", "No entry scene defined"))
        if not self.exit_points:
            errors.append(ValidationError("NO_EXIT", "No exit scene defined"))

        # All choice targets must exist
        for sid, scene in self._scenes.items():
            for c in scene.choices:
                if c.next_scene_id not in self._scenes:
                    errors.append(ValidationError(
                        "DANGLING_REF",
                        f"Choice '{c.choice_id}' targets unknown scene '{c.next_scene_id}'",
                        scene_id=sid,
                    ))

        # Reachability from entry
        if self.entry_points:
            reachable: Set[str] = set()
            stack = list(self.entry_points)
            while stack:
                curr = stack.pop()
                if curr in reachable:
                    continue
                reachable.add(curr)
                stack.extend(self._adjacency.get(curr, []))

            unreachable = set(self._scenes.keys()) - reachable
            for sid in unreachable:
                errors.append(ValidationError(
                    "UNREACHABLE", f"Scene '{sid}' not reachable from any entry",
                    scene_id=sid,
                ))

        # Dead ends (non-exit scenes with no choices)
        for sid, scene in self._scenes.items():
            if not scene.is_exit and not scene.choices:
                errors.append(ValidationError(
                    "DEAD_END", f"Non-exit scene '{sid}' has no choices",
                    scene_id=sid,
                ))

        return errors


# ---------------------------------------------------------------------------
#  Curriculum
# ---------------------------------------------------------------------------

class StoryCategory(Enum):
    ETHICAL_DILEMMA = "ethical_dilemma"
    RESOURCE_MANAGEMENT = "resource_management"
    SOCIAL_NAVIGATION = "social_navigation"
    CRISIS_RESPONSE = "crisis_response"
    EXPLORATION = "exploration"
    COOPERATION = "cooperation"
    DECEPTION_DETECTION = "deception_detection"
    LONG_TERM_PLANNING = "long_term_planning"


class CurriculumPhase(Enum):
    CHILDHOOD = "childhood"
    EDUCATION = "education"
    CAREER = "career"
    CHALLENGE = "challenge"


CATEGORY_LAYER_MAP: Dict[StoryCategory, Set[int]] = {
    StoryCategory.ETHICAL_DILEMMA:       {1, 5, 7, 10},
    StoryCategory.RESOURCE_MANAGEMENT:   {2, 4, 6, 9},
    StoryCategory.SOCIAL_NAVIGATION:     {3, 4, 7, 11},
    StoryCategory.CRISIS_RESPONSE:       {1, 2, 8, 12, 13},
    StoryCategory.EXPLORATION:           {3, 4, 6},
    StoryCategory.COOPERATION:           {4, 7, 9, 14},
    StoryCategory.DECEPTION_DETECTION:   {5, 8, 10},
    StoryCategory.LONG_TERM_PLANNING:    {4, 6, 12},
}


@dataclass
class PhaseSpec:
    phase: CurriculumPhase
    story_ids: List[str]
    required_categories: Set[StoryCategory] = field(default_factory=set)
    min_stories: int = 1
    max_stories: int = 100
    difficulty_range: Tuple[float, float] = (0.0, 1.0)
    scbe_layers_exercised: Set[int] = field(default_factory=set)


@dataclass
class Curriculum:
    curriculum_id: str
    name: str
    description: str
    phases: List[PhaseSpec]

    @property
    def total_stories(self) -> int:
        return sum(len(p.story_ids) for p in self.phases)

    @property
    def all_story_ids(self) -> List[str]:
        ids: List[str] = []
        for p in self.phases:
            ids.extend(p.story_ids)
        return ids

    @property
    def layers_covered(self) -> Set[int]:
        covered: Set[int] = set()
        for p in self.phases:
            covered |= p.scbe_layers_exercised
        return covered

    def validate(self) -> List[str]:
        """Return list of issues (empty = valid)."""
        issues: List[str] = []
        all_layers = set(range(1, 15))
        missing = all_layers - self.layers_covered
        if missing:
            issues.append(f"SCBE layers not exercised: {sorted(missing)}")
        # Check for duplicate stories across phases
        seen: Set[str] = set()
        for p in self.phases:
            for sid in p.story_ids:
                if sid in seen:
                    issues.append(f"Story '{sid}' appears in multiple phases")
                seen.add(sid)
        return issues


# ---------------------------------------------------------------------------
#  Playthrough records
# ---------------------------------------------------------------------------

@dataclass
class HistoryEntry:
    """A single decision recorded during a playthrough."""

    timestamp: float
    scene_id: str
    choice_id: str
    choice_label: str
    choice_tags: FrozenSet[str]
    stats_before: Dict[str, float]
    stats_after: Dict[str, float]
    personality_snapshot: Optional[List[float]] = None  # 21D as list for serialisation


@dataclass
class PlaythroughStep:
    """One step in a playthrough."""

    scene_id: str
    choice: Choice
    stats_snapshot: Dict[str, float] = field(default_factory=dict)
    personality_snapshot: Optional[List[float]] = None


@dataclass
class PlaythroughRecord:
    """Complete record of one agent playing one story."""

    agent_id: str
    story_id: str
    steps: List[PlaythroughStep] = field(default_factory=list)
    final_personality: Optional[List[float]] = None
    final_stats: Optional[Dict[str, float]] = None
    completed: bool = False

    def add_step(self, scene_id: str, choice: Choice,
                 stats: Optional[Dict[str, float]] = None,
                 personality: Optional[List[float]] = None) -> None:
        self.steps.append(PlaythroughStep(
            scene_id=scene_id,
            choice=choice,
            stats_snapshot=dict(stats) if stats else {},
            personality_snapshot=personality,
        ))

    def finalize(self, personality: List[float], stats: Dict[str, float]) -> None:
        self.final_personality = list(personality)
        self.final_stats = dict(stats)
        self.completed = True

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def choice_tag_distribution(self) -> Dict[str, int]:
        """Count of each tag across all choices made."""
        dist: Dict[str, int] = {}
        for step in self.steps:
            for tag in step.choice.tags:
                dist[tag] = dist.get(tag, 0) + 1
        return dist
