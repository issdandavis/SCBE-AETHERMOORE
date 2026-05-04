"""Build a personal RAG index from SCBE docs and notes.

Converts markdown files into JSONL records, then calls build_rag_index.py
or builds a simple hash-based index for fast local search.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, List

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = [
    REPO_ROOT / "docs",
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "README.md",
    REPO_ROOT / "config",
]
OUTPUT_JSONL = REPO_ROOT / "training-data" / "personal_rag.jsonl"
INDEX_DIR = REPO_ROOT / "artifacts" / "personal_rag_index"


def slugify(text: str) -> str:
    return re.sub(r"[^\w]+", "_", text).strip("_").lower()[:60]


def split_markdown_sections(path: Path, text: str) -> List[dict[str, Any]]:
    """Split a markdown file into sections by ## headings."""
    sections = []
    current_title = path.stem
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("## "):
            if current_lines:
                body = "\n".join(current_lines).strip()
                if len(body) >= 80:
                    sections.append({
                        "id": f"{slugify(path.stem)}__{slugify(current_title)}",
                        "source": str(path.relative_to(REPO_ROOT)),
                        "title": current_title,
                        "text": body,
                    })
            current_title = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        body = "\n".join(current_lines).strip()
        if len(body) >= 80:
            sections.append({
                "id": f"{slugify(path.stem)}__{slugify(current_title)}",
                "source": str(path.relative_to(REPO_ROOT)),
                "title": current_title,
                "text": body,
            })
    return sections


def main() -> None:
    all_sections: list[dict[str, Any]] = []

    for src in SOURCE_DIRS:
        if src.is_file() and src.suffix == ".md":
            paths = [src]
        elif src.is_dir():
            paths = list(src.rglob("*.md"))
        else:
            continue

        for path in paths:
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            # Skip very small files
            if len(text) < 200:
                continue
            sections = split_markdown_sections(path, text)
            all_sections.extend(sections)

    # Deduplicate by id
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for sec in all_sections:
        if sec["id"] not in seen:
            seen.add(sec["id"])
            deduped.append(sec)

    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_JSONL.open("w", encoding="utf-8", newline="\n") as fh:
        for sec in deduped:
            fh.write(json.dumps(sec, ensure_ascii=False, sort_keys=True) + "\n")

    print(f"Wrote {len(deduped)} sections to {OUTPUT_JSONL}")

    # Build hash-based index (no sentence-transformers required)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    index_path = INDEX_DIR / "hash_index.json"
    index: dict[str, Any] = {
        "schema_version": "scbe_personal_rag_v1",
        "count": len(deduped),
        "records": deduped,
    }
    with index_path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=2)

    print(f"Hash index: {index_path}")

    # Try building semantic index if sentence-transformers is available
    try:
        import subprocess
        subprocess.run([
            sys.executable, "scripts/build_rag_index.py",
            "--input-jsonl", str(OUTPUT_JSONL),
            "--output-dir", str(INDEX_DIR / "semantic"),
            "--text-fields", "text",
            "--id-fields", "id",
            "--backend", "hash",
        ], check=True, capture_output=True)
        print("Semantic hash index built.")
    except Exception as exc:
        print(f"Semantic index skipped: {exc}")


if __name__ == "__main__":
    import sys
    main()
