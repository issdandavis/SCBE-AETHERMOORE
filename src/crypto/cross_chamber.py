"""
Cross-Chamber Superposition — Acoustic State Checking via Harmonic Interference
================================================================================

Two intersecting acoustic fields:
    Chamber 1 (Root):  System baseline — dead-tone pre-tone frequency (330/352/392 Hz).
    Chamber 2 (Agent): AI agent's current state frequency from tongue prosody + color field.

When the agent's wave crosses the root wave, the L14 FFT telemetry measures
the combined interference pattern — NOT the individual waves.

    Consonance (safe):     Agent frequency forms a clean ratio with baseline
                           (3:2, 5:4, 2:1). Standing wave is stable.
                           Low spectral flux → ALLOW.

    Dissonance (unsafe):   Agent frequency clashes with baseline (45:32, 16:15).
                           Beat frequencies and destructive interference.
                           High spectral flux → QUARANTINE / ESCALATE / DENY.

A malicious prompt literally *sounds bad* to the system's math.

Pipeline position:
    dead_tone → baseline_hz
    tongue_prosody + color_field → agent_hz
    superpose(baseline, agent) → combined waveform
    FFT(combined) → spectral features
    consonance_score(ratio) → governance verdict

@layer Layer 14 (Audio Axis)
@component Cross-Chamber Superposition
@axiom A4 (Symmetry): ratio scoring is symmetric — swap baseline/agent, same result
@axiom A5 (Composition): bridges L14 audio with L13 risk decision

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2
TAU = 2.0 * math.pi

# Dead-tone baseline frequencies (Hz) — the 3 phi-unreachable intervals
BASELINE_FREQUENCIES = {
    "perfect_fifth": 330.0,  # 3:2
    "minor_sixth": 352.0,  # 8:5
    "minor_seventh": 392.0,  # 16:9
}

# Consonant ratios and their dissonance scores [0=perfect, 1=maximum clash]
# Based on just intonation + Helmholtz roughness ordering.
# Score is hand-tuned to match L13 governance thresholds.
RATIO_DISSONANCE = {
    "unison": (1.0, 0.00),
    "octave": (2.0, 0.02),
    "perfect_fifth": (3.0 / 2.0, 0.05),
    "perfect_fourth": (4.0 / 3.0, 0.08),
    "major_third": (5.0 / 4.0, 0.12),
    "minor_third": (6.0 / 5.0, 0.15),
    "major_sixth": (5.0 / 3.0, 0.18),
    "minor_sixth": (8.0 / 5.0, 0.22),
    "major_second": (9.0 / 8.0, 0.30),
    "minor_seventh": (16.0 / 9.0, 0.35),
    "major_seventh": (15.0 / 8.0, 0.55),
    "phi_interval": (PHI, 0.40),  # golden ratio — outside JI lattice
    "tritone": (45.0 / 32.0, 0.75),  # devil's interval
    "minor_second": (16.0 / 15.0, 0.90),  # maximum roughness
}

# L13 governance thresholds — dissonance score → verdict
ALLOW_THRESHOLD = 0.25  # below → ALLOW
QUARANTINE_THRESHOLD = 0.50  # below → QUARANTINE
ESCALATE_THRESHOLD = 0.75  # below → ESCALATE
# above → DENY

# Default sample rate and duration for waveform generation
DEFAULT_SAMPLE_RATE = 8000  # Hz (telephone quality — enough for ratio analysis)
DEFAULT_DURATION_S = 0.25  # 250ms — enough for at least one beat cycle


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class GovernanceVerdict(Enum):
    """L13 risk decision tiers."""

    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    ESCALATE = "ESCALATE"
    DENY = "DENY"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SpectralFeatures:
    """FFT-derived features from the superposed waveform."""

    energy: float  # total signal energy (sum of squared magnitudes)
    spectral_centroid: float  # weighted center of frequency spectrum (Hz)
    spectral_flux: float  # rate of spectral change (beat energy)
    peak_frequency: float  # dominant frequency in combined signal (Hz)
    beat_frequency: float  # |f_baseline - f_agent| — the interference rate
    n_peaks: int  # number of significant spectral peaks


@dataclass(frozen=True)
class ConsonanceReport:
    """Full cross-chamber analysis result."""

    baseline_hz: float
    agent_hz: float
    frequency_ratio: float  # normalized to [1.0, 2.0)
    nearest_interval: str  # name from RATIO_DISSONANCE
    interval_deviation: float  # how far from the nearest pure ratio
    dissonance_score: float  # [0.0, 1.0] — the governance input
    spectral: SpectralFeatures
    verdict: GovernanceVerdict
    dead_tone: str  # which dead tone was used as baseline


# ---------------------------------------------------------------------------
# 1. Waveform generation + superposition
# ---------------------------------------------------------------------------


def generate_wave(
    frequency_hz: float,
    duration_s: float = DEFAULT_DURATION_S,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    amplitude: float = 1.0,
    phase: float = 0.0,
) -> List[float]:
    """Generate a pure sine wave at the given frequency.

    Returns a list of sample values (not numpy — pure Python).
    """
    n_samples = int(duration_s * sample_rate)
    return [amplitude * math.sin(TAU * frequency_hz * (i / sample_rate) + phase) for i in range(n_samples)]


def superpose(wave_a: List[float], wave_b: List[float]) -> List[float]:
    """Point-wise addition of two waveforms (cross-chamber combination).

    If lengths differ, truncates to the shorter.
    """
    n = min(len(wave_a), len(wave_b))
    return [wave_a[i] + wave_b[i] for i in range(n)]


# ---------------------------------------------------------------------------
# 2. Pure-Python DFT + spectral feature extraction
# ---------------------------------------------------------------------------


def dft_magnitudes(signal: List[float]) -> List[float]:
    """Compute DFT magnitude spectrum (positive frequencies only).

    Uses the naive O(N^2) DFT — acceptable for N=2000 (our 250ms window).
    For production at scale, swap to scipy.fft.
    """
    n = len(signal)
    half = n // 2
    magnitudes = []
    for k in range(half):
        re = 0.0
        im = 0.0
        for t in range(n):
            angle = TAU * k * t / n
            re += signal[t] * math.cos(angle)
            im -= signal[t] * math.sin(angle)
        magnitudes.append(math.sqrt(re * re + im * im) / n)
    return magnitudes


def extract_spectral_features(
    combined: List[float],
    baseline_hz: float,
    agent_hz: float,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> SpectralFeatures:
    """Extract L14-style spectral features from the superposed signal."""
    mags = dft_magnitudes(combined)
    n_bins = len(mags)
    if n_bins == 0:
        return SpectralFeatures(0.0, 0.0, 0.0, 0.0, abs(baseline_hz - agent_hz), 0)

    freq_resolution = sample_rate / (2.0 * n_bins)  # Hz per bin

    # Energy: sum of squared magnitudes
    energy = sum(m * m for m in mags)

    # Spectral centroid: weighted average frequency
    total_mag = sum(mags)
    if total_mag > 0:
        centroid = sum(mags[i] * (i * freq_resolution) for i in range(n_bins)) / total_mag
    else:
        centroid = 0.0

    # Peak frequency: bin with highest magnitude
    peak_bin = max(range(n_bins), key=lambda i: mags[i])
    peak_frequency = peak_bin * freq_resolution

    # Beat frequency: the physical interference rate
    beat_frequency = abs(baseline_hz - agent_hz)

    # Spectral flux: energy in beat-frequency region
    # Look for energy around the beat frequency ± tolerance
    beat_bin = int(beat_frequency / freq_resolution) if freq_resolution > 0 else 0
    flux_window = max(1, int(5.0 / freq_resolution))  # ±5 Hz window
    lo = max(0, beat_bin - flux_window)
    hi = min(n_bins, beat_bin + flux_window + 1)
    spectral_flux = sum(mags[i] * mags[i] for i in range(lo, hi))

    # Number of significant peaks (above 10% of max)
    max_mag = max(mags) if mags else 0.0
    threshold = max_mag * 0.1
    n_peaks = sum(1 for m in mags if m > threshold) if max_mag > 0 else 0

    return SpectralFeatures(
        energy=energy,
        spectral_centroid=centroid,
        spectral_flux=spectral_flux,
        peak_frequency=peak_frequency,
        beat_frequency=beat_frequency,
        n_peaks=n_peaks,
    )


# ---------------------------------------------------------------------------
# 3. Consonance scoring — ratio → dissonance → verdict
# ---------------------------------------------------------------------------


def normalize_ratio(f_a: float, f_b: float) -> float:
    """Compute the frequency ratio normalized to one octave [1.0, 2.0).

    A4: Symmetry — normalize_ratio(a, b) == normalize_ratio(b, a).
    """
    if f_a <= 0 or f_b <= 0:
        return 1.0
    ratio = max(f_a, f_b) / min(f_a, f_b)
    # Fold into [1.0, 2.0) via octave reduction
    while ratio >= 2.0:
        ratio /= 2.0
    while ratio < 1.0:
        ratio *= 2.0
    return ratio


def nearest_consonance(ratio: float) -> Tuple[str, float, float]:
    """Find the nearest named interval to the given ratio.

    Returns (interval_name, deviation, base_dissonance).
    """
    best_name = "tritone"
    best_dev = float("inf")
    best_dis = 0.75

    for name, (ref_ratio, dissonance) in RATIO_DISSONANCE.items():
        dev = abs(ratio - ref_ratio)
        if dev < best_dev:
            best_dev = dev
            best_name = name
            best_dis = dissonance

    return best_name, best_dev, best_dis


def compute_dissonance(ratio: float, tolerance: float = 0.03) -> Tuple[str, float, float]:
    """Score the dissonance of a frequency ratio.

    Returns (interval_name, deviation, dissonance_score).

    The dissonance score blends the base dissonance of the nearest interval
    with a penalty for deviation from that pure ratio. Ratios far from any
    known consonance get maximum dissonance.

    Args:
        ratio: Octave-normalized frequency ratio [1.0, 2.0).
        tolerance: How close to a pure ratio counts as "in tune" (default 3%).
    """
    name, deviation, base_dissonance = nearest_consonance(ratio)

    # Deviation penalty: if you're not close to ANY consonance, you're dissonant
    # Normalized by the gap between adjacent intervals (~0.05)
    deviation_penalty = min(1.0, deviation / 0.05) * 0.5

    # Blend: base dissonance + deviation penalty, clamped to [0, 1]
    score = min(1.0, base_dissonance + deviation_penalty)

    # Grace zone: if within tolerance of a consonant interval, use base only
    if deviation <= tolerance:
        score = base_dissonance

    return name, deviation, score


def dissonance_to_verdict(score: float) -> GovernanceVerdict:
    """Map a dissonance score to an L13 governance verdict.

    Thresholds:
        [0.00, 0.25) → ALLOW
        [0.25, 0.50) → QUARANTINE
        [0.50, 0.75) → ESCALATE
        [0.75, 1.00] → DENY
    """
    if score < ALLOW_THRESHOLD:
        return GovernanceVerdict.ALLOW
    elif score < QUARANTINE_THRESHOLD:
        return GovernanceVerdict.QUARANTINE
    elif score < ESCALATE_THRESHOLD:
        return GovernanceVerdict.ESCALATE
    else:
        return GovernanceVerdict.DENY


# ---------------------------------------------------------------------------
# Public API — the full cross-chamber state check
# ---------------------------------------------------------------------------


def cross_chamber_check(
    agent_hz: float,
    dead_tone: str = "perfect_fifth",
    tolerance: float = 0.03,
    duration_s: float = DEFAULT_DURATION_S,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> ConsonanceReport:
    """Run a full cross-chamber acoustic state check.

    This is the main entry point. Given an agent's current frequency
    (derived from tongue prosody + color field) and the active dead tone,
    it:
        1. Generates both waveforms
        2. Superimposes them (cross-chamber combination)
        3. Runs FFT on the combined signal
        4. Extracts spectral features (energy, flux, centroid, peaks)
        5. Scores consonance from the frequency ratio
        6. Maps the dissonance score to a governance verdict

    Args:
        agent_hz: The frequency generated by the agent's current state.
        dead_tone: Which dead tone serves as baseline ("perfect_fifth",
                   "minor_sixth", "minor_seventh").
        tolerance: How close to a pure ratio counts as "in tune".
        duration_s: Waveform duration for FFT analysis.
        sample_rate: Samples per second.

    Returns:
        ConsonanceReport with full analysis and governance verdict.
    """
    baseline_hz = BASELINE_FREQUENCIES[dead_tone]

    # 1. Generate waves
    wave_root = generate_wave(baseline_hz, duration_s, sample_rate)
    wave_agent = generate_wave(agent_hz, duration_s, sample_rate)

    # 2. Superpose
    combined = superpose(wave_root, wave_agent)

    # 3. FFT + features
    spectral = extract_spectral_features(combined, baseline_hz, agent_hz, sample_rate)

    # 4. Ratio scoring
    ratio = normalize_ratio(baseline_hz, agent_hz)
    interval_name, deviation, dissonance = compute_dissonance(ratio, tolerance)

    # 5. Verdict
    verdict = dissonance_to_verdict(dissonance)

    return ConsonanceReport(
        baseline_hz=baseline_hz,
        agent_hz=agent_hz,
        frequency_ratio=ratio,
        nearest_interval=interval_name,
        interval_deviation=deviation,
        dissonance_score=dissonance,
        spectral=spectral,
        verdict=verdict,
        dead_tone=dead_tone,
    )


def check_all_dead_tones(
    agent_hz: float,
    tolerance: float = 0.03,
) -> List[ConsonanceReport]:
    """Run cross-chamber check against ALL three dead-tone baselines.

    Returns list of 3 ConsonanceReports. The strictest verdict wins
    (highest dissonance across all baselines).
    """
    return [cross_chamber_check(agent_hz, tone, tolerance) for tone in BASELINE_FREQUENCIES]


def strictest_verdict(reports: List[ConsonanceReport]) -> GovernanceVerdict:
    """Return the strictest (most restrictive) verdict from multiple reports."""
    order = [GovernanceVerdict.ALLOW, GovernanceVerdict.QUARANTINE, GovernanceVerdict.ESCALATE, GovernanceVerdict.DENY]
    worst = GovernanceVerdict.ALLOW
    for r in reports:
        if order.index(r.verdict) > order.index(worst):
            worst = r.verdict
    return worst
