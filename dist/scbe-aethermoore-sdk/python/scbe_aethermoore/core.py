"""
SCBE-AETHERMOORE Core Module

Contains:
- Agent6D: 6-dimensional agent with trust management
- SecurityGate: Adaptive dwell-time security gate
- SCBE: Main API class for risk evaluation
- Roundtable: Multi-signature consensus
- Hyperbolic geometry functions
"""

import asyncio
import hashlib
import json
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple

import numpy as np

# ============================================================================
# Constants
# ============================================================================

SAFE_CENTER = np.zeros(6)
RISK_THRESHOLDS = {"ALLOW": 0.3, "REVIEW": 0.7}
MAX_COMPLEXITY = 1e10

# Tongue types
TongueID = Literal["ko", "av", "ru", "ca", "um", "dr"]
ActionType = Literal["read", "query", "write", "update", "delete", "grant", "deploy", "rotate_keys"]
DecisionType = Literal["ALLOW", "REVIEW", "DENY"]

# ============================================================================
# Hyperbolic Geometry
# ============================================================================


def project_to_ball(point: np.ndarray, max_norm: float = 0.99) -> np.ndarray:
    """Project a point into the Poincaré ball (ensure ||x|| < 1)."""
    point = np.asarray(point, dtype=float)
    norm = np.linalg.norm(point)
    if norm >= max_norm:
        return point * (max_norm / norm)
    return point


def hyperbolic_distance(u: np.ndarray, v: np.ndarray, eps: float = 1e-10) -> float:
    """
    Compute the hyperbolic distance between two points in the Poincaré ball.

    Formula: d(u,v) = 2 * arctanh(||(-u) ⊕ v||)
    where ⊕ is the Möbius addition.
    """
    u = np.asarray(u, dtype=float)
    v = np.asarray(v, dtype=float)

    # Möbius addition: (-u) ⊕ v
    neg_u = -u
    u_norm_sq = np.dot(neg_u, neg_u)
    v_norm_sq = np.dot(v, v)
    uv_dot = np.dot(neg_u, v)

    # Numerator: (1 + 2<-u,v> + ||v||²)(-u) + (1 - ||u||²)v
    num = (1 + 2 * uv_dot + v_norm_sq) * neg_u + (1 - u_norm_sq) * v

    # Denominator: 1 + 2<-u,v> + ||u||²||v||²
    denom = 1 + 2 * uv_dot + u_norm_sq * v_norm_sq
    denom = max(denom, eps)

    result = num / denom
    result_norm = min(np.linalg.norm(result), 1 - eps)

    return 2 * np.arctanh(result_norm)


def harmonic_complexity(depth: int, ratio: float = 1.5) -> float:
    """
    Calculate harmonic complexity for a task depth.

    Uses the "perfect fifth" ratio (1.5) from music theory.
    """
    result = math.pow(ratio, depth * depth)
    return min(result, MAX_COMPLEXITY)


def get_pricing_tier(depth: int) -> Dict[str, Any]:
    """Get pricing tier based on task complexity."""
    complexity = harmonic_complexity(depth)

    if complexity < 2:
        return {"tier": "FREE", "complexity": complexity, "description": "Simple single-step tasks"}
    elif complexity < 10:
        return {"tier": "STARTER", "complexity": complexity, "description": "Basic workflows"}
    elif complexity < 100:
        return {"tier": "PRO", "complexity": complexity, "description": "Advanced multi-step"}
    else:
        return {"tier": "ENTERPRISE", "complexity": complexity, "description": "Complex orchestration"}


# ============================================================================
# Agent6D
# ============================================================================


@dataclass
class Agent6D:
    """
    An AI agent with a position in 6D space and trust tracking.

    Agents exist in a 6-dimensional space where:
    - Close agents = simple security (they trust each other)
    - Far agents = complex security (strangers need more checks)
    """

    name: str
    position: np.ndarray
    trust_score: float = 1.0
    last_seen: float = field(default_factory=time.time)

    def __post_init__(self):
        """Validate position is 6D."""
        self.position = np.asarray(self.position, dtype=float)
        if len(self.position) != 6:
            raise ValueError(f"Position must have exactly 6 dimensions, got {len(self.position)}")
        if not np.all(np.isfinite(self.position)):
            raise ValueError("Position elements must be finite numbers")
        self.trust_score = max(0.0, min(1.0, self.trust_score))

    def distance_to(self, other: "Agent6D") -> float:
        """Calculate Euclidean distance to another agent."""
        diff = self.position - other.position
        return float(np.linalg.norm(diff))

    def check_in(self) -> None:
        """Agent checks in - refreshes trust and timestamp."""
        self.last_seen = time.time()
        self.trust_score = min(1.0, self.trust_score + 0.1)

    def decay_trust(self, decay_rate: float = 0.01) -> float:
        """Apply trust decay based on time since last check-in."""
        elapsed = time.time() - self.last_seen
        self.trust_score *= math.exp(-decay_rate * elapsed)
        return self.trust_score


# ============================================================================
# SecurityGate
# ============================================================================


@dataclass
class SecurityGateConfig:
    """Configuration for SecurityGate."""

    min_wait_ms: int = 100
    max_wait_ms: int = 5000
    alpha: float = 1.5


DANGEROUS_ACTIONS = ["delete", "deploy", "rotate_keys", "grant_access"]


class SecurityGate:
    """
    Security gate with adaptive dwell time based on risk.

    Like a nightclub bouncer that:
    - Checks your ID (authentication)
    - Looks at your reputation (trust score)
    - Makes you wait longer if you're risky (adaptive dwell time)
    """

    def __init__(self, config: Optional[SecurityGateConfig] = None):
        config = config or SecurityGateConfig()
        self.min_wait_ms = config.min_wait_ms
        self.max_wait_ms = config.max_wait_ms
        self.alpha = config.alpha

    def assess_risk(self, agent: Agent6D, action: str, context: Dict[str, Any]) -> float:
        """Calculate risk score for an agent performing an action."""
        risk = 0.0

        # Low trust = high risk
        risk += (1.0 - agent.trust_score) * 2.0

        # Dangerous actions = high risk
        if action in DANGEROUS_ACTIONS:
            risk += 3.0

        # External context = higher risk
        if context.get("source") == "external":
            risk += 1.5

        return risk

    async def check(
        self, agent: Agent6D, action: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform security gate check with adaptive dwell time.

        Higher risk = longer wait time (slows attackers).
        """
        risk = self.assess_risk(agent, action, context)

        # Adaptive dwell time
        dwell_ms = min(self.max_wait_ms, self.min_wait_ms * (self.alpha ** risk))

        # Wait (non-blocking)
        await asyncio.sleep(dwell_ms / 1000)

        # Calculate composite score
        trust_component = agent.trust_score * 0.4
        action_component = (0.3 if action in DANGEROUS_ACTIONS else 1.0) * 0.3
        context_component = (0.8 if context.get("source") == "internal" else 0.4) * 0.3

        score = trust_component + action_component + context_component

        if score > 0.8:
            return {"status": "allow", "score": score, "dwell_ms": dwell_ms}
        elif score > 0.5:
            return {"status": "review", "score": score, "dwell_ms": dwell_ms, "reason": "Manual approval required"}
        else:
            return {"status": "deny", "score": score, "dwell_ms": dwell_ms, "reason": "Security threshold not met"}


# ============================================================================
# Roundtable
# ============================================================================


class Roundtable:
    """
    Roundtable multi-signature consensus system.

    Different actions require different numbers of "departments" to agree.
    """

    TIERS = {
        "low": ["ko"],
        "medium": ["ko", "ru"],
        "high": ["ko", "ru", "um"],
        "critical": ["ko", "ru", "um", "dr"],
    }

    @classmethod
    def required_tongues(cls, action: ActionType) -> List[TongueID]:
        """Get required tongues for an action."""
        if action in ["read", "query"]:
            return cls.TIERS["low"]
        elif action in ["write", "update"]:
            return cls.TIERS["medium"]
        elif action in ["delete", "grant"]:
            return cls.TIERS["high"]
        else:  # deploy, rotate_keys
            return cls.TIERS["critical"]

    @classmethod
    def has_quorum(cls, signatures: List[TongueID], required: List[TongueID]) -> bool:
        """Check if we have all required signatures."""
        return all(t in signatures for t in required)


# ============================================================================
# SCBE Main API
# ============================================================================


@dataclass
class RiskResult:
    """Risk evaluation result."""

    score: float
    distance: float
    scaled_cost: float
    decision: DecisionType
    reason: str


class SCBE:
    """
    Main SCBE API class.

    Provides risk evaluation, signing, and verification.
    """

    def __init__(self):
        self.safe_center = SAFE_CENTER

    def evaluate_risk(self, context: Dict[str, Any]) -> RiskResult:
        """
        Evaluate the risk of a context/action.

        Returns a risk score and decision.
        """
        # Convert context to 6D point
        point = self._context_to_point(context)

        # Project to Poincaré ball
        projected = project_to_ball(point)

        # Compute hyperbolic distance from safe center
        distance = hyperbolic_distance(projected, self.safe_center)

        # Apply harmonic scaling
        d = max(1, math.ceil(distance))
        scaled_cost = harmonic_complexity(d)

        # Normalize to 0-1 risk score
        score = min(1.0, distance / 5.0)

        # Make decision
        if score < RISK_THRESHOLDS["ALLOW"]:
            decision = "ALLOW"
            reason = "Context within safe zone"
        elif score < RISK_THRESHOLDS["REVIEW"]:
            decision = "REVIEW"
            reason = "Context requires review - moderate deviation"
        else:
            decision = "DENY"
            reason = "Context exceeds safe threshold - high risk"

        return RiskResult(
            score=score,
            distance=distance,
            scaled_cost=scaled_cost,
            decision=decision,
            reason=reason,
        )

    def _context_to_point(self, context: Dict[str, Any]) -> np.ndarray:
        """Convert arbitrary context to 6D point using hash-based mapping."""
        json_str = json.dumps(context, sort_keys=True)
        hash_bytes = hashlib.sha256(json_str.encode()).digest()

        # Map hash to 6 dimensions
        point = np.zeros(6)
        for i in range(6):
            # Use 4 bytes per dimension
            val = int.from_bytes(hash_bytes[i * 4 : (i + 1) * 4], "big")
            # Scale to [-2, 2]
            point[i] = (val / (2**32 - 1) - 0.5) * 4

        return point
