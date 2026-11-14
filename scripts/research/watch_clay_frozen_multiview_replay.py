"""Headless final-replay watcher for the frozen multi-view adapter campaign."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.clay_frozen_multiview_replay_watch import configure_threads, watch


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--status-output", type=Path)
    parser.add_argument("--replay-output", type=Path)
    parser.add_argument("--tolerance", type=float, default=1e-12)
    parser.add_argument("--poll-seconds", type=int, default=600)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    configure_threads(args.threads)
    return watch(
        args.run_dir,
        status_output=args.status_output,
        replay_output=args.replay_output,
        tolerance=args.tolerance,
        poll_seconds=args.poll_seconds,
        once=args.once,
    )


if __name__ == "__main__":
    raise SystemExit(main())
