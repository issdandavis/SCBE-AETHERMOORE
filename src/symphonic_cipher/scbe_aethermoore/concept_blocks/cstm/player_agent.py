"""
CSTM — PlayerAgent
===================

An autonomous agent that navigates stories by selecting choices based on
its 21-dimensional personality vector.

The agent is deliberately *not* a full LLM at decision time.  It is a
lightweight decision function over the personality space.  This keeps the
system tractable for running thousands of agents in parallel.

Components
----------
- ``PersonalityVector`` — 21D vector mapped to SCBE brain state dims
- ``HistoryBuffer``     — Rolling window of recent decisions
- ``DecisionEngine``    — Scores and selects choices
- ``PlayerAgent``       — Main agent class
"""

from __future__ import annotations

import math
import random
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, FrozenSet, List, Optional, Tuple

from .models import Choice, HistoryEntry, PlaythroughRecord, Scene, StoryGraph


# ---------------------------------------------------------------------------
#  Personality dimension names (21D)
# ---------------------------------------------------------------------------

DIM_NAMES: List[str] = [
    # Cognitive (0-2)
    "reasoning", "abstraction", "pattern_recognition",
    # Ethical (3-5)
    "fairness", "harm_avoidance", "honesty",
    # Social (6-8)
    "empathy", "cooperation", "assertiveness",
    # Executive (9-11)
    "planning", "impulse_control", "adaptability",
    # Motivational (12-14)
    "curiosity", "persistence", "risk_tolerance",
    # Emotional (15-17)
    "stability", "optimism", "resilience",
    # Meta (18-20)
    "self_awareness", "uncertainty_tolerance", "growth_orientation",
]

# Tag → personality dimension indices affected and direction (+1 or -1)
TAG_DRIFT_MAP: Dict[str, List[Tuple[int, float]]] = {
    "ethical":       [(3, +1), (4, +1), (5, +1)],
    "aggressive":    [(8, +1), (6, -0.5), (7, -0.5), (14, +0.5)],
    "empathetic":    [(6, +1), (7, +0.5), (3, +0.5)],
    "cautious":      [(14, -1), (9, +0.5), (10, +0.5)],
    "risky":         [(14, +1), (10, -0.5), (12, +0.5)],
    "curious":       [(12, +1), (1, +0.5), (20, +0.5)],
    "cooperative":   [(7, +1), (6, +0.5), (8, -0.3)],
    "deceptive":     [(5, -1), (8, +0.3)],
    "honest":        [(5, +1), (18, +0.3)],
    "planning":      [(9, +1), (0, +0.3)],
    "impulsive":     [(10, -1), (14, +0.5)],
    "resilient":     [(17, +1), (15, +0.5), (16, +0.3)],
    "creative":      [(1, +1), (12, +0.5), (2, +0.5)],
    "stable":        [(15, +1), (10, +0.3)],
    "optimistic":    [(16, +1), (17, +0.3)],
    "adaptive":      [(11, +1), (19, +0.3), (20, +0.3)],
}


# ---------------------------------------------------------------------------
#  PersonalityVector
# ---------------------------------------------------------------------------

class PersonalityVector:
    """
    21-dimensional vector representing the agent's personality state.

    Maps 1:1 to SCBE brain state dimensions:
        Dims  0-2 :  Cognitive
        Dims  3-5 :  Ethical
        Dims  6-8 :  Social
        Dims  9-11:  Executive
        Dims 12-14:  Motivational
        Dims 15-17:  Emotional
        Dims 18-20:  Meta
    """

    __slots__ = ("_vector", "_history")

    def __init__(self, initial: Optional[List[float]] = None, seed: int = 0) -> None:
        if initial is not None:
            if len(initial) != 21:
                raise ValueError(f"PersonalityVector requires 21 dims, got {len(initial)}")
            self._vector = [max(0.0, min(1.0, v)) for v in initial]
        else:
            rng = random.Random(seed)
            self._vector = [rng.uniform(0.3, 0.7) for _ in range(21)]
        self._history: List[Tuple[float, List[float]]] = []

    @property
    def vector(self) -> List[float]:
        return list(self._vector)

    def __getitem__(self, idx: int) -> float:
        return self._vector[idx]

    def __len__(self) -> int:
        return 21

    def apply_drift(self, delta: List[float], learning_rate: float = 0.01) -> None:
        """Shift personality by delta * learning_rate, clamped to [0, 1]."""
        self._history.append((time.time(), list(self._vector)))
        for i in range(21):
            self._vector[i] = max(0.0, min(1.0, self._vector[i] + learning_rate * delta[i]))

    def cosine_distance_from(self, other: List[float]) -> float:
        """Cosine distance (1 - cosine_similarity)."""
        dot = sum(a * b for a, b in zip(self._vector, other))
        mag_a = math.sqrt(sum(a * a for a in self._vector))
        mag_b = math.sqrt(sum(b * b for b in other))
        if mag_a < 1e-12 or mag_b < 1e-12:
            return 1.0
        return 1.0 - dot / (mag_a * mag_b)

    def dominant_traits(self, top_k: int = 5) -> List[Tuple[str, float]]:
        """Return the top_k dimensions with highest values."""
        indexed = [(DIM_NAMES[i], self._vector[i]) for i in range(21)]
        indexed.sort(key=lambda t: t[1], reverse=True)
        return indexed[:top_k]

    def drift_magnitude(self) -> float:
        """Total L2 distance traveled since initialization."""
        if not self._history:
            return 0.0
        total = 0.0
        prev = self._history[0][1]
        for _, snap in self._history[1:]:
            total += math.sqrt(sum((a - b) ** 2 for a, b in zip(prev, snap)))
            prev = snap
        # Include current position
        total += math.sqrt(sum((a - b) ** 2 for a, b in zip(prev, self._vector)))
        return total

    @property
    def snapshots(self) -> List[Tuple[float, List[float]]]:
        return list(self._history)


# ---------------------------------------------------------------------------
#  HistoryBuffer
# ---------------------------------------------------------------------------

class HistoryBuffer:
    """Rolling window of recent decisions, compressed to summary stats."""

    def __init__(self, max_size: int = 100) -> None:
        self._entries: Deque[HistoryEntry] = deque(maxlen=max_size)

    def record(
        self,
        scene_id: str,
        choice: Choice,
        stats_before: Dict[str, float],
        stats_after: Dict[str, float],
        personality: Optional[List[float]] = None,
    ) -> None:
        self._entries.append(HistoryEntry(
            timestamp=time.time(),
            scene_id=scene_id,
            choice_id=choice.choice_id,
            choice_label=choice.label,
            choice_tags=choice.tags,
            stats_before=dict(stats_before),
            stats_after=dict(stats_after),
            personality_snapshot=personality,
        ))

    def compress(self) -> List[float]:
        """
        Compress recent history into a fixed-size summary vector.

        Returns a 64D vector encoding:
        - Tag frequency distribution (first 32 dims, padded)
        - Mean stat deltas (next 16 dims, padded)
        - Recency-weighted activity (last 16 dims)
        """
        vec = [0.0] * 64
        if not self._entries:
            return vec

        # Tag frequency (first 32 dims)
        tag_counts: Dict[str, int] = {}
        for e in self._entries:
            for tag in e.choice_tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        total = max(sum(tag_counts.values()), 1)
        for i, (tag, count) in enumerate(sorted(tag_counts.items())):
            if i >= 32:
                break
            vec[i] = count / total

        # Mean stat deltas (dims 32-47)
        if len(self._entries) > 1:
            all_keys: set = set()
            for e in self._entries:
                all_keys |= set(e.stats_after.keys())
            key_list = sorted(all_keys)[:16]
            n = len(self._entries)
            for i, key in enumerate(key_list):
                delta_sum = sum(
                    e.stats_after.get(key, 0) - e.stats_before.get(key, 0)
                    for e in self._entries
                )
                vec[32 + i] = delta_sum / n

        # Recency (dims 48-63): exponentially decaying activity markers
        n = len(self._entries)
        for i in range(min(16, n)):
            vec[48 + i] = math.exp(-i * 0.3)

        return vec

    @property
    def entries(self) -> List[HistoryEntry]:
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)


# ---------------------------------------------------------------------------
#  DecisionEngine
# ---------------------------------------------------------------------------

class DecisionEngine:
    """
    Core decision function: score each available choice and select one.

    Uses a lightweight heuristic scoring model (no neural network required
    for the base implementation — neural scoring can be plugged in via
    the ``score_fn`` parameter).

    Default scoring:
        score = dot(personality_weights, tag_alignment) + difficulty_bonus + history_novelty
    """

    def __init__(
        self,
        temperature: float = 1.0,
        score_fn: Optional[Any] = None,
    ) -> None:
        self._temperature = temperature
        self._score_fn = score_fn  # Optional external scoring model

    def score_choices(
        self,
        scene: Scene,
        choices: List[Choice],
        personality: PersonalityVector,
        stats: Dict[str, float],
        history: HistoryBuffer,
    ) -> List[Tuple[Choice, float]]:
        """Return (choice, score) pairs sorted descending by score."""
        if self._score_fn is not None:
            return self._score_fn(scene, choices, personality, stats, history)

        pv = personality.vector
        scored: List[Tuple[Choice, float]] = []

        for choice in choices:
            score = self._heuristic_score(choice, pv, stats, history)
            scored.append((choice, score))

        scored.sort(key=lambda t: t[1], reverse=True)
        return scored

    def _heuristic_score(
        self,
        choice: Choice,
        pv: List[float],
        stats: Dict[str, float],
        history: HistoryBuffer,
    ) -> float:
        """Built-in heuristic scoring based on personality alignment."""
        score = 0.0

        # Tag alignment: sum personality dims associated with choice tags
        for tag in choice.tags:
            drift_spec = TAG_DRIFT_MAP.get(tag, [])
            for dim_idx, direction in drift_spec:
                # Higher personality dim + positive direction = attraction
                score += pv[dim_idx] * direction

        # Difficulty preference: risk_tolerance (dim 14) modulates preference
        risk = pv[14]  # risk_tolerance
        if choice.difficulty > 0.5:
            score += (risk - 0.5) * choice.difficulty
        else:
            score += (0.5 - risk) * (1.0 - choice.difficulty) * 0.5

        # Novelty bonus: prefer choices with tags not recently selected
        recent_tags: set = set()
        for entry in list(history.entries)[-10:]:
            recent_tags |= set(entry.choice_tags)
        novel_tags = choice.tags - frozenset(recent_tags)
        curiosity = pv[12]  # curiosity
        score += len(novel_tags) * curiosity * 0.3

        return score

    def select(self, scored: List[Tuple[Choice, float]]) -> Choice:
        """Sample from scored choices using temperature."""
        if not scored:
            raise ValueError("No choices to select from")
        if self._temperature <= 0.01 or len(scored) == 1:
            return scored[0][0]

        # Softmax with temperature
        max_score = max(s for _, s in scored)
        exp_scores = [math.exp((s - max_score) / self._temperature) for _, s in scored]
        total = sum(exp_scores)
        probs = [e / total for e in exp_scores]

        r = random.random()
        cumulative = 0.0
        for i, p in enumerate(probs):
            cumulative += p
            if r <= cumulative:
                return scored[i][0]
        return scored[-1][0]


# ---------------------------------------------------------------------------
#  PlayerAgent
# ---------------------------------------------------------------------------

class PlayerAgent:
    """A single AI agent that plays through stories."""

    def __init__(
        self,
        agent_id: str,
        personality: Optional[PersonalityVector] = None,
        decision_engine: Optional[DecisionEngine] = None,
        initial_stats: Optional[Dict[str, float]] = None,
        seed: int = 0,
    ) -> None:
        self.agent_id = agent_id
        self.personality = personality or PersonalityVector(seed=seed)
        self.decision_engine = decision_engine or DecisionEngine()
        self.stats: Dict[str, float] = dict(initial_stats) if initial_stats else {}
        self.history = HistoryBuffer()

    def play_scene(self, scene: Scene, available_choices: List[Choice]) -> Choice:
        """Process a scene and return the chosen action."""
        if not available_choices:
            raise ValueError(f"No available choices in scene '{scene.scene_id}'")

        scored = self.decision_engine.score_choices(
            scene, available_choices, self.personality, self.stats, self.history,
        )
        chosen = self.decision_engine.select(scored)

        stats_before = dict(self.stats)

        # Apply stat effects
        for stat, delta in chosen.stat_effects.items():
            self.stats[stat] = self.stats.get(stat, 0.0) + delta

        # Compute and apply personality drift from choice tags
        drift = self._compute_personality_drift(chosen)
        self.personality.apply_drift(drift)

        # Record history
        self.history.record(
            scene_id=scene.scene_id,
            choice=chosen,
            stats_before=stats_before,
            stats_after=dict(self.stats),
            personality=self.personality.vector,
        )

        return chosen

    def _compute_personality_drift(self, choice: Choice) -> List[float]:
        """
        Map choice tags to 21D personality drift.

        Magnitude modulated by choice difficulty (harder choices have more
        personality impact).
        """
        delta = [0.0] * 21
        magnitude = 1.0 + choice.difficulty  # [1.0, 2.0]

        for tag in choice.tags:
            drift_spec = TAG_DRIFT_MAP.get(tag, [])
            for dim_idx, direction in drift_spec:
                delta[dim_idx] += direction * magnitude

        return delta

    def play_story(self, graph: StoryGraph) -> PlaythroughRecord:
        """Play through an entire story from entry to exit."""
        entries = graph.entry_points
        if not entries:
            raise ValueError(f"Story '{graph.story_id}' has no entry point")

        current = graph.get_scene(entries[0])
        record = PlaythroughRecord(agent_id=self.agent_id, story_id=graph.story_id)

        max_steps = graph.total_scenes() * 3  # Safety limit to prevent infinite loops
        steps = 0

        while not current.is_exit and steps < max_steps:
            choices = graph.get_available_choices(current.scene_id, self.stats)
            if not choices:
                break  # Dead end
            chosen = self.play_scene(current, choices)
            record.add_step(
                scene_id=current.scene_id,
                choice=chosen,
                stats=dict(self.stats),
                personality=self.personality.vector,
            )
            current = graph.get_scene(chosen.next_scene_id)
            steps += 1

        record.finalize(self.personality.vector, dict(self.stats))
        return record
