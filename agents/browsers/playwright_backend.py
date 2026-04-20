"""
Playwright Browser Backend
==========================

Async browser automation using Microsoft Playwright.

Requirements:
    pip install playwright
    playwright install chromium
"""

import asyncio
from typing import Optional, Dict, Any, List
from .base import BrowserBackend

try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class PlaywrightBackend(BrowserBackend):
    """
    Browser backend using Microsoft Playwright.

    Playwright provides:
    - Multi-browser support (Chromium, Firefox, WebKit)
    - Automatic waiting and smart selectors
    - Network interception
    - Async-first design
    - Excellent for modern web apps
    """

    name = "playwright"

    def __init__(
        self,
        browser_type: str = "chromium",
        headless: bool = True,
        slow_mo: int = 0,
        viewport: Optional[Dict[str, int]] = None
    ):
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright not installed. Run: pip install playwright && playwright install")

        self.browser_type = browser_type
        self.headless = headless
        self.slow_mo = slow_mo
        self.viewport = viewport or {"width": 1280, "height": 720}

        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def initialize(self) -> bool:
        """Initialize Playwright browser."""
        try:
            self._playwright = await async_playwright().start()

            # Select browser type
            browser_launcher = getattr(self._playwright, self.browser_type)

            self._browser = await browser_launcher.launch(
                headless=self.headless,
                slow_mo=self.slow_mo
            )

            self._context = await self._browser.new_context(
                viewport=self.viewport,
                user_agent="SCBE-GovernedBrowser/1.0 (Playwright)"
            )

            self._page = await self._context.new_page()

            print(f"[Playwright] Initialized {self.browser_type} (headless={self.headless})")
            return True

        except Exception as e:
            print(f"[Playwright] Initialization failed: {e}")
            return False

    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to URL."""
        response = await self._page.goto(url, wait_until="domcontentloaded")
        return {
            "url": url,
            "status": response.status if response else None,
            "ok": response.ok if response else False
        }

    async def click(self, selector: str) -> Dict[str, Any]:
        """Click element by selector."""
        try:
            await self._page.click(selector, timeout=5000)
            return {"selector": selector, "clicked": True}
        except Exception as e:
            return {"selector": selector, "clicked": False, "error": str(e)}

    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """Type text into element."""
        try:
            await self._page.fill(selector, text)
            return {"selector": selector, "typed": True, "length": len(text)}
        except Exception as e:
            return {"selector": selector, "typed": False, "error": str(e)}

    async def get_page_content(self) -> str:
        """Get page text content."""
        return await self._page.content()

    async def screenshot(self) -> bytes:
        """Take screenshot."""
        return await self._page.screenshot(type="png", full_page=False)

    async def execute_script(self, script: str) -> Any:
        """Execute JavaScript."""
        return await self._page.evaluate(script)

    async def get_current_url(self) -> str:
        """Get current page URL."""
        return self._page.url

    async def scroll(self, direction: str = "down", amount: int = 300) -> Dict[str, Any]:
        """Scroll the page."""
        delta = amount if direction == "down" else -amount
        await self._page.mouse.wheel(0, delta)
        return {"direction": direction, "amount": amount}

    async def find_element(self, selector: str) -> Optional[Dict[str, Any]]:
        """Find element by selector."""
        try:
            element = await self._page.wait_for_selector(selector, timeout=5000)
            if element:
                box = await element.bounding_box()
                return {
                    "selector": selector,
                    "found": True,
                    "visible": await element.is_visible(),
                    "box": box
                }
        except Exception:
            pass
        return {"selector": selector, "found": False}

    async def get_cookies(self) -> List[Dict[str, Any]]:
        """Get browser cookies."""
        return await self._context.cookies()

    async def set_cookie(self, cookie: Dict[str, Any]) -> bool:
        """Set a cookie."""
        try:
            await self._context.add_cookies([cookie])
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close browser."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        print("[Playwright] Browser closed")

    # ==========================================================================
    # Playwright-Specific Features
    # ==========================================================================

    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> bool:
        """Wait for element to appear."""
        try:
            await self._page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            return False

    async def wait_for_navigation(self, timeout: int = 30000) -> Dict[str, Any]:
        """Wait for navigation to complete."""
        try:
            await self._page.wait_for_load_state("domcontentloaded", timeout=timeout)
            return {"success": True, "url": self._page.url}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def intercept_network(self, pattern: str, handler) -> None:
        """Set up network request interception."""
        await self._page.route(pattern, handler)

    async def get_page_title(self) -> str:
        """Get page title."""
        return await self._page.title()

    async def press_key(self, key: str) -> Dict[str, Any]:
        """Press a keyboard key."""
        await self._page.keyboard.press(key)
        return {"key": key, "pressed": True}

    async def select_option(self, selector: str, value: str) -> Dict[str, Any]:
        """Select option from dropdown."""
        try:
            await self._page.select_option(selector, value)
            return {"selector": selector, "value": value, "selected": True}
        except Exception as e:
            return {"selector": selector, "selected": False, "error": str(e)}

    async def get_attribute(self, selector: str, attribute: str) -> Optional[str]:
        """Get element attribute."""
        element = await self._page.query_selector(selector)
        if element:
            return await element.get_attribute(attribute)
        return None

    async def get_text(self, selector: str) -> Optional[str]:
        """Get element text content."""
        element = await self._page.query_selector(selector)
        if element:
            return await element.text_content()
        return None

    async def hover(self, selector: str) -> Dict[str, Any]:
        """Hover over element."""
        try:
            await self._page.hover(selector)
            return {"selector": selector, "hovered": True}
        except Exception as e:
            return {"selector": selector, "hovered": False, "error": str(e)}

    async def screenshot_element(self, selector: str) -> Optional[bytes]:
        """Screenshot specific element."""
        try:
            element = await self._page.query_selector(selector)
            if element:
                return await element.screenshot(type="png")
        except Exception:
            pass
        return None

    async def pdf(self) -> bytes:
        """Generate PDF of page (Chromium only)."""
        return await self._page.pdf()

    async def emulate_device(self, device_name: str) -> bool:
        """Emulate a device (must be done before navigation)."""
        try:
            device = self._playwright.devices.get(device_name)
            if device:
                self._context = await self._browser.new_context(**device)
                self._page = await self._context.new_page()
                return True
        except Exception:
            pass
        return False

    async def block_resources(self, resource_types: List[str]) -> None:
        """Block specific resource types (images, fonts, etc.)."""
        async def block_handler(route):
            if route.request.resource_type in resource_types:
                await route.abort()
            else:
                await route.continue_()

        await self._page.route("**/*", block_handler)


# =============================================================================
# Example Usage
# =============================================================================

async def example_usage():
    """Example of using PlaywrightBackend with GovernedBrowser."""
    from .base import GovernedBrowser

    # Create backend
    backend = PlaywrightBackend(
        browser_type="chromium",
        headless=True
    )

    # Wrap with governance
    browser = GovernedBrowser(
        backend,
        agent_id="playwright-agent-001"
    )

    # Initialize
    if await browser.initialize():
        # All actions are now governed by SCBE
        result = await browser.navigate("https://example.com")
        print(f"Navigate result: {result}")

        # Take screenshot
        result = await browser.screenshot()
        print(f"Screenshot result: {result}")

        # Get summary
        browser.print_summary()

        # Close
        await browser.close()


if __name__ == "__main__":
    asyncio.run(example_usage())
