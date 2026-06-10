from __future__ import annotations

import cmath
import math
import random

from scripts.research.hyperbolic_ruler import d_H, mobius_isometry


def _build_reference_measurements(seed: int = 0) -> tuple[list[float], list[float]]:
    rng = random.Random(seed)
    points = [0.0 + 0.0j]
    for _ in range(4):
        radius = rng.uniform(0.2, 0.85)
        theta = rng.uniform(0.0, 2.0 * math.pi)
        points.append(cmath.rect(radius, theta))

    pairs = [(i, j) for i in range(len(points)) for j in range(i + 1, len(points))]
    base_dh = [d_H(points[i], points[j]) for i, j in pairs]
    base_euclid = [abs(points[i] - points[j]) for i, j in pairs]

    d_h_drift = 0.0
    euclid_drift = 0.0

    for _ in range(6):
        offset = cmath.rect(rng.uniform(0.0, 0.7), rng.uniform(0.0, 2.0 * math.pi))
        frame = mobius_isometry(offset, rng.uniform(0.0, 2.0 * math.pi))
        transformed = [frame(point) for point in points]
        frame_dh = [d_H(transformed[i], transformed[j]) for i, j in pairs]
        frame_euclid = [abs(transformed[i] - transformed[j]) for i, j in pairs]

        for base, observed in zip(base_dh, frame_dh):
            d_h_drift = max(d_h_drift, abs(observed - base))
        for base, observed in zip(base_euclid, frame_euclid):
            euclid_drift = max(euclid_drift, abs(observed - base))

    return [d_h_drift, euclid_drift]


def test_mobius_reframes_preserve_true_hyperbolic_distance() -> None:
    d_h_drift, euclid_drift = _build_reference_measurements()

    assert d_h_drift < 1e-12
    assert euclid_drift > 0.05


def test_boundary_stretching_grows_without_coordinate_escape() -> None:
    near = d_H(complex(0.9, 0.0), 0.0 + 0.0j)
    closer = d_H(complex(0.99, 0.0), 0.0 + 0.0j)
    closest = d_H(complex(0.9999, 0.0), 0.0 + 0.0j)

    assert 2.9 < near < 3.1
    assert near < closer < closest
    assert closest > 9.8
