#!/usr/bin/env python3
"""Query the local World Anvil lore SQLite FTS index."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query local lore index.")
    parser.add_argument("--repo-root", default="C:/Users/issda/SCBE-AETHERMOORE")
    parser.add_argument("--db", default="artifacts/lore_rag/world_anvil_lore.sqlite")
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--jsonl", action="store_true", help="Print one JSON row per result.")
    return parser.parse_args()


def resolve_path(repo_root: Path, maybe_rel: str) -> Path:
    p = Path(maybe_rel)
    return p if p.is_absolute() else repo_root / p


def configure_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def print_json(payload: dict, *, indent: int | None = 2) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=indent)
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("utf-8", errors="replace").decode("utf-8", errors="replace"))


def run_query(db_path: Path, query: str, top_k: int) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
              c.id AS chunk_id,
              d.id AS doc_id,
              d.title AS title,
              d.source_path AS source_path,
              d.source_type AS source_type,
              d.source_url AS source_url,
              d.category AS category,
              c.chunk_index AS chunk_index,
              c.content AS content,
              bm25(chunks_fts) AS rank
            FROM chunks_fts
            JOIN chunks c ON c.id = chunks_fts.rowid
            JOIN documents d ON d.id = c.doc_id
            WHERE chunks_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, top_k),
        ).fetchall()
    finally:
        conn.close()

    out: list[dict] = []
    for row in rows:
        out.append(
            {
                "chunk_id": row["chunk_id"],
                "doc_id": row["doc_id"],
                "title": row["title"],
                "source_path": row["source_path"],
                "source_type": row["source_type"],
                "source_url": row["source_url"],
                "category": row["category"],
                "chunk_index": row["chunk_index"],
                "rank": row["rank"],
                "snippet": (row["content"][:560] + "...") if len(row["content"]) > 560 else row["content"],
                "citation": f"{row['title']} [{Path(row['source_path']).name}#chunk{row['chunk_index']}]",
            }
        )
    return out


def main() -> int:
    args = parse_args()
    configure_stdout()
    repo_root = Path(args.repo_root).resolve()
    db_path = resolve_path(repo_root, args.db)
    if not db_path.exists():
        print_json({"ok": False, "error": f"DB not found: {db_path}"})
        return 1

    results = run_query(db_path, args.query, args.top_k)
    if args.jsonl:
        for row in results:
            print_json(row, indent=None)
        return 0

    payload = {
        "ok": True,
        "query": args.query,
        "count": len(results),
        "results": results,
    }
    print_json(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
