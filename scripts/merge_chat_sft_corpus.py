#!/usr/bin/env python3
"""
merge_chat_sft_corpus.py — Build a chat-format corpus from the current root SFT set plus Claude exports.

This keeps the existing consolidated corpus intact and emits a new merged file that:
- preserves chat-style rows as chat rows
- converts instruction/response rows into chat format
- deduplicates by (user, assistant) content
- writes a compact summary with per-source counts
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUTS = (
    REPO_ROOT / "training-data" / "sft" / "consolidated_root_sft.jsonl",
    REPO_ROOT / "training-data" / "sft" / "claude_conversations_sft.jsonl",
    REPO_ROOT / "training-data" / "sft" / "claude_export_lore_sft.jsonl",
)
DEFAULT_OUTPUT = (
    REPO_ROOT / "training-data" / "sft" / "consolidated_plus_claude_exports_sft.jsonl"
)
DEFAULT_SUMMARY = (
    REPO_ROOT / "artifacts" / "training" / "consolidated_plus_claude_exports.summary.json"
)
DEFAULT_SYSTEM_PROMPT = (
    "You are Polly, the SCBE-AETHERMOORE governance assistant. You explain the system "
    "clearly and accurately, drawing from deep knowledge of the architecture, Sacred "
    "Tongues, and governance principles."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge chat-format corpus with Claude exports")
    parser.add_argument(
        "--input",
        action="append",
        dest="inputs",
        help="Input JSONL file path (can be provided multiple times)",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    parser.add_argument(
        "--shard-lines",
        type=int,
        default=0,
        help="If > 0, write the merged corpus as sharded JSONL files with this many rows per shard",
    )
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            raw = raw.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _extract_last_message(messages: list[dict[str, Any]], role: str) -> str:
    for message in reversed(messages):
        if message.get("role") == role and isinstance(message.get("content"), str):
            content = message["content"].strip()
            if content:
                return content
    return ""


def normalize_record(record: dict[str, Any], source_label: str) -> dict[str, Any] | None:
    if isinstance(record.get("messages"), list):
        messages = [m for m in record["messages"] if isinstance(m, dict)]
        user = _extract_last_message(messages, "user")
        assistant = _extract_last_message(messages, "assistant")
        if not user or not assistant:
            return None
        system = _extract_last_message(messages, "system") or DEFAULT_SYSTEM_PROMPT
        out: dict[str, Any] = {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
                {"role": "assistant", "content": assistant},
            ],
            "source": source_label,
        }
        for key in ("metadata", "category", "encoding_tongue", "event_type"):
            if key in record:
                out[key] = record[key]
        return out

    instruction = str(record.get("instruction", "")).strip()
    response = str(record.get("response", "")).strip()
    if not instruction or not response:
        return None
    out = {
        "messages": [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
            {"role": "assistant", "content": response},
        ],
        "source": source_label,
    }
    for key in ("metadata", "category"):
        if key in record:
            out[key] = record[key]
    return out


def dedup_key(record: dict[str, Any]) -> tuple[str, str]:
    messages = record["messages"]
    user = _extract_last_message(messages, "user")
    assistant = _extract_last_message(messages, "assistant")
    return (user.strip().lower(), assistant.strip().lower())


def merge_chat_corpus(inputs: list[Path]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    stats: dict[str, Any] = {
        "input_files": [str(path.relative_to(REPO_ROOT)) for path in inputs],
        "rows_read": 0,
        "rows_written": 0,
        "duplicates_removed": 0,
        "skipped": 0,
        "per_source": Counter(),
    }

    for path in inputs:
        source_label = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        for record in load_jsonl(path):
            stats["rows_read"] += 1
            normalized = normalize_record(record, source_label)
            if normalized is None:
                stats["skipped"] += 1
                continue
            key = dedup_key(normalized)
            if key in seen:
                stats["duplicates_removed"] += 1
                continue
            seen.add(key)
            stats["per_source"][source_label] += 1
            merged.append(normalized)

    stats["rows_written"] = len(merged)
    stats["per_source"] = dict(stats["per_source"])
    return merged, stats


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_sharded_jsonl(base_path: Path, rows: list[dict[str, Any]], shard_lines: int) -> list[str]:
    shard_dir = base_path.with_suffix("")
    shard_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    shard_index = 1
    for start in range(0, len(rows), shard_lines):
        chunk = rows[start : start + shard_lines]
        shard_path = shard_dir / f"part-{shard_index:04d}.jsonl"
        with shard_path.open("w", encoding="utf-8") as handle:
            for row in chunk:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        written.append(str(shard_path.relative_to(REPO_ROOT)).replace("\\", "/"))
        shard_index += 1
    return written


def write_summary(path: Path, stats: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(stats, handle, ensure_ascii=False, indent=2)


def main() -> int:
    args = parse_args()
    inputs = [Path(path) for path in args.inputs] if args.inputs else list(DEFAULT_INPUTS)
    merged, stats = merge_chat_corpus(inputs)
    output_path = Path(args.output)
    summary_path = Path(args.summary)
    if args.shard_lines > 0:
        stats["sharded"] = True
        stats["shard_lines"] = args.shard_lines
        stats["shards"] = write_sharded_jsonl(output_path, merged, args.shard_lines)
        stats["output_dir"] = str(output_path.with_suffix(""))
    else:
        write_jsonl(output_path, merged)
        stats["sharded"] = False
    write_summary(summary_path, stats)

    print(json.dumps({"output": str(output_path), "summary": str(summary_path), **stats}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
