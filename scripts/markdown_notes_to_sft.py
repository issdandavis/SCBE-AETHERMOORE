#!/usr/bin/env python3
"""Convert markdown notes into SCBE SFT pairs.

This is a direct path from text artifacts (GitHub docs, Obsidian notes, etc.)
to training-ready instruction/response rows.

Usage:
    python scripts/markdown_notes_to_sft.py --out training-data/sft_notes.jsonl
    python scripts/markdown_notes_to_sft.py --glob "docs/**/*.md" --glob "training/**/*.md"
    python scripts/markdown_notes_to_sft.py --obsidian-vault "C:\\Path\\To\\Vault" --out training-data/sft_obsidian_notes.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import glob
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert markdown notes to SFT JSONL")
    parser.add_argument(
        "--out",
        default=str(REPO_ROOT / "training-data" / "sft_notes.jsonl"),
        help="Output JSONL path",
    )
    parser.add_argument(
        "--glob",
        action="append",
        default=[],
        help="Markdown glob pattern(s) to include (repeatable)",
    )
    parser.add_argument(
        "--obsidian-vault",
        default="",
        help="Optional Obsidian vault root to include markdown from",
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Root path for relative globs",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=3200,
        help="Maximum characters per response chunk",
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=120,
        help="Minimum characters required to emit a chunk",
    )
    parser.add_argument(
        "--title-lines",
        type=int,
        default=3,
        help="How many heading-level lines to include in response preface",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="Optional hard cap on total files to process (0 = no cap)",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=0,
        help="Optional hard cap on total output records (0 = no cap)",
    )
    return parser.parse_args()


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4 :].lstrip("\n")
    return text


def detect_heading_segments(text: str) -> list[tuple[str, str]]:
    heading_re = re.compile(r"(?m)^(#{1,6})\s+(.*?)\s*$")
    matches = list(heading_re.finditer(text))
    if not matches:
        return [("", text.strip())]

    segments: list[tuple[str, str]] = []
    for i, match in enumerate(matches):
        title = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[start:end].strip()
        if chunk:
            segments.append((title, chunk))
    return segments


def to_prompt_safe(text: str) -> str:
    return " ".join(text.split())


def chunk_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    cursor = 0
    step = max_chars
    while cursor < len(text):
        end = min(len(text), cursor + step)
        window = text[cursor:end]
        cut = max(
            window.rfind("\n\n"),
            window.rfind(". "),
            window.rfind(".\n"),
        )
        if cut == -1 or cut < max_chars // 3:
            cut = max_chars
        else:
            cut += 1
        chunk = window[:cut].strip()
        if chunk:
            chunks.append(chunk)
        cursor += cut
    return chunks


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def derive_title(path: Path, heading: str | None = None) -> str:
    if heading:
        return heading
    return path.stem.replace("-", " ").replace("_", " ").title()


def iter_markdown_files(patterns: Iterable[str], repo_root: Path, max_files: int) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        if pattern.startswith("~"):
            pattern = str(Path(pattern).expanduser())
        if pattern.startswith(("\\", "C:", "D:", "E:")):
            matches = glob.glob(pattern, recursive=True)
            for p in sorted(matches):
                fp = Path(p)
                if fp.is_file() and fp.suffix.lower() == ".md":
                    files.append(fp)
        else:
            for p in sorted(repo_root.glob(pattern)):
                if p.is_file() and p.suffix.lower() == ".md":
                    files.append(p)
    deduped = []
    seen: set[Path] = set()
    for p in files:
        if p.resolve() in seen:
            continue
        seen.add(p.resolve())
        deduped.append(p)
        if max_files and len(deduped) >= max_files:
            break
    return deduped


def build_records(path: Path, text: str, max_chars: int, min_chars: int, max_records: int) -> list[dict]:
    plain = strip_frontmatter(text)
    plain = re.sub(r"\n{3,}", "\n\n", plain).strip()
    if not plain:
        return []

    source_file = str(path).replace("\\", "/")
    source_type = "obsidian" if "\\OneDrive\\" in source_file or "\\Vault\\" in source_file else "github"
    segments = detect_heading_segments(plain)
    records: list[dict] = []
    for heading, segment in segments:
        subchunks = chunk_text(segment, max_chars)
        section_title = derive_title(path, heading)
        for idx, chunk in enumerate(subchunks):
            chunk = chunk.strip()
            if len(chunk) < min_chars:
                continue
            if len(records) >= max_records > 0:
                break
            instruction = (
                f"Summarize the SCBE note section \"{section_title}\" from {path.name}. "
                f"Preserve important implementation details and assumptions."
            )
            if not heading:
                instruction = (
                    f"Summarize this SCBE note from {path.name}. "
                    f"Preserve important implementation details and assumptions."
                )
            row = {
                "id": f"sft-note-{hashlib.sha1((source_file + '|' + str(idx) + '|' + chunk[:64]).encode()).hexdigest()[:24]}",
                "instruction": instruction,
                "response": chunk if heading is None else f"{heading}\n\n{chunk}",
                "category": "notes",
                "metadata": {
                    "source_file": source_file,
                    "source_type": source_type,
                    "source_name": path.stem,
                    "section": heading or "",
                    "chunk_index": idx,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "tongue_profile": "notes",
                },
            }
            records.append(row)
    return records


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve()
    if not repo_root.exists():
        raise RuntimeError(f"Repo root not found: {repo_root}")

    default_patterns = ["docs/**/*.md", "notes/**/*.md", "training/**/*.md", "README.md"]
    globs = list(args.glob) if args.glob else default_patterns

    vault = Path(args.obsidian_vault).expanduser().resolve() if args.obsidian_vault else None
    if vault and vault.exists():
        globs.extend([
            str(vault / "**/*.md"),
        ])

    files = iter_markdown_files(globs, repo_root, max_files=args.max_files)
    if not files:
        print("No markdown files found with provided globs.")
        return 1

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    with out_path.open("w", encoding="utf-8") as f:
        for path in files:
            if total and args.max_records and total >= args.max_records:
                break
            rel = str(path)
            raw_text = read_text_file(path)
            records = build_records(path, raw_text, args.max_chars, args.min_chars, args.max_records - total if args.max_records else 0)
            for rec in records:
                if total and args.max_records and total >= args.max_records:
                    break
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                total += 1

    print(f"Converted markdown notes -> {total} SFT pairs -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
