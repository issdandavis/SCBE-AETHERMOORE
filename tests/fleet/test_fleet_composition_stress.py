"""Reproducibility checks for the fleet-composition stress matrix."""

from __future__ import annotations

from scripts.benchmark.fleet_composition_stress import (
    _effect,
    network_scenarios,
    run_benchmark,
    write_report,
)
from src.fleet.composition_coordinator import CoordinationPolicy


def test_small_stress_matrix_has_controls_and_billed_custom_arm() -> None:
    seeds = (3, 7, 11)
    payload = run_benchmark(seeds, tasks_per_seed=12)

    assert payload["claim_status"] in {"SUPPORTED", "UNDERPOWERED", "NO_LIFT"}
    assert payload["blackout_relay_claim_status"] in {
        "SUPPORTED",
        "UNDERPOWERED",
        "NO_LIFT",
    }
    assert (
        payload["method"]["custom_policy"] == CoordinationPolicy.STABILITY_GUARDED.value
    )
    assert payload["method"]["controls"] == {
        "no_intervention": CoordinationPolicy.STICKY.value,
        "size_matched_zero_tuned": CoordinationPolicy.DISTANCE.value,
        "adaptive_ablation": CoordinationPolicy.COMPOSITION_AWARE.value,
    }
    assert len(payload["runs"]) == len(seeds) * len(network_scenarios()) * len(
        CoordinationPolicy
    )

    expected_metrics = {
        "completion_rate",
        "cost_per_completed",
        "mean_transition_stability",
        "transition_churn",
    }
    for comparison in payload["comparisons"].values():
        assert set(comparison) == expected_metrics
    assert set(payload["comparisons_by_scenario"]) == {
        network.name for network in network_scenarios()
    }
    for scenario in payload["comparisons_by_scenario"].values():
        assert set(scenario) == {
            CoordinationPolicy.STICKY.value,
            CoordinationPolicy.DISTANCE.value,
        }
        assert all(
            set(comparison) == expected_metrics for comparison in scenario.values()
        )

    custom_summary = payload["summary_by_policy"][
        CoordinationPolicy.STABILITY_GUARDED.value
    ]
    assert custom_summary["candidate_evaluations"]["mean"] > 0
    assert set(payload["blackout_architecture_comparison"]) == {
        policy.value for policy in CoordinationPolicy
    }


def test_benchmark_exposes_clone_and_full_spectrum_controls(tmp_path) -> None:
    payload = run_benchmark((5,), tasks_per_seed=6)
    geometry = payload["composition_geometry"]

    assert geometry["clone_line"]["rank"] == 1
    assert geometry["clone_line"]["blind_dimensions"] == 5
    assert geometry["full_spectrum_6"]["rank"] == 6
    assert geometry["full_spectrum_6"]["blind_dimensions"] == 0

    payload["summary_by_policy"][CoordinationPolicy.ROUND_ROBIN.value][
        "cost_per_completed"
    ]["mean"] = None
    json_path, markdown_path = write_report(payload, tmp_path / "tiny-stress.json")
    assert json_path.is_file()
    assert markdown_path.is_file()
    assert "n/a" in markdown_path.read_text(encoding="utf-8")


def test_empty_effect_is_reported_as_insufficient_data() -> None:
    effect = _effect([], [], metric="cost_per_completed", higher_is_better=False)

    assert effect["status"] == "INSUFFICIENT_DATA"
    assert effect["custom_mean"] is None
    assert effect["baseline_mean"] is None
