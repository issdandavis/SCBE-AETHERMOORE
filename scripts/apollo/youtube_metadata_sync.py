"""Batch update YouTube video metadata from a local JSON plan.

This script is intentionally fail-safe:
- `preview` shows the planned changes without writing anything.
- `apply` fetches the current video snippet first, then merges the local
  update so required YouTube fields (notably categoryId) are preserved.

Google references used for this implementation:
- YouTube Data API Python quickstart
- YouTube Data API videos.update

Usage:
    python scripts/apollo/youtube_metadata_sync.py preview --input artifacts/apollo/video_reviews/youtube_description_updates_2026-03-26.json
    python scripts/apollo/youtube_metadata_sync.py apply --input artifacts/apollo/video_reviews/youtube_description_updates_2026-03-26.json
    python scripts/apollo/youtube_metadata_sync.py preview --input artifacts/apollo/video_reviews/youtube_title_tag_updates_2026-03-26.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PLAN = ROOT / "artifacts" / "apollo" / "video_reviews" / "youtube_description_updates_2026-03-26.json"
DEFAULT_CLIENT_SECRET = ROOT / "config" / "connector_oauth" / "youtube_client_secret.json"
DEFAULT_TOKEN = ROOT / "config" / "connector_oauth" / "youtube_token.json"
DEFAULT_CONNECTOR_ENV = ROOT / "config" / "connector_oauth" / ".env.connector.oauth"
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


@dataclass
class VideoUpdate:
    video_id: str
    description: str | None = None
    title: str | None = None
    tags: list[str] | None = None


def _load_google_clients():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:  # pragma: no cover - dependency gate
        raise RuntimeError(
            "Missing Google API dependencies. Install: "
            "pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
        ) from exc
    return Request, Credentials, InstalledAppFlow, build


def _resolve_path(env_name: str, default_path: Path) -> Path:
    raw = os.environ.get(env_name)
    return Path(raw).expanduser() if raw else default_path


def _load_connector_env() -> None:
    if not DEFAULT_CONNECTOR_ENV.exists():
        return
    for line in DEFAULT_CONNECTOR_ENV.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_plan(path: Path) -> list[VideoUpdate]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    updates = []
    for item in payload:
        updates.append(
            VideoUpdate(
                video_id=item["video_id"],
                description=item.get("description", "").strip() or None,
                title=item.get("title"),
                tags=item.get("tags"),
            )
        )
    return updates


def get_youtube_service():
    Request, Credentials, InstalledAppFlow, build = _load_google_clients()
    _load_connector_env()
    client_secret_path = _resolve_path("YOUTUBE_CLIENT_SECRET_PATH", DEFAULT_CLIENT_SECRET)
    token_path = _resolve_path("YOUTUBE_TOKEN_PATH", DEFAULT_TOKEN)
    legacy_token_path = ROOT / "config" / "connector_oauth" / ".youtube_tokens.json"
    if not token_path.exists() and legacy_token_path.exists():
        token_path = legacy_token_path

    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")

    def make_flow():
        if client_secret_path.exists():
            return InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)
        if client_id and client_secret:
            client_config = {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost"],
                }
            }
            return InstalledAppFlow.from_client_config(client_config, SCOPES)
        raise FileNotFoundError(
            f"Client secret not found: {client_secret_path}. "
            "Set YOUTUBE_CLIENT_SECRET_PATH or provide YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET."
        )

    creds = None
    if token_path.exists():
        token_data = json.loads(token_path.read_text(encoding="utf-8"))
        if "client_id" not in token_data and client_id:
            token_data["client_id"] = client_id
        if "client_secret" not in token_data and client_secret:
            token_data["client_secret"] = client_secret
        if "token_uri" not in token_data:
            token_data["token_uri"] = "https://oauth2.googleapis.com/token"
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)

    if not creds or not creds.valid:
        refreshed = False
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                refreshed = True
            except Exception:
                creds = None
        if not refreshed:
            flow = make_flow()
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("youtube", "v3", credentials=creds)


def fetch_current_snippet(service, video_id: str) -> dict[str, Any]:
    response = service.videos().list(part="snippet", id=video_id).execute()
    items = response.get("items", [])
    if not items:
        raise ValueError(f"Video not found or inaccessible: {video_id}")
    return items[0]


def build_updated_snippet(current: dict[str, Any], update: VideoUpdate) -> dict[str, Any]:
    snippet = dict(current["snippet"])
    snippet["title"] = (update.title or snippet.get("title") or "").strip()
    if update.description is not None:
        snippet["description"] = update.description

    if not snippet.get("categoryId"):
        raise ValueError(f"Video {update.video_id} is missing snippet.categoryId; refusing to update.")

    if update.tags is not None:
        snippet["tags"] = update.tags

    keep_fields = {
        "title",
        "description",
        "categoryId",
        "tags",
        "defaultLanguage",
        "defaultAudioLanguage",
    }
    return {k: v for k, v in snippet.items() if k in keep_fields and v not in (None, [], "")}


def preview_change(service, update: VideoUpdate) -> None:
    current = fetch_current_snippet(service, update.video_id)
    snippet = current["snippet"]
    old_desc = snippet.get("description", "")
    title = update.title or snippet.get("title", "")
    print(f"\n[{update.video_id}] {title}")
    if update.description is not None:
        print(f"  old description chars: {len(old_desc)}")
        print(f"  new description chars: {len(update.description)}")
    print(f"  categoryId: {snippet.get('categoryId', '?')}")
    if update.title and update.title != snippet.get("title", ""):
        print("  title ->")
        print(f"    old: {snippet.get('title', '')}")
        print(f"    new: {update.title}")
    if update.tags is not None:
        print(f"  tags count: {len(snippet.get('tags', []))} -> {len(update.tags)}")
    if update.description is not None:
        print("  first line ->")
        print(f"    {update.description.splitlines()[0] if update.description else ''}")


def apply_change(service, update: VideoUpdate) -> None:
    current = fetch_current_snippet(service, update.video_id)
    snippet = build_updated_snippet(current, update)
    body = {"id": update.video_id, "snippet": snippet}
    service.videos().update(part="snippet", body=body).execute()
    print(f"updated {update.video_id} -> {snippet['title']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch update YouTube metadata from a local JSON plan.")
    sub = parser.add_subparsers(dest="command", required=True)

    for command in ("preview", "apply"):
        subparser = sub.add_parser(command)
        subparser.add_argument("--input", type=Path, default=DEFAULT_PLAN)

    args = parser.parse_args()
    plan_path: Path = args.input
    if not plan_path.exists():
        raise FileNotFoundError(f"Plan file not found: {plan_path}")

    updates = load_plan(plan_path)
    service = get_youtube_service()

    if args.command == "preview":
        for update in updates:
            preview_change(service, update)
        return 0

    if args.command == "apply":
        for update in updates:
            apply_change(service, update)
        return 0

    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - CLI surface
        print(f"[youtube-metadata-sync] {exc}", file=sys.stderr)
        raise
