"""Build the root Python dependency snapshot submitted to GitHub.

GitHub's automatic Python graph can retain an older resolver snapshot after a
manifest disappears.  This builder turns the repository's exact
``requirements-lock.txt`` into a deterministic Dependency Submission API
payload so the graph follows the lock file on every relevant ``main`` push.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

PACKAGE_NAME = r"[A-Za-z0-9][A-Za-z0-9._-]*"
EXACT_REQUIREMENT = re.compile(rf"^(?P<name>{PACKAGE_NAME})==(?P<version>[^\s;]+)(?:\s*;.*)?$")
DECLARED_REQUIREMENT = re.compile(rf"^\s*(?P<name>{PACKAGE_NAME})")


def normalize_package_name(name: str) -> str:
    """Return the normalized PyPI project name used in package URLs."""

    return re.sub(r"[-_.]+", "-", name).lower()


def load_direct_dependencies(pyproject_path: Path) -> set[str]:
    """Read direct runtime dependency names from ``pyproject.toml``."""

    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    requirements = data.get("project", {}).get("dependencies", [])
    direct: set[str] = set()

    for requirement in requirements:
        match = DECLARED_REQUIREMENT.match(requirement)
        if match is None:
            raise ValueError(f"Unsupported project dependency: {requirement!r}")
        direct.add(normalize_package_name(match.group("name")))

    return direct


def load_locked_dependencies(lock_path: Path) -> tuple[dict[str, str], list[str]]:
    """Read exact registry requirements and identify intentionally skipped VCS entries."""

    locked: dict[str, str] = {}
    skipped_vcs: list[str] = []

    for line_number, raw_line in enumerate(lock_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("-e ") or " @ git+" in line:
            skipped_vcs.append(line)
            continue

        match = EXACT_REQUIREMENT.fullmatch(line)
        if match is None:
            raise ValueError(f"Unsupported lock entry at {lock_path}:{line_number}: {line!r}")

        name = normalize_package_name(match.group("name"))
        version = match.group("version")
        previous = locked.get(name)
        if previous is not None and previous != version:
            raise ValueError(f"Conflicting versions for {name}: {previous!r} and {version!r}")
        locked[name] = version

    if not locked:
        raise ValueError(f"No exact dependencies found in {lock_path}")

    return locked, skipped_vcs


def package_url(name: str, version: str) -> str:
    """Build a standards-compatible PyPI package URL."""

    encoded_name = quote(name, safe="-._~")
    encoded_version = quote(version, safe="-._~")
    return f"pkg:pypi/{encoded_name}@{encoded_version}"


def build_snapshot(
    repo_root: Path,
    *,
    sha: str,
    ref: str,
    job_id: str,
    scanned: str,
) -> tuple[dict[str, Any], list[str]]:
    """Build a Dependency Submission API snapshot for the root Python manifest."""

    if re.fullmatch(r"[0-9a-fA-F]{40}", sha) is None:
        raise ValueError("sha must be a full 40-character Git commit hash")
    if not ref.startswith("refs/"):
        raise ValueError("ref must start with 'refs/'")

    direct = load_direct_dependencies(repo_root / "pyproject.toml")
    locked, skipped_vcs = load_locked_dependencies(repo_root / "requirements-lock.txt")
    resolved: dict[str, object] = {}

    for name, version in sorted(locked.items()):
        resolved[name] = {
            "package_url": package_url(name, version),
            "relationship": "direct" if name in direct else "indirect",
            "scope": "runtime",
            "dependencies": [],
        }

    snapshot: dict[str, Any] = {
        "version": 0,
        "sha": sha.lower(),
        "ref": ref,
        "job": {
            "correlator": "00-root-python-requirements-lock",
            "id": job_id,
        },
        "detector": {
            "name": "scbe-root-python-lock",
            "version": "1.0.0",
            "url": (
                "https://github.com/issdandavis/SCBE-AETHERMOORE/" "blob/main/scripts/build_dependency_snapshot.py"
            ),
        },
        "scanned": scanned,
        "manifests": {
            "pyproject.toml": {
                "name": "pyproject.toml",
                "file": {"source_location": "pyproject.toml"},
                "metadata": {
                    "lock_file": "requirements-lock.txt",
                    "skipped_vcs_entries": len(skipped_vcs),
                },
                "resolved": resolved,
            }
        },
    }
    return snapshot, skipped_vcs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--sha", default=os.environ.get("GITHUB_SHA"))
    parser.add_argument("--ref", default=os.environ.get("GITHUB_REF"))
    parser.add_argument("--job-id", default=os.environ.get("GITHUB_RUN_ID"))
    parser.add_argument(
        "--scanned",
        default=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    )
    parser.add_argument("--output", type=Path, help="Write JSON here; omit to write to stdout")
    args = parser.parse_args()

    for field in ("sha", "ref", "job_id"):
        if not getattr(args, field):
            parser.error(f"--{field.replace('_', '-')} or its GitHub Actions environment variable is required")
    return args


def main() -> int:
    args = parse_args()
    snapshot, skipped_vcs = build_snapshot(
        args.repo_root,
        sha=args.sha,
        ref=args.ref,
        job_id=args.job_id,
        scanned=args.scanned,
    )
    rendered = json.dumps(snapshot, indent=2, sort_keys=True) + "\n"

    if args.output is None:
        sys.stdout.write(rendered)
    else:
        args.output.write_text(rendered, encoding="utf-8")

    resolved = snapshot["manifests"]["pyproject.toml"]["resolved"]
    print(
        f"Built snapshot with {len(resolved)} exact dependencies; skipped {len(skipped_vcs)} VCS entries",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
