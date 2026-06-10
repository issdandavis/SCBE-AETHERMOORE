#!/usr/bin/env python3
"""prime_rationed_lattice.py — Prime-Rationed Kinematic Lattice (PRKL).

A standalone tool for *prime-rationed moving geometry*: shapes whose sides can
move, scale, fold, or rotate, but whose lengths stay locked to prime-ratio rules.
Each edge carries a PRIME LABEL (its channel identity); its length is

    L_i(t) = p_i * s_i(t)

and motion is only valid if it preserves a chosen invariant. The point of the
tool is not to assert that "primes are special" — it is to MEASURE where the
prime-rationing does real work and where it is decoration. So, in the spirit of
the instrument family (scripts/research/instrument_family_for_geometric_claims.md),
this device ships with its own null hypotheses:

  NULL A (ratio identity): the claim "prime side-ratios resist simplification"
          is just COPRIMALITY. Any pairwise-coprime integer set keeps an
          irreducible ratio. => for plain ratio-locking, primes are DECORATIVE
          (a coprime composite set works identically).

  NULL B (Fermat angular gate): the claim "Fermat primes are constructible
          symmetry gates" is LOAD-BEARING and prime-specific. A regular p-gon
          is straightedge-compass constructible IFF p is a Fermat prime
          (p-1 a power of two). {3,5,17,257,65537} pass; 7,11,13,... fail.
          No coprime/composite substitute reproduces this.

  NULL C (straight-edge feasibility): widely-spread primes break the polygon
          inequality (3+5 < 17), so the prime line literally cannot close as a
          straight polygon past a point. That is the geometric boundary that
          forces the "use them as arc lengths / angular steps" move.

Verdict the tool returns: prime side-LENGTHS buy nothing over any coprime set
(NULL A), but prime ANGLES (Fermat) buy constructibility that nothing else does
(NULL B), and the straight/curved boundary is real and locatable (NULL C).

Usage:  PYTHONPATH=. python scripts/research/prime_rationed_lattice.py
Self-contained; reuses the verified sieve from nth_prime_baseline_gate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
import sys

# Reuse the verified prime engine (self-checking segmented sieve).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nth_prime_baseline_gate import simple_sieve  # noqa: E402

# Known Fermat primes F_k = 2^(2^k) + 1 for k = 0..4. (No others are known.)
FERMAT_PRIMES = (3, 5, 17, 257, 65537)


# --------------------------------------------------------------------------- #
# Prime predicates
# --------------------------------------------------------------------------- #
def is_power_of_two(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def is_prime(p: int) -> bool:
    if p < 2:
        return False
    # cheap, exact for our range; sieve is self-verified upstream.
    return p in set(simple_sieve(p + 1))


def is_fermat_prime(p: int) -> bool:
    """A regular p-gon is constructible IFF p is a Fermat prime.

    For a PRIME p > 2, p is Fermat iff (p - 1) is a power of two: any prime of
    the form 2^m + 1 forces m itself to be a power of two, giving p = 2^(2^k)+1.
    (p = 2 is excluded: 2 is not of the form 2^(2^k)+1.)
    """
    return p > 2 and is_prime(p) and is_power_of_two(p - 1)


# --------------------------------------------------------------------------- #
# The lattice
# --------------------------------------------------------------------------- #
@dataclass
class PrimeEdge:
    """One edge = one prime channel. Identity (prime) is fixed; scale moves."""

    prime: int
    scale: float = 1.0
    residue: int = 0  # for the modular-lane invariant

    def length(self) -> float:
        return self.prime * self.scale


@dataclass
class PrimeRationedLattice:
    """Edges labelled by primes; motion validated against an invariant."""

    edges: list[PrimeEdge] = field(default_factory=list)

    @classmethod
    def from_primes(cls, primes: list[int]) -> "PrimeRationedLattice":
        return cls(edges=[PrimeEdge(prime=p) for p in primes])

    def lengths(self) -> list[float]:
        return [e.length() for e in self.edges]

    # --- Invariant 1: ratio preservation (uniform scale keeps prime ratio) --- #
    def ratio_vector(self) -> list[Fraction]:
        """Exact L_i : L_j reduced. Under a uniform scale this == prime ratio."""
        lens = self.lengths()
        base = lens[0]
        return [Fraction(l).limit_denominator(10**9) / Fraction(base).limit_denominator(10**9) for l in lens]

    def prime_ratio_vector(self) -> list[Fraction]:
        p0 = self.edges[0].prime
        return [Fraction(e.prime, p0) for e in self.edges]

    def scale_uniform(self, s: float) -> None:
        """Move: scale every side by s. Preserves ratio invariant exactly."""
        for e in self.edges:
            e.scale *= s

    def ratio_preserved(self, tol: float = 1e-9) -> bool:
        rv = self.ratio_vector()
        pv = self.prime_ratio_vector()
        return all(abs(float(a) - float(b)) < tol for a, b in zip(rv, pv))

    # --- Invariant 3: product (prime-signature) preservation ----------------- #
    def length_product(self) -> float:
        prod = 1.0
        for l in self.lengths():
            prod *= l
        return prod

    def redistribute(self, i: int, j: int, factor: float) -> None:
        """Move length from edge j into edge i, keeping prod(L) constant."""
        self.edges[i].scale *= factor
        self.edges[j].scale /= factor

    # --- Invariant 2: modular residue lane ----------------------------------- #
    def set_residues(self) -> None:
        for e in self.edges:
            e.residue = int(round(e.length())) % e.prime

    def step_in_lane(self, i: int, k: int) -> None:
        """Move edge i by k whole prime-units; integer length stays in residue."""
        # length must be an integer multiple bump: add k * prime to the length
        e = self.edges[i]
        new_len = e.length() + k * e.prime
        e.scale = new_len / e.prime

    def residue_preserved(self) -> bool:
        return all(int(round(e.length())) % e.prime == e.residue for e in self.edges)


# --------------------------------------------------------------------------- #
# Geometry feasibility (NULL C)
# --------------------------------------------------------------------------- #
def polygon_feasible(side_ratio: list[int]) -> bool:
    """A closed planar polygon needs the longest side < sum of the others."""
    s = sorted(side_ratio)
    return s[-1] < sum(s[:-1])


def fermat_angular_steps(macro: int = 65537) -> dict[int, float]:
    """theta_i = 2*pi*p_i / macro — Fermat primes as angular steps in a macro-clock."""
    return {p: 2 * math.pi * p / macro for p in FERMAT_PRIMES}


# --------------------------------------------------------------------------- #
# NULL TESTS — where does the prime-rationing actually do work?
# --------------------------------------------------------------------------- #
def null_a_ratio_identity() -> dict:
    """Primes vs a coprime COMPOSITE set: does either ratio simplify? Neither.

    => the 'prime resists simplification' property is just coprimality; a
    coprime composite set (e.g. 8:9:25) is equally irreducible. DECORATIVE.
    """
    prime_set = [3, 5, 17]
    coprime_composite = [8, 9, 25]  # 2^3, 3^2, 5^2 — pairwise coprime, no primes
    not_coprime = [6, 8, 10]  # shares factor 2 -> collapses to 3:4:5

    def irreducible(v: list[int]) -> bool:
        g = 0
        for x in v:
            g = math.gcd(g, x)
        return g == 1

    return {
        "prime_set": prime_set,
        "prime_irreducible": irreducible(prime_set),
        "coprime_composite": coprime_composite,
        "coprime_composite_irreducible": irreducible(coprime_composite),
        "shares_factor_set": not_coprime,
        "shares_factor_irreducible": irreducible(not_coprime),
        "verdict": "DECORATIVE: primes match any pairwise-coprime set; only coprimality matters",
    }


def null_b_fermat_gate() -> dict:
    """Constructible regular p-gon iff p is Fermat. Prime-SPECIFIC and load-bearing."""
    primes = simple_sieve(300)
    constructible = [p for p in primes if is_fermat_prime(p)]
    not_constructible = [p for p in primes if not is_fermat_prime(p)][:8]
    return {
        "fermat_constructible_primes": constructible,
        "matches_known_fermat": constructible == [p for p in FERMAT_PRIMES if p < 300],
        "sample_non_constructible_primes": not_constructible,
        "verdict": "LOAD-BEARING: only Fermat primes give constructible angular gates; "
        "no coprime/composite substitute reproduces this",
    }


def null_c_feasibility_boundary() -> dict:
    """Locate where the straight prime line stops closing as a polygon."""
    return {
        "3:5:7_triangle_feasible": polygon_feasible([3, 5, 7]),  # 7 < 8  -> True
        "3:5:17_triangle_feasible": polygon_feasible([3, 5, 17]),  # 17 < 8 -> False
        "3:5:17:257_quad_feasible": polygon_feasible([3, 5, 17, 257]),  # 257 < 25 -> False
        "verdict": "REAL BOUNDARY: spread primes break the straight-edge inequality; "
        "past it, use them as arc lengths / angular steps (Fermat clock), not edges",
    }


# --------------------------------------------------------------------------- #
# Self-checks + report
# --------------------------------------------------------------------------- #
def _self_check() -> None:
    # Fermat predicate identifies exactly the known Fermat primes under 300.
    assert [p for p in simple_sieve(300) if is_fermat_prime(p)] == [3, 5, 17, 257]
    assert is_fermat_prime(65537) and not is_fermat_prime(7) and not is_fermat_prime(11)

    # Ratio invariant: uniform scaling keeps the prime ratio exactly.
    lat = PrimeRationedLattice.from_primes([3, 5, 7])
    lat.scale_uniform(123.456)
    assert lat.ratio_preserved(), "uniform scale must preserve prime ratio"

    # Product invariant: redistribution keeps prod(L) constant.
    lat2 = PrimeRationedLattice.from_primes([3, 5, 17])
    p_before = lat2.length_product()
    lat2.redistribute(0, 1, 2.0)
    assert abs(lat2.length_product() - p_before) < 1e-6, "product must be conserved"

    # Modular lane: stepping by whole prime-units keeps the residue.
    lat3 = PrimeRationedLattice.from_primes([3, 5, 7])
    lat3.set_residues()
    lat3.step_in_lane(2, 4)  # add 4*7 to the 7-channel
    assert lat3.residue_preserved(), "stepping by prime-units must keep residue lane"

    # Geometry boundary (NULL C) holds.
    assert polygon_feasible([3, 5, 7]) and not polygon_feasible([3, 5, 17])

    # NULL A: prime set and coprime-composite set are both irreducible.
    a = null_a_ratio_identity()
    assert a["prime_irreducible"] and a["coprime_composite_irreducible"]
    assert not a["shares_factor_irreducible"]

    # NULL B matches known Fermat list.
    assert null_b_fermat_gate()["matches_known_fermat"]


def main() -> int:
    _self_check()
    print("PRIME-RATIONED KINEMATIC LATTICE (PRKL)")
    print("=" * 64)

    print("\n[1] Moving triangle 3:5:7 — sides scale, prime ratio locked")
    lat = PrimeRationedLattice.from_primes([3, 5, 7])
    print(f"    t0 lengths = {lat.lengths()}   ratio = {[str(r) for r in lat.prime_ratio_vector()]}")
    lat.scale_uniform(10.0)
    print(f"    t1 lengths = {lat.lengths()}   ratio preserved = {lat.ratio_preserved()}")

    print("\n[2] Product invariant 3:5:17 — redistribute length, prime signature conserved")
    lat2 = PrimeRationedLattice.from_primes([3, 5, 17])
    print(f"    before prod(L) = {lat2.length_product():.3f}")
    lat2.redistribute(0, 1, 3.0)
    print(f"    after  prod(L) = {lat2.length_product():.3f}  (conserved)")

    print("\n[3] Fermat angular clock — theta_i = 2*pi*p_i / 65537 (constructible gates)")
    for p, th in fermat_angular_steps().items():
        print(f"    p={p:>6}  theta={th:.6e} rad   ({math.degrees(th):.6f} deg)")

    print("\n--- NULL HYPOTHESES (where the prime-rationing earns its keep) ---")
    a, b, c = null_a_ratio_identity(), null_b_fermat_gate(), null_c_feasibility_boundary()
    print(f"\nNULL A (side-length ratio): {a['verdict']}")
    print(
        f"    primes {a['prime_set']} irreducible={a['prime_irreducible']}; "
        f"coprime-composite {a['coprime_composite']} irreducible={a['coprime_composite_irreducible']}; "
        f"{a['shares_factor_set']} -> {a['shares_factor_irreducible']}"
    )
    print(f"\nNULL B (Fermat angular gate): {b['verdict']}")
    print(
        f"    constructible primes = {b['fermat_constructible_primes']}  "
        f"(matches known Fermat = {b['matches_known_fermat']})"
    )
    print(f"    non-constructible sample = {b['sample_non_constructible_primes']}")
    print(f"\nNULL C (straight-edge boundary): {c['verdict']}")
    print(
        f"    3:5:7 closes={c['3:5:7_triangle_feasible']}  "
        f"3:5:17 closes={c['3:5:17_triangle_feasible']}  "
        f"3:5:17:257 closes={c['3:5:17:257_quad_feasible']}"
    )

    print("\n" + "=" * 64)
    print("VERDICT: prime side-LENGTHS == any coprime set (NULL A, decorative).")
    print("         prime ANGLES (Fermat) buy constructibility nothing else does (NULL B).")
    print("         the straight->curved boundary is real and locatable (NULL C).")
    print("         => build the Fermat hierarchy as ANGULAR/arc gates, not straight edges.")
    print("\nself-checks: all passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
