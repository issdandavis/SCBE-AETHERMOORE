"""
Concept Blocks — SENSE
======================

Kalman-filter state estimation.  Maps to SCBE Layer 9 (spectral analysis).

Two filter classes:
- **SimpleKalmanFilter** — single-dimension (scalar) tracking
- **MultiDimKalmanFilter** — N-dimensional with full covariance

SenseBlock
----------
ConceptBlock wrapper — feed a measurement into ``tick()`` and get the
filtered estimate + uncertainty back.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from .base import BlockResult, BlockStatus, ConceptBlock


# -- scalar Kalman filter ----------------------------------------------------

class SimpleKalmanFilter:
    """1D Kalman filter for scalar signals."""

    def __init__(
        self,
        process_variance: float = 1e-4,
        measurement_variance: float = 0.1,
        initial_estimate: float = 0.0,
        initial_error: float = 1.0,
    ) -> None:
        self.q = process_variance
        self.r = measurement_variance
        self.x = initial_estimate
        self.p = initial_error

    def update(self, measurement: float) -> float:
        # Predict
        self.p += self.q
        # Update
        k = self.p / (self.p + self.r)
        self.x += k * (measurement - self.x)
        self.p *= (1.0 - k)
        return self.x

    @property
    def gain(self) -> float:
        return self.p / (self.p + self.r)

    def reset(self, estimate: float = 0.0, error: float = 1.0) -> None:
        self.x = estimate
        self.p = error


# -- multi-dim Kalman filter (pure Python, no numpy) -------------------------

def _mat_zeros(rows: int, cols: int) -> List[List[float]]:
    return [[0.0] * cols for _ in range(rows)]


def _mat_identity(n: int) -> List[List[float]]:
    m = _mat_zeros(n, n)
    for i in range(n):
        m[i][i] = 1.0
    return m


def _mat_add(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
    return [[a[i][j] + b[i][j] for j in range(len(a[0]))] for i in range(len(a))]


def _mat_sub(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
    return [[a[i][j] - b[i][j] for j in range(len(a[0]))] for i in range(len(a))]


def _mat_mul(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
    ra, ca = len(a), len(a[0])
    cb = len(b[0])
    out = _mat_zeros(ra, cb)
    for i in range(ra):
        for j in range(cb):
            s = 0.0
            for k in range(ca):
                s += a[i][k] * b[k][j]
            out[i][j] = s
    return out


def _mat_transpose(m: List[List[float]]) -> List[List[float]]:
    rows, cols = len(m), len(m[0])
    return [[m[j][i] for j in range(rows)] for i in range(cols)]


def _mat_inv_2x2(m: List[List[float]]) -> List[List[float]]:
    """Invert a 2x2 matrix. Raises if singular."""
    a, b = m[0][0], m[0][1]
    c, d = m[1][0], m[1][1]
    det = a * d - b * c
    if abs(det) < 1e-15:
        raise ValueError("Singular matrix")
    inv_det = 1.0 / det
    return [[d * inv_det, -b * inv_det], [-c * inv_det, a * inv_det]]


def _mat_inv_1x1(m: List[List[float]]) -> List[List[float]]:
    if abs(m[0][0]) < 1e-15:
        raise ValueError("Singular matrix")
    return [[1.0 / m[0][0]]]


def _mat_inv(m: List[List[float]]) -> List[List[float]]:
    """Invert a small matrix (1x1 or 2x2 fast path, else Gauss-Jordan)."""
    n = len(m)
    if n == 1:
        return _mat_inv_1x1(m)
    if n == 2:
        return _mat_inv_2x2(m)
    # Gauss-Jordan for larger matrices
    aug = [row[:] + [1.0 if j == i else 0.0 for j in range(n)] for i, row in enumerate(m)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        aug[col], aug[pivot] = aug[pivot], aug[col]
        if abs(aug[col][col]) < 1e-15:
            raise ValueError("Singular matrix")
        scale = aug[col][col]
        aug[col] = [x / scale for x in aug[col]]
        for row in range(n):
            if row != col:
                factor = aug[row][col]
                aug[row] = [aug[row][j] - factor * aug[col][j] for j in range(2 * n)]
    return [row[n:] for row in aug]


class MultiDimKalmanFilter:
    """N-dimensional Kalman filter (pure Python matrices)."""

    def __init__(
        self,
        dim: int,
        process_noise: float = 1e-4,
        measurement_noise: float = 0.1,
    ) -> None:
        self.dim = dim
        self.x = [[0.0] for _ in range(dim)]  # state column vector
        self.P = _mat_identity(dim)            # error covariance
        self.Q = [[process_noise if i == j else 0.0 for j in range(dim)] for i in range(dim)]
        self.R = [[measurement_noise if i == j else 0.0 for j in range(dim)] for i in range(dim)]
        self.F = _mat_identity(dim)            # state transition (identity default)
        self.H = _mat_identity(dim)            # observation (identity default)

    def predict(self) -> List[float]:
        self.x = _mat_mul(self.F, self.x)
        Ft = _mat_transpose(self.F)
        self.P = _mat_add(_mat_mul(_mat_mul(self.F, self.P), Ft), self.Q)
        return [row[0] for row in self.x]

    def update(self, measurement: List[float]) -> List[float]:
        z = [[m] for m in measurement]
        Ht = _mat_transpose(self.H)
        S = _mat_add(_mat_mul(_mat_mul(self.H, self.P), Ht), self.R)
        S_inv = _mat_inv(S)
        K = _mat_mul(_mat_mul(self.P, Ht), S_inv)
        y = _mat_sub(z, _mat_mul(self.H, self.x))
        self.x = _mat_add(self.x, _mat_mul(K, y))
        I = _mat_identity(self.dim)
        KH = _mat_mul(K, self.H)
        self.P = _mat_mul(_mat_sub(I, KH), self.P)
        return [row[0] for row in self.x]

    def step(self, measurement: List[float]) -> List[float]:
        self.predict()
        return self.update(measurement)

    def reset(self) -> None:
        self.x = [[0.0] for _ in range(self.dim)]
        self.P = _mat_identity(self.dim)


# -- concept block wrapper ---------------------------------------------------

class SenseBlock(ConceptBlock):
    """Concept block wrapping Kalman-filter state estimation.

    tick(inputs):
        inputs["measurement"]  — float (scalar) or List[float] (multi-dim)
    returns:
        BlockResult with output={"estimate": ..., "uncertainty": ..., "gain": ...}
    """

    def __init__(
        self,
        dim: int = 1,
        process_noise: float = 1e-4,
        measurement_noise: float = 0.1,
        name: str = "SENSE",
    ) -> None:
        super().__init__(name)
        self._dim = dim
        if dim == 1:
            self._filter = SimpleKalmanFilter(
                process_variance=process_noise,
                measurement_variance=measurement_noise,
            )
        else:
            self._filter = MultiDimKalmanFilter(
                dim=dim,
                process_noise=process_noise,
                measurement_noise=measurement_noise,
            )

    def _do_tick(self, inputs: Dict[str, Any]) -> BlockResult:
        meas = inputs.get("measurement")
        if meas is None:
            return BlockResult(status=BlockStatus.FAILURE, message="No measurement provided")

        if self._dim == 1:
            est = self._filter.update(float(meas))
            return BlockResult(
                status=BlockStatus.SUCCESS,
                output={
                    "estimate": est,
                    "uncertainty": self._filter.p,
                    "gain": self._filter.gain,
                },
            )
        else:
            est = self._filter.step(list(meas))
            trace = sum(self._filter.P[i][i] for i in range(self._dim))
            return BlockResult(
                status=BlockStatus.SUCCESS,
                output={
                    "estimate": est,
                    "uncertainty_trace": trace,
                },
            )

    def _do_configure(self, params: Dict[str, Any]) -> None:
        if "process_noise" in params and self._dim == 1:
            self._filter.q = params["process_noise"]
        if "measurement_noise" in params and self._dim == 1:
            self._filter.r = params["measurement_noise"]

    def _do_reset(self) -> None:
        self._filter.reset()
