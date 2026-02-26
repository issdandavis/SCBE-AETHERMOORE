#!/usr/bin/env python3
"""
Auto-tag normalized Perplexity JSONL records with SCBE domain tags.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_INPUT = "data/perplexity/normalized/perplexity_normalized.jsonl"
DEFAULT_OUTPUT = "data/perplexity/normalized/perplexity_tagged.jsonl"
DEFAULT_STATS = "data/perplexity/normalized/tag_stats.json"


TAG_RULES: dict[str, tuple[str, ...]] = {
    "scbe": (
        "scbe",
        "aethermoore",
        "aethermoor",
        "hydra",
        "geoseal",
        "sacred tongue",
        "spiral seal",
    ),
    "spiralverse": (
        "spiralverse",
        "soliton",
        "harmonic wall",
        "poincare",
        "hyperbolic",
        "tongues",
    ),
    "math": (
        "equation",
        "proof",
        "theorem",
        "matrix",
        "vector",
        "geometry",
        "calculus",
        "acosh",
        "phi",
        "pi^",
    ),
    "lore": (
        "lore",
        "canon",
        "myth",
        "ritual",
        "glyph",
        "codex",
        "realm",
        "aether",
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auto-tag normalized Perplexity JSONL records.")
    parser.add_argument("--input-jsonl", default=DEFAULT_INPUT)
    parser.add_argument("--output-jsonl", default=DEFAULT_OUTPUT)
    parser.add_argument("--output-stats", default=DEFAULT_STATS)
    return parser.parse_args()


def infer_tags(record: dict[str, Any]) -> list[str]:
    text = " ".join(
        [
            str(record.get("title", "")),
            str(record.get("label", "")),
            str(record.get("text", "")),
            str(record.get("content", "")),
        ]
    ).lower()
    text = re.sub(r"\s+", " ", text)

    tags = set(str(x).strip().lower() for x in (record.get("tags") or []) if str(x).strip())
    for tag, keywords in TAG_RULES.items():
        if any(keyword in text for keyword in keywords):
            tags.add(tag)
    return sorted(tags)


def tag_dataset(input_jsonl: Path, output_jsonl: Path, output_stats: Path) -> dict[str, Any]:
    if not input_jsonl.exists():
        raise FileNotFoundError(f"Input JSONL not found: {input_jsonl}")
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    output_stats.parent.mkdir(parents=True, exist_ok=True)

    rows_in = 0
    rows_out = 0
    tag_counts: dict[str, int] = {}

    with input_jsonl.open("r", encoding="utf-8") as src, output_jsonl.open(
        "w", encoding="utf-8", newline="\n"
    ) as dst:
        for line in src:
            line = line.strip()
            if not line:
                continue
            rows_in += 1
            try:
                row = json.loads(line)
            except Exception:  # noqa: BLE001
                continue

            tags = infer_tags(row)
            row["tags"] = tags
            row["tagged_at"] = utc_now()
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

            dst.write(json.dumps(row, ensure_ascii=False) + "\n")
            rows_out += 1

    stats = {
        "generated_at": utc_now(),
        "input_jsonl": str(input_jsonl),
        "output_jsonl": str(output_jsonl),
        "rows_in": rows_in,
        "rows_out": rows_out,
        "tag_counts": tag_counts,
    }
    output_stats.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


def main() -> int:
    args = parse_args()
    try:
        stats = tag_dataset(
            input_jsonl=Path(args.input_jsonl),
            output_jsonl=Path(args.output_jsonl),
            output_stats=Path(args.output_stats),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[tag_perplexity_dataset] ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    main()

