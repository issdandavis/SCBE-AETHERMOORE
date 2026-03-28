from __future__ import annotations

import json
from pathlib import Path

import scripts.build_manhwa_edit_packet as edit_packet


def write_packet(path: Path) -> None:
    packet = {
        "chapter_id": "ch-edit",
        "title": "Edit Packet Test",
        "generation_router_profile": {
            "hero_backend": "imagen-ultra",
            "batch_backend": "imagen",
            "fallback_backend": "hf",
            "output_root": str(path.parent / "rendered"),
        },
        "style_system": {"global_tags": ["story-first panel design"]},
        "style_bible": {"visual_language": "Korean webtoon / manhwa"},
        "panels": [
            {
                "id": "ch-edit-p01",
                "sequence_id": "ch-edit-seq01",
                "sequence_index": 1,
                "sequence_title": "Hero Arrival",
                "render_tier": "hero",
                "scene_prompt": "Marcus in white light looking over his shoulder",
                "scene_summary": "Marcus is hit by the white-out.",
                "story_job": "Hold the rupture as a human shock beat.",
                "continuity": "Marcus keeps his hoodie, dark hair, and office-worker exhaustion.",
                "environment": "white_void",
                "arc_lock": "protocol_transmission",
                "characters": ["marcus"],
                "w": 1280,
                "h": 720,
            }
        ],
    }
    path.write_text(json.dumps(packet), encoding="utf-8")


def write_manifest(path: Path, image_path: Path) -> None:
    manifest = {
        "packet": "packet.json",
        "chapter_id": "ch-edit",
        "dry_run": True,
        "panels": [
            {
                "id": "ch-edit-p01",
                "backend": "imagen-ultra",
                "output": str(image_path),
                "prompt": "Marcus in white light looking over his shoulder",
                "scene_summary": "Marcus is hit by the white-out.",
                "story_job": "Hold the rupture as a human shock beat.",
                "continuity": "Marcus keeps his hoodie, dark hair, and office-worker exhaustion.",
                "environment": "white_void",
                "arc_lock": "protocol_transmission",
            }
        ],
    }
    path.write_text(json.dumps(manifest), encoding="utf-8")


def test_build_edit_packet_writes_outputs_and_uses_manifest(tmp_path: Path) -> None:
    packet_path = tmp_path / "packet.json"
    manifest_path = tmp_path / "manifest.json"
    image_path = tmp_path / "rendered" / "hero.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"fakepng")

    write_packet(packet_path)
    write_manifest(manifest_path, image_path)

    json_path = edit_packet.build_edit_packet(
        packet_path=str(packet_path),
        manifest_path=str(manifest_path),
        only_ids=[],
        limit=None,
        edit_goal="Fine edit anatomy, lighting, and continuity without changing the story beat.",
        app="auto",
        output_dir=str(tmp_path / "edit-packet"),
    )

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown_path = json_path.with_name("edit_packet.md")
    html_path = json_path.with_name("contact_sheet.html")

    assert markdown_path.exists()
    assert html_path.exists()
    assert payload["recommended_default_app"] == "photoshop"
    assert payload["panels"][0]["recommended_app"] == "photoshop"
    assert payload["panels"][0]["image_path"] == str(image_path)
    assert any("Photoshop" in note for note in payload["panels"][0]["app_notes"])
    assert any("Preserve Marcus" in note for note in payload["panels"][0]["preserve"])
    assert any("Continuity:" in note for note in payload["panels"][0]["preserve"])


def test_build_edit_packet_auto_switches_to_canva_for_layout_goal(
    tmp_path: Path,
) -> None:
    packet_path = tmp_path / "packet.json"
    write_packet(packet_path)

    json_path = edit_packet.build_edit_packet(
        packet_path=str(packet_path),
        manifest_path=None,
        only_ids=[],
        limit=1,
        edit_goal="Create thumbnail text layout and promo poster treatment.",
        app="auto",
        output_dir=str(tmp_path / "edit-packet"),
    )

    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert payload["recommended_default_app"] == "canva"
    assert payload["panels"][0]["recommended_app"] == "canva"
    assert any("Canva" in note for note in payload["panels"][0]["app_notes"])
