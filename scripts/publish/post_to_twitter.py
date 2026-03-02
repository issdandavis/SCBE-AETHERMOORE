#!/usr/bin/env python3
"""
Post a thread to Twitter/X as a reply chain.

Required env vars:
    TWITTER_API_KEY        - Twitter API key (consumer key)
    TWITTER_API_SECRET     - Twitter API secret (consumer secret)
    TWITTER_ACCESS_TOKEN   - Twitter access token
    TWITTER_ACCESS_SECRET  - Twitter access token secret

Content source:
    content/articles/twitter_thread_geometric_skull.md
    Format: numbered tweets like "1/10 First tweet text" separated by blank lines.

Usage:
    python scripts/publish/post_to_twitter.py
"""

import os
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT_FILE = REPO_ROOT / "content" / "articles" / "twitter_thread_geometric_skull.md"

# Delay between tweets to avoid rate limits (seconds)
TWEET_DELAY = 2.0


def load_thread(filepath: Path) -> list[str]:
    """
    Parse the thread file into individual tweet texts.

    Expected format: tweets separated by blank lines, optionally prefixed
    with numbering like '1/10', '2/10', etc. Lines starting with '#' are
    treated as headings and skipped.
    """
    if not filepath.exists():
        raise FileNotFoundError(f"Content file not found: {filepath}")

    text = filepath.read_text(encoding="utf-8").strip()

    # Split on double newlines to get tweet blocks
    blocks = re.split(r"\n\s*\n", text)

    tweets = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # Skip pure markdown headings (lines that are only a heading)
        if block.startswith("#") and "\n" not in block:
            continue

        # Remove the leading number pattern like "1/10 " or "1. "
        cleaned = re.sub(r"^\d+[/.]\d*\s*", "", block).strip()

        # Skip if empty after cleaning
        if not cleaned:
            continue

        # Twitter limit is 280 chars; warn but don't truncate
        if len(cleaned) > 280:
            print(f"  WARNING: Tweet is {len(cleaned)} chars (limit 280): {cleaned[:50]}...")

        tweets.append(cleaned)

    return tweets


def main() -> int:
    # --- Check env vars ---
    api_key = os.environ.get("TWITTER_API_KEY")
    api_secret = os.environ.get("TWITTER_API_SECRET")
    access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
    access_secret = os.environ.get("TWITTER_ACCESS_SECRET")

    missing = []
    if not api_key:
        missing.append("TWITTER_API_KEY")
    if not api_secret:
        missing.append("TWITTER_API_SECRET")
    if not access_token:
        missing.append("TWITTER_ACCESS_TOKEN")
    if not access_secret:
        missing.append("TWITTER_ACCESS_SECRET")

    if missing:
        print(f"[twitter] ERROR: Missing env vars: {', '.join(missing)}")
        return 1

    # --- Import tweepy ---
    try:
        import tweepy  # noqa: E402
    except ImportError:
        print("[twitter] ERROR: tweepy not installed. Run: pip install tweepy")
        return 1

    # --- Load thread ---
    try:
        tweets = load_thread(CONTENT_FILE)
    except FileNotFoundError as exc:
        print(f"[twitter] ERROR: {exc}")
        return 1

    if not tweets:
        print("[twitter] ERROR: No tweets parsed from content file.")
        return 1

    print(f"[twitter] Parsed {len(tweets)} tweets from thread file.")

    # --- Authenticate with Twitter API v2 ---
    try:
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret,
        )
        # Verify credentials by fetching the authenticated user
        me = client.get_me()
        if me.data:
            print(f"[twitter] Authenticated as @{me.data.username}")
        else:
            print("[twitter] WARNING: Could not verify user identity, proceeding anyway.")
    except Exception as exc:
        print(f"[twitter] ERROR: Authentication failed: {exc}")
        return 1

    # --- Post thread as reply chain ---
    previous_tweet_id = None
    success_count = 0

    for i, tweet_text in enumerate(tweets):
        try:
            if previous_tweet_id is None:
                # First tweet in the thread
                response = client.create_tweet(text=tweet_text)
            else:
                # Reply to the previous tweet
                response = client.create_tweet(
                    text=tweet_text,
                    in_reply_to_tweet_id=previous_tweet_id,
                )

            tweet_id = response.data["id"]
            previous_tweet_id = tweet_id
            success_count += 1
            print(f"[twitter] Tweet {i + 1}/{len(tweets)} posted (id: {tweet_id})")

            # Rate-limit delay between tweets
            if i < len(tweets) - 1:
                time.sleep(TWEET_DELAY)

        except Exception as exc:
            print(f"[twitter] ERROR: Failed on tweet {i + 1}/{len(tweets)}: {exc}")
            print(f"  Text: {tweet_text[:100]}...")
            # Continue trying remaining tweets as replies to the last successful one
            if previous_tweet_id is None:
                print("[twitter] Cannot continue thread without a root tweet. Aborting.")
                break

    if success_count > 0 and previous_tweet_id:
        # Construct URL to the first tweet
        username = me.data.username if me.data else "i"
        # The first tweet ID was the response from the first successful post
        print(f"\n[twitter] SUCCESS: {success_count}/{len(tweets)} tweets posted.")
        print(f"  Thread: https://twitter.com/{username}/status/{response.data['id']}")
    else:
        print(f"\n[twitter] FAILED: No tweets were posted.")

    return 0 if success_count == len(tweets) else 1


if __name__ == "__main__":
    sys.exit(main())
