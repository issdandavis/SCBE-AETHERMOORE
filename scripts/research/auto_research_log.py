#!/usr/bin/env python3
"""
auto_research_log.py — Append research results to JSONL log and markdown timeline.

Usage:
  python scripts/research/auto_research_log.py \
    --topic "Biblical Null-Space" \
    --result "Gemini 23.3%, controls 33.3%, noise 0%" \
    --wave 2 \
    --link "docs/research/BIBLICAL_NULL_SPACE_HYPOTHESIS.md"

  python scripts/research/auto_research_log.py \
    --topic "Phi-Poincare Shells" \
    --result "35 tests passing, wired into runtime gate" \
    --wave 3

Outputs:
  artifacts/research/research_log.jsonl   — one JSON object per line
  artifacts/research/RESEARCH_TIMELINE.md — one-line summaries
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "research"
JSONL_PATH = ARTIFACTS_DIR / "research_log.jsonl"
TIMELINE_PATH = ARTIFACTS_DIR / "RESEARCH_TIMELINE.md"

WAVE_LABELS = {
    1: "Hypothesis",
    2: "Initial Evidence",
    3: "Replicated",
    4: "Peer Reviewed",
    5: "Established",
}


def ensure_dirs():
    """Create output directories if they do not exist."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def ensure_timeline_header():
    """Write the timeline header if the file does not exist yet."""
    if not TIMELINE_PATH.exists():
        TIMELINE_PATH.write_text(
            "# SCBE Research Timeline\n\n"
            "Auto-generated log of research results.  \n"
            "Format: `[timestamp] WAVE N | Topic | Result | link`\n\n"
            "---\n\n",
            encoding="utf-8",
        )


def append_jsonl(record: dict):
    """Append a single JSON record to the JSONL log."""
    with open(JSONL_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def append_timeline(timestamp: str, wave: int, topic: str, result: str, link: str):
    """Append a one-line summary to the markdown timeline."""
    ensure_timeline_header()
    link_part = f" | {link}" if link else ""
    line = f"[{timestamp}] WAVE {wave} | {topic} | {result}{link_part}\n"
    with open(TIMELINE_PATH, "a", encoding="utf-8") as f:
        f.write(line)


def main():
    parser = argparse.ArgumentParser(
        description="Log a research result to JSONL + markdown timeline."
    )
    parser.add_argument(
        "--topic",
        required=True,
        help='Research topic name, e.g. "Biblical Null-Space"',
    )
    parser.add_argument(
        "--result",
        required=True,
        help='Short summary of the result, e.g. "Gemini 23.3%%, controls 33.3%%"',
    )
    parser.add_argument(
        "--wave",
        required=True,
        type=int,
        choices=[1, 2, 3, 4, 5],
        help="Wave level (1=Hypothesis, 2=Initial Evidence, 3=Replicated, 4=Peer Reviewed, 5=Established)",
    )
    parser.add_argument(
        "--link",
        default="",
        help="URL or relative path to the full report (optional)",
    )

    args = parser.parse_args()

    ensure_dirs()

    now = datetime.now(timezone.utc)
    timestamp_display = now.strftime("%Y-%m-%d %H:%M")
    timestamp_iso = now.isoformat()

    record = {
        "timestamp": timestamp_iso,
        "topic": args.topic,
        "wave": args.wave,
        "wave_label": WAVE_LABELS[args.wave],
        "result": args.result,
        "link": args.link,
    }

    append_jsonl(record)
    append_timeline(timestamp_display, args.wave, args.topic, args.result, args.link)

    print(f"Logged: WAVE {args.wave} | {args.topic}")
    print(f"  JSONL: {JSONL_PATH}")
    print(f"  Timeline: {TIMELINE_PATH}")


if __name__ == "__main__":
    main()
