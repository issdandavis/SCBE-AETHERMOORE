"""Differential locks: genuine pure-Python DUAL-IMPLEMENTATIONS checked with cross_check.agree.

These are real contracts where two functions/paths SHOULD compute the same thing -- the kind that bit the
observer this session when a parallel surface silently disagreed. cross_check fuzzes a shared input domain;
if a future change makes a pair diverge, the (shrunk) witness names the failing input. Audited at write time
with no divergence found -- so these LOCK the agreement against regression.

Scope note: the polyglot multi-backend faces are deliberately NOT here -- python/scbe/polyglot_conformance.py
already differentials them (running node/rustc, honestly surfacing float-rounding divergences), so duplicating
it would be redundant. These cover contracts that had no differential.
"""

from __future__ import annotations

from python.scbe.cross_check import agree, shrink_list
from python.scbe.elastic_bijective_hash import splitmix64, splitmix64_inverse
from python.scbe.time_machine import Reversible, Tape

_SEED = 123456789


def test_time_scrub_reversible_agrees_with_event_sourced_replay():
    # time_machine presents two ways to get the state at logical time t: Reversible (forward/rewind, no log)
    # and Tape (event-sourced replay). For a bijective step both MUST land on splitmix64^t(seed). A divergence
    # would be a real bug in one of the time-scrub paths that underpin the Mars-DTN / reversible arc.
    def reversible_to(t):
        return Reversible(_SEED, splitmix64, splitmix64_inverse).to(t)

    def replay_to(t):
        return Tape(_SEED, lambda s, _e: splitmix64(s)).record(*([None] * t)).at(t)

    cc = agree(reversible_to, replay_to, lambda rng: rng.randint(0, 40), n=1500, seed=1, shrinker=shrink_list)
    assert cc.agreed, "Reversible vs Tape diverge at %r: %s vs %s" % (
        cc.divergence and cc.divergence.input,
        cc.divergence and cc.divergence.left,
        cc.divergence and cc.divergence.right,
    )


def test_splitmix64_is_a_bijection_both_directions():
    # the bijection the cube-token substrate, the time-step, and the quantum-gate model all rest on:
    # splitmix64_inverse undoes splitmix64 AND vice versa, over the full 64-bit domain.
    fwd_then_inv = agree(lambda x: splitmix64_inverse(splitmix64(x)), lambda x: x, _u64, n=4000, seed=2)
    assert fwd_then_inv.agreed, "inverse.forward != identity at %r" % (
        fwd_then_inv.divergence and fwd_then_inv.divergence.input
    )
    inv_then_fwd = agree(lambda x: splitmix64(splitmix64_inverse(x)), lambda x: x, _u64, n=4000, seed=3)
    assert inv_then_fwd.agreed, "forward.inverse != identity at %r" % (
        inv_then_fwd.divergence and inv_then_fwd.divergence.input
    )


def _u64(rng):
    return rng.getrandbits(64)
