"""
Chrome DevTools Protocol Backend
================================

Direct browser control via Chrome DevTools Protocol (CDP).

This provides the lowest-level access to Chrome's debugging interface,
enabling capabilities not available through higher-level frameworks.

Requirements:
    pip install websockets aiohttp
    Chrome/Chromium with --remote-debugging-port enabled
"""

import asyncio
import base64
import json
import os
import platform
import shutil
from typing import Optional, Dict, Any, List
from .base import BrowserBackend

try:
    import websockets
    import aiohttp
    CDP_AVAILABLE = True
except ImportError:
    CDP_AVAILABLE = False


class CDPBackend(BrowserBackend):
    """
    Browser backend using Chrome DevTools Protocol directly.

    CDP provides:
    - Lowest-level Chrome control
    - Access to all debugging features
    - Performance profiling
    - Network interception
    - Memory debugging
    - Security auditing
    - Direct DOM manipulation
    """

    name = "cdp"

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9222,
        target_id: Optional[str] = None
    ):
        if not CDP_AVAILABLE:
            raise ImportError("CDP dependencies not installed. Run: pip install websockets aiohttp")

        self.host = host
        self.port = port
        self.target_id = target_id

        self._ws = None
        self._http_session = None
        self._command_id = 0
        self._pending = {}
        self._event_handlers = {}
        self._receive_task = None
        self.current_url = ""

    async def initialize(self) -> bool:
        """Initialize CDP connection."""
        try:
            self._http_session = aiohttp.ClientSession()

            # Get list of targets
            async with self._http_session.get(f"http://{self.host}:{self.port}/json") as resp:
                if resp.status != 200:
                    print(f"[CDP] Failed to get targets: {resp.status}")
                    return False
                targets = await resp.json()

            if not targets:
                print("[CDP] No targets found. Start Chrome with --remote-debugging-port=9222")
                return False

            # Select target
            if self.target_id:
                target = next((t for t in targets if t["id"] == self.target_id), None)
            else:
                # Find first page target
                target = next((t for t in targets if t.get("type") == "page"), targets[0])

            if not target:
                print("[CDP] No suitable target found")
                return False

            ws_url = target.get("webSocketDebuggerUrl")
            if not ws_url:
                print("[CDP] Target has no WebSocket URL")
                return False

            # Connect via WebSocket
            self._ws = await websockets.connect(ws_url)
            print(f"[CDP] Connected to {target.get('title', 'Unknown')}")

            # Start receiving messages
            self._receive_task = asyncio.create_task(self._receive_loop())

            # Enable required domains
            await self._send("Page.enable")
            await self._send("DOM.enable")
            await self._send("Runtime.enable")
            await self._send("Network.enable")

            print(f"[CDP] Initialized on {self.host}:{self.port}")
            return True

        except Exception as e:
            print(f"[CDP] Initialization failed: {e}")
            return False

    async def _send(self, method: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Send CDP command and wait for response."""
        self._command_id += 1
        cmd_id = self._command_id

        message = {
            "id": cmd_id,
            "method": method,
            "params": params or {}
        }

        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self._pending[cmd_id] = future

        # Send command
        await self._ws.send(json.dumps(message))

        # Wait for response
        try:
            result = await asyncio.wait_for(future, timeout=30.0)
            return result
        except asyncio.TimeoutError:
            del self._pending[cmd_id]
            raise TimeoutError(f"CDP command timed out: {method}")

    async def _receive_loop(self):
        """Receive and process CDP messages."""
        try:
            async for message in self._ws:
                data = json.loads(message)

                # Check if it's a response
                if "id" in data:
                    cmd_id = data["id"]
                    if cmd_id in self._pending:
                        future = self._pending.pop(cmd_id)
                        if "error" in data:
                            future.set_exception(Exception(data["error"].get("message", "Unknown error")))
                        else:
                            future.set_result(data.get("result", {}))

                # Check if it's an event
                elif "method" in data:
                    method = data["method"]
                    params = data.get("params", {})

                    # Call registered handlers
                    if method in self._event_handlers:
                        for handler in self._event_handlers[method]:
                            try:
                                await handler(params)
                            except Exception as e:
                                print(f"[CDP] Event handler error: {e}")

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"[CDP] Receive loop error: {e}")

    def on_event(self, method: str, handler):
        """Register event handler."""
        if method not in self._event_handlers:
            self._event_handlers[method] = []
        self._event_handlers[method].append(handler)

    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to URL."""
        result = await self._send("Page.navigate", {"url": url})
        self.current_url = url

        # Wait for load
        await self._send("Page.loadEventFired")
        await asyncio.sleep(0.5)  # Brief settle time

        return {
            "url": url,
            "frameId": result.get("frameId"),
            "loaderId": result.get("loaderId")
        }

    async def click(self, selector: str) -> Dict[str, Any]:
        """Click element by CSS selector."""
        try:
            # Get document
            doc = await self._send("DOM.getDocument")
            root_id = doc["root"]["nodeId"]

            # Query selector
            result = await self._send("DOM.querySelector", {
                "nodeId": root_id,
                "selector": selector
            })

            node_id = result.get("nodeId")
            if not node_id:
                return {"selector": selector, "clicked": False, "error": "Element not found"}

            # Get box model for coordinates
            box_result = await self._send("DOM.getBoxModel", {"nodeId": node_id})
            quad = box_result["model"]["content"]

            # Calculate center point
            x = (quad[0] + quad[2] + quad[4] + quad[6]) / 4
            y = (quad[1] + quad[3] + quad[5] + quad[7]) / 4

            # Click at coordinates
            await self._send("Input.dispatchMouseEvent", {
                "type": "mousePressed",
                "x": x,
                "y": y,
                "button": "left",
                "clickCount": 1
            })

            await self._send("Input.dispatchMouseEvent", {
                "type": "mouseReleased",
                "x": x,
                "y": y,
                "button": "left",
                "clickCount": 1
            })

            return {"selector": selector, "clicked": True, "coordinates": [x, y]}

        except Exception as e:
            return {"selector": selector, "clicked": False, "error": str(e)}

    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """Type text into element."""
        try:
            # First click to focus
            await self.click(selector)
            await asyncio.sleep(0.1)

            # Type each character
            for char in text:
                await self._send("Input.dispatchKeyEvent", {
                    "type": "keyDown",
                    "text": char,
                    "key": char,
                    "code": f"Key{char.upper()}" if char.isalpha() else char
                })
                await self._send("Input.dispatchKeyEvent", {
                    "type": "keyUp",
                    "key": char
                })

            return {"selector": selector, "typed": True, "length": len(text)}

        except Exception as e:
            return {"selector": selector, "typed": False, "error": str(e)}

    async def get_page_content(self) -> str:
        """Get page HTML content."""
        # Get document
        doc = await self._send("DOM.getDocument", {"depth": -1})
        root_id = doc["root"]["nodeId"]

        # Get outer HTML
        result = await self._send("DOM.getOuterHTML", {"nodeId": root_id})
        return result.get("outerHTML", "")

    async def screenshot(self) -> bytes:
        """Take screenshot."""
        result = await self._send("Page.captureScreenshot", {"format": "png"})
        return base64.b64decode(result["data"])

    async def execute_script(self, script: str) -> Any:
        """Execute JavaScript."""
        result = await self._send("Runtime.evaluate", {
            "expression": script,
            "returnByValue": True,
            "awaitPromise": True
        })

        if "exceptionDetails" in result:
            raise Exception(result["exceptionDetails"].get("text", "Script error"))

        return result.get("result", {}).get("value")

    async def get_current_url(self) -> str:
        """Get current page URL."""
        return self.current_url

    async def scroll(self, direction: str = "down", amount: int = 300) -> Dict[str, Any]:
        """Scroll the page."""
        delta = amount if direction == "down" else -amount
        await self.execute_script(f"window.scrollBy(0, {delta})")
        return {"direction": direction, "amount": amount}

    async def find_element(self, selector: str) -> Optional[Dict[str, Any]]:
        """Find element by CSS selector."""
        try:
            doc = await self._send("DOM.getDocument")
            root_id = doc["root"]["nodeId"]

            result = await self._send("DOM.querySelector", {
                "nodeId": root_id,
                "selector": selector
            })

            node_id = result.get("nodeId")
            if not node_id:
                return {"selector": selector, "found": False}

            # Get box model
            try:
                box_result = await self._send("DOM.getBoxModel", {"nodeId": node_id})
                box = box_result.get("model", {})
            except Exception:
                box = None

            return {
                "selector": selector,
                "found": True,
                "nodeId": node_id,
                "box": box
            }

        except Exception as e:
            return {"selector": selector, "found": False, "error": str(e)}

    async def get_cookies(self) -> List[Dict[str, Any]]:
        """Get browser cookies."""
        result = await self._send("Network.getAllCookies")
        return result.get("cookies", [])

    async def set_cookie(self, cookie: Dict[str, Any]) -> bool:
        """Set a cookie."""
        try:
            await self._send("Network.setCookie", cookie)
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close connection."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self._ws:
            await self._ws.close()

        if self._http_session:
            await self._http_session.close()

        print("[CDP] Connection closed")

    # ==========================================================================
    # CDP-Specific Advanced Features
    # ==========================================================================

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get page performance metrics."""
        result = await self._send("Performance.getMetrics")
        return {m["name"]: m["value"] for m in result.get("metrics", [])}

    async def enable_performance(self) -> None:
        """Enable performance domain."""
        await self._send("Performance.enable")

    async def get_resource_tree(self) -> Dict[str, Any]:
        """Get page resource tree."""
        result = await self._send("Page.getResourceTree")
        return result.get("frameTree", {})

    async def get_frame_tree(self) -> Dict[str, Any]:
        """Get frame tree."""
        result = await self._send("Page.getFrameTree")
        return result.get("frameTree", {})

    async def enable_network_interception(self, patterns: List[Dict[str, str]]) -> None:
        """Enable network request interception."""
        await self._send("Fetch.enable", {"patterns": patterns})

    async def continue_intercepted_request(self, request_id: str, **overrides) -> None:
        """Continue an intercepted request."""
        params = {"requestId": request_id}
        params.update(overrides)
        await self._send("Fetch.continueRequest", params)

    async def fail_intercepted_request(self, request_id: str, reason: str = "Failed") -> None:
        """Fail an intercepted request."""
        await self._send("Fetch.failRequest", {
            "requestId": request_id,
            "errorReason": reason
        })

    async def set_user_agent(self, user_agent: str) -> None:
        """Override user agent."""
        await self._send("Network.setUserAgentOverride", {
            "userAgent": user_agent
        })

    async def set_extra_headers(self, headers: Dict[str, str]) -> None:
        """Set extra HTTP headers."""
        await self._send("Network.setExtraHTTPHeaders", {
            "headers": headers
        })

    async def emulate_device(
        self,
        width: int,
        height: int,
        device_scale_factor: float = 1.0,
        mobile: bool = False
    ) -> None:
        """Emulate device viewport."""
        await self._send("Emulation.setDeviceMetricsOverride", {
            "width": width,
            "height": height,
            "deviceScaleFactor": device_scale_factor,
            "mobile": mobile
        })

    async def emulate_geolocation(self, latitude: float, longitude: float, accuracy: float = 100) -> None:
        """Emulate geolocation."""
        await self._send("Emulation.setGeolocationOverride", {
            "latitude": latitude,
            "longitude": longitude,
            "accuracy": accuracy
        })

    async def clear_geolocation(self) -> None:
        """Clear geolocation override."""
        await self._send("Emulation.clearGeolocationOverride")

    async def set_timezone(self, timezone_id: str) -> None:
        """Override timezone."""
        await self._send("Emulation.setTimezoneOverride", {
            "timezoneId": timezone_id
        })

    async def get_security_state(self) -> Dict[str, Any]:
        """Get page security state."""
        await self._send("Security.enable")
        # Return current security info (would need event handler for full state)
        return {"enabled": True}

    async def print_to_pdf(self, **options) -> bytes:
        """Generate PDF of page."""
        result = await self._send("Page.printToPDF", options)
        return base64.b64decode(result["data"])

    async def get_heap_snapshot(self) -> Dict[str, Any]:
        """Take heap snapshot for memory analysis."""
        await self._send("HeapProfiler.enable")
        result = await self._send("HeapProfiler.takeHeapSnapshot", {
            "reportProgress": False
        })
        return result

    async def get_cpu_profile(self, duration_ms: int = 5000) -> Dict[str, Any]:
        """Record CPU profile."""
        await self._send("Profiler.enable")
        await self._send("Profiler.start")
        await asyncio.sleep(duration_ms / 1000)
        result = await self._send("Profiler.stop")
        return result.get("profile", {})

    async def start_tracing(self, categories: List[str] = None) -> None:
        """Start Chrome tracing."""
        await self._send("Tracing.start", {
            "categories": ",".join(categories or ["devtools.timeline"])
        })

    async def stop_tracing(self) -> Dict[str, Any]:
        """Stop tracing and get data."""
        result = await self._send("Tracing.end")
        return result

    async def get_layout_metrics(self) -> Dict[str, Any]:
        """Get page layout metrics."""
        result = await self._send("Page.getLayoutMetrics")
        return result

    async def set_offline(self, offline: bool = True) -> None:
        """Emulate offline mode."""
        await self._send("Network.emulateNetworkConditions", {
            "offline": offline,
            "latency": 0,
            "downloadThroughput": -1,
            "uploadThroughput": -1
        })

    async def clear_browser_cache(self) -> None:
        """Clear browser cache."""
        await self._send("Network.clearBrowserCache")

    async def clear_browser_cookies(self) -> None:
        """Clear all browser cookies."""
        await self._send("Network.clearBrowserCookies")

    async def focus_element(self, selector: str) -> bool:
        """Focus an element."""
        try:
            doc = await self._send("DOM.getDocument")
            root_id = doc["root"]["nodeId"]

            result = await self._send("DOM.querySelector", {
                "nodeId": root_id,
                "selector": selector
            })

            node_id = result.get("nodeId")
            if node_id:
                await self._send("DOM.focus", {"nodeId": node_id})
                return True
        except Exception:
            pass
        return False

    async def highlight_element(self, selector: str, color: Dict[str, int] = None) -> None:
        """Highlight element for debugging."""
        color = color or {"r": 255, "g": 0, "b": 0, "a": 0.5}

        doc = await self._send("DOM.getDocument")
        root_id = doc["root"]["nodeId"]

        result = await self._send("DOM.querySelector", {
            "nodeId": root_id,
            "selector": selector
        })

        if result.get("nodeId"):
            await self._send("Overlay.highlightNode", {
                "highlightConfig": {
                    "contentColor": color,
                    "showInfo": True
                },
                "nodeId": result["nodeId"]
            })

    async def clear_highlight(self) -> None:
        """Clear element highlighting."""
        await self._send("Overlay.hideHighlight")


# =============================================================================
# Helper to Start Chrome with Remote Debugging
# =============================================================================

def resolve_chrome_binary(system: Optional[str] = None) -> str:
    """Resolve a Chrome/Chromium executable path for the current platform.

    Resolution order:
    1) SCBE_CHROME_PATH env override
    2) Known OS-specific executable names/paths
    3) Safe fallback command name
    """
    system = system or platform.system()

    env_override = os.environ.get("SCBE_CHROME_PATH")
    if env_override:
        return env_override

    if system == "Windows":
        windows_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
        for path in windows_paths:
            if os.path.exists(path):
                return path
        return windows_paths[0]

    if system == "Darwin":
        mac_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        return mac_path

    # Linux: search common chrome/chromium binaries first
    linux_bins = [
        "google-chrome-stable",
        "google-chrome",
        "chromium-browser",
        "chromium",
        "chrome",
    ]
    for name in linux_bins:
        path = shutil.which(name)
        if path:
            return path

    # Fallback keeps previous behavior if binary isn't present in PATH during resolution
    return "google-chrome"


def get_chrome_launch_command(port: int = 9222, user_data_dir: str = None) -> str:
    """Get command to launch Chrome with remote debugging."""
    chrome_path = resolve_chrome_binary()
    user_dir = user_data_dir or os.path.join(os.path.expanduser("~"), ".scbe-chrome-profile")

    # Quote paths with spaces for shell friendliness.
    chrome_cmd = f'"{chrome_path}"' if " " in chrome_path and not chrome_path.startswith('"') else chrome_path
    return f'{chrome_cmd} --remote-debugging-port={port} --user-data-dir="{user_dir}"'


# =============================================================================
# Example Usage
# =============================================================================

async def example_usage():
    """Example of using CDPBackend with GovernedBrowser."""
    from .base import GovernedBrowser

    print("Start Chrome with remote debugging first:")
    print(get_chrome_launch_command())
    print()

    # Create backend
    backend = CDPBackend(
        host="127.0.0.1",
        port=9222
    )

    # Wrap with governance
    browser = GovernedBrowser(
        backend,
        agent_id="cdp-agent-001"
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
