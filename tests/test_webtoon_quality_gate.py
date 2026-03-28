from __future__ import annotations

import json
from pathlib import Path

from scripts.assemble_manhwa_strip import require_approved_packet
from scripts.webtoon_quality_gate import govern_packet, lookup_episode_metadata


def test_govern_packet_auto_fixes_sparse_packet() -> None:
    packet = {
        "chapter_id": "ch01",
        "panels": [
            {
                "prompt": "Marcus studies terminal logs in the office before reality whites out.",
            }
        ],
    }

    governed, report = govern_packet(
        packet,
        packet_path=Path("artifacts/webtoon/panel_prompts/ch01_prompts.json"),
        auto_fix=True,
        rewrite_prompts=True,
    )

    assert report["approved"] is True
    assert governed["episode_id"] == "ep01"
    assert governed["source_markdown"] == "content/book/reader-edition/ch01.md"
    assert governed["key_script"] == "artifacts/webtoon/ch1_panel_script.md"
    assert (
        governed["generation_profile"]["model_id"] == "black-forest-labs/FLUX.1-schnell"
    )
    assert governed["generation_profile"]["default_steps"] == 4
    assert governed["panels"][0]["environment"] == "earth_office"
    assert governed["panels"][0]["characters"] == ["marcus"]
    assert governed["panels"][0]["compiled_prompt"].startswith("manhwa webtoon panel")


def test_govern_packet_requires_visual_memory_packet_for_reference_chapter() -> None:
    packet = {
        "chapter_id": "ch01",
        "reference_chapter": True,
        "panels": [
            {
                "scene_prompt": "Marcus studies terminal logs in the office.",
            }
        ],
    }

    _, report = govern_packet(
        packet,
        packet_path=Path("artifacts/webtoon/panel_prompts/ch01_prompts.json"),
        auto_fix=True,
        rewrite_prompts=True,
    )

    assert report["approved"] is False
    assert "reference chapter missing readable visual_memory_packet" in report["errors"]


def test_govern_packet_rejects_unknown_character() -> None:
    packet = {
        "chapter_id": "ch01",
        "panels": [
            {
                "scene_prompt": "A stranger studies Marcus from the office doorway.",
                "environment": "earth_office",
                "characters": ["mystery_guest"],
                "arc_lock": "earth_protocol_noir",
                "cornerstone_style": "standard_dialogue",
                "mood": "tension",
                "w": 720,
                "h": 1280,
            }
        ],
    }

    _, report = govern_packet(
        packet,
        packet_path=Path("artifacts/webtoon/panel_prompts/ch01_prompts.json"),
        auto_fix=True,
        rewrite_prompts=True,
    )

    assert report["approved"] is False
    assert "unknown character 'mystery_guest'" in " ".join(report["errors"])


def test_require_approved_packet_accepts_matching_report(tmp_path: Path) -> None:
    report_path = tmp_path / "ch01_quality_report.json"
    report_path.write_text(
        json.dumps(
            {
                "chapter_id": "ch01",
                "approved": True,
                "panel_count": 3,
            }
        ),
        encoding="utf-8",
    )

    report = require_approved_packet(report_path, "ch01", panel_count=3)

    assert report["approved"] is True


def test_require_approved_packet_rejects_missing_or_bad_reports(tmp_path: Path) -> None:
    missing_report = tmp_path / "missing.json"
    try:
        require_approved_packet(missing_report, "ch01")
    except FileNotFoundError as exc:
        assert "Quality report not found" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError for missing report")

    rejected_report = tmp_path / "rejected.json"
    rejected_report.write_text(
        json.dumps(
            {
                "chapter_id": "ch01",
                "approved": False,
                "panel_count": 2,
            }
        ),
        encoding="utf-8",
    )

    try:
        require_approved_packet(rejected_report, "ch01", panel_count=2)
    except ValueError as exc:
        assert "not approved" in str(exc)
    else:
        raise AssertionError("expected ValueError for unapproved report")


def test_lookup_episode_metadata_does_not_cross_into_kyle_story_lane() -> None:
    assert lookup_episode_metadata(chapter_id="ch28") is None
    assert (
        lookup_episode_metadata(source_markdown="content/book/kyle-edition/ch28.md")
        is None
    )


def test_govern_packet_auto_fixes_supported_environment_arc_lock() -> None:
    packet = {
        "chapter_id": "ch01",
        "panels": [
            {
                "scene_prompt": "Bram walks maintenance shafts lit by conduit glow.",
                "environment": "maintenance_shafts",
                "characters": ["bram"],
                "w": 720,
                "h": 1280,
            }
        ],
    }

    governed, report = govern_packet(
        packet,
        packet_path=Path("artifacts/webtoon/panel_prompts/ch01_prompts.json"),
        auto_fix=True,
        rewrite_prompts=True,
    )

    assert report["approved"] is True
    assert governed["panels"][0]["arc_lock"] == "maintenance_underworks"


def test_govern_packet_supports_patrol_creature_and_detail_camera_defaults() -> None:
    packet = {
        "chapter_id": "ch01",
        "panels": [
            {
                "type": "DETAIL",
                "scene_prompt": "A many-legged patrol creature crosses a crystal bridge with quiet purpose.",
                "environment": "aethermoor_exterior",
                "characters": ["patrol_creature"],
                "arc_lock": "aethermoor_world_reveal",
                "cornerstone_style": "standard_dialogue",
                "mood": "awe",
                "w": 720,
                "h": 1280,
            }
        ],
    }

    governed, report = govern_packet(
        packet,
        packet_path=Path("artifacts/webtoon/panel_prompts/ch01_prompts.json"),
        auto_fix=True,
        rewrite_prompts=True,
    )

    assert report["approved"] is True
    assert "patrol_creature" in governed["character_anchors"]
    assert governed["panels"][0]["style_metadata"]["camera_angle"] == "insert close-up"
