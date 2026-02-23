"""
CSTM — KernelExtractor
=======================

Given a graduated agent's playthrough history, extract a portable
"personality kernel" — a compact representation of the agent's learned
behaviour.

Components
----------
- ``DecisionNode``     — single decision point in history
- ``DecisionTree``     — complete record of all decisions
- ``DriftAnalyzer``    — personality vector evolution analysis
- ``PreferenceMatrix`` — tag×phase frequency matrix
- ``GraduatedKernel``  — the final kernel artefact
- ``KernelExtractor``  — pipeline to build a kernel from an AgentRecord
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from .models import Choice, Curriculum, CurriculumPhase, PlaythroughRecord
from .player_agent import DIM_NAMES, PersonalityVector


# ---------------------------------------------------------------------------
#  DecisionTree
# ---------------------------------------------------------------------------

@dataclass
class DecisionNode:
    """A single decision point in the agent's history."""

    scene_id: str
    story_id: str
    chosen: Choice
    alternatives: List[Choice]
    personality_at_decision: List[float]
    stats_at_decision: Dict[str, float]
    confidence: float = 0.0       # Score gap between chosen and runner-up
    timestamp: float = 0.0


class DecisionTree:
    """Complete record of every decision an agent made."""

    def __init__(self, agent_id: str, nodes: Optional[List[DecisionNode]] = None) -> None:
        self.agent_id = agent_id
        self._nodes: List[DecisionNode] = list(nodes) if nodes else []

    def add_node(self, node: DecisionNode) -> None:
        self._nodes.append(node)

    @property
    def nodes(self) -> List[DecisionNode]:
        return list(self._nodes)

    @property
    def total_decisions(self) -> int:
        return len(self._nodes)

    def choices_by_tag(self) -> Dict[str, int]:
        """Count how many times each choice tag was selected."""
        counts: Dict[str, int] = {}
        for node in self._nodes:
            for tag in node.chosen.tags:
                counts[tag] = counts.get(tag, 0) + 1
        return counts

    def consistency_over_time(self, window: int = 20) -> List[float]:
        """Sliding window autocorrelation of tag distributions."""
        if len(self._nodes) < window * 2:
            return []

        scores: List[float] = []
        for i in range(window, len(self._nodes)):
            prev_window = self._nodes[i - window:i]
            curr_window = self._nodes[max(0, i - window // 2):i]

            prev_dist = self._tag_dist(prev_window)
            curr_dist = self._tag_dist(curr_window)
            scores.append(self._dict_cosine_sim(prev_dist, curr_dist))

        return scores

    def pivotal_decisions(self, threshold: float = 0.3) -> List[DecisionNode]:
        """Decisions where personality drift exceeded threshold."""
        pivotal: List[DecisionNode] = []
        for i in range(1, len(self._nodes)):
            prev = self._nodes[i - 1].personality_at_decision
            curr = self._nodes[i].personality_at_decision
            drift = math.sqrt(sum((a - b) ** 2 for a, b in zip(prev, curr)))
            if drift >= threshold:
                pivotal.append(self._nodes[i])
        return pivotal

    def to_preference_pairs(self) -> List[Tuple[str, str]]:
        """
        Convert to (chosen, rejected) text pairs for DPO training.

        For each decision with alternatives:
            chosen  = chosen_label
            rejected = best_alternative_label
        """
        pairs: List[Tuple[str, str]] = []
        for node in self._nodes:
            if node.alternatives:
                best_alt = node.alternatives[0]  # First alternative
                pairs.append((node.chosen.label, best_alt.label))
        return pairs

    @staticmethod
    def _tag_dist(nodes: List[DecisionNode]) -> Dict[str, float]:
        counts: Dict[str, int] = {}
        for n in nodes:
            for tag in n.chosen.tags:
                counts[tag] = counts.get(tag, 0) + 1
        total = max(sum(counts.values()), 1)
        return {k: v / total for k, v in counts.items()}

    @staticmethod
    def _dict_cosine_sim(a: Dict[str, float], b: Dict[str, float]) -> float:
        keys = set(a.keys()) | set(b.keys())
        if not keys:
            return 0.0
        dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
        ma = math.sqrt(sum(v ** 2 for v in a.values()))
        mb = math.sqrt(sum(v ** 2 for v in b.values()))
        if ma < 1e-12 or mb < 1e-12:
            return 0.0
        return dot / (ma * mb)


# ---------------------------------------------------------------------------
#  DriftAnalyzer
# ---------------------------------------------------------------------------

class DriftAnalyzer:
    """Analyze how the personality vector evolved over the curriculum."""

    def __init__(self, snapshots: List[Tuple[float, List[float]]]) -> None:
        self._snapshots = snapshots

    @property
    def trajectory(self) -> List[List[float]]:
        """Return (T, 21) list of personality vectors over time."""
        return [snap for _, snap in self._snapshots]

    def drift_per_dimension(self) -> Dict[str, float]:
        """Net change per personality dimension from start to end."""
        if len(self._snapshots) < 2:
            return {name: 0.0 for name in DIM_NAMES}
        first = self._snapshots[0][1]
        last = self._snapshots[-1][1]
        return {DIM_NAMES[i]: last[i] - first[i] for i in range(21)}

    def phase_transitions(self, threshold: float = 0.1) -> List[int]:
        """Indices where personality shifted sharply."""
        transitions: List[int] = []
        for i in range(1, len(self._snapshots)):
            prev = self._snapshots[i - 1][1]
            curr = self._snapshots[i][1]
            drift = math.sqrt(sum((a - b) ** 2 for a, b in zip(prev, curr)))
            if drift >= threshold:
                transitions.append(i)
        return transitions

    def stability_period_start(self, threshold: float = 0.02) -> Optional[int]:
        """Index where drift rate dropped below threshold and stayed low."""
        for i in range(1, len(self._snapshots)):
            # Check if all subsequent drifts are below threshold
            all_stable = True
            for j in range(i, len(self._snapshots)):
                if j == 0:
                    continue
                prev = self._snapshots[j - 1][1]
                curr = self._snapshots[j][1]
                drift = math.sqrt(sum((a - b) ** 2 for a, b in zip(prev, curr)))
                if drift >= threshold:
                    all_stable = False
                    break
            if all_stable:
                return i
        return None

    def total_drift(self) -> float:
        """Total L2 path length through personality space."""
        total = 0.0
        for i in range(1, len(self._snapshots)):
            prev = self._snapshots[i - 1][1]
            curr = self._snapshots[i][1]
            total += math.sqrt(sum((a - b) ** 2 for a, b in zip(prev, curr)))
        return total


# ---------------------------------------------------------------------------
#  PreferenceMatrix
# ---------------------------------------------------------------------------

class PreferenceMatrix:
    """
    Tag × phase frequency matrix.

    Rows: choice tag categories
    Columns: curriculum phases
    Values: normalized selection frequency
    """

    def __init__(
        self,
        tag_phase_counts: Dict[str, Dict[str, int]],
    ) -> None:
        self._data = tag_phase_counts
        self._tags = sorted(tag_phase_counts.keys())
        phases_set: Set[str] = set()
        for pmap in tag_phase_counts.values():
            phases_set |= set(pmap.keys())
        self._phases = sorted(phases_set)

    @classmethod
    def from_playthroughs(
        cls,
        playthroughs: List[PlaythroughRecord],
        story_phase_map: Optional[Dict[str, str]] = None,
    ) -> "PreferenceMatrix":
        """Build from playthrough records with optional phase mapping."""
        data: Dict[str, Dict[str, int]] = {}
        for pt in playthroughs:
            phase = (story_phase_map or {}).get(pt.story_id, "unknown")
            for step in pt.steps:
                for tag in step.choice.tags:
                    if tag not in data:
                        data[tag] = {}
                    data[tag][phase] = data[tag].get(phase, 0) + 1
        return cls(data)

    def dominant_strategy(self) -> str:
        """Overall most-selected tag."""
        totals = {tag: sum(phases.values()) for tag, phases in self._data.items()}
        if not totals:
            return "none"
        return max(totals, key=totals.get)

    def strategy_by_phase(self) -> Dict[str, str]:
        """Dominant tag per phase."""
        result: Dict[str, str] = {}
        for phase in self._phases:
            best_tag = ""
            best_count = 0
            for tag in self._tags:
                count = self._data.get(tag, {}).get(phase, 0)
                if count > best_count:
                    best_count = count
                    best_tag = tag
            result[phase] = best_tag
        return result

    def consistency_score(self) -> float:
        """How consistent the strategy is across phases. 1.0 = perfectly uniform."""
        if not self._phases or not self._tags:
            return 0.0

        # Build normalized distribution per phase
        distributions: List[Dict[str, float]] = []
        for phase in self._phases:
            dist: Dict[str, float] = {}
            total = 0
            for tag in self._tags:
                c = self._data.get(tag, {}).get(phase, 0)
                dist[tag] = c
                total += c
            if total > 0:
                dist = {k: v / total for k, v in dist.items()}
            distributions.append(dist)

        if len(distributions) < 2:
            return 1.0

        # Mean pairwise cosine similarity
        sims: List[float] = []
        for i in range(len(distributions)):
            for j in range(i + 1, len(distributions)):
                sims.append(self._dict_cosine_sim(distributions[i], distributions[j]))

        return sum(sims) / len(sims) if sims else 0.0

    def to_dict(self) -> Dict[str, Dict[str, int]]:
        return {tag: dict(phases) for tag, phases in self._data.items()}

    @staticmethod
    def _dict_cosine_sim(a: Dict[str, float], b: Dict[str, float]) -> float:
        keys = set(a.keys()) | set(b.keys())
        if not keys:
            return 0.0
        dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
        ma = math.sqrt(sum(v ** 2 for v in a.values()))
        mb = math.sqrt(sum(v ** 2 for v in b.values()))
        if ma < 1e-12 or mb < 1e-12:
            return 0.0
        return dot / (ma * mb)


# ---------------------------------------------------------------------------
#  GraduatedKernel
# ---------------------------------------------------------------------------

@dataclass
class GraduatedKernel:
    """The complete extracted kernel for a graduated agent."""

    agent_id: str
    nursery_id: str
    graduation_timestamp: float
    final_personality: List[float]          # 21D
    initial_personality: List[float]        # 21D
    total_drift: float
    decision_tree: DecisionTree
    drift_analysis: DriftAnalyzer
    preference_matrix: PreferenceMatrix
    final_stats: Dict[str, float]
    graduation_scores: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> Dict[str, Any]:
        """Serialise kernel to JSON-compatible dict."""
        return {
            "agent_id": self.agent_id,
            "nursery_id": self.nursery_id,
            "graduation_timestamp": self.graduation_timestamp,
            "final_personality": self.final_personality,
            "initial_personality": self.initial_personality,
            "total_drift": self.total_drift,
            "total_decisions": self.decision_tree.total_decisions,
            "dominant_strategy": self.preference_matrix.dominant_strategy(),
            "preference_consistency": self.preference_matrix.consistency_score(),
            "drift_per_dimension": self.drift_analysis.drift_per_dimension(),
            "pivotal_decisions": len(self.decision_tree.pivotal_decisions()),
            "final_stats": self.final_stats,
            "graduation_scores": self.graduation_scores,
            "dominant_traits": [
                {"name": name, "value": val}
                for name, val in self._dominant_traits(5)
            ],
            "metadata": self.metadata,
        }

    def save(self, path: Path) -> None:
        """Save kernel to a JSON file."""
        path.write_text(json.dumps(self.to_json(), indent=2), encoding="utf-8")

    def _dominant_traits(self, top_k: int) -> List[Tuple[str, float]]:
        indexed = [(DIM_NAMES[i], self.final_personality[i]) for i in range(21)]
        indexed.sort(key=lambda t: t[1], reverse=True)
        return indexed[:top_k]


# ---------------------------------------------------------------------------
#  KernelExtractor
# ---------------------------------------------------------------------------

class KernelExtractor:
    """Pipeline to extract a GraduatedKernel from an AgentRecord."""

    def extract(
        self,
        record: Any,  # AgentRecord (avoid circular import)
        nursery_id: str = "default",
        story_phase_map: Optional[Dict[str, str]] = None,
    ) -> GraduatedKernel:
        """Build a complete GraduatedKernel from a graduated agent's record."""
        agent = record.agent

        # Build decision tree from all playthroughs
        tree = DecisionTree(agent_id=record.agent_id)
        for pt in record.playthroughs:
            for step in pt.steps:
                # Reconstruct alternatives (all choices minus the chosen one)
                # We don't have the full list here, but we store the chosen choice
                tree.add_node(DecisionNode(
                    scene_id=step.scene_id,
                    story_id=pt.story_id,
                    chosen=step.choice,
                    alternatives=[],
                    personality_at_decision=step.personality_snapshot or agent.personality.vector,
                    stats_at_decision=step.stats_snapshot,
                ))

        # Build drift analyzer from personality snapshots
        snapshots = agent.personality.snapshots
        drift_analyzer = DriftAnalyzer(snapshots)

        # Build preference matrix
        pref_matrix = PreferenceMatrix.from_playthroughs(
            record.playthroughs,
            story_phase_map=story_phase_map,
        )

        # Get initial personality (first snapshot or current)
        initial_personality = snapshots[0][1] if snapshots else agent.personality.vector

        return GraduatedKernel(
            agent_id=record.agent_id,
            nursery_id=nursery_id,
            graduation_timestamp=record.graduation_time or time.time(),
            final_personality=agent.personality.vector,
            initial_personality=initial_personality,
            total_drift=drift_analyzer.total_drift(),
            decision_tree=tree,
            drift_analysis=drift_analyzer,
            preference_matrix=pref_matrix,
            final_stats=dict(agent.stats),
            graduation_scores=record.graduation_score or {},
        )


# Need time for default timestamp
import time
