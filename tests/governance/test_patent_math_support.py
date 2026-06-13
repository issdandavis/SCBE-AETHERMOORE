"""Focused math-regression tests for the patent support packet."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.governance.runtime_gate import RuntimeGate  # noqa: E402


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
