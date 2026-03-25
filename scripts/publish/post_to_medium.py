#!/usr/bin/env python3
"""Post stories to Medium via their API.

Usage:
    python scripts/publish/post_to_medium.py --token TOKEN --file content/book/reader-edition/ch01.md
    python scripts/publish/post_to_medium.py --token TOKEN --file ch01.md --title "Chapter 1" --tags "fiction,fantasy"
    python scripts/publish/post_to_medium.py --token TOKEN --chapters 1-3   # Post first 3 chapters
    python scripts/publish/post_to_medium.py --token TOKEN --dry-run        # Preview without posting

Medium API: https://github.com/Medium/medium-api-docs
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CHAPTER_DIR = REPO_ROOT / "content" / "book" / "reader-edition"
AMAZON_LINK = "https://www.amazon.com/dp/B0GSSFQD9G"
AMAZON_PAPERBACK = "https://www.amazon.com/dp/B0GSW8CLC6"

BOOK_CTA = f"""

---

*This is a free sample chapter from **The Six Tongues Protocol: Book One** by Issac Daniel Davis.*

*Want to keep reading?*

**[Get the full novel on Amazon (Kindle $4.99 / Paperback $13.99)]({AMAZON_LINK})**

*The Six Tongues Protocol is a fantasy novel born from 12,596 paragraphs of AI game logs, expanded into a world where languages are architecture and governance is geometry.*

*Follow the author: [GitHub](https://github.com/issdandavis) | [ORCID](https://orcid.org/0009-0002-3936-9369)*
"""

MEDIUM_API = "https://api.medium.com/v1"


def medium_get(endpoint: str, token: str) -> dict:
    req = Request(f"{MEDIUM_API}{endpoint}", headers={"Authorization": f"Bearer {token}"})
    return json.loads(urlopen(req, timeout=15).read())


def medium_post(endpoint: str, token: str, data: dict) -> dict:
    body = json.dumps(data).encode()
    req = Request(
        f"{MEDIUM_API}{endpoint}",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    return json.loads(urlopen(req, timeout=30).read())


def get_user_id(token: str) -> str:
    resp = medium_get("/me", token)
    user = resp.get("data", {})
    print(f"Authenticated as: {user.get('name', '?')} (@{user.get('username', '?')})")
    return user["id"]


def prep_chapter(path: Path, custom_title: str = "") -> tuple[str, str]:
    """Read a chapter file and return (title, content_with_cta)."""
    text = path.read_text(encoding="utf-8")
    lines = text.strip().split("\n")

    # Extract title from first heading
    title = custom_title
    if not title:
        for line in lines:
            if line.startswith("# "):
                title = line.lstrip("# ").strip()
                break
        if not title:
            title = path.stem.replace("-", " ").replace("_", " ").title()

    # Add book title prefix for discoverability
    if "Six Tongues" not in title:
        title = f"The Six Tongues Protocol — {title}"

    # Add CTA at the end
    content = text.strip() + BOOK_CTA

    return title, content


def post_story(token: str, user_id: str, title: str, content: str, tags: list[str], draft: bool = False) -> dict:
    data = {
        "title": title,
        "contentFormat": "markdown",
        "content": content,
        "tags": tags[:5],  # Medium allows max 5 tags
        "publishStatus": "draft" if draft else "public",
    }
    return medium_post(f"/users/{user_id}/posts", token, data)


def main():
    parser = argparse.ArgumentParser(description="Post to Medium")
    parser.add_argument("--token", default=os.environ.get("MEDIUM_TOKEN", ""), help="Medium integration token")
    parser.add_argument("--file", help="Single markdown file to post")
    parser.add_argument("--chapters", help="Chapter range to post (e.g., 1-3)")
    parser.add_argument("--title", default="", help="Custom title override")
    parser.add_argument("--tags", default="fiction,fantasy,ai,scifi,novel", help="Comma-separated tags")
    parser.add_argument("--draft", action="store_true", help="Post as draft (not public)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without posting")
    parser.add_argument("--delay", type=int, default=30, help="Seconds between posts (avoid rate limit)")
    args = parser.parse_args()

    if not args.token:
        print("Error: --token required or set MEDIUM_TOKEN env var")
        print("Get yours at: medium.com/me/settings/security → Integration tokens")
        sys.exit(1)

    tags = [t.strip() for t in args.tags.split(",")]

    # Determine which files to post
    files = []
    if args.file:
        files.append(Path(args.file))
    elif args.chapters:
        start, end = args.chapters.split("-")
        for i in range(int(start), int(end) + 1):
            ch_file = CHAPTER_DIR / f"ch{i:02d}.md"
            if ch_file.exists():
                files.append(ch_file)
            else:
                print(f"Warning: {ch_file} not found, skipping")
    else:
        print("Error: specify --file or --chapters")
        sys.exit(1)

    if args.dry_run:
        for f in files:
            title, content = prep_chapter(f, args.title if len(files) == 1 else "")
            print(f"\n{'='*60}")
            print(f"Title: {title}")
            print(f"Tags: {tags}")
            print(f"Length: {len(content)} chars / ~{len(content.split())} words")
            print(f"Preview: {content[:200]}...")
            print(f"CTA: ...{content[-200:]}")
        return

    # Authenticate
    user_id = get_user_id(args.token)

    # Post each file
    for i, f in enumerate(files):
        title, content = prep_chapter(f, args.title if len(files) == 1 else "")
        print(f"\nPosting: {title} ({len(content.split())} words)...")

        try:
            resp = post_story(args.token, user_id, title, content, tags, draft=args.draft)
            story = resp.get("data", {})
            print(f"  Published: {story.get('url', '?')}")
            print(f"  ID: {story.get('id', '?')}")
        except HTTPError as e:
            body = e.read().decode() if hasattr(e, "read") else str(e)
            print(f"  Error: {e.code} — {body[:200]}")

        if i < len(files) - 1:
            print(f"  Waiting {args.delay}s before next post...")
            time.sleep(args.delay)

    print("\nDone!")


if __name__ == "__main__":
    main()
