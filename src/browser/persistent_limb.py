"""
@file persistent_limb.py
@module browser/persistent_limb
@layer Layer 12, Layer 13
@component PersistentBrowserLimb — Stateful Browser Sessions for HYDRA

Wraps Playwright's launchPersistentContext to give each HYDRA finger a
durable browser profile.  Cookies, localStorage, sessionStorage, and
cache survive close → reopen cycles.

Key differences from ephemeral Finger.open():
  - Uses chromium.launch_persistent_context(userDataDir) instead of
    browser.new_context()
  - Each tongue gets its own userDataDir under a shared session root
  - Session keepalive via periodic health-check pings
  - Governance gating: every navigation is run through the Harmonic Wall
    (Layer 12) before execution

Integration points:
  - Drop-in replacement for HydraHand.Finger when persistence is needed
  - Compatible with AetherbrowseSession audit pipeline
  - Registers with HydraSpine as a governed limb

Usage:
    limb = PersistentBrowserLimb(session_id="research-alpha")
    await limb.open()

    page = await limb.navigate("KO", "https://example.com")
    text = await limb.extract_text("KO", "body")

    await limb.close()   # data flushed to userDataDir
    await limb.open()    # cookies + localStorage restored
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import os
import shutil
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger("hydra-persistent-limb")

# ── Constants ─────────────────────────────────────────────────────────

PHI = (1 + math.sqrt(5)) / 2  # Golden ratio ≈ 1.618

# Sacred Tongue identifiers
TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")

# Phi-weighted priority (golden ratio scaling) — same as hydra_hand.py
TONGUE_WEIGHT = {
    "KO": 1.000,
    "AV": 1.618,
    "RU": 2.618,
    "CA": 4.236,
    "UM": 6.854,
    "DR": 11.090,
}

# Default session root (override with HYDRA_SESSION_ROOT env)
DEFAULT_SESSION_ROOT = Path.home() / ".hydra" / "sessions"


# ── Domain Safety (mirrors hydra_hand.py) ─────────────────────────────

BLOCKED_DOMAINS = {
    "malware.com", "phishing.example", "evil.corp",
}

TRUSTED_DOMAINS = {
    "github.com", "huggingface.co", "arxiv.org", "scholar.google.com",
    "stackoverflow.com", "docs.python.org", "pypi.org",
    "en.wikipedia.org", "developer.mozilla.org",
}


def check_domain_safety(url: str) -> tuple[str, float]:
    """Quick domain check. Returns (decision, risk_score)."""
    domain = urlparse(url).netloc.lower()
    if any(blocked in domain for blocked in BLOCKED_DOMAINS):
        return "DENY", 1.0
    if any(trusted in domain for trusted in TRUSTED_DOMAINS):
        return "ALLOW", 0.0
    return "QUARANTINE", 0.5


# ── Harmonic Wall (Layer 12) ──────────────────────────────────────────

def harmonic_wall(d_star: float, R: float = 1.0) -> float:
    """
    H(d*, R) = R · π^(φ · d*)

    Cost grows exponentially with hyperbolic distance d* from safe origin.
    Safe actions (d*≈0) cost ~R.  Adversarial actions (d*>2) cost 100×+.

    # A4: Symmetry — cost function is monotonically increasing
    """
    return R * (math.pi ** (PHI * d_star))


# ── Governance Decision ───────────────────────────────────────────────

class GovernanceDecision(str, Enum):
    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    ESCALATE = "ESCALATE"
    DENY = "DENY"


@dataclass
class GovernanceResult:
    """Result of a governance check on a browser action."""
    decision: GovernanceDecision
    risk_score: float
    harmonic_cost: float
    tongue: str
    url: str
    domain_decision: str
    explanation: str


def evaluate_browser_action(
    tongue: str,
    url: str,
    action_type: str = "navigate",
    session_risk: float = 0.0,
) -> GovernanceResult:
    """
    Evaluate a browser action through the SCBE governance pipeline.

    Combines:
      - Domain safety check (RU tongue's job)
      - Tongue weight scaling (higher-weight tongues = more powerful = more risk)
      - Session accumulated risk
      - Harmonic Wall cost calculation

    Returns GovernanceResult with decision and cost.
    """
    domain_decision, domain_risk = check_domain_safety(url)

    # If domain is outright blocked, DENY immediately
    if domain_decision == "DENY":
        return GovernanceResult(
            decision=GovernanceDecision.DENY,
            risk_score=1.0,
            harmonic_cost=float("inf"),
            tongue=tongue,
            url=url,
            domain_decision=domain_decision,
            explanation=f"Domain blocked by RU safety filter",
        )

    # Action risk weights
    action_risk = {
        "navigate": 0.10,
        "extract_text": 0.05,
        "extract_links": 0.05,
        "screenshot": 0.15,
        "run_js": 0.80,
        "click": 0.30,
        "type": 0.40,
    }.get(action_type, 0.20)

    # Tongue weight contribution — higher tongues carry more authority but more risk
    tongue_w = TONGUE_WEIGHT.get(tongue, 1.0)
    tongue_risk = tongue_w / 20.0  # Normalize: KO=0.05, DR=0.55

    # Composite risk: domain + action + tongue + session history
    composite_risk = min(1.0, (
        domain_risk * 0.35
        + action_risk * 0.30
        + tongue_risk * 0.15
        + session_risk * 0.20
    ))

    # Hyperbolic distance estimate from risk score
    # d* = risk / (1 - risk + epsilon) — maps [0,1) to [0,∞)
    epsilon = 1e-9
    d_star = composite_risk / (1.0 - composite_risk + epsilon)

    cost = harmonic_wall(d_star, R=1.0)

    # Decision thresholds (same as src/browser/evaluator.ts)
    if composite_risk <= 0.30:
        decision = GovernanceDecision.ALLOW
    elif composite_risk <= 0.60:
        decision = GovernanceDecision.QUARANTINE
    elif composite_risk <= 0.85:
        decision = GovernanceDecision.ESCALATE
    else:
        decision = GovernanceDecision.DENY

    return GovernanceResult(
        decision=decision,
        risk_score=composite_risk,
        harmonic_cost=cost,
        tongue=tongue,
        url=url,
        domain_decision=domain_decision,
        explanation=f"risk={composite_risk:.3f} cost={cost:.2f} domain={domain_decision} action={action_type}",
    )


# ── Persistent Finger ────────────────────────────────────────────────

@dataclass
class PersistentFingerStats:
    """Per-finger operational statistics."""
    actions: int = 0
    blocked: int = 0
    quarantined: int = 0
    total_cost: float = 0.0
    last_active: float = 0.0


@dataclass
class PersistentFinger:
    """
    A single persistent browser instance tied to a Sacred Tongue.

    Unlike the ephemeral Finger in hydra_hand.py, this uses
    launch_persistent_context with a dedicated userDataDir per tongue.
    """
    tongue: str
    user_data_dir: Path
    context: Any = None  # Playwright BrowserContext from launch_persistent_context
    page: Any = None
    active: bool = False
    stats: PersistentFingerStats = field(default_factory=PersistentFingerStats)

    @property
    def weight(self) -> float:
        return TONGUE_WEIGHT.get(self.tongue, 1.0)

    async def open(self, playwright_instance) -> None:
        """Launch a persistent browser context for this finger."""
        self.user_data_dir.mkdir(parents=True, exist_ok=True)

        launch_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ]

        # UM (Shadow) gets stealth flags
        if self.tongue == "UM":
            launch_args.extend([
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions",
            ])

        context_opts: Dict[str, Any] = {
            "headless": True,
            "args": launch_args,
        }

        # Stealth user-agent for UM
        if self.tongue == "UM":
            context_opts["user_agent"] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )

        # THIS IS THE KEY DIFFERENCE: persistent context, not ephemeral
        self.context = await playwright_instance.chromium.launch_persistent_context(
            str(self.user_data_dir),
            **context_opts,
        )

        # Reuse the default page or create one
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        self.active = True
        self.stats.last_active = time.monotonic()
        logger.info("[%s] Persistent finger opened (dir=%s)", self.tongue, self.user_data_dir)

    async def close(self) -> None:
        """Close the persistent context (data flushes to disk)."""
        if self.context:
            await self.context.close()
            self.context = None
            self.page = None
            self.active = False
            logger.info("[%s] Persistent finger closed (data preserved)", self.tongue)

    async def navigate(self, url: str, timeout: int = 15000) -> Dict[str, Any]:
        """Navigate to URL and return result dict."""
        if not self.active or not self.page:
            raise RuntimeError(f"Finger [{self.tongue}] not active")

        start = time.monotonic()
        try:
            response = await self.page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            title = await self.page.title()
            self.stats.actions += 1
            self.stats.last_active = time.monotonic()
            return {
                "tongue": self.tongue,
                "url": url,
                "title": title,
                "status": response.status if response else 0,
                "elapsed_ms": (time.monotonic() - start) * 1000,
            }
        except Exception as e:
            return {
                "tongue": self.tongue,
                "url": url,
                "error": str(e),
                "elapsed_ms": (time.monotonic() - start) * 1000,
            }

    async def extract_text(self, selector: str = "body") -> str:
        """Extract text content from current page."""
        if not self.page:
            return ""
        try:
            el = await self.page.query_selector(selector)
            if el:
                return await el.inner_text()
            return ""
        except Exception:
            return ""

    async def extract_links(self) -> List[str]:
        """Extract all links from current page."""
        if not self.page:
            return []
        try:
            links = await self.page.eval_on_selector_all(
                "a[href]",
                "els => els.map(e => e.href).filter(h => h.startsWith('http'))"
            )
            return links[:100]
        except Exception:
            return []

    async def screenshot(self, path: str) -> str:
        """Take screenshot, return path."""
        if not self.page:
            raise RuntimeError(f"Finger [{self.tongue}] has no page")
        await self.page.screenshot(path=path, full_page=True)
        self.stats.actions += 1
        return path

    async def run_js(self, script: str) -> Any:
        """Execute JavaScript on current page."""
        if not self.page:
            raise RuntimeError(f"Finger [{self.tongue}] has no page")
        return await self.page.evaluate(script)

    async def health_check(self) -> bool:
        """Ping the browser to verify it's still responsive."""
        if not self.page:
            return False
        try:
            await self.page.evaluate("() => true")
            return True
        except Exception:
            self.active = False
            return False


# ── Persistent Browser Limb ──────────────────────────────────────────

class PersistentBrowserLimb:
    """
    A HYDRA limb with 6 persistent browser sessions (one per Sacred Tongue).

    Each tongue gets its own userDataDir for cookie/localStorage isolation.
    All actions are gated through the Harmonic Wall (Layer 12) governance.

    Lifecycle:
        limb = PersistentBrowserLimb("research-alpha")
        await limb.open()
        # ... use limb.navigate(), limb.extract_text(), etc.
        await limb.close()      # data persists to disk
        await limb.open()       # cookies/storage restored

    Spine integration:
        limb.register_with_spine(spine)  # HYDRA spine governance
    """

    def __init__(
        self,
        session_id: str = "default",
        session_root: Optional[Path] = None,
        tongues: Optional[List[str]] = None,
        governance_enabled: bool = True,
        keepalive_interval_s: float = 30.0,
    ):
        self.session_id = session_id
        self.session_root = session_root or Path(
            os.environ.get("HYDRA_SESSION_ROOT", str(DEFAULT_SESSION_ROOT))
        )
        self.tongues = tongues or list(TONGUES)
        self.governance_enabled = governance_enabled
        self.keepalive_interval_s = keepalive_interval_s

        self._playwright = None
        self._open = False
        self._keepalive_task: Optional[asyncio.Task] = None
        self._session_risk: float = 0.0  # Accumulated session risk
        self._audit_log: List[Dict[str, Any]] = []

        # Create fingers with isolated userDataDirs
        self.fingers: Dict[str, PersistentFinger] = {}
        for t in self.tongues:
            user_data_dir = self.session_root / session_id / t.lower()
            self.fingers[t] = PersistentFinger(tongue=t, user_data_dir=user_data_dir)

    async def open(self) -> None:
        """Open all persistent fingers in parallel."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright not installed. Run:\n"
                "  pip install playwright && playwright install chromium"
            )

        self._playwright = await async_playwright().__aenter__()

        # Open all fingers in parallel
        await asyncio.gather(*[
            f.open(self._playwright) for f in self.fingers.values()
        ])

        self._open = True

        # Start keepalive loop
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())

        logger.info(
            "[%s] PersistentBrowserLimb opened — %d fingers active",
            self.session_id, len(self.fingers),
        )

    async def close(self) -> None:
        """Close all fingers (data persists to disk)."""
        # Cancel keepalive
        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
            self._keepalive_task = None

        # Close all fingers
        await asyncio.gather(*[
            f.close() for f in self.fingers.values()
        ])

        if self._playwright:
            await self._playwright.__aexit__(None, None, None)
            self._playwright = None

        self._open = False
        logger.info("[%s] PersistentBrowserLimb closed (data preserved)", self.session_id)

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, *args):
        await self.close()

    # ── Governance-Gated Actions ──────────────────────────────────────

    def _gate(
        self,
        tongue: str,
        url: str,
        action_type: str = "navigate",
    ) -> GovernanceResult:
        """
        Run an action through the governance pipeline.

        Returns GovernanceResult. Caller must check .decision before executing.
        """
        result = evaluate_browser_action(
            tongue=tongue,
            url=url,
            action_type=action_type,
            session_risk=self._session_risk,
        )

        # Update session risk with decay
        if result.decision == GovernanceDecision.DENY:
            self._session_risk = min(1.0, self._session_risk + 0.15)
        elif result.decision == GovernanceDecision.ESCALATE:
            self._session_risk = min(1.0, self._session_risk + 0.08)
        elif result.decision == GovernanceDecision.QUARANTINE:
            self._session_risk = min(1.0, self._session_risk + 0.03)
        else:
            # ALLOW — gentle decay
            self._session_risk = max(0.0, self._session_risk - 0.01)

        # Record audit
        self._audit_log.append({
            "session_id": self.session_id,
            "tongue": tongue,
            "url": url,
            "action_type": action_type,
            "decision": result.decision.value,
            "risk_score": result.risk_score,
            "harmonic_cost": result.harmonic_cost,
            "session_risk": self._session_risk,
            "timestamp": time.time(),
        })

        return result

    async def navigate(
        self,
        tongue: str,
        url: str,
        timeout: int = 15000,
    ) -> Dict[str, Any]:
        """
        Navigate a finger to a URL with governance gating.

        Args:
            tongue: Sacred Tongue identifier (KO, AV, RU, CA, UM, DR)
            url: Target URL
            timeout: Navigation timeout in ms

        Returns:
            Dict with navigation result and governance metadata
        """
        finger = self._get_finger(tongue)

        # Governance gate
        if self.governance_enabled:
            gov = self._gate(tongue, url, "navigate")
            if gov.decision == GovernanceDecision.DENY:
                finger.stats.blocked += 1
                return {
                    "tongue": tongue,
                    "url": url,
                    "blocked": True,
                    "governance": {
                        "decision": gov.decision.value,
                        "risk_score": gov.risk_score,
                        "harmonic_cost": gov.harmonic_cost,
                        "explanation": gov.explanation,
                    },
                }
            if gov.decision == GovernanceDecision.QUARANTINE:
                finger.stats.quarantined += 1
                logger.warning("[%s/%s] QUARANTINED: %s — proceeding with caution", self.session_id, tongue, url)

        result = await finger.navigate(url, timeout=timeout)

        # Attach governance metadata if enabled
        if self.governance_enabled:
            result["governance"] = {
                "decision": gov.decision.value,
                "risk_score": gov.risk_score,
                "harmonic_cost": gov.harmonic_cost,
            }
            finger.stats.total_cost += gov.harmonic_cost

        return result

    async def extract_text(self, tongue: str, selector: str = "body") -> str:
        """Extract text from a finger's current page."""
        return await self._get_finger(tongue).extract_text(selector)

    async def extract_links(self, tongue: str) -> List[str]:
        """Extract links from a finger's current page."""
        return await self._get_finger(tongue).extract_links()

    async def screenshot(self, tongue: str, path: str) -> str:
        """Take a screenshot from a finger."""
        return await self._get_finger(tongue).screenshot(path)

    async def run_js(self, tongue: str, script: str) -> Any:
        """Execute JS on a finger's page with governance check."""
        finger = self._get_finger(tongue)

        if self.governance_enabled:
            current_url = finger.page.url if finger.page else "about:blank"
            gov = self._gate(tongue, current_url, "run_js")
            if gov.decision in (GovernanceDecision.DENY, GovernanceDecision.ESCALATE):
                finger.stats.blocked += 1
                raise PermissionError(
                    f"JS execution blocked by governance: {gov.explanation}"
                )

        return await finger.run_js(script)

    # ── Multi-Action Dispatch ─────────────────────────────────────────

    async def multi_navigate(
        self,
        tasks: List[Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        """
        Navigate multiple fingers to different URLs in parallel.

        Args:
            tasks: List of {"tongue": "CA", "url": "https://..."} dicts

        Returns:
            List of navigation results
        """
        coros = [
            self.navigate(t["tongue"], t["url"])
            for t in tasks
        ]
        return await asyncio.gather(*coros)

    # ── Session Management ────────────────────────────────────────────

    def purge_session(self, tongue: Optional[str] = None) -> None:
        """
        Delete persistent data for one or all tongues.

        WARNING: This destroys cookies, localStorage, cache — irreversible.
        """
        if tongue:
            finger = self.fingers.get(tongue)
            if finger and finger.user_data_dir.exists():
                shutil.rmtree(finger.user_data_dir, ignore_errors=True)
                logger.info("[%s/%s] Session data purged", self.session_id, tongue)
        else:
            session_dir = self.session_root / self.session_id
            if session_dir.exists():
                shutil.rmtree(session_dir, ignore_errors=True)
                logger.info("[%s] All session data purged", self.session_id)

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Return the governance audit trail."""
        return list(self._audit_log)

    def status(self) -> Dict[str, Any]:
        """Limb status summary."""
        return {
            "session_id": self.session_id,
            "open": self._open,
            "session_risk": self._session_risk,
            "total_audit_entries": len(self._audit_log),
            "fingers": {
                t: {
                    "active": f.active,
                    "weight": f.weight,
                    "actions": f.stats.actions,
                    "blocked": f.stats.blocked,
                    "quarantined": f.stats.quarantined,
                    "total_cost": f.stats.total_cost,
                    "user_data_dir": str(f.user_data_dir),
                }
                for t, f in self.fingers.items()
            },
        }

    # ── Spine Integration ─────────────────────────────────────────────

    def register_with_spine(self, spine: Any) -> None:
        """Register this limb with a HydraSpine for governed orchestration."""
        if hasattr(spine, "register_limb"):
            spine.register_limb(self.session_id, self)
            logger.info("[%s] Registered with HydraSpine", self.session_id)

    # ── Internal ──────────────────────────────────────────────────────

    def _get_finger(self, tongue: str) -> PersistentFinger:
        """Get a finger by tongue, with validation."""
        if tongue not in self.fingers:
            raise ValueError(f"Unknown tongue '{tongue}'. Valid: {list(self.fingers.keys())}")
        finger = self.fingers[tongue]
        if not finger.active:
            raise RuntimeError(f"Finger [{tongue}] is not active. Call limb.open() first.")
        return finger

    async def _keepalive_loop(self) -> None:
        """Periodic health check for all fingers."""
        while self._open:
            try:
                await asyncio.sleep(self.keepalive_interval_s)
                for tongue, finger in self.fingers.items():
                    if finger.active:
                        ok = await finger.health_check()
                        if not ok:
                            logger.warning(
                                "[%s/%s] Health check failed — finger marked inactive",
                                self.session_id, tongue,
                            )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("[%s] Keepalive error: %s", self.session_id, e)


# ── Factory ───────────────────────────────────────────────────────────

async def create_persistent_limb(
    session_id: str = "default",
    tongues: Optional[List[str]] = None,
    governance_enabled: bool = True,
    session_root: Optional[Path] = None,
) -> PersistentBrowserLimb:
    """
    Factory: create and open a PersistentBrowserLimb.

    Usage:
        limb = await create_persistent_limb("research-alpha")
        result = await limb.navigate("CA", "https://arxiv.org")
        await limb.close()
    """
    limb = PersistentBrowserLimb(
        session_id=session_id,
        tongues=tongues,
        governance_enabled=governance_enabled,
        session_root=session_root,
    )
    await limb.open()
    return limb
