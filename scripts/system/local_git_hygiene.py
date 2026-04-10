#!/usr/bin/env python3
"""Local-only git hygiene lane for intentionally noisy repo paths.

This script does not modify tracked repo policy. It manages:
- `.git/info/exclude` for untracked local noise
- `git update-index --skip-worktree` for tracked files the user wants quiet locally

Use this when a branch is usable but status output is polluted by paths that are
intentionally local for one operator workflow.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Iterable

SCBE_START = "# >>> SCBE_LOCAL_HYGIENE"
SCBE_END = "# <<< SCBE_LOCAL_HYGIENE"

DEFAULT_TRACKED_CANDIDATES = (
    "api/darpa_prep",
    "docs-build-smoke",
    "docs/operations/DARPA_SAM_GOV_CONTACTS_AND_PROPOSAL_STATUS.md",
    "docs/proposals/DARPA_CLARA",
    "notes/.obsidian/app.json",
    "artifacts/hydra/ledger.db",
    "artifacts/research/full_codebase_map.json",
    "training/ingest/latest_local_cloud_sync.txt",
    "training/ingest/local_cloud_sync_state.json",
)

DEFAULT_UNTRACKED_EXCLUDES = (
    "api/darpa_prep/",
    "docs-build-smoke/",
    "docs/operations/",
    "docs/proposals/DARPA_CLARA/",
    "notes/Note drops/",
    "notes/Note drops.md",
    "notes/agent-memory/",
    "notes/experiments/",
)


def run_git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )


def unique_preserve(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = value.strip().replace("\\", "/")
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def expand_tracked_paths(repo_root: Path, candidates: Iterable[str]) -> list[str]:
    tracked: list[str] = []
    for candidate in unique_preserve(candidates):
        result = run_git(repo_root, "ls-files", "--", candidate)
        if result.returncode != 0:
            continue
        tracked.extend(line.strip() for line in result.stdout.splitlines() if line.strip())
    return unique_preserve(tracked)


def get_skip_worktree_paths(repo_root: Path) -> list[str]:
    result = run_git(repo_root, "ls-files", "-v")
    if result.returncode != 0:
        return []
    flagged: list[str] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        prefix = line[0]
        path = line[2:].strip()
        if prefix == "S" and path:
            flagged.append(path.replace("\\", "/"))
    return unique_preserve(flagged)


def parse_status(repo_root: Path) -> list[dict[str, str]]:
    result = run_git(repo_root, "status", "--short")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git status failed")
    rows: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        status = line[:2]
        path = line[3:].strip().replace("\\", "/")
        if len(path) >= 2 and path[0] == '"' and path[-1] == '"':
            path = path[1:-1]
        rows.append(
            {
                "status": status,
                "path": path,
                "tracked": "?" not in status,
            }
        )
    return rows


def merge_exclude_block(existing: str, patterns: Iterable[str]) -> str:
    lines = existing.splitlines()
    output: list[str] = []
    in_block = False
    for line in lines:
        stripped = line.strip()
        if stripped == SCBE_START:
            in_block = True
            continue
        if stripped == SCBE_END:
            in_block = False
            continue
        if not in_block:
            output.append(line)

    while output and output[-1] == "":
        output.pop()

    payload = [SCBE_START, *unique_preserve(patterns), SCBE_END]
    if output:
        output.append("")
    output.extend(payload)
    return "\n".join(output) + "\n"


def remove_exclude_block(existing: str) -> str:
    lines = existing.splitlines()
    output: list[str] = []
    in_block = False
    for line in lines:
        stripped = line.strip()
        if stripped == SCBE_START:
            in_block = True
            continue
        if stripped == SCBE_END:
            in_block = False
            continue
        if not in_block:
            output.append(line)

    while output and output[-1] == "":
        output.pop()
    if not output:
        return ""
    return "\n".join(output) + "\n"


def write_exclude(repo_root: Path, patterns: Iterable[str]) -> dict[str, object]:
    exclude_path = repo_root / ".git" / "info" / "exclude"
    exclude_path.parent.mkdir(parents=True, exist_ok=True)
    previous = exclude_path.read_text(encoding="utf-8") if exclude_path.exists() else ""
    updated = merge_exclude_block(previous, patterns)
    exclude_path.write_text(updated, encoding="utf-8")
    return {
        "path": str(exclude_path),
        "patterns": unique_preserve(patterns),
    }


def clear_exclude(repo_root: Path) -> str:
    exclude_path = repo_root / ".git" / "info" / "exclude"
    previous = exclude_path.read_text(encoding="utf-8") if exclude_path.exists() else ""
    updated = remove_exclude_block(previous)
    exclude_path.write_text(updated, encoding="utf-8")
    return str(exclude_path)


def set_skip_worktree(repo_root: Path, paths: Iterable[str], enable: bool) -> list[str]:
    resolved = expand_tracked_paths(repo_root, paths)
    if not resolved:
        return []
    flag = "--skip-worktree" if enable else "--no-skip-worktree"
    batch_size = 128
    for index in range(0, len(resolved), batch_size):
        batch = resolved[index : index + batch_size]
        result = run_git(repo_root, "update-index", flag, *batch)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"git update-index {flag} failed")
    return resolved


def build_status_summary(
    repo_root: Path,
    tracked_candidates: Iterable[str],
    untracked_excludes: Iterable[str],
) -> dict[str, object]:
    tracked_defaults = set(expand_tracked_paths(repo_root, tracked_candidates))
    untracked_defaults = unique_preserve(untracked_excludes)
    skip_worktree = set(get_skip_worktree_paths(repo_root))
    rows = parse_status(repo_root)

    tracked_matches: list[str] = []
    tracked_other: list[str] = []
    untracked_matches: list[str] = []
    untracked_other: list[str] = []

    for row in rows:
        path = row["path"]
        if row["tracked"]:
            if path in tracked_defaults:
                tracked_matches.append(path)
            else:
                tracked_other.append(path)
            continue

        if any(path == pattern.rstrip("/") or path.startswith(pattern.rstrip("/") + "/") for pattern in untracked_defaults):
            untracked_matches.append(path)
        else:
            untracked_other.append(path)

    return {
        "repo_root": str(repo_root),
        "tracked_default_candidates": unique_preserve(tracked_candidates),
        "tracked_default_resolved_count": len(tracked_defaults),
        "tracked_defaults_sample": sorted(tracked_defaults)[:20],
        "untracked_excludes": untracked_defaults,
        "skip_worktree_paths": sorted(skip_worktree),
        "tracked_dirty_matches": sorted(unique_preserve(tracked_matches)),
        "tracked_dirty_other": sorted(unique_preserve(tracked_other)),
        "untracked_matches": sorted(unique_preserve(untracked_matches)),
        "untracked_other": sorted(unique_preserve(untracked_other)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage local-only git hygiene for SCBE.")
    parser.add_argument("--repo-root", default="", help="Repository root. Defaults to current working tree.")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("status", "apply", "clear"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--tracked", action="append", default=[], help="Extra tracked path or directory to quiet locally.")
        cmd.add_argument("--exclude", action="append", default=[], help="Extra untracked path pattern for .git/info/exclude.")
        cmd.add_argument("--json", action="store_true", help="Emit JSON.")
    return parser.parse_args()


def resolve_repo_root(raw: str) -> Path:
    if raw:
        return Path(raw).expanduser().resolve()
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "unable to resolve repo root")
    return Path(result.stdout.strip()).resolve()


def main() -> int:
    args = parse_args()
    repo_root = resolve_repo_root(args.repo_root)
    tracked = unique_preserve([*DEFAULT_TRACKED_CANDIDATES, *args.tracked])
    excludes = unique_preserve([*DEFAULT_UNTRACKED_EXCLUDES, *args.exclude])

    if args.command == "status":
        summary = build_status_summary(repo_root, tracked, excludes)
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(f"[git-hygiene] repo={summary['repo_root']}")
            print(f"[git-hygiene] tracked_dirty_matches={len(summary['tracked_dirty_matches'])}")
            print(f"[git-hygiene] untracked_matches={len(summary['untracked_matches'])}")
            print(f"[git-hygiene] skip_worktree_paths={len(summary['skip_worktree_paths'])}")
        return 0

    if args.command == "apply":
        exclude_info = write_exclude(repo_root, excludes)
        applied = set_skip_worktree(repo_root, tracked, enable=True)
        summary = build_status_summary(repo_root, tracked, excludes)
        summary["exclude_write"] = exclude_info
        summary["applied_skip_worktree"] = applied
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(f"[git-hygiene] applied_skip_worktree={len(applied)}")
            print(f"[git-hygiene] exclude_patterns={len(exclude_info['patterns'])}")
        return 0

    cleared = set_skip_worktree(repo_root, tracked, enable=False)
    exclude_path = clear_exclude(repo_root)
    summary = build_status_summary(repo_root, tracked, excludes)
    summary["cleared_skip_worktree"] = cleared
    summary["exclude_path"] = exclude_path
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"[git-hygiene] cleared_skip_worktree={len(cleared)}")
        print(f"[git-hygiene] exclude_path={exclude_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
