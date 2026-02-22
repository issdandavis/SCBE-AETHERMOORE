"""
CSTM — NurseryManager
======================

Orchestrate a cohort of PlayerAgents through a curriculum of stories.
Manage agent lifecycle from spawn through graduation.

Components
----------
- ``AgentLifecycleState``  — spawned → in_curriculum → graduated | failed
- ``AgentRecord``          — wraps a PlayerAgent with lifecycle metadata
- ``Cohort``               — population container with diversity metrics
- ``GraduationCriteria``   — multi-criteria graduation evaluation
- ``NurseryManager``       — top-level orchestrator
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from .models import (
    Curriculum,
    PlaythroughRecord,
    StoryGraph,
)
from .player_agent import (
    DecisionEngine,
    PersonalityVector,
    PlayerAgent,
)
from .story_engine import StoryEngine


# ---------------------------------------------------------------------------
#  Lifecycle
# ---------------------------------------------------------------------------

class AgentLifecycleState(Enum):
    SPAWNED = "spawned"
    IN_CURRICULUM = "in_curriculum"
    PENDING_GRADUATION = "pending_graduation"
    GRADUATED = "graduated"
    FAILED = "failed"
    ARCHIVED = "archived"


@dataclass
class AgentRecord:
    """Wraps a PlayerAgent with lifecycle tracking."""

    agent_id: str
    agent: PlayerAgent
    state: AgentLifecycleState = AgentLifecycleState.SPAWNED
    playthroughs: List[PlaythroughRecord] = field(default_factory=list)
    curriculum_progress: Dict[str, bool] = field(default_factory=dict)
    spawn_time: float = field(default_factory=time.time)
    graduation_time: Optional[float] = None
    graduation_score: Optional[float] = None


# ---------------------------------------------------------------------------
#  Cohort
# ---------------------------------------------------------------------------

class Cohort:
    """A group of agents progressing through curriculum together."""

    def __init__(self, cohort_id: str, agents: Optional[List[AgentRecord]] = None) -> None:
        self.cohort_id = cohort_id
        self._agents: Dict[str, AgentRecord] = {}
        if agents:
            for a in agents:
                self._agents[a.agent_id] = a

    def add_agent(self, record: AgentRecord) -> None:
        self._agents[record.agent_id] = record

    def get_agent(self, agent_id: str) -> AgentRecord:
        return self._agents[agent_id]

    @property
    def all_agents(self) -> List[AgentRecord]:
        return list(self._agents.values())

    def active_agents(self) -> List[AgentRecord]:
        return [
            a for a in self._agents.values()
            if a.state in (AgentLifecycleState.SPAWNED,
                           AgentLifecycleState.IN_CURRICULUM)
        ]

    def graduated_agents(self) -> List[AgentRecord]:
        return [a for a in self._agents.values()
                if a.state == AgentLifecycleState.GRADUATED]

    def population_personality_matrix(self) -> List[List[float]]:
        """Return (N, 21) matrix of current personality vectors."""
        return [a.agent.personality.vector for a in self.active_agents()]

    def diversity_score(self) -> float:
        """Mean pairwise cosine distance across active agents."""
        active = self.active_agents()
        n = len(active)
        if n < 2:
            return 0.0

        total_dist = 0.0
        pairs = 0
        for i in range(n):
            for j in range(i + 1, n):
                vi = active[i].agent.personality.vector
                vj = active[j].agent.personality.vector
                total_dist += active[i].agent.personality.cosine_distance_from(vj)
                pairs += 1

        return total_dist / pairs if pairs > 0 else 0.0

    def convergence_score(self) -> float:
        """Inverse of diversity — how similar the cohort has become."""
        d = self.diversity_score()
        return 1.0 - d

    @property
    def size(self) -> int:
        return len(self._agents)


# ---------------------------------------------------------------------------
#  Graduation
# ---------------------------------------------------------------------------

@dataclass
class GraduationResult:
    passed: bool
    scores: Dict[str, float]
    failing_criteria: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class GraduationCriteria:
    """
    Multi-criteria graduation evaluation.

    An agent graduates when ALL hold:
    1. Curriculum completed (all required stories played)
    2. Consistency >= threshold (stable tag distribution in recent stories)
    3. Safety >= threshold (H(d,pd) above minimum)
    4. Personality stability (low drift rate in final stories)
    5. Diversity preserved (cosine distance from all other graduates)
    """

    def __init__(
        self,
        min_consistency: float = 0.7,
        min_safety: float = 0.6,
        max_drift_rate: float = 0.05,
        min_diversity_distance: float = 0.15,
        stability_window: int = 5,
    ) -> None:
        self.min_consistency = min_consistency
        self.min_safety = min_safety
        self.max_drift_rate = max_drift_rate
        self.min_diversity_distance = min_diversity_distance
        self.stability_window = stability_window

    def evaluate(self, record: AgentRecord, cohort: Cohort) -> GraduationResult:
        """Evaluate an agent against all graduation criteria."""
        scores: Dict[str, float] = {}
        failing: List[str] = []
        recommendations: List[str] = []

        # 1. Curriculum completion
        completed = all(record.curriculum_progress.values()) if record.curriculum_progress else False
        scores["curriculum_completion"] = 1.0 if completed else 0.0
        if not completed:
            remaining = [k for k, v in record.curriculum_progress.items() if not v]
            failing.append("curriculum_incomplete")
            recommendations.append(f"Complete remaining stories: {remaining[:5]}")

        # 2. Consistency score
        consistency = self._compute_consistency(record)
        scores["consistency"] = consistency
        if consistency < self.min_consistency:
            failing.append("low_consistency")
            recommendations.append(f"Consistency {consistency:.3f} < {self.min_consistency}")

        # 3. Safety score (Hamiltonian)
        safety = self._compute_safety(record)
        scores["safety"] = safety
        if safety < self.min_safety:
            failing.append("low_safety")
            recommendations.append(f"Safety {safety:.3f} < {self.min_safety}")

        # 4. Personality stability
        drift_rate = self._compute_drift_rate(record)
        scores["drift_rate"] = drift_rate
        if drift_rate > self.max_drift_rate:
            failing.append("high_drift")
            recommendations.append(f"Drift rate {drift_rate:.4f} > {self.max_drift_rate}")

        # 5. Diversity preservation
        min_dist = self._compute_min_graduate_distance(record, cohort)
        scores["min_diversity"] = min_dist
        if min_dist < self.min_diversity_distance:
            failing.append("low_diversity")
            recommendations.append(
                f"Too similar to existing graduate (dist={min_dist:.3f})"
            )

        # Overall
        passed = len(failing) == 0
        scores["overall"] = sum(
            1.0 for k in ["curriculum_completion", "consistency", "safety"]
            if scores.get(k, 0) >= 0.5
        ) / 3.0

        return GraduationResult(
            passed=passed,
            scores=scores,
            failing_criteria=failing,
            recommendations=recommendations,
        )

    def _compute_consistency(self, record: AgentRecord) -> float:
        """
        Consistency = autocorrelation of choice-tag distributions across
        recent playthroughs.
        """
        recent = record.playthroughs[-self.stability_window:]
        if len(recent) < 2:
            return 0.0

        distributions: List[Dict[str, float]] = []
        for pt in recent:
            tags = pt.choice_tag_distribution
            total = max(sum(tags.values()), 1)
            distributions.append({k: v / total for k, v in tags.items()})

        # Pairwise cosine similarity between adjacent distributions
        similarities: List[float] = []
        for i in range(len(distributions) - 1):
            sim = self._dict_cosine_sim(distributions[i], distributions[i + 1])
            similarities.append(sim)

        return sum(similarities) / len(similarities) if similarities else 0.0

    def _compute_safety(self, record: AgentRecord) -> float:
        """
        Safety = H(d, pd) where d = deviation from center,
        pd = proportion of risky choices.
        """
        pv = record.agent.personality.vector
        # d = cosine distance from center (0.5 in all dims)
        center = [0.5] * 21
        d = record.agent.personality.cosine_distance_from(center)

        # pd = proportion of choices tagged as risky/aggressive/deceptive
        unsafe_tags = {"aggressive", "deceptive", "risky", "reckless"}
        total_choices = 0
        unsafe_choices = 0
        for pt in record.playthroughs:
            for step in pt.steps:
                total_choices += 1
                if step.choice.tags & unsafe_tags:
                    unsafe_choices += 1

        pd = unsafe_choices / max(total_choices, 1)
        # H(d, pd) = 1 / (1 + d + 2*pd)
        return 1.0 / (1.0 + d + 2.0 * pd)

    def _compute_drift_rate(self, record: AgentRecord) -> float:
        """Average L2 personality drift per playthrough in recent window."""
        snapshots = record.agent.personality.snapshots
        if len(snapshots) < 2:
            return 0.0
        recent = snapshots[-self.stability_window:]
        if len(recent) < 2:
            return 0.0
        total_drift = 0.0
        for i in range(1, len(recent)):
            prev = recent[i - 1][1]
            curr = recent[i][1]
            total_drift += math.sqrt(sum((a - b) ** 2 for a, b in zip(prev, curr)))
        return total_drift / (len(recent) - 1)

    def _compute_min_graduate_distance(self, record: AgentRecord, cohort: Cohort) -> float:
        """Minimum cosine distance from any already-graduated agent."""
        graduates = cohort.graduated_agents()
        if not graduates:
            return 1.0  # No graduates yet — max diversity
        min_dist = 1.0
        for grad in graduates:
            if grad.agent_id == record.agent_id:
                continue
            dist = record.agent.personality.cosine_distance_from(
                grad.agent.personality.vector
            )
            min_dist = min(min_dist, dist)
        return min_dist

    @staticmethod
    def _dict_cosine_sim(a: Dict[str, float], b: Dict[str, float]) -> float:
        """Cosine similarity between two sparse vectors (dicts)."""
        keys = set(a.keys()) | set(b.keys())
        if not keys:
            return 0.0
        dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
        mag_a = math.sqrt(sum(v ** 2 for v in a.values()))
        mag_b = math.sqrt(sum(v ** 2 for v in b.values()))
        if mag_a < 1e-12 or mag_b < 1e-12:
            return 0.0
        return dot / (mag_a * mag_b)


# ---------------------------------------------------------------------------
#  NurseryManager
# ---------------------------------------------------------------------------

class NurseryManager:
    """Top-level orchestrator for agent training through curricula."""

    def __init__(
        self,
        nursery_id: str,
        story_engine: Optional[StoryEngine] = None,
        curriculum: Optional[Curriculum] = None,
        graduation_criteria: Optional[GraduationCriteria] = None,
        cohort_size: int = 64,
        max_concurrent: int = 16,
    ) -> None:
        self._nursery_id = nursery_id
        self._engine = story_engine or StoryEngine()
        self._curriculum = curriculum
        self._criteria = graduation_criteria or GraduationCriteria()
        self._cohort_size = cohort_size
        self._max_concurrent = max_concurrent
        self._cohort: Optional[Cohort] = None

    @property
    def nursery_id(self) -> str:
        return self._nursery_id

    @property
    def cohort(self) -> Optional[Cohort]:
        return self._cohort

    def spawn_cohort(
        self,
        distribution: str = "uniform_center",
        seed: int = 42,
    ) -> Cohort:
        """
        Create N agents with varied initial personality vectors.

        Distributions:
          - uniform_center: uniform in [0.3, 0.7] per dim
          - diverse_poles: cluster near personality archetypes
        """
        import random as _rng

        agents: List[AgentRecord] = []
        base_rng = _rng.Random(seed)

        for i in range(self._cohort_size):
            agent_seed = base_rng.randint(0, 2 ** 31)

            if distribution == "diverse_poles":
                # Create agents clustered around personality archetypes
                archetype = i % 7  # 7 dim groups
                initial = [0.5] * 21
                for d in range(archetype * 3, min(archetype * 3 + 3, 21)):
                    initial[d] = base_rng.uniform(0.7, 0.95)
                pv = PersonalityVector(initial=initial, seed=agent_seed)
            else:
                pv = PersonalityVector(seed=agent_seed)

            agent_id = f"{self._nursery_id}_agent_{i:04d}"
            agent = PlayerAgent(
                agent_id=agent_id,
                personality=pv,
                seed=agent_seed,
            )
            record = AgentRecord(agent_id=agent_id, agent=agent)

            # Pre-fill curriculum progress map
            if self._curriculum:
                for sid in self._curriculum.all_story_ids:
                    record.curriculum_progress[sid] = False

            agents.append(record)

        self._cohort = Cohort(
            cohort_id=f"{self._nursery_id}_cohort_{seed}",
            agents=agents,
        )
        return self._cohort

    def run_agent_story(self, record: AgentRecord, graph: StoryGraph) -> PlaythroughRecord:
        """Run a single agent through a single story (synchronous)."""
        record.state = AgentLifecycleState.IN_CURRICULUM
        playthrough = record.agent.play_story(graph)
        record.playthroughs.append(playthrough)
        record.curriculum_progress[graph.story_id] = True
        return playthrough

    def run_curriculum_sync(self, story_graphs: Optional[Dict[str, StoryGraph]] = None) -> None:
        """
        Execute the full curriculum for all agents, synchronously.

        If *story_graphs* is provided, use those; otherwise, attempt to load
        from the StoryEngine using curriculum story IDs.
        """
        if self._cohort is None:
            raise RuntimeError("Must spawn_cohort() before running curriculum")
        if self._curriculum is None:
            raise RuntimeError("No curriculum configured")

        for phase in self._curriculum.phases:
            graphs: List[StoryGraph] = []
            for sid in phase.story_ids:
                if story_graphs and sid in story_graphs:
                    graphs.append(story_graphs[sid])
                else:
                    graphs.append(self._engine.load(sid))

            for record in self._cohort.active_agents():
                for graph in graphs:
                    self.run_agent_story(record, graph)

    def attempt_graduations(self) -> List[AgentRecord]:
        """Evaluate all agents against graduation criteria."""
        if self._cohort is None:
            return []

        graduated: List[AgentRecord] = []
        for rec in self._cohort.active_agents():
            # Only evaluate if curriculum is complete
            if self._curriculum and not all(rec.curriculum_progress.values()):
                continue

            rec.state = AgentLifecycleState.PENDING_GRADUATION
            result = self._criteria.evaluate(rec, self._cohort)

            if result.passed:
                rec.state = AgentLifecycleState.GRADUATED
                rec.graduation_time = time.time()
                rec.graduation_score = result.scores.get("overall", 0.0)
                graduated.append(rec)
            else:
                rec.state = AgentLifecycleState.FAILED

        return graduated

    def summary(self) -> Dict[str, Any]:
        """Return a summary of nursery status."""
        if self._cohort is None:
            return {"status": "no_cohort"}

        return {
            "nursery_id": self._nursery_id,
            "cohort_id": self._cohort.cohort_id,
            "total_agents": self._cohort.size,
            "active": len(self._cohort.active_agents()),
            "graduated": len(self._cohort.graduated_agents()),
            "diversity": self._cohort.diversity_score(),
            "curriculum_stories": self._curriculum.total_stories if self._curriculum else 0,
        }
