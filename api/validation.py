"""
Shared validation primitives for next-generation browser governance.

This module centralizes:
- 14-layer hyperbolic containment scoring
- real-time action-spectrum checks (hallucination gate)
- Symphonic Cipher verification hooks

Both FastAPI and Lambda fallback paths should call this module to avoid drift.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any, Dict, List, Sequence, Tuple

try:
    import numpy as np
except ImportError:  # pragma: no cover - runtime fallback
    np = None

try:
    from symphonic_cipher.scbe_aethermoore_core import SCBEAethermooreVerifier
except Exception:  # pragma: no cover - optional dependency
    SCBEAethermooreVerifier = None


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _hash_seed(agent_id: str, action: str, target: str) -> bytes:
    return hashlib.sha256(f"{agent_id}:{action}:{target}".encode("utf-8")).digest()


def agent_to_6d_position(agent_id: str, action: str, target: str, trust: float) -> Tuple[float, ...]:
    """Map request context to 6D bounded Poincaré coordinates."""
    seed = _hash_seed(agent_id, action, target)
    trust = _clamp(trust, 0.0, 1.0)
    radius = (1.0 - trust) * 0.8 + 0.1
    coords: List[float] = []
    for i in range(6):
        val = seed[i] / 255.0
        coords.append(val * radius - radius / 2.0)
    return tuple(coords)


def hyperbolic_distance(p1: Sequence[float], p2: Sequence[float]) -> float:
    """Poincaré-ball geodesic distance."""
    norm1_sq = sum(x * x for x in p1)
    norm2_sq = sum(x * x for x in p2)
    diff_sq = sum((a - b) ** 2 for a, b in zip(p1, p2))
    norm1_sq = min(norm1_sq, 0.9999)
    norm2_sq = min(norm2_sq, 0.9999)
    denom = (1.0 - norm1_sq) * (1.0 - norm2_sq)
    if denom <= 0.0:
        return float("inf")
    delta = 2.0 * diff_sq / denom
    return math.acosh(1.0 + max(delta, 0.0))


def _harmonic_window(seed: bytes, length: int) -> List[int]:
    """Deterministic expected harmonic bins from request seed."""
    if length <= 1:
        return [0]
    bins = []
    for i in range(4):
        bins.append((seed[10 + i] % (length - 1)) + 1)
    return sorted(set(bins))


def _fft_bins(signal: List[float], top_k: int = 4) -> List[int]:
    if len(signal) < 2:
        return [0]
    if np is None:
        # Tiny fallback DFT for deterministic environments without numpy.
        mags = []
        n = len(signal)
        for k in range(n):
            real = 0.0
            imag = 0.0
            for i, x in enumerate(signal):
                angle = 2.0 * math.pi * k * i / n
                real += x * math.cos(angle)
                imag -= x * math.sin(angle)
            mags.append(math.sqrt(real * real + imag * imag))
    else:
        mags = np.abs(np.fft.rfft(np.array(signal, dtype=float))).tolist()
    ranked = sorted(range(len(mags)), key=lambda i: mags[i], reverse=True)
    return sorted(ranked[: max(1, top_k)])


def action_spectrum_verdict(agent_id: str, action: str, target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Real-time hallucination check using action spectrum harmonics.

    A low overlap between observed and expected overtones is treated as drift.
    """
    material = f"{action}|{target}|{context.get('mode', 'default')}".encode("utf-8")
    signal = [b / 255.0 for b in material]
    observed = _fft_bins(signal, top_k=4)
    expected = _harmonic_window(_hash_seed(agent_id, action, target), max(2, len(observed) + 1))
    overlap = set(observed).intersection(expected)
    score = len(overlap) / max(len(expected), 1)
    valid = score >= 0.34
    return {
        "observed_bins": observed,
        "expected_bins": expected,
        "match_score": round(score, 4),
        "valid": valid,
    }


def _symphonic_verdict(agent_id: str, action: str, target: str, trust_score: float, sensitivity: float) -> Dict[str, Any]:
    if SCBEAethermooreVerifier is None or np is None:
        return {
            "available": False,
            "accepted": True,
            "reason": "symphonic_verifier_unavailable",
        }

    key = hashlib.sha256(f"{agent_id}:{action}".encode("utf-8")).digest()
    verifier = SCBEAethermooreVerifier(key)

    context_vec = np.array(
        [
            _clamp(trust_score, 0.0, 1.0),
            _clamp(1.0 - sensitivity, 0.0, 1.0),
            len(action) / 32.0,
            len(target) / 64.0,
            sensitivity,
            0.5,
        ],
        dtype=float,
    )
    intent_vec = np.array(
        [
            len(action) / 32.0,
            len(target) / 64.0,
            _clamp(trust_score - sensitivity, -1.0, 1.0),
        ],
        dtype=float,
    )
    payload = f"{agent_id}|{action}|{target}".encode("utf-8")
    accepted, reason, _ = verifier.verify_request(context_vec, intent_vec, payload)
    return {
        "available": True,
        "accepted": bool(accepted),
        "reason": str(reason),
    }


def run_nextgen_action_validation(
    *,
    agent_id: str,
    action: str,
    target: str,
    trust_score: float,
    sensitivity: float = 0.5,
    context: Dict[str, Any] | None = None,
    drift_threshold: float = 0.95,
) -> Tuple[str, float, Dict[str, Any]]:
    """
    Unified 14-layer + spectral + Symphonic validation.

    Returns:
      (decision_str, score, explanation)
    where decision_str is one of: ALLOW, QUARANTINE, DENY.
    """
    ctx = context or {}
    trust_score = _clamp(_to_float(trust_score, 0.5), 0.0, 1.0)
    sensitivity = _clamp(_to_float(sensitivity, 0.5), 0.0, 1.0)
    drift_threshold = _clamp(_to_float(drift_threshold, 0.95), 0.5, 0.999)

    explanation: Dict[str, Any] = {"layers": {}}

    # L1-L4: Context embedding.
    position = agent_to_6d_position(agent_id, action, target, trust_score)
    explanation["layers"]["L1-4"] = "6D context embedding computed"

    # L5-L7: Hyperbolic distance + containment penalty.
    safe_center = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    distance = hyperbolic_distance(position, safe_center)
    norm = math.sqrt(sum(x * x for x in position))
    containment_penalty = math.exp(min(distance, 4.0) ** 2)
    explanation["layers"]["L5-7"] = f"d_H={distance:.4f}, penalty=exp(d^2)={containment_penalty:.4f}"

    # L8-L12: trust/coherence/risk synthesis.
    realm_trust = trust_score * (1.0 - sensitivity * 0.5)
    coherence = 1.0 - abs(math.sin(distance * math.pi))
    temporal_score = trust_score * 0.9 + 0.1
    risk_factor = (1.0 - realm_trust) * sensitivity * 0.5
    base_score = (realm_trust * 0.6 + coherence * 0.2 + temporal_score * 0.2) - risk_factor

    explanation["layers"]["L8"] = f"realm_trust={realm_trust:.4f}"
    explanation["layers"]["L9-10"] = f"coherence={coherence:.4f}"
    explanation["layers"]["L11"] = f"temporal={temporal_score:.4f}"
    explanation["layers"]["L12"] = f"risk_factor={risk_factor:.4f}"

    # Real-time hallucination gate.
    spectrum = action_spectrum_verdict(agent_id, action, target, ctx)
    symphonic = _symphonic_verdict(agent_id, action, target, trust_score, sensitivity)
    explanation["layers"]["L13"] = (
        f"spectrum_valid={spectrum['valid']} (match={spectrum['match_score']}) "
        f"symphonic_accept={symphonic['accepted']}"
    )
    explanation["layers"]["L14"] = "telemetry_ready"

    # Decision logic.
    hard_quarantine = (
        norm >= drift_threshold
        or not spectrum["valid"]
        or not symphonic["accepted"]
    )

    if hard_quarantine:
        decision = "QUARANTINE"
    elif base_score > 0.6:
        decision = "ALLOW"
    elif base_score > 0.3:
        decision = "QUARANTINE"
    else:
        decision = "DENY"

    explanation.update(
        {
            "trust_score": round(trust_score, 4),
            "sensitivity": round(sensitivity, 4),
            "distance": round(distance, 4),
            "drift_norm": round(norm, 4),
            "drift_threshold": round(drift_threshold, 4),
            "containment_penalty": round(containment_penalty, 4),
            "risk_factor": round(risk_factor, 4),
            "spectrum": spectrum,
            "symphonic": symphonic,
        }
    )
    return decision, float(round(base_score, 6)), explanation

