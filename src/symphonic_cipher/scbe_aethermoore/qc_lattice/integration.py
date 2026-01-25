"""
Quasicrystal-HMAC Integration Module

Integrates the Quasicrystal Lattice and PHDM systems with the existing
Layer 0 HMAC chain for complete cryptographic binding.

Provides:
- Unified validation combining quasicrystal geometry + HMAC integrity
- PHDM-enhanced audit chain with polyhedral signatures
- PQC-secured quasicrystal rekeying
"""

import hashlib
import hmac
import os
import time
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
from enum import Enum

from .quasicrystal import (
    QuasicrystalLattice,
    PQCQuasicrystalLattice,
    ValidationResult,
    ValidationStatus,
    LatticePoint
)
from .phdm import (
    PHDMHamiltonianPath,
    PHDMDeviationDetector,
    HamiltonianNode,
    get_phdm_family
)


# Constants matching Layer 0 (from unified.py)
NONCE_BYTES = 12
KEY_LEN = 32
AUDIT_CHAIN_IV = b'\x00' * 32


class IntegratedDecision(Enum):
    """Combined decision from all verification layers."""
    ALLOW = "ALLOW"
    DENY = "DENY"
    QUARANTINE = "QUARANTINE"
    SNAP = "SNAP"  # Geometric discontinuity


@dataclass
class IntegratedValidation:
    """
    Result of integrated quasicrystal + PHDM + HMAC validation.
    """
    # Overall decision
    decision: IntegratedDecision
    confidence: float  # 0.0 to 1.0

    # Quasicrystal results
    qc_status: ValidationStatus
    qc_point: LatticePoint
    qc_crystallinity: float

    # PHDM results
    phdm_valid: bool
    phdm_deviation: float
    phdm_node: Optional[HamiltonianNode]

    # HMAC chain
    hmac_tag: bytes
    chain_position: int

    # Metadata
    timestamp: float = field(default_factory=time.time)
    phason_epoch: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "decision": self.decision.value,
            "confidence": self.confidence,
            "qc_status": self.qc_status.value,
            "qc_crystallinity": self.qc_crystallinity,
            "phdm_valid": self.phdm_valid,
            "phdm_deviation": self.phdm_deviation,
            "hmac_tag": self.hmac_tag.hex(),
            "chain_position": self.chain_position,
            "timestamp": self.timestamp,
            "phason_epoch": self.phason_epoch
        }


class QuasicrystalHMACChain:
    """
    Unified Quasicrystal + HMAC Chain System.

    Combines:
    - Quasicrystal lattice for geometric verification
    - PHDM for topological integrity
    - HMAC chain for cryptographic binding

    This is the Layer 0 integration for SCBE-AETHERMOORE.
    """

    def __init__(self,
                 hmac_key: Optional[bytes] = None,
                 use_pqc: bool = True):
        """
        Initialize the integrated chain.

        Args:
            hmac_key: HMAC key (generated if not provided)
            use_pqc: Whether to use PQC for quasicrystal operations
        """
        # HMAC chain setup
        self._hmac_key = hmac_key or os.urandom(KEY_LEN)
        self._chain: List[Tuple[bytes, bytes, bytes]] = []  # (data, nonce, tag)
        self._chain_iv = AUDIT_CHAIN_IV

        # Quasicrystal setup
        if use_pqc:
            self._qc = PQCQuasicrystalLattice()
        else:
            self._qc = QuasicrystalLattice()

        # PHDM setup
        self._phdm = PHDMHamiltonianPath(key=self._hmac_key)
        self._phdm.compute_path()
        self._phdm_detector = PHDMDeviationDetector(self._phdm)

        # Validation history
        self._validations: List[IntegratedValidation] = []

    @property
    def chain_length(self) -> int:
        """Current HMAC chain length."""
        return len(self._chain)

    @property
    def qc_phason_epoch(self) -> int:
        """Current quasicrystal phason epoch."""
        return self._qc.phason_epoch

    def _compute_hmac_tag(self, data: bytes, nonce: bytes, prev_tag: bytes) -> bytes:
        """Compute HMAC chain tag: H_k(data || nonce || prev_tag)"""
        combined = data + nonce + prev_tag
        return hmac.new(self._hmac_key, combined, hashlib.sha256).digest()

    def _get_prev_tag(self) -> bytes:
        """Get previous tag or IV if chain is empty."""
        if self._chain:
            return self._chain[-1][2]
        return self._chain_iv

    def validate_and_append(self,
                            gate_vector: List[int],
                            context_data: bytes,
                            nonce: Optional[bytes] = None) -> IntegratedValidation:
        """
        Validate gates through quasicrystal and append to HMAC chain.

        This is the main entry point for Layer 0 validation.

        Args:
            gate_vector: 6 integer gates for quasicrystal
            context_data: Additional context bytes for HMAC
            nonce: Optional nonce (generated if not provided)

        Returns:
            IntegratedValidation with complete results
        """
        if nonce is None:
            nonce = os.urandom(NONCE_BYTES)

        # 1. Quasicrystal validation
        qc_result = self._qc.validate_gates(gate_vector)

        # 2. Map gate sum to PHDM node (modulo 16)
        gate_sum = sum(gate_vector)
        phdm_index = gate_sum % 16
        phdm_node = self._phdm._path[phdm_index] if self._phdm._path else None

        # 3. Check PHDM integrity
        phdm_valid, _ = self._phdm.verify_path()
        phdm_deviation = self._phdm_detector.detect_manifold_deviation(
            observed_vertices=sum(gate_vector),
            observed_euler=gate_sum % 10
        )

        # 4. Combine data for HMAC
        combined_data = (
            context_data +
            b"|" + str(gate_vector).encode() +
            b"|" + qc_result.status.value.encode() +
            b"|" + str(phdm_index).encode()
        )

        # 5. Compute HMAC tag
        prev_tag = self._get_prev_tag()
        hmac_tag = self._compute_hmac_tag(combined_data, nonce, prev_tag)

        # 6. Append to chain
        self._chain.append((combined_data, nonce, hmac_tag))
        chain_position = len(self._chain) - 1

        # 7. Determine integrated decision
        decision, confidence = self._compute_decision(
            qc_result, phdm_valid, phdm_deviation
        )

        # 8. Create integrated result
        result = IntegratedValidation(
            decision=decision,
            confidence=confidence,
            qc_status=qc_result.status,
            qc_point=qc_result.lattice_point,
            qc_crystallinity=qc_result.crystallinity_score,
            phdm_valid=phdm_valid,
            phdm_deviation=phdm_deviation,
            phdm_node=phdm_node,
            hmac_tag=hmac_tag,
            chain_position=chain_position,
            phason_epoch=self._qc.phason_epoch
        )

        self._validations.append(result)
        return result

    def _compute_decision(self,
                          qc_result: ValidationResult,
                          phdm_valid: bool,
                          phdm_deviation: float) -> Tuple[IntegratedDecision, float]:
        """
        Compute integrated decision from all verification layers.

        Returns:
            Tuple of (decision, confidence)
        """
        # Start with base confidence
        confidence = 1.0

        # Check quasicrystal status
        if qc_result.status == ValidationStatus.INVALID_CRYSTALLINE_ATTACK:
            return IntegratedDecision.DENY, 0.95

        if qc_result.status == ValidationStatus.INVALID_OUTSIDE_WINDOW:
            confidence *= 0.3

        # Adjust for crystallinity (attack detection)
        if qc_result.crystallinity_score > 0.5:
            confidence *= (1 - qc_result.crystallinity_score)

        # Check PHDM integrity
        if not phdm_valid:
            return IntegratedDecision.SNAP, 0.9

        # Adjust for PHDM deviation
        if phdm_deviation > 0.5:
            confidence *= (1 - phdm_deviation * 0.5)

        # Make decision based on confidence
        if confidence >= 0.7:
            return IntegratedDecision.ALLOW, confidence
        elif confidence >= 0.4:
            return IntegratedDecision.QUARANTINE, confidence
        elif confidence >= 0.2:
            return IntegratedDecision.SNAP, confidence
        else:
            return IntegratedDecision.DENY, confidence

    def verify_chain(self) -> Tuple[bool, Optional[int]]:
        """
        Verify integrity of the entire HMAC chain.

        Returns:
            Tuple of (is_valid, first_invalid_position or None)
        """
        if not self._chain:
            return True, None

        prev_tag = self._chain_iv

        for i, (data, nonce, tag) in enumerate(self._chain):
            expected_tag = self._compute_hmac_tag(data, nonce, prev_tag)
            if not hmac.compare_digest(tag, expected_tag):
                return False, i
            prev_tag = tag

        return True, None

    def rekey_quasicrystal(self, entropy: Optional[bytes] = None) -> Dict[str, Any]:
        """
        Rekey the quasicrystal with new phason.

        Args:
            entropy: Optional entropy bytes (uses PQC if available)

        Returns:
            Dict with rekey information
        """
        if isinstance(self._qc, PQCQuasicrystalLattice):
            return self._qc.apply_pqc_phason_rekey()
        else:
            if entropy is None:
                entropy = os.urandom(32)
            self._qc.apply_phason_rekey(entropy)
            return {
                "phason_epoch": self._qc.phason_epoch,
                "pqc_used": False
            }

    def get_statistics(self) -> Dict[str, Any]:
        """Get chain statistics."""
        decisions = {}
        for v in self._validations:
            d = v.decision.value
            decisions[d] = decisions.get(d, 0) + 1

        valid, _ = self.verify_chain()

        return {
            "chain_length": len(self._chain),
            "chain_valid": valid,
            "validation_count": len(self._validations),
            "decisions": decisions,
            "phason_epoch": self._qc.phason_epoch,
            "phdm_path_valid": self._phdm.verify_path()[0],
            "pqc_available": isinstance(self._qc, PQCQuasicrystalLattice)
        }

    def export_state(self) -> Dict[str, Any]:
        """Export chain state for serialization."""
        return {
            "chain": [(d.hex(), n.hex(), t.hex()) for d, n, t in self._chain],
            "chain_iv": self._chain_iv.hex(),
            "qc_state": self._qc.export_state(),
            "phdm_state": self._phdm.export_state(),
            "statistics": self.get_statistics()
        }


class IntegratedAuditChain:
    """
    Full audit chain with Quasicrystal + PHDM + PQC integration.

    Provides a complete audit trail with:
    - Geometric verification via quasicrystal
    - Topological binding via PHDM
    - Quantum-resistant signatures via PQC
    - Tamper-evident HMAC chain
    """

    def __init__(self, use_pqc: bool = True):
        """
        Initialize the integrated audit chain.

        Args:
            use_pqc: Whether to use PQC for signatures
        """
        self._qc_chain = QuasicrystalHMACChain(use_pqc=use_pqc)
        self._pqc_available = False
        self._sig_keypair = None

        # Try to import PQC for signatures
        try:
            from ..pqc import Dilithium3
            self._Dilithium3 = Dilithium3
            self._sig_keypair = Dilithium3.generate_keypair()
            self._pqc_available = True
        except ImportError:
            pass

        # Signed validations
        self._signed_entries: List[Tuple[IntegratedValidation, Optional[bytes]]] = []

    def add_entry(self,
                  identity: str,
                  intent: str,
                  gate_vector: Optional[List[int]] = None) -> Tuple[IntegratedValidation, Optional[bytes]]:
        """
        Add a signed entry to the audit chain.

        Args:
            identity: Identity string
            intent: Intent string
            gate_vector: Optional 6-gate vector (derived from identity/intent if not provided)

        Returns:
            Tuple of (IntegratedValidation, signature or None)
        """
        # Derive gate vector from identity/intent if not provided
        if gate_vector is None:
            gate_vector = self._derive_gates(identity, intent)

        # Create context data
        context_data = f"{identity}|{intent}|{time.time()}".encode()

        # Validate and append
        validation = self._qc_chain.validate_and_append(gate_vector, context_data)

        # Sign if PQC available
        signature = None
        if self._pqc_available and self._sig_keypair:
            sign_data = (
                validation.decision.value.encode() +
                b"|" + validation.hmac_tag +
                b"|" + str(validation.chain_position).encode()
            )
            signature = self._Dilithium3.sign(self._sig_keypair.secret_key, sign_data)

        self._signed_entries.append((validation, signature))
        return validation, signature

    def _derive_gates(self, identity: str, intent: str) -> List[int]:
        """Derive 6 gate values from identity and intent."""
        # Hash the inputs
        h = hashlib.sha256((identity + "|" + intent).encode()).digest()

        # Extract 6 values
        gates = []
        for i in range(6):
            gates.append(int.from_bytes(h[i*4:(i+1)*4], 'big') % 100)

        return gates

    def verify_all(self) -> Tuple[bool, List[str]]:
        """
        Verify entire audit chain.

        Returns:
            Tuple of (all_valid, list of error messages)
        """
        errors = []

        # Check HMAC chain
        hmac_valid, pos = self._qc_chain.verify_chain()
        if not hmac_valid:
            errors.append(f"HMAC chain invalid at position {pos}")

        # Check PHDM
        phdm_valid, phdm_pos = self._qc_chain._phdm.verify_path()
        if not phdm_valid:
            errors.append(f"PHDM path invalid at position {phdm_pos}")

        # Check signatures if PQC available
        if self._pqc_available and self._sig_keypair:
            for i, (validation, signature) in enumerate(self._signed_entries):
                if signature:
                    sign_data = (
                        validation.decision.value.encode() +
                        b"|" + validation.hmac_tag +
                        b"|" + str(validation.chain_position).encode()
                    )
                    if not self._Dilithium3.verify(
                        self._sig_keypair.public_key, sign_data, signature
                    ):
                        errors.append(f"Signature invalid at entry {i}")

        return len(errors) == 0, errors

    def get_summary(self) -> Dict[str, Any]:
        """Get audit chain summary."""
        return {
            "entry_count": len(self._signed_entries),
            "pqc_available": self._pqc_available,
            "chain_statistics": self._qc_chain.get_statistics(),
            "all_valid": self.verify_all()[0]
        }

    @property
    def sig_public_key(self) -> Optional[bytes]:
        """Get signing public key."""
        if self._sig_keypair:
            return self._sig_keypair.public_key
        return None


# =============================================================================
# Convenience Functions
# =============================================================================

def create_integrated_chain(use_pqc: bool = True) -> IntegratedAuditChain:
    """
    Create a new integrated audit chain.

    Args:
        use_pqc: Whether to use PQC features

    Returns:
        Ready-to-use IntegratedAuditChain
    """
    return IntegratedAuditChain(use_pqc=use_pqc)


def quick_validate(identity: str, intent: str) -> IntegratedValidation:
    """
    Quick one-shot validation for simple use cases.

    Args:
        identity: Identity string
        intent: Intent string

    Returns:
        IntegratedValidation result
    """
    chain = QuasicrystalHMACChain(use_pqc=False)

    # Derive gates
    h = hashlib.sha256((identity + "|" + intent).encode()).digest()
    gates = [int.from_bytes(h[i*4:(i+1)*4], 'big') % 100 for i in range(6)]

    context = f"{identity}|{intent}".encode()
    return chain.validate_and_append(gates, context)
