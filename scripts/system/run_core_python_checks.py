from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "system-audit"

# Optional or experimental lanes that currently pull in extra services,
# unpublished modules, or heavyweight third-party stacks. Keep them out of the
# default merge path and triage them in dedicated workflows instead.
OPTIONAL_TEST_IGNORES: tuple[str, ...] = (
    "tests/api/test_billing_public_checkout.py",
    "tests/industry_standard/test_byzantine_consensus.py",
    "tests/test_aethermoore_patents.py",
    "tests/test_api_key_hashing.py",
    "tests/test_hallpass.py",
    "tests/test_mcp_servers.py",
    "tests/test_mobile_goal_api.py",
    "tests/test_orchestrator.py",
    "tests/test_paper_aggregator.py",
    "tests/test_sacred_tongue_integration.py",
    "tests/test_spectral_langgraph.py",
    "tests/test_system_script_security.py",
)


def build_pytest_command(maxfail: int | None = None, extra_args: list[str] | None = None) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "tests",
        "-v",
        "--ignore=tests/node_modules",
    ]
    if maxfail is not None:
        command.append(f"--maxfail={maxfail}")
    command.extend(f"--ignore={path}" for path in OPTIONAL_TEST_IGNORES)
    if extra_args:
        command.extend(extra_args)
    return command


def build_environment() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    env.setdefault("SCBE_FORCE_SKIP_LIBOQS", "1")
    return env


def summary_payload(command: list[str]) -> dict[str, object]:
    return {
        "repo_root": str(REPO_ROOT),
        "command": command,
        "optional_ignores": list(OPTIONAL_TEST_IGNORES),
        "env": {
            "PYTHONPATH": str(REPO_ROOT),
            "SCBE_FORCE_SKIP_LIBOQS": "1",
        },
    }


def write_summary(payload: dict[str, object]) -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    destination = ARTIFACT_DIR / "core_python_suite.json"
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return destination


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the curated core Python test lane for merge readiness.")
    parser.add_argument("--dry-run", action="store_true", help="Print the command and exit without running pytest.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable command summary.")
    parser.add_argument("--maxfail", type=int, default=1, help="Maximum failures before stopping pytest.")
    parser.add_argument("pytest_args", nargs="*", help="Extra pytest args appended after the curated defaults.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    command = build_pytest_command(maxfail=args.maxfail, extra_args=list(args.pytest_args))
    payload = summary_payload(command)
    summary_path = write_summary(payload)

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print("Core Python merge lane")
        print(f"repo_root={REPO_ROOT}")
        print(f"summary={summary_path}")
        for item in OPTIONAL_TEST_IGNORES:
            print(f"ignore={item}")
        print("command=" + " ".join(command))

    if args.dry_run:
        return 0

    completed = subprocess.run(command, cwd=REPO_ROOT, env=build_environment())
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
