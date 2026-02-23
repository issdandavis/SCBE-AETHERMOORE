#!/usr/bin/env python3
"""
Normalize raw Perplexity thread JSON exports into structured JSONL.

Input (default):
  data/perplexity/raw_json/*.json

Output (default):
  data/perplexity/perplexity_threads.jsonl
  data/perplexity/normalize_stats.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_RAW_DIR = "data/perplexity/raw_json"
DEFAULT_OUTPUT_JSONL = "data/perplexity/normalized/perplexity_normalized.jsonl"
DEFAULT_OUTPUT_STATS = "data/perplexity/normalized/normalize_stats.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_text(text: str) -> str:
    text = str(text or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_role(role: str) -> str:
    role = str(role or "").strip().lower()
    if role in ("user", "assistant", "system"):
        return role
    if "assistant" in role or "answer" in role:
        return "assistant"
    if "user" in role or "question" in role or "human" in role:
        return "user"
    if "system" in role:
        return "system"
    return "unknown"


def normalize_messages(
    messages: list[dict[str, Any]],
    min_message_chars: int = 3,
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    prev_key: tuple[str, str] | None = None

    for msg in messages:
        role = normalize_role(msg.get("role", "unknown"))
        content = clean_text(msg.get("content", msg.get("text", "")))
        if len(content) < min_message_chars:
            continue
        key = (role, content)
        if key == prev_key:
            continue
        out.append({"role": role, "content": content})
        prev_key = key

    return out


def estimate_token_count(text: str) -> int:
    # Lightweight estimator: ~4 chars/token.
    text = clean_text(text)
    if not text:
        return 0
    return max(1, len(text) // 4)


def build_record(
    payload: dict[str, Any],
    source_file: Path,
    min_message_chars: int = 3,
) -> dict[str, Any] | None:
    thread_id = str(payload.get("id") or source_file.stem)
    title = clean_text(payload.get("title", ""))
    url = clean_text(payload.get("url", payload.get("source_url", "")))
    label = clean_text(payload.get("label", ""))
    exported_at = clean_text(payload.get("exported_at", ""))

    raw_messages = payload.get("messages", [])
    if not isinstance(raw_messages, list):
        return None
    messages = normalize_messages(raw_messages, min_message_chars=min_message_chars)
    if not messages:
        return None

    text = "\n".join(f"[{m['role']}] {m['content']}" for m in messages)
    token_est = estimate_token_count(text)

    return {
        "source": "perplexity",
        "thread_id": thread_id,
        "title": title,
        "url": url,
        "label": label,
        "message_count": len(messages),
        "token_estimate": token_est,
        "messages": messages,
        "text": text,
        "exported_at": exported_at,
        "normalized_at": utc_now(),
        "source_file": str(source_file),
    }


def normalize_thread(path: Path, min_message_chars: int = 3) -> list[dict[str, Any]] | None:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return None

    thread_id = str(raw.get("id") or path.stem)
    title = clean_text(raw.get("title", ""))
    url = clean_text(raw.get("url", raw.get("source_url", "")))
    label = clean_text(raw.get("label", ""))
    exported_at = clean_text(raw.get("exported_at", ""))

    raw_messages = raw.get("messages", [])
    if not isinstance(raw_messages, list):
        return None
    messages = normalize_messages(raw_messages, min_message_chars=min_message_chars)
    if not messages:
        return None

    turns: list[dict[str, Any]] = []
    for i, msg in enumerate(messages):
        content = str(msg.get("content", "")).strip()
        turns.append(
            {
                "thread_id": thread_id,
                "turn_index": i,
                "role": msg.get("role", "user"),
                "text": content,
                "content": content,
                "token_estimate": estimate_token_count(content),
                "title": title,
                "url": url,
                "label": label,
                "source": "perplexity",
                "timestamp": datetime.utcnow().isoformat(),
                "tags": [],
                "model": "unknown",
                "meta": {
                    "title": raw.get("title"),
                    "url": raw.get("url"),
                    "label": raw.get("label"),
                },
                "exported_at": exported_at,
                "normalized_at": utc_now(),
                "source_file": str(path),
            }
        )

    return turns


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize raw Perplexity thread JSON into structured JSONL."
    )
    parser.add_argument("--raw-dir", default=DEFAULT_RAW_DIR)
    parser.add_argument("--output-jsonl", default=DEFAULT_OUTPUT_JSONL)
    parser.add_argument("--output-stats", default=DEFAULT_OUTPUT_STATS)
    parser.add_argument("--min-message-chars", type=int, default=3)
    parser.add_argument("--min-message-count", type=int, default=1)
    parser.add_argument("--max-records", type=int, default=0)
    return parser.parse_args()


def iter_raw_thread_files(raw_dir: Path) -> list[Path]:
    files = []
    for path in sorted(raw_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        files.append(path)
    return files


def normalize_perplexity_dataset(
    *,
    raw_dir: Path,
    output_jsonl: Path,
    output_stats: Path,
    min_message_chars: int,
    min_message_count: int,
    max_records: int,
) -> dict[str, Any]:
    raw_files = iter_raw_thread_files(raw_dir)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    output_stats.parent.mkdir(parents=True, exist_ok=True)

    kept_threads = 0
    kept_turns = 0
    skipped_parse = 0
    skipped_invalid = 0
    all_turns: list[dict[str, Any]] = []

    for path in raw_files:
        try:
            turns = normalize_thread(path=path, min_message_chars=min_message_chars)
        except Exception:  # noqa: BLE001
            skipped_parse += 1
            continue

        if not turns:
            skipped_invalid += 1
            continue
        if len(turns) < min_message_count:
            skipped_invalid += 1
            continue

        all_turns.extend(turns)
        kept_threads += 1
        kept_turns += len(turns)
        if max_records > 0 and kept_threads >= max_records:
            break

    with output_jsonl.open("w", encoding="utf-8", newline="\n") as f:
        for turn in all_turns:
            f.write(json.dumps(turn, ensure_ascii=False) + "\n")

    stats = {
        "generated_at": utc_now(),
        "raw_dir": str(raw_dir),
        "raw_files_seen": len(raw_files),
        "threads_written": kept_threads,
        "records_written": kept_turns,
        "skipped_parse": skipped_parse,
        "skipped_invalid": skipped_invalid,
        "output_jsonl": str(output_jsonl),
    }
    output_stats.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


def main() -> int:
    args = parse_args()
    try:
        stats = normalize_perplexity_dataset(
            raw_dir=Path(args.raw_dir),
            output_jsonl=Path(args.output_jsonl),
            output_stats=Path(args.output_stats),
            min_message_chars=int(args.min_message_chars),
            min_message_count=int(args.min_message_count),
            max_records=int(args.max_records),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[normalize_perplexity] ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    main()
