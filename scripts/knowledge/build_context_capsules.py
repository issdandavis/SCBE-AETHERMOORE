#!/usr/bin/env python3
"""
Build compact context capsules for Codex sessions.

Goal:
- Keep active context to 1-5 windows.
- Preserve a large local knowledge base for retrieval.
- Emit deterministic capsules from high-signal connector sources.

Outputs:
- training/context_capsules/library_chunks.jsonl
- training/context_capsules/capsule_1w.json
- training/context_capsules/capsule_3w.json
- training/context_capsules/capsule_5w.json
- training/context_capsules/manifest.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LIBRARY_PATH = PROJECT_ROOT / "src" / "knowledge" / "storage" / "open_source_api_library.json"
OUT_DIR = PROJECT_ROOT / "training" / "context_capsules"

TOKEN_RE = re.compile(r"[a-zA-Z0-9_\-\.]+")


@dataclass
class Chunk:
    chunk_id: str
    title: str
    text: str
    docs_url: str
    category: str
    score: float = 0.0


DEFAULT_QUERY = (
    "aether browser connectors rag arxiv wikidata nvd mit dataverse "
    "knowledge library governance memory graph"
)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def load_connectors(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    connectors = payload.get("connectors", [])
    if not isinstance(connectors, list):
        raise ValueError("connectors must be a list")
    return connectors


def to_chunks(connectors: Iterable[dict]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for c in connectors:
        best_for = ", ".join(c.get("best_for", []))
        constraints = "; ".join(c.get("constraints", []))
        text = (
            f"{c.get('name', '')}. "
            f"Category: {c.get('category', '')}. "
            f"Base URL: {c.get('base_url', '')}. "
            f"Auth: {c.get('auth', '')}. "
            f"Best for: {best_for}. "
            f"Constraints: {constraints}."
        )
        chunks.append(
            Chunk(
                chunk_id=c.get("id", "unknown"),
                title=c.get("name", "unknown"),
                text=text,
                docs_url=c.get("docs_url", ""),
                category=c.get("category", "unknown"),
            )
        )
    return chunks


def score_chunks(chunks: list[Chunk], query: str) -> list[Chunk]:
    q_tokens = tokenize(query)
    q_set = set(q_tokens)

    for chunk in chunks:
        c_tokens = tokenize(chunk.text)
        overlap = sum(1 for t in c_tokens if t in q_set)

        # Category and name boosts for higher precision with small windows.
        category_boost = 0.0
        if chunk.category in {"academic", "knowledge_graph", "security", "datasets"}:
            category_boost += 2.0
        if any(key in chunk.title.lower() for key in ["arxiv", "wikidata", "nvd", "dataverse", "openalex"]):
            category_boost += 2.0

        length_penalty = max(1.0, len(c_tokens) / 120.0)
        chunk.score = (overlap + category_boost) / length_penalty

    return sorted(chunks, key=lambda c: c.score, reverse=True)


def write_chunks_jsonl(chunks: list[Chunk], out_path: Path) -> None:
    lines = []
    for c in chunks:
        lines.append(
            json.dumps(
                {
                    "chunk_id": c.chunk_id,
                    "title": c.title,
                    "category": c.category,
                    "docs_url": c.docs_url,
                    "score": round(c.score, 4),
                    "text": c.text,
                },
                ensure_ascii=False,
            )
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_capsule(scored: list[Chunk], query: str, windows: int) -> dict:
    selected = scored[:windows]
    context_blocks = []
    sources = []

    for i, c in enumerate(selected, start=1):
        context_blocks.append(f"[{i}] {c.title}\n{c.text}\nSource: {c.docs_url}")
        sources.append(
            {
                "chunk_id": c.chunk_id,
                "title": c.title,
                "category": c.category,
                "docs_url": c.docs_url,
                "score": round(c.score, 4),
            }
        )

    return {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "query": query,
        "window_count": windows,
        "sources": sources,
        "context_text": "\n\n".join(context_blocks),
        "usage": {
            "load_first": f"capsule_{windows}w.json",
            "then_retrieve_from": "library_chunks.jsonl",
            "intent": "small active context, large retrieval memory",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build compact context capsules from the open API library")
    parser.add_argument("--library", type=Path, default=LIBRARY_PATH)
    parser.add_argument("--query", type=str, default=DEFAULT_QUERY)
    parser.add_argument("--windows", type=int, nargs="+", default=[1, 3, 5])
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    connectors = load_connectors(args.library)
    chunks = to_chunks(connectors)
    scored = score_chunks(chunks, args.query)

    chunks_path = args.out_dir / "library_chunks.jsonl"
    write_chunks_jsonl(scored, chunks_path)

    manifest = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "library": str(args.library),
        "query": args.query,
        "connector_count": len(connectors),
        "chunk_count": len(scored),
        "windows_generated": args.windows,
        "files": ["library_chunks.jsonl"],
    }

    for w in args.windows:
        if w < 1:
            continue
        capsule = build_capsule(scored, args.query, w)
        capsule_path = args.out_dir / f"capsule_{w}w.json"
        capsule_path.write_text(json.dumps(capsule, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        manifest["files"].append(capsule_path.name)

    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
