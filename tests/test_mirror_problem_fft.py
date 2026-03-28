from __future__ import annotations

import numpy as np
import pytest

from src.minimal.mirror_problem_fft import (
    apply_thermal_mirage,
    apply_thermal_mirror,
    attention_signal,
    compare_attention_to_controls,
    compute_spectral_probe,
    derive_thermal_profiles,
    edge_mirror,
    make_banded_control,
    make_random_control,
    make_uniform_control,
    probe_attention_matrix,
    signal_mirror,
    whole_mirror,
)


def test_attention_signal_modes_have_expected_shapes() -> None:
    matrix = make_random_control(8, seed=11)

    assert attention_signal(matrix, mode="row_mean").shape == (8,)
    assert attention_signal(matrix, mode="column_mean").shape == (8,)
    assert attention_signal(matrix, mode="diagonal").shape == (8,)
    assert attention_signal(matrix, mode="flatten").shape == (64,)


def test_attention_signal_rejects_invalid_shape_and_mode() -> None:
    with pytest.raises(ValueError):
        attention_signal(np.ones(8), mode="row_mean")

    with pytest.raises(ValueError):
        attention_signal(np.ones((8, 8)), mode="bad-mode")


def test_uniform_control_has_maximal_coherence_after_centering_short_circuit() -> None:
    probe = probe_attention_matrix(make_uniform_control(8), mode="flatten")

    assert probe.s_spec == pytest.approx(1.0)
    assert probe.energy_total == pytest.approx(0.0)
    assert probe.spectral_entropy == pytest.approx(0.0)


def test_banded_control_is_more_structured_than_random_control() -> None:
    banded = probe_attention_matrix(make_banded_control(16), mode="flatten")
    random = probe_attention_matrix(make_random_control(16, seed=19), mode="flatten")

    assert banded.s_spec > random.s_spec
    assert banded.peak_ratio > random.peak_ratio
    assert banded.spectral_entropy < random.spectral_entropy


def test_fft_probe_is_invariant_to_signal_roll() -> None:
    signal = attention_signal(make_banded_control(16), mode="flatten")
    rolled = np.roll(signal, 9)

    original = compute_spectral_probe(signal)
    shifted = compute_spectral_probe(rolled)

    assert shifted.s_spec == pytest.approx(original.s_spec)
    assert shifted.peak_ratio == pytest.approx(original.peak_ratio)
    assert shifted.spectral_entropy == pytest.approx(original.spectral_entropy)


def test_candidate_banded_attention_matches_banded_control_better_than_random() -> None:
    comparison = compare_attention_to_controls(make_banded_control(16), mode="flatten")

    banded_gap = abs(comparison.candidate.s_spec - comparison.banded_control.s_spec)
    random_gap = abs(comparison.candidate.s_spec - comparison.random_control.s_spec)

    assert banded_gap < random_gap


def test_rectangular_controls_and_comparison_work_for_hidden_state_shapes() -> None:
    matrix = make_banded_control(6, 12)
    comparison = compare_attention_to_controls(matrix, mode="flatten")

    assert matrix.shape == (6, 12)
    assert comparison.candidate.s_spec > 0.0
    assert comparison.uniform_control.energy_total >= 0.0


def test_whole_mirror_preserves_probe_metrics_for_attention_like_matrix() -> None:
    matrix = make_banded_control(12)

    original = probe_attention_matrix(matrix, mode="flatten")
    mirrored = probe_attention_matrix(whole_mirror(matrix), mode="flatten")

    assert mirrored.s_spec == pytest.approx(original.s_spec)
    assert mirrored.peak_ratio == pytest.approx(original.peak_ratio)
    assert mirrored.spectral_entropy == pytest.approx(original.spectral_entropy)


def test_edge_and_signal_mirrors_preserve_shape() -> None:
    matrix = make_banded_control(6, 10)

    assert edge_mirror(matrix).shape == (10, 6)
    assert signal_mirror(matrix).shape == matrix.shape


def test_thermal_profiles_normalize_and_thermal_mirror_scales_hot_regions() -> None:
    matrix = np.array(
        [
            [4.0, 4.0, 4.0, 4.0],
            [2.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [0.5, 0.0, 0.0, 0.0],
        ],
        dtype=np.float64,
    )

    row_heat, col_heat = derive_thermal_profiles(matrix, source="l2_norm")
    transformed, profile = apply_thermal_mirror(
        matrix, alpha=1.5, source="l2_norm", min_scale=0.2
    )

    assert row_heat.max() == pytest.approx(1.0)
    assert row_heat.min() == pytest.approx(0.0)
    assert col_heat.max() == pytest.approx(1.0)
    assert transformed.shape == matrix.shape
    assert float(profile["row_scale"][0]) <= float(profile["row_scale"][-1])
    assert np.abs(transformed[0, 0]) < np.abs(matrix[0, 0])


def test_phase_mirage_returns_complex_matrix_and_preserves_probe_execution() -> None:
    matrix = make_banded_control(10)

    transformed, profile = apply_thermal_mirage(matrix, alpha=1.0, sigma=2.0)
    probe = probe_attention_matrix(transformed, mode="flatten")

    assert np.iscomplexobj(transformed)
    assert profile["variant"] == "phase_mirage"
    assert probe.energy_total >= 0.0
