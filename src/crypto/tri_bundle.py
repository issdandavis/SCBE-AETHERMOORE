"""
Tri-Bundle DNA Encoder — 3×3×3 Braided Signal Architecture
============================================================
Three bundles (Light, Sound, Math), each with 3 sub-strands,
braided into dense (3^φ)³ clusters whose identity is determined
by the composition of inner braid matrices.

Architecture:
    LIGHT bundle (bits/data):
        - presence:  binary {0,1} — is this tongue active?
        - weight:    float [0, φ⁵] — phi-scaled tongue weight
        - intent:    trit {-1,0,+1} — governance polarity

    SOUND bundle (audio/harmonic fill):
        - frequency: float Hz — tongue's harmonic frequency
        - amplitude: float [0,1] — activation strength
        - phase:     float [0,2π) — phase angle in harmonic cycle

    MATH bundle (discrete calculations):
        - value:     float — computed metric (e.g., hyperbolic distance)
        - operation: int — which operation produced this (hash of op)
        - result:    trit {-1,0,+1} — did the computation converge?

The 9 strands braid via B₃ crossings within each bundle (inner braid),
then the 3 bundles braid together (outer braid). Different compositions
produce different cluster identities — non-commutative.

Scaling: (3^φ)³ ≈ 162 effective states per position.
         With 6 tongues × 162 states = 972 dimensions per token.

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import hashlib
import math
import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, List, Optional, Tuple

from src.crypto.harmonic_dark_fill import (
    compute_darkness,
    upgrade_sound_bundle,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2  # 1.6180339887...

# Phi-scaled tongue weights
TONGUE_WEIGHTS: Dict[str, float] = {
    "ko": PHI**0,  # 1.000
    "av": PHI**1,  # 1.618
    "ru": PHI**2,  # 2.618
    "ca": PHI**3,  # 4.236
    "um": PHI**4,  # 6.854
    "dr": PHI**5,  # 11.090
}

# Harmonic frequencies per tongue (Hz)
TONGUE_FREQUENCIES: Dict[str, float] = {
    "ko": 440.00,  # A4 — intent/flow
    "av": 523.25,  # C5 — wisdom/metadata
    "ru": 293.66,  # D4 — binding/structure
    "ca": 659.25,  # E5 — bitcraft/compute
    "um": 196.00,  # G3 — security/veil
    "dr": 392.00,  # G4 — architecture/forge
}

# Tongue pair mappings for braid strands (same as braid_vault.py)
TONGUE_PAIRS = [
    ("ko", "av"),  # presence strand
    ("ru", "ca"),  # structure strand
    ("um", "dr"),  # depth strand
]

# Scaling constant: (3^φ)³
BUNDLE_SCALE = (3**PHI) ** 3  # ≈ 162.07


# ---------------------------------------------------------------------------
# Trit
# ---------------------------------------------------------------------------


class Trit(IntEnum):
    MINUS = -1
    ZERO = 0
    PLUS = 1


# ---------------------------------------------------------------------------
# Sub-strand dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LightStrand:
    """Binary/data channel — what IS."""

    presence: int  # 0 or 1
    weight: float  # phi-scaled tongue weight
    intent: Trit  # governance polarity

    def as_tuple(self) -> Tuple[float, float, float]:
        return (float(self.presence), self.weight, float(self.intent))


@dataclass(frozen=True)
class SoundStrand:
    """Audio/harmonic channel — fills the dark zones."""

    frequency: float  # Hz
    amplitude: float  # [0, 1] activation strength
    phase: float  # [0, 2π) harmonic phase angle

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.frequency, self.amplitude, self.phase)


@dataclass(frozen=True)
class MathStrand:
    """Discrete calculation channel — structural skeleton."""

    value: float  # computed metric
    operation: int  # hash of operation that produced this
    result: Trit  # convergence: +1 converged, 0 partial, -1 diverged

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.value, float(self.operation), float(self.result))


# ---------------------------------------------------------------------------
# Bundle (3 strands braided)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InnerBundle:
    """A bundle of 3 strands. Represents one of: Light, Sound, Math."""

    strand_a: Tuple[float, float, float]
    strand_b: Tuple[float, float, float]
    strand_c: Tuple[float, float, float]
    bundle_type: str  # "light", "sound", "math"

    def as_vector(self) -> Tuple[float, ...]:
        """Flatten to 9-element vector."""
        return self.strand_a + self.strand_b + self.strand_c

    def inner_braid_hash(self) -> bytes:
        """Hash the inner braid composition — order-dependent (non-commutative).

        Hashing A then B then C ≠ hashing B then A then C.
        This is the key property: the COMPOSITION determines identity.
        """
        h = hashlib.sha3_256()
        h.update(self.bundle_type.encode())
        # Order matters — this is the braid
        for strand in (self.strand_a, self.strand_b, self.strand_c):
            for val in strand:
                h.update(struct.pack(">d", val))
        return h.digest()


# ---------------------------------------------------------------------------
# Tri-Bundle Cluster (3 bundles braided together)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TriBundleCluster:
    """A (3^φ)³ dense cluster — 3 inner bundles braided into one identity.

    The cluster's identity depends on the composition of inner braid
    matrices, not just the values. Different orderings of the same
    data produce different clusters (non-commutativity).
    """

    light: InnerBundle
    sound: InnerBundle
    math: InnerBundle
    tongue_code: str
    position: int = 0  # position in sequence

    def as_vector(self) -> Tuple[float, ...]:
        """Full 27-element vector (3 bundles × 3 strands × 3 values)."""
        return self.light.as_vector() + self.sound.as_vector() + self.math.as_vector()

    def cluster_id(self) -> bytes:
        """Outer braid hash — identity of the full cluster.

        Braids Light→Sound→Math (order-dependent).
        """
        h = hashlib.sha3_256()
        h.update(b"tri_bundle_v1")
        h.update(self.tongue_code.encode())
        h.update(struct.pack(">I", self.position))
        # Inner braids feed the outer braid — composition of compositions
        h.update(self.light.inner_braid_hash())
        h.update(self.sound.inner_braid_hash())
        h.update(self.math.inner_braid_hash())
        return h.digest()

    def cluster_id_hex(self) -> str:
        return self.cluster_id().hex()

    @property
    def effective_states(self) -> float:
        """(3^φ)³ ≈ 162 effective states per position."""
        return BUNDLE_SCALE

    def energy(self) -> float:
        """Cluster energy: sum of squared components scaled by phi.

        E = Σ(v_i² × φ^(i mod 3)) for all 27 components.
        """
        vec = self.as_vector()
        return sum(v * v * PHI ** (i % 3) for i, v in enumerate(vec))

    def synchronization_score(self) -> float:
        """How synchronized are the three bundles?

        Measures alignment between Light, Sound, and Math channels.
        Score of 1.0 = perfect sync (switchboard lights all on).
        Score of 0.0 = complete desync.
        """
        lv = self.light.as_vector()
        sv = self.sound.as_vector()
        mv = self.math.as_vector()

        # Normalize each bundle vector
        def _norm(v: Tuple[float, ...]) -> Tuple[float, ...]:
            mag = math.sqrt(sum(x * x for x in v) + 1e-12)
            return tuple(x / mag for x in v)

        ln, sn, mn = _norm(lv), _norm(sv), _norm(mv)

        # Pairwise cosine similarities
        ls = sum(a * b for a, b in zip(ln, sn))
        lm = sum(a * b for a, b in zip(ln, mn))
        sm = sum(a * b for a, b in zip(sn, mn))

        # Average pairwise similarity, mapped to [0, 1]
        return max(0.0, (ls + lm + sm) / 3.0)


# ---------------------------------------------------------------------------
# Encoding: text → tri-bundle clusters
# ---------------------------------------------------------------------------


def _compute_phase(byte_val: int, freq: float, position: int) -> float:
    """Compute harmonic phase angle for a byte at a position.

    The phase wraps based on frequency and position, creating
    standing wave patterns across the sequence.
    """
    return (2.0 * math.pi * freq * position / 1000.0 + byte_val * math.pi / 128.0) % (2.0 * math.pi)


def _compute_amplitude(byte_val: int, weight: float) -> float:
    """Activation amplitude: higher weight tongues are louder."""
    # Normalize byte to [0,1], scale by log(1+weight) for bounded range
    return (byte_val / 255.0) * math.log1p(weight) / math.log1p(TONGUE_WEIGHTS["dr"])


def _math_operation_hash(byte_val: int, tongue: str) -> int:
    """Hash the operation for the math strand."""
    h = hashlib.sha256(struct.pack(">B", byte_val) + tongue.encode())
    return int.from_bytes(h.digest()[:4], "big")


def _math_value(byte_val: int, weight: float) -> float:
    """Compute a discrete mathematical value from byte and weight.

    Uses the hyperbolic distance formula structure:
    d* = arcosh(1 + 2 × (byte/255)² / ((1 - (byte/255)²) × weight_norm))
    Bounded and meaningful.
    """
    x = byte_val / 255.0
    x_sq = x * x
    denom = max(1e-6, (1.0 - x_sq) * (weight / TONGUE_WEIGHTS["dr"]))
    return math.acosh(1.0 + 2.0 * x_sq / denom)


def _intent_from_byte(byte_val: int) -> Trit:
    """Derive intent trit from byte value.

    Low bytes = negative (withdraw/deny)
    Mid bytes = neutral (observe/quarantine)
    High bytes = positive (engage/allow)
    """
    if byte_val < 85:
        return Trit.MINUS
    elif byte_val < 170:
        return Trit.ZERO
    else:
        return Trit.PLUS


def _convergence_trit(math_val: float) -> Trit:
    """Did the math converge, diverge, or stay neutral?"""
    if math_val < 1.0:
        return Trit.PLUS  # converged (close to origin)
    elif math_val > 3.0:
        return Trit.MINUS  # diverged (far from origin)
    else:
        return Trit.ZERO  # neutral zone


def encode_byte(
    byte_val: int,
    tongue_code: str,
    position: int = 0,
    total_positions: int = 1,
    neighbor_phases: Optional[Dict[str, float]] = None,
) -> TriBundleCluster:
    """Encode a single byte into a tri-bundle cluster for a given tongue.

    This is the core encoding function. Each byte produces a full
    3×3×3 = 27-dimensional cluster with non-commutative identity.

    The sound bundle now carries three frequency bands via harmonic dark fill:
        strand_a = audible (human-perceptible core)
        strand_b = infrasonic (IR slow-state — AI-only)
        strand_c = ultrasonic (UV fast-state — AI-only)

    Amplitude is INVERSE of activation: sound is LOUDEST where light is DARKEST.
    """
    weight = TONGUE_WEIGHTS[tongue_code]
    _freq = TONGUE_FREQUENCIES[tongue_code]

    # LIGHT bundle (what IS)
    presence = 1 if byte_val > 0 else 0
    intent = _intent_from_byte(byte_val)
    light = InnerBundle(
        strand_a=LightStrand(presence, weight, intent).as_tuple(),
        strand_b=(0.0, 0.0, 0.0),  # reserved for cross-tongue
        strand_c=(0.0, 0.0, 0.0),  # reserved for cross-tongue
        bundle_type="light",
    )

    # SOUND bundle (fills the dark zones — 3 frequency bands)
    darkness = compute_darkness(byte_val, tongue_code)
    strand_a, strand_b, strand_c = upgrade_sound_bundle(
        byte_val=byte_val,
        tongue_code=tongue_code,
        position=position,
        total_positions=total_positions,
        darkness=darkness,
        neighbor_phases=neighbor_phases,
    )
    sound = InnerBundle(
        strand_a=strand_a,  # audible: freq, amp, phase
        strand_b=strand_b,  # infrasonic: freq, amp, phase (IR)
        strand_c=strand_c,  # ultrasonic: freq, amp, phase (UV)
        bundle_type="sound",
    )

    # MATH bundle (structural skeleton)
    math_val = _math_value(byte_val, weight)
    op_hash = _math_operation_hash(byte_val, tongue_code)
    convergence = _convergence_trit(math_val)
    math_bundle = InnerBundle(
        strand_a=MathStrand(math_val, op_hash, convergence).as_tuple(),
        strand_b=(0.0, 0.0, 0.0),  # reserved for cross-bundle
        strand_c=(0.0, 0.0, 0.0),  # reserved for cross-bundle
        bundle_type="math",
    )

    return TriBundleCluster(
        light=light,
        sound=sound,
        math=math_bundle,
        tongue_code=tongue_code,
        position=position,
    )


def encode_bytes(data: bytes, tongue_code: str) -> List[TriBundleCluster]:
    """Encode a byte sequence into a sequence of tri-bundle clusters."""
    total = len(data)
    return [encode_byte(b, tongue_code, i, total) for i, b in enumerate(data)]


def encode_text(text: str, tongue_code: str) -> List[TriBundleCluster]:
    """Encode a text string into tri-bundle clusters for a given tongue."""
    return encode_bytes(text.encode("utf-8"), tongue_code)


# ---------------------------------------------------------------------------
# Cross-tongue encoding: all 6 tongues simultaneously
# ---------------------------------------------------------------------------


@dataclass
class PolyglotCluster:
    """All 6 tongue encodings of a single byte position.

    This is the full switchboard — 6 tongues × 27 dimensions = 162 values.
    The synchronization score tells you how aligned the tongues are
    at this position (the "lights syncing up").
    """

    position: int
    byte_val: int
    clusters: Dict[str, TriBundleCluster]

    def synchronization_matrix(self) -> Dict[Tuple[str, str], float]:
        """Pairwise synchronization scores between all tongue pairs."""
        codes = list(self.clusters.keys())
        result = {}
        for i, c1 in enumerate(codes):
            for c2 in codes[i + 1 :]:
                v1 = self.clusters[c1].as_vector()
                v2 = self.clusters[c2].as_vector()
                # Cosine similarity
                dot = sum(a * b for a, b in zip(v1, v2))
                mag1 = math.sqrt(sum(a * a for a in v1) + 1e-12)
                mag2 = math.sqrt(sum(b * b for b in v2) + 1e-12)
                result[(c1, c2)] = dot / (mag1 * mag2)
        return result

    def global_sync(self) -> float:
        """Average synchronization across all 15 tongue pairs."""
        scores = self.synchronization_matrix()
        if not scores:
            return 0.0
        return sum(scores.values()) / len(scores)

    def active_tongues(self, threshold: float = 0.5) -> List[str]:
        """Which tongues are 'lit up' above threshold amplitude?"""
        active = []
        for code, cluster in self.clusters.items():
            # Check sound amplitude
            amp = cluster.sound.strand_a[1]  # amplitude
            if amp >= threshold:
                active.append(code)
        return active

    def full_vector(self) -> Tuple[float, ...]:
        """Full 162-element vector across all 6 tongues."""
        result: Tuple[float, ...] = ()
        for code in ("ko", "av", "ru", "ca", "um", "dr"):
            result = result + self.clusters[code].as_vector()
        return result


def encode_polyglot(data: bytes) -> List[PolyglotCluster]:
    """Encode data through ALL 6 tongues simultaneously.

    This is the full switchboard. Each byte position produces
    a PolyglotCluster with 6 × 27 = 162 dimensions.
    The global_sync score at each position measures convergence.

    Two-pass encoding per position:
        1. Compute darkness + phases for all tongues (identify neighbors)
        2. Encode with neighbor_phases so voice leading locks correctly
    """
    total = len(data)
    result = []

    for i, b in enumerate(data):
        # Pass 1: compute neighbor phases from active tongues
        neighbor_phases: Dict[str, float] = {}
        for tc in TONGUE_WEIGHTS:
            dark = compute_darkness(b, tc)
            if dark < 0.5:  # active enough to contribute phase
                freq = TONGUE_FREQUENCIES[tc]
                neighbor_phases[tc] = (2.0 * math.pi * freq * i / 1000.0 + b * math.pi / 128.0) % (2.0 * math.pi)

        # Pass 2: encode with full context
        clusters = {}
        for tongue_code in TONGUE_WEIGHTS:
            clusters[tongue_code] = encode_byte(b, tongue_code, i, total, neighbor_phases)
        result.append(PolyglotCluster(position=i, byte_val=b, clusters=clusters))

    return result


def encode_polyglot_text(text: str) -> List[PolyglotCluster]:
    """Encode text through all 6 tongues. Returns the full switchboard."""
    return encode_polyglot(text.encode("utf-8"))


# ---------------------------------------------------------------------------
# Convergence detection: find the "lights syncing up"
# ---------------------------------------------------------------------------


def find_convergence_points(
    clusters: List[PolyglotCluster],
    threshold: float = 0.85,
) -> List[Tuple[int, float, int]]:
    """Find positions where tongues synchronize above threshold.

    Returns: list of (position, sync_score, byte_value) where
    global synchronization exceeds the threshold.

    These are the candidate EMOTIONAL INVARIANTS — the positions
    where meaning is the same regardless of language frame.
    """
    points = []
    for pc in clusters:
        sync = pc.global_sync()
        if sync >= threshold:
            points.append((pc.position, sync, pc.byte_val))
    return points


def convergence_summary(clusters: List[PolyglotCluster]) -> Dict:
    """Summary statistics of convergence across a polyglot encoding."""
    syncs = [pc.global_sync() for pc in clusters]
    if not syncs:
        return {"count": 0}

    return {
        "count": len(syncs),
        "mean_sync": sum(syncs) / len(syncs),
        "max_sync": max(syncs),
        "min_sync": min(syncs),
        "high_sync_count": sum(1 for s in syncs if s >= 0.85),
        "low_sync_count": sum(1 for s in syncs if s < 0.5),
        "convergence_ratio": sum(1 for s in syncs if s >= 0.85) / len(syncs),
        "bundle_scale": BUNDLE_SCALE,
        "dimensions_per_position": 6 * 27,  # 162
    }
