"""Fast number-finding primitives — primality, factorization, and prime sieves.

Pure-stdlib, dependency-free number theory used as a bedrock tool for the SCBE
CLI ("find a number fast"). Everything here is *exact* integer arithmetic:

- ``is_prime(n)``        deterministic Miller–Rabin below ``DETERMINISTIC_BOUND``;
                         a strong probable-prime test (12 fixed bases) above it.
- ``prime_factors(n)``   Pollard's rho (Brent) + Miller–Rabin → full prime multiset.
- ``factorization(n)``   the same, collapsed to ``{prime: exponent}``.
- ``nth_prime(k)``       the k-th prime (1-indexed) via a sieve sized by the
                         Rosser prime-counting upper bound.
- ``next_prime(n)``      smallest prime strictly greater than n.
- ``primes_in_range``    segmented Sieve of Eratosthenes over ``[lo, hi)``.
- ``primes_upto(n)``     Sieve of Eratosthenes over ``[0, n]``.

The factoring routines accept an optional wall-clock ``time_budget_s`` so a
pathological input degrades to a clear timeout instead of hanging.
"""

from __future__ import annotations

import time
from math import gcd, isqrt, log
from typing import Dict, List, Optional

# Witness set proven to make Miller–Rabin a *correct* primality test for every
# n below this bound (Sorenson & Webster). Above it the same test is a strong
# probable-prime check — astronomically reliable, but not a proof.
_DET_WITNESSES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
DETERMINISTIC_BOUND = 3_317_044_064_679_887_385_961_981

_SMALL_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47)


class FactorizationTimeout(Exception):
    """Raised when factoring exceeds the supplied wall-clock budget."""


def _check_deadline(deadline: Optional[float]) -> None:
    if deadline is not None and time.monotonic() >= deadline:
        raise FactorizationTimeout()


def is_prime(n: int) -> bool:
    """Return True iff n is prime. Deterministic below DETERMINISTIC_BOUND."""
    if n < 2:
        return False
    for p in _SMALL_PRIMES:
        if n % p == 0:
            return n == p
    d = n - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in _DET_WITNESSES:
        a %= n
        if a == 0:
            continue
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def _pollard_brent(n: int, deadline: Optional[float]) -> int:
    """Return a non-trivial factor of composite n via Brent's rho variant."""
    if n % 2 == 0:
        return 2
    if n % 3 == 0:
        return 3
    c = 1
    while True:
        _check_deadline(deadline)
        y, m = 2, 128
        g = q = r = 1
        x = ys = 0
        while g == 1:
            _check_deadline(deadline)
            x = y
            for i in range(r):
                if i % 1024 == 0:
                    _check_deadline(deadline)
                y = (y * y + c) % n
            k = 0
            while k < r and g == 1:
                _check_deadline(deadline)
                ys = y
                for i in range(min(m, r - k)):
                    if i % 1024 == 0:
                        _check_deadline(deadline)
                    y = (y * y + c) % n
                    q = q * abs(x - y) % n
                g = gcd(q, n)
                k += m
            r *= 2
            _check_deadline(deadline)
        if g == n:  # backtrack to recover a factor missed by the batched gcd
            g = 1
            while g == 1:
                _check_deadline(deadline)
                ys = (ys * ys + c) % n
                g = gcd(abs(x - ys), n)
        if g != n:
            return g
        c += 1  # rare: retry with a different polynomial


def prime_factors(n: int, time_budget_s: Optional[float] = 20.0) -> List[int]:
    """Full sorted multiset of prime factors of n (n >= 0; <2 yields [])."""
    if n < 0:
        raise ValueError("n must be non-negative")
    factors: List[int] = []
    if n < 2:
        return factors
    for p in _SMALL_PRIMES:
        while n % p == 0:
            factors.append(p)
            n //= p
    deadline = (time.monotonic() + time_budget_s) if time_budget_s is not None else None
    stack = [n] if n > 1 else []
    while stack:
        _check_deadline(deadline)
        m = stack.pop()
        if m == 1:
            continue
        _check_deadline(deadline)
        if is_prime(m):
            factors.append(m)
            continue
        _check_deadline(deadline)
        d = _pollard_brent(m, deadline)
        stack.append(d)
        stack.append(m // d)
    factors.sort()
    return factors


def factorization(n: int, time_budget_s: Optional[float] = 20.0) -> Dict[int, int]:
    """Prime factorization of n as ``{prime: exponent}``."""
    out: Dict[int, int] = {}
    for p in prime_factors(n, time_budget_s=time_budget_s):
        out[p] = out.get(p, 0) + 1
    return out


def primes_upto(n: int) -> List[int]:
    """All primes in ``[0, n]`` via the Sieve of Eratosthenes."""
    if n < 2:
        return []
    sieve = bytearray([1]) * (n + 1)
    sieve[0] = sieve[1] = 0
    for i in range(2, isqrt(n) + 1):
        if sieve[i]:
            sieve[i * i :: i] = bytearray(len(range(i * i, n + 1, i)))
    return [i for i in range(2, n + 1) if sieve[i]]


def primes_in_range(lo: int, hi: int) -> List[int]:
    """All primes in the half-open interval ``[lo, hi)`` via a segmented sieve."""
    if hi <= 2 or hi <= lo:
        return []
    lo = max(lo, 2)
    base = primes_upto(isqrt(hi - 1) + 1)
    seg = bytearray([1]) * (hi - lo)
    for p in base:
        start = max(p * p, ((lo + p - 1) // p) * p)
        for m in range(start, hi, p):
            seg[m - lo] = 0
    return [lo + i for i in range(hi - lo) if seg[i]]


def nth_prime(k: int) -> int:
    """The k-th prime, 1-indexed (``nth_prime(1) == 2``)."""
    if k < 1:
        raise ValueError("k must be >= 1")
    if k <= 5:
        return (2, 3, 5, 7, 11)[k - 1]
    # Rosser's theorem: p_k < k(ln k + ln ln k) for k >= 6 — a proven upper bound.
    upper = int(k * (log(k) + log(log(k)))) + 3
    primes = primes_upto(upper)
    return primes[k - 1]


def next_prime(n: int) -> int:
    """Smallest prime strictly greater than n."""
    if n < 2:
        return 2
    candidate = n + 1
    while not is_prime(candidate):
        candidate += 1
    return candidate
