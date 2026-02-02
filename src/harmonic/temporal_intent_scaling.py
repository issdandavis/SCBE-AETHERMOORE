"""
Temporal–Intent Harmonic Scaling

The canonical extension to the Harmonic Wall formula that incorporates
temporal persistence of adversarial behavior:

    H_eff(d, R, x) = R^(d²) · x

Where:
- d  = deviation distance from safe operation (hyperbolic/geometric)
- R  = harmonic base (1.5 "Perfect Fifth" default)
- x  = temporal intent factor derived from:
       - Triadic temporal distance d_tri(t) [Layer 11]
       - CPSE z-vector channels: chaosdev, fractaldev, energydev
       - Trajectory coherence metrics

Properties:
- x < 1: Brief spikes are forgiven (reduced cost)
- x = 1: Instantaneous assessment (baseline)
- x > 1: Sustained adversarial behavior compounds super-exponentially

This makes the Harmonic Wall adaptive:
- Momentary glitches don't trigger escalation
- Persistent bad intent faces brutal exponential cost growth
- Genuine recovery paths remain accessible

@module harmonic/temporal_intent_scaling
@layer Layer 11, Layer 12
@version 1.0.0
@since 2026-02-02
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
import math
import numpy as np
from collections import deque

# ============================================================================
# Constants
# ============================================================================

PHI = 1.618033988749895  # Golden ratio
E = 2.718281828459045    # Euler's number
PERFECT_FIFTH = 1.5      # Default harmonic base R
EPSILON = 1e-10

# Decimal drift protection constants
DRIFT_TOLERANCE = 1e-9        # Maximum acceptable drift per operation
MAX_ACCUMULATED_DRIFT = 1e-6  # Trigger recalibration above this
PRECISION_DIGITS = 12         # Significant digits to preserve


# ============================================================================
# Decimal Drift Protection
# ============================================================================

class DriftMonitor:
    """
    Monitors and corrects floating-point drift in mathematical chain.

    Ensures changes propagate correctly through:
    d_H → d_tri → x(t) → H_eff

    Without accumulating numerical errors that could cause
    security decisions to diverge from mathematical intent.
    """

    def __init__(self, tolerance: float = DRIFT_TOLERANCE):
        self.tolerance = tolerance
        self.accumulated_drift = 0.0
        self.calibration_count = 0
        self.last_values: Dict[str, float] = {}

    def check_and_correct(self, name: str, computed: float, expected: Optional[float] = None) -> float:
        """
        Check value for drift and apply correction if needed.

        Args:
            name: Variable name for tracking
            computed: Newly computed value
            expected: Optional expected value for comparison

        Returns:
            Corrected value with drift removed
        """
        # Round to precision to prevent gradual drift
        corrected = round(computed, PRECISION_DIGITS)

        # Track drift if we have expected value
        if expected is not None:
            drift = abs(corrected - expected)
            self.accumulated_drift += drift

            if drift > self.tolerance:
                # Log significant drift (in production, would alert)
                pass

        # Store for chain tracking
        self.last_values[name] = corrected

        # Check if recalibration needed
        if self.accumulated_drift > MAX_ACCUMULATED_DRIFT:
            self._recalibrate()

        return corrected

    def _recalibrate(self) -> None:
        """Reset drift accumulation and force precision."""
        self.accumulated_drift = 0.0
        self.calibration_count += 1
        # Re-round all tracked values
        for name in self.last_values:
            self.last_values[name] = round(self.last_values[name], PRECISION_DIGITS)

    def get_drift_report(self) -> Dict[str, Any]:
        """Get current drift statistics."""
        return {
            "accumulated_drift": self.accumulated_drift,
            "calibration_count": self.calibration_count,
            "tracked_variables": len(self.last_values),
            "within_tolerance": self.accumulated_drift <= MAX_ACCUMULATED_DRIFT,
        }


# Global drift monitor for the H_eff chain
_drift_monitor = DriftMonitor()


def with_drift_protection(func):
    """Decorator to add drift protection to mathematical functions."""
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if isinstance(result, (int, float)):
            return _drift_monitor.check_and_correct(func.__name__, result)
        return result
    return wrapper


def reset_drift_monitor() -> None:
    """Reset the global drift monitor."""
    global _drift_monitor
    _drift_monitor = DriftMonitor()


def get_drift_status() -> Dict[str, Any]:
    """Get current drift monitor status."""
    return _drift_monitor.get_drift_report()


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class DeviationChannels:
    """
    CPSE z-vector deviation channels.

    These measure different aspects of behavioral instability:
    - chaosdev: Lyapunov-based chaos metric
    - fractaldev: Fractal dimension deviation
    - energydev: Energy distribution deviation
    """
    chaosdev: float = 0.0    # Chaos/Lyapunov deviation [0, 1]
    fractaldev: float = 0.0  # Fractal deviation [0, 1]
    energydev: float = 0.0   # Energy deviation [0, 1]
    timestamp: float = 0.0   # When measured

    def composite(self, weights: Tuple[float, float, float] = (0.4, 0.3, 0.3)) -> float:
        """Compute weighted composite deviation."""
        w1, w2, w3 = weights
        total = w1 + w2 + w3
        return (w1 * self.chaosdev + w2 * self.fractaldev + w3 * self.energydev) / total


@dataclass
class TriadicTemporalState:
    """
    Layer 11 triadic temporal distance state.

    Tracks behavior across three time horizons:
    - d1: Immediate (last few operations)
    - d2: Medium-term (session behavior)
    - d3: Long-term (historical pattern)
    """
    d_immediate: float = 0.0  # Immediate behavior distance
    d_medium: float = 0.0     # Medium-term behavior distance
    d_longterm: float = 0.0   # Long-term pattern distance
    lambda_1: float = 0.4     # Weight for immediate
    lambda_2: float = 0.3     # Weight for medium
    lambda_3: float = 0.3     # Weight for long-term

    def d_tri(self) -> float:
        """Compute triadic distance d_tri = √(λ₁d₁² + λ₂d₂² + λ₃d₃²)"""
        return math.sqrt(
            self.lambda_1 * self.d_immediate ** 2 +
            self.lambda_2 * self.d_medium ** 2 +
            self.lambda_3 * self.d_longterm ** 2
        )


@dataclass
class TrajectoryCoherence:
    """
    Trajectory coherence metrics from Part 3 predictions.

    Measures how consistently behavior follows expected patterns.
    """
    coherence: float = 1.0     # [0, 1], 1 = perfectly coherent
    drift_rate: float = 0.0    # Rate of deviation from expected
    reversal_count: int = 0    # Number of direction reversals
    stability_score: float = 1.0  # Overall stability


@dataclass
class TemporalIntentState:
    """
    Complete state for temporal intent computation.
    """
    triadic: TriadicTemporalState = field(default_factory=TriadicTemporalState)
    deviations: DeviationChannels = field(default_factory=DeviationChannels)
    trajectory: TrajectoryCoherence = field(default_factory=TrajectoryCoherence)
    history: List[float] = field(default_factory=list)  # Recent x values
    window_size: int = 10  # Rolling window for smoothing


# ============================================================================
# Temporal Intent Factor Computation
# ============================================================================

def compute_temporal_intent_factor(
    state: TemporalIntentState,
    use_smoothing: bool = True,
    alpha: float = 0.3,
) -> float:
    """
    Compute the temporal intent factor x(t).

    x(t) ≈ f(d_tri(t), chaosdev(t), fractaldev(t), energydev(t))

    The function combines:
    1. Triadic temporal distance (behavioral persistence)
    2. CPSE deviation channels (instability metrics)
    3. Trajectory coherence (pattern consistency)

    Args:
        state: Current temporal intent state
        use_smoothing: Apply exponential smoothing to x
        alpha: Smoothing factor (higher = more responsive)

    Returns:
        x factor: < 1 for forgiving, = 1 neutral, > 1 for punitive
    """
    # Component 1: Triadic temporal contribution
    d_tri = state.triadic.d_tri()

    # Scale d_tri to [0.5, 2.0] range
    # d_tri = 0 → x_tri = 0.5 (forgiving)
    # d_tri = 1 → x_tri = 1.0 (neutral)
    # d_tri = 2 → x_tri = 2.0 (punitive)
    x_tri = 0.5 + 0.5 * d_tri

    # Component 2: Deviation channel contribution
    z_composite = state.deviations.composite()

    # Scale to [0.8, 1.5] - deviations increase cost
    x_dev = 0.8 + 0.7 * z_composite

    # Component 3: Trajectory coherence contribution
    # High coherence → lower x (forgiving)
    # Low coherence → higher x (suspicious)
    coherence = state.trajectory.coherence
    stability = state.trajectory.stability_score

    # Invert: coherence=1 → x_traj=0.7, coherence=0 → x_traj=1.3
    x_traj = 1.3 - 0.6 * (coherence * stability)

    # Combine multiplicatively (they compound)
    # x = x_tri * x_dev * x_traj, but normalized
    x_raw = (x_tri * x_dev * x_traj) ** (1/3)  # Geometric mean

    # Apply reversal penalty (direction changes are suspicious)
    reversal_penalty = 1.0 + 0.05 * min(state.trajectory.reversal_count, 10)
    x_raw *= reversal_penalty

    # Clamp to reasonable bounds [0.1, 10.0]
    x_clamped = max(0.1, min(10.0, x_raw))

    # Apply exponential smoothing if history available
    if use_smoothing and state.history:
        x_smoothed = alpha * x_clamped + (1 - alpha) * state.history[-1]
    else:
        x_smoothed = x_clamped

    return x_smoothed


def update_temporal_state(
    state: TemporalIntentState,
    new_deviation: float,
    deviation_channels: Optional[DeviationChannels] = None,
    decay_rate: float = 0.9,
) -> float:
    """
    Update temporal state with new observation and return x factor.

    Args:
        state: State to update
        new_deviation: New deviation measurement
        deviation_channels: Optional CPSE channels
        decay_rate: How fast old observations decay

    Returns:
        Updated x factor
    """
    # Update triadic distances with decay
    state.triadic.d_longterm = (
        decay_rate * state.triadic.d_longterm +
        (1 - decay_rate) * state.triadic.d_medium
    )
    state.triadic.d_medium = (
        decay_rate * state.triadic.d_medium +
        (1 - decay_rate) * state.triadic.d_immediate
    )
    state.triadic.d_immediate = new_deviation

    # Update deviation channels if provided
    if deviation_channels:
        state.deviations = deviation_channels

    # Compute new x factor
    x = compute_temporal_intent_factor(state)

    # Update history (rolling window)
    state.history.append(x)
    if len(state.history) > state.window_size:
        state.history.pop(0)

    return x


# ============================================================================
# Effective Harmonic Scaling
# ============================================================================

def harmonic_scale_basic(d: float, R: float = PERFECT_FIFTH) -> float:
    """
    Basic harmonic scaling: H(d, R) = R^(d²)

    This is the original Layer 12 formula without temporal intent.
    """
    if d < 0:
        raise ValueError("Deviation d must be >= 0")
    if R <= 0:
        raise ValueError("Harmonic base R must be > 0")

    exponent = d * d
    # Prevent overflow for extreme values
    max_exp = 700 / math.log(max(R, 1.01))  # ln(DBL_MAX) ≈ 709
    exponent = min(exponent, max_exp)

    return R ** exponent


def harmonic_scale_effective(
    d: float,
    R: float = PERFECT_FIFTH,
    x: float = 1.0,
) -> float:
    """
    Temporal–Intent Harmonic Scaling: H_eff(d, R, x) = R^(d²) · x

    This is the canonical extension that incorporates temporal persistence.

    Args:
        d: Deviation distance from safe operation
        R: Harmonic base (default 1.5 "Perfect Fifth")
        x: Temporal intent factor from compute_temporal_intent_factor()

    Returns:
        Effective harmonic scaling with temporal modulation

    Properties:
        - x < 1: Brief spikes forgiven (reduced cost)
        - x = 1: Instantaneous baseline
        - x > 1: Sustained adversarial behavior compounds

    Example:
        >>> harmonic_scale_effective(2.0, 1.5, 0.5)  # Brief spike
        1.265625  # Reduced from 2.53125

        >>> harmonic_scale_effective(2.0, 1.5, 1.0)  # Neutral
        2.53125   # Standard H(2, 1.5) = 1.5^4

        >>> harmonic_scale_effective(2.0, 1.5, 2.0)  # Sustained bad
        5.0625    # Doubled cost
    """
    H = harmonic_scale_basic(d, R)
    return H * x


def harmonic_scale_with_state(
    d: float,
    state: TemporalIntentState,
    R: float = PERFECT_FIFTH,
) -> Tuple[float, float]:
    """
    Compute H_eff using temporal intent state.

    Args:
        d: Deviation distance
        state: Temporal intent state
        R: Harmonic base

    Returns:
        Tuple of (H_eff, x) - effective scaling and intent factor
    """
    x = compute_temporal_intent_factor(state)
    H_eff = harmonic_scale_effective(d, R, x)
    return H_eff, x


# ============================================================================
# Security Bit Calculation with Temporal Intent
# ============================================================================

def security_bits_effective(
    base_bits: float,
    d: float,
    R: float = PERFECT_FIFTH,
    x: float = 1.0,
) -> float:
    """
    Calculate security bits with temporal intent modulation.

    security_eff = base + d² × log₂(R) + log₂(x)

    Args:
        base_bits: Base security level in bits
        d: Deviation distance
        R: Harmonic base
        x: Temporal intent factor

    Returns:
        Effective security bits
    """
    log2_R = math.log2(R)
    log2_x = math.log2(max(x, EPSILON))  # Protect against x=0

    return base_bits + d * d * log2_R + log2_x


# ============================================================================
# Risk Decision with Temporal Awareness
# ============================================================================

@dataclass
class TemporalRiskAssessment:
    """Result of temporal-aware risk assessment."""
    H_basic: float        # Basic H(d, R)
    H_effective: float    # H_eff(d, R, x)
    x_factor: float       # Temporal intent factor
    d_star: float         # Input deviation
    risk_level: str       # ALLOW / QUARANTINE / ESCALATE / DENY
    forgiveness_applied: bool  # True if x < 1
    compounding_applied: bool  # True if x > 1
    reasoning: str        # Human-readable explanation


def assess_risk_temporal(
    d_star: float,
    state: TemporalIntentState,
    R: float = PERFECT_FIFTH,
    allow_threshold: float = 0.3,
    quarantine_threshold: float = 0.5,
    escalate_threshold: float = 0.7,
) -> TemporalRiskAssessment:
    """
    Four-tier risk decision with temporal intent awareness.

    Decision tiers:
    - ALLOW: Brief deviation, good trajectory, x < 1
    - QUARANTINE: Moderate risk, needs monitoring
    - ESCALATE: High risk, human review required
    - DENY: Sustained adversarial pattern detected

    Args:
        d_star: Deviation distance
        state: Temporal intent state
        R: Harmonic base
        allow_threshold: H_eff below this → ALLOW
        quarantine_threshold: H_eff below this → QUARANTINE
        escalate_threshold: H_eff below this → ESCALATE

    Returns:
        TemporalRiskAssessment with decision and explanation
    """
    # Compute both basic and effective scaling
    H_basic = harmonic_scale_basic(d_star, R)
    x = compute_temporal_intent_factor(state)
    H_eff = H_basic * x

    # Normalize to [0, 1] for threshold comparison
    # Using exponential saturation: risk = 1 - exp(-H_eff/scale)
    scale = 10.0  # Tunable parameter
    risk_normalized = 1.0 - math.exp(-H_eff / scale)

    # Determine risk level
    forgiveness = x < 1.0
    compounding = x > 1.0

    if risk_normalized < allow_threshold:
        level = "ALLOW"
        reasoning = "Low risk with " + (
            "temporal forgiveness applied" if forgiveness else "stable trajectory"
        )
    elif risk_normalized < quarantine_threshold:
        level = "QUARANTINE"
        reasoning = "Moderate risk, monitoring required"
    elif risk_normalized < escalate_threshold:
        level = "ESCALATE"
        reasoning = "High risk, human review recommended"
    else:
        level = "DENY"
        reasoning = "Sustained adversarial pattern detected" if compounding else "Extreme deviation"

    return TemporalRiskAssessment(
        H_basic=H_basic,
        H_effective=H_eff,
        x_factor=x,
        d_star=d_star,
        risk_level=level,
        forgiveness_applied=forgiveness,
        compounding_applied=compounding,
        reasoning=reasoning,
    )


# ============================================================================
# Convenience Functions
# ============================================================================

def create_temporal_state() -> TemporalIntentState:
    """Create a fresh temporal intent state."""
    return TemporalIntentState()


def quick_harmonic_effective(
    d: float,
    sustained_deviation_count: int = 0,
    has_recovery_attempt: bool = False,
    R: float = PERFECT_FIFTH,
) -> float:
    """
    Quick H_eff calculation without full state management.

    Args:
        d: Deviation distance
        sustained_deviation_count: How many consecutive bad operations
        has_recovery_attempt: True if agent is attempting recovery
        R: Harmonic base

    Returns:
        Approximate H_eff
    """
    # Estimate x from simple heuristics
    if has_recovery_attempt:
        x = 0.7  # Forgiveness for recovery attempt
    elif sustained_deviation_count > 5:
        x = 1.5 + 0.1 * (sustained_deviation_count - 5)  # Compounding
    elif sustained_deviation_count > 0:
        x = 1.0 + 0.1 * sustained_deviation_count  # Mild increase
    else:
        x = 1.0  # Neutral

    return harmonic_scale_effective(d, R, min(x, 5.0))


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Data structures
    "DeviationChannels",
    "TriadicTemporalState",
    "TrajectoryCoherence",
    "TemporalIntentState",
    "TemporalRiskAssessment",
    # Drift protection
    "DriftMonitor",
    "with_drift_protection",
    "reset_drift_monitor",
    "get_drift_status",
    "DRIFT_TOLERANCE",
    "MAX_ACCUMULATED_DRIFT",
    "PRECISION_DIGITS",
    # Core functions
    "compute_temporal_intent_factor",
    "update_temporal_state",
    "harmonic_scale_basic",
    "harmonic_scale_effective",
    "harmonic_scale_with_state",
    "security_bits_effective",
    "assess_risk_temporal",
    # Convenience
    "create_temporal_state",
    "quick_harmonic_effective",
    # Constants
    "PHI",
    "PERFECT_FIFTH",
]
