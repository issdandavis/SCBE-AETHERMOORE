import math

from scripts.research.prime_alignment_ledger import (
    axis_score_fn,
    fit_count_honest_config,
    gap_acceleration_scores,
    golden_spiral_phase_scores,
    log_power_bridge_scores,
    numerical_emulsion_scores,
    prime_circuit_geometry_scores,
    ratio_curvature_scores,
    ratio_graph_resonance_scores,
    residue_wheel_frequency_scores,
)


def test_log_power_bridge_scores_are_bounded() -> None:
    rows = [{"scan_prime": 3**9}, {"scan_prime": (3**9) + 2}, {"scan_prime": 4**7}]

    scores = log_power_bridge_scores(rows)

    assert len(scores) == len(rows)
    assert all(0.0 <= score <= 1.0 for score in scores)
    assert scores[0] == 1.0
    assert scores[2] == 1.0


def test_golden_spiral_phase_scores_are_bounded() -> None:
    rows = [{"scan_prime": 101}, {"scan_prime": 103}, {"scan_prime": 107}]

    scores = golden_spiral_phase_scores(rows)

    assert len(scores) == len(rows)
    assert all(0.0 <= score <= 1.0 for score in scores)


def test_gap_acceleration_scores_use_scan_idx_order_and_return_original_order() -> None:
    rows = [
        {"scan_idx": 3, "scan_ratio": 4.0},
        {"scan_idx": 1, "scan_ratio": 0.0},
        {"scan_idx": 2, "scan_ratio": 1.0},
    ]

    scores = gap_acceleration_scores(rows)

    assert scores == [0.0, 0.0, 2.0]


def test_ratio_curvature_scores_measure_log_ratio_bend() -> None:
    rows = [
        {"scan_idx": 3, "scan_prime": 12},
        {"scan_idx": 1, "scan_prime": 2},
        {"scan_idx": 2, "scan_prime": 4},
    ]

    scores = ratio_curvature_scores(rows)

    assert scores[0] == 0.0
    assert scores[1] == 0.0
    assert scores[2] > 0.0


def test_ratio_graph_resonance_prefers_repeated_transition_weights() -> None:
    rows = [
        {"scan_idx": 1, "scan_prime": 2},
        {"scan_idx": 2, "scan_prime": 4},
        {"scan_idx": 3, "scan_prime": 8},
        {"scan_idx": 4, "scan_prime": 30},
    ]

    scores = ratio_graph_resonance_scores(rows)

    assert len(scores) == len(rows)
    assert scores[1] == 0.0
    assert scores[2] == 0.0
    assert scores[3] < 0.0


def test_prime_circuit_geometry_scores_measure_folded_middle_bend() -> None:
    rows = [
        {"scan_idx": 3, "scan_prime": 47},
        {"scan_idx": 1, "scan_prime": 11},
        {"scan_idx": 2, "scan_prime": 23},
    ]

    scores = prime_circuit_geometry_scores(rows)

    assert len(scores) == len(rows)
    assert scores[0] == 0.0
    assert scores[1] == 0.0
    assert scores[2] > 0.0


def test_residue_wheel_frequency_scores_are_label_free_counts() -> None:
    rows = [
        {"scan_prime": 211},
        {"scan_prime": 421},
        {"scan_prime": 223},
        {"scan_prime": 433},
        {"scan_prime": 641},
    ]

    scores = residue_wheel_frequency_scores(rows)

    assert scores == [1.0, 1.0, 1.0, 1.0, 0.5]


def test_numerical_emulsion_scores_measure_local_factor_collar() -> None:
    rows = [
        {"scan_prime": 11, "future_anchor": True, "first_anchor_prime": 101},
        {"scan_prime": 11, "future_anchor": False, "first_anchor_prime": None},
    ]

    scores = numerical_emulsion_scores(rows)

    # Around 11 with radius 6:
    # left tau(10,9,8,7,6,5) = 4,3,4,2,4,2
    # right tau(12,13,14,15,16,17) = 6,2,4,4,5,2
    expected = math.log1p(10) + math.log1p(6) + (4 / 42)
    assert scores == [expected, expected]


def test_axis_score_fn_rejects_unknown_axis() -> None:
    try:
        axis_score_fn(None, "not_an_axis")  # type: ignore[arg-type]
    except ValueError as exc:
        assert "unknown alignment axis" in str(exc)
    else:
        raise AssertionError("unknown axis was accepted")


def test_fit_count_honest_config_prefers_count_closeness() -> None:
    rows = [
        {
            "scan_idx": 1,
            "scan_prime": 11,
            "future_anchor": True,
            "first_anchor_idx": 101,
            "first_anchor_prime": 101,
        },
        {
            "scan_idx": 2,
            "scan_prime": 13,
            "future_anchor": False,
            "first_anchor_idx": None,
            "first_anchor_prime": None,
        },
        {
            "scan_idx": 4,
            "scan_prime": 17,
            "future_anchor": False,
            "first_anchor_idx": None,
            "first_anchor_prime": None,
        },
        {
            "scan_idx": 5,
            "scan_prime": 19,
            "future_anchor": False,
            "first_anchor_idx": None,
            "first_anchor_prime": None,
        },
        {
            "scan_idx": 7,
            "scan_prime": 23,
            "future_anchor": False,
            "first_anchor_idx": None,
            "first_anchor_prime": None,
        },
        {
            "scan_idx": 8,
            "scan_prime": 29,
            "future_anchor": False,
            "first_anchor_idx": None,
            "first_anchor_prime": None,
        },
        {
            "scan_idx": 20,
            "scan_prime": 31,
            "future_anchor": True,
            "first_anchor_idx": 211,
            "first_anchor_prime": 211,
        },
    ]
    scores = [4.0, 0.0, 3.0, 0.0, 2.0, 0.0, 1.0]

    fit = fit_count_honest_config(
        rows, scores, "demo", radius=1, percentile_grid=(0.0, 0.75, 0.9)
    )

    assert fit["percentile"] == 0.75
    assert fit["predicted_clusters"] == 2
    assert fit["actual_unique_anchors"] == 2
    assert fit["count_error"] == 0
