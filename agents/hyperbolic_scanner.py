"""Hyperbolic boundary scanner for state quarantine decisions."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Iterable, Dict, Any

import numpy as np

EPS = 1e-10


def _hyperbolic_distance_to_origin(u: np.ndarray) -> float:
    norm_sq = float(np.sum(u**2))
    norm_sq = min(max(norm_sq, 0.0), 1.0 - EPS)
    cosh_dist = 1.0 + (2.0 * norm_sq) / max(1.0 - norm_sq, EPS)
    cosh_dist = max(cosh_dist, 1.0)
    return float(np.arccosh(cosh_dist))


def scan_boundary_state(
    state: Iterable[float],
    *,
    boundary_threshold: float = 0.95,
    harmonic_base: float = 1.5,
) -> Dict[str, Any]:
    """Scan context state in Poincare-like space and return governance decision."""

    u = np.asarray(list(state), dtype=np.float64)
    norm = float(np.linalg.norm(u))
    if norm >= 1.0:
        u = u / max(norm, EPS) * (1.0 - 1e-6)
        norm = float(np.linalg.norm(u))

    d_h = _hyperbolic_distance_to_origin(u)
    harmonic_cost = float(harmonic_base ** (d_h**2))
    status = "QUARANTINE" if norm >= float(boundary_threshold) else "ALLOW"

    return {
        "status": status,
        "norm": round(norm, 6),
        "d_h_origin": round(d_h, 6),
        "boundary_threshold": float(boundary_threshold),
        "harmonic_cost": round(harmonic_cost, 6),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

