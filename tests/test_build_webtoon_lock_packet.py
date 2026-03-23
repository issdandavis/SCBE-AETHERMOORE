from __future__ import annotations

import json
from pathlib import Path

from scripts.build_webtoon_lock_packet import build_lock_packet, find_panel, load_packet


def test_build_lock_packet_keeps_marcus_identity_lock(tmp_path: Path) -> None:
    packet_data = {
        "chapter_id": "ch01",
        "episode_id": "ep01",
        "default_negative_prompt": "speech bubbles, text overlays",
        "character_anchors": {
            "marcus": "Asian-American man early 30s, short dark messy hair, tired eyes, lean desk-worker build, rumpled dress shirt and hoodie.",
        },
        "character_negative_anchors": {
            "marcus": "white man, caucasian, blond hair, blue eyes, superhero jawline",
        },
        "style_bible": {"visual_language": "Korean webtoon / manhwa"},
        "panels": [
            {
                "id": "ch01-v4-p11",
                "shot_label": "CH01-011",
                "beat": "Found you",
                "scene_prompt": "Close on Marcus highlighting the impossible sequence with one hand, mouth barely moving around the words Found you, green light cutting his features into quiet certainty.",
                "environment": "earth_office",
                "characters": ["marcus"],
                "style_metadata": {"camera_angle": "tight three-quarter close-up"},
                "w": 720,
                "h": 1280,
            }
        ],
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet_data), encoding="utf-8")

    packet = load_packet(packet_path)
    panel = find_panel(packet, "ch01-v4-p11")
    lock_packet = build_lock_packet(packet, panel, lock_name="marcus-face-lock", lock_type="character")

    assert lock_packet["panel_id"] == "ch01-v4-p11"
    assert "Character lock: marcus: Asian-American man early 30s" in lock_packet["prompt"]
    assert "light stubble" in lock_packet["prompt"]
    assert "white man" in lock_packet["negative_prompt"]
    assert "teenager" in lock_packet["negative_prompt"]
    assert any("Asian-American" in item for item in lock_packet["acceptance_criteria"])
    assert any("Office proportions" in item for item in lock_packet["acceptance_criteria"])
