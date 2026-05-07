from __future__ import annotations

import json

import pytest

from scripts.experiments.mahss_metamaterial_sim import (
    OperatingPoint,
    SCHEMA_VERSION,
    VARIANTS,
    auxetic_porosity,
    build_actuation_grid,
    compare_search_modes,
    constructive_dissonance_profile,
    expand_variants,
    run_simulation,
    select_asymmetric_well_candidates,
    select_algebraic_hybrid_candidates,
    select_constructive_dissonance_candidates,
    select_length_square_beam_candidates,
    select_length_square_candidates,
    select_morton_stride_candidates,
    write_report,
)


def test_auxetic_porosity_closes_monotonically_under_actuation() -> None:
    variant = VARIANTS[0]

    relaxed = auxetic_porosity(variant, 0.0)
    half = auxetic_porosity(variant, 0.5)
    closed = auxetic_porosity(variant, 1.0)

    assert relaxed == variant.relaxed_porosity
    assert relaxed > half > closed
    assert 0.0 < closed < 1.0


def test_run_simulation_returns_ranked_mahss_report() -> None:
    report = run_simulation(objective="balanced")

    assert report["schema_version"] == SCHEMA_VERSION
    assert report["variant_count"] == len(VARIANTS)
    assert report["candidate_count"] == len(VARIANTS) * 5
    assert len(report["ranked"]) == report["candidate_count"]

    top = report["top_design"]
    assert top == report["ranked"][0]
    assert top["score"] >= report["ranked"][-1]["score"]
    assert 0.0 <= top["metrics"]["porosity"] <= 1.0
    assert top["mahss"]["schema_version"] == "scbe_mahss_v1"
    assert top["mahss"]["selected_mechanism"] in report["mechanisms"]


def test_run_simulation_is_deterministic() -> None:
    first = run_simulation(objective="release")
    second = run_simulation(objective="release")

    assert first == second


def test_tang_sampled_search_evaluates_budgeted_subset() -> None:
    report = run_simulation(objective="balanced", search_mode="tang_sampled", sample_budget=6, sample_seed=11)

    assert report["search_mode"] == "tang_sampled"
    assert report["candidate_pool_count"] == len(VARIANTS) * 5
    assert report["candidate_count"] == 6
    assert report["evaluated_candidate_count"] == 6
    sampling = report["length_square_sampling"]
    assert sampling["enabled"] is True
    assert len(sampling["probabilities"]) == report["candidate_pool_count"]
    assert sum(sampling["probabilities"].values()) == pytest.approx(1.0)


def test_length_square_candidate_selection_is_deterministic_and_keeps_top_energy() -> None:
    candidates = [(variant, 0.5) for variant in VARIANTS]

    selected_a, probabilities = select_length_square_candidates(
        candidates,
        op=OperatingPoint(),
        objective="balanced",
        sample_budget=3,
        sample_seed=7,
    )
    selected_b, _ = select_length_square_candidates(
        candidates,
        op=OperatingPoint(),
        objective="balanced",
        sample_budget=3,
        sample_seed=7,
    )

    top_key = max(probabilities, key=probabilities.get)
    selected_keys = {f"{variant.name}@{actuation:.6f}" for variant, actuation in selected_a}
    assert selected_a == selected_b
    assert len(selected_a) == 3
    assert top_key in selected_keys


def test_tang_beam_search_keeps_highest_energy_candidates() -> None:
    candidates = [(variant, actuation) for variant in VARIANTS for actuation in (0.0, 0.5, 1.0)]

    selected, probabilities = select_length_square_beam_candidates(
        candidates,
        op=OperatingPoint(),
        objective="balanced",
        sample_budget=4,
    )

    expected_keys = {key for key, _ in sorted(probabilities.items(), key=lambda item: item[1], reverse=True)[:4]}
    selected_keys = {f"{variant.name}@{actuation:.6f}" for variant, actuation in selected}

    assert selected_keys == expected_keys


def test_tang_beam_search_runs_without_random_sampling() -> None:
    report = run_simulation(objective="release", search_mode="tang_beam", sample_budget=5)

    assert report["search_mode"] == "tang_beam"
    assert report["candidate_count"] == 5
    assert report["length_square_sampling"]["enabled"] is True


def test_morton_stride_search_uses_reversible_1d_locality_order() -> None:
    candidates = [(variant, actuation) for variant in VARIANTS for actuation in (0.0, 0.25, 0.5)]

    selected, telemetry = select_morton_stride_candidates(
        candidates,
        sample_budget=5,
        variant_order=[variant.name for variant in VARIANTS],
        actuation_values=(0.0, 0.25, 0.5),
    )

    assert telemetry["schema_version"] == "scbe_morton_stride_selection_v1"
    assert telemetry["bits"] == 3
    assert len(selected) == 5
    assert telemetry["selected_keys"] == [f"{variant.name}@{actuation:.6f}" for variant, actuation in selected]


def test_morton_stride_runs_as_side_by_side_baseline() -> None:
    report = run_simulation(objective="balanced", search_mode="morton_stride", sample_budget=6)

    assert report["search_mode"] == "morton_stride"
    assert report["candidate_count"] == 6
    assert report["morton"]["schema_version"] == "scbe_morton_stride_selection_v1"


def test_radial_beam_search_emits_path_aware_hints() -> None:
    report = run_simulation(
        objective="balanced",
        search_mode="radial_beam",
        sample_budget=5,
        sampling_power=2.125,
        path_history=("mae_silicone_ferrite_lattice@0.750000",),
    )

    hints = report["length_square_sampling"]["radial_hints"]
    assert report["search_mode"] == "radial_beam"
    assert report["candidate_count"] == 5
    assert hints
    assert all("power" in row and "novelty" in row and "quasicrystal_phase" in row for row in hints.values())


def test_constructive_dissonance_profile_scores_useful_disagreement() -> None:
    candidates = [(variant, 0.5) for variant in VARIANTS]
    profile = constructive_dissonance_profile(candidates, OperatingPoint(), objective="balanced")

    assert set(profile) == {f"{variant.name}@0.500000" for variant in VARIANTS}
    assert all(row["spread"] >= 0.0 for row in profile.values())
    assert all(row["constructive_dissonance"] >= 0.0 for row in profile.values())
    assert all(row["destructive_dissonance"] >= 0.0 for row in profile.values())


def test_asymmetric_well_search_keeps_signed_residual_hints() -> None:
    candidates = [(variant, actuation) for variant in VARIANTS for actuation in (0.0, 0.5, 1.0)]
    selected, probabilities, profile = select_asymmetric_well_candidates(
        candidates,
        OperatingPoint(),
        objective="balanced",
        sample_budget=4,
        sampling_power=2.125,
    )

    assert len(selected) == 4
    assert sum(probabilities.values()) == pytest.approx(1.0)
    assert all("positive_residual_norm" in row and "negative_residual_norm" in row for row in profile.values())


def test_asymmetric_well_runs_as_third_state_search_mode() -> None:
    report = run_simulation(objective="balanced", search_mode="asymmetric_well", sample_budget=6)

    assert report["search_mode"] == "asymmetric_well"
    assert report["candidate_count"] == 6
    assert report["length_square_sampling"]["asymmetric_hints"]


def test_constructive_dissonance_prunes_to_best_scored_candidates() -> None:
    candidates = [(variant, actuation) for variant in VARIANTS for actuation in (0.0, 0.5, 1.0)]
    selected, probabilities, profile = select_constructive_dissonance_candidates(
        candidates,
        OperatingPoint(),
        objective="balanced",
        sample_budget=4,
    )

    expected = {key for key, _ in sorted(profile.items(), key=lambda item: item[1]["score"], reverse=True)[:4]}
    actual = {f"{variant.name}@{actuation:.6f}" for variant, actuation in selected}

    assert actual == expected
    assert sum(probabilities.values()) == pytest.approx(1.0)


def test_constructive_dissonance_mode_emits_hints() -> None:
    report = run_simulation(objective="balanced", search_mode="dissonance_pruned", sample_budget=6)

    assert report["search_mode"] == "dissonance_pruned"
    assert report["candidate_count"] == 6
    assert report["length_square_sampling"]["dissonance_hints"]


def test_algebraic_hybrid_combines_signals_into_one_selector() -> None:
    candidates = [(variant, actuation) for variant in VARIANTS for actuation in (0.0, 0.5, 1.0)]
    selected, probabilities, telemetry = select_algebraic_hybrid_candidates(
        candidates,
        OperatingPoint(),
        objective="balanced",
        sample_budget=5,
        variant_order=[variant.name for variant in VARIANTS],
        actuation_values=(0.0, 0.5, 1.0),
        sampling_power=2.125,
    )

    assert len(selected) == 5
    assert sum(probabilities.values()) == pytest.approx(1.0)
    assert telemetry["schema_version"] == "scbe_mahss_algebraic_hybrid_selector_v1"
    assert "radial_probability" in telemetry["formula"]


def test_algebraic_hybrid_runs_as_single_algorithm() -> None:
    report = run_simulation(objective="balanced", search_mode="algebraic_hybrid", sample_budget=6)

    assert report["search_mode"] == "algebraic_hybrid"
    assert report["candidate_count"] == 6
    assert report["algebraic_hybrid"]["schema_version"] == "scbe_mahss_algebraic_hybrid_selector_v1"


def test_search_modes_compare_against_exhaustive_and_uniform_baselines() -> None:
    report = compare_search_modes(objective="balanced", sample_budget=6, sample_seed=17)

    assert report["schema_version"] == "scbe_mahss_search_comparison_v1"
    assert set(report["summary"]) == {
        "exhaustive",
        "uniform_sampled",
        "tang_beam_2",
        "tang_beam_2_125",
        "radial_beam_2_125",
        "polar_beam_2_125",
        "asymmetric_well_2_125",
        "morton_stride",
        "dissonance_pruned",
        "algebraic_hybrid",
        "multigrid_top2",
        "mirror_beam_c1",
    }
    assert report["summary"]["exhaustive"]["score_regret_vs_exhaustive"] == 0.0
    assert report["summary"]["uniform_sampled"]["evaluated_candidate_count"] == 6
    assert report["summary"]["tang_beam_2_125"]["evaluated_candidate_count"] == 6
    assert report["summary"]["radial_beam_2_125"]["evaluated_candidate_count"] == 6
    assert report["summary"]["polar_beam_2_125"]["evaluated_candidate_count"] == 6
    assert report["summary"]["asymmetric_well_2_125"]["evaluated_candidate_count"] == 6
    assert report["summary"]["morton_stride"]["evaluated_candidate_count"] == 6
    assert report["summary"]["dissonance_pruned"]["evaluated_candidate_count"] == 6
    assert report["summary"]["algebraic_hybrid"]["evaluated_candidate_count"] == 6
    assert report["summary"]["mirror_beam_c1"]["evaluated_candidate_count"] == 6
    multigrid_row = report["summary"]["multigrid_top2"]
    assert multigrid_row["score_regret_vs_exhaustive"] == 0.0
    assert multigrid_row["evaluated_candidate_count"] < report["summary"]["exhaustive"]["evaluated_candidate_count"]


def test_scaled_candidate_board_is_deterministic_and_budgeted() -> None:
    variants = expand_variants(variants_per_base=3)
    actuation_grid = build_actuation_grid(7)
    report = compare_search_modes(
        objective="balanced",
        sample_budget=12,
        sample_seed=17,
        variants=variants,
        actuation_grid=actuation_grid,
    )

    assert len(variants) == len(VARIANTS) * 3
    assert report["candidate_pool_count"] == len(variants) * len(actuation_grid)
    assert report["summary"]["exhaustive"]["evaluated_candidate_count"] == len(variants) * len(actuation_grid)
    assert report["summary"]["algebraic_hybrid"]["evaluated_candidate_count"] == 12
    assert report["summary"]["multigrid_top2"]["evaluated_candidate_count"] < len(variants) * len(actuation_grid)


def test_mirror_beam_uses_hyperbolic_distance_one_pass_selection() -> None:
    report = run_simulation(objective="balanced", search_mode="mirror_beam", sample_budget=6)

    assert report["search_mode"] == "mirror_beam"
    assert report["candidate_count"] == 6
    mirror = report["mirror"]
    assert isinstance(mirror, dict)
    assert mirror, "mirror telemetry should not be empty"
    for _key, row in mirror.items():
        assert "hyperbolic_distance" in row
        assert "reflection_amplitude" in row
        assert "euclidean_norm" in row
        assert row["hyperbolic_distance"] >= 0.0
        assert 0.0 <= row["reflection_amplitude"] <= 1.0
    distances_by_key = {key: row["hyperbolic_distance"] for key, row in mirror.items()}
    selected_keys = {f"{cand['variant']}@{cand['metrics']['actuation_fraction']:.6f}" for cand in report["ranked"]}
    smallest_six = {key for key, _ in sorted(distances_by_key.items(), key=lambda item: item[1])[:6]}
    assert selected_keys == smallest_six


def test_multigrid_recovers_exhaustive_optimum_with_fewer_evaluations() -> None:
    exhaustive = run_simulation(objective="balanced", search_mode="exhaustive")
    multigrid = run_simulation(objective="balanced", search_mode="multigrid", sample_budget=2)

    exhaustive_top = exhaustive["top_design"]
    multigrid_top = multigrid["top_design"]
    assert isinstance(exhaustive_top, dict) and isinstance(multigrid_top, dict)
    assert float(multigrid_top["score"]) == pytest.approx(float(exhaustive_top["score"]))
    assert multigrid["evaluated_candidate_count"] < exhaustive["evaluated_candidate_count"]

    telemetry = multigrid["multigrid"]
    assert isinstance(telemetry, dict)
    coarse_pass = telemetry["coarse_pass"]
    assert isinstance(coarse_pass, list)
    assert len(coarse_pass) == len(VARIANTS)
    assert telemetry["top_k"] == 2
    assert telemetry["coarse_evaluations"] == len(VARIANTS)
    assert telemetry["total_evaluations"] == multigrid["evaluated_candidate_count"]
    assert telemetry["exhaustive_budget"] == exhaustive["evaluated_candidate_count"]


def test_objectives_can_choose_different_designs() -> None:
    filter_report = run_simulation(objective="filter")
    high_heat_report = run_simulation(objective="high_heat")

    assert filter_report["top_design"]["variant"]
    assert high_heat_report["top_design"]["variant"]
    assert filter_report["top_design"]["metrics"]["porosity"] >= 0.0
    assert high_heat_report["top_design"]["metrics"]["temperature_headroom"] >= 0.0


def test_write_report_round_trips_json(tmp_path) -> None:
    report = run_simulation(objective="balanced")
    output = tmp_path / "mahss_report.json"

    write_report(report, output)

    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded == report
