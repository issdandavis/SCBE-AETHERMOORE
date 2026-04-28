#!/usr/bin/env python3
"""Validate internal markdown links and paths."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.system.scbe_paths import REPO_ROOT, SKIP_DIRS

LINK_PATTERN = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def iter_markdown_files() -> list[Path]:
    files: list[Path] = []
    result = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    for line in result.stdout.splitlines():
        path = REPO_ROOT / line.strip()
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.exists():
            files.append(path)
    return files


def filter_files(files: list[Path], roots: tuple[str, ...]) -> list[Path]:
    if not roots:
        return files
    normalized_roots = tuple(root.strip().replace("\\", "/") for root in roots if root.strip())
    if not normalized_roots:
        return files
    filtered: list[Path] = []
    for path in files:
        rel = path.relative_to(REPO_ROOT).as_posix()
        if any(rel == root or rel.startswith(f"{root}/") for root in normalized_roots):
            filtered.append(path)
    return filtered


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return errors
    for _, href in LINK_PATTERN.findall(content):
        if href.startswith(("http://", "https://", "#", "mailto:")):
            continue
        target_rel = href.split("#", maxsplit=1)[0].strip()
        if not target_rel:
            continue
        target = (path.parent / target_rel).resolve()
        if not target.exists():
            rel_file = path.relative_to(REPO_ROOT)
            errors.append(f"{rel_file}: {href}")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check markdown internal links.")
    parser.add_argument("--fail-fast", action="store_true", help="Exit after first broken link.")
    parser.add_argument(
        "--roots",
        default="docs",
        help="Comma-separated repo-relative roots to check (default: docs). Use '*' for all markdown files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    roots = tuple() if args.roots.strip() == "*" else tuple(part.strip() for part in args.roots.split(","))
    all_errors: list[str] = []
    for md_file in filter_files(iter_markdown_files(), roots):
        errs = validate_file(md_file)
        if errs:
            all_errors.extend(errs)
            if args.fail_fast:
                break
    if all_errors:
        print(f"Broken internal links: {len(all_errors)}")
        for err in all_errors[:200]:
            print(err)
        return 1
    print("Markdown link check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

