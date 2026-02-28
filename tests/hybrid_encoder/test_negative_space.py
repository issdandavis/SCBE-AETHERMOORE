"""Tests for hybrid_encoder.negative_space."""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

from src.hybrid_encoder.negative_space import NegativeSpaceEncoder


def test_complement_flips_trits():
    ns = NegativeSpaceEncoder()
    result = ns.encode([1, 0, -1, 1, 0, -1])
    assert result.complement_trits == (-1, 0, 1, -1, 0, 1)


def test_excluded_tongues():
    ns = NegativeSpaceEncoder()
    # Original [1, 0, -1, 1, 0, -1] -> complement [-1, 0, 1, -1, 0, 1]
    # Complement trits == -1 at positions 0 (KO) and 3 (CA)
    result = ns.encode([1, 0, -1, 1, 0, -1])
    assert "KO" in result.excluded_tongues
    assert "CA" in result.excluded_tongues


def test_all_positive_complement():
    ns = NegativeSpaceEncoder()
    result = ns.encode([1, 1, 1, 1, 1, 1])
    # All +1 -> all -1 in complement -> all tongues excluded
    assert len(result.excluded_tongues) == 6


def test_all_zero_complement():
    ns = NegativeSpaceEncoder()
    result = ns.encode([0, 0, 0, 0, 0, 0])
    assert result.complement_trits == (0, 0, 0, 0, 0, 0)
    assert result.excluded_tongues == []
    assert result.anti_energy == 0.0


def test_anti_energy_positive():
    ns = NegativeSpaceEncoder()
    result = ns.encode([1, -1, 1, -1, 1, -1])
    assert result.anti_energy > 0


def test_complement_distance_symmetric_near():
    ns = NegativeSpaceEncoder()
    dist = ns.complement_distance([1, 0, 0, 0, 0, 0], [1, 0, 0, 0, 0, 0])
    # Original complement is [-1, 0, 0, 0, 0, 0]
    # Distance between candidate [1,0,0,0,0,0] and complement [-1,0,0,0,0,0] = 2 * weight[0]
    assert dist > 0


def test_complement_distance_in_negative_space():
    ns = NegativeSpaceEncoder()
    # Candidate equals the complement exactly
    dist = ns.complement_distance([1, 0, 0, 0, 0, 0], [-1, 0, 0, 0, 0, 0])
    assert dist == 0.0


def test_short_input_padded():
    ns = NegativeSpaceEncoder()
    result = ns.encode([1, -1])
    assert len(result.complement_trits) == 6
