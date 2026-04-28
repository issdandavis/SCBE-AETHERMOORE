#!/usr/bin/env python3
"""
Guarded cloud storage sync for SCBE-AETHERMOORE.

Default behavior is dry-run so operators can verify the sync set before upload.

Targets:
  - hf: Push files to a Hugging Face dataset or model repo.
  - mirror: Copy files to a local mirror directory (e.g., Dropbox/Drive-synced folder).

Examples:
  python scripts/system/cloud_storage_sync.py --target hf --repo issdandavis/scbe-aethermoore-training-data --repo-type dataset --push
  python scripts/system/cloud_storage_sync.py --target mirror --mirror-dir "C:\\Users\\issda\\Dropbox\\SCBE_SYNC" --push
  python scripts/system/cloud_storage_sync.py --target both --repo issdandavis/scbe-aethermoore-training-data --repo-type dataset --mirror-dir "C:\\Users\\issda\\Dropbox\\SCBE_SYNC" --push
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shutil
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]

# Keep sync explicit and constrained to durable lanes.
DEFAULT_INCLUDE_GLOBS = [
    "docs/**/*.md",
    "docs/**/*.json",
    "config/**/*.json",
    "config/**/*.yaml",
    "config/**/*.yml",
    "training-data/**/*.jsonl",
    "training-data/**/*.json",
    "training-data/**/*.md",
    "artifacts/**/*.json",
    "artifacts/**/*.jsonl",
    "artifacts/**/*.md",
]

# Safety denylist: never sync likely secrets, env files, or generated caches.
EXCLUDE_PATTERNS = [
    "**/.env",
    "**/.env.*",
    "**/*secret*",
    "**/*token*",
    "**/*credential*",
    "**/*.pem",
    "**/*.key",
    "**/*.p12",
    "**/*.sqlite",
    "**/*.db",
    "**/__pycache__/**",
    "**/.pytest_cache/**",
    "**/node_modules/**",
    "**/dist/**",
    "**/*.exe",
    "**/*.pdb",
]


def _is_excluded(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    return any(fnmatch.fnmatch(rel, pat) for pat in EXCLUDE_PATTERNS)


def _iter_matches(globs: Iterable[str]) -> list[Path]:
    seen: set[str] = set()
    matches: list[Path] = []
    for pattern in globs:
        for path in REPO_ROOT.glob(pattern):
            if not path.is_file():
                continue
            if _is_excluded(path):
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            if rel in seen:
                continue
            seen.add(rel)
            matches.append(path)
    return sorted(matches, key=lambda p: p.relative_to(REPO_ROOT).as_posix())


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _sync_to_mirror(files: list[Path], mirror_dir: Path, push: bool) -> dict:
    summary = {"target": "mirror", "mirror_dir": str(mirror_dir), "copied": 0}
    if not push:
        return summary
    mirror_dir.mkdir(parents=True, exist_ok=True)
    for src in files:
        dst = mirror_dir / src.relative_to(REPO_ROOT)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        summary["copied"] += 1
    return summary


def _sync_to_hf(
    files: list[Path],
    repo_id: str,
    repo_type: str,
    push: bool,
    token: str | None,
    prefix: str,
) -> dict:
    summary = {
        "target": "hf",
        "repo_id": repo_id,
        "repo_type": repo_type,
        "prefix": prefix,
        "uploaded": 0,
    }
    if not push:
        return summary
    try:
        from huggingface_hub import CommitOperationAdd, HfApi  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            f"huggingface_hub is required for --target hf: {exc}. Install with `pip install huggingface_hub`."
        )

    api = HfApi(token=token)
    operations = []
    for src in files:
        rel = _relative(src)
        path_in_repo = f"{prefix.rstrip('/')}/{rel}" if prefix else rel
        operations.append(
            CommitOperationAdd(
                path_or_fileobj=str(src),
                path_in_repo=path_in_repo,
            )
        )
    if operations:
        api.create_commit(
            repo_id=repo_id,
            repo_type=repo_type,
            operations=operations,
            commit_message=f"cloud-sync: {len(operations)} file consolidation batch",
        )
        summary["uploaded"] = len(operations)
    return summary


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Guarded cloud storage sync")
    p.add_argument(
        "--target",
        choices=["hf", "mirror", "both"],
        default="hf",
        help="Sync destination",
    )
    p.add_argument(
        "--include-glob",
        action="append",
        default=[],
        help="Additional include glob (repeatable)",
    )
    p.add_argument(
        "--include-only",
        action="store_true",
        help="Use only --include-glob patterns (skip default include set)",
    )
    p.add_argument(
        "--manifest-out",
        default="artifacts/cloud-sync/manifest.json",
        help="Write sync manifest JSON here",
    )
    p.add_argument("--push", action="store_true", help="Execute upload/copy")
    p.add_argument(
        "--max-files",
        type=int,
        default=1000,
        help="Refuse push when file count exceeds this safety cap",
    )

    # HF options
    p.add_argument("--repo", default=os.getenv("SCBE_CLOUD_HF_REPO", ""), help="HF repo id")
    p.add_argument(
        "--repo-type",
        choices=["dataset", "model", "space"],
        default=os.getenv("SCBE_CLOUD_HF_REPO_TYPE", "dataset"),
        help="HF repo type",
    )
    p.add_argument("--hf-token", default=os.getenv("HF_TOKEN"), help="HF write token")
    p.add_argument(
        "--hf-prefix",
        default=os.getenv("SCBE_CLOUD_HF_PREFIX", "cloud-sync"),
        help="Path prefix in HF repo",
    )

    # Mirror options
    p.add_argument(
        "--mirror-dir",
        default=os.getenv("SCBE_CLOUD_MIRROR_DIR", ""),
        help="Local mirror dir (Dropbox/Drive synced folder)",
    )
    return p


def main() -> int:
    args = build_parser().parse_args()
    include_globs = (
        list(args.include_glob or [])
        if args.include_only
        else list(DEFAULT_INCLUDE_GLOBS) + list(args.include_glob or [])
    )
    if not include_globs:
        raise SystemExit("no include globs resolved; pass --include-glob")
    files = _iter_matches(include_globs)
    if args.push and len(files) > int(args.max_files):
        raise SystemExit(
            f"refusing push: {len(files)} files exceeds --max-files={args.max_files}. "
            "Narrow include globs or raise --max-files explicitly."
        )

    manifest_path = REPO_ROOT / args.manifest_out
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    manifest: dict = {
        "schema": "scbe_cloud_sync_manifest_v1",
        "repo_root": str(REPO_ROOT),
        "push": bool(args.push),
        "target": args.target,
        "files": [_relative(p) for p in files],
        "include_globs": include_globs,
        "exclude_patterns": EXCLUDE_PATTERNS,
        "results": [],
    }

    if args.target in ("hf", "both"):
        if not args.repo:
            raise SystemExit("--repo is required for --target hf/both (or set SCBE_CLOUD_HF_REPO)")
        manifest["results"].append(
            _sync_to_hf(
                files=files,
                repo_id=args.repo,
                repo_type=args.repo_type,
                push=args.push,
                token=args.hf_token,
                prefix=args.hf_prefix,
            )
        )

    if args.target in ("mirror", "both"):
        if not args.mirror_dir:
            raise SystemExit(
                "--mirror-dir is required for --target mirror/both (or set SCBE_CLOUD_MIRROR_DIR)"
            )
        manifest["results"].append(
            _sync_to_mirror(files=files, mirror_dir=Path(args.mirror_dir), push=args.push)
        )

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    mode = "PUSH" if args.push else "DRY-RUN"
    print(f"[cloud-sync] {mode} files={len(files)} target={args.target}")
    print(f"[cloud-sync] manifest={manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

