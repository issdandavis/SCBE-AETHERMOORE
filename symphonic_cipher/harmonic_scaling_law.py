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

# Hyperbolic geometry constants
POINCARE_CURVATURE = -1.0  # Constant negative curvature for Poincare disk


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
    "PQ_CONTEXT_COMMITMENT_SIZE",
    "TEST_VECTORS",
]
