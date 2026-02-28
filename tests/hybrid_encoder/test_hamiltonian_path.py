"""Tests for hybrid_encoder.hamiltonian_path."""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

from src.hybrid_encoder.hamiltonian_path import HamiltonianTraversal


def test_fresh_state_allowed():
    ht = HamiltonianTraversal()
    valid, dec, count = ht.check([1, 0, -1, 1, 0, -1])
    assert valid is True
    assert dec == "ALLOW"
    assert count == 0


def test_revisit_quarantine():
    ht = HamiltonianTraversal()
    ht.record([1, 0, -1, 1, 0, -1])
    valid, dec, count = ht.check([1, 0, -1, 1, 0, -1])
    assert valid is False
    assert dec == "QUARANTINE"
    assert count == 1


def test_many_revisits_deny():
    ht = HamiltonianTraversal()
    trits = [0, 0, 0, 0, 0, 0]
    for _ in range(5):
        ht.record(trits)
    valid, dec, count = ht.check(trits)
    assert valid is False
    assert dec == "DENY"
    assert count == 5


def test_different_states_all_allowed():
    ht = HamiltonianTraversal()
    states = [
        [1, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0],
    ]
    for s in states:
        valid, dec, _ = ht.check(s)
        assert valid is True
        assert dec == "ALLOW"
        ht.record(s)


def test_unique_states_count():
    ht = HamiltonianTraversal()
    ht.record([1, 0, 0, 0, 0, 0])
    ht.record([0, 1, 0, 0, 0, 0])
    ht.record([1, 0, 0, 0, 0, 0])  # duplicate
    assert ht.unique_states_visited == 2


def test_coverage():
    ht = HamiltonianTraversal()
    ht.record([1, 0, 0, 0, 0, 0])
    assert ht.coverage == 1 / 729


def test_reset():
    ht = HamiltonianTraversal()
    ht.record([1, 0, 0, 0, 0, 0])
    ht.reset()
    assert ht.unique_states_visited == 0
    valid, dec, _ = ht.check([1, 0, 0, 0, 0, 0])
    assert valid is True
