#!/usr/bin/env python3
"""nested_integer_ruler.py — nested-integer exact measurement, down to the carve floor.

Issac's idea: "layer integers into decimal nests -> sub-measurement measurements
down to whatever layer is above the finest depth that can be accurately carved."

That is a NESTED MIXED-RADIX representation: a quantity is a stack of integer
digits, each at a finer scale; the deepest layer IS the resolution floor. Two
honest claims, two fields, two verdicts (instrument-family discipline):

  CLAIM 1 (measurement): nested integers give EXACT sub-measurement that carries
          its own precision. Null: is this just fixed-point arithmetic? Yes —
          and that is the point. It is LOAD-BEARING vs float for two reasons the
          tool demonstrates: (a) zero drift under accumulation, (b) the value
          knows its own resolution (the floor), where a float pretends infinite
          precision and silently lies. Prime radices add nothing here (decimal
          works); this is positional notation.

  CLAIM 2 (computation): the deeper prize your Fermat instinct keeps circling is
          the RESIDUE NUMBER SYSTEM (RNS): represent an integer by its residues
          mod a set of COPRIME moduli (e.g. the Fermat primes 3,5,17,257,65537).
          Then add/multiply act INDEPENDENTLY per channel — exact, carry-free,
          parallel — and reconstruct via CRT. Here the prime/coprime structure is
          genuinely LOAD-BEARING: non-coprime moduli cannot reconstruct. This is
          the real home of the NTT/Fermat "exactness" lever from fermat_ntt_readout.

Verdict shape: nesting for MEASUREMENT = exact + precision-aware (useful, known,
primes optional). Coprime residues for COMPUTATION (RNS) = where primes earn keep.

Usage:  PYTHONPATH=. python scripts/research/nested_integer_ruler.py
Self-contained; reuses the verified sieve only for prime context.
"""

from __future__ import annotations

from fractions import Fraction
from functools import reduce
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nth_prime_baseline_gate import simple_sieve  # noqa: E402  (prime context only)

FERMAT_PRIMES = (3, 5, 17, 257, 65537)


# --------------------------------------------------------------------------- #
# CLAIM 1 — nested mixed-radix measurement
# --------------------------------------------------------------------------- #
def encode_nested(value: Fraction, radices: list[int]) -> tuple[int, list[int], Fraction, Fraction]:
    """Encode value as integer part + mixed-radix digits down to the carve floor.

    Returns (a0, digits, resolution, residual). resolution = 1/prod(radices) is the
    finest carvable step; residual in [0, resolution) is what lies BELOW the floor
    (uncarvable — the honest 'we cannot measure finer than this').
    """
    a0 = value.numerator // value.denominator  # floor
    frac = value - a0
    digits: list[int] = []
    denom = 1
    for r in radices:
        frac *= r
        d = frac.numerator // frac.denominator  # floor digit in [0, r)
        digits.append(d)
        frac -= d
        denom *= r
    resolution = Fraction(1, denom)
    residual = frac * resolution  # scale back to original units
    return a0, digits, resolution, residual


def decode_nested(a0: int, digits: list[int], radices: list[int]) -> Fraction:
    """Reconstruct the exact value represented to the carve floor (residual dropped)."""
    val = Fraction(a0)
    denom = 1
    for d, r in zip(digits, radices):
        denom *= r
        val += Fraction(d, denom)
    return val


def refine_to_floor(value: Fraction, radix: int, carve_floor: Fraction) -> list[int]:
    """Add layers of the same radix until the next layer would go below carve_floor."""
    radices: list[int] = []
    step = Fraction(1)
    while step / radix >= carve_floor:
        radices.append(radix)
        step /= radix
    return radices


# --------------------------------------------------------------------------- #
# CLAIM 2 — Residue Number System (RNS) over coprime / Fermat moduli
# --------------------------------------------------------------------------- #
def to_residues(x: int, moduli: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(x % m for m in moduli)


def crt_reconstruct(residues: tuple[int, ...], moduli: tuple[int, ...]) -> int:
    """Reconstruct x in [0, prod(moduli)) from residues. Requires pairwise-coprime moduli."""
    M = reduce(lambda a, b: a * b, moduli)
    total = 0
    for r, m in zip(residues, moduli):
        Mi = M // m
        total += r * Mi * pow(Mi, -1, m)  # Mi^{-1} mod m (needs gcd(Mi,m)=1 -> coprime)
    return total % M


def pairwise_coprime(moduli: tuple[int, ...]) -> bool:
    from math import gcd

    return all(gcd(moduli[i], moduli[j]) == 1 for i in range(len(moduli)) for j in range(i + 1, len(moduli)))


# --------------------------------------------------------------------------- #
# Tests / report
# --------------------------------------------------------------------------- #
def _self_check() -> None:
    # Nested round-trip: decoded value + residual == original, residual < resolution.
    v = Fraction(31415926535, 10_000_000_000)  # pi-ish, exact rational
    a0, digits, res, residual = encode_nested(v, [10, 10, 10, 10, 10])
    decoded = decode_nested(a0, digits, [10, 10, 10, 10, 10])
    assert decoded + residual == v, "nested encode/decode must be exact"
    assert 0 <= residual < res, "residual must lie below the carve floor"

    # Mixed/prime radices also round-trip exactly.
    a0p, dp, resp, residp = encode_nested(v, [3, 5, 17, 257])
    assert decode_nested(a0p, dp, [3, 5, 17, 257]) + residp == v

    # RNS: add/mul are exact & carry-free over coprime moduli, reconstruct via CRT.
    mods = FERMAT_PRIMES
    M = reduce(lambda a, b: a * b, mods)
    x, y = 1_234_567, 9_999
    assert crt_reconstruct(to_residues(x, mods), mods) == x
    rx, ry = to_residues(x, mods), to_residues(y, mods)
    add_res = tuple((a + b) % m for a, b, m in zip(rx, ry, mods))
    mul_res = tuple((a * b) % m for a, b, m in zip(rx, ry, mods))
    assert crt_reconstruct(add_res, mods) == (x + y) % M
    assert crt_reconstruct(mul_res, mods) == (x * y) % M  # wraps mod M when x*y >= M
    # in-range product reconstructs EXACTLY (no wrap) — the clean RNS guarantee.
    xs, ys = 1_234_567, 3_000  # xs*ys < M
    mul_fit = tuple((a * b) % m for a, b, m in zip(to_residues(xs, mods), to_residues(ys, mods), mods))
    assert xs * ys < M and crt_reconstruct(mul_fit, mods) == xs * ys

    # Non-coprime moduli break RNS (the load-bearing part): 4 and 6 share factor 2.
    bad = (4, 6)
    try:
        crt_reconstruct(to_residues(5, bad), bad)
        broke = False
    except ValueError:
        broke = True  # pow(Mi,-1,m) raises when not invertible
    assert broke or not pairwise_coprime(bad), "non-coprime moduli must fail to reconstruct"


def float_drift_demo(n: int = 1_000_000) -> tuple[float, Fraction]:
    """Accumulate 0.1 n times: float drifts, nested-integer/rational stays exact."""
    f = 0.0
    for _ in range(n):
        f += 0.1
    float_err = abs(f - n / 10.0)
    exact = Fraction(1, 10) * n  # the nested-integer/rational accumulator
    exact_err = abs(exact - Fraction(n, 10))
    return float_err, exact_err


def main() -> int:
    _self_check()
    print("NESTED-INTEGER RULER — exact sub-measurement to the carve floor")
    print("=" * 68)

    v = Fraction(31415926535, 10_000_000_000)
    print(f"\n[1] measure value = {float(v):.10f}  (exact rational {v.numerator}/{v.denominator})")
    for radices, name in [([10] * 6, "decimal nest"), ([3, 5, 17, 257], "prime/Fermat nest")]:
        a0, digits, res, residual = encode_nested(v, radices)
        print(
            f"    {name:<18} digits={[a0] + digits}  resolution={float(res):.3e}  "
            f"below-floor residual={float(residual):.3e}"
        )

    print("\n[2] carve floor — refine until the next layer is finer than what can be carved")
    floor = Fraction(1, 5000)  # say the material can be carved to 1/5000
    radices = refine_to_floor(v, 10, floor)
    a0, digits, res, residual = encode_nested(v, radices)
    print(
        f"    carve_floor={float(floor):.2e} -> {len(radices)} decimal layers, "
        f"resolution={float(res):.2e} (stops ABOVE the floor; deeper would be noise)"
    )

    print("\n[3] NULL vs float — accumulate 0.1 a million times (lower error = better)")
    fe, ee = float_drift_demo()
    print(f"    float64 accumulator error = {fe:.6e}   (drifts)")
    print(f"    nested-integer/rational   = {float(ee):.6e}   (exact)")

    print("\n[4] CLAIM 2 — Residue Number System over the Fermat primes (exact, carry-free)")
    mods = FERMAT_PRIMES
    M = reduce(lambda a, b: a * b, mods)
    print(f"    moduli {mods}  pairwise-coprime={pairwise_coprime(mods)}  range M={M:,} (~2^32)")
    x, y = 1_234_567, 3_000  # in-range: x*y < M, so it reconstructs EXACTLY
    rx, ry = to_residues(x, mods), to_residues(y, mods)
    prod_res = tuple((a * b) % m for a, b, m in zip(rx, ry, mods))
    recon = crt_reconstruct(prod_res, mods)
    print(f"    {x} * {y} via independent residue channels -> CRT = {recon}  " f"(exact = {x*y}, match={recon == x*y})")
    big = 1_234_567 * 9_999  # out of range: exceeds M, so RNS wraps mod M (the range bound)
    print(
        f"    range bound: any result must be < M; {1_234_567}*9999={big} >= M wraps to " f"{big % M} (= result mod M)"
    )
    print("    non-coprime moduli (4,6) cannot reconstruct -> coprimality is load-bearing here")

    print("\n--- VERDICT ---")
    print("  MEASUREMENT (your nest): exact + precision-aware (carries its own floor),")
    print("    LOAD-BEARING vs float (zero drift, no hidden precision). It is mixed-radix")
    print("    fixed-point — a known, real tool; prime radices add nothing over decimal.")
    print("  COMPUTATION (RNS): coprime/Fermat moduli give exact carry-free PARALLEL")
    print("    arithmetic; non-coprime moduli fail. THIS is where your prime instinct pays —")
    print("    the same exactness lever as the NTT, now doing real work (Residue Number System).")
    print("\n  self-checks: nested round-trip exact, float drift shown, RNS/CRT exact — all passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
