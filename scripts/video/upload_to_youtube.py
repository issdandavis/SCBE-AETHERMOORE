#!/usr/bin/env python3
"""Thin wrapper around youtubeuploader for SCBE video uploads.

`youtubeuploader` (porjo/youtubeuploader, MIT-licensed Go binary) handles the
actual OAuth flow, token caching, and resumable upload. This wrapper just
makes invocation tidy and prevents accidental "public" uploads on first run.

Usage:
    python scripts/video/upload_to_youtube.py path/to/video.mp4 \
        --title "SCBE Systems Blueprint" \
        --description "14-layer governance pipeline walkthrough" \
        --tags "AI safety,governance,SCBE,Aethermoore" \
        --privacy unlisted

Default privacy is `private` — even if you forget the flag, you cannot
accidentally publish to the world. Override explicitly with --privacy public
when you actually intend to publish.

Requires:
    - youtubeuploader.exe in PATH (download from
      https://github.com/porjo/youtubeuploader/releases)
    - .secrets/youtube/client_secrets.json (your OAuth client secret)
    - First run pops a browser; subsequent runs are headless.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SECRETS_DIR = REPO_ROOT / ".secrets" / "youtube"
DEFAULT_CLIENT_SECRETS = DEFAULT_SECRETS_DIR / "client_secrets.json"
DEFAULT_TOKEN_CACHE = DEFAULT_SECRETS_DIR / "request.token"

VALID_PRIVACY = {"private", "unlisted", "public"}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("video", type=Path, help="MP4 to upload")
    p.add_argument("--title", required=True, help="Video title")
    p.add_argument(
        "--description",
        default="",
        help="Video description (markdown not supported by YouTube)",
    )
    p.add_argument(
        "--tags",
        default="",
        help="Comma-separated tag list",
    )
    p.add_argument(
        "--privacy",
        default="private",
        choices=sorted(VALID_PRIVACY),
        help="Privacy mode (default: private — never accidentally public)",
    )
    p.add_argument(
        "--category",
        default="28",  # Science & Technology
        help="YouTube category ID (default: 28 Science & Technology)",
    )
    p.add_argument(
        "--client-secrets",
        type=Path,
        default=DEFAULT_CLIENT_SECRETS,
        help=f"Path to client_secrets.json (default: {DEFAULT_CLIENT_SECRETS})",
    )
    p.add_argument(
        "--token-cache",
        type=Path,
        default=DEFAULT_TOKEN_CACHE,
        help=f"Path to OAuth refresh-token cache (default: {DEFAULT_TOKEN_CACHE})",
    )
    p.add_argument(
        "--thumbnail",
        type=Path,
        default=None,
        help="Optional thumbnail image",
    )
    p.add_argument(
        "--playlist",
        default=None,
        help="Add the uploaded video to this playlist ID",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the youtubeuploader command without executing it",
    )
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.video.is_file():
        print(f"ERROR: video not found: {args.video}", file=sys.stderr)
        return 1

    if not args.client_secrets.is_file():
        print(
            f"ERROR: client_secrets.json not found at {args.client_secrets}\n"
            "Move your downloaded Google OAuth client_secret_*.json to that "
            "path (or pass --client-secrets to override).",
            file=sys.stderr,
        )
        return 2

    if not shutil.which("youtubeuploader") and not shutil.which("youtubeuploader.exe"):
        print(
            "ERROR: youtubeuploader not in PATH.\n"
            "Download from https://github.com/porjo/youtubeuploader/releases "
            "and place the binary in a PATH directory (e.g. "
            r"C:\Users\issda\.local\bin\).",
            file=sys.stderr,
        )
        return 3

    args.token_cache.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "youtubeuploader",
        "-filename", str(args.video),
        "-title", args.title,
        "-description", args.description,
        "-tags", args.tags,
        "-privacy", args.privacy,
        "-categoryId", args.category,
        "-secrets", str(args.client_secrets),
        "-cache", str(args.token_cache),
    ]
    if args.thumbnail and args.thumbnail.is_file():
        cmd += ["-thumbnail", str(args.thumbnail)]
    if args.playlist:
        cmd += ["-playlistID", args.playlist]

    print("[upload_to_youtube] command:", " ".join(cmd))
    if args.dry_run:
        print("[upload_to_youtube] dry-run; not invoking")
        return 0

    if args.privacy == "public":
        print(
            "[upload_to_youtube] WARNING: privacy=public — this video will be "
            "visible to the entire internet on success. Ctrl-C within 3 seconds "
            "to abort..."
        )
        try:
            import time

            time.sleep(3)
        except KeyboardInterrupt:
            print("[upload_to_youtube] aborted by user")
            return 130

    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
