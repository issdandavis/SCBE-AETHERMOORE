from __future__ import annotations

from scripts.research.factor_operation_correlation_probe import (
    factor_complexity_arrays,
    run_probe,
)


def test_factor_complexity_arrays_match_known_values() -> None:
    omega, big_omega, v2, liouville = factor_complexity_arrays(20)

    assert omega[2] == 1
    assert big_omega[2] == 1
    assert v2[2] == 1
    assert liouville[2] == -1

    assert omega[12] == 2  # 2^2 * 3
    assert big_omega[12] == 3
    assert v2[12] == 2
    assert liouville[12] == -1

    assert omega[16] == 1
    assert big_omega[16] == 4
    assert v2[16] == 4
    assert liouville[16] == 1


def test_run_probe_reports_operation_not_prime_only_signal() -> None:
    result = run_probe(10_000)

    assert result["decision"] == "INTEGER_OPERATION_SIGNAL_NOT_PRIME_ONLY"
    assert result["corr_omega_n_n_plus_1"] < 0.0
    assert abs(result["mean_liouville_n_times_n_plus_1"]) < 0.05
    assert 0.0 < result["prime_floor_share_big_omega_eq_1"] < 0.2
