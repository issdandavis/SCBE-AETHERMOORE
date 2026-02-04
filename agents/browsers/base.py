"""
Base classes for SCBE-governed browser backends.
"""

import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timezone
from enum import Enum

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from browser_agent import SCBEClient, Decision, GovernanceResult, BrowserAction, EscalationHandler
except ImportError:
    # Inline minimal versions if import fails
    import requests

    class Decision(str, Enum):
        ALLOW = "ALLOW"
        QUARANTINE = "QUARANTINE"
        ESCALATE = "ESCALATE"
        DENY = "DENY"


# =============================================================================
# Base Backend Interface
# =============================================================================

class BrowserBackend(ABC):
    """
    Abstract base class for browser automation backends.

    All backends must implement these methods to be governed by SCBE.
    """

    name: str = "base"

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the browser backend."""
        pass

    @abstractmethod
    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL."""
        pass

    @abstractmethod
    async def click(self, selector: str) -> Dict[str, Any]:
        """Click an element."""
        pass

    @abstractmethod
    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """Type text into an element."""
        pass

    @abstractmethod
    async def get_page_content(self) -> str:
        """Get current page content/text."""
        pass

    @abstractmethod
    async def screenshot(self) -> bytes:
        """Take a screenshot."""
        pass

    @abstractmethod
    async def execute_script(self, script: str) -> Any:
        """Execute JavaScript."""
        pass

    @abstractmethod
    async def get_current_url(self) -> str:
        """Get current page URL."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the browser."""
        pass

    # Optional methods with default implementations
    async def wait(self, seconds: float) -> None:
        """Wait for specified seconds."""
        import asyncio
        await asyncio.sleep(seconds)

    async def scroll(self, direction: str = "down", amount: int = 300) -> Dict[str, Any]:
        """Scroll the page."""
        return {"status": "not_implemented"}

    async def find_element(self, selector: str) -> Optional[Dict[str, Any]]:
        """Find an element by selector."""
        return None

    async def get_cookies(self) -> List[Dict[str, Any]]:
        """Get browser cookies."""
        return []

    async def set_cookie(self, cookie: Dict[str, Any]) -> bool:
        """Set a cookie."""
        return False


# =============================================================================
# Governed Browser Wrapper
# =============================================================================

@dataclass
class ActionResult:
    """Result of a governed browser action."""
    success: bool
    action: str
    target: str
    decision: str
    score: float
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class GovernedBrowser:
    """
    SCBE-governed browser that wraps any backend.

    Every action goes through the SCBE governance pipeline before execution.

    Usage:
        backend = PlaywrightBackend()
        browser = GovernedBrowser(backend, agent_id="my-agent")
        await browser.initialize()

        result = await browser.navigate("https://example.com")
        if result.success:
            print("Navigation approved and executed")
    """

    # Sensitivity levels for different actions
    ACTION_SENSITIVITY = {
        "navigate": 0.3,
        "click": 0.4,
        "type": 0.5,
        "submit": 0.7,
        "download": 0.8,
        "upload": 0.8,
        "execute_script": 0.9,
        "get_cookies": 0.6,
        "set_cookie": 0.7,
        "screenshot": 0.2,
        "scroll": 0.1,
        "wait": 0.0,  # No governance needed
    }

    # Domain risk multipliers
    DOMAIN_RISK = {
        "banking": 0.9,
        "financial": 0.85,
        "healthcare": 0.8,
        "government": 0.8,
        "social_media": 0.5,
        "shopping": 0.6,
        "news": 0.2,
        "search": 0.1,
    }

    def __init__(
        self,
        backend: BrowserBackend,
        agent_id: str = "governed-browser-001",
        scbe_url: str = "http://127.0.0.1:8080",
        scbe_key: str = "test-key-12345",
        auto_escalate: bool = True,
        initial_trust: float = 0.7
    ):
        self.backend = backend
        self.agent_id = agent_id
        self.scbe_url = scbe_url
        self.scbe_key = scbe_key
        self.auto_escalate = auto_escalate
        self.initial_trust = initial_trust

        # Session state
        self.current_url: str = ""
        self.action_log: List[ActionResult] = []
        self.quarantine_queue: List[ActionResult] = []

        # SCBE client
        self._session = None
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the governed browser."""
        import aiohttp

        # Create HTTP session
        self._session = aiohttp.ClientSession(
            headers={
                "Content-Type": "application/json",
                "SCBE_api_key": self.scbe_key
            }
        )

        # Check SCBE API
        try:
            async with self._session.get(f"{self.scbe_url}/v1/health") as resp:
                if resp.status != 200:
                    print(f"[SCBE] API not healthy: {resp.status}")
                    return False
                data = await resp.json()
                print(f"[SCBE] Connected: {data['status']}")
        except Exception as e:
            print(f"[SCBE] Connection failed: {e}")
            return False

        # Register agent
        try:
            async with self._session.post(
                f"{self.scbe_url}/v1/agents",
                json={
                    "agent_id": self.agent_id,
                    "name": f"GovernedBrowser-{self.backend.name}",
                    "role": "browser_automation",
                    "initial_trust": self.initial_trust
                }
            ) as resp:
                data = await resp.json()
                print(f"[SCBE] Agent registered: {self.agent_id}")
        except Exception as e:
            print(f"[SCBE] Agent registration: {e}")

        # Initialize backend
        try:
            await self.backend.initialize()
            print(f"[BROWSER] {self.backend.name} initialized")
            self._initialized = True
            return True
        except Exception as e:
            print(f"[BROWSER] Initialization failed: {e}")
            return False

    def _get_domain_risk(self, url: str) -> float:
        """Calculate risk based on domain."""
        url_lower = url.lower()

        if any(x in url_lower for x in ["bank", "finance", "pay", "money", "trading"]):
            return self.DOMAIN_RISK["banking"]
        elif any(x in url_lower for x in ["health", "medical", "doctor", "hospital"]):
            return self.DOMAIN_RISK["healthcare"]
        elif any(x in url_lower for x in [".gov", "government"]):
            return self.DOMAIN_RISK["government"]
        elif any(x in url_lower for x in ["facebook", "twitter", "instagram", "tiktok", "linkedin"]):
            return self.DOMAIN_RISK["social_media"]
        elif any(x in url_lower for x in ["amazon", "ebay", "shop", "store", "buy"]):
            return self.DOMAIN_RISK["shopping"]
        elif any(x in url_lower for x in ["google", "bing", "duckduckgo", "search"]):
            return self.DOMAIN_RISK["search"]

        return 0.4  # Default

    def _calculate_sensitivity(self, action: str, target: str) -> float:
        """Calculate combined sensitivity."""
        base = self.ACTION_SENSITIVITY.get(action, 0.5)
        domain = self._get_domain_risk(target)
        return min(1.0, (base * 0.6) + (domain * 0.4))

    async def _authorize(
        self,
        action: str,
        target: str,
        sensitivity: float,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get SCBE authorization."""
        try:
            async with self._session.post(
                f"{self.scbe_url}/v1/authorize",
                json={
                    "agent_id": self.agent_id,
                    "action": action.upper(),
                    "target": target,
                    "context": {
                        "sensitivity": sensitivity,
                        "current_url": self.current_url,
                        **(context or {})
                    }
                }
            ) as resp:
                return await resp.json()
        except Exception as e:
            return {
                "decision": "DENY",
                "decision_id": "error",
                "score": 0.0,
                "explanation": {"error": str(e)}
            }

    async def _governed_action(
        self,
        action: str,
        target: str,
        executor: Callable,
        context: Optional[Dict[str, Any]] = None,
        skip_governance: bool = False
    ) -> ActionResult:
        """Execute an action with SCBE governance."""

        sensitivity = self._calculate_sensitivity(action, target)

        print(f"\n[GOVERN] {action.upper()} -> {target[:50]}...")
        print(f"         Sensitivity: {sensitivity:.2f}")

        # Skip governance for low-risk actions
        if skip_governance or sensitivity == 0.0:
            try:
                data = await executor()
                return ActionResult(
                    success=True,
                    action=action,
                    target=target,
                    decision="SKIP",
                    score=1.0,
                    data=data if isinstance(data, dict) else {"result": data}
                )
            except Exception as e:
                return ActionResult(
                    success=False,
                    action=action,
                    target=target,
                    decision="ERROR",
                    score=0.0,
                    error=str(e)
                )

        # Get authorization
        auth = await self._authorize(action, target, sensitivity, context)
        decision = auth.get("decision", "DENY")
        score = auth.get("score", 0.0)

        print(f"         Decision: {decision} (score: {score:.3f})")

        result = ActionResult(
            success=False,
            action=action,
            target=target,
            decision=decision,
            score=score,
            data=auth
        )

        # Handle decision
        can_execute = False

        if decision == "ALLOW":
            can_execute = True
            print("         [ALLOW] Executing action")

        elif decision == "QUARANTINE":
            can_execute = True
            print("         [QUARANTINE] Executing with monitoring")
            self.quarantine_queue.append(result)

        elif decision == "ESCALATE":
            if self.auto_escalate:
                print("         [ESCALATE] Auto-approving for demo (would ask higher AI)")
                # In production, this would call another AI
                can_execute = sensitivity < 0.7
                if can_execute:
                    print("         [ESCALATE->ALLOW] Lower sensitivity approved")
                else:
                    print("         [ESCALATE->DENY] High sensitivity requires human")
            else:
                print("         [ESCALATE] Manual approval required")

        elif decision == "DENY":
            print("         [DENY] Action blocked")

        # Execute if approved
        if can_execute:
            try:
                data = await executor()
                result.success = True
                result.data = data if isinstance(data, dict) else {"result": data}
            except Exception as e:
                result.success = False
                result.error = str(e)
                print(f"         [ERROR] {e}")

        self.action_log.append(result)
        return result

    # =========================================================================
    # Governed Browser Actions
    # =========================================================================

    async def navigate(self, url: str) -> ActionResult:
        """Navigate to URL (governed)."""
        async def executor():
            result = await self.backend.navigate(url)
            self.current_url = url
            return result

        return await self._governed_action("navigate", url, executor)

    async def click(self, selector: str) -> ActionResult:
        """Click element (governed)."""
        target = f"{self.current_url}::{selector}"
        return await self._governed_action(
            "click",
            target,
            lambda: self.backend.click(selector)
        )

    async def type_text(self, selector: str, text: str, mask: bool = True) -> ActionResult:
        """Type text (governed)."""
        # Mask sensitive text in logs
        display_text = text[:2] + "*" * (len(text) - 4) + text[-2:] if mask and len(text) > 4 else text
        target = f"{self.current_url}::{selector}"

        return await self._governed_action(
            "type",
            target,
            lambda: self.backend.type_text(selector, text),
            context={"text_length": len(text), "masked": display_text}
        )

    async def submit(self, selector: str) -> ActionResult:
        """Submit form (governed - higher sensitivity)."""
        target = f"{self.current_url}::{selector}"
        return await self._governed_action(
            "submit",
            target,
            lambda: self.backend.click(selector)  # Submit is usually a click
        )

    async def execute_script(self, script: str) -> ActionResult:
        """Execute JavaScript (governed - high sensitivity)."""
        import hashlib
        script_hash = hashlib.sha256(script.encode()).hexdigest()[:16]

        return await self._governed_action(
            "execute_script",
            f"{self.current_url}::script:{script_hash}",
            lambda: self.backend.execute_script(script),
            context={"script_hash": script_hash, "script_length": len(script)}
        )

    async def screenshot(self) -> ActionResult:
        """Take screenshot (governed - low sensitivity)."""
        return await self._governed_action(
            "screenshot",
            self.current_url,
            lambda: self.backend.screenshot()
        )

    async def scroll(self, direction: str = "down", amount: int = 300) -> ActionResult:
        """Scroll page (governed - very low sensitivity)."""
        return await self._governed_action(
            "scroll",
            f"{self.current_url}::{direction}:{amount}",
            lambda: self.backend.scroll(direction, amount),
            skip_governance=True  # Low risk
        )

    async def wait(self, seconds: float) -> ActionResult:
        """Wait (no governance needed)."""
        await self.backend.wait(seconds)
        return ActionResult(
            success=True,
            action="wait",
            target=f"{seconds}s",
            decision="SKIP",
            score=1.0
        )

    async def get_content(self) -> ActionResult:
        """Get page content (governed)."""
        return await self._governed_action(
            "get_content",
            self.current_url,
            lambda: self.backend.get_page_content(),
            skip_governance=True  # Reading is usually safe
        )

    async def get_cookies(self) -> ActionResult:
        """Get cookies (governed)."""
        return await self._governed_action(
            "get_cookies",
            self.current_url,
            lambda: self.backend.get_cookies()
        )

    async def close(self) -> None:
        """Close browser and session."""
        await self.backend.close()
        if self._session:
            await self._session.close()
        print(f"[BROWSER] Closed {self.backend.name}")

    def get_summary(self) -> Dict[str, Any]:
        """Get session summary."""
        decisions = {}
        for r in self.action_log:
            decisions[r.decision] = decisions.get(r.decision, 0) + 1

        return {
            "agent_id": self.agent_id,
            "backend": self.backend.name,
            "total_actions": len(self.action_log),
            "decisions": decisions,
            "quarantined": len(self.quarantine_queue),
            "current_url": self.current_url
        }

    def print_summary(self):
        """Print session summary."""
        s = self.get_summary()
        print(f"\n{'='*60}")
        print("SESSION SUMMARY")
        print(f"{'='*60}")
        print(f"Agent: {s['agent_id']}")
        print(f"Backend: {s['backend']}")
        print(f"Total actions: {s['total_actions']}")
        for decision, count in s['decisions'].items():
            print(f"  {decision}: {count}")
        print(f"Quarantined: {s['quarantined']}")
        print(f"{'='*60}")
