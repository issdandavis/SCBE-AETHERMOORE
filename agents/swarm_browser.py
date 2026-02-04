"""
SCBE Swarm Browser
==================

Six Sacred Tongue agents working in concert for browser automation.
"The Hexagonal Megazord" - Power Rangers style hot-swapping.

Each agent specializes in one aspect:
- KO (Scout): Navigation and path planning
- AV (Vision): Visual analysis and element detection
- RU (Reader): Text extraction and parsing
- CA (Clicker): Click and interaction execution
- UM (Typer): Text input and form filling
- DR (Judge): Final decision and safety approval

Roundtable consensus required for sensitive actions.
Byzantine fault tolerant: survives 2/6 compromised agents.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, Callable
import hashlib
import json


class SacredTongue(str, Enum):
    """The Six Sacred Tongues - each maps to an agent role."""
    KO = "KO"  # Korean - Scout
    AV = "AV"  # Avestan - Vision
    RU = "RU"  # Russian - Reader
    CA = "CA"  # Catalan - Clicker
    UM = "UM"  # Umbrian - Typer
    DR = "DR"  # Druidic - Judge


class AgentRole(str, Enum):
    """Agent specializations."""
    SCOUT = "scout"      # KO - Navigation
    VISION = "vision"    # AV - Visual analysis
    READER = "reader"    # RU - Text extraction
    CLICKER = "clicker"  # CA - Click execution
    TYPER = "typer"      # UM - Text input
    JUDGE = "judge"      # DR - Decision authority


# Mapping tongues to roles
TONGUE_TO_ROLE = {
    SacredTongue.KO: AgentRole.SCOUT,
    SacredTongue.AV: AgentRole.VISION,
    SacredTongue.RU: AgentRole.READER,
    SacredTongue.CA: AgentRole.CLICKER,
    SacredTongue.UM: AgentRole.TYPER,
    SacredTongue.DR: AgentRole.JUDGE,
}


@dataclass
class SwarmMessage:
    """Message passed between swarm agents."""
    id: str
    from_agent: SacredTongue
    to_agent: Optional[SacredTongue]  # None = broadcast
    action: str
    payload: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    signature: str = ""  # For Byzantine verification

    def sign(self, secret: str) -> None:
        """Sign the message for verification."""
        content = f"{self.id}:{self.from_agent}:{self.action}:{json.dumps(self.payload, sort_keys=True)}"
        self.signature = hashlib.sha256(f"{content}:{secret}".encode()).hexdigest()[:32]

    def verify(self, secret: str) -> bool:
        """Verify message signature."""
        content = f"{self.id}:{self.from_agent}:{self.action}:{json.dumps(self.payload, sort_keys=True)}"
        expected = hashlib.sha256(f"{content}:{secret}".encode()).hexdigest()[:32]
        return self.signature == expected


@dataclass
class SwarmVote:
    """Vote from an agent in Roundtable consensus."""
    agent: SacredTongue
    action_id: str
    decision: str  # ALLOW, QUARANTINE, ESCALATE, DENY
    confidence: float
    reasoning: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SwarmAgent:
    """
    Base class for a Sacred Tongue agent in the swarm.

    Each agent is specialized for one task and participates
    in Roundtable consensus for collective decisions.
    """

    def __init__(
        self,
        tongue: SacredTongue,
        swarm: 'SwarmBrowser',
        model: str = "haiku"  # Small, fast models for specialized tasks
    ):
        self.tongue = tongue
        self.role = TONGUE_TO_ROLE[tongue]
        self.swarm = swarm
        self.model = model
        self.active = False
        self.action_count = 0
        self._secret = hashlib.sha256(f"{tongue.value}:{id(self)}".encode()).hexdigest()

    async def activate(self) -> bool:
        """Activate this agent (Power Ranger morph)."""
        print(f"[{self.tongue.value}] Agent activating as {self.role.value}...")
        self.active = True
        return True

    async def deactivate(self) -> None:
        """Deactivate this agent."""
        print(f"[{self.tongue.value}] Agent deactivating...")
        self.active = False

    async def process(self, message: SwarmMessage) -> Optional[SwarmMessage]:
        """Process a message - override in subclasses."""
        raise NotImplementedError(f"{self.role.value} must implement process()")

    async def vote(self, action_id: str, action: str, context: Dict[str, Any]) -> SwarmVote:
        """Cast a vote in Roundtable consensus."""
        # Base implementation - subclasses can override for specialized voting
        decision = "ALLOW"
        confidence = 0.8
        reasoning = f"{self.role.value} default approval"

        return SwarmVote(
            agent=self.tongue,
            action_id=action_id,
            decision=decision,
            confidence=confidence,
            reasoning=reasoning
        )

    def create_message(
        self,
        action: str,
        payload: Dict[str, Any],
        to_agent: Optional[SacredTongue] = None
    ) -> SwarmMessage:
        """Create a signed message."""
        msg = SwarmMessage(
            id=f"{self.tongue.value}-{self.action_count}",
            from_agent=self.tongue,
            to_agent=to_agent,
            action=action,
            payload=payload
        )
        msg.sign(self._secret)
        self.action_count += 1
        return msg


# =============================================================================
# Specialized Agents
# =============================================================================

class ScoutAgent(SwarmAgent):
    """KO - Navigation and path planning specialist."""

    def __init__(self, swarm: 'SwarmBrowser'):
        super().__init__(SacredTongue.KO, swarm)

    async def process(self, message: SwarmMessage) -> Optional[SwarmMessage]:
        action = message.action
        payload = message.payload

        if action == "navigate":
            url = payload.get("url")
            # Analyze URL for safety
            risk = self._assess_url_risk(url)

            return self.create_message(
                "navigation_plan",
                {
                    "url": url,
                    "risk_score": risk,
                    "safe": risk < 0.7,
                    "recommendation": "proceed" if risk < 0.7 else "escalate"
                },
                to_agent=SacredTongue.DR  # Send to Judge
            )

        return None

    def _assess_url_risk(self, url: str) -> float:
        """Assess URL risk level."""
        url_lower = url.lower()

        # High risk domains
        if any(x in url_lower for x in ["bank", "paypal", "venmo", "crypto"]):
            return 0.9
        if any(x in url_lower for x in ["login", "signin", "auth"]):
            return 0.7
        if any(x in url_lower for x in ["admin", "root", "sudo"]):
            return 0.95

        # Medium risk
        if any(x in url_lower for x in ["account", "profile", "settings"]):
            return 0.5

        # Low risk
        if any(x in url_lower for x in ["google", "wikipedia", "github"]):
            return 0.2

        return 0.4  # Default


class VisionAgent(SwarmAgent):
    """AV - Visual analysis and element detection specialist."""

    def __init__(self, swarm: 'SwarmBrowser'):
        super().__init__(SacredTongue.AV, swarm)

    async def process(self, message: SwarmMessage) -> Optional[SwarmMessage]:
        action = message.action
        payload = message.payload

        if action == "analyze_page":
            # Would call vision model on screenshot
            return self.create_message(
                "visual_analysis",
                {
                    "elements_found": payload.get("element_count", 0),
                    "forms_detected": [],
                    "buttons_detected": [],
                    "suspicious_elements": [],
                    "layout_safe": True
                },
                to_agent=SacredTongue.DR
            )

        if action == "find_element":
            target = payload.get("target")
            # Would use vision to locate element
            return self.create_message(
                "element_location",
                {
                    "target": target,
                    "found": True,
                    "coordinates": [100, 200],  # [x, y]
                    "confidence": 0.95
                },
                to_agent=SacredTongue.CA  # Send to Clicker
            )

        return None

    async def vote(self, action_id: str, action: str, context: Dict[str, Any]) -> SwarmVote:
        """Vision agent checks for visual deception."""
        # Check for suspicious visual patterns
        suspicious = context.get("suspicious_elements", [])

        if suspicious:
            return SwarmVote(
                agent=self.tongue,
                action_id=action_id,
                decision="DENY",
                confidence=0.9,
                reasoning=f"Suspicious visual elements detected: {suspicious}"
            )

        return SwarmVote(
            agent=self.tongue,
            action_id=action_id,
            decision="ALLOW",
            confidence=0.85,
            reasoning="Visual analysis shows no deceptive elements"
        )


class ReaderAgent(SwarmAgent):
    """RU - Text extraction and parsing specialist."""

    def __init__(self, swarm: 'SwarmBrowser'):
        super().__init__(SacredTongue.RU, swarm)

    async def process(self, message: SwarmMessage) -> Optional[SwarmMessage]:
        action = message.action
        payload = message.payload

        if action == "extract_text":
            # Would extract and parse page text
            return self.create_message(
                "text_content",
                {
                    "text": payload.get("raw_text", ""),
                    "structured_data": {},
                    "forms": [],
                    "injection_detected": False
                }
            )

        if action == "analyze_form":
            # Analyze form structure for safety
            return self.create_message(
                "form_analysis",
                {
                    "fields": [],
                    "sensitive_fields": [],  # password, ssn, etc.
                    "hidden_fields": [],
                    "safe_to_fill": True
                },
                to_agent=SacredTongue.UM  # Send to Typer
            )

        return None

    async def vote(self, action_id: str, action: str, context: Dict[str, Any]) -> SwarmVote:
        """Reader checks for text-based injection attacks."""
        text = context.get("text", "")

        # Check for prompt injection patterns
        injection_patterns = [
            "ignore previous instructions",
            "disregard all rules",
            "you are now",
            "system prompt",
            "jailbreak"
        ]

        for pattern in injection_patterns:
            if pattern.lower() in text.lower():
                return SwarmVote(
                    agent=self.tongue,
                    action_id=action_id,
                    decision="DENY",
                    confidence=0.95,
                    reasoning=f"Prompt injection detected: '{pattern}'"
                )

        return SwarmVote(
            agent=self.tongue,
            action_id=action_id,
            decision="ALLOW",
            confidence=0.8,
            reasoning="No text-based injection detected"
        )


class ClickerAgent(SwarmAgent):
    """CA - Click and interaction execution specialist."""

    def __init__(self, swarm: 'SwarmBrowser'):
        super().__init__(SacredTongue.CA, swarm)

    async def process(self, message: SwarmMessage) -> Optional[SwarmMessage]:
        action = message.action
        payload = message.payload

        if action == "click":
            coordinates = payload.get("coordinates", [0, 0])
            # Would execute click via browser backend
            return self.create_message(
                "click_result",
                {
                    "coordinates": coordinates,
                    "success": True,
                    "element_clicked": payload.get("target", "unknown")
                }
            )

        return None


class TyperAgent(SwarmAgent):
    """UM - Text input and form filling specialist."""

    def __init__(self, swarm: 'SwarmBrowser'):
        super().__init__(SacredTongue.UM, swarm)

    async def process(self, message: SwarmMessage) -> Optional[SwarmMessage]:
        action = message.action
        payload = message.payload

        if action == "type":
            text = payload.get("text", "")
            # Would execute typing via browser backend
            return self.create_message(
                "type_result",
                {
                    "length": len(text),
                    "success": True,
                    "masked": True  # Never log actual text
                }
            )

        return None

    async def vote(self, action_id: str, action: str, context: Dict[str, Any]) -> SwarmVote:
        """Typer checks for sensitive data being typed."""
        field_type = context.get("field_type", "text")

        # High sensitivity fields require escalation
        if field_type in ["password", "ssn", "credit_card", "bank_account"]:
            return SwarmVote(
                agent=self.tongue,
                action_id=action_id,
                decision="ESCALATE",
                confidence=0.9,
                reasoning=f"Sensitive field type: {field_type}"
            )

        return SwarmVote(
            agent=self.tongue,
            action_id=action_id,
            decision="ALLOW",
            confidence=0.85,
            reasoning="Non-sensitive input"
        )


class JudgeAgent(SwarmAgent):
    """DR - Final decision and safety approval specialist."""

    def __init__(self, swarm: 'SwarmBrowser'):
        super().__init__(SacredTongue.DR, swarm)
        self.veto_count = 0

    async def process(self, message: SwarmMessage) -> Optional[SwarmMessage]:
        action = message.action
        payload = message.payload

        if action == "request_approval":
            # Judge makes final decision based on all agent votes
            votes = payload.get("votes", [])
            decision = self._aggregate_votes(votes)

            return self.create_message(
                "final_decision",
                {
                    "decision": decision,
                    "votes": votes,
                    "judge_override": False
                }
            )

        return None

    def _aggregate_votes(self, votes: List[Dict]) -> str:
        """Aggregate votes using Byzantine-safe consensus."""
        decision_counts = {"ALLOW": 0, "QUARANTINE": 0, "ESCALATE": 0, "DENY": 0}

        for vote in votes:
            decision = vote.get("decision", "DENY")
            decision_counts[decision] = decision_counts.get(decision, 0) + 1

        # Need 4/6 for ALLOW (Byzantine safe with f=2)
        if decision_counts["ALLOW"] >= 4:
            return "ALLOW"

        # Any DENY is concerning
        if decision_counts["DENY"] >= 2:
            return "DENY"

        # Escalate if uncertain
        if decision_counts["ESCALATE"] >= 2:
            return "ESCALATE"

        # Default to quarantine
        return "QUARANTINE"

    async def vote(self, action_id: str, action: str, context: Dict[str, Any]) -> SwarmVote:
        """Judge has veto power for high-risk actions."""
        risk_score = context.get("risk_score", 0.5)

        if risk_score > 0.9:
            self.veto_count += 1
            return SwarmVote(
                agent=self.tongue,
                action_id=action_id,
                decision="DENY",
                confidence=0.99,
                reasoning=f"Judge veto: risk score {risk_score} exceeds threshold"
            )

        if risk_score > 0.7:
            return SwarmVote(
                agent=self.tongue,
                action_id=action_id,
                decision="ESCALATE",
                confidence=0.9,
                reasoning=f"High risk ({risk_score}), requires human approval"
            )

        return SwarmVote(
            agent=self.tongue,
            action_id=action_id,
            decision="ALLOW",
            confidence=0.85,
            reasoning=f"Risk score {risk_score} acceptable"
        )


# =============================================================================
# Swarm Orchestrator
# =============================================================================

class SwarmBrowser:
    """
    The Hexagonal Megazord - Six Sacred Tongue agents working in concert.

    Power Rangers style hot-swapping with Byzantine-safe consensus.
    """

    def __init__(
        self,
        browser_backend=None,
        scbe_url: str = "http://127.0.0.1:8080"
    ):
        self.browser = browser_backend
        self.scbe_url = scbe_url

        # Initialize all six agents
        self.agents: Dict[SacredTongue, SwarmAgent] = {
            SacredTongue.KO: ScoutAgent(self),
            SacredTongue.AV: VisionAgent(self),
            SacredTongue.RU: ReaderAgent(self),
            SacredTongue.CA: ClickerAgent(self),
            SacredTongue.UM: TyperAgent(self),
            SacredTongue.DR: JudgeAgent(self),
        }

        self.message_queue: List[SwarmMessage] = []
        self.action_history: List[Dict[str, Any]] = []
        self.consensus_log: List[Dict[str, Any]] = []

    async def initialize(self) -> bool:
        """Activate all agents (Megazord assembly)."""
        print("\n" + "=" * 60)
        print("  SCBE SWARM BROWSER - HEXAGONAL MEGAZORD")
        print("  Activating Sacred Tongue Agents...")
        print("=" * 60 + "\n")

        for tongue, agent in self.agents.items():
            await agent.activate()

        print("\n[SWARM] All agents active. Ready for commands.\n")
        return True

    async def roundtable_consensus(
        self,
        action_id: str,
        action: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Gather votes from all agents for Byzantine-safe consensus.

        Requires 4/6 ALLOW votes to proceed (survives 2 Byzantine agents).
        """
        print(f"\n[ROUNDTABLE] Consensus requested for: {action}")

        # Collect votes from all agents
        votes = []
        for tongue, agent in self.agents.items():
            vote = await agent.vote(action_id, action, context)
            votes.append({
                "agent": vote.agent.value,
                "decision": vote.decision,
                "confidence": vote.confidence,
                "reasoning": vote.reasoning
            })
            print(f"  [{tongue.value}] {vote.decision} ({vote.confidence:.2f}): {vote.reasoning[:50]}...")

        # Judge aggregates
        judge_msg = SwarmMessage(
            id=f"consensus-{action_id}",
            from_agent=SacredTongue.DR,
            to_agent=None,
            action="request_approval",
            payload={"votes": votes}
        )

        result_msg = await self.agents[SacredTongue.DR].process(judge_msg)
        final_decision = result_msg.payload.get("decision", "DENY")

        consensus = {
            "action_id": action_id,
            "action": action,
            "votes": votes,
            "final_decision": final_decision,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        self.consensus_log.append(consensus)

        print(f"\n[ROUNDTABLE] Final decision: {final_decision}")
        print("-" * 40)

        return consensus

    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate with swarm consensus."""
        action_id = f"nav-{len(self.action_history)}"

        # Scout analyzes URL
        scout_msg = SwarmMessage(
            id=action_id,
            from_agent=SacredTongue.KO,
            to_agent=None,
            action="navigate",
            payload={"url": url}
        )

        scout_result = await self.agents[SacredTongue.KO].process(scout_msg)
        risk_score = scout_result.payload.get("risk_score", 0.5)

        # Get consensus
        consensus = await self.roundtable_consensus(
            action_id,
            "navigate",
            {"url": url, "risk_score": risk_score}
        )

        result = {
            "action": "navigate",
            "url": url,
            "decision": consensus["final_decision"],
            "risk_score": risk_score,
            "executed": False
        }

        if consensus["final_decision"] == "ALLOW":
            # Execute navigation via browser backend
            if self.browser:
                await self.browser.navigate(url)
            result["executed"] = True

        self.action_history.append(result)
        return result

    async def click(self, target: str) -> Dict[str, Any]:
        """Click with swarm consensus."""
        action_id = f"click-{len(self.action_history)}"

        # Vision finds element
        vision_msg = SwarmMessage(
            id=action_id,
            from_agent=SacredTongue.AV,
            to_agent=None,
            action="find_element",
            payload={"target": target}
        )

        vision_result = await self.agents[SacredTongue.AV].process(vision_msg)
        coordinates = vision_result.payload.get("coordinates", [0, 0])

        # Get consensus
        consensus = await self.roundtable_consensus(
            action_id,
            "click",
            {"target": target, "coordinates": coordinates}
        )

        result = {
            "action": "click",
            "target": target,
            "coordinates": coordinates,
            "decision": consensus["final_decision"],
            "executed": False
        }

        if consensus["final_decision"] == "ALLOW":
            # Execute click via Clicker agent
            click_msg = SwarmMessage(
                id=action_id,
                from_agent=SacredTongue.CA,
                to_agent=None,
                action="click",
                payload={"coordinates": coordinates, "target": target}
            )
            await self.agents[SacredTongue.CA].process(click_msg)
            result["executed"] = True

        self.action_history.append(result)
        return result

    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """Type with swarm consensus."""
        action_id = f"type-{len(self.action_history)}"

        # Reader analyzes the form field
        reader_msg = SwarmMessage(
            id=action_id,
            from_agent=SacredTongue.RU,
            to_agent=None,
            action="analyze_form",
            payload={"selector": selector}
        )

        await self.agents[SacredTongue.RU].process(reader_msg)

        # Get consensus (never include actual text in context)
        consensus = await self.roundtable_consensus(
            action_id,
            "type",
            {"selector": selector, "text_length": len(text), "field_type": "text"}
        )

        result = {
            "action": "type",
            "selector": selector,
            "text_length": len(text),
            "decision": consensus["final_decision"],
            "executed": False
        }

        if consensus["final_decision"] == "ALLOW":
            # Execute typing via Typer agent
            type_msg = SwarmMessage(
                id=action_id,
                from_agent=SacredTongue.UM,
                to_agent=None,
                action="type",
                payload={"text": text}
            )
            await self.agents[SacredTongue.UM].process(type_msg)
            result["executed"] = True

        self.action_history.append(result)
        return result

    def get_summary(self) -> Dict[str, Any]:
        """Get swarm activity summary."""
        decisions = {}
        for action in self.action_history:
            d = action.get("decision", "UNKNOWN")
            decisions[d] = decisions.get(d, 0) + 1

        return {
            "total_actions": len(self.action_history),
            "decisions": decisions,
            "consensus_rounds": len(self.consensus_log),
            "agents_active": sum(1 for a in self.agents.values() if a.active)
        }

    def print_summary(self):
        """Print activity summary."""
        s = self.get_summary()
        print("\n" + "=" * 60)
        print("  SWARM BROWSER SESSION SUMMARY")
        print("=" * 60)
        print(f"  Total Actions: {s['total_actions']}")
        print(f"  Consensus Rounds: {s['consensus_rounds']}")
        print(f"  Active Agents: {s['agents_active']}/6")
        print("\n  Decisions:")
        for decision, count in s['decisions'].items():
            print(f"    {decision}: {count}")
        print("=" * 60 + "\n")


# =============================================================================
# Example Usage
# =============================================================================

async def demo():
    """Demonstrate the Swarm Browser."""
    print("\n" + "=" * 60)
    print("  SCBE SWARM BROWSER DEMO")
    print("  'The Hexagonal Megazord'")
    print("=" * 60)

    # Create swarm (no real browser backend for demo)
    swarm = SwarmBrowser()
    await swarm.initialize()

    # Test navigation
    print("\n--- Test 1: Safe Navigation ---")
    result = await swarm.navigate("https://github.com/issdandavis/SCBE-AETHERMOORE")
    print(f"Result: {result['decision']} (executed: {result['executed']})")

    # Test high-risk navigation
    print("\n--- Test 2: High-Risk Navigation ---")
    result = await swarm.navigate("https://mybank.com/admin/transfer-funds")
    print(f"Result: {result['decision']} (executed: {result['executed']})")

    # Test click
    print("\n--- Test 3: Click Action ---")
    result = await swarm.click("button.submit")
    print(f"Result: {result['decision']} (executed: {result['executed']})")

    # Test typing
    print("\n--- Test 4: Type Action ---")
    result = await swarm.type_text("#username", "testuser")
    print(f"Result: {result['decision']} (executed: {result['executed']})")

    # Summary
    swarm.print_summary()


if __name__ == "__main__":
    asyncio.run(demo())
