from __future__ import annotations

from scripts.gen_full_book_panels import create_panel_prompts_from_chapter
from scripts.webtoon_gen import compile_panel_prompt


def test_compile_panel_prompt_uses_structured_style_and_mood_metadata() -> None:
    packet = {
        "style_system": {"global_tags": ["deliberate style shifts only on key beats"]},
        "style_bible": {
            "visual_language": "stable worldbuilding with cinematic lighting",
        },
    }
    panel = {
        "scene_prompt": "Marcus catches the impossible auth line in a dead office.",
        "arc_lock": "earth_protocol_noir",
        "environment": "earth_office",
        "cornerstone_style": "standard_dialogue",
        "mood": "tension",
        "panel_flex": "painterly_impact",
    }

    prompt = compile_panel_prompt(panel, packet)

    assert prompt.startswith("manhwa webtoon panel")
    assert "story-first composition" in prompt
    assert "green terminal glow" in prompt
    assert "forensic focus" in prompt
    assert "selective painterly detail spike on the focal beat" in prompt
    assert "Marcus catches the impossible auth line in a dead office" in prompt


def test_compile_panel_prompt_keeps_legacy_prompt_backward_compatible() -> None:
    legacy_prompt = (
        "manhwa webtoon panel, clean linework, soft atmospheric shading, Korean manhwa style, "
        "high quality digital art. Vertical close-up of Marcus staring into terminal logs."
    )

    prompt = compile_panel_prompt({"prompt": legacy_prompt}, {})

    assert prompt.count("manhwa webtoon panel") == 1
    assert "Vertical close-up of Marcus staring into terminal logs" in prompt


def test_compile_panel_prompt_injects_trigger_phrase_from_generation_profile() -> None:
    packet = {
        "generation_profile": {
            "trigger_phrases": ["sixtongues_style"],
            "style_adapter": {"trigger_word": "sixtongues_style"},
        }
    }
    panel = {
        "scene_prompt": "Marcus catches the impossible auth line in a dead office.",
        "arc_lock": "earth_protocol_noir",
        "environment": "earth_office",
        "cornerstone_style": "standard_dialogue",
        "mood": "tension",
    }

    prompt = compile_panel_prompt(panel, packet)

    assert prompt.startswith("sixtongues_style, manhwa webtoon panel")
    assert prompt.count("sixtongues_style") == 1


def test_create_panel_prompts_from_chapter_seeds_style_metadata() -> None:
    text = """# Chapter Test

Marcus sat alone in the office staring at the terminal logs.

He found an impossible authorization path and kept digging.
"""

    chapter = create_panel_prompts_from_chapter("chtest", text, target_panels=2)
    first_panel = chapter["panels"][0]

    assert chapter["style_system"]["global_tags"]
    assert chapter["style_bible"]["visual_language"]
    assert chapter["character_anchors"]["marcus"].startswith("Asian-American man")
    assert first_panel["scene_prompt"]
    assert first_panel["arc_lock"] == "earth_protocol_noir"
    assert first_panel["cornerstone_style"] == "standard_dialogue"
    assert first_panel["mood"] in {"introspective", "tension", "drama"}
    assert first_panel["style_metadata"]["color_palette"]
    assert first_panel["style_metadata"]["camera_angle"]
