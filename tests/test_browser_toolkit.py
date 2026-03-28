"""
Tests for src/browser/toolkit.py — Browser Toolkit
====================================================

Unit tests for search, diff, extract, and needs_js functions.
All network calls are mocked with httpx transport mocks — no real
HTTP requests are made.
"""

import re
import sys
from pathlib import Path
from urllib.parse import urlparse
from unittest.mock import patch

import pytest

httpx = pytest.importorskip("httpx", reason="httpx is required for browser toolkit tests")

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.browser.toolkit import (
    BUILTIN_PATTERNS,
    DEFAULT_HEADERS,
    ExtractedItem,
    JSDetectionResult,
    PageDiff,
    SearchResult,
    _extract_links_from_html,
    _extract_text_from_html,
    _parse_duckduckgo_results,
    _parse_google_results,
    diff,
    extract,
    needs_js,
    search,
)

# ── Helpers ──────────────────────────────────────────────────────────


def _has_exact_url(urls: list[str], expected: str) -> bool:
    expected_parts = urlparse(expected)
    expected_host = (expected_parts.hostname or "").lower()
    expected_path = expected_parts.path or ""
    for candidate in urls:
        parts = urlparse(candidate)
        if (
            parts.scheme == expected_parts.scheme
            and (parts.hostname or "").lower() == expected_host
            and (parts.path or "") == expected_path
        ):
            return True
    return False


def _host_has_suffix(url: str, *labels: str) -> bool:
    host = (urlparse(str(url)).hostname or "").strip(".").lower()
    host_labels = [part for part in host.split(".") if part]
    suffix = [part.lower() for part in labels]
    return len(host_labels) >= len(suffix) and host_labels[-len(suffix) :] == suffix


def _make_response(text: str, status_code: int = 200) -> httpx.Response:
    """Create a fake httpx.Response with the given text body."""
    return httpx.Response(
        status_code=status_code,
        text=text,
        request=httpx.Request("GET", "https://example.com"),
    )


class MockTransport(httpx.AsyncBaseTransport):
    """Async transport that returns canned responses for testing."""

    def __init__(self, responses: dict[str, httpx.Response] | None = None, default_text: str = ""):
        self._responses = responses or {}
        self._default_text = default_text
        self.request_log: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.request_log.append(request)
        url_str = str(request.url)
        hostname = (urlparse(url_str).hostname or "").lower().rstrip(".")
        for pattern, response in self._responses.items():
            normalized = str(pattern).lower().rstrip(".")
            if normalized.startswith(("http://", "https://")):
                if url_str.startswith(normalized):
                    return response
                continue
            if hostname == normalized or hostname.endswith(f".{normalized}"):
                return response
        return httpx.Response(
            status_code=200,
            text=self._default_text,
            request=request,
        )


# ── Import / Dataclass Tests ────────────────────────────────────────


class TestImports:
    """Verify module loads and exports all public symbols."""

    def test_import_search(self):
        from src.browser.toolkit import search

        assert callable(search)

    def test_import_diff(self):
        from src.browser.toolkit import diff

        assert callable(diff)

    def test_import_extract(self):
        from src.browser.toolkit import extract

        assert callable(extract)

    def test_import_needs_js(self):
        from src.browser.toolkit import needs_js

        assert callable(needs_js)

    def test_import_dataclasses(self):
        from src.browser.toolkit import (
            SearchResult,
            PageDiff,
            ExtractedItem,
            JSDetectionResult,
        )

        assert SearchResult is not None
        assert PageDiff is not None
        assert ExtractedItem is not None
        assert JSDetectionResult is not None


class TestSearchResultDataclass:
    """Test SearchResult construction and fields."""

    def test_default_source_is_google(self):
        r = SearchResult(title="Test", url="https://x.com", snippet="hello")
        assert r.source == "google"

    def test_custom_source(self):
        r = SearchResult(title="Test", url="https://x.com", snippet="hi", source="duckduckgo")
        assert r.source == "duckduckgo"


class TestPageDiffDataclass:
    def test_defaults(self):
        d = PageDiff(url="https://x.com", interval_seconds=30.0)
        assert d.added_links == []
        assert d.removed_links == []
        assert d.text_changed is False
        assert d.diff_summary == ""


class TestExtractedItemDataclass:
    def test_fields(self):
        item = ExtractedItem(pattern_name="email", value="a@b.com", context="contact a@b.com here")
        assert item.pattern_name == "email"
        assert item.value == "a@b.com"


class TestJSDetectionResultDataclass:
    def test_fields(self):
        r = JSDetectionResult(url="https://x.com", needs_js=True, reason="SPA detected")
        assert r.needs_js is True
        assert r.script_count == 0


# ── Internal Helper Tests ────────────────────────────────────────────


class TestExtractTextFromHtml:
    """Test the crude HTML-to-text extractor."""

    def test_strips_tags(self):
        html = "<p>Hello <b>world</b></p>"
        assert "Hello" in _extract_text_from_html(html)
        assert "world" in _extract_text_from_html(html)
        assert "<" not in _extract_text_from_html(html)

    def test_removes_scripts(self):
        html = '<p>Before</p><script>alert("x")</script><p>After</p>'
        text = _extract_text_from_html(html)
        assert "Before" in text
        assert "After" in text
        assert "alert" not in text

    def test_removes_styles(self):
        html = "<style>body{color:red}</style><p>Content</p>"
        text = _extract_text_from_html(html)
        assert "Content" in text
        assert "color" not in text

    def test_decodes_entities(self):
        html = "<p>A &amp; B &lt; C</p>"
        text = _extract_text_from_html(html)
        assert "A & B < C" in text

    def test_collapses_whitespace(self):
        html = "<p>  Hello   \n\n   world  </p>"
        text = _extract_text_from_html(html)
        assert text == "Hello world"

    def test_empty_html(self):
        assert _extract_text_from_html("") == ""


class TestExtractLinksFromHtml:
    """Test link extraction."""

    def test_absolute_links(self):
        html = '<a href="https://example.com/page">Link</a>'
        links = _extract_links_from_html(html, "https://example.com")
        assert _has_exact_url(links, "https://example.com/page")

    def test_relative_links_resolved(self):
        html = '<a href="/about">About</a>'
        links = _extract_links_from_html(html, "https://example.com")
        assert _has_exact_url(links, "https://example.com/about")

    def test_ignores_fragment_links(self):
        html = '<a href="#section">Jump</a>'
        links = _extract_links_from_html(html, "https://example.com")
        assert len(links) == 0

    def test_multiple_links(self):
        html = """
        <a href="https://a.com">A</a>
        <a href="https://b.com">B</a>
        <a href="/c">C</a>
        """
        links = _extract_links_from_html(html, "https://example.com")
        assert _has_exact_url(links, "https://a.com")
        assert _has_exact_url(links, "https://b.com")
        assert _has_exact_url(links, "https://example.com/c")

    def test_deduplicates(self):
        html = '<a href="https://a.com">1</a><a href="https://a.com">2</a>'
        links = _extract_links_from_html(html, "https://example.com")
        assert len(links) == 1


# ── Google Parser Tests ──────────────────────────────────────────────


class TestParseGoogleResults:
    """Test Google HTML result parsing."""

    def test_parses_results_with_h3(self):
        html = """
        <div>
            <a href="/url?q=https://example.com/page&sa=U">
                <h3>Example Page Title</h3>
            </a>
            <div><span class="snippet">This is the snippet text</span></div>
        </div>
        """
        results = _parse_google_results(html)
        assert len(results) >= 1
        assert results[0].title == "Example Page Title"
        assert results[0].url == "https://example.com/page"
        assert results[0].source == "google"

    def test_skips_google_internal_links(self):
        html = """
        <a href="https://www.google.com/preferences"><h3>Settings</h3></a>
        <a href="/url?q=https://real-site.com&sa=U"><h3>Real Site</h3></a>
        """
        results = _parse_google_results(html)
        urls = [r.url for r in results]
        assert not any(_host_has_suffix(u, "google", "com") for u in urls)

    def test_does_not_reject_non_google_urls_with_google_substring(self):
        html = """
        <a href="/url?q=https://evil.example.com/path/google.com-marker&sa=U">
            <h3>Mirror Result</h3>
        </a>
        """
        results = _parse_google_results(html)
        assert len(results) == 1
        assert results[0].url == "https://evil.example.com/path/google.com-marker"

    def test_empty_html(self):
        assert _parse_google_results("") == []

    def test_no_results(self):
        html = "<html><body><p>No search results found</p></body></html>"
        assert _parse_google_results(html) == []


# ── DuckDuckGo Parser Tests ─────────────────────────────────────────


class TestParseDuckDuckGoResults:
    """Test DuckDuckGo HTML result parsing."""

    def test_parses_ddg_results(self):
        html = """
        <div class="result results_links">
            <a class="result__a" href="https://example.com/ddg">DDG Result Title</a>
            <a class="result__snippet" href="#">This is the DDG snippet</a>
        </div>
        """
        results = _parse_duckduckgo_results(html)
        assert len(results) >= 1
        assert results[0].title == "DDG Result Title"
        assert results[0].url == "https://example.com/ddg"
        assert results[0].source == "duckduckgo"

    def test_empty_html(self):
        assert _parse_duckduckgo_results("") == []

    def test_skips_non_http_links(self):
        html = '<a class="result__a" href="javascript:void(0)">Bad</a>'
        assert _parse_duckduckgo_results(html) == []


# ── Search Function Tests ────────────────────────────────────────────


class TestSearch:
    """Test the search() function with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_search_returns_google_results(self):
        google_html = """
        <a href="/url?q=https://example.com/result1&sa=U">
            <h3>Result One</h3>
        </a>
        <div><span class="st">Snippet one</span></div>
        <a href="/url?q=https://example.com/result2&sa=U">
            <h3>Result Two</h3>
        </a>
        """
        transport = MockTransport(responses={"google.com": _make_response(google_html)})
        with patch("src.browser.toolkit._build_client") as mock_build:
            mock_build.return_value = httpx.AsyncClient(transport=transport)
            results = await search("test query", num_results=5)

        assert len(results) >= 1
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].source == "google"

    @pytest.mark.asyncio
    async def test_search_falls_back_to_duckduckgo(self):
        """If Google returns no parseable results, falls back to DDG."""
        ddg_html = """
        <a class="result__a" href="https://ddg-result.com/page">DDG Fallback</a>
        <a class="result__snippet" href="#">DDG snippet</a>
        """

        call_count = 0

        async def mock_get(self_client, url, **kwargs):
            nonlocal call_count
            call_count += 1
            if _host_has_suffix(str(url), "google", "com"):
                # Google returns no useful results
                return _make_response("<html><body>blocked</body></html>")
            else:
                return _make_response(ddg_html)

        with patch("httpx.AsyncClient.get", new=mock_get):
            results = await search("test query")

        assert len(results) >= 1
        assert results[0].source == "duckduckgo"
        assert results[0].title == "DDG Fallback"

    @pytest.mark.asyncio
    async def test_search_respects_num_results(self):
        html = ""
        for i in range(20):
            html += f'<a href="/url?q=https://site{i}.com&sa=U"><h3>Site {i}</h3></a>\n'

        transport = MockTransport(responses={"google.com": _make_response(html)})
        with patch("src.browser.toolkit._build_client") as mock_build:
            mock_build.return_value = httpx.AsyncClient(transport=transport)
            results = await search("many results", num_results=5)

        assert len(results) <= 5

    @pytest.mark.asyncio
    async def test_search_handles_network_error(self):
        """If both engines fail, returns empty list."""

        async def mock_get(self_client, url, **kwargs):
            raise httpx.ConnectError("connection refused")

        with patch("httpx.AsyncClient.get", new=mock_get):
            results = await search("failing query")

        assert results == []


# ── Diff Function Tests ──────────────────────────────────────────────


class TestDiff:
    """Test the diff() function with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_diff_no_changes(self):
        html = "<html><body><p>Static content</p></body></html>"
        transport = MockTransport(default_text=html)

        with patch("src.browser.toolkit._build_client") as mock_build:
            mock_build.return_value = httpx.AsyncClient(transport=transport)
            result = await diff("https://example.com", interval=0.01)

        assert isinstance(result, PageDiff)
        assert result.text_changed is False
        assert result.added_links == []
        assert result.removed_links == []
        assert "no changes" in result.diff_summary

    @pytest.mark.asyncio
    async def test_diff_detects_text_change(self):
        """Simulate text changing between two fetches."""
        call_count = 0

        async def mock_get(self_client, url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_response("<html><body><p>Version A</p></body></html>")
            else:
                return _make_response("<html><body><p>Version B with more text</p></body></html>")

        with patch("httpx.AsyncClient.get", new=mock_get):
            result = await diff("https://example.com", interval=0.01)

        assert result.text_changed is True
        assert "text changed" in result.diff_summary

    @pytest.mark.asyncio
    async def test_diff_detects_added_links(self):
        call_count = 0

        async def mock_get(self_client, url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_response('<html><body><a href="https://a.com">A</a></body></html>')
            else:
                return _make_response(
                    '<html><body><a href="https://a.com">A</a>' '<a href="https://b.com">B</a></body></html>'
                )

        with patch("httpx.AsyncClient.get", new=mock_get):
            result = await diff("https://example.com", interval=0.01)

        assert _has_exact_url(result.added_links, "https://b.com")
        assert result.removed_links == []

    @pytest.mark.asyncio
    async def test_diff_detects_removed_links(self):
        call_count = 0

        async def mock_get(self_client, url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_response(
                    '<html><body><a href="https://a.com">A</a>' '<a href="https://b.com">B</a></body></html>'
                )
            else:
                return _make_response('<html><body><a href="https://a.com">A</a></body></html>')

        with patch("httpx.AsyncClient.get", new=mock_get):
            result = await diff("https://example.com", interval=0.01)

        assert _has_exact_url(result.removed_links, "https://b.com")

    @pytest.mark.asyncio
    async def test_diff_first_fetch_failure(self):
        async def mock_get(self_client, url, **kwargs):
            raise httpx.ConnectError("connection refused")

        with patch("httpx.AsyncClient.get", new=mock_get):
            result = await diff("https://example.com", interval=0.01)

        assert "First fetch failed" in result.diff_summary

    @pytest.mark.asyncio
    async def test_diff_has_elapsed_ms(self):
        transport = MockTransport(default_text="<html><body>hi</body></html>")
        with patch("src.browser.toolkit._build_client") as mock_build:
            mock_build.return_value = httpx.AsyncClient(transport=transport)
            result = await diff("https://example.com", interval=0.01)

        assert result.elapsed_ms > 0


# ── Extract Function Tests ───────────────────────────────────────────


class TestExtract:
    """Test the extract() function with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_extract_emails(self):
        html = """
        <html><body>
            <p>Contact us at admin@example.com or support@test.org</p>
        </body></html>
        """
        transport = MockTransport(default_text=html)
        with patch("src.browser.toolkit._build_client") as mock_build:
            mock_build.return_value = httpx.AsyncClient(transport=transport)
            items = await extract("https://example.com", "email")

        values = [item.value for item in items]
        assert "admin@example.com" in values
        assert "support@test.org" in values
        assert all(item.pattern_name == "email" for item in items)

    @pytest.mark.asyncio
    async def test_extract_prices(self):
        html = """
        <html><body>
            <p>Price: $19.99</p>
            <p>Sale: $9.99</p>
            <p>Premium: $1,299.00</p>
        </body></html>
        """
        transport = MockTransport(default_text=html)
        with patch("src.browser.toolkit._build_client") as mock_build:
            mock_build.return_value = httpx.AsyncClient(transport=transport)
            items = await extract("https://shop.example.com", "price")

        values = [item.value for item in items]
        assert "$19.99" in values
        assert "$9.99" in values
        assert "$1,299.00" in values

    @pytest.mark.asyncio
    async def test_extract_dates(self):
        html = "<html><body><p>Published: 2026-03-15 Updated: 2026/01/20</p></body></html>"
        transport = MockTransport(default_text=html)
        with patch("src.browser.toolkit._build_client") as mock_build:
            mock_build.return_value = httpx.AsyncClient(transport=transport)
            items = await extract("https://blog.example.com", "date")

        values = [item.value for item in items]
        assert "2026-03-15" in values
        assert "2026/01/20" in values

    @pytest.mark.asyncio
    async def test_extract_custom_regex(self):
        html = "<html><body><p>Order #12345 and Order #67890</p></body></html>"
        transport = MockTransport(default_text=html)
        with patch("src.browser.toolkit._build_client") as mock_build:
            mock_build.return_value = httpx.AsyncClient(transport=transport)
            items = await extract("https://example.com", r"Order #\d+")

        values = [item.value for item in items]
        assert "Order #12345" in values
        assert "Order #67890" in values
        assert all(item.pattern_name == "custom" for item in items)

    @pytest.mark.asyncio
    async def test_extract_deduplicates(self):
        html = "<html><body><p>a@b.com and a@b.com repeated</p></body></html>"
        transport = MockTransport(default_text=html)
        with patch("src.browser.toolkit._build_client") as mock_build:
            mock_build.return_value = httpx.AsyncClient(transport=transport)
            items = await extract("https://example.com", "email")

        assert len(items) == 1

    @pytest.mark.asyncio
    async def test_extract_invalid_regex_returns_empty(self):
        transport = MockTransport(default_text="<html><body>text</body></html>")
        with patch("src.browser.toolkit._build_client") as mock_build:
            mock_build.return_value = httpx.AsyncClient(transport=transport)
            items = await extract("https://example.com", "[invalid(regex")

        assert items == []

    @pytest.mark.asyncio
    async def test_extract_no_matches(self):
        html = "<html><body><p>No emails here at all</p></body></html>"
        transport = MockTransport(default_text=html)
        with patch("src.browser.toolkit._build_client") as mock_build:
            mock_build.return_value = httpx.AsyncClient(transport=transport)
            items = await extract("https://example.com", "email")

        assert items == []

    @pytest.mark.asyncio
    async def test_extract_includes_context(self):
        html = "<html><body><p>Please email admin@example.com for help</p></body></html>"
        transport = MockTransport(default_text=html)
        with patch("src.browser.toolkit._build_client") as mock_build:
            mock_build.return_value = httpx.AsyncClient(transport=transport)
            items = await extract("https://example.com", "email", context_chars=20)

        assert len(items) == 1
        assert "admin@example.com" in items[0].context

    @pytest.mark.asyncio
    async def test_extract_fetch_failure(self):
        async def mock_get(self_client, url, **kwargs):
            raise httpx.ConnectError("down")

        with patch("httpx.AsyncClient.get", new=mock_get):
            items = await extract("https://example.com", "email")

        assert items == []


# ── Builtin Patterns Tests ───────────────────────────────────────────


class TestBuiltinPatterns:
    """Verify all builtin regex patterns are valid and match expected inputs."""

    def test_email_pattern(self):
        assert re.search(BUILTIN_PATTERNS["email"], "user@example.com")
        assert not re.search(BUILTIN_PATTERNS["email"], "notanemail")

    def test_price_pattern(self):
        assert re.search(BUILTIN_PATTERNS["price"], "$19.99")
        assert re.search(BUILTIN_PATTERNS["price"], "$1,299.00")
        assert re.search(BUILTIN_PATTERNS["price"], "$5.00")

    def test_date_pattern(self):
        assert re.search(BUILTIN_PATTERNS["date"], "2026-03-15")
        assert re.search(BUILTIN_PATTERNS["date"], "2026/1/5")

    def test_phone_pattern(self):
        assert re.search(BUILTIN_PATTERNS["phone"], "555-123-4567")
        assert re.search(BUILTIN_PATTERNS["phone"], "(555) 123-4567")
        assert re.search(BUILTIN_PATTERNS["phone"], "+1 555 123 4567")

    def test_url_pattern(self):
        assert re.search(BUILTIN_PATTERNS["url"], "https://example.com/path?q=1")
        assert re.search(BUILTIN_PATTERNS["url"], "http://test.org")

    def test_ipv4_pattern(self):
        assert re.search(BUILTIN_PATTERNS["ipv4"], "192.168.1.1")
        assert re.search(BUILTIN_PATTERNS["ipv4"], "10.0.0.1")

    def test_all_patterns_compile(self):
        for name, pattern in BUILTIN_PATTERNS.items():
            compiled = re.compile(pattern)
            assert compiled is not None, f"Pattern {name!r} failed to compile"


# ── needs_js Tests ───────────────────────────────────────────────────


class TestNeedsJS:
    """Test the needs_js() JavaScript detection function."""

    @pytest.mark.asyncio
    async def test_static_html_does_not_need_js(self):
        html = """
        <html>
        <head><title>Static Page</title></head>
        <body>
            <h1>Welcome to our site</h1>
            <p>This is a fully rendered HTML page with lots of content.
               It has paragraphs, headings, and all sorts of text that
               a normal server-rendered page would have.</p>
            <p>Another paragraph with even more content to make sure
               the body text length is well above the threshold.</p>
            <a href="/about">About</a>
        </body>
        </html>
        """
        transport = MockTransport(default_text=html)
        with patch("src.browser.toolkit._build_client") as mock_build:
            mock_build.return_value = httpx.AsyncClient(transport=transport)
            result = await needs_js("https://example.com")

        assert isinstance(result, JSDetectionResult)
        assert result.needs_js is False
        assert result.body_text_length > 100

    @pytest.mark.asyncio
    async def test_spa_page_needs_js(self):
        html = """
        <html>
        <head>
            <title>SPA App</title>
            <script src="/bundle.js"></script>
            <script src="/vendor.js"></script>
            <script src="/runtime.js"></script>
            <script src="/polyfills.js"></script>
            <script src="/main.js"></script>
        </head>
        <body>
            <div id="root"></div>
            <noscript>You need to enable JavaScript to run this app.</noscript>
        </body>
        </html>
        """
        transport = MockTransport(default_text=html)
        with patch("src.browser.toolkit._build_client") as mock_build:
            mock_build.return_value = httpx.AsyncClient(transport=transport)
            result = await needs_js("https://spa.example.com")

        assert result.needs_js is True
        assert result.script_count >= 5
        assert result.noscript_present is True

    @pytest.mark.asyncio
    async def test_detects_next_js_root(self):
        html = """
        <html>
        <head>
            <script src="/_next/static/chunks/main.js"></script>
            <script src="/_next/static/chunks/framework.js"></script>
            <script src="/_next/static/chunks/webpack.js"></script>
            <script src="/_next/static/chunks/pages/_app.js"></script>
            <script src="/_next/static/chunks/pages/index.js"></script>
        </head>
        <body>
            <div id="__next"></div>
        </body>
        </html>
        """
        transport = MockTransport(default_text=html)
        with patch("src.browser.toolkit._build_client") as mock_build:
            mock_build.return_value = httpx.AsyncClient(transport=transport)
            result = await needs_js("https://nextjs.example.com")

        assert result.needs_js is True
        assert "SPA root marker" in result.reason or "__next" in result.reason

    @pytest.mark.asyncio
    async def test_meta_redirect_detection(self):
        html = """
        <html>
        <head>
            <meta http-equiv="refresh" content="0;url=https://new.example.com">
            <script src="/a.js"></script>
            <script src="/b.js"></script>
            <script src="/c.js"></script>
            <script src="/d.js"></script>
            <script src="/e.js"></script>
        </head>
        <body></body>
        </html>
        """
        transport = MockTransport(default_text=html)
        with patch("src.browser.toolkit._build_client") as mock_build:
            mock_build.return_value = httpx.AsyncClient(transport=transport)
            result = await needs_js("https://redirect.example.com")

        assert result.meta_redirect is True

    @pytest.mark.asyncio
    async def test_fetch_failure(self):
        async def mock_get(self_client, url, **kwargs):
            raise httpx.ConnectError("refused")

        with patch("httpx.AsyncClient.get", new=mock_get):
            result = await needs_js("https://down.example.com")

        assert result.needs_js is False
        assert "Fetch failed" in result.reason

    @pytest.mark.asyncio
    async def test_result_has_elapsed_ms(self):
        html = "<html><body><p>Hello world</p></body></html>"
        transport = MockTransport(default_text=html)
        with patch("src.browser.toolkit._build_client") as mock_build:
            mock_build.return_value = httpx.AsyncClient(transport=transport)
            result = await needs_js("https://example.com")

        assert result.elapsed_ms >= 0

    @pytest.mark.asyncio
    async def test_counts_scripts(self):
        html = """
        <html><head>
            <script src="/a.js"></script>
            <script>console.log("inline")</script>
            <script type="module" src="/b.js"></script>
        </head><body><p>Some content here that is quite long and detailed
        to push the body text length above the threshold.</p></body></html>
        """
        transport = MockTransport(default_text=html)
        with patch("src.browser.toolkit._build_client") as mock_build:
            mock_build.return_value = httpx.AsyncClient(transport=transport)
            result = await needs_js("https://example.com")

        assert result.script_count == 3

    @pytest.mark.asyncio
    async def test_noscript_tracking_pixel_ignored(self):
        """A <noscript> with just a tracking pixel should not count."""
        html = """
        <html><head></head>
        <body>
            <p>Lots of rendered content here to ensure the page looks normal
            and has plenty of body text for the heuristics to consider.</p>
            <noscript><img src="/pixel.gif" height="1" width="1"></noscript>
        </body></html>
        """
        transport = MockTransport(default_text=html)
        with patch("src.browser.toolkit._build_client") as mock_build:
            mock_build.return_value = httpx.AsyncClient(transport=transport)
            result = await needs_js("https://example.com")

        assert result.noscript_present is False


# ── Constants Tests ──────────────────────────────────────────────────


class TestConstants:
    """Verify module-level constants."""

    def test_default_headers_has_user_agent(self):
        assert "User-Agent" in DEFAULT_HEADERS
        assert "Mozilla" in DEFAULT_HEADERS["User-Agent"]

    def test_builtin_patterns_has_expected_keys(self):
        expected = {"email", "price", "date", "phone", "url", "ipv4"}
        assert expected == set(BUILTIN_PATTERNS.keys())
