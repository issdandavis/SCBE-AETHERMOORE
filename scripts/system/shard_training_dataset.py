#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "_staging" / "training-data-repo"
DEFAULT_MANIFEST = "manifests/training_dataset_manifest.json"
DEFAULT_MAX_BYTES = 45 * 1024 * 1024


@dataclass
class OutputShard:
    path: str
    bytes: int
    rows: int
    sha256: str


def should_exclude(path: Path, exclude_globs: Iterable[str]) -> bool:
    normalized = str(repo_relative(path)).replace("\\", "/")
    for pattern in exclude_globs:
        normalized_pattern = pattern.replace("\\", "/")
        if fnmatch.fnmatch(normalized, normalized_pattern) or fnmatch.fnmatch(path.name, normalized_pattern):
            return True
        if "/" in normalized_pattern and normalized.endswith(normalized_pattern):
            return True
    return False


def discover_jsonl_files(inputs: Iterable[str], output_root: Path, exclude_globs: Iterable[str] = ()) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for raw in inputs:
        path = Path(raw)
        if not path.is_absolute():
            path = (REPO_ROOT / path).resolve()
        if not path.exists():
            continue
        candidates = [path] if path.is_file() else sorted(path.rglob("*.jsonl"))
        for candidate in candidates:
            candidate = candidate.resolve()
            if candidate.is_dir() or candidate.suffix.lower() != ".jsonl":
                continue
            if output_root in candidate.parents:
                continue
            if should_exclude(candidate, exclude_globs):
                continue
            if candidate not in seen:
                seen.add(candidate)
                files.append(candidate)
    return sorted(files)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_rows(path: Path) -> int:
    count = 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def repo_relative(path: Path) -> Path:
    try:
        return path.relative_to(REPO_ROOT)
    except ValueError:
        return Path(path.name)


def dataset_relative(path: Path) -> Path:
    rel_path = repo_relative(path)
    if not rel_path.parts:
        return rel_path
    if rel_path.parts[0] == "training-data":
        return rel_path
    return Path("generated") / Path(path.name)


def destination_stem(source: Path, rel_path: Path) -> Path:
    rel_parent = rel_path.parent
    if rel_parent == Path("."):
        rel_parent = Path()
    return Path("data") / rel_parent / source.stem


def copy_as_single(source: Path, dest_path: Path, output_root: Path) -> OutputShard:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest_path)
    return OutputShard(
        path=str(dest_path.relative_to(output_root)).replace("\\", "/"),
        bytes=dest_path.stat().st_size,
        rows=count_rows(dest_path),
        sha256=sha256_file(dest_path),
    )


def shard_jsonl(source: Path, dest_stem: Path, output_root: Path, max_bytes: int) -> list[OutputShard]:
    shards: list[OutputShard] = []
    part_index = 0
    current_path: Path | None = None
    current_handle = None
    current_bytes = 0
    current_rows = 0
    current_digest = hashlib.sha256()

    def open_part() -> None:
        nonlocal part_index, current_path, current_handle, current_bytes, current_rows, current_digest
        part_index += 1
        current_path = output_root / f"{dest_stem}.part-{part_index:04d}.jsonl"
        current_path.parent.mkdir(parents=True, exist_ok=True)
        current_handle = current_path.open("wb")
        current_bytes = 0
        current_rows = 0
        current_digest = hashlib.sha256()

    def close_part() -> None:
        nonlocal current_path, current_handle, current_bytes, current_rows, current_digest
        if current_handle is None or current_path is None:
            return
        current_handle.close()
        shards.append(
            OutputShard(
                path=str(current_path.relative_to(output_root)).replace("\\", "/"),
                bytes=current_bytes,
                rows=current_rows,
                sha256=current_digest.hexdigest(),
            )
        )
        current_path = None
        current_handle = None

    with source.open("rb") as handle:
        for raw_line in handle:
            if not raw_line.strip():
                continue
            if current_handle is None:
                open_part()
            line_bytes = len(raw_line)
            if current_rows > 0 and current_bytes + line_bytes > max_bytes:
                close_part()
                open_part()
            assert current_handle is not None
            current_handle.write(raw_line)
            current_digest.update(raw_line)
            current_bytes += line_bytes
            current_rows += 1

    close_part()
    return shards


def build_readme(manifest: dict) -> str:
    lines = [
        "# SCBE Training Data Staging Repo",
        "",
        "This tree is generated for a separate GitHub or dataset repository so the main code repo does not carry oversized JSONL history.",
        "",
        "## Rules",
        "",
        f"- Max shard size: `{manifest['max_bytes']}` bytes",
        "- Output data lives under `data/`",
        "- Manifest lives under `manifests/training_dataset_manifest.json`",
        "- Regenerate from the source repo instead of editing shards by hand",
        "",
        "## Summary",
        "",
        f"- Source files: `{manifest['counts']['source_files']}`",
        f"- Output files: `{manifest['counts']['output_files']}`",
        f"- Total rows: `{manifest['counts']['rows']}`",
    ]
    if manifest.get("dataset_repo"):
        lines.extend(["", f"Target repo: `{manifest['dataset_repo']}`"])
    return "\n".join(lines) + "\n"


def stage_dataset_repo(
    inputs: Iterable[str],
    output_root: Path,
    max_bytes: int,
    dataset_repo: str | None = None,
    exclude_globs: Iterable[str] = (),
) -> dict:
    output_root.mkdir(parents=True, exist_ok=True)
    files = discover_jsonl_files(inputs, output_root, exclude_globs=exclude_globs)
    if not files:
        raise ValueError("No JSONL files found for staging")

    records = []
    total_output_files = 0
    total_rows = 0

    for source in files:
        source_rel_path = repo_relative(source)
        rel_path = dataset_relative(source)
        source_rows = count_rows(source)
        source_bytes = source.stat().st_size
        if source_rows == 0:
            continue
        dest_rel_path = Path("data") / rel_path

        if source_bytes <= max_bytes:
            shard = copy_as_single(source, output_root / dest_rel_path, output_root)
            outputs = [shard]
            mode = "copied"
        else:
            outputs = shard_jsonl(source, destination_stem(source, rel_path), output_root, max_bytes)
            mode = "sharded"

        total_output_files += len(outputs)
        total_rows += source_rows
        records.append(
            {
                "source_path": str(source_rel_path).replace("\\", "/"),
                "source_bytes": source_bytes,
                "source_rows": source_rows,
                "mode": mode,
                "outputs": [output.__dict__ for output in outputs],
            }
        )

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_repo": dataset_repo,
        "max_bytes": max_bytes,
        "inputs": [str(Path(item)) for item in inputs],
        "exclude_globs": list(exclude_globs),
        "counts": {
            "source_files": len(records),
            "output_files": total_output_files,
            "rows": total_rows,
        },
        "files": records,
    }

    manifest_path = output_root / DEFAULT_MANIFEST
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output_root / "README.md").write_text(build_readme(manifest), encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Shard oversized JSONL files into a GitHub-safe staging repo")
    parser.add_argument("--input", action="append", required=True, help="JSONL file or directory to stage")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output staging repo root")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES, help="Maximum bytes per output file")
    parser.add_argument("--dataset-repo", default=None, help="Optional target repo name for README and manifest")
    parser.add_argument("--exclude-glob", action="append", default=[], help="Glob for JSONL paths to skip")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = Path(args.output)
    if not output_root.is_absolute():
        output_root = (REPO_ROOT / output_root).resolve()
    manifest = stage_dataset_repo(
        inputs=args.input,
        output_root=output_root,
        max_bytes=args.max_bytes,
        dataset_repo=args.dataset_repo,
        exclude_globs=args.exclude_glob,
    )
    print(f"Staged {manifest['counts']['source_files']} source files into {manifest['counts']['output_files']} output files")
    print(f"Manifest: {output_root / DEFAULT_MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
