"""
Harmonic Scaling Law: Quantum-Resistant, Bounded, Metric-Compatible Risk Amplification

This module implements the corrected Harmonic Scaling Law for the SCBE-AETHERMOORE framework.

Key Design Principles:
1. Bounded & Monotonic - No overflow, preserves ordering, metric-compatible
2. Quantum-Resistant - All scaling constants and inputs bound by hybrid PQC commitments
3. Harmonic Ratios Preserved - R derived from musical ratios as coordination constant
4. Log-Space Stability - All computations are safe and numerically stable
5. Integration with dH - Scaling applied AFTER invariant hyperbolic distance

Primary (Bounded) Form:
    H(d*, R) = 1 + alpha * tanh(beta * d*)

Where:
    d* = min_k dH(u_tilde, mu_k)  (invariant hyperbolic distance to nearest trusted realm)
    alpha = 10.0 (maximum additional risk multiplier - tunable)
    beta = 0.5 (growth rate - tunable, controls saturation speed)
    tanh ensures H in [1, 1+alpha] (bounded, monotonic, continuous)

Alternative (Logarithmic) Form:
    H(d*, R) = log2(1 + d*)

Security Decision Composition:
    Security_Decision = Crypto_Valid AND Behavioral_Risk < theta

    Crypto_Valid = PQ_Key_Exchange_Success AND PQ_Signature_Verified
                 = Kyber(ML-KEM) + Dilithium(ML-DSA) + SHA3-256

    Behavioral_Risk = w_d * D_hyp + w_c * (1 - C_spin) + w_s * (1 - S_spec) + ...

    D_hyp = tanh(d* / d_scale)  <- Uses invariant dH, bounded

    Final_Risk' = Behavioral_Risk * H(d*, R)  <- H is bounded tanh form
"""

import math
import hashlib
from dataclasses import dataclass
from typing import Tuple, Optional, List
from enum import Enum
import numpy as np


# =============================================================================
# CONSTANTS
# =============================================================================

# Default scaling parameters
DEFAULT_ALPHA = 10.0       # Maximum additional risk multiplier
DEFAULT_BETA = 0.5         # Growth rate (controls saturation speed)

# PQ Crypto placeholder constants (real impl uses liboqs)
PQ_CONTEXT_COMMITMENT_SIZE = 32  # SHA3-256 output size
KYBER_PUBLIC_KEY_SIZE = 1184     # Kyber-768 public key
DILITHIUM_SIG_SIZE = 2420        # Dilithium2 signature size

# Harmonic coordination constant (musical ratio - NOT cryptographic)
# R = 3/2 (perfect fifth ratio) - used for interpretability, not security
HARMONIC_RATIO_R = 3.0 / 2.0

# Golden Ratio - coordination constant for Langues metric
PHI = (1 + np.sqrt(5)) / 2  # φ ≈ 1.6180339887

# Hyperbolic geometry constants
POINCARE_CURVATURE = -1.0  # Constant negative curvature for Poincare disk

# Langues metric constants
LANGUES_DIMENSIONS = 6      # 6 Sacred Tongues

# Epsilon thresholds - RIGOROUS BOUNDS from Weyl's inequality analysis
# For G_0 = diag(1,1,1,φ,φ²,φ³) with harmonic progression:
#   ε* = 1/(2φ^(3D-1)) where D=6 → ε* = 1/(2φ^17) ≈ 3.67e-4
# This is much tighter than naive estimates due to exponential growth in Φ(r)
EPSILON_THRESHOLD_HARMONIC = 1.0 / (2 * PHI ** 17)  # ≈ 3.67e-4 for 6D
EPSILON_THRESHOLD_UNIFORM = 1.0 / (2 * LANGUES_DIMENSIONS)  # 1/12 ≈ 0.083 for G_0=I
EPSILON_THRESHOLD_NORMALIZED = 1.0 / (2 * LANGUES_DIMENSIONS)  # Same as uniform

# Default epsilon - use NORMALIZED mode default for practical coupling strength
DEFAULT_EPSILON = 0.05      # Safe for normalized mode
EPSILON_THRESHOLD = EPSILON_THRESHOLD_NORMALIZED  # Backwards compat (use normalized)


class CouplingMode(Enum):
    """
    Langues metric coupling modes with different ε* bounds.

    Trade-off: Harmonic progression (φ^k weights) vs coupling strength (ε).

    HARMONIC: Original φ^k weights, ε* ≈ 3.67e-4 (essentially diagonal)
    UNIFORM: G_0 = I, ε* ≈ 0.083 (genuine multidimensional interaction)
    NORMALIZED: φ^k weights with normalized C_k, ε* ≈ 0.083 (best of both)
    """
    HARMONIC = "harmonic"       # G_0 = diag(1,1,1,φ,φ²,φ³), ε* ≈ 3.67e-4
    UNIFORM = "uniform"         # G_0 = I, ε* ≈ 1/(2D)
    NORMALIZED = "normalized"   # G_0 = diag(...), C_k normalized by sqrt(g_k*g_{k+1})


class ScalingMode(Enum):
    """Scaling function modes."""
    BOUNDED_TANH = "tanh"       # Primary - bounded [1, 1+alpha]
    LOGARITHMIC = "log"         # Alternative - slower growth
    LINEAR_CLIPPED = "linear"   # Simple - linear with clip


# =============================================================================
# HYPERBOLIC DISTANCE (LAYER 8 - dH METRIC)
# =============================================================================

def hyperbolic_distance_poincare(
    u: np.ndarray,
    v: np.ndarray,
    eps: float = 1e-10
) -> float:
    """
    Compute hyperbolic distance in the Poincare ball model.

    dH(u, v) = arcosh(1 + 2 * ||u - v||^2 / ((1 - ||u||^2)(1 - ||v||^2)))

    This is the invariant metric that remains unchanged regardless of
    coordinate representation - the "unchanging law of distance" in SCBE.

    Args:
        u: Point in Poincare ball (||u|| < 1)
        v: Point in Poincare ball (||v|| < 1)
        eps: Small epsilon for numerical stability

    Returns:
        Hyperbolic distance dH(u, v)
    """
    u = np.asarray(u, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)

    norm_u_sq = np.sum(u ** 2)
    norm_v_sq = np.sum(v ** 2)
    diff_sq = np.sum((u - v) ** 2)

    # Clamp norms to ensure points are inside the ball
    norm_u_sq = min(norm_u_sq, 1.0 - eps)
    norm_v_sq = min(norm_v_sq, 1.0 - eps)

    denominator = (1 - norm_u_sq) * (1 - norm_v_sq)
    denominator = max(denominator, eps)  # Avoid division by zero

    cosh_dist = 1 + 2 * diff_sq / denominator
    cosh_dist = max(cosh_dist, 1.0)  # arcosh domain

    return float(np.arccosh(cosh_dist))


def find_nearest_trusted_realm(
    point: np.ndarray,
    trusted_realms: List[np.ndarray]
) -> Tuple[float, int]:
    """
    Find minimum hyperbolic distance to any trusted realm center.

    d* = min_k dH(u_tilde, mu_k)

    Args:
        point: Current point in Poincare ball (u_tilde)
        trusted_realms: List of trusted realm centers (mu_k)

    Returns:
        Tuple of (minimum distance d*, index of nearest realm)
    """
    if not trusted_realms:
        raise ValueError("At least one trusted realm must be defined")

    min_dist = float('inf')
    min_idx = 0

    for i, realm_center in enumerate(trusted_realms):
        d = hyperbolic_distance_poincare(point, realm_center)
        if d < min_dist:
            min_dist = d
            min_idx = i

    return min_dist, min_idx


# =============================================================================
# QUANTUM-RESISTANT CONTEXT BINDING
# =============================================================================

@dataclass
class PQContextCommitment:
    """
    Post-Quantum cryptographic context commitment.

    In production, this binds:
    - Kyber (ML-KEM) key encapsulation for shared secret
    - Dilithium (ML-DSA) signature for authentication
    - SHA3-256 hash for commitment

    Security Guarantee:
    Quantum attacker cannot forge valid d* without breaking BOTH
    Kyber AND Dilithium simultaneously.
    """
    commitment_hash: bytes      # SHA3-256(context)
    kyber_ciphertext: bytes     # ML-KEM encapsulation (placeholder)
    dilithium_signature: bytes  # ML-DSA signature (placeholder)
    context_version: int = 1

    @classmethod
    def create(
        cls,
        context_data: bytes,
        kyber_public_key: Optional[bytes] = None,
        dilithium_private_key: Optional[bytes] = None
    ) -> "PQContextCommitment":
        """
        Create a PQ-bound context commitment.

        In production, this would:
        1. Encapsulate using Kyber public key
        2. Sign context using Dilithium private key
        3. Hash everything with SHA3-256

        Args:
            context_data: The 6D context data to commit
            kyber_public_key: ML-KEM public key (placeholder)
            dilithium_private_key: ML-DSA private key (placeholder)

        Returns:
            PQContextCommitment instance
        """
        # SHA3-256 commitment hash
        commitment = hashlib.sha3_256(context_data).digest()

        # Placeholder for Kyber encapsulation
        # In production: ciphertext, shared_secret = kyber.encapsulate(public_key)
        kyber_ct = hashlib.sha3_256(b"kyber_placeholder" + context_data).digest()

        # Placeholder for Dilithium signature
        # In production: signature = dilithium.sign(private_key, commitment)
        dilithium_sig = hashlib.sha3_256(b"dilithium_placeholder" + commitment).digest()

        return cls(
            commitment_hash=commitment,
            kyber_ciphertext=kyber_ct,
            dilithium_signature=dilithium_sig
        )

    def verify(self, context_data: bytes) -> bool:
        """
        Verify the commitment matches the context.

        In production, this would verify both:
        1. Kyber decapsulation matches
        2. Dilithium signature verifies

        Args:
            context_data: Context to verify against

        Returns:
            True if commitment is valid
        """
        expected = hashlib.sha3_256(context_data).digest()
        return expected == self.commitment_hash


def create_context_commitment(
    d_star: float,
    behavioral_risk: float,
    session_id: bytes,
    extra_context: Optional[bytes] = None
) -> bytes:
    """
    Create cryptographic commitment for scaling context.

    This binds all inputs to H to prevent tampering:
    - d* (hyperbolic distance)
    - Behavioral risk components
    - Session identifier

    Args:
        d_star: Hyperbolic distance to nearest trusted realm
        behavioral_risk: Computed behavioral risk score
        session_id: Unique session identifier
        extra_context: Optional additional context bytes

    Returns:
        32-byte SHA3-256 commitment
    """
    # Pack context into bytes
    context = (
        d_star.hex().encode() if hasattr(d_star, 'hex') else str(d_star).encode()
    )
    context = str(d_star).encode()
    context += b"|" + str(behavioral_risk).encode()
    context += b"|" + session_id

    if extra_context:
        context += b"|" + extra_context

    return hashlib.sha3_256(context).digest()


# =============================================================================
# HARMONIC SCALING LAW - PRIMARY IMPLEMENTATION
# =============================================================================

class HarmonicScalingLaw:
    """
    Bounded, monotonic, metric-compatible harmonic scaling for risk amplification.

    Primary Form (Recommended):
        H(d*, R) = 1 + alpha * tanh(beta * d*)

    Properties:
        - Bounded: H in [1, 1 + alpha], no overflow ever
        - Monotonic: H(d1) < H(d2) if d1 < d2
        - Metric-compatible: Subadditive, preserves ordering
        - Interpretable: H=1 means perfect match, H=11 means maximum risk

    Integration:
        Final_Risk' = Behavioral_Risk * H(d*, R)
    """

    def __init__(
        self,
        alpha: float = DEFAULT_ALPHA,
        beta: float = DEFAULT_BETA,
        mode: ScalingMode = ScalingMode.BOUNDED_TANH,
        require_pq_binding: bool = True
    ):
        """
        Initialize Harmonic Scaling Law.

        Args:
            alpha: Maximum additional risk multiplier (default 10.0)
            beta: Growth rate controlling saturation speed (default 0.5)
            mode: Scaling function mode (default BOUNDED_TANH)
            require_pq_binding: Whether to require PQ context commitment
        """
        if alpha <= 0:
            raise ValueError("alpha must be positive")
        if beta <= 0:
            raise ValueError("beta must be positive")

        self.alpha = alpha
        self.beta = beta
        self.mode = mode
        self.require_pq_binding = require_pq_binding

        # Harmonic ratio (coordination constant, not cryptographic)
        self.harmonic_ratio = HARMONIC_RATIO_R

    def compute(
        self,
        d_star: float,
        context_commitment: Optional[bytes] = None
    ) -> float:
        """
        Compute bounded harmonic scaling factor H(d*).

        Args:
            d_star: Hyperbolic distance to nearest trusted realm (d* >= 0)
            context_commitment: 32-byte PQ context commitment

        Returns:
            Scaling factor H in [1, 1 + alpha]

        Raises:
            ValueError: If PQ binding required but commitment invalid
        """
        # Validate PQ binding if required
        if self.require_pq_binding:
            if context_commitment is None:
                raise ValueError("PQ context commitment required")
            if len(context_commitment) != PQ_CONTEXT_COMMITMENT_SIZE:
                raise ValueError(
                    f"Invalid PQ context commitment size: "
                    f"expected {PQ_CONTEXT_COMMITMENT_SIZE}, got {len(context_commitment)}"
                )

        # Ensure non-negative distance
        d_star = max(0.0, float(d_star))

        # Compute scaling based on mode
        if self.mode == ScalingMode.BOUNDED_TANH:
            # Primary form: H = 1 + alpha * tanh(beta * d*)
            h = 1.0 + self.alpha * math.tanh(self.beta * d_star)

        elif self.mode == ScalingMode.LOGARITHMIC:
            # Alternative form: H = log2(1 + d*)
            # Note: This is unbounded but grows very slowly
            h = math.log2(1.0 + d_star)
            # Ensure minimum of 1.0 for consistency
            h = max(1.0, h)

        elif self.mode == ScalingMode.LINEAR_CLIPPED:
            # Simple linear with clip: H = min(1 + d*, 1 + alpha)
            h = min(1.0 + d_star, 1.0 + self.alpha)

        else:
            raise ValueError(f"Unknown scaling mode: {self.mode}")

        return h

    def compute_risk(
        self,
        behavioral_risk: float,
        d_star: float,
        context_commitment: Optional[bytes] = None
    ) -> float:
        """
        Compute final scaled risk.

        Final_Risk' = Behavioral_Risk * H(d*, R)

        Args:
            behavioral_risk: Base behavioral risk score [0, 1]
            d_star: Hyperbolic distance to nearest trusted realm
            context_commitment: PQ context commitment

        Returns:
            Scaled risk value
        """
        h = self.compute(d_star, context_commitment)
        return behavioral_risk * h

    def compute_with_components(
        self,
        d_star: float,
        context_commitment: Optional[bytes] = None
    ) -> dict:
        """
        Compute scaling with full component breakdown.

        Args:
            d_star: Hyperbolic distance to nearest trusted realm
            context_commitment: PQ context commitment

        Returns:
            Dictionary with all intermediate values
        """
        h = self.compute(d_star, context_commitment)

        return {
            "d_star": d_star,
            "alpha": self.alpha,
            "beta": self.beta,
            "mode": self.mode.value,
            "tanh_term": math.tanh(self.beta * d_star) if self.mode == ScalingMode.BOUNDED_TANH else None,
            "H": h,
            "H_min": 1.0,
            "H_max": 1.0 + self.alpha,
            "saturation_percent": (h - 1.0) / self.alpha * 100 if self.alpha > 0 else 0,
            "harmonic_ratio_R": self.harmonic_ratio,
        }


# =============================================================================
# CONVENIENCE FUNCTION (API COMPATIBLE)
# =============================================================================

def quantum_resistant_harmonic_scaling(
    d_star: float,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
    context_commitment: bytes = b"\x00" * 32
) -> float:
    """
    Quantum-resistant harmonic scaling (standalone function).

    This is the recommended API for integration with the SCBE framework.

    1. Verify context commitment (Kyber + Dilithium in production)
    2. Compute bounded H using tanh
    3. Return scaling factor

    Args:
        d_star: Hyperbolic distance to nearest trusted realm
        alpha: Maximum additional risk multiplier (default 10.0)
        beta: Growth rate (default 0.5)
        context_commitment: 32-byte PQ context commitment

    Returns:
        Scaling factor H in [1, 1 + alpha]

    Raises:
        ValueError: If commitment is invalid
    """
    # In production: Verify Dilithium signature over context_commitment
    if len(context_commitment) != PQ_CONTEXT_COMMITMENT_SIZE:
        raise ValueError("Invalid PQ context commitment")

    # Bounded hyperbolic risk amplification
    d_star = max(0.0, float(d_star))
    h = 1.0 + alpha * math.tanh(beta * d_star)

    return h


# =============================================================================
# BEHAVIORAL RISK INTEGRATION
# =============================================================================

@dataclass
class BehavioralRiskComponents:
    """
    Components of the behavioral risk score.

    Behavioral_Risk = w_d * D_hyp + w_c * (1 - C_spin) + w_s * (1 - S_spec) + ...

    All components normalized to [0, 1].
    """
    D_hyp: float = 0.0      # Hyperbolic distance component (normalized)
    C_spin: float = 1.0     # Spin coherence (1 = perfect)
    S_spec: float = 1.0     # Spectral similarity (1 = perfect)
    T_temp: float = 1.0     # Temporal consistency (1 = perfect)
    E_entropy: float = 0.0  # Entropy deviation (0 = perfect)

    # Weights
    w_d: float = 0.3
    w_c: float = 0.2
    w_s: float = 0.2
    w_t: float = 0.15
    w_e: float = 0.15

    def compute(self) -> float:
        """Compute weighted behavioral risk."""
        risk = (
            self.w_d * self.D_hyp +
            self.w_c * (1 - self.C_spin) +
            self.w_s * (1 - self.S_spec) +
            self.w_t * (1 - self.T_temp) +
            self.w_e * self.E_entropy
        )
        # Clamp to [0, 1]
        return max(0.0, min(1.0, risk))


class SecurityDecisionEngine:
    """
    Complete security decision engine integrating PQ crypto and harmonic scaling.

    Security_Decision = Crypto_Valid AND Behavioral_Risk < theta

    Where:
        Crypto_Valid = PQ_Key_Exchange_Success AND PQ_Signature_Verified
        Final_Risk' = Behavioral_Risk * H(d*, R)
    """

    def __init__(
        self,
        scaling_law: Optional[HarmonicScalingLaw] = None,
        risk_threshold: float = 0.7
    ):
        """
        Initialize security decision engine.

        Args:
            scaling_law: HarmonicScalingLaw instance
            risk_threshold: Maximum allowed scaled risk (theta)
        """
        self.scaling_law = scaling_law or HarmonicScalingLaw(require_pq_binding=False)
        self.risk_threshold = risk_threshold

    def evaluate(
        self,
        crypto_valid: bool,
        behavioral_risk: float,
        d_star: float,
        context_commitment: Optional[bytes] = None
    ) -> Tuple[bool, dict]:
        """
        Evaluate security decision.

        Args:
            crypto_valid: Result of PQ crypto verification
            behavioral_risk: Base behavioral risk [0, 1]
            d_star: Hyperbolic distance to nearest trusted realm
            context_commitment: Optional PQ context commitment

        Returns:
            Tuple of (decision: bool, details: dict)
        """
        # Compute scaled risk
        scaling_components = self.scaling_law.compute_with_components(
            d_star,
            context_commitment
        )

        H = scaling_components["H"]
        final_risk = behavioral_risk * H

        # Security decision
        risk_acceptable = final_risk < self.risk_threshold
        decision = crypto_valid and risk_acceptable

        return decision, {
            "decision": decision,
            "crypto_valid": crypto_valid,
            "behavioral_risk": behavioral_risk,
            "d_star": d_star,
            "H": H,
            "final_risk": final_risk,
            "risk_threshold": self.risk_threshold,
            "risk_acceptable": risk_acceptable,
            "scaling_components": scaling_components,
        }


# =============================================================================
# LANGUES METRIC TENSOR (6-DIMENSIONAL WEIGHTING SYSTEM)
# =============================================================================

def get_epsilon_threshold(mode: "CouplingMode", n_dims: int = LANGUES_DIMENSIONS) -> float:
    """
    Get the rigorous epsilon threshold for a given coupling mode.

    Derived via Weyl's inequality perturbation analysis.

    Args:
        mode: Coupling mode (HARMONIC, UNIFORM, or NORMALIZED)
        n_dims: Number of dimensions

    Returns:
        Maximum safe epsilon for guaranteed positive definiteness
    """
    if mode == CouplingMode.HARMONIC:
        # ε* = 1/(2φ^(3D-1)) - exponential decay due to φ^k growth
        return 1.0 / (2 * PHI ** (3 * n_dims - 1))
    elif mode == CouplingMode.UNIFORM:
        # ε* = 1/(2D) - linear scaling
        return 1.0 / (2 * n_dims)
    elif mode == CouplingMode.NORMALIZED:
        # ε* = 1/(2D) - normalized coupling cancels φ^k growth
        return 1.0 / (2 * n_dims)
    else:
        raise ValueError(f"Unknown coupling mode: {mode}")


def create_coupling_matrix(
    k: int,
    R: float = PHI,
    epsilon: float = DEFAULT_EPSILON,
    mode: "CouplingMode" = None,
    G_0_diag: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Create coupling matrix A_k for the k-th langue dimension.

    Standard form (HARMONIC mode):
        A_k = (ln R^k) * E_kk + ε * (E_{k,k+1} + E_{k+1,k})

    Normalized form (NORMALIZED mode):
        A_k = (ln R^k) * E_kk + ε * (E_{k,k+1} + E_{k+1,k}) / sqrt(g_k * g_{k+1})

    Where:
    - E_ij = matrix with 1 at position (i,j) and 0 elsewhere
    - Indices are mod 6 (dimension 6 couples back to 1)
    - R = φ (golden ratio) ≈ 1.618
    - g_k = diagonal entries of G_0

    Args:
        k: Dimension index (0-5)
        R: Coordination constant (default: golden ratio φ)
        epsilon: Coupling strength (default: 0.05)
        mode: Coupling mode (default: NORMALIZED)
        G_0_diag: Diagonal of baseline metric (for normalization)

    Returns:
        6x6 coupling matrix A_k
    """
    if mode is None:
        mode = CouplingMode.NORMALIZED

    n = LANGUES_DIMENSIONS
    A = np.zeros((n, n), dtype=np.float64)

    # Diagonal scaling term: (ln R^k) at position (k, k)
    # For UNIFORM mode, skip the diagonal scaling
    if mode != CouplingMode.UNIFORM:
        A[k, k] = k * np.log(R) if k > 0 else 0.0

    # Nearest-neighbor coupling (cyclic)
    k_next = (k + 1) % n

    if mode == CouplingMode.NORMALIZED and G_0_diag is not None:
        # Normalize by sqrt(g_k * g_{k+1}) to cancel exponential growth
        # This gives ε* = 1/(2D) regardless of G_0 diagonal values
        normalizer = np.sqrt(G_0_diag[k] * G_0_diag[k_next])
        A[k, k_next] = epsilon / normalizer
        A[k_next, k] = epsilon / normalizer
    else:
        A[k, k_next] = epsilon
        A[k_next, k] = epsilon

    return A


def create_baseline_metric(
    R: float = PHI,
    mode: "CouplingMode" = None
) -> np.ndarray:
    """
    Create the baseline diagonal metric tensor G_0.

    HARMONIC/NORMALIZED mode:
        G_0 = diag(1, 1, 1, R, R², R³)

    UNIFORM mode:
        G_0 = I (identity matrix)

    Args:
        R: Coordination constant (default: golden ratio φ)
        mode: Coupling mode (default: NORMALIZED)

    Returns:
        6x6 diagonal baseline metric G_0
    """
    if mode is None:
        mode = CouplingMode.NORMALIZED

    if mode == CouplingMode.UNIFORM:
        return np.eye(LANGUES_DIMENSIONS, dtype=np.float64)
    else:
        return np.diag([1.0, 1.0, 1.0, R, R**2, R**3])


class LanguesMetricTensor:
    """
    6-Dimensional Langues Weight Tensor System with rigorous epsilon bounds.

    The langues weight operator is defined as:
        Λ(r) = exp(Σ_{k=1}^{6} r_k * A_k)

    The langues-modified metric tensor is:
        G_L(r) = Λ(r)^T * G_0 * Λ(r)

    COUPLING MODES (Critical for epsilon bounds):

    1. HARMONIC (Original):
       - G_0 = diag(1,1,1,φ,φ²,φ³)
       - Standard C_k coupling
       - ε* = 1/(2φ^17) ≈ 3.67e-4 (very tight!)
       - Essentially diagonal with tiny cross-coupling

    2. UNIFORM:
       - G_0 = I (identity)
       - ε* = 1/(2D) ≈ 0.083
       - Genuine multidimensional interaction
       - Loses harmonic progression

    3. NORMALIZED (Recommended):
       - G_0 = diag(1,1,1,φ,φ²,φ³)
       - C_k^norm = (E_{k,k+1} + E_{k+1,k}) / sqrt(g_k * g_{k+1})
       - ε* = 1/(2D) ≈ 0.083
       - Best of both: harmonic weights + practical coupling

    Rigorous Bounds (from Weyl's inequality):
        ε* = 1/(2φ^(3D-1)) for HARMONIC mode
        ε* = 1/(2D) for UNIFORM and NORMALIZED modes

    Patent-Ready Definition:
    "A langues weight operator Λ(r) defined as the matrix exponential
    exp(Σ r_k A_k) with coupling matrices A_k comprising diagonal
    scaling terms (ln R^k) E_kk and normalized nearest-neighbor coupling
    ε(E_{k,k+1} + E_{k+1,k})/sqrt(g_k g_{k+1}), wherein the langues-modified
    metric tensor G_L(r) = Λ(r)^T G_0 Λ(r) is positive definite for ε < 1/(2D),
    providing genuine multidimensional interaction between context dimensions
    while preserving harmonic progression weights."
    """

    def __init__(
        self,
        R: float = PHI,
        epsilon: float = DEFAULT_EPSILON,
        mode: CouplingMode = CouplingMode.NORMALIZED,
        validate_epsilon: bool = True
    ):
        """
        Initialize Langues Metric Tensor.

        Args:
            R: Coordination constant (default: golden ratio φ ≈ 1.618)
            epsilon: Coupling strength (default: 0.05)
            mode: Coupling mode (HARMONIC, UNIFORM, or NORMALIZED)
            validate_epsilon: Whether to validate epsilon < threshold

        Raises:
            ValueError: If epsilon >= threshold and validation enabled
        """
        self.mode = mode
        threshold = get_epsilon_threshold(mode)

        if validate_epsilon and epsilon >= threshold:
            raise ValueError(
                f"epsilon ({epsilon}) must be < threshold ({threshold:.6f}) "
                f"for mode {mode.value} to guarantee positive definiteness"
            )

        self.R = R
        self.epsilon = epsilon
        self.n_dims = LANGUES_DIMENSIONS
        self._epsilon_threshold = threshold

        # Baseline metric G_0
        self.G_0 = create_baseline_metric(R, mode)
        self._G_0_diag = np.diag(self.G_0)

        # Pre-compute coupling matrices
        self._coupling_matrices = [
            create_coupling_matrix(k, R, epsilon, mode, self._G_0_diag)
            for k in range(self.n_dims)
        ]

    @property
    def epsilon_threshold(self) -> float:
        """Get the rigorous epsilon threshold for this mode."""
        return self._epsilon_threshold

    def compute_weight_operator(self, r: np.ndarray) -> np.ndarray:
        """
        Compute the langues weight operator Λ(r).

        Λ(r) = exp(Σ_{k=0}^{5} r_k * A_k)

        Uses scipy.linalg.expm for matrix exponential.

        Args:
            r: Langue parameter vector (6 elements in [0, 1])

        Returns:
            6x6 weight operator matrix Λ(r)
        """
        from scipy.linalg import expm

        r = np.asarray(r, dtype=np.float64)
        if len(r) != self.n_dims:
            raise ValueError(f"r must have {self.n_dims} elements, got {len(r)}")

        # Clamp to [0, 1]
        r = np.clip(r, 0.0, 1.0)

        # Sum weighted coupling matrices
        M = np.zeros((self.n_dims, self.n_dims), dtype=np.float64)
        for k in range(self.n_dims):
            M += r[k] * self._coupling_matrices[k]

        # Matrix exponential
        return expm(M)

    def compute_metric(self, r: np.ndarray) -> np.ndarray:
        """
        Compute the langues-modified metric tensor G_L(r).

        G_L(r) = Λ(r)^T * G_0 * Λ(r)

        Args:
            r: Langue parameter vector (6 elements in [0, 1])

        Returns:
            6x6 metric tensor G_L(r)
        """
        Lambda = self.compute_weight_operator(r)
        return Lambda.T @ self.G_0 @ Lambda

    def compute_distance(
        self,
        x: np.ndarray,
        y: np.ndarray,
        r: np.ndarray
    ) -> float:
        """
        Compute the langues-weighted distance between two points.

        d_L(x, y; r) = sqrt((x - y)^T * G_L(r) * (x - y))

        Args:
            x: First point (6D vector)
            y: Second point (6D vector)
            r: Langue parameter vector

        Returns:
            Langues-weighted distance
        """
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)

        G_L = self.compute_metric(r)
        diff = x - y

        return float(np.sqrt(diff.T @ G_L @ diff))

    def validate_positive_definite(
        self,
        r: np.ndarray,
        eps: float = 1e-10
    ) -> Tuple[bool, dict]:
        """
        Validate that G_L(r) is positive definite.

        A matrix is positive definite if all eigenvalues are positive.

        Args:
            r: Langue parameter vector
            eps: Minimum eigenvalue threshold

        Returns:
            Tuple of (is_positive_definite, details)
        """
        G_L = self.compute_metric(r)
        eigenvalues = np.linalg.eigvalsh(G_L)

        min_eigenvalue = float(np.min(eigenvalues))
        max_eigenvalue = float(np.max(eigenvalues))
        condition_number = max_eigenvalue / max(min_eigenvalue, eps)

        is_pd = min_eigenvalue > eps

        return is_pd, {
            "eigenvalues": eigenvalues.tolist(),
            "min_eigenvalue": min_eigenvalue,
            "max_eigenvalue": max_eigenvalue,
            "condition_number": condition_number,
            "is_positive_definite": is_pd,
            "epsilon": self.epsilon,
            "r": r.tolist() if hasattr(r, 'tolist') else list(r),
        }

    def validate_stability(
        self,
        n_trials: int = 100,
        seed: Optional[int] = None
    ) -> dict:
        """
        Run numerical stability validation across random r vectors.

        Tests n_trials random r ∈ [0,1]^6 and reports statistics.

        Args:
            n_trials: Number of random trials
            seed: Random seed for reproducibility

        Returns:
            Dictionary with validation statistics
        """
        if seed is not None:
            np.random.seed(seed)

        min_eigenvalues = []
        max_eigenvalues = []
        condition_numbers = []
        all_pd = True

        for _ in range(n_trials):
            r = np.random.uniform(0, 1, self.n_dims)
            is_pd, details = self.validate_positive_definite(r)

            min_eigenvalues.append(details["min_eigenvalue"])
            max_eigenvalues.append(details["max_eigenvalue"])
            condition_numbers.append(details["condition_number"])

            if not is_pd:
                all_pd = False

        return {
            "n_trials": n_trials,
            "epsilon": self.epsilon,
            "all_positive_definite": all_pd,
            "min_eigenvalue_worst": float(np.min(min_eigenvalues)),
            "min_eigenvalue_best": float(np.max(min_eigenvalues)),
            "max_eigenvalue_worst": float(np.max(max_eigenvalues)),
            "condition_number_worst": float(np.max(condition_numbers)),
            "condition_number_mean": float(np.mean(condition_numbers)),
        }

    def get_coupling_matrices(self) -> List[np.ndarray]:
        """Return the pre-computed coupling matrices A_k."""
        return [A.copy() for A in self._coupling_matrices]


# =============================================================================
# FRACTAL DIMENSION ANALYZER (FRACTIONAL-DIMENSIONAL GEOMETRY)
# =============================================================================

class FractalDimensionAnalyzer:
    """
    Fractal-Dimensional Analysis for the Langues Metric System.

    When fractional-dimensional weighting is introduced via the Langues Metric's
    fractional-whole coupling (ν_k), we enter fractal-dimensional geometry where
    effective dimension is non-integer.

    Standard fractal dimension:
        D_f = log N(ε) / log(1/ε)

    For the Langues system, fractional couplings induce non-integer scaling laws:
        D_f(r) ~ ∂ ln det G_L^(ν)(r) / ∂ ln ε

    Hausdorff dimension of recursive metric attractor:
        Σ_{k=1}^{6} α_k^{D_H} = 1, where α_k = R^{ν_k r_k}

    Key Insight:
    The Langues Metric is effectively a **continuous fractal generator** embedded
    in six dimensions. Each choice of fractional-whole couplings (ν_k) defines a
    different fractal manifold.

    Number of unique fractal topologies: M^{N_ν} = 4^6 = 4096 (before continuous
    parameter variation). With real-valued ν_k ∈ [0,3], uncountably infinite.
    """

    def __init__(
        self,
        R: float = PHI,
        epsilon: float = DEFAULT_EPSILON,
        mode: CouplingMode = CouplingMode.NORMALIZED,
        fractional_orders: Optional[np.ndarray] = None
    ):
        """
        Initialize Fractal Dimension Analyzer.

        Args:
            R: Coordination constant (default: golden ratio φ)
            epsilon: Base coupling strength
            mode: Coupling mode for underlying metric
            fractional_orders: ν_k fractional orders (default: linspace(0.5, 3.0, 6))
        """
        self.R = R
        self.epsilon = epsilon
        self.mode = mode
        self.n_dims = LANGUES_DIMENSIONS

        # Fractional orders ν_k defining self-similarity exponents
        if fractional_orders is None:
            self.nu = np.linspace(0.5, 3.0, self.n_dims)
        else:
            self.nu = np.asarray(fractional_orders, dtype=np.float64)
            if len(self.nu) != self.n_dims:
                raise ValueError(f"fractional_orders must have {self.n_dims} elements")

        # Underlying metric tensor
        self._metric_tensor = LanguesMetricTensor(R, epsilon, mode, validate_epsilon=False)

    def compute_local_fractal_dimension(
        self,
        r: np.ndarray,
        delta_epsilon: float = 1e-4
    ) -> float:
        """
        Compute local fractal dimension at a point r.

        D_f(r) ≈ ∂ ln det G_L(r) / ∂ ln ε

        Uses finite difference approximation.

        Args:
            r: Langue parameter vector (6D)
            delta_epsilon: Step size for numerical differentiation

        Returns:
            Local fractal dimension D_f(r)
        """
        r = np.asarray(r, dtype=np.float64)

        # Create tensors at ε and ε + δε
        eps_lo = max(self.epsilon - delta_epsilon, 1e-6)
        eps_hi = self.epsilon + delta_epsilon

        tensor_lo = LanguesMetricTensor(
            self.R, eps_lo, self.mode, validate_epsilon=False
        )
        tensor_hi = LanguesMetricTensor(
            self.R, eps_hi, self.mode, validate_epsilon=False
        )

        # Compute determinants
        G_lo = tensor_lo.compute_metric(r)
        G_hi = tensor_hi.compute_metric(r)

        det_lo = np.linalg.det(G_lo)
        det_hi = np.linalg.det(G_hi)

        # Avoid log of non-positive
        if det_lo <= 0 or det_hi <= 0:
            return float('nan')

        # D_f ≈ d(ln det G) / d(ln ε)
        d_ln_det = np.log(det_hi) - np.log(det_lo)
        d_ln_eps = np.log(eps_hi) - np.log(eps_lo)

        return d_ln_det / d_ln_eps

    def compute_fractal_dimension_field(
        self,
        n_samples: int = 100,
        seed: Optional[int] = None
    ) -> dict:
        """
        Compute fractal dimension field over random samples.

        Args:
            n_samples: Number of random r vectors to sample
            seed: Random seed for reproducibility

        Returns:
            Dictionary with field statistics
        """
        if seed is not None:
            np.random.seed(seed)

        dimensions = []
        r_vectors = []

        for _ in range(n_samples):
            r = np.random.uniform(0, 1, self.n_dims)
            D_f = self.compute_local_fractal_dimension(r)
            if not np.isnan(D_f):
                dimensions.append(D_f)
                r_vectors.append(r.tolist())

        dimensions = np.array(dimensions)

        return {
            "n_samples": len(dimensions),
            "D_f_mean": float(np.mean(dimensions)) if len(dimensions) > 0 else 0,
            "D_f_std": float(np.std(dimensions)) if len(dimensions) > 0 else 0,
            "D_f_min": float(np.min(dimensions)) if len(dimensions) > 0 else 0,
            "D_f_max": float(np.max(dimensions)) if len(dimensions) > 0 else 0,
            "fractional_orders": self.nu.tolist(),
        }

    def iterate_metric_recursively(
        self,
        r: np.ndarray,
        n_iterations: int = 100,
        contraction_factor: float = 0.99
    ) -> Tuple[np.ndarray, List[float]]:
        """
        Iterate the metric recursively to find fractal attractor.

        G_{n+1} = α * Λ(r)^T * G_n * Λ(r)

        Where α < 1 is a contraction factor ensuring convergence.

        Args:
            r: Langue parameter vector
            n_iterations: Number of iterations
            contraction_factor: α in (0, 1) for contraction

        Returns:
            Tuple of (final metric G_∞, determinant history)
        """
        r = np.asarray(r, dtype=np.float64)
        Lambda = self._metric_tensor.compute_weight_operator(r)

        G_n = self._metric_tensor.G_0.copy()
        det_history = [float(np.linalg.det(G_n))]

        for _ in range(n_iterations):
            G_n = contraction_factor * Lambda.T @ G_n @ Lambda
            det_history.append(float(np.linalg.det(G_n)))

            # Check for convergence
            if det_history[-1] < 1e-100:
                break

        return G_n, det_history

    def compute_hausdorff_dimension(
        self,
        r: np.ndarray,
        tol: float = 1e-8,
        max_iter: int = 100
    ) -> float:
        """
        Compute Hausdorff dimension D_H of the fractal attractor.

        Solves: Σ_{k=1}^{6} α_k^{D_H} = 1

        Where α_k = R^{ν_k * r_k} are the scaling factors.

        Uses bisection method on D_H ∈ [0, ∞).

        Args:
            r: Langue parameter vector defining scaling
            tol: Convergence tolerance
            max_iter: Maximum iterations

        Returns:
            Hausdorff dimension D_H
        """
        r = np.asarray(r, dtype=np.float64)
        r = np.clip(r, 0.0, 1.0)

        # Scaling factors: α_k = R^{ν_k * r_k}
        alpha = self.R ** (self.nu * r)

        # Special case: if all α_k = 1, D_H is undefined (no scaling)
        if np.allclose(alpha, 1.0):
            return float(self.n_dims)

        # Equation to solve: f(D) = Σ α_k^D - 1 = 0
        def f(D):
            return np.sum(alpha ** D) - 1.0

        # Bisection: f(D) decreases monotonically as D increases (for α < 1)
        # For α > 1, D_H can be negative; for α < 1, D_H is positive

        # Find bounds
        D_lo, D_hi = -10.0, 100.0

        # Check if solution exists
        f_lo, f_hi = f(D_lo), f(D_hi)
        if f_lo * f_hi > 0:
            # No sign change - return estimate based on sum
            return float(np.log(self.n_dims) / np.mean(np.log(alpha) + 1e-10))

        # Bisection
        for _ in range(max_iter):
            D_mid = (D_lo + D_hi) / 2.0
            f_mid = f(D_mid)

            if abs(f_mid) < tol:
                return float(D_mid)

            if f_mid * f_lo < 0:
                D_hi = D_mid
            else:
                D_lo = D_mid

        return float((D_lo + D_hi) / 2.0)

    def compute_dimension_spectrum(
        self,
        axis_index: int,
        n_points: int = 50,
        other_r_values: Optional[np.ndarray] = None
    ) -> dict:
        """
        Compute fractal dimension spectrum along one langue axis.

        Varies r_k from 0 to 1 while holding other r values constant.

        Args:
            axis_index: Which axis to vary (0-5)
            n_points: Number of points along axis
            other_r_values: Fixed values for other axes (default: 0.5)

        Returns:
            Dictionary with spectrum data
        """
        if axis_index < 0 or axis_index >= self.n_dims:
            raise ValueError(f"axis_index must be in [0, {self.n_dims-1}]")

        if other_r_values is None:
            other_r_values = np.full(self.n_dims, 0.5)
        else:
            other_r_values = np.asarray(other_r_values, dtype=np.float64)

        r_axis = np.linspace(0, 1, n_points)
        D_f_values = []
        D_H_values = []

        for r_val in r_axis:
            r = other_r_values.copy()
            r[axis_index] = r_val

            D_f = self.compute_local_fractal_dimension(r)
            D_H = self.compute_hausdorff_dimension(r)

            D_f_values.append(D_f)
            D_H_values.append(D_H)

        return {
            "axis_index": axis_index,
            "axis_name": f"r_{axis_index}",
            "fractional_order": float(self.nu[axis_index]),
            "r_values": r_axis.tolist(),
            "D_f_spectrum": D_f_values,
            "D_H_spectrum": D_H_values,
            "other_r_values": other_r_values.tolist(),
        }

    def compute_full_spectrum(self, n_points: int = 30) -> dict:
        """
        Compute fractal dimension spectrum for all 6 langue axes.

        Args:
            n_points: Number of points per axis

        Returns:
            Dictionary with spectra for all axes
        """
        spectra = {}
        for k in range(self.n_dims):
            spectra[f"axis_{k}"] = self.compute_dimension_spectrum(k, n_points)

        return {
            "n_axes": self.n_dims,
            "n_points_per_axis": n_points,
            "fractional_orders": self.nu.tolist(),
            "spectra": spectra,
        }

    def langues_fractal_map(
        self,
        x: np.ndarray,
        r: np.ndarray
    ) -> np.ndarray:
        """
        Apply the Langues fractal map to a point.

        f(x; r) = tanh(φ^{r·ν} ⊙ sin(π·x))

        This is a bounded, continuous map with fractal attractor.

        Args:
            x: Input point (can be 1D or nD)
            r: Langue parameter vector

        Returns:
            Mapped point
        """
        x = np.asarray(x, dtype=np.float64)
        r = np.asarray(r, dtype=np.float64)

        # Compute scaling: φ^{ν_k * r_k}
        scaling = self.R ** (self.nu * r)

        # Apply fractal map with broadcasting
        if x.ndim == 1 and len(x) == self.n_dims:
            return np.tanh(scaling * np.sin(np.pi * x))
        else:
            # For arbitrary dimension, use mean scaling
            mean_scaling = np.mean(scaling)
            return np.tanh(mean_scaling * np.sin(np.pi * x))

    def generate_fractal_attractor(
        self,
        n_iterations: int = 1000,
        n_points: int = 100,
        seed: Optional[int] = None
    ) -> np.ndarray:
        """
        Generate points on the Langues fractal attractor via iteration.

        Iterates the fractal map: x_{n+1} = f(x_n; r_random)

        Args:
            n_iterations: Number of iterations per point
            n_points: Number of starting points
            seed: Random seed

        Returns:
            Array of attractor points (n_points × n_dims)
        """
        if seed is not None:
            np.random.seed(seed)

        attractor_points = []

        for _ in range(n_points):
            # Random initial point
            x = np.random.uniform(-1, 1, self.n_dims)

            # Iterate
            for _ in range(n_iterations):
                r = np.random.uniform(0, 1, self.n_dims)
                x = self.langues_fractal_map(x, r)

            attractor_points.append(x)

        return np.array(attractor_points)

    def estimate_box_counting_dimension(
        self,
        points: np.ndarray,
        n_scales: int = 10
    ) -> Tuple[float, dict]:
        """
        Estimate fractal dimension via box-counting method.

        D_f = lim_{ε→0} log N(ε) / log(1/ε)

        Args:
            points: Point cloud (n_points × n_dims)
            n_scales: Number of box scales to use

        Returns:
            Tuple of (estimated dimension, fit details)
        """
        points = np.asarray(points, dtype=np.float64)

        # Normalize to [0, 1]
        p_min = points.min(axis=0)
        p_max = points.max(axis=0)
        p_range = p_max - p_min
        p_range[p_range < 1e-10] = 1.0
        points_norm = (points - p_min) / p_range

        # Box sizes (log-spaced)
        epsilons = np.logspace(-2, 0, n_scales)
        N_boxes = []

        for eps in epsilons:
            # Count occupied boxes
            grid_indices = (points_norm / eps).astype(int)
            unique_boxes = set(tuple(idx) for idx in grid_indices)
            N_boxes.append(len(unique_boxes))

        N_boxes = np.array(N_boxes)
        log_eps_inv = np.log(1.0 / epsilons)
        log_N = np.log(N_boxes + 1)  # +1 to avoid log(0)

        # Linear regression: log N = D_f * log(1/ε) + c
        # D_f = slope
        slope, intercept = np.polyfit(log_eps_inv, log_N, 1)

        return float(slope), {
            "epsilons": epsilons.tolist(),
            "N_boxes": N_boxes.tolist(),
            "log_eps_inv": log_eps_inv.tolist(),
            "log_N": log_N.tolist(),
            "slope": float(slope),
            "intercept": float(intercept),
        }


# =============================================================================
# HYPER-TORUS MANIFOLD (N-DIMENSIONAL WITH SIGNED DIRECTION VECTORS)
# =============================================================================

class DimensionMode(Enum):
    """
    Dimension traversal modes for the Hyper-Torus.

    FORWARD (+1): Normal forward traversal in this dimension
    BACKWARD (-1): Reversed geodesic direction (asymmetric trust)
    FROZEN (0): Dimension locked - no movement allowed (security constraint)
    """
    FORWARD = 1
    BACKWARD = -1
    FROZEN = 0


class HyperTorusManifold:
    """
    N-Dimensional Hyper-Torus Memory with Signed Dimension Vectors.

    The 4D Hyper-Torus Memory is a Self-Correcting Geometric Ledger that maps
    informational interactions onto a continuous, curved Riemannian manifold.
    This implementation generalizes to n dimensions (T^n) with support for:

    1. SIGNED DIMENSIONS (D ∈ {-1, 0, +1}^n):
       - D_k = +1: Forward traversal (normal geodesic flow)
       - D_k = -1: Backward traversal (reversed, asymmetric trust)
       - D_k = 0: Frozen dimension (locked, creates hard constraint)

    2. NESTED TORUS STRUCTURE:
       For T^n, the Riemannian metric generalizes as:
       ds² = Σᵢ gᵢᵢ(θ) dθᵢ²

       where gᵢᵢ depends on the "depth" of the torus nesting:
       - Outermost dimension: g₀₀ = R₀²
       - Inner dimensions: gᵢᵢ = (Rᵢ + rᵢ cos θᵢ₋₁)²

    3. GEOMETRIC INTEGRITY ("The Snap"):
       A write is valid iff d_geo(P_prev, P_new) ≤ ε
       where ε is the Trust Threshold.

    4. DIRECTIONAL ASYMMETRY:
       When D_k = -1, movement in dimension k incurs a penalty factor,
       making it "harder to go back" in certain contexts (e.g., security).

    Key Insight:
    Logical consistency is modeled as geometric continuity. A truthful,
    coherent narrative traces a smooth geodesic. A contradiction manifests
    as a discontinuity—a "teleportation" that exceeds surface tension.

    Integration with Langues Metric:
    The 6 Sacred Tongues can be mapped to a 6-torus T^6, where each langue
    dimension has its own signed traversal mode, creating a rich space of
    valid semantic transitions.
    """

    def __init__(
        self,
        n_dims: int = 4,
        major_radii: Optional[np.ndarray] = None,
        minor_radius: float = 2.0,
        trust_threshold: float = 1.5,
        dimension_modes: Optional[np.ndarray] = None,
        asymmetry_penalty: float = 2.0
    ):
        """
        Initialize n-dimensional Hyper-Torus Manifold.

        Args:
            n_dims: Number of angular dimensions (default: 4 for 4D hyper-torus)
            major_radii: Array of major radii [R_0, R_1, ..., R_{n-2}]
                        (default: [10, 8, 6, 4, ...] geometric decay)
            minor_radius: Radius of the innermost tube (default: 2.0)
            trust_threshold: Maximum allowed geodesic distance ("The Snap" limit)
            dimension_modes: Signed dimension vector D ∈ {-1, 0, +1}^n
                           (default: all +1, forward traversal)
            asymmetry_penalty: Multiplier for backward traversal cost (default: 2.0)
        """
        if n_dims < 2:
            raise ValueError("n_dims must be >= 2 for a torus")

        self.n_dims = n_dims
        self.minor_radius = minor_radius
        self.trust_threshold = trust_threshold
        self.asymmetry_penalty = asymmetry_penalty

        # Major radii: geometric decay from outermost to innermost
        if major_radii is None:
            self.major_radii = np.array([10.0 - 2*i for i in range(n_dims - 1)])
            # Ensure all radii are positive
            self.major_radii = np.maximum(self.major_radii, minor_radius + 0.5)
        else:
            self.major_radii = np.asarray(major_radii, dtype=np.float64)
            if len(self.major_radii) != n_dims - 1:
                raise ValueError(f"major_radii must have {n_dims - 1} elements")

        # Dimension modes: D ∈ {-1, 0, +1}^n
        if dimension_modes is None:
            self.D = np.ones(n_dims, dtype=np.int8)  # All forward by default
        else:
            self.D = np.asarray(dimension_modes, dtype=np.int8)
            if len(self.D) != n_dims:
                raise ValueError(f"dimension_modes must have {n_dims} elements")
            # Validate values
            if not np.all(np.isin(self.D, [-1, 0, 1])):
                raise ValueError("dimension_modes must contain only -1, 0, or +1")

        # Count active dimensions (non-frozen)
        self.n_active = np.sum(self.D != 0)

    def set_dimension_mode(self, dim_index: int, mode: DimensionMode) -> None:
        """
        Set the traversal mode for a specific dimension.

        Args:
            dim_index: Which dimension to modify (0 to n_dims-1)
            mode: DimensionMode (FORWARD, BACKWARD, or FROZEN)
        """
        if dim_index < 0 or dim_index >= self.n_dims:
            raise ValueError(f"dim_index must be in [0, {self.n_dims - 1}]")
        self.D[dim_index] = mode.value
        self.n_active = np.sum(self.D != 0)

    def freeze_dimension(self, dim_index: int) -> None:
        """Freeze a dimension (no movement allowed)."""
        self.set_dimension_mode(dim_index, DimensionMode.FROZEN)

    def unfreeze_dimension(self, dim_index: int, backward: bool = False) -> None:
        """Unfreeze a dimension."""
        mode = DimensionMode.BACKWARD if backward else DimensionMode.FORWARD
        self.set_dimension_mode(dim_index, mode)

    def _stable_hash_to_angle(self, data: str) -> float:
        """
        Deterministically map string data to an angle in [0, 2π).

        Uses SHA-256 for stability (Python's hash() is salted).
        """
        import hashlib
        hash_bytes = hashlib.sha256(data.encode('utf-8')).digest()[:8]
        hash_int = int.from_bytes(hash_bytes, 'big')
        # Normalize to [0, 1) then scale to [0, 2π)
        normalized = hash_int / (2**64)
        return normalized * 2 * np.pi

    def map_interaction(
        self,
        domain_contexts: List[str],
        sequence_data: str
    ) -> np.ndarray:
        """
        Map an interaction to n-dimensional angular coordinates.

        Args:
            domain_contexts: List of context strings for each domain dimension
                           (should have n_dims - 1 elements for domain angles)
            sequence_data: String for the sequence/time dimension

        Returns:
            Array of angles [θ_0, θ_1, ..., θ_{n-1}] in [0, 2π)^n
        """
        coordinates = np.zeros(self.n_dims, dtype=np.float64)

        # Map domain dimensions
        for i, ctx in enumerate(domain_contexts[:self.n_dims - 1]):
            coordinates[i] = self._stable_hash_to_angle(ctx)

        # Map sequence dimension (last dimension)
        coordinates[-1] = self._stable_hash_to_angle(sequence_data)

        return coordinates

    def _minimal_angle_delta(self, theta1: float, theta2: float) -> float:
        """
        Compute minimal angular difference respecting periodic boundaries.

        Minimal Image Convention for S^1:
        Δθ = min(|θ₂ - θ₁|, 2π - |θ₂ - θ₁|)
        """
        diff = np.abs(theta2 - theta1)
        return min(diff, 2 * np.pi - diff)

    def _signed_angle_delta(
        self,
        theta1: float,
        theta2: float,
        dim_mode: int
    ) -> Tuple[float, float]:
        """
        Compute signed angular difference with directional penalty.

        Returns:
            Tuple of (minimal_delta, effective_delta after directional scaling)
        """
        # Compute raw difference (signed)
        raw_diff = theta2 - theta1

        # Wrap to [-π, π]
        while raw_diff > np.pi:
            raw_diff -= 2 * np.pi
        while raw_diff < -np.pi:
            raw_diff += 2 * np.pi

        minimal_delta = np.abs(raw_diff)

        # Apply directional penalty based on dimension mode
        if dim_mode == 0:  # FROZEN
            # Frozen dimension: any movement is forbidden (infinite penalty)
            effective_delta = np.inf if minimal_delta > 1e-10 else 0.0
        elif dim_mode == 1:  # FORWARD
            # Forward: no penalty for positive direction, penalty for negative
            if raw_diff >= 0:
                effective_delta = minimal_delta
            else:
                effective_delta = minimal_delta * self.asymmetry_penalty
        else:  # BACKWARD (dim_mode == -1)
            # Backward: penalty for positive direction
            if raw_diff <= 0:
                effective_delta = minimal_delta
            else:
                effective_delta = minimal_delta * self.asymmetry_penalty

        return minimal_delta, effective_delta

    def compute_metric_tensor(self, theta: np.ndarray) -> np.ndarray:
        """
        Compute the Riemannian metric tensor g_ij at point θ.

        For nested n-torus T^n, the metric is diagonal with:
        g_00 = R_0² (outermost)
        g_ii = (R_i + r_{i-1} cos θ_{i-1})² for i > 0

        The innermost dimension uses the minor radius.

        Args:
            theta: Angular coordinates [θ_0, ..., θ_{n-1}]

        Returns:
            n×n diagonal metric tensor
        """
        g = np.zeros((self.n_dims, self.n_dims), dtype=np.float64)

        # Outermost dimension
        g[0, 0] = self.major_radii[0] ** 2

        # Middle dimensions
        for i in range(1, self.n_dims - 1):
            # Effective radius depends on angle of previous dimension
            R_eff = self.major_radii[i] + self.major_radii[i-1] * np.cos(theta[i-1])
            g[i, i] = R_eff ** 2

        # Innermost dimension (uses minor radius)
        if self.n_dims > 1:
            R_eff = self.minor_radius + self.major_radii[-1] * np.cos(theta[-2])
            g[-1, -1] = R_eff ** 2

        return g

    def compute_geodesic_distance(
        self,
        p1: np.ndarray,
        p2: np.ndarray,
        apply_direction: bool = True
    ) -> Tuple[float, dict]:
        """
        Compute geodesic distance between two points on the hyper-torus.

        For local distances, uses the Riemannian line element:
        ds² = Σᵢ g_ii(θ̄) (Δθᵢ)²

        Args:
            p1: First point [θ_0, ..., θ_{n-1}]
            p2: Second point [θ_0, ..., θ_{n-1}]
            apply_direction: Whether to apply directional penalties

        Returns:
            Tuple of (distance, details dict)
        """
        p1 = np.asarray(p1, dtype=np.float64)
        p2 = np.asarray(p2, dtype=np.float64)

        if len(p1) != self.n_dims or len(p2) != self.n_dims:
            raise ValueError(f"Points must have {self.n_dims} dimensions")

        # Average point for metric evaluation
        theta_avg = (p1 + p2) / 2.0

        # Compute metric tensor at average point
        g = self.compute_metric_tensor(theta_avg)

        # Compute angular deltas with directional penalties
        deltas = np.zeros(self.n_dims)
        effective_deltas = np.zeros(self.n_dims)
        frozen_violation = False

        for i in range(self.n_dims):
            if apply_direction:
                delta, eff_delta = self._signed_angle_delta(p1[i], p2[i], self.D[i])
                if np.isinf(eff_delta):
                    frozen_violation = True
                deltas[i] = delta
                effective_deltas[i] = eff_delta
            else:
                deltas[i] = self._minimal_angle_delta(p1[i], p2[i])
                effective_deltas[i] = deltas[i]

        # Compute squared distance: ds² = Σ g_ii * dθ_i²
        if frozen_violation:
            distance = np.inf
        else:
            squared_dist = np.sum(np.diag(g) * effective_deltas**2)
            distance = np.sqrt(squared_dist)

        return distance, {
            "raw_deltas": deltas.tolist(),
            "effective_deltas": effective_deltas.tolist(),
            "metric_diagonal": np.diag(g).tolist(),
            "dimension_modes": self.D.tolist(),
            "frozen_violation": frozen_violation,
            "squared_distance": float(squared_dist) if not frozen_violation else np.inf,
        }

    def validate_write(
        self,
        previous_point: Optional[np.ndarray],
        new_point: np.ndarray
    ) -> dict:
        """
        The Snap Protocol: Validate geometric integrity of a write operation.

        A write is valid iff d_geo(P_prev, P_new) ≤ ε (trust threshold).

        Args:
            previous_point: Coordinates of last accepted fact (None for genesis)
            new_point: Proposed coordinates for new fact

        Returns:
            Validation result dict with status and metrics
        """
        new_point = np.asarray(new_point, dtype=np.float64)

        # Genesis block: always accept
        if previous_point is None:
            return {
                "status": "WRITE_SUCCESS",
                "is_genesis": True,
                "coordinates": new_point.tolist(),
                "distance": 0.0,
            }

        previous_point = np.asarray(previous_point, dtype=np.float64)

        # Compute geodesic distance
        distance, details = self.compute_geodesic_distance(previous_point, new_point)

        # Validate against trust threshold
        if distance <= self.trust_threshold:
            return {
                "status": "WRITE_SUCCESS",
                "is_genesis": False,
                "coordinates": new_point.tolist(),
                "distance": float(distance),
                "threshold": self.trust_threshold,
                "headroom": float(self.trust_threshold - distance),
                **details,
            }
        else:
            # THE SNAP: Geometric integrity violation
            return {
                "status": "WRITE_FAIL",
                "error": "GEOMETRIC_SNAP_DETECTED",
                "is_genesis": False,
                "divergence": float(distance) if not np.isinf(distance) else "INFINITY",
                "threshold": self.trust_threshold,
                "overshoot": float(distance - self.trust_threshold) if not np.isinf(distance) else "INFINITY",
                "frozen_violation": details.get("frozen_violation", False),
                **details,
            }

    def compute_manifold_tension(
        self,
        trajectory: List[np.ndarray]
    ) -> dict:
        """
        Compute cumulative tension along a trajectory on the manifold.

        High tension indicates logical leaps or potential inconsistencies.

        Args:
            trajectory: List of coordinate points

        Returns:
            Tension analysis dict
        """
        if len(trajectory) < 2:
            return {"total_tension": 0.0, "segments": [], "snap_count": 0}

        tensions = []
        snap_count = 0

        for i in range(1, len(trajectory)):
            dist, _ = self.compute_geodesic_distance(trajectory[i-1], trajectory[i])
            tensions.append(dist)
            if dist > self.trust_threshold:
                snap_count += 1

        return {
            "total_tension": float(np.sum(tensions)),
            "mean_tension": float(np.mean(tensions)),
            "max_tension": float(np.max(tensions)),
            "min_tension": float(np.min(tensions)),
            "segments": [float(t) for t in tensions],
            "snap_count": snap_count,
            "integrity_ratio": 1.0 - (snap_count / len(tensions)),
        }

    def compute_hausdorff_dimension_torus(self) -> float:
        """
        Compute the Hausdorff dimension of the n-torus.

        For T^n, the Hausdorff dimension equals the topological dimension n
        (tori are smooth manifolds).

        Returns:
            Hausdorff dimension (equals n_dims for standard torus)
        """
        return float(self.n_dims)

    def get_curvature_bounds(self) -> dict:
        """
        Get Gaussian curvature bounds for the hyper-torus.

        For a standard 2-torus:
        - Outer rim (θ=0): K = cos(θ) / (r(R + r cos θ)) = 1/(r(R+r)) > 0
        - Inner core (θ=π): K = -1/(r(R-r)) < 0

        Returns:
            Curvature bounds dict
        """
        # For 2-torus section (simplified analysis)
        R = self.major_radii[0] if len(self.major_radii) > 0 else 10.0
        r = self.minor_radius

        K_max = 1.0 / (r * (R + r))  # Outer rim
        K_min = -1.0 / (r * (R - r)) if R > r else -np.inf  # Inner core

        return {
            "K_max": float(K_max),
            "K_min": float(K_min),
            "R_major": float(R),
            "r_minor": float(r),
            "outer_rim_tension_multiplier": float((R + r) / (R - r)) if R > r else np.inf,
        }

    def integrate_with_langues(
        self,
        langues_tensor: "LanguesMetricTensor",
        langues_r: np.ndarray
    ) -> np.ndarray:
        """
        Integrate Langues Metric weights into the torus metric.

        The 6 Langues dimensions can modulate the first 6 torus dimensions,
        creating a coupled Langues-Torus manifold.

        Args:
            langues_tensor: LanguesMetricTensor instance
            langues_r: Langue parameter vector (6D)

        Returns:
            Modified metric tensor incorporating Langues weights
        """
        if self.n_dims < 6:
            raise ValueError("Need at least 6 dimensions to integrate Langues")

        # Get Langues metric
        G_L = langues_tensor.compute_metric(langues_r)

        # Get base torus metric at origin
        theta_origin = np.zeros(self.n_dims)
        g_torus = self.compute_metric_tensor(theta_origin)

        # Couple the metrics: modulate first 6 torus dimensions with Langues
        # Using Hadamard product for coupling
        for i in range(6):
            g_torus[i, i] *= G_L[i, i]

        return g_torus


def compute_langues_metric_distance(
    x: np.ndarray,
    y: np.ndarray,
    r: np.ndarray,
    epsilon: float = DEFAULT_EPSILON
) -> float:
    """
    Convenience function to compute langues-weighted distance.

    Args:
        x: First point (6D vector)
        y: Second point (6D vector)
        r: Langue parameter vector (6 elements in [0, 1])
        epsilon: Coupling strength

    Returns:
        Langues-weighted distance d_L(x, y; r)
    """
    tensor = LanguesMetricTensor(epsilon=epsilon, validate_epsilon=False)
    return tensor.compute_distance(x, y, r)


def validate_langues_metric_stability(
    epsilon_values: List[float] = None,
    n_trials: int = 100,
    seed: int = 42
) -> dict:
    """
    Validate langues metric stability across multiple epsilon values.

    Args:
        epsilon_values: List of epsilon values to test
        n_trials: Number of random trials per epsilon
        seed: Random seed

    Returns:
        Dictionary with results per epsilon
    """
    if epsilon_values is None:
        epsilon_values = [0.01, 0.05, 0.10]

    results = {}
    for eps in epsilon_values:
        tensor = LanguesMetricTensor(epsilon=eps, validate_epsilon=False)
        results[eps] = tensor.validate_stability(n_trials=n_trials, seed=seed)

    return results


# =============================================================================
# TEST VECTORS (FROM SPECIFICATION)
# =============================================================================

TEST_VECTORS = [
    # (d*, expected_tanh(beta*d*), expected_H) with alpha=10, beta=0.5
    (0.0, 0.0000, 1.0000),
    (0.5, 0.2449, 3.4490),
    (1.0, 0.4621, 5.6210),
    (2.0, 0.7616, 8.6160),
    (3.0, 0.9051, 10.0510),
    (4.0, 0.9640, 10.6400),
    (5.0, 0.9866, 10.8660),
    (10.0, 0.9999, 10.9990),
]


def verify_test_vectors(tolerance: float = 0.01) -> List[Tuple[bool, str]]:
    """
    Verify implementation against specification test vectors.

    Args:
        tolerance: Maximum allowed deviation

    Returns:
        List of (passed, message) tuples
    """
    results = []
    scaling_law = HarmonicScalingLaw(
        alpha=10.0,
        beta=0.5,
        require_pq_binding=False
    )

    for d_star, expected_tanh, expected_H in TEST_VECTORS:
        computed_H = scaling_law.compute(d_star, context_commitment=None)
        computed_tanh = math.tanh(0.5 * d_star)

        tanh_ok = abs(computed_tanh - expected_tanh) < tolerance
        H_ok = abs(computed_H - expected_H) < tolerance

        passed = tanh_ok and H_ok
        msg = (
            f"d*={d_star}: tanh={computed_tanh:.4f} (expected {expected_tanh:.4f}), "
            f"H={computed_H:.4f} (expected {expected_H:.4f}) - "
            f"{'PASS' if passed else 'FAIL'}"
        )
        results.append((passed, msg))

    return results


# =============================================================================
# GRAND UNIFIED SYMPHONIC CIPHER FORMULA (Ω)
# =============================================================================

class GrandUnifiedSymphonicCipher:
    """
    The Grand Unified Symphonic Cipher Formula (GUSCF).

    Unifies all four pillars of the Symphonic Cipher into a single scalar:

        Ω(θ, r; D) = H(d_T, R) · (det G_Ω)^{1/(2n)} · φ^{D_f/n}

    Where:
        - H(d_T, R) = 1 + α·tanh(β·d_T)  [Harmonic Scaling Law]
        - G_Ω = G_T ⊙ G_L               [Coupled Torus-Langues Metric]
        - D_f = fractal dimension        [Complexity Measure]
        - φ = golden ratio               [Coordination Constant]
        - n = number of dimensions       [Torus dimensionality]

    The formula captures:
        1. **Risk Amplification** via H - bounded, monotonic risk scaling
        2. **Linguistic Weighting** via G_L - 6D Langues metric tensor
        3. **Geometric Integrity** via G_T - hyper-torus manifold structure
        4. **Complexity Signature** via D_f - fractal dimensional fingerprint

    Physical Interpretation:
        Ω measures the "symphonic coherence" of a state in cipher space.
        - Low Ω (→1): Harmonic, trusted, low-dimensional
        - High Ω (→∞): Dissonant, distant, high-complexity

    Alternative Forms:

    1. Action Integral (for trajectories):
        S[γ] = ∫_γ Ω(θ(t), r; D) dt

    2. Logarithmic Form (additive):
        ln Ω = ln H + (1/2n) ln det G_Ω + (D_f/n) ln φ

    3. Partition Function (statistical):
        Z = Σ_states exp(-β·Ω)

    4. Tensor Form (6D matrix):
        Ω_ij = H · (G_T ⊙ G_L)_ij · φ^{D_f/n}
    """

    def __init__(
        self,
        n_dims: int = 6,
        alpha: float = DEFAULT_ALPHA,
        beta: float = DEFAULT_BETA,
        epsilon: float = DEFAULT_EPSILON,
        dimension_modes: np.ndarray = None,
        coupling_mode: CouplingMode = CouplingMode.NORMALIZED,
    ):
        """
        Initialize the Grand Unified Symphonic Cipher.

        Args:
            n_dims: Number of dimensions (must be >= 6 for Langues integration)
            alpha: Harmonic scaling maximum amplification
            beta: Harmonic scaling growth rate
            epsilon: Langues metric coupling strength
            dimension_modes: Signed dimension vector D ∈ {-1, 0, +1}^n
            coupling_mode: Langues metric coupling mode
        """
        if n_dims < 6:
            raise ValueError("Grand Unified formula requires n_dims >= 6 for Langues integration")

        self.n_dims = n_dims
        self.alpha = alpha
        self.beta = beta
        self.epsilon = epsilon
        self.phi = PHI

        # Initialize all four pillars
        self.harmonic_law = HarmonicScalingLaw(
            alpha=alpha,
            beta=beta,
            require_pq_binding=False
        )

        self.langues_metric = LanguesMetricTensor(
            epsilon=epsilon,
            mode=coupling_mode,
            validate_epsilon=False
        )
        # Store the coupling mode for inspection
        self.langues_metric.coupling_mode = coupling_mode

        if dimension_modes is None:
            dimension_modes = np.ones(n_dims, dtype=int)  # All FORWARD

        self.hyper_torus = HyperTorusManifold(
            n_dims=n_dims,
            dimension_modes=dimension_modes
        )

        self.fractal_analyzer = FractalDimensionAnalyzer(
            epsilon=epsilon
        )

    def compute_omega(
        self,
        theta: np.ndarray,
        r: np.ndarray,
        theta_ref: np.ndarray = None,
    ) -> float:
        """
        Compute the Grand Unified Symphonic Cipher scalar Ω.

            Ω(θ, r; D) = H(d_T, R) · (det G_Ω)^{1/(2n)} · φ^{D_f/n}

        Args:
            theta: Angular coordinates on the hyper-torus (n_dims)
            r: Langues parameter vector (6D, elements in [0, 1])
            theta_ref: Reference point for distance (default: origin)

        Returns:
            Ω scalar value (>= 1)
        """
        if theta_ref is None:
            theta_ref = np.zeros(self.n_dims)

        # 1. Compute geodesic distance on hyper-torus
        d_T, _ = self.hyper_torus.compute_geodesic_distance(theta_ref, theta)

        # Handle infinite distance (frozen dimension violation)
        if np.isinf(d_T):
            return np.inf

        # 2. Compute Harmonic scaling: H(d_T, R)
        H = self.harmonic_law.compute(d_T)

        # 3. Compute coupled metric G_Ω = G_T ⊙ G_L
        G_T = self.hyper_torus.compute_metric_tensor(theta)
        G_L = self.langues_metric.compute_metric(r)

        # Hadamard coupling for first 6 dimensions
        G_omega = G_T.copy()
        for i in range(6):
            G_omega[i, i] *= G_L[i, i]

        # 4. Compute det(G_Ω)^{1/(2n)} - the "volume element" factor
        det_G_omega = np.linalg.det(G_omega)
        if det_G_omega <= 0:
            det_factor = 1.0  # Degenerate case
        else:
            det_factor = det_G_omega ** (1.0 / (2 * self.n_dims))

        # 5. Compute fractal dimension D_f
        D_f = self.fractal_analyzer.compute_local_fractal_dimension(r)

        # 6. Compute complexity factor: φ^{D_f/n}
        complexity_factor = self.phi ** (D_f / self.n_dims)

        # 7. Grand Unified Formula: Ω = H · det_factor · complexity_factor
        omega = H * det_factor * complexity_factor

        return float(omega)

    def compute_omega_tensor(
        self,
        theta: np.ndarray,
        r: np.ndarray,
    ) -> np.ndarray:
        """
        Compute the tensorial form of Ω.

            Ω_ij = H · (G_T ⊙ G_L)_ij · φ^{D_f/n}

        Args:
            theta: Angular coordinates on the hyper-torus
            r: Langues parameter vector (6D)

        Returns:
            Ω tensor (n_dims × n_dims matrix)
        """
        # Get scalar factors
        d_T, _ = self.hyper_torus.compute_geodesic_distance(np.zeros(self.n_dims), theta)
        H = self.harmonic_law.compute(d_T) if not np.isinf(d_T) else np.inf
        D_f = self.fractal_analyzer.compute_local_fractal_dimension(r)
        complexity = self.phi ** (D_f / self.n_dims)

        # Get coupled metric
        G_T = self.hyper_torus.compute_metric_tensor(theta)
        G_L = self.langues_metric.compute_metric(r)

        # Hadamard coupling
        G_omega = G_T.copy()
        for i in range(min(6, self.n_dims)):
            G_omega[i, i] *= G_L[i, i]

        # Tensor form
        Omega_tensor = H * complexity * G_omega

        return Omega_tensor

    def compute_log_omega(
        self,
        theta: np.ndarray,
        r: np.ndarray,
        theta_ref: np.ndarray = None,
    ) -> dict:
        """
        Compute the logarithmic (additive) form of Ω.

            ln Ω = ln H + (1/2n) ln det G_Ω + (D_f/n) ln φ

        Returns decomposed contributions for analysis.

        Args:
            theta: Angular coordinates on the hyper-torus
            r: Langues parameter vector (6D)
            theta_ref: Reference point for distance

        Returns:
            Dict with log components and total
        """
        if theta_ref is None:
            theta_ref = np.zeros(self.n_dims)

        # Components
        d_T, _ = self.hyper_torus.compute_geodesic_distance(theta_ref, theta)

        if np.isinf(d_T):
            return {
                "log_H": np.inf,
                "log_det_factor": 0.0,
                "log_complexity": 0.0,
                "log_omega": np.inf,
                "omega": np.inf,
            }

        H = self.harmonic_law.compute(d_T)
        log_H = np.log(H)

        # Coupled metric determinant
        G_T = self.hyper_torus.compute_metric_tensor(theta)
        G_L = self.langues_metric.compute_metric(r)
        G_omega = G_T.copy()
        for i in range(6):
            G_omega[i, i] *= G_L[i, i]
        det_G = np.linalg.det(G_omega)
        log_det_factor = np.log(det_G) / (2 * self.n_dims) if det_G > 0 else 0.0

        # Fractal complexity
        D_f = self.fractal_analyzer.compute_local_fractal_dimension(r)
        log_complexity = (D_f / self.n_dims) * np.log(self.phi)

        log_omega = log_H + log_det_factor + log_complexity

        return {
            "log_H": float(log_H),
            "log_det_factor": float(log_det_factor),
            "log_complexity": float(log_complexity),
            "log_omega": float(log_omega),
            "omega": float(np.exp(log_omega)),
            "contributions": {
                "harmonic_pct": float(log_H / log_omega * 100) if log_omega != 0 else 0,
                "geometry_pct": float(log_det_factor / log_omega * 100) if log_omega != 0 else 0,
                "complexity_pct": float(log_complexity / log_omega * 100) if log_omega != 0 else 0,
            }
        }

    def compute_action_integral(
        self,
        trajectory: List[np.ndarray],
        r: np.ndarray,
    ) -> float:
        """
        Compute the Symphonic Action integral along a trajectory.

            S[γ] = ∫_γ Ω(θ(t), r; D) dt ≈ Σ_i Ω(θ_i, r) · Δt

        Args:
            trajectory: List of angular coordinate points
            r: Langues parameter vector (constant along trajectory)

        Returns:
            Action integral S
        """
        if len(trajectory) < 2:
            return 0.0

        action = 0.0
        for i in range(1, len(trajectory)):
            theta = trajectory[i]
            theta_prev = trajectory[i - 1]

            # Compute Ω at current point
            omega = self.compute_omega(theta, r, theta_ref=theta_prev)

            if np.isinf(omega):
                return np.inf

            # Approximate dt as 1 (uniform parameter)
            action += omega

        return float(action)

    def compute_partition_function(
        self,
        states: List[np.ndarray],
        r: np.ndarray,
        temperature: float = 1.0,
    ) -> dict:
        """
        Compute the statistical partition function.

            Z = Σ_states exp(-Ω(state)/T)

        This allows probabilistic interpretation of states.

        Args:
            states: List of state vectors (angular coordinates)
            r: Langues parameter vector
            temperature: Effective temperature (higher = more entropy)

        Returns:
            Dict with Z, probabilities, and entropy
        """
        omegas = []
        for state in states:
            omega = self.compute_omega(state, r)
            omegas.append(omega)

        omegas = np.array(omegas)

        # Handle infinite omegas
        finite_mask = np.isfinite(omegas)
        if not np.any(finite_mask):
            return {
                "Z": 0.0,
                "probabilities": np.zeros(len(states)),
                "entropy": 0.0,
                "mean_omega": np.inf,
            }

        # Boltzmann weights
        boltzmann = np.zeros(len(states))
        boltzmann[finite_mask] = np.exp(-omegas[finite_mask] / temperature)

        Z = np.sum(boltzmann)
        probabilities = boltzmann / Z if Z > 0 else boltzmann

        # Shannon entropy
        p_nonzero = probabilities[probabilities > 0]
        entropy = -np.sum(p_nonzero * np.log(p_nonzero))

        return {
            "Z": float(Z),
            "probabilities": probabilities.tolist(),
            "entropy": float(entropy),
            "mean_omega": float(np.mean(omegas[finite_mask])),
            "min_omega": float(np.min(omegas[finite_mask])),
            "max_omega": float(np.max(omegas[finite_mask])) if np.any(finite_mask) else np.inf,
        }

    def compute_coherence_score(
        self,
        theta: np.ndarray,
        r: np.ndarray,
    ) -> float:
        """
        Compute a normalized coherence score in [0, 1].

            Coherence = 1 / (1 + ln(Ω))

        High coherence (→1): State is harmonically aligned
        Low coherence (→0): State is dissonant/distant

        Args:
            theta: Angular coordinates
            r: Langues parameters

        Returns:
            Coherence score in [0, 1]
        """
        omega = self.compute_omega(theta, r)

        if np.isinf(omega):
            return 0.0

        # Map Ω ∈ [1, ∞) to coherence ∈ (0, 1]
        coherence = 1.0 / (1.0 + np.log(omega))

        return float(np.clip(coherence, 0.0, 1.0))

    def get_formula_latex(self) -> str:
        """
        Return the LaTeX representation of the Grand Unified Formula.
        """
        return r"""
Grand Unified Symphonic Cipher Formula (GUSCF):

    \Omega(\theta, r; \mathbf{D}) = H(d_T, R) \cdot (\det G_\Omega)^{\frac{1}{2n}} \cdot \varphi^{\frac{D_f}{n}}

Where:
    H(d_T, R) = 1 + \alpha \tanh(\beta \cdot d_T)     [Harmonic Scaling Law]
    G_\Omega = G_T \odot G_L                          [Coupled Metric Tensor]
    G_T = \text{Riemannian metric on } T^n            [Hyper-Torus]
    G_L = \Lambda(r)^T \Lambda(r)                     [Langues Metric]
    D_f = \frac{\partial \ln \det G_L}{\partial \ln \epsilon}  [Fractal Dimension]
    \varphi = \frac{1 + \sqrt{5}}{2} \approx 1.618    [Golden Ratio]

Alternative Forms:

1. Logarithmic (additive):
    \ln \Omega = \ln H + \frac{1}{2n} \ln \det G_\Omega + \frac{D_f}{n} \ln \varphi

2. Action Integral:
    S[\gamma] = \int_\gamma \Omega(\theta(t), r; \mathbf{D}) \, dt

3. Partition Function:
    Z = \sum_{\text{states}} \exp\left(-\frac{\Omega}{T}\right)

4. Tensor Form:
    \Omega_{ij} = H \cdot (G_T \odot G_L)_{ij} \cdot \varphi^{D_f/n}
"""

    def __repr__(self) -> str:
        return (
            f"GrandUnifiedSymphonicCipher(n_dims={self.n_dims}, "
            f"α={self.alpha}, β={self.beta}, ε={self.epsilon}, φ={self.phi:.6f})"
        )


# =============================================================================
# DIFFERENTIAL CRYPTOGRAPHY FRAMEWORK
# =============================================================================

class DifferentialCryptographyFramework:
    """
    Differential Cryptography Framework: Calculus-Based Harmonic Security.

    This framework applies calculus to cryptographic phase modulation:

    Core Waveform (Nested Sinusoidal Modulation):
        f(t) = f₀ · (1 + ε₁·sin(ω₁t + ε₂·sin(ω₂t + ε₃·sin(ω₃t + ...))))

    Differential Structure:
        f'(t)  = Phase velocity (instantaneous frequency change)
        f''(t) = Phase acceleration (curvature / "whammy" intensity)
        ∫f(t)dt = Accumulated phase (harmonic memory trace)

    Security Mapping:
        - Phase velocity → Trust gradient on manifold
        - Curvature → Snap threshold detection
        - Accumulated phase → Watermark signature
        - Nested modulation → Chaff pattern generation

    The Snap Protocol triggers when |f''(t)| > κ_max (curvature threshold).

    Connection to Riemannian Geometry:
        On the hyper-torus with metric ds² = g_ij dθ^i dθ^j,
        the Christoffel symbols Γⁱⱼₖ describe path bending.
        The curvature κ(θ) determines geometric stability.

    Watermark Generation:
        The integral ∫₀ᵀ f(τ)dτ encodes the cumulative phase signature,
        which is discretized and hashed into cryptographic key bits.
    """

    def __init__(
        self,
        base_frequency: float = 440.0,
        modulation_depth: float = 0.2,
        modulation_frequencies: Optional[List[float]] = None,
        curvature_threshold: float = 100.0,
        n_harmonics: int = 4,
    ):
        """
        Initialize Differential Cryptography Framework.

        Args:
            base_frequency: Base frequency f₀ (default: 440 Hz = A4)
            modulation_depth: Modulation amplitude ε (default: 0.2)
            modulation_frequencies: List of modulation frequencies [ω₁, ω₂, ...]
                                   (default: geometric progression from φ)
            curvature_threshold: Maximum allowed curvature κ_max (Snap threshold)
            n_harmonics: Number of nested harmonic layers
        """
        self.f0 = base_frequency
        self.epsilon = modulation_depth
        self.kappa_max = curvature_threshold
        self.n_harmonics = n_harmonics
        self.phi = PHI

        # Default modulation frequencies: φ-based geometric progression
        if modulation_frequencies is None:
            self.omega = np.array([self.phi ** k for k in range(1, n_harmonics + 1)])
        else:
            self.omega = np.asarray(modulation_frequencies, dtype=np.float64)

    def compute_nested_phase(self, t: np.ndarray, depth: int = None) -> np.ndarray:
        """
        Compute nested sinusoidal modulation phase.

        φ(t) = ε₁·sin(ω₁t + ε₂·sin(ω₂t + ε₃·sin(ω₃t + ...)))

        Args:
            t: Time array
            depth: Recursion depth (default: n_harmonics)

        Returns:
            Nested phase modulation array
        """
        if depth is None:
            depth = self.n_harmonics

        if depth == 0:
            return np.zeros_like(t)

        # Build from innermost to outermost
        phase = np.zeros_like(t)
        for k in range(depth - 1, -1, -1):
            omega_k = self.omega[k] if k < len(self.omega) else self.omega[-1]
            eps_k = self.epsilon ** (k + 1)  # Decreasing modulation depth
            phase = eps_k * np.sin(omega_k * t + phase)

        return phase

    def compute_waveform(self, t: np.ndarray) -> np.ndarray:
        """
        Compute the full harmonic fractal waveform.

        f(t) = f₀ · (1 + ε·sin(ω₁t + ε·sin(ω₂t + ...)))

        Args:
            t: Time array

        Returns:
            Modulated waveform array
        """
        nested_phase = self.compute_nested_phase(t)
        return self.f0 * (1 + nested_phase)

    def compute_phase_velocity(self, t: np.ndarray, dt: float = None) -> np.ndarray:
        """
        Compute phase velocity f'(t) - the derivative of the waveform.

        f'(t) = instantaneous rate of frequency change

        This is the "velocity of phase" - how fast the tone is bending.
        In the trust manifold, this corresponds to the trust gradient.

        Args:
            t: Time array
            dt: Time step (default: inferred from t)

        Returns:
            Phase velocity array
        """
        if dt is None:
            dt = t[1] - t[0] if len(t) > 1 else 1e-6

        f = self.compute_waveform(t)
        # Use central differences for better accuracy
        velocity = np.gradient(f, dt)

        return velocity

    def compute_curvature(self, t: np.ndarray, dt: float = None) -> np.ndarray:
        """
        Compute curvature f''(t) - the second derivative of the waveform.

        f''(t) = acceleration of phase modulation = geometric curvature

        High curvature indicates rapid phase changes ("whammy" effects).
        When |f''(t)| > κ_max, the Snap Protocol triggers.

        Args:
            t: Time array
            dt: Time step (default: inferred from t)

        Returns:
            Curvature array
        """
        if dt is None:
            dt = t[1] - t[0] if len(t) > 1 else 1e-6

        velocity = self.compute_phase_velocity(t, dt)
        curvature = np.gradient(velocity, dt)

        return curvature

    def compute_accumulated_phase(
        self,
        t: np.ndarray,
        t_start: float = None,
        t_end: float = None
    ) -> float:
        """
        Compute accumulated phase integral Φ(t) = ∫f(τ)dτ.

        This is the "harmonic memory trace" - the total phase area
        accumulated over time. In the geometric model, this corresponds
        to the total geodesic length traversed.

        Args:
            t: Time array
            t_start: Integration start (default: t[0])
            t_end: Integration end (default: t[-1])

        Returns:
            Accumulated phase (scalar)
        """
        if t_start is None:
            t_start = t[0]
        if t_end is None:
            t_end = t[-1]

        # Mask for integration bounds
        mask = (t >= t_start) & (t <= t_end)
        t_masked = t[mask]

        if len(t_masked) < 2:
            return 0.0

        f = self.compute_waveform(t_masked)
        dt = t_masked[1] - t_masked[0]

        # Trapezoidal integration
        accumulated = np.trapezoid(f, dx=dt)

        return float(accumulated)

    def detect_snap_events(self, t: np.ndarray) -> dict:
        """
        Detect Snap events where curvature exceeds threshold.

        The Snap Protocol triggers when |f''(t)| > κ_max.
        These are points of geometric instability where the
        "memory line breaks" in the trust manifold.

        Args:
            t: Time array

        Returns:
            Dict with snap event information
        """
        curvature = self.compute_curvature(t)
        snap_mask = np.abs(curvature) > self.kappa_max

        snap_times = t[snap_mask]
        snap_curvatures = curvature[snap_mask]

        return {
            "snap_count": int(np.sum(snap_mask)),
            "snap_times": snap_times.tolist(),
            "snap_curvatures": snap_curvatures.tolist(),
            "max_curvature": float(np.max(np.abs(curvature))),
            "mean_curvature": float(np.mean(np.abs(curvature))),
            "threshold": self.kappa_max,
            "stability_ratio": float(1 - np.mean(snap_mask)),
        }

    def generate_watermark_signature(
        self,
        t: np.ndarray,
        n_segments: int = 16
    ) -> np.ndarray:
        """
        Generate watermark signature from differential structure.

        The watermark encodes:
        1. Segment-wise accumulated phase integrals
        2. Curvature statistics per segment
        3. Phase velocity patterns

        This creates a unique signature from the continuous
        differential structure, discretized for cryptographic use.

        Args:
            t: Time array
            n_segments: Number of signature segments

        Returns:
            Watermark signature array (n_segments,)
        """
        segment_length = len(t) // n_segments
        signature = np.zeros(n_segments)

        f = self.compute_waveform(t)
        curvature = self.compute_curvature(t)
        velocity = self.compute_phase_velocity(t)

        for i in range(n_segments):
            start = i * segment_length
            end = start + segment_length if i < n_segments - 1 else len(t)

            # Combine multiple differential features
            segment_f = f[start:end]
            segment_kappa = curvature[start:end]
            segment_v = velocity[start:end]

            # Weighted combination of features
            phase_integral = np.trapezoid(segment_f) / (end - start)
            curvature_stat = np.std(segment_kappa)
            velocity_stat = np.mean(np.abs(segment_v))

            # Golden ratio weighted combination
            signature[i] = (
                phase_integral +
                self.phi * curvature_stat +
                self.phi ** 2 * velocity_stat
            )

        # Normalize to [0, 1]
        if np.max(signature) > np.min(signature):
            signature = (signature - np.min(signature)) / (np.max(signature) - np.min(signature))

        return signature

    def generate_chaff_pattern(
        self,
        t: np.ndarray,
        chaff_amplitude: float = 0.01,
        seed: int = None
    ) -> np.ndarray:
        """
        Generate chaff pattern as modulated phase noise.

        Chaff is low-amplitude phase perturbation that follows
        the differential structure but with added randomness.
        It's indistinguishable from the signal to an observer
        but can be detected with the correct key.

        Args:
            t: Time array
            chaff_amplitude: Amplitude of chaff noise (default: 0.01)
            seed: Random seed for reproducibility

        Returns:
            Chaff pattern array
        """
        if seed is not None:
            np.random.seed(seed)

        # Base chaff follows nested sinusoid structure
        base_chaff = self.compute_nested_phase(t, depth=self.n_harmonics - 1)

        # Add structured noise modulated by golden ratio
        noise = np.random.randn(len(t))
        modulated_noise = noise * chaff_amplitude * (1 + 0.5 * np.sin(self.phi * t))

        # Combine base pattern with modulated noise
        chaff = base_chaff * chaff_amplitude + modulated_noise

        return chaff

    def compute_trust_gradient(
        self,
        theta: np.ndarray,
        langues_r: np.ndarray,
        guscf: "GrandUnifiedSymphonicCipher" = None
    ) -> np.ndarray:
        """
        Compute trust gradient on the geometric manifold.

        In the differential framework, the trust gradient is
        the derivative of Ω with respect to position:

            ∇Ω = (∂Ω/∂θ₁, ∂Ω/∂θ₂, ..., ∂Ω/∂θₙ)

        This corresponds to f'(t) in the waveform domain.

        Args:
            theta: Angular coordinates on hyper-torus
            langues_r: Langues parameter vector
            guscf: GrandUnifiedSymphonicCipher instance (created if None)

        Returns:
            Trust gradient vector
        """
        if guscf is None:
            guscf = GrandUnifiedSymphonicCipher(n_dims=len(theta))

        h = 1e-6  # Finite difference step
        gradient = np.zeros_like(theta)

        omega_0 = guscf.compute_omega(theta, langues_r)

        for i in range(len(theta)):
            theta_plus = theta.copy()
            theta_plus[i] += h
            omega_plus = guscf.compute_omega(theta_plus, langues_r)

            # Handle infinite omega
            if np.isinf(omega_plus) or np.isinf(omega_0):
                gradient[i] = np.inf if np.isinf(omega_plus) else 0.0
            else:
                gradient[i] = (omega_plus - omega_0) / h

        return gradient

    def compute_geometric_curvature(
        self,
        theta: np.ndarray,
        langues_r: np.ndarray,
        guscf: "GrandUnifiedSymphonicCipher" = None
    ) -> np.ndarray:
        """
        Compute geometric curvature (Hessian) of Ω.

        The curvature tensor ∂²Ω/∂θᵢ∂θⱼ describes how the
        trust gradient changes - analogous to f''(t).

        When eigenvalues of this Hessian exceed κ_max,
        the Snap Protocol triggers.

        Args:
            theta: Angular coordinates
            langues_r: Langues parameters
            guscf: GrandUnifiedSymphonicCipher instance

        Returns:
            Hessian matrix (curvature tensor)
        """
        if guscf is None:
            guscf = GrandUnifiedSymphonicCipher(n_dims=len(theta))

        n = len(theta)
        h = 1e-5
        hessian = np.zeros((n, n))

        omega_0 = guscf.compute_omega(theta, langues_r)

        for i in range(n):
            for j in range(i, n):
                theta_pp = theta.copy()
                theta_pm = theta.copy()
                theta_mp = theta.copy()
                theta_mm = theta.copy()

                theta_pp[i] += h
                theta_pp[j] += h
                theta_pm[i] += h
                theta_pm[j] -= h
                theta_mp[i] -= h
                theta_mp[j] += h
                theta_mm[i] -= h
                theta_mm[j] -= h

                omega_pp = guscf.compute_omega(theta_pp, langues_r)
                omega_pm = guscf.compute_omega(theta_pm, langues_r)
                omega_mp = guscf.compute_omega(theta_mp, langues_r)
                omega_mm = guscf.compute_omega(theta_mm, langues_r)

                # Check for infinities
                if any(np.isinf(x) for x in [omega_pp, omega_pm, omega_mp, omega_mm]):
                    hessian[i, j] = np.inf
                else:
                    hessian[i, j] = (omega_pp - omega_pm - omega_mp + omega_mm) / (4 * h ** 2)

                hessian[j, i] = hessian[i, j]  # Symmetric

        return hessian

    def detect_geometric_snap(
        self,
        theta: np.ndarray,
        langues_r: np.ndarray,
        guscf: "GrandUnifiedSymphonicCipher" = None
    ) -> dict:
        """
        Detect geometric Snap based on curvature eigenvalues.

        Snap occurs when max eigenvalue of Hessian > κ_max.

        Args:
            theta: Angular coordinates
            langues_r: Langues parameters
            guscf: GrandUnifiedSymphonicCipher instance

        Returns:
            Snap detection result dict
        """
        hessian = self.compute_geometric_curvature(theta, langues_r, guscf)

        # Handle infinite entries
        if np.any(np.isinf(hessian)):
            return {
                "snap_detected": True,
                "reason": "infinite_curvature",
                "max_eigenvalue": np.inf,
                "threshold": self.kappa_max,
            }

        eigenvalues = np.linalg.eigvalsh(hessian)
        max_eigenvalue = np.max(np.abs(eigenvalues))
        snap_detected = max_eigenvalue > self.kappa_max

        return {
            "snap_detected": snap_detected,
            "max_eigenvalue": float(max_eigenvalue),
            "eigenvalues": eigenvalues.tolist(),
            "threshold": self.kappa_max,
            "stability_margin": float(self.kappa_max - max_eigenvalue),
        }

    def analyze_trajectory(
        self,
        trajectory: List[np.ndarray],
        langues_r: np.ndarray,
        timestamps: np.ndarray = None,
        guscf: "GrandUnifiedSymphonicCipher" = None
    ) -> dict:
        """
        Analyze a trajectory through the differential lens.

        Computes:
        - Trust values Ω(t) along trajectory
        - Trust gradient (velocity) at each point
        - Curvature and Snap events
        - Accumulated trust integral

        Args:
            trajectory: List of angular coordinate points
            langues_r: Langues parameters
            timestamps: Optional time values for each point
            guscf: GrandUnifiedSymphonicCipher instance

        Returns:
            Comprehensive trajectory analysis dict
        """
        if guscf is None and len(trajectory) > 0:
            guscf = GrandUnifiedSymphonicCipher(n_dims=len(trajectory[0]))

        if timestamps is None:
            timestamps = np.linspace(0, 1, len(trajectory))

        omegas = []
        gradients = []
        snap_events = []

        for i, theta in enumerate(trajectory):
            omega = guscf.compute_omega(theta, langues_r)
            omegas.append(omega)

            grad = self.compute_trust_gradient(theta, langues_r, guscf)
            gradients.append(np.linalg.norm(grad) if not np.any(np.isinf(grad)) else np.inf)

            snap = self.detect_geometric_snap(theta, langues_r, guscf)
            if snap["snap_detected"]:
                snap_events.append({
                    "index": i,
                    "time": float(timestamps[i]),
                    "eigenvalue": snap["max_eigenvalue"],
                })

        omegas = np.array(omegas)
        finite_mask = np.isfinite(omegas)

        # Accumulated trust integral
        if np.any(finite_mask):
            accumulated = np.trapezoid(omegas[finite_mask], timestamps[finite_mask])
        else:
            accumulated = np.inf

        return {
            "trust_values": omegas.tolist(),
            "trust_gradients": gradients,
            "snap_events": snap_events,
            "snap_count": len(snap_events),
            "accumulated_trust": float(accumulated),
            "mean_trust": float(np.mean(omegas[finite_mask])) if np.any(finite_mask) else np.inf,
            "max_trust": float(np.max(omegas[finite_mask])) if np.any(finite_mask) else np.inf,
            "stability_ratio": float(1 - len(snap_events) / len(trajectory)) if len(trajectory) > 0 else 1.0,
        }

    def get_differential_equations(self) -> str:
        """
        Return the formal differential equations of the framework.
        """
        return r"""
Differential Cryptography Framework - Formal Equations

═══════════════════════════════════════════════════════

1. NESTED HARMONIC MODULATION (Waveform)
   f(t) = f₀ · (1 + ε₁·sin(ω₁t + ε₂·sin(ω₂t + ε₃·sin(ω₃t + ...))))

2. PHASE VELOCITY (First Derivative)
   f'(t) = f₀ · ε₁·ω₁·cos(ω₁t + φ(t)) · [1 + ε₂·ω₂·cos(ω₂t + ...)]

   Interpretation: Trust gradient on manifold, instantaneous frequency change

3. CURVATURE (Second Derivative)
   f''(t) = d/dt[f'(t)]

   The Snap Protocol triggers when: |f''(t)| > κ_max

4. ACCUMULATED PHASE (Integral)
   Φ(T₁, T₂) = ∫_{T₁}^{T₂} f(τ) dτ

   Interpretation: Harmonic memory trace, watermark signature

5. GEOMETRIC CURVATURE (Hessian of Ω)
   H_ij = ∂²Ω/∂θᵢ∂θⱼ

   Snap detection: max|eigenvalue(H)| > κ_max

6. TRUST GRADIENT
   ∇Ω = (∂Ω/∂θ₁, ..., ∂Ω/∂θₙ)

   Maps to phase velocity in the geometric domain

7. CHRISTOFFEL SYMBOLS (Geometric Connection)
   Γⁱⱼₖ = ½gⁱˡ(∂gₗⱼ/∂xᵏ + ∂gₗₖ/∂xʲ - ∂gⱼₖ/∂xˡ)

   Describes path bending on the hyper-torus manifold

8. WATERMARK GENERATION
   W(t) = hash(∫f(τ)dτ, σ(f''(t)), μ(|f'(t)|))

   Combines integral, curvature statistics, velocity mean

═══════════════════════════════════════════════════════

Connection to Grand Unified Formula:
   Ω(θ, r; D) = H(d_T, R) · (det G_Ω)^{1/(2n)} · φ^{D_f/n}

   d/dt[Ω(θ(t))] = ∇Ω · θ'(t)    (Chain rule on manifold)
"""

    # =========================================================================
    # KEY EVOLUTION LAW
    # =========================================================================

    def evolve_key(
        self,
        t: np.ndarray,
        k0: float = 1.0,
        eta: float = 0.05
    ) -> np.ndarray:
        """
        Evolve key according to the differential key evolution law.

        The key evolves via:
            dk/dt = η · w(t) · k(t)

        Solution:
            k(t) = k(0) · exp(η · ∫₀ᵗ w(τ) dτ)

        This embeds the rhythmic watermark pattern as a continuous
        exponential warp of the key itself.

        Args:
            t: Time array
            k0: Initial key value k(0)
            eta: Sensitivity constant η

        Returns:
            Evolved key array k(t)
        """
        # Compute watermark signal
        f = self.compute_waveform(t)
        w = np.sin(2 * np.pi * f * t / self.f0)  # Normalized watermark

        # Cumulative integral of watermark
        dt = t[1] - t[0] if len(t) > 1 else 1e-6
        integral_w = np.cumsum(w) * dt

        # Key evolution: k(t) = k0 * exp(η * ∫w(τ)dτ)
        k = k0 * np.exp(eta * integral_w)

        return k

    def compute_key_derivative(
        self,
        t: np.ndarray,
        k: np.ndarray,
        eta: float = 0.05
    ) -> np.ndarray:
        """
        Compute dk/dt = η · w(t) · k(t) directly.

        Args:
            t: Time array
            k: Key values at each time
            eta: Sensitivity constant

        Returns:
            Key derivative dk/dt
        """
        f = self.compute_waveform(t)
        w = np.sin(2 * np.pi * f * t / self.f0)
        dk_dt = eta * w * k
        return dk_dt

    # =========================================================================
    # TRUST ENERGY AND STABILITY
    # =========================================================================

    def compute_trust_energy_density(
        self,
        t: np.ndarray,
        theta: np.ndarray,
        phi: np.ndarray,
        R: float = 10.0,
        r: float = 2.0
    ) -> np.ndarray:
        """
        Compute instantaneous trust energy density on the torus.

        E(t) = (R + r·cos(θ))² · (dφ/dt)² + r² · (dθ/dt)²

        This is the kinetic energy of motion on the toroidal manifold.
        High energy density indicates rapid state changes.

        Args:
            t: Time array
            theta: θ coordinate trajectory
            phi: φ coordinate trajectory
            R: Major radius
            r: Minor radius

        Returns:
            Energy density array E(t)
        """
        dt = t[1] - t[0] if len(t) > 1 else 1e-6

        # Angular velocities
        d_theta_dt = np.gradient(theta, dt)
        d_phi_dt = np.gradient(phi, dt)

        # Trust energy density: E(t) = g_φφ·(dφ/dt)² + g_θθ·(dθ/dt)²
        g_phi_phi = (R + r * np.cos(theta)) ** 2
        g_theta_theta = r ** 2

        E = g_phi_phi * d_phi_dt ** 2 + g_theta_theta * d_theta_dt ** 2

        return E

    def compute_cumulative_trust_energy(
        self,
        t: np.ndarray,
        theta: np.ndarray,
        phi: np.ndarray,
        R: float = 10.0,
        r: float = 2.0
    ) -> float:
        """
        Compute cumulative trust energy over a trajectory.

        ε(t₁,t₂) = ∫_{t₁}^{t₂} E(t) dt

        If ε exceeds E_snap, the geometric link fails (Snap).

        Args:
            t: Time array
            theta: θ trajectory
            phi: φ trajectory
            R: Major radius
            r: Minor radius

        Returns:
            Cumulative trust energy (scalar)
        """
        E = self.compute_trust_energy_density(t, theta, phi, R, r)
        dt = t[1] - t[0] if len(t) > 1 else 1e-6

        cumulative = np.trapezoid(E, dx=dt)
        return float(cumulative)

    def analyze_lyapunov_stability(
        self,
        t: np.ndarray,
        eta: float = 0.05
    ) -> dict:
        """
        Analyze Lyapunov stability of the key evolution system.

        For dk/dt = η·w(t)·k(t), the system is:
        - Stable if η·∫w(t)dt remains bounded
        - Asymptotically stable if η·∫w(t)dt → 0
        - Unstable if η·∫w(t)dt → ±∞

        The Lyapunov exponent is:
            λ = lim_{t→∞} (1/t) · ln|k(t)/k(0)| = η · ⟨w⟩

        where ⟨w⟩ is the time-averaged watermark signal.

        Args:
            t: Time array
            eta: Sensitivity constant

        Returns:
            Stability analysis dict
        """
        # Evolve key
        k = self.evolve_key(t, k0=1.0, eta=eta)

        # Compute watermark
        f = self.compute_waveform(t)
        w = np.sin(2 * np.pi * f * t / self.f0)

        # Time-averaged watermark (should be ~0 for stability)
        w_mean = np.mean(w)

        # Lyapunov exponent estimate
        T = t[-1] - t[0]
        lyapunov_exponent = eta * w_mean

        # Key growth rate
        if len(t) > 1:
            log_k_ratio = np.log(np.abs(k[-1] / k[0])) if k[0] != 0 and k[-1] != 0 else 0
            empirical_lyapunov = log_k_ratio / T
        else:
            empirical_lyapunov = 0

        # Key bounds
        k_min, k_max = np.min(k), np.max(k)
        k_range = k_max / k_min if k_min > 0 else np.inf

        # Stability classification
        if np.abs(lyapunov_exponent) < 1e-6:
            stability = "marginally_stable"
        elif lyapunov_exponent < 0:
            stability = "asymptotically_stable"
        else:
            stability = "unstable"

        # For bounded oscillatory systems, check variance
        k_variance = np.var(k)
        bounded = k_range < 100  # Heuristic bound

        return {
            "lyapunov_exponent": float(lyapunov_exponent),
            "empirical_lyapunov": float(empirical_lyapunov),
            "stability": stability,
            "bounded": bounded,
            "key_range": float(k_range),
            "key_min": float(k_min),
            "key_max": float(k_max),
            "key_variance": float(k_variance),
            "watermark_mean": float(w_mean),
            "eta": eta,
        }

    def compute_stability_bounds(
        self,
        eta_max: float = 0.5,
        n_samples: int = 20
    ) -> dict:
        """
        Compute stability bounds for the key evolution system.

        Finds the maximum η such that the system remains bounded.

        The system is bounded if:
            |η| < η_critical = 1 / (T · max|∫w(τ)dτ|)

        Args:
            eta_max: Maximum η to test
            n_samples: Number of samples

        Returns:
            Stability bounds analysis
        """
        t = np.linspace(0, 10, 1000)
        eta_values = np.linspace(0.01, eta_max, n_samples)

        results = []
        critical_eta = eta_max

        for eta in eta_values:
            k = self.evolve_key(t, k0=1.0, eta=eta)
            k_range = np.max(k) / np.min(k) if np.min(k) > 0 else np.inf

            bounded = k_range < 100 and np.all(np.isfinite(k))
            results.append({
                "eta": float(eta),
                "k_range": float(k_range),
                "bounded": bounded,
            })

            if not bounded and critical_eta == eta_max:
                critical_eta = eta

        # Find critical η (transition to unbounded)
        bounded_etas = [r["eta"] for r in results if r["bounded"]]
        if bounded_etas:
            max_bounded_eta = max(bounded_etas)
        else:
            max_bounded_eta = 0.0

        return {
            "critical_eta": float(critical_eta),
            "max_bounded_eta": float(max_bounded_eta),
            "stability_margin": float(eta_max - critical_eta),
            "samples": results,
            "recommendation": f"Use η < {max_bounded_eta:.4f} for bounded key evolution"
        }

    def verify_energy_conservation(
        self,
        t: np.ndarray,
        tolerance: float = 0.1
    ) -> dict:
        """
        Verify approximate energy conservation in the harmonic system.

        For a conservative oscillatory system, total energy should be
        approximately constant. Deviation indicates dissipation or
        external driving.

        Args:
            t: Time array
            tolerance: Relative tolerance for "conservation"

        Returns:
            Energy conservation analysis
        """
        f = self.compute_waveform(t)
        velocity = self.compute_phase_velocity(t)

        # Kinetic-like energy: (1/2)·v²
        kinetic = 0.5 * velocity ** 2

        # Potential-like energy: (1/2)·ω²·(f - f₀)²
        potential = 0.5 * (self.omega[0] ** 2) * (f - self.f0) ** 2

        total_energy = kinetic + potential

        E_mean = np.mean(total_energy)
        E_std = np.std(total_energy)
        E_relative_variation = E_std / E_mean if E_mean > 0 else np.inf

        conserved = E_relative_variation < tolerance

        return {
            "conserved": conserved,
            "mean_energy": float(E_mean),
            "energy_std": float(E_std),
            "relative_variation": float(E_relative_variation),
            "tolerance": tolerance,
            "kinetic_mean": float(np.mean(kinetic)),
            "potential_mean": float(np.mean(potential)),
        }

    def get_stability_equations(self) -> str:
        """
        Return the formal stability equations.
        """
        return r"""
Differential Cryptography - Stability Analysis
═══════════════════════════════════════════════════════

1. KEY EVOLUTION LAW
   dk/dt = η · w(t) · k(t)
   k(t) = k(0) · exp(η · ∫₀ᵗ w(τ) dτ)

2. LYAPUNOV EXPONENT
   λ = lim_{t→∞} (1/t) · ln|k(t)/k(0)|
   λ = η · ⟨w⟩   (time-averaged watermark)

   Stability Classification:
   - λ < 0:  Asymptotically stable (key → 0)
   - λ = 0:  Marginally stable (bounded oscillation)
   - λ > 0:  Unstable (key → ∞)

3. TRUST ENERGY DENSITY (on torus)
   E(t) = (R + r·cos θ)² · (dφ/dt)² + r² · (dθ/dt)²

4. CUMULATIVE TRUST ENERGY
   ε(t₁,t₂) = ∫_{t₁}^{t₂} E(t) dt

   Snap Condition: ε > E_snap ⟹ WRITE_FAIL

5. BOUNDED STABILITY CONDITION
   System bounded iff: |η| < η_critical

   where η_critical = 1 / (T · max|∫w(τ)dτ|)

6. ENERGY CONSERVATION (approximate)
   H = (1/2)·v² + (1/2)·ω²·(f - f₀)²

   dH/dt ≈ 0 for stable oscillatory system

7. WATERMARK INTEGRITY CONDITION
   Phase drift: Δφ = |φ_computed - φ_expected|
   Valid iff: Δφ < φ_tolerance

═══════════════════════════════════════════════════════

Security Guarantee:
   For bounded η and zero-mean watermark (⟨w⟩ = 0),
   the key evolution is stable with λ = 0,
   ensuring the cryptographic state remains finite
   and the watermark signature extractable.
"""

    def __repr__(self) -> str:
        return (
            f"DifferentialCryptographyFramework(f₀={self.f0}, ε={self.epsilon}, "
            f"κ_max={self.kappa_max}, n_harmonics={self.n_harmonics})"
        )


# =============================================================================
# POLYHEDRAL HAMILTONIAN DEFENSE MANIFOLD (PHDM)
# =============================================================================

@dataclass
class Polyhedron:
    """
    Represents a polyhedral structure in the defense manifold.

    Each polyhedron has:
    - A graph structure G = (V, E)
    - A position in the 6D Langues manifold
    - Topological invariants (Euler characteristic, symmetry group)
    - Cryptographic binding data
    """
    name: str
    vertices: int
    edges: int
    faces: int
    centroid: np.ndarray  # Position in 6D Langues space
    symmetry_order: int = 1
    dual_name: str = ""
    genus: int = 0  # For non-convex polyhedra

    def euler_characteristic(self) -> int:
        """Compute Euler characteristic: χ = V - E + F = 2 - 2g"""
        return self.vertices - self.edges + self.faces

    def serialize(self) -> bytes:
        """Serialize polyhedron for cryptographic hashing."""
        data = f"{self.name}|{self.vertices}|{self.edges}|{self.faces}|{self.symmetry_order}"
        data += "|" + ",".join(f"{x:.6f}" for x in self.centroid)
        return data.encode('utf-8')

    def is_valid_euler(self) -> bool:
        """Verify Euler characteristic matches expected value."""
        expected = 2 - 2 * self.genus
        return self.euler_characteristic() == expected

    def topological_invariant(self) -> bytes:
        """
        Compute a cryptographic hash of the topological invariants.

        The hash includes:
        - Euler characteristic
        - Symmetry order
        - Genus
        - Vertex/Edge/Face counts

        Returns:
            32-byte SHA256 hash
        """
        chi = self.euler_characteristic()
        data = f"TOPO|V={self.vertices}|E={self.edges}|F={self.faces}|χ={chi}|sym={self.symmetry_order}|g={self.genus}"
        return hashlib.sha256(data.encode('utf-8')).digest()


class PolyhedralHamiltonianDefense:
    """
    Polyhedral Hamiltonian Defense Manifold (PHDM).

    A cryptographic defense system that threads polyhedral structures
    along a 1-dimensional curve in a higher-dimensional manifold.

    Core Concepts:
    1. HAMILTONIAN PATH: A sequence P₁ → P₂ → ... → Pₙ through the
       polyhedral family where each structure is visited exactly once.

    2. SEQUENTIAL KEY DERIVATION:
       K_{i+1} = HMAC(K_i, Serialize(P_i))
       Each shape's parameters seed the next key.

    3. GEODESIC EMBEDDING: The path is realized as a smooth curve
       γ(t) : [0,1] → ℝ⁶ in the Langues manifold.

    4. CURVATURE-BASED DETECTION: Any deviation from γ(t) triggers
       the Snap condition. Attack velocity = d/dt[d(state, γ(t))].

    The "1-0 rhythm":
    - 1: On-path state (valid manifold point)
    - 0: Off-path deviation (attack/corruption)

    Security Properties:
    - Predictable topology: legitimate processes follow the path
    - Observable curvature: deviations are measurable
    - Sequential dependency: states are cryptographically chained
    - Geometric verifiability: the chain is auditable
    """

    # Canonical polyhedral family (mathematically significant polyhedra)
    CANONICAL_POLYHEDRA = [
        # Platonic Solids
        ("Tetrahedron", 4, 6, 4, 12),           # Simplest Platonic
        ("Cube", 8, 12, 6, 24),                  # Hexahedron
        ("Octahedron", 6, 12, 8, 24),            # Dual of cube
        ("Dodecahedron", 20, 30, 12, 60),        # 12 pentagons
        ("Icosahedron", 12, 30, 20, 60),         # 20 triangles

        # Archimedean Solids (selected)
        ("Truncated Tetrahedron", 12, 18, 8, 12),
        ("Cuboctahedron", 12, 24, 14, 24),
        ("Icosidodecahedron", 30, 60, 32, 60),

        # Kepler-Poinsot (star polyhedra)
        ("Small Stellated Dodecahedron", 12, 30, 12, 60),
        ("Great Dodecahedron", 12, 30, 12, 60),

        # Special Non-Convex
        ("Szilassi Polyhedron", 14, 21, 7, 168),  # Genus 1, χ = 0
        ("Császár Polyhedron", 7, 21, 14, 168),   # Dual of Szilassi

        # Johnson Solids (selected)
        ("Pentagonal Bipyramid", 7, 15, 10, 10),
        ("Triangular Cupola", 9, 15, 8, 6),

        # Rhombic Polyhedra
        ("Rhombic Dodecahedron", 14, 24, 12, 24),
        ("Bilinski Dodecahedron", 14, 24, 12, 4),  # Face-transitive
    ]

    def __init__(
        self,
        epsilon_snap: float = 0.5,
        langues_metric: "LanguesMetricTensor" = None,
        seed_key: bytes = None,
    ):
        """
        Initialize the Polyhedral Hamiltonian Defense Manifold.

        Args:
            epsilon_snap: Maximum allowed deviation from geodesic
            langues_metric: LanguesMetricTensor for 6D metric
            seed_key: Initial cryptographic seed (default: random)
        """
        self.epsilon_snap = epsilon_snap
        self.phi = PHI

        # Initialize Langues metric
        if langues_metric is None:
            self.langues = LanguesMetricTensor(
                epsilon=DEFAULT_EPSILON,
                validate_epsilon=False
            )
        else:
            self.langues = langues_metric

        # Seed key
        if seed_key is None:
            self.seed_key = hashlib.sha256(b"PHDM_SEED").digest()
        else:
            self.seed_key = seed_key

        # Build polyhedral family
        self.polyhedra = self._build_polyhedra()

        # Construct Hamiltonian path
        self.hamiltonian_path = self._construct_hamiltonian_path()

        # Pre-compute geodesic curve
        self._geodesic_spline = None

    def _build_polyhedra(self) -> List[Polyhedron]:
        """Build the canonical polyhedral family with 6D embeddings."""
        polyhedra = []

        for i, (name, V, E, F, sym) in enumerate(self.CANONICAL_POLYHEDRA):
            # Compute 6D centroid based on topological properties
            # Map to Langues space: (syntactic, semantic, phonological,
            #                        morphological, pragmatic, discourse)
            centroid = np.array([
                V / 20.0,                       # Vertex density (normalized)
                E / 60.0,                       # Edge density
                F / 30.0,                       # Face density
                (V - E + F) / 4.0,              # Euler characteristic scaled
                sym / 168.0,                    # Symmetry order (max: Szilassi)
                self.phi ** (i % 6) / 10.0,     # Golden ratio modulation
            ])

            # Determine genus from Euler characteristic
            chi = V - E + F
            genus = (2 - chi) // 2 if chi <= 2 else 0

            polyhedra.append(Polyhedron(
                name=name,
                vertices=V,
                edges=E,
                faces=F,
                centroid=centroid,
                symmetry_order=sym,
                genus=genus,
            ))

        return polyhedra

    def _construct_hamiltonian_path(self) -> List[int]:
        """
        Construct a Hamiltonian path through the polyhedral family.

        Uses a greedy nearest-neighbor heuristic based on the
        6D Langues metric distance between polyhedra.

        Returns:
            List of polyhedron indices in Hamiltonian order
        """
        n = len(self.polyhedra)
        visited = [False] * n
        path = [0]  # Start with first polyhedron
        visited[0] = True

        r = np.array([0.5] * 6)  # Default Langues parameters

        for _ in range(n - 1):
            current = path[-1]
            current_centroid = self.polyhedra[current].centroid

            # Find nearest unvisited neighbor
            best_dist = np.inf
            best_next = -1

            for j in range(n):
                if not visited[j]:
                    dist = self.langues.compute_distance(
                        current_centroid,
                        self.polyhedra[j].centroid,
                        r
                    )
                    if dist < best_dist:
                        best_dist = dist
                        best_next = j

            if best_next >= 0:
                path.append(best_next)
                visited[best_next] = True

        return path

    def derive_key_chain(
        self,
        initial_key: bytes = None,
    ) -> List[Tuple[Polyhedron, bytes]]:
        """
        Derive sequential keys along the Hamiltonian path.

        K_{i+1} = HMAC-SHA256(K_i, Serialize(P_i))

        This creates a cryptographically bound chain where each
        polyhedron's parameters seed the next key.

        Args:
            initial_key: Starting key (default: seed_key)

        Returns:
            List of (Polyhedron, derived_key) tuples
        """
        import hmac

        if initial_key is None:
            initial_key = self.seed_key

        chain = []
        K = initial_key

        for idx in self.hamiltonian_path:
            P = self.polyhedra[idx]

            # Derive next key
            K_next = hmac.new(K, P.serialize(), hashlib.sha256).digest()

            chain.append((P, K_next))
            K = K_next

        return chain

    def compute_geodesic_curve(
        self,
        n_points: int = 100
    ) -> np.ndarray:
        """
        Compute the geodesic curve γ(t) through the polyhedral centroids.

        Uses cubic B-spline interpolation through the Hamiltonian path
        to create a smooth curve in the 6D Langues manifold.

        Args:
            n_points: Number of points along the curve

        Returns:
            Array of shape (n_points, 6) representing γ(t)
        """
        # Get centroids in Hamiltonian order
        centroids = np.array([
            self.polyhedra[idx].centroid
            for idx in self.hamiltonian_path
        ])

        # Parameterize by arc length
        t_nodes = np.linspace(0, 1, len(centroids))
        t_eval = np.linspace(0, 1, n_points)

        # Cubic interpolation for each dimension
        from scipy.interpolate import CubicSpline

        gamma = np.zeros((n_points, 6))
        for d in range(6):
            cs = CubicSpline(t_nodes, centroids[:, d])
            gamma[:, d] = cs(t_eval)

        self._geodesic_spline = gamma
        return gamma

    def compute_curve_curvature(
        self,
        gamma: np.ndarray = None
    ) -> np.ndarray:
        """
        Compute the curvature κ(t) along the geodesic curve.

        κ(t) = |γ''(t)| / |γ'(t)|²

        High curvature indicates sharp bends in the path.

        Args:
            gamma: Geodesic curve array (n_points, 6)

        Returns:
            Curvature array (n_points,)
        """
        if gamma is None:
            if self._geodesic_spline is None:
                gamma = self.compute_geodesic_curve()
            else:
                gamma = self._geodesic_spline

        n = len(gamma)
        if n < 3:
            return np.zeros(n)

        # First derivative (velocity)
        gamma_prime = np.gradient(gamma, axis=0)
        speed = np.linalg.norm(gamma_prime, axis=1)

        # Second derivative (acceleration)
        gamma_double_prime = np.gradient(gamma_prime, axis=0)
        acceleration = np.linalg.norm(gamma_double_prime, axis=1)

        # Curvature: κ = |γ''| / |γ'|²
        with np.errstate(divide='ignore', invalid='ignore'):
            curvature = acceleration / (speed ** 2 + 1e-10)

        return curvature

    def measure_deviation(
        self,
        state: np.ndarray,
        t: float,
        gamma: np.ndarray = None
    ) -> float:
        """
        Measure deviation d(state, γ(t)) from the geodesic curve.

        Args:
            state: Current state in 6D Langues space
            t: Parameter t ∈ [0, 1] along the curve
            gamma: Pre-computed geodesic curve

        Returns:
            Euclidean distance from curve
        """
        if gamma is None:
            if self._geodesic_spline is None:
                gamma = self.compute_geodesic_curve()
            else:
                gamma = self._geodesic_spline

        # Find point on curve at parameter t
        idx = int(t * (len(gamma) - 1))
        idx = max(0, min(idx, len(gamma) - 1))

        gamma_t = gamma[idx]

        # Compute Langues-weighted distance
        r = np.array([0.5] * 6)
        deviation = self.langues.compute_distance(state, gamma_t, r)

        return float(deviation)

    def detect_intrusion(
        self,
        states: List[np.ndarray],
        timestamps: np.ndarray = None,
    ) -> dict:
        """
        Detect intrusion attempts via curvature-based analysis.

        An intrusion is detected when:
        1. d(state, γ(t)) > ε_snap (off-path deviation)
        2. d/dt[d(state, γ(t))] exceeds threshold (threat velocity)

        Args:
            states: Sequence of observed states in 6D space
            timestamps: Time values for each state

        Returns:
            Intrusion detection analysis dict
        """
        if timestamps is None:
            timestamps = np.linspace(0, 1, len(states))

        gamma = self.compute_geodesic_curve(n_points=len(states))

        deviations = []
        intrusion_events = []
        rhythm_pattern = []  # 1 = on-path, 0 = off-path

        for i, (state, t) in enumerate(zip(states, timestamps)):
            dev = self.measure_deviation(state, t, gamma)
            deviations.append(dev)

            on_path = dev <= self.epsilon_snap
            rhythm_pattern.append(1 if on_path else 0)

            if not on_path:
                intrusion_events.append({
                    "index": i,
                    "time": float(t),
                    "deviation": float(dev),
                    "threshold": self.epsilon_snap,
                })

        # Compute threat velocity: d/dt[deviation]
        deviations = np.array(deviations)
        if len(timestamps) > 1:
            dt = timestamps[1] - timestamps[0]
            threat_velocities = np.gradient(deviations, dt)
        else:
            threat_velocities = np.zeros_like(deviations)

        # Max threat velocity
        max_threat_velocity = float(np.max(np.abs(threat_velocities)))

        # Compute curvature statistics along the curve
        curvature = self.compute_curve_curvature(gamma)
        max_curvature = float(np.max(curvature))
        mean_curvature = float(np.mean(curvature))

        # Convert rhythm pattern to string
        rhythm_string = "".join(str(r) for r in rhythm_pattern)

        return {
            "intrusion_detected": len(intrusion_events) > 0,
            "intrusion_count": len(intrusion_events),
            "intrusion_events": intrusion_events,
            "deviations": deviations.tolist(),
            "threat_velocities": threat_velocities.tolist(),
            "max_threat_velocity": max_threat_velocity,
            "rhythm_pattern": rhythm_string,
            "on_path_ratio": sum(rhythm_pattern) / len(rhythm_pattern),
            "epsilon_snap": self.epsilon_snap,
            "max_curvature": max_curvature,
            "mean_curvature": mean_curvature,
        }

    def validate_key_chain(
        self,
        chain: List[Tuple[Polyhedron, bytes]],
        initial_key: bytes = None
    ) -> dict:
        """
        Validate a key derivation chain for integrity.

        Recomputes the HMAC chain and verifies each step.

        Args:
            chain: List of (Polyhedron, key) tuples
            initial_key: Expected initial key

        Returns:
            Validation result dict
        """
        import hmac

        if initial_key is None:
            initial_key = self.seed_key

        K = initial_key
        valid_count = 0
        invalid_steps = []

        for i, (P, expected_key) in enumerate(chain):
            # Recompute expected key
            K_computed = hmac.new(K, P.serialize(), hashlib.sha256).digest()

            if K_computed == expected_key:
                valid_count += 1
            else:
                invalid_steps.append({
                    "step": i,
                    "polyhedron": P.name,
                    "expected": expected_key.hex()[:16] + "...",
                    "computed": K_computed.hex()[:16] + "...",
                })

            K = expected_key  # Continue with claimed key

        return {
            "valid": len(invalid_steps) == 0,
            "valid_count": valid_count,
            "total_steps": len(chain),
            "invalid_steps": invalid_steps,
            "integrity_ratio": valid_count / len(chain) if chain else 0,
        }

    # Alias for verify_chain_integrity
    def verify_chain_integrity(
        self,
        chain: List[Tuple[Polyhedron, bytes]],
        initial_key: bytes = None
    ) -> dict:
        """Alias for validate_key_chain."""
        return self.validate_key_chain(chain, initial_key)

    def simulate_attack(
        self,
        attack_type: str = "deviation",
        attack_magnitude: float = 1.0,
        attack_position: float = 0.5
    ) -> dict:
        """
        Simulate an attack and measure detection response.

        Attack Types:
        - "deviation": Off-path state injection
        - "skip": Attempt to skip Hamiltonian path steps
        - "curvature": Inject high-curvature kink

        Args:
            attack_type: Type of attack to simulate
            attack_magnitude: Strength of attack
            attack_position: Position t ∈ [0,1] along path

        Returns:
            Attack simulation results
        """
        gamma = self.compute_geodesic_curve(n_points=100)
        n = len(gamma)

        # Generate legitimate states along the path
        states = [gamma[i].copy() for i in range(n)]

        attack_idx = int(attack_position * (n - 1))

        if attack_type == "deviation":
            # Inject off-path state
            perturbation = np.random.randn(6) * attack_magnitude
            states[attack_idx] = gamma[attack_idx] + perturbation

        elif attack_type == "skip":
            # Try to skip ahead (use wrong position)
            skip_target = min(attack_idx + int(10 * attack_magnitude), n - 1)
            states[attack_idx] = gamma[skip_target]

        elif attack_type == "curvature":
            # Inject sharp curvature kink
            for i in range(max(0, attack_idx - 2), min(n, attack_idx + 3)):
                states[i] = gamma[i] + np.sin(i * attack_magnitude) * attack_magnitude * 0.5

        # Run intrusion detection
        timestamps = np.linspace(0, 1, n)
        detection = self.detect_intrusion(states, timestamps)

        return {
            "attack_type": attack_type,
            "attack_magnitude": attack_magnitude,
            "attack_position": attack_position,
            "attack_detected": detection["intrusion_detected"],
            "detection_details": detection,
        }

    def get_path_summary(self) -> str:
        """Get summary of the Hamiltonian path."""
        lines = ["Polyhedral Hamiltonian Path:"]
        lines.append("=" * 50)

        for i, idx in enumerate(self.hamiltonian_path):
            P = self.polyhedra[idx]
            chi = P.euler_characteristic()
            lines.append(
                f"{i+1:2d}. {P.name:30s} "
                f"V={P.vertices:2d} E={P.edges:2d} F={P.faces:2d} "
                f"χ={chi:2d} g={P.genus}"
            )

        return "\n".join(lines)

    def get_defense_equations(self) -> str:
        """Return formal equations for the PHDM."""
        return r"""
Polyhedral Hamiltonian Defense Manifold (PHDM)
═══════════════════════════════════════════════════════

1. HAMILTONIAN PATH
   H = (P₁, P₂, ..., Pₙ)
   A sequence touching each polyhedron exactly once.

2. SEQUENTIAL KEY DERIVATION
   K₀ = seed
   K_{i+1} = HMAC-SHA256(K_i, Serialize(P_i))

   Security: Skipping ahead breaks the chain.

3. GEODESIC EMBEDDING
   γ : [0,1] → ℝ⁶   (Langues manifold)
   γ(t_i) ≈ centroid(P_i)   for Hamiltonian order

   Interpolation: Cubic B-spline through centroids

4. CURVATURE MEASURE
   κ(t) = |γ''(t)| / |γ'(t)|²

   High curvature = potential attack signature

5. DEVIATION MEASURE
   d(state, t) = dist_Langues(state, γ(t))

   Snap Condition: d(state, t) > ε_snap ⟹ INTRUSION

6. THREAT VELOCITY
   v_threat(t) = d/dt[d(state, γ(t))]

   Attack acceleration visible as velocity spikes

7. 1-0 RHYTHM PATTERN
   R(t) = { 1  if d(state, t) ≤ ε_snap  (on-path)
          { 0  if d(state, t) > ε_snap  (off-path)

   Attack visibility: 1 1 1 0 0 1 1 ... (disruption pattern)

═══════════════════════════════════════════════════════

Defense Properties:
- Predictable topology: known valid route
- Observable curvature: measurable deviation
- Sequential dependency: cryptographic binding
- Geometric verifiability: auditable chain
"""

    def __repr__(self) -> str:
        return (
            f"PolyhedralHamiltonianDefense("
            f"n_polyhedra={len(self.polyhedra)}, "
            f"ε_snap={self.epsilon_snap})"
        )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Core classes
    "HarmonicScalingLaw",
    "ScalingMode",
    "PQContextCommitment",
    "BehavioralRiskComponents",
    "SecurityDecisionEngine",

    # Langues Metric Tensor
    "LanguesMetricTensor",
    "CouplingMode",
    "create_coupling_matrix",
    "create_baseline_metric",
    "get_epsilon_threshold",
    "compute_langues_metric_distance",
    "validate_langues_metric_stability",

    # Fractal Dimension Analysis
    "FractalDimensionAnalyzer",

    # Hyper-Torus Manifold (N-Dimensional Geometric Ledger)
    "HyperTorusManifold",
    "DimensionMode",

    # Grand Unified Symphonic Cipher Formula
    "GrandUnifiedSymphonicCipher",

    # Differential Cryptography Framework
    "DifferentialCryptographyFramework",

    # Polyhedral Hamiltonian Defense Manifold
    "Polyhedron",
    "PolyhedralHamiltonianDefense",

    # Hyperbolic geometry
    "hyperbolic_distance_poincare",
    "find_nearest_trusted_realm",

    # Convenience functions
    "quantum_resistant_harmonic_scaling",
    "create_context_commitment",
    "verify_test_vectors",

    # Constants
    "DEFAULT_ALPHA",
    "DEFAULT_BETA",
    "HARMONIC_RATIO_R",
    "PHI",
    "LANGUES_DIMENSIONS",
    "DEFAULT_EPSILON",
    "EPSILON_THRESHOLD",
    "EPSILON_THRESHOLD_HARMONIC",
    "EPSILON_THRESHOLD_UNIFORM",
    "EPSILON_THRESHOLD_NORMALIZED",
    "PQ_CONTEXT_COMMITMENT_SIZE",
    "TEST_VECTORS",
]
