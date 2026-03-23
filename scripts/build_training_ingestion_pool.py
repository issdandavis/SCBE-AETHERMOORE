#!/usr/bin/env python3
"""Build a governed training-ingestion pool from refreshed code/docs/note sources."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "training" / "sft_records" / "sft_ingestion_pool.jsonl"
DEFAULT_DOC_OUTPUT = REPO_ROOT / "training" / "ingest" / "doc_chunks.jsonl"
DEFAULT_RUN_ROOT = REPO_ROOT / "training" / "runs" / "training_ingestion_pool"
DEFAULT_CODEBASE_SFT = REPO_ROOT / "training-data" / "sft_codebase.jsonl"
DEFAULT_DOC_GLOBS = (
    "docs/**/*.md",
    "notes/**/*.md",
    "content/articles/**/*.md",
    "notebooks/**/*.ipynb",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def path_for_manifest(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            raw = raw.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def count_jsonl_rows(path: Path) -> int:
    return len(read_jsonl(path))


def collect_source_files(patterns: Iterable[str]) -> list[str]:
    files: list[str] = []
    seen: set[str] = set()
    for pattern in patterns:
        for match in sorted(REPO_ROOT.glob(pattern)):
            if not match.is_file():
                continue
            rel = path_for_manifest(match)
            if rel in seen:
                continue
            seen.add(rel)
            files.append(rel)
    return files


def run_subprocess(cmd: list[str], *, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=True)


def refresh_codebase_sft() -> dict[str, Any]:
    script_path = REPO_ROOT / "scripts" / "codebase_to_sft.py"
    before_count = count_jsonl_rows(DEFAULT_CODEBASE_SFT)
    result = run_subprocess([sys.executable, str(script_path)])
    after_count = count_jsonl_rows(DEFAULT_CODEBASE_SFT)
    return {
        "status": "ok",
        "script": path_for_manifest(script_path),
        "output_path": path_for_manifest(DEFAULT_CODEBASE_SFT),
        "record_count_before": before_count,
        "record_count_after": after_count,
        "stdout_tail": result.stdout.splitlines()[-10:],
        "stderr_tail": result.stderr.splitlines()[-10:],
    }


def refresh_doc_chunks(
    *,
    output_path: Path,
    patterns: Iterable[str],
    chunk_size: int,
    overlap: int,
) -> dict[str, Any]:
    script_path = REPO_ROOT / "scripts" / "ingest_docs_to_training_jsonl.py"
    source_files = collect_source_files(patterns)
    if not source_files:
        write_jsonl(output_path, [])
        return {
            "status": "no_sources",
            "script": path_for_manifest(script_path),
            "output_path": path_for_manifest(output_path),
            "source_file_count": 0,
            "record_count": 0,
            "patterns": list(patterns),
        }

    cmd = [
        sys.executable,
        str(script_path),
        "--out",
        str(output_path),
        "--chunk-size",
        str(chunk_size),
        "--overlap",
        str(overlap),
    ]
    for pattern in patterns:
        cmd.extend(["--glob", pattern])
    result = run_subprocess(cmd)
    record_count = count_jsonl_rows(output_path)
    return {
        "status": "ok",
        "script": path_for_manifest(script_path),
        "output_path": path_for_manifest(output_path),
        "source_file_count": len(source_files),
        "record_count": record_count,
        "patterns": list(patterns),
        "stdout_tail": result.stdout.splitlines()[-10:],
        "stderr_tail": result.stderr.splitlines()[-10:],
    }


def infer_track_from_path(source_path: str) -> str:
    lowered = source_path.lower()
    if "govern" in lowered or "policy" in lowered or "security" in lowered:
        return "governance"
    if lowered.endswith((".py", ".ts", ".tsx", ".js", ".mjs", ".ipynb")) or "/scripts/" in lowered:
        return "functions"
    return "system"


def infer_category_from_path(source_path: str) -> str:
    lowered = source_path.lower()
    if lowered.endswith(".ipynb") or "/notebooks/" in lowered:
        return "notebook-reference"
    if "/content/articles/" in lowered:
        return "article-reference"
    if "/notes/" in lowered:
        return "research-note"
    if "govern" in lowered or "policy" in lowered:
        return "governance-reference"
    return "architecture-reference"


def build_doc_sft_records(doc_rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, row in enumerate(doc_rows, start=1):
        source_text = str(row.get("source_text", "")).strip()
        source_path = str(row.get("source_path", "")).strip().replace("\\", "/")
        chunk_index = int(row.get("chunk_index", 0) or 0)
        if not source_text or not source_path:
            continue
        category = infer_category_from_path(source_path)
        track = infer_track_from_path(source_path)
        records.append(
            {
                "id": f"ingestion-pool-{index:05d}",
                "category": category,
                "instruction": f"Explain the key material captured in `{source_path}` chunk {chunk_index}.",
                "response": source_text,
                "metadata": {
                    "origin": "training_ingestion_pool",
                    "source_type": "doc_chunk",
                    "source_file": source_path,
                    "chunk_index": chunk_index,
                    "track": track,
                    "quality": {
                        "dedup": True,
                        "validated": False,
                    },
                },
            }
        )
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a governed SCBE training ingestion pool")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--doc-output", default=str(DEFAULT_DOC_OUTPUT))
    parser.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT))
    parser.add_argument("--chunk-size", type=int, default=1400)
    parser.add_argument("--overlap", type=int, default=250)
    parser.add_argument("--skip-codebase-refresh", action="store_true")
    parser.add_argument("--skip-doc-ingest", action="store_true")
    parser.add_argument("--glob", action="append", dest="patterns", help="Override doc source globs")
    return parser.parse_args()


def build_ingestion_pool(
    *,
    output_path: Path = DEFAULT_OUTPUT,
    doc_output_path: Path = DEFAULT_DOC_OUTPUT,
    run_root: Path = DEFAULT_RUN_ROOT,
    chunk_size: int = 1400,
    overlap: int = 250,
    skip_codebase_refresh: bool = False,
    skip_doc_ingest: bool = False,
    patterns: Iterable[str] = DEFAULT_DOC_GLOBS,
) -> dict[str, Any]:
    run_id = make_run_id()
    run_dir = run_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "generated_at": utc_now(),
        "run_id": run_id,
        "output_path": path_for_manifest(output_path),
        "doc_output_path": path_for_manifest(doc_output_path),
        "patterns": list(patterns),
    }

    if skip_codebase_refresh:
        summary["codebase_refresh"] = {"status": "skipped"}
    else:
        summary["codebase_refresh"] = refresh_codebase_sft()

    if skip_doc_ingest:
        summary["doc_ingest"] = {
            "status": "skipped",
            "output_path": path_for_manifest(doc_output_path),
        }
    else:
        summary["doc_ingest"] = refresh_doc_chunks(
            output_path=doc_output_path,
            patterns=patterns,
            chunk_size=chunk_size,
            overlap=overlap,
        )

    doc_rows = read_jsonl(doc_output_path)
    sft_records = build_doc_sft_records(doc_rows)
    record_count = write_jsonl(output_path, sft_records)
    summary["sft_ingestion_pool"] = {
        "status": "ok",
        "record_count": record_count,
        "source_doc_chunks": len(doc_rows),
        "output_path": path_for_manifest(output_path),
    }

    summary_path = run_dir / "run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary["run_summary_path"] = path_for_manifest(summary_path)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    args = parse_args()
    summary = build_ingestion_pool(
        output_path=Path(args.output),
        doc_output_path=Path(args.doc_output),
        run_root=Path(args.run_root),
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        skip_codebase_refresh=args.skip_codebase_refresh,
        skip_doc_ingest=args.skip_doc_ingest,
        patterns=tuple(args.patterns or DEFAULT_DOC_GLOBS),
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
