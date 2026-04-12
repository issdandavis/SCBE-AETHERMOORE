"""
Tri-Braid DNA Encoder (DEPRECATED — use src.crypto.tri_bundle instead)

Canonical implementation: src/crypto/tri_bundle.py (with harmonic_dark_fill.py)
This file was a first draft before tri_bundle.py was identified as canonical.

Three-braid signal architecture: LIGHT (bits) + SOUND (harmonics) + INTENT (trits).
Each braid has 3 sub-strands. 3x3x3 = 27 base states per codon position,
phi-scaled to (3^phi)^3 ~ 149 effective states per cluster.

The SOUND braid fills dark nodes — positions where tongues are NOT active —
with harmonic reinforcement patterns derived from musical scale projections
of discrete mathematical relationships.

@file tri_braid_dna.py
@module scbe_aethermoore/tri_braid_dna
@layer Layer 0-3 (LIGHT), Layer 9-10 (SOUND), Layer 12-13 (INTENT)
@version 1.0.0
"""

from __future__ import annotations

import math
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2  # 1.6180339...
PI = math.pi
EPS = 1e-12

# Tongue order and phi weights
TONGUE_CODES = ["ko", "av", "ru", "ca", "um", "dr"]
TONGUE_NAMES = [
    "Kor'aelin",  # Intent/Command (code: Korvath)
    "Avali",  # Wisdom/Routing (code: Avhari)
    "Runethic",  # Governance/Entropy (code: Runeveil)
    "Cassisivadan",  # Compute/Logic (code: Caelith)
    "Umbroth",  # Security/Defense (code: Umbraex)
    "Draumric",  # Structure/Architecture (code: Draethis)
]
PHI_WEIGHTS = [PHI**i for i in range(6)]  # [1.0, 1.618, 2.618, 4.236, 6.854, 11.09]

# Musical interval ratios for the SOUND braid
MUSICAL_INTERVALS = {
    "unison": 1.0,
    "octave": 2.0,
    "perfect_fifth": 3.0 / 2.0,
    "perfect_fourth": 4.0 / 3.0,
    "major_third": 5.0 / 4.0,
    "minor_third": 6.0 / 5.0,
    "phi_interval": PHI,  # The golden interval — unique to SCBE
}

# Base frequency for harmonic generation (A4 = 440 Hz, but we use phi-scaled)
BASE_FREQ = 440.0 * (PHI - 1)  # ~272 Hz — near middle C but phi-offset


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LightStrand:
    """LIGHT braid: what IS (presence/absence/data)."""

    raw_byte: int  # L0: 0-255, the raw data
    tongue_token: str  # L1: bijective tongue token string
    orientation: Tuple[float, ...]  # L2: 6-element tongue activation vector


@dataclass(frozen=True)
class SoundStrand:
    """SOUND braid: what RESONATES (harmonic fill for dark nodes)."""

    nodal_freq: float  # S0: frequency from nodal surface equation
    octave_map: float  # S1: phi-scaled octave transposition
    phase_angle: float  # S2: wave phase at this position (radians)


@dataclass(frozen=True)
class IntentStrand:
    """INTENT braid: which WAY (polarity/direction)."""

    primary_trit: int  # I0: {-1, 0, +1}
    mirror_trit: int  # I1: {-1, 0, +1}
    governance: int  # I2: {-1, 0, +1} = DENY / QUARANTINE / ALLOW


@dataclass(frozen=True)
class TriBraidCodon:
    """A single position in the tri-braid DNA.

    Contains all 9 sub-strands (3 per braid).
    The codon is the fundamental unit of the encoding.
    """

    light: LightStrand
    sound: SoundStrand
    intent: IntentStrand

    @property
    def flat_9(self) -> Tuple:
        """Flatten to 9-element tuple for hashing/comparison."""
        return (
            self.light.raw_byte,
            self.light.tongue_token,
            self.light.orientation,
            self.sound.nodal_freq,
            self.sound.octave_map,
            self.sound.phase_angle,
            self.intent.primary_trit,
            self.intent.mirror_trit,
            self.intent.governance,
        )

    @property
    def intent_27_index(self) -> int:
        """Map the 3 trits to a unique index in [0, 26].

        (primary+1)*9 + (mirror+1)*3 + (governance+1)
        """
        return (self.intent.primary_trit + 1) * 9 + (self.intent.mirror_trit + 1) * 3 + (self.intent.governance + 1)

    @property
    def phi_density(self) -> float:
        """Phi-scaled density at this position.

        Based on which tongues are active (orientation > threshold).
        """
        active_weight = sum(w for w, a in zip(PHI_WEIGHTS, self.light.orientation) if a > 0.1)
        total_weight = sum(PHI_WEIGHTS)
        return active_weight / total_weight if total_weight > 0 else 0.0


@dataclass
class DigichainCluster:
    """A sequence of codons forming a DNA-like cluster.

    Identity depends on composition of inner braided matrices,
    not just the sequence of codons.
    """

    codons: List[TriBraidCodon]
    braid_crossings: int = 0  # Number of braid strand crossings

    @property
    def cluster_id(self) -> str:
        """Compute topological identity hash.

        Two clusters with same codons but different braid arrangements
        produce different IDs — the crossing pattern matters.
        """
        h = hashlib.sha256()
        for codon in self.codons:
            h.update(str(codon.flat_9).encode())
        h.update(self.braid_crossings.to_bytes(4, "big"))
        # Include phi density signature
        density_sig = sum(c.phi_density for c in self.codons)
        h.update(str(density_sig).encode())
        return h.hexdigest()[:32]

    @property
    def effective_states(self) -> float:
        """Phi-scaled effective state count: (3^phi)^3 per position."""
        return (3**PHI) ** 3  # ~148.8

    @property
    def dark_node_ratio(self) -> float:
        """Fraction of positions where SOUND braid is dominant (dark nodes)."""
        if not self.codons:
            return 0.0
        dark = sum(1 for c in self.codons if c.phi_density < 0.3)
        return dark / len(self.codons)


# ---------------------------------------------------------------------------
# SOUND braid: harmonic fill for dark nodes
# ---------------------------------------------------------------------------


def nodal_frequency(position_index: int, tongue_index: int, total_positions: int) -> float:
    """Compute the nodal surface frequency for a position.

    Uses the vacuum acoustics nodal surface equation:
    N(x; n, m) = cos(n*pi*x1/L)*cos(m*pi*x2/L) - cos(m*pi*x1/L)*cos(n*pi*x2/L)

    The frequency is derived from the mode numbers (n, m) mapped
    to the tongue index and position.

    Args:
        position_index: Position in the sequence.
        tongue_index: Which tongue (0-5) this frequency is for.
        total_positions: Total sequence length (used as characteristic length L).

    Returns:
        Frequency in Hz for this position's harmonic fill.
    """
    L = max(total_positions, 1)
    n = tongue_index + 1
    m = (tongue_index + 3) % 6 + 1  # Complementary mode

    # Normalized position
    x = (position_index + 0.5) / L

    # Nodal surface value determines frequency deviation
    nodal_val = math.cos(n * PI * x) * math.cos(m * PI * x) - math.cos(m * PI * x) * math.cos(n * PI * x * PHI)

    # Map nodal value to frequency via phi-scaled base
    freq = BASE_FREQ * PHI_WEIGHTS[tongue_index] * (1.0 + 0.5 * nodal_val)
    return max(freq, 20.0)  # Floor at 20 Hz (lowest audible)


def octave_transpose(freq: float, target_octave: int = 4) -> float:
    """Transpose frequency to target octave via doubling/halving.

    Stellar-to-human octave mapping: f_human = f_stellar * 2^n

    Args:
        freq: Input frequency in Hz.
        target_octave: Target octave (4 = middle C region).

    Returns:
        Transposed frequency.
    """
    if freq <= 0:
        return BASE_FREQ

    # Middle C octave boundaries: 261.63 Hz (C4) to 523.25 Hz (C5)
    low = 261.63 * (2 ** (target_octave - 4))
    high = low * 2

    result = freq
    while result < low and result > 0:
        result *= 2
    while result > high:
        result /= 2
    return result


def harmonic_phase(position_index: int, activation: float, tongue_index: int) -> float:
    """Compute phase angle for the SOUND braid at this position.

    Phase is derived from the INVERSE of activation — louder when darker.
    The sound braid fills silence with structure.

    Args:
        position_index: Position in sequence.
        activation: Tongue activation level [0, 1].
        tongue_index: Which tongue (0-5).

    Returns:
        Phase angle in radians [0, 2*pi).
    """
    # Darkness factor: high when activation is low
    darkness = 1.0 - min(max(activation, 0.0), 1.0)

    # Phase rotates with position, scaled by phi weight
    base_phase = (2 * PI * position_index * PHI_WEIGHTS[tongue_index]) % (2 * PI)

    # Darkness amplifies the phase offset
    return (base_phase + PI * darkness) % (2 * PI)


# ---------------------------------------------------------------------------
# INTENT braid: trit computation
# ---------------------------------------------------------------------------


def compute_intent_trits(
    activation_vector: Tuple[float, ...],
    prev_activation: Optional[Tuple[float, ...]] = None,
    governance_posture: str = "ALLOW",
) -> Tuple[int, int, int]:
    """Compute the three intent trits from activation context.

    I0 (primary): direction of dominant tongue activation change
    I1 (mirror): direction of complementary tongue activation change
    I2 (governance): ALLOW=+1, QUARANTINE=0, DENY=-1

    Args:
        activation_vector: Current 6-element tongue activation.
        prev_activation: Previous activation (None = first position).
        governance_posture: One of ALLOW, QUARANTINE, DENY.

    Returns:
        (primary_trit, mirror_trit, governance_trit) each in {-1, 0, +1}.
    """
    # Governance trit
    gov_map = {"ALLOW": 1, "QUARANTINE": 0, "DENY": -1}
    gov_trit = gov_map.get(governance_posture, 0)

    if prev_activation is None:
        # First position: neutral intent
        return (0, 0, gov_trit)

    # Compute activation deltas
    deltas = [a - p for a, p in zip(activation_vector, prev_activation)]

    # Primary trit: phi-weighted sum of deltas
    weighted_delta = sum(d * w for d, w in zip(deltas, PHI_WEIGHTS))
    threshold = 0.1 * sum(PHI_WEIGHTS)

    if weighted_delta > threshold:
        primary = 1
    elif weighted_delta < -threshold:
        primary = -1
    else:
        primary = 0

    # Mirror trit: complementary — uses the INACTIVE tongue deltas
    # (inverse phi weighting: heaviest weight on lightest tongue)
    inv_weights = list(reversed(PHI_WEIGHTS))
    mirror_delta = sum(d * w for d, w in zip(deltas, inv_weights))

    if mirror_delta > threshold:
        mirror = 1
    elif mirror_delta < -threshold:
        mirror = -1
    else:
        mirror = 0

    return (primary, mirror, gov_trit)


# ---------------------------------------------------------------------------
# Tri-Braid Encoder
# ---------------------------------------------------------------------------


def encode_byte_to_codon(
    raw_byte: int,
    tongue_code: str,
    tongue_token: str,
    activation_vector: Tuple[float, ...],
    position_index: int,
    total_positions: int,
    prev_activation: Optional[Tuple[float, ...]] = None,
    governance_posture: str = "ALLOW",
) -> TriBraidCodon:
    """Encode a single byte position into a full tri-braid codon.

    This is the core encoding function. One byte in, one codon out.
    The codon carries 9 sub-strand values across 3 braids.

    Args:
        raw_byte: The byte value (0-255).
        tongue_code: Which tongue encoded this ("ko", "av", etc.).
        tongue_token: The bijective token string for this byte.
        activation_vector: 6-element tongue activation for this position.
        position_index: Position in the sequence.
        total_positions: Total sequence length.
        prev_activation: Previous position's activation (for intent).
        governance_posture: ALLOW / QUARANTINE / DENY.

    Returns:
        Complete TriBraidCodon with all 9 sub-strands populated.
    """
    tongue_idx = TONGUE_CODES.index(tongue_code) if tongue_code in TONGUE_CODES else 0

    # LIGHT braid
    light = LightStrand(
        raw_byte=raw_byte,
        tongue_token=tongue_token,
        orientation=tuple(activation_vector),
    )

    # SOUND braid — fills the dark nodes
    # Frequency based on nodal surface at this position
    freq = nodal_frequency(position_index, tongue_idx, total_positions)
    # Octave-transpose to audible/computational range
    octave = octave_transpose(freq)
    # Phase from darkness level
    activation_level = activation_vector[tongue_idx] if tongue_idx < len(activation_vector) else 0.0
    phase = harmonic_phase(position_index, activation_level, tongue_idx)

    sound = SoundStrand(
        nodal_freq=round(freq, 4),
        octave_map=round(octave, 4),
        phase_angle=round(phase, 6),
    )

    # INTENT braid
    p_trit, m_trit, g_trit = compute_intent_trits(activation_vector, prev_activation, governance_posture)

    intent = IntentStrand(
        primary_trit=p_trit,
        mirror_trit=m_trit,
        governance=g_trit,
    )

    return TriBraidCodon(light=light, sound=sound, intent=intent)


def encode_sequence_to_cluster(
    byte_stream: bytes,
    tongue_code: str,
    tokenize_fn,
    activation_fn=None,
    governance_posture: str = "ALLOW",
) -> DigichainCluster:
    """Encode a byte sequence into a full digichain cluster.

    Args:
        byte_stream: Raw bytes to encode.
        tongue_code: Primary tongue for tokenization.
        tokenize_fn: Function (byte_val, tongue) -> token_string.
        activation_fn: Optional function (byte_val, position) -> 6-element activation.
            If None, uses single-tongue activation (1.0 for primary, 0.0 for others).
        governance_posture: Default governance for all positions.

    Returns:
        DigichainCluster containing all codons.
    """
    tongue_idx = TONGUE_CODES.index(tongue_code) if tongue_code in TONGUE_CODES else 0
    total = len(byte_stream)
    codons: List[TriBraidCodon] = []
    prev_act: Optional[Tuple[float, ...]] = None
    crossings = 0

    for i, b in enumerate(byte_stream):
        # Tokenize
        token = tokenize_fn(b, tongue_code)

        # Compute activation
        if activation_fn is not None:
            activation = tuple(activation_fn(b, i))
        else:
            # Default: single tongue active at phi-weighted level
            activation = tuple(PHI_WEIGHTS[j] / PHI_WEIGHTS[5] if j == tongue_idx else 0.0 for j in range(6))

        codon = encode_byte_to_codon(
            raw_byte=b,
            tongue_code=tongue_code,
            tongue_token=token,
            activation_vector=activation,
            position_index=i,
            total_positions=total,
            prev_activation=prev_act,
            governance_posture=governance_posture,
        )
        codons.append(codon)

        # Count braid crossings: when intent direction changes
        if prev_act is not None:
            if codon.intent.primary_trit != codons[-2].intent.primary_trit:
                crossings += 1
            if codon.intent.mirror_trit != codons[-2].intent.mirror_trit:
                crossings += 1

        prev_act = activation

    return DigichainCluster(codons=codons, braid_crossings=crossings)


# ---------------------------------------------------------------------------
# Multi-tongue encoding (all 6 simultaneously)
# ---------------------------------------------------------------------------


@dataclass
class HexaCodon:
    """A position encoded through ALL 6 tongues simultaneously.

    This is the full tri-braid DNA at a single position:
    6 tongue encodings, each with their own LIGHT/SOUND/INTENT,
    braided together.
    """

    tongue_codons: Dict[str, TriBraidCodon]  # keyed by tongue code

    @property
    def composite_activation(self) -> Tuple[float, ...]:
        """The combined 6-tongue activation vector."""
        if not self.tongue_codons:
            return (0.0,) * 6
        # Use the first codon's orientation (they should all share it)
        first = next(iter(self.tongue_codons.values()))
        return first.light.orientation

    @property
    def dominant_tongue(self) -> str:
        """Which tongue has highest phi-weighted activation."""
        act = self.composite_activation
        weighted = [a * w for a, w in zip(act, PHI_WEIGHTS)]
        idx = weighted.index(max(weighted))
        return TONGUE_CODES[idx]

    @property
    def is_dark(self) -> bool:
        """True if total activation is below threshold (dark node)."""
        return sum(self.composite_activation) < 0.5

    @property
    def sound_energy(self) -> float:
        """Total harmonic energy at this position (louder when darker)."""
        return sum(c.sound.nodal_freq * (1.0 - sum(c.light.orientation) / 6.0) for c in self.tongue_codons.values())

    def composite_27_state(self) -> int:
        """Aggregate intent across all tongues into a single 27-state index."""
        # Majority vote across tongues for each trit
        p_votes = [c.intent.primary_trit for c in self.tongue_codons.values()]
        m_votes = [c.intent.mirror_trit for c in self.tongue_codons.values()]
        g_votes = [c.intent.governance for c in self.tongue_codons.values()]

        def majority(votes: list) -> int:
            s = sum(votes)
            if s > 0:
                return 1
            elif s < 0:
                return -1
            return 0

        p = majority(p_votes)
        m = majority(m_votes)
        g = majority(g_votes)
        return (p + 1) * 9 + (m + 1) * 3 + (g + 1)


def encode_hexa(
    raw_byte: int,
    tokenize_fn,
    position_index: int,
    total_positions: int,
    activation_vector: Tuple[float, ...],
    prev_activation: Optional[Tuple[float, ...]] = None,
    governance_posture: str = "ALLOW",
) -> HexaCodon:
    """Encode a single byte through ALL 6 tongues simultaneously.

    This produces the full hexagonal tri-braid DNA at one position.

    Args:
        raw_byte: Byte value (0-255).
        tokenize_fn: Function (byte_val, tongue_code) -> token_string.
        position_index: Position in sequence.
        total_positions: Total sequence length.
        activation_vector: 6-element tongue activation.
        prev_activation: Previous activation for intent computation.
        governance_posture: ALLOW / QUARANTINE / DENY.

    Returns:
        HexaCodon with all 6 tongue encodings.
    """
    codons: Dict[str, TriBraidCodon] = {}
    for tongue_code in TONGUE_CODES:
        token = tokenize_fn(raw_byte, tongue_code)
        codon = encode_byte_to_codon(
            raw_byte=raw_byte,
            tongue_code=tongue_code,
            tongue_token=token,
            activation_vector=activation_vector,
            position_index=position_index,
            total_positions=total_positions,
            prev_activation=prev_activation,
            governance_posture=governance_posture,
        )
        codons[tongue_code] = codon

    return HexaCodon(tongue_codons=codons)


# ---------------------------------------------------------------------------
# Phi-scaled braid density
# ---------------------------------------------------------------------------


def phi_braid_density(n_strands: int = 3, depth: int = 3) -> float:
    """Compute (n^phi)^depth — the effective state count.

    For the tri-braid: (3^phi)^3 = (3^1.618)^3 ≈ 148.8

    This is the number of distinguishable states per cluster position
    when phi-scaling is applied to the braid density.
    """
    return (n_strands**PHI) ** depth


def cluster_information_density(cluster: DigichainCluster) -> Dict[str, float]:
    """Compute information density metrics for a cluster.

    Returns dict with:
        - flat_states: 3^3^3 = 27 (without phi scaling)
        - phi_states: (3^phi)^3 ≈ 148.8 (with phi scaling)
        - dark_ratio: fraction of dark nodes
        - sound_fill: average harmonic energy in dark nodes
        - crossing_density: braid crossings per codon
        - cluster_id: topological identity hash
    """
    n = len(cluster.codons)
    if n == 0:
        return {
            "flat_states": 27.0,
            "phi_states": phi_braid_density(),
            "dark_ratio": 0.0,
            "sound_fill": 0.0,
            "crossing_density": 0.0,
            "cluster_id": "empty",
        }

    dark_codons = [c for c in cluster.codons if c.phi_density < 0.3]
    sound_in_dark = sum(c.sound.nodal_freq for c in dark_codons) / len(dark_codons) if dark_codons else 0.0

    return {
        "flat_states": 27.0,
        "phi_states": phi_braid_density(),
        "dark_ratio": len(dark_codons) / n,
        "sound_fill": round(sound_in_dark, 2),
        "crossing_density": cluster.braid_crossings / n,
        "cluster_id": cluster.cluster_id,
    }
