import math

import numpy as np
import pytest

from src.harmonic.state21_product_metric import (
    State21Error,
    compute_energy_harmonic,
    compute_radial_norm,
    parse_state21_v1,
    product_metric_distance_v1,
    validate_state21_v1,
)


def _state_with_caches(seed: int = 123) -> np.ndarray:
    rng = np.random.default_rng(seed)

    # Tongue embedding in open Poincare ball
    u = rng.normal(0.0, 0.08, size=6)
    u = u / max(1.0, np.linalg.norm(u) / 0.45)

    # Phase angles on T^6
    theta = rng.uniform(-math.pi, math.pi, size=6)

    # Telemetry slots [12:21)
    flux_participation = 0.3
    coherence_spectral = 0.91
    coherence_spin = 0.88
    coherence_triadic = 0.86
    risk_aggregate = 0.22
    entropy_density = 0.15
    stabilization = 0.74

    radial = compute_radial_norm(u)
    harmonic = compute_energy_harmonic(u)

    telemetry = np.array(
        [
            flux_participation,
            coherence_spectral,
            coherence_spin,
            coherence_triadic,
            risk_aggregate,
            entropy_density,
            stabilization,
            radial,
            harmonic,
        ],
        dtype=float,
    )

    return np.concatenate([u, theta, telemetry])


def test_validate_accepts_consistent_state21_v1():
    s = _state_with_caches()
    st = parse_state21_v1(s)
    metrics = validate_state21_v1(st)

    assert metrics["u_norm"] < 1.0
    assert metrics["radial_abs_err"] < 1e-10
    assert metrics["harmonic_abs_err"] < 1e-10


def test_distance_is_zero_for_identical_state():
    s = _state_with_caches()
    d = product_metric_distance_v1(s, s)
    assert d == pytest.approx(0.0, abs=1e-12)


def test_validate_rejects_out_of_ball_embedding():
    s = _state_with_caches()
    s[0] = 1.05
    st = parse_state21_v1(s)

    with pytest.raises(State21Error):
        validate_state21_v1(st)


def test_torus_wrap_small_across_2pi_boundary():
    a = _state_with_caches(seed=1)
    b = a.copy()

    # Same state except one phase axis wraps across +pi/-pi boundary.
    a[6] = math.pi - 0.01
    b[6] = -math.pi + 0.01

    d = product_metric_distance_v1(a, b)
    # Wrapped delta should be ~0.02, not ~2*pi.
    assert d < 0.2
