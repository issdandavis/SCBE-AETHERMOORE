#!/usr/bin/env python3
"""AetherBrowse Toolkit — fast, persistent, parallel browsing for AI agents.

No frameworks. No abstractions. Just results.

Usage:
    from src.browser.toolkit import browse, multi, session

    # Single page
    page = browse("https://example.com")
    print(page.text[:500])
    print(page.links[:10])
    print(page.forms)

    # Parallel
    pages = multi(["https://a.com", "https://b.com", "https://c.com"])

    # Persistent session (cookies survive)
    s = session()
    s.go("https://github.com/login")
    s.fill({"login": "user", "password": "pass"})
    s.submit()
    dashboard = s.go("https://github.com")  # still logged in
    s.save()  # persist cookies to disk
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import httpx

try:
    from selectolax.parser import HTMLParser
except ImportError:
    HTMLParser = None  # fallback to regex extraction

REPO_ROOT = Path(__file__).resolve().parents[2]
SESSION_DIR = REPO_ROOT / "artifacts" / "browser_sessions"
DEFAULT_TIMEOUT = 20
MAX_PARALLEL = 10

# Common headers that don't get blocked
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Link:
    text: str
    href: str
    rel: str = ""


@dataclass
class FormField:
    name: str
    type: str
    value: str = ""
    placeholder: str = ""


@dataclass
class Form:
    action: str
    method: str
    fields: list[FormField] = field(default_factory=list)


@dataclass
class Page:
    url: str
    status: int
    title: str
    text: str
    links: list[Link]
    forms: list[Form]
    meta: dict[str, str]
    headers: dict[str, str]
    elapsed_ms: int
    error: str = ""
    raw_html: str = ""

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 400 and not self.error

    def find_links(self, pattern: str) -> list[Link]:
        """Find links matching a regex pattern in text or href."""
        rx = re.compile(pattern, re.IGNORECASE)
        return [lnk for lnk in self.links if rx.search(lnk.text) or rx.search(lnk.href)]

    def find_form(self, action_pattern: str = "") -> Optional[Form]:
        """Find first form matching action pattern, or first form if no pattern."""
        if not self.forms:
            return None
        if not action_pattern:
            return self.forms[0]
        rx = re.compile(action_pattern, re.IGNORECASE)
        for f in self.forms:
            if rx.search(f.action):
                return f
        return self.forms[0]

    def summary(self, max_chars: int = 2000) -> str:
        """Quick summary for LLM context."""
        lines = [
            f"URL: {self.url}",
            f"Status: {self.status}",
            f"Title: {self.title}",
            f"Links: {len(self.links)}",
            f"Forms: {len(self.forms)}",
            f"Time: {self.elapsed_ms}ms",
        ]
        if self.error:
            lines.append(f"Error: {self.error}")
        text_preview = self.text[:max_chars].strip()
        if text_preview:
            lines.append(f"\n--- Content ---\n{text_preview}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------

def _parse_html(html: str, base_url: str) -> tuple[str, list[Link], list[Form], dict[str, str], str]:
    """Extract text, links, forms, meta from HTML. Fast path with selectolax, fallback to regex."""
    if HTMLParser is not None:
        return _parse_selectolax(html, base_url)
    return _parse_regex(html, base_url)


def _parse_selectolax(html: str, base_url: str) -> tuple[str, list[Link], list[Form], dict[str, str], str]:
    tree = HTMLParser(html)

    # Title
    title_node = tree.css_first("title")
    title = title_node.text(strip=True) if title_node else ""

    # Remove script/style
    for tag in tree.css("script, style, noscript"):
        tag.decompose()

    # Text
    text = tree.body.text(separator="\n", strip=True) if tree.body else tree.text(strip=True)

    # Links
    links = []
    for a in tree.css("a[href]"):
        href = a.attributes.get("href", "")
        if href and not href.startswith(("#", "javascript:", "mailto:")):
            links.append(Link(
                text=a.text(strip=True)[:120],
                href=urljoin(base_url, href),
                rel=a.attributes.get("rel", ""),
            ))

    # Forms
    forms = []
    for form in tree.css("form"):
        action = urljoin(base_url, form.attributes.get("action", ""))
        method = (form.attributes.get("method", "GET")).upper()
        fields = []
        for inp in form.css("input, textarea, select"):
            name = inp.attributes.get("name", "")
            if name:
                fields.append(FormField(
                    name=name,
                    type=inp.attributes.get("type", "text"),
                    value=inp.attributes.get("value", ""),
                    placeholder=inp.attributes.get("placeholder", ""),
                ))
        forms.append(Form(action=action, method=method, fields=fields))

    # Meta
    meta = {}
    for m in tree.css("meta"):
        name = m.attributes.get("name", "") or m.attributes.get("property", "")
        content = m.attributes.get("content", "")
        if name and content:
            meta[name] = content[:500]

    return text, links, forms, meta, title


def _parse_regex(html: str, base_url: str) -> tuple[str, list[Link], list[Form], dict[str, str], str]:
    """Regex fallback when selectolax isn't installed."""
    # Title
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    title = m.group(1).strip() if m else ""

    # Strip tags for text
    clean = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", "", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", clean)
    text = re.sub(r"\s+", " ", text).strip()

    # Links
    links = []
    for m in re.finditer(r'<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.IGNORECASE | re.DOTALL):
        href, link_text = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if href and not href.startswith(("#", "javascript:", "mailto:")):
            links.append(Link(text=link_text[:120], href=urljoin(base_url, href)))

    # Forms (basic)
    forms = []
    for fm in re.finditer(r"<form\s([^>]*)>(.*?)</form>", html, re.IGNORECASE | re.DOTALL):
        attrs, body = fm.group(1), fm.group(2)
        action_m = re.search(r'action=["\']([^"\']*)["\']', attrs, re.IGNORECASE)
        method_m = re.search(r'method=["\']([^"\']*)["\']', attrs, re.IGNORECASE)
        action = urljoin(base_url, action_m.group(1)) if action_m else base_url
        method = (method_m.group(1) if method_m else "GET").upper()
        fields = []
        for inp in re.finditer(r'<(?:input|textarea|select)\s([^>]*)/?>', body, re.IGNORECASE):
            inp_attrs = inp.group(1)
            name_m = re.search(r'name=["\']([^"\']*)["\']', inp_attrs, re.IGNORECASE)
            if name_m:
                type_m = re.search(r'type=["\']([^"\']*)["\']', inp_attrs, re.IGNORECASE)
                val_m = re.search(r'value=["\']([^"\']*)["\']', inp_attrs, re.IGNORECASE)
                ph_m = re.search(r'placeholder=["\']([^"\']*)["\']', inp_attrs, re.IGNORECASE)
                fields.append(FormField(
                    name=name_m.group(1),
                    type=type_m.group(1) if type_m else "text",
                    value=val_m.group(1) if val_m else "",
                    placeholder=ph_m.group(1) if ph_m else "",
                ))
        forms.append(Form(action=action, method=method, fields=fields))

    # Meta
    meta = {}
    for m in re.finditer(r'<meta\s([^>]*)/?>', html, re.IGNORECASE):
        attrs = m.group(1)
        name_m = re.search(r'(?:name|property)=["\']([^"\']*)["\']', attrs, re.IGNORECASE)
        content_m = re.search(r'content=["\']([^"\']*)["\']', attrs, re.IGNORECASE)
        if name_m and content_m:
            meta[name_m.group(1)] = content_m.group(1)[:500]

    return text, links, forms, meta, title


# ---------------------------------------------------------------------------
# Core: browse()
# ---------------------------------------------------------------------------

def browse(
    url: str,
    *,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    follow_redirects: bool = True,
    max_text: int = 50000,
) -> Page:
    """Fetch a URL and return structured Page data."""
    t0 = time.time()
    merged_headers = {**HEADERS, **(headers or {})}

    try:
        with httpx.Client(
            follow_redirects=follow_redirects,
            timeout=timeout,
            headers=merged_headers,
            cookies=cookies,
        ) as client:
            if method.upper() == "POST" and data:
                resp = client.post(url, data=data)
            else:
                resp = client.get(url)

        elapsed = int((time.time() - t0) * 1000)
        html = resp.text[:500000]  # cap at 500KB
        text, links, forms, meta, title = _parse_html(html, str(resp.url))

        return Page(
            url=str(resp.url),
            status=resp.status_code,
            title=title,
            text=text[:max_text],
            links=links[:200],
            forms=forms[:20],
            meta=meta,
            headers=dict(resp.headers),
            elapsed_ms=elapsed,
            raw_html=html if len(html) < 100000 else "",
        )
    except Exception as exc:
        elapsed = int((time.time() - t0) * 1000)
        return Page(
            url=url, status=0, title="", text="", links=[], forms=[],
            meta={}, headers={}, elapsed_ms=elapsed, error=str(exc),
        )


# ---------------------------------------------------------------------------
# Parallel: multi()
# ---------------------------------------------------------------------------

async def _fetch_one(client: httpx.AsyncClient, url: str, max_text: int) -> Page:
    t0 = time.time()
    try:
        resp = await client.get(url)
        elapsed = int((time.time() - t0) * 1000)
        html = resp.text[:500000]
        text, links, forms, meta, title = _parse_html(html, str(resp.url))
        return Page(
            url=str(resp.url), status=resp.status_code, title=title,
            text=text[:max_text], links=links[:200], forms=forms[:20],
            meta=meta, headers=dict(resp.headers), elapsed_ms=elapsed,
        )
    except Exception as exc:
        elapsed = int((time.time() - t0) * 1000)
        return Page(
            url=url, status=0, title="", text="", links=[], forms=[],
            meta={}, headers={}, elapsed_ms=elapsed, error=str(exc),
        )


async def _multi_async(urls: list[str], max_text: int, timeout: int) -> list[Page]:
    async with httpx.AsyncClient(
        follow_redirects=True, timeout=timeout, headers=HEADERS,
    ) as client:
        tasks = [_fetch_one(client, url, max_text) for url in urls[:MAX_PARALLEL]]
        return await asyncio.gather(*tasks)


def multi(urls: list[str], *, max_text: int = 50000, timeout: int = DEFAULT_TIMEOUT) -> list[Page]:
    """Fetch multiple URLs in parallel. Returns list of Page objects."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Already in async context — use nest_asyncio or run sync
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, _multi_async(urls, max_text, timeout))
            return future.result()
    return asyncio.run(_multi_async(urls, max_text, timeout))


# ---------------------------------------------------------------------------
# Session: persistent cookies + state
# ---------------------------------------------------------------------------

class Session:
    """Persistent browsing session with cookie jar and history."""

    def __init__(self, name: str = "default"):
        self.name = name
        self.cookies: dict[str, str] = {}
        self.history: list[str] = []
        self._state_path = SESSION_DIR / f"{name}.json"
        self._load()

    def _load(self) -> None:
        if self._state_path.exists():
            try:
                data = json.loads(self._state_path.read_text(encoding="utf-8"))
                self.cookies = data.get("cookies", {})
                self.history = data.get("history", [])[-100:]
            except Exception:
                pass

    def save(self) -> None:
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(json.dumps({
            "cookies": self.cookies,
            "history": self.history[-100:],
            "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }, indent=2), encoding="utf-8")

    def go(self, url: str, **kwargs) -> Page:
        """Navigate to URL with persistent cookies."""
        page = browse(url, cookies=self.cookies, **kwargs)
        # Merge any new cookies from response
        raw_cookies = page.headers.get("set-cookie", "")
        if raw_cookies:
            for chunk in raw_cookies.split("\n"):
                parts = chunk.strip().split("=", 1)
                if len(parts) == 2:
                    name = parts[0].strip()
                    val = parts[1].split(";")[0].strip()
                    if name and not name.startswith(("path", "Path", "domain", "Domain", "expires", "Expires", "max-age", "Max-Age", "secure", "Secure", "httponly", "HttpOnly", "samesite", "SameSite")):
                        self.cookies[name] = val
        self.history.append(url)
        self.save()
        return page

    def fill(self, form: Form, values: dict[str, str]) -> Page:
        """Submit a form with values."""
        # Merge form defaults with provided values
        data = {}
        for f in form.fields:
            if f.name in values:
                data[f.name] = values[f.name]
            elif f.value:
                data[f.name] = f.value

        return self.go(
            form.action,
            method=form.method,
            data=data if form.method == "POST" else None,
        )

    def back(self) -> Optional[Page]:
        """Go back in history."""
        if len(self.history) >= 2:
            self.history.pop()  # remove current
            return self.go(self.history[-1])
        return None


def session(name: str = "default") -> Session:
    """Create or resume a named browsing session."""
    return Session(name)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.browser.toolkit <url> [url2] [url3]")
        sys.exit(1)

    urls = sys.argv[1:]
    if len(urls) == 1:
        page = browse(urls[0])
        print(page.summary())
    else:
        pages = multi(urls)
        for p in pages:
            print(f"\n{'='*60}")
            print(p.summary(max_chars=500))
