"""
PQC Audit Module - Post-Quantum Signed Audit Chain

Provides quantum-resistant digital signatures for audit chain entries
using Dilithium3. Ensures audit integrity even against quantum adversaries.

Integrates with the SCBE-AETHERMOORE governance audit system.
"""

import hashlib
import hmac
import os
import time
from dataclasses import dataclass, field
from typing import Tuple, Optional, List, Dict, Any, Union
from enum import Enum

from .pqc_core import (
    Dilithium3, DilithiumKeyPair, Kyber768, KyberKeyPair,
    derive_hybrid_key, get_backend, PQCBackend,
    DILITHIUM3_SIGNATURE_SIZE
)
from .pqc_hmac import (
    PQCHMACChain, PQCKeyMaterial, KeyDerivationMode,
    pqc_hmac_chain_tag, NONCE_BYTES, KEY_LEN, AUDIT_CHAIN_IV
)


class AuditDecision(Enum):
    """Governance decisions for audit entries (matches unified.py)."""
    ALLOW = "ALLOW"
    DENY = "DENY"
    QUARANTINE = "QUARANTINE"
    SNAP = "SNAP"


@dataclass
class PQCAuditEntry:
    """
    A single PQC-signed audit chain entry.

    Contains both HMAC chain binding and Dilithium3 signature
    for quantum-resistant integrity.
    """
    # Core audit data
    identity: str
    intent: str
    timestamp: float
    decision: AuditDecision

    # Chain binding
    chain_position: int
    nonce: bytes
    hmac_tag: bytes
    prev_tag: bytes

    # PQC signature
    signature: bytes
    signer_public_key: bytes

    # Metadata
    entry_id: bytes = field(default_factory=lambda: os.urandom(16))

    def to_bytes(self) -> bytes:
        """Serialize entry to bytes for signing/verification."""
        return (
            self.identity.encode('utf-8') + b'|' +
            self.intent.encode('utf-8') + b'|' +
            str(self.timestamp).encode('utf-8') + b'|' +
            self.decision.value.encode('utf-8') + b'|' +
            str(self.chain_position).encode('utf-8') + b'|' +
            self.nonce + b'|' +
            self.hmac_tag + b'|' +
            self.prev_tag
        )

    @classmethod
    def signable_data(cls, identity: str, intent: str, timestamp: float,
                      decision: AuditDecision, chain_position: int,
                      nonce: bytes, hmac_tag: bytes, prev_tag: bytes) -> bytes:
        """Generate signable data before entry creation."""
        return (
            identity.encode('utf-8') + b'|' +
            intent.encode('utf-8') + b'|' +
            str(timestamp).encode('utf-8') + b'|' +
            decision.value.encode('utf-8') + b'|' +
            str(chain_position).encode('utf-8') + b'|' +
            nonce + b'|' +
            hmac_tag + b'|' +
            prev_tag
        )

    def verify_signature(self) -> bool:
        """Verify the Dilithium3 signature of this entry."""
        signable = self.to_bytes()
        return Dilithium3.verify(self.signer_public_key, signable, self.signature)

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary for serialization."""
        return {
            "identity": self.identity,
            "intent": self.intent,
            "timestamp": self.timestamp,
            "decision": self.decision.value,
            "chain_position": self.chain_position,
            "nonce": self.nonce.hex(),
            "hmac_tag": self.hmac_tag.hex(),
            "prev_tag": self.prev_tag.hex(),
            "signature": self.signature.hex(),
            "signer_public_key": self.signer_public_key.hex(),
            "entry_id": self.entry_id.hex()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PQCAuditEntry":
        """Create entry from dictionary."""
        return cls(
            identity=data["identity"],
            intent=data["intent"],
            timestamp=data["timestamp"],
            decision=AuditDecision(data["decision"]),
            chain_position=data["chain_position"],
            nonce=bytes.fromhex(data["nonce"]),
            hmac_tag=bytes.fromhex(data["hmac_tag"]),
            prev_tag=bytes.fromhex(data["prev_tag"]),
            signature=bytes.fromhex(data["signature"]),
            signer_public_key=bytes.fromhex(data["signer_public_key"]),
            entry_id=bytes.fromhex(data["entry_id"])
        )


@dataclass
class AuditChainVerification:
    """Result of audit chain verification."""
    is_valid: bool
    hmac_valid: bool
    signatures_valid: bool
    entries_checked: int
    first_invalid_index: Optional[int] = None
    error_message: Optional[str] = None


class PQCAuditChain:
    """
    PQC-signed audit chain manager.

    Combines HMAC chain integrity (Layer 0) with Dilithium3 signatures
    for quantum-resistant audit trail.

    Features:
        - HMAC chain binding (tamper-evident)
        - Dilithium3 signatures (quantum-resistant authentication)
        - Chain-of-custody with ordering guarantees
        - Full verification of both HMAC and signatures

    Usage:
        # Create new audit chain
        chain = PQCAuditChain.create_new()

        # Add audit entries
        entry = chain.add_entry(
            identity="user123",
            intent="read_data",
            decision=AuditDecision.ALLOW
        )

        # Verify entire chain
        result = chain.verify_chain()
        assert result.is_valid
    """

    def __init__(self,
                 kem_keypair: Optional[KyberKeyPair] = None,
                 sig_keypair: Optional[DilithiumKeyPair] = None,
                 hmac_chain: Optional[PQCHMACChain] = None):
        """
        Initialize PQC audit chain.

        Args:
            kem_keypair: Optional Kyber keypair for HMAC key derivation
            sig_keypair: Optional Dilithium keypair for signing
            hmac_chain: Optional existing HMAC chain
        """
        # Generate or use provided signature keypair
        if sig_keypair is None:
            self._sig_keypair = Dilithium3.generate_keypair()
        else:
            self._sig_keypair = sig_keypair

        # Initialize HMAC chain
        if hmac_chain is None:
            self._hmac_chain = PQCHMACChain(kem_keypair=kem_keypair)
        else:
            self._hmac_chain = hmac_chain

        # Audit entries
        self._entries: List[PQCAuditEntry] = []
        self._chain_iv = AUDIT_CHAIN_IV

    @classmethod
    def create_new(cls,
                   key_mode: KeyDerivationMode = KeyDerivationMode.HYBRID) -> "PQCAuditChain":
        """Create a new PQC audit chain with fresh keys."""
        hmac_chain = PQCHMACChain.create_new(mode=key_mode)
        return cls(hmac_chain=hmac_chain)

    @property
    def sig_public_key(self) -> bytes:
        """Get the signature public key."""
        return self._sig_keypair.public_key

    @property
    def kem_public_key(self) -> bytes:
        """Get the KEM public key."""
        return self._hmac_chain.public_key

    @property
    def chain_length(self) -> int:
        """Get current chain length."""
        return len(self._entries)

    @property
    def backend(self) -> PQCBackend:
        """Get the PQC backend being used."""
        return get_backend()

    def add_entry(self,
                  identity: str,
                  intent: str,
                  decision: AuditDecision,
                  timestamp: Optional[float] = None,
                  nonce: Optional[bytes] = None) -> PQCAuditEntry:
        """
        Add a new signed entry to the audit chain.

        Args:
            identity: Identity string (who)
            intent: Intent string (what)
            decision: Governance decision
            timestamp: Optional timestamp (uses current time if not provided)
            nonce: Optional nonce (generated if not provided)

        Returns:
            The created PQCAuditEntry
        """
        if timestamp is None:
            timestamp = time.time()

        if nonce is None:
            nonce = os.urandom(NONCE_BYTES)

        # Get previous tag
        prev_tag = self._hmac_chain.get_latest_tag()

        # Create audit data for HMAC
        audit_data = f"{identity}|{intent}|{timestamp}|{decision.value}".encode('utf-8')

        # Add to HMAC chain and get tag
        hmac_tag = self._hmac_chain.append(audit_data, nonce)

        # Chain position
        chain_position = len(self._entries)

        # Create signable data
        signable = PQCAuditEntry.signable_data(
            identity, intent, timestamp, decision,
            chain_position, nonce, hmac_tag, prev_tag
        )

        # Sign with Dilithium3
        signature = Dilithium3.sign(self._sig_keypair.secret_key, signable)

        # Create entry
        entry = PQCAuditEntry(
            identity=identity,
            intent=intent,
            timestamp=timestamp,
            decision=decision,
            chain_position=chain_position,
            nonce=nonce,
            hmac_tag=hmac_tag,
            prev_tag=prev_tag,
            signature=signature,
            signer_public_key=self._sig_keypair.public_key
        )

        self._entries.append(entry)
        return entry

    def verify_entry(self, entry: PQCAuditEntry) -> Tuple[bool, str]:
        """
        Verify a single audit entry.

        Args:
            entry: Entry to verify

        Returns:
            Tuple of (is_valid, message)
        """
        # Verify signature
        if not entry.verify_signature():
            return False, "Invalid Dilithium3 signature"

        # Verify HMAC tag computation
        audit_data = f"{entry.identity}|{entry.intent}|{entry.timestamp}|{entry.decision.value}".encode('utf-8')
        expected_tag = pqc_hmac_chain_tag(
            audit_data,
            entry.nonce,
            entry.prev_tag,
            self._hmac_chain.key_material
        )

        if not hmac.compare_digest(entry.hmac_tag, expected_tag):
            return False, "Invalid HMAC tag"

        return True, "Valid"

    def verify_chain(self) -> AuditChainVerification:
        """
        Verify the entire audit chain.

        Checks both HMAC chain integrity and all signatures.

        Returns:
            AuditChainVerification with detailed results
        """
        if not self._entries:
            return AuditChainVerification(
                is_valid=True,
                hmac_valid=True,
                signatures_valid=True,
                entries_checked=0
            )

        # Verify HMAC chain
        hmac_valid = self._hmac_chain.verify()
        if not hmac_valid:
            return AuditChainVerification(
                is_valid=False,
                hmac_valid=False,
                signatures_valid=False,
                entries_checked=len(self._entries),
                error_message="HMAC chain verification failed"
            )

        # Verify each signature and chain binding
        prev_tag = self._chain_iv
        for i, entry in enumerate(self._entries):
            # Verify prev_tag chain binding
            if entry.prev_tag != prev_tag:
                return AuditChainVerification(
                    is_valid=False,
                    hmac_valid=True,
                    signatures_valid=False,
                    entries_checked=i + 1,
                    first_invalid_index=i,
                    error_message=f"Chain binding broken at entry {i}"
                )

            # Verify signature
            if not entry.verify_signature():
                return AuditChainVerification(
                    is_valid=False,
                    hmac_valid=True,
                    signatures_valid=False,
                    entries_checked=i + 1,
                    first_invalid_index=i,
                    error_message=f"Invalid signature at entry {i}"
                )

            prev_tag = entry.hmac_tag

        return AuditChainVerification(
            is_valid=True,
            hmac_valid=True,
            signatures_valid=True,
            entries_checked=len(self._entries)
        )

    def get_entry(self, index: int) -> Optional[PQCAuditEntry]:
        """Get entry by index."""
        if 0 <= index < len(self._entries):
            return self._entries[index]
        return None

    def get_entries_by_identity(self, identity: str) -> List[PQCAuditEntry]:
        """Get all entries for a specific identity."""
        return [e for e in self._entries if e.identity == identity]

    def get_entries_by_decision(self, decision: AuditDecision) -> List[PQCAuditEntry]:
        """Get all entries with a specific decision."""
        return [e for e in self._entries if e.decision == decision]

    def get_entries_in_range(self,
                             start_time: float,
                             end_time: float) -> List[PQCAuditEntry]:
        """Get entries within a time range."""
        return [e for e in self._entries
                if start_time <= e.timestamp <= end_time]

    def get_chain_digest(self) -> bytes:
        """
        Get a digest of the entire chain for comparison.

        Returns a hash incorporating all entries.
        """
        if not self._entries:
            return hashlib.sha3_256(b"empty_chain").digest()

        chain_data = b""
        for entry in self._entries:
            chain_data += entry.to_bytes()

        return hashlib.sha3_256(chain_data).digest()

    def export_state(self) -> Dict[str, Any]:
        """
        Export chain state for serialization.

        Note: Does not export secret keys.
        """
        return {
            "entries": [e.to_dict() for e in self._entries],
            "hmac_chain": self._hmac_chain.export_state(),
            "sig_public_key": self._sig_keypair.public_key.hex(),
            "chain_digest": self.get_chain_digest().hex(),
            "backend": get_backend().value
        }

    def get_audit_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the audit chain."""
        if not self._entries:
            return {
                "total_entries": 0,
                "decisions": {},
                "identities": [],
                "time_range": None,
                "chain_valid": True
            }

        decisions = {}
        identities = set()

        for entry in self._entries:
            decisions[entry.decision.value] = decisions.get(entry.decision.value, 0) + 1
            identities.add(entry.identity)

        return {
            "total_entries": len(self._entries),
            "decisions": decisions,
            "identities": list(identities),
            "time_range": {
                "start": self._entries[0].timestamp,
                "end": self._entries[-1].timestamp
            },
            "chain_valid": self.verify_chain().is_valid
        }


def create_audit_entry_signature(identity: str,
                                 intent: str,
                                 decision: str,
                                 timestamp: float,
                                 chain_tag: bytes,
                                 sig_keypair: DilithiumKeyPair) -> bytes:
    """
    Create a standalone PQC signature for an audit entry.

    For integration with existing audit systems that need to add
    PQC signatures without full chain migration.

    Args:
        identity: Identity string
        intent: Intent string
        decision: Decision string
        timestamp: Timestamp
        chain_tag: Current HMAC chain tag
        sig_keypair: Dilithium keypair for signing

    Returns:
        Dilithium3 signature bytes
    """
    signable = (
        identity.encode('utf-8') + b'|' +
        intent.encode('utf-8') + b'|' +
        str(timestamp).encode('utf-8') + b'|' +
        decision.encode('utf-8') + b'|' +
        chain_tag
    )

    return Dilithium3.sign(sig_keypair.secret_key, signable)


def verify_audit_entry_signature(identity: str,
                                 intent: str,
                                 decision: str,
                                 timestamp: float,
                                 chain_tag: bytes,
                                 signature: bytes,
                                 public_key: bytes) -> bool:
    """
    Verify a standalone PQC signature for an audit entry.

    Args:
        identity: Identity string
        intent: Intent string
        decision: Decision string
        timestamp: Timestamp
        chain_tag: HMAC chain tag
        signature: Signature to verify
        public_key: Dilithium public key

    Returns:
        True if signature is valid
    """
    signable = (
        identity.encode('utf-8') + b'|' +
        intent.encode('utf-8') + b'|' +
        str(timestamp).encode('utf-8') + b'|' +
        decision.encode('utf-8') + b'|' +
        chain_tag
    )

    return Dilithium3.verify(public_key, signable, signature)


class PQCAuditIntegration:
    """
    Integration helper for adding PQC signatures to existing audit systems.

    Provides a minimal interface for systems that want to add PQC
    signatures without full migration to PQCAuditChain.

    Usage:
        # Initialize with signature keypair
        integration = PQCAuditIntegration()

        # Sign existing audit entries
        sig = integration.sign_entry(
            audit_data=existing_audit_bytes,
            chain_tag=existing_hmac_tag
        )

        # Verify signatures
        is_valid = integration.verify_entry(
            audit_data=existing_audit_bytes,
            chain_tag=existing_hmac_tag,
            signature=sig,
            public_key=integration.public_key
        )
    """

    def __init__(self, sig_keypair: Optional[DilithiumKeyPair] = None):
        """Initialize with optional existing keypair."""
        if sig_keypair is None:
            self._sig_keypair = Dilithium3.generate_keypair()
        else:
            self._sig_keypair = sig_keypair

    @property
    def public_key(self) -> bytes:
        """Get the signature public key."""
        return self._sig_keypair.public_key

    def sign_entry(self, audit_data: bytes, chain_tag: bytes) -> bytes:
        """
        Sign audit data with chain binding.

        Args:
            audit_data: Raw audit entry data
            chain_tag: HMAC chain tag for binding

        Returns:
            Dilithium3 signature
        """
        signable = audit_data + b'|' + chain_tag
        return Dilithium3.sign(self._sig_keypair.secret_key, signable)

    def verify_entry(self,
                     audit_data: bytes,
                     chain_tag: bytes,
                     signature: bytes,
                     public_key: Optional[bytes] = None) -> bool:
        """
        Verify a signed audit entry.

        Args:
            audit_data: Raw audit entry data
            chain_tag: HMAC chain tag
            signature: Signature to verify
            public_key: Public key (uses own if not provided)

        Returns:
            True if valid
        """
        if public_key is None:
            public_key = self._sig_keypair.public_key

        signable = audit_data + b'|' + chain_tag
        return Dilithium3.verify(public_key, signable, signature)

    def batch_sign(self,
                   entries: List[Tuple[bytes, bytes]]) -> List[bytes]:
        """
        Sign multiple entries.

        Args:
            entries: List of (audit_data, chain_tag) tuples

        Returns:
            List of signatures
        """
        return [self.sign_entry(data, tag) for data, tag in entries]

    def batch_verify(self,
                     entries: List[Tuple[bytes, bytes, bytes]],
                     public_key: Optional[bytes] = None) -> List[bool]:
        """
        Verify multiple entries.

        Args:
            entries: List of (audit_data, chain_tag, signature) tuples
            public_key: Public key (uses own if not provided)

        Returns:
            List of verification results
        """
        return [self.verify_entry(data, tag, sig, public_key)
                for data, tag, sig in entries]
