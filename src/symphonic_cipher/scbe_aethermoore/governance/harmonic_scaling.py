"""
Canonical Harmonic Scaling — The Three H Formulas
==================================================

@file harmonic_scaling.py
@module governance/harmonic_scaling
@layer Layer 12, Layer 13
@component L12 Harmonic Scaling Canon

SINGLE SOURCE OF TRUTH for all three H formulas.
Canonical reference: docs/L12_HARMONIC_SCALING_CANON.md

1. H_score(d*, pd) = 1 / (1 + d* + 2*pd)       — bounded (0,1], pipeline L12
2. H_wall(d*, α, β)  = 1 + α·tanh(β·d*)         — bounded [1, 1+α], L13 risk
3. H_exp(d*, R)       = R^(d*²)                  — unbounded, patent/cost model

Integration with hamiltonian_braid.py:
  - harmonic_cost(d) in braid = H_exp(d, PHI) = PHI^(d²)
  - phase_deviation() in braid → Chebyshev/2 in {-1,0,+1}² → feeds pd in H_score
  - braid_distance(x, rail) → d_H + λ·phase_dev → feeds d* in all three formulas
"""

from __future__ import annotations

import math
from typing import NamedTuple

# Golden ratio — shared constant across SCBE
PHI: float = (1.0 + math.sqrt(5.0)) / 2.0

# Clamp exponent to prevent float overflow
_MAX_EXPONENT: float = 50.0


# ---------------------------------------------------------------------------
# 1. H_score — Bounded Safety Score (Pipeline L12 → L13)
# ---------------------------------------------------------------------------

def H_score(d_star: float, phase_deviation: float = 0.0) -> float:
    """Bounded safety score in (0, 1].

    H_score(d*, pd) = 1 / (1 + d* + 2 * pd)

    Properties:
        - Domain: d* >= 0, pd >= 0
        - Codomain: (0, 1]
        - H_score(0, 0) = 1.0 (maximally safe)
        - Strictly decreasing in d* and pd
        - Never zero, never negative

    L13 wiring: Risk' = Risk_base / H_score
      (lower H_score → higher amplified risk)

    Args:
        d_star: Realm distance from Layer 8 (hyperbolic radians). >= 0.
        phase_deviation: Phase deviation from Layer 10 spin coherence. [0, 1].

    Returns:
        Safety score in (0, 1].
    """
    return 1.0 / (1.0 + d_star + 2.0 * phase_deviation)


# ---------------------------------------------------------------------------
# 2. H_wall — Bounded Risk Multiplier (L13 Lemma 13.1)
# ---------------------------------------------------------------------------

def H_wall(d_star: float, alpha: float = 1.0, beta: float = 1.0) -> float:
    """Bounded risk multiplier in [1, 1+alpha].

    H_wall(d*, α, β) = 1 + α · tanh(β · d*)

    Properties:
        - Domain: d* >= 0, α > 0, β > 0
        - Codomain: [1, 1 + α]
        - H_wall(0) = 1.0 (no amplification)
        - Strictly increasing in d* (saturates at 1+α)
        - Derivative: α·β·sech²(β·d*) > 0

    L13 wiring: Risk' = Behavioral_Risk × H_wall × Time_Multi × Intent_Multi

    Args:
        d_star: Realm distance from Layer 8. >= 0.
        alpha: Maximum amplification above baseline. Default 1.0 → H in [1, 2].
        beta: Steepness of transition curve. Default 1.0.

    Returns:
        Risk multiplier in [1, 1+alpha].
    """
    return 1.0 + alpha * math.tanh(beta * d_star)


# ---------------------------------------------------------------------------
# 3. H_exp — Unbounded Exponential Wall (Patent / Cost Model)
# ---------------------------------------------------------------------------

def H_exp(d_star: float, R: float = PHI) -> float:
    """Unbounded exponential cost: R^(d*²).

    H_exp(d*, R) = R ^ (d*²)

    This is identical to harmonic_cost() in hamiltonian_braid.py when R=PHI.
    In production, exponent is clamped to 50.0 to prevent float overflow.

    Properties:
        - Domain: d* >= 0, R > 1
        - Codomain: [1, +inf)
        - H_exp(0) = 1.0
        - Super-exponential growth
        - Patent claim: "cost grows as R^(d²)"

    Args:
        d_star: Realm distance. >= 0.
        R: Harmonic base. Default PHI=1.618. Patent uses PHI, SaaS uses 1.5.

    Returns:
        Cost value >= 1.0, clamped at R^50.
    """
    exponent = min(d_star * d_star, _MAX_EXPONENT)
    return R ** exponent


# ---------------------------------------------------------------------------
# Aliases — bridge to hamiltonian_braid.py naming
# ---------------------------------------------------------------------------

def harmonic_cost(d: float) -> float:
    """PHI^(d²) — alias matching hamiltonian_braid.harmonic_cost().

    Identical semantics: distance from rail → exponential cost.
    """
    return H_exp(d, R=PHI)


# ---------------------------------------------------------------------------
# Derived utilities
# ---------------------------------------------------------------------------

class SecurityLevel(NamedTuple):
    bits: float
    label: str


def security_bits(d_star: float) -> SecurityLevel:
    """Equivalent security bits from harmonic distance.

    bits = d*² · log₂(PHI)

    Interpretation: an attacker at distance d* must perform
    ~2^bits operations to reach the safe rail.

    Args:
        d_star: Realm distance.

    Returns:
        SecurityLevel(bits, label) where label is one of:
        "trivial" (<40), "moderate" (40-80), "strong" (80-128),
        "military" (128-256), "quantum-safe" (>256).
    """
    bits = d_star * d_star * math.log2(PHI)

    if bits < 40:
        label = "trivial"
    elif bits < 80:
        label = "moderate"
    elif bits < 128:
        label = "strong"
    elif bits < 256:
        label = "military"
    else:
        label = "quantum-safe"

    return SecurityLevel(bits=bits, label=label)
