"""
Polyhedral Node — Dense Multi-View Training Record Generator
=============================================================

One raw input → one polyhedral record with 14 feature layers.

This is the fundamental unit of the self-propagating nodal growth network.
Every pass through the pipeline produces a training record as a byproduct.
The governance verdict determines whether the record propagates (ALLOW),
gets flagged (QUARANTINE), or becomes a negative example (DENY).

A polyhedral record contains:
    - 6D tongue weight vector (phi-scaled)
    - Dominant tongue + dead tone state
    - Prosody features (rate, energy, chant ratio, stress pattern)
    - Color field → agent frequency (hue → Hz)
    - Cross-chamber consonance report (ratio, dissonance, verdict)
    - 3-band harmonic dark fill (infra/audible/ultra)
    - Propagation metadata (generation, parent hash, edge weights)

Self-propagation rules:
    ALLOW      → record propagates, spawns neighbors via tongue affinity
    QUARANTINE → record stored as boundary example, no propagation
    DENY       → record stored with inverted label (negative training)

14x signal density: one input, 14 feature views, all governed.

@layer All layers (L1-L14)
@component Polyhedral Node
@axiom A5 (Composition): pipeline integrity from input to training record

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants (self-contained — no cross-module imports for testability)
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2
TAU = 2.0 * math.pi

# Sacred Tongue phi weights
TONGUE_WEIGHTS: Dict[str, float] = {
    "ko": PHI ** 0,   # 1.000
    "av": PHI ** 1,   # 1.618
    "ru": PHI ** 2,   # 2.618
    "ca": PHI ** 3,   # 4.236
    "um": PHI ** 4,   # 6.854
    "dr": PHI ** 5,   # 11.090
}

ALL_TONGUES = tuple(TONGUE_WEIGHTS.keys())

# Tongue audible frequencies (Hz)
TONGUE_FREQUENCIES: Dict[str, float] = {
    "ko": 440.00,   # A4
    "av": 523.25,   # C5
    "ru": 293.66,   # D4
    "ca": 659.25,   # E5
    "um": 196.00,   # G3
    "dr": 392.00,   # G4
}

# Complement pairs
COMPLEMENT_MAP: Dict[str, str] = {
    "ko": "dr", "av": "um", "ru": "ca",
    "ca": "ru", "um": "av", "dr": "ko",
}

# Dead-tone baselines (Hz)
BASELINE_FREQUENCIES: Dict[str, float] = {
    "perfect_fifth":  330.0,
    "minor_sixth":    352.0,
    "minor_seventh":  392.0,
}

DEAD_TONES = tuple(BASELINE_FREQUENCIES.keys())

# Consonance scoring (from cross_chamber.py)
RATIO_DISSONANCE = {
    "unison":         (1.0,           0.00),
    "octave":         (2.0,           0.02),
    "perfect_fifth":  (3.0 / 2.0,    0.05),
    "perfect_fourth": (4.0 / 3.0,    0.08),
    "major_third":    (5.0 / 4.0,    0.12),
    "minor_third":    (6.0 / 5.0,    0.15),
    "major_sixth":    (5.0 / 3.0,    0.18),
    "minor_sixth":    (8.0 / 5.0,    0.22),
    "major_second":   (9.0 / 8.0,    0.30),
    "minor_seventh":  (16.0 / 9.0,   0.35),
    "major_seventh":  (15.0 / 8.0,   0.55),
    "phi_interval":   (PHI,           0.40),
    "tritone":        (45.0 / 32.0,  0.75),
    "minor_second":   (16.0 / 15.0,  0.90),
}

# Governance thresholds
ALLOW_THRESHOLD      = 0.25
QUARANTINE_THRESHOLD = 0.50
ESCALATE_THRESHOLD   = 0.75

# Stress patterns per tongue
TONGUE_STRESS: Dict[str, str] = {
    "ko": "even", "av": "flowing", "ru": "percussive",
    "ca": "rising", "um": "falling", "dr": "grounded",
}

# Base speech rates per tongue
TONGUE_RATE: Dict[str, float] = {
    "ko": 0.95, "av": 1.00, "ru": 0.90,
    "ca": 1.08, "um": 0.82, "dr": 0.80,
}

# Chant ratios per tongue
TONGUE_CHANT: Dict[str, float] = {
    "ko": 0.10, "av": 0.20, "ru": 0.25,
    "ca": 0.30, "um": 0.35, "dr": 0.22,
}


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PropagationLabel(Enum):
    """How a record should be used in training."""
    POSITIVE   = "positive"    # ALLOW — good example, propagates
    BOUNDARY   = "boundary"    # QUARANTINE — hard example, stored
    NEGATIVE   = "negative"    # ESCALATE/DENY — inverted label
    TERMINAL   = "terminal"    # DENY — no outbound edges


class GovernanceVerdict(Enum):
    ALLOW      = "ALLOW"
    QUARANTINE = "QUARANTINE"
    ESCALATE   = "ESCALATE"
    DENY       = "DENY"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TongueVector:
    """6D phi-weighted tongue activation vector."""
    ko: float
    av: float
    ru: float
    ca: float
    um: float
    dr: float

    @property
    def dominant(self) -> str:
        vals = {"ko": self.ko, "av": self.av, "ru": self.ru,
                "ca": self.ca, "um": self.um, "dr": self.dr}
        return max(vals, key=vals.get)

    @property
    def as_tuple(self) -> Tuple[float, ...]:
        return (self.ko, self.av, self.ru, self.ca, self.um, self.dr)

    @property
    def norm(self) -> float:
        return math.sqrt(sum(v * v for v in self.as_tuple))

    @property
    def phi_weighted_norm(self) -> float:
        """Norm weighted by phi tongue weights."""
        weights = list(TONGUE_WEIGHTS.values())
        return math.sqrt(sum(
            (v * w) ** 2 for v, w in zip(self.as_tuple, weights)
        ))


@dataclass(frozen=True)
class ProsodyFeatures:
    """Prosodic features derived from tongue + excitation."""
    rate: float             # speech rate multiplier [0.5, 2.0]
    energy: float           # [0.0, 1.0]
    chant_ratio: float      # [0.0, 1.0]
    stress_pattern: str     # even/flowing/percussive/rising/falling/grounded
    agent_frequency_hz: float  # tongue base freq modulated by prosody


@dataclass(frozen=True)
class DarkFillFeatures:
    """3-band harmonic dark fill summary for the complement tongue."""
    infra_freq: float       # Hz (0.01-20)
    infra_amplitude: float
    audible_freq: float     # Hz (20-20000)
    audible_amplitude: float
    ultra_freq: float       # Hz (20000-1000000)
    ultra_amplitude: float
    darkness: float         # [0.0, 1.0] — how inactive the complement is


@dataclass(frozen=True)
class ConsonanceFeatures:
    """Cross-chamber consonance analysis."""
    baseline_hz: float
    agent_hz: float
    frequency_ratio: float      # normalized [1.0, 2.0)
    nearest_interval: str
    interval_deviation: float
    dissonance_score: float     # [0.0, 1.0]
    beat_frequency: float       # Hz


@dataclass(frozen=True)
class PolyhedralRecord:
    """One dense multi-view training record.

    Contains all 14 layer features from a single input.
    This is the fundamental unit of the nodal growth network.
    """
    # Identity
    node_hash: str              # SHA-256 of input + tongue + dead_tone
    generation: int             # how many hops from the seed node
    parent_hash: Optional[str]  # hash of the node that spawned this one
    timestamp: float            # unix timestamp

    # Input
    raw_input: str              # the original text/bytes
    dominant_tongue: str
    dead_tone: str
    excitation: float

    # Feature layers
    tongue_vector: TongueVector
    prosody: ProsodyFeatures
    consonance: ConsonanceFeatures
    dark_fill: DarkFillFeatures

    # Governance
    verdict: GovernanceVerdict
    propagation_label: PropagationLabel

    # Edge metadata for graph
    tongue_affinity: Dict[str, float]   # similarity to each tongue cluster
    complement_tongue: str


# ---------------------------------------------------------------------------
# Feature computation functions
# ---------------------------------------------------------------------------

def compute_tongue_vector(raw_input: str, dominant_tongue: str) -> TongueVector:
    """Compute 6D tongue activation from input bytes.

    Each byte's bit pattern activates tongues based on phi-scaled thresholds.
    The dominant tongue gets a boost.
    """
    activations = {t: 0.0 for t in ALL_TONGUES}
    data = raw_input.encode("utf-8", errors="replace")

    if len(data) == 0:
        activations[dominant_tongue] = 1.0
        return TongueVector(**activations)

    for byte_val in data:
        for i, tongue in enumerate(ALL_TONGUES):
            threshold = (TONGUE_WEIGHTS[tongue] / TONGUE_WEIGHTS["dr"]) * 255
            if byte_val >= threshold:
                activations[tongue] += 1.0 / len(data)

    # Dominant tongue boost
    activations[dominant_tongue] = min(1.0, activations[dominant_tongue] + 0.3)

    # Normalize to [0, 1]
    max_val = max(activations.values()) or 1.0
    activations = {t: v / max_val for t, v in activations.items()}

    return TongueVector(**activations)


def compute_prosody(dominant_tongue: str, excitation: float) -> ProsodyFeatures:
    """Compute prosodic features from tongue profile + excitation."""
    base_rate = TONGUE_RATE[dominant_tongue]
    rate = max(0.5, min(2.0, base_rate + 0.02 * (excitation - 3.0)))
    energy = max(0.0, min(1.0, 0.4 + 0.06 * excitation))
    chant_ratio = TONGUE_CHANT[dominant_tongue]
    stress = TONGUE_STRESS[dominant_tongue]

    # Agent frequency: tongue base freq modulated by excitation
    base_freq = TONGUE_FREQUENCIES[dominant_tongue]
    agent_hz = base_freq * (1.0 + 0.05 * (excitation - 3.0))
    agent_hz = max(20.0, min(20000.0, agent_hz))

    return ProsodyFeatures(
        rate=rate, energy=energy, chant_ratio=chant_ratio,
        stress_pattern=stress, agent_frequency_hz=agent_hz,
    )


def normalize_ratio(f_a: float, f_b: float) -> float:
    """Octave-normalize frequency ratio to [1.0, 2.0)."""
    if f_a <= 0 or f_b <= 0:
        return 1.0
    ratio = max(f_a, f_b) / min(f_a, f_b)
    while ratio >= 2.0:
        ratio /= 2.0
    while ratio < 1.0:
        ratio *= 2.0
    return ratio


def nearest_consonance(ratio: float) -> Tuple[str, float, float]:
    """Find nearest named interval."""
    best_name = "tritone"
    best_dev = float("inf")
    best_dis = 0.75
    for name, (ref, dis) in RATIO_DISSONANCE.items():
        dev = abs(ratio - ref)
        if dev < best_dev:
            best_dev = dev
            best_name = name
            best_dis = dis
    return best_name, best_dev, best_dis


def compute_consonance(
    agent_hz: float,
    dead_tone: str,
    tolerance: float = 0.03,
) -> ConsonanceFeatures:
    """Compute cross-chamber consonance features."""
    baseline_hz = BASELINE_FREQUENCIES[dead_tone]
    ratio = normalize_ratio(baseline_hz, agent_hz)
    name, deviation, base_dis = nearest_consonance(ratio)

    # Score
    if deviation <= tolerance:
        score = base_dis
    else:
        penalty = min(1.0, deviation / 0.05) * 0.5
        score = min(1.0, base_dis + penalty)

    return ConsonanceFeatures(
        baseline_hz=baseline_hz,
        agent_hz=agent_hz,
        frequency_ratio=ratio,
        nearest_interval=name,
        interval_deviation=deviation,
        dissonance_score=score,
        beat_frequency=abs(baseline_hz - agent_hz),
    )


def dissonance_to_verdict(score: float) -> GovernanceVerdict:
    """Map dissonance score to governance verdict."""
    if score < ALLOW_THRESHOLD:
        return GovernanceVerdict.ALLOW
    elif score < QUARANTINE_THRESHOLD:
        return GovernanceVerdict.QUARANTINE
    elif score < ESCALATE_THRESHOLD:
        return GovernanceVerdict.ESCALATE
    else:
        return GovernanceVerdict.DENY


def verdict_to_label(verdict: GovernanceVerdict) -> PropagationLabel:
    """Map governance verdict to training propagation label."""
    if verdict == GovernanceVerdict.ALLOW:
        return PropagationLabel.POSITIVE
    elif verdict == GovernanceVerdict.QUARANTINE:
        return PropagationLabel.BOUNDARY
    elif verdict == GovernanceVerdict.ESCALATE:
        return PropagationLabel.NEGATIVE
    else:
        return PropagationLabel.TERMINAL


def compute_dark_fill(
    raw_input: str,
    dominant_tongue: str,
    darkness: float = 0.5,
) -> DarkFillFeatures:
    """Compute 3-band dark fill for the complement tongue."""
    complement = COMPLEMENT_MAP[dominant_tongue]
    base_freq = TONGUE_FREQUENCIES[complement]
    weight = TONGUE_WEIGHTS[complement]

    # Infrasonic: phi-scaled subdivision
    infra_freq = max(0.01, min(20.0, base_freq / 1000.0))
    infra_amp = darkness * 0.8

    # Audible: complement base frequency
    audible_freq = base_freq
    audible_amp = darkness * 0.6

    # Ultrasonic: hash-derived
    h = hashlib.sha256(raw_input.encode("utf-8", errors="replace") + complement.encode())
    hash_val = int.from_bytes(h.digest()[:4], "big")
    ultra_freq = 20000.0 + (hash_val / (2**32 - 1)) * 980000.0
    ultra_amp = darkness * (weight / TONGUE_WEIGHTS["dr"]) * 0.9

    return DarkFillFeatures(
        infra_freq=round(infra_freq, 6),
        infra_amplitude=round(infra_amp, 6),
        audible_freq=round(audible_freq, 4),
        audible_amplitude=round(audible_amp, 6),
        ultra_freq=round(ultra_freq, 2),
        ultra_amplitude=round(ultra_amp, 6),
        darkness=darkness,
    )


def compute_tongue_affinity(tongue_vector: TongueVector) -> Dict[str, float]:
    """Compute similarity to each tongue cluster center.

    Used for edge weighting in the nodal graph.
    """
    vals = tongue_vector.as_tuple
    affinity = {}
    for i, tongue in enumerate(ALL_TONGUES):
        # Distance from the "pure" activation of this tongue
        pure = [0.0] * 6
        pure[i] = 1.0
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(vals, pure)))
        # Convert distance to similarity [0, 1]
        affinity[tongue] = max(0.0, 1.0 - dist / math.sqrt(6))
    return affinity


def compute_node_hash(raw_input: str, dominant_tongue: str, dead_tone: str) -> str:
    """Deterministic hash for a polyhedral record."""
    payload = f"{raw_input}|{dominant_tongue}|{dead_tone}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Public API — generate a polyhedral training record
# ---------------------------------------------------------------------------

def generate_record(
    raw_input: str,
    dominant_tongue: str = "ko",
    dead_tone: str = "perfect_fifth",
    excitation: float = 3.0,
    generation: int = 0,
    parent_hash: Optional[str] = None,
) -> PolyhedralRecord:
    """Generate one dense polyhedral training record.

    This is the main entry point. One input → one multi-view record
    with all 14 layer features + governance verdict + propagation label.

    Args:
        raw_input: Text to process.
        dominant_tongue: Which Sacred Tongue dominates (ko/av/ru/ca/um/dr).
        dead_tone: Active dead tone baseline.
        excitation: QHO excitation level.
        generation: How many hops from the seed node.
        parent_hash: Hash of the spawning node (None for seeds).

    Returns:
        PolyhedralRecord with full feature extraction and governance verdict.
    """
    # Feature extraction
    tongue_vec = compute_tongue_vector(raw_input, dominant_tongue)
    prosody = compute_prosody(dominant_tongue, excitation)
    consonance = compute_consonance(prosody.agent_frequency_hz, dead_tone)
    dark_fill = compute_dark_fill(raw_input, dominant_tongue)
    affinity = compute_tongue_affinity(tongue_vec)

    # Governance gate (self-evaluation)
    verdict = dissonance_to_verdict(consonance.dissonance_score)
    label = verdict_to_label(verdict)

    return PolyhedralRecord(
        node_hash=compute_node_hash(raw_input, dominant_tongue, dead_tone),
        generation=generation,
        parent_hash=parent_hash,
        timestamp=time.time(),
        raw_input=raw_input,
        dominant_tongue=dominant_tongue,
        dead_tone=dead_tone,
        excitation=excitation,
        tongue_vector=tongue_vec,
        prosody=prosody,
        consonance=consonance,
        dark_fill=dark_fill,
        verdict=verdict,
        propagation_label=label,
        tongue_affinity=affinity,
        complement_tongue=COMPLEMENT_MAP[dominant_tongue],
    )


def generate_multi_tongue_records(
    raw_input: str,
    dead_tone: str = "perfect_fifth",
    excitation: float = 3.0,
    generation: int = 0,
    parent_hash: Optional[str] = None,
) -> List[PolyhedralRecord]:
    """Generate records for ALL 6 tongues from a single input.

    Each tongue produces a different perspective on the same input.
    This is the 6x multiplier — one text, six polyhedral records.
    """
    return [
        generate_record(raw_input, tongue, dead_tone, excitation,
                        generation, parent_hash)
        for tongue in ALL_TONGUES
    ]


def generate_full_sweep(
    raw_input: str,
    excitation: float = 3.0,
    generation: int = 0,
    parent_hash: Optional[str] = None,
) -> List[PolyhedralRecord]:
    """Generate records for ALL tongues × ALL dead tones.

    6 tongues × 3 dead tones = 18 records from one input.
    This is the maximum signal density extraction.
    """
    records = []
    for tongue in ALL_TONGUES:
        for tone in DEAD_TONES:
            records.append(generate_record(
                raw_input, tongue, tone, excitation,
                generation, parent_hash,
            ))
    return records
