#!/usr/bin/env python3
"""Build a local SQLite FTS index from World Anvil exports and lore docs."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TEXT_EXTS = {".md", ".txt", ".rst"}
JSON_EXTS = {".json"}


@dataclass
class Record:
    title: str
    content: str
    source_path: str
    source_type: str
    url: str = ""
    tags: list[str] | None = None
    category: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build lore RAG index from World Anvil exports/docs.")
    parser.add_argument("--repo-root", default="C:/Users/issda/SCBE-AETHERMOORE")
    parser.add_argument(
        "--inputs",
        nargs="+",
        default=["exports/world_anvil", "docs", "notes"],
        help="Input directories or files (relative to repo-root unless absolute).",
    )
    parser.add_argument("--db", default="artifacts/lore_rag/world_anvil_lore.sqlite")
    parser.add_argument("--chunk-chars", type=int, default=1200)
    parser.add_argument("--overlap-chars", type=int, default=200)
    parser.add_argument("--min-chars", type=int, default=120)
    parser.add_argument("--limit-files", type=int, default=0, help="0 = no limit.")
    return parser.parse_args()


def resolve_path(repo_root: Path, maybe_rel: str) -> Path:
    p = Path(maybe_rel)
    return p if p.is_absolute() else repo_root / p


def clean_text(text: str) -> str:
    t = text.replace("\r\n", "\n")
    t = re.sub(r"```[\s\S]*?```", "", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", t)
    t = re.sub(r"^#{1,6}\s*", "", t, flags=re.MULTILINE)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip()


def chunk_text(text: str, chunk_chars: int, overlap_chars: int, min_chars: int) -> list[str]:
    clean = clean_text(text)
    if len(clean) <= chunk_chars:
        return [clean] if len(clean) >= min_chars else []

    chunks: list[str] = []
    start = 0
    n = len(clean)
    step = max(chunk_chars - overlap_chars, 1)

    while start < n:
        end = min(start + chunk_chars, n)
        window = clean[start:end]
        if end < n:
            split = max(window.rfind("\n\n"), window.rfind(". "), window.rfind("; "), window.rfind(", "))
            if split > 200:
                end = start + split + 1
                window = clean[start:end]

        if len(window.strip()) >= min_chars:
            chunks.append(window.strip())

        if end >= n:
            break
        start = max(end - overlap_chars, start + step)

    return chunks


def try_json_record(obj: dict[str, Any], source_path: str) -> Record | None:
    title = (
        str(obj.get("title") or obj.get("name") or obj.get("slug") or obj.get("_id") or "").strip()
    )
    body = (
        obj.get("content")
        or obj.get("body")
        or obj.get("text")
        or obj.get("description")
        or obj.get("excerpt")
        or obj.get("markdown")
        or ""
    )
    if isinstance(body, (dict, list)):
        body = json.dumps(body, ensure_ascii=False)
    body = str(body).strip()

    if not title and not body:
        return None

    tags_raw = obj.get("tags") or obj.get("tag") or []
    tags: list[str] = []
    if isinstance(tags_raw, list):
        tags = [str(x) for x in tags_raw if str(x).strip()]
    elif isinstance(tags_raw, str) and tags_raw.strip():
        tags = [x.strip() for x in tags_raw.split(",") if x.strip()]

    return Record(
        title=title or Path(source_path).stem,
        content=body or json.dumps(obj, ensure_ascii=False),
        source_path=source_path,
        source_type="world_anvil_json",
        url=str(obj.get("url") or obj.get("permalink") or ""),
        tags=tags,
        category=str(obj.get("category") or obj.get("type") or ""),
    )


def extract_records_from_json(payload: Any, source_path: str) -> list[Record]:
    out: list[Record] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            rec = try_json_record(node, source_path)
            if rec and rec.content:
                out.append(rec)
            for value in node.values():
                if isinstance(value, (dict, list)):
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    dedup: dict[tuple[str, str], Record] = {}
    for rec in out:
        key = (rec.title, rec.content[:120])
        dedup[key] = rec
    return list(dedup.values())


def collect_files(paths: list[Path], limit_files: int) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_file():
            files.append(p)
            continue
        if not p.exists():
            continue
        for ext in list(TEXT_EXTS | JSON_EXTS):
            files.extend(p.rglob(f"*{ext}"))

    files = sorted(set(files))
    if limit_files > 0:
        files = files[:limit_files]
    return files


def file_to_records(path: Path) -> list[Record]:
    ext = path.suffix.lower()
    if ext in TEXT_EXTS:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return [
            Record(
                title=path.stem.replace("-", " ").replace("_", " ").strip(),
                content=text,
                source_path=str(path),
                source_type=ext.lstrip("."),
            )
        ]

    if ext in JSON_EXTS:
        try:
            payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except json.JSONDecodeError:
            return []
        return extract_records_from_json(payload, str(path))

    return []


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT NOT NULL,
          source_path TEXT NOT NULL,
          source_type TEXT NOT NULL,
          source_url TEXT DEFAULT '',
          category TEXT DEFAULT '',
          tags_json TEXT DEFAULT '[]',
          created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          doc_id INTEGER NOT NULL,
          chunk_index INTEGER NOT NULL,
          content TEXT NOT NULL,
          char_len INTEGER NOT NULL,
          meta_json TEXT DEFAULT '{}',
          FOREIGN KEY(doc_id) REFERENCES documents(id)
        )
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
          content,
          chunk_id UNINDEXED,
          doc_id UNINDEXED
        )
        """
    )
    conn.commit()


def clear_db(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM chunks_fts")
    conn.execute("DELETE FROM chunks")
    conn.execute("DELETE FROM documents")
    conn.commit()


def build_index(
    files: list[Path],
    conn: sqlite3.Connection,
    chunk_chars: int,
    overlap_chars: int,
    min_chars: int,
) -> dict[str, int]:
    docs = 0
    chunks = 0
    skipped = 0

    for file_path in files:
        records = file_to_records(file_path)
        if not records:
            skipped += 1
            continue

        for record in records:
            text_chunks = chunk_text(record.content, chunk_chars, overlap_chars, min_chars)
            if not text_chunks:
                continue

            cur = conn.execute(
                """
                INSERT INTO documents (title, source_path, source_type, source_url, category, tags_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.title[:500],
                    record.source_path,
                    record.source_type,
                    record.url,
                    record.category,
                    json.dumps(record.tags or []),
                    utc_now(),
                ),
            )
            doc_id = int(cur.lastrowid)
            docs += 1

            for idx, chunk in enumerate(text_chunks):
                meta = {"title": record.title, "source_path": record.source_path, "category": record.category}
                cur2 = conn.execute(
                    """
                    INSERT INTO chunks (doc_id, chunk_index, content, char_len, meta_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (doc_id, idx, chunk, len(chunk), json.dumps(meta, ensure_ascii=False)),
                )
                chunk_id = int(cur2.lastrowid)
                conn.execute(
                    "INSERT INTO chunks_fts (rowid, content, chunk_id, doc_id) VALUES (?, ?, ?, ?)",
                    (chunk_id, chunk, chunk_id, doc_id),
                )
                chunks += 1

    conn.commit()
    return {"documents": docs, "chunks": chunks, "skipped_files": skipped}


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    input_paths = [resolve_path(repo_root, p) for p in args.inputs]
    db_path = resolve_path(repo_root, args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    files = collect_files(input_paths, args.limit_files)
    conn = sqlite3.connect(db_path)
    try:
        init_db(conn)
        clear_db(conn)
        stats = build_index(files, conn, args.chunk_chars, args.overlap_chars, args.min_chars)
    finally:
        conn.close()

    payload = {
        "ok": True,
        "repo_root": str(repo_root),
        "db": str(db_path),
        "files_indexed": len(files),
        **stats,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
