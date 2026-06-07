#!/usr/bin/env python3
"""Check Python source syntax against the repository's minimum Python floor.

This catches the portability hole where a newer local interpreter accepts syntax
that the repo floor rejects. It does not replace running tests under the floor
interpreter, but it catches hard import-time syntax failures such as grammar
features added after Python 3.11.
"""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from pathlib import Path

DEFAULT_ROOTS = ("python", "scripts", "src", "tests")
EXCLUDED_PARTS = {
    ".git",
    ".hypothesis",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".venv312-taichi",
    "__pycache__",
    "artifacts",
    "dist",
    "external_repos",
    "node_modules",
    "training-data",
    "training",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        default=list(DEFAULT_ROOTS),
        help="files or directories to scan; defaults to core Python roots",
    )
    parser.add_argument(
        "--floor",
        default="3.11",
        help="minimum Python grammar version, default: 3.11",
    )
    parser.add_argument(
        "--tracked-only",
        action="store_true",
        help="scan only git-tracked files under the requested paths",
    )
    args = parser.parse_args(argv)

    try:
        feature_version = _feature_version(args.floor)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    files = _python_files(
        [Path(path) for path in args.paths], tracked_only=args.tracked_only
    )
    failures: list[tuple[Path, SyntaxError]] = []
    for path in files:
        try:
            text = _read_text(path)
            ast.parse(text, filename=str(path), feature_version=feature_version)
        except SyntaxError as exc:
            failures.append((path, exc))

    if failures:
        for path, exc in failures:
            text = (exc.text or "").strip()
            print(
                f"{path}:{exc.lineno}:{exc.offset}: {exc.msg}: {text}", file=sys.stderr
            )
        print(
            f"Python {args.floor} grammar floor failed: {len(failures)} file(s)",
            file=sys.stderr,
        )
        return 1

    print(f"Python {args.floor} grammar floor ok: {len(files)} file(s)")
    return 0


def _feature_version(raw: str) -> tuple[int, int]:
    parts = raw.split(".")
    if len(parts) != 2:
        raise ValueError("--floor must look like MAJOR.MINOR, e.g. 3.11")
    major, minor = (int(part) for part in parts)
    if major != 3 or minor < 7:
        raise ValueError("ast feature_version only supports Python 3.7+ grammar floors")
    return major, minor


def _python_files(paths: list[Path], *, tracked_only: bool) -> list[Path]:
    if tracked_only:
        return _tracked_python_files(paths)

    files: list[Path] = []
    for path in paths:
        if not path.exists():
            continue
        if path.is_file():
            if path.suffix == ".py" and not _excluded(path):
                files.append(path)
            continue
        for child in path.rglob("*.py"):
            if not _excluded(child):
                files.append(child)
    return sorted(set(files))


def _tracked_python_files(paths: list[Path]) -> list[Path]:
    command = ["git", "ls-files", "--", *[str(path) for path in paths]]
    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.stderr.strip() or "git ls-files failed")
    files = [
        Path(line)
        for line in completed.stdout.splitlines()
        if line.endswith(".py") and not _excluded(Path(line))
    ]
    return sorted(set(files))


def _excluded(path: Path) -> bool:
    return any(part in EXCLUDED_PARTS for part in path.parts)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")


if __name__ == "__main__":
    raise SystemExit(main())
