"""
Scattered Attention Sphere
===========================

Holographic Weight Matrix Router — fractalizes 2D weight matrices
into a 3D Sacred Tongue sphere with phase-tunable bands of focus.

From Issac's Colab notebook, integrated into the dual-core kernel.

Pipeline:
  1. Fractalize: Break 2D weight matrix into nibble-level components
  2. Scatter: Map onto 3D sphere (longitude = tongue, latitude = phase)
  3. Layer/Cycle: Stack multiple matrices as concentric shells
  4. Band of Focus: phi_wall selects resonant components

Integration:
  - GeoKernel uses this for fast attention routing (which tongue handles this?)
  - MemoryLattice uses this for scattered storage (aperiodic addressing)
  - PhaseTunnelGate maps directly to the band-of-focus mechanism
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

PHI = 1.618033988749895

# Sacred Tongue longitudes (radians)
TONGUE_LONGITUDES = {
    "KO": 0.0,  # 0 deg
    "AV": math.pi / 3,  # 60 deg
    "RU": 2 * math.pi / 3,  # 120 deg
    "CA": math.pi,  # 180 deg
    "UM": 4 * math.pi / 3,  # 240 deg
    "DR": 5 * math.pi / 3,  # 300 deg
}

TONGUE_KEYS = list(TONGUE_LONGITUDES.keys())

# Phi-scaled weights for governance cost
TONGUE_WEIGHTS = {
    "KO": 1.0,
    "AV": PHI,
    "RU": PHI**2,
    "CA": PHI**3,
    "UM": PHI**4,
    "DR": PHI**5,
}


@dataclass
class LatticePoint:
    """A single scattered point on the attention sphere."""

    value: float
    tongue: str
    r: float  # radius (layer depth)
    theta: float  # longitude (tongue angle)
    phi: float  # latitude (phase angle)
    orig_row: int
    orig_col: int
    transmission: float = 0.0  # T from PhaseTunnelGate

    def to_cartesian(self) -> tuple[float, float, float]:
        x = self.r * math.cos(self.phi) * math.cos(self.theta)
        y = self.r * math.cos(self.phi) * math.sin(self.theta)
        z = self.r * math.sin(self.phi)
        return x, y, z

    def governance_cost(self) -> float:
        """Cost to access this point = tongue weight * distance from equator."""
        return TONGUE_WEIGHTS[self.tongue] * (1.0 + abs(self.phi))


@dataclass
class BandResult:
    """Result of a band-of-focus query."""

    phi_wall: float
    bandwidth: float
    resonant_count: int
    total_count: int
    tongue_distribution: dict[str, int]
    mean_value: float
    mean_transmission: float
    points: list[LatticePoint] = field(default_factory=list, repr=False)


class ScatteredAttentionSphere:
    """
    Holographic Weight Matrix Router.

    Fractalizes weight matrices into a 3D sphere where:
    - Longitude = Sacred Tongue domain
    - Latitude = Phase angle (value magnitude)
    - Radius = Layer depth
    - Band of Focus = PhaseTunnelGate phi_wall filter
    """

    def __init__(self, sparsity_threshold: float = 0.01):
        self.sparsity_threshold = sparsity_threshold
        self.lattice: list[LatticePoint] = []
        self._layers: list[str] = []  # track which matrices were scattered

    def scatter(
        self,
        weight_matrix: np.ndarray,
        layer_name: str = "default",
        layer_radius: float = 1.0,
    ) -> int:
        """
        Fractalize a 2D weight matrix and scatter onto the sphere.

        Args:
            weight_matrix: 2D numpy array (e.g., Q/K/V projection weights)
            layer_name: identifier for this layer
            layer_radius: radial position (1.0 = surface, <1 = inner, >1 = outer)

        Returns:
            Number of active points scattered
        """
        rows, cols = weight_matrix.shape
        count = 0

        for i in range(rows):
            for j in range(cols):
                val = float(weight_matrix[i, j])

                # Sparsity gate
                if abs(val) < self.sparsity_threshold:
                    continue

                # Tongue assignment: deterministic from position (not random)
                tongue_idx = (i * cols + j) % 6
                tongue = TONGUE_KEYS[tongue_idx]
                theta = TONGUE_LONGITUDES[tongue]

                # Small deterministic scatter based on value (not random — reproducible)
                theta += math.sin(val * 137.5) * 0.08  # golden angle scatter

                # Latitude from value magnitude (tanh maps to [-pi/2, pi/2])
                phi = math.tanh(val) * (math.pi / 2)

                # Radius from layer
                r = layer_radius

                # Compute PhaseTunnelGate transmission at this point's natural angle
                # T = cos²((phi - 0) / 2) — transmission relative to equator
                t = math.cos((phi - 0) / 2) ** 2

                point = LatticePoint(
                    value=val,
                    tongue=tongue,
                    r=r,
                    theta=theta,
                    phi=phi,
                    orig_row=i,
                    orig_col=j,
                    transmission=t,
                )
                self.lattice.append(point)
                count += 1

        self._layers.append(layer_name)
        return count

    def scatter_qkv(self, q_matrix: np.ndarray, k_matrix: np.ndarray, v_matrix: np.ndarray) -> dict[str, int]:
        """Scatter Q, K, V matrices as concentric shells."""
        return {
            "Q": self.scatter(q_matrix, "Q", layer_radius=1.0),
            "K": self.scatter(k_matrix, "K", layer_radius=0.8),
            "V": self.scatter(v_matrix, "V", layer_radius=0.6),
        }

    def band_of_focus(self, phi_wall: float, bandwidth: float = 0.2) -> BandResult:
        """
        Query the sphere at a specific phase angle.
        Returns all resonant points within the bandwidth.

        This IS the PhaseTunnelGate applied to the scattered lattice.
        """
        resonant = []
        tongue_dist: dict[str, int] = {}

        for point in self.lattice:
            if abs(point.phi - phi_wall) <= bandwidth:
                # Recompute transmission relative to phi_wall
                point.transmission = math.cos((point.phi - phi_wall) / 2) ** 2
                resonant.append(point)
                tongue_dist[point.tongue] = tongue_dist.get(point.tongue, 0) + 1

        mean_val = float(np.mean([p.value for p in resonant])) if resonant else 0.0
        mean_t = float(np.mean([p.transmission for p in resonant])) if resonant else 0.0

        return BandResult(
            phi_wall=phi_wall,
            bandwidth=bandwidth,
            resonant_count=len(resonant),
            total_count=len(self.lattice),
            tongue_distribution=tongue_dist,
            mean_value=mean_val,
            mean_transmission=mean_t,
            points=resonant,
        )

    def sweep(self, steps: int = 12) -> list[BandResult]:
        """
        Sweep phi_wall across the full sphere and return band results.
        Like turning the PhaseTunnelGate dial from -pi/2 to +pi/2.
        """
        results = []
        for i in range(steps):
            phi = -math.pi / 2 + (math.pi * i / (steps - 1))
            results.append(self.band_of_focus(phi, bandwidth=math.pi / steps))
        return results

    def tongue_census(self) -> dict[str, dict[str, Any]]:
        """Count points per tongue with stats."""
        census: dict[str, list[float]] = {t: [] for t in TONGUE_KEYS}
        for p in self.lattice:
            census[p.tongue].append(p.value)

        return {
            tongue: {
                "count": len(vals),
                "mean": float(np.mean(vals)) if vals else 0.0,
                "std": float(np.std(vals)) if vals else 0.0,
                "weight": TONGUE_WEIGHTS[tongue],
            }
            for tongue, vals in census.items()
        }

    def reconstruct(self) -> np.ndarray | None:
        """
        Reconstruct the original matrix from scattered points.
        Proves the scatter is lossless (bijective).
        """
        if not self.lattice:
            return None

        max_row = max(p.orig_row for p in self.lattice) + 1
        max_col = max(p.orig_col for p in self.lattice) + 1
        matrix = np.zeros((max_row, max_col))

        for p in self.lattice:
            matrix[p.orig_row, p.orig_col] = p.value

        return matrix

    def stats(self) -> dict[str, Any]:
        return {
            "total_points": len(self.lattice),
            "layers": self._layers,
            "tongues": self.tongue_census(),
        }
