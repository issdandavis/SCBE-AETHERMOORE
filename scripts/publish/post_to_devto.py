#!/usr/bin/env python3
"""Dev.to article publisher using the Forem/Dev.to REST API.

Usage:
    python scripts/publish/post_to_devto.py --file content/articles/YOUR_ARTICLE.md
    python scripts/publish/post_to_devto.py --file content/articles/YOUR_ARTICLE.md --dry-run
    python scripts/publish/post_to_devto.py --file content/articles/YOUR_ARTICLE.md --draft

Environment:
    DEVTO_API_KEY  — Your Dev.to API key (Settings > Extensions > DEV Community API Keys)

API docs: https://developers.forem.com/api/v1#tag/Articles/operation/createArticle
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = REPO_ROOT / "artifacts" / "publish_browser"

DEVTO_API_URL = "https://dev.to/api/articles"
_DEVTO_PLACEHOLDERS = {
    "REPLACE_ME",
    "CHANGE_ME",
    "CHANGEME",
    "YOUR_API_KEY",
    "YOUR_KEY_HERE",
    "TODO",
    "TBD",
}


def _is_usable_api_key(value: str) -> bool:
    candidate = value.strip()
    if not candidate:
        return False
    return candidate.upper() not in _DEVTO_PLACEHOLDERS


def _load_api_key() -> str | None:
    """Try multiple env var names for the Dev.to API key."""
    for name in ("DEVTO_API_KEY", "DEV_TO_API_KEY", "DEV_API_KEY"):
        key = os.environ.get(name, "").strip()
        if _is_usable_api_key(key):
            return key
    # Also check the connector oauth file
    oauth_file = REPO_ROOT / "config" / "connector_oauth" / ".env.connector.oauth"
    if oauth_file.exists():
        for line in oauth_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            if k.strip().upper() in ("DEVTO_API_KEY", "DEV_TO_API_KEY", "DEV_API_KEY"):
                value = v.strip()
                if _is_usable_api_key(value):
                    return value
    return None


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML-style frontmatter if present, return (meta, body)."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            meta = {}
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip().strip('"').strip("'")
            return meta, parts[2].strip()
    return {}, text


def _extract_title(body: str) -> tuple[str, str]:
    """Pull the first H1 as the title, return (title, remaining_body)."""
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title = line.lstrip("# ").strip()
            remaining = "\n".join(lines[:i] + lines[i + 1:]).strip()
            return title, remaining
    return "", body


def _strip_byline(body: str) -> str:
    """Remove the byline and separator that follow the title."""
    # Pattern: **By ...** | Date\n---
    body = re.sub(r"^\*\*By[^*]*\*\*\s*\|[^\n]*\n+---\n*", "", body, count=1)
    return body.strip()


def post_article(
    file_path: Path,
    title: str | None = None,
    tags: list[str] | None = None,
    published: bool = True,
    canonical_url: str | None = None,
    series: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Post an article to Dev.to. Returns the API response or dry-run payload."""

    api_key = _load_api_key()
    if not api_key and not dry_run:
        return {"error": "No Dev.to API key found. Set DEVTO_API_KEY environment variable."}

    raw = file_path.read_text(encoding="utf-8", errors="replace")
    meta, body = _parse_frontmatter(raw)

    # Extract title from frontmatter, arg, or first H1
    if not title:
        title = meta.get("title", "")
    if not title:
        title, body = _extract_title(body)
    else:
        _, body = _extract_title(body)  # still strip the H1 to avoid duplication

    # Strip byline
    body = _strip_byline(body)

    if not title:
        return {"error": "Could not determine article title."}

    # Tags
    if not tags:
        raw_tags = meta.get("tags", "")
        if raw_tags:
            tags = [t.strip() for t in raw_tags.replace("[", "").replace("]", "").split(",")]
    if not tags:
        tags = ["ai", "security", "opensource"]
    # Dev.to allows max 4 tags
    tags = tags[:4]

    # Build payload
    article_payload: dict = {
        "title": title,
        "body_markdown": body,
        "published": published,
        "tags": tags,
    }
    if canonical_url:
        article_payload["canonical_url"] = canonical_url
    if series:
        article_payload["series"] = series

    payload = {"article": article_payload}

    if dry_run:
        print("[devto] DRY RUN — would post:")
        print(f"  Title: {title}")
        print(f"  Tags: {tags}")
        print(f"  Published: {published}")
        print(f"  Body length: {len(body)} chars")
        if canonical_url:
            print(f"  Canonical URL: {canonical_url}")
        return {"dry_run": True, "payload": payload}

    # POST to Dev.to API
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        DEVTO_API_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "api-key": api_key,
            "User-Agent": "SCBE-Publisher/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            print(f"[devto] SUCCESS — published!")
            print(f"  URL: {resp_data.get('url', 'unknown')}")
            print(f"  ID: {resp_data.get('id', 'unknown')}")
            return resp_data
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"[devto] HTTP {e.code} Error: {error_body}", file=sys.stderr)
        return {"error": f"HTTP {e.code}", "detail": error_body}
    except urllib.error.URLError as e:
        print(f"[devto] Network error: {e.reason}", file=sys.stderr)
        return {"error": str(e.reason)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish an article to Dev.to")
    parser.add_argument("--file", required=True, help="Path to the markdown article file")
    parser.add_argument("--title", default="", help="Override article title")
    parser.add_argument("--tags", default="", help="Comma-separated tags (max 4)")
    parser.add_argument("--canonical-url", default="", help="Canonical URL for cross-posted content")
    parser.add_argument("--series", default="", help="Series name for multi-part articles")
    parser.add_argument("--draft", action="store_true", help="Post as draft (unpublished)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without posting")
    args = parser.parse_args()

    file_path = Path(args.file).expanduser().resolve()
    if not file_path.exists():
        print(f"[devto] File not found: {file_path}", file=sys.stderr)
        return 1

    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else None

    result = post_article(
        file_path=file_path,
        title=args.title or None,
        tags=tags,
        published=not args.draft,
        canonical_url=args.canonical_url or None,
        series=args.series or None,
        dry_run=args.dry_run,
    )

    # Save evidence
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence = {
        "run_id": run_id,
        "platform": "devto",
        "file": str(file_path),
        "dry_run": args.dry_run,
        "result": result,
    }
    evidence_path = EVIDENCE_DIR / f"devto_{run_id}.json"
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"[devto] Evidence saved: {evidence_path}")

    if "error" in result:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
