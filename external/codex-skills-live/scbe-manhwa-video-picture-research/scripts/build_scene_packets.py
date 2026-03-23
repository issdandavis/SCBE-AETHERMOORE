#!/usr/bin/env python3
"""Build scene packets for manhwa recap video and webtoon production."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List


MAPPING_MOOD = {
    "danger": "tense",
    "threat": "tense",
    "battle": "intense",
    "attack": "intense",
    "whisper": "mysterious",
    "secret": "mysterious",
    "archive": "scholarly",
    "mentor": "warm",
    "hope": "uplifting",
    "victory": "uplifting",
    "loss": "somber",
    "death": "somber",
}

MAPPING_SETTING = {
    "archive": "ancient crystal archive hall",
    "vault": "high-security containment vault",
    "city": "neo-fantasy city skyline",
    "chamber": "ritual chamber with glowing runes",
    "forest": "moonlit forest corridor",
    "network": "abstract protocol network space",
    "drone": "autonomous fleet operations bay",
    "ocean": "stormy coastal overlook",
}

SFX_BY_MOOD = {
    "tense": ["low sub drone", "heartbeat pulse", "short metallic hit"],
    "intense": ["rising braam", "impact boom", "electric crack"],
    "mysterious": ["reverse shimmer", "soft whisper swell", "glass harmonic"],
    "scholarly": ["library ambience", "quiet synth pad", "subtle page rustle"],
    "warm": ["gentle piano note", "soft wind", "light room tone"],
    "uplifting": ["string lift", "hopeful hit", "airy whoosh"],
    "somber": ["distant bell", "low piano", "dark room tone"],
    "neutral": ["soft ambience", "light transition whoosh"],
}


@dataclass
class Scene:
    index: int
    title: str
    recap_text: str
    mood: str
    setting: str


def _clean_text(raw: str) -> str:
    text = raw.replace("\r\n", "\n")
    text = re.sub(r"^```.*?$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_paragraphs(text: str) -> List[str]:
    paras = [p.strip() for p in text.split("\n\n")]
    return [p for p in paras if len(p) >= 40]


def _first_sentence(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return parts[0].strip() if parts else text.strip()


def _pick_mood(text: str) -> str:
    lower = text.lower()
    for key, mood in MAPPING_MOOD.items():
        if key in lower:
            return mood
    return "neutral"


def _pick_setting(text: str) -> str:
    lower = text.lower()
    for key, setting in MAPPING_SETTING.items():
        if key in lower:
            return setting
    return "cinematic fantasy city interior"


def _merge_to_scenes(paragraphs: List[str], max_scenes: int, words_per_scene: int) -> List[str]:
    scenes: List[str] = []
    buffer: List[str] = []
    count = 0

    for paragraph in paragraphs:
        words = paragraph.split()
        if count + len(words) > words_per_scene and buffer:
            scenes.append("\n\n".join(buffer))
            buffer = [paragraph]
            count = len(words)
        else:
            buffer.append(paragraph)
            count += len(words)

        if len(scenes) >= max_scenes:
            break

    if buffer and len(scenes) < max_scenes:
        scenes.append("\n\n".join(buffer))

    return scenes[:max_scenes]


def build_scenes(raw_text: str, max_scenes: int, words_per_scene: int) -> List[Scene]:
    clean = _clean_text(raw_text)
    paragraphs = _split_paragraphs(clean)
    blocks = _merge_to_scenes(paragraphs, max_scenes=max_scenes, words_per_scene=words_per_scene)

    output: List[Scene] = []
    for idx, block in enumerate(blocks, start=1):
        sentence = _first_sentence(block)
        title = " ".join(sentence.split()[:12]).strip()
        mood = _pick_mood(block)
        setting = _pick_setting(block)
        output.append(Scene(index=idx, title=title, recap_text=block, mood=mood, setting=setting))
    return output


def _make_image_prompt(scene: Scene, style: str) -> str:
    return (
        f"{style}, manhwa style panel, {scene.setting}, mood {scene.mood}, "
        "dynamic framing, clean lineart, dramatic lighting, high detail, no text bubbles"
    )


def _make_video_prompt(scene: Scene, style: str) -> str:
    return (
        f"{style}, cinematic storyboard shot, {scene.setting}, mood {scene.mood}, "
        "subtle camera push-in, parallax-ready composition, 2.5D depth layers"
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: List[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build scene packets from chapter/story text.")
    parser.add_argument("--chapter-file", required=True, help="Path to source chapter/story text file.")
    parser.add_argument("--chapter-title", default="Untitled Chapter", help="Human-readable chapter title.")
    parser.add_argument("--output-dir", required=True, help="Directory for generated packets.")
    parser.add_argument("--max-scenes", type=int, default=18, help="Maximum number of output scenes.")
    parser.add_argument("--words-per-scene", type=int, default=130, help="Approximate words per generated scene.")
    parser.add_argument(
        "--style-tag",
        default="neo-fantasy cyber-myth",
        help="Visual style tag prepended to image/video prompts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    chapter_path = Path(args.chapter_file)
    if not chapter_path.exists():
        raise FileNotFoundError(f"Chapter file not found: {chapter_path}")

    raw_text = chapter_path.read_text(encoding="utf-8", errors="ignore")
    scenes = build_scenes(raw_text, max_scenes=args.max_scenes, words_per_scene=args.words_per_scene)

    output_dir = Path(args.output_dir)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    storyboard = []
    image_rows = []
    video_rows = []
    voice_lines = []

    for scene in scenes:
        scene_id = f"scene_{scene.index:02d}"
        image_prompt = _make_image_prompt(scene, args.style_tag)
        video_prompt = _make_video_prompt(scene, args.style_tag)
        sfx = SFX_BY_MOOD.get(scene.mood, SFX_BY_MOOD["neutral"])

        storyboard.append(
            {
                "scene_id": scene_id,
                "chapter_title": args.chapter_title,
                "title": scene.title,
                "mood": scene.mood,
                "setting": scene.setting,
                "duration_seconds": 8 if scene.mood in {"neutral", "scholarly", "warm"} else 10,
                "sfx": sfx,
                "voice_over": scene.recap_text,
                "image_prompt": image_prompt,
                "video_prompt": video_prompt,
            }
        )

        image_rows.append(
            {
                "scene_id": scene_id,
                "target": "image",
                "prompt": image_prompt,
                "negative_prompt": "extra limbs, low detail, watermark, logo, text",
                "aspect_ratio": "9:16",
            }
        )

        video_rows.append(
            {
                "scene_id": scene_id,
                "target": "video",
                "prompt": video_prompt,
                "duration_seconds": 6,
                "fps": 24,
                "aspect_ratio": "9:16",
            }
        )

        voice_lines.append(f"[Scene {scene.index:02d}] {scene.recap_text.strip()}")

    manifest = {
        "generated_at_utc": timestamp,
        "chapter_title": args.chapter_title,
        "chapter_file": str(chapter_path),
        "scene_count": len(storyboard),
        "files": {
            "storyboard": str(output_dir / "storyboard.json"),
            "image_prompts": str(output_dir / "image_prompts.jsonl"),
            "video_prompts": str(output_dir / "video_prompts.jsonl"),
            "voice_script": str(output_dir / "voice_script.txt"),
        },
    }

    _write_json(output_dir / "storyboard.json", storyboard)
    _write_jsonl(output_dir / "image_prompts.jsonl", image_rows)
    _write_jsonl(output_dir / "video_prompts.jsonl", video_rows)
    (output_dir / "voice_script.txt").write_text("\n\n".join(voice_lines), encoding="utf-8")
    _write_json(output_dir / "manifest.json", manifest)

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

