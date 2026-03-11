"""
HYDRA Dual-View Browser — Headless + Optional Headed Mode
==========================================================

Runtime toggle between headless (production) and headed (debug/demo) browsing.
Supports Xvfb virtual framebuffer for headed mode on headless servers.

Usage:
    from hydra.dual_view import DualViewBrowser, ViewMode

    # Headless (default — production scraping)
    browser = DualViewBrowser(mode=ViewMode.HEADLESS)
    await browser.launch()
    page = await browser.new_page()
    await page.goto("https://example.com")

    # Headed (debug — see what the agent sees)
    browser = DualViewBrowser(mode=ViewMode.HEADED)
    await browser.launch()

    # Auto — headed if display available, else headless
    browser = DualViewBrowser(mode=ViewMode.AUTO)
    await browser.launch()

    # Switch at runtime
    await browser.switch_mode(ViewMode.HEADED)

    # VNC / screenshot stream for remote headed viewing
    screenshot = await browser.capture_view()
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


class ViewMode(str, Enum):
    HEADLESS = "headless"
    HEADED = "headed"
    AUTO = "auto"


@dataclass
class ViewConfig:
    """Configuration for browser view."""
    mode: ViewMode = ViewMode.AUTO
    viewport_width: int = 1366
    viewport_height: int = 768
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
    locale: str = "en-US"
    timezone: str = "America/Los_Angeles"
    user_data_dir: Optional[str] = None
    proxy: Optional[str] = None
    slow_mo: int = 0
    # Xvfb settings for headed mode on servers
    xvfb_display: str = ":99"
    xvfb_resolution: str = "1920x1080x24"


@dataclass
class ViewSnapshot:
    """A captured view of the browser state."""
    screenshot_b64: str
    url: str
    title: str
    viewport: Dict[str, int]
    mode: str
    timestamp: float


class DualViewBrowser:
    """
    Browser with runtime-switchable headless/headed modes.

    Key features:
    - Auto-detect display availability
    - Xvfb fallback for headed mode on servers
    - Screenshot streaming for remote viewing
    - Session preservation across mode switches
    - Multi-page/context support
    """

    def __init__(self, config: Optional[ViewConfig] = None):
        if not HAS_PLAYWRIGHT:
            raise RuntimeError("playwright not installed. Run: pip install 'playwright>=1.40.0'")
        self.config = config or ViewConfig()
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._contexts: Dict[str, BrowserContext] = {}
        self._pages: Dict[str, Page] = {}
        self._xvfb_proc: Optional[subprocess.Popen] = None
        self._active_mode: Optional[ViewMode] = None
        self._launched = False
        self._session_storage: Dict[str, Any] = {}

    # -- Display detection ---------------------------------------------------

    @staticmethod
    def has_display() -> bool:
        """Check if a graphical display is available."""
        if os.name == "nt" or os.uname().sysname == "Darwin":
            return True
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

    @staticmethod
    def has_xvfb() -> bool:
        """Check if Xvfb is available for virtual framebuffer."""
        return shutil.which("Xvfb") is not None or shutil.which("xvfb-run") is not None

    def _resolve_mode(self) -> ViewMode:
        """Resolve AUTO to a concrete mode."""
        if self.config.mode != ViewMode.AUTO:
            return self.config.mode
        if self.has_display():
            return ViewMode.HEADED
        if self.has_xvfb():
            return ViewMode.HEADED  # Will use Xvfb
        return ViewMode.HEADLESS

    # -- Xvfb management ----------------------------------------------------

    def _start_xvfb(self) -> None:
        """Start Xvfb virtual framebuffer if needed."""
        if self.has_display():
            return  # Real display available
        if not self.has_xvfb():
            return

        xvfb_bin = shutil.which("Xvfb")
        if not xvfb_bin:
            return

        self._xvfb_proc = subprocess.Popen(
            [xvfb_bin, self.config.xvfb_display, "-screen", "0", self.config.xvfb_resolution],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        os.environ["DISPLAY"] = self.config.xvfb_display

    def _stop_xvfb(self) -> None:
        """Stop Xvfb if we started it."""
        if self._xvfb_proc:
            self._xvfb_proc.terminate()
            self._xvfb_proc.wait(timeout=5)
            self._xvfb_proc = None

    # -- Lifecycle -----------------------------------------------------------

    async def launch(self) -> None:
        """Launch the browser in the configured mode."""
        self._active_mode = self._resolve_mode()
        is_headless = self._active_mode == ViewMode.HEADLESS

        if not is_headless:
            self._start_xvfb()

        self._playwright = await async_playwright().start()

        launch_args = {
            "headless": is_headless,
            "slow_mo": self.config.slow_mo,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-infobars",
            ],
        }
        if self.config.proxy:
            launch_args["proxy"] = {"server": self.config.proxy}

        self._browser = await self._playwright.chromium.launch(**launch_args)
        self._launched = True

    async def close(self) -> None:
        """Close browser, save session state, stop Xvfb."""
        # Save session state before closing
        for name, ctx in self._contexts.items():
            try:
                state = await ctx.storage_state()
                self._session_storage[name] = state
            except Exception:
                pass
            try:
                await ctx.close()
            except Exception:
                pass

        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

        self._stop_xvfb()
        self._contexts.clear()
        self._pages.clear()
        self._browser = None
        self._playwright = None
        self._launched = False

    # -- Mode switching (runtime) -------------------------------------------

    async def switch_mode(self, new_mode: ViewMode) -> None:
        """Switch between headless and headed at runtime.

        Preserves cookies/storage across the switch.
        """
        resolved = new_mode if new_mode != ViewMode.AUTO else (
            ViewMode.HEADED if self.has_display() or self.has_xvfb() else ViewMode.HEADLESS
        )
        if resolved == self._active_mode:
            return

        # Save current state
        page_urls = {}
        for name, page in self._pages.items():
            try:
                page_urls[name] = page.url
            except Exception:
                page_urls[name] = "about:blank"

        for name, ctx in self._contexts.items():
            try:
                self._session_storage[name] = await ctx.storage_state()
            except Exception:
                pass

        # Close current browser
        await self.close()

        # Relaunch with new mode
        self.config.mode = resolved
        await self.launch()

        # Restore contexts and navigate back
        for name, state in self._session_storage.items():
            ctx = await self.new_context(name, storage_state=state)
            if name in page_urls:
                page = await self.new_page(name)
                try:
                    await page.goto(page_urls[name], wait_until="domcontentloaded", timeout=15000)
                except Exception:
                    pass

    # -- Context / Page management ------------------------------------------

    async def new_context(
        self,
        name: str = "default",
        storage_state: Optional[Any] = None,
    ) -> BrowserContext:
        """Create or get a named browser context."""
        if name in self._contexts:
            return self._contexts[name]

        ctx_args: Dict[str, Any] = {
            "viewport": {"width": self.config.viewport_width, "height": self.config.viewport_height},
            "user_agent": self.config.user_agent,
            "locale": self.config.locale,
            "timezone_id": self.config.timezone,
        }
        if storage_state:
            ctx_args["storage_state"] = storage_state
        elif name in self._session_storage:
            ctx_args["storage_state"] = self._session_storage[name]

        ctx = await self._browser.new_context(**ctx_args)
        self._contexts[name] = ctx
        return ctx

    async def new_page(self, context_name: str = "default") -> Page:
        """Create or get a page in a named context."""
        if context_name in self._pages:
            return self._pages[context_name]

        ctx = await self.new_context(context_name)
        page = await ctx.new_page()
        self._pages[context_name] = page
        return page

    # -- View capture (for remote observation) ------------------------------

    async def capture_view(self, context_name: str = "default") -> ViewSnapshot:
        """Capture current browser view as a screenshot + metadata."""
        page = self._pages.get(context_name)
        if not page:
            raise ValueError(f"No page in context '{context_name}'")

        screenshot_bytes = await page.screenshot(type="png")
        return ViewSnapshot(
            screenshot_b64=base64.b64encode(screenshot_bytes).decode(),
            url=page.url,
            title=await page.title(),
            viewport={"width": self.config.viewport_width, "height": self.config.viewport_height},
            mode=self._active_mode.value if self._active_mode else "unknown",
            timestamp=time.time(),
        )

    # -- Status -------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return current browser status."""
        return {
            "launched": self._launched,
            "mode": self._active_mode.value if self._active_mode else None,
            "has_display": self.has_display(),
            "has_xvfb": self.has_xvfb(),
            "contexts": list(self._contexts.keys()),
            "pages": {k: (self._pages[k].url if k in self._pages else None) for k in self._contexts},
            "xvfb_running": self._xvfb_proc is not None,
        }

    # -- Convenience --------------------------------------------------------

    async def __aenter__(self):
        await self.launch()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()
        return False
