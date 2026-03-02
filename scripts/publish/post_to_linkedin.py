#!/usr/bin/env python3
"""
Post to LinkedIn as a share/article.

Required env vars:
    LINKEDIN_ACCESS_TOKEN  - OAuth 2.0 access token with w_member_social scope
                             (obtain via LinkedIn Developer Portal: https://www.linkedin.com/developers/)

Content source:
    content/articles/linkedin_ai_governance_professional.md

Usage:
    python scripts/publish/post_to_linkedin.py
"""

import os
import sys
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT_FILE = REPO_ROOT / "content" / "articles" / "linkedin_ai_governance_professional.md"
LINKEDIN_API_BASE = "https://api.linkedin.com/v2"


def load_content(filepath: Path) -> tuple[str, str]:
    """Read the markdown file and extract the title from the first line and body from the rest."""
    if not filepath.exists():
        raise FileNotFoundError(f"Content file not found: {filepath}")

    text = filepath.read_text(encoding="utf-8").strip()
    lines = text.split("\n", 1)

    title = lines[0].lstrip("#").strip()
    body = lines[1].strip() if len(lines) > 1 else ""

    return title, body


def get_user_urn(token: str) -> str:
    """Fetch the authenticated user's LinkedIn URN (person ID)."""
    import requests

    resp = requests.get(
        f"{LINKEDIN_API_BASE}/userinfo",
        headers={
            "Authorization": f"Bearer {token}",
        },
        timeout=30,
    )

    # If /userinfo fails (older tokens), try /me endpoint
    if resp.status_code != 200:
        resp = requests.get(
            f"{LINKEDIN_API_BASE}/me",
            headers={
                "Authorization": f"Bearer {token}",
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        person_id = data["id"]
        name = f"{data.get('localizedFirstName', '')} {data.get('localizedLastName', '')}".strip()
    else:
        data = resp.json()
        person_id = data.get("sub", "")
        name = data.get("name", "Unknown")

    print(f"[linkedin] Authenticated as {name} (id: {person_id})")
    return f"urn:li:person:{person_id}"


def create_share(token: str, author_urn: str, title: str, body: str) -> dict:
    """Create a share post on LinkedIn using the UGC Post API."""
    import requests

    # LinkedIn share text: combine title and body, truncated if needed
    # LinkedIn text posts support up to 3000 characters
    share_text = f"{title}\n\n{body}"
    if len(share_text) > 3000:
        share_text = share_text[:2997] + "..."
        print(f"[linkedin] WARNING: Content truncated to 3000 chars.")

    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": share_text,
                },
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC",
        },
    }

    resp = requests.post(
        f"{LINKEDIN_API_BASE}/ugcPosts",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        data=json.dumps(payload),
        timeout=30,
    )

    # If UGC API fails, try the newer Posts API (v2)
    if resp.status_code in (403, 422):
        print("[linkedin] UGC Post API unavailable, trying Posts API...")
        return create_share_v2(token, author_urn, title, body)

    resp.raise_for_status()
    return {"id": resp.headers.get("x-restli-id", resp.json().get("id", "unknown"))}


def create_share_v2(token: str, author_urn: str, title: str, body: str) -> dict:
    """Fallback: create a post using the LinkedIn Posts API (Community Management API)."""
    import requests

    share_text = f"{title}\n\n{body}"
    if len(share_text) > 3000:
        share_text = share_text[:2997] + "..."

    payload = {
        "author": author_urn,
        "commentary": share_text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
    }

    resp = requests.post(
        "https://api.linkedin.com/rest/posts",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "LinkedIn-Version": "202401",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        data=json.dumps(payload),
        timeout=30,
    )
    resp.raise_for_status()

    post_id = resp.headers.get("x-restli-id", "unknown")
    return {"id": post_id}


def main() -> int:
    # --- Check env vars ---
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    if not token:
        print("[linkedin] ERROR: Missing env var: LINKEDIN_ACCESS_TOKEN")
        print("  Get your token at: https://www.linkedin.com/developers/")
        return 1

    # --- Check requests library ---
    try:
        import requests  # noqa: F401
    except ImportError:
        print("[linkedin] ERROR: requests not installed. Run: pip install requests")
        return 1

    # --- Load content ---
    try:
        title, body = load_content(CONTENT_FILE)
    except FileNotFoundError as exc:
        print(f"[linkedin] ERROR: {exc}")
        return 1

    print(f"[linkedin] Title: {title}")
    print(f"[linkedin] Body length: {len(body)} chars")

    # --- Get user URN ---
    try:
        author_urn = get_user_urn(token)
    except Exception as exc:
        print(f"[linkedin] ERROR: Failed to authenticate: {exc}")
        return 1

    # --- Create share ---
    try:
        result = create_share(token, author_urn, title, body)
        post_id = result.get("id", "unknown")
        print(f"[linkedin] SUCCESS: Post created!")
        print(f"  Post ID: {post_id}")
        print(f"  View at: https://www.linkedin.com/feed/")
        return 0
    except Exception as exc:
        print(f"[linkedin] ERROR: Failed to create post: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
