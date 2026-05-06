"""Tests for the MAHSS tangent-rescue adversarial optimizer."""

from __future__ import annotations

from scripts.experiments.mahss_tangent_rescue_adversarial import (
    TARGET_METHOD,
    run_adversarial_search,
)


def test_adversarial_search_reports_fair_tang_cases() -> None:
    report = run_adversarial_search(
        trials=8,
        sizes=[80],
        seeds=range(8),
        key_modes=["random_orthogonal", "hadamard"],
        decoys=[12],
        decoy_norms=[6.0],
        alignments=[0.92],
        random_seed=7,
        budget_pairs=8,
    )

    assert report["schema_version"] == "scbe_mahss_tangent_rescue_adversarial_v1"
    assert report["target_method"] == TARGET_METHOD
    assert report["trials"] == 8
    assert report["fair_tang_cases"] > 0
    assert isinstance(report["worst_fair_cases"], list)


def test_adversarial_search_preserves_counterexample_fields() -> None:
    report = run_adversarial_search(
        trials=4,
        sizes=[320],
        seeds=range(4),
        key_modes=["signed_permutation"],
        decoys=[16],
        decoy_norms=[5.5],
        alignments=[0.82],
        random_seed=11,
        budget_pairs=8,
    )

    row = report["worst_all_cases"][0]
    assert {"case", "methods", "fair_tang_baseline", "adversarial_score"}.issubset(row)
    assert TARGET_METHOD in row["methods"]
    assert "tang_cross_k20" in row["methods"]
