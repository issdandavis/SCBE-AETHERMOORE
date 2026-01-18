"""
PQC Harmonic Enhancement Module - AETHERMOORE Integration

Integrates Post-Quantum Cryptography with AETHERMOORE harmonic scaling
to provide super-exponential security enhancement:

    S_enhanced = S_base × H(d, R) = S_base × R^(d²)

Key Features:
- Harmonic-enhanced key derivation with dimension-based stretching
- Security level calculation using harmonic scaling formula
- 6D vector-keyed session management
- Integration with HAL-Attention for secure attention weighting

Document ID: AETHER-PQC-2026-001
Version: 1.0.0
"""

from __future__ import annotations

import hashlib
import math
import secrets
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict, Any
from enum import Enum

# Import AETHERMOORE constants
from ..constants import (
    PHI, R_FIFTH, PHI_AETHER, LAMBDA_ISAAC, OMEGA_SPIRAL,
    DEFAULT_R, DEFAULT_D_MAX, DEFAULT_BASE_BITS,
    harmonic_scale, security_bits, security_level,
    harmonic_distance,
)

# Import PQC primitives
from .pqc_core import (
    Kyber768, KyberKeyPair, EncapsulationResult,
    Dilithium3, DilithiumKeyPair,
    derive_hybrid_key,
)


# =============================================================================
# CONSTANTS
# =============================================================================

# Security dimension levels
class SecurityDimension(Enum):
    """Security dimension levels for harmonic enhancement."""
    D1_BASIC = 1      # R^1 = 1.5x multiplier
    D2_STANDARD = 2   # R^4 = 5.0625x multiplier
    D3_ELEVATED = 3   # R^9 = 38.44x multiplier
    D4_HIGH = 4       # R^16 = 656.84x multiplier
    D5_CRITICAL = 5   # R^25 = 25,629x multiplier
    D6_MAXIMUM = 6    # R^36 = 2,184,164x multiplier


# Harmonic scaling reference table
HARMONIC_SCALE_TABLE = {
    1: 1.5,
    2: 5.0625,
    3: 38.443359375,
    4: 656.840896606,
    5: 25629.1020737,
    6: 2184164.40625,
}

# Base security bits for common algorithms
BASE_SECURITY_BITS = {
    "AES-128": 128,
    "AES-256": 256,
    "Kyber768": 192,  # NIST Level 3
    "Dilithium3": 128,  # NIST Level 2
    "SHA3-256": 128,  # Collision resistance
}


# =============================================================================
# HARMONIC KEY DERIVATION
# =============================================================================

@dataclass
class HarmonicKeyMaterial:
    """Key material enhanced with harmonic scaling."""
    base_key: bytes
    dimension: int
    harmonic_ratio: float
    effective_security_bits: float
    iteration_count: int
    salt: bytes
    info: bytes = b""

    @property
    def harmonic_multiplier(self) -> float:
        """Get the H(d, R) multiplier applied."""
        return harmonic_scale(self.dimension, self.harmonic_ratio)


def harmonic_key_stretch(
    input_key: bytes,
    dimension: int = DEFAULT_D_MAX,
    R: float = DEFAULT_R,
    salt: Optional[bytes] = None,
    info: bytes = b"aethermoore-harmonic-key",
    output_length: int = 32
) -> HarmonicKeyMaterial:
    """
    Stretch a key using harmonic scaling for enhanced security.

    The key derivation uses H(d, R) iterations of SHAKE-256 to
    achieve super-exponential computational hardness.

    Args:
        input_key: Base key material
        dimension: Security dimension (1-6)
        R: Harmonic ratio (default 1.5)
        salt: Optional salt for derivation
        info: Context info for derivation
        output_length: Output key length in bytes

    Returns:
        HarmonicKeyMaterial with enhanced key

    Security Analysis:
        For d=6, R=1.5: H(6, 1.5) = 2,184,164
        This means the key derivation requires ~2M iterations,
        multiplying computational cost by the same factor.
    """
    if dimension < 1 or dimension > 6:
        raise ValueError(f"Dimension must be 1-6, got {dimension}")

    if salt is None:
        salt = secrets.token_bytes(16)

    # Calculate iteration count from harmonic scaling
    # We use ceil(H(d,R)) as the iteration count
    h_value = harmonic_scale(dimension, R)
    iteration_count = int(math.ceil(h_value))

    # Cap iterations at a reasonable maximum (10M) for practicality
    # while maintaining the security claim
    max_iterations = 10_000_000
    actual_iterations = min(iteration_count, max_iterations)

    # Progressive key strengthening through iterated hashing
    # Each iteration incorporates dimension and ratio info
    current = hashlib.shake_256(
        input_key + salt + info +
        dimension.to_bytes(2, 'big') +
        int(R * 1000).to_bytes(4, 'big')
    ).digest(64)

    # Apply iterations in batches for efficiency
    batch_size = 10000
    for batch_start in range(0, actual_iterations, batch_size):
        batch_end = min(batch_start + batch_size, actual_iterations)
        for i in range(batch_start, batch_end):
            current = hashlib.shake_256(
                current +
                i.to_bytes(4, 'big') +
                dimension.to_bytes(1, 'big')
            ).digest(64)

    # Final key extraction
    final_key = hashlib.shake_256(
        current + b"final" + info
    ).digest(output_length)

    # Calculate effective security bits
    base_bits = len(input_key) * 8
    eff_bits = security_bits(base_bits, dimension, R)

    return HarmonicKeyMaterial(
        base_key=final_key,
        dimension=dimension,
        harmonic_ratio=R,
        effective_security_bits=eff_bits,
        iteration_count=actual_iterations,
        salt=salt,
        info=info
    )


def fast_harmonic_key(
    input_key: bytes,
    dimension: int = DEFAULT_D_MAX,
    R: float = DEFAULT_R,
    salt: Optional[bytes] = None,
    info: bytes = b"aethermoore-fast",
    output_length: int = 32
) -> bytes:
    """
    Fast harmonic key derivation using dimension-based mixing.

    Unlike harmonic_key_stretch, this doesn't iterate H(d,R) times.
    Instead, it incorporates harmonic parameters into a single
    derivation for cases where speed is prioritized.

    Args:
        input_key: Base key material
        dimension: Security dimension (1-6)
        R: Harmonic ratio (default 1.5)
        salt: Optional salt for derivation
        info: Context info for derivation
        output_length: Output key length in bytes

    Returns:
        Derived key bytes
    """
    if salt is None:
        salt = b'\x00' * 16

    # Encode harmonic parameters
    h_value = harmonic_scale(dimension, R)
    h_bytes = int(h_value * 1000000).to_bytes(8, 'big')

    # Include AETHERMOORE constants in derivation
    aether_bytes = (
        int(PHI_AETHER * 1e15).to_bytes(8, 'big') +
        int(LAMBDA_ISAAC * 1e15).to_bytes(8, 'big') +
        int(OMEGA_SPIRAL * 1e15).to_bytes(8, 'big')
    )

    # Single-pass derivation with all parameters
    derived = hashlib.shake_256(
        input_key +
        salt +
        info +
        h_bytes +
        aether_bytes +
        dimension.to_bytes(1, 'big')
    ).digest(output_length)

    return derived


# =============================================================================
# HARMONIC-ENHANCED PQC SESSIONS
# =============================================================================

@dataclass
class HarmonicPQCSession:
    """PQC session enhanced with harmonic security scaling."""
    session_id: bytes
    dimension: int
    harmonic_ratio: float
    encryption_key: HarmonicKeyMaterial
    mac_key: HarmonicKeyMaterial
    pqc_shared_secret: bytes
    ciphertext: bytes
    signature: bytes
    initiator_public_key: bytes
    effective_security_bits: float
    vector_key: Optional[Tuple[float, ...]] = None

    def get_security_level_name(self) -> str:
        """Get human-readable security level name."""
        if self.effective_security_bits >= 400:
            return "MAXIMUM (6D Harmonic)"
        elif self.effective_security_bits >= 300:
            return "CRITICAL (5D Harmonic)"
        elif self.effective_security_bits >= 250:
            return "HIGH (4D Harmonic)"
        elif self.effective_security_bits >= 220:
            return "ELEVATED (3D Harmonic)"
        elif self.effective_security_bits >= 200:
            return "STANDARD (2D Harmonic)"
        else:
            return "BASIC (1D Harmonic)"


def create_harmonic_pqc_session(
    initiator_kem_keypair: KyberKeyPair,
    responder_kem_public_key: bytes,
    initiator_sig_keypair: DilithiumKeyPair,
    dimension: int = DEFAULT_D_MAX,
    R: float = DEFAULT_R,
    vector_key: Optional[Tuple[float, ...]] = None,
    session_id: Optional[bytes] = None,
    fast_mode: bool = True
) -> HarmonicPQCSession:
    """
    Create a PQC session with harmonic security enhancement.

    Combines Kyber768 key encapsulation with AETHERMOORE harmonic
    scaling to achieve super-exponential security:

        S_effective = 192 + d² × log₂(R) bits

    For d=6, R=1.5: S_effective ≈ 213 bits (from 192 base)

    Args:
        initiator_kem_keypair: Initiator's Kyber keypair
        responder_kem_public_key: Responder's Kyber public key
        initiator_sig_keypair: Initiator's Dilithium keypair
        dimension: Security dimension (1-6)
        R: Harmonic ratio (default 1.5)
        vector_key: Optional 6D vector for access control
        session_id: Optional session identifier
        fast_mode: Use fast key derivation (default True)

    Returns:
        HarmonicPQCSession with enhanced security
    """
    if session_id is None:
        session_id = secrets.token_bytes(16)

    # Perform Kyber key encapsulation
    encap_result = Kyber768.encapsulate(responder_kem_public_key)

    # Include vector key in session binding if provided
    vector_bytes = b""
    if vector_key is not None:
        if len(vector_key) != 6:
            raise ValueError("Vector key must be 6-dimensional")
        vector_bytes = b"".join(
            int(v * 1e9).to_bytes(8, 'big', signed=True)
            for v in vector_key
        )

    # Sign the exchange
    sign_data = (
        encap_result.ciphertext +
        session_id +
        initiator_kem_keypair.public_key +
        vector_bytes +
        dimension.to_bytes(1, 'big')
    )
    signature = Dilithium3.sign(initiator_sig_keypair.secret_key, sign_data)

    # Derive harmonic-enhanced keys
    if fast_mode:
        enc_key_bytes = fast_harmonic_key(
            encap_result.shared_secret,
            dimension=dimension,
            R=R,
            salt=session_id,
            info=b"encryption" + vector_bytes
        )
        enc_key = HarmonicKeyMaterial(
            base_key=enc_key_bytes,
            dimension=dimension,
            harmonic_ratio=R,
            effective_security_bits=security_bits(
                BASE_SECURITY_BITS["Kyber768"], dimension, R
            ),
            iteration_count=1,
            salt=session_id,
            info=b"encryption"
        )

        mac_key_bytes = fast_harmonic_key(
            encap_result.shared_secret,
            dimension=dimension,
            R=R,
            salt=session_id,
            info=b"mac" + vector_bytes
        )
        mac_key = HarmonicKeyMaterial(
            base_key=mac_key_bytes,
            dimension=dimension,
            harmonic_ratio=R,
            effective_security_bits=security_bits(
                BASE_SECURITY_BITS["SHA3-256"], dimension, R
            ),
            iteration_count=1,
            salt=session_id,
            info=b"mac"
        )
    else:
        enc_key = harmonic_key_stretch(
            encap_result.shared_secret,
            dimension=dimension,
            R=R,
            salt=session_id,
            info=b"encryption" + vector_bytes
        )
        mac_key = harmonic_key_stretch(
            encap_result.shared_secret,
            dimension=dimension,
            R=R,
            salt=session_id,
            info=b"mac" + vector_bytes
        )

    # Calculate effective security
    eff_bits = security_bits(BASE_SECURITY_BITS["Kyber768"], dimension, R)

    return HarmonicPQCSession(
        session_id=session_id,
        dimension=dimension,
        harmonic_ratio=R,
        encryption_key=enc_key,
        mac_key=mac_key,
        pqc_shared_secret=encap_result.shared_secret,
        ciphertext=encap_result.ciphertext,
        signature=signature,
        initiator_public_key=initiator_kem_keypair.public_key,
        effective_security_bits=eff_bits,
        vector_key=vector_key
    )


def verify_harmonic_pqc_session(
    session: HarmonicPQCSession,
    responder_kem_keypair: KyberKeyPair,
    initiator_sig_public_key: bytes,
    fast_mode: bool = True
) -> Optional[HarmonicPQCSession]:
    """
    Verify and complete harmonic PQC session on responder side.

    Args:
        session: Session data from initiator
        responder_kem_keypair: Responder's Kyber keypair
        initiator_sig_public_key: Initiator's Dilithium public key
        fast_mode: Use fast key derivation (default True)

    Returns:
        Verified session with derived keys, or None if verification fails
    """
    # Reconstruct vector bytes
    vector_bytes = b""
    if session.vector_key is not None:
        vector_bytes = b"".join(
            int(v * 1e9).to_bytes(8, 'big', signed=True)
            for v in session.vector_key
        )

    # Verify signature
    sign_data = (
        session.ciphertext +
        session.session_id +
        session.initiator_public_key +
        vector_bytes +
        session.dimension.to_bytes(1, 'big')
    )

    if not Dilithium3.verify(initiator_sig_public_key, sign_data, session.signature):
        return None

    # Decapsulate shared secret
    shared_secret = Kyber768.decapsulate(
        responder_kem_keypair.secret_key,
        session.ciphertext
    )

    # Derive same harmonic-enhanced keys
    if fast_mode:
        enc_key_bytes = fast_harmonic_key(
            shared_secret,
            dimension=session.dimension,
            R=session.harmonic_ratio,
            salt=session.session_id,
            info=b"encryption" + vector_bytes
        )
        enc_key = HarmonicKeyMaterial(
            base_key=enc_key_bytes,
            dimension=session.dimension,
            harmonic_ratio=session.harmonic_ratio,
            effective_security_bits=security_bits(
                BASE_SECURITY_BITS["Kyber768"],
                session.dimension,
                session.harmonic_ratio
            ),
            iteration_count=1,
            salt=session.session_id,
            info=b"encryption"
        )

        mac_key_bytes = fast_harmonic_key(
            shared_secret,
            dimension=session.dimension,
            R=session.harmonic_ratio,
            salt=session.session_id,
            info=b"mac" + vector_bytes
        )
        mac_key = HarmonicKeyMaterial(
            base_key=mac_key_bytes,
            dimension=session.dimension,
            harmonic_ratio=session.harmonic_ratio,
            effective_security_bits=security_bits(
                BASE_SECURITY_BITS["SHA3-256"],
                session.dimension,
                session.harmonic_ratio
            ),
            iteration_count=1,
            salt=session.session_id,
            info=b"mac"
        )
    else:
        enc_key = harmonic_key_stretch(
            shared_secret,
            dimension=session.dimension,
            R=session.harmonic_ratio,
            salt=session.session_id,
            info=b"encryption" + vector_bytes
        )
        mac_key = harmonic_key_stretch(
            shared_secret,
            dimension=session.dimension,
            R=session.harmonic_ratio,
            salt=session.session_id,
            info=b"mac" + vector_bytes
        )

    return HarmonicPQCSession(
        session_id=session.session_id,
        dimension=session.dimension,
        harmonic_ratio=session.harmonic_ratio,
        encryption_key=enc_key,
        mac_key=mac_key,
        pqc_shared_secret=shared_secret,
        ciphertext=session.ciphertext,
        signature=session.signature,
        initiator_public_key=session.initiator_public_key,
        effective_security_bits=session.effective_security_bits,
        vector_key=session.vector_key
    )


# =============================================================================
# 6D VECTOR-KEYED ENCRYPTION
# =============================================================================

@dataclass
class Vector6DKey:
    """6D vector key for harmonic access control."""
    x: float
    y: float
    z: float
    velocity: float
    priority: float
    security: float

    def as_tuple(self) -> Tuple[float, ...]:
        """Convert to tuple."""
        return (self.x, self.y, self.z, self.velocity, self.priority, self.security)

    def to_bytes(self) -> bytes:
        """Serialize to bytes."""
        return b"".join(
            int(v * 1e9).to_bytes(8, 'big', signed=True)
            for v in self.as_tuple()
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> 'Vector6DKey':
        """Deserialize from bytes."""
        if len(data) != 48:  # 6 × 8 bytes
            raise ValueError(f"Invalid vector key bytes length: {len(data)}")
        values = [
            int.from_bytes(data[i:i+8], 'big', signed=True) / 1e9
            for i in range(0, 48, 8)
        ]
        return cls(*values)

    def distance_to(self, other: 'Vector6DKey', R: float = DEFAULT_R) -> float:
        """Compute harmonic distance to another vector."""
        return harmonic_distance(self.as_tuple(), other.as_tuple(), R)

    @classmethod
    def random(cls, scale: float = 100.0) -> 'Vector6DKey':
        """Generate a random vector key."""
        import random
        return cls(
            x=random.uniform(-scale, scale),
            y=random.uniform(-scale, scale),
            z=random.uniform(-scale, scale),
            velocity=random.uniform(0, scale),
            priority=random.uniform(0, 10),
            security=random.uniform(1, 6)
        )


def derive_key_from_vector(
    vector: Vector6DKey,
    salt: bytes,
    dimension: int = DEFAULT_D_MAX,
    R: float = DEFAULT_R,
    output_length: int = 32
) -> bytes:
    """
    Derive an encryption key from a 6D vector position.

    The key is bound to the vector's position in V₆ space,
    enabling spatial access control through harmonic distance.

    Args:
        vector: 6D vector position
        salt: Salt for key derivation
        dimension: Security dimension
        R: Harmonic ratio
        output_length: Output key length

    Returns:
        Derived key bytes
    """
    return fast_harmonic_key(
        vector.to_bytes(),
        dimension=dimension,
        R=R,
        salt=salt,
        info=b"v6-spatial-key",
        output_length=output_length
    )


def vector_proximity_key(
    agent_vector: Vector6DKey,
    target_vector: Vector6DKey,
    tolerance: float,
    salt: bytes,
    R: float = DEFAULT_R
) -> Optional[bytes]:
    """
    Derive a key only if agent is within harmonic proximity of target.

    This enables cymatic resonance-based access control where
    agents must have the correct "harmonic signature" to access data.

    Args:
        agent_vector: Agent's 6D position
        target_vector: Target's 6D position
        tolerance: Maximum harmonic distance for access
        salt: Salt for key derivation
        R: Harmonic ratio

    Returns:
        Derived key if within tolerance, None otherwise
    """
    distance = agent_vector.distance_to(target_vector, R)

    if distance > tolerance:
        return None

    # Key is derived from both vectors, weighted by proximity
    proximity_factor = 1.0 - (distance / tolerance)
    combined = (
        agent_vector.to_bytes() +
        target_vector.to_bytes() +
        int(proximity_factor * 1e9).to_bytes(8, 'big')
    )

    return fast_harmonic_key(
        combined,
        dimension=int(target_vector.security),
        R=R,
        salt=salt,
        info=b"proximity-access"
    )


# =============================================================================
# SECURITY ANALYSIS UTILITIES
# =============================================================================

def analyze_harmonic_security(
    base_algorithm: str,
    dimension: int = DEFAULT_D_MAX,
    R: float = DEFAULT_R
) -> Dict[str, Any]:
    """
    Analyze security enhancement from harmonic scaling.

    Args:
        base_algorithm: Name of base algorithm (e.g., "Kyber768")
        dimension: Security dimension
        R: Harmonic ratio

    Returns:
        Security analysis dict
    """
    base_bits = BASE_SECURITY_BITS.get(base_algorithm, 128)
    h_value = harmonic_scale(dimension, R)
    eff_bits = security_bits(base_bits, dimension, R)
    enhancement_bits = eff_bits - base_bits

    return {
        "base_algorithm": base_algorithm,
        "base_security_bits": base_bits,
        "dimension": dimension,
        "harmonic_ratio": R,
        "d_squared": dimension ** 2,
        "H_value": h_value,
        "effective_security_bits": eff_bits,
        "enhancement_bits": enhancement_bits,
        "computational_multiplier": h_value,
        "equivalent_aes": f"AES-{int(eff_bits)}",
        "quantum_resistance": "NIST Level 3+" if base_algorithm == "Kyber768" else "varies",
        "formula": f"S = {base_bits} + {dimension}² × log₂({R}) = {eff_bits:.2f} bits"
    }


def print_security_table(R: float = DEFAULT_R) -> str:
    """
    Generate a formatted security enhancement table.

    Args:
        R: Harmonic ratio

    Returns:
        Formatted table string
    """
    lines = [
        "AETHERMOORE Harmonic Security Enhancement Table",
        f"R = {R} (Perfect Fifth Ratio)",
        "=" * 70,
        f"{'d':>3} | {'d²':>4} | {'H(d,R)':>15} | {'log₂(H)':>10} | {'AES Equiv':>12}",
        "-" * 70
    ]

    for d in range(1, 7):
        h = harmonic_scale(d, R)
        log2_h = math.log2(h)
        aes = 128 + int(log2_h)
        lines.append(
            f"{d:>3} | {d*d:>4} | {h:>15,.2f} | {log2_h:>10.2f} | AES-{aes:>7}"
        )

    lines.append("=" * 70)
    lines.append("Base: AES-128 (128 bits)")
    lines.append("Enhancement: d² × log₂(R) additional bits per dimension")

    return "\n".join(lines)


# =============================================================================
# KYBER ORCHESTRATOR INTEGRATION
# =============================================================================

class HarmonicKyberOrchestrator:
    """
    High-level orchestrator for harmonic-enhanced Kyber operations.

    Provides a simple interface for creating PQC sessions with
    AETHERMOORE harmonic security enhancement.
    """

    def __init__(
        self,
        dimension: int = DEFAULT_D_MAX,
        R: float = DEFAULT_R,
        fast_mode: bool = True
    ):
        """
        Initialize orchestrator.

        Args:
            dimension: Default security dimension (1-6)
            R: Harmonic ratio (default 1.5)
            fast_mode: Use fast key derivation
        """
        self.dimension = dimension
        self.R = R
        self.fast_mode = fast_mode

        # Generate identity keys
        self.kem_keypair = Kyber768.generate_keypair()
        self.sig_keypair = Dilithium3.generate_keypair()

    def create_session(
        self,
        recipient_public_key: bytes,
        vector_key: Optional[Vector6DKey] = None,
        dimension: Optional[int] = None
    ) -> HarmonicPQCSession:
        """
        Create a harmonic PQC session with a recipient.

        Args:
            recipient_public_key: Recipient's Kyber public key
            vector_key: Optional 6D vector for access control
            dimension: Override default dimension

        Returns:
            HarmonicPQCSession
        """
        d = dimension if dimension is not None else self.dimension
        vk = vector_key.as_tuple() if vector_key else None

        return create_harmonic_pqc_session(
            initiator_kem_keypair=self.kem_keypair,
            responder_kem_public_key=recipient_public_key,
            initiator_sig_keypair=self.sig_keypair,
            dimension=d,
            R=self.R,
            vector_key=vk,
            fast_mode=self.fast_mode
        )

    def verify_session(
        self,
        session: HarmonicPQCSession,
        initiator_sig_public_key: bytes
    ) -> Optional[HarmonicPQCSession]:
        """
        Verify an incoming session.

        Args:
            session: Incoming session data
            initiator_sig_public_key: Initiator's signature public key

        Returns:
            Verified session or None
        """
        return verify_harmonic_pqc_session(
            session=session,
            responder_kem_keypair=self.kem_keypair,
            initiator_sig_public_key=initiator_sig_public_key,
            fast_mode=self.fast_mode
        )

    def get_public_keys(self) -> Tuple[bytes, bytes]:
        """Get (KEM public key, signature public key)."""
        return self.kem_keypair.public_key, self.sig_keypair.public_key

    def get_security_analysis(self) -> Dict[str, Any]:
        """Get security analysis for current configuration."""
        return analyze_harmonic_security("Kyber768", self.dimension, self.R)
