"""Phi-Lifted Poincare Projection + Fibonacci Ternary Consensus.

From Gemini collaboration session (2026-03-26):
- Continuous side: phi-lift quantizes hyperbolic space into self-similar shells
- Discrete side: Fibonacci ladder routes ternary logic without floating-point

The phi-lift counterbalances exponential metric growth in hyperbolic space.
Fibonacci is the integer shadow of phi — consensus runs on integers only.
"""

from __future__ import annotations

import math
from typing import List

import numpy as np

PHI = (1 + math.sqrt(5)) / 2
FIB_LADDER = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]


def phi_lifted_poincare_projection(v_raw: np.ndarray, k_depths: np.ndarray) -> np.ndarray:
    """Project phi-lifted vectors into the Poincare ball as concentric shells.

    v_raw: Ternary vector [-1, 0, 1] per dimension
    k_depths: Integer array — phi exponent for each dimension

    Returns: Point inside the Poincare ball, shell-quantized by phi.
    """
    v_phi = v_raw * (PHI**k_depths)

    norm = np.linalg.norm(v_phi)
    if norm == 0:
        return v_phi

    # Project into ball: r = norm / (1 + norm) keeps r < 1
    r = norm / (1 + norm)

    # Center pull toward ternary equilibrium (r ~ 0.5 envelope)
    center_pull = 0.5 * (1 - r)
    return (v_phi / norm) * (r * (1 + center_pull))


def phi_shell_radius(k: int) -> float:
    """Radius of the k-th phi shell in the Poincare ball.

    Returns: r in (0, 1) where higher k = closer to boundary = more expensive.
    """
    phi_k = PHI**k
    return phi_k / (1 + phi_k)


def fibonacci_ternary_consensus(history_q: List[int]) -> int:
    """Discrete BFT consensus routing using Fibonacci integer ladders.

    history_q: List of past ternary states [-1, 0, 1] for a node/agent.
    Returns: Integer consensus weight from the Fibonacci ladder.

    Rules:
      +1 (activate): climb one Fibonacci step (increased trust)
      0 (neutral): hold position (perpetual evaluation)
      -1 (inhibit): drop one step (decay/quarantine)

    Trust cannot be gained linearly — must prove continuous congruence
    to climb 1,1,2,3,5,8,13. But a single -1 drops momentum immediately.
    """
    idx = 0
    for q in history_q:
        if q == 1:
            idx = min(idx + 1, len(FIB_LADDER) - 1)
        elif q == -1:
            idx = max(idx - 1, 0)
        # q == 0: hold (the perpetual neutral)
    return FIB_LADDER[idx]


def fibonacci_trust_level(history_q: List[int]) -> dict:
    """Full trust assessment from a ternary history.

    Returns dict with weight, index, and trust classification.
    """
    idx = 0
    for q in history_q:
        if q == 1:
            idx = min(idx + 1, len(FIB_LADDER) - 1)
        elif q == -1:
            idx = max(idx - 1, 0)

    weight = FIB_LADDER[idx]

    if idx <= 1:
        level = "UNTRUSTED"
    elif idx <= 3:
        level = "PROVISIONAL"
    elif idx <= 6:
        level = "TRUSTED"
    else:
        level = "CORE"

    return {
        "weight": weight,
        "index": idx,
        "level": level,
        "max_possible": FIB_LADDER[-1],
    }


def harmonic_cost_at_shell(k: int, R: float = 4.0) -> float:
    """Cost of operating at phi shell k via the harmonic wall.

    H(d, R) = R^(d^2) where d = shell radius in Poincare ball.
    Higher k = closer to boundary = exponentially more expensive.
    """
    r = phi_shell_radius(k)
    return R ** (r**2)
