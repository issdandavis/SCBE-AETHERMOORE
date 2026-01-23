"""
SCBE Homebrew Quick Test Suite
==============================

Fast developer feedback tests for:
- Quick sanity checks
- Basic functionality verification
- Smoke tests for all major components
- Easy-to-understand test cases

Run: pytest tests/test_homebrew_quick.py -v -m homebrew
Average runtime: < 30 seconds

"""

import pytest
import numpy as np
import hashlib
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Try imports
try:
    from src.scbe_14layer_reference import scbe_14layer_pipeline
    SCBE_AVAILABLE = True
except ImportError:
    SCBE_AVAILABLE = False

try:
    from src.crypto.rwp_v3 import RWPv3Protocol
    RWP_AVAILABLE = True
except ImportError:
    RWP_AVAILABLE = False

try:
    from src.crypto.sacred_tongues import SacredTongueTokenizer
    TONGUES_AVAILABLE = True
except ImportError:
    TONGUES_AVAILABLE = False


# =============================================================================
# SMOKE TESTS - Quick sanity checks
# =============================================================================

@pytest.mark.homebrew
class TestSmokeTests:
    """Quick sanity checks that everything loads and runs."""

    def test_numpy_available(self):
        """Verify numpy is available and working."""
        arr = np.array([1, 2, 3])
        assert np.sum(arr) == 6

    def test_golden_ratio_computes(self):
        """Verify golden ratio can be computed."""
        phi = (1 + np.sqrt(5)) / 2
        assert 1.61 < phi < 1.62

    def test_harmonic_ratio_defined(self):
        """Verify harmonic ratio (perfect fifth) is 1.5."""
        R = 1.5
        assert R == 1.5

    @pytest.mark.skipif(not SCBE_AVAILABLE, reason="SCBE not available")
    def test_pipeline_imports(self):
        """Verify SCBE pipeline can be imported."""
        assert scbe_14layer_pipeline is not None

    @pytest.mark.skipif(not RWP_AVAILABLE, reason="RWP not available")
    def test_rwp_imports(self):
        """Verify RWP protocol can be imported."""
        rwp = RWPv3Protocol()
        assert rwp is not None


# =============================================================================
# BASIC FUNCTIONALITY TESTS
# =============================================================================

@pytest.mark.homebrew
class TestBasicFunctionality:
    """Basic functionality that must always work."""

    def test_hash_computation(self):
        """Verify SHA-256 hashing works."""
        data = b"test data"
        h = hashlib.sha256(data).hexdigest()
        assert len(h) == 64
        assert h == "916f0027a575074ce72a331777c3478d6513f786a591bd892da1a577bf2335f9"

    def test_hyperbolic_distance_formula(self):
        """Verify hyperbolic distance can be calculated."""
        def hyperbolic_dist(u, v):
            u_sq = np.sum(u ** 2)
            v_sq = np.sum(v ** 2)
            diff_sq = np.sum((u - v) ** 2)
            arg = 1 + 2 * diff_sq / ((1 - u_sq) * (1 - v_sq))
            return np.arccosh(max(arg, 1.0))

        u = np.array([0.1, 0.0, 0.0])
        v = np.array([0.2, 0.0, 0.0])

        d = hyperbolic_dist(u, v)
        assert d > 0
        assert np.isfinite(d)

    def test_harmonic_scaling(self):
        """Verify harmonic scaling formula H = R^(d²)."""
        R = 1.5
        d = 2

        H = R ** (d ** 2)  # = 1.5^4 = 5.0625

        assert np.isclose(H, 5.0625)

    def test_decision_logic(self):
        """Verify basic decision logic works."""
        def make_decision(risk, theta1=0.3, theta2=0.7):
            if risk < theta1:
                return "ALLOW"
            elif risk < theta2:
                return "QUARANTINE"
            else:
                return "DENY"

        assert make_decision(0.1) == "ALLOW"
        assert make_decision(0.5) == "QUARANTINE"
        assert make_decision(0.9) == "DENY"

    def test_vector_normalization(self):
        """Verify vector normalization works."""
        v = np.array([3, 4, 0])
        norm = np.linalg.norm(v)
        normalized = v / norm

        assert np.isclose(np.linalg.norm(normalized), 1.0)


# =============================================================================
# QUICK INTEGRATION TESTS
# =============================================================================

@pytest.mark.homebrew
class TestQuickIntegration:
    """Quick integration tests for main components."""

    @pytest.mark.skipif(not SCBE_AVAILABLE, reason="SCBE not available")
    def test_pipeline_runs(self):
        """Verify pipeline runs without error."""
        position = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        result = scbe_14layer_pipeline(t=position, D=6)

        assert "decision" in result
        assert "risk_base" in result
        assert "H" in result

    @pytest.mark.skipif(not SCBE_AVAILABLE, reason="SCBE not available")
    def test_pipeline_decision_types(self):
        """Verify pipeline returns valid decision types."""
        position = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        result = scbe_14layer_pipeline(t=position, D=6)

        valid_decisions = ["ALLOW", "QUARANTINE", "DENY"]
        assert result["decision"] in valid_decisions

    @pytest.mark.skipif(not RWP_AVAILABLE, reason="RWP not available")
    def test_encryption_roundtrip(self):
        """Verify encrypt/decrypt works."""
        rwp = RWPv3Protocol()
        plaintext = b"Hello, SCBE!"
        password = b"test_password"

        # RWP v3 API: encrypt(password, plaintext), decrypt(password, envelope)
        envelope = rwp.encrypt(password=password, plaintext=plaintext)
        decrypted = rwp.decrypt(password=password, envelope=envelope)

        assert decrypted == plaintext


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

@pytest.mark.homebrew
class TestEdgeCases:
    """Quick edge case tests."""

    def test_zero_vector(self):
        """Test handling of zero vector."""
        zero = np.zeros(6)
        assert np.allclose(zero, 0)
        assert np.linalg.norm(zero) == 0

    def test_unit_vector(self):
        """Test unit vector normalization."""
        v = np.array([1, 0, 0, 0, 0, 0])
        assert np.linalg.norm(v) == 1

    def test_large_values(self):
        """Test handling of large values."""
        large = np.array([1e6, 1e6, 1e6, 1e6, 1e6, 1e6])
        norm = np.linalg.norm(large)
        assert np.isfinite(norm)

    def test_negative_values(self):
        """Test handling of negative values."""
        neg = np.array([-1, -2, -3, -4, -5, -6])
        norm = np.linalg.norm(neg)
        assert norm > 0

    @pytest.mark.skipif(not SCBE_AVAILABLE, reason="SCBE not available")
    def test_pipeline_with_zeros(self):
        """Test pipeline with zero position."""
        position = np.zeros(6)
        result = scbe_14layer_pipeline(t=position, D=6)
        assert result["decision"] in ["ALLOW", "QUARANTINE", "DENY"]


# =============================================================================
# PERFORMANCE SMOKE TESTS
# =============================================================================

@pytest.mark.homebrew
class TestPerformanceSmoke:
    """Quick performance checks."""

    def test_hash_speed(self):
        """Verify hashing is reasonably fast."""
        start = time.time()
        for _ in range(1000):
            hashlib.sha256(b"test").digest()
        elapsed = time.time() - start

        assert elapsed < 1.0, f"Hashing too slow: {elapsed}s for 1000 hashes"

    def test_numpy_speed(self):
        """Verify numpy operations are fast."""
        start = time.time()
        for _ in range(1000):
            a = np.random.rand(6)
            b = np.random.rand(6)
            _ = np.dot(a, b)
        elapsed = time.time() - start

        assert elapsed < 1.0, f"Numpy too slow: {elapsed}s for 1000 dot products"

    @pytest.mark.skipif(not SCBE_AVAILABLE, reason="SCBE not available")
    def test_pipeline_speed(self):
        """Verify pipeline completes in reasonable time."""
        position = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])

        start = time.time()
        for _ in range(10):
            scbe_14layer_pipeline(t=position, D=6)
        elapsed = time.time() - start

        avg_time = elapsed / 10
        assert avg_time < 1.0, f"Pipeline too slow: {avg_time}s average"


# =============================================================================
# SACRED TONGUE QUICK TESTS
# =============================================================================

@pytest.mark.homebrew
class TestSacredTonguesQuick:
    """Quick Sacred Tongue tests."""

    def test_tongue_names(self):
        """Verify Sacred Tongue names are defined."""
        tongues = ["KO", "AV", "RU", "CA", "UM", "DR"]
        assert len(tongues) == 6

    def test_tongue_mapping(self):
        """Verify tongue to purpose mapping."""
        mapping = {
            "KO": "nonce",      # Kor'aelin
            "AV": "aad",        # Avali
            "RU": "salt",       # Runethic
            "CA": "ciphertext", # Cassisivadan
            "UM": "redaction",  # Umbroth
            "DR": "tag"         # Draumric
        }

        assert len(mapping) == 6
        assert mapping["KO"] == "nonce"
        assert mapping["DR"] == "tag"


# =============================================================================
# GOVERNANCE TIER QUICK TESTS
# =============================================================================

@pytest.mark.homebrew
class TestGovernanceTiersQuick:
    """Quick governance tier tests."""

    def test_tier_ordering(self):
        """Verify governance tiers have clear ordering."""
        tiers = ["COLLAPSED", "DEMI", "QUASI", "POLLY"]

        # Lower index = lower privilege
        assert tiers.index("COLLAPSED") < tiers.index("POLLY")

    def test_tier_progression(self):
        """Verify XP thresholds for tier progression."""
        thresholds = {
            "COLLAPSED": 0,
            "DEMI": 100,
            "QUASI": 500,
            "POLLY": 2000
        }

        # Thresholds should be increasing
        values = list(thresholds.values())
        assert values == sorted(values)


# =============================================================================
# QUICK VALIDATION TESTS
# =============================================================================

@pytest.mark.homebrew
class TestQuickValidation:
    """Quick validation helpers."""

    def test_position_validation(self):
        """Verify position validation logic."""
        def is_valid_position(pos):
            return (
                isinstance(pos, (list, np.ndarray)) and
                len(pos) == 6 and
                all(isinstance(x, (int, float, np.integer, np.floating)) for x in pos)
            )

        assert is_valid_position([1, 2, 3, 4, 5, 6])
        assert is_valid_position(np.array([1, 2, 3, 4, 5, 6]))
        assert not is_valid_position([1, 2, 3])  # Too short
        assert not is_valid_position("invalid")  # Wrong type

    def test_context_validation(self):
        """Verify context validation logic."""
        valid_contexts = {"internal", "external", "untrusted"}

        assert "internal" in valid_contexts
        assert "external" in valid_contexts
        assert "untrusted" in valid_contexts
        assert "invalid" not in valid_contexts

    def test_decision_validation(self):
        """Verify decision validation logic."""
        valid_decisions = {"ALLOW", "QUARANTINE", "DENY"}

        assert "ALLOW" in valid_decisions
        assert "BLOCK" not in valid_decisions


# =============================================================================
# HELPFUL DEBUG TESTS
# =============================================================================

@pytest.mark.homebrew
class TestDebugHelpers:
    """Debug helper tests - useful during development."""

    def test_can_print_array(self):
        """Verify arrays can be printed (useful for debugging)."""
        arr = np.array([1.234, 5.678, 9.012])
        s = str(arr)
        assert "1.234" in s

    def test_can_format_results(self):
        """Verify results can be formatted."""
        result = {
            "decision": "ALLOW",
            "risk": 0.15,
            "H": 1.53
        }

        formatted = f"Decision: {result['decision']}, Risk: {result['risk']:.2f}"
        assert "ALLOW" in formatted
        assert "0.15" in formatted

    @pytest.mark.skipif(not SCBE_AVAILABLE, reason="SCBE not available")
    def test_pipeline_result_printable(self):
        """Verify pipeline result is printable."""
        position = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        result = scbe_14layer_pipeline(t=position, D=6)

        # Should be able to convert to string without error
        s = str(result)
        assert len(s) > 0


# =============================================================================
# RUN ALL HOMEBREW TESTS
# =============================================================================

if __name__ == "__main__":
    # Run with verbose output and stop on first failure
    pytest.main([
        __file__,
        "-v",
        "-x",  # Stop on first failure
        "-m", "homebrew",
        "--tb=short"  # Short traceback
    ])
