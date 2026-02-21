#!/usr/bin/env python3
"""Ingest local docs into JSONL training records for node-fleet training."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
import re


TEXT_SUFFIXES = {".md", ".txt", ".rst", ".yaml", ".yml", ".json"}

FLAVOR_TERMS = (
    "sweet",
    "bitter",
    "sour",
    "salty",
    "umami",
    "spicy",
    "savory",
    "metallic",
)

SCENT_TERMS = (
    "floral",
    "earthy",
    "smoky",
    "citrus",
    "ozone",
    "mint",
    "musk",
    "clean",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest docs into training JSONL")
    parser.add_argument("--glob", action="append", required=True, help="Input glob pattern (repeatable)")
    parser.add_argument("--out", required=True, help="Output JSONL path")
    parser.add_argument("--chunk-size", type=int, default=1400)
    parser.add_argument("--overlap", type=int, default=250)
    return parser.parse_args()


def chunk_text(text: str, chunk_size: int, overlap: int) -> Iterable[str]:
    text = " ".join(text.split())
    if not text:
        return []
    step = max(1, chunk_size - overlap)
    chunks = []
    for i in range(0, len(text), step):
        chunk = text[i : i + chunk_size].strip()
        if len(chunk) >= 40:
            chunks.append(chunk)
    return chunks


def _count_terms(text: str, terms: tuple[str, ...]) -> list[float]:
    lowered = text.lower()
    counts: list[float] = []
    for term in terms:
        counts.append(float(len(re.findall(rf"\b{re.escape(term)}\b", lowered))))
    total = sum(counts)
    if total <= 0:
        return [0.0 for _ in terms]
    return [c / total for c in counts]


def extract_synesthesia_features(text: str) -> dict:
    flavor_vec = _count_terms(text, FLAVOR_TERMS)
    scent_vec = _count_terms(text, SCENT_TERMS)
    non_zero = sum(1 for v in flavor_vec + scent_vec if v > 0.0)
    confidence = non_zero / max(1, (len(flavor_vec) + len(scent_vec)))
    return {
        "flavor": flavor_vec,
        "scent": scent_vec,
        "synesthesia_confidence": confidence,
    }


def read_ipynb(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:  # noqa: BLE001
        return ""
    cells = payload.get("cells", [])
    parts: list[str] = []
    for cell in cells:
        if not isinstance(cell, dict):
            continue
        src = cell.get("source", [])
        if isinstance(src, list):
            parts.append("".join(str(x) for x in src))
        else:
            parts.append(str(src))
    return "\n".join(parts).strip()


def read_text(path: Path) -> str:
    if path.suffix.lower() == ".ipynb":
        return read_ipynb(path)
    if path.suffix.lower() in TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8", errors="ignore")
    return ""


def main() -> int:
    args = parse_args()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    files: list[Path] = []
    for pattern in args.glob:
        files.extend(sorted(Path(".").glob(pattern)))
    files = [p for p in files if p.is_file()]

    total = 0
    with out_path.open("w", encoding="utf-8") as f:
        for path in files:
            text = read_text(path)
            if not text:
                continue
            for idx, chunk in enumerate(chunk_text(text, args.chunk_size, args.overlap)):
                syn = extract_synesthesia_features(chunk)
                row = {
                    "event_type": "doc_chunk",
                    "dataset": "node_fleet_docs",
                    "source_path": str(path).replace("\\", "/"),
                    "chunk_index": idx,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "source_text": chunk,
                    "context_embedding": syn,
                }
                f.write(json.dumps(row, ensure_ascii=True) + "\n")
                total += 1

    print(f"Ingest completed: {total} chunks -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
