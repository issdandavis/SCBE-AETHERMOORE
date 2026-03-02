#!/usr/bin/env python3
"""
Submit a "Show HN" post to Hacker News.

Required env vars:
    HN_USERNAME  - Hacker News username
    HN_PASSWORD  - Hacker News password

Content source:
    content/articles/hackernews_harmonic_crypto.md
    Title extracted from first line; body used as post text.
    Submitted as a "Show HN" post linking to the GitHub repo.

Usage:
    python scripts/publish/post_to_hackernews.py
"""

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT_FILE = REPO_ROOT / "content" / "articles" / "hackernews_harmonic_crypto.md"
GITHUB_REPO_URL = "https://github.com/issdandavis/SCBE-AETHERMOORE"

HN_BASE = "https://news.ycombinator.com"
HN_LOGIN_URL = f"{HN_BASE}/login"
HN_SUBMIT_URL = f"{HN_BASE}/submit"
HN_SUBMIT_POST_URL = f"{HN_BASE}/r"


def load_content(filepath: Path) -> tuple[str, str]:
    """Read the markdown file and extract the title from the first line and body from the rest."""
    if not filepath.exists():
        raise FileNotFoundError(f"Content file not found: {filepath}")

    text = filepath.read_text(encoding="utf-8").strip()
    lines = text.split("\n", 1)

    title = lines[0].lstrip("#").strip()
    body = lines[1].strip() if len(lines) > 1 else ""

    return title, body


def login(session, username: str, password: str) -> bool:
    """Log in to Hacker News and return True on success."""
    # Get the login page to retrieve any hidden form fields
    resp = session.get(HN_LOGIN_URL, timeout=30)
    resp.raise_for_status()

    # Submit login form
    login_data = {
        "acct": username,
        "pw": password,
        "goto": "news",
    }
    resp = session.post(HN_LOGIN_URL, data=login_data, timeout=30)
    resp.raise_for_status()

    # Check if login succeeded by looking for the user link in the response
    if f"user?id={username}" in resp.text:
        return True
    # Some redirects also indicate success
    if resp.url and "news" in resp.url:
        return True

    return False


def get_fnid(session) -> str:
    """Fetch the submit page and extract the fnid (anti-CSRF token)."""
    resp = session.get(HN_SUBMIT_URL, timeout=30)
    resp.raise_for_status()

    # Find the fnid hidden input
    match = re.search(r'name="fnid"\s+value="([^"]+)"', resp.text)
    if not match:
        raise RuntimeError("Could not find fnid token on submit page. Login may have failed.")

    return match.group(1)


def submit_post(session, fnid: str, title: str, url: str, text: str) -> bool:
    """Submit the post to Hacker News."""
    # HN submit form fields
    submit_data = {
        "fnid": fnid,
        "fnop": "submit-page",
        "title": title,
        "url": url,
        "text": text,
    }

    resp = session.post(HN_SUBMIT_POST_URL, data=submit_data, timeout=30, allow_redirects=True)
    resp.raise_for_status()

    # Success usually redirects to /newest or shows the post
    if "newest" in resp.url or resp.status_code == 200:
        return True

    return False


def main() -> int:
    # --- Check env vars ---
    username = os.environ.get("HN_USERNAME")
    password = os.environ.get("HN_PASSWORD")

    missing = []
    if not username:
        missing.append("HN_USERNAME")
    if not password:
        missing.append("HN_PASSWORD")

    if missing:
        print(f"[hackernews] ERROR: Missing env vars: {', '.join(missing)}")
        return 1

    # --- Check requests library ---
    try:
        import requests  # noqa: F401
    except ImportError:
        print("[hackernews] ERROR: requests not installed. Run: pip install requests")
        return 1

    # --- Load content ---
    try:
        raw_title, body = load_content(CONTENT_FILE)
    except FileNotFoundError as exc:
        print(f"[hackernews] ERROR: {exc}")
        return 1

    # Prepend "Show HN: " if not already present
    if not raw_title.lower().startswith("show hn"):
        title = f"Show HN: {raw_title}"
    else:
        title = raw_title

    # HN titles max 80 chars
    if len(title) > 80:
        title = title[:77] + "..."
        print(f"[hackernews] WARNING: Title truncated to 80 chars.")

    print(f"[hackernews] Title: {title}")
    print(f"[hackernews] URL: {GITHUB_REPO_URL}")
    print(f"[hackernews] Body length: {len(body)} chars")

    # --- Create session and login ---
    session = requests.Session()
    session.headers.update({
        "User-Agent": "SCBE-AetherMoore/1.0 (HN poster)",
    })

    try:
        print(f"[hackernews] Logging in as {username}...")
        if not login(session, username, password):
            print("[hackernews] ERROR: Login failed. Check credentials.")
            return 1
        print(f"[hackernews] Logged in as {username}")
    except Exception as exc:
        print(f"[hackernews] ERROR: Login failed: {exc}")
        return 1

    # --- Get fnid and submit ---
    try:
        fnid = get_fnid(session)
        print(f"[hackernews] Got submit token.")
    except Exception as exc:
        print(f"[hackernews] ERROR: Could not get submit token: {exc}")
        return 1

    # For "Show HN" with a URL, we submit the URL and optionally text.
    # HN allows either url OR text, not both. If we have a URL, use that.
    # We put a brief summary as text if no URL is provided.
    try:
        success = submit_post(
            session,
            fnid=fnid,
            title=title,
            url=GITHUB_REPO_URL,
            text="",  # When url is provided, text is ignored by HN
        )

        if success:
            print(f"[hackernews] SUCCESS: Submitted to Hacker News!")
            print(f"  Check: https://news.ycombinator.com/newest")
            return 0
        else:
            print("[hackernews] WARNING: Submission may have failed. Check HN manually.")
            print(f"  Check: https://news.ycombinator.com/submitted?id={username}")
            return 1

    except Exception as exc:
        print(f"[hackernews] ERROR: Submission failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
