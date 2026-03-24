#!/usr/bin/env python3
"""
Governed quality gate for webtoon/manhwa prompt packets.

This script validates chapter prompt packets against the current style/canon
requirements, optionally auto-fixes missing structured metadata, and emits a
report that downstream generation/assembly steps can enforce.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import time
from pathlib import Path
from typing import Any

try:
    from webtoon_gen import (
        ARC_LOCK_PRESETS,
        CORNERSTONE_STYLE_PRESETS,
        DEFAULT_GENERATION_PROFILE,
        ENVIRONMENT_STYLE_TAGS,
        MOOD_PRESETS,
        PANEL_FLEX_PRESETS,
        compile_panel_prompt,
        strip_legacy_style_prefix,
    )
except ImportError:  # pragma: no cover - import path fallback for tests
    from scripts.webtoon_gen import (
        ARC_LOCK_PRESETS,
        CORNERSTONE_STYLE_PRESETS,
        DEFAULT_GENERATION_PROFILE,
        ENVIRONMENT_STYLE_TAGS,
        MOOD_PRESETS,
        PANEL_FLEX_PRESETS,
        compile_panel_prompt,
        strip_legacy_style_prefix,
    )


ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT / "artifacts" / "webtoon" / "panel_prompts"
STORYBOARD_MANIFEST = ROOT / "artifacts" / "webtoon" / "series_storyboard_manifest.json"
CANON_SOURCE_PREFIXES = ("content/book/reader-edition/",)

DEFAULT_STYLE_SYSTEM = {
    "version": 1,
    "global_tags": [
        "story-first composition",
        "stable worldbuilding",
        "deliberate style shifts only on key beats",
    ],
}

DEFAULT_STYLE_BIBLE = {
    "visual_language": (
        "Korean webtoon / manhwa with cinematic lighting, readable acting, "
        "strong environmental storytelling, and clean panel-to-panel motion."
    ),
    "rules": [
        "Preserve environment identity and panel intent.",
        "Keep character anchors readable even when finish changes.",
        "Use panel flex deliberately rather than as accidental drift.",
    ],
}

DEFAULT_CHARACTER_ANCHORS = {
    "marcus": "Asian-American man early 30s, short dark messy hair, lean desk-worker build, rumpled dress shirt",
    "polly_raven": "large raven twice normal size, glossy black-violet feathers, polished obsidian eyes, graduation cap monocle bowtie",
    "polly_human": "young woman with glossy black feather-hair, wings folded on back, obsidian eyes, slightly too-long fingers",
    "senna": "woman, controlled composure, lower register presence, weary but precise, governor bearing",
    "alexander": "teenager face but grandfather patience, calm steady ageless quality, gentle but firm",
    "bram": "large man, deep gravelly presence, sparse words, maintenance worker hands, no-nonsense",
    "izack": "robed figure, silhouette, pipe smoke, surrounded by dimensional readouts, unreachable depth",
    "patrol_creature": "many-legged patrol creature, quiet purposeful gait, bridge-scale silhouette, non-human infrastructure fauna",
}

ENVIRONMENT_TO_ARC_LOCK = {
    "earth_office": "earth_protocol_noir",
    "white_void": "protocol_transmission",
    "crystal_library": "archive_grounded_magic",
    "crystal_corridor": "archive_grounded_magic",
    "aethermoor_exterior": "aethermoor_world_reveal",
    "maintenance_shafts": "maintenance_underworks",
    "void_seed_chamber": "void_seed_containment",
    "verdant_tithe": "verdant_tithe_biome",
    "civic_terraces": "civic_terrace_cadence",
    "underroot": "underroot_biolabyrinth",
}

TYPE_TO_CORNERSTONE = {
    "ESTABLISHING": "standard_dialogue",
    "IMPACT": "dark_gritty",
    "KINETIC": "dark_gritty",
    "REVEAL": "ethereal_divine",
    "SPECTACLE": "ethereal_divine",
    "QUIET": "standard_dialogue",
    "DIALOGUE": "standard_dialogue",
    "SPLASH": "ethereal_divine",
    "CLOSING": "standard_dialogue",
}

TYPE_TO_MOOD = {
    "ESTABLISHING": "introspective",
    "IMPACT": "tension",
    "KINETIC": "action",
    "REVEAL": "awe",
    "SPECTACLE": "awe",
    "QUIET": "introspective",
    "DIALOGUE": "drama",
    "SPLASH": "awe",
    "CLOSING": "slice_of_life",
}

TYPE_TO_PANEL_FLEX = {
    "IMPACT": "painterly_impact",
    "SPECTACLE": "painterly_impact",
}

TYPE_TO_CAMERA = {
    "ESTABLISHING": "wide establishing shot",
    "DETAIL": "insert close-up",
    "IMPACT": "compressed wide impact frame",
    "KINETIC": "tall vertical kinetic frame",
    "REVEAL": "two-beat reveal frame",
    "SPECTACLE": "landscape spectacle panel",
    "QUIET": "breathing panel with negative space",
    "DIALOGUE": "shot-reverse-shot with clear acting",
    "EXPOSITION": "medium explanatory frame",
    "SPLASH": "full splash composition",
    "TRANSITION": "tracking transition frame",
    "CLOSING": "closing beat frame with forward momentum",
}

ENVIRONMENT_TO_PALETTE = {
    "earth_office": "cool blues, dead office greens, green terminal glow accents",
    "white_void": "pure white with overexposed edges and faint auroral data traces",
    "crystal_library": "warm amber crystal light with grounded stone neutrals",
    "crystal_corridor": "warm amber crystal light mixed with cool blue refractions",
    "aethermoor_exterior": "violet-gold sky, pale blue luminescence, warm amber crystal",
    "maintenance_shafts": "chalk white conduit glow, gunmetal iron, soot-dark neutrals",
    "void_seed_chamber": "void-black contrast, bruised purple shadows, ritual restraint highlights",
    "verdant_tithe": "deep emerald shadow, silver pollen glints, moss-dark greens",
    "civic_terraces": "weathered civic stone, pale sky light, public-space neutrals",
    "underroot": "deep root-brown shadow, moss green glow, bioluminescent amber accents",
}


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def humanize_chapter_id(chapter_id: str) -> str:
    if chapter_id.startswith("ch") and chapter_id[2:].isdigit():
        return f"Chapter {int(chapter_id[2:])}"
    if chapter_id.startswith("int") and chapter_id[3:].isdigit():
        return f"Interlude {int(chapter_id[3:])}"
    return chapter_id.replace("-", " ").replace("_", " ").title()


def resolve_path(path_value: str | None, packet_path: Path | None) -> Path | None:
    if not path_value:
        return None
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    root_candidate = (ROOT / candidate).resolve()
    if root_candidate.exists():
        return root_candidate
    if packet_path is not None:
        packet_candidate = (packet_path.parent / candidate).resolve()
        if packet_candidate.exists():
            return packet_candidate
        return packet_candidate
    return root_candidate


def load_storyboard_manifest() -> dict[str, Any]:
    if not STORYBOARD_MANIFEST.exists():
        return {}
    return json.loads(STORYBOARD_MANIFEST.read_text(encoding="utf-8"))


def infer_source_basename(chapter_id: str) -> str | None:
    if re.fullmatch(r"ch\d{2}", chapter_id):
        return f"{chapter_id}.md"
    if re.fullmatch(r"int\d{2}", chapter_id):
        return f"interlude-{chapter_id[3:]}-"
    if chapter_id == "rootlight":
        return "ch-rootlight.md"
    return None


def normalize_manifest_path(path_value: str | None) -> str:
    return str(path_value or "").replace("\\", "/").lstrip("./")


def is_canon_source(path_value: str | None) -> bool:
    normalized = normalize_manifest_path(path_value)
    return any(normalized.startswith(prefix) for prefix in CANON_SOURCE_PREFIXES)


def lookup_episode_metadata(
    *,
    chapter_id: str | None = None,
    source_markdown: str | None = None,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    manifest = manifest or load_storyboard_manifest()
    episodes = manifest.get("episodes", [])
    if not episodes:
        return None

    normalized_source = None
    if source_markdown:
        normalized_source = normalize_manifest_path(Path(source_markdown).as_posix())
        if not is_canon_source(normalized_source):
            return None

    if normalized_source:
        for episode in episodes:
            episode_source = normalize_manifest_path(episode.get("source_markdown"))
            if episode_source == normalized_source:
                return episode

    inferred_basename = infer_source_basename(chapter_id or "")
    if inferred_basename:
        for episode in episodes:
            episode_source = normalize_manifest_path(episode.get("source_markdown"))
            if not is_canon_source(episode_source):
                continue
            episode_name = Path(episode_source).name
            if inferred_basename.endswith(".md"):
                if episode_name == inferred_basename:
                    return episode
            elif episode_name.startswith(inferred_basename):
                return episode

    if chapter_id:
        lowered_chapter = chapter_id.casefold()
        for episode in episodes:
            episode_source = normalize_manifest_path(episode.get("source_markdown"))
            if not is_canon_source(episode_source):
                continue
            if str(episode.get("asset_slug") or "").casefold().startswith(lowered_chapter):
                return episode

    return None


def infer_environment(scene_text: str) -> str | None:
    lowered = scene_text.casefold()
    if any(token in lowered for token in ("terminal", "monitor", "office", "keyboard", "server")):
        return "earth_office"
    if any(token in lowered for token in ("whiteout", "white void", "overexposed", "reality erasing", "void")):
        return "white_void"
    if any(token in lowered for token in ("corridor", "transparent floor", "doorway", "hallway")):
        return "crystal_corridor"
    if any(token in lowered for token in ("aurora", "floating land", "luminescent river", "aethermoor")):
        return "aethermoor_exterior"
    if any(token in lowered for token in ("crystal", "archive", "shelf", "library", "bookshelf")):
        return "crystal_library"
    return None


def infer_characters(scene_text: str) -> list[str]:
    lowered = scene_text.casefold()
    characters: list[str] = []

    if "marcus" in lowered or "chen" in lowered:
        characters.append("marcus")
    if "polly" in lowered or "raven" in lowered:
        if any(token in lowered for token in ("human form", "young woman", "feather-hair", "wings folded")):
            characters.append("polly_human")
        elif "raven" in lowered or "beak" in lowered or "feathers" in lowered:
            characters.append("polly_raven")
        else:
            characters.append("polly_raven")
    if "senna" in lowered:
        characters.append("senna")
    if "alexander" in lowered:
        characters.append("alexander")
    if "bram" in lowered:
        characters.append("bram")
    if "izack" in lowered:
        characters.append("izack")
    if "patrol creature" in lowered or "many-legged" in lowered:
        characters.append("patrol_creature")

    seen: set[str] = set()
    ordered: list[str] = []
    for character in characters:
        if character not in seen:
            seen.add(character)
            ordered.append(character)
    return ordered


def default_dimensions(panel_type: str) -> tuple[int, int]:
    if panel_type in {"ESTABLISHING", "SPECTACLE", "SPLASH"}:
        return (1280, 720)
    return (720, 1280)


def panel_scene_text(panel: dict[str, Any]) -> str:
    return (
        str(panel.get("scene_prompt") or "").strip()
        or strip_legacy_style_prefix(str(panel.get("prompt") or ""))
        or str(panel.get("scene_summary") or "").strip()
        or str(panel.get("continuity") or "").strip()
        or str(panel.get("beat") or "").strip()
    )


def build_style_metadata(panel: dict[str, Any], character_anchors: dict[str, str]) -> dict[str, Any]:
    panel_type = str(panel.get("type") or "QUIET")
    characters = as_list(panel.get("characters"))
    anchors = [character_anchors[char] for char in characters if char in character_anchors]
    return {
        "color_palette": ENVIRONMENT_TO_PALETTE.get(panel.get("environment")),
        "camera_angle": TYPE_TO_CAMERA.get(panel_type),
        "composition": panel_type,
        "mood": panel.get("mood"),
        "character_anchor": ". ".join(anchors[:2]) if anchors else None,
        "arc_lock": panel.get("arc_lock"),
        "cornerstone_style": panel.get("cornerstone_style"),
    }


def auto_fix_packet(
    packet: dict[str, Any],
    *,
    packet_path: Path | None = None,
    rewrite_prompts: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    fixed = copy.deepcopy(packet)
    fixes: list[str] = []

    chapter_id = str(fixed.get("chapter_id") or "unknown")
    episode_metadata = lookup_episode_metadata(
        chapter_id=chapter_id,
        source_markdown=fixed.get("source_markdown"),
    )

    if not fixed.get("title"):
        fixed["title"] = humanize_chapter_id(chapter_id)
        fixes.append("filled missing packet title from chapter_id")

    if not fixed.get("episode_id"):
        if episode_metadata and episode_metadata.get("episode_id"):
            fixed["episode_id"] = episode_metadata["episode_id"]
            fixes.append("filled missing episode_id from storyboard manifest")
        else:
            fixed["episode_id"] = chapter_id
            fixes.append("filled missing episode_id from chapter_id")

    if not fixed.get("section_title"):
        fixed["section_title"] = (episode_metadata or {}).get("title") or fixed["title"]
        fixes.append("filled missing section_title")

    if not fixed.get("section_type"):
        fixed["section_type"] = (episode_metadata or {}).get("section_type") or (
            "interlude" if chapter_id.startswith("int") else "chapter"
        )
        fixes.append("filled missing section_type")

    if not fixed.get("source_markdown") and episode_metadata and episode_metadata.get("source_markdown"):
        fixed["source_markdown"] = episode_metadata["source_markdown"]
        fixes.append("filled missing source_markdown from storyboard manifest")

    if not fixed.get("key_script") and episode_metadata and episode_metadata.get("key_script"):
        fixed["key_script"] = episode_metadata["key_script"]
        fixes.append("filled missing key_script from storyboard manifest")

    if not fixed.get("target_panel_min"):
        fixed["target_panel_min"] = (episode_metadata or {}).get("target_panel_min") or max(
            1, len(fixed.get("panels", [])) - 2
        )
        fixes.append("filled missing target_panel_min")

    if not fixed.get("target_panel_max"):
        fixed["target_panel_max"] = (episode_metadata or {}).get("target_panel_max") or max(
            int(fixed["target_panel_min"]),
            len(fixed.get("panels", [])) + 2,
        )
        fixes.append("filled missing target_panel_max")

    if not fixed.get("status"):
        fixed["status"] = (episode_metadata or {}).get("status") or "packet-draft"
        fixes.append("filled missing packet status")

    style_system = fixed.setdefault("style_system", copy.deepcopy(DEFAULT_STYLE_SYSTEM))
    if not style_system.get("global_tags"):
        style_system["global_tags"] = copy.deepcopy(DEFAULT_STYLE_SYSTEM["global_tags"])
        fixes.append("filled missing style_system.global_tags")
    if "version" not in style_system:
        style_system["version"] = 1
        fixes.append("filled missing style_system.version")

    style_bible = fixed.setdefault("style_bible", copy.deepcopy(DEFAULT_STYLE_BIBLE))
    if not style_bible.get("visual_language"):
        style_bible["visual_language"] = DEFAULT_STYLE_BIBLE["visual_language"]
        fixes.append("filled missing style_bible.visual_language")
    if not style_bible.get("rules"):
        style_bible["rules"] = copy.deepcopy(DEFAULT_STYLE_BIBLE["rules"])
        fixes.append("filled missing style_bible.rules")

    character_anchors = fixed.setdefault("character_anchors", copy.deepcopy(DEFAULT_CHARACTER_ANCHORS))
    if not character_anchors:
        fixed["character_anchors"] = copy.deepcopy(DEFAULT_CHARACTER_ANCHORS)
        character_anchors = fixed["character_anchors"]
        fixes.append("filled missing character_anchors")

    generation_profile = fixed.setdefault("generation_profile", copy.deepcopy(DEFAULT_GENERATION_PROFILE))
    if not generation_profile.get("model_id"):
        generation_profile["model_id"] = DEFAULT_GENERATION_PROFILE["model_id"]
        fixes.append("filled missing generation_profile.model_id")
    if generation_profile.get("default_steps") is None:
        generation_profile["default_steps"] = DEFAULT_GENERATION_PROFILE["default_steps"]
        fixes.append("filled missing generation_profile.default_steps")
    if generation_profile.get("guidance_scale") is None:
        generation_profile["guidance_scale"] = DEFAULT_GENERATION_PROFILE["guidance_scale"]
        fixes.append("filled missing generation_profile.guidance_scale")
    if generation_profile.get("seed_mode") is None:
        generation_profile["seed_mode"] = DEFAULT_GENERATION_PROFILE["seed_mode"]
        fixes.append("filled missing generation_profile.seed_mode")
    if not isinstance(generation_profile.get("trigger_phrases"), list):
        generation_profile["trigger_phrases"] = copy.deepcopy(DEFAULT_GENERATION_PROFILE["trigger_phrases"])
        fixes.append("filled missing generation_profile.trigger_phrases")
    if not isinstance(generation_profile.get("style_adapter"), dict):
        generation_profile["style_adapter"] = copy.deepcopy(DEFAULT_GENERATION_PROFILE["style_adapter"])
        fixes.append("filled missing generation_profile.style_adapter")

    panels = fixed.setdefault("panels", [])
    fixed["panel_count"] = len(panels)

    for index, panel in enumerate(panels):
        panel_id = panel.get("id") or f"{chapter_id}-p{index + 1:02d}"
        if not panel.get("id"):
            panel["id"] = panel_id
            fixes.append(f"{panel_id}: filled missing panel id")

        scene_text = panel_scene_text(panel)
        if not panel.get("scene_prompt") and scene_text:
            panel["scene_prompt"] = scene_text
            fixes.append(f"{panel_id}: filled missing scene_prompt")

        panel_type = str(panel.get("type") or "QUIET").upper()
        if not panel.get("type"):
            panel["type"] = panel_type
            fixes.append(f"{panel_id}: defaulted panel type to {panel_type}")

        if not panel.get("environment"):
            inferred_environment = infer_environment(scene_text)
            if inferred_environment:
                panel["environment"] = inferred_environment
                fixes.append(f"{panel_id}: inferred environment={inferred_environment}")

        if not panel.get("characters"):
            inferred_characters = infer_characters(scene_text)
            if inferred_characters:
                panel["characters"] = inferred_characters
                fixes.append(f"{panel_id}: inferred characters={','.join(inferred_characters)}")

        if not panel.get("arc_lock") and panel.get("environment") in ENVIRONMENT_TO_ARC_LOCK:
            panel["arc_lock"] = ENVIRONMENT_TO_ARC_LOCK[str(panel["environment"])]
            fixes.append(f"{panel_id}: set arc_lock from environment")

        if not panel.get("cornerstone_style"):
            panel["cornerstone_style"] = TYPE_TO_CORNERSTONE.get(panel_type, "standard_dialogue")
            fixes.append(f"{panel_id}: set cornerstone_style from panel type")

        if not panel.get("mood"):
            panel["mood"] = TYPE_TO_MOOD.get(panel_type, "introspective")
            fixes.append(f"{panel_id}: set mood from panel type")

        if not panel.get("panel_flex") and panel_type in TYPE_TO_PANEL_FLEX:
            panel["panel_flex"] = TYPE_TO_PANEL_FLEX[panel_type]
            fixes.append(f"{panel_id}: set panel_flex from panel type")

        width = panel.get("w") or panel.get("width")
        height = panel.get("h") or panel.get("height")
        if not width or not height:
            default_w, default_h = default_dimensions(panel_type)
            panel["w"] = int(width or default_w)
            panel["h"] = int(height or default_h)
            fixes.append(f"{panel_id}: filled missing panel dimensions")
        else:
            panel["w"] = int(width)
            panel["h"] = int(height)

        panel.setdefault("style_tags", [])
        style_metadata = panel.setdefault("style_metadata", {})
        rebuilt_style_metadata = build_style_metadata(panel, fixed["character_anchors"])
        for key, value in rebuilt_style_metadata.items():
            if style_metadata.get(key) is None and value is not None:
                style_metadata[key] = value
                fixes.append(f"{panel_id}: filled style_metadata.{key}")

        compiled_prompt = compile_panel_prompt(panel, fixed)
        panel["compiled_prompt"] = compiled_prompt
        if rewrite_prompts or not panel.get("prompt"):
            panel["prompt"] = compiled_prompt
            fixes.append(f"{panel_id}: {'rewrote' if rewrite_prompts else 'filled'} prompt from governed metadata")

        if not panel.get("negative_prompt"):
            panel["negative_prompt"] = (
                "low detail, inconsistent character design, unreadable anatomy, random environment drift"
            )
            fixes.append(f"{panel_id}: filled negative_prompt guardrail")

    return fixed, fixes


def validate_packet(packet: dict[str, Any], *, packet_path: Path | None = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    chapter_id = packet.get("chapter_id")
    if not chapter_id:
        errors.append("packet missing chapter_id")
    if not packet.get("episode_id"):
        errors.append("packet missing episode_id")
    if not packet.get("title"):
        errors.append("packet missing title")
    if not packet.get("section_title"):
        errors.append("packet missing section_title")
    if not packet.get("section_type"):
        errors.append("packet missing section_type")
    if not packet.get("source_markdown"):
        errors.append("packet missing source_markdown")
    if not packet.get("key_script"):
        errors.append("packet missing key_script")
    if packet.get("target_panel_min") is None:
        errors.append("packet missing target_panel_min")
    if packet.get("target_panel_max") is None:
        errors.append("packet missing target_panel_max")
    if not packet.get("status"):
        errors.append("packet missing status")
    if not packet.get("panels"):
        errors.append("packet has no panels")

    style_system = packet.get("style_system") or {}
    if not style_system.get("global_tags"):
        errors.append("packet missing style_system.global_tags")

    style_bible = packet.get("style_bible") or {}
    if not style_bible.get("visual_language"):
        errors.append("packet missing style_bible.visual_language")

    character_anchors = packet.get("character_anchors") or {}
    if not character_anchors:
        errors.append("packet missing character_anchors")

    generation_profile = packet.get("generation_profile") or {}
    if not generation_profile.get("model_id"):
        errors.append("packet missing generation_profile.model_id")
    if generation_profile.get("default_steps") is None:
        errors.append("packet missing generation_profile.default_steps")
    if generation_profile.get("guidance_scale") is None:
        errors.append("packet missing generation_profile.guidance_scale")
    if generation_profile.get("seed_mode") is None:
        warnings.append("packet missing generation_profile.seed_mode")
    if not isinstance(generation_profile.get("trigger_phrases"), list):
        warnings.append("packet generation_profile.trigger_phrases should be a list")

    style_adapter = generation_profile.get("style_adapter") or {}
    if style_adapter and not isinstance(style_adapter, dict):
        warnings.append("packet generation_profile.style_adapter should be an object")
        style_adapter = {}

    source_markdown_path = resolve_path(packet.get("source_markdown"), packet_path)
    if packet.get("source_markdown") and (source_markdown_path is None or not source_markdown_path.exists()):
        errors.append("packet source_markdown is not readable")

    key_script_path = resolve_path(packet.get("key_script"), packet_path)
    if packet.get("key_script") and (key_script_path is None or not key_script_path.exists()):
        errors.append("packet key_script is not readable")

    if packet.get("reference_chapter"):
        visual_memory_path = resolve_path(packet.get("visual_memory_packet"), packet_path)
        if visual_memory_path is None or not visual_memory_path.exists():
            errors.append("reference chapter missing readable visual_memory_packet")
        if not generation_profile.get("trigger_phrases") and not style_adapter.get("trigger_word"):
            warnings.append("reference chapter missing trigger phrase for style activation")
        if not style_adapter.get("repo_id") and not style_adapter.get("path"):
            warnings.append("reference chapter missing style adapter source")

    if packet.get("panel_count") != len(packet.get("panels", [])):
        warnings.append("panel_count does not match number of panels")

    target_panel_min = packet.get("target_panel_min")
    target_panel_max = packet.get("target_panel_max")
    if isinstance(target_panel_min, int) and isinstance(target_panel_max, int):
        if target_panel_min > target_panel_max:
            errors.append("target panel range is inverted")
        elif not (target_panel_min <= len(packet.get("panels", [])) <= target_panel_max):
            warnings.append("panel_count falls outside target panel range")

    for index, panel in enumerate(packet.get("panels", [])):
        panel_id = panel.get("id") or f"panel-{index + 1:02d}"
        scene_text = panel_scene_text(panel)
        panel_type = str(panel.get("type") or "").upper()

        if not scene_text:
            errors.append(f"{panel_id}: missing scene_prompt/prompt text")

        if not panel.get("environment"):
            errors.append(f"{panel_id}: missing environment")
        elif panel["environment"] not in ENVIRONMENT_STYLE_TAGS:
            warnings.append(f"{panel_id}: environment '{panel['environment']}' not in governed preset map")

        if not panel.get("arc_lock"):
            errors.append(f"{panel_id}: missing arc_lock")
        elif panel["arc_lock"] not in ARC_LOCK_PRESETS:
            warnings.append(f"{panel_id}: arc_lock '{panel['arc_lock']}' not in governed preset map")

        if not panel.get("cornerstone_style"):
            errors.append(f"{panel_id}: missing cornerstone_style")
        elif panel["cornerstone_style"] not in CORNERSTONE_STYLE_PRESETS:
            warnings.append(f"{panel_id}: cornerstone_style '{panel['cornerstone_style']}' not in governed preset map")

        if not panel.get("mood"):
            errors.append(f"{panel_id}: missing mood")
        elif any(mood not in MOOD_PRESETS for mood in as_list(panel["mood"])):
            warnings.append(f"{panel_id}: mood contains non-governed preset values")

        if panel.get("panel_flex") and any(flex not in PANEL_FLEX_PRESETS for flex in as_list(panel["panel_flex"])):
            warnings.append(f"{panel_id}: panel_flex contains non-governed preset values")

        characters = as_list(panel.get("characters"))
        if not characters:
            warnings.append(f"{panel_id}: no character bindings provided")
        for character in characters:
            if character not in character_anchors:
                errors.append(f"{panel_id}: unknown character '{character}' not in character_anchors")

        width = panel.get("w") or panel.get("width")
        height = panel.get("h") or panel.get("height")
        if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
            errors.append(f"{panel_id}: invalid panel dimensions")

        style_metadata = panel.get("style_metadata") or {}
        for key in ("color_palette", "camera_angle", "composition", "mood", "character_anchor"):
            if not style_metadata.get(key):
                warnings.append(f"{panel_id}: missing style_metadata.{key}")

        if not panel.get("compiled_prompt"):
            warnings.append(f"{panel_id}: missing compiled_prompt")

    return errors, warnings


def governance_score(errors: list[str], warnings: list[str]) -> int:
    score = 100 - (len(errors) * 12) - (len(warnings) * 3)
    return max(0, min(100, score))


def govern_packet(
    packet: dict[str, Any],
    *,
    packet_path: Path | None = None,
    auto_fix: bool = True,
    rewrite_prompts: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    governed_packet = copy.deepcopy(packet)
    fixes: list[str] = []
    if auto_fix:
        governed_packet, fixes = auto_fix_packet(
            governed_packet,
            packet_path=packet_path,
            rewrite_prompts=rewrite_prompts,
        )

    errors, warnings = validate_packet(governed_packet, packet_path=packet_path)
    report = {
        "chapter_id": governed_packet.get("chapter_id"),
        "approved": not errors,
        "score": governance_score(errors, warnings),
        "errors": errors,
        "warnings": warnings,
        "auto_fixes": fixes,
        "panel_count": len(governed_packet.get("panels", [])),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "packet_path": str(packet_path) if packet_path else None,
    }
    return governed_packet, report


def load_packet(packet_path: Path) -> dict[str, Any]:
    return json.loads(packet_path.read_text(encoding="utf-8"))


def default_report_path(packet_path: Path, packet: dict[str, Any]) -> Path:
    chapter_id = packet.get("chapter_id") or packet_path.stem.replace("_prompts", "")
    return PROMPTS_DIR / f"{chapter_id}_quality_report.json"


def load_quality_report(report_path: Path) -> dict[str, Any]:
    return json.loads(report_path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Governed quality gate for webtoon prompt packets")
    parser.add_argument("--packet", required=True, help="Prompt packet JSON to validate")
    parser.add_argument("--report", help="Optional report output path")
    parser.add_argument("--write-back", action="store_true", help="Write repaired packet back to disk")
    parser.add_argument("--auto-fix", action="store_true", help="Auto-fill governed metadata before validation")
    parser.add_argument("--rewrite-prompts", action="store_true", help="Rewrite packet prompts from governed metadata")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if packet is not approved")
    args = parser.parse_args()

    packet_path = Path(args.packet)
    packet = load_packet(packet_path)
    governed_packet, report = govern_packet(
        packet,
        packet_path=packet_path,
        auto_fix=args.auto_fix,
        rewrite_prompts=args.rewrite_prompts,
    )

    report_path = Path(args.report) if args.report else default_report_path(packet_path, governed_packet)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.write_back:
        packet_path.write_text(json.dumps(governed_packet, indent=2), encoding="utf-8")

    print(json.dumps({"approved": report["approved"], "score": report["score"], "report": str(report_path)}, indent=2))
    if args.strict and not report["approved"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
