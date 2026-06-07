from __future__ import annotations

from scripts.research.log_cylinder_tangent_probe import (
    build_points,
    lane_flip_rates,
    liouville_lambda,
    run_probe,
    shuffled_angle_null_spread,
    simple_sieve,
    tangent_parallelism,
)


def test_liouville_lambda_matches_known_factor_parity() -> None:
    primes = simple_sieve(50)

    assert liouville_lambda(2, primes) == -1
    assert liouville_lambda(4, primes) == 1
    assert liouville_lambda(6, primes) == 1
    assert liouville_lambda(12, primes) == -1


def test_build_points_uses_plus2_parity_horizon() -> None:
    points = build_points(limit=30)
    by_n = {point.n: point for point in points}

    assert by_n[5].left_tangent > 0.0
    assert by_n[5].right_tangent > 0.0
    assert by_n[5].residue_mod_30 == 5
    assert by_n[5].delta_angle_plus2 in {0.0, 3.141592653589793}


def test_lane_flip_rates_reports_residue_spread() -> None:
    rates = lane_flip_rates(build_points(limit=500))

    assert 0.0 <= rates["overall_flip_rate"] <= 1.0
    assert rates["residue_rate_spread"] >= 0.0
    assert "1" in rates["residue_flip_rates"]


def test_tangent_parallelism_is_bounded_for_log_curve() -> None:
    metrics = tangent_parallelism(build_points(limit=500))

    assert metrics["right_left_ratio_min"] > 0.0
    assert metrics["right_left_ratio_max"] > metrics["right_left_ratio_min"]


def test_shuffle_null_and_probe_report_quarantine() -> None:
    points = build_points(limit=1000)
    null95 = shuffled_angle_null_spread(points, trials=5, seed=2)
    result = run_probe(limit=1000, null_trials=5, seed=2)

    assert null95 >= 0.0
    assert result["decision_record"]["promotion"] == "QUARANTINE_RESEARCH_ONLY"
    assert result["decision_record"]["verdict"] in {
        "PLUS2_TANGENT_RESIDUE_LANES",
        "PLUS2_TANGENT_PARITY_MIXED",
    }
