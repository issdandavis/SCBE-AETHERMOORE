"""
Chrome Remote Desktop multi-display runtime for SCBE browser agents.

Manages multiple remote displays from a single service by driving the
Chrome Remote Desktop web client (remotedesktop.google.com) via Playwright.
Each remote machine gets its own browser context and display handle.

Architecture:
  RemoteDisplayManager
    ├─ Display "workstation-1" (BrowserContext → CRD page → canvas relay)
    ├─ Display "gpu-box"       (BrowserContext → CRD page → canvas relay)
    └─ Display "build-server"  (BrowserContext → CRD page → canvas relay)

Input is relayed to the CRD canvas element via synthetic mouse/keyboard
events. Screenshots are captured from the CRD video stream canvas.

Usage:
    mgr = RemoteDisplayManager()
    await mgr.launch()
    await mgr.connect_display("gpu-box", pin="123456")
    await mgr.send_keys("gpu-box", "ls -la\n")
    shot = await mgr.screenshot("gpu-box")
    await mgr.close()
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("scbe.agents.remote_display")

try:
    from playwright.async_api import (
        async_playwright,
        Browser,
        BrowserContext,
        Page,
        Playwright,
    )
    _PW_AVAILABLE = True
except ImportError:
    _PW_AVAILABLE = False

# Chrome Remote Desktop URLs
CRD_BASE = "https://remotedesktop.google.com"
CRD_ACCESS = f"{CRD_BASE}/access"
CRD_SUPPORT = f"{CRD_BASE}/support"

# Selectors for CRD web client elements
_CRD_SELECTORS = {
    "machine_list": "[data-host-id]",
    "connect_button": "button[data-action='connect'], [aria-label='Connect']",
    "pin_input": "input[type='password'], input[aria-label='PIN']",
    "pin_submit": "button[type='submit'], button[aria-label='Connect']",
    "canvas": "canvas, .remoting-canvas, [class*='desktop-viewport'] canvas",
    "fullscreen_btn": "button[aria-label='Full screen'], [data-action='fullscreen']",
    "disconnect_btn": "button[aria-label='Disconnect'], [data-action='disconnect']",
    "toolbar": ".toolbar, [class*='toolbar']",
}


@dataclass
class DisplayHandle:
    """A connected remote display session."""

    name: str
    host_id: str
    context: Any  # BrowserContext
    page: Any  # Page
    connected: bool = False
    resolution: Tuple[int, int] = (1920, 1080)
    canvas_bounds: Optional[Dict[str, float]] = None


class RemoteDisplayManager:
    """
    Manages multiple Chrome Remote Desktop sessions via Playwright.

    Each display runs in an isolated BrowserContext so cookies, auth state,
    and CRD sessions don't collide. The manager presents a unified API:
    click/type/screenshot/send_keys addressed by display name.
    """

    def __init__(self) -> None:
        self._pw: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._displays: Dict[str, DisplayHandle] = {}
        self._user_data_dir: Optional[str] = None

    # -- lifecycle -----------------------------------------------------------

    async def launch(
        self,
        *,
        headless: bool = False,
        user_data_dir: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Launch the browser engine.

        Args:
            headless: CRD requires visible browser for WebRTC; default False.
            user_data_dir: Chrome profile dir with Google auth already signed in.
                          If None, you'll need to sign in manually on first run.
        """
        if not _PW_AVAILABLE:
            raise RuntimeError(
                "playwright is not installed. "
                "Run: pip install playwright && python -m playwright install chromium"
            )
        self._pw = await async_playwright().start()
        self._user_data_dir = user_data_dir

        if user_data_dir:
            # Persistent context preserves Google sign-in
            ctx = await self._pw.chromium.launch_persistent_context(
                user_data_dir,
                headless=headless,
                viewport={"width": 1920, "height": 1080},
                **kwargs,
            )
            self._browser = ctx.browser
            # Store the default context but don't use it for displays
        else:
            self._browser = await self._pw.chromium.launch(
                headless=headless, **kwargs
            )

        logger.info("RemoteDisplayManager launched (headless=%s)", headless)

    async def close(self) -> None:
        """Disconnect all displays and shut down."""
        for name in list(self._displays):
            await self.disconnect_display(name)
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._pw:
            await self._pw.stop()
            self._pw = None
        logger.info("RemoteDisplayManager closed")

    @property
    def display_names(self) -> List[str]:
        return list(self._displays.keys())

    @property
    def connected_displays(self) -> List[str]:
        return [n for n, d in self._displays.items() if d.connected]

    # -- display management --------------------------------------------------

    async def connect_display(
        self,
        name: str,
        *,
        host_id: Optional[str] = None,
        pin: Optional[str] = None,
        resolution: Tuple[int, int] = (1920, 1080),
        timeout: int = 60_000,
    ) -> DisplayHandle:
        """
        Connect to a remote machine via Chrome Remote Desktop.

        Args:
            name: Human-readable display name (e.g. "gpu-box").
            host_id: CRD host ID. If None, connects to the first available machine.
            pin: PIN for CRD access. If None, waits for user to enter it.
            resolution: Viewport resolution for the display context.
            timeout: Connection timeout in ms.

        Returns:
            DisplayHandle for the connected display.
        """
        self._require_browser()

        if name in self._displays:
            raise ValueError(f"Display '{name}' already exists — disconnect first")

        # Each display gets its own isolated context
        ctx = await self._browser.new_context(
            viewport={"width": resolution[0], "height": resolution[1]},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/130.0.0.0 Safari/537.36"
            ),
        )
        page = await ctx.new_page()

        handle = DisplayHandle(
            name=name,
            host_id=host_id or "",
            context=ctx,
            page=page,
            resolution=resolution,
        )
        self._displays[name] = handle

        # Navigate to CRD access page
        await page.goto(CRD_ACCESS, wait_until="networkidle", timeout=timeout)
        logger.info("Display '%s': navigated to CRD access page", name)

        # Wait for machine list or sign-in prompt
        try:
            await page.wait_for_selector(
                f"{_CRD_SELECTORS['machine_list']}, input[type='email']",
                timeout=timeout,
            )
        except Exception:
            logger.warning("Display '%s': timed out waiting for CRD UI", name)

        # If a specific host_id is given, click it
        if host_id:
            try:
                await page.click(f"[data-host-id='{host_id}']", timeout=10_000)
                logger.info("Display '%s': selected host %s", name, host_id)
            except Exception:
                logger.warning("Display '%s': host_id '%s' not found, trying first machine", name, host_id)
                await self._click_first_machine(page)
        else:
            await self._click_first_machine(page)

        # Enter PIN if provided
        if pin:
            await self._enter_pin(page, pin, timeout=timeout)

        # Wait for the CRD canvas to appear (means we're connected)
        try:
            await page.wait_for_selector(_CRD_SELECTORS["canvas"], timeout=timeout)
            handle.connected = True
            handle.canvas_bounds = await self._get_canvas_bounds(page)
            logger.info("Display '%s': connected (canvas bounds=%s)", name, handle.canvas_bounds)
        except Exception:
            logger.warning("Display '%s': canvas not found — may need manual PIN entry", name)

        return handle

    async def disconnect_display(self, name: str) -> None:
        """Disconnect and clean up a remote display session."""
        handle = self._displays.pop(name, None)
        if not handle:
            return
        try:
            if handle.connected:
                try:
                    await handle.page.click(_CRD_SELECTORS["disconnect_btn"], timeout=3_000)
                except Exception:
                    pass
            await handle.context.close()
        except Exception:
            pass
        logger.info("Display '%s': disconnected", name)

    # -- input relay ---------------------------------------------------------

    async def click(
        self,
        display: str,
        x: int,
        y: int,
        *,
        button: str = "left",
        click_count: int = 1,
    ) -> None:
        """Click at pixel coordinates on the remote display's CRD canvas."""
        handle = self._get_display(display)
        cx, cy = self._canvas_coords(handle, x, y)
        await handle.page.mouse.click(cx, cy, button=button, click_count=click_count)
        logger.debug("Display '%s': click (%d, %d) → canvas (%d, %d)", display, x, y, cx, cy)

    async def move_mouse(self, display: str, x: int, y: int) -> None:
        """Move mouse to pixel coordinates on the remote display."""
        handle = self._get_display(display)
        cx, cy = self._canvas_coords(handle, x, y)
        await handle.page.mouse.move(cx, cy)

    async def type_text(self, display: str, text: str, *, delay: int = 50) -> None:
        """Type text on the remote display via keyboard events."""
        handle = self._get_display(display)
        # Focus the CRD canvas first
        try:
            await handle.page.click(_CRD_SELECTORS["canvas"], timeout=3_000)
        except Exception:
            pass
        await handle.page.keyboard.type(text, delay=delay)
        logger.debug("Display '%s': typed %d chars", display, len(text))

    async def send_keys(self, display: str, keys: str) -> None:
        """
        Send key combination to the remote display.

        Args:
            keys: Playwright key descriptor, e.g. "Control+c", "Enter", "Tab".
        """
        handle = self._get_display(display)
        try:
            await handle.page.click(_CRD_SELECTORS["canvas"], timeout=3_000)
        except Exception:
            pass
        await handle.page.keyboard.press(keys)
        logger.debug("Display '%s': pressed %s", display, keys)

    async def scroll(self, display: str, x: int, y: int, delta_y: int) -> None:
        """Scroll at coordinates on the remote display."""
        handle = self._get_display(display)
        cx, cy = self._canvas_coords(handle, x, y)
        await handle.page.mouse.move(cx, cy)
        await handle.page.mouse.wheel(0, delta_y)

    # -- observation ---------------------------------------------------------

    async def screenshot(
        self,
        display: str,
        *,
        path: Optional[str] = None,
    ) -> bytes:
        """Capture screenshot of the remote display via the CRD canvas."""
        handle = self._get_display(display)

        # Try to capture just the canvas element for a clean remote-only shot
        try:
            canvas = await handle.page.query_selector(_CRD_SELECTORS["canvas"])
            if canvas:
                data = await canvas.screenshot(path=path)
                logger.debug("Display '%s': canvas screenshot taken", display)
                return data
        except Exception:
            pass

        # Fallback: full page screenshot
        data = await handle.page.screenshot(path=path)
        logger.debug("Display '%s': full page screenshot taken", display)
        return data

    async def get_display_info(self, display: str) -> Dict[str, Any]:
        """Get info about a connected display."""
        handle = self._get_display(display)
        return {
            "name": handle.name,
            "host_id": handle.host_id,
            "connected": handle.connected,
            "resolution": handle.resolution,
            "canvas_bounds": handle.canvas_bounds,
            "url": handle.page.url if handle.page else "",
        }

    async def list_available_machines(self) -> List[Dict[str, str]]:
        """
        Open CRD access page in a temp context and list available machines.

        Returns list of {name, host_id} dicts.
        """
        self._require_browser()
        ctx = await self._browser.new_context()
        page = await ctx.new_page()
        machines = []
        try:
            await page.goto(CRD_ACCESS, wait_until="networkidle", timeout=30_000)
            await page.wait_for_selector(_CRD_SELECTORS["machine_list"], timeout=15_000)
            elements = await page.query_selector_all(_CRD_SELECTORS["machine_list"])
            for el in elements:
                host_id = await el.get_attribute("data-host-id") or ""
                text = await el.inner_text()
                machines.append({"name": text.strip(), "host_id": host_id})
        except Exception as exc:
            logger.warning("list_available_machines failed: %s", exc)
        finally:
            await ctx.close()
        return machines

    # -- multi-display operations --------------------------------------------

    async def screenshot_all(self, *, path_prefix: Optional[str] = None) -> Dict[str, bytes]:
        """Screenshot all connected displays. Returns {name: png_bytes}."""
        results = {}
        tasks = []
        for name in self.connected_displays:
            p = f"{path_prefix}_{name}.png" if path_prefix else None
            tasks.append((name, self.screenshot(name, path=p)))
        for name, coro in tasks:
            results[name] = await coro
        return results

    async def broadcast_keys(self, keys: str) -> None:
        """Send the same key combination to ALL connected displays."""
        for name in self.connected_displays:
            await self.send_keys(name, keys)

    async def broadcast_text(self, text: str, *, delay: int = 50) -> None:
        """Type the same text on ALL connected displays."""
        for name in self.connected_displays:
            await self.type_text(name, text, delay=delay)

    # -- internal helpers ----------------------------------------------------

    async def _click_first_machine(self, page: Page) -> None:
        try:
            machines = await page.query_selector_all(_CRD_SELECTORS["machine_list"])
            if machines:
                await machines[0].click()
                logger.info("Clicked first available machine")
        except Exception as exc:
            logger.warning("Failed to click first machine: %s", exc)

    async def _enter_pin(self, page: Page, pin: str, *, timeout: int = 30_000) -> None:
        try:
            await page.wait_for_selector(_CRD_SELECTORS["pin_input"], timeout=timeout)
            await page.fill(_CRD_SELECTORS["pin_input"], pin)
            await page.click(_CRD_SELECTORS["pin_submit"], timeout=5_000)
            logger.info("PIN entered and submitted")
        except Exception as exc:
            logger.warning("PIN entry failed: %s", exc)

    async def _get_canvas_bounds(self, page: Page) -> Optional[Dict[str, float]]:
        try:
            canvas = await page.query_selector(_CRD_SELECTORS["canvas"])
            if canvas:
                box = await canvas.bounding_box()
                return box
        except Exception:
            pass
        return None

    def _canvas_coords(self, handle: DisplayHandle, x: int, y: int) -> Tuple[float, float]:
        """
        Map remote-display pixel coords to browser page coords.

        The CRD canvas may be offset and scaled within the browser viewport.
        This maps (x, y) in remote-display space to page coordinates for
        Playwright mouse events.
        """
        bounds = handle.canvas_bounds
        if not bounds:
            # No bounds info — assume canvas fills viewport
            return float(x), float(y)

        # Scale: remote resolution → canvas element size
        sx = bounds["width"] / handle.resolution[0]
        sy = bounds["height"] / handle.resolution[1]
        cx = bounds["x"] + x * sx
        cy = bounds["y"] + y * sy
        return cx, cy

    def _get_display(self, name: str) -> DisplayHandle:
        handle = self._displays.get(name)
        if not handle:
            raise ValueError(
                f"Display '{name}' not found. "
                f"Available: {list(self._displays.keys())}"
            )
        return handle

    def _require_browser(self) -> None:
        if self._browser is None:
            raise RuntimeError(
                "RemoteDisplayManager not launched — call await mgr.launch() first"
            )
