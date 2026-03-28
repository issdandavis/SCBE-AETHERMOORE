"""Reference ds^2 computation with boundary and Fisher-Rao terms."""

from __future__ import annotations

from typing import Dict, Iterable, Optional

import numpy as np

from src.harmonic.state21_product_metric import (
    State21Error,
    hyperbolic_distance_poincare,
)


def fisher_rao_distance_squared(
    p: Iterable[float], q: Iterable[float], eps: float = 1e-12
) -> float:
    """Squared Fisher-Rao distance on probability simplex.

    d_FR(p, q) = 2 * arccos(sum_i sqrt(p_i q_i))
    """
    p_arr = np.asarray(list(p), dtype=float)
    q_arr = np.asarray(list(q), dtype=float)
    if p_arr.shape != q_arr.shape:
        raise ValueError(
            f"Fisher-Rao vectors must match shape, got {p_arr.shape} vs {q_arr.shape}"
        )
    if p_arr.ndim != 1 or p_arr.size == 0:
        raise ValueError("Fisher-Rao vectors must be non-empty 1D arrays")
    if np.any(p_arr < 0) or np.any(q_arr < 0):
        raise ValueError("Fisher-Rao vectors must be non-negative")

    p_sum = float(p_arr.sum())
    q_sum = float(q_arr.sum())
    if p_sum <= eps or q_sum <= eps:
        raise ValueError("Fisher-Rao vectors must have positive mass")

    p_norm = p_arr / p_sum
    q_norm = q_arr / q_sum
    inner = float(np.sum(np.sqrt(p_norm * q_norm)))
    inner = float(np.clip(inner, -1.0, 1.0))
    d_fr = 2.0 * np.arccos(inner)
    return float(d_fr * d_fr)


def boundary_amplification(radius: float, eps: float = 1e-12) -> float:
    """Amplification term that increases near Poincare boundary."""
    r = float(radius)
    if r < 0.0:
        raise ValueError(f"Radius must be >= 0, got {r}")
    if r >= 1.0:
        raise State21Error(f"Radius must be < 1 for Poincare geometry, got {r}")
    return float(1.0 / max(eps, 1.0 - r * r))


def computeDsSquared(
    u: Iterable[float],
    v: Iterable[float],
    *,
    fisher_p: Optional[Iterable[float]] = None,
    fisher_q: Optional[Iterable[float]] = None,
    fisher_weight: float = 1.0,
    eps: float = 1e-12,
) -> Dict[str, float]:
    """Compute ds^2 with corrected boundary and Fisher-Rao terms.

    Returns a decomposed dict so telemetry can record each term.
    """
    u_arr = np.asarray(list(u), dtype=float)
    v_arr = np.asarray(list(v), dtype=float)
    if u_arr.shape != v_arr.shape:
        raise ValueError(
            f"u and v must have identical shape, got {u_arr.shape} vs {v_arr.shape}"
        )
    if u_arr.ndim != 1:
        raise ValueError("u and v must be 1D vectors")

    d_h = float(hyperbolic_distance_poincare(u_arr, v_arr, eps=eps))
    d_h_sq = float(d_h * d_h)
    boundary_r = float(max(np.linalg.norm(u_arr), np.linalg.norm(v_arr)))
    amp = boundary_amplification(boundary_r, eps=eps)
    d_h_sq_scaled = float(amp * d_h_sq)

    d_fisher_sq = 0.0
    if fisher_p is not None or fisher_q is not None:
        if fisher_p is None or fisher_q is None:
            raise ValueError(
                "fisher_p and fisher_q must either both be set or both be omitted"
            )
        d_fisher_sq = fisher_rao_distance_squared(fisher_p, fisher_q, eps=eps)

    total = float(d_h_sq_scaled + float(fisher_weight) * d_fisher_sq)
    return {
        "ds_squared": total,
        "hyperbolic_distance": d_h,
        "hyperbolic_squared": d_h_sq,
        "boundary_radius": boundary_r,
        "boundary_amplification": amp,
        "hyperbolic_scaled_squared": d_h_sq_scaled,
        "fisher_rao_squared": d_fisher_sq,
        "fisher_weight": float(fisher_weight),
    }
