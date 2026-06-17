"""Correctness tests for the fast number-finding primitives (src/numtheory.py)."""

from functools import reduce
from operator import mul

import pytest

from src import numtheory as nt


def _product(xs):
    return reduce(mul, xs, 1)


@pytest.mark.parametrize("n", [2, 3, 5, 7, 13, 97, 7919, 104729, 2_147_483_647, 2**61 - 1])
def test_known_primes(n):
    assert nt.is_prime(n) is True


@pytest.mark.parametrize("n", [-5, 0, 1, 4, 9, 100, 7917, 561, 1105, 2**61 - 3])
def test_known_composites_and_units(n):
    # 561, 1105 are Carmichael numbers — must not fool Miller–Rabin.
    assert nt.is_prime(n) is False


def test_carmichael_numbers_are_composite():
    for c in (561, 1105, 1729, 2465, 2821, 6601, 8911):
        assert nt.is_prime(c) is False


def test_large_prime_is_deterministic():
    # 2**31 - 1 (Mersenne prime) is far below the deterministic bound.
    assert (2**31 - 1) < nt.DETERMINISTIC_BOUND
    assert nt.is_prime(2**31 - 1) is True


@pytest.mark.parametrize(
    "n,expected",
    [
        (1, []),
        (2, [2]),
        (360, [2, 2, 2, 3, 3, 5]),
        (97, [97]),
        (1_000_000, [2, 2, 2, 2, 2, 2, 5, 5, 5, 5, 5, 5]),
    ],
)
def test_prime_factors_known(n, expected):
    assert nt.prime_factors(n) == expected


def test_factorization_roundtrip_semiprime():
    # product of two distinct large primes — Pollard rho must crack it fast.
    p = nt.next_prime(10**9)
    q = nt.next_prime(10**10)
    n = p * q
    fac = nt.factorization(n)
    assert fac == {p: 1, q: 1}
    assert _product(nt.prime_factors(n)) == n


def test_factorization_prime_power():
    assert nt.factorization(2**20) == {2: 20}
    assert nt.factorization(3**13) == {3: 13}


@pytest.mark.parametrize(
    "k,expected",
    [(1, 2), (2, 3), (3, 5), (6, 13), (100, 541), (1000, 7919), (10000, 104729)],
)
def test_nth_prime(k, expected):
    assert nt.nth_prime(k) == expected


def test_nth_prime_rejects_nonpositive():
    with pytest.raises(ValueError):
        nt.nth_prime(0)


@pytest.mark.parametrize(
    "n,expected",
    [(0, 2), (1, 2), (2, 3), (13, 17), (7918, 7919), (104728, 104729)],
)
def test_next_prime(n, expected):
    assert nt.next_prime(n) == expected


def test_primes_in_range():
    assert nt.primes_in_range(10, 30) == [11, 13, 17, 19, 23, 29]
    assert nt.primes_in_range(0, 12) == [2, 3, 5, 7, 11]
    assert nt.primes_in_range(90, 90) == []


def test_primes_upto_matches_range():
    assert nt.primes_upto(30) == [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
    # the two sieves must agree on overlapping spans
    assert nt.primes_in_range(2, 1001) == nt.primes_upto(1000)


def test_prime_factors_rejects_negative():
    with pytest.raises(ValueError):
        nt.prime_factors(-1)
