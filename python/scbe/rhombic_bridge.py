"""
Rhombic Fusion Bridge (SCBE)
============================

Implements a rhombic/diamond "circuit" constraint functional intended to sit
laterally across sensory layers (audio/vision) and the governance state.

Core idea (minimal):
  - Use absolute/magnitude transforms ONLY in selected sensory branches.
  - Keep governance state signed/structured.
  - Produce a scalar R_diamond(x,k) that can be converted to a score
    S_diamond = exp(-R_diamond) and blended into downstream gating.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass(frozen=True, slots=True)
class RhombicParams:
    alpha: float = 1.0
    beta: float = 1.0
    gamma: float = 1.0
    eta: float = 0.5
    phi: float = 1.618033988749895  # golden ratio

    # Optional cap for stability (prevents huge magnitudes from dominating)
    clip_energy: Optional[float] = None


def rhombic_fusion(
    *,
    x: np.ndarray,
    audio: np.ndarray,
    vision: np.ndarray,
    governance: np.ndarray,
    k: int = 0,
    params: Optional[RhombicParams] = None,
) -> float:
    """
    Compute rhombic scalar R_diamond(x,k).

    x: shared input-state vector (any dimension)
    audio: audio-derived feature vector (same dim as x OR broadcastable)
    vision: vision-derived feature vector (same dim as x OR broadcastable)
    governance: governance state vector (same dim as x OR broadcastable)
    k: phase index; we apply mod-3 phase cycling with (-phi^-1)^(k mod 3)
    """
    params = params or RhombicParams()

    x = np.asarray(x, dtype=float).reshape(-1)
    a = np.asarray(audio, dtype=float).reshape(-1)
    v = np.asarray(vision, dtype=float).reshape(-1)
    g = np.asarray(governance, dtype=float).reshape(-1)

    # Sensory lateral transforms: magnitude only (preserve stability)
    uA = np.abs(a)
    uV = np.abs(v)

    # Energy terms for rhombus edges/diagonals
    e01 = float(np.linalg.norm(x - uA) ** 2)
    e02 = float(np.linalg.norm(x - uV) ** 2)
    e13 = float(np.linalg.norm(uA - g) ** 2)
    e23 = float(np.linalg.norm(uV - g) ** 2)
    e12 = float(np.linalg.norm(uA - uV) ** 2)

    phase = float((-1.0 / params.phi) ** (k % 3))
    R = (
        params.alpha * (e01 + e02)
        + params.beta * (e13 + e23)
        + params.gamma * e12
        + params.eta * phase * e12
    )

    if params.clip_energy is not None:
        R = float(min(R, params.clip_energy))

    return float(R)


def rhombic_score(R: float) -> float:
    """Convert scalar energy to [0,1]-like score."""
    return float(np.exp(-float(R)))

