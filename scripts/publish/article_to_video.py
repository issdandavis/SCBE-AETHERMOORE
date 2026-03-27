#!/usr/bin/env python3
"""
Convert a markdown article into a narrated faceless YouTube video.

Pipeline:
  1. Parse markdown: strip frontmatter, extract code blocks, split into segments
  2. TTS audio: generate narration per segment via edge-tts (Microsoft Edge TTS)
  3. Visual slides: generate title/content/code/outro frames via Pillow + Pygments
  4. Compose video: combine slides + audio into MP4 via FFmpeg (H.264/AAC)

Usage:
    python scripts/publish/article_to_video.py --file content/articles/my-article.md
    python scripts/publish/article_to_video.py --file article.md --voice en-US-AriaNeural
    python scripts/publish/article_to_video.py --file article.md --dry-run
    python scripts/publish/article_to_video.py --file article.md --thumbnail-only
    python scripts/publish/article_to_video.py --file article.md --no-tts

Requirements:
    pip install edge-tts Pillow pygments

Environment:
    FFmpeg must be on PATH for final video composition.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "artifacts" / "youtube"
EVIDENCE_DIR = REPO_ROOT / "artifacts" / "publish_browser"

DEFAULT_VOICE = "kokoro:am_adam"  # Kokoro local TTS (near-ElevenLabs quality)
KOKORO_MODEL = REPO_ROOT / "kokoro-v1.0.onnx"
KOKORO_VOICES = REPO_ROOT / "voices-v1.0.bin"
_KOKORO_INSTANCE = None  # lazy singleton
RESOLUTION = (1920, 1080)
FPS = 1  # 1 frame per second; each slide held for its TTS duration
PAUSE_BETWEEN_SEGMENTS_S = 0.8
SEGMENT_TARGET_SECONDS = 30
WORDS_PER_SECOND = 2.6  # average narration speed estimate

# Branding
AUTHOR_NAME = "Issac Daniel Davis"
BRAND_NAME = "SCBE-AETHERMOORE"
GITHUB_URL = "github.com/issdandavis/SCBE-AETHERMOORE"
SUBSCRIBE_TEXT = "Subscribe for more"

# Colors (dark theme)
BG_COLOR = (18, 18, 24)
TEXT_COLOR = (230, 230, 240)
ACCENT_COLOR = (100, 140, 255)
CODE_BG_COLOR = (30, 30, 42)
MUTED_COLOR = (140, 140, 160)


def _safe_console(text: str) -> str:
    """Return text safe for the current console encoding (notably Windows cp1252)."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        text.encode(encoding)
        return text
    except UnicodeEncodeError:
        return text.encode(encoding, errors="replace").decode(encoding, errors="replace")


# ---------------------------------------------------------------------------
# Markdown parsing
# ---------------------------------------------------------------------------

def _strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter delimited by ---."""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3:].strip()
    return text.strip()


def _extract_code_blocks(text: str) -> tuple[str, list[dict]]:
    """Extract fenced code blocks, replace with placeholders, return both."""
    blocks: list[dict] = []
    counter = [0]

    def _replacer(m):
        lang = (m.group(1) or "").strip()
        code = m.group(2).strip()
        idx = counter[0]
        counter[0] += 1
        blocks.append({"index": idx, "lang": lang, "code": code})
        return f"\n[CODE_BLOCK_{idx}]\n"

    cleaned = re.sub(r"```(\w*)\n([\s\S]*?)```", _replacer, text)
    return cleaned, blocks


def _extract_title(text: str) -> str:
    """Extract the first H1 heading as the article title."""
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    # Fallback: first non-empty line
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("---"):
            return line
    return "Untitled"


def _clean_for_tts(text: str) -> str:
    """Clean text for TTS: expand abbreviations, strip markdown artifacts."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)  # bold
    text = re.sub(r"\*(.+?)\*", r"\1", text)  # italic
    text = re.sub(r"`(.+?)`", r"\1", text)  # inline code
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # links
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)  # headings
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)  # blockquotes
    text = re.sub(r"^---+\s*$", "", text, flags=re.MULTILINE)  # horizontal rules
    text = re.sub(r"^[-*]\s+", "", text, flags=re.MULTILINE)  # bullets
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)  # numbered lists
    text = re.sub(r"\[CODE_BLOCK_\d+\]", "", text)  # code placeholders
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)  # images

    # Common abbreviations
    abbrevs = {
        "e.g.": "for example",
        "i.e.": "that is",
        "etc.": "et cetera",
        "vs.": "versus",
        "API": "A P I",
        "CLI": "C L I",
        "URL": "U R L",
        "TTS": "text to speech",
        "FFT": "F F T",
        "PQC": "post quantum cryptography",
        "ML": "machine learning",
        "AI": "A I",
        "HF": "Hugging Face",
    }
    for abbr, expansion in abbrevs.items():
        text = text.replace(abbr, expansion)

    text = re.sub(r"\s+", " ", text).strip()
    return text


def _split_into_segments(
    text: str,
    code_blocks: list[dict],
    target_seconds: float = SEGMENT_TARGET_SECONDS,
    words_per_second: float = WORDS_PER_SECOND,
) -> list[dict]:
    """Split article into narration segments, each roughly target_seconds long."""
    segments: list[dict] = []
    # Split by headings and code block placeholders
    parts = re.split(r"((?:^|\n)##?\s+.+\n|\[CODE_BLOCK_\d+\])", text)

    current_text = ""
    current_display_lines: list[str] = []

    def _flush():
        nonlocal current_text, current_display_lines
        if current_text.strip():
            narration = _clean_for_tts(current_text)
            if narration.strip():
                segments.append({
                    "type": "content",
                    "narration": narration,
                    "display_lines": current_display_lines[:] if current_display_lines else [narration[:200]],
                })
        current_text = ""
        current_display_lines = []

    for part in parts:
        part_stripped = part.strip()
        if not part_stripped:
            continue

        # Code block placeholder
        code_match = re.match(r"\[CODE_BLOCK_(\d+)\]", part_stripped)
        if code_match:
            _flush()
            idx = int(code_match.group(1))
            block = next((b for b in code_blocks if b["index"] == idx), None)
            if block:
                narration = f"Here is a code example. {block['lang']} code." if block["lang"] else "Here is a code example."
                segments.append({
                    "type": "code",
                    "narration": narration,
                    "code": block["code"],
                    "lang": block["lang"],
                })
            continue

        # Heading
        heading_match = re.match(r"^##?\s+(.+)$", part_stripped)
        if heading_match:
            _flush()
            heading = heading_match.group(1).strip()
            current_display_lines.append(heading)
            current_text += f"{heading}. "
            continue

        # Regular text: accumulate until we hit target duration
        target_words = max(1, int(target_seconds * words_per_second))
        sentences = re.split(r"(?<=[.!?])\s+", part_stripped)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_words = sentence.split()
            projected = len(current_text.split()) + len(sentence_words)
            if current_text.strip() and projected > target_words:
                _flush()

            current_text += sentence + " "

            if len(sentence) > 5:
                # Clean markdown for display
                display = re.sub(r"\*\*(.+?)\*\*", r"\1", sentence)
                display = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"\1", display)  # *italic*
                display = re.sub(r"`(.+?)`", r"\1", display)
                display = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", display)  # links
                display = re.sub(r"^>\s*", "", display)  # blockquote markers
                display = re.sub(r"^#{1,3}\s+", "", display)  # heading markers
                display = re.sub(r"^---+\s*$", "", display)  # horizontal rules
                display = display.strip()
                if not display:
                    continue
                # Wrap long lines rather than truncating mid-word
                if len(display) > 100:
                    wrapped = textwrap.fill(display, width=100)
                    for wl in wrapped.splitlines():
                        current_display_lines.append(wl.strip())
                else:
                    current_display_lines.append(display)

            if len(current_text.split()) >= target_words:
                _flush()

    _flush()
    return segments


def parse_article(
    filepath: Path,
    target_seconds: float = SEGMENT_TARGET_SECONDS,
    words_per_second: float = WORDS_PER_SECOND,
) -> dict:
    """Parse a markdown article into structured segments."""
    raw = filepath.read_text(encoding="utf-8", errors="replace")
    text = _strip_frontmatter(raw)
    title = _extract_title(text)
    text_no_code, code_blocks = _extract_code_blocks(text)
    segments = _split_into_segments(
        text_no_code,
        code_blocks,
        target_seconds=target_seconds,
        words_per_second=words_per_second,
    )
    return {
        "title": title,
        "source_file": str(filepath),
        "code_blocks": code_blocks,
        "segments": segments,
    }


# ---------------------------------------------------------------------------
# TTS audio generation (edge-tts)
# ---------------------------------------------------------------------------

def _get_kokoro():
    """Lazy-load Kokoro TTS model (singleton)."""
    global _KOKORO_INSTANCE
    if _KOKORO_INSTANCE is None:
        from kokoro_onnx import Kokoro
        _KOKORO_INSTANCE = Kokoro(str(KOKORO_MODEL), str(KOKORO_VOICES))
    return _KOKORO_INSTANCE


async def _generate_tts_segment(
    text: str,
    voice: str,
    output_path: Path,
    edge_rate: str = "+0%",
    edge_pitch: str = "+0Hz",
    edge_volume: str = "+0%",
    kokoro_speed: float = 1.0,
) -> float:
    """Generate TTS audio for a single segment, return duration in seconds."""
    if voice.startswith("kokoro:"):
        # Use Kokoro local TTS
        kokoro_voice = voice.split(":", 1)[1]
        try:
            import soundfile as sf
            kokoro = _get_kokoro()
            samples, sr = kokoro.create(text, voice=kokoro_voice, speed=kokoro_speed)
            sf.write(str(output_path), samples, sr)
        except ImportError:
            print("ERROR: kokoro-onnx or soundfile not installed. Run: pip install kokoro-onnx soundfile")
            sys.exit(1)
        except Exception as e:
            print(f"  Kokoro error, falling back to edge-tts: {e}")
            import edge_tts
            communicate = edge_tts.Communicate(
                text,
                "en-US-AndrewMultilingualNeural",
                rate=edge_rate,
                pitch=edge_pitch,
                volume=edge_volume,
            )
            await communicate.save(str(output_path))
    else:
        # Use edge-tts (cloud)
        try:
            import edge_tts
        except ImportError:
            print("ERROR: edge-tts not installed. Run: pip install edge-tts")
            sys.exit(1)
        communicate = edge_tts.Communicate(
            text,
            voice,
            rate=edge_rate,
            pitch=edge_pitch,
            volume=edge_volume,
        )
        await communicate.save(str(output_path))

    # Get duration via ffprobe if available
    duration = _get_audio_duration(output_path)
    if duration <= 0:
        # Estimate from word count
        duration = max(2.0, len(text.split()) / WORDS_PER_SECOND)
    return duration


def _get_audio_duration(audio_path: Path) -> float:
    """Get audio duration in seconds via ffprobe."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return 0.0
    try:
        result = subprocess.run(
            [
                ffprobe, "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path),
            ],
            capture_output=True, text=True, timeout=10,
        )
        return float(result.stdout.strip()) if result.returncode == 0 else 0.0
    except Exception:
        return 0.0


async def generate_all_tts(
    segments: list[dict],
    voice: str,
    work_dir: Path,
    edge_rate: str = "+0%",
    edge_pitch: str = "+0Hz",
    edge_volume: str = "+0%",
    kokoro_speed: float = 1.0,
) -> list[dict]:
    """Generate TTS audio for all segments, return updated segments with paths and durations."""
    audio_dir = work_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    for i, seg in enumerate(segments):
        narration = seg.get("narration", "")
        if not narration.strip():
            seg["audio_path"] = None
            seg["duration"] = 2.0
            continue

        ext = "wav" if voice.startswith("kokoro:") else "mp3"
        audio_path = audio_dir / f"segment_{i:03d}.{ext}"
        print(_safe_console(f"  TTS segment {i + 1}/{len(segments)}: {narration[:60]}..."))
        duration = await _generate_tts_segment(
            narration,
            voice,
            audio_path,
            edge_rate=edge_rate,
            edge_pitch=edge_pitch,
            edge_volume=edge_volume,
            kokoro_speed=kokoro_speed,
        )
        seg["audio_path"] = str(audio_path)
        seg["duration"] = duration

    return segments


def concatenate_audio(segments: list[dict], work_dir: Path) -> Path:
    """Concatenate segment audio files with pauses into a single audio track."""
    concat_list = work_dir / "audio_concat.txt"

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("ERROR: FFmpeg not found on PATH.")
        sys.exit(1)

    # Detect if segments are WAV (Kokoro) or MP3 (edge-tts)
    is_wav = any(
        seg.get("audio_path", "").endswith(".wav")
        for seg in segments
        if seg.get("audio_path")
    )
    ext = "wav" if is_wav else "mp3"
    silence_path = work_dir / f"silence.{ext}"

    # Generate silence matching the segment format
    if is_wav:
        subprocess.run(
            [
                ffmpeg, "-y", "-f", "lavfi", "-i",
                "anullsrc=r=24000:cl=mono",
                "-t", str(PAUSE_BETWEEN_SEGMENTS_S),
                "-c:a", "pcm_s16le", str(silence_path),
            ],
            capture_output=True, timeout=10,
        )
    else:
        subprocess.run(
            [
                ffmpeg, "-y", "-f", "lavfi", "-i",
                "anullsrc=r=44100:cl=mono",
                "-t", str(PAUSE_BETWEEN_SEGMENTS_S),
                "-q:a", "9", str(silence_path),
            ],
            capture_output=True, timeout=10,
        )

    lines: list[str] = []
    for seg in segments:
        audio = seg.get("audio_path")
        if audio and Path(audio).exists():
            lines.append(f"file '{audio}'")
            lines.append(f"file '{silence_path}'")

    if not lines:
        return silence_path

    concat_list.write_text("\n".join(lines), encoding="utf-8")

    # Re-encode to WAV to ensure consistent format before video mux
    output = work_dir / "full_audio.wav"
    subprocess.run(
        [
            ffmpeg, "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c:a", "pcm_s16le", "-ar", "24000", "-ac", "1",
            str(output),
        ],
        capture_output=True, timeout=120,
    )
    return output


# ---------------------------------------------------------------------------
# Visual slide generation (Pillow)
# ---------------------------------------------------------------------------

def _get_font(size: int, bold: bool = False):
    """Get a TrueType font, falling back to default if needed."""
    from PIL import ImageFont

    # Try common system fonts
    font_names = []
    if bold:
        font_names = [
            "arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf",
            "LiberationSans-Bold.ttf", "calibrib.ttf",
        ]
    else:
        font_names = [
            "arial.ttf", "Arial.ttf", "DejaVuSans.ttf",
            "LiberationSans-Regular.ttf", "calibri.ttf",
        ]

    for name in font_names:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue

    # Try Windows font directory
    win_fonts = Path("C:/Windows/Fonts")
    if win_fonts.exists():
        for name in font_names:
            try:
                return ImageFont.truetype(str(win_fonts / name), size)
            except (OSError, IOError):
                continue

    # Fallback to default
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


def _get_mono_font(size: int):
    """Get a monospace font for code slides."""
    from PIL import ImageFont

    mono_names = [
        "consola.ttf", "Consolas.ttf", "DejaVuSansMono.ttf",
        "LiberationMono-Regular.ttf", "cour.ttf", "Courier New.ttf",
    ]
    win_fonts = Path("C:/Windows/Fonts")
    for name in mono_names:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            pass
        if win_fonts.exists():
            try:
                return ImageFont.truetype(str(win_fonts / name), size)
            except (OSError, IOError):
                pass
    return _get_font(size)


def generate_title_slide(title: str, output_path: Path) -> None:
    """Generate the title card slide."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", RESOLUTION, BG_COLOR)
    draw = ImageDraw.Draw(img)

    title_font = _get_font(64, bold=True)
    author_font = _get_font(36)
    brand_font = _get_font(28)

    # Title (centered, wrapped)
    wrapped = textwrap.fill(title, width=40)
    lines = wrapped.splitlines()
    total_height = len(lines) * 80
    y_start = (RESOLUTION[1] // 2) - total_height // 2 - 60

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        w = bbox[2] - bbox[0]
        x = (RESOLUTION[0] - w) // 2
        draw.text((x, y_start + i * 80), line, fill=TEXT_COLOR, font=title_font)

    # Accent line
    line_y = y_start + len(lines) * 80 + 20
    draw.rectangle(
        [(RESOLUTION[0] // 2 - 200, line_y), (RESOLUTION[0] // 2 + 200, line_y + 4)],
        fill=ACCENT_COLOR,
    )

    # Author
    author_text = AUTHOR_NAME
    bbox = draw.textbbox((0, 0), author_text, font=author_font)
    w = bbox[2] - bbox[0]
    draw.text(((RESOLUTION[0] - w) // 2, line_y + 30), author_text, fill=MUTED_COLOR, font=author_font)

    # Brand
    bbox = draw.textbbox((0, 0), BRAND_NAME, font=brand_font)
    w = bbox[2] - bbox[0]
    draw.text(((RESOLUTION[0] - w) // 2, line_y + 80), BRAND_NAME, fill=ACCENT_COLOR, font=brand_font)

    img.save(str(output_path), "PNG")


def _draw_generated_background(draw, width: int, height: int, style: str, seed: int) -> None:
    """Draw deterministic abstract backgrounds for improved visual richness."""
    rng = random.Random(seed)

    if style == "standard":
        return

    # Vertical gradient base
    top = (14, 18, 34)
    bottom = (34, 18, 46)
    if style == "cymatic":
        top = (10, 14, 30)
        bottom = (36, 20, 56)
    if style == "cinematic":
        top = (22, 14, 28)
        bottom = (14, 22, 40)

    for y in range(height):
        t = y / max(1, height - 1)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Add soft circles / wave motifs
    shape_count = 16 if style == "cinematic" else 22
    for _ in range(shape_count):
        x = rng.randint(-200, width + 200)
        y = rng.randint(-200, height + 200)
        radius = rng.randint(60, 360)
        alpha = rng.randint(24, 64)
        color = (
            rng.randint(40, 140),
            rng.randint(60, 170),
            rng.randint(120, 230),
            alpha,
        )
        draw.ellipse(
            [(x - radius, y - radius), (x + radius, y + radius)],
            outline=color,
            width=rng.randint(1, 3),
        )

    if style == "cymatic":
        center_x = width // 2
        center_y = int(height * 0.58)
        for i in range(24):
            radius = int((i + 1) * min(width, height) * 0.018)
            color = (70 + i * 2, 120 + i, 220, 45)
            draw.arc(
                [(center_x - radius, center_y - radius), (center_x + radius, center_y + radius)],
                start=0,
                end=360,
                fill=color,
                width=1,
            )


def generate_content_slide(
    display_lines: list[str],
    slide_number: int,
    output_path: Path,
    visual_style: str = "standard",
    panel_opacity: int = 196,
    bg_image_path: Path | None = None,
) -> None:
    """Generate a content slide with bullet points."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", RESOLUTION, BG_COLOR + (255,))
    draw = ImageDraw.Draw(img, "RGBA")

    heading_font = _get_font(44, bold=True)
    body_font = _get_font(32)
    number_font = _get_font(24)

    if bg_image_path and bg_image_path.exists():
        bg = Image.open(bg_image_path).convert("RGBA").resize(RESOLUTION)
        img.alpha_composite(bg)
    else:
        _draw_generated_background(draw, RESOLUTION[0], RESOLUTION[1], visual_style, seed=slide_number)

    # Slide number (top right)
    draw.text((RESOLUTION[0] - 100, 30), f"{slide_number}", fill=MUTED_COLOR, font=number_font)

    # Accent bar (left side)
    draw.rectangle([(80, 80), (86, RESOLUTION[1] - 80)], fill=ACCENT_COLOR)

    # Content panel for readability
    panel = (110, 78, RESOLUTION[0] - 86, RESOLUTION[1] - 80)
    panel_fill = (14, 16, 24, max(40, min(255, panel_opacity)))
    draw.rounded_rectangle(panel, radius=24, fill=panel_fill)

    # Content lines
    y = 100
    max_lines = 12
    for i, line in enumerate(display_lines[:max_lines]):
        line = line.strip()
        if not line:
            continue

        # First line as heading style
        if i == 0 and len(display_lines) > 1:
            wrapped = textwrap.fill(line, width=50)
            for wline in wrapped.splitlines()[:3]:
                draw.text((120, y), wline, fill=TEXT_COLOR, font=heading_font)
                y += 60
            y += 20
        else:
            # Bullet point with dot prefix
            wrapped = textwrap.fill(line, width=60)
            for j, wline in enumerate(wrapped.splitlines()[:3]):
                prefix = "    " if j > 0 else "  - "
                color = TEXT_COLOR if j == 0 else MUTED_COLOR
                draw.text((120, y), prefix + wline, fill=color, font=body_font)
                y += 42
            y += 12

        if y > RESOLUTION[1] - 100:
            break

    img.convert("RGB").save(str(output_path), "PNG")


def generate_code_slide(code: str, lang: str, output_path: Path) -> None:
    """Generate a code slide with syntax highlighting via Pygments."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", RESOLUTION, BG_COLOR)
    draw = ImageDraw.Draw(img)

    label_font = _get_font(28, bold=True)
    code_font = _get_mono_font(22)

    # Language label
    lang_label = lang.upper() if lang else "CODE"
    draw.text((80, 40), lang_label, fill=ACCENT_COLOR, font=label_font)

    # Code background panel
    panel_margin = 60
    panel_top = 90
    panel_bottom = RESOLUTION[1] - 60
    draw.rectangle(
        [(panel_margin, panel_top), (RESOLUTION[0] - panel_margin, panel_bottom)],
        fill=CODE_BG_COLOR,
    )

    # Try syntax highlighting with Pygments
    highlighted_lines = _highlight_code(code, lang)

    y = panel_top + 20
    x = panel_margin + 30
    max_code_lines = 28
    for i, (line_text, line_color) in enumerate(highlighted_lines[:max_code_lines]):
        if y > panel_bottom - 30:
            draw.text((x, y), "...", fill=MUTED_COLOR, font=code_font)
            break
        # Truncate long lines
        if len(line_text) > 85:
            line_text = line_text[:82] + "..."
        draw.text((x, y), line_text, fill=line_color, font=code_font)
        y += 30

    img.save(str(output_path), "PNG")


def _highlight_code(code: str, lang: str) -> list[tuple[str, tuple[int, int, int]]]:
    """Return list of (line_text, color) tuples. Uses Pygments if available."""
    lines = code.splitlines()
    default_color = (200, 200, 220)

    try:
        from pygments import highlight as pyg_highlight
        from pygments.lexers import get_lexer_by_name, TextLexer
        from pygments.token import Token

        try:
            lexer = get_lexer_by_name(lang) if lang else TextLexer()
        except Exception:
            lexer = TextLexer()

        # Map Pygments token types to colors
        color_map = {
            Token.Keyword: (198, 120, 221),
            Token.Name.Function: (97, 175, 239),
            Token.Name.Class: (229, 192, 123),
            Token.String: (152, 195, 121),
            Token.Comment: (92, 99, 112),
            Token.Number: (209, 154, 102),
            Token.Operator: (86, 182, 194),
            Token.Punctuation: (171, 178, 191),
        }

        # Simple per-line coloring based on dominant token
        result: list[tuple[str, tuple[int, int, int]]] = []
        for line in lines:
            tokens = list(lexer.get_tokens(line))
            if not tokens:
                result.append((line, default_color))
                continue
            # Pick color of first significant token
            color = default_color
            for ttype, value in tokens:
                if value.strip():
                    for mapped_type, mapped_color in color_map.items():
                        if ttype in mapped_type or ttype is mapped_type:
                            color = mapped_color
                            break
                    break
            result.append((line, color))
        return result

    except ImportError:
        return [(line, default_color) for line in lines]


def generate_outro_slide(output_path: Path) -> None:
    """Generate the outro/subscribe card."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", RESOLUTION, BG_COLOR)
    draw = ImageDraw.Draw(img)

    big_font = _get_font(56, bold=True)
    medium_font = _get_font(36)
    small_font = _get_font(28)

    # Subscribe text
    bbox = draw.textbbox((0, 0), SUBSCRIBE_TEXT, font=big_font)
    w = bbox[2] - bbox[0]
    draw.text(((RESOLUTION[0] - w) // 2, 300), SUBSCRIBE_TEXT, fill=ACCENT_COLOR, font=big_font)

    # Author
    bbox = draw.textbbox((0, 0), AUTHOR_NAME, font=medium_font)
    w = bbox[2] - bbox[0]
    draw.text(((RESOLUTION[0] - w) // 2, 420), AUTHOR_NAME, fill=TEXT_COLOR, font=medium_font)

    # GitHub URL
    bbox = draw.textbbox((0, 0), GITHUB_URL, font=small_font)
    w = bbox[2] - bbox[0]
    draw.text(((RESOLUTION[0] - w) // 2, 500), GITHUB_URL, fill=MUTED_COLOR, font=small_font)

    # Brand
    bbox = draw.textbbox((0, 0), BRAND_NAME, font=small_font)
    w = bbox[2] - bbox[0]
    draw.text(((RESOLUTION[0] - w) // 2, 570), BRAND_NAME, fill=ACCENT_COLOR, font=small_font)

    # Accent line
    draw.rectangle(
        [(RESOLUTION[0] // 2 - 300, 640), (RESOLUTION[0] // 2 + 300, 644)],
        fill=ACCENT_COLOR,
    )

    # Social links
    links = [
        f"GitHub: {GITHUB_URL}",
        "HuggingFace: huggingface.co/issdandavis",
    ]
    y = 680
    for link in links:
        bbox = draw.textbbox((0, 0), link, font=small_font)
        w = bbox[2] - bbox[0]
        draw.text(((RESOLUTION[0] - w) // 2, y), link, fill=MUTED_COLOR, font=small_font)
        y += 50

    img.save(str(output_path), "PNG")


def generate_thumbnail(title: str, output_path: Path) -> None:
    """Generate a YouTube thumbnail (1280x720)."""
    from PIL import Image, ImageDraw

    thumb_size = (1280, 720)
    img = Image.new("RGB", thumb_size, BG_COLOR)
    draw = ImageDraw.Draw(img)

    title_font = _get_font(72, bold=True)
    brand_font = _get_font(36, bold=True)

    # Accent gradient bar (top)
    for i in range(8):
        draw.rectangle([(0, i), (thumb_size[0], i + 1)], fill=ACCENT_COLOR)

    # Title text (centered, wrapped)
    wrapped = textwrap.fill(title, width=25)
    lines = wrapped.splitlines()[:4]
    total_height = len(lines) * 90
    y_start = (thumb_size[1] // 2) - total_height // 2 - 20

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        w = bbox[2] - bbox[0]
        x = (thumb_size[0] - w) // 2
        # Text shadow
        draw.text((x + 3, y_start + i * 90 + 3), line, fill=(0, 0, 0), font=title_font)
        draw.text((x, y_start + i * 90), line, fill=TEXT_COLOR, font=title_font)

    # Brand bar at bottom
    bar_y = thumb_size[1] - 70
    draw.rectangle([(0, bar_y), (thumb_size[0], thumb_size[1])], fill=ACCENT_COLOR)
    bbox = draw.textbbox((0, 0), BRAND_NAME, font=brand_font)
    w = bbox[2] - bbox[0]
    draw.text(((thumb_size[0] - w) // 2, bar_y + 15), BRAND_NAME, fill=(255, 255, 255), font=brand_font)

    img.save(str(output_path), "PNG")


def _list_background_images(bg_images_dir: str) -> list[Path]:
    if not bg_images_dir:
        return []
    root = Path(bg_images_dir)
    if not root.exists() or not root.is_dir():
        return []
    files = []
    for pattern in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
        files.extend(sorted(root.glob(pattern)))
    return files


def generate_all_slides(
    parsed: dict,
    work_dir: Path,
    visual_style: str = "standard",
    panel_opacity: int = 196,
    bg_images_dir: str = "",
) -> list[dict]:
    """Generate all slide images, return list of slide info dicts."""
    slides_dir = work_dir / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)

    slides: list[dict] = []
    slide_idx = 0

    # Title slide
    title_path = slides_dir / f"slide_{slide_idx:03d}.png"
    generate_title_slide(parsed["title"], title_path)
    slides.append({"path": str(title_path), "type": "title", "segment_index": -1})
    slide_idx += 1

    bg_images = _list_background_images(bg_images_dir)

    # Content and code slides
    for seg_i, seg in enumerate(parsed["segments"]):
        slide_path = slides_dir / f"slide_{slide_idx:03d}.png"

        if seg["type"] == "code":
            generate_code_slide(seg.get("code", ""), seg.get("lang", ""), slide_path)
        else:
            display = seg.get("display_lines", [""])
            bg_image = None
            if bg_images:
                bg_image = bg_images[seg_i % len(bg_images)]
            generate_content_slide(
                display,
                slide_idx,
                slide_path,
                visual_style=visual_style,
                panel_opacity=panel_opacity,
                bg_image_path=bg_image,
            )

        slides.append({"path": str(slide_path), "type": seg["type"], "segment_index": seg_i})
        slide_idx += 1

    # Outro slide
    outro_path = slides_dir / f"slide_{slide_idx:03d}.png"
    generate_outro_slide(outro_path)
    slides.append({"path": str(outro_path), "type": "outro", "segment_index": -1})

    return slides


# ---------------------------------------------------------------------------
# Video composition (FFmpeg)
# ---------------------------------------------------------------------------

def compose_video(slides: list[dict], segments: list[dict], audio_path: Path, output_path: Path) -> bool:
    """Compose final video from slides + audio using FFmpeg."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("ERROR: FFmpeg not found on PATH. Cannot compose video.")
        return False

    # Build a concat file with each slide held for its segment duration
    work_dir = Path(slides[0]["path"]).parent.parent
    concat_file = work_dir / "video_concat.txt"

    lines: list[str] = []
    for slide in slides:
        seg_idx = slide.get("segment_index", -1)
        if seg_idx >= 0 and seg_idx < len(segments):
            duration = segments[seg_idx].get("duration", 4.0)
        elif slide["type"] == "title":
            duration = 5.0
        elif slide["type"] == "outro":
            duration = 6.0
        else:
            duration = 4.0

        # FFmpeg concat demuxer format
        lines.append(f"file '{slide['path']}'")
        lines.append(f"duration {duration:.2f}")

    # Repeat last frame (FFmpeg concat requirement)
    if slides:
        lines.append(f"file '{slides[-1]['path']}'")

    concat_file.write_text("\n".join(lines), encoding="utf-8")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Compose: images + audio -> MP4
    cmd = [
        ffmpeg, "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
    ]

    if audio_path.exists() and audio_path.stat().st_size > 0:
        cmd.extend(["-i", str(audio_path)])
        cmd.extend([
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            "-r", "30",
            "-s", f"{RESOLUTION[0]}x{RESOLUTION[1]}",
            str(output_path),
        ])
    else:
        cmd.extend([
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-r", "30",
            "-s", f"{RESOLUTION[0]}x{RESOLUTION[1]}",
            str(output_path),
        ])

    print(f"  Composing video: {output_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        print(f"  FFmpeg error: {result.stderr[:500]}")
        return False

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  Video created: {output_path} ({size_mb:.1f} MB)")
    return True


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a markdown article into a narrated YouTube video.")
    parser.add_argument("--file", required=True, help="Path to the input markdown article")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help=f"TTS voice name (default: {DEFAULT_VOICE})")
    parser.add_argument("--output", default="", help="Output video path (default: artifacts/youtube/<filename>.mp4)")
    parser.add_argument("--segment-seconds", type=float, default=20.0, help="Target narration seconds per segment.")
    parser.add_argument("--words-per-second", type=float, default=WORDS_PER_SECOND, help="Words/sec estimate for segmentation.")
    parser.add_argument("--rate", default="-4%", help="edge-tts speaking rate (e.g. -8%%, +0%%, +6%%).")
    parser.add_argument("--pitch", default="+0Hz", help="edge-tts pitch (e.g. -10Hz, +0Hz, +12Hz).")
    parser.add_argument("--volume", default="+0%", help="edge-tts volume (e.g. -5%%, +0%%, +10%%).")
    parser.add_argument("--kokoro-speed", type=float, default=0.94, help="Kokoro speed scalar (0.8-1.2 typical).")
    parser.add_argument(
        "--visual-style",
        default="cymatic",
        choices=["standard", "cinematic", "cymatic"],
        help="Visual style for generated background imagery.",
    )
    parser.add_argument("--panel-opacity", type=int, default=196, help="Text panel opacity (0-255).")
    parser.add_argument("--bg-images-dir", default="", help="Optional folder of background images to cycle per segment.")
    parser.add_argument("--audio-track", default="", help="Optional external narration track (wav/mp3). Skips TTS.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be generated without creating files")
    parser.add_argument("--thumbnail-only", action="store_true", help="Only generate the thumbnail image")
    parser.add_argument("--no-tts", action="store_true", help="Skip TTS, generate slides only (for testing)")
    args = parser.parse_args()

    filepath = Path(args.file)
    if not filepath.is_absolute():
        filepath = REPO_ROOT / filepath
    if not filepath.exists():
        print(f"ERROR: File not found: {filepath}")
        return 1

    stem = filepath.stem
    output_path = Path(args.output) if args.output else OUTPUT_DIR / f"{stem}.mp4"
    if not output_path.is_absolute():
        output_path = REPO_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Parse article
    print(_safe_console(f"[article_to_video] Parsing: {filepath.name}"))
    parsed = parse_article(
        filepath,
        target_seconds=args.segment_seconds,
        words_per_second=args.words_per_second,
    )
    print(_safe_console(f"  Title: {parsed['title']}"))
    print(_safe_console(f"  Segments: {len(parsed['segments'])}"))
    print(_safe_console(f"  Code blocks: {len(parsed['code_blocks'])}"))

    if args.dry_run:
        print("\n[DRY RUN] Would generate:")
        print(_safe_console(f"  Voice: {args.voice}"))
        if args.audio_track:
            print(_safe_console(f"  External audio track: {args.audio_track}"))
        print(_safe_console(f"  Output: {output_path}"))
        print(_safe_console(f"  Thumbnail: {output_path.with_suffix('.thumb.png')}"))
        print(_safe_console(f"  Visual style: {args.visual_style}"))
        if args.bg_images_dir:
            print(_safe_console(f"  Background images: {args.bg_images_dir}"))
        for i, seg in enumerate(parsed["segments"]):
            est_dur = max(2.0, len(seg.get("narration", "").split()) / max(args.words_per_second, 0.1))
            print(_safe_console(f"  Segment {i + 1}: [{seg['type']}] ~{est_dur:.0f}s - {seg.get('narration', '')[:80]}..."))
        total_est = sum(max(2.0, len(s.get("narration", "").split()) / max(args.words_per_second, 0.1)) for s in parsed["segments"])
        print(_safe_console(f"\n  Estimated total duration: {total_est:.0f}s ({total_est / 60:.1f} min)"))

        # Write evidence
        _write_evidence(parsed, args, output_path, dry_run=True)
        return 0

    # Thumbnail
    thumb_path = output_path.with_suffix(".thumb.png")
    print(f"\n[article_to_video] Generating thumbnail...")
    generate_thumbnail(parsed["title"], thumb_path)
    print(f"  Thumbnail: {thumb_path}")

    if args.thumbnail_only:
        _write_evidence(parsed, args, output_path, dry_run=False, thumbnail_only=True)
        return 0

    # Work directory
    work_dir = Path(tempfile.mkdtemp(prefix="scbe_video_"))
    print(f"  Work dir: {work_dir}")

    try:
        # Generate slides
        print(f"\n[article_to_video] Generating slides...")
        slides = generate_all_slides(
            parsed,
            work_dir,
            visual_style=args.visual_style,
            panel_opacity=args.panel_opacity,
            bg_images_dir=args.bg_images_dir,
        )
        print(f"  Generated {len(slides)} slides")

        if args.no_tts:
            # No TTS: just generate slides, no video composition with audio
            print("\n[article_to_video] --no-tts: skipping TTS and video composition")
            # Copy slides to output dir
            slides_out = output_path.parent / f"{stem}_slides"
            slides_out.mkdir(parents=True, exist_ok=True)
            for slide in slides:
                src = Path(slide["path"])
                dst = slides_out / src.name
                shutil.copy2(src, dst)
            print(f"  Slides saved to: {slides_out}")
            _write_evidence(parsed, args, output_path, dry_run=False, no_tts=True)
            return 0

        if args.audio_track:
            ext_audio = Path(args.audio_track)
            if not ext_audio.is_absolute():
                ext_audio = (REPO_ROOT / ext_audio).resolve()
            if not ext_audio.exists():
                print(f"ERROR: External audio track not found: {ext_audio}")
                _write_evidence(parsed, args, output_path, dry_run=False, error="external audio track missing")
                return 1

            for seg in parsed["segments"]:
                seg["duration"] = max(2.0, len(seg.get("narration", "").split()) / max(args.words_per_second, 0.1))

            print(f"\n[article_to_video] Using external audio track: {ext_audio}")
            ok = compose_video(slides, parsed["segments"], ext_audio, output_path)
            if not ok:
                print("ERROR: Video composition failed with external audio.")
                _write_evidence(parsed, args, output_path, dry_run=False, error="ffmpeg composition failed")
                return 1

            _write_evidence(parsed, args, output_path, dry_run=False)
            print(f"\n[article_to_video] Done!")
            print(f"  Video: {output_path}")
            print(f"  Thumbnail: {thumb_path}")
            return 0

        # Generate TTS
        print(f"\n[article_to_video] Generating TTS audio (voice: {args.voice})...")
        segments = asyncio.run(
            generate_all_tts(
                parsed["segments"],
                args.voice,
                work_dir,
                edge_rate=args.rate,
                edge_pitch=args.pitch,
                edge_volume=args.volume,
                kokoro_speed=args.kokoro_speed,
            )
        )

        # Concatenate audio
        print(f"\n[article_to_video] Concatenating audio...")
        full_audio = concatenate_audio(segments, work_dir)
        print(f"  Full audio: {full_audio}")

        # Compose video
        print(f"\n[article_to_video] Composing video...")
        ok = compose_video(slides, segments, full_audio, output_path)
        if not ok:
            print("ERROR: Video composition failed.")
            _write_evidence(parsed, args, output_path, dry_run=False, error="ffmpeg composition failed")
            return 1

        _write_evidence(parsed, args, output_path, dry_run=False)
        print(f"\n[article_to_video] Done!")
        print(f"  Video: {output_path}")
        print(f"  Thumbnail: {thumb_path}")
        return 0

    finally:
        # Clean up work dir
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass


def _write_evidence(
    parsed: dict,
    args: argparse.Namespace,
    output_path: Path,
    dry_run: bool = False,
    thumbnail_only: bool = False,
    no_tts: bool = False,
    error: str = "",
) -> None:
    """Write evidence JSON to artifacts/publish_browser/."""
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    status = "dry_run_ready" if dry_run else "error" if error else "generated"
    if thumbnail_only:
        status = "thumbnail_only"
    if no_tts:
        status = "slides_only"

    evidence = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "platform": "youtube_video",
        "source_file": str(args.file),
        "output": str(output_path),
        "voice": args.voice,
        "audio_track": args.audio_track,
        "visual_style": args.visual_style,
        "bg_images_dir": args.bg_images_dir,
        "segment_seconds": args.segment_seconds,
        "words_per_second": args.words_per_second,
        "rate": args.rate,
        "pitch": args.pitch,
        "volume": args.volume,
        "kokoro_speed": args.kokoro_speed,
        "title": parsed["title"],
        "segment_count": len(parsed["segments"]),
        "code_block_count": len(parsed["code_blocks"]),
        "status": status,
        "error": error,
    }
    evidence_path = EVIDENCE_DIR / f"youtube_video_{run_id}.json"
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"  Evidence: {evidence_path}")


if __name__ == "__main__":
    raise SystemExit(main())
