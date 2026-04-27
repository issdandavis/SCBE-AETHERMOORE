#!/usr/bin/env python3
"""Validate PyPI release artifacts before upload.

This guard is intentionally local and offline. It checks the built wheel and
sdist for common release leaks that would make a public package look unsafe or
unprofessional: generated build trees, caches, secrets, repo artifacts, and
test-only payloads.
"""

from __future__ import annotations

import argparse
import re
import sys
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DistFile:
    path: Path
    members: list[str]


FAIL_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(^|/)\.git(/|$)"), ".git metadata"),
    (re.compile(r"(^|/)\.env(\.|$|/)"), "environment secret file"),
    (re.compile(r"(^|/)(?:config/connector_oauth|secrets?|\.aws|\.ssh)(/|$)", re.I), "secret/config directory"),
    (
        re.compile(r"(^|/)(?:artifacts|training-data|node_modules|external|external_repos)(/|$)", re.I),
        "repo artifact or dependency tree",
    ),
    (re.compile(r"(^|/)build/lib/(?:src|api|crypto|harmonic|symphonic_cipher)(/|$)", re.I), "generated build/lib tree"),
    (re.compile(r"(^|/)src/build(/|$)", re.I), "generated src/build tree"),
    (re.compile(r"(^|/)__pycache__(/|$)", re.I), "__pycache__ directory"),
    (re.compile(r"\.py[co]$", re.I), "Python bytecode"),
    (re.compile(r"(^|/)\.(?:pytest_cache|mypy_cache|ruff_cache|hypothesis)(/|$)", re.I), "tool cache"),
)

WARN_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(^|/)tests?(/|$)", re.I), "test package or test directory"),
    (re.compile(r"(^|/)(?:test_.+|.+_tests?)\.py$", re.I), "test-like module"),
    (re.compile(r"(^|/)src/(?![^/]+\.egg-info(?:/|$))", re.I), "raw src/ path inside artifact"),
)

REQUIRED_SUFFIXES = (".tar.gz", ".whl")


def normalize_member(name: str) -> str:
    return name.replace("\\", "/").lstrip("./")


def read_members(path: Path) -> list[str]:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as zf:
            return [normalize_member(name) for name in zf.namelist()]
    if path.name.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as tf:
            return [normalize_member(name) for name in tf.getnames()]
    raise ValueError(f"Unsupported distribution file: {path}")


def load_dists(dist_dir: Path) -> list[DistFile]:
    if not dist_dir.exists():
        raise FileNotFoundError(f"dist dir does not exist: {dist_dir}")
    files = sorted(path for path in dist_dir.iterdir() if path.is_file() and path.name.endswith(REQUIRED_SUFFIXES))
    if not files:
        raise FileNotFoundError(f"no .tar.gz or .whl files found in {dist_dir}")
    return [DistFile(path=path, members=read_members(path)) for path in files]


def check_required_artifacts(dists: list[DistFile]) -> list[str]:
    names = [dist.path.name for dist in dists]
    errors: list[str] = []
    if not any(name.endswith(".whl") for name in names):
        errors.append("missing wheel artifact (.whl)")
    if not any(name.endswith(".tar.gz") for name in names):
        errors.append("missing source distribution artifact (.tar.gz)")
    return errors


def scan_patterns(dist: DistFile, patterns: tuple[tuple[re.Pattern[str], str], ...]) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    for member in dist.members:
        for pattern, reason in patterns:
            if pattern.search(member):
                hits.append((member, reason))
                break
    return hits


def wheel_has_metadata(dist: DistFile) -> bool:
    if dist.path.suffix != ".whl":
        return True
    return any(name.endswith(".dist-info/METADATA") for name in dist.members) and any(
        name.endswith(".dist-info/WHEEL") for name in dist.members
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate PyPI dist artifacts before upload.")
    parser.add_argument(
        "--dist-dir", default="artifacts/pypi-dist", help="Directory containing .whl and .tar.gz files."
    )
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="Treat warnings, such as test-like modules in artifacts, as failures.",
    )
    args = parser.parse_args(argv)

    try:
        dists = load_dists(Path(args.dist_dir))
    except (FileNotFoundError, ValueError, tarfile.TarError, zipfile.BadZipFile) as exc:
        print(f"[pypi-dist-guard] ERROR: {exc}", file=sys.stderr)
        return 1

    errors = check_required_artifacts(dists)
    warnings: list[str] = []

    for dist in dists:
        print(f"[pypi-dist-guard] inspecting {dist.path.name}: {len(dist.members)} entries")
        if not wheel_has_metadata(dist):
            errors.append(f"{dist.path.name}: missing wheel METADATA or WHEEL file")

        for member, reason in scan_patterns(dist, FAIL_PATTERNS):
            errors.append(f"{dist.path.name}: {member} ({reason})")

        for member, reason in scan_patterns(dist, WARN_PATTERNS):
            warnings.append(f"{dist.path.name}: {member} ({reason})")

    if warnings:
        print("[pypi-dist-guard] warnings:")
        for warning in warnings[:40]:
            print(f" - {warning}")
        if len(warnings) > 40:
            print(f" - ... {len(warnings) - 40} more warning(s)")

    if errors:
        print("[pypi-dist-guard] release blockers:", file=sys.stderr)
        for error in errors[:80]:
            print(f" - {error}", file=sys.stderr)
        if len(errors) > 80:
            print(f" - ... {len(errors) - 80} more error(s)", file=sys.stderr)
        return 1

    if args.strict_warnings and warnings:
        print("[pypi-dist-guard] strict warning mode failed", file=sys.stderr)
        return 1

    print("[pypi-dist-guard] dist artifacts are upload-safe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
