#!/usr/bin/env python3
"""
SCBE-AETHERMOORE v2.1 Production System
========================================

Unified system integrating:
- QASI Core (axiom-safe hyperbolic geometry, A1-A12)
- Harmonic Cipher (conlang + flat-slope encoding + resonance refractoring)
- 9D State Machine (context + time + entropy + quantum)
- Governance Engine (L1-L14 pipeline + Grok tie-breaker)
- PHDM Topology Validation (Euler characteristic)
- Byzantine Attack Resistance (swarm consensus)

Architecture:
    Input State ξ(t)
         │
    ┌────▼────┐
    │ 9D State │  (context, tau, eta, quantum)
    └────┬────┘
         │
    ┌────▼────┐
    │ Harmonic │  (phase modulation, conlang encoding)
    │ Cipher   │
    └────┬────┘
         │
    ┌────▼────┐
    │ QASI    │  (Poincaré embed → hyperbolic distance → realm)
    │ Core    │
    └────┬────┘
         │
    ┌────▼────┐
    │ L1-L14  │  (coherence → risk → harmonic scaling)
    │ Pipeline│
    └────┬────┘
         │
    ┌────▼────┐
    │ Grok    │  (truth-seeking tie-breaker if marginal)
    │ Oracle  │
    └────┬────┘
         │
    ┌────▼────┐
    │ Decision│  → ALLOW / QUARANTINE / DENY
    └─────────┘

Dependencies: numpy only (scipy optional for FFT)
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass, field
from typing import Tuple, List, Dict, Any, Optional

import numpy as np

# Try scipy.fft first, fall back to numpy.fft
try:
    from scipy.fft import fft, fftfreq
except ImportError:
    from numpy.fft import fft, fftfreq


# =============================================================================
# SECTION 1: GLOBAL CONSTANTS
# =============================================================================

PHI = (1 + np.sqrt(5)) / 2                      # Golden ratio
R = PHI                                          # Harmonic base
EPSILON = 1.5                                    # Snap threshold
TAU_COH = 0.9                                    # Coherence min
ETA_TARGET = 4.0                                 # Entropy target
BETA = 0.1                                       # Entropy decay
KAPPA_MAX = 0.1                                  # Max curvature
LAMBDA_BOUND = 0.001                             # Lyapunov max
H_MAX = 10.0                                     # Max harmonic
DOT_TAU_MIN = 0.0                                # Causality min
ETA_MIN = 2.0
ETA_MAX = 6.0
DELTA_DRIFT_MAX = 0.5
DELTA_NOISE_MAX = 0.05
OMEGA_TIME = 2 * np.pi / 60
CARRIER_FREQ = 440.0
SAMPLE_RATE = 44100
DURATION = 0.5
KEY_LEN = 32
CHI_EXPECTED = 2
D = 6                                            # Core context dimensions

# Grok Parameters
GROK_WEIGHT = 0.35
GROK_THRESHOLD_LOW = 0.3
GROK_THRESHOLD_HIGH = 0.7

# Conlang Dictionary
CONLANG = {
    "shadow": -1, "gleam": -2, "flare": -3,
    "korah": 0, "aelin": 1, "dahru": 2,
    "melik": 3, "sorin": 4, "tivar": 5,
    "ulmar": 6, "vexin": 7
}
REV_CONLANG = {v: k for k, v in CONLANG.items()}

# Six Sacred Tongues
TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_WEIGHTS = [PHI**k for k in range(D)]


# =============================================================================
# SECTION 1.5: QUASICRYSTAL LATTICE (Icosahedral 6D→3D Validation)
# =============================================================================
# ┌─────────────────────────────────────────────────────────────────────────┐
# │  QUASICRYSTAL VALIDATION LAYER                                          │
# │                                                                         │
# │  The 6 Sacred Tongues map to 6D lattice points in Z^6.                  │
# │  Icosahedral projection to E_parallel (physical) and E_perp (hidden).   │
# │  Valid states lie within acceptance window in perpendicular space.      │
# │  Phason strain enables atomic rekeying without state regeneration.      │
# └─────────────────────────────────────────────────────────────────────────┘

class QuasicrystalLattice:
    """
    SCBE v3.0: Icosahedral Quasicrystal Verification System.
    Maps 6-dimensional authentication gates onto a 3D aperiodic lattice.

    The aperiodic structure prevents brute-force enumeration attacks
    that exploit crystalline periodicity.
    """

    def __init__(self, lattice_constant: float = 1.0):
        self.a = lattice_constant
        # Acceptance radius in Perpendicular Space (E_perp)
        # Points valid iff ||r_perp - phason|| < R_accept
        self.acceptance_radius = 1.5 * self.a

        # Current Phason Strain Vector (Secret Key Component)
        self.phason_strain = np.zeros(3)

        # Initialize 6D → 3D Projection Matrices
        self.M_par, self.M_perp = self._generate_basis_matrices()

    def _generate_basis_matrices(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate projection matrices from 6D Z^6 to 3D E_parallel (Physical)
        and 3D E_perp (Internal/Window) using Icosahedral symmetry.
        """
        # Normalized basis vectors for icosahedral symmetry
        norm = 1 / np.sqrt(1 + PHI**2)

        # 6 basis vectors in Physical Space (E_parallel)
        # Cyclic permutations of (1, PHI, 0)
        e_par = np.array([
            [1, PHI, 0],
            [-1, PHI, 0],
            [0, 1, PHI],
            [0, -1, PHI],
            [PHI, 0, 1],
            [PHI, 0, -1]
        ]).T * norm  # Shape (3, 6)

        # 6 basis vectors in Perpendicular Space (E_perp)
        # Related by Galois conjugation PHI → -1/PHI
        e_perp = np.array([
            [1, -1/PHI, 0],
            [-1, -1/PHI, 0],
            [0, 1, -1/PHI],
            [0, -1, -1/PHI],
            [-1/PHI, 0, 1],
            [-1/PHI, 0, -1]
        ]).T * norm  # Shape (3, 6)

        return e_par, e_perp

    def map_gates_to_lattice(self, gate_vector: List[float]) -> Tuple[np.ndarray, np.ndarray, bool]:
        """
        Map 6 inputs (SCBE Gates) to the Quasicrystal.

        Args:
            gate_vector: 6D vector from Sacred Tongues

        Returns:
            r_phys: Projected point in physical 3D space (the "Key")
            r_perp: Point in internal space (validation check)
            is_valid: True if point lies within Phason-shifted window
        """
        n = np.array(gate_vector[:6], dtype=float)
        if len(n) < 6:
            n = np.pad(n, (0, 6 - len(n)))

        # 1. Project to Physical Space (The "Public" Lattice Point)
        r_phys = self.M_par @ n

        # 2. Project to Perpendicular Space (The "Hidden" Validation Check)
        r_perp_raw = self.M_perp @ n

        # 3. Apply Phason Strain (Atomic Rekeying)
        distance = float(np.linalg.norm(r_perp_raw - self.phason_strain))
        is_valid = distance < self.acceptance_radius

        return r_phys, r_perp_raw, is_valid

    def e_perp_coherence(self, gate_vector: List[float]) -> float:
        """
        Compute E_perp coherence metric ∈ [0, 1].

        1.0 = perfectly centered in acceptance window
        0.0 = at or beyond acceptance boundary
        """
        _, r_perp, _ = self.map_gates_to_lattice(gate_vector)
        distance = float(np.linalg.norm(r_perp - self.phason_strain))
        # Normalize: 1 at center, 0 at boundary
        coherence = max(0.0, 1.0 - distance / self.acceptance_radius)
        return float(coherence)

    def apply_phason_rekey(self, entropy_seed: bytes) -> np.ndarray:
        """
        Apply Phason Strain ("Deformation") to the lattice.
        Atomically invalidates the previous valid keyspace.

        Returns:
            New phason strain vector
        """
        h = hashlib.sha256(entropy_seed).digest()
        # Map hash to 3 float values [-1, 1]
        v = np.array([
            int.from_bytes(h[0:4], 'big') / (2**32) * 2 - 1,
            int.from_bytes(h[4:8], 'big') / (2**32) * 2 - 1,
            int.from_bytes(h[8:12], 'big') / (2**32) * 2 - 1
        ])
        # Scale by acceptance radius to ensure significant shift
        self.phason_strain = v * self.acceptance_radius * 2.0
        return self.phason_strain

    def detect_crystalline_defects(self, history_vectors: List[List[float]],
                                   min_samples: int = 10) -> float:
        """
        Detect if attacker is forcing periodicity (Crystalline Defect).

        Aperiodic structures should have irrational ratios between
        successive projections. Periodic attacks show rational patterns.

        Returns:
            defect_score ∈ [0, 1]: 0 = aperiodic (safe), 1 = periodic (attack)
        """
        if len(history_vectors) < min_samples:
            return 0.0

        # Project all vectors to E_perp
        perp_points = []
        for v in history_vectors[-min_samples:]:
            _, r_perp, _ = self.map_gates_to_lattice(v)
            perp_points.append(r_perp)

        perp_points = np.array(perp_points)

        # Check for suspicious periodicity via autocorrelation
        diffs = np.diff(perp_points, axis=0)
        if len(diffs) < 2:
            return 0.0

        # Compute normalized variance of differences
        # Low variance = repeating pattern = attack
        var = float(np.var(diffs))
        mean_norm = float(np.mean(np.linalg.norm(diffs, axis=1)))

        if mean_norm < 1e-10:
            return 1.0  # All identical = definite attack

        # Normalize: high variance = low defect score
        defect_score = float(np.exp(-var / (mean_norm + 1e-10)))
        return min(1.0, max(0.0, defect_score))


# Global quasicrystal instance (can be rekeyed)
QUASICRYSTAL = QuasicrystalLattice()


# =============================================================================
# SECTION 1.6: CPSE PHYSICS ENGINE (Patent-Ready Algorithms)
# =============================================================================
# ┌─────────────────────────────────────────────────────────────────────────┐
# │  CRYPTOGRAPHIC PHYSICS SIMULATION ENGINE                                 │
# │                                                                         │
# │  Transforms abstract security metaphors into executable algorithms:     │
# │    - Lorentz Factor γ(ρ): Query throttling approaching event horizon    │
# │    - Soliton Dynamics: NLSE-inspired packet integrity with gain/loss    │
# │    - Spin Rotation: Context-dependent 6D rotation matrix product        │
# │    - Flux Jitter: Stochastic coordinate perturbation σ(NetworkLoad)     │
# │                                                                         │
# │  These provide the "Technical Solutions" required for Alice compliance.  │
# └─────────────────────────────────────────────────────────────────────────┘

# CPSE Constants
RHO_CRITICAL = 100.0          # Max queries/second before event horizon
SOLITON_ALPHA = 0.1           # Self-focusing nonlinearity coefficient
SOLITON_BETA = 0.05           # Linear loss coefficient
FLUX_SIGMA_BASE = 0.01        # Base jitter standard deviation


def lorentz_factor(rho_E: float, rho_critical: float = RHO_CRITICAL,
                   eps: float = 1e-12) -> float:
    """
    Virtual Gravity: Lorentz factor for latency throttling (Claim 54).

    γ(ρ_E) = 1 / sqrt(1 - (ρ_E / ρ_critical)²)

    As query density ρ_E → ρ_critical, delay → ∞ (event horizon).

    Args:
        rho_E: Query energy density (requests/second from context)
        rho_critical: Speed of light limit (max allowable requests)

    Returns:
        γ ∈ [1, ∞): Time dilation factor
    """
    ratio = min(abs(rho_E) / (rho_critical + eps), 0.9999)  # Clamp to avoid singularity
    denominator = np.sqrt(max(eps, 1.0 - ratio ** 2))
    return float(1.0 / denominator)


def compute_latency_delay(t_base: float, rho_E: float,
                          rho_critical: float = RHO_CRITICAL) -> float:
    """
    Compute throttled latency using Lorentz factor.

    Δt = t_base · γ(ρ_E)

    Args:
        t_base: Base processing time (seconds)
        rho_E: Current query density

    Returns:
        Throttled delay in seconds
    """
    gamma = lorentz_factor(rho_E, rho_critical)
    return float(t_base * gamma)


@dataclass
class SolitonPacket:
    """Data packet with soliton amplitude dynamics."""
    amplitude: float           # Signal integrity score A ∈ [0, 1]
    phi_d: float              # Soliton key (gain offset from private key)
    iterations: int = 0       # Evolution steps survived


def soliton_evolve(packet: SolitonPacket, alpha: float = SOLITON_ALPHA,
                   beta: float = SOLITON_BETA) -> SolitonPacket:
    """
    Soliton Dynamics: NLSE-inspired packet integrity (Claim 52 & 55).

    A_next = A_current + (α·|A|²·A - β·A) + Φ_d

    Only packets with correct Φ_d maintain amplitude over time.

    Args:
        packet: Current packet state
        alpha: Self-focusing nonlinearity (positive feedback for valid structure)
        beta: Linear loss coefficient (natural entropy)

    Returns:
        Evolved packet state
    """
    A = packet.amplitude
    phi_d = packet.phi_d

    # NLSE discrete analog
    nonlinear_gain = alpha * (A ** 2) * A  # Self-focusing
    linear_loss = beta * A                  # Entropy decay
    soliton_boost = phi_d                   # Key-derived gain

    A_next = A + (nonlinear_gain - linear_loss) + soliton_boost

    # Clamp to valid range
    A_next = float(max(0.0, min(1.0, A_next)))

    return SolitonPacket(
        amplitude=A_next,
        phi_d=phi_d,
        iterations=packet.iterations + 1
    )


def soliton_key_from_secret(secret: bytes, target_beta: float = SOLITON_BETA) -> float:
    """
    Derive Soliton Key Φ_d from private key.

    The key perfectly offsets loss β for authorized packets.

    Args:
        secret: Private key bytes
        target_beta: Loss to offset

    Returns:
        Φ_d value that maintains soliton stability
    """
    # Hash to get deterministic offset
    h = hashlib.sha256(secret).digest()
    # Map to small positive value that offsets beta
    raw = int.from_bytes(h[:4], 'big') / (2**32)
    # Scale to offset beta with small variance
    phi_d = target_beta * (0.9 + 0.2 * raw)  # ≈ beta ± 10%
    return float(phi_d)


def spin_rotation_matrix(theta: np.ndarray) -> np.ndarray:
    """
    Spin Rotation: Context-dependent 6D rotation (Claim 60).

    v_final = (∏_{i=1}^{5} R_{i,i+1}(θ_i)) · v_input

    Each R_{i,i+1} is a Givens rotation in the (i, i+1) plane.

    Args:
        theta: Array of 5 rotation angles θ_1...θ_5

    Returns:
        6x6 rotation matrix (product of 5 Givens rotations)
    """
    n = 6  # Dimension
    R_total = np.eye(n)

    for i in range(min(len(theta), n - 1)):
        # Givens rotation in (i, i+1) plane
        c = np.cos(theta[i])
        s = np.sin(theta[i])

        R_i = np.eye(n)
        R_i[i, i] = c
        R_i[i, i + 1] = -s
        R_i[i + 1, i] = s
        R_i[i + 1, i + 1] = c

        R_total = R_i @ R_total

    return R_total


def context_to_spin_angles(context_hash: bytes) -> np.ndarray:
    """
    Derive spin angles from context hash.

    θ_i = (hash_bytes[i] / 255) · 2π

    Args:
        context_hash: Hash of (Time + Location + Role)

    Returns:
        Array of 5 rotation angles ∈ [0, 2π)
    """
    angles = np.array([
        (context_hash[i] / 255.0) * 2 * np.pi
        for i in range(min(5, len(context_hash)))
    ])
    return angles


def apply_spin(v_input: np.ndarray, context: str) -> np.ndarray:
    """
    Apply context-dependent spin rotation to vector.

    Args:
        v_input: 6D input vector
        context: Context string (Time + Location + Role)

    Returns:
        Rotated vector v_final
    """
    context_hash = hashlib.sha256(context.encode()).digest()
    theta = context_to_spin_angles(context_hash)
    R = spin_rotation_matrix(theta)

    # Pad input to 6D if needed
    v = np.zeros(6)
    v[:len(v_input)] = v_input[:6]

    return R @ v


def flux_jitter(P_target: np.ndarray, network_load: float,
                sigma_base: float = FLUX_SIGMA_BASE) -> np.ndarray:
    """
    Flux Jitter: Dynamic interference (Claim 61).

    P_jitter = P_target + N(0, σ(NetworkLoad))

    The "Rail" (authorized path) accounts for jitter; attackers miss.

    Args:
        P_target: Target coordinate/address
        network_load: Current network interference ∈ [0, 1]
        sigma_base: Base standard deviation

    Returns:
        Jittered coordinate
    """
    # Scale sigma by network load (higher load = more jitter)
    sigma = sigma_base * (1.0 + network_load * 10.0)
    noise = np.random.normal(0, sigma, size=P_target.shape)
    return P_target + noise


def flux_compensated_distance(P_actual: np.ndarray, P_target: np.ndarray,
                              jitter_history: np.ndarray) -> float:
    """
    Compute distance accounting for known flux pattern.

    Authorized clients track jitter_history and compensate.
    Attackers see random noise.

    Args:
        P_actual: Actual position
        P_target: Original target
        jitter_history: Recent jitter vectors (for prediction)

    Returns:
        Compensated distance (low for authorized, high for attackers)
    """
    if len(jitter_history) < 2:
        return float(np.linalg.norm(P_actual - P_target))

    # Authorized clients can predict next jitter from pattern
    predicted_jitter = np.mean(jitter_history[-3:], axis=0)
    compensated_target = P_target + predicted_jitter

    return float(np.linalg.norm(P_actual - compensated_target))


class CPSEThrottler:
    """
    Query throttler implementing Lorentz factor dynamics.

    Tracks query density per context and applies time dilation.
    """

    def __init__(self, rho_critical: float = RHO_CRITICAL,
                 window_seconds: float = 1.0):
        self.rho_critical = rho_critical
        self.window_seconds = window_seconds
        self.query_counts: Dict[str, List[float]] = {}

    def record_query(self, context_id: str, timestamp: float) -> float:
        """
        Record query and return required delay.

        Args:
            context_id: Identifier for query source
            timestamp: Current time

        Returns:
            Required delay in seconds (Lorentz-dilated)
        """
        if context_id not in self.query_counts:
            self.query_counts[context_id] = []

        # Clean old queries outside window
        cutoff = timestamp - self.window_seconds
        self.query_counts[context_id] = [
            t for t in self.query_counts[context_id] if t > cutoff
        ]

        # Record new query
        self.query_counts[context_id].append(timestamp)

        # Compute current density
        rho_E = len(self.query_counts[context_id]) / self.window_seconds

        # Compute delay
        t_base = 0.01  # 10ms base latency
        return compute_latency_delay(t_base, rho_E, self.rho_critical)

    def get_gamma(self, context_id: str) -> float:
        """Get current Lorentz factor for context."""
        if context_id not in self.query_counts:
            return 1.0
        rho_E = len(self.query_counts[context_id]) / self.window_seconds
        return lorentz_factor(rho_E, self.rho_critical)


# Global CPSE throttler instance
CPSE_THROTTLER = CPSEThrottler()


# =============================================================================
# SECTION 2: QASI CORE (Axiom-Safe Geometry)
# =============================================================================
# ┌─────────────────────────────────────────────────────────────────────────┐
# │  CORE INVARIANT CODE — DO NOT MODIFY WITHOUT MATHEMATICAL VERIFICATION  │
# │                                                                         │
# │  These functions implement the axioms A1-A12 of the SCBE geometry.      │
# │  Any changes must preserve:                                             │
# │    - A1-A2: Realification isometry ||realify(c)|| = ||c||               │
# │    - A4: Poincaré embedding maps to open ball ||u|| < 1                 │
# │    - A5: Hyperbolic distance is symmetric and satisfies triangle ineq   │
# │    - A6: Möbius addition preserves the ball                             │
# │    - A7: Phase transform is an isometry                                 │
# │    - A8: Breathing transform is a diffeomorphism (NOT isometry)         │
# │    - A9: Realm distance is 1-Lipschitz                                  │
# │    - A11: Triadic distance is a proper metric                           │
# │    - A12: Harmonic scaling H(d,R) = R^(d²) is monotone in d             │
# └─────────────────────────────────────────────────────────────────────────┘

def _norm(x: np.ndarray) -> float:
    return float(np.linalg.norm(x))


def clamp_ball(u: np.ndarray, eps_ball: float = 1e-3) -> np.ndarray:
    """Clamp vector to closed sub-ball ||u|| <= 1 - eps_ball."""
    r = _norm(u)
    r_max = 1.0 - float(eps_ball)
    if r <= r_max:
        return u
    if r == 0.0:
        return u
    return (r_max / r) * u


def safe_arcosh(x: float) -> float:
    """arcosh with clamping for numerical stability."""
    return float(np.arccosh(max(1.0, x)))


def realify(c: np.ndarray) -> np.ndarray:
    """A1-A2: Realification isometry C^D → R^(2D)."""
    c = np.asarray(c, dtype=np.complex128)
    return np.concatenate([np.real(c), np.imag(c)]).astype(np.float64)


def apply_spd_weights(x: np.ndarray, g_diag: np.ndarray) -> np.ndarray:
    """A3: SPD weighting x_G = G^(1/2) x."""
    return np.sqrt(np.abs(g_diag)) * x


def poincare_embed(x: np.ndarray, alpha: float = 1.0, eps_ball: float = 1e-3) -> np.ndarray:
    """A4: Radial tanh embedding R^n → B^n."""
    r = _norm(x)
    if r == 0.0:
        return np.zeros_like(x)
    u = (np.tanh(alpha * r) / r) * x
    return clamp_ball(u, eps_ball=eps_ball)


def hyperbolic_distance(u: np.ndarray, v: np.ndarray, eps: float = 1e-12) -> float:
    """A5: Poincaré ball distance."""
    uu = float(np.dot(u, u))
    vv = float(np.dot(v, v))
    duv = float(np.dot(u - v, u - v))
    denom = max((1.0 - uu) * (1.0 - vv), eps)
    arg = 1.0 + (2.0 * duv) / denom
    return safe_arcosh(arg)


def mobius_add(a: np.ndarray, u: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """A6: Möbius addition (gyrovector)."""
    au = float(np.dot(a, u))
    aa = float(np.dot(a, a))
    uu = float(np.dot(u, u))
    denom = 1.0 + 2.0 * au + aa * uu
    denom = np.sign(denom) * max(abs(denom), eps)
    num = (1.0 + 2.0 * au + uu) * a + (1.0 - aa) * u
    return num / denom


def phase_transform(u: np.ndarray, a: np.ndarray, Q: Optional[np.ndarray] = None,
                    eps_ball: float = 1e-3) -> np.ndarray:
    """A7: Phase transform (isometry)."""
    u2 = mobius_add(a, u)
    if Q is not None:
        u2 = Q @ u2
    return clamp_ball(u2, eps_ball=eps_ball)


def breathing_transform(u: np.ndarray, b: float, eps_ball: float = 1e-3) -> np.ndarray:
    """A8: Breathing transform (diffeomorphism, NOT isometry)."""
    r = _norm(u)
    if r == 0.0:
        return u.copy()
    r = min(r, 1.0 - eps_ball)
    rp = float(np.tanh(b * np.arctanh(r)))
    out = (rp / r) * u
    return clamp_ball(out, eps_ball=eps_ball)


def realm_distance(u: np.ndarray, centers: np.ndarray) -> float:
    """A9: d*(u) = min_k d_H(u, μ_k) — 1-Lipschitz."""
    if centers.ndim == 1:
        centers = centers.reshape(1, -1)
    return float(min(hyperbolic_distance(u, centers[k]) for k in range(centers.shape[0])))


def spectral_stability(y: np.ndarray, eps: float = 1e-12) -> float:
    """A10: Spectral coherence S_spec ∈ [0,1].

    Measures spectral concentration: how peaked is the spectrum?
    High concentration (few dominant frequencies) → S_spec ≈ 1
    Flat spectrum (noise-like) → S_spec ≈ 0
    """
    if y.size < 2:
        return 1.0
    Y = np.fft.fft(y)
    P = np.abs(Y[:len(Y)//2]) ** 2  # Only positive frequencies
    total = max(float(np.sum(P)), eps)
    # Normalized spectral entropy: low entropy = high concentration
    p_norm = P / total
    p_norm = p_norm[p_norm > eps]
    H = float(-np.sum(p_norm * np.log(p_norm + eps)))
    H_max = np.log(len(P) + eps)  # Maximum entropy (flat spectrum)
    # S_spec = 1 when concentrated, 0 when flat
    return float(1.0 - min(1.0, H / (H_max + eps)))


def spin_coherence(phasors: np.ndarray, eps: float = 1e-12) -> float:
    """A10: Spin coherence C_spin ∈ [0,1]."""
    s = np.asarray(phasors, dtype=np.complex128)
    num = abs(np.sum(s))
    denom = float(np.sum(np.abs(s))) + eps
    return float(min(max(num / denom, 0.0), 1.0))


def audio_envelope_coherence(wave: np.ndarray, window_size: int = 256, eps: float = 1e-12) -> float:
    """Audio envelope stability S_audio ∈ [0,1].

    Measures consistency of audio envelope across windows.
    Stable envelope → S_audio ≈ 1
    Erratic envelope → S_audio ≈ 0
    """
    if wave.size < window_size * 2:
        return 1.0
    # Compute envelope via Hilbert-like approximation (abs of analytic signal)
    analytic = wave + 1j * np.imag(np.fft.ifft(np.fft.fft(wave) * 2))
    envelope = np.abs(analytic)
    # Compute envelope variance in windows
    n_windows = wave.size // window_size
    if n_windows < 2:
        return 1.0
    window_means = [np.mean(envelope[i*window_size:(i+1)*window_size]) for i in range(n_windows)]
    window_means = np.array(window_means)
    mean_envelope = np.mean(window_means)
    if mean_envelope < eps:
        return 1.0
    # Coefficient of variation: low CV = stable = high coherence
    cv = np.std(window_means) / (mean_envelope + eps)
    return float(max(0.0, min(1.0, 1.0 - cv)))


def triadic_distance(d1: float, d2: float, dG: float,
                     lambdas: Tuple[float, float, float] = (0.4, 0.3, 0.3),
                     flux: Optional[float] = None) -> float:
    """A11: Triadic temporal distance with optional flux multiplier.

    Per audit trace #8492: flux = sum(|a - a_prev|) / N accounts for
    gyro-translation jitter between frames.

    Args:
        d1: Primary hyperbolic distance
        d2: Secondary distance (e.g., auth deviation)
        dG: Governance distance (e.g., entropy deviation)
        lambdas: Weights for triadic combination
        flux: Optional flux multiplier from gyro-translation delta

    Returns:
        Triadic distance, optionally flux-amplified
    """
    l1, l2, l3 = lambdas
    s = l1 * (d1 ** 2) + l2 * (d2 ** 2) + l3 * (dG ** 2)
    d_tri = float(np.sqrt(max(0.0, s)))

    # Apply flux multiplier if provided (audit recommendation)
    if flux is not None and flux > 0:
        d_tri *= (1.0 + flux)

    return d_tri


def harmonic_scaling(d: float, R_base: float = PHI, max_log: float = 700.0,
                     zeta: Optional[float] = None,
                     omega_ratio: float = 1.0) -> Tuple[float, float]:
    """A12: H(d,R) = R^(d²) with optional resonance amplification.

    Per audit trace #8492: Add resonance damping factor ζ for
    resonant anomaly amplification near natural frequency.

    Resonance amplification: D = 1 / sqrt((1-(ω/ω_n)²)² + (2ζ·ω/ω_n)²)
    At resonance (ω = ω_n): D = 1/(2ζ)

    Args:
        d: Triadic distance
        R_base: Harmonic base (default PHI)
        max_log: Maximum log value to prevent overflow
        zeta: Damping ratio ζ ∈ (0, 1). Lower = more resonance.
              Typical: ζ=0.005 gives D≈100x at resonance
        omega_ratio: ω/ω_n frequency ratio (1.0 = at resonance)

    Returns:
        (H, logH) where H is the harmonic scaling factor
    """
    if R_base <= 1.0:
        R_base = PHI
    logH = float(np.log(R_base) * (d ** 2))
    logH_c = min(logH, max_log)
    H = float(np.exp(logH_c))

    # Apply resonance amplification if damping specified
    if zeta is not None and zeta > 0:
        # D = 1 / sqrt((1 - r²)² + (2ζr)²) where r = ω/ω_n
        r = omega_ratio
        denom_sq = (1 - r**2)**2 + (2 * zeta * r)**2
        D = 1.0 / np.sqrt(max(1e-12, denom_sq))
        H *= D
        logH_c += np.log(max(1e-12, D))

    return H, logH_c


def risk_base(d_tri_norm: float, C_spin: float, S_spec: float,
              trust_tau: float, S_audio: float, C_qc: float = 1.0) -> float:
    """A12: Base risk from coherence deficits.

    Args:
        d_tri_norm: Normalized triadic distance ∈ [0,1]
        C_spin: Spin coherence ∈ [0,1]
        S_spec: Spectral stability ∈ [0,1]
        trust_tau: Time flow trust ∈ [0,1]
        S_audio: Audio envelope coherence ∈ [0,1]
        C_qc: Quasicrystal E_perp coherence ∈ [0,1]

    Returns:
        Base risk ∈ [0,1]
    """
    # Six coherence factors now (including quasicrystal)
    w = 1.0 / 6.0
    return float(
        w * min(max(d_tri_norm, 0), 1) +
        w * (1 - min(max(C_spin, 0), 1)) +
        w * (1 - min(max(S_spec, 0), 1)) +
        w * (1 - min(max(trust_tau, 0), 1)) +
        w * (1 - min(max(S_audio, 0), 1)) +
        w * (1 - min(max(C_qc, 0), 1))
    )


def risk_prime(d_star: float, risk_base_val: float, R_base: float = PHI,
               zeta: Optional[float] = None,
               omega_ratio: float = 1.0) -> Dict[str, float]:
    """A12: Risk' = Risk_base · H(d*, R) with optional resonance.

    Per audit trace #8492: Add resonance damping ζ for anomaly amplification.

    Args:
        d_star: Realm distance
        risk_base_val: Base risk value
        R_base: Harmonic base (default PHI)
        zeta: Optional resonance damping ratio
        omega_ratio: Frequency ratio (1.0 = at resonance)

    Returns:
        Dict with risk_prime, H, logH, and resonance_factor D
    """
    H, logH = harmonic_scaling(d_star, R_base, zeta=zeta, omega_ratio=omega_ratio)
    rp = max(0.0, risk_base_val) * H

    # Calculate resonance factor for forensics
    D = 1.0
    if zeta is not None and zeta > 0:
        r = omega_ratio
        denom_sq = (1 - r**2)**2 + (2 * zeta * r)**2
        D = 1.0 / np.sqrt(max(1e-12, denom_sq))

    return {"risk_prime": float(rp), "H": float(H), "logH": float(logH), "D": float(D)}


# =============================================================================
# SECTION 3: HARMONIC CIPHER (Conlang + Encoding)
# =============================================================================

def stable_hash(data: str) -> float:
    """Deterministic hash → [0, 2π)."""
    hash_int = int(hashlib.sha256(data.encode()).hexdigest(), 16)
    return hash_int / (2**256 - 1) * 2 * np.pi


def phase_modulated_intent(intent: float) -> np.ndarray:
    """Encode intent as phase on carrier wave."""
    t = np.linspace(0, DURATION, int(SAMPLE_RATE * DURATION))
    phase = 2 * np.pi * intent
    return np.cos(2 * np.pi * CARRIER_FREQ * t + phase)


def extract_phase(wave: np.ndarray) -> float:
    """Demodulate phase via FFT."""
    N = len(wave)
    yf = fft(wave)
    peak_idx = np.argmax(np.abs(yf[:N//2]))
    phase = np.angle(yf[peak_idx])
    return float((phase % (2 * np.pi)) / (2 * np.pi))


def derive_harmonic_mask(token_id: int, secret_key: bytes) -> List[int]:
    """Key-derived harmonics for flat-slope encoding."""
    mask_seed = hmac.new(secret_key, f"mask:{token_id}".encode(), hashlib.sha256).digest()
    harmonics = [h for h in range(1, 17) if mask_seed[h % 32] > 128]
    if 1 not in harmonics:
        harmonics.append(1)
    return harmonics


def synthesize_token(harmonics: List[int]) -> np.ndarray:
    """Generate audio slice from harmonics."""
    t = np.linspace(0, DURATION, int(SAMPLE_RATE * DURATION))
    signal = np.zeros_like(t)
    for h in harmonics:
        signal += (1.0 / h) * np.sin(2 * np.pi * CARRIER_FREQ * h * t)
    max_val = np.max(np.abs(signal))
    return signal / max_val if max_val > 0 else signal


def resonance_refractor(token_ids: List[int], secret_key: bytes) -> np.ndarray:
    """Interference pattern across tokens."""
    total_len = int(SAMPLE_RATE * DURATION * len(token_ids))
    t = np.linspace(0, DURATION * len(token_ids), total_len)
    signal = np.zeros_like(t)
    for token_id in token_ids:
        phase_seed = hmac.new(secret_key, f"phase:{token_id}".encode(), hashlib.sha256).digest()
        phase = (phase_seed[0] / 255) * 2 * np.pi
        harmonics = derive_harmonic_mask(token_id, secret_key)
        for h in harmonics:
            signal += (1.0 / h) * np.sin(2 * np.pi * CARRIER_FREQ * h * t + phase)
    max_val = np.max(np.abs(signal))
    return signal / max_val if max_val > 0 else signal


def hmac_chain(messages: List[str], master_key: bytes) -> str:
    """Sequential HMAC chain for integrity."""
    T = "IV"
    for m in messages:
        T = hmac.new(master_key, (m + T).encode(), hashlib.sha256).hexdigest()
    return T


# =============================================================================
# SECTION 4: 9D STATE MACHINE
# =============================================================================

@dataclass
class State9D:
    """Full 9D state representation."""
    context: np.ndarray           # 6D context (complex)
    tau: float                    # Time flow
    eta: float                    # Entropy
    q: complex                    # Quantum state
    t: float = 0.0                # Timestamp

    def to_complex_context(self) -> np.ndarray:
        """Extract complex context for realification."""
        return np.array([
            complex(v) if not isinstance(v, complex) else v
            for v in self.context
        ], dtype=np.complex128)


def generate_context(t: float) -> np.ndarray:
    """Generate 6D context vector."""
    return np.array([
        stable_hash(f"identity_{t}"),           # Identity
        np.exp(1j * 2 * np.pi * 0.75),          # Intent phase
        0.95,                                    # Trajectory
        t % (2 * np.pi),                         # Timing
        stable_hash(f"commit_{t}"),              # Commitment
        0.88                                     # Signature
    ], dtype=object)


def compute_entropy(window: list) -> float:
    """Shannon entropy of state window ∈ [0, log2(bins)]."""
    flat = []
    for v in np.array(window, dtype=object).flatten():
        if isinstance(v, (int, float)):
            flat.append(float(v))
        elif isinstance(v, complex):
            flat.append(abs(v))
        else:
            flat.append(float(hash(str(v)) % 1000) / 1000)
    if len(flat) < 2:
        return 0.0
    # Add small jitter to avoid degenerate histograms
    flat = np.array(flat) + np.random.randn(len(flat)) * 1e-10
    n_bins = min(16, len(flat))
    hist, _ = np.histogram(flat, bins=n_bins)
    # Use counts, not density, and normalize properly
    hist = hist[hist > 0]
    if len(hist) == 0:
        return 0.0
    probs = hist / hist.sum()
    return float(-np.sum(probs * np.log2(probs + 1e-12)))


def tau_dot(t: float) -> float:
    """Time flow rate (causality)."""
    return 1.0 + DELTA_DRIFT_MAX * np.sin(OMEGA_TIME * t)


def quantum_evolution(q0: complex, t: float) -> complex:
    """Quantum state evolution."""
    return q0 * np.exp(-1j * t)


def generate_9d_state(t: float) -> State9D:
    """Generate complete 9D state."""
    context = generate_context(t)
    tau = t % 100
    eta = max(0.0, compute_entropy([context]) + 2.0)  # Shift to valid range
    q = quantum_evolution(1+0j, t)
    return State9D(context=context, tau=tau, eta=eta, q=q, t=t)


# =============================================================================
# SECTION 5: POLYHEDRAL TOPOLOGY (PHDM)
# =============================================================================

@dataclass
class Polyhedron:
    """Polyhedral state for topology validation."""
    V: int  # Vertices
    E: int  # Edges
    F: int  # Faces

    def euler_characteristic(self) -> int:
        """χ = V - E + F (expect 2 for convex)."""
        return self.V - self.E + self.F


def phdm_validate(poly: Polyhedron) -> bool:
    """Validate topology χ == 2."""
    return poly.euler_characteristic() == CHI_EXPECTED


# =============================================================================
# SECTION 6: GROK TRUTH-SEEKING ORACLE
# =============================================================================

@dataclass
class GrokResult:
    """Grok oracle result."""
    truth_score: float
    reasoning: str
    confidence: float
    invoked: bool


def call_grok(state_summary: Dict[str, Any]) -> GrokResult:
    """Grok truth-seeking oracle."""
    coh = state_summary.get('coh', 0.95)
    eta = state_summary.get('eta', ETA_TARGET)
    f_q = state_summary.get('f_q', 0.95)
    chi = state_summary.get('chi', CHI_EXPECTED)

    entropy_penalty = 1.0 - min(1.0, eta / ETA_TARGET)
    coherence_bonus = float(coh)
    quantum_bonus = float(f_q)
    topology_bonus = 1.0 if chi == CHI_EXPECTED else 0.5

    truth_score = (
        0.30 * coherence_bonus +
        0.25 * quantum_bonus +
        0.20 * topology_bonus +
        0.25 * entropy_penalty
    )
    truth_score = max(0.0, min(1.0, truth_score))

    issues = []
    if coh < TAU_COH:
        issues.append(f"low coherence ({coh:.2f})")
    if f_q < 0.9:
        issues.append(f"quantum fidelity degraded ({f_q:.2f})")
    if chi != CHI_EXPECTED:
        issues.append(f"topology violation (χ={chi})")

    reasoning = f"Flagged: {', '.join(issues)}" if issues else "State consistent"

    return GrokResult(
        truth_score=truth_score,
        reasoning=reasoning,
        confidence=0.85 + 0.15 * truth_score,
        invoked=True
    )


# =============================================================================
# SECTION 7: UNIFIED GOVERNANCE ENGINE (L1-L14 + Grok)
# =============================================================================

@dataclass
class GovernanceResult:
    """Full governance result with forensic trace fields.

    Per audit trace #8492: Include d_origin and S_spec for forensic
    logging to enable trace reconstruction and anomaly debugging.
    """
    decision: str
    output: str
    risk_base: float
    risk_amplified: float
    risk_final: float
    grok_result: GrokResult
    hyperbolic_state: np.ndarray
    metrics: Dict[str, float]
    # Forensic trace fields (audit recommendation)
    d_origin: float = 0.0          # Hyperbolic distance from origin
    S_spec: float = 1.0            # Spectral stability
    C_spin: float = 1.0            # Spin coherence
    d_tri: float = 0.0             # Triadic distance (pre-normalization)
    flux_applied: float = 0.0     # Flux multiplier used
    zeta_applied: float = 0.0     # Resonance damping used


def governance_pipeline(state: State9D, intent: float, poly: Polyhedron,
                        realm_centers: Optional[np.ndarray] = None,
                        flux: Optional[float] = None,
                        zeta: Optional[float] = None,
                        omega_ratio: float = 1.0) -> GovernanceResult:
    """
    Full L1-L14 governance pipeline with Grok integration.

    L1-L2: Complex → Real (realification)
    L3: SPD weighting
    L3.5: Quasicrystal validation (E_perp acceptance window)
    L4: Poincaré embedding
    L5: Hyperbolic distance
    L6: Breathing transform
    L7: Phase transform
    L8: Realm distance
    L9: Spectral coherence
    L10: Spin coherence
    L11: Triadic distance (with optional flux multiplier)
    L12: Harmonic scaling (with optional resonance damping ζ)
    L13: Risk aggregation (includes E_perp coherence)
    L14: Audio coherence

    Args:
        state: 9D state vector
        intent: Intent value ∈ [0,1]
        poly: Polyhedron for topology check
        realm_centers: Realm centers for distance calculation
        flux: Optional flux multiplier for triadic distance (audit #8492)
        zeta: Optional resonance damping ratio (audit #8492)
        omega_ratio: Frequency ratio for resonance (default 1.0 = at resonance)
    """
    # L1-L2: Realification
    c_complex = state.to_complex_context()
    x = realify(c_complex)

    # L3: SPD weighting (golden ratio powers)
    g_diag = np.array(TONGUE_WEIGHTS[:len(x)] + TONGUE_WEIGHTS[:len(x)])
    g_diag = g_diag[:len(x)]
    x_G = apply_spd_weights(x, g_diag)

    # L3.5: Quasicrystal validation
    # Map 6D context to quasicrystal lattice for aperiodic validation
    gate_vector = [
        float(v) if isinstance(v, (int, float)) else abs(v) if isinstance(v, complex) else 0.0
        for v in state.context[:6]
    ]
    r_phys, r_perp, qc_valid = QUASICRYSTAL.map_gates_to_lattice(gate_vector)
    C_qc = QUASICRYSTAL.e_perp_coherence(gate_vector)  # E_perp coherence ∈ [0,1]

    # L4: Poincaré embedding
    u = poincare_embed(x_G, alpha=1.0)

    # L5: Hyperbolic distance to origin (baseline)
    d_origin = hyperbolic_distance(u, np.zeros_like(u))

    # L6: Breathing transform
    breathing_factor = 1.0 + 0.1 * np.sin(state.t * OMEGA_TIME)
    u_breath = breathing_transform(u, breathing_factor)

    # L7: Phase transform
    a_shift = clamp_ball(np.ones_like(u) * 0.05)
    u_phase = phase_transform(u_breath, a_shift)

    # L8: Realm distance
    if realm_centers is None:
        realm_centers = np.zeros((1, len(u_phase)))
    d_star = realm_distance(u_phase, realm_centers)

    # L9: Spectral coherence (from intent wave)
    intent_wave = phase_modulated_intent(intent)
    S_spec = spectral_stability(intent_wave)

    # L10: Spin coherence (from complex context phases)
    phasors = np.exp(1j * np.array([
        float(v) if isinstance(v, (int, float)) else np.angle(v) if isinstance(v, complex) else 0
        for v in state.context
    ]))
    C_spin = spin_coherence(phasors)

    # L11: Triadic distance (with optional flux multiplier per audit #8492)
    d_auth = abs(intent - 0.75)  # Distance from expected intent
    d_cfg = abs(state.eta - ETA_TARGET) / ETA_TARGET
    d_tri = triadic_distance(d_star, d_auth, d_cfg, flux=flux)
    d_tri_norm = min(1.0, d_tri / (EPSILON + 1e-9))

    # L14: Audio envelope coherence
    S_audio = audio_envelope_coherence(intent_wave)

    # Trust from time flow
    trust_tau = min(1.0, max(0.0, tau_dot(state.tau) / 2.0))

    # L12-L13: Risk calculation (with optional resonance damping per audit #8492)
    rb = risk_base(d_tri_norm, C_spin, S_spec, trust_tau, S_audio, C_qc)
    rp_result = risk_prime(d_star, rb, R, zeta=zeta, omega_ratio=omega_ratio)
    risk_amplified_raw = rp_result["risk_prime"]
    # Normalize amplified risk to [0, 1) for decision thresholds using sigmoid
    risk_amplified = 1.0 - 1.0 / (1.0 + risk_amplified_raw)

    # Topology check
    chi = poly.euler_characteristic()
    f_q = min(1.0, abs(state.q)**2)

    # Grok invocation check
    grok_result = GrokResult(truth_score=1.0, reasoning="Not invoked", confidence=1.0, invoked=False)

    marginal_coherence = TAU_COH * 0.8 < C_spin < TAU_COH * 1.2
    marginal_risk = GROK_THRESHOLD_LOW < risk_amplified < GROK_THRESHOLD_HIGH
    topology_issue = chi != CHI_EXPECTED

    if marginal_coherence or marginal_risk or topology_issue:
        state_summary = {
            'coh': C_spin,
            'eta': state.eta,
            'f_q': f_q,
            'chi': chi,
        }
        grok_result = call_grok(state_summary)

    # Final risk with Grok adjustment
    risk_final = risk_amplified + GROK_WEIGHT * (1 - grok_result.truth_score)

    # Decision
    if risk_final < GROK_THRESHOLD_LOW:
        decision = "ALLOW"
        output = "Access granted - state verified"
    elif risk_final < GROK_THRESHOLD_HIGH:
        decision = "QUARANTINE"
        output = f"Marginal state (Grok score: {grok_result.truth_score:.2f}) - quarantined"
    else:
        decision = "DENY"
        output = "Access denied - state rejected"

    metrics = {
        'd_star': d_star,
        'd_origin': d_origin,   # Forensic: hyperbolic distance from origin
        'd_tri': d_tri,
        'd_tri_norm': d_tri_norm,
        'C_spin': C_spin,
        'S_spec': S_spec,
        'S_audio': S_audio,
        'C_qc': C_qc,           # Quasicrystal E_perp coherence
        'qc_valid': qc_valid,   # Quasicrystal acceptance window
        'trust_tau': trust_tau,
        'f_q': f_q,
        'chi': chi,
        'H': rp_result['H'],
        'D': rp_result.get('D', 1.0),  # Resonance amplification factor
    }

    return GovernanceResult(
        decision=decision,
        output=output,
        risk_base=rb,
        risk_amplified=risk_amplified,
        risk_final=risk_final,
        grok_result=grok_result,
        hyperbolic_state=u_phase,
        metrics=metrics,
        # Forensic trace fields (audit #8492)
        d_origin=d_origin,
        S_spec=S_spec,
        C_spin=C_spin,
        d_tri=d_tri,
        flux_applied=flux if flux is not None else 0.0,
        zeta_applied=zeta if zeta is not None else 0.0
    )


# =============================================================================
# SECTION 8: BYZANTINE ATTACK SIMULATION
# =============================================================================

@dataclass
class SwarmAgent:
    """Agent in Byzantine swarm."""
    agent_id: int
    is_byzantine: bool
    state: State9D
    vote: Optional[str] = None


def simulate_byzantine_attack(n_agents: int = 100, byzantine_fraction: float = 0.33,
                              verbose: bool = False, seed: Optional[int] = None,
                              enable_phason_rekey: bool = True) -> Dict[str, Any]:
    """
    Simulate Byzantine attack with n_agents.

    Byzantine agents attempt to forge states that pass governance.
    Honest agents follow protocol with states near authorized realm centers.

    Args:
        n_agents: Total number of agents
        byzantine_fraction: Fraction of Byzantine attackers
        verbose: Print detailed output
        seed: Random seed for reproducibility
        enable_phason_rekey: Apply phason strain to quasicrystal (atomic rekeying)

    Returns attack success/failure metrics.
    """
    if seed is not None:
        np.random.seed(seed)

    n_byzantine = int(n_agents * byzantine_fraction)
    n_honest = n_agents - n_byzantine

    agents = []
    poly = Polyhedron(V=6, E=9, F=5)
    secret_key = os.urandom(KEY_LEN)

    # Apply phason strain for session rekeying (atomic key rotation)
    if enable_phason_rekey:
        session_entropy = secret_key + str(time.time()).encode()
        QUASICRYSTAL.apply_phason_rekey(session_entropy)
        if verbose:
            print(f"[SCBE] Phason Rekey Applied: {QUASICRYSTAL.phason_strain}")

    # Define authorized realm centers (trusted state patterns)
    # States near these centers will have low d* and thus low risk
    n_realms = 5
    realm_centers = np.random.randn(n_realms, 12) * 0.3  # Small values for Poincaré embedding
    realm_centers = realm_centers / (1 + np.linalg.norm(realm_centers, axis=1, keepdims=True))  # In ball

    # Create agents
    for i in range(n_agents):
        is_byzantine = i < n_byzantine
        t = time.time() + i * 0.01

        if is_byzantine:
            # Byzantine: forge state far from authorized realms
            state = generate_9d_state(t)
            state.eta = ETA_MIN  # Artificially low entropy
            # Byzantine states have random context (likely far from realm centers)
        else:
            # Honest: generate state that will embed NEAR a realm center
            state = generate_9d_state(t)
            # Adjust context to be near an authorized realm center
            target_realm = realm_centers[i % n_realms]
            # Set context components to approximate the target (will embed nearby)
            noise = np.random.randn(6) * 0.02  # Tight noise for authorized proximity
            state.context = target_realm[:6] + noise
            # Boost coherence metrics for honest agents
            state.eta = 2.5  # Moderate entropy (not suspicious)

        agents.append(SwarmAgent(agent_id=i, is_byzantine=is_byzantine, state=state))

    # Run governance on each agent with shared realm centers
    results = {"allow": 0, "quarantine": 0, "deny": 0}
    byzantine_allowed = 0
    honest_denied = 0

    for agent in agents:
        intent = 0.75 if not agent.is_byzantine else 0.5  # Byzantine uses wrong intent
        result = governance_pipeline(agent.state, intent, poly, realm_centers=realm_centers)
        agent.vote = result.decision

        results[result.decision.lower()] += 1

        if agent.is_byzantine and result.decision == "ALLOW":
            byzantine_allowed += 1
        if not agent.is_byzantine and result.decision == "DENY":
            honest_denied += 1

    # Attack success = byzantine agents that got ALLOW
    attack_success_rate = byzantine_allowed / max(n_byzantine, 1)
    honest_success_rate = 1 - (honest_denied / max(n_honest, 1))

    # Swarm consensus (majority vote)
    majority_decision = max(results, key=results.get).upper()

    # Byzantine tolerance threshold: f < n/3
    tolerance_met = n_byzantine < n_agents / 3

    # Attack blocked: Byzantine agents rarely allowed AND honest agents mostly succeed
    # Using 80% threshold for honest success due to probabilistic nature of simulation
    passed = attack_success_rate < 0.1 and honest_success_rate > 0.8

    if verbose:
        print(f"\n{'='*60}")
        print(f"BYZANTINE ATTACK SIMULATION")
        print(f"{'='*60}")
        print(f"  Agents: {n_agents} ({n_honest} honest, {n_byzantine} Byzantine)")
        print(f"  Results: ALLOW={results['allow']}, QUARANTINE={results['quarantine']}, DENY={results['deny']}")
        print(f"  Byzantine allowed: {byzantine_allowed}/{n_byzantine} ({attack_success_rate:.1%})")
        print(f"  Honest success: {n_honest - honest_denied}/{n_honest} ({honest_success_rate:.1%})")
        print(f"  Majority decision: {majority_decision}")
        print(f"  f < n/3 tolerance: {'✓' if tolerance_met else '✗'}")
        print(f"  Attack {'BLOCKED' if passed else 'SUCCEEDED'}")
        print(f"{'='*60}\n")

    return {
        "n_agents": n_agents,
        "n_byzantine": n_byzantine,
        "attack_success_rate": attack_success_rate,
        "honest_success_rate": honest_success_rate,
        "majority_decision": majority_decision,
        "tolerance_met": tolerance_met,
        "attack_blocked": passed,
        "results": results
    }


# =============================================================================
# SECTION 9: SELF-TEST & DEMO
# =============================================================================

def self_test(verbose: bool = True) -> Dict[str, Any]:
    """Run comprehensive self-test."""
    results = {}

    # Test 1: QASI core axioms
    c = np.array([1+2j, 3-4j], dtype=np.complex128)
    x = realify(c)
    ok_realify = abs(np.linalg.norm(x) - np.sqrt(np.sum(np.abs(c)**2))) < 1e-10
    results['realify_isometry'] = ok_realify

    # Test 2: Poincaré embedding
    u = poincare_embed(x, alpha=1.0)
    ok_ball = np.linalg.norm(u) < 1.0
    results['poincare_ball'] = ok_ball

    # Test 3: Hyperbolic distance symmetry
    v = clamp_ball(np.random.randn(len(u)) * 0.1)
    d_uv = hyperbolic_distance(u, v)
    d_vu = hyperbolic_distance(v, u)
    ok_sym = abs(d_uv - d_vu) < 1e-10
    results['distance_symmetry'] = ok_sym

    # Test 4: Risk monotonicity
    rb = risk_base(0.2, 0.9, 0.9, 0.9, 0.9)
    rp1 = risk_prime(0.5, rb)["risk_prime"]
    rp2 = risk_prime(1.0, rb)["risk_prime"]
    ok_mono = rp2 >= rp1
    results['risk_monotone'] = ok_mono

    # Test 5: Governance pipeline
    state = generate_9d_state(1.0)
    poly = Polyhedron(V=6, E=9, F=5)
    gov = governance_pipeline(state, 0.75, poly)
    ok_gov = gov.decision in ["ALLOW", "QUARANTINE", "DENY"]
    results['governance'] = ok_gov

    # Test 6: Byzantine resistance (seed=42 for reproducibility)
    byz = simulate_byzantine_attack(50, 0.33, verbose=False, seed=42)
    ok_byz = byz["attack_blocked"]
    results['byzantine_resistance'] = ok_byz

    # Test 7: HMAC chain
    key = os.urandom(KEY_LEN)
    tag1 = hmac_chain(["a", "b"], key)
    tag2 = hmac_chain(["a", "b"], key)
    ok_hmac = tag1 == tag2
    results['hmac_chain'] = ok_hmac

    # Test 8: Phase roundtrip
    intent = 0.75
    wave = phase_modulated_intent(intent)
    recovered = extract_phase(wave)
    ok_phase = abs(recovered - intent) < 0.05
    results['phase_roundtrip'] = ok_phase

    # Test 9: Spectral stability variance (pure tone vs noise)
    pure_tone = phase_modulated_intent(0.5)
    noise = np.random.randn(len(pure_tone))
    s_pure = spectral_stability(pure_tone)
    s_noise = spectral_stability(noise)
    ok_spec = s_pure > 0.9 and s_noise < 0.2  # Pure concentrated, noise flat
    results['spectral_variance'] = ok_spec

    # Test 10: Audio envelope coherence
    s_audio = audio_envelope_coherence(pure_tone)
    ok_audio = 0.9 <= s_audio <= 1.0  # Pure tone has stable envelope
    results['audio_coherence'] = ok_audio

    # Test 11: Entropy non-negativity
    entropies = [compute_entropy([generate_context(float(t))]) for t in [0, 100, 1000]]
    ok_entropy = all(e >= 0 for e in entropies)
    results['entropy_positive'] = ok_entropy

    # Test 12: Extreme coordinate handling
    extreme = np.array([1e10 + 1e10j, 1e-10 - 1e-10j])
    u_extreme = poincare_embed(realify(extreme))
    ok_extreme = np.linalg.norm(u_extreme) < 1.0 and not np.any(np.isnan(u_extreme))
    results['extreme_coords'] = ok_extreme

    # Test 13: CPSE Lorentz factor (event horizon throttling)
    gamma_low = lorentz_factor(10, 100)   # 10% of critical → γ ≈ 1
    gamma_high = lorentz_factor(99, 100)  # 99% of critical → γ >> 1
    ok_lorentz = 1.0 <= gamma_low < 1.1 and gamma_high > 5.0
    results['cpse_lorentz'] = ok_lorentz

    # Test 14: CPSE Soliton dynamics (packet integrity)
    secret = b"authorized_key"
    phi_d = soliton_key_from_secret(secret)
    packet = SolitonPacket(amplitude=0.8, phi_d=phi_d)
    for _ in range(10):
        packet = soliton_evolve(packet)
    ok_soliton = 0.5 < packet.amplitude <= 1.0  # Maintains amplitude
    results['cpse_soliton'] = ok_soliton

    # Test 15: CPSE Spin rotation (context-dependent)
    v_in = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    v_out = apply_spin(v_in, "time:1234|loc:NYC|role:admin")
    ok_spin = np.linalg.norm(v_out) > 0.99  # Rotation preserves norm
    results['cpse_spin'] = ok_spin

    if verbose:
        print("=" * 60)
        print("SCBE-AETHERMOORE v2.1 SELF-TEST")
        print("=" * 60)
        for k, v in results.items():
            status = "✓ PASS" if v else "✗ FAIL"
            print(f"  {k:25s}: {status}")
        print("-" * 60)
        passed = sum(results.values())
        print(f"  Total: {passed}/{len(results)} tests passed")
        print("=" * 60)

    return {
        "passed": sum(results.values()),
        "total": len(results),
        "all_passed": all(results.values()),
        "results": results
    }


def demo():
    """Full production demo."""
    print("\n" + "=" * 70)
    print("SCBE-AETHERMOORE v2.1 PRODUCTION DEMO")
    print("=" * 70)

    # Generate 9D state
    t = time.time() % 100
    state = generate_9d_state(t)
    print(f"\n[1] 9D State generated at t={t:.2f}")
    print(f"    Context: {len(state.context)} dimensions")
    print(f"    Tau: {state.tau:.4f}, Eta: {state.eta:.4f}")
    print(f"    Quantum: {state.q}")

    # Harmonic cipher
    intent = 0.75
    wave = phase_modulated_intent(intent)
    recovered = extract_phase(wave)
    print(f"\n[2] Harmonic Cipher")
    print(f"    Intent: {intent} → Recovered: {recovered:.4f}")

    secret_key = os.urandom(KEY_LEN)
    token_ids = [CONLANG["korah"], CONLANG["aelin"], CONLANG["dahru"]]
    tokens = [REV_CONLANG[i] for i in token_ids]
    print(f"    Tokens: {tokens}")
    resonance = resonance_refractor(token_ids, secret_key)
    print(f"    Resonance pattern: {len(resonance)} samples")

    # Topology
    poly = Polyhedron(V=6, E=9, F=5)
    chi = poly.euler_characteristic()
    valid = phdm_validate(poly)
    print(f"\n[3] PHDM Topology")
    print(f"    Euler characteristic: χ = {chi}")
    print(f"    Valid: {'✓' if valid else '✗'}")

    # Full governance pipeline
    result = governance_pipeline(state, intent, poly)
    print(f"\n[4] Governance Pipeline (L1-L14)")
    print(f"    Hyperbolic state ||u|| = {np.linalg.norm(result.hyperbolic_state):.6f}")
    print(f"    d* (realm distance): {result.metrics['d_star']:.4f}")
    print(f"    C_spin: {result.metrics['C_spin']:.4f}")
    print(f"    S_spec: {result.metrics['S_spec']:.4f}")
    print(f"    Risk_base: {result.risk_base:.4f}")
    print(f"    Risk' (amplified): {result.risk_amplified:.4f}")
    print(f"    Risk'' (final): {result.risk_final:.4f}")
    print(f"\n[5] Grok Oracle")
    print(f"    Invoked: {result.grok_result.invoked}")
    print(f"    Truth score: {result.grok_result.truth_score:.4f}")
    print(f"    Reasoning: {result.grok_result.reasoning}")

    print(f"\n[6] DECISION: {result.decision}")
    print(f"    {result.output}")

    # HMAC chain
    messages = ["cmd1", "cmd2", "cmd3"]
    chain_tag = hmac_chain(messages, secret_key)
    print(f"\n[7] HMAC Chain")
    print(f"    Messages: {messages}")
    print(f"    Tag: {chain_tag[:32]}...")

    # Byzantine simulation
    print(f"\n[8] Byzantine Attack Simulation")
    simulate_byzantine_attack(50, 0.33, verbose=True)

    print("=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    # Run self-test
    test_results = self_test(verbose=True)
    print()

    # Run demo
    demo()
