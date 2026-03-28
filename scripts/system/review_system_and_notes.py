#!/usr/bin/env python3
"""Generate a combined SCBE system and notes review packet.

Scans live code roots plus the specs/research note lanes, then emits:
- a machine-readable JSON manifest
- a human-readable Markdown summary

The goal is not to prove correctness. The goal is to keep the live system,
canonical specs, and active research notes in one auditable review surface.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_ROOT = REPO_ROOT / "artifacts" / "system_review"
DEFAULT_ROOTS = (
    "src",
    "tests",
    "scripts",
    "docs/specs",
    "docs/research",
)
DEFAULT_ANCHORS = (
    "docs/specs/KERNEL_MATH_COMPLETE.md",
    "docs/specs/SYSTEM_BLUEPRINT_v2_CURRENT.md",
    "docs/specs/STATE_MANIFOLD_21D_PRODUCT_METRIC.md",
    "docs/research/FOAM_MATRIX_AND_LEARNING_LOCALIZATION.md",
    "docs/research/CONCEPT_MAP_PACKING_AND_LYAPUNOV_NOTES_2026-03-25.md",
    "docs/research/DECIMAL_BOUNDARY_AND_TURING_TAPE_NOTES_2026-03-25.md",
)
EXCLUDED_PARTS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
}

STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(.+?)\s*$", re.IGNORECASE)
DATE_RE = re.compile(r"^\*\*(Date|Version):\*\*\s*(.+?)\s*$", re.IGNORECASE)
TITLE_RE = re.compile(r"^#\s+(.+?)\s*$")
SOURCE_REF_RE = re.compile(r"\b(?:src|tests|scripts|docs)/[A-Za-z0-9_./-]+")


@dataclass
class RootSummary:
    root: str
    file_count: int
    total_bytes: int
    extension_counts: dict[str, int]


@dataclass
class NoteSummary:
    path: str
    lane: str
    title: str | None
    status: str | None
    date: str | None
    bytes: int
    modified_utc: str
    source_ref_count: int


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a full SCBE system and notes review packet.")
    parser.add_argument(
        "--run-root",
        default=str(DEFAULT_RUN_ROOT),
        help=f"Artifact output root (default: {DEFAULT_RUN_ROOT.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--roots",
        nargs="*",
        default=list(DEFAULT_ROOTS),
        help="Repo-relative roots to scan.",
    )
    parser.add_argument(
        "--recent",
        type=int,
        default=20,
        help="Number of recent files to include in the Markdown summary.",
    )
    return parser.parse_args()


def should_skip(path: Path) -> bool:
    return any(part in EXCLUDED_PARTS for part in path.parts)


def iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if should_skip(path):
            continue
        yield path


def summarize_root(root: Path) -> RootSummary:
    ext_counts: Counter[str] = Counter()
    file_count = 0
    total_bytes = 0
    for path in iter_files(root):
        file_count += 1
        total_bytes += path.stat().st_size
        ext = path.suffix.lower() or "<none>"
        ext_counts[ext] += 1
    return RootSummary(
        root=str(root.relative_to(REPO_ROOT)).replace("\\", "/"),
        file_count=file_count,
        total_bytes=total_bytes,
        extension_counts=dict(sorted(ext_counts.items())),
    )


def extract_markdown_fields(path: Path) -> NoteSummary:
    text = path.read_text(encoding="utf-8", errors="replace")
    title: str | None = None
    status: str | None = None
    date: str | None = None

    for line in text.splitlines():
        if title is None:
            match = TITLE_RE.match(line.strip())
            if match:
                title = match.group(1).strip()
        if status is None:
            match = STATUS_RE.match(line.strip())
            if match:
                status = match.group(1).strip()
        if date is None:
            match = DATE_RE.match(line.strip())
            if match:
                date = match.group(2).strip()
        if title and status and date:
            break

    rel_path = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    lane = "specs" if rel_path.startswith("docs/specs/") else "research"
    source_ref_count = len(set(SOURCE_REF_RE.findall(text)))
    stat = path.stat()
    modified_utc = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return NoteSummary(
        path=rel_path,
        lane=lane,
        title=title,
        status=status,
        date=date,
        bytes=stat.st_size,
        modified_utc=modified_utc,
        source_ref_count=source_ref_count,
    )


def collect_note_summaries() -> list[NoteSummary]:
    notes: list[NoteSummary] = []
    for lane in ("docs/specs", "docs/research"):
        root = REPO_ROOT / lane
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            if should_skip(path):
                continue
            notes.append(extract_markdown_fields(path))
    notes.sort(key=lambda item: item.path)
    return notes


def build_anchor_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for rel in DEFAULT_ANCHORS:
        path = REPO_ROOT / rel
        rows.append(
            {
                "path": rel,
                "exists": path.exists(),
                "bytes": path.stat().st_size if path.exists() else 0,
            }
        )
    return rows


def recent_file_rows(roots: Iterable[str], limit: int) -> list[dict[str, object]]:
    rows: list[tuple[float, Path]] = []
    for rel in roots:
        root = REPO_ROOT / rel
        for path in iter_files(root):
            rows.append((path.stat().st_mtime, path))
    rows.sort(key=lambda item: item[0], reverse=True)
    clipped = rows[:limit]
    return [
        {
            "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
            "modified_utc": datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "bytes": path.stat().st_size,
        }
        for mtime, path in clipped
    ]


def lane_status_counts(notes: Iterable[NoteSummary]) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter[str]] = {"specs": Counter(), "research": Counter()}
    for note in notes:
        counts[note.lane][note.status or "<missing>"] += 1
    return {lane: dict(sorted(counter.items())) for lane, counter in counts.items()}


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def write_outputs(
    run_dir: Path,
    root_summaries: list[RootSummary],
    notes: list[NoteSummary],
    anchors: list[dict[str, object]],
    recent_rows: list[dict[str, object]],
) -> tuple[Path, Path]:
    json_path = run_dir / "system_notes_review.json"
    md_path = run_dir / "system_notes_review.md"

    missing_status = [note.path for note in notes if not note.status]
    missing_title = [note.path for note in notes if not note.title]
    specs_without_source_refs = [
        note.path for note in notes if note.lane == "specs" and note.source_ref_count == 0
    ]

    payload = {
        "generated_utc": utc_now(),
        "repo_root": str(REPO_ROOT),
        "roots": [asdict(item) for item in root_summaries],
        "notes": [asdict(item) for item in notes],
        "anchors": anchors,
        "recent_files": recent_rows,
        "lane_status_counts": lane_status_counts(notes),
        "attention": {
            "missing_status": missing_status,
            "missing_title": missing_title,
            "specs_without_source_refs": specs_without_source_refs,
        },
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")

    root_rows = [
        [
            item.root,
            str(item.file_count),
            str(item.total_bytes),
            ", ".join(f"{ext}:{count}" for ext, count in list(item.extension_counts.items())[:6]),
        ]
        for item in root_summaries
    ]
    anchor_rows = [
        [str(row["exists"]), row["path"], str(row["bytes"])]
        for row in anchors
    ]
    recent_md_rows = [
        [row["modified_utc"], row["path"], str(row["bytes"])]
        for row in recent_rows
    ]

    spec_count = sum(1 for note in notes if note.lane == "specs")
    research_count = sum(1 for note in notes if note.lane == "research")

    md = f"""# System and Notes Review

Generated: {utc_now()}

## Scope

- Live system roots reviewed: {", ".join(item.root for item in root_summaries)}
- Specs notes reviewed: {spec_count}
- Research notes reviewed: {research_count}

## Root Summary

{markdown_table(["Root", "Files", "Bytes", "Top extensions"], root_rows)}

## Lane Status Counts

```json
{json.dumps(lane_status_counts(notes), indent=2, ensure_ascii=True)}
```

## Canonical Anchor Check

{markdown_table(["Exists", "Path", "Bytes"], anchor_rows)}

## Recent Files

{markdown_table(["Modified UTC", "Path", "Bytes"], recent_md_rows)}

## Attention

- Missing note status: {len(missing_status)}
- Missing note title: {len(missing_title)}
- Specs without source refs: {len(specs_without_source_refs)}

### Missing status

{chr(10).join(f"- {path}" for path in missing_status[:25]) or "- none"}

### Missing title

{chr(10).join(f"- {path}" for path in missing_title[:25]) or "- none"}

### Specs without source refs

{chr(10).join(f"- {path}" for path in specs_without_source_refs[:25]) or "- none"}
"""
    md_path.write_text(md, encoding="utf-8")
    return json_path, md_path


def main() -> int:
    args = parse_args()
    run_root = Path(args.run_root)
    if not run_root.is_absolute():
        run_root = REPO_ROOT / run_root
    run_root.mkdir(parents=True, exist_ok=True)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = run_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    root_summaries = [summarize_root(REPO_ROOT / rel) for rel in args.roots]
    notes = collect_note_summaries()
    anchors = build_anchor_rows()
    recent_rows = recent_file_rows(args.roots, args.recent)
    json_path, md_path = write_outputs(run_dir, root_summaries, notes, anchors, recent_rows)

    print(
        json.dumps(
            {
                "run_id": run_id,
                "json": str(json_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "markdown": str(md_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "notes_total": len(notes),
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
