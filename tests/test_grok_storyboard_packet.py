from __future__ import annotations

import json
from pathlib import Path

from scripts.build_ch01_prompts_v4 import build_packet
import scripts.render_grok_storyboard_packet as router


def write_packet(path: Path) -> None:
    packet = {
        "chapter_id": "chx",
        "title": "Test Chapter",
        "default_negative_prompt": "speech bubbles, text overlays",
        "character_anchors": {
            "marcus": "Asian-American man early 30s, short dark messy hair, tired eyes.",
            "polly_human": "young woman with black feather-hair, folded wings, obsidian mineral eyes.",
        },
        "character_negative_anchors": {
            "marcus": "white man, caucasian, blond hair",
            "polly_human": "white fantasy princess, pin-up posing",
        },
        "generation_router_profile": {
            "hero_backend": "imagen-ultra",
            "batch_backend": "imagen",
            "fallback_backend": "hf",
            "output_root": str(path.parent / "out"),
        },
        "style_system": {"global_tags": ["story-first panel design"]},
        "style_bible": {"visual_language": "Korean webtoon / manhwa"},
        "panels": [
            {
                "id": "chx-p01",
                "render_tier": "hero",
                "prompt": "STALE PROMPT SHOULD NOT WIN",
                "scene_prompt": "hero panel of Marcus in white light",
                "environment": "white_void",
                "arc_lock": "protocol_transmission",
                "cornerstone_style": "ethereal_divine",
                "mood": "awe",
                "characters": ["marcus"],
                "w": 1280,
                "h": 720,
            },
            {
                "id": "chx-p02",
                "render_tier": "batch",
                "scene_prompt": "batch panel of Marcus walking the corridor",
                "environment": "crystal_corridor",
                "arc_lock": "archive_grounded_magic",
                "cornerstone_style": "standard_dialogue",
                "mood": "awe",
                "characters": ["marcus", "polly_human"],
                "w": 720,
                "h": 1280,
                "negative_prompt": "low detail, inconsistent character design",
            },
        ],
    }
    path.write_text(json.dumps(packet), encoding="utf-8")


def test_build_ch01_v4_packet_has_expected_density() -> None:
    packet = build_packet()

    assert packet["panel_count"] == 56
    assert packet["target_panel_min"] == 50
    assert packet["generation_router_profile"]["hero_backend"] == "imagen-ultra"
    assert "speech bubbles" in packet["default_negative_prompt"]
    assert len(packet["beat_sequences"]) == 14
    assert packet["beat_expansion_schema"]["approach"] == "B with disciplined selective expansion"
    assert any(panel["render_tier"] == "hero" for panel in packet["panels"])
    assert packet["panels"][0]["sequence_id"] == "ch01-seq01"
    assert packet["panels"][0]["beat_id"] == "ch01-seq01-beat01"
    assert packet["panels"][0]["sequence_role"] == "setup"
    assert "Marcus feels human" in packet["panels"][0]["expansion_reason"]
    assert packet["panels"][0]["shot_label"] == "CH01-001"
    assert packet["panels"][0]["review_order"] == 1
    assert packet["panels"][0]["style_metadata"]["camera_angle"] == "extreme macro desk-level insert"
    assert packet["generation_profile"]["trigger_phrases"] == ["sixtongues_ch01_pilot"]
    assert packet["generation_profile"]["style_adapter"]["trigger_word"] == "sixtongues_ch01_pilot"
    assert packet["character_anchors"]["patrol_creature"].startswith("many-legged patrol creature")
    assert next(panel for panel in packet["panels"] if panel["id"] == "ch01-v4-p51")["characters"] == ["patrol_creature"]
    assert packet["panels"][-1]["sequence_id"] == "ch01-seq14"


def test_build_render_jobs_routes_hero_and_batch_panels(tmp_path: Path, monkeypatch) -> None:
    packet_path = tmp_path / "packet.json"
    write_packet(packet_path)

    monkeypatch.setattr(
        router,
        "check_backends",
        lambda: {"imagen": True, "imagen-ultra": True, "hf": True, "zimage": False},
    )
    monkeypatch.setattr(router, "pick_best_backend", lambda preference=None: "imagen")

    _, jobs = router.build_render_jobs(packet_path, dry_run=True)

    assert jobs[0]["backend"] == "imagen-ultra"
    assert jobs[0]["aspect"] == "16:9"
    assert jobs[0]["negative_prompt"] == "speech bubbles, text overlays, white man, caucasian, blond hair"
    assert jobs[1]["backend"] == "imagen"
    assert jobs[1]["aspect"] == "9:16"
    assert jobs[1]["negative_prompt"] == "speech bubbles, text overlays, white man, caucasian, blond hair, white fantasy princess, pin-up posing, low detail, inconsistent character design"
    assert "hero panel of Marcus in white light" in jobs[0]["prompt"]
    assert "Character lock: marcus: Asian-American man early 30s" in jobs[0]["prompt"]
    assert "STALE PROMPT SHOULD NOT WIN" not in jobs[0]["prompt"]


def test_run_packet_dry_run_writes_manifest(tmp_path: Path, monkeypatch) -> None:
    packet_path = tmp_path / "packet.json"
    write_packet(packet_path)

    monkeypatch.setattr(
        router,
        "check_backends",
        lambda: {"imagen": True, "imagen-ultra": True, "hf": True, "zimage": False},
    )
    monkeypatch.setattr(router, "pick_best_backend", lambda preference=None: "imagen")

    manifest_path = router.run_packet(packet_path, dry_run=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["dry_run"] is True
    assert len(manifest["panels"]) == 2
    assert manifest["panels"][0]["ok"] is True
    assert manifest["panels"][0]["backend"] == "imagen-ultra"


def test_run_packet_retries_with_fallback_on_quota(tmp_path: Path, monkeypatch) -> None:
    packet_path = tmp_path / "packet.json"
    write_packet(packet_path)
    calls: list[str] = []

    monkeypatch.setattr(
        router,
        "check_backends",
        lambda: {"imagen": True, "imagen-ultra": True, "hf": True, "zimage": False},
    )
    monkeypatch.setattr(router, "pick_best_backend", lambda preference=None: "imagen")

    def fake_generate(*, backend, prompt, output, aspect, reference, negative_prompt, width, height):
        calls.append(backend)
        if backend == "imagen-ultra":
            raise RuntimeError("429 RESOURCE_EXHAUSTED quota")
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_bytes(b"ok")
        return output

    monkeypatch.setattr(router, "generate", fake_generate)

    manifest_path = router.run_packet(packet_path, only_ids=["chx-p01"], dry_run=False)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    panel = manifest["panels"][0]

    assert calls == ["imagen-ultra", "hf"]
    assert panel["ok"] is True
    assert panel["backend"] == "hf"
    assert panel["fallback_from"] == "imagen-ultra"
