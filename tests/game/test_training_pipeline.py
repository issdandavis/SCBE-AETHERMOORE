"""
Tests for Training Pipeline — Python reference.

Covers: event ingestion, 3-tier classification, SFT generation,
batching, JSONL formatting, fine-tune job tracking.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from symphonic_cipher.scbe_aethermoore.game.training_pipeline import (
    MIN_QUALITY_SCORE,
    FINE_TUNE_THRESHOLD,
    TrainingPipeline,
    EventContext,
    EventAction,
    EventOutcome,
    GameEvent,
    create_game_event,
)


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------


def _ctx(**kw) -> EventContext:
    defaults = dict(
        tongue_vector=(0.2, 0.2, 0.1, 0.3, 0.1, 0.1),
        location="dungeon-floor-3",
        companion_hp_ratio=0.8,
        enemy_count=2,
        formation_type="diamond",
        bond_level=3,
        evolution_stage="juvenile",
    )
    defaults.update(kw)
    return EventContext(**defaults)


def _act(**kw) -> EventAction:
    defaults = dict(
        action_id="act_test",
        description="Fire Breath attack on slime",
        source="companion",
        confidence=0.9,
    )
    defaults.update(kw)
    return EventAction(**defaults)


def _out(safety_score: float = 0.95, success: bool = True, **kw) -> EventOutcome:
    defaults = dict(
        success=success,
        numeric_result=45.0,
        description="Dealt 45 fire damage",
        safety_score=safety_score,
    )
    defaults.update(kw)
    return EventOutcome(**defaults)


def _event(safety: float = 0.95, success: bool = True) -> GameEvent:
    return create_game_event(
        "session-1", "player-1", "comp-1", "combat_action",
        _ctx(), _act(), _out(safety, success),
    )


def _pipeline() -> TrainingPipeline:
    return TrainingPipeline("comp-1", "player-1", "test-dataset", "test-model")


# ---------------------------------------------------------------------------
#  Tests
# ---------------------------------------------------------------------------


class TestIngestion:
    def test_ingest_single(self):
        p = _pipeline()
        rid = p.ingest_event(_event())
        assert rid.startswith("rec_")
        assert p.total_records == 1
        assert len(p.get_records_by_tier("RAW")) == 1

    def test_ingest_session(self):
        p = _pipeline()
        result = p.ingest_session([
            _event(0.95),  # approved
            _event(0.6),   # quarantined
            _event(0.1),   # rejected
        ])
        assert result["approved"] == 1
        assert result["quarantined"] == 1
        assert result["rejected"] == 1
        assert p.total_records == 2


class TestClassification:
    def test_auto_approve(self):
        p = _pipeline()
        rid = p.ingest_event(_event(0.95))
        assert p.classify_record(rid) == "APPROVED"

    def test_quarantine(self):
        p = _pipeline()
        rid = p.ingest_event(_event(0.6))
        assert p.classify_record(rid) == "QUARANTINED"

    def test_reject(self):
        p = _pipeline()
        rid = p.ingest_event(_event(0.1))
        assert p.classify_record(rid) == "REJECTED"
        assert p.total_records == 0

    def test_manual_approve(self):
        p = _pipeline()
        rid = p.ingest_event(_event(0.6))
        p.classify_record(rid)
        assert p.approve_record(rid, "OK") is True
        assert len(p.get_records_by_tier("APPROVED")) == 1

    def test_manual_reject(self):
        p = _pipeline()
        rid = p.ingest_event(_event(0.6))
        p.classify_record(rid)
        assert p.reject_record(rid) is True
        assert p.total_records == 0

    def test_cannot_approve_non_quarantined(self):
        p = _pipeline()
        rid = p.ingest_event(_event(0.95))
        p.classify_record(rid)
        assert p.approve_record(rid) is False


class TestSFTGeneration:
    def test_generate_pairs(self):
        p = _pipeline()
        p.ingest_session([_event(0.95), _event(0.9)])
        count = p.generate_sft_pairs()
        assert count == 2
        assert p.total_pairs == 2

    def test_pair_content(self):
        p = _pipeline()
        p.ingest_session([_event(0.95)])
        p.generate_sft_pairs()
        pairs = p.get_pairs()
        assert len(pairs) == 1
        assert "COMBAT_ACTION" in pairs[0].instruction
        assert "Fire Breath" in pairs[0].response

    def test_no_duplicates(self):
        p = _pipeline()
        p.ingest_session([_event(0.95)])
        p.generate_sft_pairs()
        assert p.generate_sft_pairs() == 0

    def test_quality_scoring(self):
        """Success events produce higher quality SFT pairs."""
        p = _pipeline()
        p.ingest_session([_event(0.95, True)])
        p.generate_sft_pairs()
        pairs = p.get_pairs()
        assert len(pairs) == 1
        # quality = 0.95 * 1.0 * 0.9 = 0.855
        assert pairs[0].quality_score > MIN_QUALITY_SCORE
        assert "SUCCESS" in pairs[0].response


class TestBatching:
    def test_create_batch(self):
        p = _pipeline()
        p.ingest_session([_event(0.95)])
        p.generate_sft_pairs()
        batch = p.create_batch()
        assert batch is not None
        assert len(batch.pairs) == 1
        assert batch.status == "pending"

    def test_no_unpushed(self):
        p = _pipeline()
        assert p.create_batch() is None

    def test_mark_pushed(self):
        p = _pipeline()
        p.ingest_session([_event(0.95)])
        p.generate_sft_pairs()
        batch = p.create_batch()
        assert p.mark_batch_pushed(batch.batch_id) is True
        assert p.get_batches()[0].status == "pushed"

    def test_jsonl_format(self):
        p = _pipeline()
        p.ingest_session([_event(0.95)])
        p.generate_sft_pairs()
        batch = p.create_batch()
        jsonl = p.batch_to_jsonl(batch.batch_id)
        assert jsonl is not None
        parsed = json.loads(jsonl.split("\n")[0])
        assert parsed["id"].startswith("sft_")
        assert parsed["metadata"]["source"] == "spiral_forge_gameplay"


class TestFineTune:
    def _ready_pipeline(self, n: int = FINE_TUNE_THRESHOLD) -> TrainingPipeline:
        p = _pipeline()
        events = [_event(0.95) for _ in range(n)]
        p.ingest_session(events)
        p.generate_sft_pairs()
        batch = p.create_batch()
        p.mark_batch_pushed(batch.batch_id)
        return p

    def test_below_threshold(self):
        p = self._ready_pipeline(10)
        assert p.can_trigger_fine_tune() is False

    def test_at_threshold(self):
        p = self._ready_pipeline()
        assert p.can_trigger_fine_tune() is True
        job = p.create_fine_tune_job()
        assert job is not None
        assert job.status == "queued"
        assert job.total_pairs == FINE_TUNE_THRESHOLD

    def test_complete_job(self):
        p = self._ready_pipeline()
        job = p.create_fine_tune_job()
        assert p.complete_fine_tune_job(job.job_id, "ckpt_abc") is True
        assert p.get_jobs()[0].checkpoint_hash == "ckpt_abc"

    def test_no_double_complete(self):
        p = self._ready_pipeline()
        job = p.create_fine_tune_job()
        p.complete_fine_tune_job(job.job_id, "ckpt_1")
        assert p.complete_fine_tune_job(job.job_id, "ckpt_2") is False


class TestSummary:
    def test_complete_summary(self):
        p = _pipeline()
        p.ingest_session([_event(0.95), _event(0.6), _event(0.1)])
        p.generate_sft_pairs()
        s = p.summary()
        assert s["companion_id"] == "comp-1"
        assert s["approved_count"] == 1
        assert s["quarantined_count"] == 1
        assert s["dataset_repo"] == "test-dataset"

    def test_checkpoint_in_summary(self):
        p = _pipeline()
        events = [_event(0.95) for _ in range(FINE_TUNE_THRESHOLD)]
        p.ingest_session(events)
        p.generate_sft_pairs()
        batch = p.create_batch()
        p.mark_batch_pushed(batch.batch_id)
        job = p.create_fine_tune_job()
        p.complete_fine_tune_job(job.job_id, "ckpt_final")
        s = p.summary()
        assert s["latest_checkpoint"] == "ckpt_final"
