"""
SCBE Headless Browser — True Headless Research Engine
=====================================================

Replaces Perplexity/Comet with a governed, headless browser that:
- Searches DuckDuckGo (no API key) or Google (via scrape)
- Fetches and extracts structured content from any URL
- Scans all content through the antivirus membrane
- Pipes results to ResearchFunnel (local JSONL + Notion + HF)
- Runs fully headless (no GUI)
- Works as CLI, Python API, or FastAPI endpoint

Two-tier architecture:
    Tier 1 (httpx+bs4): Lightweight fetch for static pages — fast, no browser
    Tier 2 (Playwright): Full browser for JS-heavy pages — slower, more capable

Usage:
    # CLI
    python -m src.browser.headless search "SCBE competitors 2026"
    python -m src.browser.headless fetch "https://arxiv.org/abs/2401.12345"
    python -m src.browser.headless research "AI safety benchmarks" --depth 3

    # Python API
    from src.browser.headless import HeadlessBrowser
    async with HeadlessBrowser() as browser:
        results = await browser.search("hyperbolic geometry AI")
        page = await browser.fetch("https://example.com")
        report = await browser.research("topic", depth=3)

    # FastAPI
    python -m src.browser.headless serve --port 8500
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from src.governance import GovernancePacket, packet_from_request
from src.runtime.locks import IdempotentRunStore, file_lock

logger = logging.getLogger("headless-browser")

# ── Paths ───────────────────────────────────────────────────────────────

def _find_project_root() -> Path:
    here = Path(__file__).resolve().parent
    for ancestor in [here] + list(here.parents):
        if (ancestor / "package.json").exists():
            return ancestor
    return here.parent.parent

PROJECT_ROOT = _find_project_root()
RUNTIME_ROOT = PROJECT_ROOT / ".scbe" / "runtime"
HEADLESS_RUNTIME_ROOT = RUNTIME_ROOT / "headless"


# ── Antivirus membrane (inline lightweight version) ─────────────────────

PROMPT_INJECTION_PATTERNS = (
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"reveal\s+(the\s+)?system\s+prompt",
    r"developer\s+mode",
    r"act\s+as\s+root",
    r"bypass\s+safety",
    r"jailbreak",
)

MALWARE_PATTERNS = (
    r"powershell\s+-enc",
    r"cmd\.exe",
    r"rm\s+-rf",
    r"curl\s+.*\|\s*sh",
    r"wget\s+.*\|\s*bash",
    r"javascript:",
    r"data:text/html",
)


@dataclass(frozen=True)
class ThreatScan:
    verdict: str  # CLEAN, CAUTION, SUSPICIOUS, MALICIOUS
    risk_score: float
    prompt_hits: tuple
    malware_hits: tuple
    reasons: tuple


def scan_content(text: str) -> ThreatScan:
    """Scan text through antivirus membrane."""
    low = (text or "").lower()
    prompt_hits = tuple(p for p in PROMPT_INJECTION_PATTERNS if re.search(p, low))
    malware_hits = tuple(p for p in MALWARE_PATTERNS if re.search(p, low))

    risk = 0.0
    risk += min(0.60, 0.25 * len(prompt_hits))
    risk += min(0.70, 0.20 * len(malware_hits))
    risk = round(min(1.0, risk), 4)

    reasons = []
    if prompt_hits:
        reasons.append(f"prompt_injection({len(prompt_hits)})")
    if malware_hits:
        reasons.append(f"malware_signatures({len(malware_hits)})")

    if risk >= 0.7:
        verdict = "MALICIOUS"
    elif risk >= 0.4:
        verdict = "SUSPICIOUS"
    elif risk >= 0.15:
        verdict = "CAUTION"
    else:
        verdict = "CLEAN"

    return ThreatScan(
        verdict=verdict,
        risk_score=risk,
        prompt_hits=prompt_hits,
        malware_hits=malware_hits,
        reasons=tuple(reasons),
    )


# ── Data types ──────────────────────────────────────────────────────────

@dataclass
class PageResult:
    """Result from fetching a single page."""
    url: str
    title: str = ""
    text: str = ""
    html: str = ""
    links: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    meta: Dict[str, str] = field(default_factory=dict)
    scan: Optional[ThreatScan] = None
    fetch_tier: str = "httpx"  # httpx or playwright
    elapsed_ms: float = 0.0
    status_code: int = 0
    error: Optional[str] = None
    timestamp: str = ""
    attempts: int = 1

    def to_dict(self) -> dict:
        d = {
            "url": self.url,
            "title": self.title,
            "text": self.text[:2000],
            "links": self.links[:20],
            "scan_verdict": self.scan.verdict if self.scan else "UNSCANNED",
            "scan_risk": self.scan.risk_score if self.scan else 0.0,
            "fetch_tier": self.fetch_tier,
            "elapsed_ms": self.elapsed_ms,
            "status_code": self.status_code,
            "error": self.error,
            "timestamp": self.timestamp,
            "governance_score": self.scan.risk_score if self.scan else 0.0,
            "governance_verdict": self.scan.verdict if self.scan else "UNSCANNED",
            "attempts": self.attempts,
        }
        return d


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str
    position: int = 0
    governance_verdict: str = "UNSCANNED"
    governance_score: float = 0.0
    attempts: int = 1


@dataclass
class ResearchReport:
    """Full research report from a multi-page deep dive."""
    query: str
    results: List[PageResult] = field(default_factory=list)
    search_results: List[SearchResult] = field(default_factory=list)
    summary: str = ""
    total_pages: int = 0
    clean_pages: int = 0
    blocked_pages: int = 0
    elapsed_ms: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "total_pages": self.total_pages,
            "clean_pages": self.clean_pages,
            "blocked_pages": self.blocked_pages,
            "elapsed_ms": self.elapsed_ms,
            "timestamp": self.timestamp,
            "results": [r.to_dict() for r in self.results],
            "search_results": [
                {"title": s.title, "url": s.url, "snippet": s.snippet}
                for s in self.search_results
            ],
        }


# ── Extraction helpers ──────────────────────────────────────────────────

def extract_page(html: str, url: str) -> Dict[str, Any]:
    """Extract structured data from HTML."""
    soup = BeautifulSoup(html, "lxml")

    # Remove script/style/nav noise
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()

    title = ""
    if soup.title:
        title = soup.title.get_text(strip=True)

    # Meta extraction
    meta = {}
    for m in soup.find_all("meta"):
        name = m.get("name", m.get("property", ""))
        content = m.get("content", "")
        if name and content:
            meta[name] = content[:200]

    # Main content extraction (prefer article/main tags)
    main = soup.find("article") or soup.find("main") or soup.find("body")
    text = main.get_text(separator="\n", strip=True) if main else ""
    # Collapse excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Links
    base = urlparse(url)
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http"):
            links.append(href)
        elif href.startswith("/"):
            links.append(f"{base.scheme}://{base.netloc}{href}")
    links = list(dict.fromkeys(links))[:50]  # dedupe, cap at 50

    # Images
    images = []
    for img in soup.find_all("img", src=True):
        src = img["src"]
        if src.startswith("http"):
            images.append(src)
        elif src.startswith("/"):
            images.append(f"{base.scheme}://{base.netloc}{src}")
    images = list(dict.fromkeys(images))[:20]

    return {
        "title": title,
        "text": text,
        "links": links,
        "images": images,
        "meta": meta,
    }


def parse_duckduckgo_results(html: str) -> List[SearchResult]:
    """Parse DuckDuckGo HTML search results."""
    soup = BeautifulSoup(html, "lxml")
    results = []

    # DuckDuckGo lite results
    for i, item in enumerate(soup.select(".result__body, .links_main")):
        title_el = item.select_one(".result__a, .links_main a")
        snippet_el = item.select_one(".result__snippet, .links_main .snippet")
        if title_el:
            url = title_el.get("href", "")
            # DDG lite wraps URLs
            if "uddg=" in url:
                url = re.search(r"uddg=([^&]+)", url)
                url = url.group(1) if url else ""
                from urllib.parse import unquote
                url = unquote(url)
            results.append(SearchResult(
                title=title_el.get_text(strip=True),
                url=url,
                snippet=snippet_el.get_text(strip=True) if snippet_el else "",
                position=i + 1,
            ))

    # Fallback: look for any result links
    if not results:
        for i, a in enumerate(soup.select("a.result-link, a[data-testid='result-title-a']")):
            results.append(SearchResult(
                title=a.get_text(strip=True),
                url=a.get("href", ""),
                snippet="",
                position=i + 1,
            ))

    return results[:10]


# ── HeadlessBrowser ─────────────────────────────────────────────────────

class HeadlessBrowser:
    """SCBE-governed headless browser with two-tier fetch."""

    def __init__(
        self,
        user_agent: str = "SCBE-HeadlessBrowser/1.0 (research; +https://github.com/issdandavis/SCBE-AETHERMOORE)",
        timeout: float = 30.0,
        max_content_length: int = 5_000_000,  # 5MB per page
        enable_playwright: bool = True,
        max_retries: int = 3,
        retry_backoff: float = 0.5,
    ):
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_content_length = max_content_length
        self.enable_playwright = enable_playwright
        self.max_retries = max(1, int(max_retries))
        self.retry_backoff = max(0.0, float(retry_backoff))
        self._client: Optional[httpx.AsyncClient] = None
        self._playwright = None
        self._browser = None
        self._stats = {"fetched": 0, "blocked": 0, "errors": 0}
        self._run_store = IdempotentRunStore(HEADLESS_RUNTIME_ROOT / "idempotent_runs")

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, *args):
        await self.close()

    # ── Retry + governance helpers ───────────────────────────────────

    def _is_retryable_error(self, error: Exception, status_code: Optional[int] = None) -> bool:
        if status_code is not None and status_code >= 500:
            return True
        if isinstance(error, asyncio.TimeoutError):
            return True
        if isinstance(error, httpx.TimeoutException):
            return True
        if isinstance(error, (ConnectionError, httpx.NetworkError, httpx.HTTPError, OSError)):
            return True
        return False

    async def _sleep_before_retry(self, attempt: int):
        if attempt <= 0:
            return
        delay = min(self.retry_backoff * (2 ** (attempt - 1)), 2.5)
        if delay > 0:
            await asyncio.sleep(delay)

    def _log_retry(self, *, context: str, attempt: int, max_attempts: int, url: str, error: Exception):
        logger.warning(
            "Retrying %s (%s/%s) for %s after transient error: %s",
            context,
            attempt,
            max_attempts,
            url,
            error,
        )

    def _log_scan(
        self,
        *,
        action: str,
        url: str,
        tier: str,
        scan: ThreatScan,
        elapsed_ms: float,
        attempt: int,
    ):
        if scan.verdict in ("SUSPICIOUS", "MALICIOUS"):
            logger.warning(
                "Governance blocked: action=%s url=%s tier=%s attempt=%s verdict=%s "
                "governance_score=%.4f reasons=%s",
                action,
                url,
                tier,
                attempt,
                scan.verdict,
                scan.risk_score,
                scan.reasons,
            )
        else:
            logger.info(
                "Governance passed: action=%s url=%s tier=%s attempt=%s verdict=%s "
                "governance_score=%.4f elapsed_ms=%.1f",
                action,
                url,
                tier,
                attempt,
                scan.verdict,
                scan.risk_score,
                elapsed_ms,
            )

    @staticmethod
    def _action_log(*, action: str, target: str, status: str, verdict: str, governance_score: float, attempt: int):
        logger.info(
            "Action result: action=%s target=%s status=%s verdict=%s governance_score=%.4f attempts=%s",
            action,
            target,
            status,
            verdict,
            governance_score,
            attempt,
        )

    @staticmethod
    def _build_packet(payload: Dict[str, Any]) -> GovernancePacket:
        return packet_from_request(payload, defaults={"actor_id": "headless_browser", "category": "headless_browser"})

    @staticmethod
    def _load_cached_report(state: Dict[str, Any], fallback_query: str) -> ResearchReport:
        output_path = state.get("output_path")
        rows = []
        if output_path and Path(output_path).exists():
            try:
                for line in Path(output_path).read_text(encoding="utf-8").splitlines():
                    item = json.loads(line)
                    rows.append(item)
            except Exception:
                rows = []

        results = []
        for row in rows:
            scan_data = row.get("scan") or {}
            scan = None
            if scan_data:
                scan = ThreatScan(
                    verdict=scan_data.get("scan_verdict") or scan_data.get("verdict", "UNSCANNED"),
                    risk_score=float(scan_data.get("scan_risk", scan_data.get("risk_score", 0.0))),
                    prompt_hits=tuple(),
                    malware_hits=tuple(),
                    reasons=tuple(),
                )
            results.append(
                PageResult(
                    url=row.get("url", ""),
                    title=row.get("title", ""),
                    text=row.get("text", ""),
                    html=row.get("html", ""),
                    links=row.get("links", []),
                    images=row.get("images", []),
                    meta=row.get("meta", {}),
                    scan=scan,
                    fetch_tier=row.get("fetch_tier", "cache"),
                    elapsed_ms=float(row.get("elapsed_ms", 0.0)),
                    status_code=int(row.get("status_code", 0) or 0),
                    error=row.get("error") or None,
                    timestamp=row.get("timestamp", ""),
                    attempts=int(row.get("attempts", 1) or 1),
                )
            )

        return ResearchReport(
            query=state.get("query", fallback_query),
            results=results,
            total_pages=int(state.get("total_pages", len(results))),
            clean_pages=int(state.get("clean_pages", 0)),
            blocked_pages=int(state.get("blocked_pages", 0)),
            elapsed_ms=float(state.get("elapsed_ms", 0.0)),
            timestamp=state.get("created_at", ""),
            summary=f"Replayed from {output_path}" if output_path else "Replayed from cache",
        )

    async def open(self):
        """Initialize HTTP client."""
        self._client = httpx.AsyncClient(
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=self.timeout,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    async def close(self):
        """Clean up resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def _ensure_playwright(self):
        """Lazy-init Playwright browser."""
        if self._browser:
            return
        if not self.enable_playwright:
            return
        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            logger.info("Playwright Chromium launched")
        except Exception as e:
            logger.warning(f"Playwright unavailable: {e}")
            self.enable_playwright = False

    # ── Core fetch ────────────────────────────────────────────────────

    async def fetch(self, url: str, use_playwright: bool = False) -> PageResult:
        """Fetch a URL and extract content. Scans through antivirus membrane."""
        ts = datetime.now(timezone.utc).isoformat()
        t0 = time.monotonic()

        if use_playwright:
            return await self._fetch_playwright(url, ts, t0)
        return await self._fetch_httpx(url, ts, t0)

    async def _fetch_httpx(self, url: str, ts: str, t0: float) -> PageResult:
        """Tier 1: Lightweight httpx fetch."""
        if not self._client:
            await self.open()

        status_code = 0
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = await self._client.get(url)
                status_code = int(getattr(resp, "status_code", 0))
                if status_code >= 500:
                    raise RuntimeError(f"HTTP {status_code} from origin")

                elapsed = (time.monotonic() - t0) * 1000
                content_type = resp.headers.get("content-type", "")
                if "text/html" not in content_type and "text/plain" not in content_type:
                    self._action_log(
                        action="fetch",
                        target=url,
                        status="ok",
                        verdict="UNSCANNED",
                        governance_score=0.0,
                        attempt=attempt,
                    )
                    return PageResult(
                        url=url, text=f"[Non-HTML content: {content_type}]",
                        status_code=status_code, elapsed_ms=elapsed,
                        timestamp=ts, fetch_tier="httpx", attempts=attempt,
                    )

                html = resp.text[:self.max_content_length]
                extracted = extract_page(html, url)
                scan = scan_content(extracted["text"][:10000])

                self._stats["fetched"] += 1
                self._log_scan(
                    action="httpx_fetch",
                    url=url,
                    tier="httpx",
                    scan=scan,
                    elapsed_ms=elapsed,
                    attempt=attempt,
                )
                if scan.verdict in ("SUSPICIOUS", "MALICIOUS"):
                    self._stats["blocked"] += 1
                    self._action_log(
                        action="fetch",
                        target=url,
                        status="blocked",
                        verdict=scan.verdict,
                        governance_score=scan.risk_score,
                        attempt=attempt,
                    )
                    return PageResult(
                        url=url, title=extracted["title"],
                        text=f"[BLOCKED: {scan.verdict} — {scan.reasons}]",
                        scan=scan, status_code=status_code,
                        elapsed_ms=elapsed, timestamp=ts, fetch_tier="httpx", attempts=attempt,
                    )

                self._action_log(
                    action="fetch",
                    target=url,
                    status="ok",
                    verdict=scan.verdict,
                    governance_score=scan.risk_score,
                    attempt=attempt,
                )
                return PageResult(
                    url=url,
                    title=extracted["title"],
                    text=extracted["text"],
                    html=html[:50000],  # keep truncated HTML for re-extraction
                    links=extracted["links"],
                    images=extracted["images"],
                    meta=extracted["meta"],
                    scan=scan,
                    status_code=status_code,
                    elapsed_ms=elapsed,
                    timestamp=ts,
                    fetch_tier="httpx",
                    attempts=attempt,
                )

            except Exception as e:
                last_error = e
                if attempt < self.max_retries and self._is_retryable_error(e, status_code=status_code):
                    self._log_retry(
                        context="httpx fetch",
                        attempt=attempt,
                        max_attempts=self.max_retries,
                        url=url,
                        error=e,
                    )
                    await self._sleep_before_retry(attempt)
                    continue
            break

        self._stats["errors"] += 1
        elapsed = (time.monotonic() - t0) * 1000
        error_message = str(last_error) if last_error else "unknown"
        logger.error(
            "httpx fetch failed after %s attempts for %s: %s",
            self.max_retries,
            url,
            error_message,
        )
        self._action_log(
            action="fetch",
            target=url,
            status="error",
            verdict="ERROR",
            governance_score=0.0,
            attempt=self.max_retries,
        )
        return PageResult(
            url=url, error=error_message, elapsed_ms=elapsed,
            timestamp=ts, status_code=status_code, fetch_tier="httpx", attempts=self.max_retries,
        )

    async def _fetch_playwright(self, url: str, ts: str, t0: float) -> PageResult:
        """Tier 2: Full Playwright browser fetch for JS-heavy pages."""
        await self._ensure_playwright()
        if not self._browser:
            return await self._fetch_httpx(url, ts, t0)

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            page = None
            try:
                page = await self._browser.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=int(self.timeout * 1000))
                await page.wait_for_timeout(2000)  # Let JS render
                html = await page.content()
                await page.close()
                page = None

                elapsed = (time.monotonic() - t0) * 1000
                extracted = extract_page(html, url)
                scan = scan_content(extracted["text"][:10000])

                self._stats["fetched"] += 1
                self._log_scan(
                    action="playwright_fetch",
                    url=url,
                    tier="playwright",
                    scan=scan,
                    elapsed_ms=elapsed,
                    attempt=attempt,
                )
                if scan.verdict in ("SUSPICIOUS", "MALICIOUS"):
                    self._stats["blocked"] += 1
                    self._action_log(
                        action="fetch",
                        target=url,
                        status="blocked",
                        verdict=scan.verdict,
                        governance_score=scan.risk_score,
                        attempt=attempt,
                    )
                    return PageResult(
                        url=url, title=extracted["title"],
                        text=f"[BLOCKED: {scan.verdict} — {scan.reasons}]",
                        scan=scan, elapsed_ms=elapsed, timestamp=ts,
                        fetch_tier="playwright", attempts=attempt,
                    )

                self._action_log(
                    action="fetch",
                    target=url,
                    status="ok",
                    verdict=scan.verdict,
                    governance_score=scan.risk_score,
                    attempt=attempt,
                )
                return PageResult(
                    url=url,
                    title=extracted["title"],
                    text=extracted["text"],
                    html=html[:50000],
                    links=extracted["links"],
                    images=extracted["images"],
                    meta=extracted["meta"],
                    scan=scan,
                    elapsed_ms=elapsed,
                    timestamp=ts,
                    fetch_tier="playwright",
                    attempts=attempt,
                )

            except Exception as e:
                last_error = e
                if page is not None:
                    try:
                        await page.close()
                    except Exception:
                        pass

                if attempt < self.max_retries and self._is_retryable_error(e):
                    self._log_retry(
                        context="playwright fetch",
                        attempt=attempt,
                        max_attempts=self.max_retries,
                        url=url,
                        error=e,
                    )
                    await self._sleep_before_retry(attempt)
                    continue
                break

        self._stats["errors"] += 1
        logger.error(
            "Playwright fetch failed after %s attempts for %s: %s",
            self.max_retries,
            url,
            str(last_error),
        )
        self._action_log(
            action="fetch",
            target=url,
            status="error",
            verdict="ERROR",
            governance_score=0.0,
            attempt=self.max_retries,
        )
        logger.info("Falling back to httpx for %s after Playwright failures", url)
        return await self._fetch_httpx(url, ts, t0)

    # ── Search ────────────────────────────────────────────────────────

    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Search DuckDuckGo and return structured results."""
        if not self._client:
            await self.open()

        encoded = quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"

        last_error: Exception | None = None
        status_code = 0
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = await self._client.get(url)
                status_code = int(getattr(resp, "status_code", 0))
                if status_code >= 500:
                    raise RuntimeError(f"Search backend error: HTTP {resp.status_code}")

                query_scan = scan_content(query)
                results = parse_duckduckgo_results(resp.text)
                for result in results:
                    result.governance_verdict = query_scan.verdict
                    result.governance_score = query_scan.risk_score
                    result.attempts = attempt
                self._action_log(
                    action="search",
                    target=query,
                    status="ok",
                    verdict=query_scan.verdict,
                    governance_score=query_scan.risk_score,
                    attempt=attempt,
                )
                logger.info(
                    "Search completed: query=%s results=%s attempts=%s governance=%s score=%.4f",
                    query,
                    len(results),
                    attempt,
                    query_scan.verdict,
                    query_scan.risk_score,
                )
                return results[:num_results]
            except Exception as e:
                last_error = e
                if attempt < self.max_retries and self._is_retryable_error(e, status_code=status_code):
                    self._log_retry(
                        context="search",
                        attempt=attempt,
                        max_attempts=self.max_retries,
                        url=url,
                        error=e,
                    )
                    await self._sleep_before_retry(attempt)
                    continue
                logger.error("Search failed after %s attempts: %s", self.max_retries, e)
                break

        logger.debug("Search returning no results for query=%s error=%s", query, last_error)
        return []

    # ── Research (search + fetch + extract) ───────────────────────────

    async def research(
        self,
        query: str,
        depth: int = 3,
        use_playwright_for_js: bool = False,
    ) -> ResearchReport:
        """Full research pipeline: search → fetch top results → extract → scan."""
        t0 = time.monotonic()
        ts = datetime.now(timezone.utc).isoformat()

        # Search
        search_results = await self.search(query, num_results=depth * 2)

        # Fetch top results in parallel
        urls = [sr.url for sr in search_results if sr.url.startswith("http")][:depth]

        tasks = [self.fetch(url, use_playwright=use_playwright_for_js) for url in urls]
        pages = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        clean = 0
        blocked = 0
        for p in pages:
            if isinstance(p, Exception):
                results.append(PageResult(url="", error=str(p), timestamp=ts))
            else:
                results.append(p)
                if p.scan and p.scan.verdict in ("SUSPICIOUS", "MALICIOUS"):
                    blocked += 1
                else:
                    clean += 1

        elapsed = (time.monotonic() - t0) * 1000

        return ResearchReport(
            query=query,
            results=results,
            search_results=search_results,
            total_pages=len(results),
            clean_pages=clean,
            blocked_pages=blocked,
            elapsed_ms=elapsed,
            timestamp=ts,
        )

    # ── Bulk fetch ────────────────────────────────────────────────────

    async def fetch_many(self, urls: List[str], concurrency: int = 5) -> List[PageResult]:
        """Fetch multiple URLs with bounded concurrency."""
        sem = asyncio.Semaphore(concurrency)

        async def bounded_fetch(url):
            async with sem:
                return await self.fetch(url)

        return await asyncio.gather(*[bounded_fetch(u) for u in urls])

    # ── Storage integration ───────────────────────────────────────────

    async def research_and_store(
        self,
        query: str,
        depth: int = 3,
        output_dir: Optional[str] = None,
        packet: Optional[GovernancePacket] = None,
    ) -> ResearchReport:
        """Research and save results to JSONL file with idempotent replay support."""
        gov_packet = packet or self._build_packet({"query": query, "depth": depth})
        run_token = gov_packet.idempotency_token

        out_dir = Path(output_dir) if output_dir else PROJECT_ROOT / "training" / "intake" / "web_research"
        out_dir.mkdir(parents=True, exist_ok=True)

        lock_path = HEADLESS_RUNTIME_ROOT / "locks" / f"{run_token}.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        cached = self._run_store.load(run_token)
        if cached and cached.get("status") == "complete":
            return self._load_cached_report(cached, fallback_query=query)

        with file_lock(lock_path, timeout_sec=20.0):
            marker = self._run_store.load(run_token)
            if marker and marker.get("status") == "complete":
                return self._load_cached_report(marker, fallback_query=query)

            report = await self.research(query, depth=depth)

            slug = re.sub(r"[^a-z0-9]+", "_", query.lower())[:40]
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            out_file = out_dir / f"headless_{slug}_{ts}_{run_token[:8]}.jsonl"

            with open(out_file, "w", encoding="utf-8") as f:
                for page in report.results:
                    if page.error:
                        continue
                    record = {
                        "source": "headless_browser",
                        "query": query,
                        "packet_id": gov_packet.packet_id,
                        **page.to_dict(),
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\\n")

            self._run_store.save(
                run_token,
                {
                    "status": "complete",
                    "packet_id": gov_packet.packet_id,
                    "intent": gov_packet.intent or "research",
                    "query": query,
                    "depth": int(depth),
                    "total_pages": report.total_pages,
                    "clean_pages": report.clean_pages,
                    "blocked_pages": report.blocked_pages,
                    "elapsed_ms": report.elapsed_ms,
                    "created_at": report.timestamp,
                    "output_path": str(out_file),
                },
            )

            logger.info(f"Saved {len(report.results)} results to {out_file}")
            report.summary = f"Saved to {out_file}"
            return report

    @property
    def stats(self) -> Dict[str, int]:
        return dict(self._stats)


# ── FastAPI server ──────────────────────────────────────────────────────

def create_app():
    """Create FastAPI app for headless browser service."""
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel

    app = FastAPI(title="SCBE Headless Browser", version="1.0.0")
    browser = HeadlessBrowser()

    class SearchRequest(BaseModel):
        query: str
        num_results: int = 10
        packet_id: Optional[str] = None
        idempotency_key: Optional[str] = None
        actor_id: str = ""
        agent_id: str = ""
        intent: Optional[str] = None
        category: Optional[str] = None

    class FetchRequest(BaseModel):
        url: str
        use_playwright: bool = False
        packet_id: Optional[str] = None
        idempotency_key: Optional[str] = None
        actor_id: str = ""
        agent_id: str = ""
        intent: Optional[str] = None
        category: Optional[str] = None

    class ResearchRequest(BaseModel):
        query: str
        depth: int = 3
        store: bool = True
        packet_id: Optional[str] = None
        idempotency_key: Optional[str] = None
        actor_id: str = ""
        agent_id: str = ""
        intent: Optional[str] = None
        category: Optional[str] = None

    @app.on_event("startup")
    async def startup():
        await browser.open()

    @app.on_event("shutdown")
    async def shutdown():
        await browser.close()

    def _packet_from_request(req: dict, intent: str, category: str) -> GovernancePacket:
        payload = dict(req)
        if not payload.get("intent"):
            payload["intent"] = intent
        if not payload.get("category"):
            payload["category"] = category
        packet = packet_from_request(payload)
        if not packet.actor_id:
            packet.actor_id = "headless-browser"
        if not packet.targets:
            packet.targets = [payload.get("query", payload.get("url", ""))]
        return packet

    @app.get("/health")
    async def health():
        return {"status": "ok", "stats": browser.stats}

    @app.post("/v1/search")
    async def api_search(req: SearchRequest):
        packet = _packet_from_request(req.dict(), intent="headless_search", category="headless_browser")
        results = await browser.search(req.query, req.num_results)
        return {
            "packet_id": packet.packet_id,
            "idempotency_token": packet.idempotency_token,
            "results": [{"title": r.title, "url": r.url, "snippet": r.snippet} for r in results],
        }

    @app.post("/v1/fetch")
    async def api_fetch(req: FetchRequest):
        packet = _packet_from_request(req.dict(), intent="headless_fetch", category="headless_browser")
        page = await browser.fetch(req.url, use_playwright=req.use_playwright)
        payload = page.to_dict()
        payload.update({"packet_id": packet.packet_id, "idempotency_token": packet.idempotency_token})
        return payload

    @app.post("/v1/research")
    async def api_research(req: ResearchRequest):
        packet = _packet_from_request(req.dict(), intent="headless_research", category="headless_browser")
        if req.store:
            report = await browser.research_and_store(req.query, depth=req.depth, packet=packet)
        else:
            report = await browser.research(req.query, depth=req.depth)
        payload = report.to_dict()
        payload.update({"packet_id": packet.packet_id, "idempotency_token": packet.idempotency_token})
        return payload

    return app


# ── CLI ─────────────────────────────────────────────────────────────────

async def cli_main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="SCBE Headless Browser")
    sub = parser.add_subparsers(dest="command")

    # search
    sp = sub.add_parser("search", help="Search DuckDuckGo")
    sp.add_argument("query", help="Search query")
    sp.add_argument("-n", "--num", type=int, default=10, help="Number of results")

    # fetch
    fp = sub.add_parser("fetch", help="Fetch a URL")
    fp.add_argument("url", help="URL to fetch")
    fp.add_argument("--playwright", action="store_true", help="Use Playwright")

    # research
    rp = sub.add_parser("research", help="Deep research (search + fetch)")
    rp.add_argument("query", help="Research query")
    rp.add_argument("-d", "--depth", type=int, default=3, help="Pages to fetch")
    rp.add_argument("--store", action="store_true", help="Save to JSONL")

    # serve
    svp = sub.add_parser("serve", help="Start FastAPI server")
    svp.add_argument("-p", "--port", type=int, default=8500, help="Port")

    args = parser.parse_args()

    if args.command == "serve":
        import uvicorn
        app = create_app()
        uvicorn.run(app, host="0.0.0.0", port=args.port)
        return

    async with HeadlessBrowser() as browser:
        if args.command == "search":
            results = await browser.search(args.query, args.num)
            for r in results:
                print(f"  [{r.position}] {r.title}")
                print(f"      {r.url}")
                if r.snippet:
                    print(f"      {r.snippet[:100]}")
                print()

        elif args.command == "fetch":
            page = await browser.fetch(args.url, use_playwright=args.playwright)
            print(f"Title: {page.title}")
            print(f"Status: {page.status_code}")
            print(f"Scan: {page.scan.verdict if page.scan else 'N/A'} (risk={page.scan.risk_score if page.scan else 0})")
            print(f"Tier: {page.fetch_tier}")
            print(f"Time: {page.elapsed_ms:.0f}ms")
            print(f"Text ({len(page.text)} chars):")
            print(page.text[:500])
            if page.error:
                print(f"Error: {page.error}")

        elif args.command == "research":
            if args.store:
                report = await browser.research_and_store(args.query, depth=args.depth)
            else:
                report = await browser.research(args.query, depth=args.depth)
            print(f"Query: {report.query}")
            print(f"Pages: {report.total_pages} (clean={report.clean_pages}, blocked={report.blocked_pages})")
            print(f"Time: {report.elapsed_ms:.0f}ms")
            for r in report.results:
                status = r.scan.verdict if r.scan else "?"
                print(f"  [{status}] {r.title[:60]} — {r.url[:60]}")
            if report.summary:
                print(f"\n{report.summary}")
        else:
            parser.print_help()


if __name__ == "__main__":
    asyncio.run(cli_main())
