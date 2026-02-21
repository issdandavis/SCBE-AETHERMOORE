#!/usr/bin/env python3
"""
SCBE Governance Math — Backend parity module for Layer 12 + Voxel Addressing.

Mirrors the TypeScript governance helpers in the physics sim so that
backend (Redis/RocksDB/S3) and frontend share identical math.

Contains:
  - coherence_from_phases: NK-shell coherence from 6-tongue phase angles
  - drift_star: hyperbolic drift distance with weight-imbalance penalty
  - layer12_cost: super-exponential cost H(d*, C) = R · π^(φ·d*) · (1 + γ(1-C))
  - poincare_dist_3d: true Poincaré ball distance (3D projection)
  - inv_metric_factor: inverse conformal factor 1/λ² at a point
  - bft_consensus: 6-agent BFT gate (n=6, f=1, threshold=4)
  - quantize: uniform bin quantizer for voxel addressing
  - encode_voxel_key: deterministic base-36 voxel key

@module scbe_governance_math
@layer Layer 5, Layer 12, Layer 13
@version 3.2.4
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Literal

# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════

PHI = (1 + math.sqrt(5)) / 2  # 1.618033988749895
COST_R = 1.0  # base cost multiplier
GAMMA = 1.0  # coherence penalty factor
POINCARE_SCALE = 0.35  # maps ~[-3,3] world space into unit ball
EPS = 1e-9
DANGER_QUORUM = 4  # BFT threshold: >= 3f+1 for f=1 (with 6 agents)

Decision = Literal["ALLOW", "QUARANTINE", "DENY"]
Lang = Literal["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUES: tuple[Lang, ...] = ("KO", "AV", "RU", "CA", "UM", "DR")


# ═══════════════════════════════════════════════════════════════
# Data types
# ═══════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class Point3:
    """3D point in world space."""

    x: float
    y: float
    z: float


# ═══════════════════════════════════════════════════════════════
# Core math
# ═══════════════════════════════════════════════════════════════


def clamp(n: float, lo: float, hi: float) -> float:
    """Clamp n to [lo, hi]."""
    return max(lo, min(hi, n))


def wrap_pi(a: float) -> float:
    """Wrap angle to (-π, π]."""
    x = a
    while x <= -math.pi:
        x += 2 * math.pi
    while x > math.pi:
        x -= 2 * math.pi
    return x


def quantize(val: float, minv: float, maxv: float, bins: int) -> int:
    """Uniform bin quantizer. Returns bin index in [0, bins-1]."""
    v = clamp(val, minv, maxv)
    t = (v - minv) / (maxv - minv) if maxv > minv else 0.0
    q = round(t * (bins - 1))
    return int(clamp(q, 0, bins - 1))


def coherence_from_phases(phases: Dict[str, float]) -> float:
    """NK-shell coherence: mean pairwise cosine across 6 Sacred Tongues.

    C = (1/15) Σ_{i<j} cos(φ_i - φ_j)   ∈ [-1, 1]
    C = 1 when all phases aligned; C < 0 when highly misaligned.
    """
    total = 0.0
    count = 0
    for i in range(len(TONGUES)):
        for j in range(i + 1, len(TONGUES)):
            total += math.cos(phases[TONGUES[i]] - phases[TONGUES[j]])
            count += 1
    return total / count if count else 0.0


def drift_star(p: Point3, weights: Dict[str, float]) -> float:
    """Compute d* — hyperbolic drift distance with weight-imbalance penalty.

    d* = r · (1 + 1.5 · imbalance)
    where r = ‖p‖ and imbalance = max(w) / Σw.
    """
    r = math.sqrt(p.x * p.x + p.y * p.y + p.z * p.z)
    ws = list(weights.values())
    s = sum(ws) or 1.0
    maxw = max(ws) if ws else 1.0
    imbalance = maxw / s
    return r * (1.0 + 1.5 * imbalance)


def layer12_cost(d_star: float, coherence: float) -> float:
    """Layer 12 super-exponential cost.

    H(d*, C) = R · π^(φ · d*) · (1 + γ · (1 - C))

    Cost grows super-exponentially with d*, penalized further by low coherence.
    """
    base = COST_R * (math.pi ** (PHI * d_star))
    return base * (1.0 + GAMMA * (1.0 - coherence))


# ═══════════════════════════════════════════════════════════════
# Poincaré ball geometry (3D projection)
# ═══════════════════════════════════════════════════════════════


def _norm_sq(p: Point3) -> float:
    return p.x * p.x + p.y * p.y + p.z * p.z


def _to_ball(p: Point3) -> Point3:
    """Map world-space point to Poincaré ball via POINCARE_SCALE."""
    return Point3(p.x * POINCARE_SCALE, p.y * POINCARE_SCALE, p.z * POINCARE_SCALE)


def poincare_dist_3d(a: Point3, b: Point3) -> float:
    """Poincaré ball distance (3D). Requires ‖u‖,‖v‖ < 1 after scaling.

    d(u, v) = acosh(1 + 2|u-v|² / ((1-|u|²)(1-|v|²)))
    """
    u = _to_ball(a)
    v = _to_ball(b)
    u2 = _norm_sq(u)
    v2 = _norm_sq(v)
    dx, dy, dz = u.x - v.x, u.y - v.y, u.z - v.z
    du2 = dx * dx + dy * dy + dz * dz
    denom = max((1 - u2) * (1 - v2), EPS)
    arg = 1 + (2 * du2) / denom
    return math.acosh(max(arg, 1.0))


def inv_metric_factor(at: Point3) -> float:
    """Inverse conformal factor 1/λ² where λ = 2/(1-‖u‖²).

    Near origin: ~0.25 (small). Near boundary: → 0 (shrinks forces).
    """
    u = _to_ball(at)
    u2 = _norm_sq(u)
    lam = 2.0 / max(1.0 - u2, 1e-6)
    return 1.0 / (lam * lam)


# ═══════════════════════════════════════════════════════════════
# BFT consensus (6 agents, f=1, threshold=4)
# ═══════════════════════════════════════════════════════════════


def local_vote(
    lang: Lang,
    cost: float,
    coherence: float,
    phases: Dict[str, float],
    weights: Dict[str, float],
    deny_cost: float = 50.0,
    quarantine_cost: float = 12.0,
) -> Decision:
    """Single agent's local risk vote.

    risk = cost · (1 + 0.6·phase_delta) · (1 + 0.15·w) · (1 + 0.5·(1-C))
    """
    all_phases = list(phases.values())
    mean_phase = sum(all_phases) / len(all_phases) if all_phases else 0.0
    phase_delta = abs(wrap_pi(phases.get(lang, 0) - mean_phase)) / math.pi
    w = weights.get(lang, 0.5)

    risk = cost * (1 + 0.6 * phase_delta) * (1 + 0.15 * w) * (1 + 0.5 * (1 - coherence))
    if risk > deny_cost:
        return "DENY"
    if risk > quarantine_cost:
        return "QUARANTINE"
    return "ALLOW"


def bft_consensus(votes: Dict[str, Decision]) -> Decision:
    """BFT consensus gate (n=6, f=1, threshold≥4).

    Requires ≥4 votes for QUARANTINE or DENY; otherwise ALLOW.
    One faulty agent cannot lock the fleet.
    """
    deny = sum(1 for v in votes.values() if v == "DENY")
    quar = sum(1 for v in votes.values() if v == "QUARANTINE")

    if deny >= DANGER_QUORUM:
        return "DENY"
    if quar >= DANGER_QUORUM:
        return "QUARANTINE"
    return "ALLOW"


# ═══════════════════════════════════════════════════════════════
# Voxel key encoding
# ═══════════════════════════════════════════════════════════════


def _b36(n: int) -> str:
    """Base-36 encode with 2-char zero-padded output."""
    if n < 0:
        n = 0
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    if n == 0:
        return "00"
    result = ""
    val = n
    while val > 0:
        result = chars[val % 36] + result
        val //= 36
    return result.zfill(2)


def encode_voxel_key(
    base: Dict[str, int],
    decision: Decision,
) -> str:
    """Deterministic base-36 voxel key.

    Format: qr:{D}:{X}:{Y}:{Z}:{V}:{P}:{S}
    where {D} = first char of decision (A/Q/D).
    """
    return ":".join([
        "qr",
        decision[0],
        _b36(base.get("X", 0)),
        _b36(base.get("Y", 0)),
        _b36(base.get("Z", 0)),
        _b36(base.get("V", 0)),
        _b36(base.get("P", 0)),
        _b36(base.get("S", 0)),
    ])
