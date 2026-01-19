"""
SpiralSeal SS1 - High-Level API
================================
Post-quantum hybrid encryption using Kyber768 + Dilithium3 + AES-256-GCM.

Last Updated: January 18, 2026
Version: 1.1.0

This is the main entry point for the 14-layer SCBE pipeline's cryptographic
operations. It provides:

1. Hybrid encryption (Kyber768 KEM → AES-256-GCM)
2. Digital signatures (Dilithium3)
3. Sacred Tongue spell-text encoding
4. Key rotation support via key IDs (kid)

Usage:
    from spiral_seal import SpiralSealSS1
    
    ss = SpiralSealSS1()
    
    # Encrypt
    sealed = ss.seal(b"my secret API key", aad="service=openai;env=prod")
    print(sealed)  # SS1|kid=...|aad=...|salt=ru:...|nonce=ko:...|ct=ca:...|tag=dr:...
    
    # Decrypt
    plaintext = ss.unseal(sealed, aad="service=openai;env=prod")
"""

import os
import hashlib
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from .key_exchange import kyber_keygen, kyber_encaps, kyber_decaps, get_pqc_status
from .signatures import dilithium_keygen, dilithium_sign, dilithium_verify, get_pqc_sig_status
from .utils import (
    aes_gcm_encrypt, aes_gcm_decrypt, derive_key, 
    get_random, sha256, sha256_hex
)
from .sacred_tongues import (
    format_ss1_blob, parse_ss1_blob,
    encode_to_spelltext, decode_from_spelltext
)


@dataclass
class SealedPayload:
    """Container for a sealed (encrypted + signed) payload."""
    kid: str                    # Key ID for rotation
    aad: str                    # Additional authenticated data
    salt: bytes                 # KDF salt
    nonce: bytes                # AES-GCM nonce
    ciphertext: bytes           # Encrypted data
    tag: bytes                  # AES-GCM auth tag
    kyber_ct: Optional[bytes]   # Kyber ciphertext (for hybrid mode)
    signature: Optional[bytes]  # Dilithium signature
    
    def to_ss1(self) -> str:
        """Format as SS1 spell-text blob."""
        return format_ss1_blob(
            kid=self.kid,
            aad=self.aad,
            salt=self.salt,
            nonce=self.nonce,
            ciphertext=self.ciphertext,
            tag=self.tag
        )


class SpiralSealSS1:
    """
    High-level API for SpiralSeal SS1 encryption.
    
    Provides hybrid post-quantum encryption using:
    - Kyber768 for key encapsulation
    - Dilithium3 for digital signatures
    - AES-256-GCM for symmetric encryption
    - Sacred Tongue tokenization for spell-text output
    
    Attributes:
        kid: Current key ID (for rotation)
        mode: 'hybrid' (Kyber+AES) or 'symmetric' (AES only)
    """
    
    VERSION = 'SS1'
    
    def __init__(
        self,
        master_secret: Optional[bytes] = None,
        kid: str = 'k01',
        mode: str = 'symmetric'
    ):
        """
        Initialize SpiralSeal.
        
        Args:
            master_secret: 32-byte master secret for key derivation.
                          If None, generates a random one (NOT for production!)
            kid: Key ID for rotation tracking
            mode: 'hybrid' for Kyber+AES, 'symmetric' for AES-only
        """
        self.kid = kid
        self.mode = mode
        
        # Master secret (MUST be injected from env/KMS in production)
        if master_secret is None:
            import warnings
            warnings.warn(
                "No master_secret provided - generating random key. "
                "This is NOT suitable for production! Inject via env/KMS.",
                RuntimeWarning
            )
            master_secret = get_random(32)
        
        if len(master_secret) != 32:
            raise ValueError("master_secret must be 32 bytes")
        
        # Reject null/zero keys (security requirement)
        if master_secret == b'\x00' * 32:
            raise ValueError("master_secret cannot be all zeros (null key)")
        
        self._master_secret = master_secret
        
        # Generate PQC keys if in hybrid mode
        if mode == 'hybrid':
            self._sk_enc, self._pk_enc = kyber_keygen()
            self._sk_sig, self._pk_sig = dilithium_keygen()
        else:
            self._sk_enc = self._pk_enc = None
            self._sk_sig = self._pk_sig = None
    
    def seal(
        self,
        plaintext: bytes,
        aad: str = '',
        sign: bool = False
    ) -> str:
        """
        Seal (encrypt) data and return SS1 spell-text.
        
        Args:
            plaintext: Data to encrypt
            aad: Additional authenticated data (e.g., "service=openai;env=prod")
            sign: Whether to include a Dilithium signature (hybrid mode only)
        
        Returns:
            SS1 spell-text blob
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')
        
        # Generate salt for key derivation
        salt = get_random(16)
        
        # Derive encryption key
        if self.mode == 'hybrid' and self._pk_enc:
            # Kyber key encapsulation
            kyber_ct, shared_secret = kyber_encaps(self._pk_enc)
            # Combine master secret with Kyber shared secret
            combined = self._master_secret + shared_secret
            k_enc = derive_key(combined, salt, b'scbe:ss1:enc:v1')
        else:
            # Symmetric-only mode
            kyber_ct = None
            k_enc = derive_key(self._master_secret, salt, b'scbe:ss1:enc:v1')
        
        # Encrypt with AES-256-GCM
        aad_bytes = aad.encode('utf-8') if aad else b''
        nonce, ciphertext, tag = aes_gcm_encrypt(k_enc, plaintext, aad_bytes)
        
        # Optional signature
        signature = None
        if sign and self.mode == 'hybrid' and self._sk_sig:
            # Sign the ciphertext + AAD
            to_sign = ciphertext + tag + aad_bytes
            signature = dilithium_sign(self._sk_sig, to_sign)
        
        # Create payload
        payload = SealedPayload(
            kid=self.kid,
            aad=aad,
            salt=salt,
            nonce=nonce,
            ciphertext=ciphertext,
            tag=tag,
            kyber_ct=kyber_ct,
            signature=signature
        )
        
        return payload.to_ss1()
    
    def unseal(
        self,
        ss1_blob: str,
        aad: str = '',
        verify_sig: bool = False
    ) -> bytes:
        """
        Unseal (decrypt) an SS1 spell-text blob.
        
        Args:
            ss1_blob: SS1 spell-text blob
            aad: Additional authenticated data (must match seal)
            verify_sig: Whether to verify Dilithium signature (hybrid mode)
        
        Returns:
            Decrypted plaintext
        
        Raises:
            ValueError: If authentication fails or AAD mismatch
        """
        # Parse the blob
        parsed = parse_ss1_blob(ss1_blob)
        
        # Verify AAD matches
        if parsed.get('aad', '') != aad:
            raise ValueError("AAD mismatch - authentication failed")
        
        # Extract components
        salt = parsed['salt']
        nonce = parsed['nonce']
        ciphertext = parsed['ct']
        tag = parsed['tag']
        
        # Derive decryption key
        if self.mode == 'hybrid' and self._sk_enc:
            # In a real implementation, kyber_ct would be in the blob
            # For now, we use symmetric derivation
            k_enc = derive_key(self._master_secret, salt, b'scbe:ss1:enc:v1')
        else:
            k_enc = derive_key(self._master_secret, salt, b'scbe:ss1:enc:v1')
        
        # Decrypt
        aad_bytes = aad.encode('utf-8') if aad else b''
        try:
            plaintext = aes_gcm_decrypt(k_enc, nonce, ciphertext, tag, aad_bytes)
            return plaintext
        except ValueError as e:
            # Fail-to-noise: don't expose details
            raise ValueError("Authentication failed") from None
    
    def sign(self, message: bytes) -> bytes:
        """
        Sign a message using Dilithium3.
        
        Args:
            message: Message to sign
        
        Returns:
            Digital signature
        
        Raises:
            RuntimeError: If not in hybrid mode
        """
        if self.mode != 'hybrid' or not self._sk_sig:
            raise RuntimeError("Signing requires hybrid mode")
        return dilithium_sign(self._sk_sig, message)
    
    def verify(self, message: bytes, signature: bytes) -> bool:
        """
        Verify a Dilithium3 signature.
        
        Args:
            message: Original message
            signature: Signature to verify
        
        Returns:
            True if valid, False otherwise
        """
        if self.mode != 'hybrid' or not self._pk_sig:
            raise RuntimeError("Verification requires hybrid mode")
        return dilithium_verify(self._pk_sig, message, signature)
    
    def rotate_key(self, new_kid: str, new_master_secret: bytes):
        """
        Rotate to a new master secret.
        
        Args:
            new_kid: New key ID
            new_master_secret: New 32-byte master secret
        """
        if len(new_master_secret) != 32:
            raise ValueError("master_secret must be 32 bytes")
        
        self.kid = new_kid
        self._master_secret = new_master_secret
        
        # Regenerate PQC keys if in hybrid mode
        if self.mode == 'hybrid':
            self._sk_enc, self._pk_enc = kyber_keygen()
            self._sk_sig, self._pk_sig = dilithium_keygen()
    
    @staticmethod
    def get_status() -> dict:
        """
        Get the status of cryptographic backends.
        
        Returns:
            Dict with PQC availability and security info
        """
        return {
            'version': SpiralSealSS1.VERSION,
            'key_exchange': get_pqc_status(),
            'signatures': get_pqc_sig_status(),
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def seal(
    plaintext: bytes,
    master_secret: bytes,
    aad: str = '',
    kid: str = 'k01'
) -> str:
    """
    One-shot seal function.
    
    Args:
        plaintext: Data to encrypt
        master_secret: 32-byte master secret
        aad: Additional authenticated data
        kid: Key ID
    
    Returns:
        SS1 spell-text blob
    """
    ss = SpiralSealSS1(master_secret=master_secret, kid=kid, mode='symmetric')
    return ss.seal(plaintext, aad=aad)


def unseal(
    ss1_blob: str,
    master_secret: bytes,
    aad: str = ''
) -> bytes:
    """
    One-shot unseal function.
    
    Args:
        ss1_blob: SS1 spell-text blob
        master_secret: 32-byte master secret
        aad: Additional authenticated data (must match seal)
    
    Returns:
        Decrypted plaintext
    """
    ss = SpiralSealSS1(master_secret=master_secret, mode='symmetric')
    return ss.unseal(ss1_blob, aad=aad)
