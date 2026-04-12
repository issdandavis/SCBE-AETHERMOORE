"""Tests for tongue_prosody.py — 6-tongue → 5-voice parameter mapper.

Self-contained: no heavy imports.
"""

import math
from dataclasses import dataclass
from typing import Dict

# ---------------------------------------------------------------------------
# Inline module under test
# ---------------------------------------------------------------------------

PHI = 1.618033988749895

TONGUE_WEIGHTS: Dict[str, float] = {
    "ko": 1.000,
    "av": 1.618,
    "ru": 2.618,
    "ca": 4.236,
    "um": 6.854,
    "dr": 11.090,
}

DECISION_VOICE_MAP: Dict[str, str] = {
    "ALLOW": "alexander_thorne",
    "QUARANTINE": "senna",
    "ESCALATE": "polly",
    "DENY": "bram",
}


@dataclass(frozen=True)
class TongueWeightVector:
    ko: float
    av: float
    ru: float
    ca: float
    um: float
    dr: float

    def as_dict(self) -> Dict[str, float]:
        return {"ko": self.ko, "av": self.av, "ru": self.ru, "ca": self.ca, "um": self.um, "dr": self.dr}

    def norm(self) -> float:
        vals = [self.ko, self.av, self.ru, self.ca, self.um, self.dr]
        return math.sqrt(sum(v * v for v in vals))


@dataclass(frozen=True)
class ProsodyParams:
    speed: float
    pitch_semitones: float
    warmth: float
    breathiness: float
    cadence: str


def tongue_to_prosody(weights, base_speed=1.0, base_pitch=0.0):
    eps = 1e-9
    speed = base_speed * (1.0 + 0.1 * (weights.ko - weights.um))
    speed = max(0.5, min(2.0, speed))
    pitch = base_pitch + weights.ca * 2.0 - weights.dr
    pitch = max(-12.0, min(12.0, pitch))
    warmth = weights.av / (weights.av + weights.ru + eps)
    warmth = max(0.0, min(1.0, warmth))
    breathiness = weights.um * 0.3
    breathiness = max(0.0, min(1.0, breathiness))
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
    return ProsodyParams(speed=speed, pitch_semitones=pitch, warmth=warmth, breathiness=breathiness, cadence=cadence)


def governance_voice(decision):
    return DECISION_VOICE_MAP.get(decision, "narrator")


def tongue_dominant(weights):
    d = weights.as_dict()
    return max(d, key=d.get)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTongueToProsody:

    def test_default_weights_produce_valid_output(self):
        w = TongueWeightVector(ko=1.0, av=1.618, ru=2.618, ca=4.236, um=6.854, dr=11.090)
        p = tongue_to_prosody(w)
        assert 0.5 <= p.speed <= 2.0
        assert 0.0 <= p.warmth <= 1.0
        assert 0.0 <= p.breathiness <= 1.0
        assert p.cadence in ("staccato", "flowing", "measured", "grounded", "steady")

    def test_high_ko_gives_staccato(self):
        w = TongueWeightVector(ko=0.9, av=0.1, ru=0.1, ca=0.1, um=0.1, dr=0.1)
        p = tongue_to_prosody(w)
        assert p.cadence == "staccato"

    def test_high_av_gives_flowing(self):
        w = TongueWeightVector(ko=0.1, av=0.8, ru=0.1, ca=0.1, um=0.1, dr=0.1)
        p = tongue_to_prosody(w)
        assert p.cadence == "flowing"

    def test_high_ru_gives_measured(self):
        w = TongueWeightVector(ko=0.1, av=0.1, ru=0.8, ca=0.1, um=0.1, dr=0.1)
        p = tongue_to_prosody(w)
        assert p.cadence == "measured"

    def test_high_dr_gives_grounded(self):
        w = TongueWeightVector(ko=0.1, av=0.1, ru=0.1, ca=0.1, um=0.1, dr=0.8)
        p = tongue_to_prosody(w)
        assert p.cadence == "grounded"

    def test_equal_weights_gives_steady(self):
        w = TongueWeightVector(ko=0.3, av=0.3, ru=0.3, ca=0.3, um=0.3, dr=0.3)
        p = tongue_to_prosody(w)
        assert p.cadence == "steady"

    def test_speed_increases_when_ko_higher_than_um(self):
        w_fast = TongueWeightVector(ko=1.0, av=0.5, ru=0.5, ca=0.5, um=0.0, dr=0.5)
        w_slow = TongueWeightVector(ko=0.0, av=0.5, ru=0.5, ca=0.5, um=1.0, dr=0.5)
        assert tongue_to_prosody(w_fast).speed > tongue_to_prosody(w_slow).speed

    def test_warmth_dominated_by_av_over_ru(self):
        w_warm = TongueWeightVector(ko=0.5, av=1.0, ru=0.1, ca=0.5, um=0.5, dr=0.5)
        w_cold = TongueWeightVector(ko=0.5, av=0.1, ru=1.0, ca=0.5, um=0.5, dr=0.5)
        assert tongue_to_prosody(w_warm).warmth > tongue_to_prosody(w_cold).warmth

    def test_breathiness_scales_with_um(self):
        w_lo = TongueWeightVector(ko=0.5, av=0.5, ru=0.5, ca=0.5, um=0.1, dr=0.5)
        w_hi = TongueWeightVector(ko=0.5, av=0.5, ru=0.5, ca=0.5, um=1.0, dr=0.5)
        assert tongue_to_prosody(w_hi).breathiness > tongue_to_prosody(w_lo).breathiness

    def test_pitch_increases_with_ca_decreases_with_dr(self):
        w_high = TongueWeightVector(ko=0.5, av=0.5, ru=0.5, ca=5.0, um=0.5, dr=0.0)
        w_low = TongueWeightVector(ko=0.5, av=0.5, ru=0.5, ca=0.0, um=0.5, dr=5.0)
        assert tongue_to_prosody(w_high).pitch_semitones > tongue_to_prosody(w_low).pitch_semitones

    def test_speed_clamped(self):
        w = TongueWeightVector(ko=100.0, av=0.0, ru=0.0, ca=0.0, um=0.0, dr=0.0)
        assert tongue_to_prosody(w).speed <= 2.0

    def test_breathiness_clamped(self):
        w = TongueWeightVector(ko=0.0, av=0.0, ru=0.0, ca=0.0, um=10.0, dr=0.0)
        assert tongue_to_prosody(w).breathiness <= 1.0


class TestGovernanceVoice:

    def test_all_decisions_mapped(self):
        for d in ["ALLOW", "QUARANTINE", "ESCALATE", "DENY"]:
            assert governance_voice(d) != "narrator"

    def test_unknown_decision_gives_narrator(self):
        assert governance_voice("UNKNOWN") == "narrator"

    def test_allow_is_thorne(self):
        assert governance_voice("ALLOW") == "alexander_thorne"

    def test_deny_is_bram(self):
        assert governance_voice("DENY") == "bram"


class TestTongueDominant:

    def test_returns_max_weight(self):
        w = TongueWeightVector(ko=0.1, av=0.2, ru=0.3, ca=0.4, um=0.5, dr=0.6)
        assert tongue_dominant(w) == "dr"

    def test_ko_dominant(self):
        w = TongueWeightVector(ko=10.0, av=1.0, ru=1.0, ca=1.0, um=1.0, dr=1.0)
        assert tongue_dominant(w) == "ko"


class TestTongueWeightVector:

    def test_norm_positive(self):
        w = TongueWeightVector(ko=1.0, av=1.618, ru=2.618, ca=4.236, um=6.854, dr=11.090)
        assert w.norm() > 0

    def test_zero_norm(self):
        w = TongueWeightVector(ko=0, av=0, ru=0, ca=0, um=0, dr=0)
        assert w.norm() == 0.0

    def test_as_dict_keys(self):
        w = TongueWeightVector(ko=1, av=2, ru=3, ca=4, um=5, dr=6)
        assert set(w.as_dict().keys()) == {"ko", "av", "ru", "ca", "um", "dr"}
