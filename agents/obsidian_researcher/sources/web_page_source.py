"""Generic web page source adapter for the Obsidian researcher agent.

Fetches arbitrary URLs, extracts readable text content, and converts
into ``IngestionResult`` records.  Pure-stdlib implementation (uses
:mod:`urllib.request` for HTTP and :mod:`re` for HTML stripping).

Handles three content flavours:

* **HTML** -- strips tags, extracts ``<title>``, pulls text from
  ``<p>``, ``<article>``, and ``<main>`` elements.
* **Markdown** -- detected by ``.md`` extension; read as-is without
  HTML stripping.
* **Plain text** -- anything else; ingested verbatim.
"""

from __future__ import annotations

import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..source_adapter import IngestionResult, SourceAdapter, SourceType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_TIMEOUT = 15
_DEFAULT_MAX_CONTENT_LENGTH = 500_000  # 500 KB

_USER_AGENT = "SCBE-ResearchAgent/1.0 (research only)"

# Regex patterns for readability extraction
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_ARTICLE_RE = re.compile(
    r"<(?:article|main)[^>]*>(.*?)</(?:article|main)>",
    re.IGNORECASE | re.DOTALL,
)
_PARAGRAPH_RE = re.compile(
    r"<p[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL
)
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\n{3,}")
_ENTITY_MAP = {
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&#39;": "'",
    "&apos;": "'",
    "&nbsp;": " ",
}


class WebPageSource(SourceAdapter):
    """Adapter that fetches a URL, extracts readable content, and emits
    an :class:`IngestionResult`.

    Parameters
    ----------
    config : dict
        Optional keys:

        * ``timeout`` -- HTTP timeout in seconds (default 15).
        * ``max_content_length`` -- maximum bytes to read from the
          response body (default 500 000).
        * ``user_agent`` -- custom User-Agent string.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(source_type=SourceType.WEB_PAGE, config=config or {})

        self._timeout: int = int(
            self.config.get("timeout", _DEFAULT_TIMEOUT)
        )
        self._max_content_length: int = int(
            self.config.get("max_content_length", _DEFAULT_MAX_CONTENT_LENGTH)
        )
        self._user_agent: str = self.config.get("user_agent", _USER_AGENT)

    # ------------------------------------------------------------------
    # SourceAdapter interface
    # ------------------------------------------------------------------

    def fetch(self, query: str, **kwargs: Any) -> List[IngestionResult]:
        """Fetch a single URL.

        *query* **is** the URL to fetch.  Returns a list containing
        exactly one ``IngestionResult``, or an empty list on failure.
        """
        url = query.strip()
        if not url:
            return []

        result = self._fetch_url(url)
        return [result] if result is not None else []

    def fetch_by_id(self, identifier: str) -> Optional[IngestionResult]:
        """Fetch a single web page by URL (same semantics as ``fetch``)."""
        url = identifier.strip()
        if not url:
            return None
        return self._fetch_url(url)

    def health_check(self) -> bool:
        """Return ``True`` -- no persistent connection to validate."""
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_url(self, url: str) -> Optional[IngestionResult]:
        """Download *url* and convert to an ``IngestionResult``."""
        req = urllib.request.Request(
            url, headers={"User-Agent": self._user_agent}
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                content_type = resp.headers.get("Content-Type", "")
                raw_bytes = resp.read(self._max_content_length)
                final_url = resp.url  # follows redirects
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            logger.warning("WebPage HTTP error for %s: %s", url, exc)
            return None
        except Exception:
            logger.exception("Unexpected error fetching %s", url)
            return None

        # Decode
        encoding = self._detect_encoding(content_type)
        try:
            text = raw_bytes.decode(encoding, errors="replace")
        except (LookupError, UnicodeDecodeError):
            text = raw_bytes.decode("utf-8", errors="replace")

        # Determine content flavour
        parsed = urllib.parse.urlparse(url)
        path_lower = parsed.path.lower()
        is_markdown = path_lower.endswith(".md")
        is_html = (
            "text/html" in content_type.lower()
            or text.strip()[:100].lower().startswith(("<!doctype", "<html"))
        )

        if is_markdown:
            # Markdown files: use content directly
            title = self._extract_markdown_title(text, url)
            readable = text
        elif is_html:
            title = self._extract_title(text) or self._title_from_url(url)
            readable = self._extract_readable(text)
        else:
            # Plain text
            title = self._title_from_url(url)
            readable = text

        timestamp = datetime.now(tz=timezone.utc).isoformat()

        return IngestionResult(
            source_type=SourceType.WEB_PAGE,
            raw_content=readable,
            title=title,
            authors=[],
            url=final_url or url,
            timestamp=timestamp,
            identifiers={"url": url},
            tags=self._derive_tags(url),
            metadata={
                "content_type": content_type,
                "content_length": len(raw_bytes),
                "is_markdown": is_markdown,
                "is_html": is_html,
            },
            summary=readable[:500],
        )

    # ------------------------------------------------------------------
    # Readability extraction
    # ------------------------------------------------------------------

    @classmethod
    def _extract_readable(cls, html: str) -> str:
        """Strip HTML and extract readable text content.

        Prioritises content within ``<article>`` or ``<main>`` tags.
        Falls back to concatenating all ``<p>`` tag content.  If neither
        is found, strips all tags from the full document.
        """
        # Try article/main blocks first
        article_matches = _ARTICLE_RE.findall(html)
        if article_matches:
            combined = "\n\n".join(article_matches)
            return cls._clean_html(combined)

        # Fall back to paragraphs
        paragraphs = _PARAGRAPH_RE.findall(html)
        if paragraphs:
            combined = "\n\n".join(paragraphs)
            return cls._clean_html(combined)

        # Last resort: strip everything
        return cls._clean_html(html)

    @classmethod
    def _clean_html(cls, html: str) -> str:
        """Remove HTML tags, decode entities, and normalise whitespace."""
        text = _TAG_RE.sub("", html)
        text = cls._decode_entities(text)
        text = _WHITESPACE_RE.sub("\n\n", text)
        return text.strip()

    @staticmethod
    def _decode_entities(text: str) -> str:
        """Replace common HTML entities with their characters."""
        for entity, char in _ENTITY_MAP.items():
            text = text.replace(entity, char)
        # Numeric entities: &#123; and &#x1a;
        text = re.sub(
            r"&#(\d+);",
            lambda m: chr(int(m.group(1))) if int(m.group(1)) < 0x110000 else "",
            text,
        )
        text = re.sub(
            r"&#x([0-9a-fA-F]+);",
            lambda m: chr(int(m.group(1), 16)) if int(m.group(1), 16) < 0x110000 else "",
            text,
        )
        return text

    @staticmethod
    def _extract_title(html: str) -> str:
        """Extract the ``<title>`` from HTML, or return empty string."""
        match = _TITLE_RE.search(html)
        if match:
            title = _TAG_RE.sub("", match.group(1)).strip()
            return title
        return ""

    @staticmethod
    def _extract_markdown_title(text: str, url: str) -> str:
        """Extract a title from Markdown content.

        Looks for a leading ``# Title`` heading.  Falls back to the
        filename from the URL.
        """
        for line in text.splitlines()[:20]:
            stripped = line.strip()
            if stripped.startswith("# ") and len(stripped) > 2:
                return stripped[2:].strip()
        # Fall back to filename
        parsed = urllib.parse.urlparse(url)
        filename = parsed.path.rsplit("/", 1)[-1]
        if filename:
            return filename.replace("-", " ").replace("_", " ").rsplit(".", 1)[0]
        return url

    @staticmethod
    def _title_from_url(url: str) -> str:
        """Derive a human-readable title from a URL path."""
        parsed = urllib.parse.urlparse(url)
        path = urllib.parse.unquote(parsed.path).strip("/")
        if path:
            segment = path.rsplit("/", 1)[-1]
            return segment.replace("-", " ").replace("_", " ").rsplit(".", 1)[0]
        return parsed.netloc or url

    @staticmethod
    def _derive_tags(url: str) -> List[str]:
        """Generate tags from the URL domain."""
        parsed = urllib.parse.urlparse(url)
        tags: List[str] = []
        if parsed.netloc:
            tags.append(parsed.netloc)
        return tags

    @staticmethod
    def _detect_encoding(content_type: str) -> str:
        """Extract charset from Content-Type header, defaulting to utf-8."""
        if "charset=" in content_type.lower():
            parts = content_type.lower().split("charset=")
            if len(parts) > 1:
                charset = parts[1].split(";")[0].strip()
                return charset
        return "utf-8"
