#!/usr/bin/env python3
"""
Convert Isekai/Story markdown into SCBE SFT training records.

Default source:
  training/notion_ingest/iseki_story_notion_api_20260218.md

Default output:
  training-data/sft_iseki.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert Isekai markdown to SFT JSONL")
    parser.add_argument(
        "--input",
        default="training/notion_ingest/iseki_story_notion_api_20260218.md",
        help="Input markdown file",
    )
    parser.add_argument(
        "--output",
        default="training-data/sft_iseki.jsonl",
        help="Output JSONL file",
    )
    parser.add_argument(
        "--max-response-chars",
        type=int,
        default=3800,
        help="Maximum response length per record",
    )
    parser.add_argument(
        "--min-section-chars",
        type=int,
        default=120,
        help="Skip sections shorter than this length",
    )
    return parser.parse_args()


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_sections(markdown: str) -> list[tuple[str, str]]:
    """
    Split markdown by heading lines and return (title, body) sections.
    """
    heading_re = re.compile(r"(?m)^#{1,3}\s+(.+?)\s*$")
    matches = list(heading_re.finditer(markdown))
    if not matches:
        return [("Isekai Story Corpus", clean_text(markdown))]

    sections: list[tuple[str, str]] = []
    for i, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        body = clean_text(markdown[start:end])
        if body:
            sections.append((title, body))
    return sections


def categorize(title: str, body: str) -> str:
    combined = f"{title}\n{body}".lower()
    if any(k in combined for k in ("layer", "hyperbolic", "fft", "coherence", "governance", "pqc")):
        return "story-tech-mapping"
    if any(k in combined for k in ("chapter", "marcus", "polly", "academy", "aethermoor")):
        return "story-lore"
    return "story-protocol"


def make_instruction(title: str, category: str) -> str:
    if category == "story-tech-mapping":
        return f"Explain how '{title}' maps story elements to SCBE-AETHERMOORE technical architecture."
    if category == "story-lore":
        return f"Summarize '{title}' and its role in The Six Tongues Protocol narrative."
    return f"Explain '{title}' in the context of the Six Tongues Protocol."


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    chunk = text[:limit]
    cut = chunk.rfind(". ")
    if cut > limit // 2:
        return chunk[: cut + 1]
    return chunk.rstrip() + "..."


def convert(markdown: str, max_chars: int, min_chars: int) -> list[dict]:
    records: list[dict] = []
    sections = split_sections(markdown)
    for title, body in sections:
        if len(body) < min_chars:
            continue
        category = categorize(title, body)
        records.append(
            {
                "category": category,
                "instruction": make_instruction(title, category),
                "response": truncate(body, max_chars),
                "metadata": {
                    "source": "scbe_aethermoore",
                    "version": "3.3.0",
                    "author": "Issac Davis",
                    "origin": "notion_iseki_markdown",
                    "original_title": title,
                },
            }
        )
    for i, record in enumerate(records, start=1):
        record["id"] = f"sft-iseki-{i:04d}"
    return records


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input markdown not found: {input_path}")

    text = input_path.read_text(encoding="utf-8", errors="replace")
    records = convert(text, args.max_response_chars, args.min_section_chars)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "input": str(input_path).replace("\\", "/"),
                "output": str(output_path).replace("\\", "/"),
                "records": len(records),
            }
        )
    )


if __name__ == "__main__":
    main()
