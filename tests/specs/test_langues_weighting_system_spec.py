"""Regression contract for the profile-aware Langues Weighting System spec."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from src.symphonic_cipher.scbe_aethermoore.axiom_grouped.langues_metric import (
    PHASE_AMPLITUDE,
    TONGUE_FREQUENCIES,
    TONGUE_WEIGHTS,
    HyperspacePoint,
    LanguesMetric,
)

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "docs" / "specs" / "langues_weighting_system_profiles.json"
SPACE_TOR_WEIGHTS = np.array([1.0, 1.125, 1.25, 1.333, 1.5, 1.667])
SPACE_TOR_BETA = np.ones(6)
SPACE_TOR_OMEGA = np.arange(1.0, 7.0)
SPACE_TOR_PHASE = np.arange(6) * (2.0 * np.pi / 6.0)


def _registry() -> dict[str, object]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _spacetor_components(
    x: np.ndarray,
    mu: np.ndarray,
    t: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    deviations = np.abs(x - mu)
    oscillation = np.sin(SPACE_TOR_OMEGA * t + SPACE_TOR_PHASE)
    terms = SPACE_TOR_WEIGHTS * np.exp(SPACE_TOR_BETA * (deviations + oscillation))
    gradient = terms * np.sign(x - mu)
    return oscillation, terms, gradient


def test_registry_names_every_implemented_cost_profile() -> None:
    registry = _registry()
    profiles = registry["profiles"]

    assert registry["canonical_kernel_runtime"] == "kernel-v1"
    assert registry["public_cost_profiles"] == ["kernel-v1", "spacetor-v1"]
    assert {
        "lws-linear-v1",
        "kernel-v1",
        "spacetor-v1",
        "python-axiom-v1",
        "notebook-2026-01",
    } <= set(profiles)

    spacetor = profiles["spacetor-v1"]
    assert spacetor["weight_profile"] == "lws-linear"
    assert spacetor["weights"]["values"] == pytest.approx(SPACE_TOR_WEIGHTS)
    assert spacetor["beta"]["default_values"] == pytest.approx(SPACE_TOR_BETA)
    assert spacetor["frequency"]["values"] == pytest.approx(SPACE_TOR_OMEGA)
    assert spacetor["phase"]["amplitude"] == 1.0

    python_axiom = profiles["python-axiom-v1"]
    assert python_axiom["weight_profile"] == "phdm-golden"
    assert python_axiom["phase"]["amplitude"] == PHASE_AMPLITUDE
    assert python_axiom["frequency"]["values"] == [
        "1/1",
        "9/8",
        "5/4",
        "4/3",
        "3/2",
        "5/3",
    ]


def test_lws_linear_weights_are_just_intonation_not_golden_powers() -> None:
    just_intonation = np.array([1.0, 9 / 8, 5 / 4, 4 / 3, 3 / 2, 5 / 3])
    relative_ji_error = np.abs(SPACE_TOR_WEIGHTS - just_intonation) / just_intonation

    golden_ratio = (1.0 + math.sqrt(5.0)) / 2.0
    golden_powers = golden_ratio ** np.arange(6)
    relative_golden_error = np.abs(SPACE_TOR_WEIGHTS - golden_powers) / golden_powers

    assert relative_ji_error.max() == pytest.approx(0.00025)
    assert relative_ji_error.mean() == pytest.approx(0.000075)
    assert relative_golden_error.mean() == pytest.approx(0.523902547955, abs=1e-12)


def test_python_axiom_profile_constants_match_the_registry() -> None:
    just_intonation = [1.0, 9 / 8, 5 / 4, 4 / 3, 3 / 2, 5 / 3]
    golden_ratio = (1.0 + math.sqrt(5.0)) / 2.0

    assert TONGUE_FREQUENCIES == pytest.approx(just_intonation)
    assert TONGUE_WEIGHTS == pytest.approx([golden_ratio**index for index in range(6)])
    assert PHASE_AMPLITUDE == pytest.approx(0.1)


def test_spacetor_worked_example_is_exact_and_reproducible() -> None:
    x = np.array([0.8, 0.6, 0.4, 0.2, 0.1, 0.9])
    mu = np.full(6, 0.5)
    oscillation, terms, gradient = _spacetor_components(x, mu, t=1.0)

    expected_oscillation = np.array(
        [
            0.8414709848078965,
            0.0942549812584854,
            -0.9279186556418991,
            0.7568024953079282,
            0.2338034786274037,
            -0.9712396092976662,
        ]
    )
    expected_terms = np.array(
        [
            3.1313711784533886,
            1.3662066310033971,
            0.5461972502257489,
            3.835249673090031,
            2.827148444081391,
            0.9415630123311372,
        ]
    )
    expected_gradient = np.array(
        [
            3.1313711784533886,
            1.3662066310033971,
            -0.5461972502257489,
            -3.835249673090031,
            -2.827148444081391,
            0.9415630123311372,
        ]
    )
    maximum = np.sum(SPACE_TOR_WEIGHTS * np.exp(2.0 * SPACE_TOR_BETA))

    assert oscillation == pytest.approx(expected_oscillation)
    assert terms == pytest.approx(expected_terms)
    assert gradient == pytest.approx(expected_gradient)
    assert terms.sum() == pytest.approx(12.647736189185094)
    assert maximum == pytest.approx(58.18881677907887)
    assert terms.sum() / maximum == pytest.approx(0.2173568202495646)


def test_published_monte_carlo_protocol_has_a_seeded_receipt() -> None:
    rng = np.random.default_rng(0)
    x = rng.random((10_000, 6))
    deviations = np.abs(x - 0.5)
    oscillation = np.sin(SPACE_TOR_OMEGA + SPACE_TOR_PHASE)
    costs = np.sum(SPACE_TOR_WEIGHTS * np.exp(deviations + oscillation), axis=1)
    total_deviation = np.sum(deviations, axis=1)

    assert costs.mean() == pytest.approx(12.216702536450999, abs=1e-12)
    assert costs.std(ddof=0) == pytest.approx(0.8258778652654359, abs=1e-12)
    assert np.corrcoef(costs, total_deviation)[0, 1] == pytest.approx(
        0.8769837617359364,
        abs=1e-12,
    )


def test_monte_carlo_protocol_matches_analytic_moments() -> None:
    oscillation = np.sin(SPACE_TOR_OMEGA + SPACE_TOR_PHASE)
    coefficients = SPACE_TOR_WEIGHTS * np.exp(oscillation)

    mean_exp_deviation = 2.0 * (math.exp(0.5) - 1.0)
    second_exp_deviation = math.e - 1.0
    mean_d_exp_deviation = 2.0 - math.exp(0.5)
    mean_deviation = 0.25

    mean = coefficients.sum() * mean_exp_deviation
    variance = np.square(coefficients).sum() * (second_exp_deviation - mean_exp_deviation**2)
    covariance = coefficients.sum() * (mean_d_exp_deviation - mean_deviation * mean_exp_deviation)
    deviation_variance = 6.0 * (0.5**2 / 12.0)
    correlation = covariance / math.sqrt(variance * deviation_variance)

    assert mean == pytest.approx(12.218868949528453)
    assert math.sqrt(variance) == pytest.approx(0.8192162234073104)
    assert correlation == pytest.approx(0.8752530380919151)


@pytest.mark.parametrize("amplitude", [0.1, 1.0])
def test_cycle_average_uses_the_profile_phase_amplitude(amplitude: float) -> None:
    beta = 1.3
    deviation = 0.4
    theta = np.linspace(0.0, 2.0 * np.pi, 4096, endpoint=False)

    numerical = np.mean(np.exp(beta * (deviation + amplitude * np.sin(theta))))
    analytic = math.exp(beta * deviation) * np.i0(beta * amplitude)

    assert numerical == pytest.approx(analytic, abs=5e-15)


def test_python_axiom_uses_zero_subgradient_at_the_absolute_value_cusp() -> None:
    metric = LanguesMetric()
    ideal = HyperspacePoint.from_vector(metric.ideal.to_vector())

    assert metric.compute_gradient(ideal, t=0.0) == pytest.approx([0.0] * 6)

    epsilon = 1e-6
    center = metric.compute(ideal, t=0.0)
    plus_vector = ideal.to_vector()
    minus_vector = ideal.to_vector()
    plus_vector[0] += epsilon
    minus_vector[0] -= epsilon

    right_derivative = (metric.compute(HyperspacePoint.from_vector(plus_vector), t=0.0) - center) / epsilon
    left_derivative = (center - metric.compute(HyperspacePoint.from_vector(minus_vector), t=0.0)) / epsilon

    assert left_derivative == pytest.approx(-1.1, rel=1e-5)
    assert right_derivative == pytest.approx(1.1, rel=1e-5)


def test_normalization_bound_requires_bounded_deviations() -> None:
    x = np.array([10.5, 0.5, 0.5, 0.5, 0.5, 0.5])
    mu = np.full(6, 0.5)
    _, terms, _ = _spacetor_components(x, mu, t=1.0)
    maximum = np.sum(SPACE_TOR_WEIGHTS * np.exp(2.0 * SPACE_TOR_BETA))

    assert terms.sum() / maximum > 1.0


def test_current_frequency_profiles_are_rationally_dependent() -> None:
    assert np.dot([2, -1, 0, 0, 0, 0], SPACE_TOR_OMEGA) == pytest.approx(0.0)
    assert np.dot([9, -8, 0, 0, 0, 0], TONGUE_FREQUENCIES) == pytest.approx(0.0)


def test_duplicate_python_axiom_surfaces_share_the_profile_contract() -> None:
    from symphonic_cipher.scbe_aethermoore.axiom_grouped.langues_metric import (
        PHASE_AMPLITUDE as MIRROR_PHASE_AMPLITUDE,
        TONGUE_FREQUENCIES as MIRROR_FREQUENCIES,
        TONGUE_WEIGHTS as MIRROR_WEIGHTS,
        HyperspacePoint as MirrorPoint,
        LanguesMetric as MirrorMetric,
    )

    assert MIRROR_PHASE_AMPLITUDE == PHASE_AMPLITUDE
    assert MIRROR_FREQUENCIES == pytest.approx(TONGUE_FREQUENCIES)
    assert MIRROR_WEIGHTS == pytest.approx(TONGUE_WEIGHTS)

    metric = MirrorMetric()
    ideal = MirrorPoint.from_vector(metric.ideal.to_vector())
    assert metric.compute_gradient(ideal, t=0.0) == pytest.approx([0.0] * 6)
