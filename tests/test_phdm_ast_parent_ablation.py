from __future__ import annotations

import math

from scripts.eval.phdm_ast_parent_ablation import METRICS, run_ablation


def test_small_ast_parent_ablation_is_control_complete_and_finite() -> None:
    report = run_ablation(
        seeds=3,
        dimensions=6,
        file_limit=2,
        node_cap=32,
        noise_scale=0.01,
    )

    assert report["schema"] == "scbe.phdm-ast-parent-additive-ablation.v1"
    assert len(report["corpus"]) == 2
    assert "depth" in report["features"]["excluded"]
    assert set(report["arms"]) == {
        "flat_euclidean",
        "primary_clamp_hyperbolic",
        "n_bounded_hyperbolic",
        "n_bounded_euclidean",
        "linear_depth_euclidean",
        "shuffled_depth_hyperbolic",
    }
    for arm in report["arms"].values():
        assert set(arm) == set(METRICS)
        for summary in arm.values():
            assert math.isfinite(summary["mean"])
            assert math.isfinite(summary["sample_sd"])


def test_ast_parent_ablation_rejects_non_phdm_dimension() -> None:
    try:
        run_ablation(seeds=3, dimensions=8, file_limit=1, node_cap=8)
    except ValueError as exc:
        assert "six hyperbolic dimensions" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected a dimension guard")
