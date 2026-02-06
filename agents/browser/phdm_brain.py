"""
@file phdm_brain.py
@module agents/browser/phdm_brain
@layer Layer 5, Layer 12, Layer 13
@component SimplePHDM Brain for Browser Agent
@version 1.0.0

Geometrically-contained decision making using Poincare ball model.
Actions are only permitted if their embeddings fall within the safe radius.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple
import numpy as np

# Numerical stability constant
EPSILON = 1e-10

# Golden ratio for harmonic scaling
PHI = (1 + math.sqrt(5)) / 2


class SafetyDecision(Enum):
    """4-tier governance decision outcomes."""
    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    ESCALATE = "ESCALATE"
    DENY = "DENY"


@dataclass
class ContainmentResult:
    """Result of a containment check."""
    decision: SafetyDecision
    radius: float
    hyperbolic_distance: float
    risk_score: float
    message: str
    embedding: Optional[np.ndarray] = None


@dataclass
class SimplePHDM:
    """
    Simple Poincare Hyperbolic Distance Model for browser agent containment.

    Uses the Poincare ball model where:
    - The origin represents maximum safety (trusted behavior)
    - The boundary (radius=1) represents maximum risk
    - Actions with embeddings beyond safe_radius are blocked

    Mathematical basis:
    - Hyperbolic distance: d_H(u,v) = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))
    - Risk amplification: H(d,R) = R^(d^2) (super-exponential penalty)

    Attributes:
        safe_radius: Maximum Euclidean norm for safe actions (default 0.92)
        dim: Embedding dimension (default 16)
        harmonic_base: Base for risk amplification (default 1.5)
        origin: The safe reference point (origin of Poincare ball)
    """
    safe_radius: float = 0.92
    dim: int = 16
    harmonic_base: float = 1.5
    origin: np.ndarray = field(default_factory=lambda: None)

    # Decision thresholds
    allow_threshold: float = 0.33
    quarantine_threshold: float = 0.67

    # History for temporal analysis
    _history: List[Tuple[float, np.ndarray]] = field(default_factory=list)
    _max_history: int = 100

    def __post_init__(self):
        """Initialize the origin point."""
        if self.origin is None:
            self.origin = np.zeros(self.dim, dtype=np.float64)

    def project_to_ball(self, v: np.ndarray, max_norm: Optional[float] = None) -> np.ndarray:
        """
        Project a vector onto the Poincare ball.

        Ensures the vector stays within the open ball (norm < 1).

        Args:
            v: Input vector
            max_norm: Maximum allowed norm (default: 1 - EPSILON)

        Returns:
            Projected vector within the ball
        """
        if max_norm is None:
            max_norm = 1.0 - EPSILON

        norm = np.linalg.norm(v)
        if norm > max_norm:
            return v * (max_norm / norm)
        return v

    def hyperbolic_distance(self, u: np.ndarray, v: np.ndarray) -> float:
        """
        Compute hyperbolic distance in the Poincare ball model.

        Formula: d_H(u,v) = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))

        This is the invariant metric (Layer 5) that never changes across transformations.

        Args:
            u: First point in Poincare ball
            v: Second point in Poincare ball

        Returns:
            Hyperbolic distance between u and v
        """
        # Ensure points are in the ball
        u = self.project_to_ball(u)
        v = self.project_to_ball(v)

        diff = u - v
        diff_norm_sq = np.dot(diff, diff)

        u_norm_sq = np.dot(u, u)
        v_norm_sq = np.dot(v, v)

        # Clamp for numerical stability
        u_factor = max(EPSILON, 1 - u_norm_sq)
        v_factor = max(EPSILON, 1 - v_norm_sq)

        arg = 1 + (2 * diff_norm_sq) / (u_factor * v_factor)

        # Clamp argument to valid range for arcosh
        return math.acosh(max(1.0, arg))

    def distance_to_origin(self, v: np.ndarray) -> float:
        """
        Compute hyperbolic distance from a point to the origin.

        Simplified formula when one point is origin:
        d_H(0,v) = arcosh(1 + 2||v||^2 / (1-||v||^2))
                 = 2 * arctanh(||v||)

        Args:
            v: Point in Poincare ball

        Returns:
            Hyperbolic distance to origin
        """
        v = self.project_to_ball(v)
        norm = np.linalg.norm(v)

        if norm < EPSILON:
            return 0.0

        # Use the simplified formula: 2 * arctanh(||v||)
        # arctanh(x) = 0.5 * ln((1+x)/(1-x))
        clamped_norm = min(norm, 1.0 - EPSILON)
        return 2 * math.atanh(clamped_norm)

    def euclidean_radius(self, v: np.ndarray) -> float:
        """
        Compute the Euclidean norm (radius) of a point.

        Args:
            v: Point vector

        Returns:
            Euclidean norm
        """
        return float(np.linalg.norm(v))

    def harmonic_scaling(self, distance: float) -> float:
        """
        Apply harmonic wall risk amplification (Layer 12).

        Formula: H(d,R) = R^(d^2)

        This creates super-exponential penalty for geometric distance,
        making adversarial drift exponentially more costly.

        Args:
            distance: Hyperbolic distance from safe region

        Returns:
            Amplified risk factor
        """
        return math.pow(self.harmonic_base, distance * distance)

    def compute_risk_score(self, embedding: np.ndarray) -> float:
        """
        Compute the total risk score for an embedding.

        Combines:
        - Euclidean radius (proximity to boundary)
        - Hyperbolic distance (geometric deviation)
        - Harmonic scaling (risk amplification)

        Args:
            embedding: Action embedding vector

        Returns:
            Risk score in [0, 1] (clamped)
        """
        embedding = self.project_to_ball(embedding)

        # Euclidean radius normalized by safe_radius
        radius = self.euclidean_radius(embedding)
        radius_risk = radius / self.safe_radius

        # Hyperbolic distance to origin
        h_dist = self.distance_to_origin(embedding)

        # Harmonic amplification
        amplification = self.harmonic_scaling(h_dist)

        # Combined risk (weighted average with amplification)
        # Base risk from radius, amplified by harmonic scaling
        base_risk = min(1.0, radius_risk)
        amplified_risk = base_risk * min(amplification, 10.0) / 10.0

        # Blend base and amplified risk
        risk = 0.4 * base_risk + 0.6 * amplified_risk

        return min(1.0, max(0.0, risk))

    def is_safe(self, embedding: np.ndarray) -> bool:
        """
        Check if an embedding is within the safe containment region.

        This is the core safety gate: actions are only permitted if
        their embeddings have Euclidean radius < safe_radius.

        Args:
            embedding: Action embedding vector

        Returns:
            True if action is safe (radius < safe_radius)
        """
        embedding = self.project_to_ball(embedding)
        radius = self.euclidean_radius(embedding)
        return radius < self.safe_radius

    def check_containment(self, embedding: np.ndarray) -> ContainmentResult:
        """
        Perform full containment check with governance decision.

        Implements 4-tier governance (Layer 13):
        - ALLOW: Risk < allow_threshold (safe to execute)
        - QUARANTINE: allow_threshold <= Risk < quarantine_threshold
        - ESCALATE: Risk near boundary, requires human review
        - DENY: Risk >= quarantine_threshold or radius >= safe_radius

        Args:
            embedding: Action embedding vector

        Returns:
            ContainmentResult with decision and metrics
        """
        embedding = self.project_to_ball(embedding)
        radius = self.euclidean_radius(embedding)
        h_dist = self.distance_to_origin(embedding)
        risk = self.compute_risk_score(embedding)

        # Record in history for temporal analysis
        import time
        self._history.append((time.time(), embedding.copy()))
        if len(self._history) > self._max_history:
            self._history.pop(0)

        # Determine decision
        if radius >= self.safe_radius:
            decision = SafetyDecision.DENY
            message = f"BLOCKED: Radius {radius:.4f} >= safe_radius {self.safe_radius}"
        elif risk >= self.quarantine_threshold:
            decision = SafetyDecision.DENY
            message = f"DENIED: Risk score {risk:.4f} exceeds threshold"
        elif risk >= self.allow_threshold:
            # Check if we're in escalation zone (close to boundary)
            if radius >= self.safe_radius * 0.95:
                decision = SafetyDecision.ESCALATE
                message = f"ESCALATE: Near boundary (radius={radius:.4f}), requires review"
            else:
                decision = SafetyDecision.QUARANTINE
                message = f"QUARANTINE: Elevated risk {risk:.4f}, action logged"
        else:
            decision = SafetyDecision.ALLOW
            message = f"ALLOWED: Safe operation (risk={risk:.4f}, radius={radius:.4f})"

        return ContainmentResult(
            decision=decision,
            radius=radius,
            hyperbolic_distance=h_dist,
            risk_score=risk,
            message=message,
            embedding=embedding
        )

    def mobius_addition(self, u: np.ndarray, v: np.ndarray) -> np.ndarray:
        """
        Mobius addition in the Poincare ball (gyrovector operation).

        Formula: u (+) v = ((1 + 2<u,v> + ||v||^2)u + (1 - ||u||^2)v) /
                           (1 + 2<u,v> + ||u||^2||v||^2)

        This is a true hyperbolic isometry used for composing transformations.

        Args:
            u: First point
            v: Second point

        Returns:
            Mobius sum u (+) v
        """
        u = self.project_to_ball(u)
        v = self.project_to_ball(v)

        u_norm_sq = np.dot(u, u)
        v_norm_sq = np.dot(v, v)
        uv_dot = np.dot(u, v)

        numerator = (1 + 2 * uv_dot + v_norm_sq) * u + (1 - u_norm_sq) * v
        denominator = 1 + 2 * uv_dot + u_norm_sq * v_norm_sq

        result = numerator / max(denominator, EPSILON)
        return self.project_to_ball(result)

    def exponential_map(self, p: np.ndarray, v: np.ndarray) -> np.ndarray:
        """
        Exponential map from tangent space to Poincare ball.

        Maps a tangent vector v at point p to a point on the ball.

        Args:
            p: Base point on the ball
            v: Tangent vector

        Returns:
            Point on the Poincare ball
        """
        p = self.project_to_ball(p)

        p_norm_sq = np.dot(p, p)
        lambda_p = 2.0 / max(EPSILON, 1 - p_norm_sq)

        v_norm = np.linalg.norm(v)
        if v_norm < EPSILON:
            return p

        v_normalized = v / v_norm
        scaled_norm = math.tanh(lambda_p * v_norm / 2)

        return self.mobius_addition(p, scaled_norm * v_normalized)

    def get_containment_stats(self) -> dict:
        """
        Get statistics about recent containment checks.

        Returns:
            Dictionary with containment statistics
        """
        if not self._history:
            return {
                "total_checks": 0,
                "avg_radius": 0.0,
                "max_radius": 0.0,
                "min_radius": 0.0,
                "boundary_violations": 0
            }

        radii = [self.euclidean_radius(emb) for _, emb in self._history]

        return {
            "total_checks": len(self._history),
            "avg_radius": sum(radii) / len(radii),
            "max_radius": max(radii),
            "min_radius": min(radii),
            "boundary_violations": sum(1 for r in radii if r >= self.safe_radius)
        }

    def reset_history(self):
        """Clear the containment history."""
        self._history.clear()


def create_phdm_brain(
    safe_radius: float = 0.92,
    dim: int = 16,
    harmonic_base: float = 1.5
) -> SimplePHDM:
    """
    Factory function to create a SimplePHDM brain.

    Args:
        safe_radius: Maximum safe Euclidean radius (default 0.92)
        dim: Embedding dimension (default 16)
        harmonic_base: Base for harmonic scaling (default 1.5)

    Returns:
        Configured SimplePHDM instance
    """
    return SimplePHDM(
        safe_radius=safe_radius,
        dim=dim,
        harmonic_base=harmonic_base
    )
