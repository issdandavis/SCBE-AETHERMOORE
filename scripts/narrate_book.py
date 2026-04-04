"""
Book Narration Pipeline
========================

Narrate The Six Tongues Protocol chapters using Kokoro TTS.
Outputs WAV files per chapter, ready for YouTube upload or audiobook assembly.

Usage:
    python scripts/narrate_book.py                    # All unnarrated chapters
    python scripts/narrate_book.py --chapter 9        # Single chapter
    python scripts/narrate_book.py --list              # Show what needs narrating
    python scripts/narrate_book.py --interludes        # Narrate interludes only
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BOOK_DIR = REPO_ROOT / "content" / "book" / "reader-edition"
OUTPUT_DIR = REPO_ROOT / "artifacts" / "narration"
KOKORO_DIR = Path.home() / ".kokoro-onnx"

VOICE = "am_adam"
SPEED = 0.92
SAMPLE_RATE = 24000


def find_chapters() -> list[tuple[str, Path]]:
    """Find all chapter and interlude files, sorted."""
    chapters = []
    for f in sorted(BOOK_DIR.glob("ch*.md")):
        num = re.search(r"ch(\d+)", f.name)
        label = f"ch{num.group(1).zfill(2)}" if num else f.stem
        chapters.append((label, f))
    for f in sorted(BOOK_DIR.glob("interlude-*.md")):
        chapters.append((f.stem, f))
    # Rootlight chapter
    rootlight = BOOK_DIR / "ch-rootlight.md"
    if rootlight.exists():
        chapters.append(("ch-rootlight", rootlight))
    return chapters


def extract_narration_text(md_path: Path) -> str:
    """Extract readable text from markdown, stripping headers and formatting."""
    text = md_path.read_text(encoding="utf-8")

    # Remove YAML frontmatter
    text = re.sub(r"^---.*?---\s*", "", text, flags=re.DOTALL)

    # Convert headers to pauses
    text = re.sub(r"^#{1,6}\s+(.+)$", r"\1.", text, flags=re.MULTILINE)

    # Remove markdown formatting
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)  # bold
    text = re.sub(r"\*(.+?)\*", r"\1", text)  # italic
    text = re.sub(r"`(.+?)`", r"\1", text)  # code
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)  # links
    text = re.sub(r"^[-*]\s+", "", text, flags=re.MULTILINE)  # bullets
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)  # blockquotes

    # Clean up whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    return text


def narrate_chapter(label: str, md_path: Path, voice: str = VOICE, speed: float = SPEED) -> Path | None:
    """Narrate a single chapter to WAV."""
    output_path = OUTPUT_DIR / f"{label}.wav"
    if output_path.exists():
        print(f"  [{label}] Already narrated, skipping")
        return output_path

    text = extract_narration_text(md_path)
    if not text:
        print(f"  [{label}] Empty text, skipping")
        return None

    word_count = len(text.split())
    est_minutes = word_count / (150 * speed)  # ~150 WPM at speed factor
    print(f"  [{label}] {word_count} words, ~{est_minutes:.1f} min estimated")

    try:
        import kokoro_onnx
        import soundfile as sf
        import numpy as np

        # Find model files
        model_path = KOKORO_DIR / "kokoro-v1.0.int8.onnx"
        voices_path = KOKORO_DIR / "voices-v1.0.bin"

        if not model_path.exists():
            # Try v0.19
            model_path = KOKORO_DIR / "kokoro-v0.19.onnx"
        if not voices_path.exists():
            voices_path = KOKORO_DIR / "voices-v0.19.bin"

        if not model_path.exists():
            print(f"  [{label}] ERROR: No Kokoro model found in {KOKORO_DIR}")
            return None

        # Load model
        kokoro = kokoro_onnx.Kokoro(str(model_path), str(voices_path))

        # Split text into chunks (Kokoro has token limits)
        chunks = split_text(text, max_chars=500)
        all_audio = []

        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            try:
                samples, sr = kokoro.create(chunk, voice=voice, speed=speed)
                all_audio.append(samples)
                # Add small pause between chunks
                pause = np.zeros(int(sr * 0.3), dtype=samples.dtype)
                all_audio.append(pause)
            except Exception as e:
                print(f"  [{label}] Chunk {i+1}/{len(chunks)} failed: {e}")
                continue

            if (i + 1) % 20 == 0:
                print(f"  [{label}] {i+1}/{len(chunks)} chunks done...")

        if not all_audio:
            print(f"  [{label}] No audio generated")
            return None

        # Concatenate and save
        full_audio = np.concatenate(all_audio)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), full_audio, sr)

        duration = len(full_audio) / sr
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"  [{label}] Done: {duration/60:.1f} min, {size_mb:.1f} MB")
        return output_path

    except Exception as e:
        print(f"  [{label}] ERROR: {e}")
        return None


def split_text(text: str, max_chars: int = 500) -> list[str]:
    """Split text into chunks at sentence boundaries."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) > max_chars and current:
            chunks.append(current.strip())
            current = sentence
        else:
            current = current + " " + sentence if current else sentence

    if current.strip():
        chunks.append(current.strip())

    return chunks


def main():
    parser = argparse.ArgumentParser(description="Narrate The Six Tongues Protocol")
    parser.add_argument("--chapter", type=str, help="Narrate specific chapter (e.g. 9, 'rootlight', 'interlude-01')")
    parser.add_argument("--list", action="store_true", help="List chapters and narration status")
    parser.add_argument("--interludes", action="store_true", help="Narrate interludes only")
    parser.add_argument("--voice", default=VOICE, help=f"Kokoro voice (default: {VOICE})")
    parser.add_argument("--speed", type=float, default=SPEED, help=f"Speed (default: {SPEED})")
    parser.add_argument("--start", type=int, default=1, help="Start from chapter N")
    args = parser.parse_args()

    chapters = find_chapters()

    if args.list:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"{'Label':<30} {'Words':>8} {'Narrated':>10}")
        print("-" * 52)
        for label, path in chapters:
            text = extract_narration_text(path)
            words = len(text.split())
            narrated = "YES" if (OUTPUT_DIR / f"{label}.wav").exists() else "no"
            print(f"{label:<30} {words:>8} {narrated:>10}")
        return

    # Filter chapters
    if args.chapter:
        target = args.chapter.lower()
        chapters = [(l, p) for l, p in chapters if target in l.lower()]
        if not chapters:
            print(f"No chapter matching '{args.chapter}'")
            return
    elif args.interludes:
        chapters = [(l, p) for l, p in chapters if "interlude" in l]
    else:
        # Skip chapters before --start
        chapters = [
            (l, p)
            for l, p in chapters
            if not re.match(r"ch(\d+)", l) or int(re.match(r"ch(\d+)", l).group(1)) >= args.start
        ]

    print(f"Narrating {len(chapters)} chapters with voice={args.voice}, speed={args.speed}")
    print(f"Output: {OUTPUT_DIR}")
    print()

    start_time = time.monotonic()
    success = 0
    for label, path in chapters:
        result = narrate_chapter(label, path, voice=args.voice, speed=args.speed)
        if result:
            success += 1

    elapsed = time.monotonic() - start_time
    print(f"\nDone: {success}/{len(chapters)} chapters narrated in {elapsed/60:.1f} minutes")


if __name__ == "__main__":
    main()
