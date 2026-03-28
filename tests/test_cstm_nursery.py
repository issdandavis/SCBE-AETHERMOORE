from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# cstm_nursery lives in root training/ (not a package), add to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))
try:
    import cstm_nursery
except ImportError:
    cstm_nursery = None

pytestmark = pytest.mark.skipif(
    cstm_nursery is None, reason="cstm_nursery module not importable"
)


SEED_STORY = Path("training-data/hf-digimon-egg/cstm_seed_story.json")


def test_load_story_pack_reads_seed_story() -> None:
    story = cstm_nursery.load_story_pack(SEED_STORY)

    assert story.story_id == "marcus-portal-nursery-v1"
    assert len(story.parents) == 2
    assert story.parents[0].name == "Marcus Chen"
    assert len(story.chapters) == 3
    assert "portal_drill_intro" in story.scenes


def test_run_playthrough_unlocks_portal_and_return_chapters() -> None:
    story = cstm_nursery.load_story_pack(SEED_STORY)
    agent = cstm_nursery.hatch_agent(
        story,
        cohort_index=0,
        location="north-bend-wa",
        device="pollypad-sim",
        timestamp=datetime(2026, 3, 19, 9, 0, tzinfo=timezone.utc),
    )

    playthrough = cstm_nursery.run_playthrough(
        story,
        agent,
        max_steps=12,
        started_at=datetime(2026, 3, 19, 9, 0, tzinfo=timezone.utc),
    )

    chapter_ids = [step.chapter_id for step in playthrough.steps]
    assert chapter_ids == [
        "hatchery",
        "hatchery",
        "portal_drill",
        "portal_drill",
        "safe_return",
    ]
    assert "return_loop_ready" in playthrough.final_flags
    assert playthrough.final_outcome in {"ALLOW", "QUARANTINE", "DENY"}

    episode_rows = cstm_nursery.build_episode_records(playthrough)
    sft_rows = cstm_nursery.build_sft_records(playthrough)
    dpo_rows = cstm_nursery.build_dpo_records(playthrough)

    assert len(episode_rows) == len(playthrough.steps)
    assert len(sft_rows) == len(playthrough.steps)
    assert len(dpo_rows) == len(playthrough.steps)
    assert dpo_rows[0]["chosen"] != dpo_rows[0]["rejected"]


def test_main_writes_episode_sft_and_dpo_artifacts(tmp_path: Path, capsys) -> None:
    exit_code = cstm_nursery.main(
        [
            "--story",
            str(SEED_STORY),
            "--out-dir",
            str(tmp_path),
            "--cohort-size",
            "2",
            "--timestamp",
            "2026-03-19T09:00:00Z",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["cohort_size"] == 2
    assert payload["episode_count"] > 0
    assert Path(payload["artifacts"]["episodes"]).exists()
    assert Path(payload["artifacts"]["sft"]).exists()
    assert Path(payload["artifacts"]["dpo"]).exists()
    assert Path(payload["artifacts"]["summary"]).exists()
