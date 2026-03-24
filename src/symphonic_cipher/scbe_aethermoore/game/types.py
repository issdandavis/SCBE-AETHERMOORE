"""
Core types for Spiral Forge RPG — Python reference implementation.

Mirrors src/game/types.ts. All types grounded in SCBE 21D canonical state.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Tuple

# ---------------------------------------------------------------------------
#  Sacred Tongues
# ---------------------------------------------------------------------------

TongueCode = Literal["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_CODES: Tuple[TongueCode, ...] = ("KO", "AV", "RU", "CA", "UM", "DR")

PHI: float = (1 + math.sqrt(5)) / 2

TONGUE_WEIGHTS: Dict[TongueCode, float] = {
    "KO": 1.0,
    "AV": PHI,
    "RU": PHI**2,
    "CA": PHI**3,
    "UM": PHI**4,
    "DR": PHI**5,
}

TONGUE_NAMES: Dict[TongueCode, str] = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}

TONGUE_ROLES: Dict[TongueCode, str] = {
    "KO": "Command — initiative, force, origin",
    "AV": "Transport — movement, binding, flight",
    "RU": "Entropy — chaos, risk, connection",
    "CA": "Compute — analysis, encryption, logic",
    "UM": "Security — defense, erasure, wards",
    "DR": "Structure — authentication, verification, form",
}

# Hodge dual pairs: e_ij ∧ e_kl = e_1234
HODGE_DUAL_PAIRS: Tuple[Tuple[TongueCode, TongueCode], ...] = (
    ("KO", "DR"),
    ("AV", "UM"),
    ("RU", "CA"),
)

# ---------------------------------------------------------------------------
#  6D Tongue Vector
# ---------------------------------------------------------------------------

TongueVector = Tuple[float, float, float, float, float, float]


def zero_tongue_vector() -> TongueVector:
    return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def tongue_index(code: TongueCode) -> int:
    return TONGUE_CODES.index(code)


def dominant_tongue(v: TongueVector) -> TongueCode:
    max_idx = 0
    for i in range(1, 6):
        if v[i] > v[max_idx]:
            max_idx = i
    return TONGUE_CODES[max_idx]


def tongue_norm(v: TongueVector) -> float:
    return math.sqrt(sum(x * x for x in v))


def tongue_distance(a: TongueVector, b: TongueVector) -> float:
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(6)))


# ---------------------------------------------------------------------------
#  21D Canonical State Vector
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CanonicalState:
    """21D canonical state — Block A (tongue), Block B (phase), Block C (telemetry)."""

    tongue_position: TongueVector = field(default_factory=zero_tongue_vector)
    phase_angles: TongueVector = field(default_factory=zero_tongue_vector)
    flux: float = 0.5
    coherence_s: float = 0.5
    coherence_bi: float = 0.5
    coherence_tri: float = 0.5
    risk: float = 0.3
    entropy_rate: float = 0.1
    stabilization: float = 0.5
    radius: float = 0.1
    harmonic_energy: float = 0.0


def default_canonical_state() -> CanonicalState:
    return CanonicalState()


def state_to_array(s: CanonicalState) -> List[float]:
    return [
        *s.tongue_position,
        *s.phase_angles,
        s.flux,
        s.coherence_s,
        s.coherence_bi,
        s.coherence_tri,
        s.risk,
        s.entropy_rate,
        s.stabilization,
        s.radius,
        s.harmonic_energy,
    ]


def array_to_state(arr: List[float]) -> CanonicalState:
    if len(arr) != 21:
        raise ValueError(f"Expected 21 elements, got {len(arr)}")
    return CanonicalState(
        tongue_position=tuple(arr[0:6]),  # type: ignore[arg-type]
        phase_angles=tuple(arr[6:12]),  # type: ignore[arg-type]
        flux=arr[12],
        coherence_s=arr[13],
        coherence_bi=arr[14],
        coherence_tri=arr[15],
        risk=arr[16],
        entropy_rate=arr[17],
        stabilization=arr[18],
        radius=arr[19],
        harmonic_energy=arr[20],
    )


# ---------------------------------------------------------------------------
#  Risk / Governance
# ---------------------------------------------------------------------------

RiskDecision = Literal["ALLOW", "QUARANTINE", "ESCALATE", "DENY"]

# ---------------------------------------------------------------------------
#  Companion enums
# ---------------------------------------------------------------------------

DisciplineTrait = Literal["careful_verifier", "fast_heuristic", "collaborative", "solo", "risk_tolerant", "guardian"]

EmotionalState = Literal["content", "excited", "anxious", "determined", "exhausted", "corrupted", "transcendent"]

FormationRole = Literal["storm", "phalanx", "lance", "web"]

EvolutionStage = Literal["spark", "form", "prime", "apex", "transcendent"]

EVOLUTION_THRESHOLDS: Dict[EvolutionStage, float] = {
    "spark": 0.0,
    "form": 0.3,
    "prime": 0.5,
    "apex": 0.7,
    "transcendent": 0.85,
}

OVER_EVOLUTION_THRESHOLD: float = 0.95

# ---------------------------------------------------------------------------
#  Egg types
# ---------------------------------------------------------------------------

EggType = Literal[
    "mono_KO",
    "mono_AV",
    "mono_RU",
    "mono_CA",
    "mono_UM",
    "mono_DR",
    "hodge_eclipse",
    "hodge_storm",
    "hodge_paradox",
    "omni_prism",
]

BondType = Literal[
    "amplifier",
    "scout",
    "disruptor",
    "processor",
    "guardian",
    "architect",
    "harmonizer",
    "balancer",
    "synthesizer",
    "nexus",
]

# ---------------------------------------------------------------------------
#  Transform actions
# ---------------------------------------------------------------------------

TransformAction = Literal[
    "normalize",
    "substitute",
    "complete_square",
    "factor",
    "bound",
    "invariant_check",
    "case_split",
    "contradiction_probe",
    "differentiate",
    "integrate",
    "apply_theorem",
]

TRANSFORM_RISK: Dict[TransformAction, Literal["low", "medium", "high"]] = {
    "normalize": "low",
    "substitute": "medium",
    "complete_square": "low",
    "factor": "medium",
    "bound": "low",
    "invariant_check": "low",
    "case_split": "medium",
    "contradiction_probe": "high",
    "differentiate": "medium",
    "integrate": "high",
    "apply_theorem": "medium",
}

# ---------------------------------------------------------------------------
#  Synesthesia mapping
# ---------------------------------------------------------------------------

SYNESTHESIA_MAP: Dict[TongueCode, Dict[str, object]] = {
    "KO": {"hue": 0, "hex": "#DC3C3C", "note": "A", "freq": 220, "instrument": "brass"},
    "AV": {"hue": 60, "hex": "#DCB43C", "note": "B", "freq": 247, "instrument": "strings"},
    "RU": {"hue": 120, "hex": "#3CDC78", "note": "C#", "freq": 277, "instrument": "synth"},
    "CA": {"hue": 180, "hex": "#3CDCDC", "note": "D#", "freq": 311, "instrument": "piano"},
    "UM": {"hue": 240, "hex": "#3C3CDC", "note": "F", "freq": 349, "instrument": "choir"},
    "DR": {"hue": 300, "hex": "#DC3CDC", "note": "G", "freq": 392, "instrument": "harp"},
}
