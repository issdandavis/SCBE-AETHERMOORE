#!/usr/bin/env python3
"""Marp deck -> narrated MP4.

Reads a Marp markdown deck, exports each slide to PNG via marp-cli, generates
voice-over audio from the per-slide speaker notes via pyttsx3 (Windows SAPI),
then composes everything into a single MP4 with ffmpeg.

Speaker notes are extracted from HTML comments of the form:
    <!-- SPEAKER NOTES: ... -->
or the simpler form:
    <!-- ... -->

Usage:
    python scripts/video/deck_to_video.py docs/presentations/SYSTEMS_BLUEPRINT.md \
        --out artifacts/videos/SYSTEMS_BLUEPRINT.mp4

Requirements:
    pip install pyttsx3
    npm install -g @marp-team/marp-cli  (or invoke via npx; auto-detected)
    ffmpeg in PATH
"""

from __future__ import annotations

import argparse
import contextlib
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import Sequence


SLIDE_BREAK_RE = re.compile(r"^---\s*$", re.MULTILINE)
SPEAKER_NOTES_RE = re.compile(
    r"<!--\s*(?:SPEAKER NOTES:)?\s*(.*?)\s*-->",
    re.DOTALL | re.IGNORECASE,
)
MARP_DIRECTIVE_RE = re.compile(r"^_[a-zA-Z]+\s*:")
DEFAULT_FRAME_RATE = 30
DEFAULT_VIDEO_WIDTH = 1920
DEFAULT_VIDEO_HEIGHT = 1080


def parse_slides(deck_md: Path) -> list[str]:
    """Split a Marp deck into per-slide markdown chunks (frontmatter dropped)."""
    text = deck_md.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4 :]
    parts = SLIDE_BREAK_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def extract_notes(slide_md: str) -> str:
    """Return concatenated speaker-notes text for a single slide chunk.

    If the slide has no notes, the visible markdown content is collapsed to
    plain text and used as a fallback narration so the video still has audio.
    """
    matches = SPEAKER_NOTES_RE.findall(slide_md)
    if matches:
        kept = [
            m.strip()
            for m in matches
            if m.strip() and not MARP_DIRECTIVE_RE.match(m.strip())
        ]
        notes = " ".join(kept)
        if notes:
            return _normalize(notes)
    visible = SPEAKER_NOTES_RE.sub("", slide_md)
    return _normalize(visible)


def _normalize(text: str) -> str:
    text = re.sub(r"`{1,3}.*?`{1,3}", " ", text, flags=re.DOTALL)
    text = re.sub(r"^[\s>*\-#|]+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\|.*?\|", " ", text)
    text = re.sub(r"\$.*?\$", " ", text, flags=re.DOTALL)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def export_slides_png(deck_md: Path, out_dir: Path) -> list[Path]:
    """Use marp-cli to export every slide as a PNG. Returns ordered paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    template = out_dir / "slide.png"
    cmd = _resolve_marp_cmd() + [
        str(deck_md),
        "--images",
        "png",
        "--allow-local-files",
        "-o",
        str(template),
    ]
    print("[deck_to_video] exporting slide PNGs:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    pngs = sorted(out_dir.glob("slide.*.png"))
    if not pngs:
        raise RuntimeError(f"marp produced no PNGs in {out_dir}")
    return pngs


def _resolve_marp_cmd() -> list[str]:
    marp = shutil.which("marp")
    if marp:
        return [marp]
    npx = shutil.which("npx") or shutil.which("npx.cmd") or shutil.which("npx.CMD")
    if not npx:
        raise RuntimeError("Neither 'marp' nor 'npx' found in PATH")
    return [npx, "--yes", "@marp-team/marp-cli"]


def _resolve_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not in PATH; install via `winget install Gyan.FFmpeg`")
    return ffmpeg


def synth_audio(text: str, out_wav: Path, voice_id: str | None, rate: int) -> float:
    """Render `text` to a WAV file via pyttsx3. Returns audio duration in seconds."""
    import pyttsx3  # local import so --help works without the dep

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    engine = pyttsx3.init()
    engine.setProperty("rate", rate)
    if voice_id:
        engine.setProperty("voice", voice_id)
    engine.save_to_file(text or "Slide.", str(out_wav))
    engine.runAndWait()
    if not out_wav.exists() or out_wav.stat().st_size == 0:
        raise RuntimeError(f"pyttsx3 failed to write {out_wav}")
    return _wav_duration(out_wav)


def _wav_duration(path: Path) -> float:
    with contextlib.closing(wave.open(str(path), "rb")) as f:
        frames = f.getnframes()
        rate = f.getframerate() or 1
        return frames / rate


def compose_slide(png: Path, audio: Path, duration: float, out_mp4: Path) -> None:
    """Use ffmpeg to compose a still image + audio into an MP4 segment."""
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        _resolve_ffmpeg(),
        "-y",
        "-loop",
        "1",
        "-i",
        str(png),
        "-i",
        str(audio),
        "-c:v",
        "libx264",
        "-tune",
        "stillimage",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-pix_fmt",
        "yuv420p",
        "-vf",
        f"scale={DEFAULT_VIDEO_WIDTH}:{DEFAULT_VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={DEFAULT_VIDEO_WIDTH}:{DEFAULT_VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=white",
        "-r",
        str(DEFAULT_FRAME_RATE),
        "-shortest",
        "-t",
        f"{max(duration, 1.0):.3f}",
        str(out_mp4),
    ]
    print(f"[deck_to_video] composing {out_mp4.name} ({duration:.1f}s)")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def concat_segments(segments: Sequence[Path], out_mp4: Path) -> None:
    """Concat per-slide MP4s into the final video using ffmpeg's concat demuxer."""
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    list_file = out_mp4.with_suffix(".concat.txt")
    list_file.write_text(
        "\n".join(f"file '{seg.resolve().as_posix()}'" for seg in segments),
        encoding="utf-8",
    )
    cmd = [
        _resolve_ffmpeg(),
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c",
        "copy",
        str(out_mp4),
    ]
    print(f"[deck_to_video] concatenating {len(segments)} segments -> {out_mp4}")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    list_file.unlink(missing_ok=True)


def build_video(
    deck_md: Path,
    out_mp4: Path,
    voice_id: str | None,
    rate: int,
    keep_workdir: bool,
) -> None:
    workdir = Path(tempfile.mkdtemp(prefix="deck2video_"))
    print(f"[deck_to_video] workdir: {workdir}")
    try:
        slides = parse_slides(deck_md)
        if not slides:
            raise RuntimeError(f"no slides parsed from {deck_md}")
        print(f"[deck_to_video] parsed {len(slides)} slides from {deck_md}")
        pngs = export_slides_png(deck_md, workdir / "png")
        if len(pngs) != len(slides):
            print(
                f"[deck_to_video] WARNING: parser sees {len(slides)} slides but "
                f"marp produced {len(pngs)} PNGs; truncating to min."
            )
        n = min(len(slides), len(pngs))
        segments: list[Path] = []
        for i in range(n):
            note = extract_notes(slides[i])
            wav = workdir / "audio" / f"slide_{i:02d}.wav"
            duration = synth_audio(note, wav, voice_id=voice_id, rate=rate)
            seg = workdir / "segments" / f"slide_{i:02d}.mp4"
            compose_slide(pngs[i], wav, duration, seg)
            segments.append(seg)
        concat_segments(segments, out_mp4)
        size_mb = out_mp4.stat().st_size / (1024 * 1024)
        print(f"[deck_to_video] DONE -> {out_mp4} ({size_mb:.1f} MB)")
    finally:
        if not keep_workdir:
            shutil.rmtree(workdir, ignore_errors=True)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("deck", type=Path, help="Marp markdown deck path")
    p.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/videos/deck.mp4"),
        help="Output MP4 path",
    )
    p.add_argument(
        "--voice",
        default=None,
        help="pyttsx3 voice id (run with --list-voices to see options)",
    )
    p.add_argument(
        "--rate",
        type=int,
        default=180,
        help="Speech rate, words-per-minute proxy (default: 180)",
    )
    p.add_argument(
        "--list-voices",
        action="store_true",
        help="List available SAPI voices and exit",
    )
    p.add_argument(
        "--keep-workdir",
        action="store_true",
        help="Don't delete the temp workdir (useful for debugging)",
    )
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.list_voices:
        import pyttsx3

        engine = pyttsx3.init()
        for v in engine.getProperty("voices"):
            print(f"{v.id}\n  {v.name}")
        return 0
    if not args.deck.is_file():
        print(f"ERROR: deck not found: {args.deck}", file=sys.stderr)
        return 1
    build_video(
        args.deck,
        args.out,
        voice_id=args.voice,
        rate=args.rate,
        keep_workdir=args.keep_workdir,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
