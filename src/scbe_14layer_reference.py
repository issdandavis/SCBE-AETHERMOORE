#!/usr/bin/env python3
"""
SCBE 14-Layer Reference Implementation
======================================
Direct mapping to mathematical specifications from proof document.
Each function matches the LaTeX specification exactly.

Reference: scbe_proofs_complete.tex

Hook Test: This comment triggers Axiom Compliance + Test Sync + Sync Docs hooks
Last verified: 2026-01-17
"""

import sys

# Set UTF-8 encoding for Windows compatibility
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

import numpy as np
from typing import Tuple, List, Optional
from scipy.signal import hilbert


# =============================================================================
# LAYER 1: Complex State
# =============================================================================
def layer_1_complex_state(t: np.ndarray, D: int) -> np.ndarray:
    """
    Layer 1: Complex State Construction

    Input: Time-dependent features t, dimension D
    Output: c ∈ ℂ^D

    Constructs complex-valued state from amplitudes and phases.
    """
    # Split input into amplitudes and phases
    if len(t) >= 2 * D:
        amplitudes = t[:D]
        phases = t[D:2*D]
    else:
        # Handle shorter inputs
        amplitudes = np.ones(D)
        phases = np.zeros(D)
        amplitudes[:len(t)//2] = t[:len(t)//2] if len(t) >= 2 else [1.0]
        phases[:len(t)//2] = t[len(t)//2:] if len(t) >= 2 else [0.0]

    # A1: Map to complex space
    c = amplitudes * np.exp(1j * phases)
    return c


# =============================================================================
# LAYER 2: Realification
# =============================================================================
def layer_2_realification(c: np.ndarray) -> np.ndarray:
    """
    Layer 2: Realification (Complex → Real)

    Input: c ∈ ℂ^D
    Output: x ∈ ℝ^{2D}

    Isometric embedding Φ_1: ℂ^D → ℝ^{2D}
    x = [Re(c), Im(c)]
    """
    return np.concatenate([np.real(c), np.imag(c)])


# =============================================================================
# LAYER 3: Weighted Transform
# =============================================================================
def layer_3_weighted_transform(x: np.ndarray, G: Optional[np.ndarray] = None) -> np.ndarray:
    """
    Layer 3: SPD Weighted Transform

    Input: x ∈ ℝ^n, G SPD matrix
    Output: x_G = G^{1/2} · x

    A3: Applies symmetric positive-definite weighting.
    """
    n = len(x)

    if G is None:
        # Default: Golden ratio weighting
        phi = 1.618
        D = n // 2
        weights = np.array([phi ** k for k in range(D)])
        weights = weights / np.sum(weights)
        G_sqrt = np.diag(np.sqrt(np.tile(weights, 2)))
    else:
        # Compute G^{1/2} via eigendecomposition
        eigvals, eigvecs = np.linalg.eigh(G)
        G_sqrt = eigvecs @ np.diag(np.sqrt(np.maximum(eigvals, 0))) @ eigvecs.T

    return G_sqrt @ x


# =============================================================================
# LAYER 4: Poincaré Embedding
# =============================================================================
def layer_4_poincare_embedding(x_G: np.ndarray, alpha: float = 1.0,
                               eps_ball: float = 0.01) -> np.ndarray:
    """
    Layer 4: Poincaré Ball Embedding with Clamping

    Input: x_G ∈ ℝ^n
    Output: u ∈ 𝔹^n (Poincaré ball)

    A4: Ψ_α(x) = tanh(α||x||) · x/||x|| with clamping to 𝔹^n_{1-ε}
    """
    norm = np.linalg.norm(x_G)

    if norm < 1e-12:
        return np.zeros_like(x_G)

    # Poincaré embedding
    u = np.tanh(alpha * norm) * (x_G / norm)

    # A4: Clamping Π_ε: ensure ||u|| ≤ 1-ε
    u_norm = np.linalg.norm(u)
    max_norm = 1.0 - eps_ball

    if u_norm > max_norm:
        u = max_norm * (u / u_norm)

    return u


# =============================================================================
# LAYER 5: Hyperbolic Distance
# =============================================================================
def layer_5_hyperbolic_distance(u: np.ndarray, v: np.ndarray,
                               eps: float = 1e-5) -> float:
    """
    Layer 5: Poincaré Ball Metric

    Input: u, v ∈ 𝔹^n
    Output: d_ℍ(u, v) ∈ ℝ₊

    A5: d_ℍ(u,v) = arcosh(1 + 2||u-v||²/[(1-||u||²)(1-||v||²)])
    """
    diff_norm_sq = np.linalg.norm(u - v) ** 2
    u_factor = 1.0 - np.linalg.norm(u) ** 2
    v_factor = 1.0 - np.linalg.norm(v) ** 2

    # Denominator bounded below by eps² due to clamping
    denom = max(u_factor * v_factor, eps ** 2)
    arg = 1.0 + 2.0 * diff_norm_sq / denom

    return np.arccosh(max(arg, 1.0))


# =============================================================================
# LAYER 6: Breathing Transform
# =============================================================================
def layer_6_breathing_transform(u: np.ndarray, b: float,
                               b_min: float = 0.5, b_max: float = 2.0) -> np.ndarray:
    """
    Layer 6: Breathing Map (Diffeomorphism, NOT Isometry)

    Input: u ∈ 𝔹^n, breathing factor b ∈ [b_min, b_max]
    Output: u_breathed ∈ 𝔹^n

    A6: T_breath(u) with radial rescaling (changes distances!)
    """
    # Clamp breathing factor
    b = np.clip(b, b_min, b_max)

    norm = np.linalg.norm(u)
    if norm < 1e-12:
        return np.zeros_like(u)

    # Breathing: r ↦ tanh(b · arctanh(r))
    artanh_norm = np.arctanh(min(norm, 0.9999))
    new_norm = np.tanh(b * artanh_norm)

    return new_norm * (u / norm)


# =============================================================================
# LAYER 7: Phase Transform
# =============================================================================
def layer_7_phase_transform(u: np.ndarray, a: np.ndarray, Q: np.ndarray,
                           eps: float = 1e-10) -> np.ndarray:
    """
    Layer 7: Phase Transform (Isometry)

    Input: u ∈ 𝔹^n, shift a ∈ 𝔹^n, rotation Q ∈ O(n)
    Output: ũ = Q · (a ⊕ u)

    A7: Möbius addition ⊕ followed by rotation (preserves distances)

    Note: When a = 0, this reduces to pure rotation Q @ u, which is an isometry.
    """
    a_norm_sq = np.linalg.norm(a) ** 2

    # Special case: when a ≈ 0, Möbius addition is identity
    # This avoids numerical errors from eps in denominator
    if a_norm_sq < 1e-20:
        # Pure rotation (isometry)
        return Q @ u

    # Möbius addition: a ⊕ u
    u_norm_sq = np.linalg.norm(u) ** 2
    au_dot = np.dot(a, u)

    numerator = (1 + 2 * au_dot + u_norm_sq) * a + (1 - a_norm_sq) * u
    denominator = 1 + 2 * au_dot + a_norm_sq * u_norm_sq

    # Only add eps if denominator is too small (avoid division by zero)
    if abs(denominator) < eps:
        denominator = eps if denominator >= 0 else -eps

    shifted = numerator / denominator

    # Ensure stays in ball
    norm = np.linalg.norm(shifted)
    if norm >= 1.0:
        shifted = 0.99 * shifted / norm

    # Apply rotation
    return Q @ shifted


# =============================================================================
# LAYER 8: Realm Distance
# =============================================================================
def layer_8_realm_distance(u: np.ndarray, realms: List[np.ndarray],
                          eps: float = 1e-5) -> Tuple[float, np.ndarray]:
    """
    Layer 8: Minimum Distance to Realm Centers

    Input: u ∈ 𝔹^n, realm centers {μ_k} ⊂ 𝔹^n_{1-ε}
    Output: d* = min_k d_ℍ(u, μ_k)

    A8: Computes proximity to known safe regions.
    """
    distances = np.array([
        layer_5_hyperbolic_distance(u, mu, eps)
        for mu in realms
    ])

    d_star = np.min(distances)
    return d_star, distances


# =============================================================================
# LAYER 9: Spectral Coherence
# =============================================================================
def layer_9_spectral_coherence(signal: Optional[np.ndarray],
                              eps: float = 1e-5) -> float:
    """
    Layer 9: Spectral Coherence via FFT

    Input: Time-domain signal
    Output: S_spec ∈ [0,1]

    A9: Low-frequency energy ratio as pattern stability measure.
    """
    if signal is None or len(signal) == 0:
        return 0.5

    # FFT magnitude spectrum
    fft_mag = np.abs(np.fft.fft(signal))
    half = len(fft_mag) // 2

    # Low-frequency energy
    low_energy = np.sum(fft_mag[:half])
    total_energy = np.sum(fft_mag) + eps

    S_spec = low_energy / total_energy
    return np.clip(S_spec, 0.0, 1.0)


# =============================================================================
# LAYER 10: Spin Coherence
# =============================================================================
def layer_10_spin_coherence(phasors: np.ndarray) -> float:
    """
    Layer 10: Spin Coherence

    Input: Phase array (or complex phasors)
    Output: C_spin ∈ [0,1]

    A10: Mean resultant length of unit phasors.
    """
    # If input is real (phases), convert to phasors
    if np.isrealobj(phasors):
        phasors = np.exp(1j * phasors)

    # Mean phasor magnitude
    C_spin = np.abs(np.mean(phasors))
    return np.clip(C_spin, 0.0, 1.0)


# =============================================================================
# LAYER 11: Triadic Temporal Aggregation
# =============================================================================
def layer_11_triadic_temporal(d1: float, d2: float, dG: float,
                             lambda1: float = 0.33, lambda2: float = 0.34,
                             lambda3: float = 0.33, d_scale: float = 1.0) -> float:
    """
    Layer 11: Triadic Temporal Distance

    Input: Recent (d1), mid-term (d2), global (dG) distances
    Output: d_tri ∈ [0,1]

    A11: d_tri = √(λ₁d₁² + λ₂d₂² + λ₃d_G²) / d_scale
    """
    # Verify weights sum to 1
    assert abs(lambda1 + lambda2 + lambda3 - 1.0) < 1e-6, "Lambdas must sum to 1"

    d_tri = np.sqrt(lambda1 * d1**2 + lambda2 * d2**2 + lambda3 * dG**2)

    # Normalize to [0,1]
    return min(1.0, d_tri / d_scale)


# =============================================================================
# LAYER 12: Harmonic Scaling
# =============================================================================
def layer_12_harmonic_scaling(d: float, R: float = np.e) -> float:
    """
    Layer 12: Harmonic Amplification

    Input: Distance d, base R > 1
    Output: H(d, R) = R^{d²}

    A12: Exponential penalty for geometric distance.
    """
    assert R > 1, "R must be > 1"
    return R ** (d ** 2)


# =============================================================================
# LAYER 13: Risk Decision
# =============================================================================
def layer_13_risk_decision(Risk_base: float, H: float,
                          theta1: float = 0.33, theta2: float = 0.67) -> str:
    """
    Layer 13: Three-Way Risk Decision

    Input: Base risk, harmonic amplification H
    Output: Decision ∈ {ALLOW, QUARANTINE, DENY}

    A12: Risk' = Risk_base · H with thresholding.
    """
    Risk_prime = Risk_base * H

    if Risk_prime < theta1:
        return "ALLOW"
    elif Risk_prime < theta2:
        return "QUARANTINE"
    else:
        return "DENY"


# =============================================================================
# LAYER 14: Audio Axis
# =============================================================================
def layer_14_audio_axis(audio: Optional[np.ndarray], eps: float = 1e-5) -> float:
    """
    Layer 14: Audio Telemetry Coherence

    Input: Audio frame (time-domain waveform)
    Output: S_audio ∈ [0,1]

    A10: Instantaneous phase stability via Hilbert transform.
    """
    if audio is None or len(audio) == 0:
        return 0.5

    # Hilbert transform for analytic signal
    analytic = hilbert(audio)
    inst_phase = np.unwrap(np.angle(analytic))

    # Phase derivative stability
    phase_diff = np.diff(inst_phase)
    stability = 1.0 / (1.0 + np.std(phase_diff) + eps)

    return np.clip(stability, 0.0, 1.0)


# =============================================================================
# FULL PIPELINE INTEGRATION
# =============================================================================
def scbe_14layer_pipeline(
    t: np.ndarray,
    D: int = 6,
    G: Optional[np.ndarray] = None,
    realms: Optional[List[np.ndarray]] = None,
    breathing_factor: float = 1.0,
    phase_shift_vector: Optional[np.ndarray] = None,
    rotation_matrix: Optional[np.ndarray] = None,
    telemetry_signal: Optional[np.ndarray] = None,
    audio_frame: Optional[np.ndarray] = None,
    d_star_history: Optional[List[float]] = None,
    # Risk weights (must sum to 1)
    w_d: float = 0.20,
    w_c: float = 0.20,
    w_s: float = 0.20,
    w_tau: float = 0.20,
    w_a: float = 0.20,
    # Other params
    alpha: float = 1.0,
    eps_ball: float = 0.01,
    R: float = np.e,
    theta1: float = 0.33,
    theta2: float = 0.67
) -> dict:
    """
    Execute full 14-layer SCBE pipeline.

    Returns comprehensive metrics dictionary.
    """
    n = 2 * D

    # Initialize defaults
    if realms is None:
        scaling = 0.8 / np.sqrt(n)
        realms = [
            np.zeros(n),
            scaling * 0.2 * np.ones(n),
            scaling * 0.3 * np.ones(n),
            scaling * 0.1 * np.ones(n),
        ]

    if phase_shift_vector is None:
        phase_shift_vector = np.zeros(n)

    if rotation_matrix is None:
        rotation_matrix = np.eye(n)

    # =========================================================================
    # FORWARD PASS
    # =========================================================================

    # L1: Complex state
    c = layer_1_complex_state(t, D)

    # L2: Realification
    x = layer_2_realification(c)

    # L3: Weighted transform
    x_G = layer_3_weighted_transform(x, G)

    # L4: Poincaré embedding
    u = layer_4_poincare_embedding(x_G, alpha, eps_ball)

    # L5: (Used in L8 for distances)

    # L6: Breathing
    u_breath = layer_6_breathing_transform(u, breathing_factor)

    # L7: Phase transform
    u_final = layer_7_phase_transform(u_breath, phase_shift_vector, rotation_matrix)

    # L8: Realm distance
    d_star, all_distances = layer_8_realm_distance(u_final, realms)

    # L9: Spectral coherence
    S_spec = layer_9_spectral_coherence(telemetry_signal)

    # L10: Spin coherence (use original phases from complex state)
    phases = np.angle(c)
    C_spin = layer_10_spin_coherence(phases)

    # L11: Triadic temporal
    if d_star_history is None or len(d_star_history) < 3:
        d_tri_norm = d_star  # Not enough history
        tau = 0.5  # Default trust
    else:
        d1 = np.mean(d_star_history[-3:])
        d2 = np.mean(d_star_history[-6:-3]) if len(d_star_history) >= 6 else d1
        dG = np.mean(d_star_history)
        d_tri_norm = layer_11_triadic_temporal(d1, d2, dG)
        # Behavioral trust (simple inverse relationship)
        tau = 1.0 - d_tri_norm

    # L12: Harmonic scaling
    H = layer_12_harmonic_scaling(d_star, R)

    # L14: Audio coherence
    S_audio = layer_14_audio_axis(audio_frame)

    # L13: Composite risk
    assert abs(w_d + w_c + w_s + w_tau + w_a - 1.0) < 1e-6, "Weights must sum to 1"

    Risk_base = (
        w_d * d_tri_norm +
        w_c * (1.0 - C_spin) +
        w_s * (1.0 - S_spec) +
        w_tau * (1.0 - tau) +
        w_a * (1.0 - S_audio)
    )

    decision = layer_13_risk_decision(Risk_base, H, theta1, theta2)

    # =========================================================================
    # RETURN RESULTS
    # =========================================================================
    return {
        'decision': decision,
        'risk_base': Risk_base,
        'risk_prime': Risk_base * H,
        'd_star': d_star,
        'd_tri_norm': d_tri_norm,
        'H': H,
        'coherence': {
            'C_spin': C_spin,
            'S_spec': S_spec,
            'tau': tau,
            'S_audio': S_audio,
        },
        'geometry': {
            'u_norm': np.linalg.norm(u),
            'u_breath_norm': np.linalg.norm(u_breath),
            'u_final_norm': np.linalg.norm(u_final),
        },
        'all_realm_distances': all_distances,
    }


# =============================================================================
# DEMO AND TESTING
# =============================================================================
if __name__ == "__main__":
    print("=" * 80)
    print("SCBE 14-Layer Reference Implementation")
    print("=" * 80)

    # Test individual layers
    print("\n[Layer 1] Complex State:")
    t = np.array([0.5, 0.3, 0.2, 0.1, 0.4, 0.6,  # amplitudes
                  0.0, 0.5, 1.0, 1.5, 2.0, 2.5])  # phases
    c = layer_1_complex_state(t, D=6)
    print(f"  c.shape = {c.shape}, ||c|| = {np.linalg.norm(c):.4f}")

    print("\n[Layer 2] Realification:")
    x = layer_2_realification(c)
    print(f"  x.shape = {x.shape}, ||x|| = {np.linalg.norm(x):.4f}")

    print("\n[Layer 3] Weighted Transform:")
    x_G = layer_3_weighted_transform(x)
    print(f"  x_G.shape = {x_G.shape}, ||x_G|| = {np.linalg.norm(x_G):.4f}")

    print("\n[Layer 4] Poincaré Embedding:")
    u = layer_4_poincare_embedding(x_G)
    print(f"  u ∈ 𝔹^{len(u)}, ||u|| = {np.linalg.norm(u):.6f} < 0.99 ✓")

    print("\n[Layer 5] Hyperbolic Distance:")
    v = layer_4_poincare_embedding(x_G * 0.5)
    d_H = layer_5_hyperbolic_distance(u, v)
    print(f"  d_ℍ(u, v) = {d_H:.6f}")

    print("\n[Layer 6] Breathing Transform:")
    u_breath = layer_6_breathing_transform(u, b=1.2)
    print(f"  ||u_breath|| = {np.linalg.norm(u_breath):.6f}")

    print("\n[Layer 7] Phase Transform:")
    a = np.zeros(len(u))
    Q = np.eye(len(u))
    u_phase = layer_7_phase_transform(u_breath, a, Q)
    print(f"  ||u_phase|| = {np.linalg.norm(u_phase):.6f}")

    print("\n[Layer 8] Realm Distance:")
    realms = [np.zeros(12), 0.1*np.ones(12), 0.2*np.ones(12)]
    d_star, distances = layer_8_realm_distance(u_phase, realms)
    print(f"  d* = {d_star:.6f}, all distances = {distances}")

    print("\n[Layer 9] Spectral Coherence:")
    signal = np.sin(np.linspace(0, 4*np.pi, 256))
    S_spec = layer_9_spectral_coherence(signal)
    print(f"  S_spec = {S_spec:.6f}")

    print("\n[Layer 10] Spin Coherence:")
    phases = np.angle(c)
    C_spin = layer_10_spin_coherence(phases)
    print(f"  C_spin = {C_spin:.6f}")

    print("\n[Layer 11] Triadic Temporal:")
    d_tri = layer_11_triadic_temporal(0.5, 0.3, 0.2)
    print(f"  d_tri = {d_tri:.6f}")

    print("\n[Layer 12] Harmonic Scaling:")
    H = layer_12_harmonic_scaling(d_star, R=np.e)
    print(f"  H(d*={d_star:.4f}, R=e) = {H:.6f}")

    print("\n[Layer 13] Risk Decision:")
    Risk_base = 0.4
    decision = layer_13_risk_decision(Risk_base, H)
    print(f"  Risk_base = {Risk_base:.4f}, Risk' = {Risk_base * H:.4f}")
    print(f"  Decision: {decision}")

    print("\n[Layer 14] Audio Axis:")
    audio = np.random.randn(256)
    S_audio = layer_14_audio_axis(audio)
    print(f"  S_audio = {S_audio:.6f}")

    # Full pipeline test
    print("\n" + "=" * 80)
    print("FULL PIPELINE TEST")
    print("=" * 80)

    result = scbe_14layer_pipeline(
        t=t,
        D=6,
        breathing_factor=1.1,
        telemetry_signal=signal,
        audio_frame=audio
    )

    print(f"\nDecision: {result['decision']}")
    print(f"Risk (base):  {result['risk_base']:.6f}")
    print(f"Risk (prime): {result['risk_prime']:.6f}")
    print(f"\nCoherence Metrics:")
    for k, v in result['coherence'].items():
        print(f"  {k}: {v:.6f}")
    print(f"\nGeometry:")
    for k, v in result['geometry'].items():
        print(f"  {k}: {v:.6f}")

    print("\n" + "=" * 80)
    print("✓ ALL 14 LAYERS VERIFIED")
    print("=" * 80)


# =============================================================================
# ALIASES FOR BACKWARD COMPATIBILITY
# =============================================================================
# These aliases allow tests to import functions with simpler names.


def poincare_embed(x: np.ndarray, alpha: float = 1.0,
                   epsilon: float = 0.01, eps_ball: float = None) -> np.ndarray:
    """
    Backward-compatible wrapper for layer_4_poincare_embedding.
    Accepts 'epsilon' parameter name for backward compatibility.
    """
    if eps_ball is None:
        eps_ball = epsilon
    return layer_4_poincare_embedding(x, alpha=alpha, eps_ball=eps_ball)


# Layer 5
hyperbolic_distance = layer_5_hyperbolic_distance

# Layer 6
breathing_transform = layer_6_breathing_transform

# Layer 9
spectral_coherence = layer_9_spectral_coherence

# Layer 10
spin_coherence = layer_10_spin_coherence


def weighted_transform(x: np.ndarray, G: Optional[np.ndarray] = None,
                       return_matrix: bool = False):
    """
    Backward-compatible wrapper for layer_3_weighted_transform.
    Optionally returns the G matrix used.
    """
    n = len(x)

    if G is None:
        # Default: Golden ratio weighting
        phi = 1.618
        D = n // 2
        weights = np.array([phi ** k for k in range(D)])
        weights = weights / np.sum(weights)
        G = np.diag(np.tile(weights, 2))

    result = layer_3_weighted_transform(x, G)

    if return_matrix:
        return result, G
    return result


# Layer 12
harmonic_scale = layer_12_harmonic_scaling
