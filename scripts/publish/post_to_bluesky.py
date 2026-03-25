#!/usr/bin/env python3
"""Post to Bluesky — FREE API, no paywall, no OAuth dance.

Setup (one time, 30 seconds):
  1. Go to bsky.app -> sign up (or log in)
  2. Settings -> App Passwords -> Add App Password
  3. Set in .env: BLUESKY_HANDLE=yourname.bsky.social
                  BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx

Usage:
  python scripts/publish/post_to_bluesky.py --text "Hello Bluesky"
  python scripts/publish/post_to_bluesky.py --file content/book/reader-edition/ch01.md
  python scripts/publish/post_to_bluesky.py --promo book
  python scripts/publish/post_to_bluesky.py --promo chapter-1
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen


BSKY_API = "https://bsky.social/xrpc"
AMAZON_LINK = "https://a.co/d/024VowjS"
GITHUB_LINK = "https://github.com/issdandavis/SCBE-AETHERMOORE"

PROMOS = {
    "book": (
        "The Six Tongues Protocol — a fantasy novel born from 12,596 AI game log paragraphs.\n\n"
        "A world where languages are architecture and governance is geometry.\n\n"
        f"Read Chapter 1 free: {GITHUB_LINK}/discussions/704\n\n"
        f"Full novel: {AMAZON_LINK}\n"
        "Kindle $4.99 / Paperback $13.99"
    ),
    "chapter-1": (
        "Chapter 1: Protocol Handshake\n\n"
        '"The smell of stale coffee sat on Marcus Chen\'s tongue like a warning he refused to read."\n\n'
        f"Read free: {GITHUB_LINK}/discussions/704\n\n"
        f"Full novel: {AMAZON_LINK}"
    ),
    "chapter-2": (
        "Chapter 2: The Language Barrier\n\n"
        '"The corridor tasted like static electricity and old libraries."\n\n'
        f"Read free: {GITHUB_LINK}/discussions/705\n\n"
        f"Full novel: {AMAZON_LINK}"
    ),
    "chapter-3": (
        "Chapter 3: Hyperbolic Consequences\n\n"
        '"The first drink in Aethermoor arrived in a stone mug the size of a flowerpot."\n\n'
        f"Read free: {GITHUB_LINK}/discussions/706\n\n"
        f"Full novel: {AMAZON_LINK}"
    ),
    "governance": (
        "We built an AI governance framework that uses hyperbolic geometry instead of text rules.\n\n"
        "91/91 attacks blocked. 0 false positives. Beats ProtectAI DeBERTa v2.\n\n"
        "NIST AI RMF: 23/23 compliance checks pass.\n\n"
        "Open source + patent pending.\n\n"
        f"{GITHUB_LINK}"
    ),
    "design-partner": (
        "Looking for design partners to evaluate our AI governance framework.\n\n"
        "Free evaluation access. No payment during testing.\n\n"
        "- 14-layer security pipeline\n"
        "- Post-quantum crypto\n"
        "- Air-gapped sovereign deployment\n"
        "- NIST AI RMF 100% compliant\n\n"
        "aethermoorgames.com#government"
    ),
}


def bsky_login(handle: str, password: str) -> tuple[str, str]:
    """Login and get access token + DID."""
    data = json.dumps({"identifier": handle, "password": password}).encode()
    req = Request(f"{BSKY_API}/com.atproto.server.createSession", data=data,
                  headers={"Content-Type": "application/json"})
    resp = json.loads(urlopen(req, timeout=10).read())
    return resp["accessJwt"], resp["did"]


def bsky_post(token: str, did: str, text: str) -> dict:
    """Create a post on Bluesky."""
    # Detect URLs and create facets (clickable links)
    facets = []
    for m in re.finditer(r'https?://\S+', text):
        facets.append({
            "index": {"byteStart": m.start(), "byteEnd": m.end()},
            "features": [{"$type": "app.bsky.richtext.facet#link", "uri": m.group()}],
        })

    record = {
        "$type": "app.bsky.feed.post",
        "text": text[:300],  # Bluesky limit is 300 chars
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
    }
    if facets:
        record["facets"] = facets

    data = json.dumps({
        "repo": did,
        "collection": "app.bsky.feed.post",
        "record": record,
    }).encode()

    req = Request(f"{BSKY_API}/com.atproto.repo.createRecord", data=data,
                  headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return json.loads(urlopen(req, timeout=10).read())


def load_creds() -> tuple[str, str]:
    """Load Bluesky creds from env file."""
    env = {}
    env_path = Path("config/connector_oauth/.env.connector.oauth")
    if env_path.exists():
        for line in env_path.read_text().split("\n"):
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                env[k] = v

    handle = os.environ.get("BLUESKY_HANDLE", env.get("BLUESKY_HANDLE", ""))
    password = os.environ.get("BLUESKY_APP_PASSWORD", env.get("BLUESKY_APP_PASSWORD", ""))
    return handle, password


def main():
    parser = argparse.ArgumentParser(description="Post to Bluesky (FREE, no paywall)")
    parser.add_argument("--text", help="Post text directly")
    parser.add_argument("--promo", choices=list(PROMOS.keys()), help="Pre-built promo post")
    parser.add_argument("--file", help="Post first 300 chars of a file with link")
    parser.add_argument("--handle", help="Bluesky handle (or set BLUESKY_HANDLE)")
    parser.add_argument("--password", help="App password (or set BLUESKY_APP_PASSWORD)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    handle = args.handle or ""
    password = args.password or ""
    if not handle or not password:
        h, p = load_creds()
        handle = handle or h
        password = password or p

    if not handle or not password:
        print("Need Bluesky credentials.")
        print("")
        print("One-time setup (30 seconds):")
        print("  1. Go to bsky.app and sign up or log in")
        print("  2. Settings -> App Passwords -> Add App Password")
        print("  3. Add to config/connector_oauth/.env.connector.oauth:")
        print("     BLUESKY_HANDLE=yourname.bsky.social")
        print("     BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx")
        sys.exit(1)

    # Determine what to post
    if args.promo:
        text = PROMOS[args.promo]
    elif args.text:
        text = args.text
    elif args.file:
        content = Path(args.file).read_text()[:250]
        text = content + f"\n\n{AMAZON_LINK}"
    else:
        print("Specify --text, --promo, or --file")
        sys.exit(1)

    if args.dry_run:
        print(f"[DRY RUN] Would post ({len(text)} chars):")
        print(text[:300])
        return

    print(f"Logging in as {handle}...")
    token, did = bsky_login(handle, password)
    print(f"Posting ({len(text[:300])} chars)...")
    resp = bsky_post(token, did, text)
    uri = resp.get("uri", "")
    # Convert AT URI to web URL
    rkey = uri.split("/")[-1] if "/" in uri else ""
    web_url = f"https://bsky.app/profile/{handle}/post/{rkey}"
    print(f"POSTED: {web_url}")


if __name__ == "__main__":
    main()
