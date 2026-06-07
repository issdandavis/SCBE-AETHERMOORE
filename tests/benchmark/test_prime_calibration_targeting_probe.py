from scripts.research.run_prime_calibration_targeting_probe import (
    _ridge_fit_predict,
    analyze_window,
    density_control_rows,
    p_p_n_for_prime_n_by_index_limit,
    p_p_n_for_prime_n_sequence,
    wheel_candidate_count,
)


def test_wheel_candidate_count_handles_full_and_partial_cycles() -> None:
    assert wheel_candidate_count(211, 210) == 48
    assert wheel_candidate_count(1, 10, modulus=210) == 5


def test_superprime_sequence_uses_prime_index_twice() -> None:
    # n prime: 2,3,5,7
    # p_n:    3,5,11,17
    # p_p_n: 5,11,31,59
    assert p_p_n_for_prime_n_sequence(100)[:4] == [5, 11, 31, 59]


def test_superprime_index_limit_bounds_inner_index() -> None:
    assert p_p_n_for_prime_n_by_index_limit(17) == [5, 11, 31, 59]


def test_analyze_window_reports_local_gap_comparison() -> None:
    metrics = analyze_window("demo", "~small", [5, 11, 31, 59, 127, 179])

    assert metrics.sample_count == 6
    assert metrics.mean_gap == 34.8
    assert metrics.transition_count == 5
    assert metrics.local_last3_rmse >= 0.0


def test_density_control_rows_use_prior_only_features() -> None:
    rows, targets = density_control_rows([5, 11, 31, 59, 127, 179])

    assert len(rows) == 2
    assert targets == [68.0, 52.0]
    assert rows[0]["g1"] == 28.0
    assert rows[0]["g2"] == 20.0
    assert rows[0]["g3"] == 6.0


def test_ridge_fit_predict_recovers_linear_trend() -> None:
    train_x = [[1.0], [2.0], [3.0], [4.0]]
    train_y = [3.0, 5.0, 7.0, 9.0]
    test_x = [[5.0]]

    preds, beta, _means, _scales = _ridge_fit_predict(
        train_x, train_y, test_x, alpha=0.0
    )

    assert round(preds[0], 6) == 11.0
    assert len(beta) == 2
