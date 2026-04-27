"""
Async Playwright browser runtime for SCBE browser agents.

Provides real browser automation behind the governance layer.
When Playwright is not installed, methods raise RuntimeError with
a helpful message — governance stubs (dry-run mode) remain available
in browser_agent.py and swarm_browser.py without this dependency.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger("scbe.agents.playwright_runtime")

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    _PW_AVAILABLE = True
except ImportError:
    _PW_AVAILABLE = False


class PlaywrightRuntime:
    """
    Async Playwright wrapper for governed browser agents.

    Supports both local browsing and remote display access via
    Chrome Remote Desktop. For multi-display use:

        from agents.remote_display import RemoteDisplayManager
        mgr = RemoteDisplayManager()
        await mgr.launch()
        await mgr.connect_display("gpu-box", pin="123456")

    Or use PlaywrightRuntime.open_remote_display() for single remote access
    alongside local browsing.
    """

    def __init__(self) -> None:
        self._pw: Any = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._remote_displays: dict = {}  # name → RemoteDisplayManager reference

    # -- lifecycle -----------------------------------------------------------

    async def launch(self, *, headless: bool = True, **kwargs: Any) -> None:
        if not _PW_AVAILABLE:
            raise RuntimeError(
                "playwright is not installed. "
                "Run: pip install playwright && python -m playwright install chromium"
            )
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=headless, **kwargs)
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()
        logger.info("PlaywrightRuntime launched (headless=%s)", headless)

    async def close(self) -> None:
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._pw:
            await self._pw.stop()
            self._pw = None
        self._page = None
        logger.info("PlaywrightRuntime closed")

    @property
    def is_connected(self) -> bool:
        return self._browser is not None and self._browser.is_connected()

    @property
    def current_url(self) -> str:
        if self._page:
            return self._page.url
        return ""

    # -- navigation ----------------------------------------------------------

    async def navigate(self, url: str, *, timeout: int = 30_000) -> str:
        self._require_page()
        response = await self._page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        logger.info("Navigated to %s (status=%s)", url, response.status if response else "?")
        return self._page.url

    async def go_back(self) -> None:
        self._require_page()
        await self._page.go_back()

    async def go_forward(self) -> None:
        self._require_page()
        await self._page.go_forward()

    # -- interaction ---------------------------------------------------------

    async def click(self, selector: str, *, timeout: int = 10_000) -> None:
        self._require_page()
        await self._page.click(selector, timeout=timeout)
        logger.debug("Clicked %s", selector)

    async def type_text(self, selector: str, text: str, *, delay: int = 0) -> None:
        self._require_page()
        await self._page.fill(selector, "")
        if delay:
            await self._page.type(selector, text, delay=delay)
        else:
            await self._page.fill(selector, text)
        logger.debug("Typed %d chars into %s", len(text), selector)

    async def submit_form(self, selector: str) -> None:
        self._require_page()
        await self._page.click(selector)
        logger.debug("Submitted form via %s", selector)

    async def select_option(self, selector: str, value: str) -> None:
        self._require_page()
        await self._page.select_option(selector, value)

    async def hover(self, selector: str) -> None:
        self._require_page()
        await self._page.hover(selector)

    # -- observation ---------------------------------------------------------

    async def screenshot(self, *, path: Optional[str] = None, full_page: bool = False) -> bytes:
        self._require_page()
        data = await self._page.screenshot(path=path, full_page=full_page)
        logger.debug("Screenshot taken (full_page=%s)", full_page)
        return data

    async def evaluate(self, script: str, *args: Any) -> Any:
        self._require_page()
        return await self._page.evaluate(script, *args)

    async def content(self) -> str:
        self._require_page()
        return await self._page.content()

    async def title(self) -> str:
        self._require_page()
        return await self._page.title()

    async def wait_for_selector(self, selector: str, *, timeout: int = 10_000) -> None:
        self._require_page()
        await self._page.wait_for_selector(selector, timeout=timeout)

    # -- remote display integration ------------------------------------------

    async def open_remote_display(
        self,
        name: str,
        *,
        host_id: Optional[str] = None,
        pin: Optional[str] = None,
        resolution: tuple = (1920, 1080),
    ) -> Any:
        """
        Open a Chrome Remote Desktop session as an additional display.

        Returns a DisplayHandle from RemoteDisplayManager. The remote display
        runs in its own BrowserContext, isolated from local browsing.

        Args:
            name: Human-readable name (e.g. "gpu-box")
            host_id: CRD host ID (optional — uses first available if None)
            pin: CRD PIN (optional — waits for manual entry if None)
            resolution: Remote display resolution
        """
        from agents.remote_display import RemoteDisplayManager

        if not hasattr(self, "_display_mgr") or self._display_mgr is None:
            self._display_mgr = RemoteDisplayManager()
            self._display_mgr._pw = self._pw
            self._display_mgr._browser = self._browser

        handle = await self._display_mgr.connect_display(
            name, host_id=host_id, pin=pin, resolution=resolution,
        )
        self._remote_displays[name] = handle
        logger.info("Remote display '%s' opened via PlaywrightRuntime", name)
        return handle

    async def remote_screenshot(self, name: str, *, path: Optional[str] = None) -> bytes:
        """Take a screenshot of a remote display by name."""
        if not hasattr(self, "_display_mgr") or self._display_mgr is None:
            raise RuntimeError(f"No remote displays open — call open_remote_display() first")
        return await self._display_mgr.screenshot(name, path=path)

    async def remote_click(self, name: str, x: int, y: int) -> None:
        """Click at pixel coordinates on a remote display."""
        if not hasattr(self, "_display_mgr") or self._display_mgr is None:
            raise RuntimeError(f"No remote displays open")
        await self._display_mgr.click(name, x, y)

    async def remote_type(self, name: str, text: str) -> None:
        """Type text on a remote display."""
        if not hasattr(self, "_display_mgr") or self._display_mgr is None:
            raise RuntimeError(f"No remote displays open")
        await self._display_mgr.type_text(name, text)

    async def remote_keys(self, name: str, keys: str) -> None:
        """Send key combination to a remote display."""
        if not hasattr(self, "_display_mgr") or self._display_mgr is None:
            raise RuntimeError(f"No remote displays open")
        await self._display_mgr.send_keys(name, keys)

    @property
    def remote_display_names(self) -> list:
        return list(self._remote_displays.keys())

    # -- internal ------------------------------------------------------------

    def _require_page(self) -> None:
        if self._page is None:
            raise RuntimeError("PlaywrightRuntime not launched — call await runtime.launch() first")
