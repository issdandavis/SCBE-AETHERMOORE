#!/usr/bin/env python3
"""
@file headless_browser.py
@module scripts/headless_browser
@layer Layer 13, Layer 14
@component Lightweight Headless Browser CLI with SCBE Governance

Minimal headless browser tool for terminal-driven automation.
Uses Playwright (Chromium-only) with optional SCBE governance scanning.

CLI usage:
    python scripts/headless_browser.py --url https://example.com --action screenshot
    python scripts/headless_browser.py --url https://example.com --action extract --selector h1
    python scripts/headless_browser.py --url https://example.com --action text
    python scripts/headless_browser.py --url https://example.com --action fill --selector "#email" --value "test@example.com"
    python scripts/headless_browser.py --url https://example.com --action navigate
    python scripts/headless_browser.py --url https://example.com --action screenshot --govern

Python API usage:
    from scripts.headless_browser import HeadlessBrowser

    async with HeadlessBrowser() as browser:
        await browser.navigate("https://example.com")
        text = await browser.extract_text("body")
        await browser.screenshot("output.png")
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from scripts.browser_autodoor import (
    AUTODOOR_INTENT,
    AutoDoorDecision,
    build_auto_door_headers,
)

logger = logging.getLogger("scbe.headless_browser")


# ---------------------------------------------------------------------------
#  Configuration
# ---------------------------------------------------------------------------

ARTIFACTS_DIR = Path(os.environ.get(
    "SCBE_ARTIFACTS_DIR",
    str(Path(__file__).resolve().parent.parent / "artifacts" / "headless"),
))

DEFAULT_TIMEOUT_MS = 30_000
DEFAULT_VIEWPORT = {"width": 1280, "height": 720}


class Action(Enum):
    NAVIGATE = "navigate"
    SCREENSHOT = "screenshot"
    EXTRACT = "extract"
    TEXT = "text"
    FILL = "fill"
    CLICK = "click"
    EVALUATE = "evaluate"
    PDF = "pdf"


@dataclass
class BrowserResult:
    """Result returned from every browser operation."""
    action: str
    success: bool
    url: str = ""
    data: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    governance: Optional[Dict[str, Any]] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "action": self.action,
            "success": self.success,
            "url": self.url,
            "duration_ms": round(self.duration_ms, 1),
            "timestamp": self.timestamp,
        }
        if self.data is not None:
            d["data"] = self.data
        if self.error:
            d["error"] = self.error
        if self.governance:
            d["governance"] = self.governance
        return d


# ---------------------------------------------------------------------------
#  Optional SCBE Governance
# ---------------------------------------------------------------------------

def _try_governance_scan(text: str, url: str) -> Optional[Dict[str, Any]]:
    """
    Optional SCBE governance scan on extracted page content.
    Uses the SimplePHDM containment model (L5/L12/L13) if available.
    Returns None if SCBE modules are not importable.
    """
    try:
        # Try importing the PHDM brain from the agents module
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from agents.browser.phdm_brain import SimplePHDM, create_phdm_brain
        import numpy as np

        brain = create_phdm_brain(safe_radius=0.92, dim=16)

        # Create a simple embedding from page content hash
        # This is a lightweight proxy -- real deployments use VisionEmbedder
        content_hash = hashlib.sha256(text.encode("utf-8", errors="replace")).digest()
        raw = np.frombuffer(content_hash[:16 * 4], dtype=np.float32)[:16]
        # Normalize into the Poincare ball (norm < 1)
        norm = np.linalg.norm(raw) + 1e-10
        embedding = raw / norm * 0.5  # Place at radius 0.5 (safe zone)

        result = brain.check_containment(embedding)
        return {
            "decision": result.decision.value,
            "risk_score": round(result.risk_score, 4),
            "hyperbolic_distance": round(result.hyperbolic_distance, 4),
            "radius": round(result.radius, 4),
            "message": result.message,
            "url_domain": urlparse(url).netloc,
        }
    except Exception as e:
        logger.debug("Governance scan unavailable: %s", e)
        return None


# ---------------------------------------------------------------------------
#  Main Browser Class
# ---------------------------------------------------------------------------

class HeadlessBrowser:
    """
    Lightweight async headless browser using Playwright (Chromium only).

    Designed for low-disk-space systems. Uses only Chromium.

    Example:
        async with HeadlessBrowser() as browser:
            await browser.navigate("https://example.com")
            text = await browser.extract_text("h1")
            print(text)
    """

    def __init__(
        self,
        headless: bool = True,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        viewport: Optional[Dict[str, int]] = None,
        artifacts_dir: Optional[Path] = None,
    ):
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.viewport = viewport or DEFAULT_VIEWPORT
        self.artifacts_dir = artifacts_dir or ARTIFACTS_DIR
        self._pw = None
        self._browser = None
        self._page = None
        self._last_door_decision = AutoDoorDecision(
            matched_key=False,
            has_secret=False,
            headers={},
            api_key_hint="",
            context={},
        )

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *exc):
        await self.stop()

    async def start(self):
        """Launch Chromium."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright not installed.\n"
                "Run: python -m pip install playwright && python -m playwright install chromium"
            )

        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=self.headless)
        context = await self._browser.new_context(viewport=self.viewport)
        self._page = await context.new_page()
        self._page.set_default_timeout(self.timeout_ms)
        self._page.set_default_navigation_timeout(self.timeout_ms)

        # Keep the request authorization decision for diagnostics.
        self._last_door_decision = AutoDoorDecision(
            matched_key=False,
            has_secret=False,
            headers={},
            api_key_hint="",
            context={},
        )

    def _apply_auto_door(self, url: str, action: str, intent: str | None = None) -> Dict[str, str]:
        decision = build_auto_door_headers(url, action=action, intent=intent or AUTODOOR_INTENT)
        self._last_door_decision = decision
        if decision.headers and self._page and self._page.context:
            self._page.context.set_default_timeout(self.timeout_ms)
            # Context headers are set for subsequent requests and kept as-is until next navigation.
            # No-op when there are no headers.
            self._page.context.set_extra_http_headers(decision.headers)
        return decision.headers

    @property
    def last_door_decision(self) -> AutoDoorDecision:
        return self._last_door_decision

    async def stop(self):
        """Shut down the browser."""
        if self._page:
            try:
                await self._page.close()
            except Exception:
                pass
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
        if self._pw:
            try:
                await self._pw.stop()
            except Exception:
                pass

    @property
    def page(self):
        if not self._page:
            raise RuntimeError("Browser not started. Call start() or use async with.")
        return self._page

    # -- Core actions -------------------------------------------------------

    async def navigate(self, url: str, wait_until: str = "domcontentloaded", *, intent: str | None = None) -> BrowserResult:
        """Navigate to a URL and return the final URL."""
        t0 = time.perf_counter()
        try:
            self._apply_auto_door(url, "navigate", intent=intent)
            resp = await self.page.goto(url, wait_until=wait_until)
            status = resp.status if resp else None
            return BrowserResult(
                action="navigate",
                success=True,
                url=self.page.url,
                data={"status": status, "title": await self.page.title()},
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        except Exception as e:
            return BrowserResult(
                action="navigate", success=False, url=url, error=str(e),
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

    async def screenshot(
        self,
        path: Optional[str] = None,
        full_page: bool = True,
        selector: Optional[str] = None,
    ) -> BrowserResult:
        """Take a screenshot and save to disk."""
        t0 = time.perf_counter()
        try:
            self.artifacts_dir.mkdir(parents=True, exist_ok=True)
            if not path:
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                domain = urlparse(self.page.url).netloc.replace(".", "_") or "page"
                path = str(self.artifacts_dir / f"{stamp}_{domain}.png")

            if selector:
                element = await self.page.query_selector(selector)
                if not element:
                    return BrowserResult(
                        action="screenshot", success=False, url=self.page.url,
                        error=f"Selector not found: {selector}",
                        duration_ms=(time.perf_counter() - t0) * 1000,
                    )
                await element.screenshot(path=path)
            else:
                await self.page.screenshot(path=path, full_page=full_page)

            return BrowserResult(
                action="screenshot", success=True, url=self.page.url,
                data={"path": path, "full_page": full_page},
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        except Exception as e:
            return BrowserResult(
                action="screenshot", success=False, url=self.page.url, error=str(e),
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

    async def extract_text(self, selector: str = "body") -> BrowserResult:
        """Extract text content from an element."""
        t0 = time.perf_counter()
        try:
            element = await self.page.query_selector(selector)
            if not element:
                return BrowserResult(
                    action="extract", success=False, url=self.page.url,
                    error=f"Selector not found: {selector}",
                    duration_ms=(time.perf_counter() - t0) * 1000,
                )
            text = await element.text_content() or ""
            return BrowserResult(
                action="extract", success=True, url=self.page.url,
                data={"text": text[:10_000], "length": len(text), "selector": selector},
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        except Exception as e:
            return BrowserResult(
                action="extract", success=False, url=self.page.url, error=str(e),
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

    async def get_full_text(self) -> BrowserResult:
        """Extract all visible text from the page."""
        t0 = time.perf_counter()
        try:
            text = await self.page.evaluate(
                "() => document.body.innerText"
            )
            return BrowserResult(
                action="text", success=True, url=self.page.url,
                data={"text": text[:10_000], "length": len(text)},
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        except Exception as e:
            return BrowserResult(
                action="text", success=False, url=self.page.url, error=str(e),
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

    async def fill(self, selector: str, value: str) -> BrowserResult:
        """Fill an input/textarea with a value."""
        t0 = time.perf_counter()
        try:
            await self.page.fill(selector, value)
            return BrowserResult(
                action="fill", success=True, url=self.page.url,
                data={"selector": selector, "length": len(value)},
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        except Exception as e:
            return BrowserResult(
                action="fill", success=False, url=self.page.url, error=str(e),
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

    async def click(self, selector: str) -> BrowserResult:
        """Click an element."""
        t0 = time.perf_counter()
        try:
            await self.page.click(selector)
            return BrowserResult(
                action="click", success=True, url=self.page.url,
                data={"selector": selector},
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        except Exception as e:
            return BrowserResult(
                action="click", success=False, url=self.page.url, error=str(e),
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

    async def evaluate(self, script: str) -> BrowserResult:
        """Execute JavaScript in the page context."""
        t0 = time.perf_counter()
        try:
            result = await self.page.evaluate(script)
            return BrowserResult(
                action="evaluate", success=True, url=self.page.url,
                data=result,
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        except Exception as e:
            return BrowserResult(
                action="evaluate", success=False, url=self.page.url, error=str(e),
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

    async def save_pdf(self, path: Optional[str] = None) -> BrowserResult:
        """Save the current page as PDF (Chromium only)."""
        t0 = time.perf_counter()
        try:
            self.artifacts_dir.mkdir(parents=True, exist_ok=True)
            if not path:
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                domain = urlparse(self.page.url).netloc.replace(".", "_") or "page"
                path = str(self.artifacts_dir / f"{stamp}_{domain}.pdf")

            await self.page.pdf(path=path)
            return BrowserResult(
                action="pdf", success=True, url=self.page.url,
                data={"path": path},
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        except Exception as e:
            return BrowserResult(
                action="pdf", success=False, url=self.page.url, error=str(e),
                duration_ms=(time.perf_counter() - t0) * 1000,
            )


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SCBE Headless Browser - lightweight Playwright automation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --url https://example.com --action screenshot
  %(prog)s --url https://example.com --action extract --selector h1
  %(prog)s --url https://example.com --action text
  %(prog)s --url https://example.com --action fill --selector "#q" --value "search term"
  %(prog)s --url https://example.com --action screenshot --govern
  %(prog)s --url https://example.com --action evaluate --js "document.title"
        """,
    )
    parser.add_argument("--url", required=True, help="URL to navigate to")
    parser.add_argument(
        "--action",
        required=True,
        choices=[a.value for a in Action],
        help="Action to perform",
    )
    parser.add_argument("--selector", default=None, help="CSS selector (for extract/fill/click)")
    parser.add_argument("--value", default=None, help="Value to fill (for fill action)")
    parser.add_argument("--js", default=None, help="JavaScript to evaluate (for evaluate action)")
    parser.add_argument("--output", default=None, help="Output file path (for screenshot/pdf)")
    parser.add_argument("--full-page", action="store_true", help="Full page screenshot")
    parser.add_argument("--govern", action="store_true", help="Run SCBE governance scan on content")
    parser.add_argument("--intent", default=AUTODOOR_INTENT, help="Time-intent label for automatic auth doors")
    parser.add_argument("--headed", action="store_true", help="Run with visible browser")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_MS, help="Timeout in ms")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output as JSON")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")

    return parser.parse_args(argv)


async def run_cli(args: argparse.Namespace) -> BrowserResult:
    """Execute the CLI action."""
    async with HeadlessBrowser(
        headless=not args.headed,
        timeout_ms=args.timeout,
        # intent is passed to navigate and captured in auto-door headers.
    ) as browser:
        # Navigate first
        nav_result = await browser.navigate(args.url, intent=args.intent)
        if not nav_result.success:
            return nav_result

        action = Action(args.action)

        if action == Action.NAVIGATE:
            result = nav_result

        elif action == Action.SCREENSHOT:
            result = await browser.screenshot(
                path=args.output,
                full_page=args.full_page,
                selector=args.selector,
            )

        elif action == Action.EXTRACT:
            selector = args.selector or "body"
            result = await browser.extract_text(selector)

        elif action == Action.TEXT:
            result = await browser.get_full_text()

        elif action == Action.FILL:
            if not args.selector or args.value is None:
                return BrowserResult(
                    action="fill", success=False, url=args.url,
                    error="--selector and --value are required for fill action",
                )
            result = await browser.fill(args.selector, args.value)

        elif action == Action.CLICK:
            if not args.selector:
                return BrowserResult(
                    action="click", success=False, url=args.url,
                    error="--selector is required for click action",
                )
            result = await browser.click(args.selector)

        elif action == Action.EVALUATE:
            js = args.js or "document.title"
            result = await browser.evaluate(js)

        elif action == Action.PDF:
            result = await browser.save_pdf(path=args.output)

        else:
            result = BrowserResult(
                action=args.action, success=False, url=args.url,
                error=f"Unknown action: {args.action}",
            )

        # Optional governance scan
        if args.govern and result.success:
            text_result = await browser.get_full_text()
            if text_result.success and text_result.data:
                gov = _try_governance_scan(
                    text_result.data.get("text", ""),
                    browser.page.url,
                )
                if gov:
                    result.governance = gov

        return result


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s %(levelname)s %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING)

    result = asyncio.run(run_cli(args))

    if args.json_output:
        print(json.dumps(result.to_dict(), indent=2, default=str))
    else:
        status = "OK" if result.success else "FAIL"
        print(f"[{status}] {result.action} {result.url} ({result.duration_ms:.0f}ms)")

        if result.error:
            print(f"  Error: {result.error}")

        if result.data:
            if isinstance(result.data, dict):
                for k, v in result.data.items():
                    if k == "text":
                        # Truncate long text for terminal display
                        display = v[:500] + ("..." if len(v) > 500 else "")
                        print(f"  {k}: {display}")
                    else:
                        print(f"  {k}: {v}")
            else:
                print(f"  data: {result.data}")

        if result.governance:
            print(f"  governance:")
            for k, v in result.governance.items():
                print(f"    {k}: {v}")

    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
