from __future__ import annotations

import pytest

from src.geoseed.prime_seed_init import (
    DEFAULT_M6_LAYER_PRIMES,
    build_prime_anchor_seed,
    build_prime_seed_shells,
    dusart_bracket,
    nth_prime_smooth_address,
    validate_layer_primes,
)


def _primes_upto(limit: int) -> list[int]:
    sieve = bytearray([1]) * (limit + 1)
    sieve[0] = sieve[1] = 0
    for i in range(2, int(limit**0.5) + 1):
        if sieve[i]:
            sieve[i * i :: i] = bytearray(len(sieve[i * i :: i]))
    return [i for i in range(limit + 1) if sieve[i]]


# p_50000 = 611953, so this covers nth-prime indices well past 4 decades.
_PRIMES = _primes_upto(700_000)


def test_m6_shells_map_first_six_mod_layers_to_tongues() -> None:
    shells = build_prime_seed_shells()

    assert [shell.tongue_abbr for shell in shells] == [
        "KO",
        "AV",
        "RU",
        "CA",
        "UM",
        "DR",
    ]
    assert [shell.layer_prime for shell in shells] == list(DEFAULT_M6_LAYER_PRIMES)
    assert shells[3].modulus == 210
    assert shells[3].totient == 48
    assert shells[3].survival_fraction == round(48 / 210, 12)


def test_smooth_address_is_close_enough_to_known_10000th_prime() -> None:
    estimate = nth_prime_smooth_address(10_000)

    # p_10000 = 104729. The seed only needs a center, not exact lookup.
    assert abs(estimate - 104_729) / 104_729 < 0.05


def test_prime_anchor_seed_is_constructor_not_exact_pick() -> None:
    seed = build_prime_anchor_seed(10_000)

    assert seed.schema_version == "geoseed_prime_anchor_seed_v1"
    assert seed.lower_bound < seed.center_estimate < seed.upper_bound
    assert seed.lower_bound < 104_729 < seed.upper_bound
    assert seed.modulus == 30_030
    assert seed.allowed_residue_count == 5_760
    assert "never the prime pick" in seed.density_note
    assert len(seed.shells) == 6


def test_dusart_bracket_contains_nth_prime_across_scales() -> None:
    # The proven bracket must contain p_n for EVERY index in a wide sweep.
    # This is the guard the smoke test lacked: a single example can't show coverage.
    misses = []
    for n in range(6, 50_000, 97):
        lo, hi = dusart_bracket(n)
        p = _PRIMES[n - 1]
        if not (lo <= p <= hi):
            misses.append((n, lo, p, hi))
    assert not misses, f"proven bracket missed p_n at: {misses[:5]}"


def test_dusart_bracket_exact_for_small_indices() -> None:
    for n, expected in enumerate((2, 3, 5, 7, 11), start=1):
        lo, hi = dusart_bracket(n)
        assert lo == hi == expected


def test_proven_mode_coverage_is_total() -> None:
    # Default (proven) mode is guaranteed; every sampled true prime is bracketed.
    for n in (10, 100, 1_000, 10_000, 49_999):
        seed = build_prime_anchor_seed(n)  # default mode="proven"
        p = _PRIMES[n - 1]
        assert seed.lower_bound <= p <= seed.upper_bound
        assert seed.coverage_contract.startswith("proven")
        assert seed.lower_bound <= seed.center_estimate <= seed.upper_bound


def test_tight_mode_is_narrower_but_flags_no_guarantee() -> None:
    tight = build_prime_anchor_seed(10_000, mode="tight")
    proven = build_prime_anchor_seed(10_000, mode="proven")
    assert (tight.upper_bound - tight.lower_bound) < (
        proven.upper_bound - proven.lower_bound
    )
    assert "NOT guaranteed" in tight.coverage_contract


def test_unknown_mode_rejected() -> None:
    with pytest.raises(ValueError, match="mode must be"):
        build_prime_anchor_seed(10_000, mode="magic")


def test_validate_layer_primes_rejects_bad_values() -> None:
    with pytest.raises(ValueError, match="must be prime"):
        validate_layer_primes((2, 3, 4))

    with pytest.raises(ValueError, match="at most"):
        validate_layer_primes((2, 3, 5, 7, 11, 13, 17))
