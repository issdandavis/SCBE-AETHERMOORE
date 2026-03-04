"""
Training Pipeline — Game Events → SFT → HuggingFace Fine-Tune (Python reference).

Mirrors src/game/trainingPipeline.ts.

Flow:
  1. Player PAYS Energy Tokens for an adventure.
  2. Game events stream into a 3-tier dataset: RAW → QUARANTINED → APPROVED.
  3. Approved events become SFT (Supervised Fine-Tune) pairs.
  4. SFT pairs batch and push to HuggingFace dataset repo.
  5. Fine-tune job trains the companion model.
  6. Updated model deploys back into the companion.

A3: Causality — events are time-ordered, append-only.
A5: Composition — full audit trail from payment → events → SFT → model.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple

# ---------------------------------------------------------------------------
#  Event Types
# ---------------------------------------------------------------------------

GameEventType = Literal[
    "combat_action", "companion_command", "companion_response",
    "evolution_choice", "formation_change", "codex_query",
    "npc_dialogue", "item_use", "exploration_action", "tower_strategy",
]

DatasetTier = Literal["RAW", "QUARANTINED", "APPROVED"]


# ---------------------------------------------------------------------------
#  Event data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EventContext:
    tongue_vector: Tuple[float, ...]
    location: str
    companion_hp_ratio: float
    enemy_count: int
    formation_type: str
    bond_level: int
    evolution_stage: str
    status_effects: Tuple[str, ...] = ()


@dataclass(frozen=True)
class EventAction:
    action_id: str
    description: str
    source: Literal["player", "companion", "system"]
    confidence: float = 1.0


@dataclass(frozen=True)
class EventOutcome:
    success: bool
    numeric_result: float
    description: str
    tongue_shift: Optional[Tuple[float, ...]] = None
    safety_score: float = 1.0


@dataclass(frozen=True)
class GameEvent:
    event_id: str
    session_id: str
    player_id: str
    companion_id: str
    event_type: GameEventType
    timestamp: float
    context: EventContext
    action: EventAction
    outcome: EventOutcome


# ---------------------------------------------------------------------------
#  Dataset Record
# ---------------------------------------------------------------------------


@dataclass
class DatasetRecord:
    record_id: str
    event: GameEvent
    tier: DatasetTier
    created_at: float
    promoted_at: Optional[float] = None
    quarantine_reason: Optional[str] = None
    review_notes: Optional[str] = None


# ---------------------------------------------------------------------------
#  SFT Pair
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SFTPair:
    pair_id: str
    source_record_id: str
    companion_id: str
    instruction: str
    response: str
    category: str
    quality_score: float
    timestamp: float


# ---------------------------------------------------------------------------
#  HF Batch + Fine-Tune Job
# ---------------------------------------------------------------------------


@dataclass
class HFBatch:
    batch_id: str
    companion_id: str
    pairs: List[SFTPair]
    dataset_repo: str
    pushed_at: Optional[float] = None
    status: Literal["pending", "pushed", "failed"] = "pending"


@dataclass
class FineTuneJob:
    job_id: str
    companion_id: str
    dataset_repo: str
    model_repo: str
    batch_ids: List[str]
    total_pairs: int
    started_at: float
    completed_at: Optional[float] = None
    status: Literal["queued", "running", "completed", "failed"] = "queued"
    checkpoint_hash: Optional[str] = None


# ---------------------------------------------------------------------------
#  Safety Thresholds
# ---------------------------------------------------------------------------

AUTO_APPROVE_THRESHOLD = 0.8
QUARANTINE_THRESHOLD = 0.4
MIN_QUALITY_SCORE = 0.5
FINE_TUNE_THRESHOLD = 100


# ---------------------------------------------------------------------------
#  Training Pipeline
# ---------------------------------------------------------------------------


class TrainingPipeline:
    """Manages the full game-event → SFT → HuggingFace pipeline for one companion."""

    def __init__(
        self,
        companion_id: str,
        player_id: str,
        dataset_repo: str = "",
        model_repo: str = "",
    ) -> None:
        self._companion_id = companion_id
        self._player_id = player_id
        self._dataset_repo = dataset_repo or f"scbe-companion-{companion_id}"
        self._model_repo = model_repo or f"scbe-model-{companion_id}"
        self._records: List[DatasetRecord] = []
        self._pairs: List[SFTPair] = []
        self._batches: List[HFBatch] = []
        self._jobs: List[FineTuneJob] = []

    @property
    def companion_id(self) -> str:
        return self._companion_id

    @property
    def dataset_repo(self) -> str:
        return self._dataset_repo

    @property
    def model_repo(self) -> str:
        return self._model_repo

    @property
    def total_records(self) -> int:
        return len(self._records)

    @property
    def total_pairs(self) -> int:
        return len(self._pairs)

    # ----- Tier 1: Ingest -----

    def ingest_event(self, event: GameEvent) -> str:
        record_id = f"rec_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        record = DatasetRecord(
            record_id=record_id,
            event=event,
            tier="RAW",
            created_at=time.time(),
        )
        self._records.append(record)
        return record_id

    def ingest_session(
        self, events: List[GameEvent]
    ) -> Dict[str, int]:
        approved = quarantined = rejected = 0
        for event in events:
            record_id = self.ingest_event(event)
            result = self.classify_record(record_id)
            if result == "APPROVED":
                approved += 1
            elif result == "QUARANTINED":
                quarantined += 1
            else:
                rejected += 1
        return {"approved": approved, "quarantined": quarantined, "rejected": rejected}

    # ----- Tier 2: Classify -----

    def classify_record(self, record_id: str) -> str:
        record = next((r for r in self._records if r.record_id == record_id), None)
        if record is None or record.tier != "RAW":
            return "REJECTED"

        safety_score = record.event.outcome.safety_score

        if safety_score >= AUTO_APPROVE_THRESHOLD:
            record.tier = "APPROVED"
            record.promoted_at = time.time()
            return "APPROVED"
        elif safety_score >= QUARANTINE_THRESHOLD:
            record.tier = "QUARANTINED"
            record.quarantine_reason = (
                f"Safety score {safety_score:.2f} below auto-approve threshold"
            )
            return "QUARANTINED"
        else:
            self._records = [r for r in self._records if r.record_id != record_id]
            return "REJECTED"

    def approve_record(self, record_id: str, review_notes: str = "") -> bool:
        record = next((r for r in self._records if r.record_id == record_id), None)
        if record is None or record.tier != "QUARANTINED":
            return False
        record.tier = "APPROVED"
        record.promoted_at = time.time()
        record.review_notes = review_notes
        return True

    def reject_record(self, record_id: str, reason: str = "") -> bool:
        record = next((r for r in self._records if r.record_id == record_id), None)
        if record is None or record.tier != "QUARANTINED":
            return False
        self._records = [r for r in self._records if r.record_id != record_id]
        return True

    # ----- Tier 3: SFT Generation -----

    def generate_sft_pairs(self) -> int:
        approved = [r for r in self._records if r.tier == "APPROVED"]
        existing_ids = {p.source_record_id for p in self._pairs}
        count = 0
        for record in approved:
            if record.record_id in existing_ids:
                continue
            pair = self._event_to_sft_pair(record)
            if pair is not None and pair.quality_score >= MIN_QUALITY_SCORE:
                self._pairs.append(pair)
                count += 1
        return count

    def _event_to_sft_pair(self, record: DatasetRecord) -> Optional[SFTPair]:
        event = record.event
        ctx = event.context
        action = event.action
        outcome = event.outcome

        parts = [
            f"[{event.event_type.upper()}]",
            f"Location: {ctx.location}",
            f"Companion HP: {ctx.companion_hp_ratio * 100:.0f}%",
            f"Bond Level: {ctx.bond_level}",
            f"Evolution: {ctx.evolution_stage}",
            f"Formation: {ctx.formation_type}",
            f"Enemies: {ctx.enemy_count}",
        ]
        if ctx.status_effects:
            parts.append(f"Status: {', '.join(ctx.status_effects)}")
        tv = ", ".join(f"{v:.2f}" for v in ctx.tongue_vector)
        parts.append(f"Tongue: [{tv}]")
        parts.append("")
        parts.append("What action should the companion take?")
        instruction = "\n".join(parts)

        sign = "+" if outcome.numeric_result > 0 else ""
        response = "\n".join([
            f"Action: {action.description}",
            f"Result: {outcome.description}",
            "Outcome: SUCCESS" if outcome.success else "Outcome: FAILURE",
            f"Effect: {sign}{outcome.numeric_result}",
        ])

        success_factor = 1.0 if outcome.success else 0.3
        quality_score = min(
            1.0,
            outcome.safety_score * success_factor * max(action.confidence, 0.5),
        )

        return SFTPair(
            pair_id=f"sft_{int(time.time())}_{uuid.uuid4().hex[:6]}",
            source_record_id=record.record_id,
            companion_id=self._companion_id,
            instruction=instruction,
            response=response,
            category=event.event_type,
            quality_score=quality_score,
            timestamp=time.time(),
        )

    # ----- HuggingFace Push -----

    def create_batch(self) -> Optional[HFBatch]:
        batched_ids = set()
        for b in self._batches:
            for p in b.pairs:
                batched_ids.add(p.pair_id)

        unpushed = [p for p in self._pairs if p.pair_id not in batched_ids]
        if not unpushed:
            return None

        batch = HFBatch(
            batch_id=f"batch_{int(time.time())}_{uuid.uuid4().hex[:6]}",
            companion_id=self._companion_id,
            pairs=list(unpushed),
            dataset_repo=self._dataset_repo,
        )
        self._batches.append(batch)
        return batch

    def mark_batch_pushed(self, batch_id: str) -> bool:
        batch = next((b for b in self._batches if b.batch_id == batch_id), None)
        if batch is None or batch.status != "pending":
            return False
        batch.status = "pushed"
        batch.pushed_at = time.time()
        return True

    def batch_to_jsonl(self, batch_id: str) -> Optional[str]:
        batch = next((b for b in self._batches if b.batch_id == batch_id), None)
        if batch is None:
            return None
        lines = []
        for pair in batch.pairs:
            lines.append(json.dumps({
                "id": pair.pair_id,
                "category": pair.category,
                "instruction": pair.instruction,
                "response": pair.response,
                "metadata": {
                    "source": "spiral_forge_gameplay",
                    "version": "1.0.0",
                    "companion_id": pair.companion_id,
                    "quality_score": pair.quality_score,
                    "timestamp": pair.timestamp,
                },
            }))
        return "\n".join(lines)

    # ----- Fine-Tune Jobs -----

    def can_trigger_fine_tune(self) -> bool:
        pushed_pairs = sum(
            len(b.pairs) for b in self._batches if b.status == "pushed"
        )
        return pushed_pairs >= FINE_TUNE_THRESHOLD

    def create_fine_tune_job(self) -> Optional[FineTuneJob]:
        if not self.can_trigger_fine_tune():
            return None
        pushed = [b for b in self._batches if b.status == "pushed"]
        total = sum(len(b.pairs) for b in pushed)
        job = FineTuneJob(
            job_id=f"ft_{int(time.time())}_{uuid.uuid4().hex[:6]}",
            companion_id=self._companion_id,
            dataset_repo=self._dataset_repo,
            model_repo=self._model_repo,
            batch_ids=[b.batch_id for b in pushed],
            total_pairs=total,
            started_at=time.time(),
        )
        self._jobs.append(job)
        return job

    def complete_fine_tune_job(self, job_id: str, checkpoint_hash: str) -> bool:
        job = next((j for j in self._jobs if j.job_id == job_id), None)
        if job is None or job.status == "completed":
            return False
        job.status = "completed"
        job.completed_at = time.time()
        job.checkpoint_hash = checkpoint_hash
        return True

    # ----- Queries -----

    def get_records_by_tier(self, tier: DatasetTier) -> List[DatasetRecord]:
        return [r for r in self._records if r.tier == tier]

    def get_pairs(self) -> List[SFTPair]:
        return list(self._pairs)

    def get_batches(self) -> List[HFBatch]:
        return list(self._batches)

    def get_jobs(self) -> List[FineTuneJob]:
        return list(self._jobs)

    def summary(self) -> Dict:
        completed = [j for j in self._jobs if j.status == "completed"]
        completed.sort(key=lambda j: j.completed_at or 0, reverse=True)
        return {
            "companion_id": self._companion_id,
            "raw_count": sum(1 for r in self._records if r.tier == "RAW"),
            "quarantined_count": sum(1 for r in self._records if r.tier == "QUARANTINED"),
            "approved_count": sum(1 for r in self._records if r.tier == "APPROVED"),
            "sft_pair_count": len(self._pairs),
            "batches_pushed": sum(1 for b in self._batches if b.status == "pushed"),
            "batches_pending": sum(1 for b in self._batches if b.status == "pending"),
            "fine_tune_jobs": len(self._jobs),
            "fine_tune_completed": len(completed),
            "latest_checkpoint": completed[0].checkpoint_hash if completed else None,
            "dataset_repo": self._dataset_repo,
            "model_repo": self._model_repo,
        }


# ---------------------------------------------------------------------------
#  Helper: create game event
# ---------------------------------------------------------------------------


def create_game_event(
    session_id: str,
    player_id: str,
    companion_id: str,
    event_type: GameEventType,
    context: EventContext,
    action: EventAction,
    outcome: EventOutcome,
) -> GameEvent:
    return GameEvent(
        event_id=f"evt_{int(time.time())}_{uuid.uuid4().hex[:6]}",
        session_id=session_id,
        player_id=player_id,
        companion_id=companion_id,
        event_type=event_type,
        timestamp=time.time(),
        context=context,
        action=action,
        outcome=outcome,
    )
