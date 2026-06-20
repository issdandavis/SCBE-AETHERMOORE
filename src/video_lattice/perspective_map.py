"""Perspective-to-Poincare mapping helpers for video coherence.

Depth is represented as radial position in the open unit ball: near/known
objects stay closer to the origin, while far or uncertain objects move toward
the boundary where hyperbolic distance grows quickly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

import numpy as np


@dataclass(frozen=True)
class PerspectivePoint:
    """One projected point with both source depth and Poincare coordinates."""

    depth: float
    angle: float
    point: np.ndarray
    radius: float


class PerspectiveMap:
    """Map depth and angle values into a 2D Poincare disk.

    Args:
        max_depth: depth value that maps near the outer radius.
        boundary_epsilon: keeps projected points strictly inside the unit disk.
    """

    def __init__(self, max_depth: float = 1.0, boundary_epsilon: float = 1e-6) -> None:
        if max_depth <= 0:
            raise ValueError("max_depth must be positive")
        if not (0.0 < boundary_epsilon < 1.0):
            raise ValueError("boundary_epsilon must be between 0 and 1")
        self.max_depth = float(max_depth)
        self.boundary_epsilon = float(boundary_epsilon)

    def radius_for_depth(self, depth: float) -> float:
        """Convert non-negative depth to a bounded radial coordinate."""

        normalized = max(0.0, float(depth)) / self.max_depth
        radius = math.tanh(normalized)
        return min(radius, 1.0 - self.boundary_epsilon)

    def project(self, depth: float, angle: float) -> PerspectivePoint:
        """Project polar depth/angle into the open unit disk."""

        radius = self.radius_for_depth(depth)
        point = np.array([radius * math.cos(angle), radius * math.sin(angle)], dtype=np.float64)
        return PerspectivePoint(depth=float(depth), angle=float(angle), point=point, radius=radius)

    def project_xy_depth(self, x: float, y: float, depth: float) -> PerspectivePoint:
        """Project a screen-space vector and depth into the disk.

        The angle comes from ``atan2(y, x)``; depth controls the radius.
        """

        return self.project(depth=depth, angle=math.atan2(float(y), float(x)))

    @staticmethod
    def polar(point: np.ndarray) -> Tuple[float, float]:
        """Return ``(radius, angle)`` for a projected disk point."""

        arr = np.asarray(point, dtype=np.float64)
        if arr.shape[0] != 2:
            raise ValueError("PerspectiveMap.polar expects a 2D point")
        radius = float(np.linalg.norm(arr))
        angle = math.atan2(float(arr[1]), float(arr[0]))
        return radius, angle
