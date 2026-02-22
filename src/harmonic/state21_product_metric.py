"""SCBE 21D canonical state v1: product-metric reference implementation.

Schema version: state21_v1
Layout:
- 0:6   u (tongue position in Poincare ball B^6)
- 6:12  theta (tongue phase angles on T^6)
- 12    flux_participation
- 13    coherence_spectral
- 14    coherence_spin
- 15    coherence_triadic
- 16    risk_aggregate
- 17    entropy_density
- 18    stabilization
- 19    radial_norm (derived cache from u)
- 20    energy_harmonic (derived cache from u)
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, Iterable, Optional, Sequence, Tuple

import numpy as np

STATE21_DIM = 21
SCHEMA_VERSION = "state21_v1"

# Telemetry block is slots [12:21]
TELEMETRY_DIM = 9

# Default weighting and scaling for telemetry block.
# Last two (radial_norm, energy_harmonic) are derived cache slots and default to zero weight
# to avoid double-counting geometry.
DEFAULT_TELEMETRY_WEIGHTS = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 0.5, 0.5, 0.0, 0.0], dtype=float)
DEFAULT_TELEMETRY_SCALES = np.ones(TELEMETRY_DIM, dtype=float)


@dataclass(frozen=True)
class State21V1:
    raw: np.ndarray
    u: np.ndarray
    theta: np.ndarray
    telemetry: np.ndarray

    @property
    def flux_participation(self) -> float:
        return float(self.raw[12])

    @property
    def coherence_spectral(self) -> float:
        return float(self.raw[13])

    @property
    def coherence_spin(self) -> float:
        return float(self.raw[14])

    @property
    def coherence_triadic(self) -> float:
        return float(self.raw[15])

    @property
    def risk_aggregate(self) -> float:
        return float(self.raw[16])

    @property
    def entropy_density(self) -> float:
        return float(self.raw[17])

    @property
    def stabilization(self) -> float:
        return float(self.raw[18])

    @property
    def radial_norm_cached(self) -> float:
        return float(self.raw[19])

    @property
    def energy_harmonic_cached(self) -> float:
        return float(self.raw[20])


class State21Error(ValueError):
    pass


def parse_state21_v1(x: Iterable[float]) -> State21V1:
    s = np.asarray(list(x), dtype=float)
    if s.shape != (STATE21_DIM,):
        raise State21Error(f"Expected {STATE21_DIM} values, got shape {s.shape}")
    return State21V1(raw=s, u=s[0:6], theta=s[6:12], telemetry=s[12:21])


def _wrap_angle_delta(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.arctan2(np.sin(a - b), np.cos(a - b))


def hyperbolic_distance_poincare(u: np.ndarray, v: np.ndarray, eps: float = 1e-12) -> float:
    uu = float(np.dot(u, u))
    vv = float(np.dot(v, v))
    if uu >= 1.0 or vv >= 1.0:
        raise State21Error("Poincare points must satisfy ||u|| < 1")

    diff = u - v
    diff_sq = float(np.dot(diff, diff))
    denom = max(eps, (1.0 - uu) * (1.0 - vv))
    arg = 1.0 + 2.0 * diff_sq / denom
    return float(math.acosh(max(1.0, arg)))


def torus_distance(theta_a: np.ndarray, theta_b: np.ndarray) -> float:
    dtheta = _wrap_angle_delta(theta_a, theta_b)
    return float(np.linalg.norm(dtheta, ord=2))


def compute_radial_norm(u: np.ndarray) -> float:
    return float(np.linalg.norm(u, ord=2))


def compute_energy_harmonic(u: np.ndarray, d_hyp: int = 6, eps: float = 1e-12) -> float:
    """Harmonic wall cache from tongue block only.

    For u in B^6, r = ||u|| in (0,1), R_eff = 1/(1-r), H = R_eff^(d_hyp^2).
    """
    r = compute_radial_norm(u)
    if r >= 1.0:
        raise State21Error("Cannot compute harmonic energy for ||u|| >= 1")
    R_eff = 1.0 / max(eps, 1.0 - r)
    return float(R_eff ** (d_hyp * d_hyp))


def validate_state21_v1(state: State21V1, eps: float = 1e-6) -> Dict[str, float]:
    u_norm = compute_radial_norm(state.u)
    if u_norm >= 1.0:
        raise State21Error(f"Invalid tongue embedding norm: {u_norm:.8f} >= 1")

    # Coherence channels are independent measurements in [0,1]^3 (not simplex-constrained).
    coherences = np.array([state.coherence_spectral, state.coherence_spin, state.coherence_triadic], dtype=float)
    if np.any(coherences < -eps) or np.any(coherences > 1.0 + eps):
        raise State21Error("coherence_* channels must be in [0,1]")

    if state.risk_aggregate < -eps or state.risk_aggregate > 1.0 + eps:
        raise State21Error("risk_aggregate must be in [0,1]")

    if state.entropy_density < -eps:
        raise State21Error("entropy_density must be >= 0")

    if state.stabilization < -eps:
        raise State21Error("stabilization must be >= 0")

    if state.flux_participation < -eps:
        raise State21Error("flux_participation must be >= 0")

    radial = compute_radial_norm(state.u)
    harmonic = compute_energy_harmonic(state.u)

    return {
        "u_norm": u_norm,
        "radial_abs_err": abs(state.radial_norm_cached - radial),
        "harmonic_abs_err": abs(state.energy_harmonic_cached - harmonic),
    }


def product_metric_distance_v1(
    a: Iterable[float],
    b: Iterable[float],
    w_h: float = 1.0,
    w_theta: float = 0.5,
    telemetry_weights: Optional[Sequence[float]] = None,
    telemetry_scales: Optional[Sequence[float]] = None,
) -> float:
    """Distance on M = B^6 x T^6 x R^9.

    d^2 = w_h*d_hyp(u)^2 + w_theta*d_torus(theta)^2 + sum_i w_i * ((dz_i / s_i)^2)
    """
    sa = parse_state21_v1(a)
    sb = parse_state21_v1(b)

    w = np.asarray(telemetry_weights if telemetry_weights is not None else DEFAULT_TELEMETRY_WEIGHTS, dtype=float)
    s = np.asarray(telemetry_scales if telemetry_scales is not None else DEFAULT_TELEMETRY_SCALES, dtype=float)

    if w.shape != (TELEMETRY_DIM,):
        raise State21Error(f"telemetry_weights must have shape ({TELEMETRY_DIM},)")
    if s.shape != (TELEMETRY_DIM,):
        raise State21Error(f"telemetry_scales must have shape ({TELEMETRY_DIM},)")
    if np.any(s <= 0):
        raise State21Error("telemetry_scales must be strictly positive")

    d_h = hyperbolic_distance_poincare(sa.u, sb.u)
    d_theta = torus_distance(sa.theta, sb.theta)

    dz = (sa.telemetry - sb.telemetry) / s
    d_tel_sq = float(np.sum(w * dz * dz))

    total_sq = float(w_h * d_h * d_h + w_theta * d_theta * d_theta + d_tel_sq)
    return float(math.sqrt(max(0.0, total_sq)))
