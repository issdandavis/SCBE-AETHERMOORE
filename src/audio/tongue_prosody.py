"""
Tongue Prosody — 6-Tongue → 5-Voice Parameter Mapper
=====================================================

The Intent Inflection Modulator: converts a Sacred Tongue weight vector
[KO, AV, RU, CA, UM, DR] into voice parameters (speed, pitch, warmth,
breathiness, cadence).

Each tongue controls a different axis of HOW the system speaks:
    KO (intent)       → drives pacing / speed
    AV (wisdom)       → drives warmth
    RU (governance)   → drives formality / energy
    CA (compute)      → drives pitch range
    UM (security)     → drives restraint / breathiness
    DR (architecture) → drives structure / cadence

The phi weights give the transform its natural scaling.

Integrates with:
    - scripts/audiobook/narrator_voice_system.py (VoiceProfile compat)
    - src/crypto/speech_render_plan.py (SpeechRenderPlan)
    - src/crypto/choral_render.py (ChoralRenderPlan)
    - packages/kernel/src/audioAxis.ts (L14 FFT telemetry)

@layer Layer 14 (Audio Axis)
@component Intent Inflection Modulator
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional

# ============================================================================
# Constants — phi-scaled tongue weights
# ============================================================================

PHI = 1.618033988749895

TONGUE_WEIGHTS: Dict[str, float] = {
    "ko": 1.000,
    "av": 1.618,
    "ru": 2.618,
    "ca": 4.236,
    "um": 6.854,
    "dr": 11.090,
}

# Governance decision → character voice mapping (from narrator_voice_system.py)
DECISION_VOICE_MAP: Dict[str, str] = {
    "ALLOW": "alexander_thorne",   # warm, unhurried
    "QUARANTINE": "senna",         # measured, precise
    "ESCALATE": "polly",           # sharp, no filler
    "DENY": "bram",                # blunt, short sentences
}


# ============================================================================
# Data Structures
# ============================================================================

@dataclass(frozen=True)
class TongueWeightVector:
    """A 6D weight vector, one per tongue."""

    ko: float
    av: float
    ru: float
    ca: float
    um: float
    dr: float

    def as_dict(self) -> Dict[str, float]:
        return {"ko": self.ko, "av": self.av, "ru": self.ru,
                "ca": self.ca, "um": self.um, "dr": self.dr}

    def norm(self) -> float:
        vals = [self.ko, self.av, self.ru, self.ca, self.um, self.dr]
        return math.sqrt(sum(v * v for v in vals))


@dataclass(frozen=True)
class ProsodyParams:
    """5D voice parameter output from the tongue-to-prosody mapper."""

    speed: float          # 0.5 - 2.0 (1.0 = normal)
    pitch_semitones: float  # relative pitch shift
    warmth: float         # 0.0 - 1.0
    breathiness: float    # 0.0 - 1.0
    cadence: str          # "staccato" | "flowing" | "steady" | "measured" | "grounded"

    def validate(self) -> None:
        assert 0.5 <= self.speed <= 2.0
        assert 0.0 <= self.warmth <= 1.0
        assert 0.0 <= self.breathiness <= 1.0
        assert self.cadence in ("staccato", "flowing", "steady", "measured", "grounded")


# ============================================================================
# Core Mapper: 6 tongues → 5 voice params
# ============================================================================

def tongue_to_prosody(
    weights: TongueWeightVector,
    base_speed: float = 1.0,
    base_pitch: float = 0.0,
) -> ProsodyParams:
    """Map a 6D tongue weight vector to 5 voice parameters.

    The transform:
        speed       = base_speed * (1 + 0.1 * (KO_weight - UM_weight))
        pitch       = base_pitch + CA_weight * 2 - DR_weight
        warmth      = AV_weight / (AV_weight + RU_weight + eps)
        breathiness = UM_weight * 0.3
        cadence     = derived from dominant tongue

    Args:
        weights: 6D tongue weight vector (normalized or raw).
        base_speed: baseline speech rate.
        base_pitch: baseline pitch in semitones.

    Returns:
        ProsodyParams with computed voice parameters.
    """
    eps = 1e-9

    speed = base_speed * (1.0 + 0.1 * (weights.ko - weights.um))
    speed = max(0.5, min(2.0, speed))

    pitch = base_pitch + weights.ca * 2.0 - weights.dr
    pitch = max(-12.0, min(12.0, pitch))

    warmth = weights.av / (weights.av + weights.ru + eps)
    warmth = max(0.0, min(1.0, warmth))

    breathiness = weights.um * 0.3
    breathiness = max(0.0, min(1.0, breathiness))

    # Cadence from dominant tongue
    if weights.ko > 0.7:
        cadence = "staccato"
    elif weights.av > 0.6:
        cadence = "flowing"
    elif weights.ru > 0.6:
        cadence = "measured"
    elif weights.dr > 0.5:
        cadence = "grounded"
    else:
        cadence = "steady"

    return ProsodyParams(
        speed=speed,
        pitch_semitones=pitch,
        warmth=warmth,
        breathiness=breathiness,
        cadence=cadence,
    )


def governance_voice(decision: str) -> str:
    """Map a governance decision tier to a character voice ID.

    ALLOW     → alexander_thorne (warm, unhurried)
    QUARANTINE → senna (measured, precise)
    ESCALATE  → polly (sharp, no filler)
    DENY      → bram (blunt, "no" as philosophy)
    """
    return DECISION_VOICE_MAP.get(decision, "narrator")


def tongue_dominant(weights: TongueWeightVector) -> str:
    """Return the tongue code with the highest weight."""
    d = weights.as_dict()
    return max(d, key=d.get)
