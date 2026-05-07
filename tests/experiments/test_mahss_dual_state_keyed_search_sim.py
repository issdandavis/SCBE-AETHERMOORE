"""Tests for the dual-state keyed-search comparison."""

from __future__ import annotations

import math

import numpy as np
import pytest

from scripts.experiments.mahss_dual_state_keyed_search_sim import (
    DualStateSpec,
    SCHEMA_VERSION,
    amplitude_matrix,
    build_landscape,
    run_compare,
    run_seed_size_sweep,
    select_constructive_oscillation_cross,
    select_phase_angle_cross,
    select_brute_pair,
    select_polyhedral_edge_gear_cross,
    select_polyhedral_edge_tangent_rescue_cross,
    select_polyhedral_edge_walk_cross,
    select_polyhedral_walk_cross,
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
    pairs, evaluations = select_brute_pair(landscape["A"], landscape["B"], landscape["M"], budget_pairs=4)
    assert evaluations == 60 * 60
    assert set(pairs) == landscape["diamond_pairs"]


def test_resonance_cross_matches_brute_pair_recall() -> None:
    spec = DualStateSpec(n_a=60, n_b=60, n_diamond_pairs=4, n_decoys_per_side=10, seed=31)
    landscape = build_landscape(spec)
    brute_pairs, _ = select_brute_pair(landscape["A"], landscape["B"], landscape["M"], budget_pairs=4)
    resonance_pairs, _ = select_resonance_cross(landscape["A"], landscape["B"], landscape["M"], budget_pairs=4)
    assert set(resonance_pairs) == set(brute_pairs)


def test_run_compare_emits_summary_for_each_method() -> None:
    spec = DualStateSpec(n_a=50, n_b=50, n_diamond_pairs=3, n_decoys_per_side=6, seed=41)
    report = run_compare(spec, budget_pairs=4)

    assert report["schema_version"] == SCHEMA_VERSION
    core_expected = {
        "brute_pair",
        "tang_cross_k10",
        "tang_cross_k20",
        "resonance_cross_a1",
        "multigrid_cross_c20_k6",
        "multigrid_cross_c30_k10",
        "constructive_oscillation_k8_o4_w3",
        "phase_angle_k20_o7",
        "polyhedral_edge_k20_w4",
        "polyhedral_edge_k20_w10",
        "polyhedral_edge_k20_w4_hybrid",
        "polyhedral_edge_k20_w10_weighted",
        "polyhedral_edge_gear_k20_w4_w10",
        "polyhedral_edge_k20_w4_tangent_rescue_r4_b40",
        "polyhedral_edge_k30_w6",
        "polyhedral_walk_tetrahedron",
        "polyhedral_walk_octahedron",
        "polyhedral_walk_cube",
        "polyhedral_walk_icosahedron",
        "polyhedral_walk_dodecahedron",
        "resonance_lowrank_r1",
        "resonance_lowrank_r2",
        "resonance_lowrank_r4",
        "resonance_lowrank_r8",
        "resonance_lowrank_r16",
        "resonance_lowrank_r32",
    }
    assert core_expected.issubset(set(report["summary"]))
    summary_keys = set(report["summary"])
    disagreement_keys = [name for name in summary_keys if name.startswith("disagree__")]
    assert len(disagreement_keys) > 0
    n_input = len([name for name in summary_keys if name != "brute_pair" and not name.startswith("disagree__")])
    assert len(disagreement_keys) == n_input * (n_input - 1) // 2
    for name, row in report["summary"].items():
        assert "evaluations" in row and "diamond_recall" in row and "regret_log_amp" in row
        assert "total_evaluations" in row and "cost_accounting" in row
        assert "source_evaluations" in row and "probe_evaluations" in row
        if name.startswith("disagree__"):
            assert row["cost_accounting"] == "source_plus_probe"
            assert row["total_evaluations"] == row["source_evaluations"] + row["probe_evaluations"]
        else:
            assert row["cost_accounting"] == "direct"
            assert row["total_evaluations"] == row["evaluations"]


def test_key_modes_are_supported_and_reported() -> None:
    for key_mode in ("random_orthogonal", "identity", "signed_permutation", "hadamard", "block_rotation"):
        report = run_compare(
            DualStateSpec(
                n_a=40,
                n_b=40,
                n_diamond_pairs=2,
                n_decoys_per_side=4,
                seed=3,
                key_mode=key_mode,
            ),
            budget_pairs=4,
        )
        assert report["spec"]["key_mode"] == key_mode
        assert report["summary"]["tang_cross_k20"]["diamond_recall"] == 1.0


def test_lowrank_resonance_recovers_recall_at_solution_rank() -> None:
    """Effective key strength = rank of the solution subspace, not rank(M).

    With 4 planted diamond pairs, the solution span is rank-4. Rank-8
    truncation should already start recovering recall; rank>=16 should
    fully recover. Rank<4 should fail.
    """

    spec = DualStateSpec(n_a=80, n_b=80, n_diamond_pairs=4, n_decoys_per_side=12, seed=19)
    report = run_compare(spec, budget_pairs=8)
    summary = report["summary"]
    assert summary["resonance_lowrank_r2"]["diamond_recall"] < 1.0
    assert summary["resonance_lowrank_r16"]["diamond_recall"] == pytest.approx(1.0)
    assert summary["resonance_lowrank_r32"]["diamond_recall"] == pytest.approx(1.0)


def test_seed_size_sweep_reports_aggregate_and_winners() -> None:
    report = run_seed_size_sweep(sizes=[40], seeds=[0, 1], budget_pairs=4, n_diamond_pairs=2)
    assert report["schema_version"] == "scbe_mahss_dual_state_seed_size_sweep_v1"
    assert report["sizes"] == [40]
    assert report["seeds"] == [0, 1]
    assert len(report["rows"]) == 2
    assert "polyhedral_edge_k20_w4" in report["aggregate"]
    assert "polyhedral_edge_k20_w10" in report["aggregate"]
    assert "polyhedral_edge_k20_w10_weighted" in report["aggregate"]
    assert "polyhedral_edge_gear_k20_w4_w10" in report["aggregate"]
    assert "polyhedral_edge_k20_w4_tangent_rescue_r4_b40" in report["aggregate"]
    assert "constructive_oscillation_k8_o4_w3" in report["aggregate"]
    assert "speedup_vs_tang_median" in report
    assert sum(report["winner_counts"].values()) == 2


def test_disagreement_probe_double_negative_makes_positive() -> None:
    """Two methods with complementary failure modes compose to a working reranker.

    tang_cross_k20 finds diamonds at 400 evals. multigrid_cross_c30_k10
    finds 0/4. Their disagreement-midpoint probe preserves tang's recall
    with a smaller probe-local candidate set, but it is not a total-cost
    search win once the source selectors are counted.
    """

    spec = DualStateSpec(n_a=80, n_b=80, n_diamond_pairs=4, n_decoys_per_side=12, seed=19)
    report = run_compare(spec, budget_pairs=8)
    summary = report["summary"]
    probe_key = "disagree__multigrid_cross_c30_k10__X__tang_cross_k20"
    assert probe_key in summary
    probe = summary[probe_key]
    tang20 = summary["tang_cross_k20"]
    multigrid = summary["multigrid_cross_c30_k10"]
    assert probe["diamond_recall"] == pytest.approx(tang20["diamond_recall"])
    assert probe["diamond_recall"] > multigrid["diamond_recall"]
    assert probe["probe_evaluations"] == probe["evaluations"]
    assert probe["probe_evaluations"] < tang20["evaluations"]
    assert probe["source_evaluations"] == tang20["evaluations"] + multigrid["evaluations"]
    assert probe["total_evaluations"] > tang20["total_evaluations"]


def test_disagreement_probe_cost_audit_rejects_misleading_total_cost_win() -> None:
    """The default probe mechanism is useful, but not cheaper end-to-end."""

    spec = DualStateSpec(n_a=80, n_b=80, n_diamond_pairs=4, n_decoys_per_side=12, seed=19)
    report = run_compare(spec, budget_pairs=8)
    audit = report["probe_cost_audit"]
    best_single = audit["best_full_recall_single_method"]
    best_probe = audit["best_full_recall_probe_method"]
    assert best_single["method"] == "polyhedral_edge_k20_w4"
    assert best_single["total_evaluations"] == 140
    assert best_probe["method"].startswith("disagree__")
    assert best_probe["total_evaluations"] > best_single["total_evaluations"]
    assert audit["probe_beats_single_on_total_cost"] is False


def test_polyhedral_edge_walk_beats_tang_on_strong_key_default() -> None:
    """Facet edge-walk recovers all keyed pairs at lower cost than Tang k20."""

    spec = DualStateSpec(n_a=80, n_b=80, n_diamond_pairs=4, n_decoys_per_side=12, seed=19)
    report = run_compare(spec, budget_pairs=8)
    summary = report["summary"]
    poly = summary["polyhedral_edge_k20_w4"]
    tang20 = summary["tang_cross_k20"]
    assert poly["diamond_recall"] == pytest.approx(tang20["diamond_recall"])
    assert poly["regret_log_amp"] == 0.0
    assert poly["total_evaluations"] == 140
    assert poly["total_evaluations"] < tang20["total_evaluations"]


def test_polyhedral_edge_w10_is_conservative_recall_variant() -> None:
    spec = DualStateSpec(n_a=80, n_b=80, n_diamond_pairs=4, n_decoys_per_side=12, seed=19)
    report = run_compare(spec, budget_pairs=8)
    w4 = report["summary"]["polyhedral_edge_k20_w4"]
    w10 = report["summary"]["polyhedral_edge_k20_w10"]
    tang20 = report["summary"]["tang_cross_k20"]
    assert w10["diamond_recall"] == 1.0
    assert w10["regret_log_amp"] == 0.0
    assert w10["total_evaluations"] > w4["total_evaluations"]
    assert w10["total_evaluations"] <= tang20["total_evaluations"]


def test_polyhedral_edge_gear_shifts_by_search_space_size() -> None:
    small = build_landscape(DualStateSpec(n_a=80, n_b=80, n_diamond_pairs=4, n_decoys_per_side=12, seed=19))
    pairs, evaluations, meta = select_polyhedral_edge_gear_cross(
        small["A"],
        small["B"],
        small["M"],
        seed_count=20,
        fast_width=4,
        torque_width=10,
        shift_threshold=80_000,
        budget_pairs=8,
    )
    assert meta["gear"] == "fast"
    assert meta["edge_width"] == 4
    assert meta["edge_metric"] == "hamming"
    assert evaluations == 140
    assert len(pairs) == 8

    large = build_landscape(DualStateSpec(n_a=500, n_b=500, n_diamond_pairs=4, n_decoys_per_side=12, seed=1))
    pairs, evaluations, meta = select_polyhedral_edge_gear_cross(
        large["A"],
        large["B"],
        large["M"],
        seed_count=20,
        fast_width=4,
        torque_width=10,
        shift_threshold=80_000,
        budget_pairs=8,
    )
    assert meta["gear"] == "torque"
    assert meta["edge_width"] == 10
    assert meta["edge_metric"] == "hamming"
    assert evaluations < 400
    assert len(pairs) == 8


def test_polyhedral_edge_gear_is_reported_in_run_compare() -> None:
    report = run_compare(
        DualStateSpec(n_a=80, n_b=80, n_diamond_pairs=4, n_decoys_per_side=12, seed=19), budget_pairs=8
    )
    row = report["summary"]["polyhedral_edge_gear_k20_w4_w10"]
    assert row["diamond_recall"] == 1.0
    assert row["regret_log_amp"] == 0.0
    assert row["polyhedral_edge_gear"]["gear"] == "fast"
    assert row["polyhedral_edge_gear"]["edge_width"] == 4
    assert row["polyhedral_edge_gear"]["edge_metric"] == "hamming"


def test_tangent_rescue_adds_bounded_sidecar_evaluations() -> None:
    landscape = build_landscape(DualStateSpec(n_a=80, n_b=80, n_diamond_pairs=4, n_decoys_per_side=12, seed=19))
    pairs, evaluations, meta = select_polyhedral_edge_tangent_rescue_cross(
        landscape["A"],
        landscape["B"],
        landscape["M"],
        seed_count=20,
        edge_width=4,
        tangent_planes=4,
        rescue_budget=40,
        budget_pairs=8,
    )
    assert len(pairs) == 8
    assert meta["main_evaluations"] == 140
    assert meta["rescue_evaluations"] <= 40
    assert evaluations == meta["main_evaluations"] + meta["rescue_evaluations"]
    assert meta["cheap_probe_count"] > evaluations


def test_tangent_rescue_is_reported_in_run_compare() -> None:
    report = run_compare(
        DualStateSpec(n_a=80, n_b=80, n_diamond_pairs=4, n_decoys_per_side=12, seed=19), budget_pairs=8
    )
    row = report["summary"]["polyhedral_edge_k20_w4_tangent_rescue_r4_b40"]
    assert row["cost_accounting"] == "direct"
    assert row["diamond_recall"] == 1.0
    assert row["tangent_rescue"]["tangent_planes"] == 4
    assert row["tangent_rescue"]["rescue_budget"] == 40
    assert row["total_evaluations"] <= 180


def test_polyhedral_edge_metrics_are_supported() -> None:
    landscape = build_landscape(DualStateSpec(n_a=80, n_b=80, n_diamond_pairs=4, n_decoys_per_side=12, seed=19))
    for metric in ("hamming", "phase", "hybrid", "weighted_hybrid"):
        pairs, evaluations = select_polyhedral_edge_walk_cross(
            landscape["A"],
            landscape["B"],
            landscape["M"],
            seed_count=20,
            edge_width=4,
            edge_metric=metric,
            budget_pairs=8,
        )
        assert len(pairs) == 8
        assert evaluations > 0


def test_polyhedral_edge_walk_selector_is_direct_and_bounded() -> None:
    spec = DualStateSpec(n_a=80, n_b=80, n_diamond_pairs=4, n_decoys_per_side=12, seed=19)
    landscape = build_landscape(spec)
    pairs, evaluations = select_polyhedral_edge_walk_cross(
        landscape["A"],
        landscape["B"],
        landscape["M"],
        seed_count=20,
        edge_width=4,
        budget_pairs=8,
    )
    assert evaluations == 140
    assert len(pairs) == 8
    assert set(landscape["diamond_pairs"]).issubset(set(pairs))


def test_phase_angle_selector_is_direct_and_metadata_bounded() -> None:
    """Angular phase matching is a compact frontier selector, not an edge walk."""

    spec = DualStateSpec(n_a=80, n_b=80, n_diamond_pairs=4, n_decoys_per_side=12, seed=19)
    landscape = build_landscape(spec)
    pairs, evaluations, meta = select_phase_angle_cross(
        landscape["A"],
        landscape["B"],
        landscape["M"],
        seed_count=20,
        offsets=7,
        angle_width=2,
        budget_pairs=8,
    )
    assert len(pairs) == 8
    assert evaluations == meta["frontier_size"]
    assert evaluations <= 20 * 7 * 2 * 2
    assert meta["offsets"] == 7
    assert len(meta["phase_offsets"]) == 7


def test_phase_angle_selector_is_compared_cost_honestly() -> None:
    spec = DualStateSpec(n_a=80, n_b=80, n_diamond_pairs=4, n_decoys_per_side=12, seed=19)
    report = run_compare(spec, budget_pairs=8)
    phase = report["summary"]["phase_angle_k20_o7"]
    poly = report["summary"]["polyhedral_edge_k20_w4"]
    assert phase["cost_accounting"] == "direct"
    assert phase["total_evaluations"] == phase["evaluations"]
    assert "phase_angle" in phase
    assert phase["total_evaluations"] <= 20 * 7 * 2 * 2
    assert poly["diamond_recall"] == 1.0


def test_constructive_oscillation_selector_is_direct_and_metadata_bounded() -> None:
    spec = DualStateSpec(n_a=80, n_b=80, n_diamond_pairs=4, n_decoys_per_side=12, seed=19)
    landscape = build_landscape(spec)
    pairs, evaluations, meta = select_constructive_oscillation_cross(
        landscape["A"],
        landscape["B"],
        landscape["M"],
        seed_count=20,
        oscillations=7,
        beam_width=2,
        budget_pairs=8,
    )
    assert len(pairs) == 8
    assert evaluations == meta["frontier_size"]
    assert evaluations <= 20 * 7 * 2 * 2
    assert meta["oscillations"] == 7
    assert meta["max_vote"] > 0.0
    assert meta["score_model"] == "inverse_lyapunov_derivative"


def test_constructive_oscillation_is_compared_cost_honestly() -> None:
    spec = DualStateSpec(n_a=80, n_b=80, n_diamond_pairs=4, n_decoys_per_side=12, seed=19)
    report = run_compare(spec, budget_pairs=8)
    osc = report["summary"]["constructive_oscillation_k8_o4_w3"]
    poly = report["summary"]["polyhedral_edge_k20_w4"]
    assert osc["cost_accounting"] == "direct"
    assert osc["total_evaluations"] == osc["evaluations"]
    assert "constructive_oscillation" in osc
    assert osc["diamond_recall"] == 1.0
    assert osc["regret_log_amp"] == 0.0
    assert osc["total_evaluations"] == 181
    assert osc["total_evaluations"] < report["summary"]["tang_cross_k20"]["total_evaluations"]
    assert osc["total_evaluations"] > poly["total_evaluations"]
    assert poly["diamond_recall"] == 1.0


def test_phase_angle_selector_is_fast_on_curved_phase_landscape() -> None:
    """Curved-phase relation can be cheaper than edge search once mapped.

    This is the athlete-style regime: the useful relation is an angular cycle,
    not a straight line or a sign-facet edge. A tiny phase frontier recovers the
    planted pairs because the answer is encoded in repeated phase timing.
    """

    rng = np.random.default_rng(23)
    dim = 32
    n = 48
    M = np.eye(dim)
    A = 0.15 * rng.standard_normal((n, dim))
    B = 0.15 * rng.standard_normal((n, dim))
    diamond_a_idx = [2, 11, 27, 39]
    diamond_b_idx = [5, 16, 31, 44]
    phases = [0.2, 1.7, 3.3, 5.1]
    for ai, bj, theta in zip(diamond_a_idx, diamond_b_idx, phases):
        vector = np.zeros(dim)
        vector[0] = math.cos(theta)
        vector[1] = math.sin(theta)
        A[ai] = 5.0 * vector
        B[bj] = 5.0 * vector

    pairs, evaluations, meta = select_phase_angle_cross(
        A,
        B,
        M,
        seed_count=4,
        offsets=1,
        angle_width=1,
        budget_pairs=4,
    )
    diamond_pairs = set(zip(diamond_a_idx, diamond_b_idx))
    assert diamond_pairs.issubset(set(pairs))
    assert evaluations <= 8
    assert meta["frontier_size"] == evaluations


def test_constructive_oscillation_runs_fast_on_curved_phase_landscape() -> None:
    rng = np.random.default_rng(23)
    dim = 32
    n = 48
    M = np.eye(dim)
    A = 0.15 * rng.standard_normal((n, dim))
    B = 0.15 * rng.standard_normal((n, dim))
    diamond_a_idx = [2, 11, 27, 39]
    diamond_b_idx = [5, 16, 31, 44]
    phases = [0.2, 1.7, 3.3, 5.1]
    for ai, bj, theta in zip(diamond_a_idx, diamond_b_idx, phases):
        vector = np.zeros(dim)
        vector[0] = math.cos(theta)
        vector[1] = math.sin(theta)
        A[ai] = 5.0 * vector
        B[bj] = 5.0 * vector

    pairs, evaluations, meta = select_constructive_oscillation_cross(
        A,
        B,
        M,
        seed_count=4,
        oscillations=1,
        beam_width=1,
        budget_pairs=4,
    )
    diamond_pairs = set(zip(diamond_a_idx, diamond_b_idx))
    assert diamond_pairs.issubset(set(pairs))
    assert evaluations <= 8
    assert meta["frontier_size"] == evaluations
    assert meta["max_vote"] > 0.0
    assert meta["score_model"] == "inverse_lyapunov_derivative"


def test_platonic_walk_emits_polyhedron_structural_metadata() -> None:
    """Platonic-solid walk: edges count turnings; metadata is the fingerprint.

    The Platonic-solid walk is a geometrically literal compass: every
    visited vertex is one amplitude evaluation (one "turning"), and the
    polyhedron's graph-diameter bounds worst-case turnings to reach any
    region. Recall is gated by the rank-3 projection of the coupling
    matrix M: under a full-rank random-orthogonal M (the strong-key
    default), the 3D compass is structurally too coarse and recall is
    typically 0. Under low-rank coupling it can succeed. This test
    validates the structural fingerprint shipping in run_compare and
    locks the per-polyhedron expected vertex/edge/diameter triples.
    """

    spec = DualStateSpec(n_a=80, n_b=80, n_diamond_pairs=4, n_decoys_per_side=12, seed=19)
    report = run_compare(spec, budget_pairs=8)
    summary = report["summary"]

    expected_geometry = {
        "polyhedral_walk_tetrahedron": (4, 6, 1),
        "polyhedral_walk_octahedron": (6, 12, 2),
        "polyhedral_walk_cube": (8, 12, 3),
        "polyhedral_walk_icosahedron": (12, 30, 3),
        "polyhedral_walk_dodecahedron": (20, 30, 5),
    }
    for name, (n_v, n_e, diameter) in expected_geometry.items():
        assert name in summary, f"expected {name} in summary"
        row = summary[name]
        meta = row["polyhedral_walk"]
        assert meta["n_vertices"] == n_v, f"{name}: vertices"
        assert meta["n_edges"] == n_e, f"{name}: edges"
        assert meta["diameter"] == diameter, f"{name}: diameter"
        assert meta["turnings"] >= 0
        assert meta["turnings"] <= n_v - 1
        assert row["evaluations"] == meta["unique_pair_evaluations"]
        assert row["evaluations"] <= n_v
        assert row["cost_accounting"] == "direct"


def test_platonic_walk_succeeds_on_intentional_3d_landscape() -> None:
    """Platonic walk recovers diamonds when the landscape lives in R^3.

    Construct a coupling where the diamond directions are guaranteed to
    lie in the same R^3 subspace as the polyhedron compass. With a
    rank-3 diagonal M and diamonds planted along three positive axes, the
    octahedron's 6-vertex compass should land each diamond on its own
    vertex.
    """

    rng = np.random.default_rng(7)
    dim = 32
    n_a = 60
    n_b = 60
    M = np.zeros((dim, dim))
    M[0, 0] = 3.0
    M[1, 1] = 2.0
    M[2, 2] = 1.0

    A = 0.1 * rng.standard_normal((n_a, dim))
    B = 0.1 * rng.standard_normal((n_b, dim))
    diamond_a_idx = [3, 17, 41]
    diamond_b_idx = [9, 28, 52]
    for k, (ai, bj) in enumerate(zip(diamond_a_idx, diamond_b_idx)):
        direction = np.zeros(dim)
        direction[k] = 1.0
        A[ai] = 5.0 * direction
        B[bj] = 5.0 * direction

    # Octahedron: vertices at (+/-1, 0, 0), (0, +/-1, 0), (0, 0, +/-1).
    # The three planted directions map exactly to three of those axis vertices
    # in U_3 coordinates, so all three diamonds resolve.
    pairs, evaluations, meta = select_polyhedral_walk_cross(A, B, M, polyhedron="octahedron", budget_pairs=8)
    assert meta["n_vertices"] == 6
    assert evaluations <= 6
    diamond_pairs = set(zip(diamond_a_idx, diamond_b_idx))
    found = diamond_pairs & set(pairs)
    assert len(found) == len(diamond_pairs), f"expected all 3 diamonds, found {len(found)}: pairs={pairs}"


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
