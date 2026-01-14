#!/usr/bin/env python3
"""
QASI Core (2026) - Quantized/Quasi-Adaptive Security Interface
==============================================================

SCBE mathematical core with Poincare ball embedding, hyperbolic geometry,
and multi-scale risk scoring. Implements axioms A1-A12.

Dependencies: numpy only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
import numpy as np


def _norm(x: np.ndarray) -> float:
    return float(np.linalg.norm(x))


def clamp_ball(u: np.ndarray, eps_ball: float = 1e-3) -> np.ndarray:
    """Clamp vector to sub-ball ||u|| <= 1 - eps_ball."""
    r = _norm(u)
    r_max = 1.0 - float(eps_ball)
    if r <= r_max:
        return u
    if r == 0.0:
        return u
    return (r_max / r) * u


def safe_arcosh(x):
    """arcosh defined for x>=1."""
    if isinstance(x, float):
        return float(np.arccosh(max(1.0, x)))
    return np.arccosh(np.maximum(1.0, x))


def realify(c: np.ndarray) -> np.ndarray:
    """Realification isometry: C^D -> R^(2D)."""
    c = np.asarray(c, dtype=np.complex128)
    return np.concatenate([np.real(c), np.imag(c)]).astype(np.float64)


def complex_norm(c: np.ndarray) -> float:
    c = np.asarray(c, dtype=np.complex128)
    return float(np.sqrt(np.sum(np.abs(c) ** 2)))


def apply_spd_weights(x: np.ndarray, g_diag: np.ndarray) -> np.ndarray:
    """Apply x_G = G^(1/2) x for diagonal SPD G."""
    x = np.asarray(x, dtype=np.float64)
    g_diag = np.asarray(g_diag, dtype=np.float64)
    return np.sqrt(g_diag) * x


def poincare_embed(x: np.ndarray, alpha: float = 1.0, eps_ball: float = 1e-3) -> np.ndarray:
    """Radial tanh embedding to Poincare ball."""
    x = np.asarray(x, dtype=np.float64)
    r = _norm(x)
    if r == 0.0:
        return np.zeros_like(x)
    u = (np.tanh(alpha * r) / r) * x
    return clamp_ball(u, eps_ball=eps_ball)


def hyperbolic_distance(u: np.ndarray, v: np.ndarray, eps: float = 1e-12) -> float:
    """Poincare ball distance."""
    u = np.asarray(u, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)
    uu = float(np.dot(u, u))
    vv = float(np.dot(v, v))
    duv = float(np.dot(u - v, u - v))
    denom = max((1.0 - uu) * (1.0 - vv), eps)
    arg = 1.0 + (2.0 * duv) / denom
    return float(safe_arcosh(arg))


def mobius_add(a: np.ndarray, u: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """Mobius addition on Poincare ball."""
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
    """Phase transform: T_phase(u) = Q (a + u)."""
    u2 = mobius_add(a, u)
    if Q is not None:
        u2 = np.asarray(Q, dtype=np.float64) @ np.asarray(u2, dtype=np.float64)
    return clamp_ball(u2, eps_ball=eps_ball)


def breathing_transform(u: np.ndarray, b: float, eps_ball: float = 1e-3) -> np.ndarray:
    """Breathing: radial diffeomorphism on ball."""
    u = np.asarray(u, dtype=np.float64)
    r = _norm(u)
    if r == 0.0:
        return u.copy()
    r = min(r, 1.0 - eps_ball)
    rp = float(np.tanh(b * np.arctanh(r)))
    out = (rp / r) * u
    return clamp_ball(out, eps_ball=eps_ball)


def realm_distance(u: np.ndarray, centers: np.ndarray) -> float:
    """d*(u) = min_k dH(u, mu_k)."""
    u = np.asarray(u, dtype=np.float64)
    centers = np.asarray(centers, dtype=np.float64)
    dmins = [hyperbolic_distance(u, centers[k]) for k in range(centers.shape[0])]
    return float(min(dmins))


def spectral_stability(y: np.ndarray, hf_frac: float = 0.5, eps: float = 1e-12) -> float:
    """S_spec = 1 - r_HF in [0,1]."""
    y = np.asarray(y, dtype=np.float64)
    if y.size < 2:
        return 1.0
    Y = np.fft.fft(y)
    P = np.abs(Y) ** 2
    total = max(float(np.sum(P)), eps)
    N = P.size
    bins = np.arange(1, N)
    cutoff = int(np.floor((1.0 - hf_frac) * bins.size))
    hf_bins = bins[cutoff:] if bins.size > 0 else np.array([], dtype=int)
    hf_power = float(np.sum(P[hf_bins])) if hf_bins.size > 0 else 0.0
    r_hf = min(max(hf_power / total, 0.0), 1.0)
    return float(1.0 - r_hf)


def spin_coherence(phasors: np.ndarray, eps: float = 1e-12) -> float:
    """C_spin = |sum s_j| / (sum |s_j| + eps)."""
    s = np.asarray(phasors, dtype=np.complex128)
    num = abs(np.sum(s))
    denom = float(np.sum(np.abs(s))) + eps
    return float(min(max(num / denom, 0.0), 1.0))


def triadic_distance(d1: float, d2: float, dG: float,
                    lambdas: Tuple[float, float, float] = (0.4, 0.3, 0.3)) -> float:
    """d_tri = sqrt(l1*d1^2 + l2*d2^2 + l3*dG^2)."""
    l1, l2, l3 = lambdas
    s = l1 * (d1 ** 2) + l2 * (d2 ** 2) + l3 * (dG ** 2)
    return float(np.sqrt(max(0.0, s)))


def harmonic_scaling(d: float, R: float = 1.5, max_log: float = 700.0) -> Tuple[float, float]:
    """H(d,R) = R^(d^2)."""
    logH = float(np.log(R) * (d ** 2))
    logH_c = min(logH, max_log)
    H = float(np.exp(logH_c))
    return H, logH_c


@dataclass(frozen=True)
class RiskWeights:
    w_dtri: float = 0.30
    w_spin: float = 0.20
    w_spec: float = 0.20
    w_trust: float = 0.20
    w_audio: float = 0.10


def clamp01(x: float) -> float:
    return float(min(max(x, 0.0), 1.0))


def risk_base(d_tri_norm: float, C_spin: float, S_spec: float,
              trust_tau: float, S_audio: float, w: RiskWeights = RiskWeights()) -> float:
    """Base risk from bounded features."""
    terms = [
        w.w_dtri * clamp01(d_tri_norm),
        w.w_spin * (1.0 - clamp01(C_spin)),
        w.w_spec * (1.0 - clamp01(S_spec)),
        w.w_trust * (1.0 - clamp01(trust_tau)),
        w.w_audio * (1.0 - clamp01(S_audio)),
    ]
    return float(sum(terms))


def risk_prime(d_star: float, risk_base_value: float, R: float = 1.5) -> Dict[str, float]:
    """Risk' = Risk_base * H(d*, R)."""
    rb = max(0.0, float(risk_base_value))
    H, logH = harmonic_scaling(float(d_star), R=R)
    return {"risk_prime": rb * H, "H": H, "logH": logH, "risk_base": rb}


def decision_from_risk(risk_prime_value: float, allow: float = 0.30, deny: float = 0.70) -> str:
    """Convert Risk' to ALLOW/QUARANTINE/DENY."""
    r = float(risk_prime_value)
    if r < allow:
        return "ALLOW"
    if r > deny:
        return "DENY"
    return "QUARANTINE"


def self_test(verbose: bool = True) -> Dict[str, Any]:
    """Numeric axiom verification."""
    rng = np.random.default_rng(7)
    
    # A1: Realification isometry
    c = np.array([1 + 2j, 3 - 4j], dtype=np.complex128)
    x = realify(c)
    ok_iso = abs(complex_norm(c) - _norm(x)) < 1e-10
    
    # Build state
    g = np.array([1.0, 4.0, 2.0, 5.0])
    xG = apply_spd_weights(x, g)
    u = poincare_embed(xG, alpha=1.0)
    
    # A4: metric checks
    d_uu = hyperbolic_distance(u, u)
    v = clamp_ball(rng.normal(size=u.shape) * 0.1)
    d_uv = hyperbolic_distance(u, v)
    d_vu = hyperbolic_distance(v, u)
    ok_metric = (abs(d_uu) < 1e-12) and (abs(d_uv - d_vu) < 1e-10)
    
    # A5: phase isometry
    a = clamp_ball(rng.normal(size=u.shape) * 0.05)
    Q = np.eye(u.shape[0])
    duv_before = hyperbolic_distance(u, v)
    u2 = phase_transform(u, a, Q=Q)
    v2 = phase_transform(v, a, Q=Q)
    duv_after = hyperbolic_distance(u2, v2)
    ok_phase = abs(duv_before - duv_after) < 1e-8
    
    # A7: realm Lipschitz
    centers = np.stack([np.zeros_like(u), clamp_ball(np.array([0.2, 0.0, 0.0, 0.0]))], axis=0)
    dstar_u = realm_distance(u, centers)
    dstar_v = realm_distance(v, centers)
    ok_lip = abs(dstar_u - dstar_v) <= hyperbolic_distance(u, v) + 1e-7
    
    # A11: monotonicity
    rb = risk_base(0.2, 0.9, 0.9, 0.9, 0.9)
    rp1 = risk_prime(0.5, rb)["risk_prime"]
    rp2 = risk_prime(1.0, rb)["risk_prime"]
    ok_mono = rp2 >= rp1
    
    results = {
        "A1_realification_isometry": ok_iso,
        "A4_metric_checks": ok_metric,
        "A5_phase_isometry": ok_phase,
        "A7_realm_lipschitz": ok_lip,
        "A11_monotonicity": ok_mono,
    }
    
    if verbose:
        print("=" * 60)
        print("QASI CORE SELF-TEST")
        print("=" * 60)
        for k, v in results.items():
            print(f"{k:30s}: {'PASS' if v else 'FAIL'}")
        print("=" * 60)
    
    return results


if __name__ == "__main__":
    out = self_test(verbose=True)
    failed = [k for k, v in out.items() if not v]
    if failed:
        raise SystemExit(f"FAIL: {failed}")
