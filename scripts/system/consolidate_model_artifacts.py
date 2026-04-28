#!/usr/bin/env python3
"""Consolidate duplicate local model artifacts without breaking paths.

This script only touches exact byte-identical duplicates. In apply mode it
replaces duplicate files with hardlinks to one canonical copy, so every original
path still exists and tools can keep using their normal locations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "model_consolidation" / "latest" / "model_consolidation_report.json"
MODEL_EXTENSIONS = {".safetensors", ".bin", ".gguf", ".pt", ".pth", ".ckpt", ".onnx", ".model"}
DEFAULT_ROOTS = (
    "models",
    "artifacts",
    "training/runs",
)
SKIP_PARTS = {".git", "__pycache__", ".pytest_cache", "node_modules"}


@dataclass(frozen=True)
class FileInfo:
    path: Path
    size: int
    sha256: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def iter_model_files(roots: Iterable[Path], min_bytes: int) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            if path.suffix.lower() not in MODEL_EXTENSIONS:
                continue
            try:
                if path.stat().st_size < min_bytes:
                    continue
            except OSError:
                continue
            files.append(path)
    return sorted(set(files), key=lambda p: str(p).lower())


def sha256_file(path: Path, block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(block_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def collect_duplicates(files: list[Path]) -> list[list[FileInfo]]:
    by_size: dict[int, list[Path]] = defaultdict(list)
    for path in files:
        by_size[path.stat().st_size].append(path)

    groups: list[list[FileInfo]] = []
    for size, same_size in by_size.items():
        if len(same_size) < 2:
            continue
        by_hash: dict[str, list[FileInfo]] = defaultdict(list)
        for path in same_size:
            by_hash[sha256_file(path)].append(FileInfo(path=path, size=size, sha256=sha256_file(path)))
        for items in by_hash.values():
            if len(items) > 1:
                groups.append(sorted(items, key=lambda item: canonical_rank(item.path)))
    return sorted(groups, key=lambda group: (-group[0].size, repo_rel(group[0].path)))


def canonical_rank(path: Path) -> tuple[int, str]:
    rel = repo_rel(path).lower()
    score = 50
    if "/final/" in rel or rel.endswith("/adapter_model.safetensors"):
        score -= 15
    if rel.startswith("models/"):
        score -= 12
    if "/merged/" in rel:
        score -= 10
    if "/checkpoint-" in rel:
        score += 8
    if rel.endswith("/optimizer.pt"):
        score += 12
    if "/kaggle_output/" in rel:
        score += 16
    return score, rel


def same_file_id(a: Path, b: Path) -> bool:
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def hardlink_duplicate(canonical: Path, duplicate: Path) -> bool:
    if same_file_id(canonical, duplicate):
        return False
    if canonical.stat().st_dev != duplicate.stat().st_dev:
        return False
    tmp = duplicate.with_name(duplicate.name + ".dedupe-tmp")
    if tmp.exists():
        raise RuntimeError(f"temporary path already exists: {tmp}")
    duplicate.rename(tmp)
    try:
        os.link(canonical, duplicate)
        if duplicate.stat().st_size != canonical.stat().st_size:
            raise RuntimeError(f"hardlink size mismatch: {duplicate}")
        tmp.unlink()
        return True
    except Exception:
        if duplicate.exists():
            duplicate.unlink()
        tmp.rename(duplicate)
        raise


def consolidate(*, roots: list[Path], output: Path, min_bytes: int, apply: bool) -> dict:
    files = iter_model_files(roots, min_bytes)
    groups = collect_duplicates(files)
    planned_saved = sum((len(group) - 1) * group[0].size for group in groups)
    linked = 0
    linked_bytes = 0
    group_reports = []

    for group in groups:
        canonical = group[0]
        duplicates = group[1:]
        duplicate_reports = []
        for item in duplicates:
            action = "would_hardlink"
            if apply:
                changed = hardlink_duplicate(canonical.path, item.path)
                action = "hardlinked" if changed else "already_linked"
                if changed:
                    linked += 1
                    linked_bytes += item.size
            duplicate_reports.append(
                {
                    "path": repo_rel(item.path),
                    "bytes": item.size,
                    "action": action,
                }
            )
        group_reports.append(
            {
                "sha256": canonical.sha256,
                "canonical": repo_rel(canonical.path),
                "duplicate_count": len(duplicates),
                "bytes_per_file": canonical.size,
                "duplicates": duplicate_reports,
            }
        )

    report = {
        "schema_version": "scbe_model_artifact_consolidation_v1",
        "generated_at_utc": utc_now(),
        "mode": "apply" if apply else "dry_run",
        "roots": [repo_rel(root) for root in roots],
        "min_bytes": min_bytes,
        "scanned_file_count": len(files),
        "duplicate_group_count": len(groups),
        "planned_saved_bytes": planned_saved,
        "hardlinked_files": linked,
        "hardlinked_bytes": linked_bytes,
        "groups": group_reports,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Consolidate duplicate model artifacts with hardlinks")
    parser.add_argument("--apply", action="store_true", help="Replace exact duplicates with hardlinks")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--min-mb", type=float, default=1.0)
    parser.add_argument("--root", action="append", default=[])
    args = parser.parse_args()
    roots = [REPO_ROOT / item for item in (args.root or DEFAULT_ROOTS)]
    report = consolidate(
        roots=roots,
        output=Path(args.output),
        min_bytes=int(args.min_mb * 1024 * 1024),
        apply=bool(args.apply),
    )
    print(
        json.dumps(
            {
                "mode": report["mode"],
                "scanned_file_count": report["scanned_file_count"],
                "duplicate_group_count": report["duplicate_group_count"],
                "planned_saved_mb": round(report["planned_saved_bytes"] / 1024 / 1024, 2),
                "hardlinked_files": report["hardlinked_files"],
                "hardlinked_mb": round(report["hardlinked_bytes"] / 1024 / 1024, 2),
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

