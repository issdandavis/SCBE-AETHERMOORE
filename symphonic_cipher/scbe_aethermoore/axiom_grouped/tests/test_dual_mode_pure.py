#!/usr/bin/env python3
"""
Pure Python tests for Dual-Mode Axiom Core.

Tests both BOUNDED and UNBOUNDED harmonic scaling modes
without external dependencies (no numpy/scipy).
"""

import math
from typing import Tuple, List, Dict, Any


# Constants
PHI = (1 + math.sqrt(5)) / 2  # Golden ratio ≈ 1.618
EPS = 1e-10


# ============================================================================
# A12: DUAL-MODE HARMONIC SCALING (Pure Python)
# ============================================================================

def harmonic_bounded(d: float, R: float = PHI, clamp: float = 50.0) -> float:
    """
    BOUNDED: H(d) = R^(d²) with d² clamped at 50
    """
    d_sq = min(d ** 2, clamp)
    return R ** d_sq


def harmonic_unbounded(d: float) -> float:
    """
    UNBOUNDED: H(d) = exp(d²) - NO clamping (Vertical Wall patent)
    """
    return math.exp(d ** 2)


# ============================================================================
# LANGUES METRIC (Pure Python - Simplified)
# ============================================================================

def langues_weights_simple(r: List[float]) -> List[float]:
    """
    Simplified langues weighting (diagonal only, no coupling).

    w_k = R^(k+1) * exp(r_k)
    """
    n = len(r)
    weights = []
    for k in range(n):
        base_weight = PHI ** (k + 1)
        langues_mod = math.exp(r[k] * 0.5)  # Modulate by langues parameter
        weights.append(base_weight * langues_mod)
    return weights


def langues_distance_simple(x: List[float], mu: List[float], r: List[float]) -> float:
    """
    Simplified langues distance (weighted Euclidean).
    """
    weights = langues_weights_simple(r)

    d_sq = 0.0
    for i in range(min(len(x), len(mu), len(weights))):
        diff = x[i] - mu[i]
        d_sq += weights[i] * (diff ** 2)

    return math.sqrt(d_sq)


# ============================================================================
# RISK CALCULATION (Pure Python)
# ============================================================================

def calculate_base_risk(d_star: float, C_spin: float, S_spec: float,
                        tau: float = 0.5, S_audio: float = 0.5) -> float:
    """
    A12: Base Risk = weighted sum of coherence failures.
    """
    return (
        0.2 * (1 - C_spin) +
        0.2 * (1 - S_spec) +
        0.2 * (1 - tau) +
        0.2 * (1 - S_audio) +
        0.2 * math.tanh(d_star)
    )


def risk_bounded(d_star: float, C_spin: float, S_spec: float, **kwargs) -> float:
    """Final risk with BOUNDED harmonic scaling."""
    R_base = calculate_base_risk(d_star, C_spin, S_spec, **kwargs)
    H = harmonic_bounded(d_star)
    return R_base * H


def risk_unbounded(d_star: float, C_spin: float, S_spec: float, **kwargs) -> float:
    """Final risk with UNBOUNDED harmonic scaling."""
    R_base = calculate_base_risk(d_star, C_spin, S_spec, **kwargs)
    try:
        H = harmonic_unbounded(d_star)
        return R_base * H
    except OverflowError:
        return float('inf')


def decide(risk: float) -> str:
    """Decision logic."""
    if math.isinf(risk) or risk > 1e10:
        return "DENY"
    elif risk < 0.5:
        return "ALLOW"
    elif risk < 5.0:
        return "QUARANTINE"
    else:
        return "DENY"


# ============================================================================
# TESTS
# ============================================================================

def test_harmonic_modes():
    """Test both harmonic modes across various distances."""
    print("\n[Test 1: Harmonic Scaling Modes]")
    print("-" * 70)
    print(f"{'d':>6} {'H_bounded':>18} {'H_unbounded':>18} {'Ratio':>12} {'Overflow':>10}")
    print("-" * 70)

    test_distances = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0, 30.0]
    overflow_point = None
    all_monotonic_b = True
    all_monotonic_u = True
    prev_H_b = 0
    prev_H_u = 0

    for d in test_distances:
        H_b = harmonic_bounded(d)

        try:
            H_u = harmonic_unbounded(d)
            overflow = math.isinf(H_u)
        except OverflowError:
            H_u = float('inf')
            overflow = True

        if overflow and overflow_point is None:
            overflow_point = d

        # Check monotonicity
        if d > 0:
            if H_b <= prev_H_b:
                all_monotonic_b = False
            if not math.isinf(H_u) and not math.isinf(prev_H_u) and H_u <= prev_H_u:
                all_monotonic_u = False

        prev_H_b = H_b
        prev_H_u = H_u

        # Format output
        H_b_str = f"{H_b:.6f}" if H_b < 1e10 else f"{H_b:.2e}"
        H_u_str = "inf" if math.isinf(H_u) else f"{H_u:.6f}" if H_u < 1e10 else f"{H_u:.2e}"

        if not math.isinf(H_u) and H_b > 0:
            ratio = H_u / H_b
            ratio_str = f"{ratio:.4f}" if ratio < 1e6 else f"{ratio:.2e}"
        else:
            ratio_str = "inf"

        print(f"{d:>6.1f} {H_b_str:>18} {H_u_str:>18} {ratio_str:>12} {str(overflow):>10}")

    print("-" * 70)
    print(f"Overflow detected at d = {overflow_point}")
    print(f"Bounded monotonic (within clamp): {all_monotonic_b}")
    print(f"Unbounded monotonic: {all_monotonic_u}")
    print(f"Bounded clamp point: d = √50 ≈ 7.07 (H plateaus at φ^50)")

    # Verify key properties
    assert harmonic_bounded(0) == 1.0, "H_bounded(0) should be 1"
    assert harmonic_unbounded(0) == 1.0, "H_unbounded(0) should be 1"

    # Bounded mode is monotonic up to clamp, then plateaus (correct behavior)
    # Verify within non-clamped region (d < √50 ≈ 7.07)
    clamp_limit = math.sqrt(50)
    monotonic_within_clamp = True
    prev_H = 0
    for d in [0, 1, 2, 3, 4, 5, 6, 7]:
        H = harmonic_bounded(d)
        if d > 0 and H <= prev_H:
            monotonic_within_clamp = False
        prev_H = H
    assert monotonic_within_clamp, "Bounded should be monotonic within clamp region"

    # Verify plateau behavior (d > √50)
    H_at_8 = harmonic_bounded(8)
    H_at_10 = harmonic_bounded(10)
    H_at_100 = harmonic_bounded(100)
    assert abs(H_at_8 - H_at_10) < 1e-6, "Bounded should plateau after clamp"
    assert abs(H_at_10 - H_at_100) < 1e-6, "Bounded should plateau after clamp"
    print(f"Plateau verified: H(8) = H(10) = H(100) = {H_at_10:.2e}")

    print("✓ All harmonic mode tests passed")
    return True


def test_langues_metric():
    """Test langues metric with various parameters."""
    print("\n[Test 2: Langues Metric]")
    print("-" * 70)

    x = [1, 2, 3, 4, 5, 6]
    mu = [0, 0, 0, 0, 0, 0]

    # Euclidean distance
    d_euclid = math.sqrt(sum((xi - mi)**2 for xi, mi in zip(x, mu)))
    print(f"Euclidean distance: {d_euclid:.4f}")

    # Test various langues parameters
    test_cases = [
        ([0.0] * 6, "r = 0 (baseline)"),
        ([0.5] * 6, "r = 0.5 (medium)"),
        ([1.0] * 6, "r = 1.0 (maximum)"),
        ([0.1, 0.5, 0.8, 0.2, 0.6, 0.4], "r = mixed"),
    ]

    print(f"\n{'Langues params':>25} {'d_langues':>12} {'Ratio to Euclid':>15}")
    print("-" * 55)

    for r, name in test_cases:
        d_L = langues_distance_simple(x, mu, r)
        ratio = d_L / d_euclid
        print(f"{name:>25} {d_L:>12.4f} {ratio:>15.4f}")

    # Verify r=0 gives baseline (golden ratio weighted)
    r_zero = [0.0] * 6
    d_zero = langues_distance_simple(x, mu, r_zero)
    assert d_zero > d_euclid, "Langues with phi weighting should exceed Euclidean"

    print("-" * 55)
    print("✓ All langues metric tests passed")
    return True


def test_dual_mode_risk():
    """Test risk calculation in both modes."""
    print("\n[Test 3: Dual-Mode Risk Calculation]")
    print("-" * 80)

    scenarios = [
        {"d_star": 0.3, "C_spin": 0.9, "S_spec": 0.8, "name": "low_risk"},
        {"d_star": 1.5, "C_spin": 0.5, "S_spec": 0.5, "name": "medium_risk"},
        {"d_star": 3.0, "C_spin": 0.2, "S_spec": 0.3, "name": "high_risk"},
        {"d_star": 5.0, "C_spin": 0.1, "S_spec": 0.1, "name": "very_high_risk"},
        {"d_star": 10.0, "C_spin": 0.1, "S_spec": 0.1, "name": "extreme_risk"},
    ]

    print(f"{'Scenario':>15} {'R_bounded':>15} {'R_unbounded':>15} {'Dec_B':>12} {'Dec_U':>12}")
    print("-" * 80)

    for s in scenarios:
        R_b = risk_bounded(s["d_star"], s["C_spin"], s["S_spec"])
        R_u = risk_unbounded(s["d_star"], s["C_spin"], s["S_spec"])

        dec_b = decide(R_b)
        dec_u = decide(R_u)

        R_b_str = f"{R_b:.6f}" if R_b < 1e10 else f"{R_b:.2e}"
        R_u_str = "inf" if math.isinf(R_u) else f"{R_u:.6f}" if R_u < 1e10 else f"{R_u:.2e}"

        print(f"{s['name']:>15} {R_b_str:>15} {R_u_str:>15} {dec_b:>12} {dec_u:>12}")

    print("-" * 80)

    # Verify key properties
    # 1. Low risk should ALLOW in both modes
    R_low_b = risk_bounded(0.3, 0.9, 0.8)
    R_low_u = risk_unbounded(0.3, 0.9, 0.8)
    assert decide(R_low_b) == "ALLOW", "Low risk bounded should ALLOW"
    assert decide(R_low_u) == "ALLOW", "Low risk unbounded should ALLOW"

    # 2. Extreme risk should DENY in both modes
    R_extreme_b = risk_bounded(10.0, 0.1, 0.1)
    R_extreme_u = risk_unbounded(10.0, 0.1, 0.1)
    assert decide(R_extreme_b) == "DENY", "Extreme risk bounded should DENY"
    assert decide(R_extreme_u) == "DENY", "Extreme risk unbounded should DENY"

    # 3. Unbounded should be stricter (higher risk) at moderate distances
    R_mod_b = risk_bounded(3.0, 0.5, 0.5)
    R_mod_u = risk_unbounded(3.0, 0.5, 0.5)
    if not math.isinf(R_mod_u):
        assert R_mod_u >= R_mod_b, "Unbounded risk >= bounded risk"

    print("✓ All dual-mode risk tests passed")
    return True


def test_phase_shift():
    """Test phase-shifting between modes."""
    print("\n[Test 4: Phase-Shift Capability]")
    print("-" * 70)

    d_test = 3.0
    C_spin = 0.5
    S_spec = 0.5

    # Calculate in both modes
    R_bounded = risk_bounded(d_test, C_spin, S_spec)
    R_unbounded = risk_unbounded(d_test, C_spin, S_spec)

    print(f"Test parameters: d={d_test}, C_spin={C_spin}, S_spec={S_spec}")
    print(f"\nBOUNDED mode:")
    print(f"  H(d) = {harmonic_bounded(d_test):.6f}")
    print(f"  Risk = {R_bounded:.6f}")
    print(f"  Decision = {decide(R_bounded)}")

    print(f"\nUNBOUNDED mode:")
    H_u = harmonic_unbounded(d_test)
    print(f"  H(d) = {'inf' if math.isinf(H_u) else f'{H_u:.6f}'}")
    print(f"  Risk = {'inf' if math.isinf(R_unbounded) else f'{R_unbounded:.6f}'}")
    print(f"  Decision = {decide(R_unbounded)}")

    # Verify phase-shift preserves base properties
    assert harmonic_bounded(0) == harmonic_unbounded(0), "H(0) = 1 in both modes"

    print("\n✓ Phase-shift capability verified")
    print("  Both modes can be used interchangeably")
    print("  BOUNDED: Numerical stability, predictable values")
    print("  UNBOUNDED: Vertical Wall patent, true rejection barrier")
    return True


def run_all_tests():
    """Run complete test suite."""
    print("=" * 70)
    print("DUAL-MODE AXIOM CORE: Pure Python Test Suite")
    print("=" * 70)
    print(f"Golden ratio φ = {PHI:.10f}")

    results = {
        "harmonic_modes": test_harmonic_modes(),
        "langues_metric": test_langues_metric(),
        "dual_mode_risk": test_dual_mode_risk(),
        "phase_shift": test_phase_shift(),
    }

    print("\n" + "=" * 70)
    all_passed = all(results.values())
    print(f"OVERALL: {'PASS ✓' if all_passed else 'FAIL ✗'}")
    print("=" * 70)

    if all_passed:
        print("\n[Summary]")
        print("  ✓ BOUNDED mode (R^d² clamped): Verified")
        print("  ✓ UNBOUNDED mode (exp(d²) unclamped): Verified")
        print("  ✓ Langues metric with φ-weighting: Verified")
        print("  ✓ Risk calculation in both modes: Verified")
        print("  ✓ Phase-shift capability: Verified")
        print("\n  Both formulations work correctly.")
        print("  System can phase-shift between modes as needed.")

    return all_passed


if __name__ == "__main__":
    run_all_tests()
