"""
SCBE Headless Browser Driver — Playwright-based execution engine
================================================================

Bridges WebPollyPad BrowserActions to real browser automation via Playwright.
Supports persistent sessions, multi-platform posting, and governed navigation.

Usage:
    driver = HeadlessBrowserDriver()
    await driver.start()
    await driver.navigate("https://linkedin.com")
    await driver.type_text("div.editor", "Hello world")
    await driver.click("button.post")
    await driver.stop()
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page

    HAS_PLAYWRIGHT = True
    try:
        from playwright_stealth import Stealth

        HAS_STEALTH = True
    except ImportError:
        HAS_STEALTH = False
except ImportError:
    HAS_PLAYWRIGHT = False
    HAS_STEALTH = False

# ---------------------------------------------------------------------------
#  Configuration
# ---------------------------------------------------------------------------

PROFILES_DIR = Path(
    os.environ.get(
        "SCBE_BROWSER_PROFILES",
        os.path.expanduser("~/.scbe/browser_profiles"),
    )
)
PROFILES_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_VIEWPORT = {"width": 1366, "height": 768}
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


class DriverMode(Enum):
    HEADLESS = "headless"
    HEADED = "headed"


class ActionType(Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCREENSHOT = "screenshot"
    WAIT = "wait"
    SCROLL = "scroll"
    SELECT = "select"
    EXTRACT = "extract"
    EVALUATE = "evaluate"


@dataclass
class ActionResult:
    success: bool
    action: str
    data: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    screenshot_path: Optional[str] = None


@dataclass
class SessionProfile:
    """Persistent browser session for a platform."""

    platform: str
    profile_dir: str
    cookies_file: str
    logged_in: bool = False
    last_used: float = 0.0


# ---------------------------------------------------------------------------
#  Main Driver
# ---------------------------------------------------------------------------


class HeadlessBrowserDriver:
    """
    Playwright-based headless browser that integrates with SCBE web agent.

    Features:
    - Persistent sessions per platform (LinkedIn, X, Medium, dev.to, etc.)
    - Stealth mode to avoid bot detection
    - Human-like interaction delays
    - Screenshot capture for debugging
    - Multi-tab support
    - Cookie persistence across runs
    """

    def __init__(
        self,
        mode: DriverMode = DriverMode.HEADLESS,
        stealth: bool = True,
        slow_mo: int = 50,
        profiles_dir: Optional[Path] = None,
        fast_mode: bool = False,
    ):
        if not HAS_PLAYWRIGHT:
            raise RuntimeError("Playwright not installed. Run: pip install playwright && playwright install chromium")
        self.mode = mode
        self.stealth = stealth
        self.slow_mo = 0 if fast_mode else slow_mo
        self.fast_mode = fast_mode
        self.profiles_dir = profiles_dir or PROFILES_DIR
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._contexts: Dict[str, BrowserContext] = {}
        self._pages: Dict[str, Page] = {}
        self._sessions: Dict[str, SessionProfile] = {}

    # -- Lifecycle -----------------------------------------------------------

    async def start(self):
        """Launch the browser."""
        self._playwright = await async_playwright().start()
        launch_args = {
            "headless": self.mode == DriverMode.HEADLESS,
            "slow_mo": self.slow_mo,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-infobars",
            ],
        }
        self._browser = await self._playwright.chromium.launch(**launch_args)

    async def stop(self):
        """Close browser and save sessions."""
        for name, ctx in self._contexts.items():
            await self._save_session(name, ctx)
            await ctx.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._contexts.clear()
        self._pages.clear()

    # -- Session Management --------------------------------------------------

    def _get_profile(self, platform: str) -> SessionProfile:
        """Get or create a session profile for a platform."""
        if platform not in self._sessions:
            profile_dir = str(self.profiles_dir / platform)
            os.makedirs(profile_dir, exist_ok=True)
            self._sessions[platform] = SessionProfile(
                platform=platform,
                profile_dir=profile_dir,
                cookies_file=str(self.profiles_dir / f"{platform}_cookies.json"),
            )
        return self._sessions[platform]

    async def get_context(self, platform: str = "default") -> BrowserContext:
        """Get or create a browser context with persistent session."""
        if platform in self._contexts:
            return self._contexts[platform]

        profile = self._get_profile(platform)

        ctx_args = {
            "viewport": DEFAULT_VIEWPORT,
            "user_agent": USER_AGENT,
            "locale": "en-US",
            "timezone_id": "America/Los_Angeles",
        }

        # Load saved cookies
        cookies_path = Path(profile.cookies_file)
        if cookies_path.exists():
            ctx_args["storage_state"] = str(cookies_path)
            profile.logged_in = True

        ctx = await self._browser.new_context(**ctx_args)

        if self.stealth:
            # Apply stealth patches to avoid detection
            pass  # stealth_async applied per-page

        self._contexts[platform] = ctx
        return ctx

    async def get_page(self, platform: str = "default") -> Page:
        """Get or create a page for a platform."""
        if platform in self._pages:
            return self._pages[platform]

        ctx = await self.get_context(platform)
        page = await ctx.new_page()

        if self.stealth:
            if HAS_STEALTH:
                await Stealth().apply_stealth_async(page)

        self._pages[platform] = page
        return page

    async def _save_session(self, platform: str, ctx: BrowserContext):
        """Save cookies and session state."""
        profile = self._get_profile(platform)
        try:
            state = await ctx.storage_state()
            with open(profile.cookies_file, "w") as f:
                json.dump(state, f, indent=2)
            profile.last_used = time.time()
        except Exception:
            pass  # Non-critical

    # -- Human-like Behavior -------------------------------------------------

    async def _human_delay(self, min_ms: int = 200, max_ms: int = 800):
        """Add random human-like delay. Skipped in fast mode."""
        if self.fast_mode:
            return
        delay = random.randint(min_ms, max_ms) / 1000.0
        await asyncio.sleep(delay)

    async def _human_type(self, page: Page, selector: str, text: str):
        """Type text with human-like keystroke delays. Fast in fast mode."""
        element = page.locator(selector)
        await element.click()
        if self.fast_mode:
            await page.keyboard.type(text, delay=5)
            return
        await self._human_delay(100, 300)
        for char in text:
            await page.keyboard.type(char, delay=random.randint(30, 120))
            if random.random() < 0.05:  # 5% chance of brief pause
                await self._human_delay(200, 600)

    # -- Core Actions --------------------------------------------------------

    async def navigate(self, url: str, platform: str = "default", wait: str = "domcontentloaded") -> ActionResult:
        """Navigate to a URL."""
        t0 = time.time()
        try:
            page = await self.get_page(platform)
            resp = await page.goto(url, wait_until=wait, timeout=30000)
            await self._human_delay(500, 1500)
            return ActionResult(
                success=True,
                action="navigate",
                data={"url": url, "status": resp.status if resp else None},
                duration_ms=(time.time() - t0) * 1000,
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action="navigate",
                error=str(e),
                duration_ms=(time.time() - t0) * 1000,
            )

    async def click(self, selector: str, platform: str = "default") -> ActionResult:
        """Click an element."""
        t0 = time.time()
        try:
            page = await self.get_page(platform)
            await self._human_delay()
            await page.click(selector, timeout=10000)
            await self._human_delay(300, 800)
            return ActionResult(
                success=True,
                action="click",
                data={"selector": selector},
                duration_ms=(time.time() - t0) * 1000,
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action="click",
                error=str(e),
                duration_ms=(time.time() - t0) * 1000,
            )

    async def type_text(
        self,
        selector: str,
        text: str,
        platform: str = "default",
        human_like: bool = True,
    ) -> ActionResult:
        """Type text into an element."""
        t0 = time.time()
        try:
            page = await self.get_page(platform)
            if human_like:
                await self._human_type(page, selector, text)
            else:
                await page.fill(selector, text)
            return ActionResult(
                success=True,
                action="type",
                data={"selector": selector, "length": len(text)},
                duration_ms=(time.time() - t0) * 1000,
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action="type",
                error=str(e),
                duration_ms=(time.time() - t0) * 1000,
            )

    async def screenshot(
        self,
        path: Optional[str] = None,
        platform: str = "default",
        full_page: bool = False,
    ) -> ActionResult:
        """Take a screenshot."""
        t0 = time.time()
        try:
            page = await self.get_page(platform)
            if not path:
                path = str(self.profiles_dir / f"screenshot_{int(time.time())}.png")
            await page.screenshot(path=path, full_page=full_page)
            return ActionResult(
                success=True,
                action="screenshot",
                data={"path": path},
                screenshot_path=path,
                duration_ms=(time.time() - t0) * 1000,
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action="screenshot",
                error=str(e),
                duration_ms=(time.time() - t0) * 1000,
            )

    async def extract_text(self, selector: str = "body", platform: str = "default") -> ActionResult:
        """Extract text content from an element."""
        t0 = time.time()
        try:
            page = await self.get_page(platform)
            text = await page.locator(selector).inner_text(timeout=10000)
            return ActionResult(
                success=True,
                action="extract",
                data={"text": text[:5000], "full_length": len(text)},
                duration_ms=(time.time() - t0) * 1000,
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action="extract",
                error=str(e),
                duration_ms=(time.time() - t0) * 1000,
            )

    async def evaluate(self, script: str, platform: str = "default") -> ActionResult:
        """Run JavaScript on the page."""
        t0 = time.time()
        try:
            page = await self.get_page(platform)
            result = await page.evaluate(script)
            return ActionResult(
                success=True,
                action="evaluate",
                data=result,
                duration_ms=(time.time() - t0) * 1000,
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action="evaluate",
                error=str(e),
                duration_ms=(time.time() - t0) * 1000,
            )

    async def wait_for(self, selector: str, platform: str = "default", timeout: int = 10000) -> ActionResult:
        """Wait for an element to appear."""
        t0 = time.time()
        try:
            page = await self.get_page(platform)
            await page.wait_for_selector(selector, timeout=timeout)
            return ActionResult(
                success=True,
                action="wait",
                data={"selector": selector},
                duration_ms=(time.time() - t0) * 1000,
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action="wait",
                error=str(e),
                duration_ms=(time.time() - t0) * 1000,
            )

    # -- Platform-Specific Posting -------------------------------------------

    async def post_to_linkedin(self, text: str) -> ActionResult:
        """Post content to LinkedIn."""
        platform = "linkedin"
        results = []

        r = await self.navigate("https://www.linkedin.com/feed/", platform)
        if not r.success:
            return r
        results.append(r)

        await self._human_delay(1000, 2000)

        # Click "Start a post"
        r = await self.click(
            'button:has-text("Start a post"), [data-test-id="share-box-feed-entry__trigger"]',
            platform,
        )
        if not r.success:
            # Try alternate selector
            r = await self.click('[role="button"]:has-text("Start a post")', platform)
        results.append(r)

        await self._human_delay(1500, 3000)

        # Type into the editor
        page = await self.get_page(platform)
        try:
            # LinkedIn uses contenteditable div
            editor = page.locator('[contenteditable="true"], [role="textbox"], .ql-editor').first
            await editor.click()
            await self._human_delay(300, 600)

            # Type with human-like delays
            for line in text.split("\n"):
                await page.keyboard.type(line, delay=random.randint(20, 60))
                await page.keyboard.press("Enter")
                await self._human_delay(100, 300)

            await self._human_delay(1000, 2000)

            # Click Post button
            post_btn = page.locator('button:has-text("Post")').last
            await post_btn.click()

            await self._human_delay(2000, 4000)

            return ActionResult(
                success=True,
                action="post_linkedin",
                data={"text_length": len(text), "steps": len(results)},
            )
        except Exception as e:
            return ActionResult(success=False, action="post_linkedin", error=str(e))

    async def post_to_devto(self, title: str, body: str, tags: List[str] = None) -> ActionResult:
        """Post an article to dev.to."""
        platform = "devto"
        tags = tags or ["ai", "fantasy", "worldbuilding"]

        r = await self.navigate("https://dev.to/new", platform)
        if not r.success:
            return r

        await self._human_delay(1500, 3000)

        page = await self.get_page(platform)
        try:
            # Title
            title_input = page.locator('#article-form-title, [id*="title"]').first
            await title_input.click()
            await page.keyboard.type(title, delay=random.randint(20, 50))

            await self._human_delay(500, 1000)

            # Tags
            for tag in tags[:4]:
                tag_input = page.locator('#tag-input, [id*="tag"]').first
                await tag_input.click()
                await page.keyboard.type(tag, delay=random.randint(30, 80))
                await page.keyboard.press("Enter")
                await self._human_delay(200, 400)

            await self._human_delay(500, 1000)

            # Body — dev.to uses a textarea or markdown editor
            body_input = page.locator('#article_body_markdown, textarea[id*="body"]').first
            await body_input.click()
            await page.keyboard.type(body, delay=random.randint(5, 15))

            await self._human_delay(1000, 2000)

            # Publish
            publish_btn = page.locator('button:has-text("Publish")').first
            await publish_btn.click()

            await self._human_delay(3000, 5000)

            return ActionResult(
                success=True,
                action="post_devto",
                data={"title": title, "tags": tags, "url": page.url},
            )
        except Exception as e:
            return ActionResult(success=False, action="post_devto", error=str(e))

    # -- Batch Operations ----------------------------------------------------

    async def multi_platform_post(
        self, text: str, platforms: List[str], title: Optional[str] = None
    ) -> Dict[str, ActionResult]:
        """Post to multiple platforms in sequence."""
        results = {}
        for plat in platforms:
            if plat == "linkedin":
                results[plat] = await self.post_to_linkedin(text)
            elif plat == "devto" and title:
                results[plat] = await self.post_to_devto(title, text)
            else:
                results[plat] = ActionResult(
                    success=False,
                    action=f"post_{plat}",
                    error=f"Platform {plat} not yet supported for headless posting",
                )
            # Brief pause between platforms
            await self._human_delay(2000, 5000)
        return results

    # -- Login Helpers -------------------------------------------------------

    async def interactive_login(self, url: str, platform: str):
        """
        Open a headed browser for manual login, then save the session.
        Use this once per platform to capture cookies.
        """
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=False, slow_mo=100)
        profile = self._get_profile(platform)
        ctx = await browser.new_context(
            viewport=DEFAULT_VIEWPORT,
            user_agent=USER_AGENT,
        )
        page = await ctx.new_page()
        await page.goto(url)

        print(f"\n  Log in to {platform} in the browser window.")
        print("  Press Enter here when done...")
        input()

        # Save session
        state = await ctx.storage_state()
        with open(profile.cookies_file, "w") as f:
            json.dump(state, f, indent=2)
        profile.logged_in = True
        print(f"  Session saved to {profile.cookies_file}")

        await browser.close()
        await pw.stop()


# ---------------------------------------------------------------------------
#  CLI entry point for quick testing
# ---------------------------------------------------------------------------


async def _selftest():
    """Quick smoke test."""
    print("SCBE Headless Browser Driver — Self-Test")
    print("=" * 50)

    driver = HeadlessBrowserDriver(mode=DriverMode.HEADLESS, stealth=True)
    await driver.start()

    # Test 1: Navigate
    r = await driver.navigate("https://example.com")
    print(f"  Navigate: {'PASS' if r.success else 'FAIL'} ({r.duration_ms:.0f}ms)")

    # Test 2: Extract text
    r = await driver.extract_text("h1")
    print(f"  Extract:  {'PASS' if r.success else 'FAIL'} — {r.data.get('text', '')[:40] if r.data else 'N/A'}")

    # Test 3: Screenshot
    r = await driver.screenshot()
    print(f"  Screenshot: {'PASS' if r.success else 'FAIL'} — {r.screenshot_path}")

    # Test 4: Evaluate JS
    r = await driver.evaluate("document.title")
    print(f"  Evaluate: {'PASS' if r.success else 'FAIL'} — {r.data}")

    await driver.stop()
    print("\nAll tests complete.")


if __name__ == "__main__":
    asyncio.run(_selftest())
