"""Run YouTube metadata sync and Apollo review as one local workflow.

Usage:
    python scripts/apollo/youtube_sync_and_review.py preview --input artifacts/apollo/video_reviews/youtube_title_tag_updates_2026-03-26.json
    python scripts/apollo/youtube_sync_and_review.py apply --input artifacts/apollo/video_reviews/youtube_title_tag_updates_2026-03-26.json
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
SYNC_SCRIPT = ROOT / "scripts" / "apollo" / "youtube_metadata_sync.py"
REVIEW_SCRIPT = ROOT / "scripts" / "apollo" / "video_review.py"


def run_command(args: list[str]) -> int:
    completed = subprocess.run(args, cwd=ROOT)
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview/apply YouTube metadata plan and rerun review.")
    sub = parser.add_subparsers(dest="command", required=True)

    for command in ("preview", "apply"):
        subparser = sub.add_parser(command)
        subparser.add_argument("--input", type=Path, required=True)
        subparser.add_argument("--skip-review", action="store_true")

    args = parser.parse_args()

    exit_code = run_command([sys.executable, str(SYNC_SCRIPT), args.command, "--input", str(args.input)])
    if exit_code != 0:
        return exit_code

    if args.command == "apply" and not args.skip_review:
        return run_command([sys.executable, str(REVIEW_SCRIPT), "review-all"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
