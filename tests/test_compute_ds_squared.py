import numpy as np
import pytest

from src.harmonic.compute_ds_squared import (
    boundary_amplification,
    computeDsSquared,
    fisher_rao_distance_squared,
)


def test_fisher_rao_zero_for_identical_distributions():
    p = [0.2, 0.3, 0.5]
    assert fisher_rao_distance_squared(p, p) == pytest.approx(0.0, abs=1e-12)


def test_fisher_rao_is_symmetric():
    p = [0.6, 0.4]
    q = [0.2, 0.8]
    d_pq = fisher_rao_distance_squared(p, q)
    d_qp = fisher_rao_distance_squared(q, p)
    assert d_pq == pytest.approx(d_qp, rel=1e-12)


def test_boundary_amplification_increases_near_boundary():
    assert boundary_amplification(0.1) < boundary_amplification(0.8)
    assert boundary_amplification(0.8) < boundary_amplification(0.95)


def test_compute_ds_squared_zero_for_identical_points_without_fisher():
    u = np.array([0.2, 0.1, 0.0, 0.0, 0.0, 0.0], dtype=float)
    out = computeDsSquared(u, u)
    assert out["ds_squared"] == pytest.approx(0.0, abs=1e-12)
    assert out["hyperbolic_distance"] == pytest.approx(0.0, abs=1e-12)


def test_compute_ds_squared_grows_near_boundary_for_same_euclidean_step():
    u_center = np.array([0.10, 0, 0, 0, 0, 0], dtype=float)
    v_center = np.array([0.12, 0, 0, 0, 0, 0], dtype=float)
    center = computeDsSquared(u_center, v_center)

    u_edge = np.array([0.90, 0, 0, 0, 0, 0], dtype=float)
    v_edge = np.array([0.92, 0, 0, 0, 0, 0], dtype=float)
    edge = computeDsSquared(u_edge, v_edge)

    assert edge["hyperbolic_squared"] > center["hyperbolic_squared"]
    assert edge["hyperbolic_scaled_squared"] > center["hyperbolic_scaled_squared"]
