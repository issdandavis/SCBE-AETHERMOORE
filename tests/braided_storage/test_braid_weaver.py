"""Tests for BraidedVoxelStore — BraidWeaver."""

import time

import pytest

from src.braided_storage.braid_weaver import BraidWeaver
from src.braided_storage.types import BraidedPayload, SemanticBits


def _make_semantic_bits(**overrides) -> SemanticBits:
    defaults = dict(
        dominant_tongue="KO",
        tongue_trits=[1, 0, -1, 0, 1, -1],
        fingerprint_ids=["abc123"],
        sha256_hash="a" * 64,
        threat_score=0.1,
        governance_decision="ALLOW",
    )
    defaults.update(overrides)
    return SemanticBits(**defaults)


@pytest.fixture
def weaver():
    return BraidWeaver(memory_decay_rate=0.5)


class TestWeaveBasic:
    def test_weave_basic(self, weaver):
        bits = _make_semantic_bits()
        result = weaver.weave(bits, b"test data", "test://source", "text/plain")
        assert isinstance(result, BraidedPayload)
        assert result.strand_intent > 0
        assert result.strand_memory > 0
        assert result.braided_time > 0
        assert result.quarantined is False

    def test_three_strands(self, weaver):
        bits = _make_semantic_bits(threat_score=0.5)
        result = weaver.weave(bits, b"test", "s", "t/p")
        # All three strands should be positive
        assert result.strand_intent > 0
        assert result.strand_memory > 0
        assert result.strand_governance > 0


class TestBraidDistance:
    def test_braided_distance(self, weaver):
        bits = _make_semantic_bits()
        result = weaver.weave(bits, b"data", "src", "t/p")
        assert result.d_braid >= 0
        assert isinstance(result.d_braid, float)

    def test_harmonic_cost(self, weaver):
        bits = _make_semantic_bits()
        result = weaver.weave(bits, b"data", "src", "t/p")
        # Cost >= 1.0 always (phi^(d^2) >= 1)
        assert result.harmonic_cost >= 1.0


class TestPhaseState:
    def test_phase_state(self, weaver):
        bits = _make_semantic_bits(tongue_trits=[1, 1, 1, -1, -1, -1])
        result = weaver.weave(bits, b"data", "src", "t/p")
        # par = sign(1+1+1) = +1, perp = sign(-1-1-1) = -1
        assert result.phase_state == (1, -1)
        assert result.phase_label == "advance-contract"

    def test_equilibrium_phase(self, weaver):
        bits = _make_semantic_bits(tongue_trits=[0, 0, 0, 0, 0, 0])
        result = weaver.weave(bits, b"data", "src", "t/p")
        assert result.phase_state == (0, 0)
        assert result.phase_label == "equilibrium"


class TestMemoryDecay:
    def test_memory_decay(self, weaver):
        """Repeated content should have lower memory strand."""
        bits = _make_semantic_bits(sha256_hash="repeat" * 10 + "a" * 4)
        r1 = weaver.weave(bits, b"data", "src", "t/p")
        r2 = weaver.weave(bits, b"data", "src", "t/p")
        # Second weave should have lower or equal memory (repeated content)
        assert r2.strand_memory <= r1.strand_memory


class TestGovernanceScaling:
    def test_governance_scaling(self, weaver):
        """Higher threat score should increase governance strand."""
        low = _make_semantic_bits(threat_score=0.05, sha256_hash="a" * 64)
        high = _make_semantic_bits(threat_score=0.9, sha256_hash="b" * 64)
        r_low = weaver.weave(low, b"lo", "s", "t/p")
        r_high = weaver.weave(high, b"hi", "s", "t/p")
        assert r_high.strand_governance > r_low.strand_governance

    def test_quarantine_from_governance(self, weaver):
        bits = _make_semantic_bits(governance_decision="DENY")
        result = weaver.weave(bits, b"data", "src", "t/p")
        assert result.quarantined is True
