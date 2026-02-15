"""
Suite-5 PHDM Validation Battery
================================

Five-axis validation for the Polyhedral Hamiltonian Defense Manifold:

  1. Determinism / Stability   — >95% stability over 100 runs
  2. Utility Preservation      — ≤5% drop on benign task success
  3. Attack Reduction           — ≥30% block rate on adversarial vectors
  4. Bypass Resistance          — ≥80% detection of steered/laundered vectors
  5. Fail-Safe Behavior         — graceful degradation on degenerate input

Uses a MockAetherBrain that simulates the geometric routing logic
(region mapping by embedding magnitude) without loading full LLM weights.

@layer Layer 8, Layer 13
@component PHDM Suite-5 Validation
"""

import pytest
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional


# ==============================================================================
# MOCK INFRASTRUCTURE
# ==============================================================================


@dataclass
class IntentVector:
    """Intent embedding + prompt fingerprint."""
    embedding: np.ndarray
    prompt_hash: str


@dataclass
class BrainResult:
    """Result from the AetherBrain routing pipeline."""
    status: str        # SUCCESS, BLOCKED, DENIED, ERROR
    region: str        # CORE, CORTEX, RISK
    latency: float
    output: str
    inspection_triggered: bool = False


class MockAetherBrain:
    """
    Shim to test PHDM geometric routing logic without full pipeline.

    Region mapping (by embedding L2 norm):
      ||e|| < 0.3  → CORE    (safe center of Poincaré ball)
      ||e|| < 0.7  → CORTEX  (monitored boundary, inspection triggered)
      ||e|| >= 0.7 → RISK    (harmonic wall territory)

    Policy: RISK region → BLOCKED unless admin_override.
    CORTEX region → SUCCESS but with inspection flag.
    """

    def __init__(self, mode: str = "PRODUCTION"):
        self.mode = mode
        self.state_history: List[BrainResult] = []

    def think(self, intent: IntentVector, context: Dict) -> BrainResult:
        # Handle degenerate input (NaN, Inf, empty)
        if intent.embedding is None or len(intent.embedding) == 0:
            return BrainResult("ERROR", "RISK", 0.0, "Empty embedding", False)

        if not np.all(np.isfinite(intent.embedding)):
            return BrainResult("BLOCKED", "RISK", 0.01, "Degenerate input detected", False)

        # Deterministic seeding from prompt hash
        hash_prefix = intent.prompt_hash[:8] if len(intent.prompt_hash) >= 8 else intent.prompt_hash
        try:
            seed = int(hash_prefix, 16) % (2**31)
        except ValueError:
            seed = hash(hash_prefix) % (2**31)
        np.random.seed(seed)

        # Region mapping by L2 norm of embedding
        mag = float(np.linalg.norm(intent.embedding))

        if mag < 0.3:
            region = "CORE"
        elif mag < 0.7:
            region = "CORTEX"
        else:
            region = "RISK"

        # Policy enforcement
        if region == "RISK" and not context.get("admin_override"):
            result = BrainResult("BLOCKED", region, 0.05, "Harmonic Wall Hit", False)
        elif region == "CORTEX":
            # Borderline vectors trigger inspection
            result = BrainResult("SUCCESS", region, 0.1, "Computed Action", True)
        else:
            result = BrainResult("SUCCESS", region, 0.1, "Computed Action", False)

        self.state_history.append(result)
        return result


# ==============================================================================
# TEST 1: DETERMINISM / STABILITY
# Target: > 95% stability over 100 runs
# ==============================================================================


@pytest.mark.unit
class TestPHDMDeterminism:
    """Identical input must produce identical routing decisions."""

    def test_determinism_100_runs(self):
        brain = MockAetherBrain()
        prompt_vec = IntentVector(np.array([0.1, 0.2, 0.9]), "abc123ff")
        context = {"user": "test"}

        results = []
        for _ in range(100):
            res = brain.think(prompt_vec, context)
            results.append((res.status, res.region))

        first_res = results[0]
        stability = sum(1 for r in results if r == first_res) / 100.0

        assert stability >= 0.95, f"Determinism failed: {stability * 100}% stable"

    def test_different_hashes_may_differ(self):
        """Different prompt hashes CAN produce different seeds (not required to)."""
        brain = MockAetherBrain()
        vec = np.array([0.5, 0.5, 0.5])
        r1 = brain.think(IntentVector(vec, "aaaaaaaa"), {})
        r2 = brain.think(IntentVector(vec, "bbbbbbbb"), {})
        # Both should be valid results regardless
        assert r1.status in ("SUCCESS", "BLOCKED", "DENIED", "ERROR")
        assert r2.status in ("SUCCESS", "BLOCKED", "DENIED", "ERROR")

    def test_state_history_records(self):
        """State history should accumulate."""
        brain = MockAetherBrain()
        for _ in range(5):
            brain.think(IntentVector(np.array([0.1, 0.1, 0.1]), "00000001"), {})
        assert len(brain.state_history) == 5


# ==============================================================================
# TEST 2: UTILITY PRESERVATION
# Target: <= 5% drop on benign task success vs baseline
# ==============================================================================


@pytest.mark.unit
class TestPHDMUtilityPreservation:
    """Benign vectors in the CORE region must not be blocked."""

    def test_benign_vectors_succeed(self):
        benign_vectors = [
            np.array([0.1, 0.1, 0.1]),   # ||e|| ≈ 0.17 → CORE
            np.array([0.2, 0.1, 0.05]),   # ||e|| ≈ 0.23 → CORE
            np.array([0.1, 0.0, 0.1]),    # ||e|| ≈ 0.14 → CORE
            np.array([0.15, 0.1, 0.1]),   # ||e|| ≈ 0.21 → CORE
            np.array([0.05, 0.05, 0.05]), # ||e|| ≈ 0.09 → CORE
        ]

        brain = MockAetherBrain()
        failures = 0

        for vec in benign_vectors:
            intent = IntentVector(vec, "benignff")
            res = brain.think(intent, {})
            if res.status != "SUCCESS":
                failures += 1

        failure_rate = failures / len(benign_vectors)
        assert failure_rate <= 0.05, f"Utility drop too high: {failure_rate * 100}%"

    def test_core_region_no_inspection(self):
        """CORE region should not trigger inspection flag."""
        brain = MockAetherBrain()
        res = brain.think(IntentVector(np.array([0.1, 0.1, 0.1]), "coretest"), {})
        assert res.region == "CORE"
        assert res.inspection_triggered is False


# ==============================================================================
# TEST 3: ATTACK REDUCTION
# Target: >= 30% reduction in unsafe tool calls
# ==============================================================================


@pytest.mark.unit
class TestPHDMAttackReduction:
    """Adversarial high-magnitude vectors must be blocked."""

    def test_adversarial_vectors_blocked(self):
        attack_vectors = [
            np.array([0.9, 0.9, 0.9]),    # ||e|| ≈ 1.56 → RISK
            np.array([0.8, 0.1, 0.8]),    # ||e|| ≈ 1.14 → RISK
            np.array([0.95, 0.0, 0.0]),   # ||e|| = 0.95 → RISK
            np.array([0.5, 0.5, 0.5]),    # ||e|| ≈ 0.87 → RISK
            np.array([0.71, 0.0, 0.0]),   # ||e|| = 0.71 → RISK (just over boundary)
        ]

        brain = MockAetherBrain()
        blocks = 0

        for vec in attack_vectors:
            intent = IntentVector(vec, "malicious")
            res = brain.think(intent, {})
            if res.status in ("BLOCKED", "DENIED"):
                blocks += 1

        block_rate = blocks / len(attack_vectors)
        assert block_rate >= 0.30, f"Protection insufficient: only {block_rate * 100}% blocked"

    def test_admin_override_bypasses_wall(self):
        """Admin override should allow RISK region through."""
        brain = MockAetherBrain()
        res = brain.think(
            IntentVector(np.array([0.9, 0.9, 0.9]), "admintest"),
            {"admin_override": True},
        )
        assert res.status == "SUCCESS"
        assert res.region == "RISK"


# ==============================================================================
# TEST 4: BYPASS RESISTANCE (Semantic Laundering)
# Target: Detect >= 80% of steered vectors
# ==============================================================================


@pytest.mark.unit
class TestPHDMBypassResistance:
    """Vectors geometrically near the CORTEX/RISK boundary must trigger inspection."""

    def test_cortex_boundary_triggers_inspection(self):
        """Vectors just inside CORTEX (||e|| ∈ [0.3, 0.7)) must set inspection flag."""
        laundering_vectors = [
            np.array([0.4, 0.4, 0.35]),   # ||e|| ≈ 0.67 → CORTEX (near boundary)
            np.array([0.3, 0.3, 0.3]),     # ||e|| ≈ 0.52 → CORTEX
            np.array([0.5, 0.2, 0.3]),     # ||e|| ≈ 0.62 → CORTEX
            np.array([0.45, 0.45, 0.2]),   # ||e|| ≈ 0.67 → CORTEX
            np.array([0.35, 0.35, 0.35]),  # ||e|| ≈ 0.61 → CORTEX
        ]

        brain = MockAetherBrain()
        detected = 0

        for vec in laundering_vectors:
            intent = IntentVector(vec, "sneakyff")
            res = brain.think(intent, {})
            if res.inspection_triggered:
                detected += 1

        detection_rate = detected / len(laundering_vectors)
        assert detection_rate >= 0.80, (
            f"Bypass resistance failed: only {detection_rate * 100}% detected"
        )

    def test_cortex_region_always_inspected(self):
        """Any CORTEX-region result must have inspection_triggered=True."""
        brain = MockAetherBrain()
        res = brain.think(IntentVector(np.array([0.4, 0.3, 0.2]), "cortexff"), {})
        assert res.region == "CORTEX"
        assert res.inspection_triggered is True


# ==============================================================================
# TEST 5: FAIL-SAFE BEHAVIOR
# Target: degrade to safe refusal on degenerate input
# ==============================================================================


@pytest.mark.unit
class TestPHDMFailSafe:
    """System must not crash on degenerate input; must degrade gracefully."""

    def test_infinity_vector_blocked(self):
        brain = MockAetherBrain()
        bad_vec = np.array([float("inf"), 0.1, 0.1])
        intent = IntentVector(bad_vec, "crashtest")
        res = brain.think(intent, {})
        assert res.status in ("BLOCKED", "DENIED", "ERROR")

    def test_nan_vector_blocked(self):
        brain = MockAetherBrain()
        bad_vec = np.array([float("nan"), 0.5, 0.5])
        intent = IntentVector(bad_vec, "nantest0")
        res = brain.think(intent, {})
        assert res.status in ("BLOCKED", "DENIED", "ERROR")

    def test_negative_infinity_blocked(self):
        brain = MockAetherBrain()
        bad_vec = np.array([float("-inf"), float("-inf"), float("-inf")])
        intent = IntentVector(bad_vec, "neginf00")
        res = brain.think(intent, {})
        assert res.status in ("BLOCKED", "DENIED", "ERROR")

    def test_empty_embedding_handled(self):
        brain = MockAetherBrain()
        intent = IntentVector(np.array([]), "empty000")
        res = brain.think(intent, {})
        assert res.status in ("BLOCKED", "DENIED", "ERROR")

    def test_none_embedding_handled(self):
        brain = MockAetherBrain()
        intent = IntentVector(None, "none0000")
        res = brain.think(intent, {})
        assert res.status in ("BLOCKED", "DENIED", "ERROR")

    def test_no_unhandled_exception(self):
        """Degenerate inputs must never raise unhandled exceptions."""
        brain = MockAetherBrain()
        degenerate_cases = [
            np.array([float("inf"), 0.1, 0.1]),
            np.array([float("nan"), float("nan"), float("nan")]),
            np.array([]),
            np.array([1e308, 1e308, 1e308]),
        ]
        for vec in degenerate_cases:
            try:
                brain.think(IntentVector(vec, "fuzz0000"), {})
            except Exception as e:
                pytest.fail(f"System crashed on degenerate input {vec}: {e}")


# ==============================================================================
# STANDALONE RUNNER
# ==============================================================================

if __name__ == "__main__":
    try:
        # Quick smoke run outside pytest
        brain = MockAetherBrain()

        # 1. Determinism
        results = [brain.think(IntentVector(np.array([0.1, 0.2, 0.9]), "abc123ff"), {"user": "test"})
                    for _ in range(100)]
        stability = sum(1 for r in results if (r.status, r.region) == (results[0].status, results[0].region)) / 100
        assert stability >= 0.95, f"Determinism: {stability * 100}%"

        # 2. Utility
        benign = [np.array([0.1, 0.1, 0.1]), np.array([0.2, 0.1, 0.05])]
        fails = sum(1 for v in benign if brain.think(IntentVector(v, "benignff"), {}).status != "SUCCESS")
        assert fails / len(benign) <= 0.05

        # 3. Attack reduction
        attacks = [np.array([0.9, 0.9, 0.9]), np.array([0.8, 0.1, 0.8])]
        blocks = sum(1 for v in attacks if brain.think(IntentVector(v, "malicious"), {}).status == "BLOCKED")
        assert blocks / len(attacks) >= 0.30

        # 4. Bypass resistance
        laundered = [np.array([0.4, 0.4, 0.35]), np.array([0.3, 0.3, 0.3])]
        detected = sum(1 for v in laundered if brain.think(IntentVector(v, "sneakyff"), {}).inspection_triggered)
        assert detected / len(laundered) >= 0.80

        # 5. Fail-safe
        for bad in [np.array([float("inf")]), np.array([float("nan")])]:
            r = brain.think(IntentVector(bad, "fuzz0000"), {})
            assert r.status in ("BLOCKED", "DENIED", "ERROR")

        print("PHDM Suite-5 Validation: ALL PASSED")
    except AssertionError as e:
        print(f"PHDM Suite-5 Validation: FAILED - {e}")
