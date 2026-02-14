"""
SCBE Math Reference — Python canonical implementation of the formula chain.

Matches the TypeScript kernel at packages/kernel/src/:
  - hyperbolic.ts         → hyperbolic_distance_poincare
  - temporalIntent.ts     → compute_x_factor, harmonic_wall_eff, harm_score, omega_gate
  - temporalPhase.ts      → triadic_risk

This file is the single source of truth for the Python side.
The TypeScript kernel is the single source of truth overall.

@version 3.2.5
"""

import math
from dataclasses import dataclass
from typing import Iterable

PHI = 1.618033988749895


# ═══════════════════════════════════════════════════════════════
# Formula 1: Hyperbolic distance in the Poincaré ball
# ═══════════════════════════════════════════════════════════════


def l2_norm_sq(u: Iterable[float]) -> float:
    return sum(float(x) * float(x) for x in u)


def l2_dist_sq(u: Iterable[float], v: Iterable[float]) -> float:
    return sum((float(a) - float(b)) ** 2 for a, b in zip(u, v))


def hyperbolic_distance_poincare(u, v, eps: float = 1e-12) -> float:
    """
    d = acosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))
    Domain: ||u|| < 1 and ||v|| < 1
    """
    uu = l2_norm_sq(u)
    vv = l2_norm_sq(v)
    if uu >= 1.0 or vv >= 1.0:
        raise ValueError("Points must lie inside the Poincaré ball (norm < 1).")

    denom = (1.0 - uu) * (1.0 - vv)
    denom = max(denom, eps)
    arg = 1.0 + (2.0 * l2_dist_sq(u, v)) / denom
    arg = max(arg, 1.0 + eps)  # acosh domain
    return math.acosh(arg)


# ═══════════════════════════════════════════════════════════════
# Formula 2: Intent persistence (x-factor)
# ═══════════════════════════════════════════════════════════════


def compute_x_factor(accumulated_intent: float, trust: float) -> float:
    """
    x = min(3.0, (0.5 + accumulated_intent*0.25) * (1 + (1 - trust)))
    """
    trust = max(0.0, min(1.0, float(trust)))
    base = 0.5 + float(accumulated_intent) * 0.25
    x = base * (1.0 + (1.0 - trust))
    return min(3.0, x)


# ═══════════════════════════════════════════════════════════════
# Formula 3: Harmonic Wall — H_eff(d, R, x) = R^(d² · x)
# ═══════════════════════════════════════════════════════════════


def harmonic_wall_eff(d: float, x: float, R: float = 1.5) -> float:
    """
    H_eff(d, R, x) = R^(d^2 * x)

    Uses exp/log form for numerical stability with large exponents.
    R = 1.5 is the musical perfect fifth (3/2), not the golden ratio.
    """
    if R <= 1.0:
        raise ValueError("R must be > 1 for an exponential wall.")
    d = max(0.0, float(d))
    x = max(0.0, float(x))
    return math.exp((d * d * x) * math.log(R))


def harm_score_from_wall(H_eff: float) -> float:
    """
    Matches kernel (temporalIntent.ts line 402):
      harmScore = 1 / (1 + log(max(1, H_eff)))

    Properties:
      - harm_score(1) = 1  (safe center)
      - monotone decreasing for H_eff >= 1
      - never reaches 0 (always positive)
      - smooth at H_eff = 1
    """
    H_eff = max(1.0, float(H_eff))
    return 1.0 / (1.0 + math.log(H_eff))


def harm_score_from_log(logH: float) -> float:
    """
    Log-space alternative (avoids overflow for extreme d):
      logH = d² · x · log(R)
      harm_score = 1 / (1 + max(0, logH))

    Numerically identical to harm_score_from_wall(exp(logH)).
    """
    logH = max(0.0, float(logH))
    return 1.0 / (1.0 + logH)


# ═══════════════════════════════════════════════════════════════
# Formula 4: Triadic risk — multi-clock aggregation
# ═══════════════════════════════════════════════════════════════


def triadic_risk(
    I_fast: float,
    I_memory: float,
    I_governance: float,
    phi: float = PHI,
) -> float:
    """
    d_tri = (0.3·I_fast^φ + 0.5·I_memory^φ + 0.2·I_governance^φ)^(1/φ)

    Golden-ratio exponents prevent any single timescale from being zeroed out.
    Memory weight (0.5) dominates — session drift matters most.
    """
    for val in (I_fast, I_memory, I_governance):
        if val < 0:
            raise ValueError("Triadic inputs must be nonnegative.")

    s = (
        0.3 * (I_fast**phi)
        + 0.5 * (I_memory**phi)
        + 0.2 * (I_governance**phi)
    )
    return s ** (1.0 / phi)


# ═══════════════════════════════════════════════════════════════
# Formula 5: Omega gate — final go/no-go
# ═══════════════════════════════════════════════════════════════

# Decision thresholds (from temporalIntent.ts)
ALLOW_THRESHOLD = 0.85
QUARANTINE_THRESHOLD = 0.40


def omega_gate(
    pqc_valid: float,
    harm_score: float,
    drift_factor: float,
    triadic_stable: float,
    spectral_score: float,
) -> float:
    """
    Ω = pqc × harm × drift × triadic × spectral

    Five locks, one door. If any factor is 0, Ω = 0 (blocked).
    Higher Ω = safer (harm_score is already inverted from H_eff).
    """

    def c01(x: float) -> float:
        return max(0.0, min(1.0, float(x)))

    return (
        c01(pqc_valid)
        * c01(harm_score)
        * c01(drift_factor)
        * c01(triadic_stable)
        * c01(spectral_score)
    )


def omega_decision(omega: float) -> str:
    """Map Ω to a decision string."""
    if omega > ALLOW_THRESHOLD:
        return "ALLOW"
    elif omega > QUARANTINE_THRESHOLD:
        return "QUARANTINE"
    else:
        return "DENY"


# ═══════════════════════════════════════════════════════════════
# Full chain: text position → distance → intent → wall → gate
# ═══════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ChainOutputs:
    d: float
    x: float
    H_eff: float
    harm: float
    d_tri: float
    omega: float
    decision: str


def full_chain(
    u,
    v,
    *,
    accumulated_intent: float,
    trust: float,
    R: float = 1.5,
    I_fast: float,
    I_memory: float,
    I_governance: float,
    pqc_valid: float = 1.0,
    drift_factor: float = 1.0,
    triadic_stable: float = 1.0,
    spectral_score: float = 1.0,
) -> ChainOutputs:
    """Run the complete formula chain: d → x → H → harm → Ω → decision."""
    d = hyperbolic_distance_poincare(u, v)
    x = compute_x_factor(accumulated_intent, trust)
    H = harmonic_wall_eff(d, x, R=R)
    harm = harm_score_from_wall(H)
    dtri = triadic_risk(I_fast, I_memory, I_governance)
    omega = omega_gate(pqc_valid, harm, drift_factor, triadic_stable, spectral_score)
    decision = omega_decision(omega)
    return ChainOutputs(
        d=d, x=x, H_eff=H, harm=harm, d_tri=dtri, omega=omega, decision=decision
    )
