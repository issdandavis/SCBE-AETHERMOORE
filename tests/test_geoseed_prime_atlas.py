from __future__ import annotations

import math
from dataclasses import fields

import pytest

from src.geoseed.prime_atlas import (
    COORDINATE_STATUS,
    RESIDUE_PRIMES,
    WHEEL_MODULUS,
    PrimeAddress,
    alignment_vs_null,
    build_prime_atlas,
    build_prime_seed_region,
    circular_shift_null,
    nearest_known_structures,
    prime_ap_through,
)


def _primes_upto(limit: int) -> list[int]:
    sieve = bytearray([1]) * (limit + 1)
    sieve[0] = sieve[1] = 0
    for i in range(2, int(limit**0.5) + 1):
        if sieve[i]:
            sieve[i * i :: i] = bytearray(len(sieve[i * i :: i]))
    return [i for i in range(limit + 1) if sieve[i]]


_PRIMES = _primes_upto(200_000)
_PSET = set(_PRIMES)


def test_every_coordinate_has_declared_status() -> None:
    # Truthful-by-construction guard: no atlas coordinate may be unclassified.
    coord_names = {f.name for f in fields(PrimeAddress)}
    declared = set(COORDINATE_STATUS)
    assert coord_names == declared, f"status mismatch: {coord_names ^ declared}"
    for status, _note in COORDINATE_STATUS.values():
        assert status in {"FACT", "KNOWN_STRUCTURE", "FALSIFIED_PROJECTION"}


def test_atlas_addresses_are_exact() -> None:
    atlas = build_prime_atlas(9_999, 3)
    a = atlas[1]  # index 10000 -> p_10000 = 104729
    assert a.index == 10_000
    assert a.value == 104_729 == _PRIMES[9_999]
    assert a.gap_prev == 104_729 - _PRIMES[9_998]
    assert a.gap_next == _PRIMES[10_000] - 104_729
    assert a.residues == tuple(104_729 % q for q in RESIDUE_PRIMES)
    assert a.wheel_lane == 104_729 % WHEEL_MODULUS
    assert a.graph_signature == (a.gap_prev, a.gap_next)
    assert math.isclose(a.ratio_prev, 104_729 / _PRIMES[9_998])


def test_prime_ap_through_finds_known_green_tao_progression() -> None:
    is_prime = lambda n: n in _PSET  # noqa: E731
    # 5, 11, 17, 23, 29 is a 5-term arithmetic progression of primes, d=6.
    length, diff = prime_ap_through(17, is_prime, max_len=6, max_diff=30)
    assert length == 5 and diff == 6
    # 3, 5, 7 is a 3-term AP, d=2.
    assert prime_ap_through(5, is_prime, max_len=6, max_diff=30)[0] >= 3


def test_nearest_known_structures_uses_only_survived_relations() -> None:
    atlas = build_prime_atlas(2, 60)  # small primes: twins, APs present
    near = [nearest_known_structures(a) for a in atlas]
    assert any(n["twin_prime"] for n in near)
    assert any(n["on_prime_ap"] for n in near)
    assert all("ap_length" in n and "wheel_lane" in n for n in near)


def test_seed_region_query_contains_target_under_proven_contract() -> None:
    region = build_prime_seed_region(10_000)
    assert region.schema_version == "prime_seed_region_v1"
    assert region.seed.coverage_contract.startswith("proven")
    assert region.target_inside_window
    assert region.target_value == 104_729
    assert region.seed.lower_bound <= region.target_value <= region.seed.upper_bound
    assert all(
        region.seed.lower_bound <= address.value <= region.seed.upper_bound
        for address in region.addresses
    )
    assert region.structure_counts["known_primes"] == len(region.addresses)
    assert region.structure_counts["wheel_coprime"] == len(region.addresses)

    payload = region.to_dict()
    assert payload["target_value"] == 104_729
    assert len(payload["known_structures"]) == len(region.addresses)


def test_seed_region_query_requires_explicit_large_sieve_override() -> None:
    with pytest.raises(ValueError, match="increase max_sieve_limit"):
        build_prime_seed_region(200_000, max_sieve_limit=100_000)


def test_circular_shift_null_preserves_multiset() -> None:
    vals = [1.0, 2.0, 3.0, 4.0, 5.0]
    rolled = circular_shift_null(vals, 2)
    assert sorted(rolled) == sorted(vals)
    assert len(rolled) == len(vals)
    assert rolled != vals


def test_alignment_vs_null_distinguishes_real_from_hallucinated() -> None:
    target = [float(i % 7) for i in range(64)]
    # Identical signal is perfectly aligned -> must beat the null.
    real = alignment_vs_null(target, target, seeds=200)
    assert real["beats_null"] and real["real"] > 0.9
    # A flat signal carries no alignment -> must NOT beat the null.
    flat = [1.0] * 64
    res = alignment_vs_null(flat, target, seeds=200)
    assert not res["beats_null"]


def test_alignment_vs_null_rejects_short_inputs() -> None:
    with pytest.raises(ValueError, match="at least 8 points"):
        alignment_vs_null([1.0, 2.0], [1.0, 2.0])
