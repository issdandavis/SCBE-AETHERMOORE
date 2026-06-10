"""Focused math-regression tests for the patent support packet."""

from __future__ import annotations

import cmath
import math
import random
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.governance.runtime_gate import RuntimeGate  # noqa: E402
from scripts.research.hyperbolic_ruler import d_H, mobius_isometry  # noqa: E402


def test_runtime_gate_cost_is_monotone_in_weighted_drift():
    gate = RuntimeGate()
    gate._centroid = np.array([0.4, 0.2, 0.5, 0.1, 0.2, 0.3])

    near = [0.45, 0.2, 0.5, 0.1, 0.2, 0.3]
    mid = [0.65, 0.2, 0.5, 0.1, 0.2, 0.3]
    far = [0.95, 0.2, 0.5, 0.1, 0.2, 0.3]

    costs = [gate._harmonic_cost(coords) for coords in (near, mid, far)]

    assert costs == sorted(costs)
    assert costs[0] < costs[1] < costs[2]


def test_runtime_gate_centroid_update_is_incremental_running_mean():
    gate = RuntimeGate()
    points = [
        [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
        [0.3, 0.2, 0.1, 0.0, 0.5, 0.9],
        [0.8, 0.1, 0.1, 0.3, 0.2, 0.4],
    ]

    for point in points:
        gate._update_centroid(point)

    expected = np.mean(np.array(points), axis=0)
    assert gate._centroid_count == len(points)
    assert gate._centroid.tolist() == pytest.approx(expected.tolist())


def test_runtime_gate_cost_formula_matches_claimed_clamped_expression():
    gate = RuntimeGate()
    gate._centroid = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    coords = [0.5, 0.25, 0.0, 0.0, 0.0, 0.0]

    phi = 1.618033988749895
    weights = np.array([phi**k for k in range(6)])
    weighted_dist = float(np.sqrt(np.sum(weights * np.array(coords) ** 2)))
    d_star = min(weighted_dist, 5.0)
    expected = math.pi ** (phi * d_star)

    assert gate._harmonic_cost(coords) == pytest.approx(expected)


def test_runtime_gate_cost_is_not_mobius_invariant_even_when_true_dh_is():
    gate = RuntimeGate()
    base_centroid = complex(0.18, -0.12)
    base_point = complex(0.63, 0.21)
    base_coords = [base_point.real, base_point.imag, 0.0, 0.0, 0.0, 0.0]
    gate._centroid = np.array([base_centroid.real, base_centroid.imag, 0.0, 0.0, 0.0, 0.0], dtype=float)

    base_cost = gate._harmonic_cost(base_coords)
    base_dh = d_H(base_centroid, base_point)

    rng = random.Random(7)
    cost_drift = 0.0
    dh_drift = 0.0

    for _ in range(6):
        offset = cmath.rect(rng.uniform(0.0, 0.55), rng.uniform(0.0, 2.0 * math.pi))
        frame = mobius_isometry(offset, rng.uniform(0.0, 2.0 * math.pi))
        transformed_centroid = frame(base_centroid)
        transformed_point = frame(base_point)

        gate._centroid = np.array(
            [transformed_centroid.real, transformed_centroid.imag, 0.0, 0.0, 0.0, 0.0],
            dtype=float,
        )
        transformed_cost = gate._harmonic_cost(
            [transformed_point.real, transformed_point.imag, 0.0, 0.0, 0.0, 0.0]
        )

        cost_drift = max(cost_drift, abs(transformed_cost - base_cost))
        dh_drift = max(dh_drift, abs(d_H(transformed_centroid, transformed_point) - base_dh))

    assert dh_drift < 1e-12
    assert cost_drift > 0.1


def test_runtime_gate_stats_coords_are_not_direct_poincare_points():
    gate = RuntimeGate(coords_backend="stats")
    coords = gate._text_to_coords("Summarize this report.")

    raw_norm = float(np.linalg.norm(np.asarray(coords, dtype=float)))

    assert raw_norm > 1.0


def test_runtime_gate_projected_hyperbolic_cost_uses_valid_ball_points():
    gate = RuntimeGate(coords_backend="stats")
    gate._centroid = np.array([0.4, 0.2, 0.5, 0.1, 0.2, 0.3], dtype=float)
    coords = gate._text_to_coords("Send data to https://example.com webhook")

    projected_coords = gate._project_coords_to_unit_ball(coords)
    projected_centroid = gate._project_coords_to_unit_ball(gate._centroid.tolist())
    projected_cost = gate._experimental_projected_hyperbolic_cost(coords)

    assert float(np.linalg.norm(projected_coords)) < 1.0
    assert float(np.linalg.norm(projected_centroid)) < 1.0
    assert math.isfinite(gate._poincare_distance(projected_coords, projected_centroid))
    assert projected_cost > 1.0
