#!/usr/bin/env python3
"""
Spiral Engine deterministic gameplay simulator for Aethermoor.

Purpose:
- Convert SCBE governance math into a playable strategy simulation contract.
- Keep outputs deterministic and inspectable for backend/frontend parity.
- Emit required dual outputs per tick:
  - StateVector
  - DecisionRecord

Gameplay stack encoded here:
1) Poincare movement + hyperbolic distance
2) Intent persistence + runtime wall cost
3) Triadic watcher risk
4) Sheaf cohomology obstruction proxy on watcher lattice (Tarski-style id ∧ L flow)
5) Omega gate and action selection
6) Voxel addressing, sharding, progression state updates
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Literal

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.scbe_governance_math import PHI, Point3, poincare_dist_3d

Tongue = Literal["KO", "AV", "RU", "CA", "UM", "DR"]
PadMode = Literal[
    "ENGINEERING",
    "NAVIGATION",
    "SCIENCE",
    "COMMS",
    "SYSTEMS",
    "MISSION_PLANNING",
]
Action = Literal["ALLOW", "QUARANTINE", "DENY"]

TONGUES: tuple[Tongue, ...] = ("KO", "AV", "RU", "CA", "UM", "DR")
PADS: tuple[PadMode, ...] = (
    "ENGINEERING",
    "NAVIGATION",
    "SCIENCE",
    "COMMS",
    "SYSTEMS",
    "MISSION_PLANNING",
)

LWS_WEIGHTS: Dict[Tongue, float] = {
    "KO": 1.000,
    "AV": 1.125,
    "RU": 1.250,
    "CA": 1.333,
    "UM": 1.500,
    "DR": 1.667,
}

PAD_TONGUE_BONUS: Dict[PadMode, Dict[Tongue, float]] = {
    "ENGINEERING": {"KO": 0.12, "CA": 0.08},
    "NAVIGATION": {"AV": 0.12, "RU": 0.06},
    "SCIENCE": {"CA": 0.12, "RU": 0.06},
    "COMMS": {"UM": 0.12, "AV": 0.05},
    "SYSTEMS": {"DR": 0.12, "RU": 0.06},
    "MISSION_PLANNING": {"DR": 0.08, "KO": 0.05, "AV": 0.05},
}

SHEAF_EDGES: tuple[tuple[str, str], ...] = (
    ("fast", "memory"),
    ("memory", "governance"),
    ("fast", "governance"),
    ("fast", "spectral"),
    ("memory", "spectral"),
    ("governance", "spectral"),
)

DEFAULT_WORLD_PROFILE_PATH = ROOT / "config" / "game" / "worlds" / "aethermoor.json"
DEFAULT_WORLD_PROFILE: Dict[str, Any] = {
    "world_id": "aethermoor",
    "display_name": "Aethermoor",
    "safe_center": {"x": 0.0, "y": 0.0, "z": 0.0},
    "target_bounds": {"min": -2.6, "max": 2.6},
    "mission_duration": {"min": 6, "max": 15},
    "risk_bounds": {
        "fast": {"min": 0.15, "max": 0.90},
        "memory": {"min": 0.10, "max": 0.90},
        "governance": {"min": 0.12, "max": 0.90},
    },
    "reward_bounds": {
        "trust": {"min": 0.01, "max": 0.07},
        "coherence": {"min": 0.01, "max": 0.07},
    },
    "mission_archetypes": (
        "Leyline Stabilization",
        "Archive Recovery",
        "Trade Conduit",
        "Guardian Escort",
        "Signal Relay",
        "Boundary Patrol",
    ),
}


@dataclass(frozen=True)
class Mission:
    mission_id: str
    archetype: str
    region: str
    faction: str
    duration_ticks: int
    risk_fast: float
    risk_memory: float
    risk_governance: float
    target: Point3
    reward_trust: float
    reward_coherence: float


@dataclass
class PlayerState:
    position: Point3 = field(default_factory=lambda: Point3(0.15, 0.05, -0.1))
    trust: float = 0.82
    coherence: float = 0.78
    accumulated_intent: float = 0.20
    trust_xp: float = 0.0
    coherence_xp: float = 0.0
    tongue_levels: Dict[Tongue, int] = field(
        default_factory=lambda: {tongue: 1 for tongue in TONGUES}
    )
    pad_levels: Dict[PadMode, int] = field(
        default_factory=lambda: {pad: 1 for pad in PADS}
    )
    inventory: Dict[str, int] = field(
        default_factory=lambda: {
            "sacred_eggs": 1,
            "consensus_seal": 0,
            "spectral_filter": 0,
            "quarantine_resolver": 0,
            "audit_proof": 0,
        }
    )


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _clamp01(x: float) -> float:
    return _clamp(x, 0.0, 1.0)


def _lerp_unit(raw_byte: int, lo: float, hi: float) -> float:
    if hi <= lo:
        return lo
    return lo + (hi - lo) * (raw_byte / 255.0)


def load_world_profile(path: str | None) -> Dict[str, Any]:
    """
    Load world profile from JSON file with safe fallback to defaults.
    """
    if not path:
        return dict(DEFAULT_WORLD_PROFILE)
    p = Path(path)
    if not p.exists():
        return dict(DEFAULT_WORLD_PROFILE)
    try:
        loaded = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            return dict(DEFAULT_WORLD_PROFILE)
    except Exception:
        return dict(DEFAULT_WORLD_PROFILE)

    merged = dict(DEFAULT_WORLD_PROFILE)
    for key, value in loaded.items():
        merged[key] = value
    return merged


def quantize_floor(val: float, minv: float, maxv: float, bins: int) -> int:
    """Stable voxel quantizer (floor-based to avoid boundary flicker)."""
    if bins <= 1:
        return 0
    v = _clamp(val, minv, maxv)
    t = (v - minv) / (maxv - minv) if maxv > minv else 0.0
    q = math.floor(t * bins)
    return int(_clamp(q, 0, bins - 1))


def compute_x_factor(accumulated_intent: float, trust: float) -> float:
    trust_c = _clamp01(trust)
    x = (0.5 + accumulated_intent * 0.25) * (1.0 + (1.0 - trust_c))
    return min(3.0, x)


def runtime_wall_cost(d: float, x: float, base_r: float = 1.5) -> float:
    d_pos = max(0.0, d)
    x_pos = max(0.0, x)
    return math.exp((d_pos * d_pos * x_pos) * math.log(base_r))


def canonical_wall_cost(d_star: float, realm_scale: float = 1.0) -> float:
    """Canonical SCBE wall formula from constants skill guidance."""
    return realm_scale * (math.pi ** (PHI * d_star))


def harm_score_from_wall(h_eff: float) -> float:
    return 1.0 / (1.0 + math.log(max(1.0, h_eff)))


def triadic_risk(i_fast: float, i_memory: float, i_governance: float) -> float:
    for value in (i_fast, i_memory, i_governance):
        if value < 0:
            raise ValueError("Triadic watcher values must be nonnegative.")
    return (
        0.3 * (i_fast ** PHI)
        + 0.5 * (i_memory ** PHI)
        + 0.2 * (i_governance ** PHI)
    ) ** (1.0 / PHI)


def _neighbor_map(nodes: tuple[str, ...]) -> Dict[str, set[str]]:
    adj: Dict[str, set[str]] = {node: set() for node in nodes}
    for a, b in SHEAF_EDGES:
        if a in adj and b in adj:
            adj[a].add(b)
            adj[b].add(a)
    return adj


def tarski_laplacian_sections(local_sections: Dict[str, float]) -> Dict[str, float]:
    """
    Meet-based diffusion approximation for lattice-valued cellular sheaf data.

    For each node, L(node) = meet(neighbor values) = min(neighbor values).
    """
    keys = tuple(sorted(local_sections.keys()))
    adj = _neighbor_map(keys)
    out: Dict[str, float] = {}
    for node in keys:
        neighbors = adj.get(node, set())
        if not neighbors:
            out[node] = _clamp01(local_sections[node])
            continue
        meet_val = min(_clamp01(local_sections[n]) for n in neighbors)
        out[node] = meet_val
    return out


def tarski_postfixpoint(
    local_sections: Dict[str, float],
    *,
    max_iter: int = 32,
    tol: float = 1e-9,
) -> Dict[str, float]:
    """
    Compute Post(L) via id ∧ L fixed-point iteration.

    Phi_t = (id ∧ L)^t where ∧ is min on [0,1] lattice.
    """
    current = {k: _clamp01(v) for k, v in local_sections.items()}
    for _ in range(max_iter):
        lap = tarski_laplacian_sections(current)
        nxt = {k: min(current[k], lap[k]) for k in current}
        delta = max(abs(nxt[k] - current[k]) for k in current) if current else 0.0
        current = nxt
        if delta <= tol:
            break
    return current


def sheaf_edge_deltas(local_sections: Dict[str, float]) -> Dict[str, float]:
    """
    1-cochain edge residuals from 0-cochain local sections.

    delta0(a->b) = s(b) - s(a)
    """
    out: Dict[str, float] = {}
    for a, b in SHEAF_EDGES:
        if a in local_sections and b in local_sections:
            out[f"{a}->{b}"] = float(local_sections[b]) - float(local_sections[a])
    return out


def sheaf_obstruction(local_sections: Dict[str, float]) -> float:
    """
    Obstruction proxy: average gap from local sections to Tarski postfixpoint.
    """
    base = {k: _clamp01(v) for k, v in local_sections.items()}
    fixed = tarski_postfixpoint(base)
    if not base:
        return 0.0
    return sum(abs(base[k] - fixed[k]) for k in base) / float(len(base))


def sheaf_stability_from_obstruction(obstruction: float) -> float:
    return 1.0 / (1.0 + max(0.0, obstruction))


def omega_gate(
    pqc_valid: float,
    harm_score: float,
    drift_factor: float,
    triadic_stable: float,
    spectral_score: float,
    sheaf_stability: float,
) -> float:
    factors = [
        _clamp01(pqc_valid),
        _clamp01(harm_score),
        _clamp01(drift_factor),
        _clamp01(triadic_stable),
        _clamp01(spectral_score),
        _clamp01(sheaf_stability),
    ]
    out = 1.0
    for factor in factors:
        out *= factor
    return out


def _heat_from_distance(d: float, d_cap: float = 4.0) -> float:
    """
    Normalize hyperbolic distance into [0,1] heat for HUD rendering.
    """
    return _clamp01(d / max(1e-6, d_cap))


def _digest(seed: str) -> bytes:
    return hashlib.sha256(seed.encode("utf-8")).digest()


def _u8_to_unit(x: int) -> float:
    return x / 255.0


def generate_mission(seed: str, tick: int, *, world_profile: Dict[str, Any] | None = None) -> Mission:
    profile = world_profile or DEFAULT_WORLD_PROFILE
    raw = _digest(f"{seed}:{tick}")
    archetypes = tuple(profile.get("mission_archetypes", DEFAULT_WORLD_PROFILE["mission_archetypes"]))
    if not archetypes:
        archetypes = tuple(DEFAULT_WORLD_PROFILE["mission_archetypes"])
    archetype = archetypes[raw[0] % len(archetypes)]
    rb = profile.get("risk_bounds", {})
    fast_b = rb.get("fast", {"min": 0.15, "max": 0.90})
    mem_b = rb.get("memory", {"min": 0.10, "max": 0.90})
    gov_b = rb.get("governance", {"min": 0.12, "max": 0.90})

    risk_fast = _lerp_unit(raw[1], float(fast_b.get("min", 0.15)), float(fast_b.get("max", 0.90)))
    risk_memory = _lerp_unit(raw[2], float(mem_b.get("min", 0.10)), float(mem_b.get("max", 0.90)))
    risk_governance = _lerp_unit(raw[3], float(gov_b.get("min", 0.12)), float(gov_b.get("max", 0.90)))

    duration_cfg = profile.get("mission_duration", {"min": 6, "max": 15})
    dmin = int(duration_cfg.get("min", 6))
    dmax = int(duration_cfg.get("max", 15))
    if dmax < dmin:
        dmax = dmin
    duration_ticks = dmin + (raw[4] % (dmax - dmin + 1))

    def _coord(idx: int) -> float:
        target_bounds = profile.get("target_bounds", {"min": -2.6, "max": 2.6})
        lo = float(target_bounds.get("min", -2.6))
        hi = float(target_bounds.get("max", 2.6))
        return _lerp_unit(raw[idx], lo, hi)

    target = Point3(_coord(5), _coord(6), _coord(7))
    mission_id = f"m-{tick:03d}-{raw[:3].hex()}"
    regions = tuple(profile.get("regions", ("Polly Bazaar",)))
    factions = tuple(profile.get("factions", ("Order of Polly",)))
    region = regions[raw[10] % len(regions)] if regions else "Polly Bazaar"
    faction = factions[raw[11] % len(factions)] if factions else "Order of Polly"
    reward_cfg = profile.get("reward_bounds", {})
    trust_cfg = reward_cfg.get("trust", {"min": 0.01, "max": 0.07})
    coh_cfg = reward_cfg.get("coherence", {"min": 0.01, "max": 0.07})
    reward_trust = _lerp_unit(raw[8], float(trust_cfg.get("min", 0.01)), float(trust_cfg.get("max", 0.07)))
    reward_coherence = _lerp_unit(raw[9], float(coh_cfg.get("min", 0.01)), float(coh_cfg.get("max", 0.07)))
    return Mission(
        mission_id=mission_id,
        archetype=archetype,
        region=region,
        faction=faction,
        duration_ticks=duration_ticks,
        risk_fast=round(risk_fast, 6),
        risk_memory=round(risk_memory, 6),
        risk_governance=round(risk_governance, 6),
        target=target,
        reward_trust=round(reward_trust, 6),
        reward_coherence=round(reward_coherence, 6),
    )


def spectral_score(
    state: PlayerState,
    pad: PadMode,
    tongue: Tongue,
    mission: Mission,
) -> float:
    tongue_level = state.tongue_levels[tongue]
    pad_level = state.pad_levels[pad]
    tongue_bonus = PAD_TONGUE_BONUS.get(pad, {}).get(tongue, 0.0)
    lws_bonus = (LWS_WEIGHTS[tongue] - 1.0) / 0.667
    risk_drag = (mission.risk_fast + mission.risk_memory + mission.risk_governance) / 3.0

    score = (
        0.40
        + 0.35 * state.coherence
        + 0.08 * min(1.0, tongue_level / 10.0)
        + 0.08 * min(1.0, pad_level / 10.0)
        + 0.06 * tongue_bonus
        + 0.05 * _clamp01(lws_bonus)
        - 0.10 * risk_drag
    )
    return _clamp01(score)


def encode_voxel_keys(
    state: PlayerState,
    d: float,
    h_eff: float,
    tongue_levels: Dict[Tongue, int],
    bins: int = 36,
) -> tuple[str, Dict[Tongue, str], int]:
    x = quantize_floor(state.position.x, -3.0, 3.0, bins)
    y = quantize_floor(state.position.y, -3.0, 3.0, bins)
    z = quantize_floor(state.position.z, -3.0, 3.0, bins)
    v = quantize_floor((state.coherence * 2.0) - 1.0, -1.0, 1.0, bins)
    p = quantize_floor(d, 0.0, 6.0, bins)
    s = quantize_floor(min(math.log1p(h_eff), 6.0), 0.0, 6.0, bins)

    base_key = f"base/{x:02d}:{y:02d}:{z:02d}:{v:02d}:{p:02d}:{s:02d}"

    per_lang: Dict[Tongue, str] = {}
    for tongue in TONGUES:
        pl = quantize_floor(min(10.0, float(tongue_levels[tongue])), 0.0, 10.0, bins)
        per_lang[tongue] = f"{tongue}/{x:02d}:{y:02d}:{z:02d}:{v:02d}:{pl:02d}:{s:02d}"

    shard = int(hashlib.sha256(base_key.encode("utf-8")).hexdigest(), 16) % 64
    return base_key, per_lang, shard


def _decision_confidence(action: Action, omega: float) -> float:
    if action == "ALLOW":
        return _clamp01((omega - 0.70) / 0.30)
    if action == "QUARANTINE":
        return _clamp01(1.0 - abs(omega - 0.55) / 0.25)
    return _clamp01((0.45 - omega) / 0.45)


def _next_position(cur: Point3, target: Point3, action: Action, mission: Mission) -> Point3:
    step = 0.20 if action == "ALLOW" else 0.10 if action == "QUARANTINE" else 0.05
    dx = target.x - cur.x
    dy = target.y - cur.y
    dz = target.z - cur.z

    risk_push = (mission.risk_fast - 0.5) * 0.05
    nx = cur.x + (step * dx) + risk_push
    ny = cur.y + (step * dy) - (risk_push * 0.6)
    nz = cur.z + (step * dz) + (risk_push * 0.3)

    return Point3(
        _clamp(nx, -2.9, 2.9),
        _clamp(ny, -2.9, 2.9),
        _clamp(nz, -2.9, 2.9),
    )


def simulate_tick(
    state: PlayerState,
    mission: Mission,
    *,
    pad: PadMode,
    tongue: Tongue,
    action_intensity: float,
    safe_center: Point3 = Point3(0.0, 0.0, 0.0),
) -> Dict[str, Any]:
    d = poincare_dist_3d(state.position, safe_center)

    intent_increment = action_intensity * (
        0.45 + mission.risk_fast * 0.35 + mission.risk_memory * 0.25
    )
    state.accumulated_intent = _clamp(state.accumulated_intent * 0.92 + intent_increment, 0.0, 12.0)

    x = compute_x_factor(state.accumulated_intent, state.trust)
    h_eff = runtime_wall_cost(d, x, base_r=1.5)
    harm = harm_score_from_wall(h_eff)

    d_tri = triadic_risk(mission.risk_fast, mission.risk_memory, mission.risk_governance)
    triadic_stable = _clamp01(1.0 / (1.0 + d_tri))
    drift_factor = _clamp01(math.exp(-0.35 * d))

    spectral = spectral_score(state, pad, tongue, mission)
    local_sections = {
        "fast": mission.risk_fast,
        "memory": mission.risk_memory,
        "governance": mission.risk_governance,
        "spectral": spectral,
    }
    fixed_sections = tarski_postfixpoint(local_sections)
    obstruction = sheaf_obstruction(local_sections)
    sheaf_stability = sheaf_stability_from_obstruction(obstruction)

    pqc_valid = _clamp01(
        0.60
        + (0.20 if state.inventory.get("sacred_eggs", 0) > 0 else 0.0)
        + (0.20 if state.inventory.get("consensus_seal", 0) > 0 else 0.0)
    )

    omega = omega_gate(
        pqc_valid=pqc_valid,
        harm_score=harm,
        drift_factor=drift_factor,
        triadic_stable=triadic_stable,
        spectral_score=spectral,
        sheaf_stability=sheaf_stability,
    )
    heat = _heat_from_distance(d)
    wall_pressure = _clamp01(math.log1p(h_eff) / 6.0)

    if omega >= 0.70:
        action: Action = "ALLOW"
        reason = "all five locks stable"
    elif omega >= 0.45:
        action = "QUARANTINE"
        reason = "partial lock instability"
    else:
        action = "DENY"
        reason = "gate lock failure"

    exile_triggered = action == "DENY" and omega < 0.22 and state.trust < 0.35

    if action == "ALLOW":
        state.trust = _clamp(state.trust + mission.reward_trust, 0.0, 1.0)
        state.coherence = _clamp(state.coherence + mission.reward_coherence, 0.0, 1.0)
        state.trust_xp += 4.0
        state.coherence_xp += 4.0
        state.tongue_levels[tongue] = min(10, state.tongue_levels[tongue] + 1)
        state.pad_levels[pad] = min(10, state.pad_levels[pad] + 1)
        if state.inventory.get("audit_proof", 0) >= 1 and state.inventory.get("consensus_seal", 0) == 0:
            state.inventory["consensus_seal"] = 1
    elif action == "QUARANTINE":
        state.trust = _clamp(state.trust - 0.02, 0.0, 1.0)
        state.coherence = _clamp(state.coherence - 0.01, 0.0, 1.0)
        state.trust_xp += 1.0
        state.coherence_xp += 1.0
        state.inventory["quarantine_resolver"] = state.inventory.get("quarantine_resolver", 0) + 1
    else:
        state.trust = _clamp(state.trust - 0.05, 0.0, 1.0)
        state.coherence = _clamp(state.coherence - 0.03, 0.0, 1.0)
        state.inventory["audit_proof"] = state.inventory.get("audit_proof", 0) + 1

    if exile_triggered:
        state.inventory["sacred_eggs"] = max(0, state.inventory.get("sacred_eggs", 0) - 1)
        state.trust = _clamp(state.trust * 0.8, 0.0, 1.0)
        state.coherence = _clamp(state.coherence * 0.85, 0.0, 1.0)
        reason = "deny path crossed exile envelope"

    state.position = _next_position(state.position, mission.target, action, mission)

    d_star = max(0.0, math.sqrt(state.position.x**2 + state.position.y**2 + state.position.z**2))
    canonical_cost = canonical_wall_cost(d_star, realm_scale=1.0)

    base_key, per_lang, shard = encode_voxel_keys(state, d=d, h_eff=h_eff, tongue_levels=state.tongue_levels)

    state_vector = {
        "position": {
            "x": round(state.position.x, 6),
            "y": round(state.position.y, 6),
            "z": round(state.position.z, 6),
        },
        "trust": round(state.trust, 6),
        "coherence": round(state.coherence, 6),
        "d_star": round(d_star, 6),
        "hyperbolic_distance": round(d, 6),
        "intent_x": round(x, 6),
        "H_eff": round(h_eff, 6),
        "harm": round(harm, 6),
        "canonical_wall_cost": round(canonical_cost, 6),
        "d_tri": round(d_tri, 6),
        "sheaf_obstruction": round(obstruction, 6),
        "sheaf_stability": round(sheaf_stability, 6),
        "tarski_fixed_sections": {k: round(v, 6) for k, v in fixed_sections.items()},
        "Omega": round(omega, 6),
        "hud": {
            "poincare_heat": round(heat, 6),
            "wall_pressure": round(wall_pressure, 6),
            "watcher_rings": {
                "fast": round(mission.risk_fast, 6),
                "memory": round(mission.risk_memory, 6),
                "governance": round(mission.risk_governance, 6),
                "triadic": round(d_tri, 6),
            },
            "gate_locks": {
                "pqc_valid": round(pqc_valid, 6),
                "harm": round(harm, 6),
                "drift_factor": round(drift_factor, 6),
                "triadic_stable": round(triadic_stable, 6),
                "spectral_score": round(spectral, 6),
                "sheaf_stability": round(sheaf_stability, 6),
            },
        },
        "voxel_base_key": base_key,
        "voxel_shard": shard,
        "xp": {
            "trust_xp": round(state.trust_xp, 4),
            "coherence_xp": round(state.coherence_xp, 4),
        },
        "inventory": dict(state.inventory),
    }

    signature_payload = {
        "mission_id": mission.mission_id,
        "action": action,
        "omega": round(omega, 6),
        "voxel": base_key,
        "sheaf_obstruction": round(obstruction, 6),
    }
    signature = hashlib.sha256(
        json.dumps(signature_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    decision_record = {
        "action": action,
        "signature": signature,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "confidence": round(_decision_confidence(action, omega), 6),
    }

    return {
        "mission": {
            "mission_id": mission.mission_id,
            "archetype": mission.archetype,
            "region": mission.region,
            "faction": mission.faction,
            "duration_ticks": mission.duration_ticks,
            "risk": {
                "fast": mission.risk_fast,
                "memory": mission.risk_memory,
                "governance": mission.risk_governance,
            },
            "target": asdict(mission.target),
        },
        "StateVector": state_vector,
        "DecisionRecord": decision_record,
        "voxel_keys_per_lang": per_lang,
        "exile_triggered": exile_triggered,
    }


def run_simulation(
    seed: str,
    ticks: int,
    *,
    pad: PadMode,
    tongue: Tongue,
    action_intensity: float,
    world_profile_path: str | None = None,
) -> Dict[str, Any]:
    world = load_world_profile(world_profile_path)
    safe_center_cfg = world.get("safe_center", {"x": 0.0, "y": 0.0, "z": 0.0})
    safe_center = Point3(
        float(safe_center_cfg.get("x", 0.0)),
        float(safe_center_cfg.get("y", 0.0)),
        float(safe_center_cfg.get("z", 0.0)),
    )

    state = PlayerState()
    history: list[Dict[str, Any]] = []

    for tick in range(ticks):
        mission = generate_mission(seed, tick, world_profile=world)
        tick_out = simulate_tick(
            state,
            mission,
            pad=pad,
            tongue=tongue,
            action_intensity=action_intensity,
            safe_center=safe_center,
        )
        history.append({"tick": tick, **tick_out})

    return {
        "seed": seed,
        "world_id": world.get("world_id", "aethermoor"),
        "world_display_name": world.get("display_name", "Aethermoor"),
        "ticks": ticks,
        "pad": pad,
        "tongue": tongue,
        "history": history,
        "final_state": {
            "position": asdict(state.position),
            "trust": round(state.trust, 6),
            "coherence": round(state.coherence, 6),
            "accumulated_intent": round(state.accumulated_intent, 6),
            "tongue_levels": dict(state.tongue_levels),
            "pad_levels": dict(state.pad_levels),
            "inventory": dict(state.inventory),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Spiral Engine simulator")
    parser.add_argument("--seed", default="aethermoor-mvp")
    parser.add_argument("--ticks", type=int, default=8)
    parser.add_argument("--pad", choices=list(PADS), default="ENGINEERING")
    parser.add_argument("--tongue", choices=list(TONGUES), default="KO")
    parser.add_argument("--action-intensity", type=float, default=0.65)
    parser.add_argument("--world-profile", default=str(DEFAULT_WORLD_PROFILE_PATH))
    parser.add_argument("--output", default="artifacts/spiral_engine_run.json")
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = run_simulation(
        seed=args.seed,
        ticks=max(1, args.ticks),
        pad=args.pad,
        tongue=args.tongue,
        action_intensity=_clamp(args.action_intensity, 0.0, 2.0),
        world_profile_path=args.world_profile,
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if args.pretty:
        out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    else:
        out_path.write_text(json.dumps(output, separators=(",", ":")), encoding="utf-8")

    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

