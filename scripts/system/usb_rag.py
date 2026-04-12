"""
USB RAG — SQLite FTS5 knowledge base on F:/scbe-rag/

Usage:
  python scripts/system/usb_rag.py ingest          # index all master files
  python scripts/system/usb_rag.py query "n8n bridge routes"
  python scripts/system/usb_rag.py query "governance gate" --top 5
  python scripts/system/usb_rag.py list             # show what's indexed
  python scripts/system/usb_rag.py add <path>       # add a specific file
"""

import sys
import os
import sqlite3
import hashlib
import datetime
import argparse
from pathlib import Path

RAG_DIR = Path("F:/scbe-rag")
DB_PATH = RAG_DIR / "index.db"

# Master file sources — these are the canonical files worth keeping
MASTER_SOURCES = [
    # Docs
    ("C:/Users/issda/SCBE-AETHERMOORE/CLAUDE.md", "docs"),
    ("C:/Users/issda/SCBE-AETHERMOORE/SPEC.md", "docs"),
    ("C:/Users/issda/SCBE-AETHERMOORE/SYSTEM_ARCHITECTURE.md", "docs"),
    ("C:/Users/issda/SCBE-AETHERMOORE/LAYER_INDEX.md", "docs"),
    ("C:/Users/issda/CLAUDE.md", "docs"),
    # Key docs folder
    ("C:/Users/issda/SCBE-AETHERMOORE/docs/M5_MESH_PRODUCT_SERVICE_BLUEPRINT.md", "product"),
    ("C:/Users/issda/SCBE-AETHERMOORE/docs/M6_SEED_MULTI_NODAL_NETWORK_SPEC.md", "product"),
    ("C:/Users/issda/SCBE-AETHERMOORE/docs/SCBE_BOOTSTRAP_RUNBOOK.md", "ops"),
    ("C:/Users/issda/SCBE-AETHERMOORE/docs/N8N_LOCAL_STACK_RUNBOOK.md", "ops"),
    ("C:/Users/issda/SCBE-AETHERMOORE/docs/LANGUES_WEIGHTING_SYSTEM.md", "architecture"),
    ("C:/Users/issda/SCBE-AETHERMOORE/docs/PUBLISHING.md", "ops"),
    ("C:/Users/issda/SCBE-AETHERMOORE/docs/API.md", "architecture"),
    # Agents
    ("C:/Users/issda/SCBE-AETHERMOORE/.claude/agents/dry-run-specialist.md", "agents"),
    # Key source files (small enough to be useful as reference)
    ("C:/Users/issda/SCBE-AETHERMOORE/workflows/n8n/scbe_n8n_bridge.py", "workflows"),
    ("C:/Users/issda/SCBE-AETHERMOORE/src/geoseal_cli.py", "core"),
    ("C:/Users/issda/SCBE-AETHERMOORE/src/governance/runtime_gate.py", "core"),
    # Config
    ("C:/Users/issda/SCBE-AETHERMOORE/pytest.ini", "config"),
    ("C:/Users/issda/SCBE-AETHERMOORE/vitest.config.ts", "config"),
    ("C:/Users/issda/SCBE-AETHERMOORE/package.json", "config"),
]

# Directories to sweep for training manifests and workflow JSONs
SWEEP_DIRS = [
    ("C:/Users/issda/SCBE-AETHERMOORE/workflows/n8n", "workflows", [".json", ".py", ".md"]),
    ("C:/Users/issda/SCBE-AETHERMOORE/docs", "docs", [".md"]),
    ("C:/Users/issda/SCBE-AETHERMOORE/.claude/agents", "agents", [".md"]),
    ("C:/Users/issda/SCBE-AETHERMOORE/config", "config", [".json", ".yaml", ".yml", ".md"]),
]


def get_db():
    RAG_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(
            path,
            category,
            title,
            content,
            file_hash,
            indexed_at,
            tokenize='porter unicode61'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            path TEXT PRIMARY KEY,
            file_hash TEXT,
            indexed_at TEXT,
            category TEXT,
            size_bytes INTEGER
        )
    """)
    conn.commit()
    return conn


def file_hash(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def ingest_file(conn, path_str, category):
    path = Path(path_str)
    if not path.exists():
        print(f"  skip (not found): {path_str}")
        return False

    fhash = file_hash(path)
    row = conn.execute("SELECT file_hash FROM meta WHERE path=?", (path_str,)).fetchone()
    if row and row[0] == fhash:
        return False  # unchanged

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"  skip (read error): {path_str}: {e}")
        return False

    title = path.name
    now = datetime.datetime.now().isoformat()
    size = path.stat().st_size

    # Remove old entry if exists
    conn.execute("DELETE FROM docs WHERE path=?", (path_str,))
    conn.execute(
        "INSERT INTO docs(path, category, title, content, file_hash, indexed_at) VALUES (?,?,?,?,?,?)",
        (path_str, category, title, content, fhash, now),
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta(path, file_hash, indexed_at, category, size_bytes) VALUES (?,?,?,?,?)",
        (path_str, fhash, now, category, size),
    )
    return True


def cmd_ingest(conn, extra_path=None, extra_category="custom"):
    print("Indexing master files...")
    added = 0
    skipped = 0

    sources = list(MASTER_SOURCES)
    if extra_path:
        sources.append((extra_path, extra_category))

    for path_str, category in sources:
        result = ingest_file(conn, path_str, category)
        if result:
            print(f"  + [{category}] {Path(path_str).name}")
            added += 1
        else:
            skipped += 1

    # Sweep directories
    for dir_path, category, exts in SWEEP_DIRS:
        d = Path(dir_path)
        if not d.exists():
            continue
        for fp in d.rglob("*"):
            if fp.is_file() and fp.suffix in exts and fp.stat().st_size < 2_000_000:
                # Skip if already in MASTER_SOURCES
                if str(fp) in [s[0] for s in MASTER_SOURCES]:
                    continue
                result = ingest_file(conn, str(fp), category)
                if result:
                    print(f"  + [{category}] {fp.name}")
                    added += 1
                else:
                    skipped += 1

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM meta").fetchone()[0]
    print(f"\nDone. Added/updated: {added}, unchanged: {skipped}, total in index: {total}")


def cmd_query(conn, query, top=5):
    rows = conn.execute(
        """
        SELECT path, category, title, snippet(docs, 3, '[', ']', '...', 32)
        FROM docs
        WHERE docs MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (query, top),
    ).fetchall()

    if not rows:
        print(f"No results for: {query}")
        return

    print(f"\nResults for '{query}':\n")
    for i, (path, category, title, snippet) in enumerate(rows, 1):
        print(f"  {i}. [{category}] {title}")
        print(f"     {path}")
        print(f"     ...{snippet}...")
        print()


def cmd_list(conn):
    rows = conn.execute(
        "SELECT category, COUNT(*) as n, SUM(size_bytes)/1024 as kb FROM meta GROUP BY category ORDER BY n DESC"
    ).fetchall()
    total = conn.execute("SELECT COUNT(*), SUM(size_bytes)/1024 FROM meta").fetchone()
    print(f"\nUSB RAG Index — {DB_PATH}")
    print(f"{'Category':<20} {'Files':>6} {'Size':>10}")
    print("-" * 40)
    for cat, n, kb in rows:
        print(f"  {cat:<18} {n:>6} {kb or 0:>8} KB")
    print("-" * 40)
    print(f"  {'TOTAL':<18} {total[0]:>6} {total[1] or 0:>8} KB")


def main():
    parser = argparse.ArgumentParser(description="USB RAG — SCBE knowledge base on F: drive")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("ingest", help="Index all master files")
    sub.add_parser("list", help="Show indexed files by category")

    q = sub.add_parser("query", help="Search the index")
    q.add_argument("terms", nargs="+", help="Search terms")
    q.add_argument("--top", type=int, default=5, help="Number of results")

    a = sub.add_parser("add", help="Add a specific file")
    a.add_argument("path", help="File path to add")
    a.add_argument("--category", default="custom", help="Category label")

    args = parser.parse_args()
    conn = get_db()

    if args.cmd == "ingest":
        cmd_ingest(conn)
    elif args.cmd == "query":
        cmd_query(conn, " ".join(args.terms), args.top)
    elif args.cmd == "list":
        cmd_list(conn)
    elif args.cmd == "add":
        cmd_ingest(conn, extra_path=args.path, extra_category=args.category)
    else:
        parser.print_help()

    conn.close()


if __name__ == "__main__":
    main()
