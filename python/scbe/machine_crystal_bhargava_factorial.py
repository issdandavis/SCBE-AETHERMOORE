"""Bhargava-factorial layer for the Machine Crystal.

Bhargava's work goes beyond cubes. One separate thread is the generalized
factorial: for a set S of integers, define k!_S so many factorial theorems keep
working after replacing the ordinary factorial by k!_S.

This module implements exact, local surfaces we can validate without pretending
to implement the full p-ordering theory for arbitrary infinite sets:

* S = Z: k!_S = k!
* S = aZ + b: k!_S = |a|^k k!

It also maps the first eight generalized factorials onto the Machine Crystal's
8-address cube and verifies the Bhargava-cube discriminant invariant there.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import factorial, prod
import json
from pathlib import Path

from .machine_crystal_bhargava import BhargavaCube


class BhargavaFactorialError(ValueError):
    """Invalid generalized factorial input."""


def _primes_upto(n: int) -> list[int]:
    if n < 2:
        return []
    sieve = [True] * (n + 1)
    sieve[0] = sieve[1] = False
    for p in range(2, int(n**0.5) + 1):
        if sieve[p]:
            for q in range(p * p, n + 1, p):
                sieve[q] = False
    return [i for i, ok in enumerate(sieve) if ok]


def p_adic_valuation_factorial(k: int, p: int) -> int:
    """Legendre valuation v_p(k!)."""

    if k < 0:
        raise BhargavaFactorialError("k must be non-negative")
    if p < 2:
        raise BhargavaFactorialError("p must be prime-like and >= 2")
    total = 0
    power = p
    while power <= k:
        total += k // power
        power *= p
    return total


def ordinary_factorial_from_prime_powers(k: int) -> int:
    """Reconstruct k! from prime-power valuation factors."""

    if k < 0:
        raise BhargavaFactorialError("k must be non-negative")
    return prod(p ** p_adic_valuation_factorial(k, p) for p in _primes_upto(k))


def bhargava_factorial_z(k: int) -> int:
    """Bhargava factorial for S = Z."""

    if k < 0:
        raise BhargavaFactorialError("k must be non-negative")
    return factorial(k)


def bhargava_factorial_arithmetic_progression(k: int, step: int, offset: int = 0) -> int:
    """Bhargava factorial for S = {step*n + offset | n in Z}.

    The offset does not affect pairwise differences, so only ``step`` matters.
    """

    if k < 0:
        raise BhargavaFactorialError("k must be non-negative")
    if step == 0:
        raise BhargavaFactorialError("arithmetic progression step must be nonzero")
    return (abs(int(step)) ** k) * factorial(k)


@dataclass(frozen=True, slots=True)
class FactorialProfile:
    """A named generalized factorial surface."""

    name: str
    values: tuple[int, ...]

    def cube(self) -> BhargavaCube:
        if len(self.values) < 8:
            raise BhargavaFactorialError("need at least 8 values for cube overlay")
        return BhargavaCube.from_iterable(self.values[:8])

    def packet(self) -> dict:
        cube = self.cube()
        return {
            "name": self.name,
            "values": list(self.values),
            "first_eight_cube": cube.packet(),
            "cube_equal_discriminants": cube.equal_discriminants(),
        }


def factorial_profile(kind: str, *, n: int = 8, step: int = 1, offset: int = 0) -> FactorialProfile:
    """Build a finite receipt profile for a supported generalized factorial."""

    if n < 0:
        raise BhargavaFactorialError("n must be non-negative")
    if kind == "Z":
        return FactorialProfile("Z", tuple(bhargava_factorial_z(k) for k in range(n + 1)))
    if kind == "arithmetic_progression":
        name = f"{step}Z+{offset}"
        return FactorialProfile(
            name,
            tuple(bhargava_factorial_arithmetic_progression(k, step, offset) for k in range(n + 1)),
        )
    raise BhargavaFactorialError(f"unsupported factorial profile kind: {kind!r}")


def divisibility_checks(values: tuple[int, ...]) -> list[dict]:
    """Check (m+n)!_S is divisible by m!_S n!_S where values are available."""

    checks = []
    for m in range(len(values)):
        for n in range(len(values)):
            if m + n >= len(values):
                continue
            denom = values[m] * values[n]
            ok = denom != 0 and values[m + n] % denom == 0
            checks.append({"m": m, "n": n, "ok": ok})
    return checks


def bhargava_factorial_receipt() -> dict:
    """Validate exact generalized-factorial surfaces we support."""

    z_profile = factorial_profile("Z", n=12)
    even_profile = factorial_profile("arithmetic_progression", n=12, step=2, offset=0)
    three_plus_one = factorial_profile("arithmetic_progression", n=12, step=3, offset=1)

    z_prime_power_ok = all(
        ordinary_factorial_from_prime_powers(k) == bhargava_factorial_z(k)
        for k in range(13)
    )
    z_div = divisibility_checks(z_profile.values)
    even_div = divisibility_checks(even_profile.values)
    three_div = divisibility_checks(three_plus_one.values)

    checks = {
        "z_prime_power_reconstructs_factorial_0_to_12": z_prime_power_ok,
        "z_divisibility_law": all(item["ok"] for item in z_div),
        "even_formula_2_power_k_times_k_factorial": all(
            even_profile.values[k] == (2**k) * factorial(k) for k in range(13)
        ),
        "even_divisibility_law": all(item["ok"] for item in even_div),
        "three_plus_one_formula_step_only": all(
            three_plus_one.values[k] == (3**k) * factorial(k) for k in range(13)
        ),
        "three_plus_one_divisibility_law": all(item["ok"] for item in three_div),
        "z_cube_equal_discriminants": z_profile.cube().equal_discriminants(),
        "even_cube_equal_discriminants": even_profile.cube().equal_discriminants(),
        "three_plus_one_cube_equal_discriminants": three_plus_one.cube().equal_discriminants(),
    }

    return {
        "schema": "scbe_machine_crystal_bhargava_factorial_v1",
        "claim": "Bhargava factorial surfaces for Z and arithmetic progressions feed values into the Machine Crystal 8-cube while preserving validated factorial divisibility and cube discriminant invariants.",
        "profiles": [z_profile.packet(), even_profile.packet(), three_plus_one.packet()],
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "honest_boundary": "Supports exact Z and arithmetic-progression formulas only; arbitrary-set p-orderings are research backlog.",
    }


def main() -> int:
    receipt = bhargava_factorial_receipt()
    out_dir = Path("artifacts/machine_crystal")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "bhargava_factorial.json"
    out_path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["verdict"] == "PASS" else 1


__all__ = [
    "BhargavaFactorialError",
    "FactorialProfile",
    "bhargava_factorial_arithmetic_progression",
    "bhargava_factorial_receipt",
    "bhargava_factorial_z",
    "divisibility_checks",
    "factorial_profile",
    "ordinary_factorial_from_prime_powers",
    "p_adic_valuation_factorial",
]


if __name__ == "__main__":
    raise SystemExit(main())
