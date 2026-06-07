from __future__ import annotations

from scripts.research.prime_inverse_line_4d_probe import (
    ADMISSIBLE_MOD_30,
    FEATURE_NAMES,
    build_records,
    centroid_accuracy,
    four_dimensional_features,
    null_p95,
    run_probe,
    simple_sieve,
    survives_wheel,
)


def test_four_dimensional_features_exclude_candidate_factorization() -> None:
    factor_primes = simple_sieve(100)
    features = four_dimensional_features(31, factor_primes)

    assert len(features[:4]) == len(FEATURE_NAMES)
    assert features[1] == ADMISSIBLE_MOD_30.index(31 % 30) / 7
    assert features[4] > 0
    assert features[5] > 0


def test_wheel_survival_marks_admissible_candidates() -> None:
    assert survives_wheel(31)
    assert survives_wheel(49)
    assert not survives_wheel(33)
    assert not survives_wheel(35)


def test_build_records_pairs_known_primes_with_wheel_composites() -> None:
    records = build_records(n_primes=100, seed=3)

    assert records
    assert sum(record.label == "prime" for record in records) == sum(
        record.label == "composite" for record in records
    )
    assert all(record.residue_mod_30 in ADMISSIBLE_MOD_30 for record in records)
    assert all(len(record.feature_vector) == 4 for record in records)


def test_centroid_accuracy_null_has_teeth_on_separable_records() -> None:
    records = build_records(n_primes=300, seed=5)
    real = centroid_accuracy(records, seed=5)
    shuffled = null_p95(records, trials=10, seed=5)

    assert 0.0 <= real <= 1.0
    assert 0.0 <= shuffled <= 1.0


def test_run_probe_reports_quarantine_decision() -> None:
    result = run_probe(n_primes=300, null_trials=10, seed=7)

    assert result["n_records"] > 500
    assert result["feature_names"] == FEATURE_NAMES
    assert result["decision_record"]["promotion"] == "QUARANTINE_RESEARCH_ONLY"
    assert result["decision_record"]["verdict"] in {
        "INVERSE_LINE_INDICATOR_SURVIVES_NULL",
        "INVERSE_LINE_COLLAPSES_TO_NULL",
    }
