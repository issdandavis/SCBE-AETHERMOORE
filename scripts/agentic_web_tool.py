#!/usr/bin/env python3
"""Web access utility for agentic workflows with Playwright or HTTP fallback."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


@dataclass
class CaptureResult:
    url: str
    title: str
    status_code: int | None
    text_snippet: str
    links: List[Dict[str, str]]
    method: str
    screenshot_path: str | None = None
    warning: str | None = None


def _http_fetch_html(url: str, timeout: int = 25) -> tuple[int | None, str]:
    req = Request(url, headers={"User-Agent": "SCBE-Agentic-Web-Tool/1.0"})
    with urlopen(req, timeout=timeout) as response:
        html_bytes = response.read()
        status_code = getattr(response, "status", 200)
        charset = response.headers.get_content_charset() or "utf-8"
        html = html_bytes.decode(charset, errors="ignore")
    return status_code, html


def _http_fetch(url: str, timeout: int = 25) -> CaptureResult:
    status_code, html = _http_fetch_html(url, timeout=timeout)

    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
    title = title_match.group(1).strip() if title_match else url
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    links: List[Dict[str, str]] = []
    for match in re.finditer(r"<a[^>]+href=['\\\"](.*?)['\\\"][^>]*>(.*?)</a>", html, flags=re.I | re.S):
        href = match.group(1).strip()
        label = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        if href and not href.lower().startswith("javascript:"):
            links.append({"href": href, "text": label[:120]})
        if len(links) >= 20:
            break

    return CaptureResult(
        url=url,
        title=title,
        status_code=status_code,
        text_snippet=text[:1200],
        links=links,
        method="http",
    )


async def _playwright_capture(url: str, output_dir: Path, timeout_ms: int = 30000) -> CaptureResult:
    result: CaptureResult
    from playwright.async_api import async_playwright  # type: ignore

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
        response = await page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
        title = await page.title()
        text = (await page.locator("body").inner_text()).strip()
        links: List[Dict[str, str]] = []
        for entry in await page.locator("a[href]").evaluate_all("els => els.slice(0, 20).map(e => ({ href: e.href, text: e.textContent }))"):
            href = str(entry.get("href", "")).strip()
            text_value = str(entry.get("text", "") or "").strip()
            if href:
                links.append({"href": href, "text": text_value[:120]})
                if len(links) >= 20:
                    break

        artifact_slug = hashlib.sha1(f"{url}:{datetime.now(timezone.utc).timestamp()}".encode("utf-8")).hexdigest()[:12]
        output_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = str(output_dir / f"{artifact_slug}.png")
        await page.screenshot(path=screenshot_path, full_page=True)
        await browser.close()

    status_code = response.status if response else None
    result = CaptureResult(
        url=url,
        title=title,
        status_code=status_code,
        text_snippet=text[:1200],
        links=links,
        method="playwright",
        screenshot_path=screenshot_path,
    )
    return result


def _capture_with_fallback(url: str, output_dir: Path, engine: str) -> CaptureResult:
    if engine == "playwright":
        try:
            return asyncio.run(_playwright_capture(url, output_dir))
        except Exception as exc:
            capture = _http_fetch(url)
            capture.method = "http-fallback"
            capture.warning = f"playwright_failed: {exc}"
            return capture

    if engine == "auto":
        try:
            return asyncio.run(_playwright_capture(url, output_dir))
        except Exception:
            return _http_fetch(url)

    return _http_fetch(url)


def _search_duckduckgo(query: str, max_results: int = 8) -> List[Dict[str, str]]:
    encoded = quote_plus(query)
    url = f"https://duckduckgo.com/html/?q={encoded}"
    _, html = _http_fetch_html(url)

    # Best effort HTML parsing, no dependency on external parsers.
    results: List[Dict[str, str]] = []
    for match in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, flags=re.I | re.S):
        link = match.group(1)
        title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        results.append({"title": title, "url": link})
        if len(results) >= max_results:
            break

    return results


def _save_capture(output_dir: Path, result: CaptureResult) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output = {
        "url": result.url,
        "title": result.title,
        "status_code": result.status_code,
        "method": result.method,
        "warning": result.warning,
        "screenshot_path": result.screenshot_path,
        "text_snippet": result.text_snippet,
        "links": result.links,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    filename = hashlib.sha1(result.url.encode("utf-8")).hexdigest()[:12] + ".json"
    output_path = output_dir / filename
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    return output_path


def _search_and_save(output_dir: Path, query: str, max_results: int) -> Path:
    results = _search_duckduckgo(query, max_results=max_results)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = {
        "query": query,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "result_count": len(results),
        "results": results,
    }
    filename = hashlib.sha1(query.encode("utf-8")).hexdigest()[:12] + ".json"
    output_path = output_dir / filename
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Agentic web helper for search and capture")
    parser.add_argument("--engine", default="auto", choices=["auto", "playwright", "http"], help="Capture engine")
    parser.add_argument("--output-dir", default="artifacts/web_tool", help="Capture artifact directory")
    parser.add_argument("--timeout", type=int, default=25, help="HTTP timeout in seconds")
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument("--max-results", type=int, default=8)

    capture_parser = subparsers.add_parser("capture")
    capture_parser.add_argument("--url", required=True)

    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.command == "search":
        output_path = _search_and_save(output_dir, args.query, args.max_results)
        print(f"Search output written to {output_path}")
        return 0

    if args.command == "capture":
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "0")
        result = _capture_with_fallback(args.url, output_dir, args.engine)
        output_path = _save_capture(output_dir, result)
        print(f"Capture output written to {output_path}")
        if result.screenshot_path:
            print(f"Screenshot written to {result.screenshot_path}")
        if result.warning:
            print(f"Warning: {result.warning}")
        print(f"Title: {result.title}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
