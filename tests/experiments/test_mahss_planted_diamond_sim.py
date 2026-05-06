"""Tests for the planted-diamond stress test."""

from __future__ import annotations

import pytest

from scripts.experiments.mahss_planted_diamond_sim import (
    PlantedSpec,
    SCHEMA_VERSION,
    build_landscape,
    run_compare,
)


def test_build_landscape_plants_exact_diamond_count() -> None:
    spec = PlantedSpec(n_candidates=50, n_diamonds=3, seed=11)
    query, sketches, scores, diamond_idxs = build_landscape(spec)

    assert query.shape == (64,)
    assert sketches.shape == (50, 64)
    assert len(diamond_idxs) == 3
    assert len(set(int(i) for i in diamond_idxs)) == 3
    assert scores.shape == (50,)
    assert all(0 <= int(i) < 50 for i in diamond_idxs)


def test_diamonds_dominate_true_score_in_clean_landscape() -> None:
    spec = PlantedSpec(n_candidates=100, n_diamonds=5, seed=7)
    _query, _sketches, scores, diamond_idxs = build_landscape(spec)

    diamond_scores = scores[diamond_idxs]
    non_diamond = sorted(set(range(100)) - set(int(i) for i in diamond_idxs))
    assert min(diamond_scores) > max(scores[non_diamond])


def test_run_compare_emits_summary_for_each_baseline() -> None:
    spec = PlantedSpec(n_candidates=80, n_diamonds=3, seed=23)
    report = run_compare(spec, budget=8)

    assert report["schema_version"] == SCHEMA_VERSION
    assert report["budget"] == 8
    expected = {
        "uniform_sampled",
        "tang_beam_2",
        "tang_beam_2_125",
        "cosine_top_k",
        "mirror_beam_c1",
        "mirror_beam_c0_25",
        "mirror_beam_c4",
        "mirror_resonance_a1",
    }
    assert set(report["summary"]) == expected
    for row in report["summary"].values():
        assert "diamond_recall" in row
        assert 0.0 <= row["diamond_recall"] <= 1.0


def test_resonance_isolates_diamonds_under_confounded_landscape() -> None:
    spec = PlantedSpec(
        n_candidates=200,
        n_diamonds=5,
        n_high_norm_misaligned=20,
        n_low_norm_aligned=20,
        seed=17,
    )
    report = run_compare(spec, budget=10)

    summary = report["summary"]
    resonance = summary["mirror_resonance_a1"]
    tang = summary["tang_beam_2"]
    assert resonance["diamond_recall"] == pytest.approx(1.0)
    assert tang["diamond_recall"] == pytest.approx(0.0)
    assert resonance["regret"] == pytest.approx(0.0)
    assert tang["regret"] > resonance["regret"]


def test_run_compare_is_deterministic_under_fixed_seed() -> None:
    spec = PlantedSpec(n_candidates=100, n_diamonds=4, seed=42)
    a = run_compare(spec, budget=8)
    b = run_compare(spec, budget=8)
    assert a == b
