#!/usr/bin/env python3
"""Ingest Microsoft Copilot / podcast transcripts into SCBE cloud-kernel intake."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INTAKE_DIR = REPO_ROOT / "training" / "intake" / "copilot" / "podcasts"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def split_chunks(text: str, chunk_size: int = 1800, overlap: int = 220) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []
    if chunk_size <= 10:
        raise ValueError("chunk_size must be > 10")
    step = max(1, chunk_size - max(0, overlap))
    chunks: list[str] = []
    for start in range(0, len(text), step):
        chunk = text[start : start + chunk_size].strip()
        if len(chunk) >= 40:
            chunks.append(chunk)
    return chunks


def sanitize_name(value: str, fallback: str = "podcast") -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9-_]", "_", value).strip("_")
    return (cleaned[:120] or fallback).strip("_")


def strip_srt_vtt(text: str) -> str:
    lines = text.splitlines()
    output: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.lower() == "webvtt":
            continue
        if re.fullmatch(r"\d+", line):
            continue
        if re.search(r"\d{2}:\d{2}:\d{2}[\.,]\d{3}\s+-->\s+\d{2}:\d{2}:\d{2}[\.,]\d{3}", line):
            continue
        if re.fullmatch(r"\d{2}:\d{2}:\d{2}(?:[\.,]\d{3})?", line):
            continue
        output.append(line)
    return " ".join(output)


def read_transcript(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    ext = path.suffix.lower()
    if ext in {".srt", ".vtt"}:
        return strip_srt_vtt(raw)
    if ext in {".txt", ".md", ".text"}:
        return " ".join(raw.split())
    # Fallback: still try best-effort extraction
    return " ".join(raw.split())


def build_rows(*, source_system: str, source_url: str, source_title: str, podcast_id: str, chunks: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    run_time = utc_now()
    for idx, chunk in enumerate(chunks):
        row_hash = hashlib.sha256((source_url + "\n" + chunk).encode("utf-8")).hexdigest()
        rows.append(
            {
                "event_type": "podcast_chunk",
                "dataset": "copilot_podcast_intake",
                "source_system": source_system,
                "source_system_hint": "copilot",
                "source_path": f"training/intake/copilot/podcasts/{podcast_id}.jsonl",
                "chunk_index": idx,
                "source_id": row_hash,
                "source_url": source_url,
                "title": source_title,
                "text": chunk,
                "created_at_utc": run_time,
                "category": "audio",
            }
        )
    return rows


def write_intake(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        for row in rows:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest Copilot podcast transcripts into SCBE training intake")
    parser.add_argument("--transcript-path", required=True, help="Path to .txt/.srt/.vtt transcript file")
    parser.add_argument("--source-url", default="", help="Optional podcast or episode URL")
    parser.add_argument("--title", default="", help="Episode title")
    parser.add_argument("--source-system", default="copilot_podcast", help="source_system metadata field")
    parser.add_argument("--chunk-size", type=int, default=1800)
    parser.add_argument("--chunk-overlap", type=int, default=220)
    parser.add_argument("--intake-dir", default=str(DEFAULT_INTAKE_DIR))
    parser.add_argument("--run-cloud-pipeline", action="store_true", help="Run cloud_kernel_data_pipeline after write")
    parser.add_argument("--pipeline-config", default="training/cloud_kernel_pipeline.tuned.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    transcript_path = Path(args.transcript_path)
    if not transcript_path.exists():
        raise FileNotFoundError(f"Transcript not found: {transcript_path}")

    transcript = read_transcript(transcript_path)
    if not transcript.strip():
        raise RuntimeError("Transcript text is empty after parsing")

    podcast_id = sanitize_name(transcript_path.stem, fallback="copilot_podcast")
    title = args.title.strip() or podcast_id
    chunks = split_chunks(transcript, chunk_size=args.chunk_size, overlap=args.chunk_overlap)

    rows = build_rows(
        source_system=args.source_system,
        source_url=args.source_url,
        source_title=title,
        podcast_id=podcast_id,
        chunks=chunks,
    )

    intake_dir = Path(args.intake_dir)
    out_file = intake_dir / f"copilot_podcast_{podcast_id}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.jsonl"
    write_intake(out_file, rows)

    print(f"WROTE={out_file}")
    print(f"CHUNKS={len(rows)}")

    if args.run_cloud_pipeline:
        cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "cloud_kernel_data_pipeline.py"),
            "--config",
            args.pipeline_config,
        ]
        proc = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(proc.stdout)
        return proc.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())