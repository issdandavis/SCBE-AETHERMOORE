#!/usr/bin/env python3
"""Convert longform draft roots into lore/manuscript SFT JSONL records."""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts import claude_export_lore_to_sft as claude_lore

DEFAULT_OUTPUT = REPO_ROOT / "training-data" / "sft" / "draft_corpus_sft.jsonl"
DEFAULT_SUMMARY = REPO_ROOT / "artifacts" / "training" / "draft_corpus_sft.summary.json"
SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt", ".html", ".htm", ".docx", ".rtf", ".odt"}
SKIP_DIR_NAMES = {".git", "node_modules", "dist", "build", ".venv", "venv", "__pycache__", ".dropbox.cache"}


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert longform draft roots into lore/manuscript SFT JSONL")
    parser.add_argument("--root", action="append", required=True, help="Draft root directory or file")
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT), help=f"Output JSONL path (default: {DEFAULT_OUTPUT})")
    parser.add_argument(
        "--summary",
        default=str(DEFAULT_SUMMARY),
        help=f"Summary JSON path (default: {DEFAULT_SUMMARY})",
    )
    parser.add_argument("--chunk-target", type=int, default=6000, help="Target chunk size in chars")
    parser.add_argument("--chunk-max", type=int, default=8500, help="Hard max chunk size in chars")
    parser.add_argument("--min-doc-chars", type=int, default=1200, help="Skip docs shorter than this")
    return parser.parse_args()


def _resolve_path(raw: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    return path


def _html_to_text(raw: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(raw)
    parser.close()
    return "\n".join(parser.parts)


def _rtf_to_text(raw: str) -> str:
    text = re.sub(r"\\par[d]?", "\n", raw)
    text = re.sub(r"\\'[0-9a-fA-F]{2}", "", text)
    text = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", text)
    text = text.replace("{", "").replace("}", "")
    return text


def _odt_to_text(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        content = zf.read("content.xml").decode("utf-8", errors="replace")
    text = re.sub(r"</text:p>", "\n\n", content)
    text = re.sub(r"<[^>]+>", "", text)
    return text


def read_text_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown", ".txt"}:
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix in {".html", ".htm"}:
        return _html_to_text(path.read_text(encoding="utf-8", errors="replace"))
    if suffix == ".rtf":
        return _rtf_to_text(path.read_text(encoding="utf-8", errors="replace"))
    if suffix == ".odt":
        return _odt_to_text(path)
    if suffix == ".docx":
        try:
            import docx  # type: ignore
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError("python-docx is required to ingest .docx drafts") from exc
        doc = docx.Document(str(path))
        return "\n\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip())
    raise ValueError(f"Unsupported draft suffix: {suffix}")


def discover_draft_files(roots: Iterable[str]) -> list[tuple[Path, Path]]:
    discovered: list[tuple[Path, Path]] = []
    seen: set[Path] = set()
    for raw in roots:
        root = _resolve_path(raw)
        if not root.exists():
            continue
        if root.is_file():
            candidates = [root]
            base = root.parent
        else:
            candidates = []
            base = root
            for candidate in root.rglob("*"):
                if any(part in SKIP_DIR_NAMES for part in candidate.parts):
                    continue
                if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_SUFFIXES:
                    candidates.append(candidate)
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            discovered.append((base.resolve(), resolved))
    return sorted(discovered, key=lambda item: str(item[1]).lower())


def collect_rows(
    roots: Iterable[str],
    *,
    chunk_target: int,
    chunk_max: int,
    min_doc_chars: int,
) -> tuple[list[dict], dict[str, int]]:
    rows: list[dict] = []
    seen_keys: set[str] = set()
    stats = {
        "files_total": 0,
        "files_kept": 0,
        "files_skipped_noise": 0,
        "files_skipped_error": 0,
        "rows_written": 0,
        "duplicates_removed": 0,
    }

    for base, path in discover_draft_files(roots):
        stats["files_total"] += 1
        rel_path = path.relative_to(base)
        try:
            text = claude_lore.normalize_text(read_text_document(path))
        except Exception:
            stats["files_skipped_error"] += 1
            continue

        source_label = base.name or "draft_root"
        if not claude_lore.is_candidate_doc(source_label, path.name, text, min_doc_chars):
            stats["files_skipped_noise"] += 1
            continue

        stats["files_kept"] += 1
        chunks = claude_lore.chunk_text(text, target=chunk_target, hard_max=chunk_max)
        total = len(chunks)
        for idx, chunk in enumerate(chunks, start=1):
            key = claude_lore.dedupe_key(str(rel_path), chunk)
            if key in seen_keys:
                stats["duplicates_removed"] += 1
                continue
            seen_keys.add(key)
            rows.append(
                {
                    "instruction": (
                        "Provide the canon draft excerpt from the imported manuscript archive.\n\n"
                        f"Root: {source_label}\n"
                        f"Document: {rel_path.as_posix()}\n"
                        f"Part: {idx}/{total}\n\n"
                        "Preserve names, terminology, lore details, and scene logic exactly as they appear in the source."
                    ),
                    "response": chunk,
                    "source": "draft_corpus_import",
                    "category": "lore_reference",
                    "metadata": {
                        "root_name": source_label,
                        "document_name": rel_path.name,
                        "document_path": rel_path.as_posix(),
                        "part_index": idx,
                        "part_total": total,
                        "source_type": f"draft_file:{path.suffix.lower()}",
                        "quality": {"dedup": True, "validated": False},
                    },
                }
            )
            stats["rows_written"] += 1

    return rows, stats


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
            count += 1
    return count


def main() -> int:
    args = parse_args()
    rows, stats = collect_rows(
        roots=args.root,
        chunk_target=args.chunk_target,
        chunk_max=args.chunk_max,
        min_doc_chars=args.min_doc_chars,
    )

    out_path = Path(args.out).expanduser()
    summary_path = Path(args.summary).expanduser()
    count = write_jsonl(out_path, rows)
    summary = {
        "roots": [str(_resolve_path(item)) for item in args.root],
        "output_path": str(out_path),
        "rows_written": count,
        **stats,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
