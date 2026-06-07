from __future__ import annotations

from scripts.research.prime_shell_regional_trend import (
    ADMISSIBLE_MOD_30,
    build_shell_points,
    lane_trends,
    linear_fit,
    null_spread_p95,
    regional_spread,
    run_probe,
)


def test_linear_fit_recovers_simple_slope() -> None:
    slope, intercept, r2 = linear_fit([1.0, 2.0, 3.0], [3.0, 5.0, 7.0])

    assert slope == 2.0
    assert intercept == 1.0
    assert r2 == 1.0


def test_shell_points_live_on_admissible_mod_30_regions() -> None:
    points = build_shell_points(n_primes=200)

    assert points
    assert {point.residue_mod_30 for point in points}.issubset(set(ADMISSIBLE_MOD_30))
    assert all(point.gap_divergence > 0.0 for point in points)
    assert all(point.shell_radius > 1.0 for point in points)


def test_lane_trends_report_each_populated_region() -> None:
    trends = lane_trends(build_shell_points(n_primes=300))

    assert len(trends) == len(ADMISSIBLE_MOD_30)
    assert all(trend.count > 0 for trend in trends)
    assert all(trend.mean_gap_divergence > 0.0 for trend in trends)


def test_regional_spread_null_is_non_negative() -> None:
    points = build_shell_points(n_primes=500)
    spread = regional_spread(points, "gap_divergence")
    null95 = null_spread_p95(points, "gap_divergence", trials=10, seed=5)

    assert spread >= 0.0
    assert null95 >= 0.0


def test_run_probe_reports_quarantine_decision() -> None:
    result = run_probe(n_primes=500, null_trials=10, seed=7)

    assert result["n_points"] > 400
    assert result["n_lanes"] == len(ADMISSIBLE_MOD_30)
    assert result["decision_record"]["promotion"] == "QUARANTINE_RESEARCH_ONLY"
    assert result["decision_record"]["verdict"] in {
        "REGIONAL_TREND_SURVIVES_NULL",
        "WHEEL_LANES_ONLY",
    }
