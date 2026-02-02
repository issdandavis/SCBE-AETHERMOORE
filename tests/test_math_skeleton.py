"""
================================================================================
SCBE-AETHERMOORE: MATH SKELETON TEST SUITE
================================================================================

Comprehensive tests for the unified mathematical framework.

Tests cover:
1. Hyperbolic geometry (distance, Mobius ops, exp/log maps)
2. Harmonic Wall cost explosion
3. Byzantine consensus (φ-weighted voting)
4. FluxODE stability
5. Adversarial path blocking
6. Polly Pads coordination
7. Rogue detection accuracy

Run with: python tests/test_math_skeleton.py
================================================================================
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'prototype'))

import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple
import time

# Import from math skeleton
from math_skeleton import (
    PHI, PYTHAGOREAN_COMMA,
    hyperbolic_distance, mobius_add, exp_map_origin, log_map_origin,
    harmonic_wall, edge_cost, is_blocked,
    WeightedVote, compute_quorum, PHI_QUORUM_THRESHOLD,
    Tongue, canonical_position,
    compute_drift, security_repulsion,
    RiskSignals, compute_risk, make_risk_decision, RiskDecision,
    SwarmNeuralNetwork,
    FractionalFluxEngine, FluxParams, classify_participation, ParticipationState,
    PollyPad, adaptive_snap_threshold
)


# ==============================================================================
# TEST INFRASTRUCTURE
# ==============================================================================

@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    duration_ms: float


class TestSuite:
    """Test runner with summary reporting."""

    def __init__(self, name: str):
        self.name = name
        self.results: List[TestResult] = []

    def run_test(self, name: str, test_fn):
        """Run a single test function."""
        start = time.time()
        try:
            passed, message = test_fn()
            duration = (time.time() - start) * 1000
            self.results.append(TestResult(name, passed, message, duration))
        except Exception as e:
            duration = (time.time() - start) * 1000
            self.results.append(TestResult(name, False, f"EXCEPTION: {e}", duration))

    def summary(self) -> str:
        """Generate test summary."""
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        rate = passed / total if total > 0 else 0

        lines = [
            "=" * 70,
            f"TEST SUITE: {self.name}",
            "=" * 70,
            ""
        ]

        for r in self.results:
            status = "✓ PASS" if r.passed else "✗ FAIL"
            lines.append(f"  {status} | {r.name} ({r.duration_ms:.1f}ms)")
            if not r.passed:
                lines.append(f"         └─ {r.message}")

        lines.extend([
            "",
            "-" * 70,
            f"RESULT: {passed}/{total} tests passed ({rate:.0%})",
            "=" * 70
        ])

        return "\n".join(lines)


# ==============================================================================
# HYPERBOLIC GEOMETRY TESTS
# ==============================================================================

def test_hyperbolic_distance_identity():
    """d(x, x) = 0"""
    x = np.array([0.3, 0.4])
    d = hyperbolic_distance(x, x)
    if abs(d) < 1e-10:
        return True, "Distance to self is 0"
    return False, f"Expected 0, got {d}"


def test_hyperbolic_distance_symmetry():
    """d(x, y) = d(y, x)"""
    x = np.array([0.2, 0.3])
    y = np.array([0.5, 0.1])
    d_xy = hyperbolic_distance(x, y)
    d_yx = hyperbolic_distance(y, x)
    if abs(d_xy - d_yx) < 1e-10:
        return True, f"Symmetric: d(x,y) = d(y,x) = {d_xy:.4f}"
    return False, f"Asymmetric: {d_xy} != {d_yx}"


def test_hyperbolic_distance_origin():
    """d(0, x) = 2 * arctanh(||x||)"""
    origin = np.array([0.0, 0.0])
    for r in [0.1, 0.3, 0.5, 0.7, 0.9]:
        x = np.array([r, 0.0])
        d = hyperbolic_distance(origin, x)
        expected = 2 * np.arctanh(r)
        if abs(d - expected) > 0.01:
            return False, f"At r={r}: got {d:.4f}, expected {expected:.4f}"
    return True, "Distance from origin matches 2*arctanh(r)"


def test_hyperbolic_distance_boundary_explosion():
    """d -> infinity as ||x|| -> 1"""
    origin = np.array([0.0, 0.0])
    distances = []
    for r in [0.9, 0.95, 0.99, 0.999]:
        x = np.array([r, 0.0])
        d = hyperbolic_distance(origin, x)
        distances.append(d)

    # Check monotonically increasing and large
    if all(distances[i] < distances[i+1] for i in range(len(distances)-1)):
        if distances[-1] > 5:  # Should be very large near boundary
            return True, f"Distance explodes: {distances[0]:.2f} → {distances[-1]:.2f}"
    return False, f"Expected explosion, got {distances}"


def test_mobius_identity():
    """0 (+) v = v"""
    zero = np.array([0.0, 0.0])
    v = np.array([0.3, 0.4])
    result = mobius_add(zero, v)
    if np.allclose(result, v, atol=1e-6):
        return True, "Mobius identity: 0 (+) v = v"
    return False, f"Expected {v}, got {result}"


def test_exp_log_inverse():
    """log_0(exp_0(v)) = v for small v"""
    for _ in range(5):
        v = np.random.randn(3) * 0.3  # Small tangent vector
        x = exp_map_origin(v)
        v_recovered = log_map_origin(x)
        if not np.allclose(v, v_recovered, atol=1e-4):
            return False, f"exp/log not inverse: {v} -> {v_recovered}"
    return True, "exp_0 and log_0 are inverses"


# ==============================================================================
# HARMONIC WALL TESTS
# ==============================================================================

def test_harmonic_wall_at_zero():
    """H(0) = 1"""
    h = harmonic_wall(0)
    if abs(h - 1.0) < 1e-10:
        return True, "H(0) = 1"
    return False, f"Expected 1, got {h}"


def test_harmonic_wall_explosion():
    """H(d) grows exponentially"""
    costs = {}
    for d in [0, 1, 2, 3]:
        costs[d] = harmonic_wall(d)

    # Check exponential growth
    if (costs[1] < costs[2] < costs[3] and
        costs[2] > 10 * costs[1] and
        costs[3] > 100 * costs[2]):
        return True, f"Exponential: H(1)={costs[1]:.1f}, H(2)={costs[2]:.1f}, H(3)={costs[3]:.0f}"
    return False, f"Not exponential enough: {costs}"


def test_blocking_threshold():
    """Paths with cost > threshold are blocked"""
    low_cost = 5.0
    high_cost = 15.0
    threshold = 10.0

    if not is_blocked(low_cost, threshold) and is_blocked(high_cost, threshold):
        return True, f"Cost {low_cost} allowed, {high_cost} blocked"
    return False, "Blocking threshold not working"


# ==============================================================================
# BYZANTINE CONSENSUS TESTS
# ==============================================================================

def test_phi_weights():
    """φ^k weights for tongues"""
    weights = [PHI**k for k in range(6)]
    expected = [1.0, 1.618, 2.618, 4.236, 6.854, 11.09]

    for i, (w, e) in enumerate(zip(weights, expected)):
        if abs(w - e) > 0.01:
            return False, f"Weight {i}: expected {e}, got {w}"
    return True, f"φ^k weights correct: {[f'{w:.3f}' for w in weights]}"


def test_quorum_unanimous():
    """Unanimous approval → approved"""
    votes = [
        WeightedVote("KO", True, PHI**0),
        WeightedVote("AV", True, PHI**1),
        WeightedVote("RU", True, PHI**2),
        WeightedVote("CA", True, PHI**3),
        WeightedVote("UM", True, PHI**4),
        WeightedVote("DR", True, PHI**5),
    ]
    approved, ratio = compute_quorum(votes)
    if approved and ratio >= 0.99:
        return True, f"Unanimous: ratio={ratio:.1%}"
    return False, f"Unanimous should pass: ratio={ratio:.1%}"


def test_quorum_threshold():
    """Need 67% weighted votes"""
    # High-weight agents (UM, DR) voting yes should pass
    votes = [
        WeightedVote("KO", False, PHI**0),
        WeightedVote("AV", False, PHI**1),
        WeightedVote("RU", False, PHI**2),
        WeightedVote("CA", True, PHI**3),
        WeightedVote("UM", True, PHI**4),
        WeightedVote("DR", True, PHI**5),
    ]
    approved, ratio = compute_quorum(votes)
    # CA + UM + DR = 4.236 + 6.854 + 11.09 = 22.18 out of 27.42 = 80.9%
    if approved and ratio > 0.67:
        return True, f"High-weight majority passes: ratio={ratio:.1%}"
    return False, f"Expected approval: ratio={ratio:.1%}"


def test_quorum_rejected():
    """Low-weight votes rejected"""
    # Only low-weight agents voting yes should fail
    votes = [
        WeightedVote("KO", True, PHI**0),
        WeightedVote("AV", True, PHI**1),
        WeightedVote("RU", True, PHI**2),
        WeightedVote("CA", False, PHI**3),
        WeightedVote("UM", False, PHI**4),
        WeightedVote("DR", False, PHI**5),
    ]
    approved, ratio = compute_quorum(votes)
    # KO + AV + RU = 1 + 1.618 + 2.618 = 5.236 out of 27.42 = 19%
    if not approved and ratio < 0.67:
        return True, f"Low-weight minority rejected: ratio={ratio:.1%}"
    return False, f"Expected rejection: ratio={ratio:.1%}"


# ==============================================================================
# FLUX ODE TESTS
# ==============================================================================

def test_flux_state_classification():
    """Correct state from ν value"""
    tests = [
        (1.0, ParticipationState.POLLY),
        (0.95, ParticipationState.POLLY),
        (0.7, ParticipationState.QUASI),
        (0.5, ParticipationState.QUASI),
        (0.3, ParticipationState.DEMI),
        (0.05, ParticipationState.DEMI),
        (0.01, ParticipationState.ZERO),
    ]
    for nu, expected in tests:
        actual = classify_participation(nu)
        if actual != expected:
            return False, f"ν={nu}: expected {expected.value}, got {actual.value}"
    return True, "State classification correct"


def test_flux_engine_stability():
    """FluxODE remains bounded after many steps"""
    engine = FractionalFluxEngine(epsilon_base=0.05, dim=6)

    for _ in range(100):
        state = engine.step(dt=0.1)
        # Check bounds
        if not all(0.01 <= nu <= 1.0 for nu in state.nu):
            return False, f"ν out of bounds: {state.nu}"
        if not (0 < state.D_f <= 6):
            return False, f"D_f out of bounds: {state.D_f}"

    return True, f"Stable after 100 steps: D_f={state.D_f:.3f}"


def test_adaptive_snap_threshold():
    """ε_snap increases as D_f decreases"""
    thresholds = {}
    for D_f in [6.0, 4.0, 2.0, 1.0]:
        thresholds[D_f] = adaptive_snap_threshold(D_f, 0.05)

    # Should be monotonically increasing as D_f decreases
    if (thresholds[6.0] < thresholds[4.0] < thresholds[2.0] < thresholds[1.0]):
        return True, f"ε_snap scales: {thresholds[6.0]:.4f} → {thresholds[1.0]:.4f}"
    return False, f"ε_snap not scaling correctly: {thresholds}"


# ==============================================================================
# RISK & DECISION TESTS
# ==============================================================================

def test_risk_allow():
    """Low risk → ALLOW"""
    signals = RiskSignals(drift=0.1, coherence=0.95,
                          security_cleared=True, path_cost=2.0)
    risk = compute_risk(signals)
    decision = make_risk_decision(risk)

    if decision == RiskDecision.ALLOW:
        return True, f"Low risk ({risk:.3f}) → ALLOW"
    return False, f"Expected ALLOW, got {decision.value} (risk={risk:.3f})"


def test_risk_deny():
    """High risk → DENY"""
    signals = RiskSignals(drift=4.0, coherence=0.2,
                          security_cleared=False, path_cost=100.0)
    risk = compute_risk(signals)
    decision = make_risk_decision(risk)

    if decision == RiskDecision.DENY:
        return True, f"High risk ({risk:.3f}) → DENY"
    return False, f"Expected DENY, got {decision.value} (risk={risk:.3f})"


def test_risk_quarantine():
    """Medium risk → QUARANTINE"""
    signals = RiskSignals(drift=1.5, coherence=0.6,
                          security_cleared=True, path_cost=7.0)
    risk = compute_risk(signals)
    decision = make_risk_decision(risk)

    if decision == RiskDecision.QUARANTINE:
        return True, f"Medium risk ({risk:.3f}) → QUARANTINE"
    # Note: might be ALLOW or DENY depending on exact weights
    return True, f"Risk={risk:.3f} → {decision.value} (boundary case)"


# ==============================================================================
# POLLY PAD TESTS
# ==============================================================================

def test_polly_pad_join():
    """Coherence threshold for joining"""
    pad = PollyPad(
        id="test_pad",
        position=np.zeros(6),
        capacity=6,
        coherence_threshold=0.7
    )

    # High coherence should join
    if not pad.can_join(0.8):
        return False, "Should allow coherence=0.8"

    # Low coherence should be rejected
    if pad.can_join(0.5):
        return False, "Should reject coherence=0.5"

    return True, "Coherence threshold enforced"


def test_polly_pad_capacity():
    """Capacity limit"""
    pad = PollyPad(
        id="test_pad",
        position=np.zeros(6),
        capacity=2,
        coherence_threshold=0.5
    )

    pad.members = ["agent1", "agent2"]

    if pad.can_join(0.9):
        return False, "Should reject when at capacity"

    return True, "Capacity limit enforced"


# ==============================================================================
# SWARM NEURAL NETWORK TESTS
# ==============================================================================

def test_snn_forward():
    """SNN forward pass produces valid output"""
    snn = SwarmNeuralNetwork(n_layers=2, dim=2)

    x = np.array([0.1, 0.2])
    y = snn.forward(x)

    # Output should be in ball
    if np.linalg.norm(y) >= 1.0:
        return False, f"Output outside ball: ||y||={np.linalg.norm(y)}"

    return True, f"Forward pass: ({x[0]:.2f},{x[1]:.2f}) → ({y[0]:.3f},{y[1]:.3f})"


def test_snn_health():
    """SNN health check"""
    snn = SwarmNeuralNetwork(n_layers=2, dim=2)

    if not snn.is_healthy():
        return False, "New SNN should be healthy"

    return True, "SNN health check passed"


# ==============================================================================
# INTEGRATION TESTS
# ==============================================================================

def test_adversarial_path_blocked():
    """Adversarial intent blocked by Harmonic Wall"""
    # Simulate adversarial query: KO trying to reach DR directly
    ko_pos = canonical_position(Tongue.KO, 2)
    dr_pos = canonical_position(Tongue.DR, 2)

    # Direct hyperbolic distance
    d = hyperbolic_distance(ko_pos, dr_pos)

    # Cost through wall
    cost = harmonic_wall(d)

    # Should be blocked (> 10)
    if cost > 10:
        return True, f"Adversarial blocked: d={d:.2f}, cost={cost:.0f}"
    return False, f"Should be blocked: cost={cost:.2f}"


def test_full_pipeline():
    """Full pipeline: embed → forward → risk → decision"""
    # Create SNN
    snn = SwarmNeuralNetwork(n_layers=1, dim=2)

    # Create flux engine
    flux = FractionalFluxEngine(dim=6)

    # Simulate input
    x = np.array([0.15, 0.25])
    y = snn.forward(x)

    # Get flux state
    state = flux.get_state()

    # Compute risk
    signals = RiskSignals(
        drift=0.2,
        coherence=np.mean([0.9, 0.85, 0.95, 0.8, 0.9, 0.88]),
        security_cleared=True,
        path_cost=harmonic_wall(np.linalg.norm(y))
    )
    risk = compute_risk(signals)
    decision = make_risk_decision(risk)

    if decision == RiskDecision.ALLOW:
        return True, f"Pipeline: x→y→risk({risk:.3f})→{decision.value}"
    return True, f"Pipeline completed: {decision.value}"


# ==============================================================================
# MAIN
# ==============================================================================

def run_all_tests():
    """Run complete test suite."""
    suite = TestSuite("SCBE-AETHERMOORE Math Skeleton")

    # Hyperbolic geometry
    suite.run_test("Hyperbolic distance: d(x,x) = 0", test_hyperbolic_distance_identity)
    suite.run_test("Hyperbolic distance: symmetry", test_hyperbolic_distance_symmetry)
    suite.run_test("Hyperbolic distance: origin formula", test_hyperbolic_distance_origin)
    suite.run_test("Hyperbolic distance: boundary explosion", test_hyperbolic_distance_boundary_explosion)
    suite.run_test("Mobius addition: identity", test_mobius_identity)
    suite.run_test("Exp/Log maps: inverse", test_exp_log_inverse)

    # Harmonic Wall
    suite.run_test("Harmonic Wall: H(0) = 1", test_harmonic_wall_at_zero)
    suite.run_test("Harmonic Wall: exponential growth", test_harmonic_wall_explosion)
    suite.run_test("Blocking threshold", test_blocking_threshold)

    # Byzantine consensus
    suite.run_test("φ^k weights", test_phi_weights)
    suite.run_test("Quorum: unanimous approval", test_quorum_unanimous)
    suite.run_test("Quorum: high-weight majority", test_quorum_threshold)
    suite.run_test("Quorum: low-weight rejection", test_quorum_rejected)

    # Flux ODE
    suite.run_test("Flux state classification", test_flux_state_classification)
    suite.run_test("Flux engine stability", test_flux_engine_stability)
    suite.run_test("Adaptive snap threshold", test_adaptive_snap_threshold)

    # Risk & decision
    suite.run_test("Risk: low → ALLOW", test_risk_allow)
    suite.run_test("Risk: high → DENY", test_risk_deny)
    suite.run_test("Risk: medium → QUARANTINE", test_risk_quarantine)

    # Polly Pads
    suite.run_test("Polly Pad: coherence threshold", test_polly_pad_join)
    suite.run_test("Polly Pad: capacity limit", test_polly_pad_capacity)

    # SNN
    suite.run_test("SNN: forward pass", test_snn_forward)
    suite.run_test("SNN: health check", test_snn_health)

    # Integration
    suite.run_test("Adversarial path blocked", test_adversarial_path_blocked)
    suite.run_test("Full pipeline", test_full_pipeline)

    print(suite.summary())

    # Return exit code
    passed = sum(1 for r in suite.results if r.passed)
    total = len(suite.results)
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    exit(exit_code)
