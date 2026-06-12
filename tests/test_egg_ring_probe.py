"""Regression locks for the egg-ring probe (scripts/eval/egg_ring_probe.py).

Each test freezes one verdict about whether ring structure on the Sacred-Egg
descent is load-bearing:

  1. m-adic coherence catches incoherent splices the enum ladder misses
  2. m-adic ALONE misses a coherent secret-swap — the commitment is still needed
  3. the Z[i] norm is exactly multiplicative (aggregate-receipt foundation)
  4. a sub-path is verifiable from aggregate norms alone (ring-only capability)
  5. a non-UFD ring admits a receipt collision -> must use class-number-1
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_PROBE = _REPO / "scripts" / "eval" / "egg_ring_probe.py"

sys.path.insert(0, str(_REPO))
_spec = importlib.util.spec_from_file_location("egg_ring_probe_under_test", _PROBE)
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)


def test_honest_descent_passes_all_three_checks():
    s = 12345 % E.MOD
    toks = E.honest_descent(s)
    assert E.enum_ladder_ok(toks)
    assert E.madic_ok(toks)


def test_incoherent_splice_passes_enum_but_fails_madic():
    # The headline: the integer ladder is blind to coherence; the algebra is not.
    for seed in range(50):
        s = (seed * 9176 + 1) % E.MOD
        E.R.seed(seed)
        spliced = E.incoherent_splice(s)
        assert E.enum_ladder_ok(spliced), "enum should accept a well-tagged splice"
        assert not E.madic_ok(spliced), "m-adic must reject a broken reduction"


def test_coherent_swap_fools_madic_but_not_the_commitment():
    # The null: algebra alone is insufficient — a coherent swap needs the yolk hash.
    for seed in range(50):
        s = (seed * 5557 + 3) % E.MOD
        E.R.seed(1000 + seed)
        real = E.honest_descent(s)
        swap, other = E.coherent_swap(s)
        assert other != s
        assert E.madic_ok(swap), "a swapped-but-coherent tower slips past m-adic"
        assert E.hash_chain(swap) != E.hash_chain(real), "commitment must catch the swap"


def test_gaussian_norm_is_multiplicative():
    for a in range(-4, 5):
        for b in range(-4, 5):
            for c in range(-3, 4):
                z, w = (a, b), (c, c - 1)
                assert E.zi_norm(E.zi_mul(z, w)) == E.zi_norm(z) * E.zi_norm(w)


def test_subpath_verifiable_from_aggregate_norm():
    steps = [(2, 1), (1, 3), (3, 0), (2, 2), (1, 1)]
    total = steps[0]
    for z in steps[1:]:
        total = E.zi_mul(total, z)
    tn = E.zi_norm(total)
    sub = E.zi_norm(steps[1]) * E.zi_norm(steps[2]) * E.zi_norm(steps[3])
    assert tn % sub == 0
    assert tn // sub == E.zi_norm(steps[0]) * E.zi_norm(steps[4])


def test_non_ufd_admits_receipt_collision_ufd_does_not():
    # Z[sqrt(-5)]: 6 = 2*3 = (1+s)(1-s), identical product AND norm -> collision.
    a = E.z5_mul((2, 0), (3, 0))
    b = E.z5_mul((1, 1), (1, -1))
    assert a == b == (6, 0)
    assert E.z5_norm(a) == E.z5_norm(b) == 36
    assert ((2, 0), (3, 0)) != ((1, 1), (1, -1))
    # Z[i] (UFD): every norm-9 element is an associate of 3 -> no operation swap.
    norm9 = sorted((x, y) for x in range(-3, 4) for y in range(-3, 4) if E.zi_norm((x, y)) == 9)
    assert norm9 == sorted([(-3, 0), (0, -3), (0, 3), (3, 0)])
