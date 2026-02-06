"""
@file phdm_brain.py
@module agents/browser/phdm_brain
@layer Layer 5, Layer 12, Layer 13
@component PHDM Brain - Poincaré Hyperbolic Disk Model for Browser Agent Containment
@version 3.0.0

SimplePHDM - Geometric containment brain for browser agents.

Uses the Poincaré ball model to create hard geometric boundaries around
agent actions. Actions are embedded into hyperbolic space; any embedding
whose radius exceeds the safe threshold is rejected.

Key insight (from Claims Audit): Phase deviation + distance is the
validated discriminative mechanism — not "hyperbolic is magic" but
"domain phase + distance is discriminative."

Mathematical foundation:
    - exp_map: tangent space → Poincaré ball via tanh containment (proven, L5)
    - Harmonic wall: H(d, R) = R^(d²) cost amplification (proven, L12)
    - 4-tier decision: ALLOW/QUARANTINE/ESCALATE/DENY (L13)
"""

import math
import time
import hashlib
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum


# =============================================================================
# Constants
# =============================================================================

EPSILON = 1e-10
PHI = (1 + math.sqrt(5)) / 2  # Golden ratio ≈ 1.618


class Decision(str, Enum):
    """4-tier SCBE governance decisions (Layer 13)."""
    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    ESCALATE = "ESCALATE"
    DENY = "DENY"


# Sacred Tongue phases for domain separation (6 × 2π/6 offsets)
TONGUE_PHASES = {
    "KO": 0.0,                    # Scout: navigation
    "AV": math.pi / 3,            # Vision: visual analysis
    "RU": 2 * math.pi / 3,        # Reader: text extraction
    "CA": math.pi,                 # Clicker: interactions
    "UM": 4 * math.pi / 3,        # Typer: text input
    "DR": 5 * math.pi / 3,        # Judge: final decisions
}

# Action-to-tongue mapping
ACTION_TONGUE = {
    "navigate": "KO",
    "click": "CA",
    "type": "UM",
    "scroll": "KO",
    "screenshot": "AV",
    "get_content": "RU",
    "submit": "CA",
    "execute_script": "DR",
    "download": "DR",
}


# =============================================================================
# Data classes
# =============================================================================

@dataclass
class SafetyResult:
    """Result of a geometric safety check."""
    safe: bool
    reason: str
    radius: float
    angular_deviation: float
    decision: Decision
    cost: float
    embedding: Optional[List[float]] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class ActionEmbedding:
    """An action embedded in hyperbolic space."""
    action: str
    target: str
    vector: List[float]
    tongue: str
    phase: float
    timestamp: float = field(default_factory=time.time)


# =============================================================================
# SimplePHDM - Poincaré Hyperbolic Disk Model Brain
# =============================================================================

class SimplePHDM:
    """
    Poincaré Hyperbolic Disk Model brain for browser agent containment.

    Embeds browser actions into a 16-dimensional Poincaré ball and enforces
    geometric safety boundaries. Actions whose embeddings drift beyond the
    safe radius (0.92) are rejected — the harmonic wall makes adversarial
    deviation exponentially costly.

    Args:
        dim: Embedding dimensionality (default 16).
        curvature: Poincaré ball curvature parameter (default 1.0).
        safe_radius: Maximum allowed radius in the ball (default 0.92).
        max_angular_dev: Maximum angular deviation from expected phase (default 0.3).

    Example:
        brain = SimplePHDM()
        v = brain.encode_action("navigate", "https://example.com")
        emb = brain.exp_map(v)
        safe, reason = brain.is_safe(emb)
    """

    def __init__(
        self,
        dim: int = 16,
        curvature: float = 1.0,
        safe_radius: float = 0.92,
        max_angular_dev: float = 0.3,
    ):
        if dim < 2:
            raise ValueError("Dimension must be >= 2")
        if curvature <= 0:
            raise ValueError("Curvature must be positive")
        if not (0 < safe_radius < 1):
            raise ValueError("Safe radius must be in (0, 1)")
        if max_angular_dev <= 0:
            raise ValueError("Max angular deviation must be positive")

        self.dim = dim
        self.curvature = curvature
        self.safe_radius = safe_radius
        self.max_angular_dev = max_angular_dev

        # Origin point (zero vector in Poincaré ball = safest point)
        self._origin = [0.0] * dim

        # Action history for trajectory analysis
        self._history: List[ActionEmbedding] = []

        # Expected phase references per tongue (unit vectors with phase offset)
        self._tongue_refs = self._build_tongue_references()

    # =========================================================================
    # Vector operations
    # =========================================================================

    @staticmethod
    def _norm(v: List[float]) -> float:
        """Euclidean norm of a vector."""
        return math.sqrt(sum(x * x for x in v))

    @staticmethod
    def _norm_sq(v: List[float]) -> float:
        """Squared Euclidean norm."""
        return sum(x * x for x in v)

    @staticmethod
    def _dot(u: List[float], v: List[float]) -> float:
        """Dot product."""
        return sum(a * b for a, b in zip(u, v))

    @staticmethod
    def _scale(v: List[float], s: float) -> List[float]:
        """Scale vector by scalar."""
        return [x * s for x in v]

    @staticmethod
    def _add(u: List[float], v: List[float]) -> List[float]:
        """Vector addition."""
        return [a + b for a, b in zip(u, v)]

    @staticmethod
    def _sub(u: List[float], v: List[float]) -> List[float]:
        """Vector subtraction."""
        return [a - b for a, b in zip(u, v)]

    # =========================================================================
    # Poincaré ball operations (Layer 5)
    # =========================================================================

    def exp_map(self, v: List[float], c: Optional[float] = None) -> List[float]:
        """
        Exponential map from tangent space at origin to Poincaré ball.

        exp_0(v) = tanh(√c · ‖v‖ / 2) · v / (√c · ‖v‖)

        Maps tangent vectors to points inside the ball via tanh containment.
        This is mathematically guaranteed to produce points with ‖p‖ < 1
        (proven: standard hyperbolic geometry).

        Args:
            v: Tangent vector at the origin. Must have length == self.dim.
            c: Curvature override (default: self.curvature).

        Returns:
            Point in the Poincaré ball with ‖result‖ < 1.

        Raises:
            ValueError: If vector dimension doesn't match self.dim.
        """
        if len(v) != self.dim:
            raise ValueError(f"Expected {self.dim}-dim vector, got {len(v)}")

        c = c if c is not None else self.curvature
        sqrt_c = math.sqrt(c)

        v_norm = self._norm(v)
        if v_norm < EPSILON:
            return [0.0] * self.dim

        # tanh(√c · ‖v‖ / 2) · v / (√c · ‖v‖)
        coeff = math.tanh(sqrt_c * v_norm / 2.0) / (sqrt_c * v_norm)
        return self._scale(v, coeff)

    def log_map(self, p: List[float], c: Optional[float] = None) -> List[float]:
        """
        Logarithmic map from Poincaré ball to tangent space at origin.

        log_0(p) = (2 / √c) · arctanh(√c · ‖p‖) · p / ‖p‖

        Inverse of exp_map. Maps points back to tangent vectors.

        Args:
            p: Point in the Poincaré ball (‖p‖ < 1).
            c: Curvature override.

        Returns:
            Tangent vector at the origin.
        """
        if len(p) != self.dim:
            raise ValueError(f"Expected {self.dim}-dim vector, got {len(p)}")

        c = c if c is not None else self.curvature
        sqrt_c = math.sqrt(c)

        p_norm = self._norm(p)
        if p_norm < EPSILON:
            return [0.0] * self.dim

        # Clamp to avoid atanh(1) = inf
        clamped = min(sqrt_c * p_norm, 1.0 - EPSILON)
        atanh_val = 0.5 * math.log((1 + clamped) / (1 - clamped))
        coeff = (2.0 / sqrt_c) * atanh_val / p_norm
        return self._scale(p, coeff)

    def hyperbolic_distance(self, u: List[float], v: List[float]) -> float:
        """
        Poincaré ball distance (Layer 5 invariant metric).

        d_H(u, v) = (2/√c) · arctanh(√c · ‖-u ⊕ v‖)

        where ⊕ is Möbius addition. Equivalent formulation:
        d_H(u, v) = (1/√c) · arcosh(1 + 2c · ‖u-v‖² / ((1-c‖u‖²)(1-c‖v‖²)))

        Args:
            u: First point in Poincaré ball.
            v: Second point in Poincaré ball.

        Returns:
            Hyperbolic distance (non-negative).
        """
        diff = self._sub(u, v)
        diff_sq = self._norm_sq(diff)
        u_sq = self._norm_sq(u)
        v_sq = self._norm_sq(v)

        c = self.curvature

        u_factor = max(EPSILON, 1.0 - c * u_sq)
        v_factor = max(EPSILON, 1.0 - c * v_sq)

        arg = 1.0 + (2.0 * c * diff_sq) / (u_factor * v_factor)
        return (1.0 / math.sqrt(c)) * math.acosh(max(1.0, arg))

    def project_to_ball(self, p: List[float], max_norm: Optional[float] = None) -> List[float]:
        """
        Project point onto the Poincaré ball (clamp ‖p‖ < max_norm).

        Args:
            p: Point to project.
            max_norm: Maximum norm (default: 1 - epsilon).

        Returns:
            Point inside the ball.
        """
        if max_norm is None:
            max_norm = 1.0 - EPSILON
        n = self._norm(p)
        if n < max_norm:
            return list(p)
        return self._scale(p, max_norm / n)

    def mobius_add(self, u: List[float], v: List[float]) -> List[float]:
        """
        Möbius addition in the Poincaré ball.

        u ⊕ v = ((1 + 2c⟨u,v⟩ + c‖v‖²)u + (1 - c‖u‖²)v)
                / (1 + 2c⟨u,v⟩ + c²‖u‖²‖v‖²)

        Args:
            u: First point.
            v: Second point.

        Returns:
            Möbius sum u ⊕ v.
        """
        c = self.curvature
        uv = self._dot(u, v)
        u_sq = self._norm_sq(u)
        v_sq = self._norm_sq(v)

        num_u = 1.0 + 2.0 * c * uv + c * v_sq
        num_v = 1.0 - c * u_sq
        denom = 1.0 + 2.0 * c * uv + c * c * u_sq * v_sq

        result = []
        for i in range(len(u)):
            result.append((num_u * u[i] + num_v * v[i]) / denom)
        return result

    # =========================================================================
    # Harmonic wall (Layer 12)
    # =========================================================================

    def harmonic_cost(self, distance: float, R: float = PHI) -> float:
        """
        Harmonic wall cost function H(d, R) = R^(d²).

        Exponential cost for deviation from safe operation center.
        At the Poincaré boundary (d → ∞), cost → ∞.
        At the origin (d ≈ 0), cost ≈ 1.

        Uses golden ratio (φ ≈ 1.618) as default base per SCBE spec.

        Args:
            distance: Hyperbolic distance from origin.
            R: Base ratio (default: φ).

        Returns:
            Cost value (>= 1).
        """
        exponent = distance * distance * math.log(R)
        # Cap to prevent overflow
        if exponent > 700:
            return float("inf")
        return math.exp(exponent)

    # =========================================================================
    # Safety checking (Layer 13 decision gate)
    # =========================================================================

    def is_safe(self, embedding: List[float]) -> Tuple[bool, str]:
        """
        Check if an embedding is within the geometric safety boundary.

        Validates two conditions:
        1. Radius check: ‖embedding‖ < safe_radius (0.92)
        2. Angular deviation: deviation from expected tongue phase < max_angular_dev

        This is the primary containment mechanism. Per the Claims Audit,
        phase + distance is the validated discriminative signal.

        Args:
            embedding: Point in the Poincaré ball (from exp_map).

        Returns:
            Tuple of (is_safe: bool, reason: str).
            If safe, reason is "within_bounds".
            If unsafe, reason explains which check failed.
        """
        if len(embedding) != self.dim:
            return False, f"dimension_mismatch: expected {self.dim}, got {len(embedding)}"

        radius = self._norm(embedding)

        # Check 1: Radius boundary
        if radius > self.safe_radius:
            return False, f"radius_exceeded: {radius:.4f} > {self.safe_radius}"

        # Check 2: Angular deviation from nearest tongue reference
        if radius > EPSILON:
            min_dev = self._angular_deviation(embedding)
            if min_dev > self.max_angular_dev:
                return False, f"angular_deviation: {min_dev:.4f} > {self.max_angular_dev}"

        return True, "within_bounds"

    def check_action(self, embedding: List[float], action: str = "", target: str = "") -> SafetyResult:
        """
        Full safety check with decision, cost, and audit metadata.

        Combines radius check, angular deviation, and harmonic wall cost
        into a 4-tier decision:
            ALLOW:      radius < 0.7 * safe_radius
            QUARANTINE: radius < safe_radius and angular_dev < max_angular_dev
            ESCALATE:   radius < safe_radius but angular_dev >= max_angular_dev
            DENY:       radius >= safe_radius

        Args:
            embedding: Point in the Poincaré ball.
            action: Action name (for audit).
            target: Action target (for audit).

        Returns:
            SafetyResult with decision, cost, and metadata.
        """
        if len(embedding) != self.dim:
            return SafetyResult(
                safe=False,
                reason=f"dimension_mismatch: expected {self.dim}, got {len(embedding)}",
                radius=0.0,
                angular_deviation=0.0,
                decision=Decision.DENY,
                cost=float("inf"),
            )

        radius = self._norm(embedding)
        angular_dev = self._angular_deviation(embedding) if radius > EPSILON else 0.0
        dist_from_origin = self.hyperbolic_distance(self._origin, embedding)
        cost = self.harmonic_cost(dist_from_origin)

        # 4-tier decision logic
        if radius >= self.safe_radius:
            decision = Decision.DENY
            safe = False
            reason = f"radius_exceeded: {radius:.4f} >= {self.safe_radius}"
        elif angular_dev > self.max_angular_dev:
            decision = Decision.ESCALATE
            safe = False
            reason = f"angular_deviation: {angular_dev:.4f} > {self.max_angular_dev}"
        elif radius < self.safe_radius * 0.7:
            decision = Decision.ALLOW
            safe = True
            reason = "within_bounds"
        else:
            decision = Decision.QUARANTINE
            safe = True
            reason = "near_boundary: monitoring"

        return SafetyResult(
            safe=safe,
            reason=reason,
            radius=radius,
            angular_deviation=angular_dev,
            decision=decision,
            cost=cost,
            embedding=list(embedding),
        )

    # =========================================================================
    # Action encoding
    # =========================================================================

    def encode_action(self, action: str, target: str, context: Optional[Dict[str, Any]] = None) -> List[float]:
        """
        Encode a browser action as a tangent vector for exp_map.

        Creates a deterministic embedding that incorporates:
        - Action type (mapped to Sacred Tongue phase)
        - Target hash (distributed across dimensions)
        - Context features (sensitivity, domain risk)

        The resulting tangent vector can be mapped to the Poincaré ball
        via exp_map() for safety checking.

        Args:
            action: Action name (navigate, click, type, etc.).
            target: Action target (URL, selector, etc.).
            context: Optional dict with extra features (sensitivity, etc.).

        Returns:
            Tangent vector of dimension self.dim.
        """
        context = context or {}

        # Get tongue assignment and phase
        tongue = ACTION_TONGUE.get(action, "DR")
        phase = TONGUE_PHASES[tongue]

        # Hash target for reproducible distribution
        target_hash = hashlib.sha256(target.encode("utf-8")).digest()

        # Build tangent vector
        v = [0.0] * self.dim

        # Dimensions 0-1: phase-encoded action type (polar → cartesian)
        sensitivity = context.get("sensitivity", 0.5)
        action_magnitude = 0.5 + sensitivity * 1.5  # range [0.5, 2.0]
        v[0] = action_magnitude * math.cos(phase)
        v[1] = action_magnitude * math.sin(phase)

        # Dimensions 2-9: target hash features
        for i in range(min(8, self.dim - 2)):
            byte_val = target_hash[i % len(target_hash)]
            # Normalize byte to [-1, 1] and scale by action sensitivity
            v[i + 2] = ((byte_val / 127.5) - 1.0) * (0.3 + sensitivity * 0.4)

        # Dimensions 10-11: domain risk signal
        if self.dim > 10:
            domain_risk = context.get("domain_risk", 0.4)
            v[10] = domain_risk * math.cos(phase * 2)
            v[11] = domain_risk * math.sin(phase * 2)

        # Dimensions 12-13: temporal signal (step count normalization)
        if self.dim > 12:
            step = context.get("step", 0)
            max_steps = context.get("max_steps", 10)
            progress = min(step / max(max_steps, 1), 1.0)
            v[12] = progress * 0.5
            v[13] = (1.0 - progress) * 0.5

        # Dimensions 14-15: confidence / urgency
        if self.dim > 14:
            confidence = context.get("confidence", 0.8)
            urgency = context.get("urgency", 0.5)
            v[14] = confidence * 0.3
            v[15] = urgency * 0.3

        return v

    def embed_action(self, action: str, target: str, context: Optional[Dict[str, Any]] = None) -> ActionEmbedding:
        """
        Full pipeline: encode action → exp_map → return ActionEmbedding.

        Convenience method that combines encode_action and exp_map.

        Args:
            action: Action name.
            target: Action target.
            context: Optional context dict.

        Returns:
            ActionEmbedding with the hyperbolic point and metadata.
        """
        tongue = ACTION_TONGUE.get(action, "DR")
        tangent = self.encode_action(action, target, context)
        point = self.exp_map(tangent)

        embedding = ActionEmbedding(
            action=action,
            target=target,
            vector=point,
            tongue=tongue,
            phase=TONGUE_PHASES[tongue],
        )

        self._history.append(embedding)
        return embedding

    # =========================================================================
    # Phase / angular analysis
    # =========================================================================

    def _build_tongue_references(self) -> Dict[str, List[float]]:
        """Build unit reference vectors for each Sacred Tongue phase."""
        refs = {}
        for tongue, phase in TONGUE_PHASES.items():
            v = [0.0] * self.dim
            v[0] = math.cos(phase)
            v[1] = math.sin(phase)
            refs[tongue] = v
        return refs

    def _angular_deviation(self, embedding: List[float]) -> float:
        """
        Minimum angular deviation from any tongue reference.

        Computes cos(angle) between embedding and each tongue reference
        using the first 2 dimensions (where phase is encoded), then
        returns the smallest angular deviation.

        Args:
            embedding: Point in Poincaré ball.

        Returns:
            Minimum angular deviation in radians.
        """
        # Use first 2 dims for phase comparison
        e_norm_2d = math.sqrt(embedding[0] ** 2 + embedding[1] ** 2)
        if e_norm_2d < EPSILON:
            return 0.0  # At origin, no angular deviation

        min_angle = math.pi
        for ref in self._tongue_refs.values():
            r_norm_2d = math.sqrt(ref[0] ** 2 + ref[1] ** 2)
            if r_norm_2d < EPSILON:
                continue
            cos_angle = (embedding[0] * ref[0] + embedding[1] * ref[1]) / (e_norm_2d * r_norm_2d)
            cos_angle = max(-1.0, min(1.0, cos_angle))
            angle = math.acos(cos_angle)
            min_angle = min(min_angle, angle)

        return min_angle

    # =========================================================================
    # Trajectory analysis
    # =========================================================================

    def trajectory_drift(self, window: int = 5) -> float:
        """
        Compute trajectory drift over the last N actions.

        Measures the cumulative hyperbolic distance between consecutive
        action embeddings. High drift may indicate erratic behavior.

        Args:
            window: Number of recent actions to analyze.

        Returns:
            Cumulative hyperbolic distance over the window.
        """
        if len(self._history) < 2:
            return 0.0

        recent = self._history[-window:]
        total_drift = 0.0
        for i in range(1, len(recent)):
            total_drift += self.hyperbolic_distance(recent[i - 1].vector, recent[i].vector)
        return total_drift

    def get_state(self) -> Dict[str, Any]:
        """
        Get current brain state for monitoring/audit.

        Returns:
            Dict with configuration, history length, and latest radius.
        """
        latest_radius = 0.0
        if self._history:
            latest_radius = self._norm(self._history[-1].vector)

        return {
            "dim": self.dim,
            "curvature": self.curvature,
            "safe_radius": self.safe_radius,
            "max_angular_dev": self.max_angular_dev,
            "history_length": len(self._history),
            "latest_radius": latest_radius,
            "trajectory_drift": self.trajectory_drift(),
        }

    def reset(self) -> None:
        """Clear action history."""
        self._history.clear()
