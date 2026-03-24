#!/usr/bin/env python3
"""
Build a single-image lock packet from a storyboard prompt packet.

Use this when the lane needs to stop batch rendering and lock one image first:
- character reference lock
- environment ratio lock
- hero frame refinement
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.webtoon_gen import compile_panel_prompt


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = ROOT / "artifacts" / "webtoon" / "lock_packets"


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def merge_negative_prompts(*values: Any) -> str | None:
    parts: list[str] = []
    for value in values:
        if not value:
            continue
        if isinstance(value, list):
            for item in value:
                parts.extend(piece.strip() for piece in str(item).split(",") if piece.strip())
        else:
            parts.extend(piece.strip() for piece in str(value).split(",") if piece.strip())
    merged = ", ".join(dict.fromkeys(parts))
    return merged or None


def character_negative_prompt(packet: dict[str, Any], panel: dict[str, Any]) -> str | None:
    negatives = packet.get("character_negative_anchors", {})
    if not isinstance(negatives, dict):
        return None
    parts: list[str] = []
    for character in as_list(panel.get("characters")):
        negative = negatives.get(character)
        if negative:
            parts.append(str(negative))
    return merge_negative_prompts(parts)


def lock_prompt_reinforcement(panel: dict[str, Any], lock_type: str) -> str | None:
    characters = set(as_list(panel.get("characters")))
    reinforcements: list[str] = []

    if lock_type == "character" and "marcus" in characters:
        reinforcements.append(
            "Visible age cue: clearly early-30s Asian-American engineer, light stubble, under-eye fatigue, long-hour office weariness, not teenage, not idol-clean."
        )

    if lock_type == "environment" and str(panel.get("environment") or "") == "crystal_corridor":
        reinforcements.append(
            "Environment lock: corridor proportions must feel reusable and architecturally repeatable from panel to panel."
        )

    return " ".join(reinforcements).strip() or None


def lock_negative_reinforcement(panel: dict[str, Any], lock_type: str) -> str | None:
    characters = set(as_list(panel.get("characters")))
    additions: list[str] = []

    if lock_type == "character" and "marcus" in characters:
        additions.extend(
            [
                "teenager",
                "boy band idol",
                "bishonen",
                "baby face",
                "k-pop idol styling",
                "overly pretty",
                "fashion-model jawline",
                "fade haircut",
                "undercut glamour",
            ]
        )

    return merge_negative_prompts(additions)


def load_packet(packet_path: Path) -> dict[str, Any]:
    return json.loads(packet_path.read_text(encoding="utf-8"))


def find_panel(packet: dict[str, Any], panel_id: str) -> dict[str, Any]:
    for panel in packet.get("panels", []):
        if panel.get("id") == panel_id:
            return dict(panel)
    raise KeyError(f"Panel '{panel_id}' not found")


def acceptance_criteria(packet: dict[str, Any], panel: dict[str, Any], lock_type: str) -> list[str]:
    criteria = [
        "One strong image is worth more than a dozen drifting acceptable ones.",
        "No text, speech bubbles, subtitles, or caption boxes in the image.",
        "Composition must stay usable for Chapter 1 reference work.",
    ]

    characters = set(as_list(panel.get("characters")))
    environment = str(panel.get("environment") or "")
    scene_text = str(panel.get("scene_prompt") or panel.get("scene_summary") or "")

    if "marcus" in characters:
        criteria.extend(
            [
                "Marcus must clearly read as Asian-American, not generically white or ambiguous.",
                "Marcus stays lean, tired, and technical-looking, never superheroic or fashion-model polished.",
                "Hair stays short, dark, and slightly messy.",
            ]
        )

    if "polly_human" in characters:
        criteria.append("Polly human form must keep feather-hair, obsidian eyes, and controlled posture.")
    if "polly_raven" in characters:
        criteria.append("Polly raven form must read as academic authority, not mascot-cute.")

    if environment == "earth_office":
        criteria.extend(
            [
                "Office proportions must feel grounded and corporate, not cathedral-like.",
                "Green monitor glow and dead fluorescent mood should stay consistent.",
            ]
        )
    elif environment == "crystal_library":
        criteria.extend(
            [
                "Archive scale must feel architectural and coherent, not random fantasy cavern.",
                "Shelf, arch, and floor ratios should support reuse in adjacent panels.",
            ]
        )
    elif environment == "crystal_corridor":
        criteria.extend(
            [
                "Corridor width, ceiling rhythm, and crystal column spacing must feel repeatable.",
                "The corridor should read as infrastructure, not decorative palace hallway.",
            ]
        )

    if lock_type == "character":
        criteria.append("Primary judgment is character identity lock before anything else.")
    if lock_type == "environment":
        criteria.append("Primary judgment is stable architectural ratio and reusable room logic.")
    if "coffee" in scene_text.casefold():
        criteria.append("The mood should stay human and practical, not gag-panel silly.")

    return criteria


def build_lock_packet(
    packet: dict[str, Any],
    panel: dict[str, Any],
    *,
    lock_name: str,
    lock_type: str,
) -> dict[str, Any]:
    prompt = compile_panel_prompt(panel, packet)
    prompt = " ".join(part for part in [prompt, lock_prompt_reinforcement(panel, lock_type)] if part).strip()
    negative_prompt = merge_negative_prompts(
        packet.get("default_negative_prompt"),
        character_negative_prompt(packet, panel),
        lock_negative_reinforcement(panel, lock_type),
        panel.get("negative_prompt"),
    )

    return {
        "lock_name": lock_name,
        "lock_type": lock_type,
        "chapter_id": packet.get("chapter_id"),
        "episode_id": packet.get("episode_id"),
        "panel_id": panel.get("id"),
        "shot_label": panel.get("shot_label"),
        "title": panel.get("beat") or panel.get("scene_summary") or panel.get("id"),
        "preferred_backend": "imagen-ultra",
        "scene_prompt": panel.get("scene_prompt"),
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "width": int(panel.get("w") or panel.get("width") or 720),
        "height": int(panel.get("h") or panel.get("height") or 1280),
        "environment": panel.get("environment"),
        "characters": as_list(panel.get("characters")),
        "character_anchors": {
            character: packet.get("character_anchors", {}).get(character)
            for character in as_list(panel.get("characters"))
            if packet.get("character_anchors", {}).get(character)
        },
        "style_metadata": panel.get("style_metadata") or {},
        "acceptance_criteria": acceptance_criteria(packet, panel, lock_type),
    }


def lock_packet_markdown(lock_packet: dict[str, Any]) -> str:
    criteria = "\n".join(f"- {item}" for item in lock_packet["acceptance_criteria"])
    anchors = "\n".join(
        f"- `{name}`: {anchor}" for name, anchor in (lock_packet.get("character_anchors") or {}).items()
    )
    if not anchors:
        anchors = "- none"

    return f"""# {lock_packet['lock_name']}

- Chapter: `{lock_packet['chapter_id']}`
- Episode: `{lock_packet['episode_id']}`
- Panel: `{lock_packet['panel_id']}`
- Shot: `{lock_packet.get('shot_label') or 'n/a'}`
- Lock type: `{lock_packet['lock_type']}`
- Preferred backend: `{lock_packet['preferred_backend']}`
- Target size: `{lock_packet['width']}x{lock_packet['height']}`

## Why This Frame

{lock_packet['scene_prompt']}

## Character Anchors

{anchors}

## Prompt

```text
{lock_packet['prompt']}
```

## Negative Prompt

```text
{lock_packet.get('negative_prompt') or ''}
```

## Acceptance Criteria

{criteria}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a single-image webtoon lock packet")
    parser.add_argument("--packet", required=True, help="Prompt packet JSON path")
    parser.add_argument("--panel-id", required=True, help="Panel id to lock")
    parser.add_argument(
        "--lock-type",
        choices=("character", "environment", "hero"),
        default="character",
        help="Primary thing this lock packet is trying to stabilize",
    )
    parser.add_argument("--lock-name", help="Optional friendly name")
    parser.add_argument("--output-dir", help="Optional output directory")
    args = parser.parse_args()

    packet_path = Path(args.packet)
    packet = load_packet(packet_path)
    panel = find_panel(packet, args.panel_id)
    chapter_id = str(packet.get("chapter_id") or "packet")
    lock_name = args.lock_name or f"{chapter_id}-{args.panel_id}-{args.lock_type}-lock"
    output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUT_DIR / chapter_id / lock_name
    output_dir.mkdir(parents=True, exist_ok=True)

    packet_payload = build_lock_packet(packet, panel, lock_name=lock_name, lock_type=args.lock_type)
    json_path = output_dir / "lock_packet.json"
    md_path = output_dir / "lock_packet.md"

    json_path.write_text(json.dumps(packet_payload, indent=2), encoding="utf-8")
    md_path.write_text(lock_packet_markdown(packet_payload), encoding="utf-8")

    print(json.dumps({"json": str(json_path), "markdown": str(md_path)}, indent=2))


if __name__ == "__main__":
    main()
