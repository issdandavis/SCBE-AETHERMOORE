"""
Harmonic Dark Fill — Sound Braid for Inactive Nodes
====================================================
Fills the "dark zones" of the tri-bundle with harmonic patterns.

When a tongue is NOT active at a given position, its SOUND braid
produces ambient harmonic structure instead of silence. This keeps
the full bundle coherent and provides the AI with perception channels
beyond human hearing range.

Three frequency bands:
    AUDIBLE (20 Hz - 20 kHz):   Human-perceptible. Training signal.
    INFRASONIC (0.01 - 20 Hz):  Slow state / long-memory patterns (IR band).
    ULTRASONIC (20 kHz - 1 MHz): Fast state / micro-structure (UV band).

The audible band carries musical intervals (Tymoczko voice leading).
The infra/ultra bands carry information only the AI can process —
temporal drift patterns and micro-structural hashing respectively.

Connection to IR/UV color spectrum theory:
    - Infrasonic = IR (slow state, long wavelength, deep memory)
    - Audible = Visible (the 6 Sacred Tongues' phi-weighted frequencies)
    - Ultrasonic = UV (fast state, short wavelength, rapid computation)

Musical intervals used (from real music theory):
    Unison       1:1     Identity
    Octave       2:1     Binary doubling
    Perfect 5th  3:2     phi approximation (R_harm default)
    Perfect 4th  4:3     Inverse fifth
    Major 3rd    5:4     Geometric mean step
    Minor 3rd    6:5     Complement
    Phi interval phi:1   The golden interval (unique to SCBE)

Tymoczko (2006, Science 313:72-74) proved that 3-voice counterpoint
lives in the orbifold T^3/S_3, where voice crossings correspond to
B3 braid group elements. The SOUND braid IS voice leading.

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import math
import hashlib
import struct
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2
PI = math.pi

# Tongue phi weights
TONGUE_WEIGHTS: Dict[str, float] = {
    "ko": PHI**0,  # 1.000
    "av": PHI**1,  # 1.618
    "ru": PHI**2,  # 2.618
    "ca": PHI**3,  # 4.236
    "um": PHI**4,  # 6.854
    "dr": PHI**5,  # 11.090
}

# Base audible frequencies per tongue (Hz) — musical notes
# These sit in the "visible" band of the harmonic spectrum
TONGUE_AUDIBLE_FREQ: Dict[str, float] = {
    "ko": 440.00,  # A4 — intent/flow
    "av": 523.25,  # C5 — wisdom/transport
    "ru": 293.66,  # D4 — binding/governance
    "ca": 659.25,  # E5 — compute/bitcraft
    "um": 196.00,  # G3 — security/veil
    "dr": 392.00,  # G4 — structure/forge
}

# Musical interval ratios (just intonation)
# Full chromatic set — phi-weighted tongue geometry naturally selects
# which intervals are reachable (harmonic selection rules).
INTERVALS = {
    "unison": 1.0,
    "minor_second": 16.0 / 15.0,  # ~1.067 — maximum dissonance
    "major_second": 9.0 / 8.0,  # ~1.125 — whole tone
    "minor_third": 6.0 / 5.0,  # ~1.200 — dark consonance
    "major_third": 5.0 / 4.0,  # ~1.250 — warm consonance
    "perfect_fourth": 4.0 / 3.0,  # ~1.333 — inverted fifth, tension
    "tritone": 45.0 / 32.0,  # ~1.406 — devil's interval
    "perfect_fifth": 3.0 / 2.0,  # ~1.500 — strongest consonance
    "minor_sixth": 8.0 / 5.0,  # ~1.600 — inverted major third
    "phi_interval": PHI,  # ~1.618 — golden ratio
    "major_sixth": 5.0 / 3.0,  # ~1.667 — inverted minor third
    "minor_seventh": 16.0 / 9.0,  # ~1.778 — dominant tension
    "major_seventh": 15.0 / 8.0,  # ~1.875 — leading tone
    "octave": 2.0,  # 2:1 — perfect doubling
}

# Frequency band boundaries
INFRA_MIN = 0.01  # 0.01 Hz — geological-scale rhythms
INFRA_MAX = 20.0  # 20 Hz — bottom of human hearing
AUDIBLE_MIN = 20.0
AUDIBLE_MAX = 20000.0
ULTRA_MIN = 20000.0
ULTRA_MAX = 1000000.0  # 1 MHz — micro-structural hashing

# Complementary tongue pairs for voice leading
# When a tongue is dark, its complement provides the fill
COMPLEMENT_MAP: Dict[str, str] = {
    "ko": "dr",  # intent ↔ structure
    "av": "um",  # wisdom ↔ security
    "ru": "ca",  # governance ↔ compute
    "ca": "ru",
    "um": "av",
    "dr": "ko",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HarmonicFill:
    """The harmonic fill for a single tongue at a single position.

    Contains three frequency bands: infra, audible, ultra.
    Each band has frequency, amplitude, and phase.
    """

    # Infrasonic band — slow state / long memory (IR)
    infra_freq: float  # Hz (0.01 - 20)
    infra_amplitude: float  # [0, 1]
    infra_phase: float  # radians [0, 2π)

    # Audible band — musical intervals (Visible)
    audible_freq: float  # Hz (20 - 20000)
    audible_amplitude: float
    audible_phase: float

    # Ultrasonic band — fast state / micro-structure (UV)
    ultra_freq: float  # Hz (20000 - 1000000)
    ultra_amplitude: float
    ultra_phase: float

    def as_tuple(self) -> Tuple[float, float, float, float, float, float, float, float, float]:
        return (
            self.infra_freq,
            self.infra_amplitude,
            self.infra_phase,
            self.audible_freq,
            self.audible_amplitude,
            self.audible_phase,
            self.ultra_freq,
            self.ultra_amplitude,
            self.ultra_phase,
        )

    def as_sound_strands(self) -> Tuple[
        Tuple[float, float, float],
        Tuple[float, float, float],
        Tuple[float, float, float],
    ]:
        """Pack into the tri-bundle's 3 sound strands:
        strand_a = audible (the human-perceptible core)
        strand_b = infrasonic (IR slow-state fill)
        strand_c = ultrasonic (UV fast-state fill)
        """
        return (
            (self.audible_freq, self.audible_amplitude, self.audible_phase),
            (self.infra_freq, self.infra_amplitude, self.infra_phase),
            (self.ultra_freq, self.ultra_amplitude, self.ultra_phase),
        )

    @property
    def total_energy(self) -> float:
        """Sum of squared amplitudes across all bands."""
        return self.infra_amplitude**2 + self.audible_amplitude**2 + self.ultra_amplitude**2

    @property
    def darkness(self) -> float:
        """How 'dark' is this fill? Inverse of audible amplitude.
        1.0 = completely dark (loud fill), 0.0 = fully lit (quiet fill).
        """
        return 1.0 - self.audible_amplitude


# ---------------------------------------------------------------------------
# Nodal surface from vacuum acoustics
# ---------------------------------------------------------------------------


def nodal_surface_value(x1: float, x2: float, n: float, m: float, L: float = 1.0) -> float:
    """N(x; n, m) = cos(nπx₁/L)cos(mπx₂/L) - cos(mπx₁/L)cos(nπx₂/L)

    Returns 0 at nodal lines (dark nodes).
    """
    term1 = math.cos(n * PI * x1 / L) * math.cos(m * PI * x2 / L)
    term2 = math.cos(m * PI * x1 / L) * math.cos(n * PI * x2 / L)
    return term1 - term2


# ---------------------------------------------------------------------------
# Voice leading intervals (Tymoczko counterpoint in B3)
# ---------------------------------------------------------------------------


def voice_leading_interval(
    from_tongue: str,
    to_tongue: str,
) -> float:
    """Compute the musical interval ratio between two tongues.

    Uses phi-weighted frequency ratios. When two tongues are adjacent
    in the phi hierarchy, their interval is close to a perfect fifth
    (3:2 ≈ phi - 0.118). This is not coincidental — phi IS the limit
    of the Fibonacci ratio, and the perfect fifth IS the most consonant
    interval after unison and octave.
    """
    f1 = TONGUE_AUDIBLE_FREQ[from_tongue]
    f2 = TONGUE_AUDIBLE_FREQ[to_tongue]
    ratio = f2 / f1 if f1 > 0 else 1.0
    # Normalize to one octave (1.0 to 2.0)
    while ratio < 1.0:
        ratio *= 2.0
    while ratio >= 2.0:
        ratio /= 2.0
    return ratio


def nearest_musical_interval(ratio: float) -> Tuple[str, float]:
    """Find the nearest named musical interval to a given ratio.

    Returns (interval_name, deviation).
    """
    best_name = "unison"
    best_dev = abs(ratio - 1.0)
    for name, ref in INTERVALS.items():
        dev = abs(ratio - ref)
        if dev < best_dev:
            best_dev = dev
            best_name = name
    return best_name, best_dev


# ---------------------------------------------------------------------------
# Dark node detection and harmonic fill computation
# ---------------------------------------------------------------------------


def compute_darkness(
    byte_val: int,
    tongue_code: str,
    activation_vector: Optional[Dict[str, float]] = None,
) -> float:
    """How dark is this tongue at this position?

    0.0 = fully active (no fill needed)
    1.0 = completely inactive (maximum fill)

    If activation_vector is provided, uses it directly.
    Otherwise, estimates from byte value and tongue weight.
    """
    if activation_vector is not None:
        act = activation_vector.get(tongue_code, 0.0)
        return max(0.0, min(1.0, 1.0 - act))

    # Estimate: higher-weight tongues activate at higher byte values
    weight = TONGUE_WEIGHTS[tongue_code]
    threshold = weight / (PHI**5) * 255  # normalized
    if byte_val >= threshold:
        return 0.0  # active
    return 1.0 - (byte_val / max(threshold, 1.0))


def compute_harmonic_fill(
    byte_val: int,
    tongue_code: str,
    position: int,
    total_positions: int,
    darkness: float,
    neighbor_phases: Optional[Dict[str, float]] = None,
) -> HarmonicFill:
    """Compute the full harmonic fill for a dark node.

    The fill has three bands:
        INFRASONIC — slow patterns from long-range context (IR band)
        AUDIBLE — musical intervals from voice leading (Visible band)
        ULTRASONIC — micro-structural hash patterns (UV band)

    The key principle: AMPLITUDE IS INVERSE OF ACTIVATION.
    The fill is LOUDEST where the tongue is DARKEST.
    Sound fills silence. Math fills absence.

    Args:
        byte_val: The data byte at this position.
        tongue_code: Which tongue to fill.
        position: Position in sequence.
        total_positions: Total sequence length.
        darkness: How dark this node is [0, 1].
        neighbor_phases: Phase angles from neighboring active tongues
            (for voice leading coherence).
    """
    weight = TONGUE_WEIGHTS[tongue_code]
    base_freq = TONGUE_AUDIBLE_FREQ[tongue_code]
    complement = COMPLEMENT_MAP[tongue_code]
    comp_freq = TONGUE_AUDIBLE_FREQ[complement]

    # Normalized position in sequence
    t = position / max(total_positions, 1)

    # --- INFRASONIC BAND (IR / slow state) ---
    # Frequency: phi-scaled subdivision of the audible base
    # Lower tongues → lower infrasonic (KO at 0.44 Hz, DR at 1.1 Hz)
    infra_freq = base_freq / 1000.0 * (1.0 + 0.5 * math.sin(2 * PI * t))
    infra_freq = max(INFRA_MIN, min(INFRA_MAX, infra_freq))

    # Amplitude: darkness-weighted (louder when darker)
    infra_amp = darkness * 0.8  # cap at 0.8 to leave headroom

    # Phase: derived from long-range position (slow drift)
    infra_phase = (2 * PI * t * PHI) % (2 * PI)

    # --- AUDIBLE BAND (Visible / musical intervals) ---
    # When a tongue is dark, the COMPLEMENT tongue provides the fill frequency
    # through the voice leading interval
    interval_ratio = voice_leading_interval(tongue_code, complement)
    audible_freq = base_freq * interval_ratio

    # Modulate by nodal surface — creates standing wave patterns
    tongue_idx = list(TONGUE_WEIGHTS.keys()).index(tongue_code)
    comp_idx = list(TONGUE_WEIGHTS.keys()).index(complement)
    nodal_val = nodal_surface_value(t, byte_val / 255.0, tongue_idx + 1, comp_idx + 1)
    audible_freq *= 1.0 + 0.1 * nodal_val
    audible_freq = max(AUDIBLE_MIN, min(AUDIBLE_MAX, audible_freq))

    # Amplitude: darkness-weighted, musical dynamics
    audible_amp = darkness * (0.6 + 0.4 * abs(nodal_val))

    # Phase: coherent with neighbors for voice leading
    if neighbor_phases and complement in neighbor_phases:
        # Lock phase to complement (counterpoint coherence)
        audible_phase = (neighbor_phases[complement] + PI * interval_ratio) % (2 * PI)
    else:
        audible_phase = (2 * PI * base_freq * position / 1000.0 + byte_val * PI / 128.0) % (2 * PI)

    # --- ULTRASONIC BAND (UV / fast state) ---
    # Frequency: hash-derived micro-structure
    # Each byte×tongue combo maps to a unique ultrasonic frequency
    h = hashlib.sha256(struct.pack(">BH", byte_val, tongue_idx) + tongue_code.encode())
    hash_val = int.from_bytes(h.digest()[:4], "big")
    ultra_freq = ULTRA_MIN + (hash_val / (2**32 - 1)) * (ULTRA_MAX - ULTRA_MIN)

    # Amplitude: darkness-weighted but with phi scaling
    # Higher-weight tongues produce louder ultrasonic (more computational resolution)
    ultra_amp = darkness * (weight / PHI**5) * 0.9

    # Phase: deterministic from hash (reproducible micro-structure)
    ultra_phase = (hash_val % 1000) / 1000.0 * 2 * PI

    return HarmonicFill(
        infra_freq=round(infra_freq, 6),
        infra_amplitude=round(infra_amp, 6),
        infra_phase=round(infra_phase, 6),
        audible_freq=round(audible_freq, 4),
        audible_amplitude=round(audible_amp, 6),
        audible_phase=round(audible_phase, 6),
        ultra_freq=round(ultra_freq, 2),
        ultra_amplitude=round(ultra_amp, 6),
        ultra_phase=round(ultra_phase, 6),
    )


# ---------------------------------------------------------------------------
# Full-sequence dark fill
# ---------------------------------------------------------------------------


def fill_dark_nodes(
    data: bytes,
    activations: Optional[List[Dict[str, float]]] = None,
) -> List[Dict[str, HarmonicFill]]:
    """Compute harmonic fills for all dark nodes in a byte sequence.

    For each position and each tongue, computes the fill.
    Active tongues get minimal fill; dark tongues get full harmonic projection.

    Args:
        data: Byte sequence.
        activations: Optional list of per-position activation dicts.
            If None, estimates activation from byte values.

    Returns:
        List of dicts mapping tongue_code → HarmonicFill per position.
    """
    total = len(data)
    fills: List[Dict[str, HarmonicFill]] = []

    for i, b in enumerate(data):
        position_fills: Dict[str, HarmonicFill] = {}
        act_dict = activations[i] if activations and i < len(activations) else None

        # First pass: compute phases for active tongues (neighbors)
        neighbor_phases: Dict[str, float] = {}
        for tc in TONGUE_WEIGHTS:
            dark = compute_darkness(b, tc, act_dict)
            if dark < 0.5:  # active enough to be a "neighbor"
                freq = TONGUE_AUDIBLE_FREQ[tc]
                neighbor_phases[tc] = (2 * PI * freq * i / 1000.0 + b * PI / 128.0) % (2 * PI)

        # Second pass: compute fills
        for tc in TONGUE_WEIGHTS:
            dark = compute_darkness(b, tc, act_dict)
            fill = compute_harmonic_fill(
                byte_val=b,
                tongue_code=tc,
                position=i,
                total_positions=total,
                darkness=dark,
                neighbor_phases=neighbor_phases,
            )
            position_fills[tc] = fill

        fills.append(position_fills)

    return fills


# ---------------------------------------------------------------------------
# Integration with tri_bundle.py: upgrade sound strands
# ---------------------------------------------------------------------------


def upgrade_sound_bundle(
    byte_val: int,
    tongue_code: str,
    position: int,
    total_positions: int,
    darkness: float,
    neighbor_phases: Optional[Dict[str, float]] = None,
) -> Tuple[
    Tuple[float, float, float],
    Tuple[float, float, float],
    Tuple[float, float, float],
]:
    """Compute the 3 sound strands for tri_bundle.InnerBundle.

    Returns (strand_a, strand_b, strand_c) ready to plug into
    the tri_bundle's sound InnerBundle.

    strand_a = audible (human-perceptible core)
    strand_b = infrasonic (IR slow-state — AI-only)
    strand_c = ultrasonic (UV fast-state — AI-only)
    """
    fill = compute_harmonic_fill(
        byte_val=byte_val,
        tongue_code=tongue_code,
        position=position,
        total_positions=total_positions,
        darkness=darkness,
        neighbor_phases=neighbor_phases,
    )
    return fill.as_sound_strands()


# ---------------------------------------------------------------------------
# Spectrum analysis: the full frequency landscape
# ---------------------------------------------------------------------------


@dataclass
class SpectrumSnapshot:
    """The full frequency landscape at a single position across all tongues."""

    position: int
    byte_val: int
    fills: Dict[str, HarmonicFill]

    @property
    def total_infra_energy(self) -> float:
        return sum(f.infra_amplitude**2 for f in self.fills.values())

    @property
    def total_audible_energy(self) -> float:
        return sum(f.audible_amplitude**2 for f in self.fills.values())

    @property
    def total_ultra_energy(self) -> float:
        return sum(f.ultra_amplitude**2 for f in self.fills.values())

    @property
    def ir_uv_ratio(self) -> float:
        """IR/UV energy ratio. >1 = slow-state dominant, <1 = fast-state dominant."""
        uv = self.total_ultra_energy
        return self.total_infra_energy / max(uv, 1e-12)

    @property
    def band_distribution(self) -> Dict[str, float]:
        """Energy distribution across the three bands."""
        total = self.total_infra_energy + self.total_audible_energy + self.total_ultra_energy
        if total < 1e-12:
            return {"infra": 0.0, "audible": 0.0, "ultra": 0.0}
        return {
            "infra": self.total_infra_energy / total,
            "audible": self.total_audible_energy / total,
            "ultra": self.total_ultra_energy / total,
        }

    def dark_tongues(self) -> List[str]:
        """Which tongues are dark (fill amplitude > 0.5)?"""
        return [tc for tc, f in self.fills.items() if f.darkness > 0.5]

    def active_tongues(self) -> List[str]:
        """Which tongues are active (fill amplitude < 0.5)?"""
        return [tc for tc, f in self.fills.items() if f.darkness <= 0.5]


def sequence_spectrum(data: bytes, activations: Optional[List[Dict[str, float]]] = None) -> List[SpectrumSnapshot]:
    """Compute the full frequency spectrum for a byte sequence."""
    fills = fill_dark_nodes(data, activations)
    return [SpectrumSnapshot(position=i, byte_val=b, fills=fills[i]) for i, b in enumerate(data)]
