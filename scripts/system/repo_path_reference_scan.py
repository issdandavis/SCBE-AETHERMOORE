#!/usr/bin/env python3
"""Scan repo for hardcoded path references targeted for restructure."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.system.scbe_paths import (
    ABSOLUTE_WINDOWS_PREFIX,
    REPO_ROOT,
    SCANNED_ROOT_REFERENCES,
    SKIP_DIRS,
    TEXT_EXTENSIONS,
)


@dataclass(frozen=True)
class Hit:
    path: str
    line: int
    token: str
    text: str


def should_scan(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    if path.is_dir():
        return False
    return path.suffix.lower() in TEXT_EXTENSIONS


def iter_scan_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    files: list[Path] = []
    for line in result.stdout.splitlines():
        candidate = REPO_ROOT / line.strip()
        if candidate.exists() and should_scan(candidate):
            files.append(candidate)
    return files


def scan_file(path: Path, tokens: tuple[str, ...], absolute_regex: re.Pattern[str]) -> list[Hit]:
    hits: list[Hit] = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return hits
    for lineno, line in enumerate(content.splitlines(), start=1):
        for token in tokens:
            if token in line:
                hits.append(Hit(str(path.relative_to(REPO_ROOT)), lineno, token, line.strip()))
        if absolute_regex.search(line):
            hits.append(Hit(str(path.relative_to(REPO_ROOT)), lineno, "ABSOLUTE_C_USERS_PATH", line.strip()))
    return hits


def build_report(hits: list[Hit]) -> dict[str, object]:
    grouped: dict[str, int] = {}
    for hit in hits:
        grouped[hit.token] = grouped.get(hit.token, 0) + 1
    return {
        "repo_root": str(REPO_ROOT),
        "scan_tokens": list(SCANNED_ROOT_REFERENCES) + ["ABSOLUTE_C_USERS_PATH"],
        "total_hits": len(hits),
        "counts_by_token": grouped,
        "hits": [hit.__dict__ for hit in hits],
    }


def write_report(report: dict[str, object], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan for hardcoded path references before repo moves.")
    parser.add_argument(
        "--output",
        default="artifacts/system-audit/repo_path_reference_scan.json",
        help="Path to JSON report (default: artifacts/system-audit/repo_path_reference_scan.json).",
    )
    parser.add_argument("--fail-on-hit", action="store_true", help="Return non-zero if any references are found.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tokens = tuple(SCANNED_ROOT_REFERENCES)
    absolute_regex = re.compile(r"C:\\Users\\issda\\", re.IGNORECASE)
    hits: list[Hit] = []
    for file_path in iter_scan_files():
        hits.extend(scan_file(file_path, tokens, absolute_regex))
    report = build_report(hits)
    write_report(report, REPO_ROOT / args.output)
    print(f"repo_path_reference_scan: {report['total_hits']} hit(s)")
    print(f"report: {args.output}")
    if args.fail_on_hit and hits:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

