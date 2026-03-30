#!/usr/bin/env python3
"""Convert a Claude-style export zip into lore/manuscript SFT records.

The export bundle contains conversations, project documents, and project memory
records. The conversation pairs were already extracted separately; this script
focuses on the remaining high-value lore/manuscript corpus in ``projects.json``
and ``memories.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ZIP = Path(r"C:\Users\issda\Downloads\data-2026-03-30-13-50-27-batch-0000.zip")
DEFAULT_OUT = REPO_ROOT / "training-data" / "sft" / "claude_export_lore_sft.jsonl"
DEFAULT_SUMMARY = REPO_ROOT / "artifacts" / "training" / "claude_export_lore_sft.summary.json"

LORE_PROJECT_NAMES = {
    "avalon story",
    "more stuff",
    "suragu",
    "finished product",
    "spiral of polyonneth",
    "final draft spot",
    "final draft",
    "dump site",
    "choicescript",
    "aethermoore-testagent-1",
}

LORE_KEYWORDS = {
    "avalon",
    "spiral",
    "polly",
    "pollyoneth",
    "izack",
    "aria",
    "eldrin",
    "ravencrest",
    "clay",
    "world tree",
    "academy",
    "magic",
    "dimensional",
    "realm",
    "aethermoor",
    "sacred tongue",
    "tongue",
    "chapter",
    "shore to king",
    "architect of realms",
    "collaborative",
    "lexicon",
    "chronicle",
    "codex",
    "everweave",
    "fizzle",
    "zara",
    "kael",
    "senna",
}

NOISE_NAME_PATTERNS = [
    re.compile(pat, re.IGNORECASE)
    for pat in (
        r"^a\s*full\s*log",
        r"skip to content",
        r"^market overview",
        r"^how to use claude",
        r"^pipedream$",
        r"^codeing$",
        r"^business$",
        r"^going haywire$",
        r"^look here dumb ass$",
        r"^stfud$",
        r"^syffj$",
        r"^louhjkl$",
        r"^dhit$",
        r"^drft$",
        r"^mokols$",
        r"^pl$",
    )
]

UI_DUMP_MARKERS = (
    "skip to content",
    "open sidebar",
    "saved memory full",
    "chatgpt 4.5",
    "you said:",
    "create task",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert Claude export lore/manuscript data to SFT JSONL")
    parser.add_argument("--zip", default=str(DEFAULT_ZIP), help=f"Export zip (default: {DEFAULT_ZIP})")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help=f"Output JSONL path (default: {DEFAULT_OUT})")
    parser.add_argument(
        "--summary",
        default=str(DEFAULT_SUMMARY),
        help=f"Summary JSON path (default: {DEFAULT_SUMMARY})",
    )
    parser.add_argument("--chunk-target", type=int, default=6000, help="Target chunk size in chars")
    parser.add_argument("--chunk-max", type=int, default=8500, help="Hard max chunk size in chars")
    parser.add_argument("--min-doc-chars", type=int, default=1200, help="Skip docs shorter than this")
    return parser.parse_args()


def normalize_text(text: str) -> str:
    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\x00", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def sanitize_name(name: str) -> str:
    base = re.sub(r"\s+", " ", str(name or "").strip())
    return base[:160] if base else "Untitled"


def is_noise_doc(filename: str, text: str) -> bool:
    clean_name = sanitize_name(filename)
    for pat in NOISE_NAME_PATTERNS:
        if pat.search(clean_name):
            return True
    sample = normalize_text(text)[:1500].lower()
    hits = sum(1 for marker in UI_DUMP_MARKERS if marker in sample)
    return hits >= 2


def lore_score(project_name: str, filename: str, text: str) -> int:
    sample = f"{project_name}\n{filename}\n{text[:5000]}".lower()
    score = 0
    for kw in LORE_KEYWORDS:
        if kw in sample:
            score += 1
    if project_name.strip().lower() in LORE_PROJECT_NAMES:
        score += 2
    if re.search(r"(avalon|spiral|shore|polly|izack|aria|chapter|draft|lore|codex|academy)", filename, re.IGNORECASE):
        score += 2
    return score


def is_candidate_doc(project_name: str, filename: str, text: str, min_doc_chars: int) -> bool:
    text = normalize_text(text)
    if len(text) < min_doc_chars:
        return False
    if is_noise_doc(filename, text):
        return False
    score = lore_score(project_name, filename, text)
    return score >= 4


def chunk_text(text: str, target: int, hard_max: int) -> list[str]:
    text = normalize_text(text)
    if len(text) <= hard_max:
        return [text]

    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if current:
            chunks.append("\n\n".join(current).strip())
            current = []
            current_len = 0

    for para in paras:
        if len(para) > hard_max:
            flush()
            start = 0
            while start < len(para):
                piece = para[start : start + hard_max].strip()
                if piece:
                    chunks.append(piece)
                start += hard_max
            continue

        projected = current_len + len(para) + (2 if current else 0)
        if current and projected > hard_max:
            flush()
        current.append(para)
        current_len += len(para) + (2 if current_len else 0)
        if current_len >= target:
            flush()

    flush()
    return [chunk for chunk in chunks if chunk]


def dedupe_key(*parts: str) -> str:
    raw = "\n".join(normalize_text(part) for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_export(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    with zipfile.ZipFile(path) as zf:
        conversations = json.loads(zf.read("conversations.json"))
        projects = json.loads(zf.read("projects.json"))
        memories_list = json.loads(zf.read("memories.json"))
    memory_root = memories_list[0] if memories_list else {}
    return conversations, projects, memory_root


def project_doc_rows(projects: list[dict[str, Any]], target: int, hard_max: int, min_doc_chars: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    stats = {"docs_total": 0, "docs_kept": 0, "docs_skipped_noise": 0, "doc_chunks": 0, "doc_duplicates": 0}

    for project in projects:
        project_name = sanitize_name(project.get("name") or "Untitled Project")
        docs = project.get("docs", [])
        for doc in docs:
            stats["docs_total"] += 1
            filename = sanitize_name(doc.get("filename") or doc.get("name") or "Untitled")
            text = normalize_text(doc.get("content") or doc.get("text") or "")
            if not is_candidate_doc(project_name, filename, text, min_doc_chars):
                stats["docs_skipped_noise"] += 1
                continue
            stats["docs_kept"] += 1
            chunks = chunk_text(text, target, hard_max)
            total = len(chunks)
            for idx, chunk in enumerate(chunks, start=1):
                key = dedupe_key(project_name, filename, chunk)
                if key in seen:
                    stats["doc_duplicates"] += 1
                    continue
                seen.add(key)
                stats["doc_chunks"] += 1
                prompt = (
                    f"Provide the canon reference excerpt from the Claude project archive.\n\n"
                    f"Project: {project_name}\n"
                    f"Document: {filename}\n"
                    f"Part: {idx}/{total}\n\n"
                    "Preserve names, terminology, story logic, and lore details exactly as they appear in the source."
                )
                rows.append(
                    {
                        "instruction": prompt,
                        "response": chunk,
                        "source": "claude_export_projects",
                        "category": "lore_reference",
                        "metadata": {
                            "project_name": project_name,
                            "project_uuid": project.get("uuid"),
                            "document_name": filename,
                            "part_index": idx,
                            "part_total": total,
                            "source_type": "claude_export_project_doc",
                            "quality": {"dedup": True, "validated": False},
                        },
                    }
                )
    return rows, stats


def project_memory_rows(projects: list[dict[str, Any]], memory_root: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    rows: list[dict[str, Any]] = []
    stats = {"memories_total": 0, "memories_kept": 0}
    project_name_by_uuid = {str(p.get("uuid")): sanitize_name(p.get("name") or "Untitled Project") for p in projects}
    project_memories = memory_root.get("project_memories", {}) if isinstance(memory_root, dict) else {}

    for project_uuid, memory in project_memories.items():
        stats["memories_total"] += 1
        text = normalize_text(memory if isinstance(memory, str) else json.dumps(memory, ensure_ascii=True))
        project_name = project_name_by_uuid.get(str(project_uuid), "Unknown Project")
        if lore_score(project_name, project_name, text) < 4:
            continue
        stats["memories_kept"] += 1
        rows.append(
            {
                "instruction": (
                    f"What is the current canon scope, writing state, and project context for `{project_name}` "
                    "from the Claude project memory archive?"
                ),
                "response": text,
                "source": "claude_export_project_memories",
                "category": "project_memory",
                "metadata": {
                    "project_name": project_name,
                    "project_uuid": project_uuid,
                    "source_type": "claude_export_project_memory",
                    "quality": {"dedup": True, "validated": False},
                },
            }
        )
    return rows, stats


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
            count += 1
    return count


def main() -> int:
    args = parse_args()
    zip_path = Path(args.zip).expanduser()
    out_path = Path(args.out).expanduser()
    summary_path = Path(args.summary).expanduser()

    _, projects, memory_root = load_export(zip_path)
    doc_rows, doc_stats = project_doc_rows(projects, args.chunk_target, args.chunk_max, args.min_doc_chars)
    memory_rows, memory_stats = project_memory_rows(projects, memory_root)
    rows = doc_rows + memory_rows
    count = write_jsonl(out_path, rows)

    summary = {
        "zip_path": str(zip_path),
        "output_path": str(out_path),
        "rows_written": count,
        "doc_rows": len(doc_rows),
        "memory_rows": len(memory_rows),
        **doc_stats,
        **memory_stats,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
