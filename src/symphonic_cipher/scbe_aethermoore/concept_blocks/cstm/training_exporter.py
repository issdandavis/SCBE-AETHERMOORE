"""
CSTM — Training Data Exporter
===============================

Convert CSTM playthrough records into training data formats:

- **SFT pairs** — (instruction, response) for supervised fine-tuning
- **DPO pairs** — (prompt, chosen, rejected) for Direct Preference Optimization
- **JSONL export** — HuggingFace-compatible line-delimited JSON

Each playthrough step becomes one or more training examples by combining
scene context, available choices, the agent's decision, and the
personality-driven rationale.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import Choice, PlaythroughRecord, PlaythroughStep, StoryGraph
from .player_agent import DIM_NAMES, PersonalityVector, TAG_DRIFT_MAP


# ---------------------------------------------------------------------------
#  Training data record types
# ---------------------------------------------------------------------------

@dataclass
class SFTPair:
    """Supervised fine-tuning example."""

    instruction: str
    response: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instruction": self.instruction,
            "response": self.response,
            **self.metadata,
        }


@dataclass
class DPOTriple:
    """Direct Preference Optimization example."""

    prompt: str
    chosen: str
    rejected: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt": self.prompt,
            "chosen": self.chosen,
            "rejected": self.rejected,
            **self.metadata,
        }


# ---------------------------------------------------------------------------
#  Rationale generation (personality-based)
# ---------------------------------------------------------------------------

def _personality_rationale(
    personality: Optional[List[float]],
    choice: Choice,
) -> str:
    """Generate a brief rationale explaining why this personality chose this."""
    if personality is None or len(personality) != 21:
        return f"Selected '{choice.label}' based on current state."

    # Find which personality traits aligned with this choice's tags
    alignments: List[str] = []
    for tag in choice.tags:
        drift_spec = TAG_DRIFT_MAP.get(tag, [])
        for dim_idx, direction in drift_spec:
            val = personality[dim_idx]
            name = DIM_NAMES[dim_idx]
            if (direction > 0 and val > 0.6) or (direction < 0 and val < 0.4):
                alignments.append(f"{name}={val:.2f}")

    if alignments:
        traits = ", ".join(alignments[:3])
        return (
            f"Selected '{choice.label}' — aligned with personality traits "
            f"({traits}). Difficulty: {choice.difficulty:.1f}."
        )
    if choice.difficulty > 0.5:
        return f"Selected '{choice.label}' — a challenging path (difficulty {choice.difficulty:.1f})."
    return f"Selected '{choice.label}' as the best available option."


def _format_choices(choices: List[Choice]) -> str:
    """Format available choices for an instruction prompt."""
    lines = []
    for i, c in enumerate(choices, 1):
        tags_str = f" [{', '.join(sorted(c.tags))}]" if c.tags else ""
        diff_str = f" (difficulty: {c.difficulty:.1f})" if c.difficulty > 0 else ""
        lines.append(f"  {i}. {c.label}{tags_str}{diff_str}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  Step-level converters
# ---------------------------------------------------------------------------

def step_to_sft(
    step: PlaythroughStep,
    story_id: str,
    agent_id: str,
    scene_text: Optional[str] = None,
) -> Optional[SFTPair]:
    """Convert a single playthrough step to an SFT pair."""
    choices = step.available_choices
    if not choices:
        return None

    scene_ctx = f"Scene: {step.scene_id}"
    if scene_text:
        scene_ctx += f"\n{scene_text}"

    instruction = (
        f"You are navigating a branching narrative.\n\n"
        f"{scene_ctx}\n\n"
        f"Available choices:\n{_format_choices(choices)}\n\n"
        f"Which option do you choose and why?"
    )

    rationale = _personality_rationale(step.personality_snapshot, step.choice)
    response = rationale

    pair_hash = hashlib.sha256(
        f"{story_id}:{step.scene_id}:{step.choice.choice_id}".encode()
    ).hexdigest()[:12]

    return SFTPair(
        instruction=instruction,
        response=response,
        metadata={
            "source": "cstm",
            "story_id": story_id,
            "scene_id": step.scene_id,
            "agent_id": agent_id,
            "choice_id": step.choice.choice_id,
            "choice_tags": sorted(step.choice.tags),
            "difficulty": step.choice.difficulty,
            "pair_hash": pair_hash,
        },
    )


def step_to_dpo(
    step: PlaythroughStep,
    story_id: str,
    agent_id: str,
    scene_text: Optional[str] = None,
) -> List[DPOTriple]:
    """Convert a single step to DPO triples (one per rejected alternative)."""
    choices = step.available_choices
    alternatives = [c for c in choices if c.choice_id != step.choice.choice_id]
    if not alternatives:
        return []

    scene_ctx = f"Scene: {step.scene_id}"
    if scene_text:
        scene_ctx += f"\n{scene_text}"

    prompt = (
        f"You are navigating a branching narrative.\n\n"
        f"{scene_ctx}\n\n"
        f"Available choices:\n{_format_choices(choices)}\n\n"
        f"Which option do you choose and why?"
    )

    chosen_rationale = _personality_rationale(step.personality_snapshot, step.choice)
    triples = []

    for alt in alternatives:
        alt_rationale = f"Selected '{alt.label}' — an alternative path."
        triples.append(DPOTriple(
            prompt=prompt,
            chosen=chosen_rationale,
            rejected=alt_rationale,
            metadata={
                "source": "cstm_dpo",
                "story_id": story_id,
                "scene_id": step.scene_id,
                "agent_id": agent_id,
                "chosen_id": step.choice.choice_id,
                "rejected_id": alt.choice_id,
                "chosen_tags": sorted(step.choice.tags),
                "rejected_tags": sorted(alt.tags),
            },
        ))

    return triples


# ---------------------------------------------------------------------------
#  Playthrough-level converters
# ---------------------------------------------------------------------------

def playthrough_to_sft(
    record: PlaythroughRecord,
    story_graph: Optional[StoryGraph] = None,
) -> List[SFTPair]:
    """Convert an entire playthrough to SFT pairs."""
    pairs: List[SFTPair] = []
    for step in record.steps:
        scene_text = None
        if story_graph:
            try:
                scene = story_graph.get_scene(step.scene_id)
                scene_text = scene.text
            except KeyError:
                pass
        pair = step_to_sft(step, record.story_id, record.agent_id, scene_text)
        if pair:
            pairs.append(pair)
    return pairs


def playthrough_to_dpo(
    record: PlaythroughRecord,
    story_graph: Optional[StoryGraph] = None,
) -> List[DPOTriple]:
    """Convert an entire playthrough to DPO triples."""
    triples: List[DPOTriple] = []
    for step in record.steps:
        scene_text = None
        if story_graph:
            try:
                scene = story_graph.get_scene(step.scene_id)
                scene_text = scene.text
            except KeyError:
                pass
        triples.extend(step_to_dpo(step, record.story_id, record.agent_id, scene_text))
    return triples


# ---------------------------------------------------------------------------
#  TrainingExporter — main class
# ---------------------------------------------------------------------------

class TrainingExporter:
    """
    Export CSTM playthrough data as training datasets.

    Usage::

        exporter = TrainingExporter()
        exporter.add_playthrough(record, story_graph)
        exporter.export_sft("training-data/cstm/sft.jsonl")
        exporter.export_dpo("training-data/cstm/dpo.jsonl")
        stats = exporter.stats()
    """

    def __init__(self) -> None:
        self._sft_pairs: List[SFTPair] = []
        self._dpo_triples: List[DPOTriple] = []
        self._records_processed: int = 0

    def add_playthrough(
        self,
        record: PlaythroughRecord,
        story_graph: Optional[StoryGraph] = None,
    ) -> Tuple[int, int]:
        """
        Process one playthrough record, generating SFT and DPO data.

        Returns (sft_count, dpo_count) of pairs generated.
        """
        sft = playthrough_to_sft(record, story_graph)
        dpo = playthrough_to_dpo(record, story_graph)
        self._sft_pairs.extend(sft)
        self._dpo_triples.extend(dpo)
        self._records_processed += 1
        return len(sft), len(dpo)

    def add_playthroughs(
        self,
        records: List[PlaythroughRecord],
        story_graphs: Optional[Dict[str, StoryGraph]] = None,
    ) -> Tuple[int, int]:
        """Process multiple playthroughs."""
        total_sft = 0
        total_dpo = 0
        for rec in records:
            graph = (story_graphs or {}).get(rec.story_id)
            s, d = self.add_playthrough(rec, graph)
            total_sft += s
            total_dpo += d
        return total_sft, total_dpo

    def export_sft(self, path: str, append: bool = False) -> int:
        """Export SFT pairs as JSONL. Returns line count."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with open(p, mode, encoding="utf-8") as f:
            for pair in self._sft_pairs:
                f.write(json.dumps(pair.to_dict(), ensure_ascii=False) + "\n")
        return len(self._sft_pairs)

    def export_dpo(self, path: str, append: bool = False) -> int:
        """Export DPO triples as JSONL. Returns line count."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with open(p, mode, encoding="utf-8") as f:
            for triple in self._dpo_triples:
                f.write(json.dumps(triple.to_dict(), ensure_ascii=False) + "\n")
        return len(self._dpo_triples)

    def export_combined(self, path: str) -> int:
        """Export both SFT and DPO in a single JSONL with a 'type' field."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with open(p, "w", encoding="utf-8") as f:
            for pair in self._sft_pairs:
                d = pair.to_dict()
                d["type"] = "sft"
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
                count += 1
            for triple in self._dpo_triples:
                d = triple.to_dict()
                d["type"] = "dpo"
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
                count += 1
        return count

    def stats(self) -> Dict[str, Any]:
        """Return export statistics."""
        return {
            "records_processed": self._records_processed,
            "sft_pairs": len(self._sft_pairs),
            "dpo_triples": len(self._dpo_triples),
            "total_examples": len(self._sft_pairs) + len(self._dpo_triples),
            "unique_stories": len(set(
                p.metadata.get("story_id", "") for p in self._sft_pairs
            )),
            "unique_agents": len(set(
                p.metadata.get("agent_id", "") for p in self._sft_pairs
            )),
        }

    def clear(self) -> None:
        """Reset all accumulated data."""
        self._sft_pairs.clear()
        self._dpo_triples.clear()
        self._records_processed = 0
