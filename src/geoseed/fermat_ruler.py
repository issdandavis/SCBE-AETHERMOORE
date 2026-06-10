from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

from src.geoseed.prime_coordinate_abacus import factorize, is_prime

FERMAT_UNIT = 65537
FERMAT_BINARY_BLOCK = 1 << 16
KNOWN_FERMAT_ODD_PRIMES = (3, 5, 17, 257, 65537)
FERMAT_GENERATORS = (2, *KNOWN_FERMAT_ODD_PRIMES)
SCHEMA_VERSION = "geoseed_fermat_ruler_v1"


@dataclass(frozen=True)
class FermatCoordinate:
    schema_version: str
    n: int
    unit: int
    quotient: int
    residue: int
    block_shift: int
    low_sum: int
    carry16: int
    binary_high: int
    binary_low: int
    binary_high_expected: int
    binary_low_expected: int
    diagonal_identity_holds: bool
    is_on_spine: bool
    is_prime: bool
    fermat_generated: bool
    factor_vector: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FermatOperationReport:
    schema_version: str
    unit: int
    left: FermatCoordinate
    right: FermatCoordinate
    sum_coordinate: FermatCoordinate
    product_coordinate: FermatCoordinate
    sum_pair: tuple[int, int]
    product_pair: tuple[int, int]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "unit": self.unit,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "sum_coordinate": self.sum_coordinate.to_dict(),
            "product_coordinate": self.product_coordinate.to_dict(),
            "sum_pair": list(self.sum_pair),
            "product_pair": list(self.product_pair),
        }


@dataclass(frozen=True)
class FermatPrimeResidueSample:
    schema_version: str
    unit: int
    limit: int
    total_primes: int
    zero_residue_primes: tuple[int, ...]
    occupied_nonzero_lanes: int
    top_lanes: tuple[dict[str, int], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "unit": self.unit,
            "limit": self.limit,
            "total_primes": self.total_primes,
            "zero_residue_primes": list(self.zero_residue_primes),
            "occupied_nonzero_lanes": self.occupied_nonzero_lanes,
            "top_lanes": list(self.top_lanes),
        }


@dataclass(frozen=True)
class FermatSemigroupSummary:
    schema_version: str
    unit: int
    limit: int
    total_members: int
    first_members: tuple[int, ...]
    sample_coordinates: tuple[FermatCoordinate, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "unit": self.unit,
            "limit": self.limit,
            "total_members": self.total_members,
            "first_members": list(self.first_members),
            "sample_coordinates": [coordinate.to_dict() for coordinate in self.sample_coordinates],
        }


def build_fermat_coordinate(n: int) -> FermatCoordinate:
    if n < 0:
        raise ValueError("n must be a nonnegative integer")
    quotient, residue = divmod(n, FERMAT_UNIT)
    low_sum = quotient + residue
    carry16 = low_sum >> 16
    binary_high_expected = quotient + carry16
    binary_low_expected = low_sum & (FERMAT_BINARY_BLOCK - 1)
    binary_high = n >> 16
    binary_low = n & (FERMAT_BINARY_BLOCK - 1)
    factors = factorize(n) if n > 0 else {}
    factor_vector = {f"p{prime}": exp for prime, exp in sorted(factors.items())}
    return FermatCoordinate(
        schema_version=SCHEMA_VERSION,
        n=n,
        unit=FERMAT_UNIT,
        quotient=quotient,
        residue=residue,
        block_shift=quotient * FERMAT_BINARY_BLOCK,
        low_sum=low_sum,
        carry16=carry16,
        binary_high=binary_high,
        binary_low=binary_low,
        binary_high_expected=binary_high_expected,
        binary_low_expected=binary_low_expected,
        diagonal_identity_holds=(binary_high == binary_high_expected and binary_low == binary_low_expected),
        is_on_spine=(residue == 0),
        is_prime=is_prime(n),
        fermat_generated=is_fermat_generated(n, factors=factors),
        factor_vector=factor_vector,
    )


def recompose_fermat_pair(quotient: int, residue: int) -> int:
    if quotient < 0 or residue < 0:
        raise ValueError("quotient and residue must be nonnegative")
    if residue >= FERMAT_UNIT:
        raise ValueError("residue must be less than the Fermat unit")
    return quotient * FERMAT_UNIT + residue


def add_fermat_pairs(left: tuple[int, int], right: tuple[int, int]) -> tuple[int, int]:
    q = left[0] + right[0]
    r = left[1] + right[1]
    carry, residue = divmod(r, FERMAT_UNIT)
    return q + carry, residue


def multiply_fermat_pairs(left: tuple[int, int], right: tuple[int, int]) -> tuple[int, int]:
    q1, r1 = left
    q2, r2 = right
    residue_product = r1 * r2
    carry, residue = divmod(residue_product, FERMAT_UNIT)
    quotient = q1 * q2 * FERMAT_UNIT + q1 * r2 + q2 * r1 + carry
    return quotient, residue


def build_operation_report(left_n: int, right_n: int) -> FermatOperationReport:
    left = build_fermat_coordinate(left_n)
    right = build_fermat_coordinate(right_n)
    sum_pair = add_fermat_pairs((left.quotient, left.residue), (right.quotient, right.residue))
    product_pair = multiply_fermat_pairs((left.quotient, left.residue), (right.quotient, right.residue))
    return FermatOperationReport(
        schema_version="geoseed_fermat_ruler_ops_v1",
        unit=FERMAT_UNIT,
        left=left,
        right=right,
        sum_coordinate=build_fermat_coordinate(left_n + right_n),
        product_coordinate=build_fermat_coordinate(left_n * right_n),
        sum_pair=sum_pair,
        product_pair=product_pair,
    )


def build_prime_residue_sample(limit: int, *, top: int = 8) -> FermatPrimeResidueSample:
    if limit < 2:
        raise ValueError("limit must be at least 2")
    if top < 1:
        raise ValueError("top must be at least 1")
    primes = _primes_upto(limit)
    counts = Counter(prime % FERMAT_UNIT for prime in primes)
    zero_residue_primes = tuple(prime for prime in primes if prime % FERMAT_UNIT == 0)
    lanes = sorted(
        (
            {"residue": residue, "count": count}
            for residue, count in counts.items()
            if residue != 0
        ),
        key=lambda item: (-item["count"], item["residue"]),
    )
    return FermatPrimeResidueSample(
        schema_version="geoseed_fermat_prime_residue_sample_v1",
        unit=FERMAT_UNIT,
        limit=limit,
        total_primes=len(primes),
        zero_residue_primes=zero_residue_primes,
        occupied_nonzero_lanes=len(lanes),
        top_lanes=tuple(lanes[:top]),
    )


def enumerate_fermat_generated(limit: int) -> tuple[int, ...]:
    if limit < 1:
        raise ValueError("limit must be at least 1")
    values: set[int] = set()

    def walk(index: int, current: int) -> None:
        if index == len(FERMAT_GENERATORS):
            values.add(current)
            return
        generator = FERMAT_GENERATORS[index]
        value = current
        while value <= limit:
            walk(index + 1, value)
            if value > limit // generator:
                break
            value *= generator

    walk(0, 1)
    return tuple(sorted(values))


def build_fermat_semigroup_summary(limit: int, *, sample: int = 16) -> FermatSemigroupSummary:
    if sample < 1:
        raise ValueError("sample must be at least 1")
    values = enumerate_fermat_generated(limit)
    first_members = values[:sample]
    return FermatSemigroupSummary(
        schema_version="geoseed_fermat_semigroup_summary_v1",
        unit=FERMAT_UNIT,
        limit=limit,
        total_members=len(values),
        first_members=first_members,
        sample_coordinates=tuple(build_fermat_coordinate(value) for value in first_members),
    )


def is_fermat_generated(n: int, *, factors: dict[int, int] | None = None) -> bool:
    if n < 1:
        return False
    active_factors = factors if factors is not None else factorize(n)
    return all(prime in FERMAT_GENERATORS for prime in active_factors)


def _primes_upto(limit: int) -> list[int]:
    sieve = bytearray([1]) * (limit + 1)
    sieve[0:2] = b"\x00\x00"
    root = int(limit**0.5)
    for value in range(2, root + 1):
        if sieve[value]:
            start = value * value
            sieve[start : limit + 1 : value] = b"\x00" * (((limit - start) // value) + 1)
    return [value for value, flag in enumerate(sieve) if flag]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="65537 Fermat ruler and coordinate tool.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_coordinate = sub.add_parser("coordinate", help="Build Fermat coordinates for one integer.")
    p_coordinate.add_argument("n", type=int)
    p_coordinate.add_argument("--json", action="store_true")

    p_ops = sub.add_parser("ops", help="Show addition and multiplication on Fermat pairs.")
    p_ops.add_argument("--left", type=int, required=True)
    p_ops.add_argument("--right", type=int, required=True)
    p_ops.add_argument("--json", action="store_true")

    p_primes = sub.add_parser("primes", help="Sample prime residues modulo 65537.")
    p_primes.add_argument("--limit", type=int, required=True)
    p_primes.add_argument("--top", type=int, default=8)
    p_primes.add_argument("--json", action="store_true")

    p_semigroup = sub.add_parser("semigroup", help="Enumerate Fermat-generated numbers up to a limit.")
    p_semigroup.add_argument("--limit", type=int, required=True)
    p_semigroup.add_argument("--sample", type=int, default=16)
    p_semigroup.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "coordinate":
        payload = build_fermat_coordinate(args.n).to_dict()
    elif args.command == "ops":
        payload = build_operation_report(args.left, args.right).to_dict()
    elif args.command == "primes":
        payload = build_prime_residue_sample(args.limit, top=args.top).to_dict()
    elif args.command == "semigroup":
        payload = build_fermat_semigroup_summary(args.limit, sample=args.sample).to_dict()
    else:
        parser.error(f"unknown command: {args.command}")

    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


__all__ = [
    "FERMAT_BINARY_BLOCK",
    "FERMAT_GENERATORS",
    "FERMAT_UNIT",
    "KNOWN_FERMAT_ODD_PRIMES",
    "SCHEMA_VERSION",
    "FermatCoordinate",
    "FermatOperationReport",
    "FermatPrimeResidueSample",
    "FermatSemigroupSummary",
    "add_fermat_pairs",
    "build_fermat_coordinate",
    "build_fermat_semigroup_summary",
    "build_operation_report",
    "build_prime_residue_sample",
    "enumerate_fermat_generated",
    "is_fermat_generated",
    "main",
    "multiply_fermat_pairs",
    "recompose_fermat_pair",
]


if __name__ == "__main__":
    raise SystemExit(main())
