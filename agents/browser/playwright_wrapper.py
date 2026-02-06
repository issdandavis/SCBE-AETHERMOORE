"""
@file playwright_wrapper.py
@module agents/browser/playwright_wrapper
@layer Layer 5, Layer 12, Layer 13
@component PHDM-Governed Playwright Browser Wrapper
@version 3.0.0

Playwright-based browser automation with geometric containment via PHDM brain.

Every browser action is:
    1. Encoded as a tangent vector (action type + target hash + context)
    2. Mapped into the Poincaré ball via exp_map
    3. Safety-checked against the geometric boundary (radius < 0.92)
    4. Executed only if ALLOW or QUARANTINE; blocked if ESCALATE or DENY

This wrapper integrates with the existing agents/browsers/ backend system
while adding the PHDM containment layer on top.

Requirements:
    pip install playwright
    playwright install chromium
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable, Awaitable

from .phdm_brain import SimplePHDM, SafetyResult, Decision, ACTION_TONGUE

try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_TIMEOUT_MS = 30_000
DEFAULT_VIEWPORT = {"width": 1280, "height": 720}

# Action sensitivity levels (higher = more dangerous)
ACTION_SENSITIVITY = {
    "navigate": 0.3,
    "click": 0.4,
    "type": 0.5,
    "scroll": 0.1,
    "screenshot": 0.2,
    "get_content": 0.2,
    "submit": 0.7,
    "execute_script": 0.9,
    "download": 0.8,
}

# Domain risk heuristics
DOMAIN_PATTERNS = {
    0.9: ["bank", "finance", "pay", "money", "trading", "crypto"],
    0.8: ["health", "medical", "doctor", "hospital", ".gov", "government"],
    0.5: ["facebook", "twitter", "instagram", "tiktok", "linkedin"],
    0.6: ["amazon", "ebay", "shop", "store", "buy"],
    0.2: ["news", "blog", "wiki"],
    0.1: ["google", "bing", "duckduckgo", "search"],
}


# =============================================================================
# Data classes
# =============================================================================

@dataclass
class BrowserActionResult:
    """Result of a PHDM-governed browser action."""
    success: bool
    action: str
    target: str
    decision: Decision
    safety: SafetyResult
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    elapsed_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


# =============================================================================
# PHDMPlaywrightBrowser
# =============================================================================

class PHDMPlaywrightBrowser:
    """
    PHDM-governed browser using Playwright.

    Wraps Playwright with a SimplePHDM brain that validates every action
    against geometric safety boundaries before execution.

    Args:
        brain: SimplePHDM instance (or None to create default).
        headless: Run browser without GUI.
        browser_type: Playwright browser engine ("chromium", "firefox", "webkit").
        timeout_ms: Default timeout for actions.
        viewport: Browser viewport dimensions.
        max_steps: Maximum actions per session.

    Example:
        browser = PHDMPlaywrightBrowser()
        await browser.start()
        result = await browser.navigate("https://example.com")
        if result.success:
            content = await browser.get_content()
        await browser.stop()
    """

    def __init__(
        self,
        brain: Optional[SimplePHDM] = None,
        headless: bool = True,
        browser_type: str = "chromium",
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        viewport: Optional[Dict[str, int]] = None,
        max_steps: int = 100,
    ):
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright not installed. Run: pip install playwright && playwright install"
            )

        self.brain = brain or SimplePHDM()
        self.headless = headless
        self.browser_type = browser_type
        self.timeout_ms = timeout_ms
        self.viewport = viewport or DEFAULT_VIEWPORT
        self.max_steps = max_steps

        # Playwright state
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

        # Session state
        self._current_url: str = ""
        self._step_count: int = 0
        self._action_log: List[BrowserActionResult] = []
        self._started = False

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def start(self) -> bool:
        """
        Start the browser and initialize the PHDM session.

        Returns:
            True if browser started successfully.
        """
        try:
            self._playwright = await async_playwright().start()
            launcher = getattr(self._playwright, self.browser_type)

            self._browser = await launcher.launch(headless=self.headless)
            self._context = await self._browser.new_context(
                viewport=self.viewport,
                user_agent="SCBE-PHDMBrowser/3.0 (Playwright)",
            )
            self._page = await self._context.new_page()
            self._page.set_default_timeout(self.timeout_ms)

            self._started = True
            self.brain.reset()
            self._step_count = 0
            self._action_log = []

            logger.info(
                "PHDM browser started: %s headless=%s", self.browser_type, self.headless
            )
            return True

        except Exception as e:
            logger.error("Failed to start browser: %s", e)
            return False

    async def stop(self) -> None:
        """Stop the browser and clean up."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._page = None
        self._context = None
        self._started = False
        logger.info("PHDM browser stopped")

    @property
    def is_running(self) -> bool:
        """Check if browser is running."""
        return self._started and self._page is not None

    # =========================================================================
    # PHDM governance layer
    # =========================================================================

    def _get_domain_risk(self, url: str) -> float:
        """Heuristic domain risk scoring."""
        url_lower = url.lower()
        for risk, patterns in DOMAIN_PATTERNS.items():
            if any(p in url_lower for p in patterns):
                return risk
        return 0.4

    def _build_context(self, action: str, target: str) -> Dict[str, Any]:
        """Build context dict for action encoding."""
        return {
            "sensitivity": ACTION_SENSITIVITY.get(action, 0.5),
            "domain_risk": self._get_domain_risk(target),
            "step": self._step_count,
            "max_steps": self.max_steps,
            "current_url": self._current_url,
        }

    async def _governed_execute(
        self,
        action: str,
        target: str,
        executor: Callable[[], Awaitable[Any]],
    ) -> BrowserActionResult:
        """
        Execute a browser action through the PHDM governance pipeline.

        Pipeline:
            1. Encode action → tangent vector
            2. exp_map → Poincaré ball point
            3. check_action → SafetyResult with 4-tier decision
            4. Execute if ALLOW or QUARANTINE
            5. Log result

        Args:
            action: Action name.
            target: Action target (URL, selector, etc.).
            executor: Async callable that performs the actual browser action.

        Returns:
            BrowserActionResult with decision and outcome.
        """
        if not self.is_running:
            return BrowserActionResult(
                success=False,
                action=action,
                target=target,
                decision=Decision.DENY,
                safety=SafetyResult(
                    safe=False,
                    reason="browser_not_running",
                    radius=0.0,
                    angular_deviation=0.0,
                    decision=Decision.DENY,
                    cost=float("inf"),
                ),
                error="Browser is not running",
            )

        if self._step_count >= self.max_steps:
            return BrowserActionResult(
                success=False,
                action=action,
                target=target,
                decision=Decision.DENY,
                safety=SafetyResult(
                    safe=False,
                    reason=f"max_steps_exceeded: {self._step_count} >= {self.max_steps}",
                    radius=0.0,
                    angular_deviation=0.0,
                    decision=Decision.DENY,
                    cost=float("inf"),
                ),
                error=f"Max steps ({self.max_steps}) exceeded",
            )

        start_time = time.monotonic()

        # Step 1-2: Encode and map to Poincaré ball
        ctx = self._build_context(action, target)
        embedding = self.brain.embed_action(action, target, ctx)

        # Step 3: Safety check
        safety = self.brain.check_action(embedding.vector, action, target)

        # Step 4: Execute based on decision
        self._step_count += 1
        can_execute = safety.decision in (Decision.ALLOW, Decision.QUARANTINE)

        result = BrowserActionResult(
            success=False,
            action=action,
            target=target,
            decision=safety.decision,
            safety=safety,
        )

        if can_execute:
            try:
                data = await executor()
                result.success = True
                result.data = data if isinstance(data, dict) else {"result": data}
            except Exception as e:
                result.error = str(e)
                logger.warning("Action %s failed: %s", action, e)
        else:
            result.error = f"Action blocked by PHDM: {safety.reason}"
            logger.warning(
                "PHDM %s for %s(%s): %s (radius=%.4f, cost=%.2f)",
                safety.decision.value,
                action,
                target[:60],
                safety.reason,
                safety.radius,
                safety.cost,
            )

        result.elapsed_ms = (time.monotonic() - start_time) * 1000
        self._action_log.append(result)
        return result

    # =========================================================================
    # Browser actions (all governed)
    # =========================================================================

    async def navigate(self, url: str) -> BrowserActionResult:
        """Navigate to a URL (governed)."""
        async def _exec():
            response = await self._page.goto(url, wait_until="domcontentloaded")
            self._current_url = url
            return {
                "url": url,
                "status": response.status if response else None,
                "ok": response.ok if response else False,
            }

        return await self._governed_execute("navigate", url, _exec)

    async def click(self, selector: str) -> BrowserActionResult:
        """Click an element (governed)."""
        target = f"{self._current_url}::{selector}"

        async def _exec():
            await self._page.click(selector, timeout=self.timeout_ms)
            return {"selector": selector, "clicked": True}

        return await self._governed_execute("click", target, _exec)

    async def type_text(self, selector: str, text: str) -> BrowserActionResult:
        """Type text into an element (governed)."""
        target = f"{self._current_url}::{selector}"

        async def _exec():
            await self._page.fill(selector, text)
            return {"selector": selector, "typed": True, "length": len(text)}

        return await self._governed_execute("type", target, _exec)

    async def scroll(self, direction: str = "down", amount: int = 300) -> BrowserActionResult:
        """Scroll the page (governed)."""
        target = f"{self._current_url}::scroll:{direction}"

        async def _exec():
            delta = amount if direction == "down" else -amount
            await self._page.mouse.wheel(0, delta)
            return {"direction": direction, "amount": amount}

        return await self._governed_execute("scroll", target, _exec)

    async def screenshot(self) -> BrowserActionResult:
        """Take a screenshot (governed)."""
        async def _exec():
            data = await self._page.screenshot(type="png", full_page=False)
            return {"size_bytes": len(data), "format": "png"}

        return await self._governed_execute("screenshot", self._current_url or "about:blank", _exec)

    async def screenshot_bytes(self) -> Optional[bytes]:
        """
        Take a screenshot and return raw bytes (for vision pipeline).

        This bypasses the governance result wrapper to return raw bytes
        directly, but still runs through PHDM validation.

        Returns:
            PNG screenshot bytes, or None if action was blocked/failed.
        """
        if not self.is_running:
            return None

        ctx = self._build_context("screenshot", self._current_url or "about:blank")
        embedding = self.brain.embed_action("screenshot", self._current_url or "about:blank", ctx)
        safety = self.brain.check_action(embedding.vector, "screenshot", self._current_url)

        if safety.decision in (Decision.ALLOW, Decision.QUARANTINE):
            try:
                return await self._page.screenshot(type="png", full_page=False)
            except Exception as e:
                logger.warning("Screenshot failed: %s", e)
                return None
        return None

    async def get_content(self) -> BrowserActionResult:
        """Get page HTML content (governed)."""
        async def _exec():
            html = await self._page.content()
            return {"length": len(html), "content": html}

        return await self._governed_execute("get_content", self._current_url or "about:blank", _exec)

    async def get_text(self) -> BrowserActionResult:
        """Get page text content (governed)."""
        async def _exec():
            text = await self._page.inner_text("body")
            return {"length": len(text), "text": text}

        return await self._governed_execute("get_content", self._current_url or "about:blank", _exec)

    async def get_accessibility_tree(self) -> BrowserActionResult:
        """
        Get the accessibility tree snapshot (governed).

        The accessibility tree provides a structured representation of the page
        suitable for agent decision-making without vision models.
        """
        async def _exec():
            snapshot = await self._page.accessibility.snapshot()
            return {"tree": snapshot}

        return await self._governed_execute(
            "get_content", self._current_url or "about:blank", _exec
        )

    async def submit(self, selector: str) -> BrowserActionResult:
        """Submit a form (governed, higher sensitivity)."""
        target = f"{self._current_url}::{selector}"

        async def _exec():
            await self._page.click(selector, timeout=self.timeout_ms)
            return {"selector": selector, "submitted": True}

        return await self._governed_execute("submit", target, _exec)

    async def execute_script(self, script: str) -> BrowserActionResult:
        """Execute JavaScript (governed, highest sensitivity)."""
        script_hash = hashlib.sha256(script.encode()).hexdigest()[:16]
        target = f"{self._current_url}::script:{script_hash}"

        async def _exec():
            result = await self._page.evaluate(script)
            return {"script_hash": script_hash, "result": result}

        return await self._governed_execute("execute_script", target, _exec)

    async def wait_for_selector(self, selector: str, timeout_ms: Optional[int] = None) -> bool:
        """Wait for an element to appear (not governed — passive observation)."""
        if not self.is_running:
            return False
        try:
            await self._page.wait_for_selector(
                selector, timeout=timeout_ms or self.timeout_ms
            )
            return True
        except Exception:
            return False

    async def get_current_url(self) -> str:
        """Get current page URL (not governed — passive read)."""
        if self._page:
            return self._page.url
        return ""

    # =========================================================================
    # Session management
    # =========================================================================

    def get_summary(self) -> Dict[str, Any]:
        """Get session summary with PHDM metrics."""
        decisions: Dict[str, int] = {}
        for r in self._action_log:
            key = r.decision.value
            decisions[key] = decisions.get(key, 0) + 1

        avg_radius = 0.0
        max_radius = 0.0
        if self._action_log:
            radii = [r.safety.radius for r in self._action_log]
            avg_radius = sum(radii) / len(radii)
            max_radius = max(radii)

        return {
            "browser_type": self.browser_type,
            "is_running": self.is_running,
            "current_url": self._current_url,
            "step_count": self._step_count,
            "max_steps": self.max_steps,
            "total_actions": len(self._action_log),
            "decisions": decisions,
            "avg_radius": avg_radius,
            "max_radius": max_radius,
            "safe_radius": self.brain.safe_radius,
            "trajectory_drift": self.brain.trajectory_drift(),
            "brain_state": self.brain.get_state(),
        }

    def print_summary(self) -> None:
        """Print formatted session summary."""
        s = self.get_summary()
        print(f"\n{'=' * 60}")
        print("PHDM BROWSER SESSION SUMMARY")
        print(f"{'=' * 60}")
        print(f"Browser:     {s['browser_type']} (running={s['is_running']})")
        print(f"URL:         {s['current_url']}")
        print(f"Steps:       {s['step_count']} / {s['max_steps']}")
        print(f"Actions:     {s['total_actions']}")
        for decision, count in s["decisions"].items():
            print(f"  {decision}: {count}")
        print(f"Avg radius:  {s['avg_radius']:.4f}")
        print(f"Max radius:  {s['max_radius']:.4f}")
        print(f"Safe radius: {s['safe_radius']}")
        print(f"Drift:       {s['trajectory_drift']:.4f}")
        print(f"{'=' * 60}")
