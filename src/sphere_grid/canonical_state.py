"""
Canonical 21D State Vector for SCBE Sphere Grid.

Simplified from the full canonical_state.py for backend use.
Slots 0-5:   Tongue position (R^6) -- KO, AV, RU, CA, UM, DR
Slots 6-11:  Phase angles (R^6)
Slots 12-20: Telemetry -- flux, coh_s, coh_bi, coh_tri, risk, entropy, stab, radius, harm_energy
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np

PHI = 1.618033988749895
PI = math.pi

# Tongue indices
KO, AV, RU, CA, UM, DR = 0, 1, 2, 3, 4, 5

TONGUE_NAMES = {0: "KO", 1: "AV", 2: "RU", 3: "CA", 4: "UM", 5: "DR"}
TONGUE_PHASES = {0: 0.0, 1: PI / 3, 2: 2 * PI / 3, 3: PI, 4: 4 * PI / 3, 5: 5 * PI / 3}
TONGUE_WEIGHTS = {i: PHI**i for i in range(6)}  # phi-scaled weights

# Hodge dual pairs
HODGE_PAIRS = [(KO, DR), (AV, UM), (RU, CA)]

# Telemetry slot names
FLUX = 12
COHERENCE_S = 13
COHERENCE_BI = 14
COHERENCE_TRI = 15
RISK = 16
ENTROPY_RATE = 17
STABILIZATION = 18
RADIUS = 19
HARMONIC_ENERGY = 20

SLOT_MAP = {
    "ko": 0, "av": 1, "ru": 2, "ca": 3, "um": 4, "dr": 5,
    "flux": 12, "coherence_s": 13, "coherence_bi": 14,
    "coherence_tri": 15, "risk": 16, "entropy_rate": 17,
    "stabilization": 18, "radius": 19, "harmonic_energy": 20,
}


@dataclass(frozen=True)
class CanonicalState:
    """Immutable 21D state vector."""

    data: Tuple[float, ...] = field(default_factory=lambda: tuple([0.0] * 21))

    def __post_init__(self):
        if len(self.data) != 21:
            raise ValueError(f"State must be 21D, got {len(self.data)}")

    @property
    def tongue(self) -> np.ndarray:
        return np.array(self.data[0:6])

    @property
    def phase(self) -> np.ndarray:
        return np.array(self.data[6:12])

    @property
    def telemetry(self) -> np.ndarray:
        return np.array(self.data[12:21])

    @property
    def radius(self) -> float:
        return self.data[RADIUS]

    @property
    def risk(self) -> float:
        return self.data[RISK]

    @property
    def coherence(self) -> float:
        return self.data[COHERENCE_S]

    @property
    def dominant_tongue(self) -> int:
        return int(np.argmax(self.tongue))

    @property
    def dominant_tongue_name(self) -> str:
        return TONGUE_NAMES[self.dominant_tongue]

    def with_updates(self, **kwargs) -> "CanonicalState":
        """Return new state with updated slots."""
        d = list(self.data)
        for k, v in kwargs.items():
            if k in SLOT_MAP:
                d[SLOT_MAP[k]] = float(v)
            elif isinstance(k, int) and 0 <= k < 21:
                d[k] = float(v)
        return CanonicalState(data=tuple(d))

    def to_dict(self) -> Dict[str, float]:
        """Serialize to dict for JSON storage."""
        result = {}
        for name, idx in SLOT_MAP.items():
            result[name] = self.data[idx]
        for i in range(6, 12):
            result[f"phase_{i - 6}"] = self.data[i]
        return result

    @classmethod
    def from_dict(cls, d: Dict[str, float]) -> "CanonicalState":
        """Deserialize from dict."""
        data = [0.0] * 21
        for name, idx in SLOT_MAP.items():
            if name in d:
                data[idx] = d[name]
        for i in range(6):
            key = f"phase_{i}"
            if key in d:
                data[6 + i] = d[key]
        return cls(data=tuple(data))


def compute_ds_squared(s1: CanonicalState, s2: CanonicalState) -> Dict[str, float]:
    """
    Compute ds^2 between two canonical states.
    Block A (tongue): Euclidean
    Block B (phase): Circular distance
    Block C (telemetry): Weighted Euclidean with hyperbolic risk term
    """
    # Block A: tongue distance
    dt = s1.tongue - s2.tongue
    ds2_tongue = float(np.dot(dt, dt))

    # Block B: phase distance (circular)
    dp = s1.phase - s2.phase
    dp_wrapped = np.arctan2(np.sin(dp), np.cos(dp))
    ds2_phase = float(np.dot(dp_wrapped, dp_wrapped))

    # Block C: telemetry distance with risk weighting
    dc = s1.telemetry - s2.telemetry
    risk_avg = (s1.risk + s2.risk) / 2.0
    weight_c = np.ones(9)
    weight_c[4] = 1.0 + math.sinh(risk_avg)  # risk slot amplified
    ds2_telemetry = float(np.dot(dc * weight_c, dc))

    total = ds2_tongue + ds2_phase + ds2_telemetry
    return {
        "tongue": ds2_tongue,
        "phase": ds2_phase,
        "telemetry": ds2_telemetry,
        "total": total,
    }


def harmonic_wall_cost(d_star: float, R: float) -> float:
    """
    H(d*, R) = R * pi^(phi * d*)
    Layer 12 superexponential cost barrier.
    """
    return R * (PI ** (PHI * d_star))


def compute_rho_e(state: CanonicalState) -> float:
    """Entropy density rho_e from state. Used for Layer 12 gating."""
    entropy = state.data[ENTROPY_RATE]
    risk = state.data[RISK]
    stab = max(state.data[STABILIZATION], 0.01)
    return (entropy + risk) / stab


def governance_gate(state: CanonicalState, intent_tongue: int, threshold: float = 1.0) -> str:
    """
    Evaluate governance gate for a skill activation.
    Returns ALLOW, DENY, or QUARANTINE.
    """
    rho = compute_rho_e(state)
    tongue_strength = state.data[intent_tongue]
    coherence = state.coherence

    # Harmonic wall check
    d_star = state.radius
    R = rho
    wall_cost = harmonic_wall_cost(d_star, R)

    # ALLOW: low entropy density, strong tongue alignment, high coherence
    if rho < threshold and tongue_strength > 0.3 and coherence > 0.5:
        return "ALLOW"
    # QUARANTINE: high risk but potentially valid
    if state.risk > 0.7 or wall_cost > 1e6:
        return "QUARANTINE"
    # DENY: insufficient alignment
    return "DENY"


def make_creature_state(
    tongue_dominant: int,
    strength: float = 0.5,
    radius: float = 0.3,
    coherence: float = 0.8,
) -> CanonicalState:
    """Factory: create a creature state with one dominant tongue."""
    d = [0.0] * 21
    d[tongue_dominant] = strength
    for i in range(6):
        if i != tongue_dominant:
            d[i] = strength * 0.1
    for i in range(6, 12):
        d[i] = (i - 6) * PI / 3
    d[FLUX] = 0.5
    d[COHERENCE_S] = coherence
    d[COHERENCE_BI] = coherence * 0.9
    d[COHERENCE_TRI] = coherence * 0.8
    d[RISK] = 0.2
    d[ENTROPY_RATE] = 0.3
    d[STABILIZATION] = 0.7
    d[RADIUS] = radius
    d[HARMONIC_ENERGY] = radius**2 * 1e6
    return CanonicalState(data=tuple(d))


def make_player_state(tongue_xp: List[float] = None) -> CanonicalState:
    """Factory: create a player state from tongue experience vector."""
    if tongue_xp is None:
        tongue_xp = [0.1] * 6
    d = [0.0] * 21
    for i in range(6):
        d[i] = tongue_xp[i]
    for i in range(6, 12):
        d[i] = 0.0
    d[FLUX] = 1.0
    d[COHERENCE_S] = 0.9
    d[COHERENCE_BI] = 0.85
    d[COHERENCE_TRI] = 0.8
    d[RISK] = 0.1
    d[ENTROPY_RATE] = 0.2
    d[STABILIZATION] = 0.9
    d[RADIUS] = sum(tongue_xp) / 6.0
    d[HARMONIC_ENERGY] = d[RADIUS] ** 2 * 1e6
    return CanonicalState(data=tuple(d))


def make_skill_node_state(
    skill_name: str,
    phase: str,
    primary_tongue: int,
    difficulty: float = 0.5,
) -> CanonicalState:
    """
    Factory: create a state for a skill node on the sphere grid.
    Phase determines the layer range (SENSE=L1-4, PLAN=L5-8, etc.)
    """
    phase_radius = {
        "SENSE": 0.2,
        "PLAN": 0.4,
        "EXECUTE": 0.6,
        "PUBLISH": 0.8,
    }
    r = phase_radius.get(phase, 0.5)

    d = [0.0] * 21
    d[primary_tongue] = difficulty
    for i in range(6):
        if i != primary_tongue:
            d[i] = difficulty * 0.05
    # Phase angle from tongue assignment
    d[6 + primary_tongue] = TONGUE_PHASES[primary_tongue]
    # Telemetry
    d[FLUX] = 0.5
    d[COHERENCE_S] = 1.0 - difficulty * 0.3
    d[COHERENCE_BI] = d[COHERENCE_S] * 0.9
    d[COHERENCE_TRI] = d[COHERENCE_S] * 0.8
    d[RISK] = difficulty * 0.4
    d[ENTROPY_RATE] = difficulty * 0.3
    d[STABILIZATION] = 1.0 - difficulty * 0.2
    d[RADIUS] = r
    d[HARMONIC_ENERGY] = harmonic_wall_cost(r, compute_rho_e(CanonicalState(data=tuple(d))) if d[STABILIZATION] > 0 else 1.0)
    return CanonicalState(data=tuple(d))
