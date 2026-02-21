#!/usr/bin/env python3
"""
Ingest Spiralverse codex markdown into:
1) verbatim JSONL chunks
2) compact section JSONL chunks

Updates latest pointer files:
- training/ingest/latest_lore_verbatim.txt
- training/ingest/latest_lore_drop.txt
- training/ingest/latest_lore_source.txt
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        default="training/raw/spiralverse_canonical_linguistic_codex_v1_seed_20260218.md",
        help="Path to markdown source.",
    )
    parser.add_argument(
        "--source-url",
        default="local://spiralverse-canonical-linguistic-codex-v1",
        help="Source URL/reference written into JSONL metadata.",
    )
    parser.add_argument(
        "--verbatim-chunk-size",
        type=int,
        default=6000,
        help="Characters per verbatim JSONL chunk.",
    )
    return parser.parse_args()


def split_sections(text: str) -> List[Tuple[str, str]]:
    """Split by roman numeral section headers and chapter markers when present."""
    section_re = re.compile(
        r"(?im)^\s*(?:##\s+)?((?:[IVX]+)\.\s+[^\n]+|Chapter\s+\d+\s*:\s*[^\n]+)\s*$"
    )
    matches = list(section_re.finditer(text))
    if not matches:
        return [("Full text", text.strip())]

    sections: List[Tuple[str, str]] = []
    lead = text[: matches[0].start()].strip()
    if lead:
        sections.append(("Preface", lead))

    for i, m in enumerate(matches):
        title = re.sub(r"\s+", " ", m.group(1)).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            sections.append((title, body))
    return sections


def infer_interest(body: str) -> List[str]:
    lower = body.lower()
    mapping = {
        "tokenizer": "tokenizer",
        "geo seal": "geoseal",
        "geoseal": "geoseal",
        "swarm": "swarm-consensus",
        "fleet": "fleet-dynamics",
        "protocol": "protocol-architecture",
        "runethic": "ru-policy",
        "umbroth": "um-security",
        "draumric": "dr-manifestation",
        "kor’aelin": "ko-intent",
        "cassisivadan": "ca-compute",
        "avali": "av-bridge",
        "canon": "canon-governance",
        "provenance": "provenance-chain",
    }
    tags = [v for k, v in mapping.items() if k in lower]
    if not tags:
        tags = ["spiralverse", "lore", "canon"]
    return tags[:10]


def infer_targets(body: str) -> List[str]:
    lower = body.lower()
    targets = {"doc_plan", "memory_storage"}
    if any(
        k in lower
        for k in (
            "tokenizer",
            "bijection",
            "attestation",
            "selftest",
            "fleet",
            "swarm",
            "security",
            "policy",
            "protocol",
        )
    ):
        targets.add("code_execute")
    return sorted(targets)


def chunk_text(text: str, size: int) -> Iterable[str]:
    for i in range(0, len(text), size):
        yield text[i : i + size]


def main() -> None:
    args = parse_args()
    source = Path(args.source)
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source}")

    ts = datetime.now(timezone.utc)
    stamp = ts.strftime("%Y%m%dT%H%M%SZ")
    generated_at = ts.isoformat()

    text = source.read_text(encoding="utf-8", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        raise RuntimeError(f"Source text is empty: {source}")

    ingest_dir = Path("training/ingest")
    ingest_dir.mkdir(parents=True, exist_ok=True)

    verbatim_path = ingest_dir / f"lore_verbatim_{stamp}.jsonl"
    compact_path = ingest_dir / f"lore_drop_{stamp}.jsonl"

    with verbatim_path.open("w", encoding="utf-8") as f:
        for idx, part in enumerate(chunk_text(text, args.verbatim_chunk_size)):
            rec = {
                "event_type": "doc_chunk",
                "dataset": "node_fleet_docs_verbatim",
                "source_url": args.source_url,
                "source_path": str(source).replace("\\", "/"),
                "chunk_index": idx,
                "generated_at": generated_at,
                "source_text": part,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    sections = split_sections(text)
    with compact_path.open("w", encoding="utf-8") as f:
        for idx, (title, body) in enumerate(sections):
            body_flat = re.sub(r"\s+", " ", body).strip()
            excerpt = body_flat[:2600]
            rec = {
                "event_type": "doc_chunk",
                "dataset": "node_fleet_docs",
                "source_url": args.source_url,
                "source_path": str(source).replace("\\", "/"),
                "chunk_index": idx,
                "generated_at": generated_at,
                "context": title,
                "interest": infer_interest(body),
                "relevancy": 0.99,
                "action_target": infer_targets(body),
                "source_text": f"{title} -- {excerpt}",
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    (ingest_dir / "latest_lore_verbatim.txt").write_text(
        str(verbatim_path).replace("\\", "/"), encoding="utf-8"
    )
    (ingest_dir / "latest_lore_drop.txt").write_text(
        str(compact_path).replace("\\", "/"), encoding="utf-8"
    )
    (ingest_dir / "latest_lore_source.txt").write_text(
        str(source).replace("\\", "/"), encoding="utf-8"
    )

    print(f"Source: {source}")
    print(f"Verbatim JSONL: {verbatim_path}")
    print(f"Compact JSONL: {compact_path}")


if __name__ == "__main__":
    main()

