"""
Browser Toolkit — Lightweight HTTP Utilities for HYDRA
=======================================================

Provides simple, httpx-based utilities that do NOT require Playwright.
Use these for quick tasks where a full HydraHand squad is overkill:

    - search()       — Google/DuckDuckGo search with parsed results
    - diff()         — Monitor a page for changes over time
    - extract()      — Regex-based structured data extraction
    - needs_js()     — Detect if a page requires a JS runtime

All functions use httpx (async HTTP/2 client) and return clean
dataclasses.  No Playwright, no browser launch overhead.

Usage:
    from src.browser.toolkit import search, diff, extract, needs_js

    results = await search("SCBE hyperbolic security")
    changes = await diff("https://example.com/status", interval=30)
    prices  = await extract("https://shop.example.com", "price")
    heavy   = await needs_js("https://spa-app.example.com")

Layer compliance:
    L8  — Governance-safe: no credential handling, no downloads
    L13 — Informational only; no mutation actions

@module browser/toolkit
@layer Layer 8, Layer 13
@component Browser Toolkit
"""

from __future__ import annotations

from html.parser import HTMLParser
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Set
from urllib.parse import quote_plus, urljoin, urlparse

import httpx

logger = logging.getLogger("browser-toolkit")

# ── Constants ────────────────────────────────────────────────────────

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

DEFAULT_TIMEOUT = 15.0  # seconds


class _VisibleTextParser(HTMLParser):
    """Extract visible text while ignoring script/style blocks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        if tag.lower() in {"script", "style"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
        if tag.lower() in {"script", "style"} and self._ignored_depth > 0:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        if not self._ignored_depth and data:
            self._chunks.append(data)

    def text(self) -> str:
        return " ".join(self._chunks)


# ── Data Classes ─────────────────────────────────────────────────────


@dataclass
class SearchResult:
    """A single search engine result."""

    title: str
    url: str
    snippet: str
    source: str = "google"  # "google" or "duckduckgo"


@dataclass
class PageDiff:
    """Changes detected between two fetches of the same URL."""

    url: str
    interval_seconds: float
    added_links: List[str] = field(default_factory=list)
    removed_links: List[str] = field(default_factory=list)
    text_changed: bool = False
    old_length: int = 0
    new_length: int = 0
    diff_summary: str = ""
    elapsed_ms: float = 0.0


@dataclass
class ExtractedItem:
    """A single extracted data point from a page."""

    pattern_name: str
    value: str
    context: str = ""  # surrounding text for reference


@dataclass
class JSDetectionResult:
    """Result of JavaScript dependency detection."""

    url: str
    needs_js: bool
    reason: str
    content_length: int = 0
    script_count: int = 0
    noscript_present: bool = False
    meta_redirect: bool = False
    body_text_length: int = 0
    elapsed_ms: float = 0.0


# ── Extraction Patterns ──────────────────────────────────────────────

BUILTIN_PATTERNS: Dict[str, str] = {
    "email": r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    "price": r"\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?",
    "date": r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b",
    "phone": r"\+?1?\s?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}",
    "url": r"https?://[^\s\"'<>]+",
    "ipv4": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
}


# ── Internal Helpers ─────────────────────────────────────────────────


def _build_client(**kwargs) -> httpx.AsyncClient:
    """Create an httpx client with sane defaults."""
    defaults = {
        "headers": DEFAULT_HEADERS,
        "timeout": DEFAULT_TIMEOUT,
        "follow_redirects": True,
    }
    defaults.update(kwargs)
    return httpx.AsyncClient(**defaults)


def _hostname_matches(url: str, domain: str) -> bool:
    try:
        hostname = (urlparse(url).hostname or "").lower().rstrip(".")
    except ValueError:
        return False
    normalized = domain.lower().rstrip(".")
    return hostname == normalized or hostname.endswith(f".{normalized}")


def _extract_text_from_html(html: str) -> str:
    """Crude text extraction using an HTML parser instead of regex stripping."""
    parser = _VisibleTextParser()
    parser.feed(html)
    parser.close()
    return re.sub(r"\s+", " ", parser.text()).strip()


def _extract_links_from_html(html: str, base_url: str) -> Set[str]:
    """Pull all href values from anchor tags."""
    links: Set[str] = set()
    for match in re.finditer(r'<a\s[^>]*href=["\']([^"\']+)["\']', html, re.IGNORECASE):
        href = match.group(1).strip()
        if href.startswith(("http://", "https://")):
            links.add(href)
        elif href.startswith("/"):
            links.add(urljoin(base_url, href))
    return links


# ── 1. Google Search ─────────────────────────────────────────────────


def _parse_google_results(html: str) -> List[SearchResult]:
    """Parse Google search HTML into SearchResult list.

    Google's HTML structure changes frequently.  We look for common
    patterns: <a href="..."><h3>Title</h3></a> followed by snippet divs.
    """
    results: List[SearchResult] = []

    # Pattern: links that look like organic results (not google internal)
    # Google wraps results in <a href="/url?q=ACTUAL_URL&..."> or direct links
    link_pattern = re.compile(
        r'<a\s[^>]*href="(/url\?q=([^"&]+)&[^"]*|https?://(?!www\.google\.com)[^"]+)"[^>]*>' r".*?<h3[^>]*>(.*?)</h3>",
        re.DOTALL | re.IGNORECASE,
    )

    for match in link_pattern.finditer(html):
        raw_href = match.group(1)
        title_html = match.group(3) if match.group(3) else ""

        # Resolve /url?q= redirect
        if raw_href.startswith("/url?q="):
            url = match.group(2)
        else:
            url = raw_href

        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or _hostname_matches(url, "google.com"):
            continue

        title = _extract_text_from_html(title_html).strip()
        if not title:
            continue

        # Try to find a snippet near this result
        snippet = ""
        # Look for text in the next few hundred chars after the match
        after = html[match.end() : match.end() + 500]
        # Snippet is often in a <span> or <div> after the link
        snippet_match = re.search(
            r'<(?:span|div)[^>]*class="[^"]*"[^>]*>(.*?)</(?:span|div)>',
            after,
            re.DOTALL,
        )
        if snippet_match:
            snippet = _extract_text_from_html(snippet_match.group(1)).strip()

        results.append(
            SearchResult(
                title=title,
                url=url,
                snippet=snippet[:300],
                source="google",
            )
        )

    return results


def _parse_duckduckgo_results(html: str) -> List[SearchResult]:
    """Parse DuckDuckGo HTML results page."""
    results: List[SearchResult] = []

    # DDG result links are in <a class="result__a" href="...">Title</a>
    # with snippets in <a class="result__snippet" ...>...</a>
    result_pattern = re.compile(
        r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )

    for match in result_pattern.finditer(html):
        url = match.group(1).strip()
        title_html = match.group(2)
        title = _extract_text_from_html(title_html).strip()

        if not url.startswith("http") or not title:
            continue

        # Look for snippet
        snippet = ""
        after = html[match.end() : match.end() + 500]
        snippet_match = re.search(
            r'<a[^>]*class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>',
            after,
            re.DOTALL | re.IGNORECASE,
        )
        if snippet_match:
            snippet = _extract_text_from_html(snippet_match.group(1)).strip()

        results.append(
            SearchResult(
                title=title,
                url=url,
                snippet=snippet[:300],
                source="duckduckgo",
            )
        )

    return results


async def search(
    query: str,
    num_results: int = 10,
    timeout: float = DEFAULT_TIMEOUT,
) -> List[SearchResult]:
    """Search Google (with DuckDuckGo fallback) and return parsed results.

    Args:
        query: The search query string.
        num_results: Maximum number of results to return.
        timeout: HTTP timeout in seconds.

    Returns:
        List of SearchResult dataclasses with title, url, snippet.
        Falls back to DuckDuckGo if Google returns no results or errors.
    """
    results: List[SearchResult] = []

    # ── Try Google first ──────────────────────────────────────────
    google_url = f"https://www.google.com/search?q={quote_plus(query)}&num={num_results}"
    try:
        async with _build_client(timeout=timeout) as client:
            resp = await client.get(google_url)
            if resp.status_code == 200:
                results = _parse_google_results(resp.text)
    except Exception as exc:
        logger.debug("Google search failed: %s", exc)

    if results:
        return results[:num_results]

    # ── Fallback: DuckDuckGo ──────────────────────────────────────
    ddg_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    try:
        async with _build_client(timeout=timeout) as client:
            resp = await client.get(ddg_url)
            if resp.status_code == 200:
                results = _parse_duckduckgo_results(resp.text)
    except Exception as exc:
        logger.warning("DuckDuckGo search also failed: %s", exc)

    return results[:num_results]


# ── 2. Page Diff ─────────────────────────────────────────────────────


async def diff(
    url: str,
    interval: float = 60.0,
    timeout: float = DEFAULT_TIMEOUT,
) -> PageDiff:
    """Fetch a page twice with a delay and report what changed.

    Args:
        url: The URL to monitor.
        interval: Seconds to wait between the two fetches.
        timeout: HTTP timeout in seconds per fetch.

    Returns:
        PageDiff with added/removed links, text change flag, and summary.
    """
    start = time.monotonic()
    result = PageDiff(url=url, interval_seconds=interval)

    async with _build_client(timeout=timeout) as client:
        # First fetch
        try:
            resp1 = await client.get(url)
            html1 = resp1.text
        except Exception as exc:
            result.diff_summary = f"First fetch failed: {exc}"
            result.elapsed_ms = (time.monotonic() - start) * 1000
            return result

        # Wait
        import asyncio

        await asyncio.sleep(interval)

        # Second fetch
        try:
            resp2 = await client.get(url)
            html2 = resp2.text
        except Exception as exc:
            result.diff_summary = f"Second fetch failed: {exc}"
            result.elapsed_ms = (time.monotonic() - start) * 1000
            return result

    # Compare links
    links1 = _extract_links_from_html(html1, url)
    links2 = _extract_links_from_html(html2, url)
    result.added_links = sorted(links2 - links1)
    result.removed_links = sorted(links1 - links2)

    # Compare text
    text1 = _extract_text_from_html(html1)
    text2 = _extract_text_from_html(html2)
    result.old_length = len(text1)
    result.new_length = len(text2)
    result.text_changed = text1 != text2

    # Build summary
    changes: List[str] = []
    if result.added_links:
        changes.append(f"+{len(result.added_links)} links")
    if result.removed_links:
        changes.append(f"-{len(result.removed_links)} links")
    if result.text_changed:
        delta = result.new_length - result.old_length
        sign = "+" if delta >= 0 else ""
        changes.append(f"text changed ({sign}{delta} chars)")
    result.diff_summary = "; ".join(changes) if changes else "no changes detected"

    result.elapsed_ms = (time.monotonic() - start) * 1000
    return result


# ── 3. Smart Extract ─────────────────────────────────────────────────


async def extract(
    url: str,
    pattern: str,
    timeout: float = DEFAULT_TIMEOUT,
    context_chars: int = 40,
) -> List[ExtractedItem]:
    """Fetch a page and extract structured data matching a pattern.

    Args:
        url: Page to fetch and extract from.
        pattern: Either a builtin pattern name (email, price, date,
                 phone, url, ipv4) or a raw regex string.
        timeout: HTTP timeout in seconds.
        context_chars: Number of surrounding characters to include.

    Returns:
        List of ExtractedItem with matched values and surrounding context.
    """
    # Resolve builtin pattern or use raw regex
    regex_str = BUILTIN_PATTERNS.get(pattern, pattern)
    try:
        regex = re.compile(regex_str)
    except re.error as exc:
        logger.error("Invalid regex pattern %r: %s", pattern, exc)
        return []

    pattern_name = pattern if pattern in BUILTIN_PATTERNS else "custom"

    async with _build_client(timeout=timeout) as client:
        try:
            resp = await client.get(url)
            html = resp.text
        except Exception as exc:
            logger.warning("Extract fetch failed for %s: %s", url, exc)
            return []

    # Extract from raw HTML (captures values inside tags/attributes too)
    text = _extract_text_from_html(html)

    items: List[ExtractedItem] = []
    seen: Set[str] = set()

    for match in regex.finditer(text):
        value = match.group(0)
        if value in seen:
            continue
        seen.add(value)

        # Surrounding context
        start = max(0, match.start() - context_chars)
        end = min(len(text), match.end() + context_chars)
        context = text[start:end].strip()

        items.append(
            ExtractedItem(
                pattern_name=pattern_name,
                value=value,
                context=context,
            )
        )

    return items


# ── 4. JavaScript Detection ─────────────────────────────────────────


async def needs_js(
    url: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> JSDetectionResult:
    """Detect whether a page likely requires JavaScript to render content.

    Heuristics:
        1. Very little visible text but many <script> tags
        2. Presence of JS framework root markers (id="root", id="app", id="__next")
        3. <noscript> tags with content warnings
        4. Meta refresh / JS redirect patterns

    Args:
        url: The URL to check.
        timeout: HTTP timeout in seconds.

    Returns:
        JSDetectionResult with needs_js bool and reasoning.
    """
    start = time.monotonic()

    async with _build_client(timeout=timeout) as client:
        try:
            resp = await client.get(url)
            html = resp.text
        except Exception as exc:
            return JSDetectionResult(
                url=url,
                needs_js=False,
                reason=f"Fetch failed: {exc}",
                elapsed_ms=(time.monotonic() - start) * 1000,
            )

    content_length = len(html)

    # Count <script> tags
    script_count = len(re.findall(r"<script[\s>]", html, re.IGNORECASE))

    # Check <noscript> presence with meaningful content
    noscript_match = re.search(r"<noscript[^>]*>(.*?)</noscript>", html, re.DOTALL | re.IGNORECASE)
    noscript_present = False
    if noscript_match:
        noscript_text = noscript_match.group(1).strip()
        # Only count it if it has real content (not just a tracking pixel)
        if len(noscript_text) > 20 and "<img" not in noscript_text.lower():
            noscript_present = True

    # Check for meta redirect
    meta_redirect = bool(
        re.search(
            r'<meta[^>]*http-equiv=["\']refresh["\'][^>]*>',
            html,
            re.IGNORECASE,
        )
    )

    # Extract body text
    body_match = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
    body_html = body_match.group(1) if body_match else html
    body_text = _extract_text_from_html(body_html)
    body_text_length = len(body_text)

    # Check for SPA framework root markers
    spa_markers = re.findall(
        r'id=["\'](?:root|app|__next|__nuxt|__svelte)["\']',
        html,
        re.IGNORECASE,
    )

    # ── Decision logic ──────────────────────────────────────────
    reasons: List[str] = []
    js_score = 0

    # Heuristic 1: Lots of scripts, little text
    if script_count >= 5 and body_text_length < 200:
        reasons.append(f"{script_count} scripts but only {body_text_length} chars of body text")
        js_score += 3

    # Heuristic 2: SPA framework markers
    if spa_markers:
        reasons.append(f"SPA root marker found: {spa_markers[0]}")
        js_score += 2

    # Heuristic 3: noscript warning
    if noscript_present:
        reasons.append("meaningful <noscript> content present")
        js_score += 2

    # Heuristic 4: meta redirect (often used with JS redirect)
    if meta_redirect:
        reasons.append("meta refresh redirect detected")
        js_score += 1

    # Heuristic 5: Very short body relative to total HTML
    if content_length > 1000 and body_text_length < 100:
        reasons.append(f"HTML is {content_length} bytes but body text is only {body_text_length} chars")
        js_score += 2

    needs_javascript = js_score >= 3
    reason = "; ".join(reasons) if reasons else "page appears to render without JS"

    return JSDetectionResult(
        url=url,
        needs_js=needs_javascript,
        reason=reason,
        content_length=content_length,
        script_count=script_count,
        noscript_present=noscript_present,
        meta_redirect=meta_redirect,
        body_text_length=body_text_length,
        elapsed_ms=(time.monotonic() - start) * 1000,
    )
