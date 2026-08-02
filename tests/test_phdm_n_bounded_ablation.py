from __future__ import annotations

import math

from scripts.eval.phdm_n_bounded_ablation import (
    METRICS,
    binary_tree_paths,
    gate,
    run_ablation,
)


def test_complete_depth_four_binary_tree_has_thirty_nodes() -> None:
    paths = binary_tree_paths(4)

    assert len(paths) == 30
    assert len(set(paths)) == 30
    assert {len(path) for path in paths} == {1, 2, 3, 4}


def test_gate_requires_more_than_two_pooled_standard_deviations() -> None:
    candidate = {"metric": {"mean": 0.8, "sample_sd": 0.1}}
    passing_control = {"metric": {"mean": 0.5, "sample_sd": 0.1}}
    underpowered_control = {"metric": {"mean": 0.65, "sample_sd": 0.1}}

    assert gate(candidate, passing_control, "metric")["verdict"] == "PASS"
    assert gate(candidate, underpowered_control, "metric")["verdict"] == "UNDERPOWERED"


def test_small_ablation_emits_finite_control_complete_receipt() -> None:
    report = run_ablation(seeds=3, dimensions=6, max_depth=4)

    assert report["schema"] == "scbe.phdm-n-bounded-additive-ablation.v1"
    assert report["config"]["nodes"] == 30
    assert set(report["arms"]) == {
        "primary_clamp_hyperbolic",
        "matched_fixed_hyperbolic",
        "n_bounded_hyperbolic",
        "n_bounded_euclidean",
        "linear_depth_euclidean",
        "shuffled_depth_hyperbolic",
    }
    assert set(report["comparisons"]) == {
        "primary_clamp_hyperbolic",
        "matched_fixed_hyperbolic",
        "n_bounded_euclidean",
        "linear_depth_euclidean",
        "shuffled_depth_hyperbolic",
    }
    for arm in report["arms"].values():
        assert set(arm) == set(METRICS)
        for summary in arm.values():
            assert math.isfinite(summary["mean"])
            assert math.isfinite(summary["sample_sd"])
