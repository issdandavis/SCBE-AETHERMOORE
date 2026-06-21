"""Tests for cross_check -- the differential harness that flags when two implementations of one contract diverge.

Pins: identical implementations agree; a one-off difference is caught at the first witness; a one-side crash
is a divergence; the run is deterministic; and on the real contract that diverged this session (the observer
CBJ jump-back target) the FIXED assumption-core surface agrees while the pre-fix min-of-core BUG is caught
with a concrete, reproducible witness -- the instrument that would have caught the parallel-lane root-drop.
"""

from __future__ import annotations

from python.scbe.cross_check import agree, demo


def _ints(rng):
    return rng.randint(-50, 50)


def test_identical_implementations_agree():
    cc = agree(lambda x: x * 2, lambda x: x + x, _ints, n=500, seed=1)
    assert cc.agreed and cc.divergence is None and cc.samples == 500


def test_a_one_off_difference_is_caught_with_a_witness():
    cc = agree(lambda x: x, lambda x: x + 1, _ints, n=500, seed=1)
    assert not cc.agreed
    assert cc.divergence is not None
    assert cc.divergence.index == 0  # caught immediately
    assert cc.divergence.left != cc.divergence.right  # the two outputs on the witness input


def test_a_one_side_crash_is_a_divergence():
    # left raises on negatives, right never does -> a genuine disagreement, not a harness failure
    def left(x):
        if x < 0:
            raise ValueError("neg")
        return x

    cc = agree(left, lambda x: x, _ints, n=500, seed=3)
    assert not cc.agreed
    assert "raised: ValueError" in str(cc.divergence.left)


def test_key_normalizes_before_comparing():
    # outputs differ as lists but agree as sets -> a key that sorts makes them agree
    cc = agree(lambda x: [x, -x], lambda x: [-x, x], _ints, n=200, seed=1, key=sorted)
    assert cc.agreed


def test_deterministic_same_seed_same_result():
    a = agree(lambda x: x, lambda x: x + 1, _ints, n=100, seed=7)
    b = agree(lambda x: x, lambda x: x + 1, _ints, n=100, seed=7)
    assert (a.agreed, a.samples, a.divergence.input_repr) == (b.agreed, b.samples, b.divergence.input_repr)


def test_observer_contract_fixed_agrees_buggy_is_caught():
    d = demo()
    assert d["fixed_surface_agrees"] is True  # the #2592 fix holds across the fuzz
    assert d["buggy_surface_is_caught"] is True  # the pre-fix min-of-core bug is detected
    w = d["_buggy"].divergence
    assert w is not None and w.left != w.right  # a concrete witness: canonical root vs the dropped root
