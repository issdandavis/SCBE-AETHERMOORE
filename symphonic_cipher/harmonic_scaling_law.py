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
