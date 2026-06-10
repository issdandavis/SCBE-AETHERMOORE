from __future__ import annotations

from scripts.research.nth_prime_baseline_gate import (
    lucy_key_count,
    nth_prime_baseline,
    nth_prime_corridor,
    prime_count_sieve,
    prime_pi_lucy,
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
    primes, segments, candidates, composites = segmented_primes(1, 200, base_primes, segment_size=64)

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


# --- Lucy_Hedgehog sublinear count: acceptance gate (exactness + floor moved) ---


def test_prime_pi_lucy_matches_known_values() -> None:
    # canonical pi(x) table values
    assert prime_pi_lucy(10) == 4
    assert prime_pi_lucy(100) == 25
    assert prime_pi_lucy(1000) == 168
    assert prime_pi_lucy(10**6) == 78498
    assert prime_pi_lucy(10**7) == 664579  # true pi, not the x/ln x PNT estimate


def test_prime_pi_lucy_agrees_with_the_sieve_it_replaces() -> None:
    # cross-check the sublinear count against the O(x) oracle it replaced, exactly
    for limit in (2, 3, 49, 5_000, 123_457, 10**6):
        assert prime_pi_lucy(limit) == prime_count_sieve(limit)


def test_acceptance_exact_value_preserved_at_1e6() -> None:
    # ASSERTION 1: a subtly-wrong pi(x) yields an off corridor and the wrong prime.
    assert nth_prime_baseline(10**6).prime == 15_485_863


def test_acceptance_count_floor_moved_below_corridor() -> None:
    # ASSERTION 2: the count step now does ~2*sqrt(x) ratio-point work, which must
    # sit *below* the corridor's candidate-touch count -- proving the count step is
    # no longer the dominant stage (it previously sieved to ~p_n).
    result = nth_prime_baseline(10**6)
    assert result.count_step_keys == lucy_key_count(result.corridor_lower - 1)
    assert result.count_step_keys < result.candidates_touched
    # and it is genuinely sublinear: keys are O(sqrt(lower)), not O(lower)
    assert result.count_step_keys < 50 * (result.corridor_lower**0.5)
