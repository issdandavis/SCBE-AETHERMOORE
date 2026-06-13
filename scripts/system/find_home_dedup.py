#!/usr/bin/env python3
"""Read-only home-directory duplicate-file finder.

Walks a user-home subtree and reports byte-identical files grouped by
sha256. Writes ONE artifact: a JSON report. Does NOT delete, move,
copy, hash open, or otherwise mutate any input file.

Hard-excluded paths (never descended into):
  - Microsoft OneDrive subtree (would force file hydration on Win)
  - .claude/ session memory (Claude Code auto-managed; corrupting it
    breaks the session)
  - AppData/ (Windows app state; touching is the road to ruin)
  - any **/node_modules/, **/.git/, **/.venv/, **/dist/, **/build/,
    **/__pycache__/, **/.pytest_cache/, **/.codex_tmp/, **/.tmp-build/
  - any **/artifacts/aetherdesk_receipts/ (append-only governance log)

Output schema: home_dedup_report_v1
  {
    "schema": "home_dedup_report_v1",
    "generated_at": "...",
    "scope_root": "...",
    "files_scanned": int,
    "files_hashed": int,
    "files_skipped_too_large": int,
    "files_skipped_too_small": int,
    "files_skipped_unreadable": int,
    "directories_excluded": [...],
    "duplicate_clusters": [
      {
        "sha256": "...",
        "bytes_each": int,
        "n_copies": int,
        "bytes_recoverable": int,   # (n-1) * bytes_each
        "paths": [...],             # all copies, longest first
        "suggested_keep": "...",    # canonical-ish keeper
        "risk": "low" | "medium" | "high"
      },
      ...
    ],
    "totals": {
      "n_clusters": int,
      "n_redundant_files": int,
      "bytes_recoverable_total": int
    }
  }
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

DEFAULT_SCOPE_ROOT = Path(r"C:\Users\issda")
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "dedup"

# Names that should never be descended into anywhere they appear.
EXCLUDE_DIR_NAMES: Set[str] = {
    "OneDrive",
    "OneDrive - Personal",
    ".claude",
    "AppData",
    "node_modules",
    ".git",
    ".venv",
    ".env",
    "venv",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".codex_tmp",
    ".tmp-build",
    ".pytest_tmp_hallpass_review",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".gradle",
    ".m2",
    ".cargo",
    ".rustup",
    ".npm",
    ".yarn",
    ".nuget",
    "site-packages",
    # SCBE bulk dirs — millions of small training/intake artifacts that
    # are not actionable for dedup (they're append-only by design).
    "training-data",
    "training-runs",
    "training_data",
    "intake",
    "training",
    "origin",
    ".scbe",
    "scbe-aethermoore",  # nested mirror of the repo inside itself
    "artifacts",
    "dropbox_brain",  # external mirror, owned elsewhere
    ".cache",
    ".local",
    "Library",  # macOS-style cache dir if present
    "Logs",
}

# Paths that should never be descended into at this exact location
# (relative to scope root). For things that legitimately use one of the
# names above and shouldn't be excluded, add an exception here later.
EXCLUDE_RELATIVE_PATHS: Set[str] = {
    "SCBE-AETHERMOORE/artifacts/aetherdesk_receipts",
    "SCBE-AETHERMOORE/artifacts/build-tmp",
    "SCBE-AETHERMOORE/artifacts/pytest_tmp",
    "SCBE-AETHERMOORE/artifacts/playwright-both-side",
    "SCBE-AETHERMOORE/artifacts/scbe_min",
    "SCBE-AETHERMOORE/.scbe/lanes",
    "SCBE-AETHERMOORE/.scbe/packets",
    "SCBE-AETHERMOORE/.scbe/skill_registry",
}

# File-name extensions that are almost always either generated or where
# duplicate detection is unhelpful. We still hash them but flag them
# higher-risk so the user knows to think before deleting.
GENERATED_EXTENSIONS = {".pyc", ".pyo", ".o", ".so", ".dll", ".dylib", ".class"}

# We intentionally skip anything bigger than this on the first pass —
# hashing 5GB models eats hours. The report still lists their existence.
DEFAULT_MAX_HASH_BYTES = 500 * 1024 * 1024  # 500 MB

# Files this small are almost always system config (empty markers,
# .keep, .gitkeep, etc.) and would generate huge spurious clusters.
DEFAULT_MIN_HASH_BYTES = 256


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


_EXCLUDE_DIR_NAMES_LOWER = {n.lower() for n in EXCLUDE_DIR_NAMES}


def _is_excluded_dir(path: Path, scope_root: Path) -> bool:
    # Windows file system is case-insensitive — match accordingly.
    if path.name.lower() in _EXCLUDE_DIR_NAMES_LOWER:
        return True
    try:
        rel = path.relative_to(scope_root).as_posix()
    except ValueError:
        return False
    return rel in EXCLUDE_RELATIVE_PATHS


def _walk_safely(scope_root: Path) -> Iterable[Tuple[Path, int]]:
    """Yield (file_path, size_bytes) tuples, descending only into safe dirs.

    Uses os.scandir for speed and to avoid forcing OneDrive hydration
    of files we never open.
    """
    stack: List[Path] = [scope_root]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            child = Path(entry.path)
                            if _is_excluded_dir(child, scope_root):
                                continue
                            stack.append(child)
                        elif entry.is_file(follow_symlinks=False):
                            try:
                                size = entry.stat(follow_symlinks=False).st_size
                            except OSError:
                                continue
                            yield Path(entry.path), size
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError, NotADirectoryError):
            continue


def _sha256_file(path: Path, chunk_size: int = 1 << 20) -> Optional[str]:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            while True:
                chunk = fh.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except (PermissionError, OSError):
        return None


def _suggest_keeper(paths: List[str]) -> Tuple[str, str]:
    """Pick the canonical keeper from a list of duplicate paths.

    Heuristic (low to high preference):
      1. Inside SCBE-AETHERMOORE/origin/ replica  -> avoid (it's a mirror)
      2. Inside .home/.agents/skills/             -> avoid
      3. Inside artifacts/                        -> avoid
      4. Inside src/, tests/, docs/, book/        -> prefer
      5. Shorter path tiebreak
    """

    def rank(p: str) -> Tuple[int, int]:
        norm = p.replace("\\", "/").lower()
        # Higher first-element = LESS preferred
        if "/origin/" in norm:
            tier = 9
        elif "/.home/.agents/skills/" in norm:
            tier = 8
        elif "/artifacts/" in norm:
            tier = 7
        elif "/training-data/" in norm or "/training-runs/" in norm:
            tier = 6
        elif "/src/" in norm or "/tests/" in norm or "/docs/" in norm or "/book/" in norm:
            tier = 1
        elif "/scbe-aethermoore/" in norm and "/scbe-aethermoore/scbe-aethermoore/" not in norm:
            tier = 2
        else:
            tier = 5
        return (tier, len(p))

    best = sorted(paths, key=rank)[0]

    # Reason: state which heuristic chose it
    norm = best.replace("\\", "/").lower()
    if "/src/" in norm or "/tests/" in norm or "/docs/" in norm or "/book/" in norm:
        reason = "in canonical source tree (src/tests/docs/book)"
    elif "/scbe-aethermoore/" in norm:
        reason = "inside repo root (preferred over external mirrors)"
    else:
        reason = "shortest path among non-mirror candidates"
    return best, reason


def _classify_risk(paths: List[str]) -> str:
    """Conservative risk class for a duplicate cluster."""
    norms = [p.replace("\\", "/").lower() for p in paths]
    # If any copy is under a contracts / proposal / sealed / private path,
    # mark high-risk regardless. We never want to nudge the user toward
    # collapsing those.
    high_risk_substrings = (
        "/scbe-private/",
        "/proposals/",
        "/contracts/",
        "/contracting/",
        "/dava_blind",
        "/sealed",
        "/.secrets/",
        "/.ssh/",
        "/credentials",
        "/keys/",
    )
    for n in norms:
        if any(s in n for s in high_risk_substrings):
            return "high"
    # Anything with an extension we know is generated -> low risk to dedupe
    if all(Path(p).suffix.lower() in GENERATED_EXTENSIONS for p in paths):
        return "low"
    # If all copies are inside artifacts/ or origin/ mirrors, low risk
    if all("/artifacts/" in n or "/origin/" in n for n in norms):
        return "low"
    return "medium"


def scan(
    scope_root: Path,
    *,
    min_size: int,
    max_size: int,
    progress_every: int = 5000,
) -> Dict:
    if not scope_root.exists():
        raise FileNotFoundError(f"scope root does not exist: {scope_root}")

    started_at = time.perf_counter()
    files_scanned = 0
    files_hashed = 0
    files_skipped_too_large = 0
    files_skipped_too_small = 0
    files_skipped_unreadable = 0

    # First pass: build size_groups so we only hash files that have at
    # least one same-size sibling. This skips the vast majority of files
    # (their size alone proves they're unique).
    size_groups: Dict[int, List[Path]] = {}
    print(f"[dedup] walking {scope_root} (excluding hazard dirs)", file=sys.stderr, flush=True)
    for path, size in _walk_safely(scope_root):
        files_scanned += 1
        if files_scanned % progress_every == 0:
            elapsed = time.perf_counter() - started_at
            print(
                f"[dedup] walked {files_scanned} files in {elapsed:.1f}s, " f"{len(size_groups)} distinct sizes",
                file=sys.stderr,
                flush=True,
            )
        if size < min_size:
            files_skipped_too_small += 1
            continue
        if size > max_size:
            files_skipped_too_large += 1
            continue
        size_groups.setdefault(size, []).append(path)

    candidate_groups = {sz: paths for sz, paths in size_groups.items() if len(paths) > 1}
    n_candidates = sum(len(p) for p in candidate_groups.values())
    print(
        f"[dedup] walk complete: {files_scanned} files, "
        f"{n_candidates} candidates in {len(candidate_groups)} same-size groups; hashing...",
        file=sys.stderr,
        flush=True,
    )

    hash_to_paths: Dict[str, List[Path]] = {}
    for paths in candidate_groups.values():
        for p in paths:
            digest = _sha256_file(p)
            if digest is None:
                files_skipped_unreadable += 1
                continue
            files_hashed += 1
            hash_to_paths.setdefault(digest, []).append(p)
            if files_hashed % 500 == 0:
                elapsed = time.perf_counter() - started_at
                print(
                    f"[dedup] hashed {files_hashed} files in {elapsed:.1f}s",
                    file=sys.stderr,
                    flush=True,
                )

    clusters: List[Dict] = []
    n_redundant = 0
    bytes_recoverable_total = 0
    for digest, paths in hash_to_paths.items():
        if len(paths) < 2:
            continue
        try:
            bytes_each = paths[0].stat().st_size
        except OSError:
            continue
        path_strs = sorted(str(p) for p in paths)
        keeper, keeper_reason = _suggest_keeper(path_strs)
        bytes_recoverable = (len(paths) - 1) * bytes_each
        risk = _classify_risk(path_strs)
        clusters.append(
            {
                "sha256": digest,
                "bytes_each": bytes_each,
                "n_copies": len(paths),
                "bytes_recoverable": bytes_recoverable,
                "paths": path_strs,
                "suggested_keep": keeper,
                "suggested_keep_reason": keeper_reason,
                "risk": risk,
            }
        )
        n_redundant += len(paths) - 1
        bytes_recoverable_total += bytes_recoverable

    # Sort: biggest savings first
    clusters.sort(key=lambda c: c["bytes_recoverable"], reverse=True)

    elapsed = time.perf_counter() - started_at
    print(
        f"[dedup] done in {elapsed:.1f}s: {len(clusters)} clusters, "
        f"{n_redundant} redundant files, {bytes_recoverable_total / 1024 / 1024:.1f} MB recoverable",
        file=sys.stderr,
        flush=True,
    )

    return {
        "schema": "home_dedup_report_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope_root": str(scope_root),
        "files_scanned": files_scanned,
        "files_hashed": files_hashed,
        "files_skipped_too_large": files_skipped_too_large,
        "files_skipped_too_small": files_skipped_too_small,
        "files_skipped_unreadable": files_skipped_unreadable,
        "directories_excluded": sorted(EXCLUDE_DIR_NAMES),
        "relative_paths_excluded": sorted(EXCLUDE_RELATIVE_PATHS),
        "min_size_bytes": min_size,
        "max_size_bytes": max_size,
        "duration_seconds": round(elapsed, 2),
        "duplicate_clusters": clusters,
        "totals": {
            "n_clusters": len(clusters),
            "n_redundant_files": n_redundant,
            "bytes_recoverable_total": bytes_recoverable_total,
        },
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--scope-root",
        type=Path,
        default=DEFAULT_SCOPE_ROOT,
        help=f"directory to scan (default: {DEFAULT_SCOPE_ROOT})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"directory to write the JSON report (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=DEFAULT_MIN_HASH_BYTES,
        help=f"skip files smaller than N bytes (default: {DEFAULT_MIN_HASH_BYTES})",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=DEFAULT_MAX_HASH_BYTES,
        help=f"skip files larger than N bytes (default: {DEFAULT_MAX_HASH_BYTES})",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="how many largest-savings clusters to print to stdout (default: 20)",
    )
    args = parser.parse_args(argv)

    report = scan(
        args.scope_root,
        min_size=args.min_size,
        max_size=args.max_size,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / f"dedup_report_{_utc_stamp()}.json"
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    rel = (
        out_path.relative_to(REPO_ROOT)
        if out_path.is_absolute() and str(out_path).startswith(str(REPO_ROOT))
        else out_path
    )

    print()
    print(f"Report: {rel}")
    print()
    print(
        f"Scanned {report['files_scanned']} files, hashed {report['files_hashed']}, "
        f"found {report['totals']['n_clusters']} duplicate clusters covering "
        f"{report['totals']['n_redundant_files']} redundant files."
    )
    print(
        "Bytes recoverable if all redundant copies were collapsed: "
        f"{report['totals']['bytes_recoverable_total'] / 1024 / 1024:.1f} MB"
    )
    print()
    print(f"Top {args.top} clusters by bytes recoverable:")
    print(f"{'#':>3}  {'risk':<6}  {'copies':>6}  {'each_KB':>9}  {'recover_MB':>11}  example_paths")
    for i, c in enumerate(report["duplicate_clusters"][: args.top], 1):
        each_kb = c["bytes_each"] / 1024
        recover_mb = c["bytes_recoverable"] / 1024 / 1024
        sample = c["paths"][0]
        if len(sample) > 70:
            sample = "..." + sample[-67:]
        print(f"{i:>3}  {c['risk']:<6}  {c['n_copies']:>6}  {each_kb:>9.1f}  {recover_mb:>11.2f}  {sample}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
