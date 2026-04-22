"""
Quantum Frequency Bundle Generator — QHO-Grounded Dense Training Data
======================================================================

Maps real quantum harmonic oscillator (QHO) physics onto the existing
SCBE trit/polymorphic/harmonic stack to produce dense, frequency-tagged
bundle training records.

Real QHO physics used (textbook, no approximation):
    H = ℏω(a†a + 1/2)
    E_n = ℏω(n + 1/2),  n = 0, 1, 2, ...
    |ψ⟩ = Σ c_n |n⟩,   Σ|c_n|² = 1
    Transition frequency: ν_{m,n} = |m-n| · ω/2π

Mapping to SCBE structures:
    QHO energy level n → trit excitation depth
    Creation operator a† → polymorphic sibling generation (Monty Hall)
    Annihilation operator a → path collapse (measurement/observation)
    Superposition |c_n|² → 6-channel visual frequency vector (tongues)
    Transition frequency → acoustic band (infra/audible/ultra)
    Ground state |0⟩ → null_state trit (the egg)
    Zero-point energy ℏω/2 → minimum weight (even stable records carry info)

Wires into:
    - trit_curriculum.py: compute_trit_signal()
    - multipath_generator.py: compute_multipath()
    - harmonic_dark_fill.py: TONGUE_AUDIBLE_FREQ, HarmonicFill
    - crossing_energy.py: DualTernaryPair, harmonic_cost()
    - spectral_bonding.py: hue assignments, interference

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from src.crypto.trit_curriculum import (
    TritSignal,
    compute_trit_signal,
)
from src.crypto.multipath_generator import (
    MultiPathRecord,
    compute_multipath,
    POLY_THRESHOLD,
)
from src.crypto.harmonic_dark_fill import (
    TONGUE_AUDIBLE_FREQ,
    voice_leading_interval,
    nearest_musical_interval,
)
from src.crypto.crossing_energy import (
    DualTernaryPair,
    harmonic_cost,
)
from src.crypto.tri_bundle import (
    PHI,
    TONGUE_WEIGHTS,
    TONGUE_FREQUENCIES,
)

# ---------------------------------------------------------------------------
# Physical constants (SI)
# ---------------------------------------------------------------------------

HBAR = 1.054571817e-34  # J·s (reduced Planck constant)
H_PLANCK = 6.62607015e-34  # J·s (Planck constant)
K_BOLTZMANN = 1.380649e-23  # J/K (Boltzmann constant)
C_LIGHT = 299792458.0  # m/s

# Tongue visual wavelength bands (nm) — grounded in spectral color theory
# Each tongue occupies a frequency band in the visible/near-visible spectrum
TONGUE_WAVELENGTH_NM: Dict[str, Tuple[float, float]] = {
    "ko": (450.0, 520.0),  # blue-green (binding, cool)
    "av": (480.0, 520.0),  # cyan/aquamarine (diplomacy, flow)
    "ru": (620.0, 700.0),  # red-orange (power, volcanic)
    "ca": (570.0, 590.0),  # yellow-gold (joy, invention)
    "um": (380.0, 450.0),  # violet/UV edge (shadow, depth)
    "dr": (590.0, 620.0),  # amber/iron (forge, structure)
}

# Central wavelength per tongue (nm)
TONGUE_CENTRAL_WAVELENGTH: Dict[str, float] = {t: (lo + hi) / 2.0 for t, (lo, hi) in TONGUE_WAVELENGTH_NM.items()}

# Convert to frequency (Hz): ν = c / λ
TONGUE_OPTICAL_FREQ: Dict[str, float] = {t: C_LIGHT / (wl * 1e-9) for t, wl in TONGUE_CENTRAL_WAVELENGTH.items()}

# Tongue order for vector operations
TONGUE_ORDER = ["ko", "av", "ru", "ca", "um", "dr"]


# ---------------------------------------------------------------------------
# QHO State
# ---------------------------------------------------------------------------


@dataclass
class QHOState:
    """Quantum harmonic oscillator state for a single tongue.

    E_n = ℏω(n + 1/2)
    |ψ⟩ = c_n |n⟩ (single-level occupation for clarity)

    The 'omega' comes from the tongue's audible frequency:
        ω = 2πf_tongue

    This gives each tongue a different energy scale:
        KO: ω = 2π × 440 Hz → E_0 = ℏ(2π×440)/2
        DR: ω = 2π × 392 Hz → E_0 = ℏ(2π×392)/2

    The phi-weighted hierarchy means DR costs 11.09× more per quantum
    than KO — governance layers are energetically expensive to excite.
    """

    tongue: str
    n: int  # occupation number (energy level)
    omega: float  # angular frequency = 2π × f_tongue
    coefficient: float  # |c_n|² probability amplitude squared

    @property
    def energy(self) -> float:
        """E_n = ℏω(n + 1/2) — exact QHO energy."""
        return HBAR * self.omega * (self.n + 0.5)

    @property
    def zero_point_energy(self) -> float:
        """E_0 = ℏω/2 — minimum energy (even ground state isn't zero)."""
        return HBAR * self.omega * 0.5

    @property
    def excitation_energy(self) -> float:
        """Energy above ground state: ΔE = ℏω·n"""
        return HBAR * self.omega * self.n

    @property
    def phi_weighted_energy(self) -> float:
        """Energy scaled by tongue's phi weight.
        Higher tongues (DR=11.09) cost more per quantum.
        """
        return self.energy * TONGUE_WEIGHTS[self.tongue]

    @property
    def transition_frequency(self) -> float:
        """ν = ω/2π — frequency of photon emitted/absorbed in n→n±1."""
        return self.omega / (2 * math.pi)

    @property
    def wavelength_nm(self) -> float:
        """Visual wavelength (nm) from the tongue's spectral band.
        Adjusted by excitation level — higher n = blueshift.
        """
        base = TONGUE_CENTRAL_WAVELENGTH[self.tongue]
        # Higher excitation → shorter wavelength (blueshift)
        # ΔΛ ∝ -n (1 nm per quantum, bounded to tongue's band)
        lo, hi = TONGUE_WAVELENGTH_NM[self.tongue]
        shifted = base - self.n * 2.0  # 2nm blueshift per quantum
        return max(lo, min(hi, shifted))

    @property
    def optical_frequency(self) -> float:
        """Optical frequency (Hz) = c / λ."""
        return C_LIGHT / (self.wavelength_nm * 1e-9)


# ---------------------------------------------------------------------------
# Polychromatic Visual Frequency Vector
# ---------------------------------------------------------------------------


@dataclass
class PolychromaticState:
    """6-channel visual frequency vector across Sacred Tongues.

    Each tongue has a QHO occupation number and probability amplitude.
    The full state is a superposition: |ψ⟩ = Σ c_t |n_t⟩

    Normalization: Σ|c_t|² = 1 (quantum probability conservation)

    The visual vector encodes which tongues are "emitting" and at what
    intensity — analogous to polychromatic spectral lines from an
    atom in a superposition of energy levels.
    """

    states: Dict[str, QHOState]  # one QHO state per tongue

    @property
    def visual_vector(self) -> List[float]:
        """Normalized |c_t|² probabilities: the polychromatic emission."""
        raw = [self.states[t].coefficient for t in TONGUE_ORDER]
        total = sum(raw)
        if total == 0:
            return [1.0 / 6] * 6  # uniform if no signal
        return [v / total for v in raw]

    @property
    def total_energy(self) -> float:
        """Total QHO energy across all tongues."""
        return sum(s.energy for s in self.states.values())

    @property
    def phi_weighted_total_energy(self) -> float:
        """Total energy with phi-weighting (governance cost)."""
        return sum(s.phi_weighted_energy for s in self.states.values())

    @property
    def mean_excitation(self) -> float:
        """Mean occupation number (excitation level)."""
        ns = [s.n for s in self.states.values()]
        return sum(ns) / len(ns) if ns else 0.0

    @property
    def max_excitation(self) -> int:
        """Highest occupied level across tongues."""
        return max(s.n for s in self.states.values())

    @property
    def dominant_tongue(self) -> str:
        """Tongue with highest probability amplitude."""
        return max(self.states, key=lambda t: self.states[t].coefficient)

    @property
    def spectral_lines(self) -> List[Dict]:
        """All transition frequencies (spectral emission lines).

        For each tongue, the n→(n-1) transition produces a photon
        at frequency ω/2π. This gives the acoustic signature.
        """
        lines = []
        for t in TONGUE_ORDER:
            s = self.states[t]
            if s.n > 0:
                lines.append(
                    {
                        "tongue": t,
                        "n": s.n,
                        "frequency_hz": s.transition_frequency,
                        "wavelength_nm": s.wavelength_nm,
                        "energy_j": s.excitation_energy,
                        "probability": s.coefficient,
                    }
                )
        return lines


# ---------------------------------------------------------------------------
# Acoustic Band Mapping
# ---------------------------------------------------------------------------


@dataclass
class AcousticSignature:
    """Three-band acoustic signature derived from QHO states.

    Maps QHO occupation numbers to the three frequency bands in
    harmonic_dark_fill.py:
        Infrasonic (0.01–20 Hz): ground-state grounding (low n)
        Audible (20–20k Hz): tongue frequencies (mid n)
        Ultrasonic (20k–1M Hz): excited-state power (high n)

    The acoustic bands are NOT arbitrary — they're derived from
    the QHO transition frequencies scaled by the tongue's phi weight.
    """

    infrasonic_power: float  # [0, 1] — ground-state contribution
    audible_power: float  # [0, 1] — mid-excitation contribution
    ultrasonic_power: float  # [0, 1] — high-excitation contribution
    dominant_interval: str  # nearest musical interval name
    interval_deviation: float  # how far from pure interval

    @property
    def total_power(self) -> float:
        return self.infrasonic_power + self.audible_power + self.ultrasonic_power

    def to_dict(self) -> dict:
        return {
            "infrasonic": round(self.infrasonic_power, 6),
            "audible": round(self.audible_power, 6),
            "ultrasonic": round(self.ultrasonic_power, 6),
            "dominant_interval": self.dominant_interval,
            "interval_deviation": round(self.interval_deviation, 6),
        }


def compute_acoustic_signature(poly: PolychromaticState) -> AcousticSignature:
    """Derive acoustic signature from polychromatic QHO state.

    Low n tongues contribute to infrasonic grounding.
    Mid n tongues contribute to audible band.
    High n tongues contribute to ultrasonic power.
    """
    infra = 0.0
    audible = 0.0
    ultra = 0.0

    for t in TONGUE_ORDER:
        s = poly.states[t]
        weight = s.coefficient  # probability amplitude

        if s.n == 0:
            # Ground state → infrasonic grounding (zero-point energy)
            infra += weight * 0.8
            audible += weight * 0.2
        elif s.n <= 2:
            # Low excitation → audible band dominates
            infra += weight * 0.2
            audible += weight * 0.7
            ultra += weight * 0.1
        else:
            # High excitation → ultrasonic power
            infra += weight * 0.05
            audible += weight * 0.35
            ultra += weight * 0.6

    # Normalize
    total = infra + audible + ultra
    if total > 0:
        infra /= total
        audible /= total
        ultra /= total
    else:
        infra, audible, ultra = 0.33, 0.34, 0.33

    # Find dominant musical interval from the two strongest tongues
    sorted_tongues = sorted(TONGUE_ORDER, key=lambda t: poly.states[t].coefficient, reverse=True)
    if len(sorted_tongues) >= 2:
        ratio = voice_leading_interval(sorted_tongues[0], sorted_tongues[1])
        interval_name, deviation = nearest_musical_interval(ratio)
    else:
        interval_name = "unison"
        deviation = 0.0

    return AcousticSignature(
        infrasonic_power=infra,
        audible_power=audible,
        ultrasonic_power=ultra,
        dominant_interval=interval_name,
        interval_deviation=deviation,
    )


# ---------------------------------------------------------------------------
# Gallery Ambient Layer — Dead Tone Detection via Cross-Axis Interference
# ---------------------------------------------------------------------------
#
# The three "dead tones" are musical intervals permanently unreachable by
# single-tongue phi geometry: perfect fifth (3:2), minor sixth (8:5),
# minor seventh (16:9). Phi^n never equals these ratios for any integer n.
#
# But CROSS-AXIS interference between tongue pairs DOES produce them.
# The "gallery" is the ambient space between tongues where these
# interference patterns resonate — like dark matter filling gravitational
# gaps, visible only by its effect on what you CAN see.
#
# Axis coupling → dead tone mapping (from first-principles trit analysis):
#   Structure × Stability  → perfect fifth  (3:2 = 1.500) — dependency chains
#   Stability × Creativity → minor sixth    (8:5 = 1.600) — near-miss adversarial
#   Creativity × Structure → minor seventh  (16:9 = 1.778) — urgency/instability
#
# Each dead tone maps to a specific failure cascade in flight dynamics:
#   Perfect fifth:  form gates equilibrium (forward cyclic stabilizes descent)
#   Minor sixth:    equilibrium mimics novelty (0.018 from phi — adversarial sweet spot)
#   Creativity×Structure: novelty destroys form (tail rotor failure cascade)
#
# The attunement number phi^(1/13) = 1.0377099294 subdivides each tongue
# gap into 13 Fibonacci sub-steps, capturing the dead tones within error
# < 0.003 of their true ratios.
#
# These ambient notes are "free-floating" — they belong to no single tongue
# but exist in the gallery between the paintings.
#

PHI_13 = PHI ** (1.0 / 13.0)  # 1.0377099294 — the attunement number

# Dead tone ratios (just intonation, exact)
DEAD_TONE_FIFTH = 3.0 / 2.0  # 1.500 — dependency
DEAD_TONE_SIXTH = 8.0 / 5.0  # 1.600 — near-miss (0.018 from phi)
DEAD_TONE_SEVENTH = 16.0 / 9.0  # 1.778 — urgency

# Phi-13 step positions that capture each dead tone
# (from log_phi(ratio) analysis: which phi^(k/13) step hits closest)
DEAD_TONE_PHI13_STEPS = {
    "perfect_fifth": 11,  # phi^(11/13) ≈ 1.4973, err 0.0027
    "minor_sixth": 12,  # phi^(12/13) ≈ 1.5529, err 0.047 (worst; needs pair coupling)
    "minor_seventh": 15,  # phi^(15/13) ≈ 1.7740, err 0.004
}

# Cross-axis tongue pairs that produce each dead tone via interference
DEAD_TONE_AXIS_COUPLINGS = {
    "perfect_fifth": ("structure", "stability"),  # DR/KO × AV/UM
    "minor_sixth": ("stability", "creativity"),  # AV/UM × RU/CA
    "minor_seventh": ("creativity", "structure"),  # RU/CA × DR/KO
}

# Sacred Tongue hybrid phrases for dead-tone recovery (from autorotation mapping)
DEAD_TONE_HYBRIDS = {
    "perfect_fifth": {
        "tongues": ["dr", "av"],
        "hybrid": "Draum'vhari",
        "meaning": "forge-wisdom (structure anchoring equilibrium)",
        "sensory": "heavy resonant stone meeting cool diplomatic flow",
    },
    "minor_sixth": {
        "tongues": ["av", "ca"],
        "hybrid": "Avhari'siva",
        "meaning": "wisdom-invention (equilibrium approaching novelty)",
        "sensory": "cool aquamarine shimmer with copper-cardamom undertone",
    },
    "minor_seventh": {
        "tongues": ["ca", "ko", "um"],
        "hybrid": "Cassiv'broth",
        "meaning": "invention-shadow (novelty demanding structure through survival)",
        "sensory": "copper spark dissolving into half-tone echoes — urgency",
    },
}

# Autorotation recovery: the gallery-mode hybrid for total phi-geometry failure
AUTOROTATION_HYBRID = {
    "tongues": ["dr", "ca", "um"],
    "hybrid": "Draum'broth + Cassisivadan",
    "meaning": "forge + shadow + inventive spark — controlled descent from VRS",
    "sensory": "heavy resonant stone/steam with echoing half-tones and sudden copper-cardamom bursts",
    "physics": "collective to zero, forward cyclic for RPM, flare at touchdown",
    "code_analogy": "graceful shutdown: surrender power intentionally, forge forward motion, invent final spark",
}


@dataclass
class GalleryAmbientNote:
    """A single dead-tone ambient note from cross-axis interference.

    These notes exist in the 'gallery' between tongues — free-floating
    tones that no single tongue can produce but emerge from axis coupling.
    """

    dead_tone: str  # "perfect_fifth" | "minor_sixth" | "minor_seventh"
    target_ratio: float  # the exact just-intonation ratio
    observed_ratio: float  # the actual cross-axis interference ratio
    deviation: float  # |observed - target| — smaller = closer to blind spot
    coupling_strength: float  # [0, 1] how strongly the two axes are coupled
    axis_pair: Tuple[str, str]  # which trit axes are interfering
    tongue_pair: Tuple[str, str]  # dominant tongue from each axis
    phi_13_step: int  # nearest phi^(k/13) attunement step
    phi_13_error: float  # error from phi^(k/13) to target ratio
    blind_spot_proximity: float  # [0, 1] how close to the actual blind spot (1 = dead center)
    hybrid_name: str  # Sacred Tongue hybrid for this dead tone
    security_implication: str  # what this blind spot means for governance


@dataclass
class GalleryAmbient:
    """The full gallery ambient layer — three dead-tone interference signals.

    This is the "missing link" between phi-geometry and the intervals it
    cannot produce. The gallery fills the lattice gaps the same way dark
    matter fills gravitational gaps.

    When all three dead tones are active simultaneously, the record is at
    the autorotation boundary — total phi-geometry failure requiring the
    Draum'broth + Cassisivadan hybrid recovery path.
    """

    notes: Dict[str, GalleryAmbientNote]  # keyed by dead_tone name
    autorotation_active: bool  # True when all 3 dead tones are strong
    gallery_energy: float  # total cross-axis interference energy
    dominant_dead_tone: str  # which blind spot is most active
    recovery_hybrid: str  # Sacred Tongue hybrid for current state

    @property
    def fifth_strength(self) -> float:
        """Strength of perfect fifth (dependency) blind spot signal."""
        return self.notes.get(
            "perfect_fifth",
            GalleryAmbientNote(
                "perfect_fifth", 1.5, 1.0, 0.5, 0.0, ("structure", "stability"), ("dr", "av"), 11, 0.003, 0.0, "", ""
            ),
        ).coupling_strength

    @property
    def sixth_strength(self) -> float:
        """Strength of minor sixth (near-miss) blind spot signal."""
        return self.notes.get(
            "minor_sixth",
            GalleryAmbientNote(
                "minor_sixth", 1.6, 1.0, 0.6, 0.0, ("stability", "creativity"), ("av", "ca"), 12, 0.047, 0.0, "", ""
            ),
        ).coupling_strength

    @property
    def seventh_strength(self) -> float:
        """Strength of minor seventh (urgency) blind spot signal."""
        return self.notes.get(
            "minor_seventh",
            GalleryAmbientNote(
                "minor_seventh",
                1.778,
                1.0,
                0.778,
                0.0,
                ("creativity", "structure"),
                ("ca", "dr"),
                15,
                0.004,
                0.0,
                "",
                "",
            ),
        ).coupling_strength

    def to_dict(self) -> dict:
        return {
            "notes": {
                k: {
                    "dead_tone": n.dead_tone,
                    "target_ratio": round(n.target_ratio, 6),
                    "observed_ratio": round(n.observed_ratio, 6),
                    "deviation": round(n.deviation, 6),
                    "coupling_strength": round(n.coupling_strength, 6),
                    "axis_pair": list(n.axis_pair),
                    "tongue_pair": list(n.tongue_pair),
                    "phi_13_step": n.phi_13_step,
                    "phi_13_error": round(n.phi_13_error, 6),
                    "blind_spot_proximity": round(n.blind_spot_proximity, 6),
                    "hybrid_name": n.hybrid_name,
                    "security_implication": n.security_implication,
                }
                for k, n in self.notes.items()
            },
            "autorotation_active": self.autorotation_active,
            "gallery_energy": round(self.gallery_energy, 6),
            "dominant_dead_tone": self.dominant_dead_tone,
            "recovery_hybrid": self.recovery_hybrid,
        }


# Axis → tongue pairs (used by all three detectors)
_AXIS_TONGUES = {
    "structure": ("ko", "dr"),
    "stability": ("av", "um"),
    "creativity": ("ru", "ca"),
}


def _cross_axis_ratio(
    qho: PolychromaticState,
    trit: "TritSignal",
    axis_a: str,
    axis_b: str,
    dead_tone: str,
) -> Tuple[float, float, str, str]:
    """Compute cross-axis interference for a specific dead tone.

    Each dead tone uses its own biological detection model, because each
    represents a fundamentally different failure mode. "Not every layer
    needs to be the same — they just need to be interpretable by the
    system that runs it and those that use it."

    Perfect fifth (dependency) — Lotka-Volterra predator-prey dynamics:
        Structure and stability oscillate. When the prey/predator ratio
        locks to 3:2, one agent gates another in an invisible loop.
        Ratio = 1 + (prey_pop / (prey_pop + predator_pop))
        Range: [1.0, 2.0], clusters near 1.5 when populations balance.

    Minor sixth (near-miss) — immune self/non-self discrimination:
        How close is this record to being "harmonic" (self) vs adversarial
        (non-self)? Uses the MHC-like presentation distance from phi.
        Ratio = phi * (1 - antigen_distance) where antigen is the axis
        imbalance. Range: [1.0, phi], clusters near 1.6 for balanced axes.

    Minor seventh (urgency) — sympathetic fight-or-flight ratio:
        When creativity outpaces structure faster than recovery allows,
        the system hits the urgency dead zone. Adrenaline model:
        Ratio = 1 + sympathetic/parasympathetic (creativity/structure).
        Range: [1.0, ~3.0], octave-folds to [1.0, 2.0], hits 1.778
        when creativity dominates at ~1.78x structure.

    Returns: (ratio, coupling_strength, tongue_a, tongue_b)
    """
    pair_a = _AXIS_TONGUES[axis_a]
    pair_b = _AXIS_TONGUES[axis_b]

    t_a = max(pair_a, key=lambda t: qho.states[t].coefficient)
    t_b = max(pair_b, key=lambda t: qho.states[t].coefficient)

    # Axis deviations (signed and absolute)
    devs = {
        "structure": trit.dev_structure,
        "stability": trit.dev_stability,
        "creativity": trit.dev_creativity,
    }
    abs_a = abs(devs[axis_a])
    abs_b = abs(devs[axis_b])

    # QHO activations for coupling strength
    act_a = sum(qho.states[t].coefficient for t in pair_a)
    act_b = sum(qho.states[t].coefficient for t in pair_b)
    coupling = math.sqrt(act_a * act_b)

    if dead_tone == "perfect_fifth":
        # Lotka-Volterra predator-prey with strong phase sensitivity.
        # Phase (signed difference) drives the ratio across a wide range
        # using arctan for smooth, broad mapping.
        phase = devs[axis_a] - devs[axis_b]
        # arctan maps (-inf, +inf) to (-pi/2, pi/2), normalized to (-1, 1)
        phase_norm = math.atan(phase * 15.0) / (math.pi / 2.0)
        ratio = 1.5 + 0.45 * phase_norm
        # Range: [1.05, 1.95], centered at 1.5 with wide tails

    elif dead_tone == "minor_sixth":
        # Immune self/non-self discrimination.
        # Cross-product of signed deviations is the antigen signature.
        # Concordant deviations (same sign) → closer to phi → dangerous.
        # Discordant (opposite sign) → further → detectable.
        cross = devs[axis_a] * devs[axis_b]
        ratio = 1.6 + 0.35 * math.tanh(cross * 40.0)
        # Range: [1.25, 1.95], centered at 1.6

    elif dead_tone == "minor_seventh":
        # Perpendicular echo sonar: the inverse response of the
        # cross-axis sound field. When the direct path (creativity →
        # structure) is weak, the perpendicular echo is strong.
        # S_perp = phi / (|E(tangent)| + eps)
        tangent = abs(devs["creativity"]) / (abs(devs["structure"]) + 0.005)
        echo_mag = PHI / (abs(tangent) + 0.01)
        cortisol = 0.1 * math.tanh(devs["stability"] * 20.0)
        echo_norm = min(echo_mag, 5.0) / 5.0  # [0, 1]
        ratio = 1.0 + echo_norm * 0.778 + cortisol
        # structure >> creativity → echo loud → ratio near 1.778

    else:
        # Fallback: generic metabolic ratio
        K_m = 0.03
        ratio = 1.0 + abs_a / (abs_b + K_m)
        while ratio >= 2.0:
            ratio /= 2.0

    # Clamp to [1.0, 2.0) octave
    while ratio >= 2.0:
        ratio /= 2.0
    ratio = max(1.0, ratio)

    return ratio, coupling, t_a, t_b


def compute_gallery_ambient(
    qho: PolychromaticState,
    trit: "TritSignal",
) -> GalleryAmbient:
    """Derive the gallery ambient layer from cross-axis interference.

    For each dead tone, computes:
    1. The cross-axis frequency ratio between the two coupled axes
    2. How close that ratio is to the dead-tone target
    3. The coupling strength (how strongly both axes are active)
    4. The blind spot proximity (closer = more governance-invisible)
    5. The Sacred Tongue hybrid for recovery

    When all three dead tones are strongly active (coupling > 0.3 AND
    blind_spot_proximity > 0.5), the record triggers autorotation mode —
    total phi-geometry failure requiring multi-axis hybrid recovery.
    """
    notes: Dict[str, GalleryAmbientNote] = {}
    dead_tone_configs = {
        "perfect_fifth": DEAD_TONE_FIFTH,
        "minor_sixth": DEAD_TONE_SIXTH,
        "minor_seventh": DEAD_TONE_SEVENTH,
    }

    security_implications = {
        "perfect_fifth": "Invisible dependency chains — one agent gates another at 3:2 power ratio, undetectable by phi-tuned governance",
        "minor_sixth": "Adversarial sweet spot — input is 0.018 from phi, passes harmonic wall at cost ~1.0002 but is NOT harmonic",
        "minor_seventh": "Urgency blind spot — state demands immediate transition but signal falls between ESCALATE and DENY thresholds",
    }

    for tone_name, target in dead_tone_configs.items():
        axis_a, axis_b = DEAD_TONE_AXIS_COUPLINGS[tone_name]
        ratio, coupling, t_a, t_b = _cross_axis_ratio(qho, trit, axis_a, axis_b, tone_name)

        deviation = abs(ratio - target)
        # Blind spot proximity: each dead tone has its own sensitivity scale.
        # The biological models produce different deviation distributions, so
        # a uniform exp(-10*d) would always favor whichever model lands closest.
        # Instead, calibrate per-tone so each produces a ~[0, 1] threat score.
        #
        # Perfect fifth (LV): typical deviation 0.0-0.15, use scale 5
        # Minor sixth (immune): typical deviation 0.0-0.3, use scale 3
        # Minor seventh (fight/flight): typical deviation 0.0-0.4, use scale 2.5
        _TONE_SENSITIVITY = {
            "perfect_fifth": 5.0,  # tighter: dependency locks are precise
            "minor_sixth": 3.0,  # moderate: immune boundaries are fuzzy
            "minor_seventh": 2.5,  # broad: urgency is a gradient, not a cliff
        }
        sensitivity = _TONE_SENSITIVITY.get(tone_name, 10.0)
        blind_spot_proximity = math.exp(-sensitivity * deviation)

        # Scale coupling by axis deviations — larger axis movement = stronger signal
        axis_devs = {
            "structure": abs(trit.dev_structure),
            "stability": abs(trit.dev_stability),
            "creativity": abs(trit.dev_creativity),
        }
        axis_factor = (axis_devs[axis_a] + axis_devs[axis_b]) / 0.3  # normalize
        adjusted_coupling = min(1.0, coupling * max(0.1, axis_factor))

        # Phi-13 step
        step = DEAD_TONE_PHI13_STEPS[tone_name]
        phi13_value = PHI ** (step / 13.0)
        phi13_error = abs(phi13_value - target)

        hybrid_info = DEAD_TONE_HYBRIDS[tone_name]

        notes[tone_name] = GalleryAmbientNote(
            dead_tone=tone_name,
            target_ratio=target,
            observed_ratio=ratio,
            deviation=deviation,
            coupling_strength=adjusted_coupling,
            axis_pair=(axis_a, axis_b),
            tongue_pair=(t_a, t_b),
            phi_13_step=step,
            phi_13_error=phi13_error,
            blind_spot_proximity=blind_spot_proximity,
            hybrid_name=hybrid_info["hybrid"],
            security_implication=security_implications[tone_name],
        )

    # Autorotation check: all three dead tones strongly active
    strong_count = sum(1 for n in notes.values() if n.coupling_strength > 0.3 and n.blind_spot_proximity > 0.5)
    autorotation_active = strong_count >= 2  # 2 of 3 is enough for VRS-like state

    # Total gallery energy = sum of coupling × proximity
    gallery_energy = sum(n.coupling_strength * n.blind_spot_proximity for n in notes.values())

    # Dominant dead tone = highest coupling × proximity product
    dominant = max(notes.values(), key=lambda n: n.coupling_strength * n.blind_spot_proximity)

    # Recovery hybrid selection
    if autorotation_active:
        recovery_hybrid = AUTOROTATION_HYBRID["hybrid"]
    else:
        recovery_hybrid = DEAD_TONE_HYBRIDS[dominant.dead_tone]["hybrid"]

    return GalleryAmbient(
        notes=notes,
        autorotation_active=autorotation_active,
        gallery_energy=gallery_energy,
        dominant_dead_tone=dominant.dead_tone,
        recovery_hybrid=recovery_hybrid,
    )


# ---------------------------------------------------------------------------
# VRS State (Vortex Ring State — helicopter physics bridge)
# ---------------------------------------------------------------------------


@dataclass
class VRSState:
    """Vortex Ring State derived from QHO excitation + trit stability.

    Real physics (momentum theory):
        v_i = sqrt(T / 2ρA)   — induced velocity
        VRS onset: v_descent ≈ 0.7·v_i to 1.5·v_i
        Power spike: P = T·v_i + P_profile + P_parasite

    Mapping from SCBE pipeline:
        Descent rate ← trit stability axis (negative = descending)
        Induced velocity ← QHO mean excitation → rotor RPM
        VRS margin ← ratio of descent to induced velocity
        Recovery paths ← polymorphic fork count → Monty Hall selection
    """

    in_vrs: bool
    vrs_margin: float  # 1.0=safe, 0.0=onset, <0=deep VRS
    descent_rate_ms: float  # m/s vertical descent
    induced_velocity_ms: float  # m/s momentum theory hover downwash
    rotor: RotorState
    recovery_paths: List[RecoveryPath]
    flight_regime: str  # hover / cruise / descent / vrs / departure / tail_rotor_failure
    tail_rotor: Optional[TailRotorState] = None
    pacejka: Optional[PacejkaTireState] = None

    @property
    def vrs_ratio(self) -> float:
        """v_descent / v_i — the core VRS diagnostic."""
        if self.induced_velocity_ms < 1e-6:
            return 0.0
        return abs(self.descent_rate_ms) / self.induced_velocity_ms

    @property
    def power_spike_factor(self) -> float:
        """How much induced power spikes in VRS relative to hover.
        In the VRS zone, power required can double or triple.
        """
        ratio = self.vrs_ratio
        if ratio < 0.7:
            return 1.0
        elif ratio < 1.5:
            # Power spikes parabolically in VRS zone
            normalized = (ratio - 0.7) / 0.8
            return 1.0 + 2.0 * normalized**2
        else:
            return 3.0  # deep VRS: ~3x hover power

    @property
    def best_recovery(self) -> Optional[RecoveryPath]:
        """Highest success probability recovery path."""
        if not self.recovery_paths:
            return None
        return max(self.recovery_paths, key=lambda p: p.success_probability)

    def to_dict(self) -> dict:
        d = {
            "in_vrs": self.in_vrs,
            "vrs_margin": round(self.vrs_margin, 4),
            "vrs_ratio": round(self.vrs_ratio, 4),
            "descent_rate_ms": round(self.descent_rate_ms, 2),
            "induced_velocity_ms": round(self.induced_velocity_ms, 2),
            "power_spike_factor": round(self.power_spike_factor, 4),
            "flight_regime": self.flight_regime,
            "rotor": self.rotor.to_dict(),
            "recovery_paths": [p.to_dict() for p in self.recovery_paths],
        }
        if self.tail_rotor:
            d["tail_rotor"] = self.tail_rotor.to_dict()
        if self.pacejka:
            d["pacejka"] = self.pacejka.to_dict()
        return d


def compute_vrs_state(
    qho: PolychromaticState,
    trit: "TritSignal",
    mp: "MultiPathRecord",
) -> VRSState:
    """Derive VRS state from QHO excitation + trit stability axis.

    Physics bridge:
        Mean excitation → rotor RPM (higher n = faster rotor)
        Stability deviation → descent rate (negative stability = descent)
        Polymorphic forks → recovery path options
        Altitude from max excitation (n=0 → ground, n=7 → 10km)
    """
    mean_n = qho.mean_excitation
    max_n = qho.max_excitation
    from src.crypto.flight_dynamics import (
        RotorState,
        compute_pacejka_state,
        compute_recovery_paths,
        compute_tail_rotor_state,
    )

    # Rotor RPM from mean excitation: idle=200, max=320 RPM
    rpm = 200.0 + mean_n * 17.14  # scales 0-7 to 200-320
    rotor = RotorState(rotor_rpm=rpm)

    # Descent rate from stability axis: negative = descending
    # Scale: dev_stability of -0.15 → ~6 m/s descent
    descent_rate = max(0.0, -trit.dev_stability * 40.0)

    # Induced velocity from rotor state
    vi = rotor.induced_velocity

    # VRS margin
    margin = rotor.vrs_margin(descent_rate)

    # Altitude from max excitation (0→0m, 7→10000m)
    altitude = max_n * (10000.0 / 7.0)

    # Tail rotor failure from creativity axis
    tail_rotor = compute_tail_rotor_state(rotor, trit.dev_creativity)

    # Pacejka tire model for ground state (n=0, the egg)
    pacejka = None
    if max_n == 0:
        pacejka = compute_pacejka_state(trit.dev_structure)

    # Flight regime classification
    if tail_rotor.failed:
        regime = "tail_rotor_failure"
    elif margin < 0:
        regime = "departure"  # deep VRS
    elif margin < 0.3:
        regime = "vrs"
    elif descent_rate > 2.0:
        regime = "descent"
    elif descent_rate < 0.5 and mean_n < 2:
        regime = "hover"
    elif max_n == 0:
        regime = "ground"
    else:
        regime = "cruise"

    # Recovery paths (only computed when near VRS boundary or tail rotor failure)
    recovery_paths = []
    if margin < 0.8 or tail_rotor.failed:
        recovery_paths = compute_recovery_paths(
            margin,
            altitude,
            mp,
            tail_rotor_failed=tail_rotor.failed,
        )

    in_vrs = margin < 0.3

    return VRSState(
        in_vrs=in_vrs,
        vrs_margin=margin,
        descent_rate_ms=descent_rate,
        induced_velocity_ms=vi,
        rotor=rotor,
        recovery_paths=recovery_paths,
        flight_regime=regime,
        tail_rotor=tail_rotor,
        pacejka=pacejka,
    )


# ---------------------------------------------------------------------------
# Code Lattice Layer (anti-patterns as "swear words" with severity)
# ---------------------------------------------------------------------------

# Coding anti-pattern registry — each maps to a flight/physics analogy
CODE_ANTI_PATTERNS = {
    "unhandled_exception_in_critical_path": {
        "description": "Sudden collapse at high load — VRS entry when error hits critical section",
        "physics_analogy": "VRS: recirculating vortex ring collapses lift",
        "recovery_example": (
            "# Good: explicit recovery path (Vuichard-style)\n"
            "try:\n"
            "    critical_operation(data)\n"
            "except SpecificError as e:\n"
            "    return vuichard_recovery(e)  # lateral cyclic equivalent\n"
            "else:\n"
            "    return clean_airflow(data)"
        ),
    },
    "mutable_global_state": {
        "description": "Pollutes the entire lattice like uncontrolled rotor torque",
        "physics_analogy": "Torque imbalance: anti-torque pedal failure → uncontrolled yaw",
        "recovery_example": (
            "# Bad: global mutable\n"
            "STATE = {}\n"
            "# Good: pure function with explicit intent\n"
            "def pure_operation(input_state: dict) -> dict:\n"
            "    return {**input_state, 'new_key': compute(input_state)}"
        ),
    },
    "null_check_in_hot_path": {
        "description": "Defensive null checks where types guarantee non-null — drag coefficient without lift",
        "physics_analogy": "Parasitic drag: C_D0 penalty with no lift benefit",
        "recovery_example": (
            "# Bad: null check where type guarantees value\n"
            "if data is not None and data.value is not None:\n"
            "    process(data.value)\n"
            "# Good: trust the type system\n"
            "process(data.value)  # data: NonNullData (type-guaranteed)"
        ),
    },
    "unbounded_recursion": {
        "description": "Stack overflow as VRS spiral — each call descends deeper into the vortex",
        "physics_analogy": "VRS descent spiral: each revolution loses more altitude",
        "recovery_example": (
            "# Bad: unbounded\n"
            "def process(n): return process(n-1)\n"
            "# Good: bounded with explicit base case\n"
            "def process(n, depth=0, max_depth=100):\n"
            "    if depth >= max_depth or n <= 0:\n"
            "        return base_case()\n"
            "    return process(n-1, depth+1, max_depth)"
        ),
    },
    "fire_and_forget_async": {
        "description": "Unmonitored async task — like autorotation without monitoring rotor RPM",
        "physics_analogy": "Autorotation: must monitor Nr (rotor RPM) or rotor stalls",
        "recovery_example": (
            "# Bad: fire and forget\n"
            "asyncio.create_task(do_work())\n"
            "# Good: monitored with recovery\n"
            "task = asyncio.create_task(do_work())\n"
            "task.add_done_callback(handle_result_or_failure)"
        ),
    },
    "implicit_type_coercion": {
        "description": "Silent type conversion — cyclic/collective mismatch in control inputs",
        "physics_analogy": "Control cross-coupling: cyclic input read as collective → unexpected climb/dive",
        "recovery_example": (
            "# Bad: implicit coercion\n"
            "result = str_value + int_value  # silent concatenation or addition?\n"
            "# Good: explicit conversion\n"
            "result = int(str_value) + int_value  # intent is clear"
        ),
    },
}


@dataclass
class CodeAntiPattern:
    """A coding anti-pattern ('swear word') with severity from QHO physics."""

    name: str
    severity: float  # 0-1, derived from monty_hall_gain + qho excitation
    description: str
    physics_analogy: str
    recovery_example: str
    linked_vrs: bool  # maps to VRS-like collapse pattern


@dataclass
class CodeLatticeState:
    """The living coding world layer — intentions compound here.

    System intent (physics + governance) × learner intent (text semantics)
    builds higher energy states exactly like QHO creation/annihilation.

    Curriculum levels:
        L0: Raw observation (ground state, no anti-patterns)
        L1: Single excitation + frequency tagging
        L2: Boundary detection + polymorphic forks
        L3: QHO excitation + VRS entry (high-n unstable)
        L4: Multi-path recovery + code lattice
        L5: Full lattice generalization + cross-domain transfer
    """

    anti_patterns: List[CodeAntiPattern]
    compounding_intent_score: float  # system_intent × learner_intent / normalization
    curriculum_difficulty: float  # 0-1, derived from all signals
    curriculum_level: int  # 0-5, progressive abstraction
    cross_domain_mapping: str  # e.g. "VRS → deadlock recovery"

    @property
    def total_severity(self) -> float:
        """Sum of all anti-pattern severities."""
        return sum(ap.severity for ap in self.anti_patterns)

    @property
    def swear_word_count(self) -> int:
        """Number of active 'swear words' (anti-patterns)."""
        return len(self.anti_patterns)

    def to_dict(self) -> dict:
        return {
            "anti_patterns": [
                {
                    "name": ap.name,
                    "severity": round(ap.severity, 4),
                    "description": ap.description,
                    "physics_analogy": ap.physics_analogy,
                    "recovery_example": ap.recovery_example,
                    "linked_vrs": ap.linked_vrs,
                }
                for ap in self.anti_patterns
            ],
            "compounding_intent_score": round(self.compounding_intent_score, 4),
            "curriculum_difficulty": round(self.curriculum_difficulty, 4),
            "curriculum_level": self.curriculum_level,
            "cross_domain_mapping": self.cross_domain_mapping,
            "total_severity": round(self.total_severity, 4),
            "swear_word_count": self.swear_word_count,
        }


def compute_code_lattice(
    qho: PolychromaticState,
    mp: "MultiPathRecord",
    vrs: VRSState,
) -> CodeLatticeState:
    """Derive code lattice state from pipeline outputs.

    Anti-patterns trigger based on QHO excitation + Monty Hall gain + VRS state.
    Higher excitation + higher gain = more anti-patterns with higher severity.
    """
    gain = mp.monty_hall_advantage
    max_n = qho.max_excitation
    qho.mean_excitation

    anti_patterns = []

    # Swear word 1: unhandled_exception_in_critical_path
    # Triggers at high gain + high excitation (VRS-like boundary)
    if gain > 0.3 and max_n >= 4:
        ap = CODE_ANTI_PATTERNS["unhandled_exception_in_critical_path"]
        anti_patterns.append(
            CodeAntiPattern(
                name="unhandled_exception_in_critical_path",
                severity=min(1.0, gain * 1.2 + (max_n - 4) * 0.1),
                description=ap["description"],
                physics_analogy=ap["physics_analogy"],
                recovery_example=ap["recovery_example"],
                linked_vrs=True,
            )
        )

    # Swear word 2: mutable_global_state
    # Triggers when creativity axis has high deviation (creative = risky mutations)
    if mp.forks and any(f.axis == "creativity" for f in mp.forks):
        ap = CODE_ANTI_PATTERNS["mutable_global_state"]
        anti_patterns.append(
            CodeAntiPattern(
                name="mutable_global_state",
                severity=0.85,
                description=ap["description"],
                physics_analogy=ap["physics_analogy"],
                recovery_example=ap["recovery_example"],
                linked_vrs=False,
            )
        )

    # Swear word 3: null_check_in_hot_path
    # Triggers at mid excitation with low gain (stable but wasteful)
    if 2 <= max_n <= 4 and gain < 0.2:
        ap = CODE_ANTI_PATTERNS["null_check_in_hot_path"]
        anti_patterns.append(
            CodeAntiPattern(
                name="null_check_in_hot_path",
                severity=0.4 + max_n * 0.05,
                description=ap["description"],
                physics_analogy=ap["physics_analogy"],
                recovery_example=ap["recovery_example"],
                linked_vrs=False,
            )
        )

    # Swear word 4: unbounded_recursion
    # Triggers when in VRS (the spiral descent analogy is exact)
    if vrs.in_vrs:
        ap = CODE_ANTI_PATTERNS["unbounded_recursion"]
        anti_patterns.append(
            CodeAntiPattern(
                name="unbounded_recursion",
                severity=min(1.0, 0.7 + abs(vrs.vrs_margin) * 0.3),
                description=ap["description"],
                physics_analogy=ap["physics_analogy"],
                recovery_example=ap["recovery_example"],
                linked_vrs=True,
            )
        )

    # Swear word 5: fire_and_forget_async
    # Triggers at high excitation with multiple forks (many async paths)
    if max_n >= 5 and len(mp.forks) >= 2:
        ap = CODE_ANTI_PATTERNS["fire_and_forget_async"]
        anti_patterns.append(
            CodeAntiPattern(
                name="fire_and_forget_async",
                severity=min(1.0, 0.6 + len(mp.forks) * 0.15),
                description=ap["description"],
                physics_analogy=ap["physics_analogy"],
                recovery_example=ap["recovery_example"],
                linked_vrs=False,
            )
        )

    # Swear word 6: implicit_type_coercion
    # Triggers when stability and structure axes have opposite polarity (cross-coupling)
    if mp.forks and len(mp.forks) >= 2:
        axes = [f.axis for f in mp.forks]
        if "structure" in axes and "stability" in axes:
            ap = CODE_ANTI_PATTERNS["implicit_type_coercion"]
            anti_patterns.append(
                CodeAntiPattern(
                    name="implicit_type_coercion",
                    severity=0.65,
                    description=ap["description"],
                    physics_analogy=ap["physics_analogy"],
                    recovery_example=ap["recovery_example"],
                    linked_vrs=False,
                )
            )

    # Compounding intent score (system × learner)
    system_intent = qho.phi_weighted_total_energy
    learner_intent = gain * (max_n + 1)
    compounding_score = system_intent * learner_intent / max(1e-30, 1000.0)

    # Curriculum difficulty: combine VRS margin, gain, excitation, anti-pattern count
    vrs_factor = max(0.0, 1.0 - vrs.vrs_margin) if vrs.vrs_margin < 1.0 else 0.0
    difficulty = min(
        1.0,
        (
            0.2 * (max_n / 7.0)  # excitation contribution
            + 0.25 * gain  # Monty Hall contribution
            + 0.3 * vrs_factor  # VRS proximity contribution
            + 0.25 * min(1.0, len(anti_patterns) / 3.0)  # anti-pattern density
        ),
    )

    # Curriculum level (progressive abstraction)
    if max_n == 0 and not mp.forks:
        level = 0  # ground state, no forks
    elif max_n <= 2 and not mp.forks:
        level = 1  # low excitation, stable
    elif mp.forks and not vrs.in_vrs:
        level = 2  # boundary detection, polymorphic
    elif max_n >= 4 and not vrs.in_vrs:
        level = 3  # high excitation, pre-VRS
    elif vrs.in_vrs or vrs.recovery_paths:
        level = 4  # VRS + recovery paths
    else:
        level = 2  # default mid-level

    # Upgrade to L5 if all signals are high (expert territory)
    if difficulty > 0.85 and len(anti_patterns) >= 2 and vrs.recovery_paths:
        level = 5

    # Cross-domain mapping based on state
    if vrs.in_vrs:
        mapping = "VRS recovery → graceful error handling in async code"
    elif vrs.flight_regime == "descent":
        mapping = "Controlled descent → resource cleanup / shutdown sequence"
    elif mp.forks and gain > 0.5:
        mapping = "Polymorphic fork → strategy pattern with runtime selection"
    elif max_n >= 5:
        mapping = "High excitation → performance-critical hot path optimization"
    elif max_n == 0:
        mapping = "Ground state → idempotent function design (no side effects)"
    else:
        mapping = "Stable hover → defensive programming with bounded inputs"

    return CodeLatticeState(
        anti_patterns=anti_patterns,
        compounding_intent_score=compounding_score,
        curriculum_difficulty=difficulty,
        curriculum_level=level,
        cross_domain_mapping=mapping,
    )


# ---------------------------------------------------------------------------
# Gallery Ambient Notes (dead tone fills)
# ---------------------------------------------------------------------------
# The 3 dead tones (perfect fifth 3:2, minor sixth 8:5, minor seventh 16:9)
# are geometrically unreachable by pure phi scaling. Gallery ambient notes
# fill these gaps via multi-tongue interference — free-floating tones in
# the space between tongues, generated by multi-tongue chord combinations.

# Dead tones and their ratios (from INTERVALS in harmonic_dark_fill.py)
DEAD_TONES = {
    "perfect_fifth": 3.0 / 2.0,  # 1.500 — strongest consonance
    "minor_sixth": 8.0 / 5.0,  # 1.600 — inverted major third
    "minor_seventh": 16.0 / 9.0,  # 1.778 — dominant tension
}

# Which tongue couplings generate each dead tone through interference
DEAD_TONE_GENERATORS = {
    "perfect_fifth": ["run_dr", "ko_ru", "dr_um_ca"],
    "minor_sixth": ["ko_um", "av_um", "dr_um_ca"],
    "minor_seventh": ["ru_um", "ca_um", "dr_um_ca"],
}


@dataclass
class DeadToneFill:
    """Free-floating tone in the space between tongues that fills dead-tone gaps.

    Dead tones cannot be reached by direct phi scaling of any single tongue.
    They emerge only from multi-tongue interference — the gallery fills them.

    The DR+UM+CA autorotation hybrid (generating_couplings) is the chord
    that resonates at all three dead tones through combination.
    """

    interval_name: str  # "perfect_fifth", "minor_sixth", "minor_seventh"
    ratio: float  # target ratio (e.g. 1.5)
    achieved_ratio: float  # actual ratio from interference
    error_from_dead_tone: float  # |achieved - target|
    generating_couplings: List[str]  # e.g. ["run_dr", "dr_um_ca"]
    intensity: float  # 0-1, how strongly this note resonates

    def to_dict(self) -> dict:
        return {
            "interval_name": self.interval_name,
            "ratio": round(self.ratio, 4),
            "achieved_ratio": round(self.achieved_ratio, 4),
            "error_from_dead_tone": round(self.error_from_dead_tone, 6),
            "generating_couplings": self.generating_couplings,
            "intensity": round(self.intensity, 4),
        }


def compute_dead_tone_fills(
    qho: PolychromaticState,
    acoustic: AcousticSignature,
) -> List[DeadToneFill]:
    """Compute gallery ambient notes from tongue-pair interference.

    For each dead tone, we compute the nearest achievable ratio from
    the interference of the generating tongue couplings. The intensity
    depends on the excitation levels of the participating tongues.

    Higher QHO excitation = stronger gallery notes (more energy to fill gaps).
    """
    notes = []

    for name, target in DEAD_TONES.items():
        couplings = DEAD_TONE_GENERATORS[name]

        # Achieved ratio from tongue-pair interference
        # Use the dominant interval's deviation to shift toward the dead tone
        deviation = acoustic.interval_deviation
        achieved = target + deviation * 0.01  # small perturbation from exact

        # Intensity from participating tongue excitation levels
        # Extract tongue names from coupling labels
        participating = set()
        for c in couplings:
            parts = c.split("_")
            for p in parts:
                if p in TONGUE_ORDER:
                    participating.add(p)

        if participating:
            mean_n = sum(qho.states[t].n for t in participating) / len(participating)
            intensity = min(1.0, mean_n / 4.0)  # n=4+ → full intensity
        else:
            intensity = 0.1

        notes.append(
            DeadToneFill(
                interval_name=name,
                ratio=target,
                achieved_ratio=achieved,
                error_from_dead_tone=abs(achieved - target),
                generating_couplings=couplings,
                intensity=intensity,
            )
        )

    return notes


# ---------------------------------------------------------------------------
# Echolocation Ping Layer (active dead-tone probing)
# ---------------------------------------------------------------------------
# Sends short acoustic "pings" into the tongue lattice, measures reflections
# from dead-tone zones. This is active sonar — not passive observation.
#
# Real physics:
#   Ping: short broadband impulse (infra + audible + ultra)
#   Return amplitude: low = dead tone absorption
#   Phase distortion: high = gallery boundary (near phi edge)
#   Time-of-flight: delay ∝ distance to dead zone in phi-space


@dataclass
class EcholocationPing:
    """Active ping into the tongue lattice measuring dead-tone reflections."""

    target_dead_tone: str  # which dead tone we're probing
    ping_frequency_hz: float  # center frequency of the impulse
    return_amplitude: float  # 0-1, low = absorbed by dead zone
    phase_distortion_rad: float  # phase shift at reflection boundary
    time_of_flight_s: float  # delay to reflection (phi-space distance)
    gallery_fill_coupling: List[str]  # which couplings fill this dead tone
    detected: bool  # did we detect the dead tone?

    def to_dict(self) -> dict:
        return {
            "target_dead_tone": self.target_dead_tone,
            "ping_frequency_hz": round(self.ping_frequency_hz, 1),
            "return_amplitude": round(self.return_amplitude, 4),
            "phase_distortion_rad": round(self.phase_distortion_rad, 4),
            "time_of_flight_s": round(self.time_of_flight_s, 6),
            "gallery_fill_coupling": self.gallery_fill_coupling,
            "detected": self.detected,
        }


def send_echolocation_pings(
    qho: PolychromaticState,
    acoustic: AcousticSignature,
) -> List[EcholocationPing]:
    """Send acoustic pings and measure dead-tone reflections.

    Each dead tone has a characteristic reflection signature:
      - Perfect fifth (3:2): low return + moderate phase lag
      - Minor sixth (8:5): near-zero return + high phase distortion (phi edge)
      - Minor seventh (16:9): echo-harmonic ring + urgency spike

    The phi proximity (|ratio - PHI|) determines absorption:
      closer to PHI → more absorption → lower return amplitude.
    """
    pings = []

    # Base frequency from dominant tongue
    dominant = qho.dominant_tongue
    base_freq = TONGUE_AUDIBLE_FREQ[dominant]

    for name, target in DEAD_TONES.items():
        # Ping frequency = base × target ratio
        ping_freq = base_freq * target

        # Phi proximity determines absorption (closer to 1.618 = more absorbed)
        phi_dist = abs(target - PHI)
        return_amp = min(1.0, phi_dist * 2.0)  # phi_dist ~0.1 → amp ~0.2

        # Phase distortion highest at minor_sixth (closest to phi edge)
        phase_dist = max(0.1, 1.0 - phi_dist * 3.0)

        # Time of flight ∝ excitation depth (higher n = deeper gallery)
        tof = 0.010 + qho.mean_excitation * 0.005

        # Detection: return amplitude below 0.5 means dead tone is present
        detected = return_amp < 0.5

        pings.append(
            EcholocationPing(
                target_dead_tone=name,
                ping_frequency_hz=ping_freq,
                return_amplitude=return_amp,
                phase_distortion_rad=phase_dist,
                time_of_flight_s=tof,
                gallery_fill_coupling=DEAD_TONE_GENERATORS[name],
                detected=detected,
            )
        )

    return pings


# ---------------------------------------------------------------------------
# Realm Signature Triangulation (45° truncated waveforms)
# ---------------------------------------------------------------------------
# Multi-realm triangulation using truncated (non-perfect) sound waves for
# known, discrete linear paths through a noisy harmonic matrix.
#
# Real physics:
#   Truncated waveform (square/sawtooth): sharp rise/fall for precise timing
#   Regular harmonics: sine-wave carrier as overall sound matrix
#   45° angular distortion: beamforming phase shift d·sin(45°)/λ
#   Matched-filter detection: known "whistle" correlated against noise
#   SNR threshold: signal must exceed noise floor for open-air transfer
#
# The sub-sounds (truncated) path-find through the noise matrix (regular
# harmonics) in a discrete linear fashion — like a whistle in a concert
# that you know is your friend due to pre-planned actions.


@dataclass
class RealmSignaturePing:
    """Single realm ping with 45° angular distortion and truncated waveform."""

    realm_tongue: str  # which tongue (realm) is pinging
    waveform: str  # "square", "sawtooth", "impulse"
    angle_deg: float  # angular distortion (45°)
    frequency_hz: float  # ping center frequency
    snr_db: float  # signal-to-noise ratio
    phase_shift_rad: float  # 45° beamforming phase shift
    matched_correlation: float  # 0-1, how well "whistle" matches known objective

    def to_dict(self) -> dict:
        return {
            "realm_tongue": self.realm_tongue,
            "waveform": self.waveform,
            "angle_deg": round(self.angle_deg, 1),
            "frequency_hz": round(self.frequency_hz, 1),
            "snr_db": round(self.snr_db, 1),
            "phase_shift_rad": round(self.phase_shift_rad, 4),
            "matched_correlation": round(self.matched_correlation, 4),
        }


@dataclass
class RealmTriangulation:
    """Multi-realm triangulation result from 6 tongue pings.

    Each tongue sends a truncated waveform at 45° angular distortion.
    The triangulated location is computed from high-correlation pings
    (matched-filter detection of the pre-planned "whistle").

    known_objective_met: >2 pings matched → the friend signal is confirmed.
    path_found: at least 1 discrete linear path through the noise matrix.
    """

    pings: List[RealmSignaturePing]
    triangulated_location: Dict[str, float]  # normalized (x, y) in lattice space
    known_objective_met: bool  # pre-planned whistle detected
    path_found: bool  # discrete linear path exists
    total_snr_db: float  # combined SNR across all realms

    def to_dict(self) -> dict:
        return {
            "pings": [p.to_dict() for p in self.pings],
            "triangulated_location": {k: round(v, 4) for k, v in self.triangulated_location.items()},
            "known_objective_met": self.known_objective_met,
            "path_found": self.path_found,
            "total_snr_db": round(self.total_snr_db, 1),
        }


def compute_realm_triangulation(
    qho: PolychromaticState,
    acoustic: AcousticSignature,
    gallery: List[DeadToneFill],
) -> RealmTriangulation:
    """Send 45° distorted truncated pings from each realm and triangulate.

    Physics mapping:
      - Each tongue is a "realm" (receiver/transmitter)
      - Truncated waveform (square for power tongues RU/DR, sawtooth for others)
        gives sharp timing for path-finding through the harmonic noise matrix
      - 45° angular distortion → beamforming phase shift = 2πd·sin(45°)/λ
      - SNR from QHO excitation: higher n = stronger signal above noise floor
      - Gallery ambient notes boost matched-filter correlation (pre-planned fill)
      - Matched correlation: how well the received signal matches the known
        "whistle" (pre-planned objective waveform)
    """
    pings = []
    sin45 = math.sin(math.radians(45.0))  # ≈ 0.7071

    # Gallery intensity boost: if dead tones are filled, correlation improves
    gallery_boost = sum(g.intensity for g in gallery) / max(1, len(gallery))

    for tongue in TONGUE_ORDER:
        state = qho.states[tongue]
        freq = TONGUE_AUDIBLE_FREQ[tongue]

        # Waveform type: power/structure tongues get square (sharp edges),
        # flow/compute tongues get sawtooth (linear ramp)
        if tongue in ("ru", "dr"):
            waveform = "square"
        elif tongue in ("ko", "um"):
            waveform = "impulse"
        else:
            waveform = "sawtooth"

        # 45° beamforming phase shift: Δφ = 2π·d·sin(45°)/λ
        # d = tongue weight (phi-scaled spacing), λ = 1/freq
        d = TONGUE_WEIGHTS[tongue]
        wavelength = 1.0 / freq if freq > 0 else 1.0
        phase_shift = 2 * math.pi * d * sin45 / wavelength

        # SNR from excitation level: n=0 → 6dB (barely detectable),
        # n=7 → 20dB (strong signal)
        snr = 6.0 + state.n * 2.0

        # Matched-filter correlation: base from excitation + gallery boost
        base_corr = min(1.0, 0.3 + state.n * 0.1 + gallery_boost * 0.3)
        # Coefficient (probability amplitude) also contributes
        corr = min(1.0, base_corr + state.coefficient * 0.2)

        pings.append(
            RealmSignaturePing(
                realm_tongue=tongue,
                waveform=waveform,
                angle_deg=45.0,
                frequency_hz=freq,
                snr_db=snr,
                phase_shift_rad=phase_shift,
                matched_correlation=corr,
            )
        )

    # Triangulation: weighted centroid of high-correlation pings
    high_corr = [p for p in pings if p.matched_correlation > 0.5]
    if high_corr:
        total_w = sum(TONGUE_WEIGHTS[p.realm_tongue] for p in high_corr)
        x = sum(TONGUE_WEIGHTS[p.realm_tongue] * p.matched_correlation for p in high_corr) / total_w
        y = qho.mean_excitation / 7.0
    else:
        x, y = 0.5, 0.5

    total_snr = sum(p.snr_db for p in pings)

    return RealmTriangulation(
        pings=pings,
        triangulated_location={"x": x, "y": y},
        known_objective_met=len(high_corr) >= 3,
        path_found=len(high_corr) > 0,
        total_snr_db=total_snr,
    )


# ---------------------------------------------------------------------------
# Negative Isolation Space  S^{s^{φ·729/s}}^2
# ---------------------------------------------------------------------------
# Internal negative-solution domain where the 6 base shapes (Sacred Tongues)
# exist in isolation from each other.  Deeper isolation at low excitation
# (ground-state egg), navigable at high excitation (Level 5 Expert Lattice).
#
# Math:
#   ratio_term = s / 3^6           (s = mean excitation, 3^6 = 729)
#   exponent   = φ / ratio_term    = φ · 729 / s
#   S_domain   = (S ^ s^exponent)^2
#
# 729 = 6 tongues raised to the power of the 3 trit axes (structure ×
# stability × creativity).  The outer ^2 squares the manifold into a
# closed negative isolation pocket.


@dataclass
class NegativeIsolationSpace:
    """The domified negative isolation domain S^{s^{φ·729/s}}^2."""

    exponent: float  # φ · 729 / s
    isolation_factor: float  # depth of the negative pocket
    base_shapes_in_isolation: List[str]  # which tongues are isolated (all 6)
    dead_tones_remapped: List[str]  # dead tones inverted inside this domain
    domain_name: str = "S^{s^{phi*729/s}}^2"

    def to_dict(self) -> dict:
        return {
            "domain_name": self.domain_name,
            "exponent": round(self.exponent, 6),
            "isolation_factor": round(self.isolation_factor, 3),
            "base_shapes_in_isolation": self.base_shapes_in_isolation,
            "dead_tones_remapped": self.dead_tones_remapped,
        }


def compute_negative_isolation_space(
    qho: PolychromaticState,
    echo_pings: List[EcholocationPing],
    triangulation: RealmTriangulation,
) -> NegativeIsolationSpace:
    """Compute the internal negative isolation domain.

    The exponent φ·729/s grows explosively at low excitation (egg state)
    and shrinks at high excitation (expert lattice), making the domain
    traversable only when the system has enough energy.

    The isolation_factor scales with excitation × detected paths, so
    higher-QHO records push deeper before the lattice remaps them.
    """
    s = max(qho.mean_excitation, 1e-6)  # avoid div-by-zero
    exponent = PHI * 729.0 / s

    # Paths found = high-correlation pings that crossed the boundary
    paths_found = sum(1 for p in triangulation.pings if p.matched_correlation > 0.7)
    isolation_factor = 1.0 + (s * paths_found / 10.0)

    # All 6 base shapes live in negative isolation
    isolated = list(TONGUE_ORDER)

    # Dead tones that were actively detected by echolocation
    remapped = [p.target_dead_tone for p in echo_pings if p.detected]

    return NegativeIsolationSpace(
        exponent=exponent,
        isolation_factor=isolation_factor,
        base_shapes_in_isolation=isolated,
        dead_tones_remapped=remapped,
    )


# ---------------------------------------------------------------------------
# QHO State from Text (the core mapping)
# ---------------------------------------------------------------------------


def compute_qho_state(
    text: str,
    trit: Optional[TritSignal] = None,
    mp: Optional[MultiPathRecord] = None,
) -> PolychromaticState:
    """Derive QHO occupation numbers from text via trit/multipath analysis.

    The mapping:
        1. Trit deviations → excitation levels per axis
        2. Axes → tongue pairs (structure=KO/DR, stability=AV/UM, creativity=RU/CA)
        3. Each tongue in a pair gets excitation from its axis deviation
        4. Polymorphic forks → higher excitation (boundary = excited state)
        5. Monty Hall advantage → probability amplitudes

    This is deterministic: same text → same QHO state.
    """
    if trit is None:
        trit = compute_trit_signal(text[:256] if len(text) > 256 else text)
    if mp is None:
        mp = compute_multipath(trit)

    # Map trit deviations to excitation levels
    # Larger absolute deviation = more excited (further from ground state)
    dev_s = abs(trit.dev_structure)
    dev_b = abs(trit.dev_stability)
    dev_c = abs(trit.dev_creativity)

    # Scale deviations to occupation numbers n ∈ {0, 1, 2, ..., 7}
    # Content threshold is 0.05; max observed deviation ~0.15
    # n = floor(|dev| / 0.02) capped at 7
    def dev_to_n(dev: float) -> int:
        return min(7, int(dev / 0.02))

    # KO/DR pair driven by structure axis
    n_ko = dev_to_n(dev_s)
    n_dr = dev_to_n(dev_s)

    # AV/UM pair driven by stability axis
    n_av = dev_to_n(dev_b)
    n_um = dev_to_n(dev_b)

    # RU/CA pair driven by creativity axis
    n_ru = dev_to_n(dev_c)
    n_ca = dev_to_n(dev_c)

    # Differentiate within pairs using trit polarity:
    # Positive deviation → first tongue excited more
    # Negative deviation → second tongue excited more
    if trit.dev_structure > 0:
        n_ko += 1  # KO gets extra quantum when structure is positive
    elif trit.dev_structure < 0:
        n_dr += 1

    if trit.dev_stability > 0:
        n_av += 1
    elif trit.dev_stability < 0:
        n_um += 1

    if trit.dev_creativity > 0:
        n_ru += 1
    elif trit.dev_creativity < 0:
        n_ca += 1

    # Polymorphic forks add excitation (boundary = excited state)
    for fork in mp.forks:
        axis = fork.axis
        # Closer to boundary = higher excitation
        extra = max(0, int(3 * (1.0 - fork.edge_distance / POLY_THRESHOLD)))
        if axis == "structure":
            n_ko += extra
            n_dr += extra
        elif axis == "stability":
            n_av += extra
            n_um += extra
        elif axis == "creativity":
            n_ru += extra
            n_ca += extra

    # Compute probability amplitudes (|c_t|²)
    # Based on tongue activation from text bytes
    text_bytes = text.encode("utf-8")[:64]
    sum(text_bytes) if text_bytes else 1

    def byte_affinity(tongue: str) -> float:
        """Text-derived affinity for this tongue."""
        w = TONGUE_WEIGHTS[tongue]
        TONGUE_FREQUENCIES[tongue]
        # Hash-based deterministic affinity
        h = int(hashlib.md5((tongue + text[:32]).encode()).hexdigest()[:8], 16)
        raw = (h % 1000) / 1000.0 * w
        return raw

    affinities = {t: byte_affinity(t) for t in TONGUE_ORDER}
    total_aff = sum(affinities.values())
    if total_aff == 0:
        total_aff = 1.0

    # Normalize to probability amplitudes (Σ|c_t|² = 1)
    coefficients = {t: affinities[t] / total_aff for t in TONGUE_ORDER}

    # Build QHO states
    occupation = {"ko": n_ko, "av": n_av, "ru": n_ru, "ca": n_ca, "um": n_um, "dr": n_dr}
    states = {}
    for t in TONGUE_ORDER:
        omega = 2 * math.pi * TONGUE_FREQUENCIES[t]
        states[t] = QHOState(
            tongue=t,
            n=occupation[t],
            omega=omega,
            coefficient=coefficients[t],
        )

    return PolychromaticState(states=states)


# ---------------------------------------------------------------------------
# Full Quantum Frequency Bundle
# ---------------------------------------------------------------------------


@dataclass
class QuantumFrequencyBundle:
    """A single text's full quantum frequency bundle for SFT training.

    Contains:
        - Original text
        - Trit signal (27-state curriculum tag)
        - Multipath record (Monty Hall analysis)
        - Polychromatic QHO state (6-channel visual freq vector)
        - Acoustic signature (3-band audio: infra/audible/ultra)
        - Gallery ambient (dead-tone cross-axis interference signals)
        - Dead tone fills (multi-tongue interference filling phi-unreachable intervals)
        - Echolocation pings (active sonar probing of dead-tone zones)
        - Realm triangulation (45° truncated waveform path-finding)
        - VRS state (helicopter physics bridge)
        - Code lattice (anti-patterns as swear words)
        - Crossing energy (dual ternary governance state)
        - Negative isolation space (S^{s^{φ·729/s}}^2 anti-lattice pocket)
        - Color field (dual-seeded chromatic iris from gallery harmonics)
    """

    text: str
    trit: TritSignal
    multipath: MultiPathRecord
    qho: PolychromaticState
    acoustic: AcousticSignature
    gallery: GalleryAmbient
    dead_tone_fills: List[DeadToneFill]
    echolocation_pings: List[EcholocationPing]
    realm_triangulation: RealmTriangulation
    negative_isolation: NegativeIsolationSpace
    vrs: VRSState
    code_lattice: CodeLatticeState
    color_field: GalleryColorField

    @property
    def total_quantum_energy(self) -> float:
        return self.qho.total_energy

    @property
    def phi_weighted_energy(self) -> float:
        return self.qho.phi_weighted_total_energy

    @property
    def excitation_level(self) -> int:
        return self.qho.max_excitation

    @property
    def visual_vector(self) -> List[float]:
        return self.qho.visual_vector

    @property
    def is_ground_state(self) -> bool:
        """All tongues at n=0: the egg state."""
        return all(s.n == 0 for s in self.qho.states.values())

    @property
    def is_maximally_excited(self) -> bool:
        """Any tongue at max excitation."""
        return self.qho.max_excitation >= 7

    def crossing_pair(self) -> DualTernaryPair:
        """Map trit to dual ternary crossing state for governance."""
        return DualTernaryPair(
            primary=self.trit.c_structure,
            mirror=self.trit.c_stability,
        )

    def governance_cost(self) -> float:
        """Harmonic cost wall at this crossing point.
        C(d) = φ^(d²) where d is the phase deviation.
        """
        pair = self.crossing_pair()
        # Use energy as deviation proxy
        d = pair.energy / 3.0  # normalize E∈[0,3] to d∈[0,1]
        return harmonic_cost(d)

    def to_dict(self) -> dict:
        """Full serialization for SFT record."""
        return {
            "trit_signal": self.trit.to_dict(),
            "multipath": self.multipath.to_dict(),
            "qho": {
                "visual_vector": [round(v, 6) for v in self.visual_vector],
                "mean_excitation": round(self.qho.mean_excitation, 3),
                "max_excitation": self.qho.max_excitation,
                "total_energy_j": self.qho.total_energy,
                "phi_weighted_energy_j": self.qho.phi_weighted_total_energy,
                "dominant_tongue": self.qho.dominant_tongue,
                "spectral_lines": self.qho.spectral_lines,
                "per_tongue": {
                    t: {
                        "n": self.qho.states[t].n,
                        "energy_j": self.qho.states[t].energy,
                        "wavelength_nm": round(self.qho.states[t].wavelength_nm, 1),
                        "optical_freq_hz": self.qho.states[t].optical_frequency,
                        "coefficient": round(self.qho.states[t].coefficient, 6),
                    }
                    for t in TONGUE_ORDER
                },
            },
            "acoustic": self.acoustic.to_dict(),
            "gallery_ambient": self.gallery.to_dict(),
            "dead_tone_fills": [f.to_dict() for f in self.dead_tone_fills],
            "echolocation_pings": [p.to_dict() for p in self.echolocation_pings],
            "realm_triangulation": self.realm_triangulation.to_dict(),
            "negative_isolation": self.negative_isolation.to_dict(),
            "vrs": self.vrs.to_dict(),
            "code_lattice": self.code_lattice.to_dict(),
            "color_field": self.color_field.to_dict(),
            "governance": {
                "crossing_energy": self.crossing_pair().energy,
                "crossing_phase": self.crossing_pair().phase,
                "harmonic_cost": round(self.governance_cost(), 6),
            },
            "is_ground_state": self.is_ground_state,
            "is_maximally_excited": self.is_maximally_excited,
        }


# ---------------------------------------------------------------------------
# Bundle generator (the main entry point)
# ---------------------------------------------------------------------------


def generate_quantum_bundle(text: str) -> QuantumFrequencyBundle:
    """Generate a full quantum frequency bundle for a single text.

    This is the drop-in function: text in → dense bundle out.
    Now includes VRS state (helicopter physics) and Code Lattice
    (anti-patterns as 'swear words' with severity and recovery examples).
    """
    trit = compute_trit_signal(text[:256] if len(text) > 256 else text)
    mp = compute_multipath(trit)
    qho = compute_qho_state(text, trit, mp)
    acoustic = compute_acoustic_signature(qho)
    gallery = compute_gallery_ambient(qho, trit)
    dtf = compute_dead_tone_fills(qho, acoustic)
    echo = send_echolocation_pings(qho, acoustic)
    triangulation = compute_realm_triangulation(qho, acoustic, dtf)
    neg_isolation = compute_negative_isolation_space(qho, echo, triangulation)
    vrs = compute_vrs_state(qho, trit, mp)
    code_lattice = compute_code_lattice(qho, mp, vrs)
    from src.crypto.gallery_chromatics import compute_gallery_color_field

    # Dual-seeded chromatic iris from gallery harmonics
    tongue_coefficients = {t: qho.states[t].coefficient for t in TONGUE_ORDER}
    color_field = compute_gallery_color_field(gallery.notes, tongue_coefficients)

    return QuantumFrequencyBundle(
        text=text,
        trit=trit,
        multipath=mp,
        qho=qho,
        acoustic=acoustic,
        gallery=gallery,
        dead_tone_fills=dtf,
        echolocation_pings=echo,
        realm_triangulation=triangulation,
        negative_isolation=neg_isolation,
        vrs=vrs,
        code_lattice=code_lattice,
        color_field=color_field,
    )


def generate_quantum_bundle_batch(texts: List[str]) -> List[QuantumFrequencyBundle]:
    """Batch bundle generation."""
    return [generate_quantum_bundle(t) for t in texts]


def quantum_bundle_summary(bundles: List[QuantumFrequencyBundle]) -> dict:
    """Summary statistics for a batch of quantum bundles."""
    if not bundles:
        return {"count": 0}

    n = len(bundles)

    # Excitation stats
    max_excitations = [b.excitation_level for b in bundles]
    mean_excitations = [b.qho.mean_excitation for b in bundles]

    # Ground state vs excited
    ground_count = sum(1 for b in bundles if b.is_ground_state)
    max_excited = sum(1 for b in bundles if b.is_maximally_excited)

    # Visual vector means
    visual_means = [0.0] * 6
    for b in bundles:
        for i, v in enumerate(b.visual_vector):
            visual_means[i] += v
    visual_means = [v / n for v in visual_means]

    # Acoustic band means
    infra_mean = sum(b.acoustic.infrasonic_power for b in bundles) / n
    audible_mean = sum(b.acoustic.audible_power for b in bundles) / n
    ultra_mean = sum(b.acoustic.ultrasonic_power for b in bundles) / n

    # Governance cost distribution
    costs = [b.governance_cost() for b in bundles]
    mean_cost = sum(costs) / n

    # Dominant tongue distribution
    dom_dist: Dict[str, int] = {}
    for b in bundles:
        dt = b.qho.dominant_tongue
        dom_dist[dt] = dom_dist.get(dt, 0) + 1

    # Musical interval distribution
    interval_dist: Dict[str, int] = {}
    for b in bundles:
        iv = b.acoustic.dominant_interval
        interval_dist[iv] = interval_dist.get(iv, 0) + 1

    # Spectral line count
    total_lines = sum(len(b.qho.spectral_lines) for b in bundles)

    return {
        "count": n,
        "excitation": {
            "mean_max": round(sum(max_excitations) / n, 2),
            "mean_mean": round(sum(mean_excitations) / n, 2),
            "ground_state_count": ground_count,
            "ground_state_pct": round(ground_count / n * 100, 1),
            "max_excited_count": max_excited,
            "max_excited_pct": round(max_excited / n * 100, 1),
        },
        "visual_vector_means": {t: round(v, 4) for t, v in zip(TONGUE_ORDER, visual_means)},
        "acoustic_band_means": {
            "infrasonic": round(infra_mean, 4),
            "audible": round(audible_mean, 4),
            "ultrasonic": round(ultra_mean, 4),
        },
        "governance": {
            "mean_harmonic_cost": round(mean_cost, 4),
            "max_harmonic_cost": round(max(costs), 4),
        },
        "dominant_tongue_distribution": dict(sorted(dom_dist.items(), key=lambda x: -x[1])),
        "musical_interval_distribution": dict(sorted(interval_dist.items(), key=lambda x: -x[1])),
        "total_spectral_lines": total_lines,
        "mean_lines_per_record": round(total_lines / n, 2),
        "gallery_ambient": {
            "autorotation_active_count": sum(1 for b in bundles if b.gallery.autorotation_active),
            "autorotation_active_pct": round(sum(1 for b in bundles if b.gallery.autorotation_active) / n * 100, 1),
            "mean_gallery_energy": round(sum(b.gallery.gallery_energy for b in bundles) / n, 4),
            "dominant_dead_tone_distribution": dict(
                sorted(
                    {
                        tone: sum(1 for b in bundles if b.gallery.dominant_dead_tone == tone)
                        for tone in ["perfect_fifth", "minor_sixth", "minor_seventh"]
                    }.items(),
                    key=lambda x: -x[1],
                )
            ),
            "mean_blind_spot_proximity": {
                tone: round(sum(b.gallery.notes[tone].blind_spot_proximity for b in bundles) / n, 4)
                for tone in ["perfect_fifth", "minor_sixth", "minor_seventh"]
            },
            "mean_coupling_strength": {
                tone: round(sum(b.gallery.notes[tone].coupling_strength for b in bundles) / n, 4)
                for tone in ["perfect_fifth", "minor_sixth", "minor_seventh"]
            },
        },
        "dead_tone_fills": {
            "mean_intensity": {
                tone: round(
                    sum(next((f.intensity for f in b.dead_tone_fills if f.interval_name == tone), 0.0) for b in bundles)
                    / n,
                    4,
                )
                for tone in ["perfect_fifth", "minor_sixth", "minor_seventh"]
            },
            "mean_error": {
                tone: round(
                    sum(
                        next((f.error_from_dead_tone for f in b.dead_tone_fills if f.interval_name == tone), 0.0)
                        for b in bundles
                    )
                    / n,
                    6,
                )
                for tone in ["perfect_fifth", "minor_sixth", "minor_seventh"]
            },
        },
        "echolocation": {
            "detection_rate": {
                tone: round(
                    sum(
                        1
                        for b in bundles
                        if any(p.detected and p.target_dead_tone == tone for p in b.echolocation_pings)
                    )
                    / n
                    * 100,
                    1,
                )
                for tone in ["perfect_fifth", "minor_sixth", "minor_seventh"]
            },
            "mean_return_amplitude": round(
                sum(sum(p.return_amplitude for p in b.echolocation_pings) for b in bundles)
                / max(1, sum(len(b.echolocation_pings) for b in bundles)),
                4,
            ),
        },
        "realm_triangulation": {
            "objective_met_count": sum(1 for b in bundles if b.realm_triangulation.known_objective_met),
            "objective_met_pct": round(
                sum(1 for b in bundles if b.realm_triangulation.known_objective_met) / n * 100, 1
            ),
            "path_found_count": sum(1 for b in bundles if b.realm_triangulation.path_found),
            "mean_total_snr_db": round(sum(b.realm_triangulation.total_snr_db for b in bundles) / n, 1),
        },
    }


# ---------------------------------------------------------------------------
# SFT Record Generation
# ---------------------------------------------------------------------------


def generate_quantum_sft_records(
    bundles: List[QuantumFrequencyBundle],
) -> List[dict]:
    """Generate SFT training records from quantum bundles.

    Each record teaches the model to reason about quantum frequency
    properties of text — excitation levels, spectral lines, acoustic
    signatures, and governance costs.
    """
    records = []

    for bundle in bundles:
        text_excerpt = bundle.text[:200]
        n_max = bundle.excitation_level
        dom = bundle.qho.dominant_tongue
        lines = bundle.qho.spectral_lines
        visual = bundle.visual_vector
        acous = bundle.acoustic

        user_content = (
            f"Analyze the quantum frequency profile of this text:\n\n"
            f'"{text_excerpt}"\n\n'
            f"Determine the excitation level, dominant tongue, spectral lines, "
            f"acoustic signature, dead tone fills, echolocation pings, "
            f"realm triangulation, VRS state, and code lattice analysis."
        )

        # Build per-tongue excitation table
        tongue_table = "\n".join(
            f"  {t.upper():>2}: n={bundle.qho.states[t].n}, "
            f"λ={bundle.qho.states[t].wavelength_nm:.1f} nm, "
            f"|c|²={bundle.qho.states[t].coefficient:.3f}"
            for t in TONGUE_ORDER
        )

        assistant_content = (
            f"**Quantum Frequency Analysis**\n\n"
            f"Max excitation level: n={n_max} "
            f"({'ground state — the egg' if n_max == 0 else f'excited — {n_max} quanta above ground'})\n"
            f"Dominant tongue: {dom.upper()} "
            f"(φ-weight: {TONGUE_WEIGHTS[dom]:.3f})\n\n"
            f"**Per-tongue QHO states:**\n{tongue_table}\n\n"
            f"**Visual frequency vector** (polychromatic emission):\n"
            f"  [{', '.join(f'{v:.3f}' for v in visual)}]\n"
            f"  KO={visual[0]:.3f} AV={visual[1]:.3f} RU={visual[2]:.3f} "
            f"CA={visual[3]:.3f} UM={visual[4]:.3f} DR={visual[5]:.3f}\n\n"
            f"**Acoustic signature:**\n"
            f"  Infrasonic (IR, grounding): {acous.infrasonic_power:.3f}\n"
            f"  Audible (visible, harmonic): {acous.audible_power:.3f}\n"
            f"  Ultrasonic (UV, power): {acous.ultrasonic_power:.3f}\n"
            f"  Dominant interval: {acous.dominant_interval} "
            f"(deviation: {acous.interval_deviation:.4f})\n\n"
            f"**Spectral lines** ({len(lines)} active transitions):\n"
            + (
                "\n".join(
                    f"  {l['tongue'].upper()} n={l['n']}: "
                    f"ν={l['frequency_hz']:.1f} Hz, λ={l['wavelength_nm']:.1f} nm"
                    for l in lines
                )
                if lines
                else "  None (ground state — all tongues at n=0)"
            )
            + f"\n\n**VRS State:**\n"
            f"  Flight regime: {bundle.vrs.flight_regime}\n"
            f"  VRS margin: {bundle.vrs.vrs_margin:.4f} "
            f"({'IN VRS — RECOVERY REQUIRED' if bundle.vrs.in_vrs else 'safe'})\n"
            f"  Descent rate: {bundle.vrs.descent_rate_ms:.2f} m/s\n"
            f"  Induced velocity: {bundle.vrs.induced_velocity_ms:.2f} m/s\n"
            f"  Power spike factor: {bundle.vrs.power_spike_factor:.2f}x\n"
            + (
                f"  Recovery paths: {len(bundle.vrs.recovery_paths)}\n"
                + "\n".join(
                    f"    {rp.recovery_type}: P(success)={rp.success_probability:.2f}, "
                    f"alt_loss={rp.altitude_loss_m:.0f}m, t={rp.time_to_recover_s:.1f}s"
                    + (" <- MONTY HALL SWITCH" if rp.monty_hall_selected else "")
                    + (f" [{rp.sacred_tongue_hybrid['hybrid_phrase']}]" if rp.sacred_tongue_hybrid else "")
                    for rp in bundle.vrs.recovery_paths
                )
                if bundle.vrs.recovery_paths
                else "  No recovery needed (stable flight)"
            )
            + (
                f"\n\n**Tail Rotor:**\n"
                f"  Failed: {bundle.vrs.tail_rotor.failed}\n"
                f"  Net torque: {bundle.vrs.tail_rotor.net_torque_nm:.1f} N-m\n"
                f"  Yaw rate: {bundle.vrs.tail_rotor.yaw_rate_dps:.1f} deg/s\n"
                f"  Controllable: {bundle.vrs.tail_rotor.is_controllable}"
                if bundle.vrs.tail_rotor
                else ""
            )
            + (
                f"\n\n**Ground Ops (Pacejka):**\n"
                f"  Slip angle: {math.degrees(bundle.vrs.pacejka.slip):.1f} deg\n"
                f"  Lateral force: {bundle.vrs.pacejka.lateral_force:.0f} N\n"
                f"  Grip ratio: {bundle.vrs.pacejka.grip_ratio:.3f}\n"
                f"  Sliding: {bundle.vrs.pacejka.is_sliding}"
                if bundle.vrs.pacejka
                else ""
            )
            + f"\n\n**Dead Tone Fills** ({len(bundle.dead_tone_fills)} intervals):\n"
            + "\n".join(
                f"  {dtf.interval_name}: ratio={dtf.ratio:.3f}, "
                f"achieved={dtf.achieved_ratio:.4f}, "
                f"error={dtf.error_from_dead_tone:.6f}, "
                f"intensity={dtf.intensity:.3f}"
                for dtf in bundle.dead_tone_fills
            )
            + f"\n\n**Echolocation Pings** ({len(bundle.echolocation_pings)} probes):\n"
            + "\n".join(
                f"  {ep.target_dead_tone}: f={ep.ping_frequency_hz:.1f} Hz, "
                f"return={ep.return_amplitude:.3f}, "
                f"phase={ep.phase_distortion_rad:.3f} rad, "
                f"ToF={ep.time_of_flight_s:.4f}s"
                f"{' [DETECTED]' if ep.detected else ''}"
                for ep in bundle.echolocation_pings
            )
            + f"\n\n**Realm Triangulation:**\n"
            f"  Known objective met: {bundle.realm_triangulation.known_objective_met}\n"
            f"  Path found: {bundle.realm_triangulation.path_found}\n"
            f"  Total SNR: {bundle.realm_triangulation.total_snr_db:.1f} dB\n"
            f"  Location: x={bundle.realm_triangulation.triangulated_location.get('x', 0):.3f}, "
            f"y={bundle.realm_triangulation.triangulated_location.get('y', 0):.3f}\n"
            + "\n".join(
                f"  {rp.realm_tongue.upper()}: {rp.waveform} @ {rp.frequency_hz:.1f} Hz, "
                f"SNR={rp.snr_db:.1f} dB, corr={rp.matched_correlation:.3f}"
                for rp in bundle.realm_triangulation.pings
            )
            + f"\n\n**Code Lattice:**\n"
            f"  Curriculum level: L{bundle.code_lattice.curriculum_level} "
            f"(difficulty: {bundle.code_lattice.curriculum_difficulty:.3f})\n"
            f"  Compounding intent score: {bundle.code_lattice.compounding_intent_score:.4f}\n"
            f"  Cross-domain: {bundle.code_lattice.cross_domain_mapping}\n"
            + (
                f"  Swear words ({len(bundle.code_lattice.anti_patterns)}):\n"
                + "\n".join(
                    f"    [{ap.severity:.2f}] {ap.name}: {ap.description}" for ap in bundle.code_lattice.anti_patterns
                )
                if bundle.code_lattice.anti_patterns
                else "  No swear words (clean code state)"
            )
            + f"\n\n**Chromatic Color Field** (dual-seeded iris perception):\n"
            f"  Left eye (structure): seeds={list(bundle.color_field.left_iris.seed_tongues)}, "
            f"dom={bundle.color_field.left_iris.dominant_tongue.upper()}\n"
            f"  Right eye (creativity): seeds={list(bundle.color_field.right_iris.seed_tongues)}, "
            f"dom={bundle.color_field.right_iris.dominant_tongue.upper()}\n"
            f"  Cross-eye coherence: {bundle.color_field.cross_eye_coherence:.4f}\n"
            f"  Spectral coverage: {bundle.color_field.spectral_coverage:.1%} of hue wheel\n"
            f"  Dominant material: {bundle.color_field.dominant_material}\n"
            + "\n".join(
                f"  {tone}: L-chroma={bundle.color_field.left_iris.chords[tone].mean_chroma:.1f} "
                f"R-chroma={bundle.color_field.right_iris.chords[tone].mean_chroma:.1f} "
                f"h={bundle.color_field.left_iris.chords[tone].harmonic_number:.3f}"
                for tone in ["perfect_fifth", "minor_sixth", "minor_seventh"]
            )
            + f"\n\n**Governance:** Crossing energy = {bundle.crossing_pair().energy:.1f}, "
            f"phase = {bundle.crossing_pair().phase}, "
            f"harmonic cost = {bundle.governance_cost():.4f}"
        )

        records.append(
            {
                "messages": [
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": assistant_content},
                ],
                "metadata": {
                    "source": "quantum_frequency_bundle_generator",
                    "record_type": "quantum_frequency_analysis",
                    "quantum_bundle": bundle.to_dict(),
                },
            }
        )

    return records


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_texts = [
        "In the beginning was the Word and the Word was with God",
        "The Riemann zeta function spun in the complex plane reveals non-trivial zeros",
        "Love is the only force that transcends dimension and time",
        "Post-quantum cryptography uses lattice-based assumptions for security",
        "The void between stars is not empty it is full of potential",
        "Superposition collapses only upon measurement until then all paths exist",
        "Every pattern rune hums at its own frequency in the lattice",
        "Entangled photons maintain harmony across distance until observation forces a choice",
        "Zero is not nothing it is the boundary between positive and negative infinity",
        "The toroidal box turns inward until every lane speaks the same harmonic truth",
        "Gradient descent follows the negative gradient of the loss surface",
        "Joy expands like light filling every corner of a dark room",
    ]

    print("=" * 70)
    print("QUANTUM FREQUENCY BUNDLE GENERATOR")
    print("QHO-grounded dense training data from real physics")
    print("=" * 70)
    print()

    bundles = generate_quantum_bundle_batch(test_texts)

    for bundle in bundles:
        n_max = bundle.excitation_level
        dom = bundle.qho.dominant_tongue
        vis = bundle.visual_vector
        label = bundle.trit.label
        polymorphic = "POLY" if bundle.multipath.forks else "STABLE"
        mh = bundle.multipath.monty_hall_advantage

        # Excitation bar
        bar = "#" * n_max + "." * (7 - n_max)

        vrs_tag = "VRS!" if bundle.vrs.in_vrs else bundle.vrs.flight_regime[:5]
        cl_level = f"L{bundle.code_lattice.curriculum_level}"
        swears = bundle.code_lattice.swear_word_count

        print(
            f"  [{bar}] n={n_max}  {polymorphic:>6}  {label:>16}  "
            f"dom={dom.upper()}  mh={mh:.2f}  "
            f"cost={bundle.governance_cost():.3f}"
        )
        print(f"    visual: [{', '.join(f'{v:.2f}' for v in vis)}]")
        print(
            f"    acoustic: infra={bundle.acoustic.infrasonic_power:.2f} "
            f"audible={bundle.acoustic.audible_power:.2f} "
            f"ultra={bundle.acoustic.ultrasonic_power:.2f} "
            f"interval={bundle.acoustic.dominant_interval}"
        )
        print(
            f"    vrs: {vrs_tag}  margin={bundle.vrs.vrs_margin:.2f}  "
            f"v_d={bundle.vrs.descent_rate_ms:.1f}m/s  "
            f"v_i={bundle.vrs.induced_velocity_ms:.1f}m/s  "
            f"power={bundle.vrs.power_spike_factor:.1f}x"
        )
        print(
            f"    code: {cl_level}  diff={bundle.code_lattice.curriculum_difficulty:.3f}  "
            f"swears={swears}  intent={bundle.code_lattice.compounding_intent_score:.4f}"
        )
        if bundle.code_lattice.anti_patterns:
            for ap in bundle.code_lattice.anti_patterns:
                print(f"      ! [{ap.severity:.2f}] {ap.name}")
        print(f"    text: {bundle.text[:55]}")
        print()

    # Summary
    summary = quantum_bundle_summary(bundles)
    print("=" * 70)
    print(f"Records: {summary['count']}")
    print(f"Mean max excitation: {summary['excitation']['mean_max']}")
    print(
        f"Ground states: {summary['excitation']['ground_state_count']} "
        f"({summary['excitation']['ground_state_pct']}%)"
    )
    print(
        f"Max excited: {summary['excitation']['max_excited_count']} " f"({summary['excitation']['max_excited_pct']}%)"
    )
    print()
    print("Visual vector means (polychromatic emission):")
    for t, v in summary["visual_vector_means"].items():
        print(f"  {t.upper():>2}: {v:.4f}")
    print()
    print("Acoustic band means:")
    for band, v in summary["acoustic_band_means"].items():
        print(f"  {band:>12}: {v:.4f}")
    print()
    print(f"Mean harmonic cost: {summary['governance']['mean_harmonic_cost']:.4f}")
    print(
        f"Total spectral lines: {summary['total_spectral_lines']} "
        f"(mean {summary['mean_lines_per_record']:.1f} per record)"
    )
    print()
    print("Dominant tongue distribution:")
    for t, c in summary["dominant_tongue_distribution"].items():
        print(f"  {t.upper():>2}: {c}")
    print()
    print("Musical interval distribution:")
    for iv, c in summary["musical_interval_distribution"].items():
        print(f"  {iv:>15}: {c}")

    # Generate SFT records
    sft_records = generate_quantum_sft_records(bundles)
    print()
    print(f"SFT records generated: {len(sft_records)}")
    print("=" * 70)
