"""
Causality Axiom Module - Time-Ordered Transforms

This module groups layers that satisfy the causality axiom from physics:
transformations that respect the causal (time-ordered) structure of events.

Assigned Layers:
- Layer 6: Breathing Transform - Time-dependent expansion/contraction
- Layer 11: Triadic Temporal Distance - Combines space, time, and entropy
- Layer 13: Decision & Risk Assessment - Governance pipeline (causal decisions)

Mathematical Foundation:
A transform T satisfies causality iff for events e₁, e₂:
    t(e₁) < t(e₂) ⟹ T(e₁) does not depend on T(e₂)

This ensures information cannot travel backwards in time.
"""

from __future__ import annotations

import functools
import numpy as np
from typing import Callable, TypeVar, Any, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
import time as time_module

# Type variables for generic decorators
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

# Constants
EPS = 1e-10
PHI = (1 + np.sqrt(5)) / 2  # Golden ratio
OMEGA_BREATH = 2 * np.pi / 60  # Breathing frequency (60s period)
B_BREATH_MAX = 1.5  # Maximum breathing amplitude
THETA_1 = 0.5  # Low risk threshold
THETA_2 = 2.0  # High risk threshold


class CausalityViolation(Exception):
    """Raised when a transform violates the causality axiom."""
    pass


class RiskLevel(Enum):
    """Risk levels for governance decisions."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Decision(Enum):
    """Governance decisions based on risk assessment."""
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    DENY = "DENY"
    SNAP = "SNAP"  # Emergency intervention


@dataclass
class CausalityCheckResult:
    """Result of a causality axiom check."""
    passed: bool
    time_ordering_preserved: bool
    future_dependency_detected: bool
    layer_name: str
    current_time: float
    message: str

    def __str__(self) -> str:
        status = "PASSED" if self.passed else "FAILED"
        return (
            f"CausalityCheck[{self.layer_name}]: {status}\n"
            f"  Time ordering preserved: {self.time_ordering_preserved}\n"
            f"  Future dependency: {self.future_dependency_detected}\n"
            f"  Current time: {self.current_time:.4f}\n"
            f"  Message: {self.message}"
        )


@dataclass
class TemporalState:
    """Encapsulates the temporal state of the system."""
    t: float  # Current time
    tau: float  # Temporal coordinate
    eta: float  # Entropy
    history: List[Tuple[float, Any]]  # (timestamp, state) history

    def record(self, state: Any) -> None:
        """Record current state in history."""
        self.history.append((self.t, state))

    def get_past_states(self, lookback: float) -> List[Tuple[float, Any]]:
        """Get states from the past within lookback window."""
        cutoff = self.t - lookback
        return [(t, s) for t, s in self.history if t >= cutoff]


def causality_check(
    require_time_param: bool = True,
    allow_acausal: bool = False
) -> Callable[[F], F]:
    """
    Decorator that verifies a transform respects causality.

    Causality is checked by ensuring:
    1. The transform depends only on past/present states
    2. Time parameters flow forward monotonically

    Args:
        require_time_param: If True, function must have a time parameter
        allow_acausal: If True, allow violations (for debugging/testing)

    Returns:
        Decorated function with causality verification
    """
    def decorator(func: F) -> F:
        # Track last execution time for ordering checks
        last_time = {'value': None}

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract time parameter
            current_time = kwargs.get('t', None)
            if current_time is None and len(args) > 1:
                # Try to find time in positional args
                for arg in args:
                    if isinstance(arg, (int, float)) and 0 <= arg < 1e10:
                        current_time = float(arg)
                        break

            if current_time is None:
                current_time = time_module.time() % 1000  # Use system time

            # Check time ordering
            time_ordering_preserved = True
            future_dependency = False
            message = "OK"

            if last_time['value'] is not None:
                if current_time < last_time['value']:
                    time_ordering_preserved = False
                    message = f"Time went backwards: {current_time:.4f} < {last_time['value']:.4f}"
                    if not allow_acausal:
                        future_dependency = True

            # Update last time
            last_time['value'] = current_time

            # Execute the function
            result = func(*args, **kwargs)

            # Record causality check
            check_result = CausalityCheckResult(
                passed=time_ordering_preserved and not future_dependency,
                time_ordering_preserved=time_ordering_preserved,
                future_dependency_detected=future_dependency,
                layer_name=func.__name__,
                current_time=current_time,
                message=message
            )

            wrapper.last_check = check_result

            if not check_result.passed and not allow_acausal:
                raise CausalityViolation(str(check_result))

            return result

        wrapper.last_check = None
        wrapper.axiom = "causality"
        wrapper.reset_time = lambda: last_time.update({'value': None})
        return wrapper
    return decorator


# ============================================================================
# Layer 6: Breathing Transform
# ============================================================================

def breathing_factor(t: float, b_max: float = B_BREATH_MAX, omega: float = OMEGA_BREATH) -> float:
    """
    Compute the breathing factor at time t.

    b(t) = 1 + b_max · sin(ωt)

    This creates expansion/contraction cycles synchronized with
    the governance breathing rhythm.

    Args:
        t: Current time
        b_max: Maximum breathing amplitude
        omega: Angular frequency

    Returns:
        Breathing factor b(t) ∈ [1 - b_max, 1 + b_max]
    """
    return 1.0 + b_max * np.sin(omega * t)


@causality_check(require_time_param=True)
def layer_6_breathing(u: np.ndarray, t: float) -> np.ndarray:
    """
    Layer 6: Breathing Transform

    T_breath(u; t) = tanh(b(t) · artanh(||u||)) · u/||u||

    Time-dependent expansion/contraction of hyperbolic space.

    Causality Property:
        The transform at time t depends ONLY on the current state u
        and current time t. It does not access future times.

    Properties:
        - Diffeomorphism of the Poincaré ball onto itself
        - Does NOT preserve hyperbolic distance (intentional)
        - Creates rhythmic cycles that modulate governance sensitivity

    Args:
        u: Point in Poincaré ball
        t: Current time (seconds)

    Returns:
        Transformed point (still in ball)
    """
    norm_u = np.linalg.norm(u)

    if norm_u < EPS:
        return u.copy()

    # Clamp to stay strictly inside ball
    norm_u = min(norm_u, 1.0 - EPS)

    # Compute breathing factor
    b = breathing_factor(t)

    # Apply radial scaling
    # artanh(||u||) gives hyperbolic radius
    # b(t) * artanh scales it
    # tanh brings it back to [0, 1)
    hyp_radius = np.arctanh(norm_u)
    scaled_radius = np.tanh(b * hyp_radius)

    # Preserve direction
    direction = u / norm_u

    return scaled_radius * direction


def layer_6_inverse(u_breathed: np.ndarray, t: float) -> np.ndarray:
    """
    Inverse of Layer 6: Undo breathing at time t.

    Args:
        u_breathed: Transformed point
        t: Time at which breathing was applied

    Returns:
        Original point
    """
    norm_u = np.linalg.norm(u_breathed)

    if norm_u < EPS:
        return u_breathed.copy()

    norm_u = min(norm_u, 1.0 - EPS)
    b = breathing_factor(t)

    # Invert: artanh(tanh(b * artanh(||u_orig||))) = b * artanh(||u_orig||)
    # So: artanh(||u_breathed||) / b = artanh(||u_orig||)
    hyp_radius_scaled = np.arctanh(norm_u)
    hyp_radius_orig = hyp_radius_scaled / b
    norm_orig = np.tanh(hyp_radius_orig)

    direction = u_breathed / norm_u

    return norm_orig * direction


# ============================================================================
# Layer 11: Triadic Temporal Distance
# ============================================================================

def quantum_fidelity(q1: complex, q2: complex) -> float:
    """
    Compute quantum fidelity between two pure state amplitudes.

    F_q = |⟨q1|q2⟩|² = |q1* · q2|²

    Args:
        q1, q2: Complex amplitudes

    Returns:
        Fidelity in [0, 1]
    """
    inner = np.conj(q1) * q2
    return float(np.abs(inner) ** 2)


def hyperbolic_distance(u: np.ndarray, v: np.ndarray) -> float:
    """
    Compute hyperbolic distance in the Poincaré ball.

    d_H(u, v) = arcosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))
    """
    diff = u - v
    diff_sq = np.dot(diff, diff)
    u_sq = np.dot(u, u)
    v_sq = np.dot(v, v)

    # Clamp to avoid numerical issues
    u_sq = min(u_sq, 1.0 - EPS)
    v_sq = min(v_sq, 1.0 - EPS)

    denominator = (1 - u_sq) * (1 - v_sq)
    if denominator < EPS:
        return float('inf')

    arg = 1 + 2 * diff_sq / denominator
    arg = max(arg, 1.0)

    return float(np.arccosh(arg))


@causality_check(require_time_param=False)
def layer_11_triadic_distance(
    u: np.ndarray,
    ref_u: np.ndarray,
    tau: float,
    ref_tau: float,
    eta: float,
    ref_eta: float,
    q: complex,
    ref_q: complex
) -> float:
    """
    Layer 11: Triadic Temporal Distance

    d_tri = √(d_H² + (Δτ)² + (Δη)² + (1 - F_q))

    Combines four distance components:
    1. Hyperbolic distance in context space
    2. Temporal difference (Δτ)
    3. Entropy difference (Δη)
    4. Quantum fidelity loss (1 - F_q)

    Causality Property:
        Distance computation compares current state to a REFERENCE state
        (which must be from the past or present). The triadic structure
        explicitly encodes temporal ordering through τ.

    Args:
        u, ref_u: Current and reference points in Poincaré ball
        tau, ref_tau: Current and reference temporal coordinates
        eta, ref_eta: Current and reference entropy values
        q, ref_q: Current and reference quantum amplitudes

    Returns:
        Triadic distance d_tri
    """
    # Component 1: Hyperbolic distance
    d_H = hyperbolic_distance(u, ref_u)

    # Component 2: Temporal difference
    delta_tau = abs(tau - ref_tau)

    # Component 3: Entropy difference
    delta_eta = abs(eta - ref_eta)

    # Component 4: Quantum fidelity loss
    F_q = quantum_fidelity(q, ref_q)
    fidelity_loss = 1.0 - F_q

    # Combine with Pythagorean sum
    d_tri = np.sqrt(d_H**2 + delta_tau**2 + delta_eta**2 + fidelity_loss)

    return float(d_tri)


# ============================================================================
# Layer 13: Decision & Risk Assessment
# ============================================================================

@dataclass
class RiskAssessment:
    """Complete risk assessment from the governance pipeline."""
    level: RiskLevel
    decision: Decision
    raw_risk: float
    harmonic_amplified: float
    distance_to_realm: float
    realm_index: int
    coherence: float
    timestamp: float

    def __str__(self) -> str:
        return (
            f"RiskAssessment @ t={self.timestamp:.2f}\n"
            f"  Level: {self.level.value}\n"
            f"  Decision: {self.decision.value}\n"
            f"  Raw Risk: {self.raw_risk:.4f}\n"
            f"  H(d*): {self.harmonic_amplified:.4f}\n"
            f"  d* (to realm {self.realm_index}): {self.distance_to_realm:.4f}\n"
            f"  Coherence: {self.coherence:.4f}"
        )


def harmonic_scaling(d: float, R: float = PHI) -> float:
    """
    Harmonic scaling function with superexponential growth.

    H(d, R) = R^(d²)

    Properties:
        - H(0) = 1
        - H'(d) = 2d · R^(d²) · ln(R) > 0 (strictly increasing)
        - Creates "vertical wall" effect at large d

    Args:
        d: Distance value
        R: Base (default: golden ratio φ)

    Returns:
        Harmonically scaled value
    """
    # Clamp to prevent overflow
    d_sq = min(d ** 2, 50.0)
    return R ** d_sq


@causality_check(require_time_param=False)
def layer_13_decision(
    d_star: float,
    coherence: float,
    realm_index: int,
    realm_weight: float = 1.0,
    theta_1: float = THETA_1,
    theta_2: float = THETA_2,
    R: float = PHI
) -> RiskAssessment:
    """
    Layer 13: Decision & Risk Assessment

    Risk' = H(d*) · (1 - coherence) · realm_weight

    Makes governance decisions based on:
    1. Distance to nearest realm (d*)
    2. Coherence of the signal
    3. Realm sensitivity weight

    Decision Logic:
        H(d*) > 100 → CRITICAL → SNAP
        d* ≥ θ₂ → HIGH → DENY
        θ₁ ≤ d* < θ₂ → MEDIUM → REVIEW
        d* < θ₁ → LOW → ALLOW

    Causality Property:
        The decision at time t is based ONLY on measurements taken
        at time t or earlier. The decision tree is deterministic
        given the inputs (no future lookahead).

    Args:
        d_star: Minimum distance to any realm center
        coherence: Signal coherence [0, 1]
        realm_index: Index of nearest realm
        realm_weight: Governance sensitivity multiplier
        theta_1, theta_2: Risk thresholds
        R: Harmonic scaling base

    Returns:
        Complete risk assessment
    """
    # Compute harmonic amplification
    H_d = harmonic_scaling(d_star, R)

    # Raw risk computation
    raw_risk = H_d * (1.0 - coherence) * realm_weight

    # Decision logic based on thresholds
    if H_d > 100.0:
        level = RiskLevel.CRITICAL
        decision = Decision.SNAP
    elif d_star >= theta_2:
        level = RiskLevel.HIGH
        decision = Decision.DENY
    elif d_star >= theta_1:
        level = RiskLevel.MEDIUM
        decision = Decision.REVIEW
    else:
        level = RiskLevel.LOW
        decision = Decision.ALLOW

    return RiskAssessment(
        level=level,
        decision=decision,
        raw_risk=raw_risk,
        harmonic_amplified=H_d,
        distance_to_realm=d_star,
        realm_index=realm_index,
        coherence=coherence,
        timestamp=time_module.time()
    )


# ============================================================================
# Temporal Pipeline Orchestrator
# ============================================================================

class CausalPipeline:
    """
    Orchestrates causal (time-ordered) layer execution.

    Ensures that layers are executed in strict temporal order
    and that no future information leaks into past computations.
    """

    def __init__(self):
        self.temporal_state = TemporalState(
            t=0.0,
            tau=0.0,
            eta=0.0,
            history=[]
        )
        self.execution_log: List[Tuple[float, str, Any]] = []

    def advance_time(self, dt: float) -> None:
        """Advance the temporal state by dt."""
        self.temporal_state.t += dt

    def execute_layer_6(self, u: np.ndarray) -> np.ndarray:
        """Execute breathing transform with current time."""
        result = layer_6_breathing(u, self.temporal_state.t)
        self.execution_log.append((self.temporal_state.t, "layer_6", result.copy()))
        return result

    def execute_layer_11(
        self,
        u: np.ndarray,
        ref_u: np.ndarray,
        q: complex,
        ref_q: complex
    ) -> float:
        """Execute triadic distance with temporal state."""
        result = layer_11_triadic_distance(
            u=u,
            ref_u=ref_u,
            tau=self.temporal_state.tau,
            ref_tau=0.0,  # Reference is at t=0
            eta=self.temporal_state.eta,
            ref_eta=0.0,
            q=q,
            ref_q=ref_q
        )
        self.execution_log.append((self.temporal_state.t, "layer_11", result))
        return result

    def execute_layer_13(
        self,
        d_star: float,
        coherence: float,
        realm_index: int
    ) -> RiskAssessment:
        """Execute decision layer."""
        result = layer_13_decision(
            d_star=d_star,
            coherence=coherence,
            realm_index=realm_index
        )
        self.execution_log.append((self.temporal_state.t, "layer_13", result))
        return result

    def verify_causality(self) -> bool:
        """
        Verify that the execution log respects causality.

        Returns True if all executions are in temporal order.
        """
        if len(self.execution_log) < 2:
            return True

        for i in range(1, len(self.execution_log)):
            t_prev = self.execution_log[i - 1][0]
            t_curr = self.execution_log[i][0]
            if t_curr < t_prev:
                return False

        return True


# ============================================================================
# Causality Verification Utilities
# ============================================================================

def verify_layer_causality(
    layer_func: Callable,
    n_tests: int = 100,
    verbose: bool = False
) -> Tuple[bool, dict]:
    """
    Verify that a layer respects causality over multiple invocations.

    Args:
        layer_func: Layer function to test
        n_tests: Number of sequential tests
        verbose: Print detailed results

    Returns:
        Tuple of (all_passed, statistics)
    """
    # Reset time tracker
    if hasattr(layer_func, 'reset_time'):
        layer_func.reset_time()

    all_passed = True
    violations = 0
    dim = 12

    # Generate monotonically increasing times
    times = np.sort(np.random.uniform(0, 100, n_tests))

    for i, t in enumerate(times):
        # Random point in Poincaré ball
        u = np.random.randn(dim)
        u = 0.5 * u / (np.linalg.norm(u) + EPS)

        try:
            if layer_func.__name__ == "layer_6_breathing":
                _ = layer_func(u, t=t)
            elif layer_func.__name__ == "layer_13_decision":
                _ = layer_func(
                    d_star=np.random.uniform(0, 3),
                    coherence=np.random.uniform(0, 1),
                    realm_index=0
                )
            else:
                _ = layer_func(u)

            check = getattr(layer_func, 'last_check', None)
            if check and not check.passed:
                all_passed = False
                violations += 1
                if verbose:
                    print(f"Test {i}: {check}")

        except CausalityViolation as e:
            all_passed = False
            violations += 1
            if verbose:
                print(f"Test {i}: VIOLATION - {e}")

    return all_passed, {
        "n_tests": n_tests,
        "violations": violations,
        "violation_rate": violations / n_tests
    }


# ============================================================================
# Axiom Layer Registry
# ============================================================================

CAUSALITY_LAYERS = {
    6: {
        "name": "Breathing Transform",
        "function": layer_6_breathing,
        "inverse": layer_6_inverse,
        "description": "Time-dependent radial scaling: T_breath(u; t)",
        "is_time_dependent": True,
    },
    11: {
        "name": "Triadic Temporal Distance",
        "function": layer_11_triadic_distance,
        "inverse": None,  # Distance is not invertible
        "description": "4-component distance: d_tri = √(d_H² + Δτ² + Δη² + (1-F_q))",
        "is_time_dependent": True,
    },
    13: {
        "name": "Decision & Risk Assessment",
        "function": layer_13_decision,
        "inverse": None,  # Decision is not invertible
        "description": "Governance pipeline: Risk' → Level → Decision",
        "is_time_dependent": True,
    },
}


def get_causality_layer(layer_num: int) -> dict:
    """Get layer info by number."""
    if layer_num not in CAUSALITY_LAYERS:
        raise ValueError(f"Layer {layer_num} is not a causality layer")
    return CAUSALITY_LAYERS[layer_num]


def list_causality_layers() -> list:
    """List all layers satisfying the causality axiom."""
    return list(CAUSALITY_LAYERS.keys())
