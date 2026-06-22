"""
Optical Laser / Penetration-Retention Model for Prime Transition Manifold

This module formalizes the "laser in the darkness" idea discussed for the
prime_fog_of_war probe.

Core concepts:
- log_R and log_Q as scale-invariant multiplicative transitions and curvature.
- Optical depth d (how "deep" we are in the manifold).
- Penetration mode (explore with imaginary paths) vs Retention mode (retrieve similar historical transitions).
- Dual wavelength: ultra-visible (fine recent Q) and sub-visible (coarse structure / long-range similarity).
- Depth-dependent switch at d*.

This is designed to be dropped into or alongside prime_fog_of_war_probe.py.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class Transition:
    idx: int
    log_r: float
    log_q: float
    thermal_amplitude: float = 0.0
    gradient_abs: float = 0.0


def compute_log_transitions(gaps: List[float]) -> List[Transition]:
    """Convert raw gaps into log R and log Q (curvature)."""
    if len(gaps) < 3:
        return []
    trans = []
    for i in range(len(gaps) - 2):
        r = gaps[i + 1] / gaps[i] if gaps[i] > 0 else 1.0
        q = (gaps[i + 1] / gaps[i]) / (gaps[i + 2] / gaps[i + 1]) if gaps[i + 1] > 0 and gaps[i] > 0 else 1.0
        trans.append(
            Transition(
                idx=i,
                log_r=math.log(r) if r > 0 else 0.0,
                log_q=math.log(q) if q > 0 else 0.0,
            )
        )
    return trans


def optical_depth(t: Transition, window: List[Transition], cold_spot: float, gradient_abs: float) -> float:
    """
    Estimate local optical depth.
    Combines local curvature magnitude + thermal signal strength.
    Higher d means deeper in "darkness" (more retention, less pure penetration).
    """
    local_curvature = abs(t.log_q)
    # Simple proxy: stronger thermal gradient or lower cold_spot -> higher depth.
    thermal_signal = gradient_abs * (1.0 / (1.0 + cold_spot))
    d = local_curvature * 2.0 + thermal_signal * 1.5
    return d


def compute_dual_wavelength_scores(
    recent_trans: List[Transition], historical: List[Transition], k: int = 8
) -> Dict[str, float]:
    """
    Ultra-visible: fine detail on recent log_q
    Sub-visible: broader structure via similarity to historical
    """
    if not recent_trans:
        return {"ultra": 0.0, "sub": 0.0}

    # Ultra-visible (high-pass / recent fine curvature)
    recent_q = [abs(t.log_q) for t in recent_trans[-4:]]
    ultra = sum(recent_q) / len(recent_q) if recent_q else 0.0

    # Sub-visible: average similarity to k historical neighbors (by log_r)
    current_log_r = recent_trans[-1].log_r if recent_trans else 0.0
    similarities = []
    for h in historical:
        dist = abs(h.log_r - current_log_r)
        sim = math.exp(-dist * 2.0)
        similarities.append(sim)
    similarities.sort(reverse=True)
    sub = sum(similarities[:k]) / k if similarities else 0.0

    return {"ultra": ultra, "sub": sub}


def laser_mode(d: float, d_star: float = 1.8, retention_weight: float = 0.7) -> Tuple[str, float]:
    """
    Returns (mode, retention_strength)
    """
    if d < d_star:
        return "penetration", 0.0
    else:
        strength = min(0.95, (d - d_star) * retention_weight)
        return "retention", strength


def retention_boost(current: Transition, historical: List[Transition], top_k: int = 5) -> float:
    """
    In retention mode, find similar past transitions and return a boost.
    This is the 'photon retention' / memory retrieval step.
    """
    if not historical:
        return 1.0

    scored = []
    for h in historical:
        dist = abs(h.log_r - current.log_r) + abs(h.log_q - current.log_q) * 0.5
        scored.append((dist, h))

    scored.sort(key=lambda x: x[0])
    top = scored[:top_k]

    if not top:
        return 1.0

    # Boost is inverse to average distance (closer historical = stronger retention signal)
    avg_dist = sum(d for d, _ in top) / len(top)
    boost = 1.0 + (1.0 / (1.0 + avg_dist * 3.0))
    return boost


def apply_optical_laser(
    window_trans: List[Transition],
    historical_trans: List[Transition],
    cold_spot: float,
    gradient_abs: float,
    d_star: float = 1.8,
) -> float:
    """
    Main function: compute an adjusted anchor likelihood using the laser model.
    This can be used as an additional channel or to re-weight imaginary path scores.
    """
    if not window_trans:
        return 0.5

    current = window_trans[-1]
    d = optical_depth(current, window_trans, cold_spot, gradient_abs)
    mode, retention_strength = laser_mode(d, d_star)

    wl = compute_dual_wavelength_scores(window_trans, historical_trans)

    base = wl["ultra"] * 0.6 + wl["sub"] * 0.4

    if mode == "penetration":
        score = base * (1.0 + 0.3 * gradient_abs)  # encourage exploration
    else:
        boost = retention_boost(current, historical_trans)
        score = base * (1.0 + retention_strength * boost * 1.2)

    # Bound it
    return max(0.01, min(0.99, score))


# Example usage stub
if __name__ == "__main__":
    # Toy example with fake log transitions
    fake_gaps = [10, 14, 18, 22, 30, 42, 50, 58, 70, 90, 110]
    trans = compute_log_transitions(fake_gaps)
    print("Transitions:", [(round(t.log_r, 4), round(t.log_q, 4)) for t in trans])

    hist = trans[:-3]  # pretend earlier ones are "historical"
    recent = trans[-3:]
    score = apply_optical_laser(recent, hist, cold_spot=3.0, gradient_abs=5.0)
    print(f"Optical laser adjusted score: {score:.4f}")
