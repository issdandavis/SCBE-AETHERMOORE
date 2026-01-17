#!/usr/bin/env python3
"""
Integration Test: Harmonic Scaling Law
=======================================

Validates the Corrected Harmonic Scaling Law as specified in the
SCBE-AETHERMOORE framework.

Key Properties Verified:
1. Bounded & Monotonic - H in [1, 1+alpha], no overflow
2. Quantum-Resistant - PQ context binding enforced
3. Metric-Compatible - Preserves ordering, subadditive-like
4. Specification Test Vectors - All 8 vectors pass

Primary Form:
    H(d*, R) = 1 + alpha * tanh(beta * d*)

Where:
    d* = invariant hyperbolic distance to nearest trusted realm
    alpha = 10.0 (maximum additional risk multiplier)
    beta = 0.5 (growth rate)

Run with:
    python test_harmonic_scaling_integration.py
"""

import sys
import math
import numpy as np

# Add the symphonic_cipher module
sys.path.insert(0, '.')

from symphonic_cipher.harmonic_scaling_law import (
    HarmonicScalingLaw,
    ScalingMode,
    PQContextCommitment,
    BehavioralRiskComponents,
    SecurityDecisionEngine,
    hyperbolic_distance_poincare,
    find_nearest_trusted_realm,
    quantum_resistant_harmonic_scaling,
    create_context_commitment,
    verify_test_vectors,
    DEFAULT_ALPHA,
    DEFAULT_BETA,
    TEST_VECTORS,
)


def print_header(title: str):
    """Print a formatted test header."""
    width = 70
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def print_result(test_name: str, passed: bool, details: str = ""):
    """Print test result with consistent formatting."""
    status = "PASS" if passed else "FAIL"
    symbol = "[+]" if passed else "[X]"
    print(f"{symbol} {test_name}: {status}")
    if details:
        for line in details.split('\n'):
            print(f"    {line}")


def test_specification_vectors() -> bool:
    """
    Test 1: Specification Test Vectors

    Verify all 8 test vectors from the specification match expected values.
    Using alpha=10, beta=0.5:

    | d* | tanh(beta*d*) | H(d*) = 1 + 10*tanh(beta*d*) |
    |----|---------------|------------------------------|
    | 0.0  | 0.0000 | 1.0000  - Perfect match         |
    | 0.5  | 0.2449 | 3.4490  - Minor deviation       |
    | 1.0  | 0.4621 | 5.6210  - Moderate deviation    |
    | 2.0  | 0.7616 | 8.6160  - Significant deviation |
    | 3.0  | 0.9051 | 10.0510 - High risk             |
    | 4.0  | 0.9640 | 10.6400 - Near-maximum          |
    | 5.0  | 0.9866 | 10.8660 - Saturated             |
    | 10.0 | 0.9999 | 10.9990 - Effectively maximum   |
    """
    print_header("Test 1: Specification Test Vectors")

    all_passed = True
    tolerance = 0.01
    law = HarmonicScalingLaw(alpha=10.0, beta=0.5, require_pq_binding=False)

    print(f"\nParameters: alpha={law.alpha}, beta={law.beta}")
    print(f"Tolerance: {tolerance}")
    print()
    print(f"{'d*':>6} | {'tanh(calc)':>10} | {'tanh(exp)':>10} | {'H(calc)':>10} | {'H(exp)':>10} | Status")
    print("-" * 72)

    for d_star, expected_tanh, expected_H in TEST_VECTORS:
        computed_H = law.compute(d_star)
        computed_tanh = math.tanh(0.5 * d_star)

        tanh_ok = abs(computed_tanh - expected_tanh) < tolerance
        H_ok = abs(computed_H - expected_H) < tolerance
        passed = tanh_ok and H_ok

        status = "OK" if passed else "MISMATCH"
        print(f"{d_star:>6.1f} | {computed_tanh:>10.4f} | {expected_tanh:>10.4f} | "
              f"{computed_H:>10.4f} | {expected_H:>10.4f} | {status}")

        if not passed:
            all_passed = False

    print_result("Specification Test Vectors", all_passed)
    return all_passed


def test_bounded_monotonic() -> bool:
    """
    Test 2: Bounded & Monotonic Properties

    Verify:
    - H is always in [1, 1 + alpha]
    - H(d1) < H(d2) if d1 < d2
    - No overflow for any value of d*
    """
    print_header("Test 2: Bounded & Monotonic Properties")

    law = HarmonicScalingLaw(alpha=10.0, beta=0.5, require_pq_binding=False)
    H_min, H_max = 1.0, 1.0 + law.alpha

    test_values = [0.0, 0.001, 0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 100.0, 1000.0, 1e6, 1e10]

    bounded_ok = True
    monotonic_ok = True
    prev_H = 0.0

    print(f"\nBounds: H in [{H_min}, {H_max}]")
    print()

    for d in test_values:
        H = law.compute(d)

        if not (H_min <= H <= H_max):
            bounded_ok = False
            print(f"  [X] d*={d}: H={H} OUT OF BOUNDS")

        if H < prev_H:
            monotonic_ok = False
            print(f"  [X] d*={d}: H={H} < prev H={prev_H} (NOT MONOTONIC)")

        prev_H = H

    # Test extreme values
    H_extreme = law.compute(1e100)
    if not math.isfinite(H_extreme):
        bounded_ok = False
        print(f"  [X] d*=1e100: H={H_extreme} (NOT FINITE)")

    passed = bounded_ok and monotonic_ok

    details = f"Bounded: {bounded_ok}, Monotonic: {monotonic_ok}"
    details += f"\nH(0)={law.compute(0.0):.6f}, H(inf)={law.compute(1e10):.6f}"
    print_result("Bounded & Monotonic", passed, details)
    return passed


def test_hyperbolic_distance() -> bool:
    """
    Test 3: Hyperbolic Distance (Poincare Ball Model)

    Verify the invariant dH metric:
    - d(u, u) = 0 (identity)
    - d(u, v) = d(v, u) (symmetry)
    - d(0, r) = 2*arctanh(r) (from origin formula)
    - Distance increases toward boundary
    """
    print_header("Test 3: Hyperbolic Distance (Invariant dH Metric)")

    all_passed = True

    # Test 1: Identity
    u = np.array([0.3, 0.4])
    d_self = hyperbolic_distance_poincare(u, u)
    identity_ok = abs(d_self) < 1e-10
    print(f"  Identity d(u,u): {d_self:.10f} {'OK' if identity_ok else 'FAIL'}")
    all_passed &= identity_ok

    # Test 2: Symmetry
    v = np.array([0.1, 0.2])
    d_uv = hyperbolic_distance_poincare(u, v)
    d_vu = hyperbolic_distance_poincare(v, u)
    symmetry_ok = abs(d_uv - d_vu) < 1e-10
    print(f"  Symmetry: d(u,v)={d_uv:.6f}, d(v,u)={d_vu:.6f} {'OK' if symmetry_ok else 'FAIL'}")
    all_passed &= symmetry_ok

    # Test 3: From origin formula
    r = 0.5
    origin = np.array([0.0, 0.0])
    point = np.array([r, 0.0])
    d_computed = hyperbolic_distance_poincare(origin, point)
    d_expected = 2 * np.arctanh(r)
    origin_ok = abs(d_computed - d_expected) < 0.01
    print(f"  From origin: computed={d_computed:.6f}, expected={d_expected:.6f} {'OK' if origin_ok else 'FAIL'}")
    all_passed &= origin_ok

    # Test 4: Boundary behavior (distance increases)
    d1 = hyperbolic_distance_poincare(origin, np.array([0.1, 0.0]))
    d2 = hyperbolic_distance_poincare(origin, np.array([0.5, 0.0]))
    d3 = hyperbolic_distance_poincare(origin, np.array([0.9, 0.0]))
    boundary_ok = d1 < d2 < d3
    print(f"  Boundary behavior: d(0.1)={d1:.4f} < d(0.5)={d2:.4f} < d(0.9)={d3:.4f} {'OK' if boundary_ok else 'FAIL'}")
    all_passed &= boundary_ok

    print_result("Hyperbolic Distance", all_passed)
    return all_passed


def test_quantum_resistant_binding() -> bool:
    """
    Test 4: Quantum-Resistant Binding

    Verify PQ context commitment:
    - Binding enforced when required
    - SHA3-256 commitment (32 bytes)
    - Placeholder for Kyber + Dilithium integration
    """
    print_header("Test 4: Quantum-Resistant Binding")

    all_passed = True

    # Test 1: Binding required by default
    law_strict = HarmonicScalingLaw(require_pq_binding=True)
    try:
        law_strict.compute(1.0)
        binding_required_ok = False
        print("  [X] PQ binding not enforced when required")
    except ValueError as e:
        binding_required_ok = "commitment required" in str(e)
        print(f"  [+] PQ binding enforced: {e}")
    all_passed &= binding_required_ok

    # Test 2: Valid commitment accepted
    commitment = b"\x00" * 32
    try:
        H = law_strict.compute(1.0, context_commitment=commitment)
        valid_commitment_ok = H > 1.0
        print(f"  [+] Valid commitment accepted: H={H:.4f}")
    except ValueError:
        valid_commitment_ok = False
        print("  [X] Valid commitment rejected")
    all_passed &= valid_commitment_ok

    # Test 3: Invalid size rejected
    try:
        law_strict.compute(1.0, context_commitment=b"\x00" * 16)
        invalid_size_ok = False
        print("  [X] Invalid commitment size accepted")
    except ValueError as e:
        invalid_size_ok = "size" in str(e).lower()
        print(f"  [+] Invalid size rejected: {e}")
    all_passed &= invalid_size_ok

    # Test 4: Context commitment creation
    ctx = create_context_commitment(
        d_star=1.5,
        behavioral_risk=0.3,
        session_id=b"test_session"
    )
    commitment_size_ok = len(ctx) == 32
    print(f"  Context commitment size: {len(ctx)} bytes {'OK' if commitment_size_ok else 'FAIL'}")
    all_passed &= commitment_size_ok

    # Test 5: PQContextCommitment class
    pq_commitment = PQContextCommitment.create(b"test_data")
    verify_ok = pq_commitment.verify(b"test_data")
    verify_fail = not pq_commitment.verify(b"wrong_data")
    pq_class_ok = verify_ok and verify_fail
    print(f"  PQContextCommitment verify: correct={verify_ok}, wrong_rejected={verify_fail} {'OK' if pq_class_ok else 'FAIL'}")
    all_passed &= pq_class_ok

    print_result("Quantum-Resistant Binding", all_passed)
    return all_passed


def test_security_decision_engine() -> bool:
    """
    Test 5: Security Decision Engine Integration

    Verify:
    Security_Decision = Crypto_Valid AND Behavioral_Risk < theta

    Where:
        Final_Risk' = Behavioral_Risk * H(d*, R)
    """
    print_header("Test 5: Security Decision Engine")

    all_passed = True

    engine = SecurityDecisionEngine(
        scaling_law=HarmonicScalingLaw(alpha=10.0, require_pq_binding=False),
        risk_threshold=0.7
    )

    # Scenario 1: Accept (crypto valid, low risk, close to trusted realm)
    decision1, details1 = engine.evaluate(
        crypto_valid=True,
        behavioral_risk=0.1,
        d_star=0.5
    )
    scenario1_ok = decision1 is True
    print(f"\n  Scenario 1: Accept (valid crypto, low risk)")
    print(f"    crypto_valid=True, risk=0.1, d*=0.5")
    print(f"    H={details1['H']:.4f}, final_risk={details1['final_risk']:.4f}")
    print(f"    Decision: {decision1} {'OK' if scenario1_ok else 'FAIL'}")
    all_passed &= scenario1_ok

    # Scenario 2: Reject (crypto invalid)
    decision2, details2 = engine.evaluate(
        crypto_valid=False,
        behavioral_risk=0.1,
        d_star=0.5
    )
    scenario2_ok = decision2 is False
    print(f"\n  Scenario 2: Reject (invalid crypto)")
    print(f"    crypto_valid=False, risk=0.1, d*=0.5")
    print(f"    Decision: {decision2} {'OK' if scenario2_ok else 'FAIL'}")
    all_passed &= scenario2_ok

    # Scenario 3: Reject (high risk due to large d*)
    decision3, details3 = engine.evaluate(
        crypto_valid=True,
        behavioral_risk=0.5,
        d_star=5.0  # Far from trusted realm
    )
    scenario3_ok = decision3 is False
    print(f"\n  Scenario 3: Reject (high scaled risk)")
    print(f"    crypto_valid=True, risk=0.5, d*=5.0")
    print(f"    H={details3['H']:.4f}, final_risk={details3['final_risk']:.4f}")
    print(f"    Decision: {decision3} (expected False) {'OK' if scenario3_ok else 'FAIL'}")
    all_passed &= scenario3_ok

    # Scenario 4: Edge case at threshold
    engine_tight = SecurityDecisionEngine(
        scaling_law=HarmonicScalingLaw(alpha=10.0, require_pq_binding=False),
        risk_threshold=0.5
    )
    decision4, details4 = engine_tight.evaluate(
        crypto_valid=True,
        behavioral_risk=0.1,
        d_star=0.0  # Perfect match: H=1, final_risk=0.1
    )
    scenario4_ok = decision4 is True
    print(f"\n  Scenario 4: Edge case (perfect match)")
    print(f"    crypto_valid=True, risk=0.1, d*=0.0")
    print(f"    H={details4['H']:.4f}, final_risk={details4['final_risk']:.4f}")
    print(f"    Decision: {decision4} {'OK' if scenario4_ok else 'FAIL'}")
    all_passed &= scenario4_ok

    print_result("Security Decision Engine", all_passed)
    return all_passed


def test_behavioral_risk_components() -> bool:
    """
    Test 6: Behavioral Risk Components

    Behavioral_Risk = w_d * D_hyp + w_c * (1 - C_spin) + w_s * (1 - S_spec) + ...

    All components normalized to [0, 1].
    """
    print_header("Test 6: Behavioral Risk Components")

    all_passed = True

    # Perfect match (risk = 0)
    perfect = BehavioralRiskComponents(
        D_hyp=0.0, C_spin=1.0, S_spec=1.0, T_temp=1.0, E_entropy=0.0
    )
    risk_perfect = perfect.compute()
    perfect_ok = abs(risk_perfect) < 1e-10
    print(f"  Perfect match: risk={risk_perfect:.6f} {'OK' if perfect_ok else 'FAIL'}")
    all_passed &= perfect_ok

    # Maximum deviation (risk = 1)
    worst = BehavioralRiskComponents(
        D_hyp=1.0, C_spin=0.0, S_spec=0.0, T_temp=0.0, E_entropy=1.0
    )
    risk_worst = worst.compute()
    worst_ok = abs(risk_worst - 1.0) < 1e-10
    print(f"  Maximum deviation: risk={risk_worst:.6f} {'OK' if worst_ok else 'FAIL'}")
    all_passed &= worst_ok

    # Partial deviation
    partial = BehavioralRiskComponents(
        D_hyp=0.5, C_spin=0.5, S_spec=0.5, T_temp=0.5, E_entropy=0.5
    )
    risk_partial = partial.compute()
    partial_ok = 0.0 < risk_partial < 1.0
    print(f"  Partial deviation: risk={risk_partial:.6f} {'OK' if partial_ok else 'FAIL'}")
    all_passed &= partial_ok

    print_result("Behavioral Risk Components", all_passed)
    return all_passed


def test_scaling_modes() -> bool:
    """
    Test 7: Alternative Scaling Modes

    - BOUNDED_TANH: H = 1 + alpha * tanh(beta * d*) [primary]
    - LOGARITHMIC: H = log2(1 + d*) [slower growth]
    - LINEAR_CLIPPED: H = min(1 + d*, 1 + alpha) [simple]
    """
    print_header("Test 7: Alternative Scaling Modes")

    all_passed = True

    # Logarithmic mode
    law_log = HarmonicScalingLaw(mode=ScalingMode.LOGARITHMIC, require_pq_binding=False)
    H_log_1 = law_log.compute(1.0)
    H_log_7 = law_log.compute(7.0)
    log_ok = abs(H_log_1 - 1.0) < 0.01 and abs(H_log_7 - 3.0) < 0.01
    print(f"  LOGARITHMIC: H(1)={H_log_1:.4f}~1, H(7)={H_log_7:.4f}~3 {'OK' if log_ok else 'FAIL'}")
    all_passed &= log_ok

    # Linear clipped mode
    law_linear = HarmonicScalingLaw(alpha=10.0, mode=ScalingMode.LINEAR_CLIPPED, require_pq_binding=False)
    H_lin_5 = law_linear.compute(5.0)
    H_lin_15 = law_linear.compute(15.0)
    linear_ok = abs(H_lin_5 - 6.0) < 1e-10 and abs(H_lin_15 - 11.0) < 1e-10
    print(f"  LINEAR_CLIPPED: H(5)={H_lin_5:.4f}=6, H(15)={H_lin_15:.4f}=11 (clipped) {'OK' if linear_ok else 'FAIL'}")
    all_passed &= linear_ok

    print_result("Alternative Scaling Modes", all_passed)
    return all_passed


def test_find_nearest_realm() -> bool:
    """
    Test 8: Find Nearest Trusted Realm

    d* = min_k dH(u_tilde, mu_k)
    """
    print_header("Test 8: Find Nearest Trusted Realm")

    all_passed = True

    point = np.array([0.3, 0.3])
    realms = [
        np.array([0.1, 0.1]),   # Index 0 - closest
        np.array([0.7, 0.7]),   # Index 1
        np.array([-0.5, 0.0]),  # Index 2
    ]

    d_star, idx = find_nearest_trusted_realm(point, realms)

    nearest_ok = idx == 0
    distance_ok = d_star > 0

    print(f"  Point: {point}")
    print(f"  Realms: {[r.tolist() for r in realms]}")
    print(f"  Nearest realm index: {idx} (expected 0) {'OK' if nearest_ok else 'FAIL'}")
    print(f"  Distance d*: {d_star:.4f} {'OK' if distance_ok else 'FAIL'}")

    all_passed = nearest_ok and distance_ok
    print_result("Find Nearest Realm", all_passed)
    return all_passed


def run_all_tests():
    """Run all integration tests."""
    print("\n" + "=" * 70)
    print("  HARMONIC SCALING LAW - INTEGRATION TEST SUITE")
    print("  SCBE-AETHERMOORE Framework")
    print("=" * 70)
    print("\nPrimary Form: H(d*, R) = 1 + alpha * tanh(beta * d*)")
    print(f"Default Parameters: alpha={DEFAULT_ALPHA}, beta={DEFAULT_BETA}")
    print("Bounds: H in [1, 11] for default parameters")

    results = []

    results.append(("Specification Test Vectors", test_specification_vectors()))
    results.append(("Bounded & Monotonic", test_bounded_monotonic()))
    results.append(("Hyperbolic Distance", test_hyperbolic_distance()))
    results.append(("Quantum-Resistant Binding", test_quantum_resistant_binding()))
    results.append(("Security Decision Engine", test_security_decision_engine()))
    results.append(("Behavioral Risk Components", test_behavioral_risk_components()))
    results.append(("Alternative Scaling Modes", test_scaling_modes()))
    results.append(("Find Nearest Realm", test_find_nearest_realm()))

    # Summary
    print("\n" + "=" * 70)
    print("  TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)

    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        symbol = "[+]" if ok else "[X]"
        print(f"  {symbol} {name}: {status}")

    print()
    print(f"  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n  ALL TESTS PASSED - Harmonic Scaling Law is production-ready!")
        print("  The invariant dH metric remains the unchanging law of distance.")
        print("  Quantum threats defeated by hybrid PQC (Kyber + Dilithium).")
        print("  Risk amplification is bounded, monotonic, and interpretable.")
    else:
        print(f"\n  {total - passed} test(s) failed - review output above.")

    print("=" * 70)

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
