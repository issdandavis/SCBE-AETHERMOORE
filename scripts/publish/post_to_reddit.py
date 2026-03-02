#!/usr/bin/env python3
"""
Post to Reddit (r/aisafety and r/MachineLearning).

Required env vars:
    REDDIT_CLIENT_ID      - Reddit app client ID (from https://www.reddit.com/prefs/apps)
    REDDIT_CLIENT_SECRET  - Reddit app client secret
    REDDIT_USERNAME       - Reddit account username
    REDDIT_PASSWORD       - Reddit account password

Content source:
    content/articles/reddit_aisafety_geometric_containment.md

Usage:
    python scripts/publish/post_to_reddit.py
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT_FILE = REPO_ROOT / "content" / "articles" / "reddit_aisafety_geometric_containment.md"
SUBREDDITS = ["aisafety", "MachineLearning"]
USER_AGENT = "SCBE-AetherMoore:v1.0 (by /u/{username})"


def load_content(filepath: Path) -> tuple[str, str]:
    """Read the markdown file and extract the title from the first line and body from the rest."""
    if not filepath.exists():
        raise FileNotFoundError(f"Content file not found: {filepath}")

    text = filepath.read_text(encoding="utf-8").strip()
    lines = text.split("\n", 1)

    # Title from the first line, stripping any leading '#' markdown heading
    title = lines[0].lstrip("#").strip()
    body = lines[1].strip() if len(lines) > 1 else ""

    return title, body


def main() -> int:
    # --- Check env vars ---
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    username = os.environ.get("REDDIT_USERNAME")
    password = os.environ.get("REDDIT_PASSWORD")

    missing = []
    if not client_id:
        missing.append("REDDIT_CLIENT_ID")
    if not client_secret:
        missing.append("REDDIT_CLIENT_SECRET")
    if not username:
        missing.append("REDDIT_USERNAME")
    if not password:
        missing.append("REDDIT_PASSWORD")

    if missing:
        print(f"[reddit] ERROR: Missing env vars: {', '.join(missing)}")
        return 1

    # --- Import praw (install hint if missing) ---
    try:
        import praw  # noqa: E402
    except ImportError:
        print("[reddit] ERROR: praw not installed. Run: pip install praw")
        return 1

    # --- Load content ---
    try:
        title, body = load_content(CONTENT_FILE)
    except FileNotFoundError as exc:
        print(f"[reddit] ERROR: {exc}")
        return 1

    print(f"[reddit] Title: {title}")
    print(f"[reddit] Body length: {len(body)} chars")

    # --- Authenticate ---
    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent=USER_AGENT.format(username=username),
        )
        # Verify auth
        reddit.user.me()
        print(f"[reddit] Authenticated as u/{username}")
    except Exception as exc:
        print(f"[reddit] ERROR: Authentication failed: {exc}")
        return 1

    # --- Post to each subreddit ---
    success_count = 0
    for sub_name in SUBREDDITS:
        try:
            subreddit = reddit.subreddit(sub_name)
            submission = subreddit.submit(
                title=title,
                selftext=body,
                send_replies=True,
            )
            print(f"[reddit] SUCCESS: Posted to r/{sub_name}")
            print(f"  URL: {submission.url}")
            print(f"  ID:  {submission.id}")
            success_count += 1
        except Exception as exc:
            print(f"[reddit] ERROR: Failed to post to r/{sub_name}: {exc}")

    print(f"\n[reddit] Done. {success_count}/{len(SUBREDDITS)} posts succeeded.")
    return 0 if success_count == len(SUBREDDITS) else 1


if __name__ == "__main__":
    sys.exit(main())
