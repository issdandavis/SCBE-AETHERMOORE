"""Keep one hash-pinned frozen multi-view campaign alive without duplicating it."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.clay_frozen_multiview_supervisor import (  # noqa: E402
    SupervisorContract,
    watch,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--run-manifest-sha256", required=True)
    parser.add_argument("--headless-config", type=Path, required=True)
    parser.add_argument("--headless-config-sha256", required=True)
    parser.add_argument("--headless-launcher", type=Path, required=True)
    parser.add_argument("--headless-launcher-sha256", required=True)
    parser.add_argument("--training-cli", type=Path, required=True)
    parser.add_argument("--training-cli-sha256", required=True)
    parser.add_argument("--status-output", type=Path)
    parser.add_argument("--lock-path", type=Path)
    parser.add_argument("--max-restarts", type=int, default=3)
    parser.add_argument("--max-no-progress-restarts", type=int, default=3)
    parser.add_argument("--grace-seconds", type=int, default=30)
    parser.add_argument("--startup-seconds", type=int, default=30)
    parser.add_argument("--poll-seconds", type=int, default=300)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    contract = SupervisorContract(
        run_dir=run_dir,
        run_manifest_sha256=args.run_manifest_sha256,
        headless_config=args.headless_config,
        headless_config_sha256=args.headless_config_sha256,
        headless_launcher=args.headless_launcher,
        headless_launcher_sha256=args.headless_launcher_sha256,
        training_cli=args.training_cli,
        training_cli_sha256=args.training_cli_sha256,
        status_output=args.status_output or run_dir / "TRAINING_SUPERVISOR_STATUS.json",
        lock_path=args.lock_path or run_dir / "TRAINING_SUPERVISOR.lock",
        max_restarts=args.max_restarts,
        max_no_progress_restarts=args.max_no_progress_restarts,
        grace_seconds=args.grace_seconds,
        startup_seconds=args.startup_seconds,
    )
    return watch(contract, poll_seconds=args.poll_seconds, once=args.once)


if __name__ == "__main__":
    raise SystemExit(main())
