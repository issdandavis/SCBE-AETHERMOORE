"""
ChoiceEngine — Training Data Generation via Interactive Fiction
===============================================================

Wraps CSTM's StoryEngine + PlayerAgent to produce SFT training data
as a byproduct of game playthroughs.

Key features:
- Plays games (manually or autonomously) and captures every decision
- Exports playthrough trajectories as SFT instruction/response pairs
- Generates preference pairs for DPO training (good vs bad outcomes)
- Compatible with the existing training pipeline (codebase_to_sft format)

Usage::

    from concept_blocks.choice_engine import ChoiceEngine

    engine = ChoiceEngine()
    engine.load_game("training-data/games/governance_simulator.twee")

    # Autonomous playthrough
    records = engine.auto_play(n_agents=100, seed=42)

    # Export as SFT
    engine.export_sft("training-data/sft_games.jsonl")

Part of SCBE-AETHERMOORE (USPTO #63/961,403)
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .cstm.models import Choice, PlaythroughRecord, StoryGraph
from .cstm.player_agent import DecisionEngine, PersonalityVector, PlayerAgent
from .cstm.story_engine import StoryEngine


# ---------------------------------------------------------------------------
#  SFT record templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are SCBE-AETHERMOORE, a 14-layer AI safety and governance framework. "
    "You are playing an interactive training scenario. Make decisions based on "
    "the governance principles: safety first, ethical reasoning, and balanced "
    "risk assessment across the Six Sacred Tongues domains."
)

_INSTRUCTION_TEMPLATES = [
    "You are in the following scenario:\n\n{scene_text}\n\nAvailable choices:\n{choices_text}\n\nWhich choice do you make and why?",
    "Consider this governance dilemma:\n\n{scene_text}\n\nOptions:\n{choices_text}\n\nAnalyze each option and select the best one.",
    "As an SCBE-governed AI agent, you face this situation:\n\n{scene_text}\n\nPossible actions:\n{choices_text}\n\nWhat is the optimal decision?",
]


# ---------------------------------------------------------------------------
#  Trajectory record
# ---------------------------------------------------------------------------

@dataclass
class TrajectoryStep:
    """One step in a game trajectory, enriched for SFT export."""

    scene_id: str
    scene_title: str
    scene_text: str
    available_choices: List[Dict[str, Any]]
    selected_choice: Dict[str, Any]
    stats_before: Dict[str, float]
    stats_after: Dict[str, float]
    personality_before: List[float]
    personality_after: List[float]
    timestamp: float = field(default_factory=time.time)


@dataclass
class GameTrajectory:
    """Complete record of one playthrough with SFT-ready data."""

    agent_id: str
    game_id: str
    steps: List[TrajectoryStep] = field(default_factory=list)
    final_stats: Dict[str, float] = field(default_factory=dict)
    final_personality: List[float] = field(default_factory=list)
    outcome_score: float = 0.0  # Higher = better outcome for DPO
    completed: bool = False

    @property
    def total_steps(self) -> int:
        return len(self.steps)


# ---------------------------------------------------------------------------
#  ChoiceEngine
# ---------------------------------------------------------------------------

class ChoiceEngine:
    """
    Training data generation engine that wraps CSTM game playthrough.

    Plays interactive fiction games (Twee/JSON format) and captures
    every decision as SFT-compatible training data.
    """

    def __init__(self) -> None:
        self._engine = StoryEngine()
        self._trajectories: List[GameTrajectory] = []
        self._games: Dict[str, StoryGraph] = {}

    def load_game(self, path: str | Path, game_id: str | None = None) -> StoryGraph:
        """Load a game file (Twee or JSON format)."""
        graph = self._engine.load(path, story_id=game_id)
        errors = graph.validate()
        if errors:
            error_msgs = [f"  {e}" for e in errors]
            raise ValueError(
                f"Game validation failed with {len(errors)} errors:\n"
                + "\n".join(error_msgs)
            )
        self._games[graph.story_id] = graph
        return graph

    def load_game_string(self, text: str, fmt: str = "twee", game_id: str | None = None) -> StoryGraph:
        """Load a game from a string."""
        graph = self._engine.load_from_string(text, fmt=fmt, story_id=game_id)
        self._games[graph.story_id] = graph
        return graph

    # ------------------------------------------------------------------
    #  Autonomous playthrough
    # ------------------------------------------------------------------

    def auto_play(
        self,
        game_id: str | None = None,
        n_agents: int = 100,
        seed: int = 42,
        temperature: float = 1.0,
        initial_stats: Dict[str, float] | None = None,
    ) -> List[GameTrajectory]:
        """Run n_agents autonomous playthroughs and capture trajectories."""
        if game_id is None:
            if not self._games:
                raise ValueError("No games loaded. Call load_game() first.")
            game_id = next(iter(self._games))

        graph = self._games[game_id]
        trajectories: List[GameTrajectory] = []
        rng = random.Random(seed)

        for i in range(n_agents):
            agent_seed = rng.randint(0, 2**31)
            agent = PlayerAgent(
                agent_id=f"agent-{i:04d}",
                personality=PersonalityVector(seed=agent_seed),
                decision_engine=DecisionEngine(temperature=temperature),
                initial_stats=dict(initial_stats) if initial_stats else {},
                seed=agent_seed,
            )

            trajectory = self._play_and_capture(agent, graph)
            trajectories.append(trajectory)

        self._trajectories.extend(trajectories)
        return trajectories

    def _play_and_capture(
        self, agent: PlayerAgent, graph: StoryGraph
    ) -> GameTrajectory:
        """Play through a game and capture every step as a trajectory."""
        entries = graph.entry_points
        if not entries:
            raise ValueError(f"Game '{graph.story_id}' has no entry point")

        trajectory = GameTrajectory(
            agent_id=agent.agent_id,
            game_id=graph.story_id,
        )

        current = graph.get_scene(entries[0])
        max_steps = graph.total_scenes() * 3

        for _ in range(max_steps):
            if current.is_exit:
                break

            choices = graph.get_available_choices(current.scene_id, agent.stats)
            if not choices:
                break

            # Capture pre-decision state
            personality_before = agent.personality.vector
            stats_before = dict(agent.stats)

            # Make decision
            chosen = agent.play_scene(current, choices)

            # Capture post-decision state
            personality_after = agent.personality.vector
            stats_after = dict(agent.stats)

            # Record trajectory step
            step = TrajectoryStep(
                scene_id=current.scene_id,
                scene_title=current.title,
                scene_text=current.text,
                available_choices=[
                    {
                        "label": c.label,
                        "choice_id": c.choice_id,
                        "tags": list(c.tags),
                        "difficulty": c.difficulty,
                        "stat_effects": dict(c.stat_effects),
                    }
                    for c in choices
                ],
                selected_choice={
                    "label": chosen.label,
                    "choice_id": chosen.choice_id,
                    "tags": list(chosen.tags),
                    "difficulty": chosen.difficulty,
                    "stat_effects": dict(chosen.stat_effects),
                },
                stats_before=stats_before,
                stats_after=stats_after,
                personality_before=personality_before,
                personality_after=personality_after,
            )
            trajectory.steps.append(step)

            current = graph.get_scene(chosen.next_scene_id)

        trajectory.final_stats = dict(agent.stats)
        trajectory.final_personality = agent.personality.vector
        trajectory.completed = current.is_exit
        trajectory.outcome_score = self._compute_outcome_score(trajectory)

        return trajectory

    def _compute_outcome_score(self, trajectory: GameTrajectory) -> float:
        """Score a trajectory's outcome (higher = better for DPO ranking)."""
        score = 0.0

        # Completion bonus
        if trajectory.completed:
            score += 1.0

        # Stat-based scoring (higher stats = better)
        for stat_val in trajectory.final_stats.values():
            score += max(0.0, stat_val) * 0.1

        # Personality balance (closer to 0.5 on all dims = more balanced)
        if trajectory.final_personality:
            balance = sum(
                1.0 - abs(v - 0.5) * 2 for v in trajectory.final_personality
            ) / len(trajectory.final_personality)
            score += balance

        return score

    # ------------------------------------------------------------------
    #  SFT Export
    # ------------------------------------------------------------------

    def export_sft(
        self, output_path: str | Path, include_chat_format: bool = True
    ) -> int:
        """Export all captured trajectories as SFT training data."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        records: List[Dict[str, Any]] = []
        rng = random.Random(42)

        for trajectory in self._trajectories:
            for step in trajectory.steps:
                sft_record = self._step_to_sft(step, trajectory, rng)
                records.append(sft_record)

        # Assign IDs
        for i, record in enumerate(records):
            record["id"] = f"sft-game-{i+1:05d}"

        # Write SFT format
        with open(path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # Also write chat format if requested
        if include_chat_format:
            chat_path = path.with_stem(path.stem + "_chat")
            with open(chat_path, "w", encoding="utf-8") as f:
                for record in records:
                    chat = {
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": record["instruction"]},
                            {"role": "assistant", "content": record["response"]},
                        ]
                    }
                    f.write(json.dumps(chat, ensure_ascii=False) + "\n")

        return len(records)

    def _step_to_sft(
        self,
        step: TrajectoryStep,
        trajectory: GameTrajectory,
        rng: random.Random,
    ) -> Dict[str, Any]:
        """Convert a trajectory step to an SFT instruction/response pair."""
        # Format choices as numbered list
        choices_text = "\n".join(
            f"  {i+1}. {c['label']}"
            for i, c in enumerate(step.available_choices)
        )

        # Select instruction template
        template = rng.choice(_INSTRUCTION_TEMPLATES)
        instruction = template.format(
            scene_text=step.scene_text,
            choices_text=choices_text,
        )

        # Build response
        selected_label = step.selected_choice["label"]
        selected_tags = step.selected_choice.get("tags", [])

        response_parts = [
            f"I choose: **{selected_label}**\n",
        ]

        # Add reasoning based on tags
        if selected_tags:
            response_parts.append(
                f"This decision aligns with: {', '.join(selected_tags)}."
            )

        # Add stat effects
        effects = step.selected_choice.get("stat_effects", {})
        if effects:
            effect_str = ", ".join(
                f"{k}: {'+' if v > 0 else ''}{v}" for k, v in effects.items()
            )
            response_parts.append(f"Expected impact: {effect_str}.")

        # Add governance reasoning
        response_parts.append(
            "\nGovernance analysis: This choice balances safety and effectiveness "
            "within the SCBE framework's constraints."
        )

        response = "\n".join(response_parts)

        return {
            "instruction": instruction,
            "response": response,
            "category": "governance",
            "metadata": {
                "source": "scbe_aethermoore",
                "origin": "training_game",
                "source_type": "game_playthrough",
                "game_id": trajectory.game_id,
                "agent_id": trajectory.agent_id,
                "scene_id": step.scene_id,
                "track": "governance",
                "quality": {"dedup": True, "validated": True},
            },
        }

    # ------------------------------------------------------------------
    #  DPO Export (preference pairs)
    # ------------------------------------------------------------------

    def export_dpo_pairs(
        self, output_path: str | Path, min_score_diff: float = 0.5
    ) -> int:
        """
        Export preference pairs for DPO training.

        Pairs trajectories with high vs low outcome scores to create
        (chosen, rejected) pairs for preference optimization.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Sort trajectories by outcome score
        sorted_trajs = sorted(
            self._trajectories, key=lambda t: t.outcome_score, reverse=True
        )

        pairs: List[Dict[str, Any]] = []
        n = len(sorted_trajs)

        # Pair top half with bottom half
        for i in range(min(n // 4, n - n // 4)):
            good = sorted_trajs[i]
            bad = sorted_trajs[-(i + 1)]

            if good.outcome_score - bad.outcome_score < min_score_diff:
                continue

            # Create pairs from corresponding steps
            for step_idx in range(min(len(good.steps), len(bad.steps))):
                good_step = good.steps[step_idx]
                bad_step = bad.steps[step_idx]

                if good_step.scene_id != bad_step.scene_id:
                    continue  # Only compare same scenes

                choices_text = "\n".join(
                    f"  {j+1}. {c['label']}"
                    for j, c in enumerate(good_step.available_choices)
                )

                pair = {
                    "prompt": (
                        f"Scenario: {good_step.scene_text}\n\n"
                        f"Choices:\n{choices_text}\n\n"
                        f"Which choice is best?"
                    ),
                    "chosen": f"I choose: {good_step.selected_choice['label']}",
                    "rejected": f"I choose: {bad_step.selected_choice['label']}",
                    "metadata": {
                        "game_id": good.game_id,
                        "scene_id": good_step.scene_id,
                        "good_score": good.outcome_score,
                        "bad_score": bad.outcome_score,
                    },
                }
                pairs.append(pair)

        with open(path, "w", encoding="utf-8") as f:
            for pair in pairs:
                f.write(json.dumps(pair, ensure_ascii=False) + "\n")

        return len(pairs)

    # ------------------------------------------------------------------
    #  Stats
    # ------------------------------------------------------------------

    @property
    def total_trajectories(self) -> int:
        return len(self._trajectories)

    @property
    def total_steps(self) -> int:
        return sum(t.total_steps for t in self._trajectories)

    def summary(self) -> Dict[str, Any]:
        """Return summary statistics of all captured trajectories."""
        if not self._trajectories:
            return {"total_trajectories": 0, "total_steps": 0}

        scores = [t.outcome_score for t in self._trajectories]
        completed = sum(1 for t in self._trajectories if t.completed)

        return {
            "total_trajectories": len(self._trajectories),
            "total_steps": self.total_steps,
            "completed": completed,
            "completion_rate": completed / len(self._trajectories),
            "avg_steps": self.total_steps / len(self._trajectories),
            "avg_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "games": list(self._games.keys()),
        }
