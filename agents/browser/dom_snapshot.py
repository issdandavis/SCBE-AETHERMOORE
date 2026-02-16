"""DOM snapshot utilities for AetherBrowse."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from typing import Any, Optional
from urllib.parse import urlparse
from datetime import datetime, timezone


def _safe_int(value: Optional[str]) -> int:
    try:
        return int(value or 0)
    except ValueError:
        return 0


class _PlainTextExtractor(HTMLParser):
    """Minimal HTML -> text extractor without third-party dependencies."""

    IGNORE_TAGS = {"script", "style", "noscript"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._pieces: list[str] = []
        self._ignore_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.IGNORE_TAGS:
            self._ignore_depth += 1

    def handle_endtag(self, tag):
        if tag in self.IGNORE_TAGS and self._ignore_depth:
            self._ignore_depth -= 1

    def handle_data(self, data):
        if self._ignore_depth:
            return
        text = data.strip()
        if text:
            self._pieces.append(text)

    def text(self) -> str:
        return unescape(" ".join(self._pieces))


@dataclass
class DomSnapshot:
    source_url: Optional[str]
    title: Optional[str]
    text: str
    text_length: int
    link_count: int
    form_count: int
    input_count: int
    button_count: int
    timestamp: str
    html_sha256: str
    raw_html: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_url": self.source_url,
            "title": self.title,
            "text": self.text,
            "text_length": self.text_length,
            "link_count": self.link_count,
            "form_count": self.form_count,
            "input_count": self.input_count,
            "button_count": self.button_count,
            "timestamp": self.timestamp,
            "html_sha256": self.html_sha256,
        }


def _parse_title(html: str) -> Optional[str]:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return unescape(match.group(1).strip())


def _count_tag(html: str, tag: str) -> int:
    if not html:
        return 0
    return len(re.findall(rf"<{tag}\b", html, flags=re.IGNORECASE))


def make_dom_snapshot(
    html: str,
    source_url: Optional[str] = None,
    *,
    max_text: int = 8000,
    include_html: bool = False,
) -> DomSnapshot:
    """Create a compact representation of a page for governance and logging."""
    html = html or ""
    title = _parse_title(html)
    parser = _PlainTextExtractor()
    parser.feed(html)
    text = re.sub(r"\s+", " ", parser.text()).strip()

    digest = hashlib.sha256(html.encode("utf-8", errors="ignore")).hexdigest()
    parsed = urlparse(source_url or "")

    return DomSnapshot(
        source_url=parsed.geturl() if source_url else None,
        title=title,
        text=text[:max_text],
        text_length=len(text),
        link_count=_count_tag(html, "a"),
        form_count=_count_tag(html, "form"),
        input_count=_count_tag(html, "input"),
        button_count=_count_tag(html, "button"),
        timestamp=datetime.now(timezone.utc).isoformat(),
        html_sha256=digest,
        raw_html=html[:max(64, 2 * max_text)] if include_html else None,
    )


def make_action_snapshot_context(snapshot: DomSnapshot) -> dict[str, object]:
    """Compact context payload for audit + future embeddings."""
    return {
        "source_url": snapshot.source_url,
        "title": snapshot.title,
        "text_length": snapshot.text_length,
        "counts": {
            "links": snapshot.link_count,
            "forms": snapshot.form_count,
            "inputs": snapshot.input_count,
            "buttons": snapshot.button_count,
        },
        "html_sha256": snapshot.html_sha256,
        "timestamp": snapshot.timestamp,
    }
