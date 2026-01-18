#!/usr/bin/env python3
"""
QASI Core (2026) — Quantized/Quasi-Adaptive Security Interface
==============================================================

This replaces the older "quantum/unitary" math core with the *actual* SCBE math:
- Complex → real isometry (realification)
- SPD weighting
- Poincaré ball embedding + clamping
- Hyperbolic distance (immutable metric law)
- Möbius addition + phase isometries
- Breathing diffeomorphism (severity modulation)
- Multi-well realms and 1-Lipschitz realm distance
- Spectral / spin / audio coherence features in [0,1]
- Triadic temporal distance (norm)
- Harmonic scaling H(d,R)=R^(d^2)
- Monotone Risk' aggregation + decision thresholds

Design goal:
- Everything is numerically stable with eps floors and ball clamping.
- Includes a self-test suite validating the axioms numerically.

Dependencies: numpy only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
import numpy as np


# ----------------------------
# Utilities / guardrails
# ----------------------------

def _norm(x: np.ndarray) -> float:
    return float(np.linalg.norm(x))


def clamp_ball(u: np.ndarray, eps_ball: float = 1e-3) -> np.ndarray:
    """Clamp a vector to the closed sub-ball ||u|| <= 1 - eps_ball."""
    r = _norm(u)
    r_max = 1.0 - float(eps_ball)
    if r <= r_max:
        return u
    if r == 0.0:
        return u
    return (r_max / r) * u


def safe_arcosh(x: np.ndarray | float) -> np.ndarray | float:
    """arcosh is only defined for x>=1. Clamp for numerical noise."""
    if isinstance(x, float):
        return float(np.arccosh(max(1.0, x)))
    return np.arccosh(np.maximum(1.0, x))


# ----------------------------
# Layer group 1–3: Complex → Real → SPD weight
# ----------------------------

def realify(c: np.ndarray) -> np.ndarray:
    """
    Realification isometry Φ: C^D → R^(2D):
      Φ(z1..zD) = (Re z1..Re zD, Im z1..Im zD)
    """
    c = np.asarray(c, dtype=np.complex128)
    return np.concatenate([np.real(c), np.imag(c)]).astype(np.float64)


def complex_norm(c: np.ndarray) -> float:
    c = np.asarray(c, dtype=np.complex128)
    # Hermitian norm equals l2 norm of realification
    return float(np.sqrt(np.sum(np.abs(c) ** 2)))


def apply_spd_weights(x: np.ndarray, g_diag: np.ndarray) -> np.ndarray:
    """
    Apply x_G = G^(1/2) x for diagonal SPD G = diag(g_i), g_i>0.
    """
    x = np.asarray(x, dtype=np.float64)
    g_diag = np.asarray(g_diag, dtype=np.float64)
    if x.shape[0] != g_diag.shape[0]:
        raise ValueError("x and g_diag must have same length")
    if np.any(g_diag <= 0):
        raise ValueError("All SPD diagonal weights must be > 0")
    return np.sqrt(g_diag) * x


# ----------------------------
# Layer group 4–8: Poincaré ball + hyperbolic ops + realms
# ----------------------------

def poincare_embed(x: np.ndarray, alpha: float = 1.0, eps_ball: float = 1e-3) -> np.ndarray:
    """
    Radial tanh embedding Ψα: R^n → B^n:
      u = tanh(alpha*||x||) * x/||x||, u(0)=0
    Then clamp to ||u|| <= 1 - eps_ball for numerical safety.
    """
    x = np.asarray(x, dtype=np.float64)
    r = _norm(x)
    if r == 0.0:
        return np.zeros_like(x)
    u = (np.tanh(alpha * r) / r) * x
    return clamp_ball(u, eps_ball=eps_ball)


def hyperbolic_distance(u: np.ndarray, v: np.ndarray, eps: float = 1e-12) -> float:
    """
    Poincaré ball distance:
      dH(u,v)=arcosh(1 + 2||u-v||^2/((1-||u||^2)(1-||v||^2)) )
    eps protects denominators.
    """
    u = np.asarray(u, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)

    uu = float(np.dot(u, u))
    vv = float(np.dot(v, v))
    duv = float(np.dot(u - v, u - v))

    denom = (1.0 - uu) * (1.0 - vv)
    denom = max(denom, eps)  # floor
    arg = 1.0 + (2.0 * duv) / denom
    return float(safe_arcosh(arg))


def mobius_add(a: np.ndarray, u: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """
    Möbius addition on the Poincaré ball (gyrovector addition):
      a ⊕ u = ((1+2<a,u>+||u||^2)a + (1-||a||^2)u) / (1+2<a,u>+||a||^2||u||^2)
    """
    a = np.asarray(a, dtype=np.float64)
    u = np.asarray(u, dtype=np.float64)

    au = float(np.dot(a, u))
    aa = float(np.dot(a, a))
    uu = float(np.dot(u, u))

    denom = 1.0 + 2.0 * au + aa * uu
    denom = np.sign(denom) * max(abs(denom), eps)

    num = (1.0 + 2.0 * au + uu) * a + (1.0 - aa) * u
    return num / denom


def phase_transform(u: np.ndarray, a: np.ndarray, Q: Optional[np.ndarray] = None,
                    eps_ball: float = 1e-3) -> np.ndarray:
    """
    Phase transform: T_phase(u) = Q (a ⊕ u), where Q ∈ O(n).
    If Q is None, identity is used.
    """
    u2 = mobius_add(a, u)
    if Q is not None:
        u2 = np.asarray(Q, dtype=np.float64) @ np.asarray(u2, dtype=np.float64)
    return clamp_ball(u2, eps_ball=eps_ball)


def breathing_transform(u: np.ndarray, b: float, eps_ball: float = 1e-3) -> np.ndarray:
    """
    Breathing: radial diffeomorphism on the ball:
      r' = tanh(b * artanh(r)), u' = (r'/r) u
    Not an isometry unless b=1.
    """
    u = np.asarray(u, dtype=np.float64)
    r = _norm(u)
    if r == 0.0:
        return u.copy()
    # keep inside open interval for arctanh
    r = min(r, 1.0 - eps_ball)
    rp = float(np.tanh(b * np.arctanh(r)))
    out = (rp / r) * u
    return clamp_ball(out, eps_ball=eps_ball)


def realm_distance(u: np.ndarray, centers: np.ndarray) -> float:
    """d*(u) = min_k dH(u, μ_k)."""
    u = np.asarray(u, dtype=np.float64)
    centers = np.asarray(centers, dtype=np.float64)
    if centers.ndim != 2:
        raise ValueError("centers must be shape (K,n)")
    dmins = [hyperbolic_distance(u, centers[k]) for k in range(centers.shape[0])]
    return float(min(dmins))


# ----------------------------
# Layer group 9–11: coherence + triadic temporal distance
# ----------------------------

def spectral_stability(y: np.ndarray, hf_frac: float = 0.5, eps: float = 1e-12) -> float:
    """
    Spectral stability S_spec = 1 - r_HF where r_HF is fraction of power in high bins.
    hf_frac=0.5 means top half of non-DC bins are "high".
    Returns S_spec in [0,1].
    """
    y = np.asarray(y, dtype=np.float64)
    if y.size < 2:
        return 1.0

    Y = np.fft.fft(y)
    P = np.abs(Y) ** 2
    total = float(np.sum(P))
    total = max(total, eps)

    # define high-frequency set: highest hf_frac of bins excluding DC
    N = P.size
    k0 = 1  # exclude DC
    bins = np.arange(k0, N)
    cutoff = int(np.floor((1.0 - hf_frac) * bins.size))
    hf_bins = bins[cutoff:] if bins.size > 0 else np.array([], dtype=int)

    hf_power = float(np.sum(P[hf_bins])) if hf_bins.size > 0 else 0.0
    r_hf = hf_power / total
    r_hf = min(max(r_hf, 0.0), 1.0)
    return float(1.0 - r_hf)


def spin_coherence(phasors: np.ndarray, eps: float = 1e-12) -> float:
    """
    C_spin = |sum s_j| / (sum |s_j| + eps) ∈ [0,1]
    """
    s = np.asarray(phasors, dtype=np.complex128)
    num = abs(np.sum(s))
    denom = float(np.sum(np.abs(s))) + eps
    c = float(num / denom)
    return float(min(max(c, 0.0), 1.0))


def triadic_distance(d1: float, d2: float, dG: float,
                    lambdas: Tuple[float, float, float] = (0.4, 0.3, 0.3)) -> float:
    """
    d_tri = sqrt(λ1 d1^2 + λ2 d2^2 + λ3 dG^2), λi>0, sum=1.
    """
    l1, l2, l3 = lambdas
    if min(l1, l2, l3) <= 0:
        raise ValueError("All lambdas must be > 0")
    s = l1 * (d1 ** 2) + l2 * (d2 ** 2) + l3 * (dG ** 2)
    return float(np.sqrt(max(0.0, s)))


def clamp01(x: float) -> float:
    return float(min(max(x, 0.0), 1.0))


# ----------------------------
# Layer group 12–14: Harmonic scaling + risk + decision
# ----------------------------

def harmonic_scaling(d: float, R: float = 1.5, max_log: float = 700.0) -> Tuple[float, float]:
    """
    H(d,R) = R^(d^2) computed safely via exp(log(R)*d^2).
    Returns (H, logH). logH is clamped to max_log to avoid overflow.
    """
    if R <= 1.0:
        raise ValueError("R must be > 1 for harmonic amplification")
    logH = float(np.log(R) * (d ** 2))
    logH_c = min(logH, max_log)
    H = float(np.exp(logH_c))
    return H, logH_c


@dataclass(frozen=True)
class RiskWeights:
    """
    Weights for base risk terms.
    All must be >=0.
    Recommended: sum to 1, but not required.
    """
    w_dtri: float = 0.30
    w_spin: float = 0.20
    w_spec: float = 0.20
    w_trust: float = 0.20
    w_audio: float = 0.10


def risk_base(
    d_tri_norm: float,
    C_spin: float,
    S_spec: float,
    trust_tau: float,
    S_audio: float,
    w: RiskWeights = RiskWeights(),
) -> float:
    """
    Base risk is a nonnegative weighted sum of "badness" features:
      d_tri_norm ∈ [0,1]
      1-C_spin ∈ [0,1]
      1-S_spec ∈ [0,1]
      1-trust_tau ∈ [0,1]
      1-S_audio ∈ [0,1]
    """
    d_tri_norm = clamp01(d_tri_norm)
    C_spin = clamp01(C_spin)
    S_spec = clamp01(S_spec)
    trust_tau = clamp01(trust_tau)
    S_audio = clamp01(S_audio)

    terms = [
        w.w_dtri * d_tri_norm,
        w.w_spin * (1.0 - C_spin),
        w.w_spec * (1.0 - S_spec),
        w.w_trust * (1.0 - trust_tau),
        w.w_audio * (1.0 - S_audio),
    ]
    # Nonnegative by construction if weights are nonnegative
    return float(sum(terms))


def risk_prime(
    d_star: float,
    risk_base_value: float,
    R: float = 1.5,
    max_log: float = 700.0,
) -> Dict[str, float]:
    """
    Risk' = Risk_base * H(d*, R)
    Returns risk', plus H and logH for debugging / stability.
    """
    rb = max(0.0, float(risk_base_value))
    H, logH = harmonic_scaling(float(d_star), R=R, max_log=max_log)
    rp = rb * H
    return {"risk_prime": float(rp), "H": float(H), "logH": float(logH), "risk_base": float(rb)}


def decision_from_risk(risk_prime_value: float,
                       allow: float = 0.30,
                       deny: float = 0.70) -> str:
    """
    Convert Risk' into a discrete decision.
    If you want strict 1/0 outputs, map ALLOW->1, others->0 externally.
    """
    r = float(risk_prime_value)
    if r < allow:
        return "ALLOW"
    if r > deny:
        return "DENY"
    return "QUARANTINE"


# ----------------------------
# Self-test: numeric verification of axioms
# ----------------------------

def self_test(verbose: bool = True) -> Dict[str, Any]:
    rng = np.random.default_rng(7)

    # A1: Realification isometry
    c = np.array([1 + 2j, 3 - 4j], dtype=np.complex128)
    x = realify(c)
    ok_iso = abs(complex_norm(c) - _norm(x)) < 1e-10

    # Build a ball state for later tests
    g = np.array([1.0, 4.0, 2.0, 5.0])
    xG = apply_spd_weights(x, g)
    u = poincare_embed(xG, alpha=1.0, eps_ball=1e-3)

    # A4: distance symmetry, identity (numeric)
    d_uu = hyperbolic_distance(u, u)
    v = clamp_ball(rng.normal(size=u.shape) * 0.1, eps_ball=1e-3)
    d_uv = hyperbolic_distance(u, v)
    d_vu = hyperbolic_distance(v, u)
    ok_metric = (abs(d_uu) < 1e-12) and (abs(d_uv - d_vu) < 1e-10) and (d_uv >= 0.0)

    # A5: phase isometry (numeric)
    a = clamp_ball(rng.normal(size=u.shape) * 0.05, eps_ball=1e-3)
    Q = np.eye(u.shape[0])
    duv_before = hyperbolic_distance(u, v)
    u2 = phase_transform(u, a, Q=Q, eps_ball=1e-3)
    v2 = phase_transform(v, a, Q=Q, eps_ball=1e-3)
    duv_after = hyperbolic_distance(u2, v2)
    ok_phase_iso = abs(duv_before - duv_after) < 1e-8

    # A7: realm distance is 1-Lipschitz (numeric check)
    centers = np.stack([
        np.zeros_like(u),
        clamp_ball(np.array([0.2, 0.0, 0.0, 0.0]), eps_ball=1e-3)
    ], axis=0)
    dstar_u = realm_distance(u, centers)
    dstar_v = realm_distance(v, centers)
    ok_lip = abs(dstar_u - dstar_v) <= hyperbolic_distance(u, v) + 1e-7

    # A11: monotonicity in a badness feature (d*).
    rb = risk_base(d_tri_norm=0.2, C_spin=0.9, S_spec=0.9, trust_tau=0.9, S_audio=0.9)
    rp1 = risk_prime(d_star=0.5, risk_base_value=rb, R=1.5)["risk_prime"]
    rp2 = risk_prime(d_star=1.0, risk_base_value=rb, R=1.5)["risk_prime"]
    ok_mono = rp2 >= rp1

    results = {
        "A1_realification_isometry": ok_iso,
        "A4_metric_basic_checks": ok_metric,
        "A5_phase_isometry_numeric": ok_phase_iso,
        "A7_realm_distance_lipschitz_numeric": ok_lip,
        "A11_risk_monotone_in_dstar": ok_mono,
        "sample_u_norm": _norm(u),
        "sample_dstar_u": dstar_u,
        "sample_rb": rb,
        "sample_rp_dstar_1": rp2,
    }

    if verbose:
        print("=" * 72)
        print("QASI CORE SELF-TEST (numeric axiom verification)")
        print("=" * 72)
        for k, v in results.items():
            if isinstance(v, bool):
                print(f"{k:35s}: {'PASS' if v else 'FAIL'}")
        print("-" * 72)
        print(f"sample ||u||          = {results['sample_u_norm']:.6f}")
        print(f"sample d*(u)          = {results['sample_dstar_u']:.6f}")
        print(f"sample Risk_base      = {results['sample_rb']:.6f}")
        print(f"sample Risk'(d*=1.0)  = {results['sample_rp_dstar_1']:.6e}")
        print("=" * 72)

    return results


if __name__ == "__main__":
    out = self_test(verbose=True)
    # Exit code style behavior (optional): fail hard if any bool is False
    failed = [k for k, v in out.items() if isinstance(v, bool) and not v]
    if failed:
        raise SystemExit(f"QASI core self-test FAILED: {failed}")
