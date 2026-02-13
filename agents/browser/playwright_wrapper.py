"""
@file playwright_wrapper.py
@module agents/browser/playwright_wrapper
@layer Layer 13, Layer 14
@component Browser Control with Timeout Safety
@version 1.0.0

Safe browser automation wrapper using Playwright with built-in timeouts
and action logging for governance auditing.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import platform
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class BrowserActionType(Enum):
    """Types of browser actions for governance tracking."""
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCREENSHOT = "screenshot"
    SCROLL = "scroll"
    WAIT = "wait"
    EXTRACT = "extract"
    EVALUATE = "evaluate"


@dataclass
class BrowserAction:
    """Record of a browser action for audit trail."""
    action_type: BrowserActionType
    target: str
    params: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    success: bool = False
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class BrowserConfig:
    """Configuration for the browser wrapper."""
    headless: bool = True
    default_timeout_ms: int = 30000
    navigation_timeout_ms: int = 60000
    screenshot_timeout_ms: int = 10000
    viewport_width: int = 1280
    viewport_height: int = 720
    user_agent: Optional[str] = None

    # Optional browser selection (useful for Linux system Chrome)
    browser_channel: Optional[str] = None
    executable_path: Optional[str] = None

    # Safety limits
    max_actions_per_session: int = 100
    max_navigation_depth: int = 10
    blocked_domains: List[str] = field(default_factory=list)
    allowed_domains: Optional[List[str]] = None


@dataclass
class ScreenshotResult:
    """Result of a screenshot operation."""
    data: bytes
    width: int
    height: int
    format: str = "png"
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_base64(self) -> str:
        """Convert screenshot to base64 string."""
        return base64.b64encode(self.data).decode('utf-8')


class PlaywrightWrapper:
    """
    Safe browser automation wrapper with timeout controls.

    Provides a contained interface for browser interactions with:
    - Configurable timeouts for all operations
    - Action logging for governance auditing
    - Domain filtering for navigation safety
    - Action limits to prevent runaway sessions

    Example:
        async with PlaywrightWrapper() as browser:
            await browser.navigate("https://example.com")
            screenshot = await browser.screenshot()
            text = await browser.extract_text("body")
    """

    def __init__(self, config: Optional[BrowserConfig] = None):
        """
        Initialize the browser wrapper.

        Args:
            config: Browser configuration (uses defaults if not provided)
        """
        self.config = config or BrowserConfig()
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._action_history: List[BrowserAction] = []
        self._navigation_depth = 0
        self._is_initialized = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def _resolve_linux_chrome_path(self) -> Optional[str]:
        """Resolve a Linux Chrome/Chromium executable if available."""
        env_path = os.environ.get("SCBE_CHROME_PATH")
        if env_path:
            return env_path

        candidates = [
            "google-chrome-stable",
            "google-chrome",
            "chromium-browser",
            "chromium",
            "chrome",
        ]
        for candidate in candidates:
            path = shutil.which(candidate)
            if path:
                return path
        return None

    def _build_launch_options(self) -> Dict[str, Any]:
        """Build Playwright launch options with Linux Chrome support."""
        options: Dict[str, Any] = {"headless": self.config.headless}

        if self.config.executable_path:
            options["executable_path"] = self.config.executable_path
            return options

        if self.config.browser_channel:
            options["channel"] = self.config.browser_channel
            return options

        if platform.system() == "Linux":
            linux_path = self._resolve_linux_chrome_path()
            if linux_path:
                options["executable_path"] = linux_path

        return options

    async def initialize(self):
        """
        Initialize the browser instance.

        Raises:
            RuntimeError: If Playwright is not installed
        """
        if self._is_initialized:
            return

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && playwright install"
            )

        self._playwright = await async_playwright().start()
        launch_options = self._build_launch_options()
        self._browser = await self._playwright.chromium.launch(**launch_options)

        context_options = {
            "viewport": {
                "width": self.config.viewport_width,
                "height": self.config.viewport_height
            }
        }
        if self.config.user_agent:
            context_options["user_agent"] = self.config.user_agent

        self._context = await self._browser.new_context(**context_options)
        self._page = await self._context.new_page()

        # Set default timeouts
        self._page.set_default_timeout(self.config.default_timeout_ms)
        self._page.set_default_navigation_timeout(self.config.navigation_timeout_ms)

        self._is_initialized = True
        logger.info("Browser initialized successfully")

    async def close(self):
        """Close the browser and cleanup resources."""
        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

        self._is_initialized = False
        logger.info("Browser closed")

    def _check_action_limits(self):
        """
        Check if action limits have been reached.

        Raises:
            RuntimeError: If action limits exceeded
        """
        if len(self._action_history) >= self.config.max_actions_per_session:
            raise RuntimeError(
                f"Max actions per session ({self.config.max_actions_per_session}) exceeded"
            )

    def _check_domain_allowed(self, url: str) -> bool:
        """
        Check if a URL's domain is allowed.

        Args:
            url: URL to check

        Returns:
            True if domain is allowed
        """
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Check blocked domains
            for blocked in self.config.blocked_domains:
                if blocked.lower() in domain:
                    return False

            # Check allowed domains (if whitelist is set)
            if self.config.allowed_domains is not None:
                return any(
                    allowed.lower() in domain
                    for allowed in self.config.allowed_domains
                )

            return True
        except Exception:
            return False

    def _record_action(
        self,
        action_type: BrowserActionType,
        target: str,
        params: Dict[str, Any],
        success: bool,
        error: Optional[str] = None,
        duration_ms: float = 0.0
    ):
        """Record an action in the history."""
        action = BrowserAction(
            action_type=action_type,
            target=target,
            params=params,
            success=success,
            error=error,
            duration_ms=duration_ms
        )
        self._action_history.append(action)

    async def _execute_with_timeout(
        self,
        coro: Callable,
        timeout_ms: int,
        action_type: BrowserActionType,
        target: str,
        params: Dict[str, Any]
    ) -> Any:
        """
        Execute a coroutine with timeout and logging.

        Args:
            coro: Coroutine to execute
            timeout_ms: Timeout in milliseconds
            action_type: Type of action for logging
            target: Target element/URL
            params: Action parameters

        Returns:
            Result of the coroutine

        Raises:
            asyncio.TimeoutError: If operation times out
        """
        self._check_action_limits()

        start_time = asyncio.get_event_loop().time()
        try:
            result = await asyncio.wait_for(
                coro,
                timeout=timeout_ms / 1000.0
            )
            duration = (asyncio.get_event_loop().time() - start_time) * 1000
            self._record_action(action_type, target, params, True, duration_ms=duration)
            return result
        except asyncio.TimeoutError:
            duration = (asyncio.get_event_loop().time() - start_time) * 1000
            error_msg = f"Operation timed out after {timeout_ms}ms"
            self._record_action(
                action_type, target, params, False,
                error=error_msg, duration_ms=duration
            )
            raise
        except Exception as e:
            duration = (asyncio.get_event_loop().time() - start_time) * 1000
            self._record_action(
                action_type, target, params, False,
                error=str(e), duration_ms=duration
            )
            raise

    async def navigate(
        self,
        url: str,
        timeout_ms: Optional[int] = None,
        wait_until: str = "domcontentloaded"
    ) -> str:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to
            timeout_ms: Navigation timeout (uses default if not specified)
            wait_until: Wait condition ('load', 'domcontentloaded', 'networkidle')

        Returns:
            Final URL after navigation

        Raises:
            ValueError: If domain is not allowed
            asyncio.TimeoutError: If navigation times out
        """
        if not self._is_initialized:
            await self.initialize()

        if not self._check_domain_allowed(url):
            raise ValueError(f"Domain not allowed: {url}")

        if self._navigation_depth >= self.config.max_navigation_depth:
            raise RuntimeError(
                f"Max navigation depth ({self.config.max_navigation_depth}) exceeded"
            )

        timeout = timeout_ms or self.config.navigation_timeout_ms

        async def _nav():
            response = await self._page.goto(url, wait_until=wait_until)
            self._navigation_depth += 1
            return self._page.url

        return await self._execute_with_timeout(
            _nav(),
            timeout,
            BrowserActionType.NAVIGATE,
            url,
            {"wait_until": wait_until}
        )

    async def click(
        self,
        selector: str,
        timeout_ms: Optional[int] = None
    ):
        """
        Click an element.

        Args:
            selector: CSS selector for element
            timeout_ms: Click timeout

        Raises:
            asyncio.TimeoutError: If operation times out
        """
        if not self._is_initialized:
            raise RuntimeError("Browser not initialized")

        timeout = timeout_ms or self.config.default_timeout_ms

        return await self._execute_with_timeout(
            self._page.click(selector, timeout=timeout),
            timeout,
            BrowserActionType.CLICK,
            selector,
            {}
        )

    async def type_text(
        self,
        selector: str,
        text: str,
        timeout_ms: Optional[int] = None,
        delay_ms: int = 50
    ):
        """
        Type text into an element.

        Args:
            selector: CSS selector for input element
            text: Text to type
            timeout_ms: Operation timeout
            delay_ms: Delay between keystrokes

        Raises:
            asyncio.TimeoutError: If operation times out
        """
        if not self._is_initialized:
            raise RuntimeError("Browser not initialized")

        timeout = timeout_ms or self.config.default_timeout_ms

        async def _type():
            await self._page.fill(selector, text, timeout=timeout)

        return await self._execute_with_timeout(
            _type(),
            timeout,
            BrowserActionType.TYPE,
            selector,
            {"text_length": len(text)}
        )

    async def screenshot(
        self,
        selector: Optional[str] = None,
        full_page: bool = False,
        timeout_ms: Optional[int] = None
    ) -> ScreenshotResult:
        """
        Take a screenshot.

        Args:
            selector: Optional CSS selector for element screenshot
            full_page: Capture full scrollable page
            timeout_ms: Screenshot timeout

        Returns:
            ScreenshotResult with image data

        Raises:
            asyncio.TimeoutError: If operation times out
        """
        if not self._is_initialized:
            raise RuntimeError("Browser not initialized")

        timeout = timeout_ms or self.config.screenshot_timeout_ms

        async def _screenshot():
            options = {"type": "png", "full_page": full_page}

            if selector:
                element = await self._page.query_selector(selector)
                if element:
                    data = await element.screenshot(**options)
                else:
                    raise ValueError(f"Element not found: {selector}")
            else:
                data = await self._page.screenshot(**options)

            viewport = self._page.viewport_size
            return ScreenshotResult(
                data=data,
                width=viewport["width"] if viewport else self.config.viewport_width,
                height=viewport["height"] if viewport else self.config.viewport_height
            )

        return await self._execute_with_timeout(
            _screenshot(),
            timeout,
            BrowserActionType.SCREENSHOT,
            selector or "full_page",
            {"full_page": full_page}
        )

    async def scroll(
        self,
        direction: str = "down",
        amount: int = 300,
        timeout_ms: Optional[int] = None
    ):
        """
        Scroll the page.

        Args:
            direction: 'up', 'down', 'left', 'right'
            amount: Pixels to scroll
            timeout_ms: Operation timeout
        """
        if not self._is_initialized:
            raise RuntimeError("Browser not initialized")

        timeout = timeout_ms or self.config.default_timeout_ms

        scroll_map = {
            "down": f"window.scrollBy(0, {amount})",
            "up": f"window.scrollBy(0, -{amount})",
            "right": f"window.scrollBy({amount}, 0)",
            "left": f"window.scrollBy(-{amount}, 0)"
        }

        script = scroll_map.get(direction.lower())
        if not script:
            raise ValueError(f"Invalid scroll direction: {direction}")

        async def _scroll():
            await self._page.evaluate(script)

        return await self._execute_with_timeout(
            _scroll(),
            timeout,
            BrowserActionType.SCROLL,
            direction,
            {"amount": amount}
        )

    async def extract_text(
        self,
        selector: str,
        timeout_ms: Optional[int] = None
    ) -> str:
        """
        Extract text content from an element.

        Args:
            selector: CSS selector for element
            timeout_ms: Operation timeout

        Returns:
            Text content of element
        """
        if not self._is_initialized:
            raise RuntimeError("Browser not initialized")

        timeout = timeout_ms or self.config.default_timeout_ms

        async def _extract():
            element = await self._page.query_selector(selector)
            if element:
                return await element.text_content()
            return ""

        return await self._execute_with_timeout(
            _extract(),
            timeout,
            BrowserActionType.EXTRACT,
            selector,
            {}
        )

    async def get_page_content(self) -> str:
        """
        Get the full HTML content of the page.

        Returns:
            HTML content as string
        """
        if not self._is_initialized:
            raise RuntimeError("Browser not initialized")

        return await self._page.content()

    async def evaluate(
        self,
        script: str,
        timeout_ms: Optional[int] = None
    ) -> Any:
        """
        Evaluate JavaScript in the page context.

        Args:
            script: JavaScript code to evaluate
            timeout_ms: Operation timeout

        Returns:
            Result of the evaluation

        Note:
            Use with caution - arbitrary JS execution has security implications.
        """
        if not self._is_initialized:
            raise RuntimeError("Browser not initialized")

        timeout = timeout_ms or self.config.default_timeout_ms

        return await self._execute_with_timeout(
            self._page.evaluate(script),
            timeout,
            BrowserActionType.EVALUATE,
            "script",
            {"script_length": len(script)}
        )

    def get_action_history(self) -> List[BrowserAction]:
        """Get the action history for auditing."""
        return self._action_history.copy()

    def get_current_url(self) -> Optional[str]:
        """Get the current page URL."""
        if self._page:
            return self._page.url
        return None

    def reset_session(self):
        """Reset session counters (but keep browser open)."""
        self._action_history.clear()
        self._navigation_depth = 0
        logger.info("Session reset")


async def create_browser(
    headless: bool = True,
    timeout_ms: int = 30000,
    allowed_domains: Optional[List[str]] = None,
    browser_channel: Optional[str] = None,
    executable_path: Optional[str] = None,
) -> PlaywrightWrapper:
    """
    Factory function to create and initialize a browser wrapper.

    Args:
        headless: Run in headless mode
        timeout_ms: Default timeout for operations
        allowed_domains: Optional whitelist of allowed domains
        browser_channel: Optional Playwright channel (e.g. "chrome")
        executable_path: Optional explicit browser executable path

    Returns:
        Initialized PlaywrightWrapper
    """
    config = BrowserConfig(
        headless=headless,
        default_timeout_ms=timeout_ms,
        allowed_domains=allowed_domains,
        browser_channel=browser_channel,
        executable_path=executable_path,
    )
    browser = PlaywrightWrapper(config)
    await browser.initialize()
    return browser
