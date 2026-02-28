#!/usr/bin/env python3
"""Ingest arbitrary artifacts into a SCBE-readable markdown corpus.

This utility is designed for the "AI Dropbox" pattern you described:
- collect arbitrary exported files (pdf/docx/chat dumps, web exports, notes)
- convert supported formats to markdown with rich provenance metadata
- store converted notes into Obsidian in a deterministic, queryable layout
- emit run-level manifests for context pooling and training ingestion
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import mimetypes
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator

from pypdf import PdfReader


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class IntakeRecord:
    source_path: str
    output_path: str
    source_relative: str
    output_relative: str
    status: str
    source_type: str
    mime_type: str
    conversation_stream: str
    conversation_type: str
    service: str
    model: str
    provider: str
    source_system: str
    run_id: str
    checksum_sha256: str
    size_bytes: int
    imported_at_utc: str
    extracted_text_chars: int
    error: str = ""


@dataclass
class IngestSummary:
    run_id: str
    started_at: str
    completed_at: str
    source_root: str
    vault_root: str
    corpus_root: str
    total_files: int
    converted_files: int
    failed_files: int
    skipped_files: int
    records: list[dict[str, Any]]


def _safe_filename(value: str, max_len: int = 110) -> str:
    value = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "-", value)
    value = re.sub(r"\s+", "-", value.strip().lower())
    value = re.sub(r"-+", "-", value)
    value = value.strip("-")
    return value[:max_len] or "document"


def _checksum_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_supported_files(source_root: Path, suffixes: set[str] | None = None) -> Iterator[Path]:
    if suffixes:
        wanted = set(s.lower() for s in suffixes)
        for path in source_root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() in wanted:
                yield path
            elif not suffixes:
                yield path
    else:
        for path in source_root.rglob("*"):
            if path.is_file():
                yield path


def _looks_text_like(raw: bytes, threshold: float = 0.95) -> bool:
    if not raw:
        return True
    if b"\x00" in raw:
        return False
    printable = sum(1 for b in raw if 9 <= b <= 13 or 32 <= b <= 126)
    return printable / max(1, len(raw)) >= threshold


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _read_html(path: Path) -> str:
    text = _read_text(path)
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(text, "lxml")
        return soup.get_text("\n")
    except Exception:
        # Fallback to removing tags only; keeps things readable enough for recall.
        return re.sub(r"<[^>]+>", "", text)


def _read_csv(path: Path) -> str:
    rows: list[list[str]] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.reader(f)
        rows = [row for row in reader]

    if not rows:
        return ""

    lines: list[str] = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join(["---"] * len(rows[0])) + " |"]
    for row in rows[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    chunks: list[str] = []
    for page in reader.pages:
        try:
            extracted = page.extract_text() or ""
            chunks.append(extracted)
        except Exception:
            continue
    return "\n\n".join(chunks)


def _read_docx(path: Path) -> str:
    try:
        from docx import Document
    except Exception as exc:
        raise RuntimeError(f"docx support unavailable: {exc}") from exc

    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def _read_ipynb(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    cells = payload.get("cells", [])
    parts: list[str] = []
    for cell in cells:
        if not isinstance(cell, dict):
            continue
        source = cell.get("source", [])
        if isinstance(source, list):
            parts.append("".join(str(x) for x in source).strip())
        elif isinstance(source, str):
            parts.append(source.strip())
    return "\n\n".join(part for part in parts if part)


def _read_json(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    return json.dumps(payload, ensure_ascii=True, indent=2)


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


SUPPORTED_READERS: dict[str, Callable[[Path], str]] = {
    ".txt": _read_text,
    ".md": _read_text,
    ".rst": _read_text,
    ".yaml": _read_text,
    ".yml": _read_text,
    ".toml": _read_text,
    ".ini": _read_text,
    ".cfg": _read_text,
    ".json": _read_json,
    ".ipynb": _read_ipynb,
    ".html": _read_html,
    ".htm": _read_html,
    ".pdf": _read_pdf,
    ".docx": _read_docx,
    ".csv": _read_csv,
    ".tsv": _read_csv,
}


def _extract_text(path: Path) -> tuple[str, str]:
    ext = path.suffix.lower()
    if ext in SUPPORTED_READERS:
        reader = SUPPORTED_READERS[ext]
    else:
        # Last-resort text extraction for files that are mostly text.
        raw = path.read_bytes()
        if _looks_text_like(raw):
            return _normalize_text(raw.decode("utf-8", errors="replace")), "text"
        raise ValueError(f"unsupported binary type: {ext or '[no extension]'}")

    return _normalize_text(reader(path)), "text"


def _frontmatter(record: IntakeRecord, source_name: str, tags: list[str]) -> str:
    tags_block = "\n  - " + "\n  - ".join(tags) if tags else "\n  []"
    lines = [
        "---",
        f'title: "{source_name}"',
        f"source_path: {record.source_path}",
        f"source_relative: {record.source_relative}",
        f"output_relative: {record.output_relative}",
        f"source_type: {record.source_type}",
        f"mime_type: {record.mime_type}",
        f"checksum_sha256: {record.checksum_sha256}",
        f"size_bytes: {record.size_bytes}",
        f"imported_at_utc: {record.imported_at_utc}",
        f"conversation_stream: {record.conversation_stream}",
        f"conversation_type: {record.conversation_type}",
        f"service: {record.service}",
        f"provider: {record.provider}",
        f"model: {record.model}",
        f"source_system: {record.source_system}",
        "tags:",
        tags_block,
        f"status: {record.status}",
        f"run_id: {record.run_id}",
        "---",
    ]
    return "\n".join(lines) + "\n"


def _markdown_for_record(
    source_path: Path,
    output_path: Path,
    text: str,
    record: IntakeRecord,
    tags: list[str],
) -> str:
    source_name = source_path.stem
    lines = [
        _frontmatter(record, source_name, tags),
        f"# {source_name}",
        "",
        f"- Source: `{record.source_type}` from `{record.source_relative}`",
        f"- Run: `{record.run_id}`",
        f"- Stream: `{record.conversation_stream}`",
        f"- Conversation class: `{record.conversation_type}`",
        f"- Service: `{record.service}`",
        f"- Model: `{record.provider}:{record.model}`",
        f"- Imported: `{record.imported_at_utc}`",
        "",
        "## Source Metadata",
        f"- SHA256: `{record.checksum_sha256}`",
        f"- Extracted chars: {record.extracted_text_chars}",
        "",
        "## Extracted Content",
        text,
        "",
    ]
    if record.error:
        lines.insert(-2, f"- Error: {record.error}")
    return "\n".join(lines)


def _build_record(*, source_root: Path, path: Path, output_path: Path, args: argparse.Namespace) -> IntakeRecord:
    size = path.stat().st_size
    rel = str(path.relative_to(source_root)).replace("\\", "/")
    return IntakeRecord(
        source_path=str(path.resolve()),
        output_path=str(output_path.resolve()),
        source_relative=rel,
        output_relative=str(output_path.relative_to(args.vault_root)).replace("\\", "/") if args.vault_root else str(output_path),
        status="success",
        source_type=path.suffix.lower() or "[noext]",
        mime_type=mimetypes.guess_type(str(path))[0] or "application/octet-stream",
        conversation_stream=args.conversation_stream,
        conversation_type=args.conversation_type,
        service=args.service,
        model=args.model,
        provider=args.provider,
        source_system=args.source_system,
        run_id=args.run_id,
        checksum_sha256=_checksum_sha256(path),
        size_bytes=size,
        imported_at_utc=_now_iso(),
        extracted_text_chars=0,
    )


def run(argv: list[str] | None = None) -> IngestSummary:
    parser = argparse.ArgumentParser(
        description="Convert incoming files to markdown and ingest into SCBE-Hub corpus",
    )
    parser.add_argument("--source-root", required=True, help="Directory with raw files to ingest")
    parser.add_argument("--vault-path", default="", help="Obsidian vault root path")
    parser.add_argument("--run-root", default="training/runs/ai_dropbox_intake", help="Run output root")
    parser.add_argument("--run-id", default="", help="Stable identifier for run")
    parser.add_argument("--service", default="multi-ai", help="Source service label")
    parser.add_argument("--conversation-stream", default="cross-model", help="Conversation stream tag")
    parser.add_argument("--conversation-type", default="mixed", help="Stream class: coder/worldbuilder/general")
    parser.add_argument("--provider", default="manual", help="Model provider label")
    parser.add_argument("--model", default="unknown", help="Model name")
    parser.add_argument(
        "--source-system",
        default="external-export",
        help="Source-system tag (GPT/Claude/ClaudeCode/CLI/etc.)",
    )
    parser.add_argument(
        "--extensions",
        nargs="*",
        default=[],
        help="Optional list of extensions to include (like .pdf .md .docx). Empty means all supported paths.",
    )
    parser.add_argument("--write-jsonl", action="store_true", help="Also emit jsonl training record")
    parser.add_argument("--dry-run", action="store_true", help="Validate and report without writing")
    parser.add_argument("--no-hash-rename", action="store_true", help="Keep original file names")
    parser.add_argument(
        "--include-extensions",
        nargs="*",
        default=[],
        help="Legacy alias for --extensions",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[2]
    source_root = Path(args.source_root).resolve()

    if not source_root.exists() or not source_root.is_dir():
        raise FileNotFoundError(f"source-root not found: {source_root}")

    run_id = args.run_id.strip()
    if not run_id:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    args.run_id = run_id

    run_root = (repo_root / args.run_root / run_id).resolve()
    args.vault_root = (Path(args.vault_path) if args.vault_path else repo_root / "tmp" / "vault").resolve()

    if not args.vault_path:
        args.vault_root = args.vault_root

    allowed_exts: set[str] = set()
    include_exts = args.extensions or args.include_extensions
    if include_exts:
        for item in include_exts:
            if not item.startswith("."):
                allowed_exts.add(f".{item.lower().strip()}")
            else:
                allowed_exts.add(item.lower().strip())

    started_at = _now_iso()
    corpus_root = args.vault_root / "SCBE-Hub" / "Corpus" / args.conversation_stream / args.conversation_type / run_id
    notes_root = corpus_root / args.service
    jsonl_path = run_root / "records.jsonl"
    manifest_path = run_root / "manifest.json"
    summary_path = run_root / "summary.json"

    results: list[IntakeRecord] = []
    total = 0
    failed = 0
    skipped = 0

    for source_path in _iter_supported_files(source_root, allowed_exts or None):
        total += 1
        out_name_base = _safe_filename(source_path.stem)
        ext = source_path.suffix.lower()
        ext_suffix = ext if ext else ".md"
        output_path = notes_root / f"{out_name_base}{ext_suffix}.md"

        # Stable path when there are duplicate names in different folders.
        if output_path.exists():
            stem_hash = hashlib.sha1(str(source_path.relative_to(source_root)).encode("utf-8")).hexdigest()[:10]
            output_path = notes_root / f"{out_name_base}-{stem_hash}{ext_suffix}.md"

        if args.no_hash_rename:
            output_path = notes_root / (source_path.name + ".md")

        try:
            if args.dry_run:
                record = _build_record(source_root=source_root, path=source_path, output_path=output_path, args=args)
                text = "[dry-run: not written]"
                record.extracted_text_chars = len(text)
                results.append(record)
                continue

            text, _kind = _extract_text(source_path)
            record = _build_record(source_root=source_root, path=source_path, output_path=output_path, args=args)
            record.extracted_text_chars = len(text)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            tags = [
                args.conversation_stream,
                args.conversation_type,
                args.service,
                args.source_system,
                args.provider,
            ]
            tags = [t for t in tags if t]
            markdown = _markdown_for_record(source_path, output_path, text, record, tags)
            output_path.write_text(markdown, encoding="utf-8")
            results.append(record)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            err = str(exc)
            if args.dry_run:
                err = "dry-run: " + err
            record = _build_record(source_root=source_root, path=source_path, output_path=output_path, args=args)
            record.status = "failed"
            record.error = err
            record.extracted_text_chars = 0
            results.append(record)

    # Keep deterministic order for reproducible runs.
    results.sort(key=lambda r: r.source_path)
    manifest = IngestSummary(
        run_id=run_id,
        started_at=started_at,
        completed_at=_now_iso(),
        source_root=str(source_root),
        vault_root=str(args.vault_root),
        corpus_root=str(corpus_root),
        total_files=total,
        converted_files=sum(1 for r in results if r.status == "success"),
        failed_files=failed,
        skipped_files=skipped,
        records=[asdict(r) for r in results],
    )

    run_root.mkdir(parents=True, exist_ok=True)

    summary_payload = asdict(manifest)
    if args.dry_run:
        summary_payload["status"] = "dry-run"

    manifest_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
    summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

    if args.write_jsonl:
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for rec in results:
                if rec.status != "success":
                    continue
                handle.write(
                    json.dumps(
                        {
                            "event_type": "ai-dropbox-corpus",
                            "run_id": rec.run_id,
                            "source_path": rec.source_relative,
                            "output_path": rec.output_relative,
                            "source_type": rec.source_type,
                            "sha256": rec.checksum_sha256,
                            "conversation_stream": rec.conversation_stream,
                            "conversation_type": rec.conversation_type,
                            "service": rec.service,
                            "source_system": rec.source_system,
                            "provider": rec.provider,
                            "model": rec.model,
                            "imported_at_utc": rec.imported_at_utc,
                        },
                        ensure_ascii=True,
                    )
                    + "\n"
                )

    return manifest


def main(argv: list[str] | None = None) -> int:
    _ = run(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
