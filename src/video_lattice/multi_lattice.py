"""
Multi-lattice fleet — N independent Poincaré balls, one per semantic axis.

Each axis tracks a distinct aspect of a video frame (or rendered world state):
  identity   — subject/character consistency
  motion     — velocity field coherence
  scene      — background/environment stability
  color      — palette/lighting drift
  depth      — spatial depth map coherence
  structure  — edge/silhouette topology

Drift on any axis triggers a per-axis correction signal. Axes can be
weighted differently — high phi-weight axes dominate the aggregate error signal
(same weighting philosophy as the Sacred Tongues LWS).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import numpy as np

from .poincare_lattice import PoincareLattice

# Default phi-based axis weights (mirrors Langues Weighting System)
_PHI = (1 + math.sqrt(5)) / 2


class LatticeAxis(Enum):
    IDENTITY = "identity"
    MOTION = "motion"
    SCENE = "scene"
    COLOR = "color"
    DEPTH = "depth"
    STRUCTURE = "structure"


# Default weights in phi-scaled progression (low→high importance)
DEFAULT_WEIGHTS: Dict[LatticeAxis, float] = {
    LatticeAxis.IDENTITY: _PHI**0,  # 1.000
    LatticeAxis.MOTION: _PHI**1,  # 1.618
    LatticeAxis.SCENE: _PHI**2,  # 2.618
    LatticeAxis.COLOR: _PHI**3,  # 4.236
    LatticeAxis.DEPTH: _PHI**4,  # 6.854
    LatticeAxis.STRUCTURE: _PHI**5,  # 11.09
}


@dataclass
class AxisObservation:
    axis: LatticeAxis
    embedding: np.ndarray
    drift: float
    centroid: Optional[np.ndarray]


@dataclass
class MultiLatticeFrame:
    """Result of observing one frame across all axes."""

    frame_index: int
    observations: Dict[LatticeAxis, AxisObservation] = field(default_factory=dict)
    aggregate_drift: float = 0.0
    max_drift_axis: Optional[LatticeAxis] = None
    correction_triggered: bool = False

    def drift_vector(self) -> np.ndarray:
        axes = list(LatticeAxis)
        return np.array([self.observations.get(ax, AxisObservation(ax, np.zeros(1), 0.0, None)).drift for ax in axes])


class MultiLattice:
    """Fleet of Poincaré balls — one per semantic axis.

    Args:
        dim: embedding dimension per ball (same for all axes by default)
        weights: per-axis weight override (default: phi-scaled DEFAULT_WEIGHTS)
        correction_threshold: aggregate drift above this triggers correction
        axis_dims: optional per-axis dimension overrides
    """

    def __init__(
        self,
        dim: int = 64,
        weights: Optional[Dict[LatticeAxis, float]] = None,
        correction_threshold: float = 2.0,
        axis_dims: Optional[Dict[LatticeAxis, int]] = None,
    ) -> None:
        self.weights = weights or dict(DEFAULT_WEIGHTS)
        self.correction_threshold = correction_threshold
        self._frame_count = 0

        axis_dims = axis_dims or {}
        self._lattices: Dict[LatticeAxis, PoincareLattice] = {
            ax: PoincareLattice(dim=axis_dims.get(ax, dim), name=ax.value) for ax in LatticeAxis
        }

    # ------------------------------------------------------------------
    # Core observe API
    # ------------------------------------------------------------------

    def observe(
        self,
        axis_vectors: Dict[LatticeAxis, np.ndarray],
    ) -> MultiLatticeFrame:
        """Observe one frame across all provided axes.

        Args:
            axis_vectors: mapping from axis to raw feature vector for that axis.
                          Axes not present in the dict are skipped for this frame.

        Returns:
            MultiLatticeFrame with per-axis observations and aggregate drift.
        """
        result = MultiLatticeFrame(frame_index=self._frame_count)
        self._frame_count += 1

        total_weight = 0.0
        weighted_drift = 0.0
        max_drift = 0.0
        max_axis: Optional[LatticeAxis] = None

        for ax, vec in axis_vectors.items():
            lattice = self._lattices[ax]
            p, d = lattice.observe(vec)
            centroid = lattice.centroid
            obs = AxisObservation(axis=ax, embedding=p, drift=d, centroid=centroid)
            result.observations[ax] = obs

            w = self.weights.get(ax, 1.0)
            weighted_drift += w * d
            total_weight += w

            if d > max_drift:
                max_drift = d
                max_axis = ax

        if total_weight > 0:
            result.aggregate_drift = weighted_drift / total_weight
        result.max_drift_axis = max_axis
        result.correction_triggered = result.aggregate_drift > self.correction_threshold

        return result

    # ------------------------------------------------------------------
    # Single-axis helpers
    # ------------------------------------------------------------------

    def lattice(self, axis: LatticeAxis) -> PoincareLattice:
        return self._lattices[axis]

    def axis_drift(self, axis: LatticeAxis, vec: np.ndarray) -> float:
        """Compute drift on a single axis without updating centroids."""
        p = self._lattices[axis].embed(vec)
        return self._lattices[axis].drift(p)

    # ------------------------------------------------------------------
    # Fleet state
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, object]:
        return {
            "frame_count": self._frame_count,
            "axes": {
                ax.value: {
                    "mean_drift": self._lattices[ax].mean_drift(),
                    "trajectory_variance": self._lattices[ax].trajectory_variance(),
                    "centroid_count": self._lattices[ax].centroid_count,
                }
                for ax in LatticeAxis
            },
        }

    def reset(self, axes: Optional[List[LatticeAxis]] = None) -> None:
        for ax in axes or list(LatticeAxis):
            self._lattices[ax].reset()
        if axes is None:
            self._frame_count = 0
