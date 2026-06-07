"""Prime-coordinate abacus for integer navigation.

This module treats primes as a depth ruler rather than a predictor. A number is
mapped onto several computable coordinates:

    position      -> n
    prime anchor  -> pi(n), previous/next prime, anchor gaps
    material      -> big Omega and little omega
    structure     -> prime factor vector
    direction     -> residues on nested wheel bases

The output can be rendered as Polly Pad abacus layers or used directly by
agents that need an auditable number-series feature surface.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from typing import Sequence

DEFAULT_RESIDUE_BASES = (30, 210, 2310)
SCHEMA_VERSION = "geoseed_prime_coordinate_v1"


@dataclass(frozen=True)
class PrimeCoordinate:
    """Structural coordinate for one integer on the counting line."""

    schema_version: str
    n: int
    is_prime: bool
    prime_index: int
    anchor_prime: int | None
    next_prime: int
    gap_to_anchor: int | None
    gap_to_next: int
    big_omega: int
    little_omega: int
    factor_vector: dict[str, int]
    residues: dict[str, int]
    wheel_units: dict[str, bool]
    log_n: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PrimeCoordinateAbacus:
    """Abacus-ready view of a prime coordinate."""

    schema_version: str
    coordinate: PrimeCoordinate
    layers: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "coordinate": self.coordinate.to_dict(),
            "layers": list(self.layers),
        }


def build_prime_coordinate(
    n: int,
    *,
    residue_bases: Sequence[int] = DEFAULT_RESIDUE_BASES,
) -> PrimeCoordinate:
    """Build the coordinate tuple for one positive integer."""
    if n < 1:
        raise ValueError("n must be a positive integer")
    if any(base < 2 for base in residue_bases):
        raise ValueError("residue bases must be >= 2")

    factors = factorize(n)
    is_prime = n >= 2 and factors == {n: 1}
    prime_index = prime_pi(n)
    anchor = previous_prime(n)
    next_p = next_prime_after(n)
    residues = {f"mod{base}": n % base for base in residue_bases}
    wheel_units = {f"mod{base}": math.gcd(n, base) == 1 for base in residue_bases}

    return PrimeCoordinate(
        schema_version=SCHEMA_VERSION,
        n=n,
        is_prime=is_prime,
        prime_index=prime_index,
        anchor_prime=anchor,
        next_prime=next_p,
        gap_to_anchor=None if anchor is None else n - anchor,
        gap_to_next=next_p - n,
        big_omega=sum(factors.values()),
        little_omega=len(factors),
        factor_vector={f"p{prime}": exp for prime, exp in sorted(factors.items())},
        residues=residues,
        wheel_units=wheel_units,
        log_n=round(math.log(n), 12),
    )


def build_prime_coordinate_abacus(
    n: int,
    *,
    residue_bases: Sequence[int] = DEFAULT_RESIDUE_BASES,
) -> PrimeCoordinateAbacus:
    """Build three abacus layers for anchor, factor depth, and residue compass."""
    coordinate = build_prime_coordinate(n, residue_bases=residue_bases)
    return PrimeCoordinateAbacus(
        schema_version="geoseed_prime_coordinate_abacus_v1",
        coordinate=coordinate,
        layers=(
            _anchor_layer(coordinate),
            _factor_layer(coordinate),
            _residue_layer(coordinate),
        ),
    )


def factorize(n: int) -> dict[int, int]:
    """Return prime factor exponents for a positive integer."""
    if n < 1:
        raise ValueError("n must be a positive integer")
    if n == 1:
        return {}

    remainder = n
    factors: dict[int, int] = {}
    for prime in _small_primes_upto(math.isqrt(n) + 1):
        if prime * prime > remainder:
            break
        while remainder % prime == 0:
            factors[prime] = factors.get(prime, 0) + 1
            remainder //= prime
    if remainder > 1:
        factors[remainder] = factors.get(remainder, 0) + 1
    return factors


def prime_pi(n: int) -> int:
    """Count primes <= n with a deterministic sieve."""
    if n < 2:
        return 0
    return len(_small_primes_upto(n))


def previous_prime(n: int) -> int | None:
    """Return the largest prime <= n, or None when no anchor exists."""
    if n < 2:
        return None
    primes = _small_primes_upto(n)
    return primes[-1] if primes else None


def next_prime_after(n: int) -> int:
    """Return the smallest prime strictly greater than n."""
    candidate = max(2, n + 1)
    while not is_prime(candidate):
        candidate += 1
    return candidate


def is_prime(n: int) -> bool:
    """Small deterministic primality check for coordinate construction."""
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    limit = math.isqrt(n)
    factor = 5
    while factor <= limit:
        if n % factor == 0 or n % (factor + 2) == 0:
            return False
        factor += 6
    return True


def _small_primes_upto(limit: int) -> list[int]:
    if limit < 2:
        return []
    sieve = bytearray(b"\x01") * (limit + 1)
    sieve[0:2] = b"\x00\x00"
    root = math.isqrt(limit)
    for value in range(2, root + 1):
        if sieve[value]:
            start = value * value
            sieve[start : limit + 1 : value] = b"\x00" * (
                ((limit - start) // value) + 1
            )
    return [value for value, flag in enumerate(sieve) if flag]


def _anchor_layer(coordinate: PrimeCoordinate) -> dict[str, object]:
    return {
        "id": f"prime-coordinate-anchor-{coordinate.n}",
        "name": f"Prime Coordinate Anchor {coordinate.n}",
        "rows": [
            _row("position", "position n", 1, coordinate.n),
            _row("prime-index", "prime progress pi(n)", 1, coordinate.prime_index),
            _row("anchor-gap", "gap to prime anchor", 1, coordinate.gap_to_anchor or 0),
            _row("next-gap", "gap to next prime", 1, coordinate.gap_to_next),
            _row("big-omega", "material depth Omega(n)", 1, coordinate.big_omega),
            _row(
                "little-omega",
                "distinct factor count omega(n)",
                1,
                coordinate.little_omega,
            ),
        ],
    }


def _factor_layer(coordinate: PrimeCoordinate) -> dict[str, object]:
    rows = [
        _row(key, f"{key} exponent", int(key[1:]), count)
        for key, count in coordinate.factor_vector.items()
    ]
    if not rows:
        rows = [_row("unit", "unit / no prime material", 1, 0)]
    return {
        "id": f"prime-factor-vector-{coordinate.n}",
        "name": f"Prime Factor Vector {coordinate.n}",
        "rows": rows,
    }


def _residue_layer(coordinate: PrimeCoordinate) -> dict[str, object]:
    rows = []
    for key, residue in coordinate.residues.items():
        unit = coordinate.wheel_units[key]
        label = f"{key} residue" + (" unit lane" if unit else " scaffold lane")
        rows.append(_row(key, label, 1, residue))
    return {
        "id": f"prime-residue-compass-{coordinate.n}",
        "name": f"Prime Residue Compass {coordinate.n}",
        "rows": rows,
    }


def _row(row_id: str, label: str, value: int, count: int) -> dict[str, object]:
    return {
        "id": row_id,
        "label": label,
        "value": value,
        "count": count,
        "maxCount": max(12, count),
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a prime-coordinate abacus for a positive integer."
    )
    parser.add_argument("n", type=int, help="positive integer to map")
    parser.add_argument(
        "--bases",
        default="30,210,2310",
        help="comma-separated residue bases",
    )
    parser.add_argument("--json", action="store_true", help="emit full JSON payload")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    try:
        bases = tuple(
            int(part.strip()) for part in args.bases.split(",") if part.strip()
        )
        abacus = build_prime_coordinate_abacus(args.n, residue_bases=bases)
    except ValueError as exc:
        parser.error(str(exc))
    payload = abacus.to_dict()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        coord = abacus.coordinate
        print(
            json.dumps(
                {
                    "n": coord.n,
                    "prime_index": coord.prime_index,
                    "anchor_prime": coord.anchor_prime,
                    "gap_to_anchor": coord.gap_to_anchor,
                    "big_omega": coord.big_omega,
                    "little_omega": coord.little_omega,
                    "is_prime": coord.is_prime,
                    "residues": coord.residues,
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


__all__ = [
    "DEFAULT_RESIDUE_BASES",
    "SCHEMA_VERSION",
    "PrimeCoordinate",
    "PrimeCoordinateAbacus",
    "build_prime_coordinate",
    "build_prime_coordinate_abacus",
    "factorize",
    "is_prime",
    "next_prime_after",
    "previous_prime",
    "prime_pi",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
