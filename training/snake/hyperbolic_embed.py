"""Stage 4: Hyperbolic Embedding — Poincare ball projection.

Projects lattice coordinates into the Poincare ball model of hyperbolic space.
Center = safe/simple. Edge = adversarial/complex. The further from center,
the exponentially more costly to reach — this IS the harmonic wall.

Phase angles from the mirror refractor (Stage 3.5) feed into Mobius
rotation, giving each record a unique orientation in hyperbolic space.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .config import PHI, TONGUES, TONGUE_WEIGHTS


@dataclass
class HyperbolicPoint:
    """A point in the Poincare ball with full embedding metadata."""

    poincare_point: list[float]  # 6D point in the unit ball
    hyperbolic_distance: float    # Distance from origin (arcosh-based)
    breath_phase: float           # Temporal breathing transform [0, 2pi]
    safety_score: float           # 1/(1 + phi*d_H) — the harmonic wall
    mobius_orientation: list[float]  # 3 Mobius rotation angles
    ball_radius: float            # ||point|| — how close to the boundary

    def to_dict(self) -> dict[str, Any]:
        return {
            "poincare_point": self.poincare_point,
            "hyperbolic_distance": self.hyperbolic_distance,
            "breath_phase": self.breath_phase,
            "safety_score": self.safety_score,
            "mobius_orientation": self.mobius_orientation,
            "ball_radius": self.ball_radius,
        }


def _project_to_ball(coordinate: list[float], max_radius: float = 0.95) -> list[float]:
    """Project a lattice coordinate into the Poincare ball.

    Uses exponential map from origin: maps Euclidean coordinates to
    hyperbolic space, clamping to max_radius to avoid numerical instability
    at the boundary.
    """
    norm = math.sqrt(sum(x * x for x in coordinate))
    if norm < 1e-10:
        return [0.0] * len(coordinate)

    # Exponential map: tanh(||v||/2) * v/||v||
    # This naturally maps R^n → B^n (open unit ball)
    hyperbolic_norm = math.tanh(norm / 2)
    hyperbolic_norm = min(hyperbolic_norm, max_radius)

    scale = hyperbolic_norm / norm
    return [x * scale for x in coordinate]


def _hyperbolic_distance_from_origin(point: list[float]) -> float:
    """Compute hyperbolic distance from origin in Poincare ball.

    d_H = arcosh(1 + 2*||x||^2 / (1 - ||x||^2))

    This grows EXPONENTIALLY as the point approaches the boundary,
    which is exactly the harmonic wall behavior we want.
    """
    norm_sq = sum(x * x for x in point)
    if norm_sq >= 1.0:
        norm_sq = 0.9999  # Clamp to avoid division by zero

    argument = 1 + 2 * norm_sq / (1 - norm_sq)
    if argument < 1.0:
        return 0.0
    return math.acosh(argument)


def _breathing_transform(point: list[float], phase: float) -> list[float]:
    """Apply breathing transform — temporal dynamics via sinusoidal scaling.

    The Poincare ball "breathes" — points oscillate in and out with a
    phi-modulated frequency. This encodes temporal information into the
    spatial embedding.
    """
    # Breathing amplitude: phi-modulated
    amplitude = 0.1 * math.sin(phase * PHI)

    norm = math.sqrt(sum(x * x for x in point))
    if norm < 1e-10:
        return point

    # Scale the radius by (1 + amplitude), clamped to ball
    new_norm = min(norm * (1 + amplitude), 0.98)
    scale = new_norm / norm
    return [x * scale for x in point]


def _mobius_rotate(point: list[float], phase_angles: list[float]) -> list[float]:
    """Apply Mobius rotation using mirror refractor phase angles.

    Rotates the point in 3 planes defined by the tongue mirror pairs:
      plane 0: KO-DR (dims 0,5)
      plane 1: AV-CA (dims 1,3)
      plane 2: RU-UM (dims 2,4)
    """
    result = list(point)

    # Mirror pair dimension indices: KO=0, AV=1, RU=2, CA=3, UM=4, DR=5
    planes = [(0, 5), (1, 3), (2, 4)]

    for (i, j), angle in zip(planes, phase_angles):
        if i < len(result) and j < len(result):
            a, b = result[i], result[j]
            result[i] = a * math.cos(angle) - b * math.sin(angle)
            result[j] = a * math.sin(angle) + b * math.cos(angle)

    # Re-clamp to ball after rotation
    norm = math.sqrt(sum(x * x for x in result))
    if norm > 0.98:
        scale = 0.98 / norm
        result = [x * scale for x in result]

    return result


def embed(
    lattice_coordinate: list[float],
    phase_angles: list[float] | None = None,
    breath_time: float = 0.0,
) -> HyperbolicPoint:
    """Embed a lattice coordinate into the Poincare ball.

    Args:
        lattice_coordinate: 6D coordinate from lattice router
        phase_angles: 3 mirror refractor phase angles (for Mobius rotation)
        breath_time: Temporal parameter for breathing transform [0, 2pi]
    """
    if phase_angles is None:
        phase_angles = [0.0, 0.0, 0.0]

    # Project into Poincare ball
    ball_point = _project_to_ball(lattice_coordinate)

    # Apply Mobius rotation from mirror phase angles
    rotated = _mobius_rotate(ball_point, phase_angles)

    # Apply breathing transform
    breath_phase = breath_time % (2 * math.pi)
    breathing = _breathing_transform(rotated, breath_phase)

    # Compute hyperbolic distance from origin
    d_h = _hyperbolic_distance_from_origin(breathing)

    # Safety score: H(d) = 1/(1 + phi*d_H)
    # This is the harmonic wall — exponential cost for adversarial drift
    safety = 1.0 / (1.0 + PHI * d_h)

    # Ball radius (how close to boundary)
    radius = math.sqrt(sum(x * x for x in breathing))

    return HyperbolicPoint(
        poincare_point=[round(x, 8) for x in breathing],
        hyperbolic_distance=round(d_h, 6),
        breath_phase=round(breath_phase, 6),
        safety_score=round(safety, 6),
        mobius_orientation=[round(a, 6) for a in phase_angles],
        ball_radius=round(radius, 6),
    )


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from .lattice_router import route

    profiles = [
        ("Center (balanced)", {"KO": 0.17, "AV": 0.17, "RU": 0.17, "CA": 0.17, "UM": 0.16, "DR": 0.16}),
        ("Edge (UM dominant)", {"KO": 0.02, "AV": 0.02, "RU": 0.02, "CA": 0.02, "UM": 0.90, "DR": 0.02}),
    ]

    print("Hyperbolic Embedding (Poincare Ball)")
    for name, profile in profiles:
        lattice = route(profile)
        point = embed(lattice.coordinate, phase_angles=[0.1, -0.3, 0.5])
        print(f"\n  {name}:")
        print(f"    Ball radius:  {point.ball_radius}")
        print(f"    Hyp distance: {point.hyperbolic_distance}")
        print(f"    Safety score: {point.safety_score}")
        print(f"    Mobius orient: {point.mobius_orientation}")
