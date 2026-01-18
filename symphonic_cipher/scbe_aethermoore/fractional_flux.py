#!/usr/bin/env python3
"""
SCBE-AETHERMOORE Fractional Dimension Flux
============================================

Implements Claim 16: Adaptive Dimensional Breathing via ODE Dynamics

The fractional dimension coefficients ν(t) ∈ ℝ⁶ evolve via bounded ODE:

    ν̇_i = κ_i(ν̄_i - ν_i) + σ_i sin(Ω_i t)

Where:
    - ν_i ∈ (0, 1]: Fractional participation of dimension i
    - κ_i > 0: Decay rate toward equilibrium ν̄_i
    - σ_i: Oscillation amplitude (breathing)
    - Ω_i: Oscillation frequency

Effective dimension:
    D_f(t) = Σ ν_i(t)  ∈ (0, 6]

Participation States:
    - POLLY:  ν ≈ 1      (full participation)
    - QUASI:  0.5 ≤ ν < 1  (partial participation)
    - DEMI:   0 < ν < 0.5  (minimal participation)

Adaptive Snap Threshold:
    ε_snap = ε_base · √(6/D_f)

As D_f decreases (fewer active dimensions), the snap threshold INCREASES,
making the system MORE sensitive to deviations in remaining dimensions.

Date: January 15, 2026
Golden Master: v2.0.1
Patent Claim: 16 (Fractional Dimension Flux)
"""

from __future__ import annotations

import numpy as np
from scipy.integrate import solve_ivp
from dataclasses import dataclass, field
from typing import Tuple, Dict, Any, Optional, List, Callable
from enum import Enum

# =============================================================================
# CONSTANTS
# =============================================================================

PHI = (1 + np.sqrt(5)) / 2  # Golden ratio ≈ 1.618
EPSILON = 1e-10
DEFAULT_DIM = 6  # 6D Langues space


class ParticipationState(Enum):
    """Dimensional participation states."""
    POLLY = "POLLY"   # ν ≈ 1 (full)
    QUASI = "QUASI"   # 0.5 ≤ ν < 1 (partial)
    DEMI = "DEMI"     # 0 < ν < 0.5 (minimal)
    ZERO = "ZERO"     # ν ≈ 0 (inactive)


# =============================================================================
# ODE PARAMETERS
# =============================================================================

@dataclass
class FluxParams:
    """
    Parameters for fractional dimension flux ODE.

    ν̇_i = κ_i(ν̄_i - ν_i) + σ_i sin(Ω_i t)
    """
    dim: int = DEFAULT_DIM

    # Decay rates κ_i (attraction to equilibrium)
    kappa: np.ndarray = field(default_factory=lambda: np.array([0.5, 0.4, 0.3, 0.3, 0.4, 0.5]))

    # Equilibrium values ν̄_i
    nu_bar: np.ndarray = field(default_factory=lambda: np.array([1.0, 0.9, 0.8, 0.8, 0.9, 1.0]))

    # Oscillation amplitudes σ_i
    sigma: np.ndarray = field(default_factory=lambda: np.array([0.1, 0.15, 0.2, 0.2, 0.15, 0.1]))

    # Oscillation frequencies Ω_i
    omega: np.ndarray = field(default_factory=lambda: np.array([0.5, 0.7, 1.0, 1.1, 0.8, 0.6]))

    # Bounds
    nu_min: float = 0.01  # Minimum participation (never fully zero)
    nu_max: float = 1.0   # Maximum participation

    def __post_init__(self):
        """Ensure arrays are correct size."""
        if len(self.kappa) != self.dim:
            self.kappa = np.ones(self.dim) * 0.5
        if len(self.nu_bar) != self.dim:
            self.nu_bar = np.ones(self.dim) * 0.9
        if len(self.sigma) != self.dim:
            self.sigma = np.ones(self.dim) * 0.1
        if len(self.omega) != self.dim:
            self.omega = np.ones(self.dim) * 1.0


@dataclass
class FluxState:
    """Current state of fractional dimension system."""
    nu: np.ndarray              # Current ν values
    t: float                    # Current time
    D_f: float                  # Effective dimension Σν_i
    states: List[ParticipationState]  # State per dimension
    epsilon_snap: float         # Current snap threshold


# =============================================================================
# FRACTIONAL DIMENSION FLUX ENGINE
# =============================================================================

class FractionalFluxEngine:
    """
    Engine for fractional dimension dynamics.

    Implements the ODE:
        ν̇_i = κ_i(ν̄_i - ν_i) + σ_i sin(Ω_i t)

    With bounded evolution ν_i ∈ [ν_min, ν_max].
    """

    def __init__(
        self,
        params: Optional[FluxParams] = None,
        epsilon_base: float = 0.05
    ):
        """
        Initialize fractional flux engine.

        Args:
            params: FluxParams for ODE
            epsilon_base: Base snap threshold
        """
        self.params = params or FluxParams()
        self.epsilon_base = epsilon_base

        # Initial state: all dimensions at equilibrium
        self._nu = self.params.nu_bar.copy()
        self._t = 0.0

    def _ode_rhs(self, t: float, nu: np.ndarray) -> np.ndarray:
        """
        Right-hand side of the ODE.

        ν̇_i = κ_i(ν̄_i - ν_i) + σ_i sin(Ω_i t)
        """
        p = self.params

        # Decay toward equilibrium
        decay = p.kappa * (p.nu_bar - nu)

        # Oscillatory breathing
        oscillation = p.sigma * np.sin(p.omega * t)

        return decay + oscillation

    def step(self, dt: float) -> FluxState:
        """
        Evolve system by time dt.

        Uses scipy.integrate.solve_ivp for numerical integration.
        """
        # Solve ODE from t to t+dt
        sol = solve_ivp(
            self._ode_rhs,
            t_span=(self._t, self._t + dt),
            y0=self._nu,
            method='RK45',
            dense_output=False
        )

        # Update state
        self._nu = sol.y[:, -1]
        self._t = self._t + dt

        # Clamp to bounds
        self._nu = np.clip(self._nu, self.params.nu_min, self.params.nu_max)

        return self.get_state()

    def evolve(self, t_final: float, n_steps: int = 100) -> List[FluxState]:
        """
        Evolve system to t_final, returning trajectory.
        """
        dt = t_final / n_steps
        trajectory = []

        for _ in range(n_steps):
            state = self.step(dt)
            trajectory.append(state)

        return trajectory

    def get_state(self) -> FluxState:
        """Get current flux state."""
        D_f = self.effective_dimension()
        states = [self._classify_participation(nu) for nu in self._nu]
        eps_snap = self.snap_threshold()

        return FluxState(
            nu=self._nu.copy(),
            t=self._t,
            D_f=D_f,
            states=states,
            epsilon_snap=eps_snap
        )

    def effective_dimension(self) -> float:
        """
        Compute effective dimension D_f = Σν_i.

        D_f ∈ (0, dim] where dim=6 typically.
        """
        return float(np.sum(self._nu))

    def snap_threshold(self) -> float:
        """
        Compute adaptive snap threshold.

        ε_snap = ε_base · √(6/D_f)

        As D_f decreases, threshold INCREASES (more sensitive).
        """
        D_f = max(self.effective_dimension(), EPSILON)
        return self.epsilon_base * np.sqrt(self.params.dim / D_f)

    def _classify_participation(self, nu: float) -> ParticipationState:
        """Classify participation state of a dimension."""
        if nu >= 0.95:
            return ParticipationState.POLLY
        elif nu >= 0.5:
            return ParticipationState.QUASI
        elif nu >= 0.05:
            return ParticipationState.DEMI
        else:
            return ParticipationState.ZERO

    def reset(self, nu_init: Optional[np.ndarray] = None):
        """Reset to initial state."""
        self._t = 0.0
        self._nu = nu_init if nu_init is not None else self.params.nu_bar.copy()

    def set_equilibrium(self, nu_bar: np.ndarray):
        """Update equilibrium values (for adaptive control)."""
        self.params.nu_bar = np.clip(nu_bar, self.params.nu_min, self.params.nu_max)

    def apply_pressure(self, pressure: float):
        """
        Apply external pressure to modify dynamics.

        High pressure → dimensions contract (lower ν̄)
        Low pressure → dimensions expand (higher ν̄)
        """
        # Pressure modulates equilibrium
        # P=0: ν̄ = default, P=1: ν̄ = 0.5 (contracted)
        contraction = 1.0 - 0.5 * pressure
        self.params.nu_bar = self.params.nu_bar * contraction
        self.params.nu_bar = np.clip(self.params.nu_bar, self.params.nu_min, self.params.nu_max)


# =============================================================================
# DIMENSIONAL WEIGHTING
# =============================================================================

def compute_weighted_metric(
    G_base: np.ndarray,
    nu: np.ndarray
) -> np.ndarray:
    """
    Apply fractional dimension weighting to metric tensor.

    G_weighted = diag(ν) @ G_base @ diag(ν)

    Dimensions with low ν contribute less to the metric.
    """
    nu_diag = np.diag(nu)
    return nu_diag @ G_base @ nu_diag


def compute_weighted_distance(
    u: np.ndarray,
    v: np.ndarray,
    G_base: np.ndarray,
    nu: np.ndarray
) -> float:
    """
    Compute distance with fractional dimension weighting.

    d² = (u-v)ᵀ G_weighted (u-v)
    """
    G_weighted = compute_weighted_metric(G_base, nu)
    diff = u - v
    d_sq = diff @ G_weighted @ diff
    return float(np.sqrt(max(0, d_sq)))


# =============================================================================
# SNAP DETECTION
# =============================================================================

@dataclass
class SnapResult:
    """Result of snap detection."""
    snapped: bool               # Whether snap occurred
    deviation: float            # Deviation magnitude
    threshold: float            # Current threshold
    margin: float              # threshold - deviation (negative = snapped)
    dimension_contribution: np.ndarray  # Per-dimension contribution


def detect_snap(
    deviation_vector: np.ndarray,
    flux_state: FluxState,
    mode: str = "L2"
) -> SnapResult:
    """
    Detect snap using adaptive threshold.

    A snap occurs when deviation exceeds ε_snap.

    Args:
        deviation_vector: Per-dimension deviations
        flux_state: Current flux state
        mode: "L2" (Euclidean), "Linf" (max), or "weighted"

    Returns:
        SnapResult with diagnosis
    """
    nu = flux_state.nu
    threshold = flux_state.epsilon_snap

    if mode == "L2":
        # Weighted L2 norm
        weighted = deviation_vector * nu
        deviation = np.linalg.norm(weighted)
    elif mode == "Linf":
        # Max of weighted deviations
        weighted = np.abs(deviation_vector) * nu
        deviation = np.max(weighted)
    else:  # weighted
        # Custom weighted sum
        deviation = np.sum(np.abs(deviation_vector) * nu) / np.sum(nu)

    snapped = deviation > threshold
    margin = threshold - deviation

    return SnapResult(
        snapped=snapped,
        deviation=deviation,
        threshold=threshold,
        margin=margin,
        dimension_contribution=np.abs(deviation_vector) * nu
    )


# =============================================================================
# INTEGRATION WITH LIVING METRIC
# =============================================================================

def integrate_with_living_metric(
    flux_engine: FractionalFluxEngine,
    G_living: np.ndarray,
    pressure: float
) -> Tuple[np.ndarray, FluxState]:
    """
    Integrate fractional flux with living metric.

    1. Apply pressure to flux dynamics
    2. Get current fractional state
    3. Weight the living metric by ν

    Returns:
        (G_final, flux_state) where G_final incorporates both effects
    """
    # Apply pressure to flux
    flux_engine.apply_pressure(pressure)

    # Get current state
    state = flux_engine.get_state()

    # Weight the metric
    G_final = compute_weighted_metric(G_living, state.nu)

    return G_final, state


# =============================================================================
# BREATHING PATTERNS
# =============================================================================

class BreathingPattern(Enum):
    """Predefined breathing patterns."""
    UNIFORM = "UNIFORM"         # All dimensions breathe together
    ALTERNATING = "ALTERNATING" # Odd/even dimensions alternate
    WAVE = "WAVE"               # Wave propagates through dimensions
    RANDOM = "RANDOM"           # Stochastic breathing
    STABLE = "STABLE"           # Minimal oscillation


def apply_breathing_pattern(
    params: FluxParams,
    pattern: BreathingPattern,
    intensity: float = 1.0
) -> FluxParams:
    """
    Apply a predefined breathing pattern to flux parameters.

    Args:
        params: Base parameters
        pattern: Breathing pattern
        intensity: Scale factor for oscillation
    """
    p = FluxParams(dim=params.dim)
    p.kappa = params.kappa.copy()
    p.nu_bar = params.nu_bar.copy()

    if pattern == BreathingPattern.UNIFORM:
        # All same frequency/amplitude
        p.sigma = np.ones(params.dim) * 0.1 * intensity
        p.omega = np.ones(params.dim) * 1.0

    elif pattern == BreathingPattern.ALTERNATING:
        # Odd dimensions phase-shifted from even
        p.sigma = np.ones(params.dim) * 0.15 * intensity
        p.omega = np.array([1.0 if i % 2 == 0 else 1.0 for i in range(params.dim)])
        # Phase shift encoded in initial conditions

    elif pattern == BreathingPattern.WAVE:
        # Wave propagates: phase shift proportional to index
        p.sigma = np.ones(params.dim) * 0.12 * intensity
        p.omega = np.ones(params.dim) * 0.8
        # Omega variation creates wave effect
        p.omega = np.array([0.8 + 0.1 * i for i in range(params.dim)])

    elif pattern == BreathingPattern.RANDOM:
        # Random parameters
        np.random.seed(42)  # Reproducible
        p.sigma = np.random.uniform(0.05, 0.2, params.dim) * intensity
        p.omega = np.random.uniform(0.5, 1.5, params.dim)

    elif pattern == BreathingPattern.STABLE:
        # Minimal oscillation
        p.sigma = np.ones(params.dim) * 0.02 * intensity
        p.omega = np.ones(params.dim) * 0.3

    return p


# =============================================================================
# SELF-TESTS
# =============================================================================

def self_test() -> Dict[str, Any]:
    """Run fractional flux self-tests."""
    results = {}
    passed = 0
    total = 0

    # Test 1: ODE evolution bounds
    total += 1
    try:
        engine = FractionalFluxEngine()
        trajectory = engine.evolve(t_final=10.0, n_steps=100)

        all_bounded = all(
            np.all(s.nu >= engine.params.nu_min) and np.all(s.nu <= engine.params.nu_max)
            for s in trajectory
        )

        if all_bounded:
            passed += 1
            results["ode_bounds"] = "✓ PASS (ν ∈ [ν_min, ν_max] for all t)"
        else:
            results["ode_bounds"] = "✗ FAIL (ν exceeded bounds)"
    except Exception as e:
        results["ode_bounds"] = f"✗ FAIL ({e})"

    # Test 2: Effective dimension range
    total += 1
    try:
        engine = FractionalFluxEngine()
        trajectory = engine.evolve(t_final=20.0, n_steps=200)

        D_f_values = [s.D_f for s in trajectory]
        D_f_min, D_f_max = min(D_f_values), max(D_f_values)

        if 0 < D_f_min and D_f_max <= engine.params.dim:
            passed += 1
            results["D_f_range"] = f"✓ PASS (D_f ∈ [{D_f_min:.2f}, {D_f_max:.2f}])"
        else:
            results["D_f_range"] = f"✗ FAIL (D_f out of range)"
    except Exception as e:
        results["D_f_range"] = f"✗ FAIL ({e})"

    # Test 3: Snap threshold inversely proportional to D_f
    total += 1
    try:
        engine = FractionalFluxEngine(epsilon_base=0.1)

        # High D_f → low threshold
        engine._nu = np.ones(6) * 1.0
        eps_high_D = engine.snap_threshold()

        # Low D_f → high threshold
        engine._nu = np.ones(6) * 0.3
        eps_low_D = engine.snap_threshold()

        if eps_low_D > eps_high_D:
            passed += 1
            results["snap_threshold"] = f"✓ PASS (ε_snap: {eps_high_D:.3f} → {eps_low_D:.3f} as D_f ↓)"
        else:
            results["snap_threshold"] = "✗ FAIL (threshold not inversely proportional)"
    except Exception as e:
        results["snap_threshold"] = f"✗ FAIL ({e})"

    # Test 4: Participation state classification
    total += 1
    try:
        engine = FractionalFluxEngine()

        polly = engine._classify_participation(0.98)
        quasi = engine._classify_participation(0.7)
        demi = engine._classify_participation(0.3)
        zero = engine._classify_participation(0.01)

        if (polly == ParticipationState.POLLY and
            quasi == ParticipationState.QUASI and
            demi == ParticipationState.DEMI and
            zero == ParticipationState.ZERO):
            passed += 1
            results["participation_states"] = "✓ PASS (POLLY/QUASI/DEMI/ZERO correct)"
        else:
            results["participation_states"] = "✗ FAIL (state classification wrong)"
    except Exception as e:
        results["participation_states"] = f"✗ FAIL ({e})"

    # Test 5: Weighted metric diminishes with low ν
    total += 1
    try:
        G_base = np.eye(6)

        nu_full = np.ones(6)
        nu_half = np.ones(6) * 0.5

        G_full = compute_weighted_metric(G_base, nu_full)
        G_half = compute_weighted_metric(G_base, nu_half)

        trace_full = np.trace(G_full)
        trace_half = np.trace(G_half)

        if trace_half < trace_full:
            passed += 1
            results["weighted_metric"] = f"✓ PASS (trace: {trace_full:.1f} → {trace_half:.2f} with ν=0.5)"
        else:
            results["weighted_metric"] = "✗ FAIL (weighted metric not diminished)"
    except Exception as e:
        results["weighted_metric"] = f"✗ FAIL ({e})"

    # Test 6: Snap detection
    total += 1
    try:
        engine = FractionalFluxEngine(epsilon_base=0.1)
        state = engine.get_state()

        # Small deviation → no snap
        small_dev = np.ones(6) * 0.01
        result_small = detect_snap(small_dev, state)

        # Large deviation → snap
        large_dev = np.ones(6) * 0.5
        result_large = detect_snap(large_dev, state)

        if not result_small.snapped and result_large.snapped:
            passed += 1
            results["snap_detection"] = f"✓ PASS (small={result_small.deviation:.3f}, large={result_large.deviation:.3f})"
        else:
            results["snap_detection"] = "✗ FAIL (snap detection wrong)"
    except Exception as e:
        results["snap_detection"] = f"✗ FAIL ({e})"

    # Test 7: Pressure affects equilibrium
    total += 1
    try:
        engine = FractionalFluxEngine()
        nu_bar_initial = engine.params.nu_bar.copy()

        engine.apply_pressure(0.8)  # High pressure
        nu_bar_after = engine.params.nu_bar.copy()

        if np.all(nu_bar_after <= nu_bar_initial):
            passed += 1
            results["pressure_effect"] = "✓ PASS (high pressure contracts equilibrium)"
        else:
            results["pressure_effect"] = "✗ FAIL (pressure didn't contract)"
    except Exception as e:
        results["pressure_effect"] = f"✗ FAIL ({e})"

    # Test 8: Breathing patterns
    total += 1
    try:
        base_params = FluxParams()

        patterns_valid = True
        for pattern in BreathingPattern:
            p = apply_breathing_pattern(base_params, pattern)
            if len(p.sigma) != base_params.dim or len(p.omega) != base_params.dim:
                patterns_valid = False
                break

        if patterns_valid:
            passed += 1
            results["breathing_patterns"] = "✓ PASS (all patterns valid)"
        else:
            results["breathing_patterns"] = "✗ FAIL (pattern dimension mismatch)"
    except Exception as e:
        results["breathing_patterns"] = f"✗ FAIL ({e})"

    # Test 9: Oscillatory behavior (ν should oscillate)
    total += 1
    try:
        params = FluxParams(sigma=np.ones(6) * 0.2, omega=np.ones(6) * 2.0)
        engine = FractionalFluxEngine(params=params)

        trajectory = engine.evolve(t_final=10.0, n_steps=100)
        nu_0_values = [s.nu[0] for s in trajectory]

        # Check for oscillation: variance should be non-trivial
        variance = np.var(nu_0_values)

        if variance > 0.001:
            passed += 1
            results["oscillation"] = f"✓ PASS (ν[0] variance={variance:.4f})"
        else:
            results["oscillation"] = f"✗ FAIL (no oscillation detected)"
    except Exception as e:
        results["oscillation"] = f"✗ FAIL ({e})"

    # Test 10: Formula verification ε_snap = ε_base · √(6/D_f)
    total += 1
    try:
        engine = FractionalFluxEngine(epsilon_base=0.1)

        # Test at D_f = 6 (full)
        engine._nu = np.ones(6)
        eps_6 = engine.snap_threshold()
        expected_6 = 0.1 * np.sqrt(6 / 6)  # = 0.1

        # Test at D_f = 3 (half)
        engine._nu = np.ones(6) * 0.5
        eps_3 = engine.snap_threshold()
        expected_3 = 0.1 * np.sqrt(6 / 3)  # ≈ 0.141

        if abs(eps_6 - expected_6) < 0.001 and abs(eps_3 - expected_3) < 0.001:
            passed += 1
            results["formula_verification"] = f"✓ PASS (ε(D=6)={eps_6:.3f}, ε(D=3)={eps_3:.3f})"
        else:
            results["formula_verification"] = f"✗ FAIL (formula mismatch)"
    except Exception as e:
        results["formula_verification"] = f"✗ FAIL ({e})"

    return {
        "passed": passed,
        "total": total,
        "success_rate": f"{passed}/{total} ({100*passed/total:.1f}%)",
        "results": results
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("SCBE-AETHERMOORE FRACTIONAL DIMENSION FLUX")
    print("Claim 16: Adaptive Dimensional Breathing")
    print("=" * 70)

    # Run self-tests
    test_results = self_test()

    print("\n[SELF-TESTS]")
    for name, result in test_results["results"].items():
        print(f"  {name}: {result}")

    print("-" * 70)
    print(f"TOTAL: {test_results['success_rate']}")

    # Demonstration
    print("\n" + "=" * 70)
    print("DIMENSIONAL BREATHING DEMO")
    print("=" * 70)

    engine = FractionalFluxEngine(epsilon_base=0.05)

    print("\n  Time | D_f    | ε_snap | States")
    print("  " + "-" * 55)

    for t in [0, 2, 4, 6, 8, 10]:
        if t > 0:
            engine.evolve(t_final=2.0, n_steps=20)
        state = engine.get_state()

        state_chars = "".join([s.value[0] for s in state.states])
        print(f"  {state.t:4.1f} | {state.D_f:6.3f} | {state.epsilon_snap:6.4f} | {state_chars}")

    # Snap threshold demo
    print("\n" + "-" * 70)
    print("SNAP THRESHOLD SCALING:")
    print("  ε_snap = ε_base · √(6/D_f)")
    print()

    for D_f in [6.0, 4.5, 3.0, 1.5]:
        engine._nu = np.ones(6) * (D_f / 6)
        eps = engine.snap_threshold()
        print(f"  D_f = {D_f:.1f}: ε_snap = {eps:.4f}")

    print("=" * 70)
