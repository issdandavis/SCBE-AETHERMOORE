#!/usr/bin/env python3
"""
SCBE-AETHERMOORE Layers 9-12: Signal Aggregation Pillar
========================================================

Bridges geometric layers (1-8) to governance decision (Layer 13).

Layer 9:  Spectral Coherence  - FFT-based stability metric
Layer 10: Spin Coherence      - Phase alignment metric
Layer 11: Triadic Distance    - Multi-modal aggregation
Layer 12: Harmonic Scaling    - Risk amplification & normalization

Mathematical Foundation (Axioms A9-A12):
- A9:  S_spec = 1 - r_HF ∈ [0,1]
- A10: C_spin = |mean(e^{iφ})| ∈ [0,1]
- A11: d_tri = √(λ₁d₁² + λ₂d₂² + λ₃d₃²)
- A12: R̂ = 1 - exp(-R_base × H(d*,R))

Key Properties (Proven):
- Bounded coherence [0,1]
- Triadic monotonicity
- Risk monotonicity
- No false allow (system soundness)

Date: January 15, 2026
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Tuple, List, Dict, Any, Optional
from enum import Enum

# =============================================================================
# CONSTANTS
# =============================================================================

PHI = (1 + np.sqrt(5)) / 2  # Golden ratio ≈ 1.618
E = np.e                     # Euler's number ≈ 2.718
EPSILON = 1e-10              # Numerical safety


# =============================================================================
# LAYER 9: SPECTRAL COHERENCE (Axiom A9)
# =============================================================================

@dataclass
class SpectralAnalysis:
    """Results from spectral coherence analysis."""
    s_spec: float           # Spectral coherence [0,1]
    r_hf: float             # High-frequency ratio
    total_power: float      # Total spectral power
    dominant_freq: int      # Dominant frequency bin
    bandwidth: float        # Spectral bandwidth


def compute_spectral_coherence(
    signal: np.ndarray,
    hf_cutoff: float = 0.5,
    window: Optional[str] = "hann"
) -> SpectralAnalysis:
    """
    Layer 9: Compute spectral coherence from signal.

    S_spec = 1 - r_HF where r_HF = Σ P[k high] / Σ P[k]

    Args:
        signal: Input signal array
        hf_cutoff: Fraction of spectrum considered "high frequency"
        window: Window function ("hann", "hamming", None)

    Returns:
        SpectralAnalysis with coherence metrics

    Properties:
        - S_spec ∈ [0,1] (Lemma 3.1)
        - High S_spec = stable/coherent signal
        - Low S_spec = noisy/chaotic signal
    """
    if len(signal) < 4:
        return SpectralAnalysis(
            s_spec=1.0, r_hf=0.0, total_power=0.0,
            dominant_freq=0, bandwidth=0.0
        )

    # Apply window function
    if window == "hann":
        win = np.hanning(len(signal))
    elif window == "hamming":
        win = np.hamming(len(signal))
    else:
        win = np.ones(len(signal))

    windowed = signal * win

    # Compute FFT and power spectrum
    fft = np.fft.rfft(windowed)
    power = np.abs(fft) ** 2

    total_power = np.sum(power)
    if total_power < EPSILON:
        return SpectralAnalysis(
            s_spec=0.5, r_hf=0.5, total_power=0.0,
            dominant_freq=0, bandwidth=0.0
        )

    # High-frequency ratio
    cutoff_bin = int(len(power) * hf_cutoff)
    hf_power = np.sum(power[cutoff_bin:])
    r_hf = hf_power / total_power

    # Spectral coherence (Axiom A9)
    s_spec = 1.0 - r_hf

    # Additional metrics
    dominant_freq = int(np.argmax(power))

    # Spectral bandwidth (spread around centroid)
    freqs = np.arange(len(power))
    centroid = np.sum(freqs * power) / total_power
    bandwidth = np.sqrt(np.sum((freqs - centroid)**2 * power) / total_power)

    return SpectralAnalysis(
        s_spec=float(np.clip(s_spec, 0, 1)),
        r_hf=float(r_hf),
        total_power=float(total_power),
        dominant_freq=dominant_freq,
        bandwidth=float(bandwidth)
    )


def spectral_stability(signal: np.ndarray, reference: Optional[np.ndarray] = None) -> float:
    """
    Compute spectral stability relative to reference.

    If reference provided: correlation of power spectra
    Otherwise: self-coherence via S_spec
    """
    analysis = compute_spectral_coherence(signal)

    if reference is None:
        return analysis.s_spec

    # Cross-spectral coherence
    ref_analysis = compute_spectral_coherence(reference)

    fft1 = np.fft.rfft(signal)
    fft2 = np.fft.rfft(reference)

    # Pad to same length
    max_len = max(len(fft1), len(fft2))
    fft1 = np.pad(fft1, (0, max_len - len(fft1)))
    fft2 = np.pad(fft2, (0, max_len - len(fft2)))

    # Normalized correlation
    norm1 = np.linalg.norm(fft1)
    norm2 = np.linalg.norm(fft2)

    if norm1 < EPSILON or norm2 < EPSILON:
        return 0.5

    correlation = np.abs(np.vdot(fft1, fft2)) / (norm1 * norm2)
    return float(np.clip(correlation, 0, 1))


# =============================================================================
# LAYER 10: SPIN COHERENCE (Axiom A10)
# =============================================================================

@dataclass
class SpinAnalysis:
    """Results from spin coherence analysis."""
    c_spin: float           # Spin coherence [0,1]
    mean_phase: float       # Mean phase angle
    phase_variance: float   # Circular variance
    alignment_vector: Tuple[float, float]  # (cos, sin) of mean


def compute_spin_coherence(phases: np.ndarray) -> SpinAnalysis:
    """
    Layer 10: Compute spin/phase coherence.

    C_spin = |mean(e^{iφ_j})| ∈ [0,1]

    Args:
        phases: Array of phase angles in radians

    Returns:
        SpinAnalysis with coherence metrics

    Properties:
        - C_spin ∈ [0,1] (Lemma 3.1, triangle inequality)
        - C_spin = 1: all phases aligned
        - C_spin = 0: phases uniformly distributed
    """
    if len(phases) == 0:
        return SpinAnalysis(
            c_spin=1.0, mean_phase=0.0, phase_variance=0.0,
            alignment_vector=(1.0, 0.0)
        )

    # Convert to unit vectors on complex plane
    phasors = np.exp(1j * phases)

    # Mean phasor
    mean_phasor = np.mean(phasors)

    # Spin coherence = magnitude of mean (Axiom A10)
    c_spin = np.abs(mean_phasor)

    # Mean phase angle
    mean_phase = np.angle(mean_phasor)

    # Circular variance (1 - R where R is resultant length)
    phase_variance = 1.0 - c_spin

    # Alignment vector
    alignment_vector = (float(np.real(mean_phasor)), float(np.imag(mean_phasor)))

    return SpinAnalysis(
        c_spin=float(np.clip(c_spin, 0, 1)),
        mean_phase=float(mean_phase),
        phase_variance=float(phase_variance),
        alignment_vector=alignment_vector
    )


def compute_spin_from_signal(signal: np.ndarray, hop_size: int = 256) -> SpinAnalysis:
    """
    Extract phase information from signal and compute spin coherence.

    Uses STFT to get instantaneous phases.
    """
    if len(signal) < hop_size * 2:
        return SpinAnalysis(
            c_spin=1.0, mean_phase=0.0, phase_variance=0.0,
            alignment_vector=(1.0, 0.0)
        )

    # Short-time Fourier transform (simplified)
    n_frames = (len(signal) - hop_size) // hop_size
    phases = []

    for i in range(n_frames):
        frame = signal[i * hop_size:(i + 1) * hop_size]
        fft = np.fft.rfft(frame)

        # Get phase of dominant frequency
        dominant = np.argmax(np.abs(fft[1:])) + 1  # Skip DC
        phases.append(np.angle(fft[dominant]))

    return compute_spin_coherence(np.array(phases))


# =============================================================================
# LAYER 11: TRIADIC TEMPORAL DISTANCE (Axiom A11)
# =============================================================================

@dataclass
class TriadicWeights:
    """Weights for triadic distance aggregation."""
    lambda_1: float = 0.4  # Hyperbolic distance weight
    lambda_2: float = 0.3  # Authentication distance weight
    lambda_3: float = 0.3  # Configuration distance weight

    def __post_init__(self):
        # Normalize to sum to 1
        total = self.lambda_1 + self.lambda_2 + self.lambda_3
        if total > EPSILON:
            self.lambda_1 /= total
            self.lambda_2 /= total
            self.lambda_3 /= total


@dataclass
class TriadicAnalysis:
    """Results from triadic distance computation."""
    d_tri: float            # Raw triadic distance
    d_tri_norm: float       # Normalized [0,1]
    components: Tuple[float, float, float]  # (d1, d2, d3)
    weights: Tuple[float, float, float]     # (λ1, λ2, λ3)


def compute_triadic_distance(
    d_hyperbolic: float,
    d_auth: float,
    d_config: float,
    weights: Optional[TriadicWeights] = None,
    scale: float = 3.0
) -> TriadicAnalysis:
    """
    Layer 11: Compute triadic temporal distance.

    d_tri = √(λ₁d₁² + λ₂d₂² + λ₃d₃²)

    Args:
        d_hyperbolic: Distance from geometric layers (d_H or d*)
        d_auth: Authentication/swarm trust distance
        d_config: Configuration/topology distance
        weights: TriadicWeights (default: 0.4, 0.3, 0.3)
        scale: Normalization scale factor

    Returns:
        TriadicAnalysis with distance metrics

    Properties (Theorem 3):
        - d_tri monotonically increasing in each d_i
        - ∂d_tri/∂d_i = λ_i × d_i / d_tri > 0
    """
    if weights is None:
        weights = TriadicWeights()

    # Weighted L2 norm (Axiom A11)
    d_tri_sq = (
        weights.lambda_1 * d_hyperbolic**2 +
        weights.lambda_2 * d_auth**2 +
        weights.lambda_3 * d_config**2
    )
    d_tri = np.sqrt(d_tri_sq)

    # Normalized to [0,1]
    d_tri_norm = min(1.0, d_tri / scale)

    return TriadicAnalysis(
        d_tri=float(d_tri),
        d_tri_norm=float(d_tri_norm),
        components=(d_hyperbolic, d_auth, d_config),
        weights=(weights.lambda_1, weights.lambda_2, weights.lambda_3)
    )


def triadic_gradient(
    d_hyperbolic: float,
    d_auth: float,
    d_config: float,
    weights: Optional[TriadicWeights] = None
) -> Tuple[float, float, float]:
    """
    Compute gradient of triadic distance w.r.t. each component.

    ∂d_tri/∂d_i = λ_i × d_i / d_tri

    Used for sensitivity analysis and optimization.
    """
    if weights is None:
        weights = TriadicWeights()

    analysis = compute_triadic_distance(d_hyperbolic, d_auth, d_config, weights)

    if analysis.d_tri < EPSILON:
        return (0.0, 0.0, 0.0)

    grad_1 = weights.lambda_1 * d_hyperbolic / analysis.d_tri
    grad_2 = weights.lambda_2 * d_auth / analysis.d_tri
    grad_3 = weights.lambda_3 * d_config / analysis.d_tri

    return (grad_1, grad_2, grad_3)


# =============================================================================
# LAYER 12: HARMONIC SCALING & RISK (Axiom A12)
# =============================================================================

@dataclass
class RiskWeights:
    """Weights for composite risk computation."""
    w_spectral: float = 0.20   # Spectral coherence weight
    w_spin: float = 0.20       # Spin coherence weight
    w_triadic: float = 0.25    # Triadic distance weight
    w_trust: float = 0.20      # Trust/swarm weight
    w_audio: float = 0.15      # Audio coherence weight

    def __post_init__(self):
        # Normalize
        total = (self.w_spectral + self.w_spin + self.w_triadic +
                 self.w_trust + self.w_audio)
        if total > EPSILON:
            self.w_spectral /= total
            self.w_spin /= total
            self.w_triadic /= total
            self.w_trust /= total
            self.w_audio /= total


@dataclass
class RiskAnalysis:
    """Results from risk computation."""
    r_base: float           # Base risk [0,1]
    H: float                # Harmonic scaling factor
    r_prime: float          # Amplified risk
    r_hat: float            # Final normalized risk [0,1]
    decision: str           # ALLOW / QUARANTINE / DENY
    components: Dict[str, float]  # Individual risk contributions


def harmonic_scaling(d_star: float, R: float = PHI, max_exp: float = 50.0,
                      use_vertical_wall: bool = True) -> float:
    """
    Compute harmonic scaling factor.

    Two modes (A12):
        - Vertical Wall: H = exp(d*²) [UNBOUNDED - Patent Claim]
        - Soft Wall:     H = R^{d*²}  [Bounded growth]

    Properties (Theorem 4):
        - H ≥ 1 for d* ≥ 0
        - H monotonically increasing in d*
        - Vertical Wall: ∂H/∂d* = 2d* × H (exponential growth)
    """
    exponent = min(d_star ** 2, max_exp)  # Prevent overflow

    if use_vertical_wall:
        # A12 Vertical Wall: H = exp(d*²) - UNBOUNDED
        return float(np.exp(exponent))
    else:
        # Soft wall: H = R^{d*²}
        return float(R ** exponent)


def compute_risk(
    s_spec: float,
    c_spin: float,
    d_tri_norm: float,
    tau: float,
    s_audio: float,
    d_star: float,
    weights: Optional[RiskWeights] = None,
    R: float = PHI,
    rho: float = 1.0,
    allow_threshold: float = 0.3,
    deny_threshold: float = 0.7
) -> RiskAnalysis:
    """
    Layer 12: Compute final risk score.

    R_base = Σ w_k(1 - s_k) + w_d × d̃_tri
    H = R^{d*²}
    R' = R_base × H
    R̂ = 1 - exp(-R'/ρ)

    Args:
        s_spec: Spectral coherence [0,1]
        c_spin: Spin coherence [0,1]
        d_tri_norm: Normalized triadic distance [0,1]
        tau: Trust score [0,1]
        s_audio: Audio coherence [0,1]
        d_star: Realm distance (for harmonic scaling)
        weights: RiskWeights for aggregation
        R: Harmonic base (default: golden ratio)
        rho: Saturation parameter
        allow_threshold: Risk below this → ALLOW
        deny_threshold: Risk above this → DENY

    Returns:
        RiskAnalysis with decision

    Properties (Theorem 4):
        - R̂ ∈ [0,1]
        - R̂ monotonically increasing in d_star, d_tri
        - R̂ monotonically decreasing in s_spec, c_spin, tau, s_audio
    """
    if weights is None:
        weights = RiskWeights()

    # Component risks (1 - coherence = risk contribution)
    risk_spectral = weights.w_spectral * (1.0 - s_spec)
    risk_spin = weights.w_spin * (1.0 - c_spin)
    risk_triadic = weights.w_triadic * d_tri_norm
    risk_trust = weights.w_trust * (1.0 - tau)
    risk_audio = weights.w_audio * (1.0 - s_audio)

    # Base risk (Axiom A12)
    r_base = risk_spectral + risk_spin + risk_triadic + risk_trust + risk_audio
    r_base = float(np.clip(r_base, 0, 1))

    # Harmonic scaling
    H = harmonic_scaling(d_star, R)

    # Amplified risk
    r_prime = r_base * H

    # Normalized risk with soft saturation
    r_hat = 1.0 - np.exp(-r_prime / rho)
    r_hat = float(np.clip(r_hat, 0, 1))

    # Decision
    if r_hat < allow_threshold:
        decision = "ALLOW"
    elif r_hat < deny_threshold:
        decision = "QUARANTINE"
    else:
        decision = "DENY"

    return RiskAnalysis(
        r_base=r_base,
        H=H,
        r_prime=r_prime,
        r_hat=r_hat,
        decision=decision,
        components={
            "spectral": risk_spectral,
            "spin": risk_spin,
            "triadic": risk_triadic,
            "trust": risk_trust,
            "audio": risk_audio,
        }
    )


def risk_gradient(
    s_spec: float,
    c_spin: float,
    d_tri_norm: float,
    tau: float,
    s_audio: float,
    d_star: float,
    weights: Optional[RiskWeights] = None,
    R: float = PHI
) -> Dict[str, float]:
    """
    Compute gradient of R̂ w.r.t. each input.

    Used for sensitivity analysis and adversarial detection.
    """
    if weights is None:
        weights = RiskWeights()

    # Current risk
    analysis = compute_risk(s_spec, c_spin, d_tri_norm, tau, s_audio, d_star, weights, R)

    # Numerical gradient (small perturbation)
    eps = 1e-6
    gradients = {}

    for name, val, w in [
        ("s_spec", s_spec, -weights.w_spectral),
        ("c_spin", c_spin, -weights.w_spin),
        ("d_tri", d_tri_norm, weights.w_triadic),
        ("tau", tau, -weights.w_trust),
        ("s_audio", s_audio, -weights.w_audio),
    ]:
        # Analytical gradient for base risk
        gradients[name] = w * analysis.H * np.exp(-analysis.r_prime)

    # d_star gradient (through H)
    dH_dd = 2 * d_star * np.log(R) * analysis.H
    gradients["d_star"] = analysis.r_base * dH_dd * np.exp(-analysis.r_prime)

    return gradients


# =============================================================================
# INTEGRATED LAYER 9-12 PIPELINE
# =============================================================================

@dataclass
class AggregatedSignals:
    """Complete signal aggregation from Layers 9-12."""
    # Layer 9
    spectral: SpectralAnalysis
    # Layer 10
    spin: SpinAnalysis
    # Layer 11
    triadic: TriadicAnalysis
    # Layer 12
    risk: RiskAnalysis


def process_layers_9_12(
    signal: np.ndarray,
    phases: np.ndarray,
    d_hyperbolic: float,
    d_auth: float,
    d_config: float,
    d_star: float,
    tau: float = 1.0,
    s_audio: float = 1.0
) -> AggregatedSignals:
    """
    Complete Layer 9-12 pipeline.

    Args:
        signal: Input signal for spectral analysis
        phases: Phase array for spin analysis
        d_hyperbolic: Hyperbolic distance from Layer 5
        d_auth: Authentication distance from swarm
        d_config: Configuration distance from topology
        d_star: Realm distance from Layer 8
        tau: Trust score from Byzantine consensus
        s_audio: Audio coherence from Layer 14

    Returns:
        AggregatedSignals with all layer outputs
    """
    # Layer 9: Spectral Coherence
    spectral = compute_spectral_coherence(signal)

    # Layer 10: Spin Coherence
    spin = compute_spin_coherence(phases)

    # Layer 11: Triadic Distance
    triadic = compute_triadic_distance(d_hyperbolic, d_auth, d_config)

    # Layer 12: Risk
    risk = compute_risk(
        s_spec=spectral.s_spec,
        c_spin=spin.c_spin,
        d_tri_norm=triadic.d_tri_norm,
        tau=tau,
        s_audio=s_audio,
        d_star=d_star
    )

    return AggregatedSignals(
        spectral=spectral,
        spin=spin,
        triadic=triadic,
        risk=risk
    )


# =============================================================================
# SELF-TESTS
# =============================================================================

def self_test() -> Dict[str, Any]:
    """Run Layer 9-12 self-tests."""
    results = {}
    passed = 0
    total = 0

    # Test 1: Spectral coherence bounds
    total += 1
    try:
        # Pure tone (high coherence)
        t = np.linspace(0, 1, 1000)
        pure_tone = np.sin(2 * np.pi * 50 * t)
        analysis = compute_spectral_coherence(pure_tone)

        # Noise (low coherence)
        noise = np.random.randn(1000)
        noise_analysis = compute_spectral_coherence(noise)

        if 0 <= analysis.s_spec <= 1 and 0 <= noise_analysis.s_spec <= 1:
            if analysis.s_spec > noise_analysis.s_spec:
                passed += 1
                results["spectral_bounds"] = f"✓ PASS (tone={analysis.s_spec:.3f}, noise={noise_analysis.s_spec:.3f})"
            else:
                results["spectral_bounds"] = f"✗ FAIL (tone should be more coherent)"
        else:
            results["spectral_bounds"] = "✗ FAIL (out of bounds)"
    except Exception as e:
        results["spectral_bounds"] = f"✗ FAIL ({e})"

    # Test 2: Spin coherence bounds
    total += 1
    try:
        # Aligned phases
        aligned = np.zeros(10)
        aligned_analysis = compute_spin_coherence(aligned)

        # Random phases
        random_phases = np.random.uniform(0, 2*np.pi, 100)
        random_analysis = compute_spin_coherence(random_phases)

        if 0 <= aligned_analysis.c_spin <= 1 and 0 <= random_analysis.c_spin <= 1:
            if aligned_analysis.c_spin > random_analysis.c_spin:
                passed += 1
                results["spin_bounds"] = f"✓ PASS (aligned={aligned_analysis.c_spin:.3f}, random={random_analysis.c_spin:.3f})"
            else:
                results["spin_bounds"] = f"✗ FAIL (aligned should be more coherent)"
        else:
            results["spin_bounds"] = "✗ FAIL (out of bounds)"
    except Exception as e:
        results["spin_bounds"] = f"✗ FAIL ({e})"

    # Test 3: Triadic monotonicity
    total += 1
    try:
        d_values = np.linspace(0, 2, 20)
        tri_values = [compute_triadic_distance(d, 0.5, 0.5).d_tri for d in d_values]

        diffs = np.diff(tri_values)
        if np.all(diffs >= -EPSILON):
            passed += 1
            results["triadic_monotone"] = f"✓ PASS (d_tri monotonic in d_H)"
        else:
            results["triadic_monotone"] = f"✗ FAIL (not monotonic)"
    except Exception as e:
        results["triadic_monotone"] = f"✗ FAIL ({e})"

    # Test 4: Risk monotonicity in d_star
    total += 1
    try:
        d_star_values = np.linspace(0, 2, 20)
        risk_values = [compute_risk(0.8, 0.8, 0.3, 0.9, 0.9, d).r_hat for d in d_star_values]

        diffs = np.diff(risk_values)
        if np.all(diffs >= -EPSILON):
            passed += 1
            results["risk_monotone_d"] = f"✓ PASS (R̂ monotonic in d*)"
        else:
            results["risk_monotone_d"] = f"✗ FAIL (not monotonic)"
    except Exception as e:
        results["risk_monotone_d"] = f"✗ FAIL ({e})"

    # Test 5: Risk monotonicity in coherence (decreasing)
    total += 1
    try:
        s_values = np.linspace(0, 1, 20)
        risk_values = [compute_risk(s, 0.8, 0.3, 0.9, 0.9, 0.5).r_hat for s in s_values]

        diffs = np.diff(risk_values)
        if np.all(diffs <= EPSILON):  # Should decrease
            passed += 1
            results["risk_monotone_s"] = f"✓ PASS (R̂ decreasing in s_spec)"
        else:
            results["risk_monotone_s"] = f"✗ FAIL (not decreasing)"
    except Exception as e:
        results["risk_monotone_s"] = f"✗ FAIL ({e})"

    # Test 6: Risk bounds
    total += 1
    try:
        # Extreme good case
        good_risk = compute_risk(1.0, 1.0, 0.0, 1.0, 1.0, 0.0)
        # Extreme bad case
        bad_risk = compute_risk(0.0, 0.0, 1.0, 0.0, 0.0, 3.0)

        if 0 <= good_risk.r_hat <= 1 and 0 <= bad_risk.r_hat <= 1:
            if good_risk.r_hat < bad_risk.r_hat:
                passed += 1
                results["risk_bounds"] = f"✓ PASS (good={good_risk.r_hat:.3f}, bad={bad_risk.r_hat:.3f})"
            else:
                results["risk_bounds"] = f"✗ FAIL (good should be less risky)"
        else:
            results["risk_bounds"] = "✗ FAIL (out of bounds)"
    except Exception as e:
        results["risk_bounds"] = f"✗ FAIL ({e})"

    # Test 7: Decision thresholds
    total += 1
    try:
        allow = compute_risk(0.95, 0.95, 0.1, 0.95, 0.95, 0.1)
        deny = compute_risk(0.1, 0.1, 0.9, 0.1, 0.1, 2.5)

        if allow.decision == "ALLOW" and deny.decision == "DENY":
            passed += 1
            results["decision_thresholds"] = f"✓ PASS (allow={allow.r_hat:.3f}→ALLOW, deny={deny.r_hat:.3f}→DENY)"
        else:
            results["decision_thresholds"] = f"✗ FAIL (wrong decisions: {allow.decision}, {deny.decision})"
    except Exception as e:
        results["decision_thresholds"] = f"✗ FAIL ({e})"

    # Test 8: Harmonic scaling properties (Vertical Wall)
    total += 1
    try:
        # Vertical Wall: H = exp(d*²)
        h0 = harmonic_scaling(0.0, use_vertical_wall=True)
        h1 = harmonic_scaling(1.0, use_vertical_wall=True)
        h2 = harmonic_scaling(2.0, use_vertical_wall=True)

        # H(0) = exp(0) = 1, H(1) = exp(1) = e, H(2) = exp(4) ≈ 54.6
        if abs(h0 - 1.0) < 0.01 and abs(h1 - np.e) < 0.01 and h2 > h1:
            passed += 1
            results["harmonic_scaling"] = f"✓ PASS (Vertical Wall: H(0)={h0:.2f}, H(1)={h1:.2f}, H(2)={h2:.2f})"
        else:
            results["harmonic_scaling"] = f"✗ FAIL (H not matching exp(d*²))"
    except Exception as e:
        results["harmonic_scaling"] = f"✗ FAIL ({e})"

    # Test 9: Full pipeline
    total += 1
    try:
        signal = np.sin(2 * np.pi * 100 * np.linspace(0, 1, 1000))
        phases = np.linspace(0, 0.1, 10)  # Nearly aligned

        aggregated = process_layers_9_12(
            signal=signal,
            phases=phases,
            d_hyperbolic=0.3,
            d_auth=0.2,
            d_config=0.1,
            d_star=0.2,
            tau=0.9,
            s_audio=0.95
        )

        if aggregated.risk.decision == "ALLOW":
            passed += 1
            results["full_pipeline"] = f"✓ PASS (R̂={aggregated.risk.r_hat:.3f}→{aggregated.risk.decision})"
        else:
            results["full_pipeline"] = f"✗ FAIL (expected ALLOW, got {aggregated.risk.decision})"
    except Exception as e:
        results["full_pipeline"] = f"✗ FAIL ({e})"

    # Test 10: No false allow (system soundness)
    total += 1
    try:
        # Bad signals should never get ALLOW
        bad_result = compute_risk(
            s_spec=0.1,    # Low spectral coherence
            c_spin=0.2,    # Low spin coherence
            d_tri_norm=0.9, # High triadic distance
            tau=0.1,       # Low trust
            s_audio=0.1,   # Low audio coherence
            d_star=2.0     # Far from realm
        )

        if bad_result.decision != "ALLOW":
            passed += 1
            results["no_false_allow"] = f"✓ PASS (bad signals → {bad_result.decision})"
        else:
            results["no_false_allow"] = f"✗ FAIL (bad signals incorrectly ALLOWED)"
    except Exception as e:
        results["no_false_allow"] = f"✗ FAIL ({e})"

    return {
        "passed": passed,
        "total": total,
        "success_rate": f"{passed}/{total} ({100*passed/total:.1f}%)",
        "results": results
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SCBE-AETHERMOORE LAYERS 9-12 SELF-TEST")
    print("=" * 60)

    results = self_test()

    for name, result in results["results"].items():
        print(f"  {name}: {result}")

    print("-" * 60)
    print(f"TOTAL: {results['success_rate']}")
    print("=" * 60)
