#!/usr/bin/env python3
"""Primes as a counting system -- three concrete formalisms, run with worked examples.

1. offset-pair   : n -> (k, r)   discrete prime-stratum index (exact, invertible)
2. freq-octave   : n -> 2^(k + frac)   primes as octave boundaries (sonification)
3. leap-ladder   : the user's twist -- 1 = the HIGHEST prime, count downward in
   massive prime leaps; compound primes (primorials) mark the big bands.

Honest framing: all three are real encodings. They're great for indexing,
sonification, and prime-anchored visualization; they do NOT make ordinary
arithmetic easier (carries/products become nonlocal). There is no single "best"
mapping -- you pick by goal.

    python scripts/experiments/prime_count.py
"""

from __future__ import annotations

# Fermat primes -- the example template the idea uses.
FERMAT = [3, 5, 17, 257, 65537]


def offset_pair(n: int, P: list[int]):
    """n -> (k, r): k = prime stratum, r = offset inside [P[k], P[k+1])."""
    if n < P[0]:
        return (-1, n)  # below the first anchor
    for k in range(len(P) - 1):
        if P[k] <= n < P[k + 1]:
            return (k, n - P[k])
    return (len(P) - 1, n - P[-1])  # at/above the last anchor


def freq_octave(n: int, P: list[int], base: float = 2.0):
    """n -> base^(k + (n-P[k])/(P[k+1]-P[k])): cross a prime = an exact octave jump."""
    k, r = offset_pair(n, P)
    if k < 0:
        return base ** (n / P[0])  # interpolate up to the first anchor
    if k >= len(P) - 1:
        return base**k
    width = P[k + 1] - P[k]
    return base ** (k + r / width)


def primorial_chain(P: list[int]):
    """Compound primes: running products P[0], P[0]*P[1], ... (the user's 'compound primes')."""
    out, acc = [], 1
    for p in P:
        acc *= p
        out.append(acc)
    return out


def leap_ladder(P: list[int]):
    """The twist: 1 = the highest prime; each count is a leap down to the next prime."""
    desc = sorted(P, reverse=True)
    rows = []
    for i, p in enumerate(desc, start=1):
        leap = desc[i - 2] - p if i >= 2 else 0
        rows.append((i, p, leap))
    return rows


def main():
    P = FERMAT
    print(f"\nTEMPLATE (Fermat primes): {P}\n")

    print("1) offset-pair  n -> (k, r)   and the octave frequency f(n):")
    print(f"   {'n':>6} {'(k, r)':>10} {'f(n)':>12}")
    for n in [1, 4, 9, 16, 18, 100, 137, 256, 300, 70000]:
        k, r = offset_pair(n, P)
        f = freq_octave(n, P)
        print(f"   {n:>6} {f'({k}, {r})':>10} {f:>12.4f}")

    print("\n   note: crossing a prime is an EXACT doubling --")
    print(f"      f(17)  = {freq_octave(17, P):.4f}   (= 2^2, an octave floor)")
    print(f"      f(257) = {freq_octave(257, P):.4f}   (= 2^3, the next octave)")

    print("\n2) compound primes (primorial chain -- products of the template):")
    chain = primorial_chain(P)
    for p, c in zip(P, chain):
        print(f"   x{p:<6} -> {c}")

    print("\n3) YOUR TWIST -- leap ladder (1 = highest prime, count in massive leaps):")
    print(f"   {'count':>6} {'prime':>8} {'leap from prev':>16}")
    for i, p, leap in leap_ladder(P):
        print(f"   {i:>6} {p:>8} {('-' if leap == 0 else leap):>16}")

    # SCBE tie-in: the octave frequencies land near the Sacred-Tongue pitches.
    print("\nSCBE TIE-IN: f(n) scaled to audio sits right where the tongues already live --")
    print("   the six tongues carry harmonic_frequency (ko=440, av=523.25, ...);")
    print("   primes-as-octaves IS the sonification layer nsm_primes already gestures at.")
    print(f"   example: f(137) * 110 Hz = {freq_octave(137, P) * 110:.1f} Hz  (a real pitch)\n")


if __name__ == "__main__":
    main()
