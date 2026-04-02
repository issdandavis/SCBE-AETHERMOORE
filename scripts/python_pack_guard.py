#!/usr/bin/env python3
"""Guard built Python artifacts against overshipping internal repo surfaces."""

from __future__ import annotations

import argparse
import tarfile
import zipfile
from pathlib import Path
import re
import sys


BANNED_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(^|/)docs/"), "docs should not ship in Python artifacts"),
    (re.compile(r"(^|/)notebooks/"), "notebooks should not ship in Python artifacts"),
    (re.compile(r"(^|/)training-data/"), "training data should not ship in Python artifacts"),
    (re.compile(r"(^|/)training/"), "training code should not ship in Python artifacts"),
    (re.compile(r"(^|/)artifacts/"), "artifacts should not ship in Python artifacts"),
    (re.compile(r"(^|/)\.github/"), "GitHub workflows should not ship in Python artifacts"),
    (re.compile(r"(^|/)app/"), "app surfaces should not ship in Python artifacts"),
    (re.compile(r"(^|/)apps/"), "app surfaces should not ship in Python artifacts"),
    (re.compile(r"(^|/)conference-app/"), "app surfaces should not ship in Python artifacts"),
    (re.compile(r"(^|/)desktop/"), "app surfaces should not ship in Python artifacts"),
    (re.compile(r"(^|/)kindle-app/"), "app surfaces should not ship in Python artifacts"),
    (re.compile(r"(^|/)prototype/"), "prototype surfaces should not ship in Python artifacts"),
    (re.compile(r"(^|/)spaces/"), "space surfaces should not ship in Python artifacts"),
    (re.compile(r"(^|/)tests?/"), "tests should not ship in Python artifacts"),
    (re.compile(r"(^|/)examples/"), "examples should not ship in Python artifacts"),
    (re.compile(r"(^|/)package-lock\.json$"), "Node lockfile should not ship in Python artifacts"),
    (re.compile(r"(^|/)src/package\.json$"), "duplicate src package manifest should not ship"),
    (re.compile(r"(^|/)src/pyproject\.toml$"), "duplicate src pyproject should not ship"),
    (re.compile(r"\.ipynb$", re.IGNORECASE), "notebooks should not ship in Python artifacts"),
)

REQUIRED_MATCHERS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(^|/)README\.md$"), "README.md"),
    (re.compile(r"(^|/)LICENSE$"), "LICENSE"),
    (re.compile(r"(^|/)spiralverse/__init__\.py$"), "spiralverse/__init__.py"),
    (re.compile(r"(^|/)spiralverse/cli\.py$"), "spiralverse/cli.py"),
)


def normalize_candidates(name: str) -> set[str]:
    normalized = name.replace("\\", "/").lstrip("./")
    if not normalized:
        return set()
    candidates = {normalized}
    if "/" in normalized:
        _, remainder = normalized.split("/", 1)
        if remainder:
            candidates.add(remainder)
    return candidates


def scan_member_names(names: list[str]) -> tuple[list[tuple[str, str]], list[str]]:
    violations: list[tuple[str, str]] = []
    seen_requirements = {label: False for _, label in REQUIRED_MATCHERS}

    for original_name in names:
        candidates = normalize_candidates(original_name)
        blocked = False
        for candidate in candidates:
            for pattern, reason in BANNED_PATTERNS:
                if pattern.search(candidate):
                    violations.append((original_name, reason))
                    blocked = True
                    break
            if blocked:
                break
            for pattern, label in REQUIRED_MATCHERS:
                if pattern.search(candidate):
                    seen_requirements[label] = True

    missing = [label for label, present in seen_requirements.items() if not present]
    return violations, missing


def iter_artifact_names(artifact: Path) -> list[str]:
    if artifact.suffix == ".whl" or artifact.suffix == ".zip":
        with zipfile.ZipFile(artifact) as zf:
            return [info.filename for info in zf.infolist() if not info.is_dir()]

    if artifact.name.endswith(".tar.gz") or artifact.suffix == ".gz":
        with tarfile.open(artifact, "r:gz") as tf:
            return [member.name for member in tf.getmembers() if member.isfile()]

    raise ValueError(f"Unsupported artifact type: {artifact}")


def guard_artifact(artifact: Path) -> tuple[list[tuple[str, str]], list[str]]:
    names = iter_artifact_names(artifact)
    return scan_member_names(names)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dist-dir",
        default="dist",
        help="Directory containing built wheel/sdist artifacts.",
    )
    args = parser.parse_args(argv)

    dist_dir = Path(args.dist_dir)
    artifacts = sorted(list(dist_dir.glob("*.whl")) + list(dist_dir.glob("*.tar.gz")))
    if not artifacts:
        print(f"[python-pack-guard] no artifacts found in {dist_dir}")
        return 1

    failed = False
    for artifact in artifacts:
        violations, missing = guard_artifact(artifact)
        print(f"[python-pack-guard] artifact={artifact.name} entries_checked")
        if missing:
            failed = True
            print("[python-pack-guard] missing required files:")
            for item in missing:
                print(f" - {item}")
        if violations:
            failed = True
            print("[python-pack-guard] disallowed files detected:")
            for member, reason in violations:
                print(f" - {member} ({reason})")
        if not missing and not violations:
            print("[python-pack-guard] artifact contents are clean")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
