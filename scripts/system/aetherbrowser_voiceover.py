#!/usr/bin/env python3
"""Aetherbrowser voiceover receipt tool.

Creates a local WAV voiceover from text using python.scbe.tts_backend and can
optionally speak it through the default audio device. The JSON receipt avoids
echoing the full transcript; it records length/hash plus a short preview.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = ROOT / "artifacts" / "aetherbrowser_voiceover"

sys.path.insert(0, str(ROOT))

from python.scbe.tts_backend import available, speak  # noqa: E402


def utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip())[:80].strip("-")
    return slug or "voiceover"


def public_text_preview(text: str) -> str:
    compact = " ".join(text.split())
    return compact[:160]


def build_receipt(
    *,
    ok: bool,
    text: str,
    engine: str | None,
    wav_path: Path | None,
    spoken: bool,
    out_dir: Path,
    rate: int | None,
    voice: str | None,
    error: str | None = None,
) -> dict[str, Any]:
    wav_exists = bool(wav_path and wav_path.exists())
    return {
        "ok": ok,
        "schema_version": "aetherbrowser-voiceover-v1",
        "status": "VOICEOVER_READY" if ok else "VOICEOVER_FAILED",
        "engine": engine,
        "voice": voice,
        "rate": rate,
        "spoken": spoken,
        "wav_path": str(wav_path) if wav_path else None,
        "wav_bytes": wav_path.stat().st_size if wav_exists else 0,
        "out_dir": str(out_dir),
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "text_length": len(text),
        "text_preview": public_text_preview(text),
        "error": error,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a local Aetherbrowser text-to-speech voiceover.")
    parser.add_argument("--text", required=True, help="Transcript text to synthesize.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Directory for WAV and receipt artifacts.")
    parser.add_argument("--basename", default="", help="Optional safe artifact filename stem.")
    parser.add_argument("--voice", default="", help="Optional local voice name substring.")
    parser.add_argument("--rate", type=int, default=None, help="Speech rate, usually -10 to 10 for SAPI.")
    parser.add_argument("--engine", default="", help="Optional engine override: sapi, pyttsx3, espeak, or say.")
    parser.add_argument("--speak-now", action="store_true", help="Also speak through the default audio device.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    text = str(args.text or "").strip()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    engine = args.engine.strip() or available()
    base = safe_slug(args.basename or f"voiceover-{utc_stamp()}-{hashlib.sha1(text.encode('utf-8')).hexdigest()[:8]}")
    wav_path = out_dir / f"{base}.wav"
    voice = args.voice.strip() or None
    rate = args.rate

    if not text:
        receipt = build_receipt(
            ok=False,
            text=text,
            engine=engine,
            wav_path=None,
            spoken=False,
            out_dir=out_dir,
            rate=rate,
            voice=voice,
            error="No text provided.",
        )
        (out_dir / "last_voiceover.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print(json.dumps(receipt, indent=2))
        return 2

    if len(text) > 20_000:
        receipt = build_receipt(
            ok=False,
            text=text,
            engine=engine,
            wav_path=None,
            spoken=False,
            out_dir=out_dir,
            rate=rate,
            voice=voice,
            error="Text too long for one voiceover call; limit is 20000 characters.",
        )
        (out_dir / "last_voiceover.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print(json.dumps(receipt, indent=2))
        return 2

    try:
        speak(text, out_path=str(wav_path), rate=rate, voice=voice, engine=engine)
        spoken = False
        if args.speak_now:
            speak(text, out_path=None, rate=rate, voice=voice, engine=engine)
            spoken = True
        receipt = build_receipt(
            ok=True,
            text=text,
            engine=engine,
            wav_path=wav_path,
            spoken=spoken,
            out_dir=out_dir,
            rate=rate,
            voice=voice,
        )
        (out_dir / "last_voiceover.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print(json.dumps(receipt, indent=2))
        return 0
    except Exception as exc:  # local tool should return a receipt instead of a traceback
        receipt = build_receipt(
            ok=False,
            text=text,
            engine=engine,
            wav_path=wav_path if wav_path.exists() else None,
            spoken=False,
            out_dir=out_dir,
            rate=rate,
            voice=voice,
            error=f"{type(exc).__name__}: {exc}",
        )
        (out_dir / "last_voiceover.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print(json.dumps(receipt, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
