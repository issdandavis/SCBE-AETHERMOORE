#!/usr/bin/env python3
"""
Post to Buffer using Buffer Publish API.

Environment:
    BUFFER_ACCESS_TOKEN  - Buffer access token (required)
    BUFFER_PROFILE_IDS   - Comma-separated Buffer profile IDs (required)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BUFFER_CREATE_URL = "https://api.bufferapp.com/1/updates/create.json"
BUFFER_PROFILES_URL = "https://api.bufferapp.com/1/profiles.json"


def _is_present(value: str) -> bool:
    return bool(value and value != "REPLACE_ME")


def _profiles_from_env(raw: str) -> list[str]:
    return [p.strip() for p in (raw or "").split(",") if p.strip()]


def _discover_profile_ids(token: str) -> list[str]:
    params = urllib.parse.urlencode({"access_token": token})
    req = urllib.request.Request(f"{BUFFER_PROFILES_URL}?{params}", method="GET")
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return []

    if not isinstance(data, list):
        return []
    preferred = [p.get("id", "") for p in data if isinstance(p, dict) and p.get("service") in ("twitter", "x")]
    fallback = [p.get("id", "") for p in data if isinstance(p, dict)]
    values = preferred or fallback
    return [v for v in values if v]


def _load_credentials() -> tuple[str, list[str]]:
    token = os.environ.get("BUFFER_ACCESS_TOKEN", "")
    profiles = _profiles_from_env(os.environ.get("BUFFER_PROFILE_IDS", ""))
    if _is_present(token) and not profiles:
        profiles = _discover_profile_ids(token)
    return token, profiles


def _parse_thread_file(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8", errors="replace")
    parts = re.split(r"^## \d+/\d+\s*\n", content, flags=re.MULTILINE)
    posts: list[str] = []
    for part in parts:
        part = part.strip()
        if not part or part.startswith("---") or part.startswith("#"):
            continue
        text = re.sub(r"\s+", " ", part).strip()
        if len(text) > 280:
            text = text[:277].rstrip() + "..."
        if text:
            posts.append(text)
    return posts


def _buffer_create_update(text: str, token: str, profile_ids: list[str]) -> tuple[bool, str]:
    payload = {
        "access_token": token,
        "text": text,
        "profile_ids[]": profile_ids,
        "now": "true",
        "shorten": "true",
    }
    encoded = urllib.parse.urlencode(payload, doseq=True).encode("utf-8")
    req = urllib.request.Request(BUFFER_CREATE_URL, data=encoded, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return True, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return False, f"HTTP {e.code}: {body}"
    except Exception as e:
        return False, str(e)


def _post_text(text: str, dry_run: bool) -> int:
    token, profile_ids = _load_credentials()
    if not _is_present(token):
        print("ERROR: BUFFER_ACCESS_TOKEN is not configured.")
        return 1
    if not profile_ids:
        print("ERROR: BUFFER_PROFILE_IDS is not configured.")
        return 1

    if dry_run:
        print(f"[DRY RUN] Buffer post to profiles={profile_ids}: {text[:120]}")
        return 0

    ok, detail = _buffer_create_update(text=text, token=token, profile_ids=profile_ids)
    if ok:
        print("Buffer post created.")
        return 0
    print(f"ERROR: Buffer post failed: {detail[:500]}")
    return 1


def _post_thread(path: Path, dry_run: bool) -> int:
    posts = _parse_thread_file(path)
    if not posts:
        print("ERROR: no posts found in thread file.")
        return 1
    print(f"Thread: {len(posts)} posts")
    for i, text in enumerate(posts, start=1):
        print(f"--- Buffer post {i}/{len(posts)} ({len(text)} chars) ---")
        rc = _post_text(text=text, dry_run=dry_run)
        if rc != 0:
            return rc
        if not dry_run and i < len(posts):
            time.sleep(2)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Post to Buffer.")
    parser.add_argument("--text", default="", help="Single status text.")
    parser.add_argument("--thread", default="", help="Thread markdown file path.")
    parser.add_argument("--dry-run", action="store_true", help="Preview only.")
    args = parser.parse_args()

    if args.thread:
        return _post_thread(Path(args.thread), dry_run=args.dry_run)
    if args.text:
        return _post_text(text=args.text, dry_run=args.dry_run)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
