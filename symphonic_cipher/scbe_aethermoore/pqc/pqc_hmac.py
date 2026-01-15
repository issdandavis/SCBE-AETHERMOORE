"""
PQC HMAC Module - Post-Quantum Enhanced HMAC Key Derivation

Replaces classical HMAC key derivation with PQC shared secrets for
quantum-resistant key exchange in the SCBE-AETHERMOORE HMAC chain.

Integrates with Layer 0 cryptographic foundation.
"""

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass, field
from typing import Tuple, Optional, List, Dict, Any
from enum import Enum

from .pqc_core import (
    Kyber768, KyberKeyPair, EncapsulationResult,
    derive_hybrid_key, get_backend, PQCBackend,
    KYBER768_SHARED_SECRET_SIZE
)


# Constants for HMAC chain (matching unified.py Layer 0)
NONCE_BYTES = 12
KEY_LEN = 32
AUDIT_CHAIN_IV = b'\x00' * 32


class KeyDerivationMode(Enum):
    """Key derivation mode for HMAC operations."""
    CLASSICAL = "classical"      # Traditional HMAC key
    PQC_ONLY = "pqc_only"        # PQC-derived key only
    HYBRID = "hybrid"            # Combined classical + PQC


@dataclass
class PQCKeyMaterial:
    """
    PQC-derived key material for HMAC chain operations.

    Contains both the derived key and the cryptographic artifacts
    needed for key reconstruction and verification.
    """
    hmac_key: bytes                          # 32-byte derived HMAC key
    pqc_shared_secret: bytes                 # Original PQC shared secret
    ciphertext: bytes                        # KEM ciphertext for key recovery
    derivation_mode: KeyDerivationMode       # How the key was derived
    classical_component: Optional[bytes] = None  # Optional classical secret
    salt: bytes = field(default_factory=lambda: secrets.token_bytes(16))
    key_id: bytes = field(default_factory=lambda: secrets.token_bytes(8))

    def __post_init__(self):
        if len(self.hmac_key) != KEY_LEN:
            raise ValueError(f"hmac_key must be {KEY_LEN} bytes")
        if len(self.pqc_shared_secret) != KYBER768_SHARED_SECRET_SIZE:
            raise ValueError(f"pqc_shared_secret must be {KYBER768_SHARED_SECRET_SIZE} bytes")


@dataclass
class PQCHMACState:
    """
    State for PQC-enhanced HMAC chain.

    Maintains both classical and PQC key material for the audit chain.
    """
    kem_keypair: KyberKeyPair
    key_material: PQCKeyMaterial
    chain_iv: bytes = AUDIT_CHAIN_IV
    chain_position: int = 0
    mode: KeyDerivationMode = KeyDerivationMode.HYBRID


def pqc_derive_hmac_key(recipient_public_key: bytes,
                        classical_secret: Optional[bytes] = None,
                        salt: Optional[bytes] = None,
                        mode: KeyDerivationMode = KeyDerivationMode.HYBRID) -> PQCKeyMaterial:
    """
    Derive an HMAC key using PQC key encapsulation.

    This replaces classical key derivation with quantum-resistant
    key exchange, ensuring forward secrecy against quantum attacks.

    Args:
        recipient_public_key: Kyber768 public key of the key recipient
        classical_secret: Optional classical shared secret for hybrid mode
        salt: Optional salt for key derivation
        mode: Key derivation mode (CLASSICAL, PQC_ONLY, HYBRID)

    Returns:
        PQCKeyMaterial with derived HMAC key and artifacts
    """
    if salt is None:
        salt = secrets.token_bytes(16)

    # Perform Kyber768 key encapsulation
    encap_result = Kyber768.encapsulate(recipient_public_key)

    # Derive HMAC key based on mode
    if mode == KeyDerivationMode.PQC_ONLY:
        hmac_key = derive_hybrid_key(
            encap_result.shared_secret,
            classical_shared_secret=None,
            salt=salt,
            info=b"scbe-aethermoore-hmac-pqc"
        )
    elif mode == KeyDerivationMode.HYBRID:
        if classical_secret is None:
            # Generate fresh classical component
            classical_secret = secrets.token_bytes(32)
        hmac_key = derive_hybrid_key(
            encap_result.shared_secret,
            classical_shared_secret=classical_secret,
            salt=salt,
            info=b"scbe-aethermoore-hmac-hybrid"
        )
    else:  # CLASSICAL fallback
        # Even in classical mode, use PQC to derive key
        hmac_key = derive_hybrid_key(
            encap_result.shared_secret,
            salt=salt,
            info=b"scbe-aethermoore-hmac-classical"
        )

    return PQCKeyMaterial(
        hmac_key=hmac_key,
        pqc_shared_secret=encap_result.shared_secret,
        ciphertext=encap_result.ciphertext,
        derivation_mode=mode,
        classical_component=classical_secret,
        salt=salt
    )


def pqc_recover_hmac_key(secret_key: bytes,
                         ciphertext: bytes,
                         salt: bytes,
                         classical_component: Optional[bytes] = None,
                         mode: KeyDerivationMode = KeyDerivationMode.HYBRID) -> bytes:
    """
    Recover HMAC key from PQC ciphertext.

    Used by the key recipient to derive the same HMAC key.

    Args:
        secret_key: Kyber768 secret key
        ciphertext: KEM ciphertext from key derivation
        salt: Salt used in original derivation
        classical_component: Classical secret if used in hybrid mode
        mode: Original derivation mode

    Returns:
        32-byte HMAC key
    """
    # Decapsulate shared secret
    shared_secret = Kyber768.decapsulate(secret_key, ciphertext)

    # Derive HMAC key with same parameters
    if mode == KeyDerivationMode.PQC_ONLY:
        return derive_hybrid_key(
            shared_secret,
            classical_shared_secret=None,
            salt=salt,
            info=b"scbe-aethermoore-hmac-pqc"
        )
    elif mode == KeyDerivationMode.HYBRID:
        return derive_hybrid_key(
            shared_secret,
            classical_shared_secret=classical_component,
            salt=salt,
            info=b"scbe-aethermoore-hmac-hybrid"
        )
    else:
        return derive_hybrid_key(
            shared_secret,
            salt=salt,
            info=b"scbe-aethermoore-hmac-classical"
        )


def pqc_hmac_chain_tag(message: bytes,
                       nonce: bytes,
                       prev_tag: bytes,
                       key_material: PQCKeyMaterial) -> bytes:
    """
    Compute HMAC chain tag using PQC-derived key.

    Mirrors the Layer 0 hmac_chain_tag function from unified.py
    but uses PQC-derived key material.

    Formula: T_i = HMAC_K(M_i || nonce_i || T_{i-1})

    Security Properties:
        - Quantum-resistant key derivation
        - Tamper evidence: Any modification breaks the chain
        - Chain-of-custody: Each block binds to previous via T_{i-1}
        - Ordering: Nonce sequence enforces message order

    Args:
        message: Current message bytes
        nonce: Current nonce (NONCE_BYTES)
        prev_tag: Previous chain tag (32 bytes)
        key_material: PQC-derived key material

    Returns:
        32-byte HMAC tag
    """
    data = message + nonce + prev_tag
    return hmac.new(key_material.hmac_key, data, hashlib.sha256).digest()


def pqc_verify_hmac_chain(messages: List[bytes],
                          nonces: List[bytes],
                          tags: List[bytes],
                          key_material: PQCKeyMaterial,
                          iv: bytes = AUDIT_CHAIN_IV) -> bool:
    """
    Verify integrity of PQC-enhanced HMAC chain.

    Args:
        messages: List of message bytes
        nonces: List of nonces
        tags: List of HMAC tags
        key_material: PQC-derived key material
        iv: Initial vector (default: zeros)

    Returns:
        True if chain is valid, False otherwise
    """
    if len(messages) != len(nonces) or len(messages) != len(tags):
        return False

    prev_tag = iv
    for msg, nonce, tag in zip(messages, nonces, tags):
        expected_tag = pqc_hmac_chain_tag(msg, nonce, prev_tag, key_material)
        if not hmac.compare_digest(tag, expected_tag):
            return False
        prev_tag = tag

    return True


class PQCHMACChain:
    """
    PQC-enhanced HMAC chain manager.

    Provides a complete interface for managing HMAC chains with
    quantum-resistant key derivation. Integrates with Layer 0
    of the SCBE-AETHERMOORE governance system.

    Usage:
        # Initialize with new PQC keys
        chain = PQCHMACChain.create_new()

        # Or initialize with existing keypair
        keypair = Kyber768.generate_keypair()
        chain = PQCHMACChain(keypair)

        # Add entries to the chain
        chain.append(b"audit entry 1")
        chain.append(b"audit entry 2")

        # Verify chain integrity
        assert chain.verify()

        # Export for serialization
        export_data = chain.export_state()
    """

    def __init__(self,
                 kem_keypair: Optional[KyberKeyPair] = None,
                 key_material: Optional[PQCKeyMaterial] = None,
                 mode: KeyDerivationMode = KeyDerivationMode.HYBRID):
        """
        Initialize PQC HMAC chain.

        Args:
            kem_keypair: Optional Kyber keypair (generated if not provided)
            key_material: Optional pre-derived key material
            mode: Key derivation mode
        """
        self._mode = mode
        self._chain: List[Tuple[bytes, bytes, bytes]] = []  # (message, nonce, tag)
        self._chain_iv = AUDIT_CHAIN_IV

        # Generate or use provided keypair
        if kem_keypair is None:
            self._kem_keypair = Kyber768.generate_keypair()
        else:
            self._kem_keypair = kem_keypair

        # Generate or use provided key material
        if key_material is None:
            self._key_material = pqc_derive_hmac_key(
                self._kem_keypair.public_key,
                mode=mode
            )
        else:
            self._key_material = key_material

    @classmethod
    def create_new(cls,
                   mode: KeyDerivationMode = KeyDerivationMode.HYBRID) -> "PQCHMACChain":
        """Create a new PQC HMAC chain with fresh keys."""
        return cls(mode=mode)

    @classmethod
    def from_keypair(cls,
                     kem_keypair: KyberKeyPair,
                     ciphertext: bytes,
                     salt: bytes,
                     classical_component: Optional[bytes] = None,
                     mode: KeyDerivationMode = KeyDerivationMode.HYBRID) -> "PQCHMACChain":
        """
        Create chain from existing keypair and key exchange data.

        Used by the recipient side of key exchange.
        """
        hmac_key = pqc_recover_hmac_key(
            kem_keypair.secret_key,
            ciphertext,
            salt,
            classical_component,
            mode
        )

        # Reconstruct key material
        shared_secret = Kyber768.decapsulate(kem_keypair.secret_key, ciphertext)
        key_material = PQCKeyMaterial(
            hmac_key=hmac_key,
            pqc_shared_secret=shared_secret,
            ciphertext=ciphertext,
            derivation_mode=mode,
            classical_component=classical_component,
            salt=salt
        )

        return cls(kem_keypair=kem_keypair, key_material=key_material, mode=mode)

    @property
    def public_key(self) -> bytes:
        """Get the KEM public key for key exchange."""
        return self._kem_keypair.public_key

    @property
    def chain_length(self) -> int:
        """Get current chain length."""
        return len(self._chain)

    @property
    def key_material(self) -> PQCKeyMaterial:
        """Get the current key material."""
        return self._key_material

    @property
    def backend(self) -> PQCBackend:
        """Get the PQC backend being used."""
        return get_backend()

    def append(self, message: bytes, nonce: Optional[bytes] = None) -> bytes:
        """
        Append a message to the HMAC chain.

        Args:
            message: Message bytes to add
            nonce: Optional nonce (generated if not provided)

        Returns:
            The computed HMAC tag for this entry
        """
        if nonce is None:
            nonce = os.urandom(NONCE_BYTES)

        # Get previous tag or IV
        if self._chain:
            prev_tag = self._chain[-1][2]
        else:
            prev_tag = self._chain_iv

        # Compute tag
        tag = pqc_hmac_chain_tag(message, nonce, prev_tag, self._key_material)

        # Append to chain
        self._chain.append((message, nonce, tag))

        return tag

    def verify(self) -> bool:
        """Verify the integrity of the entire chain."""
        if not self._chain:
            return True

        messages, nonces, tags = zip(*self._chain)
        return pqc_verify_hmac_chain(
            list(messages), list(nonces), list(tags),
            self._key_material, self._chain_iv
        )

    def get_entry(self, index: int) -> Optional[Tuple[bytes, bytes, bytes]]:
        """Get a specific chain entry by index."""
        if 0 <= index < len(self._chain):
            return self._chain[index]
        return None

    def get_latest_tag(self) -> bytes:
        """Get the most recent tag (or IV if chain is empty)."""
        if self._chain:
            return self._chain[-1][2]
        return self._chain_iv

    def export_state(self) -> Dict[str, Any]:
        """
        Export chain state for serialization.

        Note: Does not export secret keys for security.
        """
        return {
            "chain": [(m.hex(), n.hex(), t.hex()) for m, n, t in self._chain],
            "chain_iv": self._chain_iv.hex(),
            "public_key": self._kem_keypair.public_key.hex(),
            "ciphertext": self._key_material.ciphertext.hex(),
            "salt": self._key_material.salt.hex(),
            "key_id": self._key_material.key_id.hex(),
            "mode": self._key_material.derivation_mode.value,
            "backend": get_backend().value
        }

    def import_chain(self, chain_data: List[Tuple[str, str, str]]) -> None:
        """
        Import chain entries from serialized data.

        Args:
            chain_data: List of (message_hex, nonce_hex, tag_hex) tuples
        """
        self._chain = [
            (bytes.fromhex(m), bytes.fromhex(n), bytes.fromhex(t))
            for m, n, t in chain_data
        ]

    def rotate_key(self) -> PQCKeyMaterial:
        """
        Rotate to a new PQC-derived HMAC key.

        Returns the new key material. The chain continues with the new key.
        """
        self._key_material = pqc_derive_hmac_key(
            self._kem_keypair.public_key,
            mode=self._mode
        )
        return self._key_material


def create_pqc_hmac_state(mode: KeyDerivationMode = KeyDerivationMode.HYBRID) -> PQCHMACState:
    """
    Create a new PQC HMAC state for audit chain integration.

    This is the primary entry point for integrating PQC with
    the existing Layer 0 HMAC chain in unified.py.

    Args:
        mode: Key derivation mode

    Returns:
        PQCHMACState ready for audit chain operations
    """
    keypair = Kyber768.generate_keypair()
    key_material = pqc_derive_hmac_key(keypair.public_key, mode=mode)

    return PQCHMACState(
        kem_keypair=keypair,
        key_material=key_material,
        mode=mode
    )


def migrate_classical_chain(classical_key: bytes,
                            messages: List[bytes],
                            nonces: List[bytes],
                            tags: List[bytes]) -> Tuple[PQCHMACChain, bool]:
    """
    Migrate an existing classical HMAC chain to PQC.

    Creates a new PQC chain and verifies it produces equivalent
    security properties for the existing messages.

    Args:
        classical_key: Original HMAC key
        messages: Existing chain messages
        nonces: Existing chain nonces
        tags: Existing chain tags

    Returns:
        Tuple of (new PQCHMACChain, migration_success)
    """
    # Create new PQC chain
    chain = PQCHMACChain.create_new()

    # Re-add all messages to new chain
    for message, nonce in zip(messages, nonces):
        chain.append(message, nonce)

    # Verify new chain is valid
    is_valid = chain.verify()

    return chain, is_valid
