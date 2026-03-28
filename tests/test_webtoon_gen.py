from __future__ import annotations

import json
from pathlib import Path

from scripts.webtoon_gen import (
    LEGACY_STYLE_PREFIXES,
    compile_panel_prompt,
    infer_episode_panel_metadata,
    load_batch_payload,
)


def test_compile_panel_prompt_uses_style_metadata() -> None:
    panel = {
        "scene_prompt": "Marcus jolts back from the shelf as Polly squawks at him.",
        "environment": "crystal_library",
        "arc_lock": "archive_grounded_magic",
        "cornerstone_style": "chibi_sd",
        "mood": "comedy",
        "panel_flex": "comedic_expression",
        "style_tags": ["reaction punchline", "subtitle-safe lower margin"],
    }

    prompt = compile_panel_prompt(panel)

    assert "towering crystal bookshelves" in prompt
    assert "deliberate chibi exaggeration" in prompt
    assert "comic timing" in prompt
    assert "exaggerated reaction beat" in prompt
    assert "Marcus jolts back from the shelf as Polly squawks at him." in prompt


def test_compile_panel_prompt_includes_character_lock_and_story_context() -> None:
    packet = {
        "character_anchors": {
            "marcus": "Asian-American man early 30s, short dark messy hair, tired eyes, lean desk-worker build.",
        },
        "style_bible": {"visual_language": "Korean webtoon / manhwa"},
    }
    panel = {
        "scene_prompt": "Marcus rubs his face at the desk.",
        "continuity": "He has not gone home in days.",
        "story_job": "Humanize Marcus before the rupture.",
        "characters": ["marcus"],
        "style_metadata": {
            "camera_angle": "tight three-quarter close-up",
            "character_anchor": (
                "Asian-American man early 30s, short dark messy hair,"
                " tired eyes, lean desk-worker build."
            ),
        },
    }

    prompt = compile_panel_prompt(panel, packet)

    assert "tight three-quarter close-up" in prompt
    assert "Character lock: marcus: Asian-American man early 30s" in prompt
    assert "primary look: Asian-American man early 30s" in prompt
    assert "He has not gone home in days." not in prompt
    assert "Humanize Marcus before the rupture." not in prompt


def test_compile_panel_prompt_strips_legacy_prefix() -> None:
    panel = {
        "prompt": LEGACY_STYLE_PREFIXES[0]
        + "Wide reveal of Marcus alone in the office.",
        "cornerstone_style": "standard_dialogue",
    }

    prompt = compile_panel_prompt(panel)

    assert prompt.count("manhwa webtoon panel") == 1
    assert "Wide reveal of Marcus alone in the office." in prompt


def test_load_batch_payload_supports_chapter_prompt_packet(tmp_path: Path) -> None:
    payload = {
        "chapter_id": "ch99",
        "style_system": {"global_tags": ["story-first panel design"]},
        "panels": [
            {
                "id": "ch99-p01",
                "scene_prompt": "Marcus studies the crystal corridor.",
                "environment": "crystal_corridor",
                "w": 900,
                "h": 1600,
            }
        ],
    }
    batch_file = tmp_path / "ch99_prompts.json"
    batch_file.write_text(json.dumps(payload), encoding="utf-8")

    packet, panels = load_batch_payload(str(batch_file))

    assert packet is not None
    assert packet["chapter_id"] == "ch99"
    assert panels[0]["width"] == 900
    assert panels[0]["height"] == 1600
    assert Path(panels[0]["output"]).parent.name == "ch99"
    assert Path(panels[0]["output"]).name == "ch99-p01.png"


def test_infer_episode_panel_metadata_flags_infographic_panels() -> None:
    inferred = infer_episode_panel_metadata(
        "Protocol readout",
        "COHERENCE INDEX: 0.92 floating beside Polly as she studies Marcus.",
    )

    assert inferred["cornerstone_style"] == "infographic"
    assert inferred["mood"] == "exposition"
    assert inferred["panel_flex"] == "infographic_overlay"
