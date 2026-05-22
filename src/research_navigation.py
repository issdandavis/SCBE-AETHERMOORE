"""Structured research/navigation packets for agents and CLI users.

The goal is not to replace a browser. The goal is to give agents a stable,
auditable source-access shape that can be routed through GeoSeal, Apollo, and
the agent bus without every workflow inventing its own search/source format.
"""

from __future__ import annotations

import html
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Optional
from urllib.parse import parse_qs, urljoin, urlparse

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
LINK_RE = re.compile(r"<a\s+[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ResearchLink:
    href: str
    text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResearchEvidencePacket:
    url: str
    resolved_url: str
    status: str
    title: str
    text_excerpt: str
    links: list[ResearchLink] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    fetched_at: str = ""
    security: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "scbe-research-evidence-v1",
            "url": self.url,
            "resolved_url": self.resolved_url,
            "status": self.status,
            "title": self.title,
            "text_excerpt": self.text_excerpt,
            "links": [link.to_dict() for link in self.links],
            "metrics": self.metrics,
            "fetched_at": self.fetched_at,
            "security": self.security,
            "error": self.error,
        }


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _clean_html_text(value: str, *, limit: int = 800) -> str:
    text = TAG_RE.sub(" ", value or "")
    text = html.unescape(text)
    text = SPACE_RE.sub(" ", text).strip()
    return text[:limit]


def _extract_title(markup: str) -> str:
    match = TITLE_RE.search(markup or "")
    return _clean_html_text(match.group(1), limit=200) if match else ""


def _extract_links(markup: str, base_url: str, max_links: int) -> list[ResearchLink]:
    links: list[ResearchLink] = []
    seen: set[str] = set()
    for href, body in LINK_RE.findall(markup or ""):
        resolved = urljoin(base_url, html.unescape(href.strip()))
        if not resolved or resolved in seen:
            continue
        seen.add(resolved)
        links.append(ResearchLink(href=resolved, text=_clean_html_text(body, limit=120)))
        if len(links) >= max_links:
            break
    return links


def _scan_content(content: str, url: str) -> dict[str, Any]:
    try:
        from src.symphonic_cipher.scbe_aethermoore.concept_blocks.web_agent.semantic_antivirus import (
            SemanticAntivirus,
        )

        return SemanticAntivirus().scan(content, url=url).to_dict()
    except Exception as exc:  # noqa: BLE001 - scanner should never block packet creation
        return {
            "verdict": "UNSCANNED",
            "governance_decision": "QUARANTINE",
            "reason": f"semantic antivirus unavailable: {exc.__class__.__name__}",
        }


def build_research_evidence_packet(
    *,
    url: str,
    content: Optional[str] = None,
    fetch: bool = True,
    max_links: int = 20,
    timeout: float = 12.0,
) -> ResearchEvidencePacket:
    """Fetch or package a web source into the evidence contract."""

    raw_url = str(url or "").strip()
    if not raw_url:
        raise ValueError("url is required")

    status = "inline"
    resolved_url = raw_url
    body = content or ""
    error: Optional[str] = None

    if content is None and fetch:
        try:
            req = urllib.request.Request(raw_url, headers={"User-Agent": "SCBE-ResearchNav/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                resolved_url = resp.geturl()
                status = str(getattr(resp, "status", "ok"))
                body = resp.read(1_000_000).decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            status = str(exc.code)
            error = str(exc)
            body = exc.read(100_000).decode("utf-8", errors="replace")
            resolved_url = exc.geturl()
        except Exception as exc:  # noqa: BLE001
            status = "fetch_error"
            error = str(exc)
            body = ""
    elif content is None:
        status = "not_fetched"

    title = _extract_title(body)
    excerpt = _clean_html_text(body, limit=1200)
    links = _extract_links(body, resolved_url, max_links=max(0, max_links))
    security = _scan_content(body, resolved_url) if body else {"verdict": "NO_CONTENT", "governance_decision": "QUARANTINE"}
    return ResearchEvidencePacket(
        url=raw_url,
        resolved_url=resolved_url,
        status=status,
        title=title,
        text_excerpt=excerpt,
        links=links,
        metrics={
            "char_count": len(body),
            "excerpt_chars": len(excerpt),
            "link_count": len(links),
            "fetched": bool(content is not None or (fetch and body)),
        },
        fetched_at=_now(),
        security=security,
        error=error,
    )


def extract_youtube_video_id(target: str) -> str:
    raw = str(target or "").strip()
    if not raw:
        raise ValueError("YouTube URL or ID is required")
    if VIDEO_ID_RE.fullmatch(raw):
        return raw

    parsed = urlparse(raw)
    host = (parsed.netloc or "").lower()
    path = parsed.path.strip("/")

    if host in {"youtu.be", "www.youtu.be"}:
        candidate = path.split("/", 1)[0]
        if VIDEO_ID_RE.fullmatch(candidate):
            return candidate

    if host in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}:
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [""])[0].strip()
            if VIDEO_ID_RE.fullmatch(candidate):
                return candidate
        for prefix in ("shorts/", "live/", "embed/"):
            if path.startswith(prefix):
                candidate = path[len(prefix) :].split("/", 1)[0]
                if VIDEO_ID_RE.fullmatch(candidate):
                    return candidate

    raise ValueError(f"Could not extract a YouTube video ID from '{target}'")


def _transcript_text(segments: Iterable[dict[str, Any]]) -> str:
    return "\n".join(str(segment.get("text", "")).strip() for segment in segments if segment.get("text"))


def _fetch_youtube_transcript(video_id: str, languages: list[str]) -> tuple[list[dict[str, Any]], Optional[str]]:
    try:
        from scripts.system.youtube_transcript_pull import fetch_transcript

        return fetch_transcript(video_id, languages), None
    except Exception as exc:  # noqa: BLE001
        return [], str(exc)


def build_youtube_navigation_packet(
    *,
    target: str,
    fetch_metadata: bool = False,
    fetch_transcript: bool = False,
    languages: Optional[list[str]] = None,
    max_links: int = 20,
) -> dict[str, Any]:
    """Build a YouTube source packet with optional transcript evidence."""

    video_id = extract_youtube_video_id(target)
    canonical_url = f"https://www.youtube.com/watch?v={video_id}"
    language_list = [lang for lang in (languages or ["en"]) if lang]

    evidence = build_research_evidence_packet(url=canonical_url, fetch=fetch_metadata, max_links=max_links).to_dict()
    segments: list[dict[str, Any]] = []
    transcript_error: Optional[str] = None
    if fetch_transcript:
        segments, transcript_error = _fetch_youtube_transcript(video_id, language_list)

    text = _transcript_text(segments)
    return {
        "schema_version": "scbe-youtube-navigation-v1",
        "video_id": video_id,
        "canonical_url": canonical_url,
        "languages": language_list,
        "evidence": evidence,
        "transcript": {
            "requested": fetch_transcript,
            "available": bool(segments),
            "segment_count": len(segments),
            "text_excerpt": text[:1200],
            "error": transcript_error,
        },
        "metrics": {
            "has_metadata": bool(evidence.get("metrics", {}).get("fetched")),
            "has_transcript": bool(segments),
            "source_count": 1 + int(bool(segments)),
        },
    }


def packet_to_json(payload: dict[str, Any] | ResearchEvidencePacket) -> str:
    if isinstance(payload, ResearchEvidencePacket):
        payload = payload.to_dict()
    return json.dumps(payload, indent=2, ensure_ascii=False)
