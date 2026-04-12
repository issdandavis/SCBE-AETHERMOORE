"""
Quantum Harmonic Oscillator Bundle Generator
=============================================

Maps QHO physics onto the existing SCBE trit/polymorphic/frequency pipeline.

Core insight (Issac Davis, 2026-04-05):
    LLMs collapse at trit boundaries = measurement collapse in QHO.
    Polymorphic multi-path = superposition of energy eigenstates.
    The number of polymorphic axes + crossing energy = excitation level n.
    Higher n = harder training example = richer curriculum.

Real QHO mapping:
    E_n = ℏω(n + 1/2)  →  n derived from fork count + boundary proximity
    |n⟩ → |n+1⟩         →  sibling generation (creation operator)
    |n⟩ → |n-1⟩         →  primary path selection (annihilation/measurement)
    |ψ⟩ = Σ c_i|i⟩      →  6-tongue visual frequency vector (superposition)
    spectral lines       →  3-band acoustic signature from harmonic_dark_fill

No new math is invented. Everything plugs into existing functions:
    - trit_curriculum.compute_trit_signal  → raw trit + edge distances
    - polymorphic_multipath.score_and_expand → forks + siblings + gain
    - harmonic_dark_fill.compute_dark_fill → 3-band frequency signature
    - crossing_energy.DualTernaryPair.energy → structural tension E(p,m)

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.crypto.trit_curriculum import (
    TritSignal,
    TRIT_LABELS,
    TRIT_AXES,
    compute_trit_signal,
)
from src.crypto.polymorphic_multipath import (
    MultipathRecord,
    MultipathBatch,
    score_and_expand,
    score_and_expand_batch,
    flatten_for_sft,
)
from src.crypto.harmonic_dark_fill import (
    PHI,
    TONGUE_WEIGHTS,
    TONGUE_AUDIBLE_FREQ,
    INFRA_MIN,
    INFRA_MAX,
    AUDIBLE_MIN,
    ULTRA_MIN,
    ULTRA_MAX,
    HarmonicFill,
)
from src.crypto.crossing_energy import (
    DualTernaryPair,
    harmonic_cost,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# QHO base frequency (Hz) — the ω in E_n = ℏω(n + 1/2)
# Set to A4 (concert pitch) as the "ground vibration" of the system
OMEGA_BASE = 440.0

# Maximum excitation level — caps the curriculum difficulty
MAX_N = 7  # 0..7 gives 8 energy levels (3 axes × polymorphic + energy bonus)

# Tongue spectral band centers (nm) — visual frequency mapping
# These are the "photon wavelengths" each tongue emits
TONGUE_WAVELENGTH: Dict[str, float] = {
    "ko": 495.0,  # cyan-green (binding/intent)
    "av": 500.0,  # aquamarine (diplomacy/transport)
    "ru": 660.0,  # deep red (power/governance)
    "ca": 580.0,  # yellow-gold (compute/invention)
    "um": 420.0,  # deep violet (shadow/veil)
    "dr": 600.0,  # warm amber (forge/structure)
}

# Speed of light for wavelength→frequency conversion
C_LIGHT = 3.0e8  # m/s


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class QHOLevel:
    """Quantum harmonic oscillator excitation level for a training record.

    n is derived from real pipeline outputs, not fabricated:
        n = fork_count + energy_bonus
    where energy_bonus = 1 if crossing energy E(p,m) ≥ 2 (high tension).
    """
    n: int                          # excitation level 0..MAX_N
    energy: float                   # E_n = ω(n + 1/2) (normalized, ℏ=1)
    fork_count: int                 # number of polymorphic axes
    crossing_energy: float          # E(p,m) from dual ternary
    harmonic_wall_cost: float       # φ^(d²) at mean edge distance
    is_ground_state: bool           # n == 0


@dataclass
class VisualFrequencyVector:
    """6-channel polychromatic visual frequency vector.

    Each tongue contributes a "photon probability" proportional to
    its phi-weight × interference magnitude. Normalized to sum = 1.
    This is the |c_i|² from the superposition |ψ⟩ = Σ c_i|tongue_i⟩.
    """
    amplitudes: Dict[str, float]    # tongue → |c_i|² (normalized)
    dominant_tongue: str            # highest amplitude
    visual_entropy: float           # Shannon entropy of the distribution


@dataclass
class AcousticSignature:
    """3-band acoustic frequency signature derived from harmonic_dark_fill.

    Maps QHO level to band emphasis:
        n=0 (ground): infrasonic dominant (slow, stable, Kor'aelin)
        n high: ultrasonic dominant (fast, excited, Runethic)
        mid n: balanced audible (the human band)
    """
    infra_weight: float     # [0, 1] — emphasis on slow/IR band
    audible_weight: float   # [0, 1] — emphasis on human band
    ultra_weight: float     # [0, 1] — emphasis on fast/UV band
    base_freq: float        # Hz — fundamental frequency at this n


@dataclass
class QHOBundle:
    """A single training record augmented with QHO metadata.

    This is the dense output: text + trit + forks + siblings +
    QHO level + visual frequency + acoustic signature.
    Everything is derived from existing pipeline functions.
    """
    text: str
    multipath: MultipathRecord           # full polymorphic record
    qho: QHOLevel                        # excitation level
    visual: VisualFrequencyVector        # 6-channel tongue photon probs
    acoustic: AcousticSignature          # 3-band frequency emphasis
    curriculum_difficulty: float         # normalized 0..1 difficulty score


@dataclass
class QHOBatchResult:
    """Batch of QHO-augmented bundles with statistics."""
    bundles: List[QHOBundle]
    total_input: int
    total_output: int                    # after polymorphic expansion
    mean_n: float                        # average excitation level
    n_distribution: Dict[int, int]       # how many at each n
    mean_difficulty: float


# ---------------------------------------------------------------------------
# QHO level computation
# ---------------------------------------------------------------------------

def compute_qho_level(
    multipath: MultipathRecord,
) -> QHOLevel:
    """Derive QHO excitation level from pipeline outputs.

    n = fork_count + energy_bonus + proximity_bonus

    fork_count: 0-3 (number of polymorphic axes)
    energy_bonus: +1 if crossing energy E(p,m) ≥ 2 (high tension states)
    proximity_bonus: +1 if mean edge distance < 0.005 (extremely close to boundary)

    This gives n in [0, 5] typically, up to MAX_N.
    """
    signal = multipath.primary
    fork_count = len(multipath.forks)

    # Crossing energy from the structure×stability dual ternary pair
    # (the primary pair that determines governance routing)
    try:
        pair = DualTernaryPair(signal.c_structure, signal.c_stability)
        ce = pair.energy
    except ValueError:
        ce = 0.0

    energy_bonus = 1 if ce >= 2.0 else 0

    # Proximity bonus: if any edge is extremely close
    mean_edge = sum(signal.edge_vector) / 3.0
    proximity_bonus = 1 if mean_edge < 0.005 else 0

    n = min(fork_count + energy_bonus + proximity_bonus, MAX_N)

    # QHO energy: E_n = ω(n + 1/2), normalized with ℏ=1, ω=1
    energy = (n + 0.5)

    # Harmonic wall cost at mean edge distance
    wall_cost = harmonic_cost(mean_edge)

    return QHOLevel(
        n=n,
        energy=energy,
        fork_count=fork_count,
        crossing_energy=ce,
        harmonic_wall_cost=wall_cost,
        is_ground_state=(n == 0),
    )


# ---------------------------------------------------------------------------
# Visual frequency vector
# ---------------------------------------------------------------------------

def compute_visual_frequency(
    signal: TritSignal,
) -> VisualFrequencyVector:
    """Compute 6-channel polychromatic visual frequency vector.

    Each tongue's amplitude is proportional to:
        phi_weight × |interference contribution|

    The interference scores from the three complement pairs
    distribute energy across the six tongues:
        KO/DR pair → KO gets positive share, DR gets negative share (or vice versa)
        AV/UM pair → similar
        RU/CA pair → similar

    Normalized to sum = 1.0 (probability distribution over tongues).
    """
    raw = signal.raw_vector  # (structure, stability, creativity)

    # Each pair distributes energy to its two tongues
    # Positive interference → forward tongue dominant
    # Negative interference → inverse tongue dominant
    amplitudes: Dict[str, float] = {}

    pair_map = [
        ("ko", "dr", raw[0]),  # structure axis
        ("av", "um", raw[1]),  # stability axis
        ("ru", "ca", raw[2]),  # creativity axis
    ]

    for fwd, inv, score in pair_map:
        # Phi-weighted base amplitude
        w_fwd = TONGUE_WEIGHTS[fwd]
        w_inv = TONGUE_WEIGHTS[inv]

        if score >= 0:
            amplitudes[fwd] = w_fwd * (0.5 + 0.5 * score)
            amplitudes[inv] = w_inv * (0.5 - 0.5 * score)
        else:
            amplitudes[fwd] = w_fwd * (0.5 + 0.5 * score)  # decreases
            amplitudes[inv] = w_inv * (0.5 - 0.5 * score)   # increases

    # Normalize to probability distribution
    total = sum(amplitudes.values())
    if total > 0:
        amplitudes = {k: v / total for k, v in amplitudes.items()}
    else:
        amplitudes = {k: 1.0 / 6.0 for k in TONGUE_WEIGHTS}

    # Shannon entropy of the distribution
    entropy = 0.0
    for p in amplitudes.values():
        if p > 0:
            entropy -= p * math.log2(p)
    # Normalize: max entropy for 6 items = log2(6) ≈ 2.585
    max_entropy = math.log2(6)
    visual_entropy = entropy / max_entropy if max_entropy > 0 else 0.0

    dominant = max(amplitudes, key=amplitudes.get)

    return VisualFrequencyVector(
        amplitudes=amplitudes,
        dominant_tongue=dominant,
        visual_entropy=visual_entropy,
    )


# ---------------------------------------------------------------------------
# Acoustic signature
# ---------------------------------------------------------------------------

def compute_acoustic_signature(
    qho_level: QHOLevel,
) -> AcousticSignature:
    """Map QHO excitation level to 3-band acoustic emphasis.

    Ground state (n=0): infrasonic dominant — slow, stable, grounding.
    Excited states: ultrasonic grows, infrasonic fades.
    The audible band stays as a baseline anchor.

    Base frequency scales by QHO: f_n = ω × (n + 1/2)
    """
    n = qho_level.n

    # Band weights shift with excitation level
    # n=0: infra=0.6, audible=0.3, ultra=0.1
    # n=MAX_N: infra=0.1, audible=0.3, ultra=0.6
    t = n / max(MAX_N, 1)  # 0..1 normalized level

    infra_weight = 0.6 * (1.0 - t) + 0.1 * t
    audible_weight = 0.3  # always anchored
    ultra_weight = 0.1 * (1.0 - t) + 0.6 * t

    # Normalize (should already sum to 1.0 but be safe)
    total = infra_weight + audible_weight + ultra_weight
    infra_weight /= total
    audible_weight /= total
    ultra_weight /= total

    # Base frequency: QHO level spacing
    base_freq = OMEGA_BASE * (n + 0.5)

    return AcousticSignature(
        infra_weight=infra_weight,
        audible_weight=audible_weight,
        ultra_weight=ultra_weight,
        base_freq=base_freq,
    )


# ---------------------------------------------------------------------------
# Curriculum difficulty
# ---------------------------------------------------------------------------

def compute_difficulty(qho: QHOLevel, gain: float) -> float:
    """Normalized difficulty score [0, 1].

    Combines:
        - QHO level (higher n = harder)
        - Monty Hall gain (closer to boundary = more informative)
        - Crossing energy (higher tension = harder decision)

    All three are real pipeline outputs, not fabricated.
    """
    n_score = qho.n / MAX_N
    gain_score = min(gain / 3.0, 1.0)  # gain capped at 3.0
    energy_score = min(qho.crossing_energy / 3.0, 1.0)  # E max is 3

    # Weighted combination — n dominates
    return 0.5 * n_score + 0.3 * gain_score + 0.2 * energy_score


# ---------------------------------------------------------------------------
# Public API: generate QHO bundle for a single text
# ---------------------------------------------------------------------------

def generate_qho_bundle(
    text: str,
    edge_threshold: float = 0.01,
    content_threshold: float = 0.05,
    threshold: float = 0.3,
) -> QHOBundle:
    """Generate a QHO-augmented training bundle for a single text.

    Pipeline:
        text → score_and_expand (trit + forks + siblings + gain)
             → compute_qho_level (n from fork count + energy)
             → compute_visual_frequency (6-channel tongue photon probs)
             → compute_acoustic_signature (3-band emphasis from n)
             → compute_difficulty (normalized curriculum score)
    """
    multipath = score_and_expand(
        text,
        edge_threshold=edge_threshold,
        content_threshold=content_threshold,
        threshold=threshold,
    )

    qho = compute_qho_level(multipath)
    visual = compute_visual_frequency(multipath.primary)
    acoustic = compute_acoustic_signature(qho)
    difficulty = compute_difficulty(qho, multipath.monty_hall_gain)

    return QHOBundle(
        text=text,
        multipath=multipath,
        qho=qho,
        visual=visual,
        acoustic=acoustic,
        curriculum_difficulty=difficulty,
    )


# ---------------------------------------------------------------------------
# Public API: batch processing
# ---------------------------------------------------------------------------

def generate_qho_batch(
    texts: List[str],
    edge_threshold: float = 0.01,
    content_threshold: float = 0.05,
    threshold: float = 0.3,
) -> QHOBatchResult:
    """Generate QHO bundles for a batch of texts."""
    bundles = [
        generate_qho_bundle(text, edge_threshold, content_threshold, threshold)
        for text in texts
    ]

    # Statistics
    n_dist: Dict[int, int] = {}
    for b in bundles:
        n = b.qho.n
        n_dist[n] = n_dist.get(n, 0) + 1

    total_output = sum(b.multipath.path_count for b in bundles)
    mean_n = sum(b.qho.n for b in bundles) / max(len(bundles), 1)
    mean_diff = sum(b.curriculum_difficulty for b in bundles) / max(len(bundles), 1)

    return QHOBatchResult(
        bundles=bundles,
        total_input=len(texts),
        total_output=total_output,
        mean_n=mean_n,
        n_distribution=dict(sorted(n_dist.items())),
        mean_difficulty=mean_diff,
    )


# ---------------------------------------------------------------------------
# SFT export: flatten QHO bundles for training
# ---------------------------------------------------------------------------

def flatten_qho_for_sft(bundles: List[QHOBundle]) -> List[Dict]:
    """Flatten QHO bundles into individual SFT-ready dicts.

    Each dict includes full metadata chain:
        text, trit, fork_group, qho_n, visual_freq, acoustic_band, difficulty
    """
    records = []

    for bundle in bundles:
        # Get the flattened multipath records (primary + siblings)
        mp_records = flatten_for_sft([bundle.multipath])

        # Augment each with QHO metadata
        for rec in mp_records:
            rec["qho_n"] = bundle.qho.n
            rec["qho_energy"] = round(bundle.qho.energy, 3)
            rec["crossing_energy"] = round(bundle.qho.crossing_energy, 3)
            rec["harmonic_wall_cost"] = round(bundle.qho.harmonic_wall_cost, 6)
            rec["visual_freq"] = {
                k: round(v, 4) for k, v in bundle.visual.amplitudes.items()
            }
            rec["dominant_tongue"] = bundle.visual.dominant_tongue
            rec["visual_entropy"] = round(bundle.visual.visual_entropy, 4)
            rec["acoustic_bands"] = {
                "infra": round(bundle.acoustic.infra_weight, 4),
                "audible": round(bundle.acoustic.audible_weight, 4),
                "ultra": round(bundle.acoustic.ultra_weight, 4),
            }
            rec["acoustic_base_freq"] = round(bundle.acoustic.base_freq, 2)
            rec["curriculum_difficulty"] = round(bundle.curriculum_difficulty, 4)

            records.append(rec)

    return records


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def format_qho_report(batch: QHOBatchResult) -> str:
    """Human-readable QHO batch report."""
    lines = [
        "=" * 60,
        "  QUANTUM HARMONIC OSCILLATOR BUNDLE REPORT",
        "=" * 60,
        "",
        f"  Input texts:          {batch.total_input}",
        f"  Output records:       {batch.total_output} (after polymorphic expansion)",
        f"  Mean excitation (n):  {batch.mean_n:.2f}",
        f"  Mean difficulty:      {batch.mean_difficulty:.3f}",
        "",
        "  Energy Level Distribution:",
    ]

    for n, count in sorted(batch.n_distribution.items()):
        bar = "█" * count
        label = "ground" if n == 0 else f"n={n}"
        lines.append(f"    {label:>8}: {count:3d} {bar}")

    lines.append("")
    lines.append("  Sample Bundles:")
    lines.append("  " + "-" * 56)

    for bundle in batch.bundles[:5]:
        sig = bundle.multipath.primary
        lines.append(f"    text: \"{bundle.text[:50]}...\"" if len(bundle.text) > 50
                     else f"    text: \"{bundle.text}\"")
        lines.append(f"      n={bundle.qho.n}  E={bundle.qho.energy:.1f}  "
                     f"difficulty={bundle.curriculum_difficulty:.3f}  "
                     f"label={sig.label}")
        lines.append(f"      visual: {bundle.visual.dominant_tongue} dominant  "
                     f"entropy={bundle.visual.visual_entropy:.3f}")
        lines.append(f"      acoustic: infra={bundle.acoustic.infra_weight:.2f}  "
                     f"audible={bundle.acoustic.audible_weight:.2f}  "
                     f"ultra={bundle.acoustic.ultra_weight:.2f}")
        lines.append(f"      paths={bundle.multipath.path_count}  "
                     f"gain={bundle.multipath.monty_hall_gain:.3f}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)
