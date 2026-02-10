"""
SCBE-AETHERMOORE Browser Agent
==============================

A browser automation agent governed by the SCBE 4-tier decision system.

Every action (navigate, click, type, submit) goes through:
1. SCBE API authorization check
2. 4-tier decision: ALLOW / QUARANTINE / ESCALATE / DENY
3. ESCALATE triggers higher AI review, then human if needed

Usage:
    python browser_agent.py

Requires:
    - SCBE API running at http://127.0.0.1:8080
    - API key set in environment or passed to agent
"""

import os
import sys
import json
import time
import hashlib
import requests
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from datetime import datetime, timezone


# =============================================================================
# Configuration
# =============================================================================

SCBE_API_URL = os.getenv("SCBE_API_URL", "http://127.0.0.1:8080")
SCBE_API_KEY = os.getenv("SCBE_API_KEY", "test-key-12345")

# Action sensitivity levels (higher = stricter governance)
ACTION_SENSITIVITY = {
    "navigate": 0.3,
    "click": 0.4,
    "type": 0.5,
    "submit": 0.7,
    "download": 0.8,
    "upload": 0.8,
    "execute_script": 0.9,
    "modify_cookies": 0.9,
    "access_storage": 0.7,
}

# Domain risk levels
DOMAIN_RISK = {
    "banking": 0.9,
    "financial": 0.85,
    "healthcare": 0.8,
    "government": 0.8,
    "social_media": 0.5,
    "shopping": 0.6,
    "news": 0.2,
    "search": 0.1,
    "default": 0.4,
}


# =============================================================================
# Data Classes
# =============================================================================

class Decision(str, Enum):
    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    ESCALATE = "ESCALATE"
    DENY = "DENY"


@dataclass
class GovernanceResult:
    """Result from SCBE governance check."""
    decision: Decision
    decision_id: str
    score: float
    explanation: Dict[str, Any]
    token: Optional[str] = None
    expires_at: Optional[str] = None

    @property
    def allowed(self) -> bool:
        return self.decision == Decision.ALLOW

    @property
    def needs_escalation(self) -> bool:
        return self.decision == Decision.ESCALATE

    @property
    def quarantined(self) -> bool:
        return self.decision == Decision.QUARANTINE

    @property
    def denied(self) -> bool:
        return self.decision == Decision.DENY


@dataclass
class BrowserAction:
    """Represents a browser action to be governed."""
    action_type: str
    target: str
    data: Optional[Dict[str, Any]] = None
    sensitivity: float = 0.5
    requires_roundtable: bool = False
    roundtable_tier: int = 1


@dataclass
class EscalationResult:
    """Result from escalation to higher AI or human."""
    source: str  # "higher_ai" or "human"
    decision: Decision
    reason: str
    timestamp: str


# =============================================================================
# SCBE Client
# =============================================================================

class SCBEClient:
    """Client for SCBE-AETHERMOORE API."""

    def __init__(self, api_url: str = SCBE_API_URL, api_key: str = SCBE_API_KEY):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "SCBE_api_key": self.api_key,
        })

    def health_check(self) -> bool:
        """Check if SCBE API is available."""
        try:
            resp = self.session.get(f"{self.api_url}/v1/health", timeout=5)
            return resp.status_code == 200 and resp.json().get("status") == "healthy"
        except Exception as e:
            print(f"[SCBE] Health check failed: {e}")
            return False

    def authorize(
        self,
        agent_id: str,
        action: str,
        target: str,
        sensitivity: float = 0.5,
        context: Optional[Dict[str, Any]] = None
    ) -> GovernanceResult:
        """Request authorization from SCBE API."""
        payload = {
            "agent_id": agent_id,
            "action": action,
            "target": target,
            "context": {
                "sensitivity": sensitivity,
                **(context or {})
            }
        }

        try:
            resp = self.session.post(
                f"{self.api_url}/v1/authorize",
                json=payload,
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()

            return GovernanceResult(
                decision=Decision(data["decision"]),
                decision_id=data["decision_id"],
                score=data["score"],
                explanation=data["explanation"],
                token=data.get("token"),
                expires_at=data.get("expires_at")
            )
        except requests.exceptions.RequestException as e:
            print(f"[SCBE] Authorization failed: {e}")
            # Fail-safe: DENY on API failure
            return GovernanceResult(
                decision=Decision.DENY,
                decision_id="error",
                score=0.0,
                explanation={"error": str(e)}
            )

    def roundtable(
        self,
        action: str,
        target: str,
        tier: int,
        signers: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Request Roundtable multi-sig approval."""
        payload = {
            "action": action,
            "target": target,
            "tier": tier,
            "signers": signers,
            "context": context or {}
        }

        try:
            resp = self.session.post(
                f"{self.api_url}/v1/roundtable",
                json=payload,
                timeout=30
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            print(f"[SCBE] Roundtable failed: {e}")
            return {"status": "REJECTED", "error": str(e)}

    def register_agent(
        self,
        agent_id: str,
        name: str,
        role: str,
        initial_trust: float = 0.5
    ) -> Dict[str, Any]:
        """Register a new agent with SCBE."""
        payload = {
            "agent_id": agent_id,
            "name": name,
            "role": role,
            "initial_trust": initial_trust
        }

        try:
            resp = self.session.post(
                f"{self.api_url}/v1/agents",
                json=payload,
                timeout=10
            )
            if resp.status_code == 409:
                # Agent already exists
                return {"agent_id": agent_id, "status": "exists"}
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            print(f"[SCBE] Agent registration failed: {e}")
            return {"error": str(e)}


# =============================================================================
# Escalation Handlers
# =============================================================================

class EscalationHandler:
    """Handles escalation to higher AI or human."""

    def __init__(self):
        self.higher_ai_decisions: List[EscalationResult] = []
        self.human_decisions: List[EscalationResult] = []

    def ask_higher_ai(
        self,
        action: BrowserAction,
        original_result: GovernanceResult
    ) -> EscalationResult:
        """
        Simulate asking a higher AI for approval.
        In production, this would call another AI model.
        """
        print(f"\n[ESCALATE] Asking higher AI about: {action.action_type} -> {action.target}")
        print(f"           Original score: {original_result.score:.3f}")

        # Simulate higher AI decision based on action sensitivity
        # Higher AI is more permissive for low-sensitivity actions
        if action.sensitivity < 0.5:
            decision = Decision.ALLOW
            reason = "Low sensitivity action approved by supervisor AI"
        elif action.sensitivity < 0.7:
            decision = Decision.QUARANTINE
            reason = "Medium sensitivity - approved with monitoring"
        else:
            decision = Decision.ESCALATE  # Escalate to human
            reason = "High sensitivity - requires human approval"

        result = EscalationResult(
            source="higher_ai",
            decision=decision,
            reason=reason,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        self.higher_ai_decisions.append(result)

        print(f"           Higher AI decision: {decision.value} - {reason}")
        return result

    def ask_human(
        self,
        action: BrowserAction,
        original_result: GovernanceResult,
        ai_result: Optional[EscalationResult] = None
    ) -> EscalationResult:
        """
        Ask human for approval via console input.
        In production, this would integrate with a UI or notification system.
        """
        print(f"\n{'='*60}")
        print("[HUMAN APPROVAL REQUIRED]")
        print(f"{'='*60}")
        print(f"Action:      {action.action_type}")
        print(f"Target:      {action.target}")
        print(f"Sensitivity: {action.sensitivity}")
        print(f"SCBE Score:  {original_result.score:.3f}")
        if ai_result:
            print(f"Higher AI:   {ai_result.decision.value} - {ai_result.reason}")
        print(f"{'='*60}")

        while True:
            response = input("Approve? [y/n/q(quarantine)]: ").strip().lower()
            if response in ("y", "yes"):
                decision = Decision.ALLOW
                reason = "Human approved"
                break
            elif response in ("n", "no"):
                decision = Decision.DENY
                reason = "Human denied"
                break
            elif response in ("q", "quarantine"):
                decision = Decision.QUARANTINE
                reason = "Human approved with monitoring"
                break
            else:
                print("Please enter y, n, or q")

        result = EscalationResult(
            source="human",
            decision=decision,
            reason=reason,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        self.human_decisions.append(result)

        print(f"Human decision: {decision.value}")
        return result


# =============================================================================
# Browser Agent
# =============================================================================

class SCBEBrowserAgent:
    """
    Browser automation agent governed by SCBE.

    Every action goes through the governance pipeline:
    1. Check SCBE API for authorization
    2. Handle 4-tier decision (ALLOW/QUARANTINE/ESCALATE/DENY)
    3. Execute action if approved
    4. Log all decisions for audit
    """

    def __init__(
        self,
        agent_id: str = "browser-agent-001",
        agent_name: str = "SCBE Browser Agent",
        initial_trust: float = 0.7,
        auto_escalate: bool = True
    ):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.initial_trust = initial_trust
        self.auto_escalate = auto_escalate

        # Initialize components
        self.scbe = SCBEClient()
        self.escalation = EscalationHandler()

        # Action log
        self.action_log: List[Dict[str, Any]] = []

        # Quarantine queue (actions pending review)
        self.quarantine_queue: List[Dict[str, Any]] = []

        # Initialize
        self._initialize()

    def _initialize(self):
        """Initialize the agent with SCBE."""
        print(f"[AGENT] Initializing {self.agent_name} ({self.agent_id})")

        # Check API health
        if not self.scbe.health_check():
            raise RuntimeError("SCBE API not available")
        print("[AGENT] SCBE API connected")

        # Register agent
        result = self.scbe.register_agent(
            agent_id=self.agent_id,
            name=self.agent_name,
            role="browser_automation",
            initial_trust=self.initial_trust
        )
        print(f"[AGENT] Registered: {result}")

    def _get_domain_risk(self, url: str) -> float:
        """Calculate risk level based on domain."""
        url_lower = url.lower()

        if any(x in url_lower for x in ["bank", "finance", "pay", "money"]):
            return DOMAIN_RISK["banking"]
        elif any(x in url_lower for x in ["health", "medical", "doctor"]):
            return DOMAIN_RISK["healthcare"]
        elif any(x in url_lower for x in [".gov", "government"]):
            return DOMAIN_RISK["government"]
        elif any(x in url_lower for x in ["facebook", "twitter", "instagram", "tiktok"]):
            return DOMAIN_RISK["social_media"]
        elif any(x in url_lower for x in ["amazon", "ebay", "shop", "store"]):
            return DOMAIN_RISK["shopping"]
        elif any(x in url_lower for x in ["google", "bing", "duckduckgo"]):
            return DOMAIN_RISK["search"]
        else:
            return DOMAIN_RISK["default"]

    def _calculate_sensitivity(self, action: BrowserAction) -> float:
        """Calculate combined sensitivity for an action."""
        base_sensitivity = ACTION_SENSITIVITY.get(action.action_type, 0.5)
        domain_risk = self._get_domain_risk(action.target)

        # Combine: average weighted toward higher value
        combined = (base_sensitivity * 0.6) + (domain_risk * 0.4)
        return min(1.0, combined)

    def _log_action(
        self,
        action: BrowserAction,
        result: GovernanceResult,
        executed: bool,
        escalation: Optional[EscalationResult] = None
    ):
        """Log action for audit trail."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action_type": action.action_type,
            "target": action.target,
            "sensitivity": action.sensitivity,
            "decision": result.decision.value,
            "score": result.score,
            "decision_id": result.decision_id,
            "executed": executed,
            "escalation": escalation.__dict__ if escalation else None
        }
        self.action_log.append(entry)

    def govern(self, action: BrowserAction) -> tuple[bool, GovernanceResult]:
        """
        Run governance check on an action.

        Returns:
            (can_execute, governance_result)
        """
        # Calculate sensitivity if not set
        if action.sensitivity == 0.5:  # default
            action.sensitivity = self._calculate_sensitivity(action)

        print(f"\n[GOVERN] {action.action_type.upper()} -> {action.target}")
        print(f"         Sensitivity: {action.sensitivity:.2f}")

        # Get SCBE authorization
        result = self.scbe.authorize(
            agent_id=self.agent_id,
            action=action.action_type.upper(),
            target=action.target,
            sensitivity=action.sensitivity,
            context=action.data
        )

        print(f"         Decision: {result.decision.value} (score: {result.score:.3f})")

        # Handle decision
        can_execute = False
        escalation_result = None

        if result.allowed:
            can_execute = True
            print("         [ALLOW] Proceeding with action")

        elif result.quarantined:
            print("         [QUARANTINE] Action isolated for monitoring")
            self.quarantine_queue.append({
                "action": action,
                "result": result,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            # In quarantine mode, we might still execute with extra logging
            can_execute = True  # Execute but monitored

        elif result.needs_escalation:
            if self.auto_escalate:
                # First ask higher AI
                ai_result = self.escalation.ask_higher_ai(action, result)
                escalation_result = ai_result

                if ai_result.decision == Decision.ALLOW:
                    can_execute = True
                elif ai_result.decision == Decision.ESCALATE:
                    # Higher AI wants human approval
                    human_result = self.escalation.ask_human(action, result, ai_result)
                    escalation_result = human_result
                    can_execute = human_result.decision in (Decision.ALLOW, Decision.QUARANTINE)
                elif ai_result.decision == Decision.QUARANTINE:
                    can_execute = True  # Execute but monitored
                else:
                    can_execute = False
            else:
                print("         [ESCALATE] Manual escalation required")
                can_execute = False

        elif result.denied:
            print("         [DENY] Action blocked")
            can_execute = False

        # Log the action
        self._log_action(action, result, can_execute, escalation_result)

        return can_execute, result

    # =========================================================================
    # Browser Actions (each governed by SCBE)
    # =========================================================================

    def navigate(self, url: str) -> bool:
        """Navigate to a URL (governed)."""
        action = BrowserAction(
            action_type="navigate",
            target=url,
            data={"url": url}
        )

        can_execute, result = self.govern(action)

        if can_execute:
            print(f"         Navigating to: {url}")
            # In real implementation, this would use browser automation
            # e.g., selenium, playwright, or Chrome DevTools Protocol
            return True
        return False

    def click(self, selector: str, page_url: str = "") -> bool:
        """Click an element (governed)."""
        action = BrowserAction(
            action_type="click",
            target=f"{page_url}::{selector}",
            data={"selector": selector, "page": page_url}
        )

        can_execute, result = self.govern(action)

        if can_execute:
            print(f"         Clicking: {selector}")
            return True
        return False

    def type_text(self, selector: str, text: str, page_url: str = "") -> bool:
        """Type text into an element (governed)."""
        # Mask sensitive data in logs
        masked_text = text if len(text) < 4 else text[:2] + "*" * (len(text) - 4) + text[-2:]

        action = BrowserAction(
            action_type="type",
            target=f"{page_url}::{selector}",
            data={"selector": selector, "text_length": len(text), "masked": masked_text}
        )

        can_execute, result = self.govern(action)

        if can_execute:
            print(f"         Typing into: {selector}")
            return True
        return False

    def submit_form(self, form_selector: str, page_url: str = "") -> bool:
        """Submit a form (governed - higher sensitivity)."""
        action = BrowserAction(
            action_type="submit",
            target=f"{page_url}::{form_selector}",
            data={"form": form_selector, "page": page_url}
        )

        can_execute, result = self.govern(action)

        if can_execute:
            print(f"         Submitting form: {form_selector}")
            return True
        return False

    def download_file(self, url: str, filename: str = "") -> bool:
        """Download a file (governed - high sensitivity)."""
        action = BrowserAction(
            action_type="download",
            target=url,
            data={"filename": filename},
            sensitivity=0.8  # High sensitivity
        )

        can_execute, result = self.govern(action)

        if can_execute:
            print(f"         Downloading: {url}")
            return True
        return False

    def execute_script(self, script: str, page_url: str = "") -> bool:
        """Execute JavaScript (governed - very high sensitivity)."""
        # Hash script for logging (don't log full script)
        script_hash = hashlib.sha256(script.encode()).hexdigest()[:16]

        action = BrowserAction(
            action_type="execute_script",
            target=f"{page_url}::script",
            data={"script_hash": script_hash, "script_length": len(script)},
            sensitivity=0.9  # Very high sensitivity
        )

        can_execute, result = self.govern(action)

        if can_execute:
            print(f"         Executing script (hash: {script_hash})")
            return True
        return False

    # =========================================================================
    # High-Security Actions (require Roundtable approval)
    # =========================================================================

    def critical_action(
        self,
        action_type: str,
        target: str,
        tier: int = 4,
        signers: Optional[List[str]] = None
    ) -> bool:
        """
        Execute a critical action requiring Roundtable multi-sig approval.

        Tier 4+ requires multiple Sacred Tongue signatures.
        """
        if signers is None:
            signers = [self.agent_id] * tier  # Self-sign (in production, different agents)

        print(f"\n[ROUNDTABLE] Tier {tier} approval required for: {action_type}")

        result = self.scbe.roundtable(
            action=action_type,
            target=target,
            tier=tier,
            signers=signers,
            context={"agent": self.agent_id}
        )

        print(f"             Status: {result.get('status')}")
        print(f"             Tongues: {result.get('tongues_used', [])}")

        if result.get("status") == "APPROVED":
            print(f"             [APPROVED] Proceeding with critical action")
            return True
        elif result.get("status") == "ESCALATE_TO_HUMAN":
            print(f"             [ESCALATE] Requires human approval")
            # Ask human (handle non-interactive mode)
            try:
                human_input = input("             Human approval required [y/n]: ").strip().lower()
                return human_input in ("y", "yes")
            except EOFError:
                print("             [NON-INTERACTIVE] Defaulting to DENY")
                return False
        else:
            print(f"             [REJECTED] Critical action blocked")
            return False

    # =========================================================================
    # Reporting
    # =========================================================================

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get the action audit log."""
        return self.action_log

    def get_quarantine_queue(self) -> List[Dict[str, Any]]:
        """Get actions in quarantine."""
        return self.quarantine_queue

    def print_summary(self):
        """Print session summary."""
        print(f"\n{'='*60}")
        print("SESSION SUMMARY")
        print(f"{'='*60}")
        print(f"Agent: {self.agent_name} ({self.agent_id})")
        print(f"Total actions: {len(self.action_log)}")

        # Count by decision
        decisions = {}
        for entry in self.action_log:
            d = entry["decision"]
            decisions[d] = decisions.get(d, 0) + 1

        for decision, count in decisions.items():
            print(f"  {decision}: {count}")

        print(f"Quarantined: {len(self.quarantine_queue)}")
        print(f"Escalations (AI): {len(self.escalation.higher_ai_decisions)}")
        print(f"Escalations (Human): {len(self.escalation.human_decisions)}")
        print(f"{'='*60}")


# =============================================================================
# Demo / CLI
# =============================================================================

def demo():
    """Run a demo of the SCBE Browser Agent."""
    print("="*60)
    print("SCBE-AETHERMOORE Browser Agent Demo")
    print("="*60)

    # Create agent
    agent = SCBEBrowserAgent(
        agent_id="demo-browser-001",
        agent_name="Demo Browser Agent",
        initial_trust=0.75,
        auto_escalate=True
    )

    # Test various actions
    print("\n--- Testing Navigation ---")
    agent.navigate("https://google.com")  # Low risk
    agent.navigate("https://news.ycombinator.com")  # Low risk
    agent.navigate("https://bank.example.com/login")  # High risk

    print("\n--- Testing Clicks ---")
    agent.click("#search-button", "https://google.com")
    agent.click("#login-form", "https://bank.example.com")

    print("\n--- Testing Form Submission ---")
    agent.submit_form("#payment-form", "https://shop.example.com/checkout")

    print("\n--- Testing Script Execution ---")
    agent.execute_script("console.log('test');", "https://example.com")

    print("\n--- Testing Critical Action (Roundtable) ---")
    agent.critical_action(
        action_type="DEPLOY",
        target="production-config",
        tier=4
    )

    # Print summary
    agent.print_summary()

    return agent


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        print("SCBE Browser Agent")
        print("Usage: python browser_agent.py demo")
        print("\nOr import and use programmatically:")
        print("  from browser_agent import SCBEBrowserAgent")
        print("  agent = SCBEBrowserAgent()")
        print("  agent.navigate('https://example.com')")
