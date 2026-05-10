#!/usr/bin/env python3
"""Find regenerable-bloat directories and report sizes (read-only).

Locates directories whose contents regenerate (node_modules, .venv, dist,
build, __pycache__, .next, .turbo, target, etc.) and totals their bytes.
Does NOT delete anything. Does NOT descend into OneDrive. Does NOT
descend into the bloat dirs themselves once found (we just sum-then-skip).

Output: artifacts/dedup/regenerable_bloat_<UTC>.json
Schema: regenerable_bloat_v1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "dedup"
DEFAULT_SCOPE_ROOT = Path(r"C:\Users\issda")

# Directories whose contents are regenerable. Case-insensitive match on dir name.
REGENERABLE_DIR_NAMES = {
    "node_modules",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    "__pycache__",
    ".next",
    ".turbo",
    ".nuxt",
    ".cache",
    ".parcel-cache",
    "target",  # rust/cargo
    ".gradle",  # java
    "out",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    "site-packages",
    ".eggs",
    ".tmp-build",
    ".codex_tmp",
    ".pytest_tmp_hallpass_review",
    "coverage",
    ".nyc_output",
    "playwright-report",
    "test-results",
}

# Hard-skip these — never descend into them at all.
HARD_SKIP_DIR_NAMES = {
    "OneDrive",
    "OneDrive - Personal",
    ".claude",
    "AppData",
    ".git",
    ".rustup",  # the rustup toolchain itself, not regenerable
    ".cargo",  # cargo registry — regenerable but huge, separate handling
    ".npm",  # npm cache — regenerable
    ".nuget",
    "Library",
}

_REGEN_LOWER = {n.lower() for n in REGENERABLE_DIR_NAMES}
_HARD_SKIP_LOWER = {n.lower() for n in HARD_SKIP_DIR_NAMES}


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _dir_size_bytes(path: Path) -> Tuple[int, int]:
    """Return (total_bytes, file_count) of everything under path. Errors swallowed."""
    total = 0
    count = 0
    stack = [path]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            try:
                                total += entry.stat(follow_symlinks=False).st_size
                                count += 1
                            except OSError:
                                continue
                    except OSError:
                        continue
        except (PermissionError, OSError, NotADirectoryError):
            continue
    return total, count


def find_bloat(scope_root: Path, *, progress_every: float = 5.0) -> List[Dict]:
    """Walk scope_root, yielding hits at regenerable dirs (no recursion into them)."""
    hits: List[Dict] = []
    last_progress = time.perf_counter()
    dirs_visited = 0
    stack = [scope_root]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        if not entry.is_dir(follow_symlinks=False):
                            continue
                        name_lower = entry.name.lower()
                        if name_lower in _HARD_SKIP_LOWER:
                            continue
                        child = Path(entry.path)
                        if name_lower in _REGEN_LOWER:
                            size_bytes, file_count = _dir_size_bytes(child)
                            hits.append(
                                {
                                    "path": str(child),
                                    "kind": entry.name,
                                    "bytes": size_bytes,
                                    "file_count": file_count,
                                }
                            )
                            # Do NOT descend — we already counted everything under it.
                            continue
                        stack.append(child)
                        dirs_visited += 1
                        now = time.perf_counter()
                        if now - last_progress >= progress_every:
                            print(
                                f"[bloat] visited {dirs_visited} dirs, " f"{len(hits)} regenerable hits so far",
                                file=sys.stderr,
                                flush=True,
                            )
                            last_progress = now
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError, NotADirectoryError):
            continue
    return hits


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scope-root", type=Path, default=DEFAULT_SCOPE_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--top", type=int, default=30)
    args = parser.parse_args(argv)

    if not args.scope_root.exists():
        print(f"scope root does not exist: {args.scope_root}", file=sys.stderr)
        return 2

    started = time.perf_counter()
    print(f"[bloat] scanning {args.scope_root} for regenerable dirs", file=sys.stderr, flush=True)
    hits = find_bloat(args.scope_root)
    elapsed = time.perf_counter() - started
    print(f"[bloat] done in {elapsed:.1f}s: {len(hits)} regenerable dirs found", file=sys.stderr, flush=True)

    by_kind: Dict[str, Dict] = {}
    for h in hits:
        k = h["kind"]
        slot = by_kind.setdefault(k, {"count": 0, "bytes": 0, "file_count": 0})
        slot["count"] += 1
        slot["bytes"] += h["bytes"]
        slot["file_count"] += h["file_count"]

    hits.sort(key=lambda h: h["bytes"], reverse=True)
    total_bytes = sum(h["bytes"] for h in hits)
    total_files = sum(h["file_count"] for h in hits)

    report = {
        "schema": "regenerable_bloat_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope_root": str(args.scope_root),
        "duration_seconds": round(elapsed, 2),
        "regenerable_dir_names": sorted(REGENERABLE_DIR_NAMES),
        "hard_skip_dir_names": sorted(HARD_SKIP_DIR_NAMES),
        "totals": {
            "regenerable_dirs_found": len(hits),
            "total_bytes": total_bytes,
            "total_mb": round(total_bytes / 1024 / 1024, 1),
            "total_gb": round(total_bytes / 1024 / 1024 / 1024, 2),
            "total_files": total_files,
        },
        "by_kind": dict(sorted(by_kind.items(), key=lambda kv: -kv[1]["bytes"])),
        "hits": hits,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / f"regenerable_bloat_{_utc_stamp()}.json"
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print()
    print(f"Report: {out_path}")
    print(
        f"Total regenerable disk: {report['totals']['total_gb']} GB "
        f"({report['totals']['total_files']} files in {len(hits)} dirs)"
    )
    print()
    print("By kind:")
    for k, v in report["by_kind"].items():
        gb = v["bytes"] / 1024 / 1024 / 1024
        print(f"  {k:<24} {v['count']:>5} dirs   {gb:>8.2f} GB   {v['file_count']:>9} files")
    print()
    print(f"Top {args.top} biggest:")
    for i, h in enumerate(hits[: args.top], 1):
        gb = h["bytes"] / 1024 / 1024 / 1024
        path = h["path"]
        if len(path) > 80:
            path = "..." + path[-77:]
        print(f"  {i:>2}. {gb:>7.2f} GB  {h['kind']:<16}  {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
