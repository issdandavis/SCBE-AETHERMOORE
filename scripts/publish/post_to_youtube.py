#!/usr/bin/env python3
"""
Upload videos to YouTube via the YouTube Data API v3.

Supports:
- OAuth 2.0 authorization flow (browser-based)
- Resumable uploads for large video files
- Thumbnail upload
- Auto-generated descriptions from article content

Usage:
    python scripts/publish/post_to_youtube.py --auth                    # One-time: authorize
    python scripts/publish/post_to_youtube.py --file video.mp4 --title "My Video"
    python scripts/publish/post_to_youtube.py --file video.mp4 --title "My Video" --dry-run
    python scripts/publish/post_to_youtube.py --file video.mp4 --title "My Video" --thumbnail thumb.png
    python scripts/publish/post_to_youtube.py --file video.mp4 --title "My Video" --privacy public

Environment (from config/connector_oauth/.env.connector.oauth):
    YOUTUBE_CLIENT_ID      - OAuth 2.0 Client ID
    YOUTUBE_CLIENT_SECRET  - OAuth 2.0 Client Secret
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import http.server
import json
import os
import re
import secrets
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

from env_bootstrap import load_connector_env as _load_connector_env

REPO_ROOT = Path(__file__).resolve().parents[2]
TOKEN_FILE = REPO_ROOT / "config" / "connector_oauth" / ".youtube_tokens.json"
ENV_FILE = REPO_ROOT / "config" / "connector_oauth" / ".env.connector.oauth"
EVIDENCE_DIR = REPO_ROOT / "artifacts" / "publish_browser"

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
THUMBNAILS_URL = "https://www.googleapis.com/youtube/v3/thumbnails/set"
PLAYLISTS_URL = "https://www.googleapis.com/youtube/v3/playlists"
PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
REDIRECT_URI = "http://127.0.0.1:8922/callback"
SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube https://www.googleapis.com/auth/youtube.force-ssl"

AUTHOR_NAME = "Issac Daniel Davis"
GITHUB_URL = "https://github.com/issdandavis/SCBE-AETHERMOORE"
STANDARD_FOOTER = f"\n\nBuilt with SCBE-AETHERMOORE | {GITHUB_URL}"

DEFAULT_CATEGORY = "28"  # Science & Technology
DEFAULT_PRIVACY = "unlisted"

VALID_PRIVACIES = ("private", "unlisted", "public")


def _is_present(value: str) -> bool:
    return bool(value and value != "REPLACE_ME")


def load_env() -> None:
    """Load credentials from vault/.env if not already present."""
    _load_connector_env(prefer_vault=True, include_repo_dotenv=True, override=False, verbose=False)


def load_tokens() -> dict:
    """Load saved OAuth tokens."""
    if TOKEN_FILE.exists():
        try:
            return json.loads(TOKEN_FILE.read_text("utf-8"))
        except Exception:
            pass
    return {}


def save_tokens(tokens: dict) -> None:
    """Persist OAuth tokens to disk (gitignored)."""
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(tokens, indent=2), "utf-8")
    print(f"  Tokens saved to {TOKEN_FILE}")


def get_access_token() -> str:
    """Get a valid access token, refreshing if needed."""
    tokens = load_tokens()
    access = tokens.get("access_token", "")

    # Check if token is expired
    expires_at = tokens.get("expires_at", 0)
    if _is_present(access) and (expires_at == 0 or time.time() < expires_at - 60):
        return access

    # Try refresh
    refresh = tokens.get("refresh_token", "")
    if _is_present(refresh):
        new_tokens = refresh_access_token(refresh)
        if new_tokens:
            return new_tokens.get("access_token", "")

    print("ERROR: No valid access token. Run: python scripts/publish/post_to_youtube.py --auth")
    return ""


def refresh_access_token(refresh_token: str) -> dict | None:
    """Use refresh token to get a new access token."""
    client_id = os.environ.get("YOUTUBE_CLIENT_ID", "")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return None

    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    }).encode("utf-8")

    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        ctx = ssl.create_default_context()
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        tokens = json.loads(resp.read().decode())
        # Preserve refresh token (Google doesn't always return it on refresh)
        if "refresh_token" not in tokens:
            tokens["refresh_token"] = refresh_token
        tokens["expires_at"] = time.time() + tokens.get("expires_in", 3600)
        save_tokens(tokens)
        print("  Access token refreshed.")
        return tokens
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"  Refresh failed {e.code}: {body[:300]}")
        return None


def do_auth() -> None:
    """Run the full OAuth 2.0 authorization flow for YouTube."""
    client_id = os.environ.get("YOUTUBE_CLIENT_ID", "")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
    if not client_id:
        print("ERROR: YOUTUBE_CLIENT_ID not set in env or .env.connector.oauth")
        return

    # Generate PKCE verifier + challenge
    code_verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    state = secrets.token_urlsafe(32)

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    print("Opening browser for YouTube authorization...")
    print(f"URL: {auth_url}\n")
    webbrowser.open(auth_url)

    # Start local server to catch callback
    auth_code = [None]

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            if qs.get("state", [None])[0] != state:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"State mismatch")
                return
            auth_code[0] = qs.get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>YouTube authorization successful!</h1><p>You can close this tab.</p>")

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 8922), CallbackHandler)
    print("Waiting for callback on http://127.0.0.1:8922/callback ...")
    server.handle_request()
    server.server_close()

    if not auth_code[0]:
        print("ERROR: No authorization code received.")
        return

    print(f"  Got authorization code: {auth_code[0][:10]}...")

    # Exchange code for tokens
    token_data = {
        "grant_type": "authorization_code",
        "code": auth_code[0],
        "redirect_uri": REDIRECT_URI,
        "client_id": client_id,
        "code_verifier": code_verifier,
    }
    if client_secret:
        token_data["client_secret"] = client_secret

    data = urllib.parse.urlencode(token_data).encode("utf-8")
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        ctx = ssl.create_default_context()
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        tokens = json.loads(resp.read().decode())
        tokens["expires_at"] = time.time() + tokens.get("expires_in", 3600)
        save_tokens(tokens)
        print(f"\n  Access token obtained!")
        print(f"  Scopes: {tokens.get('scope', 'unknown')}")
        print(f"  Expires in: {tokens.get('expires_in', '?')}s")
        if tokens.get("refresh_token"):
            print("  Refresh token saved for auto-renewal.")
        print("\nYou can now upload videos with: --file and --title")
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"  Token exchange failed {e.code}: {body[:300]}")


def _auto_description(article_path: Path | None, max_words: int = 200) -> str:
    """Generate a description from article content (first N words + links)."""
    if not article_path or not article_path.exists():
        return ""

    text = article_path.read_text(encoding="utf-8", errors="replace")

    # Strip frontmatter
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3:]

    # Strip markdown artifacts
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)

    # Preserve link URLs
    links: list[str] = re.findall(r"https?://[^\s\)]+", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()

    words = text.split()
    excerpt = " ".join(words[:max_words])
    if len(words) > max_words:
        excerpt += "..."

    if links:
        excerpt += "\n\nLinks:\n" + "\n".join(f"- {link}" for link in links[:5])

    return excerpt


def upload_video(
    file_path: Path,
    title: str,
    description: str,
    tags: list[str],
    category: str,
    privacy: str,
    thumbnail_path: Path | None = None,
    dry_run: bool = False,
) -> dict:
    """Upload a video to YouTube via resumable upload."""
    result: dict = {
        "file": str(file_path),
        "title": title,
        "privacy": privacy,
        "status": "pending",
    }

    # YouTube rejects descriptions containing < or > characters
    description = description.replace("->", " to ").replace("<-", " from ")
    description = description.replace(">", "").replace("<", "")
    full_description = description + STANDARD_FOOTER

    metadata = {
        "snippet": {
            "title": title,
            "description": full_description,
            "tags": tags,
            "categoryId": category,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    if dry_run:
        result["status"] = "dry_run_ready"
        result["metadata"] = metadata
        result["detail"] = f"Would upload '{file_path.name}' as '{title}' ({privacy})"
        result["description_preview"] = full_description[:500]
        return result

    token = get_access_token()
    if not token:
        result["status"] = "error"
        result["detail"] = "No valid access token"
        return result

    # Step 1: Initiate resumable upload
    params = urllib.parse.urlencode({
        "uploadType": "resumable",
        "part": "snippet,status",
    })
    init_url = f"{UPLOAD_URL}?{params}"

    metadata_bytes = json.dumps(metadata).encode("utf-8")
    ctx = ssl.create_default_context()

    req = urllib.request.Request(init_url, data=metadata_bytes, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    req.add_header("X-Upload-Content-Type", "video/*")
    req.add_header("X-Upload-Content-Length", str(file_path.stat().st_size))

    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        upload_url = resp.headers.get("Location")
        if not upload_url:
            result["status"] = "error"
            result["detail"] = "No upload URL returned from initiation"
            return result
        print(f"  Upload initiated, got resumable URL")
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        result["status"] = "error"
        result["detail"] = f"Upload init failed (HTTP {e.code}): {body[:500]}"
        return result

    # Step 2: Upload video data
    file_size = file_path.stat().st_size
    file_bytes = file_path.read_bytes()

    req = urllib.request.Request(upload_url, data=file_bytes, method="PUT")
    req.add_header("Content-Type", "video/*")
    req.add_header("Content-Length", str(file_size))

    print(f"  Uploading {file_size / (1024 * 1024):.1f} MB...")
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=600)
        response_data = json.loads(resp.read().decode())
        video_id = response_data.get("id", "")
        result["video_id"] = video_id
        result["url"] = f"https://www.youtube.com/watch?v={video_id}"
        result["status"] = "uploaded"
        print(f"  Uploaded! Video ID: {video_id}")
        print(f"  URL: {result['url']}")
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        result["status"] = "error"
        result["detail"] = f"Upload failed (HTTP {e.code}): {body[:500]}"
        return result

    # Step 3: Upload thumbnail (optional)
    if thumbnail_path and thumbnail_path.exists() and video_id:
        print(f"  Uploading thumbnail: {thumbnail_path.name}")
        thumb_ok = _upload_thumbnail(token, video_id, thumbnail_path)
        result["thumbnail_uploaded"] = thumb_ok

    return result


def _upload_thumbnail(token: str, video_id: str, thumb_path: Path) -> bool:
    """Upload a custom thumbnail for a video."""
    params = urllib.parse.urlencode({"videoId": video_id})
    url = f"{THUMBNAILS_URL}?{params}"

    thumb_bytes = thumb_path.read_bytes()
    content_type = "image/png" if thumb_path.suffix.lower() == ".png" else "image/jpeg"

    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, data=thumb_bytes, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", content_type)

    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        print(f"  Thumbnail uploaded successfully")
        return True
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"  Thumbnail upload failed (HTTP {e.code}): {body[:200]}")
        return False


def create_playlist(token: str, title: str, description: str, privacy: str) -> str:
    """Create a YouTube playlist and return its ID."""
    body = json.dumps({
        "snippet": {"title": title, "description": description},
        "status": {"privacyStatus": privacy},
    }).encode("utf-8")

    params = urllib.parse.urlencode({"part": "snippet,status"})
    url = f"{PLAYLISTS_URL}?{params}"
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        data = json.loads(resp.read().decode())
        playlist_id = data["id"]
        print(f"  Created playlist: {title} (ID: {playlist_id})")
        return playlist_id
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        print(f"  Playlist creation failed (HTTP {e.code}): {body_text[:300]}")
        return ""


def add_to_playlist(token: str, playlist_id: str, video_id: str, position: int) -> bool:
    """Add a video to a playlist at a specific position."""
    body = json.dumps({
        "snippet": {
            "playlistId": playlist_id,
            "resourceId": {"kind": "youtube#video", "videoId": video_id},
            "position": position,
        }
    }).encode("utf-8")

    params = urllib.parse.urlencode({"part": "snippet"})
    url = f"{PLAYLIST_ITEMS_URL}?{params}"
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    try:
        urllib.request.urlopen(req, context=ctx, timeout=30)
        return True
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        print(f"  Playlist add failed (HTTP {e.code}): {body_text[:200]}")
        return False


def run_queue_upload(args) -> int:
    """Upload videos from a queue JSON file."""
    queue_path = Path(args.queue)
    if not queue_path.is_absolute():
        queue_path = REPO_ROOT / queue_path
    if not queue_path.exists():
        print(f"ERROR: Queue file not found: {queue_path}")
        return 1

    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    episodes = queue.get("episodes", [])
    default_tags = queue.get("default_tags", [])
    video_dir = queue_path.parent

    # Slice episodes
    start = max(0, args.start_index - 1)
    if args.max_episodes > 0:
        episodes = episodes[start : start + args.max_episodes]
    else:
        episodes = episodes[start:]

    if not episodes:
        print("No episodes to upload.")
        return 0

    print(f"\n{'=' * 60}")
    print(f"YouTube Queue Upload: {len(episodes)} episodes")
    print(f"Privacy: {args.privacy}")
    print(f"{'=' * 60}\n")

    # Preview all episodes
    for i, ep in enumerate(episodes, start=start + 1):
        mp4 = video_dir / ep["file"]
        thumb = video_dir / ep["file"].replace(".mp4", ".thumb.png")
        size = f"{mp4.stat().st_size / 1024 / 1024:.1f} MB" if mp4.exists() else "MISSING"
        print(f"  [{i:2d}] {ep['title']}")
        print(f"       File: {ep['file']} ({size})")
        print(f"       Thumb: {'yes' if thumb.exists() else 'no'}")
        if not mp4.exists():
            print(f"       WARNING: Video file not found!")
        print()

    if args.dry_run:
        print("DRY RUN complete. No videos uploaded.")
        return 0

    # Get token
    token = get_access_token()
    if not token:
        print("ERROR: No valid access token. Run --auth first.")
        return 1

    # Create or use playlist
    playlist_id = args.playlist_id
    if not args.no_playlist and not playlist_id:
        playlist_title = queue.get("playlist_title", "Uploaded Videos")
        playlist_desc = queue.get("playlist_description", "")
        playlist_id = create_playlist(token, playlist_title, playlist_desc, args.privacy)

    uploaded = []
    for i, ep in enumerate(episodes, start=start + 1):
        mp4 = video_dir / ep["file"]
        thumb = video_dir / ep["file"].replace(".mp4", ".thumb.png")

        if not mp4.exists():
            print(f"  [{i}] SKIP (file missing): {ep['file']}")
            continue

        print(f"  [{i}] Uploading: {ep['title']}")

        result = upload_video(
            file_path=mp4,
            title=ep["title"],
            description=ep["description"],
            tags=default_tags,
            category=args.category,
            privacy=args.privacy,
            thumbnail_path=thumb if thumb.exists() else None,
            dry_run=False,
        )

        if result["status"] == "uploaded":
            video_id = result.get("video_id", "")
            uploaded.append({"episode": i, "video_id": video_id, "title": ep["title"], "url": result.get("url", "")})

            if playlist_id and video_id:
                ok = add_to_playlist(token, playlist_id, video_id, len(uploaded) - 1)
                if ok:
                    print(f"    Added to playlist.")

            # Rate-limit (YouTube quota = 10,000 units/day, each upload = 1600 units)
            if i < start + len(episodes):
                print("    Waiting 5s (quota courtesy)...")
                time.sleep(5)
        else:
            print(f"    ERROR: {result.get('detail', 'unknown error')}")
            print("    Stopping to avoid quota burn. Re-run with --start-index to resume.")
            break

    # Save results
    results_path = video_dir / "upload_results.json"
    results = {
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "playlist_id": playlist_id,
        "privacy": args.privacy,
        "videos": uploaded,
    }
    results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(f"\n{'=' * 60}")
    print(f"Uploaded {len(uploaded)} / {len(episodes)} videos")
    if playlist_id:
        print(f"Playlist: https://www.youtube.com/playlist?list={playlist_id}")
    print(f"Results saved: {results_path}")
    print(f"{'=' * 60}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload videos to YouTube via the Data API v3.")
    parser.add_argument("--auth", action="store_true", help="Run OAuth 2.0 authorization flow")
    parser.add_argument("--file", help="Path to the video file to upload")
    parser.add_argument("--title", help="Video title")
    parser.add_argument("--description", default="", help="Video description (auto-generated if omitted)")
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    parser.add_argument(
        "--category", default=DEFAULT_CATEGORY,
        help=f"YouTube category ID (default: {DEFAULT_CATEGORY} = Science & Technology)",
    )
    parser.add_argument("--thumbnail", default="", help="Path to thumbnail image (PNG/JPEG)")
    parser.add_argument(
        "--privacy", default=DEFAULT_PRIVACY, choices=VALID_PRIVACIES,
        help=f"Privacy status (default: {DEFAULT_PRIVACY})",
    )
    parser.add_argument("--article", default="", help="Source article for auto-description generation")
    parser.add_argument("--dry-run", action="store_true", help="Preview metadata without uploading")
    parser.add_argument("--queue", default="", help="Path to upload queue JSON for batch upload")
    parser.add_argument("--start-index", type=int, default=1, help="1-based episode start index (queue mode)")
    parser.add_argument("--max-episodes", type=int, default=0, help="Max episodes to upload, 0=all (queue mode)")
    parser.add_argument("--no-playlist", action="store_true", help="Skip playlist creation (queue mode)")
    parser.add_argument("--playlist-id", default="", help="Existing playlist ID to add videos to")
    args = parser.parse_args()

    load_env()

    if args.auth:
        do_auth()
        return 0

    if args.queue:
        return run_queue_upload(args)

    if not args.file:
        parser.print_help()
        return 1

    file_path = Path(args.file)
    if not file_path.is_absolute():
        file_path = REPO_ROOT / file_path
    if not file_path.exists() and not args.dry_run:
        print(f"ERROR: Video file not found: {file_path}")
        return 1

    title = args.title or file_path.stem.replace("-", " ").replace("_", " ").title()

    # Build description
    description = args.description
    if not description and args.article:
        article_path = Path(args.article)
        if not article_path.is_absolute():
            article_path = REPO_ROOT / article_path
        description = _auto_description(article_path)
    if not description:
        # Try to find a matching article
        article_candidates = list((REPO_ROOT / "content" / "articles").glob(f"*{file_path.stem}*"))
        if article_candidates:
            description = _auto_description(article_candidates[0])
    if not description:
        description = f"{title} by {AUTHOR_NAME}"

    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else [
        "SCBE", "AETHERMOORE", "AI Safety", "machine learning", "Issac Daniel Davis",
    ]

    thumbnail_path = Path(args.thumbnail) if args.thumbnail else None
    if thumbnail_path and not thumbnail_path.is_absolute():
        thumbnail_path = REPO_ROOT / thumbnail_path
    # Auto-detect thumbnail from video companion file
    if not thumbnail_path:
        auto_thumb = file_path.with_suffix(".thumb.png")
        if auto_thumb.exists():
            thumbnail_path = auto_thumb

    result = upload_video(
        file_path=file_path,
        title=title,
        description=description,
        tags=tags,
        category=args.category,
        privacy=args.privacy,
        thumbnail_path=thumbnail_path,
        dry_run=args.dry_run,
    )

    # Write evidence
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": bool(args.dry_run),
        "platform": "youtube",
        "result": result,
    }
    evidence_path = EVIDENCE_DIR / f"youtube_{run_id}.json"
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    print(f"\n[youtube] status={result['status']}")
    if result.get("url"):
        print(f"[youtube] URL={result['url']}")
    print(f"[youtube] evidence={evidence_path}")

    return 0 if result["status"] in ("uploaded", "dry_run_ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
