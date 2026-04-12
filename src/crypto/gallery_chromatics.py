"""
Gallery Chromatics — Dual-Seeded Color Field from Dead Tone Harmonics
=====================================================================

Maps dead-tone frequencies to a perceptual color field using CIELAB
coordinates, then scatters 4 color points per note at equal angular
distance from the harmonic root. Each Sacred Tongue rotates the entire
4-point set by its own phase offset, creating tongue-specific "irises"
that see different orientations of the same harmonic structure.

Pipeline:
    frequency → harmonic number → (θ, r) polar → CIELAB → material band

Material bands (applied as a separate axis, not mixed into color):
    0 = matte       (L* darkened, low chroma)
    1 = fluorescent  (L* boosted, high chroma, slight green shift)
    2 = neon         (max chroma, L* mid-range, saturated)
    3 = metallic     (L* high, chroma compressed, slight warm shift)

Dual-seeded eyes:
    Left eye  = seeded by structure tongues (KO, DR) — sees dependency/form
    Right eye = seeded by creativity tongues (RU, CA) — sees novelty/urgency
    Both eyes share stability tongues (AV, UM) as the "optic nerve" bridge

The 4 colors per note are placed at 90° intervals on the CIELAB a*b* plane,
equidistant from the harmonic seed point. This gives each dead tone a
"color chord" — a set of perceptually distinct colors that are harmonically
related.

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from src.crypto.quantum_frequency_bundle import GalleryAmbientNote

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI = 1.618033988749895
TAU = 2.0 * math.pi

# Dead tone target ratios
DEAD_TONE_RATIOS = {
    "perfect_fifth": 3.0 / 2.0,  # 1.500
    "minor_sixth": 8.0 / 5.0,  # 1.600
    "minor_seventh": 16.0 / 9.0,  # 1.778
}

# Sacred Tongue phase offsets (radians) — phi-scaled angular rotation
# Each tongue rotates the 4-color set by this amount on the a*b* plane
TONGUE_PHASE_OFFSETS = {
    "ko": 0.0,  # origin — intent
    "av": TAU / PHI,  # ~3.883 rad — wisdom
    "ru": TAU / (PHI**2),  # ~2.399 rad — binding
    "ca": TAU / (PHI**3),  # ~1.483 rad — invention
    "um": TAU / (PHI**4),  # ~0.917 rad — shadow
    "dr": TAU / (PHI**5),  # ~0.566 rad — structure
}

# Tongue groupings for dual-eye seeding
LEFT_EYE_TONGUES = ("ko", "dr")  # structure/form eye
RIGHT_EYE_TONGUES = ("ru", "ca")  # creativity/novelty eye
BRIDGE_TONGUES = ("av", "um")  # stability bridge (shared)

# Material band properties (L* modifier, chroma scale, hue shift)
MATERIAL_BANDS = {
    "matte": {"L_mod": -15.0, "chroma_scale": 0.6, "hue_shift": 0.0},
    "fluorescent": {"L_mod": 12.0, "chroma_scale": 1.3, "hue_shift": 0.15},
    "neon": {"L_mod": 0.0, "chroma_scale": 1.5, "hue_shift": 0.0},
    "metallic": {"L_mod": 10.0, "chroma_scale": 0.7, "hue_shift": 0.08},
}
MATERIAL_ORDER = ["matte", "fluorescent", "neon", "metallic"]


# ---------------------------------------------------------------------------
# CIELAB Color
# ---------------------------------------------------------------------------


@dataclass
class LabColor:
    """CIELAB color with material band annotation."""

    L: float  # lightness [0, 100]
    a: float  # green(-) to red(+) [-128, 128]
    b: float  # blue(-) to yellow(+) [-128, 128]
    material: str  # "matte", "fluorescent", "neon", "metallic"

    @property
    def chroma(self) -> float:
        """Perceptual colorfulness: C* = sqrt(a² + b²)"""
        return math.sqrt(self.a**2 + self.b**2)

    @property
    def hue_angle(self) -> float:
        """Hue angle in radians: h = atan2(b, a)"""
        return math.atan2(self.b, self.a)

    @property
    def hue_degrees(self) -> float:
        """Hue angle in degrees [0, 360)."""
        h = math.degrees(self.hue_angle)
        return h if h >= 0 else h + 360.0

    def to_dict(self) -> dict:
        return {
            "L": round(self.L, 2),
            "a": round(self.a, 2),
            "b": round(self.b, 2),
            "chroma": round(self.chroma, 2),
            "hue_deg": round(math.degrees(self.hue_angle) % 360, 1),
            "material": self.material,
        }


# ---------------------------------------------------------------------------
# Harmonic-to-Color Mapping
# ---------------------------------------------------------------------------


def frequency_to_harmonic_number(ratio: float) -> float:
    """Convert a frequency ratio to a continuous harmonic number.

    Uses log-phi scaling: h = log_phi(ratio)
    This maps phi-related ratios to integer harmonics and dead tones
    to irrational positions between them — exactly the gaps we want
    to visualize.
    """
    if ratio <= 0:
        return 0.0
    return math.log(ratio) / math.log(PHI)


def harmonic_to_polar(harmonic: float, radius: float = 50.0) -> Tuple[float, float]:
    """Map a harmonic number to polar coordinates on the a*b* plane.

    theta = harmonic * phi * pi  (golden angle spiral)
    r = radius * (1 - exp(-|harmonic|))  (saturates at radius)

    The golden angle ensures harmonics don't overlap and dead tones
    land in visually distinct regions.
    """
    theta = harmonic * PHI * math.pi
    r = radius * (1.0 - math.exp(-abs(harmonic)))
    return theta, r


def scatter_color_quad(
    theta_center: float,
    r_center: float,
    tongue_phase: float,
    L_base: float = 65.0,
) -> List[LabColor]:
    """Place 4 colors at 90° intervals around a center point.

    Each color gets a different material band. The tongue_phase rotates
    the entire quad, so different tongues see different color orientations
    of the same harmonic structure.

    Args:
        theta_center: base angle on the a*b* plane (radians)
        r_center: distance from origin (chroma)
        tongue_phase: tongue-specific rotation (radians)
        L_base: base lightness

    Returns:
        4 LabColor instances, one per material band
    """
    colors = []
    for i, material_name in enumerate(MATERIAL_ORDER):
        mat = MATERIAL_BANDS[material_name]

        # 90° spacing + tongue rotation
        angle = theta_center + tongue_phase + (i * math.pi / 2.0)
        # Apply material hue shift
        angle += mat["hue_shift"]

        # Chroma = r_center scaled by material
        chroma = r_center * mat["chroma_scale"]

        # CIELAB coordinates
        a = chroma * math.cos(angle)
        b = chroma * math.sin(angle)
        L = max(0.0, min(100.0, L_base + mat["L_mod"]))

        colors.append(LabColor(L=L, a=a, b=b, material=material_name))

    return colors


# ---------------------------------------------------------------------------
# Dead Tone Color Chord
# ---------------------------------------------------------------------------


@dataclass
class DeadToneColorChord:
    """4-color chord for a single dead tone, as seen by one tongue."""

    dead_tone: str  # "perfect_fifth" | "minor_sixth" | "minor_seventh"
    tongue: str  # which tongue's phase was used
    harmonic_number: float  # log-phi harmonic position
    colors: List[LabColor]  # 4 colors (matte, fluorescent, neon, metallic)

    @property
    def mean_chroma(self) -> float:
        return sum(c.chroma for c in self.colors) / len(self.colors)

    @property
    def hue_spread_deg(self) -> float:
        """Angular spread of the 4 hues in degrees."""
        hues = sorted(math.degrees(c.hue_angle) % 360 for c in self.colors)
        if len(hues) < 2:
            return 0.0
        # Max gap between consecutive hues
        gaps = [hues[i + 1] - hues[i] for i in range(len(hues) - 1)]
        gaps.append(360.0 - hues[-1] + hues[0])  # wrap-around gap
        return 360.0 - max(gaps)  # spread = 360 - largest gap

    def to_dict(self) -> dict:
        return {
            "dead_tone": self.dead_tone,
            "tongue": self.tongue,
            "harmonic_number": round(self.harmonic_number, 4),
            "mean_chroma": round(self.mean_chroma, 2),
            "hue_spread_deg": round(self.hue_spread_deg, 1),
            "colors": [c.to_dict() for c in self.colors],
        }


# ---------------------------------------------------------------------------
# Iris (one eye's view of all 3 dead tones)
# ---------------------------------------------------------------------------


@dataclass
class ChromaticIris:
    """One eye's complete color field — 3 dead tones × 4 colors = 12 points.

    Each iris is seeded by a pair of tongues. The tongue with the higher
    QHO coefficient dominates the phase rotation, while the secondary
    tongue adds a sub-rotation to each material band.
    """

    eye: str  # "left" or "right"
    seed_tongues: Tuple[str, str]  # which tongues seed this eye
    dominant_tongue: str  # which tongue has higher activation
    chords: Dict[str, DeadToneColorChord]  # 3 dead tone chords
    bridge_phase: float  # stability bridge contribution

    @property
    def total_chroma(self) -> float:
        return sum(ch.mean_chroma for ch in self.chords.values())

    @property
    def color_count(self) -> int:
        return sum(len(ch.colors) for ch in self.chords.values())

    def to_dict(self) -> dict:
        return {
            "eye": self.eye,
            "seed_tongues": list(self.seed_tongues),
            "dominant_tongue": self.dominant_tongue,
            "bridge_phase": round(self.bridge_phase, 4),
            "total_chroma": round(self.total_chroma, 2),
            "color_count": self.color_count,
            "chords": {k: v.to_dict() for k, v in self.chords.items()},
        }


# ---------------------------------------------------------------------------
# Gallery Color Field (dual eyes)
# ---------------------------------------------------------------------------


@dataclass
class GalleryColorField:
    """Dual-seeded chromatic perception of the gallery ambient layer.

    Left eye (structure): sees dependency chains and form locks
    Right eye (creativity): sees novelty gaps and urgency states
    Both share the stability bridge for cross-eye coherence.

    The field contains 24 total color points (2 eyes × 3 tones × 4 colors).
    """

    left_iris: ChromaticIris
    right_iris: ChromaticIris
    cross_eye_coherence: float  # how aligned are the two irises [0, 1]
    dominant_material: str  # which material band has most chroma
    spectral_coverage: float  # fraction of hue wheel covered [0, 1]

    def to_dict(self) -> dict:
        return {
            "left_iris": self.left_iris.to_dict(),
            "right_iris": self.right_iris.to_dict(),
            "cross_eye_coherence": round(self.cross_eye_coherence, 4),
            "dominant_material": self.dominant_material,
            "spectral_coverage": round(self.spectral_coverage, 4),
        }


# ---------------------------------------------------------------------------
# Core Computation
# ---------------------------------------------------------------------------


def _build_iris(
    eye_name: str,
    seed_tongues: Tuple[str, str],
    tongue_coefficients: Dict[str, float],
    dead_tone_ratios: Dict[str, float],
    bridge_phase: float,
) -> ChromaticIris:
    """Build one chromatic iris from tongue seeds and dead tone ratios.

    Args:
        eye_name: "left" or "right"
        seed_tongues: pair of tongues seeding this eye
        tongue_coefficients: QHO probability amplitudes per tongue
        dead_tone_ratios: observed ratio per dead tone from gallery ambient
        bridge_phase: stability bridge phase contribution
    """
    # Dominant tongue = higher coefficient
    t1, t2 = seed_tongues
    coeff1 = tongue_coefficients.get(t1, 0.5)
    coeff2 = tongue_coefficients.get(t2, 0.5)
    dominant = t1 if coeff1 >= coeff2 else t2
    secondary = t2 if dominant == t1 else t1

    # Primary phase from dominant tongue
    primary_phase = TONGUE_PHASE_OFFSETS[dominant]
    # Secondary adds a sub-rotation scaled by its relative strength
    secondary_weight = tongue_coefficients.get(secondary, 0.5)
    sub_rotation = TONGUE_PHASE_OFFSETS[secondary] * secondary_weight * 0.3

    chords: Dict[str, DeadToneColorChord] = {}

    for tone_name, ratio in dead_tone_ratios.items():
        h = frequency_to_harmonic_number(ratio)
        theta, r = harmonic_to_polar(h)

        # Combined phase = primary + sub-rotation + bridge + tone-specific offset
        tone_offset = {"perfect_fifth": 0.0, "minor_sixth": PHI, "minor_seventh": PHI * 2}.get(tone_name, 0.0)
        combined_phase = primary_phase + sub_rotation + bridge_phase * 0.2 + tone_offset

        colors = scatter_color_quad(theta, r, combined_phase)

        chords[tone_name] = DeadToneColorChord(
            dead_tone=tone_name,
            tongue=dominant,
            harmonic_number=h,
            colors=colors,
        )

    return ChromaticIris(
        eye=eye_name,
        seed_tongues=seed_tongues,
        dominant_tongue=dominant,
        chords=chords,
        bridge_phase=bridge_phase,
    )


def compute_gallery_color_field(
    gallery_notes: Dict[str, "GalleryAmbientNote"],
    tongue_coefficients: Dict[str, float],
) -> GalleryColorField:
    """Compute the dual-seeded chromatic field from gallery ambient data.

    Args:
        gallery_notes: dict of dead tone name → GalleryAmbientNote
            (from QuantumFrequencyBundle.gallery.notes)
        tongue_coefficients: dict of tongue → QHO probability amplitude
            (from QuantumFrequencyBundle.qho.states[t].coefficient)

    Returns:
        GalleryColorField with 24 color points across 2 irises
    """
    # Extract observed ratios from gallery notes
    dead_tone_ratios = {name: note.observed_ratio for name, note in gallery_notes.items()}

    # Bridge phase from stability tongues (AV, UM)
    av_phase = TONGUE_PHASE_OFFSETS["av"] * tongue_coefficients.get("av", 0.5)
    um_phase = TONGUE_PHASE_OFFSETS["um"] * tongue_coefficients.get("um", 0.5)
    bridge_phase = (av_phase + um_phase) / 2.0

    # Build both irises
    left = _build_iris("left", LEFT_EYE_TONGUES, tongue_coefficients, dead_tone_ratios, bridge_phase)
    right = _build_iris("right", RIGHT_EYE_TONGUES, tongue_coefficients, dead_tone_ratios, bridge_phase)

    # Cross-eye coherence: how similar are the two irises' chroma patterns?
    left_chromas = [left.chords[t].mean_chroma for t in DEAD_TONE_RATIOS]
    right_chromas = [right.chords[t].mean_chroma for t in DEAD_TONE_RATIOS]
    # Cosine similarity of chroma vectors
    dot = sum(l * r for l, r in zip(left_chromas, right_chromas))
    mag_l = math.sqrt(sum(x**2 for x in left_chromas)) or 1e-9
    mag_r = math.sqrt(sum(x**2 for x in right_chromas)) or 1e-9
    coherence = max(0.0, min(1.0, dot / (mag_l * mag_r)))

    # Dominant material: which material band has highest total chroma?
    material_chroma = {m: 0.0 for m in MATERIAL_ORDER}
    for iris in (left, right):
        for chord in iris.chords.values():
            for color in chord.colors:
                material_chroma[color.material] += color.chroma
    dominant_material = max(material_chroma, key=material_chroma.get)

    # Spectral coverage: what fraction of the 360° hue wheel is covered?
    all_hues = []
    for iris in (left, right):
        for chord in iris.chords.values():
            for color in chord.colors:
                all_hues.append(math.degrees(color.hue_angle) % 360)
    all_hues.sort()
    if len(all_hues) >= 2:
        gaps = [all_hues[i + 1] - all_hues[i] for i in range(len(all_hues) - 1)]
        gaps.append(360.0 - all_hues[-1] + all_hues[0])
        largest_gap = max(gaps)
        spectral_coverage = (360.0 - largest_gap) / 360.0
    else:
        spectral_coverage = 0.0

    return GalleryColorField(
        left_iris=left,
        right_iris=right,
        cross_eye_coherence=coherence,
        dominant_material=dominant_material,
        spectral_coverage=spectral_coverage,
    )
