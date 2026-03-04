"""
HYDRA Browser Backends — AI-Independent
========================================

Standalone browser automation backends for HYDRA limbs.
No Claude/vendor dependency — uses Playwright, Selenium, or raw CDP.

Each backend implements the same async interface:
    initialize(), navigate(), click(), type_text(),
    screenshot(), scroll(), get_page_content(), close()
"""

import asyncio
import base64
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BrowserBackend(ABC):
    """Abstract interface for all browser backends."""

    @abstractmethod
    async def initialize(self) -> None: ...

    @abstractmethod
    async def navigate(self, url: str) -> Dict[str, Any]: ...

    @abstractmethod
    async def click(self, selector: str) -> Dict[str, Any]: ...

    @abstractmethod
    async def type_text(self, selector: str, text: str) -> Dict[str, Any]: ...

    @abstractmethod
    async def screenshot(self) -> bytes: ...

    @abstractmethod
    async def scroll(self, direction: str = "down", amount: int = 300) -> Dict[str, Any]: ...

    @abstractmethod
    async def get_page_content(self) -> str: ...

    @abstractmethod
    async def close(self) -> None: ...


# ---------------------------------------------------------------------------
# Playwright Backend (primary)
# ---------------------------------------------------------------------------

class PlaywrightBackend(BrowserBackend):
    """Primary backend using Playwright (async, headless).

    Requires:
        pip install playwright && python -m playwright install chromium
    """

    def __init__(self, headless: bool = True, browser_type: str = "chromium"):
        self._headless = headless
        self._browser_type = browser_type
        self._browser = None
        self._context = None
        self._page = None

    async def initialize(self) -> None:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError(
                "playwright is required for PlaywrightBackend.\n"
                "Install with:  pip install playwright && python -m playwright install chromium"
            )
        self._pw = await async_playwright().__aenter__()
        launcher = getattr(self._pw, self._browser_type)
        self._browser = await launcher.launch(headless=self._headless)
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()

    async def navigate(self, url: str) -> Dict[str, Any]:
        resp = await self._page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        return {
            "url": self._page.url,
            "status": resp.status if resp else None,
            "title": await self._page.title(),
        }

    async def click(self, selector: str) -> Dict[str, Any]:
        await self._page.click(selector, timeout=10_000)
        return {"clicked": selector}

    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        await self._page.fill(selector, text, timeout=10_000)
        return {"typed": len(text), "selector": selector}

    async def screenshot(self) -> bytes:
        return await self._page.screenshot(type="png")

    async def scroll(self, direction: str = "down", amount: int = 300) -> Dict[str, Any]:
        delta = amount if direction == "down" else -amount
        await self._page.mouse.wheel(0, delta)
        return {"scrolled": direction, "amount": amount}

    async def get_page_content(self) -> str:
        return await self._page.content()

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
        if hasattr(self, "_pw") and self._pw:
            await self._pw.__aexit__(None, None, None)


# ---------------------------------------------------------------------------
# Selenium Backend (fallback)
# ---------------------------------------------------------------------------

class SeleniumBackend(BrowserBackend):
    """Fallback backend using Selenium WebDriver.

    Requires:
        pip install selenium webdriver-manager
    """

    def __init__(self, headless: bool = True):
        self._headless = headless
        self._driver = None

    async def initialize(self) -> None:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
        except ImportError:
            raise ImportError(
                "selenium is required for SeleniumBackend.\n"
                "Install with:  pip install selenium webdriver-manager"
            )

        opts = Options()
        if self._headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")

        loop = asyncio.get_event_loop()
        self._driver = await loop.run_in_executor(None, lambda: webdriver.Chrome(options=opts))

    async def navigate(self, url: str) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._driver.get, url)
        return {
            "url": self._driver.current_url,
            "title": self._driver.title,
        }

    async def click(self, selector: str) -> Dict[str, Any]:
        from selenium.webdriver.common.by import By
        loop = asyncio.get_event_loop()
        el = await loop.run_in_executor(
            None, self._driver.find_element, By.CSS_SELECTOR, selector
        )
        await loop.run_in_executor(None, el.click)
        return {"clicked": selector}

    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        from selenium.webdriver.common.by import By
        loop = asyncio.get_event_loop()
        el = await loop.run_in_executor(
            None, self._driver.find_element, By.CSS_SELECTOR, selector
        )
        await loop.run_in_executor(None, el.clear)
        await loop.run_in_executor(None, el.send_keys, text)
        return {"typed": len(text), "selector": selector}

    async def screenshot(self) -> bytes:
        loop = asyncio.get_event_loop()
        png_b64 = await loop.run_in_executor(
            None, self._driver.get_screenshot_as_base64
        )
        return base64.b64decode(png_b64)

    async def scroll(self, direction: str = "down", amount: int = 300) -> Dict[str, Any]:
        delta = amount if direction == "down" else -amount
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._driver.execute_script,
            f"window.scrollBy(0, {delta})"
        )
        return {"scrolled": direction, "amount": amount}

    async def get_page_content(self) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self._driver.page_source)

    async def close(self) -> None:
        if self._driver:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._driver.quit)


# ---------------------------------------------------------------------------
# Chrome DevTools Protocol Backend (minimal/advanced)
# ---------------------------------------------------------------------------

class CDPBackend(BrowserBackend):
    """Minimal Chrome DevTools Protocol backend via websockets.

    Requires:
        pip install websockets

    Connect to an already-running Chrome instance:
        chrome --remote-debugging-port=9222
    """

    def __init__(self, cdp_url: str = "http://localhost:9222"):
        self._cdp_url = cdp_url
        self._ws = None
        self._msg_id = 0

    async def initialize(self) -> None:
        try:
            import websockets  # noqa: F401
        except ImportError:
            raise ImportError(
                "websockets is required for CDPBackend.\n"
                "Install with:  pip install websockets"
            )
        import aiohttp
        # Discover the first available debugging target
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self._cdp_url}/json") as resp:
                targets = await resp.json()

        page_targets = [t for t in targets if t.get("type") == "page"]
        if not page_targets:
            raise RuntimeError("No page target found on CDP endpoint")

        ws_url = page_targets[0]["webSocketDebuggerUrl"]
        import websockets
        self._ws = await websockets.connect(ws_url, max_size=10 * 1024 * 1024)

    async def _send(self, method: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        self._msg_id += 1
        msg = {"id": self._msg_id, "method": method, "params": params or {}}
        await self._ws.send(json.dumps(msg))
        while True:
            raw = await self._ws.recv()
            data = json.loads(raw)
            if data.get("id") == self._msg_id:
                return data.get("result", {})

    async def navigate(self, url: str) -> Dict[str, Any]:
        result = await self._send("Page.navigate", {"url": url})
        await asyncio.sleep(1)  # simple wait for load
        return {"url": url, "frameId": result.get("frameId")}

    async def click(self, selector: str) -> Dict[str, Any]:
        js = f'document.querySelector("{selector}").click()'
        await self._send("Runtime.evaluate", {"expression": js})
        return {"clicked": selector}

    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        js = (
            f'let el = document.querySelector("{selector}"); '
            f'el.focus(); el.value = {json.dumps(text)}; '
            f'el.dispatchEvent(new Event("input", {{bubbles:true}}))'
        )
        await self._send("Runtime.evaluate", {"expression": js})
        return {"typed": len(text), "selector": selector}

    async def screenshot(self) -> bytes:
        result = await self._send("Page.captureScreenshot", {"format": "png"})
        return base64.b64decode(result.get("data", ""))

    async def scroll(self, direction: str = "down", amount: int = 300) -> Dict[str, Any]:
        delta = amount if direction == "down" else -amount
        await self._send(
            "Runtime.evaluate",
            {"expression": f"window.scrollBy(0, {delta})"},
        )
        return {"scrolled": direction, "amount": amount}

    async def get_page_content(self) -> str:
        result = await self._send(
            "Runtime.evaluate",
            {"expression": "document.documentElement.outerHTML"},
        )
        return result.get("result", {}).get("value", "")

    async def close(self) -> None:
        if self._ws:
            await self._ws.close()
