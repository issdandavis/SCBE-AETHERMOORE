"""Prototype dynamic per-tongue relation radii: r_i(t) = w_i + epsilon * rho_i(t).

Empirical-only. Opt-in via `composite_harmonic_wall_dynamic`; the production wall
in `polyhedral_flow.composite_harmonic_wall` is untouched.

Falls back to the static wall whenever any requested axis is below the rho warmup
threshold (so behavior is identical to static when there is not yet enough signal).

Read flow:
    rho is computed from the same in-memory buffer the SCBE_RHO_LOG logger fills.
    No file I/O. No env gating.
"""

from __future__ import annotations

import math
from typing import Deque, Dict, Mapping, Optional, Tuple

from . import polyhedral_flow as pf

PHI: float = pf.PHI


def _rho_for(history: Mapping[str, Deque[Tuple[float, float]]], axis: str) -> Optional[float]:
    buf = history.get(axis)
    if buf is None or len(buf) < pf._RHO_LOG_MIN_SAMPLES:
        return None
    return pf._pearson(list(buf))


def compute_dynamic_radii(
    axes: Optional[Mapping[str, float]] = None,
    *,
    epsilon: float = 0.1,
    base_weights: Mapping[str, float] = pf.TONGUE_WEIGHTS,
    history: Optional[Mapping[str, Deque[Tuple[float, float]]]] = None,
) -> Optional[Dict[str, float]]:
    """Return per-axis radii or None if any requested axis is not warm.

    axes:    optional iterable / mapping of axis names to limit the radii to.
             Default: keys of base_weights.
    epsilon: rho perturbation gain. Small (~0.1) keeps weights near static.
    """
    hist = history if history is not None else pf._RHO_HISTORY
    keys = list((axes or base_weights).keys())
    radii: Dict[str, float] = {}
    for k in keys:
        if k not in base_weights:
            continue
        rho = _rho_for(hist, k)
        if rho is None:
            return None
        radii[k] = max(0.0, float(base_weights[k]) + float(epsilon) * float(rho))
    return radii or None


def composite_harmonic_wall_dynamic(
    distances: Dict[str, float],
    *,
    epsilon: float = 0.1,
    phase_deviation: float = 0.0,
    phi: float = PHI,
    history: Optional[Mapping[str, Deque[Tuple[float, float]]]] = None,
) -> Dict[str, object]:
    """Opt-in dynamic-radii variant of composite_harmonic_wall.

    When all requested axes are warm, uses radii-weighted mean distance:
        weighted_mean_d = sum(r_i * d_i) / sum(r_i)

    Otherwise falls back to the static wall (behavior-identical to
    composite_harmonic_wall). The returned dict includes a `mode` key
    ("dynamic" or "static_fallback") plus `radii` when dynamic.
    """
    radii = compute_dynamic_radii(distances, epsilon=epsilon, history=history)
    if radii is None:
        out = pf.composite_harmonic_wall(distances, phase_deviation=phase_deviation, phi=phi)
        return {**out, "mode": "static_fallback", "radii": None}

    total_r = sum(radii.values())
    if total_r <= 0.0:
        out = pf.composite_harmonic_wall(distances, phase_deviation=phase_deviation, phi=phi)
        return {**out, "mode": "static_fallback", "radii": None}

    weighted_mean_d = sum(radii[k] * float(distances[k]) for k in radii) / total_r
    h = math.exp(-phi * weighted_mean_d) * math.exp(-abs(float(phase_deviation)) / 5.0)
    h *= math.exp(-0.03 * max(len(distances) - 1, 0))
    h = float(max(min(h, 1.0), 1e-12))
    tier = "ALLOW" if h >= 0.75 else ("DENY" if h < 0.15 else "QUARANTINE")
    return {
        "h_composite": h,
        "tier": tier,
        "mitm_immune": True,
        "mode": "dynamic",
        "radii": radii,
        "weighted_mean_d": float(weighted_mean_d),
    }
