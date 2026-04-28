#!/usr/bin/env python3
"""Profile-driven launch wrapper for controlled blast radius startup."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class LaunchProfile:
    name: str
    description: str
    commands: tuple[list[str], ...]


PROFILES: dict[str, LaunchProfile] = {
    "dev-min": LaunchProfile(
        name="dev-min",
        description="Minimal safe startup: preflight + browser service.",
        commands=(
            [sys.executable, "scripts/system/repo_launch_preflight.py", "--profile", "dev-min"],
            ["node", "scripts/system/start_aetherbrowser_extension_service.mjs"],
        ),
    ),
    "browser": LaunchProfile(
        name="browser",
        description="Browser lane: start + verify extension service.",
        commands=(
            [sys.executable, "scripts/system/repo_launch_preflight.py", "--profile", "browser"],
            ["node", "scripts/system/start_aetherbrowser_extension_service.mjs"],
            [sys.executable, "scripts/verify_aetherbrowser_extension_service.py", "--run-backend-smoke"],
        ),
    ),
    "training": LaunchProfile(
        name="training",
        description="Training lane safety checks and local run review.",
        commands=(
            [sys.executable, "scripts/system/repo_launch_preflight.py", "--profile", "training"],
            [sys.executable, "scripts/system/review_training_runs.py"],
        ),
    ),
    "contracts": LaunchProfile(
        name="contracts",
        description="Contracts lane preflight and SAM ingest smoke.",
        commands=(
            [sys.executable, "scripts/system/repo_launch_preflight.py", "--profile", "contracts"],
            [sys.executable, "scripts/sam_gov_ingest.py", "--help"],
        ),
    ),
    "full-local": LaunchProfile(
        name="full-local",
        description="Preflight only for full local stack; manual start remains explicit.",
        commands=([sys.executable, "scripts/system/repo_launch_preflight.py", "--profile", "full-local"],),
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SCBE launch profiles.")
    parser.add_argument("--profile", choices=tuple(PROFILES.keys()), default="dev-min")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without execution.")
    return parser.parse_args()


def run_command(command: list[str]) -> int:
    print(f"[launch-profile] {shlex.join(command)}")
    completed = subprocess.run(command, cwd=REPO_ROOT)
    return completed.returncode


def main() -> int:
    args = parse_args()
    profile = PROFILES[args.profile]
    print(f"Profile: {profile.name} — {profile.description}")
    for command in profile.commands:
        if args.dry_run:
            print(f"[dry-run] {shlex.join(command)}")
            continue
        code = run_command(command)
        if code != 0:
            print(f"Profile {profile.name} failed with exit code {code}")
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

