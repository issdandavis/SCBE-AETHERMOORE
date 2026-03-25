"""
Governance Engine for Cognitive Governance
==========================================

The main decision engine that uses the 54-dimensional double hypercube
geometry to make governance decisions.

Decision tiers:
- ALLOW: Safe operation, proceed freely
- CONSTRAIN: Operation permitted with restrictions
- REDIRECT: Operation redirected to a safer path
- DENY: Operation blocked (adversarial or too risky)

The engine evaluates:
1. Position in cognitive space (distance from center)
2. Hypercube face permeability (which dimensions are blocked)
3. Phase coupling (alignment with safe operation)
4. Historical trust (agent's track record)
5. Exponential cost (H = R^((d*gamma)^2))

@module cognitive_governance/governance_engine
@layer L13 (Risk decision)
"""

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .dimensional_space import (
    PHI,
    TONGUE_NAMES,
    CognitivePoint,
    DimensionalSpace,
    StateValence,
)
from .hypercube_geometry import DoubleHypercube, PhaseProjection
from .permeability import (
    DimensionalWall,
    PermeabilityMatrix,
    WallVisibility,
    create_security_walls,
)


class GovernanceDecision(Enum):
    """Governance decision tiers."""
    ALLOW = "ALLOW"
    CONSTRAIN = "CONSTRAIN"
    REDIRECT = "REDIRECT"
    DENY = "DENY"


@dataclass
class DecisionContext:
    """Full context for a governance decision."""
    decision: GovernanceDecision
    score: float  # 0.0 (deny) to 1.0 (allow)
    cost: float   # Total governance cost
    distance: float  # Hyperbolic distance from center
    classification: str  # interior / governance / exterior
    passable_tongues: List[str]  # Which tongues can proceed
    blocked_tongues: List[str]   # Which tongues are blocked
    dominant_tongue: str  # Agent's dominant tongue
    dominant_valence: str  # Agent's dominant valence
    phase_alignment: float  # Phase alignment with safe operation
    explanation: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class GovernanceEngine:
    """
    Main governance engine using double hypercube geometry.

    Evaluates agent actions through the 54-dimensional cognitive space
    and makes ALLOW/CONSTRAIN/REDIRECT/DENY decisions based on:
    - Hyperbolic distance from safe center
    - Exponential cost scaling
    - Dimensional permeability
    - Phase coupling
    - Trust history
    """
    space: DimensionalSpace = field(default_factory=DimensionalSpace)
    hypercube: DoubleHypercube = field(default_factory=DoubleHypercube)
    permeability: PermeabilityMatrix = field(default_factory=create_security_walls)
    # Trust scores per agent
    trust_scores: Dict[str, float] = field(default_factory=dict)
    # Decision history
    history: List[DecisionContext] = field(default_factory=list)
    # Decision thresholds
    allow_threshold: float = 0.7
    constrain_threshold: float = 0.4
    redirect_threshold: float = 0.2
    # Maximum history to keep
    max_history: int = 1000

    def get_trust(self, agent_id: str) -> float:
        """Get trust score for an agent (default 0.5)."""
        return self.trust_scores.get(agent_id, 0.5)

    def set_trust(self, agent_id: str, trust: float):
        """Set trust score for an agent."""
        self.trust_scores[agent_id] = max(0.0, min(1.0, trust))

    def update_trust(self, agent_id: str, delta: float):
        """Update trust score by delta."""
        current = self.get_trust(agent_id)
        self.set_trust(agent_id, current + delta)

    def evaluate(
        self,
        agent_id: str,
        action: str,
        target: str,
        sensitivity: float = 0.5,
        context: Optional[Dict[str, Any]] = None,
    ) -> DecisionContext:
        """
        Evaluate an agent action through the full governance pipeline.

        This is the main entry point for governance decisions.

        @axiom A1-A5: Full pipeline (Layers 1-14)
        """
        trust = self.get_trust(agent_id)

        # L1-L4: Embed action into cognitive space
        point = self.space.embed_action(
            agent_id=agent_id,
            action=action,
            target=target,
            trust=trust,
            sensitivity=sensitivity,
        )

        # L5: Hyperbolic distance from center
        distance = self.space.distance_from_center(point)

        # L6-L7: Phase alignment with safe operation
        safe_center = CognitivePoint()
        phase_alignment = self.space.phase_coupling(point, safe_center)

        # L8: Classify position in double hypercube
        classification = self.hypercube.classify_point(point)

        # L9-L10: Check dimensional permeability
        passable = self.permeability.passable_tongues()
        blocked = self.permeability.blocked_tongues()

        # L12: Compute governance cost
        cost = self.hypercube.governance_cost(point)

        # L12: Safety score
        safety = self.space.safety_score(point)

        # L13: Compute final score
        score = self._compute_score(
            safety=safety,
            trust=trust,
            distance=distance,
            phase_alignment=phase_alignment,
            classification=classification,
            cost=cost,
            sensitivity=sensitivity,
        )

        # L13: Make decision
        decision = self._decide(score, classification, blocked, action)

        # Build context
        ctx = DecisionContext(
            decision=decision,
            score=score,
            cost=cost,
            distance=distance,
            classification=classification,
            passable_tongues=passable,
            blocked_tongues=blocked,
            dominant_tongue=point.dominant_tongue(),
            dominant_valence=point.dominant_valence().name,
            phase_alignment=phase_alignment,
            explanation={
                "agent_id": agent_id,
                "action": action,
                "target": target,
                "trust": trust,
                "sensitivity": sensitivity,
                "safety_score": round(safety, 4),
                "hyperbolic_distance": round(distance, 4),
                "governance_cost": round(cost, 4) if cost != float("inf") else "infinity",
                "phase_alignment": round(phase_alignment, 4),
                "classification": classification,
                "context": context or {},
            },
        )

        # Update trust based on decision
        self._update_trust_from_decision(agent_id, decision)

        # Record history
        self.history.append(ctx)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        return ctx

    def _compute_score(
        self,
        safety: float,
        trust: float,
        distance: float,
        phase_alignment: float,
        classification: str,
        cost: float,
        sensitivity: float,
    ) -> float:
        """
        Compute final governance score from multiple factors.

        Score ranges from 0.0 (deny) to 1.0 (allow).
        """
        # Base score from safety
        score = safety * 0.4

        # Trust contribution
        score += trust * 0.3

        # Phase alignment contribution (normalized to [0, 1])
        score += (phase_alignment + 1.0) / 2.0 * 0.15

        # Distance penalty (exponential)
        if distance < 5:
            distance_penalty = 1.0 / (1.0 + distance)
        else:
            distance_penalty = 0.0
        score += distance_penalty * 0.15

        # Classification penalty
        if classification == "exterior":
            score *= 0.1
        elif classification == "governance":
            score *= 0.7

        # Sensitivity scaling
        score *= (1.0 - sensitivity * 0.3)

        return max(0.0, min(1.0, score))

    def _decide(
        self,
        score: float,
        classification: str,
        blocked_tongues: List[str],
        action: str,
    ) -> GovernanceDecision:
        """
        Make the governance decision based on score and constraints.
        """
        # Exterior classification = always deny
        if classification == "exterior":
            return GovernanceDecision.DENY

        # If the action's relevant tongues are all blocked = deny
        action_tongue_map = {
            "READ": ["KO", "AV"],
            "WRITE": ["KO", "AV", "RU"],
            "EXECUTE": ["KO", "CA"],
            "DELETE": ["KO", "RU", "UM"],
            "ADMIN": ["KO", "UM", "DR"],
            "DEPLOY": ["KO", "RU", "DR"],
        }
        relevant_tongues = action_tongue_map.get(action.upper(), ["KO"])
        if all(t in blocked_tongues for t in relevant_tongues):
            return GovernanceDecision.DENY

        # Score-based decision
        if score >= self.allow_threshold:
            return GovernanceDecision.ALLOW
        elif score >= self.constrain_threshold:
            return GovernanceDecision.CONSTRAIN
        elif score >= self.redirect_threshold:
            return GovernanceDecision.REDIRECT
        else:
            return GovernanceDecision.DENY

    def _update_trust_from_decision(self, agent_id: str, decision: GovernanceDecision):
        """
        Update trust based on governance decision.

        ALLOW: slight trust increase
        CONSTRAIN: no change
        REDIRECT: slight trust decrease
        DENY: larger trust decrease
        """
        trust_deltas = {
            GovernanceDecision.ALLOW: 0.01,
            GovernanceDecision.CONSTRAIN: 0.0,
            GovernanceDecision.REDIRECT: -0.02,
            GovernanceDecision.DENY: -0.05,
        }
        delta = trust_deltas.get(decision, 0.0)
        if delta != 0.0:
            self.update_trust(agent_id, delta)

    def batch_evaluate(
        self,
        requests: List[Dict[str, Any]],
    ) -> List[DecisionContext]:
        """
        Evaluate a batch of agent requests.

        Each request should have: agent_id, action, target, sensitivity.
        """
        results = []
        for req in requests:
            ctx = self.evaluate(
                agent_id=req["agent_id"],
                action=req["action"],
                target=req["target"],
                sensitivity=req.get("sensitivity", 0.5),
                context=req.get("context"),
            )
            results.append(ctx)
        return results

    def get_agent_summary(self, agent_id: str) -> Dict[str, Any]:
        """Get a summary of an agent's governance history."""
        agent_history = [h for h in self.history if h.explanation.get("agent_id") == agent_id]
        if not agent_history:
            return {"agent_id": agent_id, "decisions": 0, "trust": self.get_trust(agent_id)}

        decisions = {}
        for h in agent_history:
            d = h.decision.value
            decisions[d] = decisions.get(d, 0) + 1

        return {
            "agent_id": agent_id,
            "trust": self.get_trust(agent_id),
            "total_decisions": len(agent_history),
            "decisions": decisions,
            "avg_score": sum(h.score for h in agent_history) / len(agent_history),
            "avg_distance": sum(h.distance for h in agent_history) / len(agent_history),
            "dominant_tongue": agent_history[-1].dominant_tongue,
        }
