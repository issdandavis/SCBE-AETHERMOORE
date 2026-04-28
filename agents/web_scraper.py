"""
Governed web scraper built on PlaywrightRuntime.

Extracts structured data from web pages: text, links, tables, metadata,
forms, images, and JSON-LD. All extraction runs through the SCBE zone
gate system — RED-zone sites require approval before scraping.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

logger = logging.getLogger("scbe.agents.web_scraper")

# JS snippets injected into pages for extraction
_EXTRACT_TEXT = """() => {
    const sel = window.getSelection();
    sel.removeAllRanges();
    const body = document.body.cloneNode(true);
    body.querySelectorAll('script,style,noscript,svg,nav,footer,header,[aria-hidden=true]').forEach(e => e.remove());
    return body.innerText.replace(/\\n{3,}/g, '\\n\\n').trim();
}"""

_EXTRACT_LINKS = """() => {
    return Array.from(document.querySelectorAll('a[href]')).map(a => ({
        text: a.innerText.trim().substring(0, 200),
        href: a.href,
        rel: a.rel || '',
        is_external: a.hostname !== location.hostname
    })).filter(l => l.href.startsWith('http'));
}"""

_EXTRACT_META = """() => {
    const get = (name) => {
        const el = document.querySelector(`meta[name="${name}"],meta[property="${name}"]`);
        return el ? el.content : null;
    };
    const jsonld = Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
        .map(s => { try { return JSON.parse(s.textContent); } catch { return null; } })
        .filter(Boolean);
    return {
        title: document.title,
        description: get('description') || get('og:description'),
        author: get('author') || get('article:author'),
        published: get('article:published_time') || get('date'),
        canonical: (document.querySelector('link[rel="canonical"]') || {}).href || null,
        og_image: get('og:image'),
        og_type: get('og:type'),
        language: document.documentElement.lang || null,
        jsonld: jsonld,
        word_count: document.body.innerText.split(/\\s+/).length
    };
}"""

_EXTRACT_TABLES = """() => {
    return Array.from(document.querySelectorAll('table')).slice(0, 10).map(table => {
        const headers = Array.from(table.querySelectorAll('th')).map(th => th.innerText.trim());
        const rows = Array.from(table.querySelectorAll('tbody tr, tr')).slice(0, 100).map(tr =>
            Array.from(tr.querySelectorAll('td,th')).map(td => td.innerText.trim())
        );
        return { headers, rows: rows.filter(r => r.length > 0), row_count: rows.length };
    });
}"""

_EXTRACT_IMAGES = """() => {
    return Array.from(document.querySelectorAll('img[src]')).slice(0, 50).map(img => ({
        src: img.src,
        alt: img.alt || '',
        width: img.naturalWidth,
        height: img.naturalHeight
    })).filter(i => i.width > 50 && i.height > 50);
}"""

_EXTRACT_HEADINGS = """() => {
    const headings = Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6')).map(h => ({
        level: parseInt(h.tagName[1]),
        text: h.innerText.trim().substring(0, 200)
    })).filter(h => h.text);
    if (headings.length) return headings;
    const fallbacks = Array.from(document.querySelectorAll('.titleline a, .athing .title a, article a, main a'))
        .map(a => (a.innerText || '').trim())
        .filter(Boolean)
        .slice(0, 10);
    return fallbacks.map(text => ({ level: 2, text: text.substring(0, 200), source: 'fallback-selector' }));
}"""


@dataclass
class PageData:
    """Structured extraction from a single page."""

    url: str
    title: str = ""
    text: str = ""
    word_count: int = 0
    description: str = ""
    author: str = ""
    published: str = ""
    language: str = ""
    canonical: str = ""
    og_image: str = ""
    headings: List[Dict[str, Any]] = field(default_factory=list)
    links: List[Dict[str, Any]] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    jsonld: List[Dict[str, Any]] = field(default_factory=list)
    forms: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def summary(self, max_text: int = 500) -> Dict[str, Any]:
        """Compact summary for LLM consumption."""
        return {
            "url": self.url,
            "title": self.title,
            "description": self.description,
            "word_count": self.word_count,
            "headings": self.headings[:10],
            "link_count": len(self.links),
            "table_count": len(self.tables),
            "text_preview": self.text[:max_text] + ("..." if len(self.text) > max_text else ""),
        }


class WebScraper:
    """
    Governed web scraper. Wraps PlaywrightRuntime for structured extraction.

    Usage:
        from agents.playwright_runtime import PlaywrightRuntime
        from agents.web_scraper import WebScraper

        rt = PlaywrightRuntime()
        await rt.launch(headless=True)
        scraper = WebScraper(rt)

        page = await scraper.scrape("https://example.com")
        print(page.title, page.word_count)
        print(page.text[:500])

        # Multi-page
        pages = await scraper.scrape_many([
            "https://example.com",
            "https://example.org",
        ])

        await rt.close()
    """

    def __init__(self, runtime, *, timeout: int = 30_000) -> None:
        self.runtime = runtime
        self.timeout = timeout
        self._history: List[str] = []

    async def scrape(
        self,
        url: str,
        *,
        extract_text: bool = True,
        extract_links: bool = True,
        extract_tables: bool = True,
        extract_images: bool = False,
        extract_headings: bool = True,
        wait_selector: Optional[str] = None,
    ) -> PageData:
        """
        Navigate to URL and extract structured data.

        Returns PageData with text, links, tables, metadata, etc.
        """
        page = PageData(url=url)
        try:
            await self.runtime.navigate(url, timeout=self.timeout)
            self._history.append(url)

            if wait_selector:
                await self.runtime.wait_for_selector(wait_selector, timeout=self.timeout)

            # Metadata (always extracted)
            meta = await self.runtime.evaluate(_EXTRACT_META)
            page.title = meta.get("title", "")
            page.description = meta.get("description") or ""
            page.author = meta.get("author") or ""
            page.published = meta.get("published") or ""
            page.canonical = meta.get("canonical") or ""
            page.og_image = meta.get("og_image") or ""
            page.language = meta.get("language") or ""
            page.word_count = meta.get("word_count", 0)
            page.jsonld = meta.get("jsonld", [])

            if extract_text:
                page.text = await self.runtime.evaluate(_EXTRACT_TEXT)
                page.word_count = len(page.text.split())

            if extract_headings:
                page.headings = await self.runtime.evaluate(_EXTRACT_HEADINGS)
                if not page.description and page.headings:
                    page.description = page.headings[0].get("text", "")

            if extract_links:
                page.links = await self.runtime.evaluate(_EXTRACT_LINKS)

            if extract_tables:
                page.tables = await self.runtime.evaluate(_EXTRACT_TABLES)

            if extract_images:
                page.images = await self.runtime.evaluate(_EXTRACT_IMAGES)

        except Exception as exc:
            page.error = str(exc)
            logger.warning("Scrape failed for %s: %s", url, exc)

        return page

    async def scrape_many(
        self,
        urls: List[str],
        *,
        extract_text: bool = True,
        extract_links: bool = True,
        delay_ms: int = 500,
    ) -> List[PageData]:
        """Scrape multiple URLs sequentially with optional delay."""
        results = []
        for url in urls:
            page = await self.scrape(
                url,
                extract_text=extract_text,
                extract_links=extract_links,
            )
            results.append(page)
            if delay_ms > 0 and url != urls[-1]:
                await asyncio.sleep(delay_ms / 1000)
        return results

    async def search_and_scrape(
        self,
        query: str,
        *,
        engine: str = "duckduckgo",
        max_results: int = 5,
    ) -> List[PageData]:
        """
        Search the web and scrape top results.

        Uses DuckDuckGo Instant Answer API (JSON, no browser needed) for
        URL discovery, then Playwright for scraping the actual pages.
        Falls back to DDG HTML if the API returns no results.
        """
        result_links = await self._search_urls(query, engine, max_results)
        logger.info("Search '%s' found %d result URLs", query, len(result_links))
        return await self.scrape_many(result_links, delay_ms=800)

    async def _search_urls(self, query: str, engine: str, max_results: int) -> List[str]:
        """
        Get search result URLs via direct HTTP (no browser needed for search).

        Uses DuckDuckGo Instant Answer API + HTML scrape as fallback.
        The browser is only used later to scrape the actual result pages.
        """
        import urllib.request as _req
        from urllib.parse import quote_plus
        import json as _json

        urls: List[str] = []
        headers = {"User-Agent": "SCBE-AetherBrowser/1.0 (research agent)"}

        # Method 1: DuckDuckGo Instant Answer API (JSON, zero auth, no browser)
        try:
            api_url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
            http_req = _req.Request(api_url, headers=headers)
            with _req.urlopen(http_req, timeout=10) as resp:
                data = _json.loads(resp.read())

            if data.get("AbstractURL"):
                urls.append(data["AbstractURL"])
            for topic in data.get("RelatedTopics", []):
                if isinstance(topic, dict) and topic.get("FirstURL"):
                    first = topic["FirstURL"]
                    # Skip DDG internal category links
                    if not first.startswith("https://duckduckgo.com/c/"):
                        urls.append(first)
                if isinstance(topic, dict) and "Topics" in topic:
                    for sub in topic["Topics"]:
                        if isinstance(sub, dict) and sub.get("FirstURL"):
                            first = sub["FirstURL"]
                            if not first.startswith("https://duckduckgo.com/c/"):
                                urls.append(first)
            for r in data.get("Results", []):
                if isinstance(r, dict) and r.get("FirstURL"):
                    urls.append(r["FirstURL"])
        except Exception as exc:
            logger.debug("DDG API failed: %s", exc)

        # Method 2: DDG HTML via urllib (parse the HTML directly)
        if len(urls) < max_results:
            try:
                html_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
                http_req = _req.Request(html_url, headers=headers)
                with _req.urlopen(http_req, timeout=10) as resp:
                    html = resp.read().decode("utf-8", errors="replace")
                # Extract result URLs from href attributes
                import re as _re

                for match in _re.finditer(r'class="result__a"[^>]*href="([^"]+)"', html):
                    href = match.group(1)
                    if href.startswith("http") and "duckduckgo.com" not in href:
                        if href not in urls:
                            urls.append(href)
                # Also try uddg= parameter (DDG redirect URLs)
                for match in _re.finditer(r'uddg=([^&"]+)', html):
                    from urllib.parse import unquote

                    href = unquote(match.group(1))
                    if href.startswith("http") and "duckduckgo.com" not in href:
                        if href not in urls:
                            urls.append(href)
            except Exception as exc:
                logger.debug("DDG HTML fallback failed: %s", exc)

        # Deduplicate and limit
        seen = set()
        unique = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                unique.append(u)
        return unique[:max_results]

    async def extract_article(self, url: str) -> Dict[str, Any]:
        """
        Extract article content with readability heuristics.
        Returns title, author, date, body text, and estimated read time.
        """
        page = await self.scrape(url, extract_text=True, extract_images=True)
        if page.error:
            return {"error": page.error, "url": url}

        # Estimate read time (250 wpm average)
        read_minutes = max(1, page.word_count // 250)

        return {
            "url": page.canonical or page.url,
            "title": page.title,
            "author": page.author,
            "published": page.published,
            "language": page.language,
            "word_count": page.word_count,
            "read_time_minutes": read_minutes,
            "description": page.description,
            "text": page.text,
            "headings": page.headings,
            "images": [img for img in page.images[:5]],
            "jsonld": page.jsonld,
        }

    @property
    def history(self) -> List[str]:
        return list(self._history)
