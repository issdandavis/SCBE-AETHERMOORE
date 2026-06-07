from __future__ import annotations

from scripts.research.prime_boundary_spectrum_null import (
    boundary_class,
    centroid_accuracy,
    factorize,
    features_from_factors,
    first_n_primes,
    random_wheel_even_near,
    run_experiment,
    simple_sieve,
    survives_wheel_predecessor,
)


def test_factorize_and_boundary_classes_capture_expected_spectrum() -> None:
    primes = simple_sieve(100)

    assert factorize(90, primes) == {2: 1, 3: 2, 5: 1}
    assert boundary_class(factorize(32, primes)) == "tower_2_power"
    assert boundary_class(factorize(2 * 47, primes)) == "semiprime_2q"
    assert boundary_class(factorize(2 * 3 * 5 * 7, primes)) == "smooth_7_shattered"
    assert boundary_class(factorize(2 * 31 * 37, primes)) == "generic"


def test_feature_vector_marks_smoothness_and_two_adic_layer() -> None:
    primes = simple_sieve(100)
    factors = factorize(2**5 * 3, primes)
    (
        omega,
        big_omega,
        log_tau,
        two_adic,
        largest_ratio,
        smooth_7,
        smooth_29,
        smooth_97,
    ) = features_from_factors(2**5 * 3, factors)

    assert omega == 2.0
    assert big_omega == 6.0
    assert log_tau > 0.0
    assert two_adic == 5.0
    assert 0.0 < largest_ratio < 1.0
    assert smooth_7 == 1.0
    assert smooth_29 == 1.0
    assert smooth_97 == 1.0


def test_wheel_even_sampler_requires_admissible_predecessor() -> None:
    import random

    rng = random.Random(123)
    sample = random_wheel_even_near(10_000, rng, (2, 3, 5, 7))

    assert sample % 2 == 0
    assert survives_wheel_predecessor(sample, (2, 3, 5, 7))


def test_centroid_accuracy_can_fail_on_shuffled_labels() -> None:
    positives = [(2.0, 2.0), (2.1, 2.0), (1.9, 2.2), (2.0, 1.8)] * 10
    negatives = [(-2.0, -2.0), (-2.1, -2.0), (-1.9, -2.2), (-2.0, -1.8)] * 10

    real = centroid_accuracy(positives, negatives, seed=1, shuffle_labels=False)
    shuffled = centroid_accuracy(positives, negatives, seed=1, shuffle_labels=True)

    assert real > 0.95
    assert shuffled < 0.75


def test_run_experiment_reports_raw_and_wheel_nulls() -> None:
    result = run_experiment(n_primes=250, seed=7, null_trials=10)

    assert result["n_records"] > 200
    assert result["feature_names"]
    assert "classifier_prime_vs_raw_even" in result
    assert "classifier_prime_vs_wheel_even" in result
    assert result["decision_record"]["promotion"] == "QUARANTINE_RESEARCH_ONLY"


def test_first_n_primes_has_requested_length_and_order() -> None:
    primes = first_n_primes(20)

    assert len(primes) == 20
    assert primes[:6] == [2, 3, 5, 7, 11, 13]
    assert primes == sorted(primes)
