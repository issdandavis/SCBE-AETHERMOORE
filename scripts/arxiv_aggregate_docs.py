#!/usr/bin/env python3
"""Aggregate repo documentation into a compact JSON bundle for arXiv drafting."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

ALLOWED_SUFFIXES = {".md", ".tex", ".txt"}
DEFAULT_INCLUDE = ["README.md", "docs", "paper"]
DEFAULT_EXCLUDE_PARTS = {"node_modules", ".git", "dist", "artifacts", "coverage", "venv", ".venv"}


def _iter_files(root: Path, include: Iterable[str]) -> list[Path]:
    out: list[Path] = []
    for entry in include:
        p = root / entry
        if not p.exists():
            continue
        if p.is_file() and p.suffix.lower() in ALLOWED_SUFFIXES:
            out.append(p)
            continue
        if p.is_dir():
            for fp in p.rglob("*"):
                if not fp.is_file() or fp.suffix.lower() not in ALLOWED_SUFFIXES:
                    continue
                if any(part in DEFAULT_EXCLUDE_PARTS for part in fp.relative_to(root).parts):
                    continue
                out.append(fp)
    return sorted(set(out))


def _read_trimmed(path: Path, max_chars: int) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if len(raw) <= max_chars:
        return raw
    return raw[:max_chars] + "\n\n[TRUNCATED]"


def aggregate(root: Path, include: list[str], max_chars: int) -> dict:
    files = _iter_files(root, include)
    docs = []
    for fp in files:
        rel = fp.relative_to(root).as_posix()
        docs.append(
            {
                "path": rel,
                "chars": fp.stat().st_size,
                "content": _read_trimmed(fp, max_chars=max_chars),
            }
        )
    return {
        "bundle_version": "1.0.0",
        "project": root.name,
        "doc_count": len(docs),
        "documents": docs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate documentation for arXiv synthesis")
    parser.add_argument("--root", default=".")
    parser.add_argument("--include", nargs="*", default=DEFAULT_INCLUDE)
    parser.add_argument("--max-chars", type=int, default=12000)
    parser.add_argument("--output", default="artifacts/arxiv/aggregated_bundle.json")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    bundle = aggregate(root=root, include=list(args.include), max_chars=args.max_chars)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    print(f"wrote {out} docs={bundle['doc_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
