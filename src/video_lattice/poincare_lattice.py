"""
Poincaré ball — single lattice unit.

Geometry:
  Open unit ball  B^n = { x ∈ R^n : ||x|| < 1 }
  Hyperbolic distance:
    d_H(u, v) = arccosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))

  Exponential map (Euclidean → Poincaré):
    exp_0(v) = tanh(||v|| / 2) * (v / ||v||)   for v ≠ 0

  Centroid update (running mean approximation in hyperbolic space):
    c_{n+1} = (n * c_n + p) / (n + 1)   then project back into B^n

Properties:
  - Distances near the boundary → ∞ (exponential cost scaling)
  - Objects near origin ≈ close / baseline-aligned
  - Drift toward boundary = exponentially more distant semantically
  - Session centroid tracks "where we've been" in semantic space
"""

from __future__ import annotations

import math
from typing import List, Optional

import numpy as np

_EPS = 1e-6  # boundary guard — keep ||x|| < 1 strictly
_MAX_NORM = 1.0 - _EPS


class PoincareLattice:
    """Single n-dimensional Poincaré ball.

    Args:
        dim: embedding dimension
        name: label for this lattice (used in diagnostics)
    """

    def __init__(self, dim: int, name: str = "lattice") -> None:
        self.dim = dim
        self.name = name
        self._centroid: Optional[np.ndarray] = None
        self._centroid_count: int = 0
        self._drift_history: List[float] = []

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    def embed(self, v: np.ndarray) -> np.ndarray:
        """Map a Euclidean vector into the open unit ball via exponential map.

        Uses tanh-normalized projection so the output is strictly inside B^n.
        Epsilon clamping prevents boundary saturation.
        """
        v = np.asarray(v, dtype=np.float64)
        norm = float(np.linalg.norm(v))
        if norm < _EPS:
            return np.zeros(self.dim, dtype=np.float64)
        # exp_0(v) = tanh(||v||/2) * v/||v||
        r = math.tanh(norm / 2.0)
        r = min(r, _MAX_NORM)  # epsilon clamp
        return (r / norm) * v

    def project(self, p: np.ndarray) -> np.ndarray:
        """Project an arbitrary point back into B^n (clamp if outside)."""
        p = np.asarray(p, dtype=np.float64)
        norm = float(np.linalg.norm(p))
        if norm >= 1.0:
            p = p * (_MAX_NORM / norm)
        return p

    # ------------------------------------------------------------------
    # Distance
    # ------------------------------------------------------------------

    def distance(self, u: np.ndarray, v: np.ndarray) -> float:
        """Hyperbolic distance d_H(u, v) in B^n.

        d_H = arccosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))
        """
        u = np.asarray(u, dtype=np.float64)
        v = np.asarray(v, dtype=np.float64)
        diff_sq = float(np.dot(u - v, u - v))
        denom = (1.0 - float(np.dot(u, u))) * (1.0 - float(np.dot(v, v)))
        denom = max(denom, _EPS)
        arg = 1.0 + 2.0 * diff_sq / denom
        arg = max(arg, 1.0)  # arccosh domain guard
        return math.acosh(arg)

    # ------------------------------------------------------------------
    # Session centroid
    # ------------------------------------------------------------------

    def update_centroid(self, p: np.ndarray) -> np.ndarray:
        """Incremental centroid update in ambient Euclidean coordinates.

        Approximation: running mean in R^n projected back into B^n.
        Exact Fréchet mean is expensive; this approximation is sufficient
        for drift tracking at video frame rate.

        Returns the updated centroid.
        """
        p = self.project(np.asarray(p, dtype=np.float64))
        n = self._centroid_count
        if self._centroid is None or n == 0:
            self._centroid = p.copy()
            self._centroid_count = 1
        else:
            # centroid_{n+1} = (n * c_n + p) / (n + 1)
            new_c = (n * self._centroid + p) / (n + 1)
            self._centroid = self.project(new_c)
            self._centroid_count += 1
        return self._centroid.copy()

    @property
    def centroid(self) -> Optional[np.ndarray]:
        return self._centroid.copy() if self._centroid is not None else None

    @property
    def centroid_count(self) -> int:
        return self._centroid_count

    # ------------------------------------------------------------------
    # Drift tracking
    # ------------------------------------------------------------------

    def drift(self, p: np.ndarray) -> float:
        """Hyperbolic distance from p to the current centroid.

        Returns 0.0 if no centroid established yet.
        """
        if self._centroid is None:
            return 0.0
        return self.distance(np.asarray(p, dtype=np.float64), self._centroid)

    def observe(self, v: np.ndarray) -> tuple[np.ndarray, float]:
        """Embed v, compute drift, update centroid.

        Returns (embedded_point, drift_from_centroid).
        The drift is computed BEFORE updating the centroid so it reflects
        how far this observation is from the prior trajectory.
        """
        p = self.embed(v)
        d = self.drift(p)
        self._drift_history.append(d)
        self.update_centroid(p)
        return p, d

    # ------------------------------------------------------------------
    # Trajectory statistics
    # ------------------------------------------------------------------

    def trajectory_variance(self) -> float:
        """Variance of drift values over observed frames.

        High variance = unstable trajectory (temporal incoherence).
        Low variance  = stable trajectory (locked-in coherence or drift plateau).
        """
        if len(self._drift_history) < 2:
            return 0.0
        arr = np.array(self._drift_history)
        return float(np.var(arr))

    def mean_drift(self) -> float:
        if not self._drift_history:
            return 0.0
        return float(np.mean(self._drift_history))

    def reset(self) -> None:
        self._centroid = None
        self._centroid_count = 0
        self._drift_history = []
