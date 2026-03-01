#!/usr/bin/env python3
"""Repo-wide file scanner + organization manifest.

Usage:
  python scripts/repo_scanner.py --root . --obsidian "C:\\Path\\To\\AI Workspace" \
    --compute-hash --max-hash-size-mb 5
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import hashlib
import json
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence


DEFAULT_IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "__pycache__",
    ".obsidian",
}

DEFAULT_IGNORE_FILES = {
    ".DS_Store",
    "thumbs.db",
}


@dataclass
class FileRecord:
    source: str
    path: str
    size_bytes: int
    mtime_utc: str
    extension: str
    is_symlink: bool
    is_readable: bool
    sha256: str | None = None

    def to_json(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Inventory and scan file layout for SCBE repos and vaults.")
    p.add_argument("--root", default=".", help="Primary repository/workspace root to scan")
    p.add_argument("--obsidian", default="", help="Optional Obsidian vault path")
    p.add_argument("--out-dir", default="artifacts/repo_scans", help="Output directory for scan artifacts")
    p.add_argument("--include", nargs="*", default=[], help="Additional include root paths (alias to separate source)")
    p.add_argument("--name", default="scan", help="Name tag used in output filenames")
    p.add_argument("--max-depth", type=int, default=None, help="Optional max directory depth")
    p.add_argument("--compute-hash", action="store_true", help="Compute sha256 for small files")
    p.add_argument("--max-hash-size-mb", type=float, default=1.0, help="Do not hash files larger than this size")
    p.add_argument("--max-size-mb", type=float, default=200.0, help="Skip files larger than this size")
    p.add_argument("--ignore", action="append", default=[], help="Additional path patterns to ignore")
    p.add_argument("--no-default-ignores", action="store_true", help="Scan hidden/generated dirs too")
    p.add_argument("--follow-symlinks", action="store_true", help="Follow symlinks (default: false)")
    p.add_argument("--format", choices=["json", "md", "csv", "all"], default="all")
    p.add_argument("--no-skips", action="store_true", help="Do not emit skipped files summary")
    return p.parse_args()


def load_gitignore_patterns(root: Path) -> List[str]:
    gitignore = root / ".gitignore"
    patterns: List[str] = []
    if not gitignore.exists():
        return patterns
    for line in gitignore.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line.replace("\\", "/"))
    return patterns


def build_ignore_patterns(args: argparse.Namespace, root: Path) -> List[str]:
    patterns = list(load_gitignore_patterns(root))
    if not args.no_default_ignores:
        patterns.extend([f"**/{d}/**" for d in DEFAULT_IGNORE_DIRS])
        patterns.extend(DEFAULT_IGNORE_FILES)
    patterns.extend(args.ignore)
    return list(dict.fromkeys(patterns))


def match_ignore(rel: Path, patterns: Sequence[str]) -> bool:
    rel_path = rel.as_posix()
    for raw in patterns:
        pat = raw.replace("\\", "/")
        # Normalize common gitignore forms.
        if pat.startswith("/"):
            pat = pat[1:]
        if pat.endswith("/"):
            pat = pat.rstrip("/")
            if rel_path == pat or rel_path.startswith(pat + "/"):
                return True
        if pat.endswith("/**"):
            pfx = pat[:-3]
            if rel_path == pfx or rel_path.startswith(pfx + "/"):
                return True
        if fnmatch.fnmatch(rel_path, pat) or fnmatch.fnmatch(rel.name, pat):
            return True
    return False


def sha256_file(path: Path, max_size_bytes: int) -> str | None:
    try:
        size = path.stat().st_size
        if size > max_size_bytes:
            return None
    except OSError:
        return None

    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def scan_root(
    source: str,
    root: Path,
    ignore_patterns: Sequence[str],
    max_depth: int | None,
    max_file_bytes: int,
    compute_hash: bool,
    max_hash_bytes: int,
    follow_symlinks: bool,
) -> tuple[list[FileRecord], dict[str, int], list[str]]:
    files: list[FileRecord] = []
    skipped: list[str] = []
    extension_counts: Counter[str] = Counter()

    if not root.exists():
        return files, {"missing_root": 1}, [f"{source}: missing root {root}"]

    for dirpath, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
        cur_dir = Path(dirpath)
        rel_dir = cur_dir.relative_to(root)
        depth = len(rel_dir.parts) if str(rel_dir) != "." else 0
        if max_depth is not None and depth > max_depth:
            dirnames[:] = []
            continue

        # Prune ignored directories to avoid unnecessary traversal.
        for d in list(dirnames):
            rel_d = rel_dir / d
            if match_ignore(rel_d, ignore_patterns):
                skipped.append(f"{source}:{rel_d.as_posix()}/ (dir ignored)")
                dirnames.remove(d)

        for fname in filenames:
            raw = cur_dir / fname
            rel = raw.relative_to(root)
            if match_ignore(rel, ignore_patterns):
                skipped.append(f"{source}:{rel}")
                continue
            try:
                stat = raw.stat()
            except OSError as exc:
                skipped.append(f"{source}:{rel} (stat error: {exc})")
                continue
            if stat.st_size > max_file_bytes:
                skipped.append(f"{source}:{rel} (size {stat.st_size})")
                continue

            digest = None
            if compute_hash:
                digest = sha256_file(raw, max_hash_bytes)

            files.append(
                FileRecord(
                    source=source,
                    path=rel.as_posix(),
                    size_bytes=stat.st_size,
                    mtime_utc=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    extension=raw.suffix.lower() or "<no_ext>",
                    is_symlink=raw.is_symlink(),
                    is_readable=True,
                    sha256=digest,
                )
            )
            extension_counts[raw.suffix.lower() or "<no_ext>"] += 1

    return files, dict(extension_counts), skipped


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: List[FileRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source", "path", "size_bytes", "mtime_utc", "extension", "is_symlink", "is_readable", "sha256"])
        for r in rows:
            w.writerow([r.source, r.path, r.size_bytes, r.mtime_utc, r.extension, str(r.is_symlink), str(r.is_readable), r.sha256 or ""])


def write_md(path: Path, rows: List[FileRecord], summary: Dict[str, Any], skipped: list[str], include_skips: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    total = len(rows)
    total_bytes = sum(r.size_bytes for r in rows)
    ext_top = sorted(summary.get("extensions", {}).items(), key=lambda kv: kv[1], reverse=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# Repository Scan Report\n\n")
        f.write(f"Generated: {summary['generated_at']}\n\n")
        f.write(f"- Total files: {total}\n")
        f.write(f"- Total bytes: {total_bytes}\n")
        f.write(f"- Skipped count: {summary.get('skipped_count', 0)}\n")
        f.write(f"- Total roots: {len(summary.get('roots', []))}\n\n")
        for r in summary.get("roots", []):
            f.write(f"- {r['source']}: {r['path']}\n")
        f.write("\n## Top extensions\n\n")
        for ext, count in ext_top[:30]:
            f.write(f"- `{ext}`: {count}\n")

        f.write("\n## Duplicate hash candidates\n\n")
        by_hash: Dict[str, List[str]] = {}
        for row in rows:
            if not row.sha256:
                continue
            by_hash.setdefault(row.sha256, []).append(f"{row.source}:{row.path}")
        duplicate_groups = [(h, lst) for h, lst in by_hash.items() if len(lst) > 1]
        if duplicate_groups:
            for h, paths in sorted(duplicate_groups, key=lambda kv: len(kv[1]), reverse=True):
                f.write(f"- `{h}`: {len(paths)}\n")
                for p in paths:
                    f.write(f"  - {p}\n")
        else:
            f.write("- No duplicate hashes in scanned files.\n")

        if include_skips:
            f.write("\n## Skipped files\n\n")
            for s in skipped[:500]:
                f.write(f"- {s}\n")
            if len(skipped) > 500:
                f.write(f"- ... ({len(skipped)-500} more skipped not shown)\n")


def main() -> None:
    args = parse_args()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    repo_root = Path(args.root).expanduser().resolve()
    roots = [("repo", repo_root)]
    if args.obsidian:
        roots.append(("obsidian", Path(args.obsidian).expanduser().resolve()))
    for idx, inc in enumerate(args.include, start=1):
        roots.append((f"extra-{idx}", Path(inc).expanduser().resolve()))

    all_files: list[FileRecord] = []
    skipped_total: list[str] = []
    extension_total: Counter[str] = Counter()
    root_summaries: list[dict[str, Any]] = []

    max_file_bytes = int(args.max_size_mb * 1024 * 1024)
    max_hash_bytes = int(args.max_hash_size_mb * 1024 * 1024)

    for source, root in roots:
        ignore_patterns = build_ignore_patterns(args, root)
        files, ext_counts, skipped = scan_root(
            source=source,
            root=root,
            ignore_patterns=ignore_patterns,
            max_depth=args.max_depth,
            max_file_bytes=max_file_bytes,
            compute_hash=args.compute_hash,
            max_hash_bytes=max_hash_bytes,
            follow_symlinks=args.follow_symlinks,
        )
        all_files.extend(files)
        skipped_total.extend(skipped)
        extension_total.update(ext_counts)
        root_summaries.append({
            "source": source,
            "path": str(root),
            "files": len(files),
            "bytes": sum(f.size_bytes for f in files),
        })

    output_dir = Path(args.out_dir).expanduser().resolve()
    stamp_dir = output_dir / f"{ts}-{args.name}"

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scan_name": args.name,
        "roots": root_summaries,
        "file_count": len(all_files),
        "skipped_count": len(skipped_total),
        "max_file_size_mb": args.max_size_mb,
        "compute_hash": args.compute_hash,
        "max_hash_size_mb": args.max_hash_size_mb,
        "extensions": dict(extension_total.most_common()),
    }

    records = [r.to_json() for r in all_files]

    if args.format in ("json", "all"):
        write_json(stamp_dir / "scan_manifest.json", {"summary": summary, "files": records})
        write_json(stamp_dir / "scan_summary.json", summary)
    if args.format in ("csv", "all"):
        write_csv(stamp_dir / "scan_manifest.csv", all_files)
    if args.format in ("md", "all"):
        write_md(stamp_dir / "scan_report.md", all_files, summary, skipped_total, not args.no_skips)

    print(f"Scan complete: {len(all_files)} files")
    print(f"Output: {stamp_dir}")
    print(f"Skipped: {len(skipped_total)}")


if __name__ == "__main__":
    main()
