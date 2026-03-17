#!/usr/bin/env python3
"""Pull a YouTube transcript by video URL or ID.

Prefers the `youtube_transcript_api` package when installed and emits either:
- plain text transcript to stdout
- JSON transcript payload
- optional output file write
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_video_id(target: str) -> str:
    raw = str(target or "").strip()
    if not raw:
        raise ValueError("Video URL or ID is required")
    if VIDEO_ID_RE.fullmatch(raw):
        return raw

    parsed = urlparse(raw)
    host = (parsed.netloc or "").lower()
    path = parsed.path.strip("/")

    if host in {"youtu.be", "www.youtu.be"}:
        candidate = path.split("/", 1)[0]
        if VIDEO_ID_RE.fullmatch(candidate):
            return candidate

    if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [""])[0].strip()
            if VIDEO_ID_RE.fullmatch(candidate):
                return candidate
        for prefix in ("shorts/", "live/", "embed/"):
            if path.startswith(prefix):
                candidate = path[len(prefix) :].split("/", 1)[0]
                if VIDEO_ID_RE.fullmatch(candidate):
                    return candidate

    raise ValueError(f"Could not extract a YouTube video ID from '{target}'")


def _normalize_segment(segment: Any) -> dict[str, Any]:
    if isinstance(segment, dict):
        text = str(segment.get("text", "")).strip()
        start = float(segment.get("start", 0.0) or 0.0)
        duration = float(segment.get("duration", 0.0) or 0.0)
        return {"text": text, "start": start, "duration": duration}

    text = str(getattr(segment, "text", "")).strip()
    start = float(getattr(segment, "start", 0.0) or 0.0)
    duration = float(getattr(segment, "duration", 0.0) or 0.0)
    return {"text": text, "start": start, "duration": duration}


def fetch_transcript(video_id: str, languages: list[str]) -> list[dict[str, Any]]:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError as exc:  # pragma: no cover - exercised via error path in main
        raise RuntimeError(
            "youtube_transcript_api is not installed. Install it to enable transcript pulls."
        ) from exc

    segments: Any
    if hasattr(YouTubeTranscriptApi, "get_transcript"):
        segments = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
    else:  # Newer object-style API fallback
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, languages=languages)
        segments = fetched.to_raw_data() if hasattr(fetched, "to_raw_data") else list(fetched)

    return [_normalize_segment(segment) for segment in segments]


def transcript_text(segments: list[dict[str, Any]]) -> str:
    return "\n".join(segment["text"] for segment in segments if segment.get("text"))


def transcript_payload(video_id: str, languages: list[str], segments: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "video_id": video_id,
        "languages": languages,
        "segment_count": len(segments),
        "segments": segments,
        "text": transcript_text(segments),
    }


def write_output(path: Path, payload: dict[str, Any], as_json: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if as_json:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return
    path.write_text(payload["text"], encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pull a YouTube transcript by URL or video ID.")
    parser.add_argument("target", help="YouTube video URL or raw 11-character video ID.")
    parser.add_argument(
        "--language",
        action="append",
        dest="languages",
        default=None,
        help="Preferred transcript language. Repeat to add fallbacks.",
    )
    parser.add_argument("--output", default="", help="Optional output path for text or JSON transcript.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of plain text.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    languages = [str(lang).strip() for lang in (args.languages or ["en"]) if str(lang).strip()]
    video_id = extract_video_id(args.target)
    segments = fetch_transcript(video_id, languages)
    payload = transcript_payload(video_id, languages, segments)

    if args.output.strip():
        write_output(Path(args.output).expanduser(), payload, as_json=bool(args.json))

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(payload["text"])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"[youtube-transcript] {exc}", file=sys.stderr)
        raise SystemExit(1)
