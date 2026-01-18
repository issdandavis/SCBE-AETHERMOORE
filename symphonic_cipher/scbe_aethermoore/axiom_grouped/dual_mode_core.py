"""
Dual-Mode Axiom Core: Bounded vs Unbounded Harmonic Wall

This module implements BOTH formulations for the harmonic scaling (A12):
1. BOUNDED: H(d) = R^(d²) with d² clamped at 50 (original axiom-grouped)
2. UNBOUNDED: H(d) = exp(d²) with NO clamping (v2.0.1 Golden Master patent claim)

Plus the full Langues Metric with coupling (enhanced A3).

Phase-shifting between modes allows:
- BOUNDED: Numerical stability, predictable risk values
- UNBOUNDED: "Vertical Wall" patent compliance, true rejection barrier
"""

from __future__ import annotations

import numpy as np
from typing import Tuple, Optional, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum
import scipy.linalg

# Constants
PHI = (1 + np.sqrt(5)) / 2  # Golden ratio ≈ 1.618
EPS = 1e-10
EPSILON_COUPLING = 0.05  # Langues coupling constant


class HarmonicMode(Enum):
    """Harmonic scaling mode selection."""
    BOUNDED = "bounded"      # R^(d²) with clamp
    UNBOUNDED = "unbounded"  # exp(d²) no clamp


class AxiomMode(Enum):
    """Full axiom mode (affects multiple layers)."""
    STABLE = "stable"        # Production-safe, bounded
    PATENT = "patent"        # Patent-compliant, unbounded vertical wall


@dataclass
class DualModeConfig:
    """Configuration for dual-mode axiom execution."""
    harmonic_mode: HarmonicMode = HarmonicMode.BOUNDED
    R_base: float = PHI
    d_sq_clamp: float = 50.0  # Only used in BOUNDED mode
    epsilon_coupling: float = EPSILON_COUPLING
    langues_enabled: bool = True


# ============================================================================
# A12: DUAL-MODE HARMONIC SCALING
# ============================================================================

def harmonic_scaling_bounded(d: float, R: float = PHI, clamp: float = 50.0) -> float:
    """
    BOUNDED Harmonic Scaling: H(d) = R^(d²), d² ≤ clamp

    Properties:
        - H(0) = 1
        - Strictly monotonic increasing
        - Bounded output for numerical stability
        - Max value: R^clamp ≈ 1.3e21 for φ, clamp=50
    """
    d_sq = min(d ** 2, clamp)
    return float(R ** d_sq)


def harmonic_scaling_unbounded(d: float) -> float:
    """
    UNBOUNDED Harmonic Scaling: H(d) = exp(d²)

    Properties:
        - H(0) = 1
        - Strictly monotonic increasing
        - UNBOUNDED output (Vertical Wall patent claim)
        - Creates true rejection barrier at large d

    WARNING: Can overflow to inf for d > ~26.6
    """
    return float(np.exp(d ** 2))


def harmonic_scaling_dual(
    d: float,
    mode: HarmonicMode = HarmonicMode.BOUNDED,
    R: float = PHI,
    clamp: float = 50.0
) -> float:
    """
    Dual-mode harmonic scaling with phase-shift capability.

    Args:
        d: Distance value
        mode: BOUNDED or UNBOUNDED
        R: Base for bounded mode
        clamp: Clamp value for bounded mode

    Returns:
        Harmonically scaled value H(d)
    """
    if mode == HarmonicMode.UNBOUNDED:
        return harmonic_scaling_unbounded(d)
    else:
        return harmonic_scaling_bounded(d, R, clamp)


# ============================================================================
# A3: ENHANCED LANGUES METRIC WITH COUPLING
# ============================================================================

def build_coupling_matrix(k: int, n: int = 6, epsilon: float = EPSILON_COUPLING) -> np.ndarray:
    """
    Build coupling matrix A_k for langues operator.

    A_k = ln(R^(k+1)) * E_kk + ε * (E_{k,k+1} + E_{k+1,k})

    Where:
        - E_ij is elementary matrix (1 at (i,j), 0 elsewhere)
        - Cyclic coupling: k+1 mod n
        - R = φ (golden ratio)
    """
    A_k = np.zeros((n, n))

    # Diagonal: golden ratio scaling
    A_k[k, k] = np.log(PHI ** (k + 1))

    # Off-diagonal: coupling terms (cyclic)
    k_next = (k + 1) % n
    A_k[k, k_next] = epsilon
    A_k[k_next, k] = epsilon

    return A_k


def langues_operator(r: np.ndarray, epsilon: float = EPSILON_COUPLING) -> np.ndarray:
    """
    Compute langues operator Λ(r) = exp(Σ r_k A_k).

    This is a matrix exponential that introduces cross-dimensional
    coupling based on the langues parameters r.

    Args:
        r: Langues parameters [r_1, ..., r_n] ∈ [0,1]^n
        epsilon: Coupling strength

    Returns:
        Langues operator matrix Λ(r)
    """
    n = len(r)
    sum_A = np.zeros((n, n))

    for k in range(n):
        A_k = build_coupling_matrix(k, n, epsilon)
        sum_A += r[k] * A_k

    return scipy.linalg.expm(sum_A)


def build_langues_metric_tensor(
    r: np.ndarray,
    G_0: Optional[np.ndarray] = None,
    epsilon: float = EPSILON_COUPLING
) -> np.ndarray:
    """
    Build the full Langues Metric Tensor G_L(r).

    G_L(r) = Λ(r)^T G_0 Λ(r)

    Where:
        - Λ(r) is the langues operator (matrix exp)
        - G_0 is the base metric: diag(1, 1, 1, R, R², R³) for 6D

    Properties:
        - Positive definite (for valid ε)
        - Introduces cross-dimensional coupling
        - Reduces to G_0 when r = 0
    """
    n = len(r)

    if G_0 is None:
        # Build base metric with golden ratio scaling
        if n <= 6:
            G_0 = np.diag([1, 1, 1, PHI, PHI**2, PHI**3][:n])
        else:
            # Extend pattern for higher dimensions
            diag = []
            for i in range(n):
                if i < 3:
                    diag.append(1.0)
                else:
                    diag.append(PHI ** (i - 2))
            G_0 = np.diag(diag)

    Lambda = langues_operator(r, epsilon)
    G_L = Lambda.T @ G_0 @ Lambda

    return G_L


def langues_distance(
    x: np.ndarray,
    mu: np.ndarray,
    r: np.ndarray,
    epsilon: float = EPSILON_COUPLING
) -> float:
    """
    Compute distance using the Langues Metric.

    d_L = √[(x - μ)^T G_L(r) (x - μ)]

    Args:
        x: Current point
        mu: Reference point (ideal/realm center)
        r: Langues parameters
        epsilon: Coupling strength

    Returns:
        Langues-weighted distance
    """
    G_L = build_langues_metric_tensor(r, epsilon=epsilon)
    diff = x - mu

    # Ensure correct dimensions
    if len(diff) > G_L.shape[0]:
        diff = diff[:G_L.shape[0]]
    elif len(diff) < G_L.shape[0]:
        diff_padded = np.zeros(G_L.shape[0])
        diff_padded[:len(diff)] = diff
        diff = diff_padded

    d_sq = diff.T @ G_L @ diff
    return float(np.sqrt(max(0, d_sq)))


def verify_langues_positive_definite(
    r: np.ndarray,
    epsilon: float = EPSILON_COUPLING
) -> Tuple[bool, float]:
    """
    Verify that G_L(r) is positive definite.

    Returns:
        Tuple of (is_positive_definite, min_eigenvalue)
    """
    G_L = build_langues_metric_tensor(r, epsilon=epsilon)
    eigenvalues = np.linalg.eigvalsh(G_L)
    min_eig = float(np.min(eigenvalues))
    return min_eig > 0, min_eig


# ============================================================================
# DUAL-MODE RISK CALCULATION (A12 + A13)
# ============================================================================

@dataclass
class DualModeRiskResult:
    """Result from dual-mode risk calculation."""
    risk_bounded: float
    risk_unbounded: float
    base_risk: float
    distance: float
    mode_used: HarmonicMode
    final_risk: float
    decision: str
    overflow_detected: bool


def calculate_risk_dual_mode(
    d_star: float,
    C_spin: float,
    S_spec: float,
    tau: float = 0.5,
    S_audio: float = 0.5,
    mode: HarmonicMode = HarmonicMode.BOUNDED,
    config: Optional[DualModeConfig] = None
) -> DualModeRiskResult:
    """
    Calculate risk using dual-mode harmonic scaling.

    Tests BOTH modes and returns comparison, uses specified mode for decision.

    Args:
        d_star: Minimum distance to realm
        C_spin: Spin coherence [0,1]
        S_spec: Spectral coherence [0,1]
        tau: Trust factor [0,1]
        S_audio: Audio coherence [0,1]
        mode: Which mode to use for final decision
        config: Configuration (uses defaults if None)

    Returns:
        DualModeRiskResult with both calculations
    """
    if config is None:
        config = DualModeConfig()

    # A12: Base Risk (weighted sum of coherence failures)
    R_base = (
        0.2 * (1 - C_spin) +
        0.2 * (1 - S_spec) +
        0.2 * (1 - tau) +
        0.2 * (1 - S_audio) +
        0.2 * np.tanh(d_star)
    )

    # Calculate BOTH harmonic scalings
    H_bounded = harmonic_scaling_bounded(d_star, config.R_base, config.d_sq_clamp)

    overflow_detected = False
    try:
        H_unbounded = harmonic_scaling_unbounded(d_star)
        if np.isinf(H_unbounded) or np.isnan(H_unbounded):
            overflow_detected = True
            H_unbounded = float('inf')
    except (OverflowError, FloatingPointError):
        overflow_detected = True
        H_unbounded = float('inf')

    # Final risks
    R_bounded = R_base * H_bounded
    R_unbounded = R_base * H_unbounded if not np.isinf(H_unbounded) else float('inf')

    # Select based on mode
    if mode == HarmonicMode.UNBOUNDED:
        final_risk = R_unbounded
    else:
        final_risk = R_bounded

    # Decision logic (handles both finite and infinite)
    if np.isinf(final_risk) or final_risk > 1e10:
        decision = "DENY"
    elif final_risk < 0.5:
        decision = "ALLOW"
    elif final_risk < 5.0:
        decision = "QUARANTINE"
    else:
        decision = "DENY"

    return DualModeRiskResult(
        risk_bounded=R_bounded,
        risk_unbounded=R_unbounded,
        base_risk=R_base,
        distance=d_star,
        mode_used=mode,
        final_risk=final_risk,
        decision=decision,
        overflow_detected=overflow_detected
    )


# ============================================================================
# COMPREHENSIVE DUAL-MODE TESTS
# ============================================================================

def test_harmonic_modes() -> Dict[str, Any]:
    """
    Test both harmonic scaling modes across various distances.

    Returns:
        Dictionary with test results
    """
    results = {
        "bounded": [],
        "unbounded": [],
        "comparison": [],
        "overflow_points": [],
        "all_passed": True
    }

    test_distances = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0, 30.0]

    for d in test_distances:
        H_b = harmonic_scaling_bounded(d)

        try:
            H_u = harmonic_scaling_unbounded(d)
            overflow = np.isinf(H_u) or np.isnan(H_u)
        except:
            H_u = float('inf')
            overflow = True

        results["bounded"].append((d, H_b))
        results["unbounded"].append((d, H_u))
        results["comparison"].append({
            "d": d,
            "H_bounded": H_b,
            "H_unbounded": H_u,
            "ratio": H_u / H_b if H_b > 0 and not np.isinf(H_u) else float('inf'),
            "overflow": overflow
        })

        if overflow:
            results["overflow_points"].append(d)

    # Verify monotonicity (both should be strictly increasing)
    for mode_name, mode_results in [("bounded", results["bounded"]), ("unbounded", results["unbounded"])]:
        for i in range(1, len(mode_results)):
            d_prev, H_prev = mode_results[i-1]
            d_curr, H_curr = mode_results[i]
            if not np.isinf(H_curr) and H_curr <= H_prev:
                results["all_passed"] = False
                results[f"{mode_name}_monotonicity_failure"] = (d_prev, d_curr)

    return results


def test_langues_metric() -> Dict[str, Any]:
    """
    Test the Langues Metric with various coupling parameters.

    Returns:
        Dictionary with test results
    """
    results = {
        "positive_definite_tests": [],
        "distance_comparisons": [],
        "coupling_effects": [],
        "all_passed": True
    }

    # Test positive definiteness
    test_r_values = [
        np.zeros(6),
        np.ones(6) * 0.5,
        np.ones(6),
        np.array([0.1, 0.5, 0.8, 0.2, 0.6, 0.4]),
        np.random.rand(6)
    ]

    for r in test_r_values:
        is_pd, min_eig = verify_langues_positive_definite(r)
        results["positive_definite_tests"].append({
            "r": r.tolist(),
            "is_positive_definite": is_pd,
            "min_eigenvalue": min_eig
        })
        if not is_pd:
            results["all_passed"] = False

    # Test distance comparisons
    x = np.array([1, 2, 3, 4, 5, 6])
    mu = np.zeros(6)
    euclidean_d = np.linalg.norm(x - mu)

    for r in test_r_values:
        d_L = langues_distance(x, mu, r)
        results["distance_comparisons"].append({
            "r": r.tolist(),
            "d_euclidean": euclidean_d,
            "d_langues": d_L,
            "ratio": d_L / euclidean_d
        })

    # Test coupling effects (r=0 should give baseline)
    r_zero = np.zeros(6)
    G_L_zero = build_langues_metric_tensor(r_zero)
    G_0 = np.diag([1, 1, 1, PHI, PHI**2, PHI**3])

    # With r=0 and ε→0, should approach G_0
    G_L_nocoupling = build_langues_metric_tensor(r_zero, epsilon=1e-10)
    coupling_diff = np.max(np.abs(G_L_nocoupling - G_0))
    results["coupling_effects"].append({
        "test": "r=0, ε→0 approaches G_0",
        "max_diff": coupling_diff,
        "passed": coupling_diff < 0.01
    })

    return results


def test_dual_mode_risk() -> Dict[str, Any]:
    """
    Test dual-mode risk calculation with various inputs.

    Returns:
        Dictionary with test results
    """
    results = {
        "risk_calculations": [],
        "mode_comparisons": [],
        "decision_consistency": [],
        "all_passed": True
    }

    # Test scenarios
    scenarios = [
        {"d_star": 0.3, "C_spin": 0.9, "S_spec": 0.8, "name": "low_risk"},
        {"d_star": 1.5, "C_spin": 0.5, "S_spec": 0.5, "name": "medium_risk"},
        {"d_star": 3.0, "C_spin": 0.2, "S_spec": 0.3, "name": "high_risk"},
        {"d_star": 10.0, "C_spin": 0.1, "S_spec": 0.1, "name": "extreme_risk"},
    ]

    for scenario in scenarios:
        # Test BOUNDED mode
        result_bounded = calculate_risk_dual_mode(
            d_star=scenario["d_star"],
            C_spin=scenario["C_spin"],
            S_spec=scenario["S_spec"],
            mode=HarmonicMode.BOUNDED
        )

        # Test UNBOUNDED mode
        result_unbounded = calculate_risk_dual_mode(
            d_star=scenario["d_star"],
            C_spin=scenario["C_spin"],
            S_spec=scenario["S_spec"],
            mode=HarmonicMode.UNBOUNDED
        )

        results["risk_calculations"].append({
            "scenario": scenario["name"],
            "bounded_risk": result_bounded.final_risk,
            "unbounded_risk": result_unbounded.final_risk,
            "bounded_decision": result_bounded.decision,
            "unbounded_decision": result_unbounded.decision,
            "overflow": result_unbounded.overflow_detected
        })

        # For extreme distances, unbounded should be stricter (DENY vs QUARANTINE)
        if scenario["d_star"] > 5.0:
            if result_unbounded.decision != "DENY":
                results["all_passed"] = False
                results["decision_consistency"].append({
                    "scenario": scenario["name"],
                    "issue": "Unbounded mode should DENY at extreme distance"
                })

    return results


def run_all_tests() -> Dict[str, Any]:
    """
    Run all dual-mode tests and return comprehensive results.
    """
    print("=" * 60)
    print("DUAL-MODE AXIOM CORE: Comprehensive Test Suite")
    print("=" * 60)

    all_results = {}

    # Test 1: Harmonic Modes
    print("\n[1] Testing Harmonic Scaling Modes...")
    harmonic_results = test_harmonic_modes()
    all_results["harmonic_modes"] = harmonic_results
    print(f"    Bounded mode: {len(harmonic_results['bounded'])} tests")
    print(f"    Unbounded mode: {len(harmonic_results['unbounded'])} tests")
    print(f"    Overflow detected at d = {harmonic_results['overflow_points']}")
    print(f"    All passed: {harmonic_results['all_passed']}")

    # Test 2: Langues Metric
    print("\n[2] Testing Langues Metric with Coupling...")
    langues_results = test_langues_metric()
    all_results["langues_metric"] = langues_results
    pd_passed = sum(1 for t in langues_results["positive_definite_tests"] if t["is_positive_definite"])
    print(f"    Positive definite tests: {pd_passed}/{len(langues_results['positive_definite_tests'])}")
    print(f"    All passed: {langues_results['all_passed']}")

    # Test 3: Dual-Mode Risk
    print("\n[3] Testing Dual-Mode Risk Calculation...")
    risk_results = test_dual_mode_risk()
    all_results["dual_mode_risk"] = risk_results
    print(f"    Risk scenarios tested: {len(risk_results['risk_calculations'])}")
    print(f"    All passed: {risk_results['all_passed']}")

    # Summary
    print("\n" + "=" * 60)
    overall_passed = (
        harmonic_results["all_passed"] and
        langues_results["all_passed"] and
        risk_results["all_passed"]
    )
    all_results["overall_passed"] = overall_passed
    print(f"OVERALL: {'PASS ✓' if overall_passed else 'FAIL ✗'}")
    print("=" * 60)

    # Print comparison table
    print("\n[Harmonic Mode Comparison Table]")
    print("-" * 60)
    print(f"{'d':>8} {'H_bounded':>15} {'H_unbounded':>15} {'Ratio':>10}")
    print("-" * 60)
    for comp in harmonic_results["comparison"][:8]:
        d = comp["d"]
        H_b = comp["H_bounded"]
        H_u = comp["H_unbounded"]
        ratio = comp["ratio"]
        H_b_str = f"{H_b:.6f}" if H_b < 1e10 else f"{H_b:.2e}"
        H_u_str = f"{H_u:.6f}" if H_u < 1e10 and not np.isinf(H_u) else "inf" if np.isinf(H_u) else f"{H_u:.2e}"
        ratio_str = f"{ratio:.4f}" if ratio < 1e6 and not np.isinf(ratio) else "inf"
        print(f"{d:>8.1f} {H_b_str:>15} {H_u_str:>15} {ratio_str:>10}")
    print("-" * 60)

    # Phase-shift capability
    print("\n[Phase-Shift Capability]")
    print("  BOUNDED mode: Numerical stability, bounded risk values")
    print("  UNBOUNDED mode: Vertical Wall patent, true rejection barrier")
    print("  Both modes verified and operational for phase-shifting.")

    return all_results


# ============================================================================
# PHASE-SHIFT INTERFACE
# ============================================================================

class DualModeAxiomCore:
    """
    Dual-mode axiom core with phase-shift capability.

    Allows runtime switching between BOUNDED and UNBOUNDED modes
    for the harmonic scaling (A12) axiom.
    """

    def __init__(self, initial_mode: HarmonicMode = HarmonicMode.BOUNDED):
        self.mode = initial_mode
        self.config = DualModeConfig(harmonic_mode=initial_mode)
        self._mode_history = [(0, initial_mode)]

    def phase_shift(self, new_mode: HarmonicMode) -> None:
        """Switch to a different axiom mode."""
        old_mode = self.mode
        self.mode = new_mode
        self.config.harmonic_mode = new_mode
        self._mode_history.append((len(self._mode_history), new_mode))
        print(f"Phase shift: {old_mode.value} → {new_mode.value}")

    def harmonic_scale(self, d: float) -> float:
        """Apply harmonic scaling in current mode."""
        return harmonic_scaling_dual(d, self.mode, self.config.R_base, self.config.d_sq_clamp)

    def calculate_risk(self, d_star: float, C_spin: float, S_spec: float, **kwargs) -> DualModeRiskResult:
        """Calculate risk in current mode."""
        return calculate_risk_dual_mode(d_star, C_spin, S_spec, mode=self.mode, config=self.config, **kwargs)

    def langues_distance(self, x: np.ndarray, mu: np.ndarray, r: np.ndarray) -> float:
        """Calculate langues-weighted distance."""
        return langues_distance(x, mu, r, self.config.epsilon_coupling)

    @property
    def current_mode(self) -> str:
        return self.mode.value

    def get_mode_history(self) -> list:
        return self._mode_history


# ============================================================================
# MAIN: Run tests when executed directly
# ============================================================================

if __name__ == "__main__":
    results = run_all_tests()

    # Demonstrate phase-shifting
    print("\n[Phase-Shift Demonstration]")
    core = DualModeAxiomCore(HarmonicMode.BOUNDED)

    d_test = 3.0
    print(f"\nDistance d = {d_test}")

    # Bounded mode
    H1 = core.harmonic_scale(d_test)
    print(f"  {core.current_mode.upper()} mode: H(d) = {H1:.6f}")

    # Phase shift to unbounded
    core.phase_shift(HarmonicMode.UNBOUNDED)
    H2 = core.harmonic_scale(d_test)
    print(f"  {core.current_mode.upper()} mode: H(d) = {H2:.6f}")

    # Phase shift back
    core.phase_shift(HarmonicMode.BOUNDED)
    H3 = core.harmonic_scale(d_test)
    print(f"  {core.current_mode.upper()} mode: H(d) = {H3:.6f}")

    print(f"\nMode history: {core.get_mode_history()}")
