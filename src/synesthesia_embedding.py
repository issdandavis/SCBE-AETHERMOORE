"""
Synesthesia embedding utilities for flavor/scent context channels.
"""

from __future__ import annotations

from typing import Dict, Sequence

import numpy as np


PHI = (1.0 + np.sqrt(5.0)) / 2.0


def _as_vector(values: Sequence[float] | None) -> np.ndarray:
    if values is None:
        return np.zeros(0, dtype=np.float64)
    arr = np.asarray(list(values), dtype=np.float64).reshape(-1)
    if arr.size == 0:
        return np.zeros(0, dtype=np.float64)
    return arr


def langues_weights(dim: int) -> np.ndarray:
    if dim <= 0:
        return np.zeros(0, dtype=np.float64)
    base = np.array([PHI**k for k in range(6)], dtype=np.float64)
    if dim <= base.size:
        return base[:dim]
    reps = int(np.ceil(dim / base.size))
    return np.tile(base, reps)[:dim]


def _pad_to_same(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    dim = max(a.size, b.size, 1)
    aa = np.zeros(dim, dtype=np.float64)
    bb = np.zeros(dim, dtype=np.float64)
    aa[: a.size] = a
    bb[: b.size] = b
    return aa, bb


def flavor_scent_alignment(
    flavor_features: Sequence[float] | None,
    scent_features: Sequence[float] | None,
    eps: float = 1e-9,
) -> Dict[str, float]:
    """
    Compute synesthesia alignment using a Langues-weighted cosine.

    Returns:
      c_syn in [0,1] where 1 is highest alignment
      confidence in [0,1] from finite-overlap mask density
    """
    f_raw = _as_vector(flavor_features)
    s_raw = _as_vector(scent_features)
    f_vec, s_vec = _pad_to_same(f_raw, s_raw)

    finite_mask = np.isfinite(f_vec) & np.isfinite(s_vec)
    confidence = float(np.mean(finite_mask.astype(np.float64)))
    if not np.any(finite_mask):
        return {
            "c_syn": 0.5,
            "confidence": 0.0,
            "effective_dim": float(f_vec.size),
            "masked_dims": 0.0,
        }

    w = langues_weights(f_vec.size)
    f = np.where(finite_mask, f_vec, 0.0)
    s = np.where(finite_mask, s_vec * w, 0.0)

    denom = float(np.linalg.norm(f) * np.linalg.norm(s))
    if denom <= eps:
        c_syn = 0.5
    else:
        cos_val = float(np.dot(f, s) / denom)
        c_syn = float(np.clip((cos_val + 1.0) * 0.5, 0.0, 1.0))

    return {
        "c_syn": c_syn,
        "confidence": confidence,
        "effective_dim": float(f_vec.size),
        "masked_dims": float(np.sum(finite_mask)),
    }


def synesthesia_risk_factor(
    c_syn: float,
    confidence: float,
    beta: float = 0.2,
    confidence_floor: float = 0.25,
) -> float:
    c = float(np.clip(c_syn, 0.0, 1.0))
    conf = float(np.clip(confidence, 0.0, 1.0))
    if conf < confidence_floor:
        return float(1.0 + beta * 0.25)
    return float(1.0 + beta * (1.0 - c) * (0.5 + 0.5 * conf))
