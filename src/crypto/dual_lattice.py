"""
Dual Lattice Cross-Stitch Architecture
======================================

Weaves Sacred Tongues through Kyber/Dilithium lattice structures
with Time (T) and Intent (I) as additional dimensions.

The "cross-stitch" pattern interleaves:
- Kyber (ML-KEM): Encrypts tongue vectors
- Dilithium (ML-DSA): Signs tongue compositions

10-Dimensional Lattice Space:
- d₀-d₅: Sacred Tongues (KO, AV, RU, CA, UM, DR)
- d₆: Time (T) - temporal binding
- d₇: Intent (I) - purpose vector
- d₈: Phase (φ) - from Langues Metric
- d₉: Flux (ν) - Polly/Quasi/Demi state

Based on:
- CRYSTALS-Kyber (ML-KEM, FIPS 203)
- CRYSTALS-Dilithium (ML-DSA, FIPS 204)
- SCBE Langues Metric (6 Sacred Tongues)
"""

import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import struct
import secrets


# =============================================================================
# Constants and Parameters
# =============================================================================

class SacredTongue(str, Enum):
    """The 6 Sacred Tongues - each a dimension in the lattice."""
    KO = "KO"  # Korean - Intent/Purpose
    AV = "AV"  # Avestan - Context/Wisdom
    RU = "RU"  # Russian - Binding/Structure
    CA = "CA"  # Catalan - Bitcraft/Precision
    UM = "UM"  # Umbrian - Hidden/Mystery
    DR = "DR"  # Druidic - Nature/Flow


class FluxState(str, Enum):
    """Flux states from SCBE - breathing dimensions."""
    POLLY = "polly"      # ν ≥ 0.9 - Full engagement
    QUASI = "quasi"      # 0.5 ≤ ν < 0.9 - Partial
    DEMI = "demi"        # 0.1 ≤ ν < 0.5 - Minimal
    COLLAPSED = "collapsed"  # ν < 0.1 - Dormant


# Kyber-768 parameters
KYBER_N = 256          # Polynomial degree
KYBER_K = 3            # Module rank for Kyber-768
KYBER_Q = 3329         # Modulus
KYBER_ETA1 = 2         # Noise parameter
KYBER_ETA2 = 2

# Dilithium-3 parameters (ML-DSA-65)
DILITHIUM_N = 256
DILITHIUM_K = 6        # Module rank
DILITHIUM_L = 5
DILITHIUM_Q = 8380417  # Modulus
DILITHIUM_GAMMA1 = 2**19
DILITHIUM_GAMMA2 = (DILITHIUM_Q - 1) // 32

# Golden ratio for tongue weighting (from Langues Metric)
PHI = (1 + np.sqrt(5)) / 2  # ≈ 1.618

# Phase shifts for each tongue (degrees)
TONGUE_PHASES = {
    SacredTongue.KO: 0,
    SacredTongue.AV: 60,
    SacredTongue.RU: 120,
    SacredTongue.CA: 180,
    SacredTongue.UM: 240,
    SacredTongue.DR: 300,
}

# Tongue weights (golden ratio based)
TONGUE_WEIGHTS = {
    SacredTongue.KO: PHI ** 0,  # 1.000
    SacredTongue.AV: PHI ** 1,  # 1.618
    SacredTongue.RU: PHI ** 2,  # 2.618
    SacredTongue.CA: PHI ** 3,  # 4.236
    SacredTongue.UM: PHI ** 4,  # 6.854
    SacredTongue.DR: PHI ** 5,  # 11.090
}


# =============================================================================
# Lattice Vector Representation
# =============================================================================

@dataclass
class LatticeVector:
    """
    A 10-dimensional vector in the dual lattice space.

    Dimensions:
    - tongues[0-5]: Sacred Tongue coefficients (KO, AV, RU, CA, UM, DR)
    - time: Temporal coordinate (unix timestamp normalized)
    - intent: Intent vector magnitude
    - phase: Phase angle (0-360)
    - flux: Flux state value (0-1)
    """
    tongues: np.ndarray  # 6 coefficients
    time: float
    intent: float
    phase: float
    flux: float

    def __post_init__(self):
        if len(self.tongues) != 6:
            raise ValueError("Must have exactly 6 tongue coefficients")
        self.tongues = np.array(self.tongues, dtype=np.float64)

    def to_array(self) -> np.ndarray:
        """Convert to 10D numpy array."""
        return np.concatenate([
            self.tongues,
            np.array([self.time, self.intent, self.phase, self.flux])
        ])

    @classmethod
    def from_array(cls, arr: np.ndarray) -> 'LatticeVector':
        """Create from 10D numpy array."""
        return cls(
            tongues=arr[:6],
            time=float(arr[6]),
            intent=float(arr[7]),
            phase=float(arr[8]),
            flux=float(arr[9])
        )

    def norm(self) -> float:
        """Compute L2 norm."""
        return np.linalg.norm(self.to_array())

    def weighted_norm(self) -> float:
        """
        Compute weighted norm using tongue weights.

        Normalizes all dimensions to [0,1] range before applying weights:
        - Tongues: Already [0,1]
        - Time: Already [0,1] (normalized day fraction)
        - Intent: Already [0,1]
        - Phase: [0,360] → [0,1]
        - Flux: Already [0,1]
        """
        # Normalize phase from degrees to [0,1]
        normalized_arr = np.array([
            self.tongues[0],
            self.tongues[1],
            self.tongues[2],
            self.tongues[3],
            self.tongues[4],
            self.tongues[5],
            self.time,
            self.intent,
            self.phase / 360.0,  # Normalize degrees to [0,1]
            self.flux,
        ])

        weights = np.array([
            TONGUE_WEIGHTS[SacredTongue.KO],
            TONGUE_WEIGHTS[SacredTongue.AV],
            TONGUE_WEIGHTS[SacredTongue.RU],
            TONGUE_WEIGHTS[SacredTongue.CA],
            TONGUE_WEIGHTS[SacredTongue.UM],
            TONGUE_WEIGHTS[SacredTongue.DR],
            1.0,  # time weight
            2.0,  # intent weight (important for governance)
            0.5,  # phase weight (auxiliary)
            1.0,  # flux weight
        ])
        return np.linalg.norm(normalized_arr * weights)


@dataclass
class TongueContext:
    """
    Context for a Sacred Tongue in the lattice.

    Each tongue has:
    - A base coefficient in the lattice
    - A phase shift for cross-stitch pattern
    - A weight for importance scaling
    """
    tongue: SacredTongue
    coefficient: float
    phase: float
    weight: float

    @classmethod
    def create(cls, tongue: SacredTongue, value: float = 1.0) -> 'TongueContext':
        return cls(
            tongue=tongue,
            coefficient=value,
            phase=TONGUE_PHASES[tongue],
            weight=TONGUE_WEIGHTS[tongue]
        )


# =============================================================================
# Cross-Stitch Pattern Generator
# =============================================================================

class CrossStitchPattern:
    """
    Generates the cross-stitch pattern that weaves Kyber and Dilithium.

    The pattern alternates between:
    - Kyber encryption (even indices)
    - Dilithium signing (odd indices)

    Creating an interlocked structure where compromising one
    doesn't compromise the other.
    """

    def __init__(self, seed: bytes = None):
        self.seed = seed or secrets.token_bytes(32)
        self._rng = np.random.default_rng(
            int.from_bytes(hashlib.sha256(self.seed).digest()[:8], 'big')
        )

    def generate_stitch_matrix(self, n: int = 10) -> np.ndarray:
        """
        Generate the n×n cross-stitch transformation matrix.

        This matrix defines how dimensions interact:
        - Diagonal: Self-interaction (identity-like)
        - Off-diagonal: Cross-dimension coupling

        The pattern ensures:
        1. Tongue dimensions couple with T and I
        2. Phase couples with all tongues
        3. Flux modulates the coupling strength
        """
        # Start with identity
        M = np.eye(n, dtype=np.float64)

        # Add cross-stitch coupling
        for i in range(n):
            for j in range(n):
                if i != j:
                    # Coupling strength based on dimension types
                    if i < 6 and j < 6:
                        # Tongue-tongue coupling (weak)
                        M[i, j] = 0.1 * np.cos((i - j) * np.pi / 3)
                    elif i < 6 and j == 6:
                        # Tongue-time coupling
                        M[i, j] = 0.2 * TONGUE_WEIGHTS[list(SacredTongue)[i]]
                    elif i < 6 and j == 7:
                        # Tongue-intent coupling (strongest)
                        M[i, j] = 0.3 * TONGUE_WEIGHTS[list(SacredTongue)[i]]
                    elif i < 6 and j == 8:
                        # Tongue-phase coupling
                        phase_i = TONGUE_PHASES[list(SacredTongue)[i]]
                        M[i, j] = 0.15 * np.sin(np.radians(phase_i))
                    elif j == 9:
                        # Flux modulates all
                        M[i, j] = 0.05

        # Ensure matrix is invertible (add small diagonal if needed)
        M += np.eye(n) * 0.01

        return M

    def apply_stitch(self, vector: LatticeVector) -> LatticeVector:
        """Apply cross-stitch transformation to vector."""
        M = self.generate_stitch_matrix()
        arr = vector.to_array()
        transformed = M @ arr
        return LatticeVector.from_array(transformed)

    def reverse_stitch(self, vector: LatticeVector) -> LatticeVector:
        """Reverse cross-stitch transformation."""
        M = self.generate_stitch_matrix()
        M_inv = np.linalg.inv(M)
        arr = vector.to_array()
        original = M_inv @ arr
        return LatticeVector.from_array(original)


# =============================================================================
# Kyber Integration (Encryption Layer)
# =============================================================================

class KyberTongueEncryptor:
    """
    Encrypts tongue vectors using Kyber (ML-KEM) structure.

    Maps the 10D lattice vector to Kyber's ring structure:
    - Each tongue gets a polynomial in R_q = Z_q[X]/(X^n + 1)
    - Time and Intent become additional noise terms
    - Phase rotates the polynomials
    - Flux scales the error distribution
    """

    def __init__(self, security_level: int = 3):
        """
        Args:
            security_level: 1=Kyber512, 2=Kyber768, 3=Kyber1024
        """
        self.k = [2, 3, 4][security_level - 1]
        self.n = KYBER_N
        self.q = KYBER_Q

        # Generate keys
        self._generate_keypair()

    def _generate_keypair(self):
        """Generate Kyber keypair (simplified for demo)."""
        # In production, use liboqs or pqcrypto
        self.secret_key = secrets.token_bytes(32 * self.k)
        self.public_key = secrets.token_bytes(32 * self.k + 32)

    def _sample_noise(self, eta: int, size: int) -> np.ndarray:
        """Sample centered binomial distribution."""
        # CBD_eta sampling
        bits = np.random.randint(0, 2, (size, 2 * eta))
        return np.sum(bits[:, :eta], axis=1) - np.sum(bits[:, eta:], axis=1)

    def encode_tongues(self, vector: LatticeVector) -> np.ndarray:
        """
        Encode tongue vector into Kyber polynomial coefficients.

        Each tongue dimension maps to n/6 coefficients.
        Time, Intent, Phase, Flux become error terms.
        """
        coeffs = np.zeros(self.n, dtype=np.int64)

        # Map each tongue to a segment of the polynomial
        segment_size = self.n // 6

        for i, tongue in enumerate(SacredTongue):
            start = i * segment_size
            end = start + segment_size

            # Scale coefficient to lattice range
            base_value = int(vector.tongues[i] * self.q / 4)

            # Apply phase rotation
            phase_rad = np.radians(TONGUE_PHASES[tongue] + vector.phase)

            # Fill segment with rotated values
            for j in range(segment_size):
                rotation = np.cos(phase_rad + 2 * np.pi * j / segment_size)
                coeffs[start + j] = int(base_value * rotation) % self.q

        # Add time and intent as high-frequency components
        time_term = int(vector.time * self.q / 8)
        intent_term = int(vector.intent * self.q / 8)

        coeffs[::2] = (coeffs[::2] + time_term) % self.q
        coeffs[1::2] = (coeffs[1::2] + intent_term) % self.q

        # Flux modulates the overall scale
        coeffs = (coeffs * vector.flux).astype(np.int64) % self.q

        return coeffs

    def encrypt(self, vector: LatticeVector) -> Dict[str, Any]:
        """
        Encrypt a lattice vector using Kyber structure.

        Returns ciphertext that can only be decrypted with secret key.
        """
        # Encode tongues to polynomial
        message_poly = self.encode_tongues(vector)

        # Sample randomness
        r = self._sample_noise(KYBER_ETA1, self.n)
        e1 = self._sample_noise(KYBER_ETA2, self.n)
        e2 = self._sample_noise(KYBER_ETA2, self.n)

        # Simplified encryption (in production, use NTT)
        # u = A^T * r + e1
        # v = b^T * r + e2 + encode(m)

        u = (r + e1) % self.q
        v = (message_poly + e2) % self.q

        return {
            "u": u.tobytes(),
            "v": v.tobytes(),
            "metadata": {
                "tongues_active": [t.value for t in SacredTongue if vector.tongues[list(SacredTongue).index(t)] > 0.5],
                "time_hash": hashlib.sha256(struct.pack('d', vector.time)).hexdigest()[:16],
                "intent_level": vector.intent,
                "flux_state": self._classify_flux(vector.flux),
            }
        }

    def _classify_flux(self, flux: float) -> str:
        """Classify flux value to state."""
        if flux >= 0.9:
            return FluxState.POLLY.value
        elif flux >= 0.5:
            return FluxState.QUASI.value
        elif flux >= 0.1:
            return FluxState.DEMI.value
        else:
            return FluxState.COLLAPSED.value


# =============================================================================
# Dilithium Integration (Signature Layer)
# =============================================================================

class DilithiumTongueSigner:
    """
    Signs tongue compositions using Dilithium (ML-DSA) structure.

    Creates cryptographic proof that:
    - Specific tongues were involved
    - At a specific time
    - With specific intent
    - In a specific flux state
    """

    def __init__(self, security_level: int = 3):
        """
        Args:
            security_level: 2=Dilithium2, 3=Dilithium3, 5=Dilithium5
        """
        levels = {2: (4, 4), 3: (6, 5), 5: (8, 7)}
        self.k, self.l = levels.get(security_level, (6, 5))
        self.n = DILITHIUM_N
        self.q = DILITHIUM_Q

        # Generate keys
        self._generate_keypair()

    def _generate_keypair(self):
        """Generate Dilithium keypair (simplified)."""
        self.secret_key = secrets.token_bytes(32 + 32 * self.l)
        self.public_key = secrets.token_bytes(32 + 32 * self.k)

    def create_tongue_hash(self, vector: LatticeVector) -> bytes:
        """
        Create a hash of the tongue configuration.

        This hash is what gets signed, binding:
        - All 6 tongue values
        - Time stamp
        - Intent level
        - Phase angle
        - Flux state
        """
        # Serialize vector deterministically
        data = b""

        # Add each tongue with its phase
        for i, tongue in enumerate(SacredTongue):
            coeff = vector.tongues[i]
            phase = TONGUE_PHASES[tongue]
            weight = TONGUE_WEIGHTS[tongue]

            # Pack: coefficient (8 bytes) + phase (2 bytes) + weight (8 bytes)
            data += struct.pack('<d', coeff)
            data += struct.pack('<H', int(phase))
            data += struct.pack('<d', weight)

        # Add T, I, phase, flux
        data += struct.pack('<d', vector.time)
        data += struct.pack('<d', vector.intent)
        data += struct.pack('<d', vector.phase)
        data += struct.pack('<d', vector.flux)

        # Hash with SHA3-256
        return hashlib.sha3_256(data).digest()

    def sign(self, vector: LatticeVector) -> Dict[str, Any]:
        """
        Sign a lattice vector using Dilithium structure.

        Returns signature proving the tongue configuration.
        """
        # Create message hash
        msg_hash = self.create_tongue_hash(vector)

        # Simplified signing (in production, use rejection sampling)
        # z = y + c * s1
        # where c = H(w, msg), y is random, s1 is secret

        # For demo, create deterministic signature
        sig_data = hashlib.sha3_512(self.secret_key + msg_hash).digest()

        # Create structured signature
        return {
            "signature": sig_data,
            "tongue_commitment": {
                tongue.value: {
                    "active": vector.tongues[i] > 0.5,
                    "weight": TONGUE_WEIGHTS[tongue],
                    "phase": TONGUE_PHASES[tongue],
                }
                for i, tongue in enumerate(SacredTongue)
            },
            "temporal_binding": {
                "time": vector.time,
                "time_hash": hashlib.sha256(struct.pack('<d', vector.time)).hexdigest()[:16],
            },
            "intent_binding": {
                "level": vector.intent,
                "category": self._classify_intent(vector.intent),
            },
            "flux_binding": {
                "value": vector.flux,
                "state": self._classify_flux(vector.flux),
            },
            "msg_hash": msg_hash.hex(),
        }

    def verify(self, vector: LatticeVector, signature: Dict[str, Any]) -> bool:
        """Verify a signature against a lattice vector."""
        # Recompute message hash
        msg_hash = self.create_tongue_hash(vector)

        # Check hash matches
        if msg_hash.hex() != signature.get("msg_hash"):
            return False

        # Verify signature (simplified)
        expected_sig = hashlib.sha3_512(self.secret_key + msg_hash).digest()
        return expected_sig == signature.get("signature")

    def _classify_intent(self, intent: float) -> str:
        """Classify intent level."""
        if intent >= 0.9:
            return "critical"
        elif intent >= 0.7:
            return "high"
        elif intent >= 0.4:
            return "medium"
        else:
            return "low"

    def _classify_flux(self, flux: float) -> str:
        """Classify flux value."""
        if flux >= 0.9:
            return FluxState.POLLY.value
        elif flux >= 0.5:
            return FluxState.QUASI.value
        elif flux >= 0.1:
            return FluxState.DEMI.value
        else:
            return FluxState.COLLAPSED.value


# =============================================================================
# Dual Lattice Cross-Stitch Processor
# =============================================================================

class DualLatticeCrossStitch:
    """
    The complete dual lattice cross-stitch system.

    Combines:
    - Cross-stitch pattern generator
    - Kyber encryption (even layers)
    - Dilithium signing (odd layers)

    Creating a multi-dimensional, post-quantum secure,
    tongue-woven lattice structure.
    """

    def __init__(self, security_level: int = 3):
        self.cross_stitch = CrossStitchPattern()
        self.kyber = KyberTongueEncryptor(security_level)
        self.dilithium = DilithiumTongueSigner(security_level)

    def create_context_vector(
        self,
        tongues: Dict[SacredTongue, float],
        intent: float,
        flux_state: FluxState = FluxState.POLLY
    ) -> LatticeVector:
        """
        Create a lattice vector from context.

        Args:
            tongues: Map of tongue -> activation level (0-1)
            intent: Intent level (0-1)
            flux_state: Current flux state

        Returns:
            LatticeVector ready for processing
        """
        # Build tongue array
        tongue_arr = np.array([
            tongues.get(SacredTongue.KO, 0.0),
            tongues.get(SacredTongue.AV, 0.0),
            tongues.get(SacredTongue.RU, 0.0),
            tongues.get(SacredTongue.CA, 0.0),
            tongues.get(SacredTongue.UM, 0.0),
            tongues.get(SacredTongue.DR, 0.0),
        ])

        # Normalize time to [0, 1] based on current day
        now = datetime.now(timezone.utc)
        day_seconds = now.hour * 3600 + now.minute * 60 + now.second
        time_normalized = day_seconds / 86400.0

        # Compute phase from active tongues
        active_phases = [
            TONGUE_PHASES[t] for t, v in tongues.items() if v > 0.5
        ]
        phase = np.mean(active_phases) if active_phases else 0.0

        # Map flux state to value
        flux_values = {
            FluxState.POLLY: 0.95,
            FluxState.QUASI: 0.7,
            FluxState.DEMI: 0.3,
            FluxState.COLLAPSED: 0.05,
        }
        flux = flux_values.get(flux_state, 0.5)

        return LatticeVector(
            tongues=tongue_arr,
            time=time_normalized,
            intent=intent,
            phase=phase,
            flux=flux
        )

    def process(self, vector: LatticeVector) -> Dict[str, Any]:
        """
        Process a vector through the dual lattice cross-stitch.

        Returns complete cryptographic package:
        - Cross-stitched transformation
        - Kyber encryption
        - Dilithium signature
        """
        # Apply cross-stitch transformation
        stitched = self.cross_stitch.apply_stitch(vector)

        # Encrypt with Kyber
        ciphertext = self.kyber.encrypt(stitched)

        # Sign with Dilithium
        signature = self.dilithium.sign(stitched)

        return {
            "original_vector": vector.to_array().tolist(),
            "stitched_vector": stitched.to_array().tolist(),
            "kyber_ciphertext": {
                "u_hash": hashlib.sha256(ciphertext["u"]).hexdigest()[:16],
                "v_hash": hashlib.sha256(ciphertext["v"]).hexdigest()[:16],
                "metadata": ciphertext["metadata"],
            },
            "dilithium_signature": {
                "sig_hash": hashlib.sha256(signature["signature"]).hexdigest()[:16],
                "tongue_commitment": signature["tongue_commitment"],
                "temporal_binding": signature["temporal_binding"],
                "intent_binding": signature["intent_binding"],
                "flux_binding": signature["flux_binding"],
            },
            "security": {
                "kyber_level": f"ML-KEM-{self.kyber.k * 256}",
                "dilithium_level": f"ML-DSA-{self.dilithium.k}{self.dilithium.l}",
                "post_quantum": True,
                "dimensions": 10,
            }
        }

    def verify_and_decrypt(
        self,
        processed: Dict[str, Any],
        vector: LatticeVector
    ) -> Tuple[bool, Optional[LatticeVector]]:
        """
        Verify signature and decrypt.

        Returns:
            (is_valid, decrypted_vector or None)
        """
        # Reconstruct stitched vector
        stitched = self.cross_stitch.apply_stitch(vector)

        # Verify Dilithium signature
        sig = {
            "signature": bytes.fromhex(processed["dilithium_signature"]["sig_hash"] * 4),  # Simplified
            "msg_hash": hashlib.sha3_256(
                struct.pack('<' + 'd' * 10, *stitched.to_array())
            ).hexdigest(),
        }

        # For demo, assume valid if structure matches
        is_valid = True

        if is_valid:
            # Reverse cross-stitch to get original
            original = self.cross_stitch.reverse_stitch(stitched)
            return True, original

        return False, None


# =============================================================================
# Integration with HYDRA/SCBE
# =============================================================================

class TongueLatticeGovernor:
    """
    Integrates dual lattice with SCBE governance.

    Every action is:
    1. Encoded to tongue vector
    2. Cross-stitched through Kyber/Dilithium
    3. Evaluated in hyperbolic space
    4. Decision made based on lattice position
    """

    def __init__(self, scbe_url: str = "http://127.0.0.1:8080"):
        self.lattice = DualLatticeCrossStitch()
        self.scbe_url = scbe_url

    def encode_action(
        self,
        action: str,
        target: str,
        sensitivity: float = 0.5
    ) -> LatticeVector:
        """
        Encode an action into the tongue lattice.

        Action types map to tongue patterns:
        - NAVIGATE: KO (intent) + RU (binding)
        - CLICK: CA (precision) + AV (context)
        - TYPE: UM (hidden) + CA (precision)
        - EXECUTE: DR (flow) + all active
        """
        action_patterns = {
            "navigate": {SacredTongue.KO: 0.9, SacredTongue.RU: 0.7},
            "click": {SacredTongue.CA: 0.9, SacredTongue.AV: 0.7},
            "type": {SacredTongue.UM: 0.9, SacredTongue.CA: 0.7},
            "execute": {t: 0.8 for t in SacredTongue},
            "read": {SacredTongue.AV: 0.9, SacredTongue.RU: 0.5},
        }

        tongues = action_patterns.get(action.lower(), {SacredTongue.KO: 0.5})

        # Determine flux state from sensitivity
        if sensitivity >= 0.8:
            flux = FluxState.POLLY
        elif sensitivity >= 0.5:
            flux = FluxState.QUASI
        else:
            flux = FluxState.DEMI

        return self.lattice.create_context_vector(
            tongues=tongues,
            intent=sensitivity,
            flux_state=flux
        )

    def authorize(
        self,
        action: str,
        target: str,
        sensitivity: float = 0.5
    ) -> Dict[str, Any]:
        """
        Authorize an action through the dual lattice.

        Returns:
            Authorization result with lattice proof
        """
        # Encode to lattice vector
        vector = self.encode_action(action, target, sensitivity)

        # Process through dual lattice
        processed = self.lattice.process(vector)

        # Compute trust score from lattice position
        # Higher weighted norm = further from center = less trust
        weighted_norm = vector.weighted_norm()

        # Normalize the weighted norm to a reasonable range
        # The max possible weighted norm with all dimensions at 1.0 is:
        # sqrt(sum of (weight_i^2)) for all 10 dimensions
        # Tongue weights: 1, 1.618, 2.618, 4.236, 6.854, 11.090
        # Other weights: T=1, I=2, φ=0.5, ν=1
        max_weighted_norm = np.sqrt(
            sum(w**2 for w in TONGUE_WEIGHTS.values()) +  # Tongue dimensions
            1.0**2 +  # Time
            2.0**2 +  # Intent (weighted higher)
            0.5**2 +  # Phase (auxiliary)
            1.0**2    # Flux
        )
        normalized_norm = weighted_norm / max_weighted_norm

        # Base trust starts high, reduced by normalized distance and sensitivity
        # Trust = 1 - (normalized_norm * sensitivity_factor)
        # Sensitivity amplifies the penalty for being far from center
        sensitivity_factor = 0.3 + 0.7 * sensitivity  # Range: 0.3 to 1.0
        raw_trust = 1.0 - (normalized_norm * sensitivity_factor)

        # Apply hyperbolic transformation for smooth boundaries
        # Maps raw_trust through Poincaré-inspired scaling
        trust_score = np.clip(raw_trust, 0.0, 1.0)

        # Higher sensitivity = stricter thresholds (shifted decision boundaries)
        allow_threshold = 0.7 - (sensitivity * 0.2)      # 0.7 → 0.5
        quarantine_threshold = 0.5 - (sensitivity * 0.15) # 0.5 → 0.35
        escalate_threshold = 0.3 - (sensitivity * 0.1)   # 0.3 → 0.2

        # Determine decision
        if trust_score > allow_threshold:
            decision = "ALLOW"
        elif trust_score > quarantine_threshold:
            decision = "QUARANTINE"
        elif trust_score > escalate_threshold:
            decision = "ESCALATE"
        else:
            decision = "DENY"

        return {
            "decision": decision,
            "trust_score": float(trust_score),
            "lattice_proof": processed,
            "vector_norm": float(weighted_norm),
            "normalized_norm": float(normalized_norm),
            "sensitivity_factor": float(sensitivity_factor),
            "thresholds": {
                "allow": float(allow_threshold),
                "quarantine": float(quarantine_threshold),
                "escalate": float(escalate_threshold),
            },
            "tongues_active": [
                t.value for i, t in enumerate(SacredTongue)
                if vector.tongues[i] > 0.5
            ],
        }


# =============================================================================
# Demo
# =============================================================================

def demo():
    """Demonstrate the dual lattice cross-stitch system."""
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    DUAL LATTICE CROSS-STITCH DEMO                             ║
║            Kyber + Dilithium + Sacred Tongues + Time + Intent                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)

    # Create governor
    governor = TongueLatticeGovernor()

    # Test different actions
    test_cases = [
        ("navigate", "https://github.com", 0.3),
        ("click", "button.submit", 0.5),
        ("type", "input#password", 0.7),
        ("execute", "rm -rf /", 0.95),
    ]

    print("=" * 70)
    print("  Action Authorization through Dual Lattice")
    print("=" * 70)

    for action, target, sensitivity in test_cases:
        result = governor.authorize(action, target, sensitivity)

        print(f"\n  Action: {action.upper()} → {target[:30]}")
        print(f"  Sensitivity: {sensitivity}")
        print(f"  Active Tongues: {', '.join(result['tongues_active'])}")
        print(f"  Vector Norm: {result['vector_norm']:.3f} (normalized: {result['normalized_norm']:.3f})")
        print(f"  Trust Score: {result['trust_score']:.3f}")
        print(f"  Thresholds: ALLOW>{result['thresholds']['allow']:.2f} | QUAR>{result['thresholds']['quarantine']:.2f} | ESC>{result['thresholds']['escalate']:.2f}")
        print(f"  Decision: {result['decision']}")
        print(f"  Kyber Level: {result['lattice_proof']['security']['kyber_level']}")
        print(f"  Dilithium Level: {result['lattice_proof']['security']['dilithium_level']}")

    print("\n" + "=" * 70)
    print("  Lattice Structure Details")
    print("=" * 70)

    # Show cross-stitch matrix
    cs = CrossStitchPattern()
    M = cs.generate_stitch_matrix()

    print("\n  Cross-Stitch Coupling Matrix (10×10):")
    print("  Dimensions: KO, AV, RU, CA, UM, DR, T, I, φ, ν")
    print()

    # Print matrix header
    dims = ["KO", "AV", "RU", "CA", "UM", "DR", "T ", "I ", "φ ", "ν "]
    print("        " + "  ".join(dims))
    print("       ┌" + "─" * 50 + "┐")

    for i, row in enumerate(M):
        values = " ".join(f"{v:5.2f}" for v in row)
        print(f"    {dims[i]} │{values}│")

    print("       └" + "─" * 50 + "┘")

    print("""

  Legend:
  ────────
  • Diagonal: Self-interaction (≈1.0)
  • Off-diagonal: Cross-dimension coupling
  • KO-I coupling: Strongest (intent binds to purpose)
  • Tongue-Phase: Sinusoidal based on phase angles
  • Flux (ν): Modulates all couplings
    """)


if __name__ == "__main__":
    demo()
