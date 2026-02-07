#!/usr/bin/env python3
"""
Three-Mechanism Combined Detection Experiment
==============================================

Tests the combined detection power of all three validated mechanisms:
  1. Phase + distance scoring (proven: 0.9999 AUC on synthetic)
  2. 6-tonic temporal coherence (proven: 1.0 AUC on replay/static/synthetic)
  3. Decimal drift authentication (proven: 0.9954 AUC on synthetic bypass)

Uses the REAL 14-layer SCBE pipeline (scbe_14layer_reference.py).

Each mechanism covers different attack classes:
  - Phase: wrong tongue/domain
  - 6-tonic: replay, static position, wrong frequency, synthetic
  - Drift: data that bypassed the pipeline, rounded decimals, scale anomalies

HYPOTHESIS: Combined three-mechanism detection achieves >0.99 AUC across
ALL attack types simultaneously, with each mechanism covering what others miss.

Author: SCBE-AETHERMOORE Experiments
Date: February 2026
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'SCBE-AETHERMOORE-v3.0.0', 'src'))

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json
from pathlib import Path
import time

# Import the real 14-layer pipeline
from scbe_14layer_reference import (
    layer_1_complex_state,
    layer_2_realification,
    layer_3_weighted_transform,
    layer_4_poincare_embedding,
    layer_5_hyperbolic_distance,
    layer_6_breathing_transform,
    layer_7_phase_transform,
    layer_8_realm_distance,
    layer_9_spectral_coherence,
    layer_10_spin_coherence,
    layer_11_triadic_temporal,
    layer_12_harmonic_scaling,
    layer_13_risk_decision,
    layer_14_audio_axis,
    scbe_14layer_pipeline,
)

# =============================================================================
# CONSTANTS
# =============================================================================

PHI = (1 + np.sqrt(5)) / 2
NUM_TONGUES = 6
TONGUE_NAMES = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR']
# Phase angles: 60 degree spacing (0, 60, 120, 180, 240, 300)
TONGUE_PHASES = np.array([i * (2 * np.pi / NUM_TONGUES) for i in range(NUM_TONGUES)])


# =============================================================================
# MECHANISM 1: Phase + Distance Scoring
# =============================================================================

def compute_phase_deviation(observed_phase: float, expected_phase: float) -> float:
    """
    Circular phase deviation normalized to [0, 1].

    0 = perfect alignment, 1 = maximum deviation (pi radians).
    """
    diff = abs(observed_phase - expected_phase) % (2 * np.pi)
    if diff > np.pi:
        diff = 2 * np.pi - diff
    return diff / np.pi  # Normalize to [0, 1]


def phase_distance_score(
    u: np.ndarray,
    tongue_idx: int,
    tongue_centroids: List[np.ndarray],
    observed_phase: float
) -> float:
    """
    Mechanism 1: Phase-augmented distance score.

    score = 1 / (1 + d_H + 2 * phase_dev)

    Higher score = more trusted.
    """
    expected_phase = TONGUE_PHASES[tongue_idx]
    phase_dev = compute_phase_deviation(observed_phase, expected_phase)

    # Hyperbolic distance to the assigned tongue centroid
    d_H = layer_5_hyperbolic_distance(u, tongue_centroids[tongue_idx])

    return 1.0 / (1.0 + d_H + 2.0 * phase_dev)


# =============================================================================
# MECHANISM 2: 6-Tonic Temporal Coherence
# =============================================================================

def compute_6tonic_coherence(
    position_history: np.ndarray,
    tongue_idx: int,
    time_steps: np.ndarray
) -> float:
    """
    Mechanism 2: 6-tonic spherical nodal oscillation coherence.

    Each tongue oscillates at frequency f_i = (i+1) * base_freq.
    Legitimate data tracks its tongue's oscillation.
    Score = correlation between position radius and expected oscillation.

    ANTI-REPLAY: Adds epoch-dependent chirp component that makes the
    expected pattern non-periodic. A replayed trajectory from a different
    time window will mismatch because the chirp phase drifts with absolute time.
    """
    if len(position_history) < 3:
        return 0.5

    base_freq = 0.1
    tongue_freq = (tongue_idx + 1) * base_freq

    # Anti-replay: epoch-dependent chirp adds a slowly varying phase
    # that depends on absolute time (not just relative offsets).
    # chirp_phase(t) = 0.05 * t^2 makes the pattern non-periodic.
    chirp = 0.05 * time_steps ** 2

    # Expected oscillation includes both the tongue frequency and chirp
    expected_oscillation = (0.5 + 0.3 * np.sin(2 * np.pi * tongue_freq * time_steps + chirp))

    # Observed: radius of position over time
    observed_radii = np.array([np.linalg.norm(p) for p in position_history])

    # Normalize both to zero mean
    expected_norm = expected_oscillation - np.mean(expected_oscillation)
    observed_norm = observed_radii - np.mean(observed_radii)

    # Correlation
    denom = np.linalg.norm(expected_norm) * np.linalg.norm(observed_norm) + 1e-10
    correlation = np.dot(expected_norm, observed_norm) / denom

    # Map from [-1, 1] to [0, 1]
    return float(np.clip((correlation + 1) / 2, 0, 1))


def compute_temporal_frequency_match(
    position_history: np.ndarray,
    tongue_idx: int,
    time_steps: np.ndarray
) -> float:
    """
    Check if the dominant frequency of position variation matches the tongue frequency.
    """
    if len(position_history) < 8:
        return 0.5

    base_freq = 0.1
    expected_freq = (tongue_idx + 1) * base_freq

    # FFT of position radii
    radii = np.array([np.linalg.norm(p) for p in position_history])
    radii_centered = radii - np.mean(radii)

    fft_mag = np.abs(np.fft.rfft(radii_centered))
    if len(fft_mag) < 2:
        return 0.5

    # Frequency resolution
    dt = time_steps[1] - time_steps[0] if len(time_steps) > 1 else 1.0
    freqs = np.fft.rfftfreq(len(radii_centered), d=dt)

    # Find the peak frequency (skip DC)
    peak_idx = np.argmax(fft_mag[1:]) + 1
    peak_freq = freqs[peak_idx] if peak_idx < len(freqs) else 0

    # How close is peak to expected?
    freq_error = abs(peak_freq - expected_freq)
    max_error = expected_freq + 0.05  # Normalize

    return float(np.clip(1.0 - freq_error / max_error, 0, 1))


# =============================================================================
# MECHANISM 3: Decimal Drift Authentication
# =============================================================================

def compute_drift_signature(pipeline_result: dict, input_data: np.ndarray = None) -> np.ndarray:
    """
    Mechanism 3: Extract drift signature from pipeline output + input analysis.

    Combines:
    - 13-dimensional pipeline output drift (layer-by-layer fingerprint)
    - Input fractional entropy analysis (detects rounded/calculated inputs)

    The input entropy analysis is the key to catching adaptive attackers:
    legitimate inputs have full float64 precision (~15 significant digits),
    while constructed/rounded inputs have reduced fractional entropy.
    """
    sig = np.zeros(17)  # Extended from 13 to 17

    # Geometry norms (from actual pipeline)
    geom = pipeline_result.get('geometry', {})
    sig[0] = geom.get('u_norm', 0)
    sig[1] = geom.get('u_breath_norm', 0)
    sig[2] = geom.get('u_final_norm', 0)

    # Coherence metrics
    coh = pipeline_result.get('coherence', {})
    sig[3] = coh.get('C_spin', 0)
    sig[4] = coh.get('S_spec', 0)
    sig[5] = coh.get('tau', 0)
    sig[6] = coh.get('S_audio', 0)

    # Distance metrics
    sig[7] = pipeline_result.get('d_star', 0)
    sig[8] = pipeline_result.get('d_tri_norm', 0)
    sig[9] = pipeline_result.get('H', 0)
    sig[10] = pipeline_result.get('risk_base', 0)
    sig[11] = pipeline_result.get('risk_prime', 0)

    # Fractional entropy of pipeline outputs
    frac_parts = np.abs(sig[:12] - np.floor(np.abs(sig[:12])))
    sig[12] = np.std(frac_parts) if np.any(frac_parts > 0) else 0

    # INPUT fractional entropy analysis (catches adaptive/rounded attacks)
    if input_data is not None:
        # Fractional parts of input
        input_frac = np.abs(input_data - np.floor(np.abs(input_data)))
        # Entropy of fractional distribution (binned)
        hist, _ = np.histogram(input_frac, bins=20, range=(0, 1))
        hist = hist / (np.sum(hist) + 1e-10)
        input_entropy = -np.sum(hist * np.log2(hist + 1e-10))
        sig[13] = input_entropy

        # Number of unique decimal places in input (rounded inputs have fewer)
        unique_decimals = len(set(
            len(f"{abs(x):.15g}".split('.')[-1]) if '.' in f"{abs(x):.15g}" else 0
            for x in input_data
        ))
        sig[14] = unique_decimals / len(input_data)

        # Kolmogorov-Smirnov-like test: how uniform are the fractional parts?
        # Legitimate data from rng.uniform/normal has near-uniform fractional parts
        # Rounded data clusters at specific fractional values
        sorted_frac = np.sort(input_frac)
        expected_uniform = np.linspace(0, 1, len(sorted_frac))
        ks_stat = np.max(np.abs(sorted_frac - expected_uniform))
        sig[15] = ks_stat

        # Bit-level precision: count trailing zeros in float representation
        # Rounded numbers have more trailing zeros
        precision_scores = []
        for x in input_data:
            s = f"{abs(x):.15e}"
            mantissa = s.split('e')[0].replace('.', '').rstrip('0')
            precision_scores.append(len(mantissa))
        sig[16] = np.mean(precision_scores) / 15.0  # Normalize by max precision
    else:
        sig[13:17] = 0.5  # Default

    return sig


def drift_distance_to_baseline(drift_sig: np.ndarray, baseline_sigs: np.ndarray) -> float:
    """
    Compute how far a drift signature is from the legitimate baseline cluster.

    Returns: distance (lower = more legitimate).
    """
    if len(baseline_sigs) == 0:
        return 1.0

    centroid = np.mean(baseline_sigs, axis=0)
    std = np.std(baseline_sigs, axis=0) + 1e-10

    # Mahalanobis-like distance (diagonal covariance)
    diff = (drift_sig - centroid) / std
    return float(np.linalg.norm(diff))


# =============================================================================
# COMBINED THREE-MECHANISM DETECTOR
# =============================================================================

@dataclass
class DetectionResult:
    """Result from three-mechanism detection."""
    phase_score: float
    tonic_score: float
    drift_score: float
    combined_score: float
    decision: str
    mechanism_contributions: Dict[str, float]


def three_mechanism_detect(
    input_data: np.ndarray,
    tongue_idx: int,
    position_history: np.ndarray,
    time_steps: np.ndarray,
    tongue_centroids: List[np.ndarray],
    baseline_drift_sigs: np.ndarray,
    pipeline_result: dict,
    # Weights for combination (tunable)
    w_phase: float = 0.35,
    w_tonic: float = 0.35,
    w_drift: float = 0.30,
) -> DetectionResult:
    """
    Combined three-mechanism adversarial detection.

    Returns a DetectionResult with scores from all three mechanisms
    and a combined decision.
    """
    # Mechanism 1: Phase + distance
    u = pipeline_result.get('_u_final', np.zeros(12))
    observed_phase = np.arctan2(
        np.mean(input_data[len(input_data)//2:]),
        np.mean(input_data[:len(input_data)//2])
    )
    phase_score = phase_distance_score(u, tongue_idx, tongue_centroids, observed_phase)

    # Mechanism 2: 6-tonic temporal coherence
    tonic_corr = compute_6tonic_coherence(position_history, tongue_idx, time_steps)
    tonic_freq = compute_temporal_frequency_match(position_history, tongue_idx, time_steps)
    tonic_score = 0.6 * tonic_corr + 0.4 * tonic_freq

    # Mechanism 3: Decimal drift (now includes input entropy analysis)
    drift_sig = compute_drift_signature(pipeline_result, input_data)
    drift_dist = drift_distance_to_baseline(drift_sig, baseline_drift_sigs)
    # Convert distance to score (lower distance = higher score)
    drift_score = 1.0 / (1.0 + drift_dist)

    # Combined score (weighted)
    combined = w_phase * phase_score + w_tonic * tonic_score + w_drift * drift_score

    # Decision thresholds
    if combined > 0.6:
        decision = "ALLOW"
    elif combined > 0.35:
        decision = "QUARANTINE"
    else:
        decision = "DENY"

    return DetectionResult(
        phase_score=phase_score,
        tonic_score=tonic_score,
        drift_score=drift_score,
        combined_score=combined,
        decision=decision,
        mechanism_contributions={
            'phase': w_phase * phase_score,
            'tonic': w_tonic * tonic_score,
            'drift': w_drift * drift_score,
        }
    )


# =============================================================================
# ATTACK GENERATORS
# =============================================================================

def generate_legitimate_input(rng, tongue_idx: int, D: int = 6) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate legitimate input that goes through the full pipeline with correct tongue.

    Returns: (input_features, position_history, time_steps)
    """
    # Base features with tongue-specific phase
    phase_offset = TONGUE_PHASES[tongue_idx]
    amplitudes = rng.uniform(0.1, 0.5, D)
    phases = phase_offset + rng.normal(0, 0.1, D)  # Centered on tongue phase

    input_data = np.concatenate([amplitudes, phases])

    # Generate position history tracking the tongue's oscillation
    num_steps = 20
    time_steps = np.linspace(0, 10, num_steps)
    base_freq = 0.1
    tongue_freq = (tongue_idx + 1) * base_freq

    position_history = np.zeros((num_steps, 2 * D))
    for t_idx, t in enumerate(time_steps):
        # Include epoch-dependent chirp matching the detector
        chirp = 0.05 * t ** 2
        r = 0.5 + 0.3 * np.sin(2 * np.pi * tongue_freq * t + chirp) + rng.normal(0, 0.02)
        angle = phase_offset + 0.05 * np.sin(0.5 * t)
        # Simple 2D projection for tracking
        pos = np.zeros(2 * D)
        pos[0] = r * np.cos(angle)
        pos[1] = r * np.sin(angle)
        pos[2:] = rng.normal(0, 0.05, 2 * D - 2)
        position_history[t_idx] = pos

    return input_data, position_history, time_steps


def generate_attack_A_wrong_tongue(rng, true_tongue: int, D: int = 6):
    """Attack A: Correct pipeline but WRONG tongue assignment."""
    wrong_tongue = (true_tongue + rng.integers(1, NUM_TONGUES)) % NUM_TONGUES
    phase_offset = TONGUE_PHASES[wrong_tongue]  # Wrong phase!

    amplitudes = rng.uniform(0.1, 0.5, D)
    phases = phase_offset + rng.normal(0, 0.1, D)

    input_data = np.concatenate([amplitudes, phases])

    num_steps = 20
    time_steps = np.linspace(0, 10, num_steps)
    base_freq = 0.1
    tongue_freq = (wrong_tongue + 1) * base_freq  # Tracking wrong tongue

    position_history = np.zeros((num_steps, 2 * D))
    for t_idx, t in enumerate(time_steps):
        chirp = 0.05 * t ** 2
        r = 0.5 + 0.3 * np.sin(2 * np.pi * tongue_freq * t + chirp) + rng.normal(0, 0.02)
        angle = phase_offset + 0.05 * np.sin(0.5 * t)
        pos = np.zeros(2 * D)
        pos[0] = r * np.cos(angle)
        pos[1] = r * np.sin(angle)
        pos[2:] = rng.normal(0, 0.05, 2 * D - 2)
        position_history[t_idx] = pos

    return input_data, position_history, time_steps, true_tongue


def generate_attack_B_replay(rng, tongue_idx: int, D: int = 6):
    """
    Attack B: Replay a legitimate trajectory from a different time window.

    The position history was generated for time window [0, 10], but
    the attacker presents it at time window [50, 60]. The chirp component
    in the 6-tonic detector makes the expected pattern different at t=50
    vs t=0, so the replayed positions won't correlate.
    """
    input_data, position_history, time_steps = generate_legitimate_input(rng, tongue_idx, D)

    # Replay: present the same positions but claim they're from a later time
    time_steps_shifted = time_steps + 50.0

    return input_data, position_history, time_steps_shifted, tongue_idx


def generate_attack_C_synthetic(rng, tongue_idx: int, D: int = 6):
    """Attack C: Synthetic data that never went through the pipeline."""
    amplitudes = rng.uniform(0.1, 0.5, D)
    phases = rng.uniform(0, 2 * np.pi, D)  # Random phases

    input_data = np.concatenate([amplitudes, phases])

    # Static position (no temporal coherence)
    num_steps = 20
    time_steps = np.linspace(0, 10, num_steps)
    position_history = np.tile(rng.normal(0, 0.3, 2 * D), (num_steps, 1))
    position_history += rng.normal(0, 0.001, position_history.shape)  # Tiny noise

    return input_data, position_history, time_steps, tongue_idx


def generate_attack_D_wrong_freq(rng, tongue_idx: int, D: int = 6):
    """Attack D: Correct tongue phase but wrong temporal frequency."""
    phase_offset = TONGUE_PHASES[tongue_idx]
    amplitudes = rng.uniform(0.1, 0.5, D)
    phases = phase_offset + rng.normal(0, 0.1, D)  # Correct phase

    input_data = np.concatenate([amplitudes, phases])

    num_steps = 20
    time_steps = np.linspace(0, 10, num_steps)
    base_freq = 0.1
    wrong_freq = ((tongue_idx + 3) % NUM_TONGUES + 1) * base_freq  # Different frequency

    position_history = np.zeros((num_steps, 2 * D))
    for t_idx, t in enumerate(time_steps):
        chirp = 0.05 * t ** 2  # Attacker tries to use chirp but with wrong freq
        r = 0.5 + 0.3 * np.sin(2 * np.pi * wrong_freq * t + chirp) + rng.normal(0, 0.02)
        angle = phase_offset + 0.05 * np.sin(0.5 * t)
        pos = np.zeros(2 * D)
        pos[0] = r * np.cos(angle)
        pos[1] = r * np.sin(angle)
        pos[2:] = rng.normal(0, 0.05, 2 * D - 2)
        position_history[t_idx] = pos

    return input_data, position_history, time_steps, tongue_idx


def generate_attack_E_scale_anomaly(rng, tongue_idx: int, D: int = 6):
    """Attack E: Correct tongue but anomalous amplitude scaling."""
    phase_offset = TONGUE_PHASES[tongue_idx]
    amplitudes = rng.uniform(2.0, 5.0, D)  # Way too large
    phases = phase_offset + rng.normal(0, 0.1, D)

    input_data = np.concatenate([amplitudes, phases])

    num_steps = 20
    time_steps = np.linspace(0, 10, num_steps)
    base_freq = 0.1
    tongue_freq = (tongue_idx + 1) * base_freq

    position_history = np.zeros((num_steps, 2 * D))
    for t_idx, t in enumerate(time_steps):
        r = 2.0 + 0.3 * np.sin(2 * np.pi * tongue_freq * t) + rng.normal(0, 0.02)
        angle = phase_offset
        pos = np.zeros(2 * D)
        pos[0] = r * np.cos(angle)
        pos[1] = r * np.sin(angle)
        pos[2:] = rng.normal(0, 0.3, 2 * D - 2)
        position_history[t_idx] = pos

    return input_data, position_history, time_steps, tongue_idx


def generate_attack_F_adaptive(rng, tongue_idx: int, D: int = 6):
    """
    Attack F: Adaptive attacker that knows phase AND frequency AND chirp,
    but constructs inputs externally (rounds to 4 decimals).

    This is the hardest attack. The attacker:
    - Knows the correct tongue phase
    - Knows the correct frequency
    - Knows the chirp formula
    - Tracks the oscillation correctly
    But their INPUT DATA has reduced precision (rounded), which the
    drift mechanism should detect via fractional entropy analysis.
    """
    # Attacker uses correct phase and frequency
    phase_offset = TONGUE_PHASES[tongue_idx]
    amplitudes = rng.uniform(0.1, 0.5, D)
    phases = phase_offset + rng.normal(0, 0.05, D)

    input_data = np.concatenate([amplitudes, phases])

    num_steps = 20
    time_steps = np.linspace(0, 10, num_steps)
    base_freq = 0.1
    tongue_freq = (tongue_idx + 1) * base_freq

    position_history = np.zeros((num_steps, 2 * D))
    for t_idx, t in enumerate(time_steps):
        chirp = 0.05 * t ** 2
        r = 0.5 + 0.3 * np.sin(2 * np.pi * tongue_freq * t + chirp) + rng.normal(0, 0.02)
        angle = phase_offset + 0.05 * np.sin(0.5 * t)
        pos = np.zeros(2 * D)
        pos[0] = r * np.cos(angle)
        pos[1] = r * np.sin(angle)
        pos[2:] = rng.normal(0, 0.05, 2 * D - 2)
        position_history[t_idx] = pos

    # Adaptive attacker's "tell": constructed input with reduced precision
    # Rounds to 4 decimal places (legitimate inputs have ~15 decimal places)
    input_data = np.round(input_data, 4)

    return input_data, position_history, time_steps, tongue_idx


# =============================================================================
# EXPERIMENT RUNNER
# =============================================================================

def run_pipeline_and_extend(input_data: np.ndarray, D: int = 6) -> dict:
    """
    Run the real 14-layer pipeline and extend the result with
    the intermediate u_final vector for phase scoring.
    """
    result = scbe_14layer_pipeline(t=input_data, D=D)

    # Also compute u_final explicitly for the phase scorer
    c = layer_1_complex_state(input_data, D)
    x = layer_2_realification(c)
    x_G = layer_3_weighted_transform(x)
    u = layer_4_poincare_embedding(x_G)
    u_breath = layer_6_breathing_transform(u, 1.0)
    a = np.zeros(2 * D)
    Q = np.eye(2 * D)
    u_final = layer_7_phase_transform(u_breath, a, Q)

    result['_u_final'] = u_final
    return result


def compute_roc_auc(scores: np.ndarray, labels: np.ndarray, num_thresholds: int = 500) -> float:
    """Compute ROC-AUC from scores and binary labels."""
    if len(np.unique(labels)) < 2:
        return 0.5
    if len(np.unique(scores)) < 2:
        return 0.5

    min_s, max_s = np.min(scores), np.max(scores)
    thresholds = np.linspace(min_s - 0.01, max_s + 0.01, num_thresholds)

    tprs, fprs = [], []
    for thresh in thresholds:
        pred_pos = scores >= thresh
        tp = np.sum(pred_pos & (labels == 1))
        fp = np.sum(pred_pos & (labels == 0))
        fn = np.sum(~pred_pos & (labels == 1))
        tn = np.sum(~pred_pos & (labels == 0))

        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        tprs.append(tpr)
        fprs.append(fpr)

    tprs, fprs = np.array(tprs), np.array(fprs)
    sorted_idx = np.argsort(fprs)
    return float(np.abs(np.trapezoid(tprs[sorted_idx], fprs[sorted_idx])))


def run_experiment():
    """Run the full three-mechanism combined experiment."""
    print("=" * 80)
    print("  THREE-MECHANISM COMBINED DETECTION EXPERIMENT")
    print("  Phase + 6-Tonic + Drift on REAL 14-Layer Pipeline")
    print("=" * 80)

    rng = np.random.default_rng(42)
    D = 6
    n = 2 * D
    num_trials = 50  # Per attack type

    # Create tongue centroids in the Poincare ball
    tongue_centroids = []
    for i in range(NUM_TONGUES):
        centroid = np.zeros(n)
        angle = TONGUE_PHASES[i]
        centroid[0] = 0.3 * np.cos(angle)
        centroid[1] = 0.3 * np.sin(angle)
        tongue_centroids.append(centroid)

    # Step 1: Generate baseline drift signatures from legitimate inputs
    print("\n[Step 1] Building legitimate drift baseline...")
    baseline_drift_sigs = []
    for _ in range(100):
        tongue_idx = rng.integers(0, NUM_TONGUES)
        inp, pos_hist, t_steps = generate_legitimate_input(rng, tongue_idx, D)
        result = run_pipeline_and_extend(inp, D)
        sig = compute_drift_signature(result, inp)
        baseline_drift_sigs.append(sig)
    baseline_drift_sigs = np.array(baseline_drift_sigs)
    print(f"  Built baseline from {len(baseline_drift_sigs)} legitimate samples")

    # Step 2: Define attack types
    attack_generators = {
        'A_wrong_tongue': generate_attack_A_wrong_tongue,
        'B_replay': generate_attack_B_replay,
        'C_synthetic': generate_attack_C_synthetic,
        'D_wrong_freq': generate_attack_D_wrong_freq,
        'E_scale_anomaly': generate_attack_E_scale_anomaly,
        'F_adaptive': generate_attack_F_adaptive,
    }

    # Step 3: Run detection on all attack types
    print("\n[Step 2] Running detection across all attack types...")
    results = {}

    for attack_name, attack_gen in attack_generators.items():
        print(f"\n  Attack: {attack_name}")

        all_scores = {
            'phase': [], 'tonic': [], 'drift': [],
            'combined': [], 'phase_only': [], 'tonic_only': [], 'drift_only': []
        }
        labels = []

        for trial in range(num_trials):
            # Generate legitimate sample
            tongue_idx = rng.integers(0, NUM_TONGUES)
            leg_inp, leg_hist, leg_time = generate_legitimate_input(rng, tongue_idx, D)
            leg_result = run_pipeline_and_extend(leg_inp, D)

            leg_detect = three_mechanism_detect(
                leg_inp, tongue_idx, leg_hist, leg_time,
                tongue_centroids, baseline_drift_sigs, leg_result
            )

            all_scores['phase'].append(leg_detect.phase_score)
            all_scores['tonic'].append(leg_detect.tonic_score)
            all_scores['drift'].append(leg_detect.drift_score)
            all_scores['combined'].append(leg_detect.combined_score)
            labels.append(0)  # legitimate

            # Generate attack sample
            atk_result = attack_gen(rng, tongue_idx, D)
            atk_inp, atk_hist, atk_time, atk_tongue = atk_result

            atk_pipeline = run_pipeline_and_extend(atk_inp, D)

            atk_detect = three_mechanism_detect(
                atk_inp, tongue_idx, atk_hist, atk_time,
                tongue_centroids, baseline_drift_sigs, atk_pipeline
            )

            all_scores['phase'].append(atk_detect.phase_score)
            all_scores['tonic'].append(atk_detect.tonic_score)
            all_scores['drift'].append(atk_detect.drift_score)
            all_scores['combined'].append(atk_detect.combined_score)
            labels.append(1)  # attack

        labels = np.array(labels)

        # Compute AUC for each mechanism and combined
        # Note: higher score = more legitimate, so attacks should have LOWER scores
        # AUC computed with legitimate=positive
        phase_auc = compute_roc_auc(
            -np.array(all_scores['phase']), labels
        )
        tonic_auc = compute_roc_auc(
            -np.array(all_scores['tonic']), labels
        )
        drift_auc = compute_roc_auc(
            -np.array(all_scores['drift']), labels
        )
        combined_auc = compute_roc_auc(
            -np.array(all_scores['combined']), labels
        )

        results[attack_name] = {
            'phase_auc': phase_auc,
            'tonic_auc': tonic_auc,
            'drift_auc': drift_auc,
            'combined_auc': combined_auc,
            'n_samples': len(labels),
        }

        print(f"    Phase AUC:    {phase_auc:.4f}")
        print(f"    6-Tonic AUC:  {tonic_auc:.4f}")
        print(f"    Drift AUC:    {drift_auc:.4f}")
        print(f"    COMBINED AUC: {combined_auc:.4f}")

    # Step 4: Print summary table
    print("\n" + "=" * 80)
    print("  RESULTS SUMMARY")
    print("=" * 80)
    print(f"\n  {'Attack':<20} {'Phase':>8} {'6-Tonic':>8} {'Drift':>8} {'COMBINED':>10}")
    print("  " + "-" * 60)

    for attack_name in attack_generators:
        r = results[attack_name]
        print(f"  {attack_name:<20} {r['phase_auc']:>8.4f} {r['tonic_auc']:>8.4f} "
              f"{r['drift_auc']:>8.4f} {r['combined_auc']:>10.4f}")

    # Average across all attacks
    avg_phase = np.mean([r['phase_auc'] for r in results.values()])
    avg_tonic = np.mean([r['tonic_auc'] for r in results.values()])
    avg_drift = np.mean([r['drift_auc'] for r in results.values()])
    avg_combined = np.mean([r['combined_auc'] for r in results.values()])

    print("  " + "-" * 60)
    print(f"  {'AVERAGE':<20} {avg_phase:>8.4f} {avg_tonic:>8.4f} "
          f"{avg_drift:>8.4f} {avg_combined:>10.4f}")

    # Step 5: Coverage analysis
    print("\n" + "=" * 80)
    print("  COVERAGE ANALYSIS: Which mechanism catches which attack?")
    print("=" * 80)
    print(f"  (AUC > 0.75 = 'catches', shown as +)")
    print(f"\n  {'Attack':<20} {'Phase':>8} {'6-Tonic':>8} {'Drift':>8} {'Gap?':>6}")
    print("  " + "-" * 55)

    any_gap = False
    for attack_name in attack_generators:
        r = results[attack_name]
        p = "+" if r['phase_auc'] > 0.75 else "-"
        t = "+" if r['tonic_auc'] > 0.75 else "-"
        d = "+" if r['drift_auc'] > 0.75 else "-"
        gap = "YES" if max(r['phase_auc'], r['tonic_auc'], r['drift_auc']) < 0.75 else "no"
        if gap == "YES":
            any_gap = True
        print(f"  {attack_name:<20} {p:>8} {t:>8} {d:>8} {gap:>6}")

    if not any_gap:
        print("\n  RESULT: No coverage gaps. Every attack is caught by at least one mechanism.")
    else:
        print("\n  WARNING: Coverage gaps detected. Some attacks are not reliably caught.")

    # Step 6: Verdict
    print("\n" + "=" * 80)
    print("  VERDICT")
    print("=" * 80)

    if avg_combined >= 0.95:
        print(f"\n  STRONG PASS: Average combined AUC = {avg_combined:.4f}")
        print("  Three-mechanism defense achieves robust detection across all attack types.")
    elif avg_combined >= 0.80:
        print(f"\n  PASS: Average combined AUC = {avg_combined:.4f}")
        print("  Three-mechanism defense provides meaningful improvement over single mechanisms.")
    elif avg_combined >= 0.65:
        print(f"\n  WEAK PASS: Average combined AUC = {avg_combined:.4f}")
        print("  Combined detection works but individual mechanisms need tuning.")
    else:
        print(f"\n  FAIL: Average combined AUC = {avg_combined:.4f}")
        print("  Combined detection does not achieve reliable adversarial detection.")

    # Per-mechanism value added
    print(f"\n  Per-mechanism average AUC:")
    print(f"    Phase alone:    {avg_phase:.4f}")
    print(f"    6-Tonic alone:  {avg_tonic:.4f}")
    print(f"    Drift alone:    {avg_drift:.4f}")
    print(f"    Combined:       {avg_combined:.4f}")

    best_single = max(avg_phase, avg_tonic, avg_drift)
    improvement = avg_combined - best_single
    print(f"\n  Improvement over best single mechanism: {improvement:+.4f}")

    print("=" * 80)

    # Save results
    output = {
        'experiment': 'three_mechanism_combined',
        'date': '2026-02-06',
        'pipeline': 'REAL scbe_14layer_reference.py',
        'num_trials_per_attack': num_trials,
        'results': results,
        'averages': {
            'phase': avg_phase,
            'tonic': avg_tonic,
            'drift': avg_drift,
            'combined': avg_combined,
        },
        'coverage_gaps': any_gap,
    }

    output_path = Path(__file__).parent / "three_mechanism_results.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {output_path}")

    return output


if __name__ == '__main__':
    run_experiment()
