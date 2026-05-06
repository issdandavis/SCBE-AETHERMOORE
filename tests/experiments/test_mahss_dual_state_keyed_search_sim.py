"""Tests for the dual-state keyed-search comparison."""

from __future__ import annotations

import numpy as np
import pytest

from scripts.experiments.mahss_dual_state_keyed_search_sim import (
    DualStateSpec,
    SCHEMA_VERSION,
    amplitude_matrix,
    build_landscape,
    run_compare,
    select_brute_pair,
    select_resonance_cross,
)


def test_landscape_plants_matched_diamond_pairs() -> None:
    spec = DualStateSpec(n_a=40, n_b=40, n_diamond_pairs=3, n_decoys_per_side=5, seed=11)
    landscape = build_landscape(spec)

    A = landscape["A"]
    B = landscape["B"]
    M = landscape["M"]
    diamond_pairs = landscape["diamond_pairs"]
    assert isinstance(A, np.ndarray) and A.shape == (40, 32)
    assert isinstance(B, np.ndarray) and B.shape == (40, 32)
    assert isinstance(M, np.ndarray) and M.shape == (32, 32)
    assert isinstance(diamond_pairs, set)
    assert len(diamond_pairs) == 3
    assert all(isinstance(p, tuple) and len(p) == 2 for p in diamond_pairs)


def test_diamond_pairs_score_higher_than_random_pairs() -> None:
    spec = DualStateSpec(n_a=50, n_b=50, n_diamond_pairs=3, n_decoys_per_side=8, seed=23)
    landscape = build_landscape(spec)
    log_amp = amplitude_matrix(landscape["A"], landscape["B"], landscape["M"])
    diamond_pairs = landscape["diamond_pairs"]
    diamond_amps = [log_amp[a, b] for a, b in diamond_pairs]
    n_a, n_b = log_amp.shape
    non_diamond_total = log_amp.sum() - sum(diamond_amps)
    non_diamond_count = n_a * n_b - len(diamond_pairs)
    non_diamond_mean = non_diamond_total / non_diamond_count
    assert min(diamond_amps) > non_diamond_mean


def test_brute_pair_recovers_all_diamond_pairs() -> None:
    spec = DualStateSpec(n_a=60, n_b=60, n_diamond_pairs=4, n_decoys_per_side=10, seed=31)
    landscape = build_landscape(spec)
    pairs, evaluations = select_brute_pair(
        landscape["A"], landscape["B"], landscape["M"], budget_pairs=4
    )
    assert evaluations == 60 * 60
    assert set(pairs) == landscape["diamond_pairs"]


def test_resonance_cross_matches_brute_pair_recall() -> None:
    spec = DualStateSpec(n_a=60, n_b=60, n_diamond_pairs=4, n_decoys_per_side=10, seed=31)
    landscape = build_landscape(spec)
    brute_pairs, _ = select_brute_pair(
        landscape["A"], landscape["B"], landscape["M"], budget_pairs=4
    )
    resonance_pairs, _ = select_resonance_cross(
        landscape["A"], landscape["B"], landscape["M"], budget_pairs=4
    )
    assert set(resonance_pairs) == set(brute_pairs)


def test_run_compare_emits_summary_for_each_method() -> None:
    spec = DualStateSpec(n_a=50, n_b=50, n_diamond_pairs=3, n_decoys_per_side=6, seed=41)
    report = run_compare(spec, budget_pairs=4)

    assert report["schema_version"] == SCHEMA_VERSION
    expected = {
        "brute_pair",
        "tang_cross_k10",
        "tang_cross_k20",
        "resonance_cross_a1",
        "multigrid_cross_c20_k6",
        "multigrid_cross_c30_k10",
    }
    assert set(report["summary"]) == expected
    for row in report["summary"].values():
        assert "evaluations" in row and "diamond_recall" in row and "regret_log_amp" in row


def test_resonance_outperforms_multigrid_under_key_coupling() -> None:
    """Multigrid breaks under multiplicative cross-coupling; resonance survives.

    This is the central finding: when the score function couples the two
    spaces via a random orthogonal key matrix, decompose-and-recombine
    multigrid loses recall because no per-axis representative predicts the
    cross-coupling. Resonance, which evaluates the joint amplitude directly,
    matches brute-force recall.
    """

    spec = DualStateSpec(
        n_a=80,
        n_b=80,
        n_diamond_pairs=4,
        n_decoys_per_side=12,
        seed=19,
    )
    report = run_compare(spec, budget_pairs=8)
    summary = report["summary"]
    resonance = summary["resonance_cross_a1"]
    multigrid = summary["multigrid_cross_c20_k6"]
    brute = summary["brute_pair"]
    assert resonance["diamond_recall"] == pytest.approx(brute["diamond_recall"])
    assert multigrid["diamond_recall"] < resonance["diamond_recall"]
    assert multigrid["regret_log_amp"] > resonance["regret_log_amp"]
