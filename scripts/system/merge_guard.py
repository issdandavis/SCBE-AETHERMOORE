#!/usr/bin/env python3
"""
merge_guard — will this branch merge into origin/main cleanly?  Run before pushing.

Keeps pushes clean and conflict-free *moving forward*: it fetches origin, reports
divergence, PREVIEWS the merge (without touching the tree) to surface conflicts
BEFORE they hit GitHub, scans tracked files for leftover conflict markers, and
flags submodule-vs-real deletions so benign noise isn't mistaken for data loss.

Exit 0 = ready to push (merges clean). Non-zero = fix the listed items first.

    python scripts/system/merge_guard.py [--base origin/main]
"""

from __future__ import annotations

import argparse
import subprocess
import sys

# Only the angle-bracket markers are reliable: a real conflict has a line that
# STARTS with <<<<<<< or >>>>>>>. (======= alone is a common markdown/code rule.)
MARKERS = ("<<<<<<<", ">>>>>>>")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--no-fetch", action="store_true")
    args = ap.parse_args()

    problems: list[str] = []
    notes: list[str] = []

    if not args.no_fetch:
        subprocess.run(["git", "fetch", "origin"], capture_output=True)

    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    ahead = _git("rev-list", "--count", f"{args.base}..HEAD")
    behind = _git("rev-list", "--count", f"HEAD..{args.base}")
    print(f"branch: {branch}   ahead of {args.base}: {ahead}   behind: {behind}")

    # 1) merge conflict preview (no working-tree change)
    base = _git("merge-base", "HEAD", args.base)
    preview = subprocess.run(["git", "merge-tree", "--write-tree", "HEAD", args.base], capture_output=True, text=True)
    conflicts = [ln for ln in preview.stdout.splitlines() if "CONFLICT" in ln]
    if conflicts:
        problems.append(f"{len(conflicts)} merge conflict(s) vs {args.base}:")
        for c in conflicts[:12]:
            problems.append(f"    {c.strip()}")
    else:
        notes.append(f"no merge conflicts vs {args.base}")

    # 2) leftover conflict markers in tracked files
    tracked = _git("ls-files").splitlines()
    marked = []
    for f in tracked:
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                txt = fh.read()
        except (OSError, IsADirectoryError):
            continue
        if f == "scripts/system/merge_guard.py":
            continue
        if any(ln.startswith(MARKERS) for ln in txt.splitlines()):
            marked.append(f)
    if marked:
        problems.append(f"{len(marked)} file(s) with leftover conflict markers: {marked[:8]}")
    else:
        notes.append("no leftover conflict markers")

    # 3) distinguish benign submodule 'deletions' from real ones
    status = _git("status", "--porcelain")
    del_paths = [ln[3:] for ln in status.splitlines() if ln.startswith(" D")]
    submods = set(_git("config", "--file", ".gitmodules", "--get-regexp", "path").split()[1::2]) if del_paths else set()
    real_dels = [p for p in del_paths if p not in submods]
    benign = [p for p in del_paths if p in submods]
    if benign:
        notes.append(
            f"{len(benign)} deleted path(s) are uninitialized submodules (benign — "
            f"run `git submodule update --init` to populate)"
        )
    if real_dels:
        problems.append(f"{len(real_dels)} REAL file deletion(s) staged/working: {real_dels[:8]}")

    print("\nchecks:")
    for n in notes:
        print(f"  OK   {n}")
    for p in problems:
        print(f"  !!   {p}")

    ready = not conflicts and not marked and not real_dels
    print(f"\n{'READY TO PUSH (merges clean)' if ready else 'NOT READY — resolve the !! items above'}")
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
