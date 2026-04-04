"""Chapter Video Pipeline — TTS narration + title cards for YouTube.

Reads the novel manuscript, splits into chapters, generates TTS audio
using Kokoro, creates title card images with Pillow, and composites
into videos with ffmpeg.

Usage:
    python scripts/publish/chapter_video_pipeline.py --chapter 1        # Single chapter
    python scripts/publish/chapter_video_pipeline.py --all              # All chapters
    python scripts/publish/chapter_video_pipeline.py --list             # List chapters
    python scripts/publish/chapter_video_pipeline.py --chapter 1 --dry-run  # Preview only
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BOOK_PATH = PROJECT_ROOT / "artifacts" / "book" / "kdp" / "six-tongues-protocol-v2.md"
OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "videos"
MODEL_PATH = PROJECT_ROOT / "kokoro-v1.0.onnx"
VOICES_PATH = PROJECT_ROOT / "voices-v1.0.bin"

# TTS settings (tuned from user's cadence matching insight)
VOICE = "am_adam"
SPEED = 0.92  # slightly slower for narrative weight
MAX_CHARS_PER_SEGMENT = 500  # Kokoro handles this well

# Video settings
WIDTH = 1920
HEIGHT = 1080
BG_COLOR = (11, 13, 18)  # matches website --bg
ACCENT_COLOR = (214, 167, 86)  # matches website --accent
TEXT_COLOR = (242, 240, 234)  # matches website --text
MUTED_COLOR = (163, 172, 185)  # matches website --muted
FPS = 1  # static image + audio = 1 FPS is fine


@dataclass
class Chapter:
    number: int
    title: str
    text: str
    line_start: int
    line_end: int
    word_count: int


def parse_chapters(book_path: Path) -> List[Chapter]:
    """Parse the manuscript into chapters."""
    content = book_path.read_text(encoding="utf-8")
    lines = content.split("\n")

    # Find chapter boundaries
    chapter_pattern = re.compile(r"^Chapter\s+(\d+):\s*(.+)$", re.IGNORECASE)
    chapter_starts = []

    for i, line in enumerate(lines):
        m = chapter_pattern.match(line.strip())
        if m:
            chapter_starts.append((i, int(m.group(1)), m.group(2).strip()))

    chapters = []
    for idx, (start_line, num, title) in enumerate(chapter_starts):
        end_line = chapter_starts[idx + 1][0] if idx + 1 < len(chapter_starts) else len(lines)
        text = "\n".join(lines[start_line + 1 : end_line]).strip()
        # Clean up markdown artifacts
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)  # bold
        text = re.sub(r"\*([^*]+)\*", r"\1", text)  # italic
        text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)  # headers
        text = re.sub(r"---+", "", text)  # horizontal rules
        text = re.sub(r"\n{3,}", "\n\n", text)  # excessive newlines
        word_count = len(text.split())
        chapters.append(Chapter(
            number=num, title=title, text=text,
            line_start=start_line, line_end=end_line,
            word_count=word_count,
        ))

    return chapters


def split_text_for_tts(text: str, max_chars: int = MAX_CHARS_PER_SEGMENT) -> List[str]:
    """Split text into TTS-friendly segments at sentence boundaries."""
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    segments = []
    current = ""

    for sentence in sentences:
        if not sentence.strip():
            continue
        if len(current) + len(sentence) + 1 > max_chars and current:
            segments.append(current.strip())
            current = sentence
        else:
            current = current + " " + sentence if current else sentence

    if current.strip():
        segments.append(current.strip())

    return segments


def generate_tts(text: str, output_path: Path, voice: str = VOICE, speed: float = SPEED) -> float:
    """Generate TTS audio for text, return duration in seconds."""
    from kokoro_onnx import Kokoro
    import numpy as np
    import soundfile as sf

    kokoro = Kokoro(str(MODEL_PATH), str(VOICES_PATH))
    segments = split_text_for_tts(text)

    all_samples = []
    sr = 24000

    for i, segment in enumerate(segments):
        if not segment.strip():
            continue
        try:
            samples, sr = kokoro.create(segment, voice=voice, speed=speed)
            all_samples.append(samples)
            # Add a small pause between segments (0.3s silence)
            all_samples.append(np.zeros(int(sr * 0.3), dtype=np.float32))
        except Exception as e:
            print(f"  Warning: TTS failed for segment {i}: {e}")
            continue

    if not all_samples:
        return 0.0

    combined = np.concatenate(all_samples)
    sf.write(str(output_path), combined, sr)
    duration = len(combined) / sr
    return duration


def create_title_card(chapter: Chapter, output_path: Path):
    """Create a title card image for the chapter."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Try to use a good font, fall back to default
    font_large = None
    font_medium = None
    font_small = None

    font_paths = [
        "C:/Windows/Fonts/georgia.ttf",
        "C:/Windows/Fonts/times.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]

    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font_large = ImageFont.truetype(fp, 72)
                font_medium = ImageFont.truetype(fp, 36)
                font_small = ImageFont.truetype(fp, 24)
                break
            except Exception:
                continue

    if font_large is None:
        font_large = ImageFont.load_default()
        font_medium = font_large
        font_small = font_large

    # Draw accent line at top
    draw.rectangle([(0, 0), (WIDTH, 6)], fill=ACCENT_COLOR)

    # Draw "THE SIX TONGUES PROTOCOL" subtitle
    subtitle = "THE SIX TONGUES PROTOCOL"
    bbox = draw.textbbox((0, 0), subtitle, font=font_small)
    sw = bbox[2] - bbox[0]
    draw.text(((WIDTH - sw) // 2, 200), subtitle, font=font_small, fill=ACCENT_COLOR)

    # Draw chapter number
    ch_text = f"Chapter {chapter.number}"
    bbox = draw.textbbox((0, 0), ch_text, font=font_large)
    cw = bbox[2] - bbox[0]
    draw.text(((WIDTH - cw) // 2, 320), ch_text, font=font_large, fill=TEXT_COLOR)

    # Draw chapter title
    title_wrapped = textwrap.fill(chapter.title, width=30)
    for i, line in enumerate(title_wrapped.split("\n")):
        bbox = draw.textbbox((0, 0), line, font=font_medium)
        tw = bbox[2] - bbox[0]
        draw.text(((WIDTH - tw) // 2, 440 + i * 50), line, font=font_medium, fill=MUTED_COLOR)

    # Draw word count at bottom
    wc_text = f"{chapter.word_count:,} words"
    bbox = draw.textbbox((0, 0), wc_text, font=font_small)
    ww = bbox[2] - bbox[0]
    draw.text(((WIDTH - ww) // 2, HEIGHT - 120), wc_text, font=font_small, fill=MUTED_COLOR)

    # Draw accent line at bottom
    draw.rectangle([(0, HEIGHT - 6), (WIDTH, HEIGHT)], fill=ACCENT_COLOR)

    img.save(str(output_path), quality=95)


def create_video(
    title_card_path: Path,
    audio_path: Path,
    output_path: Path,
    duration: float,
) -> bool:
    """Combine title card + audio into an MP4 video."""
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(title_card_path),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-t", str(duration + 1),  # pad 1s
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def process_chapter(chapter: Chapter, dry_run: bool = False) -> dict:
    """Process a single chapter into a video."""
    ch_dir = OUTPUT_DIR / f"ch{chapter.number:02d}"
    ch_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "chapter": chapter.number,
        "title": chapter.title,
        "words": chapter.word_count,
        "segments": len(split_text_for_tts(chapter.text)),
    }

    if dry_run:
        # Estimate duration: ~150 words per minute at 0.92 speed
        est_duration = chapter.word_count / 150 * (1 / SPEED)
        result["estimated_duration_min"] = round(est_duration, 1)
        result["status"] = "dry_run"
        return result

    # Step 1: Title card
    card_path = ch_dir / "title_card.png"
    print(f"  Creating title card...")
    create_title_card(chapter, card_path)
    result["title_card"] = str(card_path)

    # Step 2: TTS audio
    audio_path = ch_dir / "narration.wav"
    print(f"  Generating TTS audio ({chapter.word_count} words, {result['segments']} segments)...")
    duration = generate_tts(chapter.text, audio_path)
    result["audio_duration_s"] = round(duration, 1)
    result["audio_duration_min"] = round(duration / 60, 1)
    result["audio_path"] = str(audio_path)

    if duration == 0:
        result["status"] = "tts_failed"
        return result

    # Step 3: Video composite
    video_path = ch_dir / f"chapter_{chapter.number:02d}.mp4"
    print(f"  Compositing video ({duration:.0f}s)...")
    success = create_video(card_path, audio_path, video_path, duration)

    if success:
        result["video_path"] = str(video_path)
        result["video_size_mb"] = round(os.path.getsize(str(video_path)) / (1024 * 1024), 1)
        result["status"] = "complete"
    else:
        result["status"] = "ffmpeg_failed"

    return result


def main():
    parser = argparse.ArgumentParser(description="Chapter Video Pipeline")
    parser.add_argument("--chapter", type=int, help="Process specific chapter number")
    parser.add_argument("--all", action="store_true", help="Process all chapters")
    parser.add_argument("--list", action="store_true", help="List all chapters")
    parser.add_argument("--dry-run", action="store_true", help="Preview without generating")
    parser.add_argument("--voice", default=VOICE, help=f"TTS voice (default: {VOICE})")
    parser.add_argument("--speed", type=float, default=SPEED, help=f"TTS speed (default: {SPEED})")
    args = parser.parse_args()

    if not BOOK_PATH.exists():
        print(f"Book not found: {BOOK_PATH}")
        sys.exit(1)

    chapters = parse_chapters(BOOK_PATH)
    print(f"Found {len(chapters)} chapters ({sum(c.word_count for c in chapters):,} total words)")

    if args.list:
        for ch in chapters:
            print(f"  Ch {ch.number:2d}: {ch.title} ({ch.word_count:,} words)")
        return

    if args.chapter:
        targets = [ch for ch in chapters if ch.number == args.chapter]
        if not targets:
            print(f"Chapter {args.chapter} not found")
            sys.exit(1)
    elif args.all:
        targets = chapters
    else:
        parser.print_help()
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    for ch in targets:
        print(f"\n{'=' * 60}")
        print(f"  Chapter {ch.number}: {ch.title}")
        print(f"{'=' * 60}")
        result = process_chapter(ch, dry_run=args.dry_run)
        results.append(result)
        print(f"  Status: {result['status']}")
        if "audio_duration_min" in result:
            print(f"  Duration: {result['audio_duration_min']} min")
        if "video_size_mb" in result:
            print(f"  Size: {result['video_size_mb']} MB")

    # Save manifest
    manifest_path = OUTPUT_DIR / "pipeline_manifest.json"
    manifest_path.write_text(json.dumps(results, indent=2))
    print(f"\nManifest saved: {manifest_path}")

    # Summary
    total_duration = sum(r.get("audio_duration_min", 0) for r in results)
    total_size = sum(r.get("video_size_mb", 0) for r in results)
    complete = sum(1 for r in results if r.get("status") == "complete")
    print(f"\nSummary: {complete}/{len(results)} complete, {total_duration:.1f} min total, {total_size:.1f} MB")


if __name__ == "__main__":
    main()
