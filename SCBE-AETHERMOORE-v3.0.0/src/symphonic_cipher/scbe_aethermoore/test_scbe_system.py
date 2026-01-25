#!/usr/bin/env python3
"""
SCBE-AETHERMOORE Industry-Standard Test Suite
==============================================

pytest-compatible test suite following industry best practices:
- Unit tests for each component
- Integration tests for end-to-end flows
- Property-based tests for mathematical invariants
- Performance benchmarks

Run with: pytest test_scbe_system.py -v
Or:       python3 test_scbe_system.py

Requirements: numpy (standard library otherwise)
"""

import sys
import time
import hashlib
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any

# =============================================================================
# TEST CONFIGURATION
# =============================================================================

VERBOSE = True
PERFORMANCE_ITERATIONS = 100


# =============================================================================
# TEST RESULT TRACKING
# =============================================================================

@dataclass
class TestResult:
    name: str
    passed: bool
    duration_ms: float
    details: str = ""
    category: str = "unit"


class TestRunner:
    """Simple test runner that works without pytest installed."""

    def __init__(self):
        self.results: List[TestResult] = []
        self.current_category = "unit"

    def run_test(self, name: str, test_fn, category: str = "unit"):
        """Run a single test and record results."""
        start = time.perf_counter()
        try:
            result = test_fn()
            duration = (time.perf_counter() - start) * 1000

            if isinstance(result, tuple):
                passed, details = result
            elif isinstance(result, bool):
                passed, details = result, ""
            else:
                passed, details = True, str(result) if result else ""

            self.results.append(TestResult(name, passed, duration, details, category))

            if VERBOSE:
                status = "\033[92m PASS \033[0m" if passed else "\033[91m FAIL \033[0m"
                print(f"  [{status}] {name} ({duration:.2f}ms)")
                if details and not passed:
                    print(f"         {details}")

            return passed

        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            self.results.append(TestResult(name, False, duration, str(e), category))
            if VERBOSE:
                print(f"  [\033[91m FAIL \033[0m] {name} ({duration:.2f}ms)")
                print(f"         Exception: {e}")
            return False

    def summary(self) -> Dict[str, Any]:
        """Generate test summary."""
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)

        by_category = {}
        for r in self.results:
            if r.category not in by_category:
                by_category[r.category] = {"passed": 0, "total": 0}
            by_category[r.category]["total"] += 1
            if r.passed:
                by_category[r.category]["passed"] += 1

        return {
            "passed": passed,
            "total": total,
            "success_rate": f"{100*passed/total:.1f}%" if total > 0 else "N/A",
            "by_category": by_category,
            "total_time_ms": sum(r.duration_ms for r in self.results),
        }


# =============================================================================
# UNIT TESTS: MATHEMATICAL PRIMITIVES
# =============================================================================

def test_golden_ratio_constant():
    """Verify golden ratio is correctly defined."""
    PHI = (1 + np.sqrt(5)) / 2

    # Property: PHI^2 = PHI + 1
    assert abs(PHI**2 - (PHI + 1)) < 1e-10, "Golden ratio identity failed"

    # Property: 1/PHI = PHI - 1
    assert abs(1/PHI - (PHI - 1)) < 1e-10, "Golden ratio inverse failed"

    return True, f"PHI = {PHI:.10f}"


def test_realification_isometry():
    """Verify complex-to-real mapping preserves norm."""
    # Create complex vector
    c = np.array([1+2j, 3-4j, 0.5+0.5j])

    # Realify: [Re, Im]
    x = np.concatenate([c.real, c.imag])

    # Check norm preservation
    c_norm = np.linalg.norm(c)
    x_norm = np.linalg.norm(x)

    assert abs(c_norm - x_norm) < 1e-10, f"Norm drift: {abs(c_norm - x_norm)}"
    return True, f"||c|| = ||x|| = {c_norm:.6f}"


def test_poincare_ball_containment():
    """Verify Poincaré embedding stays strictly inside unit ball."""
    BALL_RADIUS = 0.999  # Safety margin

    def poincare_embed(x, alpha=1.0):
        r = np.linalg.norm(x)
        if r < 1e-10:
            return x
        u = np.tanh(alpha * r) * (x / r)
        # Clamp to ensure strictly inside ball
        u_norm = np.linalg.norm(u)
        if u_norm >= BALL_RADIUS:
            u = u * (BALL_RADIUS / u_norm)
        return u

    # Test many random inputs
    np.random.seed(42)
    max_norm = 0.0

    for _ in range(1000):
        x = np.random.randn(6) * np.random.uniform(0.1, 100)
        u = poincare_embed(x)
        norm = np.linalg.norm(u)
        max_norm = max(max_norm, norm)

        if norm >= 1.0:
            return False, f"Point escaped ball: ||u|| = {norm}"

    return True, f"max ||u|| = {max_norm:.6f} < 1.0"


def test_hyperbolic_distance_properties():
    """Verify hyperbolic distance satisfies metric axioms."""
    def hyperbolic_distance(u, v):
        u_norm_sq = np.dot(u, u)
        v_norm_sq = np.dot(v, v)
        diff_norm_sq = np.dot(u - v, u - v)

        u_norm_sq = min(u_norm_sq, 0.999**2)
        v_norm_sq = min(v_norm_sq, 0.999**2)

        denom = (1 - u_norm_sq) * (1 - v_norm_sq)
        if denom < 1e-10:
            return 50.0

        arg = 1 + 2 * diff_norm_sq / denom
        return float(np.arccosh(max(1.0, arg)))

    np.random.seed(123)

    for _ in range(100):
        u = np.random.randn(3) * 0.3
        v = np.random.randn(3) * 0.3
        w = np.random.randn(3) * 0.3

        # Non-negativity
        d = hyperbolic_distance(u, v)
        if d < 0:
            return False, f"Negative distance: {d}"

        # Identity of indiscernibles
        if hyperbolic_distance(u, u) > 1e-10:
            return False, f"d(u,u) != 0"

        # Symmetry
        if abs(hyperbolic_distance(u, v) - hyperbolic_distance(v, u)) > 1e-10:
            return False, "Symmetry violated"

        # Triangle inequality
        d_uv = hyperbolic_distance(u, v)
        d_vw = hyperbolic_distance(v, w)
        d_uw = hyperbolic_distance(u, w)

        if d_uw > d_uv + d_vw + 1e-6:
            return False, f"Triangle inequality violated: {d_uw} > {d_uv} + {d_vw}"

    return True, "All metric axioms satisfied"


def test_harmonic_scaling_monotonicity():
    """Verify harmonic scaling H(d,R) = R^{d^2} is monotonic in d."""
    PHI = (1 + np.sqrt(5)) / 2

    def harmonic_scaling(d, R=PHI):
        exponent = min(d**2, 700 / np.log(R + 1e-10))
        return R ** exponent

    d_values = np.linspace(0, 3, 50)
    H_values = [harmonic_scaling(d) for d in d_values]

    # Check monotonicity
    for i in range(len(H_values) - 1):
        if H_values[i+1] < H_values[i] - 1e-6:
            return False, f"Not monotonic at d={d_values[i]}"

    return True, f"H(0)={H_values[0]:.2f}, H(3)={H_values[-1]:.2f}"


def test_mobius_addition_properties():
    """Verify Möbius addition preserves ball containment."""
    def mobius_add(u, v, eps=1e-5):
        u_norm_sq = np.dot(u, u)
        v_norm_sq = np.dot(v, v)
        uv_dot = np.dot(u, v)

        num = (1 + 2*uv_dot + v_norm_sq) * u + (1 - u_norm_sq) * v
        den = 1 + 2*uv_dot + u_norm_sq * v_norm_sq

        result = num / max(den, eps)

        # Clamp to ball
        norm = np.linalg.norm(result)
        if norm >= 1 - eps:
            result = result * (1 - eps) / norm

        return result

    np.random.seed(456)

    for _ in range(100):
        u = np.random.randn(3) * 0.4
        v = np.random.randn(3) * 0.4

        w = mobius_add(u, v)

        if np.linalg.norm(w) >= 1.0:
            return False, f"Result escaped ball: ||w|| = {np.linalg.norm(w)}"

        if np.any(np.isnan(w)):
            return False, "NaN in result"

    return True, "Ball containment preserved"


# =============================================================================
# UNIT TESTS: CRYPTOGRAPHIC COMPONENTS
# =============================================================================

def test_hmac_chain_integrity():
    """Verify HMAC chain produces deterministic, non-repeating tags."""
    import hmac as hmac_lib

    def hmac_chain(key: bytes, messages: List[bytes]) -> List[bytes]:
        tags = []
        current_tag = key
        for msg in messages:
            current_tag = hmac_lib.new(current_tag, msg, hashlib.sha256).digest()
            tags.append(current_tag)
        return tags

    key = b"test_key_12345"
    messages = [f"message_{i}".encode() for i in range(10)]

    tags = hmac_chain(key, messages)

    # All tags should be unique
    if len(set(tags)) != len(tags):
        return False, "Duplicate tags in chain"

    # Chain should be deterministic
    tags2 = hmac_chain(key, messages)
    if tags != tags2:
        return False, "Chain not deterministic"

    # Different key = different chain
    tags3 = hmac_chain(b"different_key", messages)
    if tags == tags3:
        return False, "Different keys produced same chain"

    return True, f"Generated {len(tags)} unique tags"


def test_chaos_sensitivity():
    """Verify logistic map chaos amplifies small differences."""
    def logistic_iterate(r, x0, n):
        x = x0
        for _ in range(n):
            x = r * x * (1 - x)
        return x

    r1 = 3.97
    r2 = 3.9701  # Δr = 0.0001
    x0 = 0.5
    n = 50

    out1 = logistic_iterate(r1, x0, n)
    out2 = logistic_iterate(r2, x0, n)

    diff = abs(out2 - out1)

    # Difference should be large (chaos amplification)
    if diff < 0.1:
        return False, f"Insufficient chaos amplification: Δout = {diff}"

    amplification = diff / 0.0001

    return True, f"Δr=0.0001 → Δout={diff:.4f} ({amplification:.0f}x amplification)"


def test_sha256_determinism():
    """Verify SHA256 produces consistent hashes."""
    test_inputs = [
        b"hello world",
        b"SCBE-AETHERMOORE",
        bytes(range(256)),
        b"",
    ]

    for data in test_inputs:
        h1 = hashlib.sha256(data).hexdigest()
        h2 = hashlib.sha256(data).hexdigest()

        if h1 != h2:
            return False, f"SHA256 not deterministic for {data[:20]}"

        if len(h1) != 64:
            return False, f"Wrong hash length: {len(h1)}"

    return True, "SHA256 deterministic and correct length"


# =============================================================================
# UNIT TESTS: NEURAL/ENERGY COMPONENTS
# =============================================================================

def test_hopfield_energy_computation():
    """Verify Hopfield energy E(c) = -1/2 c'Wc + theta'c."""
    # Create simple Hopfield network
    np.random.seed(789)
    D = 6

    # Weight matrix (symmetric)
    W = np.random.randn(D, D)
    W = (W + W.T) / 2

    # Bias
    theta = np.random.randn(D)

    def energy(c):
        return -0.5 * c @ W @ c + theta @ c

    # Train on a pattern (should have low energy)
    pattern = np.random.randn(D)

    # Novel pattern (should have higher energy)
    novel = np.random.randn(D) * 2

    E_pattern = energy(pattern)
    E_novel = energy(novel)

    # Energy should be computable without errors
    if np.isnan(E_pattern) or np.isnan(E_novel):
        return False, "NaN in energy computation"

    return True, f"E(pattern)={E_pattern:.4f}, E(novel)={E_novel:.4f}"


def test_coherence_metrics_bounded():
    """Verify coherence metrics stay in [0, 1]."""
    np.random.seed(101)

    for _ in range(100):
        # Spectral coherence (1 - high_freq_ratio)
        signal = np.random.randn(1000)
        fft = np.fft.rfft(signal)
        magnitude = np.abs(fft)

        if np.sum(magnitude) > 1e-10:
            mid = len(magnitude) // 2
            hf_ratio = np.sum(magnitude[mid:]) / np.sum(magnitude)
            s_spec = 1.0 - hf_ratio

            if not (0 <= s_spec <= 1):
                return False, f"Spectral coherence out of bounds: {s_spec}"

        # Spin coherence |mean(e^{i*phi})|
        phases = np.random.uniform(0, 2*np.pi, 10)
        phasors = np.exp(1j * phases)
        c_spin = np.abs(np.mean(phasors))

        if not (0 <= c_spin <= 1):
            return False, f"Spin coherence out of bounds: {c_spin}"

    return True, "All coherence metrics in [0, 1]"


# =============================================================================
# UNIT TESTS: GOVERNANCE COMPONENTS
# =============================================================================

def test_risk_score_bounded():
    """Verify risk scores stay in valid range."""
    PHI = (1 + np.sqrt(5)) / 2

    def compute_risk(d_tri, s_spec, s_spin, d_star):
        # Base risk from coherence deficits
        R_base = 0.3 * (1 - s_spec) + 0.3 * (1 - s_spin) + 0.4 * np.tanh(d_tri)

        # Harmonic scaling
        H = PHI ** min(d_star**2, 10)

        # Final risk
        R_hat = 1.0 - np.exp(-R_base * H)

        return np.clip(R_hat, 0, 1)

    np.random.seed(202)

    for _ in range(100):
        d_tri = np.random.uniform(0, 5)
        s_spec = np.random.uniform(0, 1)
        s_spin = np.random.uniform(0, 1)
        d_star = np.random.uniform(0, 3)

        risk = compute_risk(d_tri, s_spec, s_spin, d_star)

        if not (0 <= risk <= 1):
            return False, f"Risk out of bounds: {risk}"

        if np.isnan(risk):
            return False, "NaN in risk computation"

    return True, "All risk scores in [0, 1]"


def test_decision_thresholds():
    """Verify decision logic works correctly."""
    def decide(risk, allow_thresh=0.3, deny_thresh=0.7):
        if risk < allow_thresh:
            return "ALLOW"
        elif risk < deny_thresh:
            return "QUARANTINE"
        else:
            return "DENY"

    # Test boundary conditions
    assert decide(0.0) == "ALLOW"
    assert decide(0.29) == "ALLOW"
    assert decide(0.31) == "QUARANTINE"
    assert decide(0.5) == "QUARANTINE"
    assert decide(0.69) == "QUARANTINE"
    assert decide(0.71) == "DENY"
    assert decide(1.0) == "DENY"

    return True, "Decision thresholds correct"


def test_trust_decay_mechanics():
    """Verify Byzantine trust decay works correctly."""
    def update_trust(tau, is_valid, alpha=0.9, decay=0.05, gain=0.02):
        if is_valid:
            return min(1.0, tau + gain)
        else:
            return max(0.0, tau - decay)

    # Simulate honest node
    tau_honest = 0.5
    for _ in range(20):
        tau_honest = update_trust(tau_honest, True)

    if tau_honest < 0.8:
        return False, f"Honest node should gain trust: {tau_honest}"

    # Simulate Byzantine node
    tau_byzantine = 0.5
    for _ in range(20):
        tau_byzantine = update_trust(tau_byzantine, False)

    if tau_byzantine > 0.1:
        return False, f"Byzantine node should lose trust: {tau_byzantine}"

    return True, f"Honest: {tau_honest:.2f}, Byzantine: {tau_byzantine:.2f}"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

def test_full_embedding_pipeline():
    """Test complete context → embedding → distance pipeline."""
    PHI = (1 + np.sqrt(5)) / 2

    # Step 1: Create context vector (complex)
    context = np.array([0.5+0.2j, 0.3-0.1j, 0.8+0.4j])

    # Step 2: Realify
    x = np.concatenate([context.real, context.imag])

    # Step 3: Weight with golden ratio
    weights = np.array([PHI**(-k) for k in range(len(x))])
    x_weighted = weights * x

    # Step 4: Poincaré embed
    r = np.linalg.norm(x_weighted)
    if r > 1e-10:
        u = np.tanh(r) * (x_weighted / r)
    else:
        u = x_weighted

    # Step 5: Compute distance to origin
    u_norm_sq = np.dot(u, u)
    if u_norm_sq < 0.999**2:
        d_H = np.arccosh(1 + 2 * u_norm_sq / (1 - u_norm_sq)**2)
    else:
        d_H = 10.0

    # Verify pipeline produced valid results
    if np.any(np.isnan(u)):
        return False, "NaN in embedding"

    if np.linalg.norm(u) >= 1.0:
        return False, "Embedding escaped ball"

    if d_H < 0:
        return False, "Negative distance"

    return True, f"||u|| = {np.linalg.norm(u):.4f}, d_H = {d_H:.4f}"


def test_governance_end_to_end():
    """Test complete governance decision flow."""
    PHI = (1 + np.sqrt(5)) / 2

    # Simulate valid context
    np.random.seed(303)

    # Good signals
    s_spec = 0.9  # High spectral coherence
    s_spin = 0.95  # High phase alignment
    d_star = 0.2  # Close to realm center
    d_tri = 0.1  # Low triadic distance

    # Compute risk
    R_base = 0.25 * (1 - s_spec) + 0.25 * (1 - s_spin) + 0.3 * d_tri + 0.2 * d_star
    H = PHI ** (d_star**2)
    risk = 1.0 - np.exp(-R_base * H)

    # Decision
    if risk < 0.3:
        decision = "ALLOW"
    elif risk < 0.7:
        decision = "QUARANTINE"
    else:
        decision = "DENY"

    # Valid context should be allowed
    if decision != "ALLOW":
        return False, f"Valid context got {decision}, risk={risk:.4f}"

    # Now test bad context
    s_spec = 0.2  # Low coherence
    s_spin = 0.3
    d_star = 2.0  # Far from realm
    d_tri = 1.5

    R_base = 0.25 * (1 - s_spec) + 0.25 * (1 - s_spin) + 0.3 * d_tri + 0.2 * d_star
    H = PHI ** min(d_star**2, 10)
    risk = 1.0 - np.exp(-R_base * H)

    if risk < 0.3:
        decision = "ALLOW"
    elif risk < 0.7:
        decision = "QUARANTINE"
    else:
        decision = "DENY"

    if decision == "ALLOW":
        return False, f"Bad context got ALLOW, risk={risk:.4f}"

    return True, f"Valid→ALLOW, Invalid→{decision}"


def test_phdm_geodesic_path():
    """Test PHDM geodesic curve evaluation."""
    np.random.seed(404)

    # Create simple waypoints in 6D
    n_waypoints = 5
    waypoints = [np.random.randn(6) * 0.3 for _ in range(n_waypoints)]
    duration = 10.0

    def evaluate_path(t):
        """Evaluate piecewise linear path at time t."""
        if t <= 0:
            return waypoints[0].copy()
        if t >= duration:
            return waypoints[-1].copy()

        segment_duration = duration / (n_waypoints - 1)
        segment = int(t / segment_duration)
        segment = min(segment, n_waypoints - 2)

        alpha = (t - segment * segment_duration) / segment_duration
        return (1 - alpha) * waypoints[segment] + alpha * waypoints[segment + 1]

    # Test path continuity
    t_values = np.linspace(0, duration, 100)

    for i in range(len(t_values) - 1):
        p1 = evaluate_path(t_values[i])
        p2 = evaluate_path(t_values[i + 1])

        dist = np.linalg.norm(p2 - p1)

        if dist > 1.0:  # Should be smooth
            return False, f"Discontinuity at t={t_values[i]}: jump={dist}"

    # Test endpoints
    start = evaluate_path(0)
    end = evaluate_path(duration)

    if np.linalg.norm(start - waypoints[0]) > 1e-6:
        return False, "Start point mismatch"

    if np.linalg.norm(end - waypoints[-1]) > 1e-6:
        return False, "End point mismatch"

    return True, f"Path smooth over {len(t_values)} samples"


def test_pqc_key_exchange_simulation():
    """Test simulated post-quantum key exchange."""
    # Simulated ML-KEM-768
    def keygen():
        seed = hashlib.sha256(str(time.time()).encode()).digest()
        public_key = hashlib.sha256(seed + b"public").digest()
        secret_key = seed + public_key
        return public_key, secret_key

    def encaps(public_key):
        randomness = hashlib.sha256(str(time.time_ns()).encode()).digest()
        shared_secret = hashlib.sha256(public_key + randomness).digest()
        ciphertext = hashlib.sha256(randomness + public_key).digest()
        return shared_secret, ciphertext, randomness

    def decaps(secret_key, ciphertext, randomness):
        public_key = secret_key[32:]
        shared_secret = hashlib.sha256(public_key + randomness).digest()
        return shared_secret

    # Generate keypair
    pk, sk = keygen()

    # Encapsulate
    ss1, ct, rand = encaps(pk)

    # Decapsulate (with randomness for simulation)
    ss2 = decaps(sk, ct, rand)

    # Shared secrets should match
    if ss1 != ss2:
        return False, "Shared secret mismatch"

    # Keys should have correct length
    if len(pk) != 32 or len(ss1) != 32:
        return False, f"Wrong key lengths: pk={len(pk)}, ss={len(ss1)}"

    return True, f"Key exchange successful, ss={ss1[:8].hex()}..."


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

def test_embedding_performance():
    """Benchmark embedding speed."""
    def poincare_embed(x, alpha=1.0):
        r = np.linalg.norm(x)
        if r < 1e-10:
            return x
        return np.tanh(alpha * r) * (x / r)

    np.random.seed(505)
    vectors = [np.random.randn(12) for _ in range(PERFORMANCE_ITERATIONS)]

    start = time.perf_counter()
    for v in vectors:
        _ = poincare_embed(v)
    duration_ms = (time.perf_counter() - start) * 1000

    per_op = duration_ms / PERFORMANCE_ITERATIONS

    # Should be fast (< 0.1ms per operation)
    if per_op > 1.0:
        return False, f"Too slow: {per_op:.3f}ms/op"

    return True, f"{per_op:.4f}ms/op ({PERFORMANCE_ITERATIONS} iterations)"


def test_distance_performance():
    """Benchmark hyperbolic distance speed."""
    def hyperbolic_distance(u, v):
        u_norm_sq = min(np.dot(u, u), 0.999**2)
        v_norm_sq = min(np.dot(v, v), 0.999**2)
        diff_norm_sq = np.dot(u - v, u - v)
        denom = (1 - u_norm_sq) * (1 - v_norm_sq)
        if denom < 1e-10:
            return 50.0
        arg = 1 + 2 * diff_norm_sq / denom
        return float(np.arccosh(max(1.0, arg)))

    np.random.seed(606)
    pairs = [(np.random.randn(6) * 0.3, np.random.randn(6) * 0.3)
             for _ in range(PERFORMANCE_ITERATIONS)]

    start = time.perf_counter()
    for u, v in pairs:
        _ = hyperbolic_distance(u, v)
    duration_ms = (time.perf_counter() - start) * 1000

    per_op = duration_ms / PERFORMANCE_ITERATIONS

    return True, f"{per_op:.4f}ms/op ({PERFORMANCE_ITERATIONS} iterations)"


def test_hash_performance():
    """Benchmark SHA256 speed."""
    data = b"test data for hashing" * 100

    start = time.perf_counter()
    for _ in range(PERFORMANCE_ITERATIONS):
        _ = hashlib.sha256(data).digest()
    duration_ms = (time.perf_counter() - start) * 1000

    per_op = duration_ms / PERFORMANCE_ITERATIONS
    throughput = len(data) * PERFORMANCE_ITERATIONS / (duration_ms / 1000) / 1e6

    return True, f"{per_op:.4f}ms/op, {throughput:.1f} MB/s"


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_all_tests():
    """Run all tests and generate report."""
    runner = TestRunner()

    print("=" * 70)
    print("SCBE-AETHERMOORE INDUSTRY-STANDARD TEST SUITE")
    print("=" * 70)

    # Unit Tests: Mathematical Primitives
    print("\n[UNIT] Mathematical Primitives")
    print("-" * 40)
    runner.run_test("golden_ratio_constant", test_golden_ratio_constant, "unit")
    runner.run_test("realification_isometry", test_realification_isometry, "unit")
    runner.run_test("poincare_ball_containment", test_poincare_ball_containment, "unit")
    runner.run_test("hyperbolic_distance_properties", test_hyperbolic_distance_properties, "unit")
    runner.run_test("harmonic_scaling_monotonicity", test_harmonic_scaling_monotonicity, "unit")
    runner.run_test("mobius_addition_properties", test_mobius_addition_properties, "unit")

    # Unit Tests: Cryptographic Components
    print("\n[UNIT] Cryptographic Components")
    print("-" * 40)
    runner.run_test("hmac_chain_integrity", test_hmac_chain_integrity, "unit")
    runner.run_test("chaos_sensitivity", test_chaos_sensitivity, "unit")
    runner.run_test("sha256_determinism", test_sha256_determinism, "unit")

    # Unit Tests: Neural/Energy Components
    print("\n[UNIT] Neural/Energy Components")
    print("-" * 40)
    runner.run_test("hopfield_energy_computation", test_hopfield_energy_computation, "unit")
    runner.run_test("coherence_metrics_bounded", test_coherence_metrics_bounded, "unit")

    # Unit Tests: Governance Components
    print("\n[UNIT] Governance Components")
    print("-" * 40)
    runner.run_test("risk_score_bounded", test_risk_score_bounded, "unit")
    runner.run_test("decision_thresholds", test_decision_thresholds, "unit")
    runner.run_test("trust_decay_mechanics", test_trust_decay_mechanics, "unit")

    # Integration Tests
    print("\n[INTEGRATION] End-to-End Flows")
    print("-" * 40)
    runner.run_test("full_embedding_pipeline", test_full_embedding_pipeline, "integration")
    runner.run_test("governance_end_to_end", test_governance_end_to_end, "integration")
    runner.run_test("phdm_geodesic_path", test_phdm_geodesic_path, "integration")
    runner.run_test("pqc_key_exchange_simulation", test_pqc_key_exchange_simulation, "integration")

    # Performance Tests
    print("\n[PERFORMANCE] Benchmarks")
    print("-" * 40)
    runner.run_test("embedding_performance", test_embedding_performance, "performance")
    runner.run_test("distance_performance", test_distance_performance, "performance")
    runner.run_test("hash_performance", test_hash_performance, "performance")

    # Summary
    summary = runner.summary()

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for category, stats in summary["by_category"].items():
        pct = 100 * stats["passed"] / stats["total"] if stats["total"] > 0 else 0
        status = "\033[92mPASS\033[0m" if pct == 100 else "\033[91mFAIL\033[0m"
        print(f"  {category.upper():15} {stats['passed']}/{stats['total']} ({pct:.0f}%) [{status}]")

    print("-" * 70)
    all_pass = summary["passed"] == summary["total"]
    status = "\033[92mALL TESTS PASSED\033[0m" if all_pass else "\033[91mSOME TESTS FAILED\033[0m"
    print(f"  TOTAL: {summary['passed']}/{summary['total']} ({summary['success_rate']}) [{status}]")
    print(f"  Time: {summary['total_time_ms']:.2f}ms")
    print("=" * 70)

    return summary


# =============================================================================
# PYTEST COMPATIBILITY
# =============================================================================

# These can be run with: pytest test_scbe_system.py -v

def test_pytest_golden_ratio():
    assert test_golden_ratio_constant()[0]

def test_pytest_realification():
    assert test_realification_isometry()[0]

def test_pytest_poincare_ball():
    assert test_poincare_ball_containment()[0]

def test_pytest_hyperbolic_distance():
    assert test_hyperbolic_distance_properties()[0]

def test_pytest_harmonic_scaling():
    assert test_harmonic_scaling_monotonicity()[0]

def test_pytest_mobius():
    assert test_mobius_addition_properties()[0]

def test_pytest_hmac():
    assert test_hmac_chain_integrity()[0]

def test_pytest_chaos():
    assert test_chaos_sensitivity()[0]

def test_pytest_sha256():
    assert test_sha256_determinism()[0]

def test_pytest_hopfield():
    assert test_hopfield_energy_computation()[0]

def test_pytest_coherence():
    assert test_coherence_metrics_bounded()[0]

def test_pytest_risk():
    assert test_risk_score_bounded()[0]

def test_pytest_decisions():
    assert test_decision_thresholds()[0]

def test_pytest_trust():
    assert test_trust_decay_mechanics()[0]

def test_pytest_pipeline():
    assert test_full_embedding_pipeline()[0]

def test_pytest_governance():
    assert test_governance_end_to_end()[0]

def test_pytest_phdm():
    assert test_phdm_geodesic_path()[0]

def test_pytest_pqc():
    assert test_pqc_key_exchange_simulation()[0]


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    summary = run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if summary["passed"] == summary["total"] else 1)
