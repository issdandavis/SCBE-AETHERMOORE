#!/usr/bin/env python3
"""Strict guard for Python distribution artifacts.

Validates wheels and sdists built for public release so only the public
Python package surface ships:
  - spiralverse
  - code_prism
"""

from __future__ import annotations

import argparse
import json
import tarfile
import zipfile
from pathlib import Path
from typing import Iterable


BANNED_PREFIXES = (
    ".github/",
    "agents/",
    "api/",
    "app/",
    "apps/",
    "artifacts/",
    "content/",
    "demo/",
    "demos/",
    "docs/",
    "examples/",
    "external/",
    "notebooks/",
    "scripts/",
    "tests/",
    "training/",
    "training-data/",
)

BANNED_SUFFIXES = (".ipynb", ".pyc", ".pyo", ".zip")

WHEEL_ALLOWED_PREFIXES = (
    "spiralverse/",
    "code_prism/",
)

SDIST_ALLOWED_PREFIXES = (
    "src/spiralverse/",
    "src/code_prism/",
)

SDIST_ALLOWED_ROOT_FILES = {
    "README.md",
    "LICENSE",
    "MANIFEST.in",
    "pyproject.toml",
    "PKG-INFO",
    "setup.cfg",
}


def _normalize(member: str) -> str:
    value = member.replace("\\", "/").lstrip("./")
    while "//" in value:
        value = value.replace("//", "/")
    return value


def _strip_sdist_root(member: str) -> str:
    if "/" not in member:
        return member
    _, remainder = member.split("/", 1)
    return remainder or member


def iter_archive_members(archive_path: Path) -> list[str]:
    if archive_path.suffix == ".whl" or archive_path.suffix == ".zip":
        with zipfile.ZipFile(archive_path) as zf:
            return [_normalize(name) for name in zf.namelist() if not name.endswith("/")]

    if archive_path.suffixes[-2:] == [".tar", ".gz"] or archive_path.suffix == ".tgz":
        with tarfile.open(archive_path, "r:*") as tf:
            return [
                _normalize(member.name)
                for member in tf.getmembers()
                if member.isfile()
            ]

    raise ValueError(f"Unsupported distribution archive: {archive_path}")


def _has_required_metadata(archive_path: Path, members: Iterable[str]) -> bool:
    if archive_path.suffix == ".whl":
        return any(member.endswith(".dist-info/METADATA") for member in members)

    return any(member.endswith("PKG-INFO") for member in members)


def _unexpected_wheel_member(member: str) -> bool:
    if ".dist-info/" in member:
        return False
    return not any(member.startswith(prefix) for prefix in WHEEL_ALLOWED_PREFIXES)


def _unexpected_sdist_member(member: str) -> bool:
    normalized = _strip_sdist_root(member)
    if normalized in SDIST_ALLOWED_ROOT_FILES:
        return False
    if ".egg-info/" in normalized:
        return False
    return not any(normalized.startswith(prefix) for prefix in SDIST_ALLOWED_PREFIXES)


def evaluate_archive(archive_path: Path) -> dict[str, object]:
    members = iter_archive_members(archive_path)
    violations: list[dict[str, str]] = []
    is_wheel = archive_path.suffix == ".whl"

    for member in members:
        normalized = _normalize(member)
        if any(normalized.startswith(prefix) or f"/{prefix}" in normalized for prefix in BANNED_PREFIXES):
            violations.append({"file": member, "reason": "repo-only surface shipped in public dist"})
            continue
        if "__pycache__/" in normalized:
            violations.append({"file": member, "reason": "__pycache__ leaked into public dist"})
            continue
        if any(normalized.endswith(suffix) for suffix in BANNED_SUFFIXES):
            violations.append({"file": member, "reason": "banned artifact suffix in public dist"})
            continue
        if is_wheel and _unexpected_wheel_member(normalized):
            violations.append({"file": member, "reason": "unexpected file outside public wheel surface"})
            continue
        if not is_wheel and _unexpected_sdist_member(normalized):
            violations.append({"file": member, "reason": "unexpected file outside public sdist surface"})

    metadata_ok = _has_required_metadata(archive_path, members)
    return {
        "archive": archive_path.name,
        "entries": len(members),
        "metadata_ok": metadata_ok,
        "violations": violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate built Python wheel/sdist contents.")
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=Path("artifacts/python-dist"),
        help="Directory containing built wheel/sdist archives.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON summary.",
    )
    args = parser.parse_args()

    dist_dir = args.dist_dir
    archives = sorted(
        [
            path
            for path in dist_dir.iterdir()
            if path.is_file() and (path.suffix == ".whl" or path.suffix == ".zip" or path.suffix == ".tgz" or path.suffixes[-2:] == [".tar", ".gz"])
        ]
    ) if dist_dir.exists() else []

    if not archives:
        print(f"[python-dist-guard] No distribution archives found in {dist_dir}")
        return 1

    results = [evaluate_archive(path) for path in archives]
    failures = [
        result
        for result in results
        if not result["metadata_ok"] or result["violations"]
    ]

    if args.json:
        print(json.dumps({"dist_dir": str(dist_dir), "results": results, "failures": failures}, indent=2))
    else:
        print(f"[python-dist-guard] dist_dir={dist_dir} archives={len(results)}")
        for result in results:
            print(
                f"[python-dist-guard] {result['archive']} entries={result['entries']} "
                f"metadata_ok={result['metadata_ok']} violations={len(result['violations'])}"
            )
            for violation in result["violations"]:
                print(f" - {violation['file']} ({violation['reason']})")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
