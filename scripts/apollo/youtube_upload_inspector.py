#!/usr/bin/env python3
"""Inspect uploaded YouTube videos for cut endings and repair paths.

This is the post-upload companion to ``scripts/publish/youtube_video_tool.py``.
It reads live YouTube metadata through the existing OAuth token path used by
``post_to_youtube.py``, checks transcripts when available, and writes a report
that points back to local tail export / append-ending commands.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "publish"))

REPORT_DIR = ROOT / "artifacts" / "apollo" / "video_reviews"
YOUTUBE_API = "https://www.googleapis.com/youtube/v3"
TOKEN_FILE = ROOT / "config" / "connector_oauth" / ".youtube_tokens.json"
ENV_FILE = ROOT / "config" / "connector_oauth" / ".env.connector.oauth"
TOKEN_URL = "https://oauth2.googleapis.com/token"


@dataclass(frozen=True)
class UploadSourceEvidence:
    file: str | None = None
    evidence_file: str | None = None
    dry_run: bool | None = None
    local_duration_seconds: float | None = None


@dataclass(frozen=True)
class UploadedVideoInspection:
    video_id: str
    title: str
    url: str
    live_duration_seconds: int
    privacy_status: str
    upload_status: str
    processing_status: str | None
    transcript_checked: bool
    transcript_length: int
    transcript_tail: str
    chapter_package: dict[str, Any]
    risk: str
    issues: list[str]
    suggestions: list[str]
    source: UploadSourceEvidence = field(default_factory=UploadSourceEvidence)


def parse_iso_duration(value: str) -> int:
    """Parse YouTube ISO 8601 duration strings like PT1H2M3S."""
    import re

    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def format_seconds(seconds: int | float | None) -> str:
    if seconds is None:
        return "?"
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    return f"{minutes}m {secs}s"


def _load_access_token() -> str:
    load_connector_env()
    tokens = load_tokens()
    access = tokens.get("access_token", "")
    expires_at = tokens.get("expires_at", 0)
    if access and (expires_at == 0 or time.time() < expires_at - 60):
        return access

    refresh = tokens.get("refresh_token", "")
    if refresh:
        refreshed = refresh_access_token(refresh)
        if refreshed.get("access_token"):
            return refreshed["access_token"]
    raise RuntimeError("No YouTube access token. Run: python scripts/publish/post_to_youtube.py --auth")


def load_connector_env() -> None:
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_tokens() -> dict[str, Any]:
    if TOKEN_FILE.exists():
        try:
            return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_tokens(tokens: dict[str, Any]) -> None:
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")


def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    client_id = os.environ.get("YOUTUBE_CLIENT_ID", "")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return {}

    data = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }
    ).encode("utf-8")
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=30) as response:
            tokens = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise RuntimeError(f"YouTube token refresh failed HTTP {exc.code}: {body[:300]}") from exc
    tokens["refresh_token"] = tokens.get("refresh_token") or refresh_token
    tokens["expires_at"] = time.time() + tokens.get("expires_in", 3600)
    save_tokens(tokens)
    return tokens


def youtube_get(token: str, resource: str, params: dict[str, Any]) -> dict[str, Any]:
    query = urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
    url = f"{YOUTUBE_API}/{resource}?{query}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise RuntimeError(f"YouTube API {resource} failed HTTP {exc.code}: {body[:400]}") from exc


def get_uploads_playlist_id(token: str) -> str:
    payload = youtube_get(token, "channels", {"part": "contentDetails", "mine": "true"})
    items = payload.get("items", [])
    if not items:
        raise RuntimeError("No authenticated YouTube channel returned for mine=true.")
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def list_uploaded_video_ids(token: str, *, limit: int = 25) -> list[str]:
    playlist_id = get_uploads_playlist_id(token)
    ids: list[str] = []
    page_token = ""
    while len(ids) < limit:
        payload = youtube_get(
            token,
            "playlistItems",
            {
                "part": "contentDetails",
                "playlistId": playlist_id,
                "maxResults": min(50, limit - len(ids)),
                "pageToken": page_token,
            },
        )
        for item in payload.get("items", []):
            video_id = item.get("contentDetails", {}).get("videoId")
            if video_id:
                ids.append(video_id)
        page_token = payload.get("nextPageToken", "")
        if not page_token:
            break
    return ids


def fetch_video_records(token: str, video_ids: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for start in range(0, len(video_ids), 50):
        chunk = video_ids[start : start + 50]
        payload = youtube_get(
            token,
            "videos",
            {
                "part": "snippet,contentDetails,status,processingDetails",
                "id": ",".join(chunk),
                "maxResults": 50,
            },
        )
        records.extend(payload.get("items", []))
    return records


def get_transcript_text(video_id: str, *, no_delay: bool = True) -> tuple[bool, str]:
    try:
        from scripts.apollo.youtube_transcript_collector import get_transcript

        transcript = get_transcript(video_id, delay=not no_delay)
        return True, transcript or ""
    except Exception:
        return False, ""


def load_local_upload_evidence() -> dict[str, UploadSourceEvidence]:
    """Map uploaded video IDs and dry-run titles to local source files."""
    evidence: dict[str, UploadSourceEvidence] = {}
    if not (ROOT / "artifacts" / "publish_browser").exists():
        return evidence
    for path in sorted((ROOT / "artifacts" / "publish_browser").glob("youtube*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        result = payload.get("result", {})
        source = UploadSourceEvidence(
            file=result.get("file"),
            evidence_file=str(path),
            dry_run=bool(payload.get("dry_run")),
        )
        video_id = result.get("video_id")
        if video_id:
            evidence[video_id] = source
        title = result.get("title")
        if title:
            evidence[f"title:{title.strip().lower()}"] = source
    return evidence


def inspect_video_record(record: dict[str, Any], source_index: dict[str, UploadSourceEvidence]) -> UploadedVideoInspection:
    video_id = record.get("id", "")
    snippet = record.get("snippet", {})
    status = record.get("status", {})
    content = record.get("contentDetails", {})
    processing = record.get("processingDetails", {})
    title = snippet.get("title", "")
    description = snippet.get("description", "")
    live_duration = parse_iso_duration(content.get("duration", ""))
    transcript_checked, transcript = get_transcript_text(video_id)
    transcript_tail = " ".join(transcript.split()[-24:]) if transcript else ""
    source = source_index.get(video_id) or source_index.get(f"title:{title.strip().lower()}") or UploadSourceEvidence()
    try:
        from scripts.publish.youtube_video_tool import ScriptPlan, build_chapter_package

        chapter_package = build_chapter_package(
            package_text=" ".join(part for part in [description, transcript_tail] if part),
            script=ScriptPlan(path=None, available=False, final_words=transcript_tail),
            require_chapter_package=True,
        )
        chapter_package_dict = asdict(chapter_package)
    except Exception:
        chapter_package_dict = {}

    issues: list[str] = []
    suggestions: list[str] = []
    risk_score = 0

    if processing.get("processingStatus") not in (None, "succeeded"):
        risk_score += 2
        issues.append(f"Processing status is {processing.get('processingStatus')}")
        suggestions.append("Wait for YouTube processing to finish before judging the ending.")
    if live_duration <= 0:
        risk_score += 4
        issues.append("Live YouTube duration is missing or zero")
        suggestions.append("Re-check through YouTube Studio and the local render before publishing.")
    if transcript_checked and not transcript:
        risk_score += 2
        issues.append("No YouTube transcript/captions were available")
        suggestions.append("Upload captions or compare the local source transcript before public release.")
    if transcript and len(transcript.split()) < max(30, live_duration * 0.6):
        risk_score += 3
        issues.append("Transcript is short relative to live duration")
        suggestions.append("Inspect the last 30 seconds; the narration or captions may be incomplete.")
    if transcript_tail and transcript_tail[-1:] not in ".?!'\"":
        risk_score += 1
        issues.append("Transcript tail does not end with terminal punctuation")
        suggestions.append("Read/listen to the tail; this is a weak but useful cutoff signal.")
    if chapter_package_dict:
        if not chapter_package_dict.get("recap_present"):
            risk_score += 1
            issues.append("Viewer package lacks a pre-chapter recap")
            suggestions.append("Add a short 'what happened before' bridge to the description or intro.")
        if not chapter_package_dict.get("chapter_setup_present"):
            risk_score += 1
            issues.append("Viewer package lacks chapter setup")
            suggestions.append("State what the chapter is leading the listener into before the scene starts.")
        if not chapter_package_dict.get("outro_present"):
            risk_score += 1
            issues.append("Viewer package lacks outro/CTA language")
            suggestions.append("Add subscribe and notification-bell language after the chapter close.")
        if not chapter_package_dict.get("next_lead_present"):
            risk_score += 1
            issues.append("Viewer package lacks next-chapter lead-in")
            suggestions.append("Add one sentence about what this chapter sets up next.")
    if source.file:
        local_file = Path(source.file)
        if local_file.exists():
            try:
                from scripts.publish.youtube_video_tool import probe_media

                media = probe_media(local_file)
                source = UploadSourceEvidence(
                    file=source.file,
                    evidence_file=source.evidence_file,
                    dry_run=source.dry_run,
                    local_duration_seconds=media.duration_seconds or None,
                )
                if media.duration_seconds and live_duration and abs(media.duration_seconds - live_duration) > 2.0:
                    risk_score += 4
                    issues.append(
                        f"Live duration {format_seconds(live_duration)} differs from local render "
                        f"{format_seconds(media.duration_seconds)}"
                    )
                    suggestions.append("Treat this as a likely upload/render mismatch; replace with a fresh upload.")
            except Exception as exc:
                suggestions.append(f"Local media probe failed for source file: {exc}")
        else:
            suggestions.append("Local source file from upload evidence is not present on this machine.")

    if not issues:
        suggestions.append("No cutoff signal found from live metadata/transcript. Still review the tail before public release.")
    if source.file:
        suggestions.append(
            "Tail review: python scripts/publish/youtube_video_tool.py tail "
            f"--file \"{source.file}\" --seconds 30 --out artifacts/youtube/reviews/{video_id}.tail.mp4"
        )
        suggestions.append(
            "Repair flow: render a fixed ending clip, then run "
            "python scripts/publish/youtube_video_tool.py append-ending --file <original.mp4> --ending <ending.mp4> --out <fixed.mp4>"
        )
    suggestions.append("YouTube cannot overwrite uploaded video media; upload the fixed file as a replacement/unlisted first.")

    risk = "high" if risk_score >= 5 else "medium" if risk_score >= 2 else "low"
    return UploadedVideoInspection(
        video_id=video_id,
        title=title,
        url=f"https://www.youtube.com/watch?v={video_id}",
        live_duration_seconds=live_duration,
        privacy_status=status.get("privacyStatus", ""),
        upload_status=status.get("uploadStatus", ""),
        processing_status=processing.get("processingStatus"),
        transcript_checked=transcript_checked,
        transcript_length=len(transcript),
        transcript_tail=transcript_tail,
        chapter_package=chapter_package_dict,
        risk=risk,
        issues=issues,
        suggestions=suggestions,
        source=source,
    )


def write_report(reports: list[UploadedVideoInspection], output: Path | None = None) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = output or REPORT_DIR / f"youtube_upload_inspection_{dt.date.today().isoformat()}.json"
    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "count": len(reports),
        "reports": [asdict(report) for report in reports],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def print_summary(reports: list[UploadedVideoInspection], report_path: Path) -> None:
    print("YOUTUBE UPLOAD INSPECTION")
    print("=" * 60)
    for report in reports:
        print(f"\n[{report.risk.upper()}] {report.title}")
        print(f"  {report.url}")
        print(f"  Live duration: {format_seconds(report.live_duration_seconds)}")
        if report.source.local_duration_seconds is not None:
            print(f"  Local duration: {format_seconds(report.source.local_duration_seconds)}")
        if report.issues:
            for issue in report.issues:
                print(f"  ! {issue}")
        else:
            print("  No cutoff signal found")
    print(f"\nReport: {report_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect live YouTube uploads for cut endings.")
    sub = parser.add_subparsers(dest="command", required=True)

    latest = sub.add_parser("latest", help="Inspect the latest uploads from the authenticated channel")
    latest.add_argument("--limit", type=int, default=10)
    latest.add_argument("--out", type=Path)

    one = sub.add_parser("video", help="Inspect one video by ID")
    one.add_argument("--video-id", required=True)
    one.add_argument("--out", type=Path)

    args = parser.parse_args(argv)
    token = _load_access_token()
    source_index = load_local_upload_evidence()

    if args.command == "latest":
        ids = list_uploaded_video_ids(token, limit=args.limit)
    else:
        ids = [args.video_id]

    records = fetch_video_records(token, ids)
    reports = [inspect_video_record(record, source_index) for record in records]
    report_path = write_report(reports, args.out)
    print_summary(reports, report_path)
    return 0 if reports else 1


if __name__ == "__main__":
    raise SystemExit(main())
