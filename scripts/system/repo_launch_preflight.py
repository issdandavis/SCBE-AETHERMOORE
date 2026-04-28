#!/usr/bin/env python3
"""Phase 0/1 preflight checks for launch and build stabilization."""

from __future__ import annotations

import argparse
import socket
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.system.scbe_paths import FROZEN_ROOTS, REPO_ROOT

PROFILE_PORTS = {
    "dev-min": (8002, 9222),
    "browser": (8002, 9222),
    "training": tuple(),
    "contracts": tuple(),
    "full-local": (8002, 9222, 8400, 8401, 8088),
}

PROFILE_REQUIRED_PATHS = {
    "dev-min": ("scripts/system/start_aetherbrowser_extension_service.mjs",),
    "browser": (
        "scripts/system/start_aetherbrowser_extension_service.mjs",
        "scripts/verify_aetherbrowser_extension_service.py",
    ),
    "training": ("scripts/system/review_training_runs.py",),
    "contracts": ("scripts/sam_gov_ingest.py",),
    "full-local": (
        "scripts/system/start_aetherbrowser_extension_service.mjs",
        "scripts/system/start_aether_native_stack.ps1",
        "scripts/system/start_aether_phone_mode.ps1",
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run launch/build preflight checks.")
    parser.add_argument(
        "--profile",
        choices=tuple(PROFILE_PORTS.keys()),
        default="dev-min",
        help="Launch profile to preflight.",
    )
    parser.add_argument(
        "--strict-ports",
        action="store_true",
        help="Fail if expected profile ports are already in use.",
    )
    return parser.parse_args()


def check_frozen_roots() -> list[str]:
    errors: list[str] = []
    for root in FROZEN_ROOTS:
        if not (REPO_ROOT / root).exists():
            errors.append(f"missing frozen root: {root}")
    return errors


def check_profile_paths(profile: str) -> list[str]:
    errors: list[str] = []
    for rel_path in PROFILE_REQUIRED_PATHS[profile]:
        if not (REPO_ROOT / rel_path).exists():
            errors.append(f"missing profile path ({profile}): {rel_path}")
    return errors


def is_port_busy(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def check_ports(profile: str, strict: bool) -> list[str]:
    if not strict:
        return []
    errors: list[str] = []
    for port in PROFILE_PORTS[profile]:
        if is_port_busy(port):
            errors.append(f"profile {profile} expects free port but found busy: {port}")
    return errors


def main() -> int:
    args = parse_args()
    errors = []
    errors.extend(check_frozen_roots())
    errors.extend(check_profile_paths(args.profile))
    errors.extend(check_ports(args.profile, args.strict_ports))
    if errors:
        print("repo_launch_preflight FAILED")
        for err in errors:
            print(f"- {err}")
        return 1
    print(f"repo_launch_preflight OK for profile={args.profile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

