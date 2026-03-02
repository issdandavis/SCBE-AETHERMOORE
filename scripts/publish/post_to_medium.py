#!/usr/bin/env python3
"""
Post to Medium as a draft article.

Required env vars:
    MEDIUM_TOKEN  - Integration token from https://medium.com/me/settings

Content source:
    content/articles/medium_geometric_skull_v2.md

Usage:
    python scripts/publish/post_to_medium.py
"""

import os
import sys
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT_FILE = REPO_ROOT / "content" / "articles" / "medium_geometric_skull_v2.md"
MEDIUM_API_BASE = "https://api.medium.com/v1"
TAGS = ["AI Safety", "Machine Learning", "Mathematics", "Cryptography"]


def load_content(filepath: Path) -> tuple[str, str]:
    """Read the markdown file and extract the title from the first line and body from the rest."""
    if not filepath.exists():
        raise FileNotFoundError(f"Content file not found: {filepath}")

    text = filepath.read_text(encoding="utf-8").strip()
    lines = text.split("\n", 1)

    title = lines[0].lstrip("#").strip()
    body = lines[1].strip() if len(lines) > 1 else ""

    return title, body


def get_user_id(token: str) -> str:
    """Fetch the authenticated user's Medium ID."""
    import requests

    resp = requests.get(
        f"{MEDIUM_API_BASE}/me",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    user_id = data["data"]["id"]
    username = data["data"]["username"]
    print(f"[medium] Authenticated as @{username} (id: {user_id})")
    return user_id


def create_post(token: str, user_id: str, title: str, body: str) -> dict:
    """Create a draft post on Medium."""
    import requests

    # Combine title and body into full markdown content
    content = f"# {title}\n\n{body}"

    payload = {
        "title": title,
        "contentFormat": "markdown",
        "content": content,
        "tags": TAGS,
        "publishStatus": "draft",
    }

    resp = requests.post(
        f"{MEDIUM_API_BASE}/users/{user_id}/posts",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        data=json.dumps(payload),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"]


def main() -> int:
    # --- Check env vars ---
    token = os.environ.get("MEDIUM_TOKEN")
    if not token:
        print("[medium] ERROR: Missing env var: MEDIUM_TOKEN")
        print("  Get your token at: https://medium.com/me/settings")
        return 1

    # --- Check requests library ---
    try:
        import requests  # noqa: F401
    except ImportError:
        print("[medium] ERROR: requests not installed. Run: pip install requests")
        return 1

    # --- Load content ---
    try:
        title, body = load_content(CONTENT_FILE)
    except FileNotFoundError as exc:
        print(f"[medium] ERROR: {exc}")
        return 1

    print(f"[medium] Title: {title}")
    print(f"[medium] Body length: {len(body)} chars")
    print(f"[medium] Tags: {', '.join(TAGS)}")

    # --- Get user ID ---
    try:
        user_id = get_user_id(token)
    except Exception as exc:
        print(f"[medium] ERROR: Failed to authenticate: {exc}")
        return 1

    # --- Create draft post ---
    try:
        post_data = create_post(token, user_id, title, body)
        print(f"[medium] SUCCESS: Draft created!")
        print(f"  URL: {post_data.get('url', 'N/A')}")
        print(f"  ID:  {post_data.get('id', 'N/A')}")
        print(f"  Status: {post_data.get('publishStatus', 'N/A')}")
        print(f"\n  Edit and publish at: https://medium.com/p/{post_data.get('id', '')}/edit")
        return 0
    except Exception as exc:
        print(f"[medium] ERROR: Failed to create post: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
