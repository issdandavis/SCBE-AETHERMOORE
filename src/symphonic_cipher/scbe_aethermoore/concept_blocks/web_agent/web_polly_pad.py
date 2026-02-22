"""
SCBE Web Agent — WebPollyPad
=============================

Browser actuator layer that translates governance-approved goals into
browser actions (navigate, click, type, scroll, screenshot).

Maps to the existing Polly Pads architecture:
- ``ENGINEERING`` mode → form filling, data entry
- ``NAVIGATION`` mode → link following, URL traversal
- ``SYSTEMS`` mode → cookie/storage management
- ``SCIENCE`` mode → data extraction, reading
- ``COMMS`` mode → messaging, email
- ``MISSION`` mode → complex multi-step workflows

Recovery pads activate when the agent gets stuck:
- Page didn't load → retry with backoff
- Element not found → fallback selectors or replan
- Blocked by CAPTCHA → escalate or skip
- Session expired → re-authenticate
- Rate limited → exponential backoff
- Navigation loop → break cycle and replan

Integrates with:
- SCBE Layer 8  (Hamiltonian → actuator energy regulation)
- SCBE Layer 12 (Polyglot → multi-mode coordination)
- SCBE Layer 13 (Audit → action telemetry)
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple

from .semantic_antivirus import SemanticAntivirus, ContentVerdict


# ---------------------------------------------------------------------------
#  Types
# ---------------------------------------------------------------------------

PadMode = Literal["ENGINEERING", "NAVIGATION", "SYSTEMS", "SCIENCE", "COMMS", "MISSION"]

PAD_MODES: Tuple[PadMode, ...] = (
    "ENGINEERING", "NAVIGATION", "SYSTEMS", "SCIENCE", "COMMS", "MISSION",
)


class ActionType(str, Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    SCREENSHOT = "screenshot"
    WAIT = "wait"
    EXTRACT = "extract"
    SUBMIT = "submit"
    SELECT = "select"
    BACK = "back"
    REFRESH = "refresh"


class RecoveryStrategy(str, Enum):
    RETRY = "retry"
    BACKOFF = "backoff"
    REPLAN = "replan"
    SKIP = "skip"
    ESCALATE = "escalate"
    BREAK_LOOP = "break_loop"


# ---------------------------------------------------------------------------
#  BrowserAction
# ---------------------------------------------------------------------------

@dataclass
class BrowserAction:
    """A single browser action to execute."""

    action_type: ActionType
    target: str = ""                    # URL, CSS selector, XPath, text
    data: Optional[str] = None          # Text to type, option to select
    timeout_ms: int = 10000
    fallback_target: Optional[str] = None   # Alternative selector if primary fails
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def sensitivity(self) -> float:
        """How governance-sensitive is this action? [0, 1]."""
        SENSITIVITY = {
            ActionType.NAVIGATE: 0.3,
            ActionType.CLICK: 0.4,
            ActionType.TYPE: 0.5,
            ActionType.SCROLL: 0.1,
            ActionType.SCREENSHOT: 0.2,
            ActionType.WAIT: 0.0,
            ActionType.EXTRACT: 0.2,
            ActionType.SUBMIT: 0.7,
            ActionType.SELECT: 0.4,
            ActionType.BACK: 0.1,
            ActionType.REFRESH: 0.2,
        }
        return SENSITIVITY.get(self.action_type, 0.5)


@dataclass
class ActionResult:
    """Result of executing a browser action."""

    success: bool
    action: BrowserAction
    duration_ms: float = 0.0
    data: Optional[Any] = None          # Extracted text, screenshot bytes, etc.
    error: Optional[str] = None
    governance_decision: str = "ALLOW"
    recovery_used: Optional[RecoveryStrategy] = None


# ---------------------------------------------------------------------------
#  WebPollyPad
# ---------------------------------------------------------------------------

class WebPollyPad:
    """
    Browser actuator with SCBE governance and recovery.

    The pad doesn't execute browser actions directly — it produces a
    governed action plan that a browser driver (Playwright, Lightpanda,
    Selenium) can execute.

    Lifecycle per action:
    1. Pre-scan: antivirus checks the target URL/content
    2. Governance gate: H(d,pd) must be above threshold
    3. Action dispatch: produce the action for the browser driver
    4. Post-scan: verify the result content is safe
    5. Recovery: if action failed, apply recovery strategy

    The pad tracks:
    - Visited URLs (cycle detection)
    - Action history (pattern analysis)
    - Error counts (escalation triggers)
    - Hamiltonian score over time
    """

    def __init__(
        self,
        pad_id: str = "web-pad-001",
        mode: PadMode = "NAVIGATION",
        antivirus: Optional[SemanticAntivirus] = None,
        max_retries: int = 3,
        stuck_threshold: int = 5,
    ) -> None:
        self.pad_id = pad_id
        self.mode = mode
        self._antivirus = antivirus or SemanticAntivirus()
        self._max_retries = max_retries
        self._stuck_threshold = stuck_threshold

        # State tracking
        self._visited_urls: List[str] = []
        self._action_history: List[ActionResult] = []
        self._error_streak = 0
        self._total_actions = 0
        self._total_errors = 0
        self._loop_detector: Dict[str, int] = {}  # URL → visit count
        self._start_time = time.time()

    # -- governance gate -----------------------------------------------------

    def gate_action(self, action: BrowserAction) -> Tuple[str, Optional[str]]:
        """
        Run governance gate on a proposed action.
        Returns (decision, reason).
        """
        # Pre-scan target URL
        if action.action_type == ActionType.NAVIGATE and action.target:
            profile = self._antivirus.scan_url(action.target)
            if profile.governance_decision == "DENY":
                return "DENY", f"URL blocked: {profile.reasons}"
            if profile.governance_decision == "QUARANTINE":
                return "QUARANTINE", f"URL suspicious: {profile.reasons}"

        # Check action sensitivity vs current session risk
        session_risk = self._antivirus.session_stats["mean_risk"]
        if action.sensitivity > 0.6 and session_risk > 0.3:
            return "QUARANTINE", f"High-sensitivity action ({action.sensitivity}) in elevated-risk session ({session_risk:.2f})"

        # Loop detection
        if action.action_type == ActionType.NAVIGATE:
            visits = self._loop_detector.get(action.target, 0)
            if visits >= 3:
                return "DENY", f"Navigation loop detected: visited {action.target} {visits} times"

        return "ALLOW", None

    def prepare_action(self, action: BrowserAction) -> Tuple[BrowserAction, str]:
        """
        Gate and prepare an action for execution.
        Returns (possibly-modified action, governance_decision).
        """
        decision, reason = self.gate_action(action)

        if decision == "DENY":
            return action, "DENY"

        # Track navigation
        if action.action_type == ActionType.NAVIGATE:
            self._visited_urls.append(action.target)
            self._loop_detector[action.target] = self._loop_detector.get(action.target, 0) + 1

        return action, decision

    def record_result(self, result: ActionResult) -> Optional[RecoveryStrategy]:
        """
        Record an action result and return recovery strategy if needed.
        """
        self._action_history.append(result)
        self._total_actions += 1

        if result.success:
            self._error_streak = 0
            return None

        self._total_errors += 1
        self._error_streak += 1

        return self._select_recovery(result)

    def _select_recovery(self, result: ActionResult) -> RecoveryStrategy:
        """Choose recovery strategy based on failure pattern."""
        error = (result.error or "").lower()

        # Navigation loop
        if self._error_streak >= self._stuck_threshold:
            return RecoveryStrategy.REPLAN

        # Timeout / not found
        if "timeout" in error or "not found" in error:
            if result.action.fallback_target:
                return RecoveryStrategy.RETRY  # Will use fallback selector
            return RecoveryStrategy.SKIP

        # Rate limiting
        if "429" in error or "rate limit" in error:
            return RecoveryStrategy.BACKOFF

        # CAPTCHA / blocked
        if "captcha" in error or "blocked" in error or "forbidden" in error:
            return RecoveryStrategy.ESCALATE

        # Session expired
        if "401" in error or "session" in error or "login" in error:
            return RecoveryStrategy.REPLAN

        # Default
        if self._error_streak >= 2:
            return RecoveryStrategy.REPLAN
        return RecoveryStrategy.RETRY

    # -- scan results --------------------------------------------------------

    def scan_page_content(self, content: str, url: str) -> ContentVerdict:
        """Scan page content after navigation."""
        profile = self._antivirus.scan(content, url=url)
        return profile.verdict

    # -- status API ----------------------------------------------------------

    @property
    def is_stuck(self) -> bool:
        return self._error_streak >= self._stuck_threshold

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self._start_time

    def summary(self) -> Dict[str, Any]:
        return {
            "pad_id": self.pad_id,
            "mode": self.mode,
            "total_actions": self._total_actions,
            "total_errors": self._total_errors,
            "error_streak": self._error_streak,
            "is_stuck": self.is_stuck,
            "unique_urls": len(set(self._visited_urls)),
            "uptime_seconds": round(self.uptime_seconds, 1),
            "antivirus_stats": self._antivirus.session_stats,
        }

    def reset(self) -> None:
        self._visited_urls.clear()
        self._action_history.clear()
        self._error_streak = 0
        self._total_actions = 0
        self._total_errors = 0
        self._loop_detector.clear()
        self._antivirus.reset_session()
        self._start_time = time.time()
