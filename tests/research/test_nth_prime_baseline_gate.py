from __future__ import annotations

from scripts.research.nth_prime_baseline_gate import (
    nth_prime_baseline,
    nth_prime_corridor,
    run_benchmark,
    segmented_primes,
    simple_sieve,
    wheel_candidates_in_segment,
)


def test_simple_sieve_returns_expected_small_primes() -> None:
    assert simple_sieve(30) == [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]


def test_wheel_candidates_include_only_admissible_large_values() -> None:
    candidates = wheel_candidates_in_segment(1, 70)

    assert [2, 3, 5] == candidates[:3]
    assert 49 in candidates  # candidate lane, later crossed off by sieving
    assert 9 not in candidates
    assert 25 not in candidates


def test_segmented_primes_matches_simple_sieve_window() -> None:
    base_primes = simple_sieve(20)
    primes, segments, candidates, composites = segmented_primes(
        1, 200, base_primes, segment_size=64
    )

    assert primes == simple_sieve(200)
    assert segments > 1
    assert candidates > len(primes)
    assert composites > 0


def test_corridor_contains_known_prime_for_mid_index() -> None:
    corridor = nth_prime_corridor(1000)
    prime = nth_prime_baseline(1000).prime

    assert corridor.lower <= prime <= corridor.upper


def test_nth_prime_baseline_known_values() -> None:
    known = {
        1: 2,
        2: 3,
        3: 5,
        10: 29,
        100: 541,
        1000: 7919,
        10000: 104729,
    }

    for index, prime in known.items():
        assert nth_prime_baseline(index).prime == prime


def test_run_benchmark_reports_instrumentation() -> None:
    summary = run_benchmark([10, 1000], segment_size=4096)

    assert summary["decision_record"]["promotion"] == "BASELINE_GATE"
    assert summary["results"][0]["prime"] == 29
    assert summary["results"][1]["prime"] == 7919
    assert summary["results"][1]["candidates_touched"] > 0
