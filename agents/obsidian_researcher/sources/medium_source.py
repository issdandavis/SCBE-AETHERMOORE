"""Medium source adapter for the Obsidian researcher agent.

Medium has no public read API. This adapter uses two access methods:

1. **RSS Feed** — ``https://medium.com/feed/@username`` returns the last
   10 articles as Atom/RSS XML. Free, no auth, rate-limited by Medium CDN.
2. **rss2json** — Optional JSON proxy that converts RSS to JSON for easier
   parsing. Free tier: 10K req/day. ``https://api.rss2json.com/v1/api.json``

Limitations:
- RSS feed only returns the **last 10 articles** per user/publication.
- No full-text access via RSS (truncated HTML content).
- No search endpoint — can only pull by username or publication slug.

For writing/publishing to Medium, use the official Medium API with an
integration token (not implemented here — use the content publisher skill).

@layer Layer 1 (identity), Layer 14 (telemetry)
@component ResearchPipeline.Medium
"""

from __future__ import annotations

import html
import logging
import os
import re
import json
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..source_adapter import IngestionResult, SourceAdapter, SourceType

logger = logging.getLogger(__name__)

_MEDIUM_FEED_BASE = "https://medium.com/feed"
_RSS2JSON_API = "https://api.rss2json.com/v1/api.json"
_USER_AGENT = "SCBE-AETHERMOORE/1.0 (research)"
_DEFAULT_TIMEOUT = 15

# HTML tag stripping
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


class MediumSource(SourceAdapter):
    """Adapter that reads Medium articles via RSS feed.

    Parameters
    ----------
    config : dict
        Optional keys:

        * ``username``     -- Medium username (default: env MEDIUM_USERNAME)
        * ``publication``  -- Medium publication slug (optional)
        * ``timeout``      -- HTTP timeout in seconds (default 15)
        * ``use_rss2json`` -- Use rss2json API for JSON output (default True)
        * ``rss2json_key`` -- API key for rss2json (optional, for higher limits)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(source_type=SourceType.WEB, config=config or {})
        self._username: str = self.config.get(
            "username",
            os.environ.get("MEDIUM_USERNAME", ""),
        )
        self._publication: str = self.config.get("publication", "")
        self._timeout: int = int(self.config.get("timeout", _DEFAULT_TIMEOUT))
        self._use_rss2json: bool = self.config.get("use_rss2json", True)
        self._rss2json_key: str = self.config.get(
            "rss2json_key",
            os.environ.get("RSS2JSON_API_KEY", ""),
        )

    def _get_feed_url(self, username: Optional[str] = None) -> str:
        """Build the Medium RSS feed URL."""
        user = username or self._username
        if self._publication:
            return f"{_MEDIUM_FEED_BASE}/{self._publication}"
        if user:
            # Ensure @ prefix
            if not user.startswith("@"):
                user = f"@{user}"
            return f"{_MEDIUM_FEED_BASE}/{user}"
        return ""

    def _fetch_raw(self, url: str) -> Optional[bytes]:
        """Fetch raw bytes from a URL."""
        headers = {"User-Agent": _USER_AGENT}
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            logger.warning("Medium HTTP error for %s: %s", url, exc)
            return None
        except Exception:
            logger.exception("Medium unexpected error for %s", url)
            return None

    def _fetch_via_rss2json(self, feed_url: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch feed via rss2json API (returns JSON)."""
        params: Dict[str, str] = {"rss_url": feed_url}
        if self._rss2json_key:
            params["api_key"] = self._rss2json_key

        url = f"{_RSS2JSON_API}?{urllib.parse.urlencode(params)}"
        raw = self._fetch_raw(url)
        if not raw:
            return None

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Medium rss2json response not valid JSON")
            return None

        if data.get("status") != "ok":
            logger.warning("Medium rss2json error: %s", data.get("message", "unknown"))
            return None

        return data.get("items", [])

    def _fetch_via_xml(self, feed_url: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch feed directly and parse RSS XML."""
        raw = self._fetch_raw(feed_url)
        if not raw:
            return None

        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            logger.warning("Medium RSS XML parse error")
            return None

        items = []
        # RSS 2.0 format
        for item in root.iter("item"):
            entry: Dict[str, Any] = {}
            title_el = item.find("title")
            entry["title"] = title_el.text if title_el is not None and title_el.text else ""

            link_el = item.find("link")
            entry["link"] = link_el.text if link_el is not None and link_el.text else ""

            # Try dc:creator or author
            creator_el = item.find("{http://purl.org/dc/elements/1.1/}creator")
            if creator_el is not None and creator_el.text:
                entry["author"] = creator_el.text
            else:
                author_el = item.find("author")
                entry["author"] = author_el.text if author_el is not None and author_el.text else ""

            pub_date_el = item.find("pubDate")
            entry["pubDate"] = pub_date_el.text if pub_date_el is not None and pub_date_el.text else ""

            # Content (may be in content:encoded)
            content_el = item.find("{http://purl.org/rss/1.0/modules/content/}encoded")
            if content_el is not None and content_el.text:
                entry["content"] = content_el.text
            else:
                desc_el = item.find("description")
                entry["content"] = desc_el.text if desc_el is not None and desc_el.text else ""

            # Categories/tags
            categories = []
            for cat in item.findall("category"):
                if cat.text:
                    categories.append(cat.text)
            entry["categories"] = categories

            # GUID
            guid_el = item.find("guid")
            entry["guid"] = guid_el.text if guid_el is not None and guid_el.text else ""

            items.append(entry)

        return items

    def fetch_articles(self, username: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch articles from Medium RSS feed.

        Returns list of article dicts with: title, link, author, pubDate,
        content, categories, guid.
        """
        feed_url = self._get_feed_url(username)
        if not feed_url:
            logger.warning("No Medium username or publication configured")
            return []

        if self._use_rss2json:
            items = self._fetch_via_rss2json(feed_url)
            if items is not None:
                return items
            # Fall back to XML
            logger.info("rss2json failed, falling back to XML parsing")

        items = self._fetch_via_xml(feed_url)
        return items or []

    @staticmethod
    def _strip_html(text: str) -> str:
        """Strip HTML tags and decode entities."""
        text = _TAG_RE.sub("", text)
        text = html.unescape(text)
        text = _WHITESPACE_RE.sub(" ", text)
        return text.strip()

    @staticmethod
    def _extract_thumbnail(content_html: str) -> str:
        """Extract first image URL from HTML content."""
        match = re.search(r'<img[^>]+src="([^"]+)"', content_html or "")
        return match.group(1) if match else ""

    @staticmethod
    def _parse_date(date_str: str) -> str:
        """Parse Medium date formats to ISO."""
        if not date_str:
            return ""
        # Try common formats
        for fmt in (
            "%a, %d %b %Y %H:%M:%S %Z",
            "%a, %d %b %Y %H:%M:%S %z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
        ):
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.isoformat()
            except ValueError:
                continue
        return date_str

    def fetch(self, query: str, **kwargs: Any) -> List[IngestionResult]:
        """Fetch articles from Medium, optionally filtered by query.

        Since Medium RSS has no search, this fetches all available articles
        and filters client-side by title/content matching.
        """
        username = kwargs.get("username")
        articles = self.fetch_articles(username)
        results = []
        query_lower = query.lower()

        for article in articles:
            title = article.get("title", "")
            content_html = article.get("content", "") or article.get("description", "")
            content_text = self._strip_html(content_html)

            # Filter by query if provided
            if query_lower:
                searchable = f"{title} {content_text}".lower()
                if query_lower not in searchable:
                    continue

            author = article.get("author", article.get("creator", ""))
            link = article.get("link", article.get("url", ""))
            pub_date = self._parse_date(article.get("pubDate", ""))
            categories = article.get("categories", [])
            guid = article.get("guid", link)
            thumbnail = article.get("thumbnail", "") or self._extract_thumbnail(content_html)

            tags = ["medium"]
            for cat in categories[:10]:
                tags.append(f"tag:{cat}")

            identifiers: Dict[str, str] = {"medium_url": link}
            if guid and guid != link:
                identifiers["medium_guid"] = guid

            results.append(IngestionResult(
                source_type=SourceType.WEB,
                raw_content=content_text[:5000],
                title=title,
                authors=[author] if author else [],
                url=link,
                timestamp=pub_date,
                identifiers=identifiers,
                tags=tags,
                metadata={
                    "categories": categories,
                    "thumbnail": thumbnail,
                    "content_length": len(content_text),
                    "source": "medium",
                    "username": self._username,
                },
                summary=content_text[:500],
            ))

        return results

    def fetch_by_id(self, identifier: str) -> Optional[IngestionResult]:
        """Fetch a specific article by URL.

        Medium RSS doesn't support per-article fetch, so this fetches
        all articles and finds the matching one.
        """
        articles = self.fetch_articles()
        for article in articles:
            link = article.get("link", article.get("url", ""))
            guid = article.get("guid", "")
            if identifier in (link, guid):
                content_html = article.get("content", "")
                content_text = self._strip_html(content_html)
                author = article.get("author", "")
                pub_date = self._parse_date(article.get("pubDate", ""))

                return IngestionResult(
                    source_type=SourceType.WEB,
                    raw_content=content_text,
                    title=article.get("title", ""),
                    authors=[author] if author else [],
                    url=link,
                    timestamp=pub_date,
                    identifiers={"medium_url": link},
                    tags=["medium"] + [f"tag:{c}" for c in article.get("categories", [])],
                    metadata={"source": "medium"},
                    summary=content_text[:500],
                )
        return None

    # ------------------------------------------------------------------
    # Write API (requires integration token)
    # ------------------------------------------------------------------

    def _get_user_id(self) -> Optional[str]:
        """Get the authenticated user's Medium ID."""
        token = self.config.get(
            "integration_token",
            os.environ.get("MEDIUM_INTEGRATION_TOKEN", ""),
        )
        if not token:
            return None

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        req = urllib.request.Request(
            "https://api.medium.com/v1/me",
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read())
                return data.get("data", {}).get("id")
        except Exception as exc:
            logger.warning("Medium user lookup failed: %s", exc)
            return None

    def publish(
        self,
        title: str,
        content: str,
        *,
        content_format: str = "markdown",
        tags: Optional[List[str]] = None,
        publish_status: str = "draft",
        canonical_url: str = "",
        notify_followers: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Publish an article to Medium.

        Requires ``MEDIUM_INTEGRATION_TOKEN`` env var or
        ``integration_token`` in config.

        Parameters
        ----------
        title : str
            Article title.
        content : str
            Article body (markdown or HTML).
        content_format : str
            ``"markdown"`` or ``"html"`` (default: markdown).
        tags : list[str], optional
            Up to 5 tags for the article.
        publish_status : str
            ``"draft"`` (default), ``"public"``, or ``"unlisted"``.
        canonical_url : str
            Original URL if cross-posting.
        notify_followers : bool
            Whether to notify followers (default False).

        Returns
        -------
        dict or None
            Medium API response with article URL, or None on failure.
        """
        token = self.config.get(
            "integration_token",
            os.environ.get("MEDIUM_INTEGRATION_TOKEN", ""),
        )
        if not token:
            logger.error("Medium integration token required for publishing")
            return None

        user_id = self._get_user_id()
        if not user_id:
            logger.error("Could not resolve Medium user ID")
            return None

        payload: Dict[str, Any] = {
            "title": title,
            "contentFormat": content_format,
            "content": content,
            "publishStatus": publish_status,
        }
        if tags:
            payload["tags"] = tags[:5]  # Medium allows max 5 tags
        if canonical_url:
            payload["canonicalUrl"] = canonical_url
        if notify_followers:
            payload["notifyFollowers"] = True

        url = f"https://api.medium.com/v1/users/{user_id}/posts"
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                result = json.loads(resp.read())
                data = result.get("data", {})
                logger.info(
                    "Published to Medium: %s (%s)",
                    data.get("title", ""),
                    data.get("url", ""),
                )
                return data
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            logger.error("Medium publish failed (%d): %s", exc.code, error_body)
            return None
        except Exception as exc:
            logger.exception("Medium publish unexpected error: %s", exc)
            return None

    def health_check(self) -> bool:
        """Verify Medium RSS feed is reachable."""
        feed_url = self._get_feed_url()
        if not feed_url:
            return False
        raw = self._fetch_raw(feed_url)
        return raw is not None and len(raw) > 0
