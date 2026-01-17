"""
Quasicrystal Lattice Verification System

SCBE v3.0: Maps 6-dimensional authentication gates onto a 3D aperiodic
icosahedral quasicrystal lattice for geometric verification.

Integrated with PQC (Post-Quantum Cryptography) for:
- Kyber768-derived phason entropy
- Dilithium3-signed validation proofs

Key Concepts:
- Quasicrystals have aperiodic order (never repeating patterns)
- 6D integer inputs project to 3D physical space + 3D validation space
- Points are valid only if they fall within the "Atomic Surface" window
- Phason shifts (rekeying) move the validation window atomically
"""

import numpy as np
import hashlib
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict, Any
from enum import Enum
import time

# Golden Ratio - fundamental to icosahedral symmetry
PHI = (1 + np.sqrt(5)) / 2
TAU = 2 * np.pi


class ValidationStatus(Enum):
    """Status of quasicrystal validation."""
    VALID = "VALID"
    INVALID_OUTSIDE_WINDOW = "INVALID_OUTSIDE_WINDOW"
    INVALID_CRYSTALLINE_ATTACK = "INVALID_CRYSTALLINE_ATTACK"
    INVALID_PHASON_MISMATCH = "INVALID_PHASON_MISMATCH"


@dataclass
class LatticePoint:
    """A point in the quasicrystal lattice."""
    gate_vector: List[int]           # 6D integer input
    r_physical: np.ndarray           # 3D physical space projection
    r_perpendicular: np.ndarray      # 3D internal space projection
    distance_to_window: float        # Distance from phason center
    is_valid: bool                   # Within acceptance radius
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "gate_vector": self.gate_vector,
            "r_physical": self.r_physical.tolist(),
            "r_perpendicular": self.r_perpendicular.tolist(),
            "distance_to_window": self.distance_to_window,
            "is_valid": self.is_valid,
            "timestamp": self.timestamp
        }


@dataclass
class ValidationResult:
    """Result of quasicrystal validation."""
    status: ValidationStatus
    lattice_point: LatticePoint
    crystallinity_score: float       # 0.0 = aperiodic (good), 1.0 = periodic (attack)
    phason_epoch: int                # Current phason generation
    message: str


class QuasicrystalLattice:
    """
    Icosahedral Quasicrystal Verification System.

    Maps 6-dimensional authentication gates onto a 3D aperiodic lattice.
    Uses icosahedral symmetry (golden ratio) for projection.

    The 6 gates correspond to SCBE authentication dimensions:
    - Gate 0: Context hash (identity binding)
    - Gate 1: Intent classification
    - Gate 2: Trajectory state
    - Gate 3: Additional authenticated data
    - Gate 4: Commitment level
    - Gate 5: Signature verification state

    Usage:
        lattice = QuasicrystalLattice()

        # Validate a 6-gate input
        result = lattice.validate_gates([1, 2, 3, 5, 8, 13])

        # Rekey with new entropy (invalidates old valid points)
        lattice.apply_phason_rekey(entropy_bytes)
    """

    def __init__(self, lattice_constant: float = 1.0):
        """
        Initialize the quasicrystal lattice.

        Args:
            lattice_constant: Scale factor for the lattice (default 1.0)
        """
        self.a = lattice_constant

        # Acceptance radius in Perpendicular Space
        # Points are valid iff ||r_perp - phason|| < acceptance_radius
        self.acceptance_radius = 1.5 * self.a

        # Current Phason Strain Vector (Secret Key Component)
        self._phason_strain = np.zeros(3)
        self._phason_epoch = 0

        # History for crystallinity detection
        self._validation_history: List[LatticePoint] = []
        self._max_history = 100

        # Initialize 6D -> 3D Projection Matrices
        self.M_par, self.M_perp = self._generate_basis_matrices()

    def _generate_basis_matrices(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate projection matrices from 6D Z^6 to 3D spaces.

        Uses icosahedral symmetry with golden ratio (PHI).

        Returns:
            M_par: Projection to Physical Space (3x6 matrix)
            M_perp: Projection to Perpendicular/Internal Space (3x6 matrix)
        """
        # Normalization factor for icosahedral basis
        norm = 1 / np.sqrt(1 + PHI**2)

        # 6 basis vectors in Physical Space (E_parallel)
        # Cyclic permutations of (1, PHI, 0) with sign variations
        e_par = np.array([
            [1, PHI, 0],
            [-1, PHI, 0],
            [0, 1, PHI],
            [0, -1, PHI],
            [PHI, 0, 1],
            [PHI, 0, -1]
        ]).T * norm  # Shape (3, 6)

        # 6 basis vectors in Perpendicular Space (E_perp)
        # Related by Galois conjugation (PHI -> -1/PHI)
        e_perp = np.array([
            [1, -1/PHI, 0],
            [-1, -1/PHI, 0],
            [0, 1, -1/PHI],
            [0, -1, -1/PHI],
            [-1/PHI, 0, 1],
            [-1/PHI, 0, -1]
        ]).T * norm  # Shape (3, 6)

        return e_par, e_perp

    @property
    def phason_epoch(self) -> int:
        """Current phason generation number."""
        return self._phason_epoch

    @property
    def phason_strain(self) -> np.ndarray:
        """Current phason strain vector (read-only copy)."""
        return self._phason_strain.copy()

    def map_gates_to_lattice(self, gate_vector: List[int]) -> LatticePoint:
        """
        Map 6 integer gate inputs to the quasicrystal lattice.

        Args:
            gate_vector: List of 6 integers (gate states)

        Returns:
            LatticePoint with physical/perpendicular projections and validity
        """
        if len(gate_vector) != 6:
            raise ValueError(f"Gate vector must have 6 elements, got {len(gate_vector)}")

        n = np.array(gate_vector, dtype=float)

        # Project to Physical Space (the "public" lattice point)
        r_phys = self.M_par @ n

        # Project to Perpendicular Space (the "hidden" validation check)
        r_perp = self.M_perp @ n

        # Calculate distance from phason-shifted window center
        distance = np.linalg.norm(r_perp - self._phason_strain)

        # Valid if within acceptance radius
        is_valid = distance < self.acceptance_radius

        return LatticePoint(
            gate_vector=list(gate_vector),
            r_physical=r_phys,
            r_perpendicular=r_perp,
            distance_to_window=distance,
            is_valid=is_valid
        )

    def validate_gates(self, gate_vector: List[int]) -> ValidationResult:
        """
        Validate a 6-gate input against the quasicrystal.

        Performs:
        1. Lattice projection and window check
        2. Crystallinity detection (attack detection)
        3. History tracking

        Args:
            gate_vector: List of 6 integers

        Returns:
            ValidationResult with status and details
        """
        # Map to lattice
        point = self.map_gates_to_lattice(gate_vector)

        # Add to history
        self._validation_history.append(point)
        if len(self._validation_history) > self._max_history:
            self._validation_history.pop(0)

        # Check for crystalline attack
        crystallinity = self.detect_crystalline_defects()

        # Determine status
        if crystallinity > 0.5:
            status = ValidationStatus.INVALID_CRYSTALLINE_ATTACK
            message = f"Crystalline attack detected (score: {crystallinity:.2f})"
        elif not point.is_valid:
            status = ValidationStatus.INVALID_OUTSIDE_WINDOW
            message = f"Point outside acceptance window (distance: {point.distance_to_window:.4f})"
        else:
            status = ValidationStatus.VALID
            message = "Valid quasicrystal point"

        return ValidationResult(
            status=status,
            lattice_point=point,
            crystallinity_score=crystallinity,
            phason_epoch=self._phason_epoch,
            message=message
        )

    def apply_phason_rekey(self, entropy_seed: bytes) -> np.ndarray:
        """
        Apply a Phason Strain (deformation) to the lattice.

        This atomically invalidates the previous valid keyspace and
        creates a new one without changing the 6D integer logic.

        Args:
            entropy_seed: Bytes to derive new phason from

        Returns:
            The new phason strain vector
        """
        # Generate deterministic 3D vector from seed
        h = hashlib.sha256(entropy_seed).digest()

        # Map hash to 3 float values in [-1, 1]
        v = np.array([
            int.from_bytes(h[0:4], 'big') / (2**32) * 2 - 1,
            int.from_bytes(h[4:8], 'big') / (2**32) * 2 - 1,
            int.from_bytes(h[8:12], 'big') / (2**32) * 2 - 1
        ])

        # Scale by acceptance radius to ensure significant shift
        self._phason_strain = v * self.acceptance_radius * 2.0
        self._phason_epoch += 1

        # Clear history on rekey
        self._validation_history.clear()

        return self._phason_strain.copy()

    def detect_crystalline_defects(self) -> float:
        """
        Detect if an attacker is forcing periodicity (crystalline defect).

        In a true quasicrystal, patterns should be aperiodic.
        If we see simple integer periodicity, it's likely an attack.

        Returns:
            Crystallinity score: 0.0 = aperiodic (safe), 1.0 = periodic (attack)
        """
        if len(self._validation_history) < 10:
            return 0.0

        # Get recent gate vectors
        vectors = [p.gate_vector for p in self._validation_history[-20:]]

        # Check for exact repetition (simple attack)
        unique_count = len(set(tuple(v) for v in vectors))
        repetition_ratio = 1 - (unique_count / len(vectors))

        # Check for arithmetic progression (sophisticated attack)
        if len(vectors) >= 3:
            diffs = []
            for i in range(1, len(vectors)):
                diff = [vectors[i][j] - vectors[i-1][j] for j in range(6)]
                diffs.append(tuple(diff))

            unique_diffs = len(set(diffs))
            progression_ratio = 1 - (unique_diffs / len(diffs))
        else:
            progression_ratio = 0.0

        # Combined score
        crystallinity = max(repetition_ratio, progression_ratio * 0.8)

        return min(1.0, crystallinity)

    def get_fibonacci_gates(self, seed: int = 1) -> List[int]:
        """
        Generate Fibonacci-based gate values (resonate well with golden ratio).

        Args:
            seed: Starting Fibonacci number

        Returns:
            List of 6 Fibonacci numbers
        """
        fib = [seed, seed]
        for _ in range(10):
            fib.append(fib[-1] + fib[-2])

        # Return 6 consecutive Fibonacci numbers
        return fib[2:8]

    def export_state(self) -> Dict[str, Any]:
        """Export lattice state for serialization."""
        return {
            "lattice_constant": self.a,
            "acceptance_radius": self.acceptance_radius,
            "phason_strain": self._phason_strain.tolist(),
            "phason_epoch": self._phason_epoch,
            "history_length": len(self._validation_history),
            "M_par_shape": list(self.M_par.shape),
            "M_perp_shape": list(self.M_perp.shape)
        }


class PQCQuasicrystalLattice(QuasicrystalLattice):
    """
    Quasicrystal Lattice with PQC (Post-Quantum Cryptography) integration.

    Extends QuasicrystalLattice with:
    - Kyber768-derived phason entropy
    - Dilithium3-signed validation proofs
    """

    def __init__(self, lattice_constant: float = 1.0):
        super().__init__(lattice_constant)
        self._pqc_available = False
        self._sig_keypair = None
        self._kem_keypair = None

        # Try to import PQC module
        try:
            from ..pqc import Kyber768, Dilithium3, is_liboqs_available
            self._Kyber768 = Kyber768
            self._Dilithium3 = Dilithium3
            self._pqc_available = True

            # Generate signing keypair for validation proofs
            self._sig_keypair = Dilithium3.generate_keypair()
            self._kem_keypair = Kyber768.generate_keypair()
        except ImportError:
            pass

    @property
    def pqc_available(self) -> bool:
        """Check if PQC is available."""
        return self._pqc_available

    def apply_pqc_phason_rekey(self, peer_public_key: Optional[bytes] = None) -> Dict[str, Any]:
        """
        Apply phason rekey using PQC key encapsulation.

        If peer_public_key is provided, derives entropy from key exchange.
        Otherwise, generates fresh entropy.

        Args:
            peer_public_key: Optional Kyber768 public key for key exchange

        Returns:
            Dict with phason info and optional ciphertext for peer
        """
        if not self._pqc_available:
            # Fallback to random entropy
            entropy = hashlib.sha256(str(time.time()).encode()).digest()
            self.apply_phason_rekey(entropy)
            return {"phason_epoch": self._phason_epoch, "pqc_used": False}

        if peer_public_key:
            # Key exchange with peer
            result = self._Kyber768.encapsulate(peer_public_key)
            entropy = result.shared_secret
            ciphertext = result.ciphertext
        else:
            # Self-encapsulation for fresh entropy
            result = self._Kyber768.encapsulate(self._kem_keypair.public_key)
            entropy = result.shared_secret
            ciphertext = None

        # Apply phason with PQC-derived entropy
        self.apply_phason_rekey(entropy)

        return {
            "phason_epoch": self._phason_epoch,
            "phason_strain": self._phason_strain.tolist(),
            "pqc_used": True,
            "ciphertext": ciphertext.hex() if ciphertext else None,
            "kem_public_key": self._kem_keypair.public_key.hex()
        }

    def sign_validation(self, result: ValidationResult) -> Optional[bytes]:
        """
        Sign a validation result with Dilithium3.

        Args:
            result: ValidationResult to sign

        Returns:
            Signature bytes, or None if PQC not available
        """
        if not self._pqc_available or not self._sig_keypair:
            return None

        # Create signable data from result
        data = (
            result.status.value.encode() +
            b"|" + str(result.lattice_point.gate_vector).encode() +
            b"|" + str(result.phason_epoch).encode() +
            b"|" + str(result.lattice_point.timestamp).encode()
        )

        return self._Dilithium3.sign(self._sig_keypair.secret_key, data)

    def verify_validation_signature(self, result: ValidationResult,
                                   signature: bytes,
                                   public_key: Optional[bytes] = None) -> bool:
        """
        Verify a signed validation result.

        Args:
            result: ValidationResult that was signed
            signature: Signature to verify
            public_key: Public key (uses own if not provided)

        Returns:
            True if signature is valid
        """
        if not self._pqc_available:
            return False

        if public_key is None:
            public_key = self._sig_keypair.public_key

        data = (
            result.status.value.encode() +
            b"|" + str(result.lattice_point.gate_vector).encode() +
            b"|" + str(result.phason_epoch).encode() +
            b"|" + str(result.lattice_point.timestamp).encode()
        )

        return self._Dilithium3.verify(public_key, data, signature)

    @property
    def sig_public_key(self) -> Optional[bytes]:
        """Get signing public key."""
        if self._sig_keypair:
            return self._sig_keypair.public_key
        return None

    @property
    def kem_public_key(self) -> Optional[bytes]:
        """Get KEM public key for key exchange."""
        if self._kem_keypair:
            return self._kem_keypair.public_key
        return None
