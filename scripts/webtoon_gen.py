#!/usr/bin/env python3
"""
SCBE webtoon panel generator for local FLUX.1-schnell runs.

This script now supports a structured prompt lane:
- cornerstone style
- mood
- arc lock
- panel flex

It remains backward-compatible with legacy prompt strings and simple batch files.

Usage:
    python scripts/webtoon_gen.py --prompt "scene description" -o panel.png
    python scripts/webtoon_gen.py --batch artifacts/webtoon/panel_prompts/ch01_prompts.json
    python scripts/webtoon_gen.py --episode ep02
    python scripts/webtoon_gen.py --batch artifacts/webtoon/panel_prompts/ch01_prompts.json --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "artifacts" / "webtoon"
PROMPTS_DIR = OUT_DIR / "panel_prompts"
DEFAULT_MODEL_ID = "black-forest-labs/FLUX.1-schnell"
DEFAULT_ADAPTER_NAME = "scbe-style"

LEGACY_STYLE_PREFIXES = (
    "manhwa webtoon panel, clean linework, soft atmospheric shading, Korean manhwa style, cinematic composition, high quality digital art. ",
    "manhwa webtoon panel, clean linework, soft atmospheric shading, Korean manhwa style, high quality digital art. ",
)

BASE_STYLE_TAGS = [
    "manhwa webtoon panel",
    "single vertical panel for smartphone scroll reading",
    "one clear story beat, not a poster or splash page",
    "Korean manhwa style",
    "story-first composition",
    "readable acting",
    "emotion carried by posture, gaze, and camera framing",
    "high quality digital art",
]

COMPACT_BASE_STYLE_TAGS = [
    "single vertical Korean webtoon panel",
    "hand-drawn digital illustration",
    "subtle line variation",
    "natural facial acting",
]

CORNERSTONE_STYLE_PRESETS: dict[str, list[str]] = {
    "standard_dialogue": [
        "clean linework",
        "soft atmospheric shading",
        "proportional figures",
        "clear expression acting",
        "soft background separation",
    ],
    "ethereal_divine": [
        "painterly softness",
        "luminous sacred atmosphere",
        "white-gold or auroral light logic",
        "ornamental visual rhythm",
        "awe-forward staging",
    ],
    "chibi_sd": [
        "super-deformed chibi proportions",
        "comedy beat framing",
        "oversized expression shapes",
        "big Korean SFX energy",
        "deliberate temporary style shift",
    ],
    "dark_gritty": [
        "muted palette",
        "heavier contrast",
        "grounded texture emphasis",
        "tension-heavy staging",
        "serious physical weight",
    ],
    "infographic": [
        "infographic panel design",
        "symbolic overlays",
        "crest or readout composition",
        "text-box-safe layout",
        "exposition-forward readability",
    ],
}

MOOD_PRESETS: dict[str, list[str]] = {
    "comedy": [
        "comic timing",
        "playful acting",
        "reaction-first emphasis",
    ],
    "drama": [
        "serious emotional tension",
        "intimate acting",
        "emotionally legible faces",
    ],
    "divine": [
        "sacred awe",
        "reverent composition",
        "numinous light treatment",
    ],
    "exposition": [
        "clarity over clutter",
        "organized visual explanation",
        "clean symbolic readability",
    ],
    "action": [
        "kinetic movement",
        "impact framing",
        "directional energy",
    ],
    "introspective": [
        "quiet internal tension",
        "close emotional framing",
        "brooding stillness",
    ],
    "slice_of_life": [
        "warm domestic energy",
        "gentle timing",
        "soft interpersonal focus",
    ],
    "awe": [
        "scale and wonder",
        "breathtaking reveal energy",
        "environment-first spectacle",
    ],
    "tension": [
        "unease",
        "forensic focus",
        "held-breath suspense",
    ],
}

PANEL_FLEX_PRESETS: dict[str, list[str]] = {
    "chibi_puncture": [
        "allow temporary chibi distortion for emphasis",
        "keep world continuity stable while faces simplify",
    ],
    "painterly_impact": [
        "selective painterly detail spike on the focal beat",
        "treat the key image as a deliberate cornerstone panel",
    ],
    "sketch_memory": [
        "cool desaturated memory treatment",
        "sketch-like instability without breaking continuity",
    ],
    "comedic_expression": [
        "allow exaggerated reaction acting for one beat",
        "temporary expression distortion is intentional",
    ],
    "infographic_overlay": [
        "UI or lore overlay can temporarily break the normal panel format",
        "keep layout readable for narration or system explanation",
    ],
}

ARC_LOCK_PRESETS: dict[str, list[str]] = {
    "earth_protocol_noir": [
        "dark office realism",
        "green terminal glow",
        "dead fluorescent atmosphere",
        "tech-noir world grounding",
    ],
    "protocol_transmission": [
        "protocol-space traversal",
        "abstract routing geometry",
        "whiteout membrane transition",
    ],
    "archive_grounded_magic": [
        "warm crystal archive continuity",
        "architectural fantasy grounded in physical structure",
        "books, stone, and crystal feel material and real",
    ],
    "aethermoor_world_reveal": [
        "coherent impossible geography",
        "Aethermoor reveal logic stays stable",
        "spectacle without losing readability",
    ],
    "maintenance_underworks": [
        "service-tunnel realism",
        "industrial conduit infrastructure",
        "iron brackets, underworks grit, and practical maintenance logic",
    ],
    "void_seed_containment": [
        "anti-light chamber geometry",
        "UM dread containment logic",
        "ritual restraint architecture with severe contrast",
    ],
    "verdant_tithe_biome": [
        "cathedral-dim living forest",
        "memory-garden ecology with coherent pathways",
        "verdant atmospheric depth without losing figure readability",
    ],
    "civic_terrace_cadence": [
        "public-works city architecture",
        "terraced stone geometry and open-air civic flow",
        "ordered Aethermoor urban readability",
    ],
    "underroot_biolabyrinth": [
        "subterranean root-labyrinth logic",
        "living tunnel ecology and bioluminescent shadow",
        "ancient organic infrastructure beneath the world",
    ],
}

ENVIRONMENT_STYLE_TAGS: dict[str, list[str]] = {
    "earth_office": [
        "green monitor light",
        "office-night isolation",
        "corporate realism",
    ],
    "white_void": [
        "overexposed white void",
        "reality erasure",
        "auroral data structures",
    ],
    "crystal_library": [
        "warm amber crystal archive",
        "towering crystal-grown shelves",
        "quiet humming resonance",
    ],
    "crystal_corridor": [
        "transparent crystal corridor",
        "infrastructural fantasy architecture",
        "warm directional crystal light",
    ],
    "aethermoor_exterior": [
        "violet-gold sky",
        "floating landmasses",
        "luminescent river",
        "impossible but coherent landscape",
    ],
    "maintenance_shafts": [
        "CA-white conduit glow",
        "iron brackets and service tunnels",
        "utilitarian darkness with practical wear",
    ],
    "void_seed_chamber": [
        "shadow-black anti-light",
        "geometric dread chamber",
        "containment ritual architecture",
    ],
    "verdant_tithe": [
        "layered emerald shadow",
        "silver pollen and living root canopies",
        "cathedral-dim forest atmosphere",
    ],
    "civic_terraces": [
        "open-air civic terraces",
        "sunlit or overcast public stonework",
        "ordered city-edge architecture",
    ],
    "underroot": [
        "subterranean living roots",
        "bioluminescent root tunnels",
        "organic labyrinth atmosphere",
    ],
}

COMPACT_CORNERSTONE_LABELS: dict[str, str] = {
    "standard_dialogue": "clean linework, hand-drawn softness",
    "ethereal_divine": "luminous sacred atmosphere, painterly softness",
    "chibi_sd": "deliberate chibi exaggeration",
    "dark_gritty": "grounded texture, heavier contrast, lived-in surfaces",
    "infographic": "symbolic infographic composition",
}

COMPACT_MOOD_LABELS: dict[str, str] = {
    "comedy": "comic timing",
    "drama": "serious emotional tension",
    "divine": "sacred awe",
    "exposition": "clear visual explanation",
    "action": "kinetic movement",
    "introspective": "quiet internal tension",
    "slice_of_life": "warm domestic energy",
    "awe": "scale and wonder",
    "tension": "held-breath suspense",
}

COMPACT_PANEL_FLEX_LABELS: dict[str, str] = {
    "chibi_puncture": "temporary chibi puncture",
    "painterly_impact": "painterly focal beat",
    "sketch_memory": "sketch-memory instability",
    "comedic_expression": "exaggerated reaction beat",
    "infographic_overlay": "symbolic overlay readability",
}

COMPACT_ARC_LOCK_LABELS: dict[str, str] = {
    "earth_protocol_noir": "night office realism, green terminal glow",
    "protocol_transmission": "whiteout transmission space",
    "archive_grounded_magic": "physical crystal archive, warm amber light",
    "aethermoor_world_reveal": "operational impossible geography",
    "maintenance_underworks": "industrial maintenance underworks",
    "void_seed_containment": "anti-light containment chamber",
    "verdant_tithe_biome": "cathedral-dim living forest",
    "civic_terrace_cadence": "ordered civic terrace cityscape",
    "underroot_biolabyrinth": "subterranean living root labyrinth",
}

COMPACT_ENVIRONMENT_LABELS: dict[str, str] = {
    "earth_office": "night office, green monitor glow",
    "white_void": "overexposed white void",
    "crystal_library": "towering crystal bookshelves",
    "crystal_corridor": "transparent crystal corridor",
    "aethermoor_exterior": "impossible Aethermoor landscape",
    "maintenance_shafts": "service tunnels and conduit shafts",
    "void_seed_chamber": "geometric dread chamber",
    "verdant_tithe": "layered emerald root canopy",
    "civic_terraces": "open-air civic terraces",
    "underroot": "bioluminescent root tunnels",
}

DEFAULT_GENERATION_PROFILE: dict[str, Any] = {
    "model_id": DEFAULT_MODEL_ID,
    "default_steps": 4,
    "guidance_scale": 0.0,
    "seed_mode": "panel-index-offset",
    "trigger_phrases": [],
    "style_adapter": {},
}


def normalize_generation_profile(packet_or_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "model_id": DEFAULT_GENERATION_PROFILE["model_id"],
        "default_steps": DEFAULT_GENERATION_PROFILE["default_steps"],
        "guidance_scale": DEFAULT_GENERATION_PROFILE["guidance_scale"],
        "seed_mode": DEFAULT_GENERATION_PROFILE["seed_mode"],
        "trigger_phrases": list(DEFAULT_GENERATION_PROFILE["trigger_phrases"]),
        "style_adapter": dict(DEFAULT_GENERATION_PROFILE["style_adapter"]),
    }

    if isinstance(packet_or_profile, dict):
        if isinstance(packet_or_profile.get("generation_profile"), dict):
            source = packet_or_profile["generation_profile"]
        else:
            source = packet_or_profile
    else:
        source = {}

    if not isinstance(source, dict):
        source = {}

    for key in ("model_id", "default_steps", "guidance_scale", "seed_mode"):
        if source.get(key) is not None:
            profile[key] = source[key]

    profile["trigger_phrases"] = unique_phrases(
        as_list(source.get("trigger_phrases", profile["trigger_phrases"]))
    )

    style_adapter = dict(profile.get("style_adapter") or {})
    if isinstance(source.get("style_adapter"), dict):
        for key, value in source["style_adapter"].items():
            if value is not None:
                style_adapter[key] = value
    profile["style_adapter"] = style_adapter

    if source.get("require_adapter") is not None:
        profile["require_adapter"] = bool(source["require_adapter"])

    return profile


def generation_trigger_phrases(packet: dict[str, Any] | None = None) -> list[str]:
    profile = normalize_generation_profile(packet)
    trigger_phrases = list(profile.get("trigger_phrases") or [])
    style_adapter = profile.get("style_adapter") or {}
    if style_adapter.get("trigger_word"):
        trigger_phrases.append(str(style_adapter["trigger_word"]))
    return unique_phrases(trigger_phrases)


def load_style_adapter(pipe, generation_profile: dict[str, Any], *, strict_adapter: bool = False) -> None:
    style_adapter = generation_profile.get("style_adapter") or {}
    adapter_source = style_adapter.get("path") or style_adapter.get("repo_id")
    if not adapter_source:
        return

    adapter_name = style_adapter.get("adapter_name") or DEFAULT_ADAPTER_NAME
    adapter_kwargs: dict[str, Any] = {"adapter_name": adapter_name}
    if style_adapter.get("weight_name"):
        adapter_kwargs["weight_name"] = style_adapter["weight_name"]

    try:
        pipe.load_lora_weights(adapter_source, **adapter_kwargs)
        if style_adapter.get("scale") is not None and hasattr(pipe, "set_adapters"):
            pipe.set_adapters(adapter_name, adapter_weights=float(style_adapter["scale"]))
        print(f"Loaded style adapter: {adapter_source} ({adapter_name})")
    except Exception as exc:  # pragma: no cover - runtime-only adapter path
        if strict_adapter or generation_profile.get("require_adapter"):
            raise
        print(f"WARNING: could not load style adapter {adapter_source}: {exc}")


def get_pipeline(
    *,
    generation_profile: dict[str, Any] | None = None,
    strict_adapter: bool = False,
):
    """Load the requested text-to-image pipeline and optional style adapter."""
    import torch
    from diffusers import AutoPipelineForText2Image, FluxPipeline

    profile = normalize_generation_profile(generation_profile)
    model_id = str(profile.get("model_id") or DEFAULT_MODEL_ID)
    print(f"Loading {model_id}...")

    if "flux" in model_id.casefold():
        pipe = FluxPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.float16,
        )
    else:
        pipe = AutoPipelineForText2Image.from_pretrained(
            model_id,
            torch_dtype=torch.float16,
            variant="fp16",
        )

    if torch.cuda.is_available():
        pipe = pipe.to("cuda")
        try:
            pipe.enable_attention_slicing()
        except Exception:
            pass
    else:
        print("WARNING: No CUDA GPU detected. Running on CPU (very slow).")

    load_style_adapter(pipe, profile, strict_adapter=strict_adapter)
    return pipe


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if item]
    return [value]


def unique_phrases(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        text = text.rstrip(".")
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def compact_anchor_text(anchor: Any, *, max_traits: int = 5) -> str:
    if anchor is None:
        return ""
    parts = [part.strip().rstrip(".") for part in str(anchor).split(",") if part.strip()]
    if not parts:
        return ""
    return ", ".join(parts[:max_traits])


def limited_style_tags(values: Any, *, limit: int = 2) -> list[str]:
    return unique_phrases([str(value).strip() for value in as_list(values) if str(value).strip()])[:limit]


def concise_style_tokens(values: Any, compact_labels: dict[str, str], presets: dict[str, list[str]] | None = None) -> list[str]:
    phrases: list[str] = []
    for value in as_list(values):
        token = str(value).strip()
        if not token:
            continue
        if token in compact_labels:
            phrases.append(compact_labels[token])
            continue
        if presets:
            expanded = expand_style_tokens(token, presets)
            if expanded:
                phrases.append(expanded[0])
                continue
        phrases.append(token.replace("_", " "))
    return unique_phrases(phrases)


def compact_visual_language(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    if not text:
        return None
    lowered = text.casefold()
    if "webtoon" in lowered or "manhwa" in lowered:
        return "Korean webtoon / manhwa"
    return text


def strip_legacy_style_prefix(prompt: str) -> str:
    text = (prompt or "").strip()
    for prefix in LEGACY_STYLE_PREFIXES:
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    return text


def expand_style_tokens(values: Any, presets: dict[str, list[str]]) -> list[str]:
    expanded: list[str] = []
    for value in as_list(values):
        if isinstance(value, str) and value in presets:
            expanded.extend(presets[value])
        else:
            expanded.append(str(value))
    return expanded


def infer_environment_tags(panel_text: str) -> list[str]:
    lowered = panel_text.casefold()
    if "crystal" in lowered or "archive" in lowered or "shelf" in lowered:
        return ENVIRONMENT_STYLE_TAGS["crystal_library"]
    if "corridor" in lowered:
        return ENVIRONMENT_STYLE_TAGS["crystal_corridor"]
    if "office" in lowered or "monitor" in lowered or "terminal" in lowered:
        return ENVIRONMENT_STYLE_TAGS["earth_office"]
    return []


def infer_episode_panel_metadata(name: str, description: str) -> dict[str, Any]:
    combined = f"{name} {description}".casefold()
    metadata: dict[str, Any] = {
        "scene_prompt": description.strip() or name.strip(),
        "style_tags": [],
    }

    if any(token in combined for token in ("readout", "coherence index", "lore", "diagram", "overlay")):
        metadata["cornerstone_style"] = "infographic"
        metadata["mood"] = "exposition"
        metadata["panel_flex"] = "infographic_overlay"
    elif any(token in combined for token in ("memory", "flashback", "washed-out", "distant silhouette")):
        metadata["cornerstone_style"] = "ethereal_divine"
        metadata["mood"] = "introspective"
        metadata["panel_flex"] = "sketch_memory"
    elif any(token in combined for token in ("impact", "kinetic", "fall", "slam", "strike", "movement")):
        metadata["cornerstone_style"] = "dark_gritty"
        metadata["mood"] = "action"
    elif any(token in combined for token in ("spectacle", "awe", "impossible", "aurora", "world reveal", "glimpse")):
        metadata["cornerstone_style"] = "ethereal_divine"
        metadata["mood"] = "awe"
        metadata["panel_flex"] = "painterly_impact"
    elif any(token in combined for token in ("coffee", "sleep-caw", "awkward", "funny", "dry dialogue")):
        metadata["cornerstone_style"] = "standard_dialogue"
        metadata["mood"] = "comedy"
        metadata["panel_flex"] = "comedic_expression"
    else:
        metadata["cornerstone_style"] = "standard_dialogue"
        metadata["mood"] = "drama" if "dialogue" in combined or "decision" in combined else "introspective"

    metadata["style_tags"] = infer_environment_tags(combined)
    return metadata


def resolve_scene_text(panel: dict[str, Any]) -> str:
    candidates = [
        panel.get("scene_prompt"),
        strip_legacy_style_prefix(panel.get("prompt", "")),
        panel.get("description"),
        panel.get("scene_summary"),
        panel.get("beat"),
        panel.get("name"),
    ]
    for candidate in candidates:
        text = str(candidate).strip() if candidate else ""
        if text:
            return text
    return ""


def panel_character_locks(panel: dict[str, Any], packet: dict[str, Any] | None = None) -> list[str]:
    packet = packet or {}
    locks: list[str] = []
    packet_anchors = packet.get("character_anchors", {}) if isinstance(packet, dict) else {}
    characters = as_list(panel.get("characters"))
    for character in characters:
        anchor = packet_anchors.get(character) if isinstance(packet_anchors, dict) else None
        if anchor:
            label = character.replace("_", " ")
            compact = compact_anchor_text(anchor)
            if compact:
                locks.append(f"{label}: {compact}")

    style_metadata = panel.get("style_metadata", {})
    if isinstance(style_metadata, dict):
        primary_anchor = style_metadata.get("character_anchor")
        if primary_anchor:
            compact = compact_anchor_text(primary_anchor)
            if compact:
                locks.append(f"primary look: {compact}")

    return unique_phrases(locks)


def compile_panel_prompt(panel: dict[str, Any], packet: dict[str, Any] | None = None) -> str:
    packet = packet or {}
    style_bible = packet.get("style_bible", {}) if isinstance(packet, dict) else {}
    style_metadata = panel.get("style_metadata", {}) if isinstance(panel.get("style_metadata"), dict) else {}

    tags: list[str] = []
    tags.extend(generation_trigger_phrases(packet))
    tags.extend(COMPACT_BASE_STYLE_TAGS)
    visual_language = compact_visual_language(style_bible.get("visual_language"))
    if visual_language:
        tags.append(visual_language)
    tags.extend(concise_style_tokens(panel.get("arc_lock"), COMPACT_ARC_LOCK_LABELS, ARC_LOCK_PRESETS))
    tags.extend(concise_style_tokens(panel.get("environment"), COMPACT_ENVIRONMENT_LABELS, ENVIRONMENT_STYLE_TAGS))
    tags.extend(concise_style_tokens(panel.get("cornerstone_style"), COMPACT_CORNERSTONE_LABELS, CORNERSTONE_STYLE_PRESETS))
    tags.extend(concise_style_tokens(panel.get("mood"), COMPACT_MOOD_LABELS, MOOD_PRESETS))
    tags.extend(concise_style_tokens(panel.get("panel_flex"), COMPACT_PANEL_FLEX_LABELS, PANEL_FLEX_PRESETS))

    camera_angle = style_metadata.get("camera_angle")
    if camera_angle:
        tags.append(str(camera_angle))
    tags.extend(limited_style_tags(panel.get("style_tags"), limit=2))

    prefix = ", ".join(unique_phrases(tags))
    scene_text = resolve_scene_text(panel) or "story-driven webtoon panel"
    sentence_parts = []

    character_locks = panel_character_locks(panel, packet)
    if character_locks:
        sentence_parts.append("Character lock: " + " | ".join(character_locks))

    sentence_parts.append(scene_text)
    compiled_scene = " ".join(sentence_parts).strip()
    return f"{prefix}. {compiled_scene}" if prefix else compiled_scene


def build_single_prompt(prompt: str, packet: dict[str, Any] | None = None) -> str:
    return compile_panel_prompt({"scene_prompt": prompt, "cornerstone_style": "standard_dialogue"}, packet)


def default_output_path_for_panel(panel: dict[str, Any], chapter_id: str, index: int) -> Path:
    panel_id = panel.get("id") or f"{chapter_id}-p{index + 1:02d}"
    return OUT_DIR / chapter_id / f"{panel_id}.png"


def load_batch_payload(batch_file: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    with open(batch_file, encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, list):
        return None, data

    if isinstance(data, dict) and isinstance(data.get("panels"), list):
        chapter_id = data.get("chapter_id") or Path(batch_file).stem.replace("_prompts", "")
        panels: list[dict[str, Any]] = []
        for index, raw_panel in enumerate(data["panels"]):
            panel = dict(raw_panel)
            panel.setdefault("output", str(default_output_path_for_panel(panel, chapter_id, index)))
            panel.setdefault("seed", 42 + index)
            panel.setdefault("width", panel.pop("w", None) or 720)
            panel.setdefault("height", panel.pop("h", None) or 1280)
            panels.append(panel)
        return data, panels

    raise ValueError(f"Unsupported batch payload in {batch_file}")


def generate_panel(
    pipe,
    prompt: str,
    output_path: str | Path,
    width: int = 720,
    height: int = 1280,
    seed: int | None = None,
    steps: int = 4,
    guidance_scale: float = 0.0,
) -> str:
    """Generate a single panel image."""
    import torch

    generator = torch.Generator("cuda" if torch.cuda.is_available() else "cpu")
    if seed is not None:
        generator.manual_seed(seed)

    t0 = time.time()
    image = pipe(
        prompt,
        width=width,
        height=height,
        num_inference_steps=steps,
        generator=generator,
        guidance_scale=guidance_scale,
    ).images[0]

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(output_path))
    elapsed = time.time() - t0
    size_kb = os.path.getsize(output_path) / 1024
    print(f"  Saved: {output_path} ({size_kb:.0f}KB, {elapsed:.1f}s, seed={seed})")
    return str(output_path)


def parse_episode_markdown(text: str) -> list[dict[str, str]]:
    panels: list[dict[str, str]] = []
    current_panel: dict[str, str] | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line and line[0].isdigit() and "**" in line:
            if current_panel:
                panels.append(current_panel)
            name = line.split("**")[1] if "**" in line else line
            current_panel = {"name": name, "description": ""}
            continue

        if not current_panel or not line or line.startswith("#"):
            continue
        if line.startswith("Story job:"):
            continue
        current_panel["description"] += (" " if current_panel["description"] else "") + line

    if current_panel:
        panels.append(current_panel)

    return panels


def run_episode(
    pipe,
    episode_id: str,
    *,
    dry_run: bool = False,
    steps: int = 4,
    guidance_scale: float = 0.0,
) -> None:
    """Generate all panels for an episode markdown packet."""
    ep_dir = OUT_DIR / "episodes"
    matches = list(ep_dir.glob(f"{episode_id}*.md"))
    if not matches:
        print(f"No episode file found for '{episode_id}' in {ep_dir}")
        sys.exit(1)

    ep_file = matches[0]
    print(f"\nGenerating panels for: {ep_file.name}")
    panels = parse_episode_markdown(ep_file.read_text(encoding="utf-8"))
    if not panels:
        print("No panels found in episode file.")
        return

    out_dir = OUT_DIR / episode_id.replace("-", "_")
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    print(f"Found {len(panels)} panels.")
    for index, panel in enumerate(panels):
        panel_id = f"{episode_id}-p{index + 1:02d}"
        inferred = infer_episode_panel_metadata(panel["name"], panel["description"])
        prompt = compile_panel_prompt({**panel, **inferred})

        is_wide = any(keyword in panel["name"].lower() for keyword in ["memory", "split", "readout", "glimpse"])
        width, height = (1280, 720) if is_wide else (720, 1280)
        out_path = out_dir / f"{panel_id}.png"

        print(f"\n  Panel {index + 1}/{len(panels)}: {panel['name']}")
        print(f"  Prompt: {prompt[:140]}...")

        result = {
            "id": panel_id,
            "name": panel["name"],
            "prompt": prompt,
            "path": str(out_path),
        }

        if dry_run:
            result["ok"] = True
            results.append(result)
            continue

        try:
            generate_panel(
                pipe,
                prompt,
                out_path,
                width=width,
                height=height,
                seed=2000 + index,
                steps=steps,
                guidance_scale=guidance_scale,
            )
            result["ok"] = True
        except Exception as exc:
            print(f"  FAILED: {exc}")
            result["ok"] = False
            result["error"] = str(exc)
        results.append(result)

    manifest = out_dir / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "episode": episode_id,
                "source": str(ep_file),
                "panels": results,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "dry_run": dry_run,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nManifest: {manifest}")

    if dry_run:
        print(f"{len(results)} prompts compiled (dry run).")
        return

    success = sum(1 for result in results if result["ok"])
    print(f"{success}/{len(results)} panels generated.")


def run_batch(
    pipe,
    batch_file: str,
    *,
    dry_run: bool = False,
    packet: dict[str, Any] | None = None,
    panels: list[dict[str, Any]] | None = None,
    generation_profile: dict[str, Any] | None = None,
) -> None:
    """Generate panels from a batch list or a chapter prompt packet."""
    loaded_packet, loaded_panels = load_batch_payload(batch_file)
    packet = packet if packet is not None else loaded_packet
    panels = panels if panels is not None else loaded_panels
    runtime_profile = normalize_generation_profile(generation_profile or packet)
    packet_for_prompt = dict(packet or {})
    packet_for_prompt["generation_profile"] = runtime_profile
    results: list[dict[str, Any]] = []

    for index, panel in enumerate(panels):
        prompt = compile_panel_prompt(panel, packet_for_prompt)
        output = panel.get("output", f"artifacts/webtoon/batch_p{index + 1:02d}.png")
        seed = int(panel.get("seed", 42 + index))
        width = int(panel.get("width", panel.get("w", 720)))
        height = int(panel.get("height", panel.get("h", 1280)))
        steps = int(panel.get("steps", runtime_profile.get("default_steps", 4)))
        guidance_scale = float(panel.get("guidance_scale", runtime_profile.get("guidance_scale", 0.0)))

        result = {
            "id": panel.get("id", f"panel-{index + 1:02d}"),
            "prompt": prompt,
            "path": str(output),
            "seed": seed,
            "width": width,
            "height": height,
            "steps": steps,
            "guidance_scale": guidance_scale,
        }

        if dry_run:
            results.append({**result, "ok": True})
            continue

        try:
            generate_panel(
                pipe,
                prompt,
                output,
                width=width,
                height=height,
                seed=seed,
                steps=steps,
                guidance_scale=guidance_scale,
            )
            result["ok"] = True
        except Exception as exc:
            print(f"FAILED: {exc}")
            result["ok"] = False
            result["error"] = str(exc)
        results.append(result)

    manifest_dir = Path(results[0]["path"]).parent if results else OUT_DIR
    manifest_name = f"{Path(batch_file).stem}_manifest.json"
    manifest_path = manifest_dir / manifest_name
    manifest_path.write_text(
        json.dumps(
            {
                "source": str(batch_file),
                "chapter_id": packet.get("chapter_id") if packet else None,
                "panels": results,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "dry_run": dry_run,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Manifest: {manifest_path}")

    if dry_run:
        print(json.dumps({"source": batch_file, "compiled": len(results), "manifest": str(manifest_path)}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="SCBE webtoon panel generator - FLUX.1-schnell")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prompt", "-p", help="Generate a single panel from a prompt")
    mode.add_argument("--episode", "-e", help="Generate all panels for an episode (for example ep02)")
    mode.add_argument("--batch", "-b", help="JSON batch file or chapter prompt packet")
    parser.add_argument("--output", "-o", default=None, help="Output file path (single mode)")
    parser.add_argument("--seed", "-s", type=int, default=42, help="Random seed")
    parser.add_argument("--width", "-W", type=int, default=720)
    parser.add_argument("--height", "-H", type=int, default=1280)
    parser.add_argument("--steps", type=int, default=None, help="Inference steps (defaults to packet or model profile)")
    parser.add_argument("--guidance-scale", type=float, default=None, help="Guidance scale (defaults to packet or model profile)")
    parser.add_argument("--model-id", default=None, help="Model id override for generation")
    parser.add_argument("--trigger-phrase", action="append", default=[], help="Extra trigger phrase to prepend to prompts")
    parser.add_argument("--adapter-repo", default=None, help="Hugging Face repo id for a LoRA adapter")
    parser.add_argument("--adapter-path", default=None, help="Local path to a LoRA adapter")
    parser.add_argument("--adapter-weight-name", default=None, help="Optional LoRA weight filename")
    parser.add_argument("--adapter-name", default=None, help="Optional adapter name inside diffusers")
    parser.add_argument("--adapter-scale", type=float, default=None, help="Optional adapter scale")
    parser.add_argument("--strict-adapter", action="store_true", help="Fail if the requested adapter cannot be loaded")
    parser.add_argument("--dry-run", action="store_true", help="Compile prompts and write manifests without loading the model")
    args = parser.parse_args()

    def build_runtime_profile(packet: dict[str, Any] | None = None) -> dict[str, Any]:
        profile = normalize_generation_profile(packet)
        if args.model_id:
            profile["model_id"] = args.model_id
        if args.steps is not None:
            profile["default_steps"] = args.steps
        if args.guidance_scale is not None:
            profile["guidance_scale"] = args.guidance_scale
        if args.trigger_phrase:
            profile["trigger_phrases"] = unique_phrases(
                list(profile.get("trigger_phrases") or []) + list(args.trigger_phrase)
            )

        style_adapter = dict(profile.get("style_adapter") or {})
        if args.adapter_repo:
            style_adapter["repo_id"] = args.adapter_repo
        if args.adapter_path:
            style_adapter["path"] = args.adapter_path
        if args.adapter_weight_name:
            style_adapter["weight_name"] = args.adapter_weight_name
        if args.adapter_name:
            style_adapter["adapter_name"] = args.adapter_name
        if args.adapter_scale is not None:
            style_adapter["scale"] = args.adapter_scale
        if style_adapter:
            profile["style_adapter"] = style_adapter
        if args.strict_adapter:
            profile["require_adapter"] = True
        return profile

    if args.prompt:
        runtime_profile = build_runtime_profile()
        compiled_prompt = build_single_prompt(args.prompt, {"generation_profile": runtime_profile})
        if args.dry_run:
            print(json.dumps({"prompt": compiled_prompt, "generation_profile": runtime_profile}, indent=2))
            return
        pipe = get_pipeline(generation_profile=runtime_profile, strict_adapter=bool(runtime_profile.get("require_adapter")))
        output = args.output or str(OUT_DIR / "single_panel.png")
        generate_panel(
            pipe,
            compiled_prompt,
            output,
            args.width,
            args.height,
            args.seed,
            int(runtime_profile.get("default_steps", 4)),
            float(runtime_profile.get("guidance_scale", 0.0)),
        )
    elif args.episode:
        runtime_profile = build_runtime_profile()
        pipe = None if args.dry_run else get_pipeline(
            generation_profile=runtime_profile,
            strict_adapter=bool(runtime_profile.get("require_adapter")),
        )
        run_episode(
            pipe,
            args.episode,
            dry_run=args.dry_run,
            steps=int(runtime_profile.get("default_steps", 4)),
            guidance_scale=float(runtime_profile.get("guidance_scale", 0.0)),
        )
    elif args.batch:
        packet, panels = load_batch_payload(args.batch)
        runtime_profile = build_runtime_profile(packet)
        pipe = None if args.dry_run else get_pipeline(
            generation_profile=runtime_profile,
            strict_adapter=bool(runtime_profile.get("require_adapter")),
        )
        run_batch(
            pipe,
            args.batch,
            dry_run=args.dry_run,
            packet=packet,
            panels=panels,
            generation_profile=runtime_profile,
        )


if __name__ == "__main__":
    main()
