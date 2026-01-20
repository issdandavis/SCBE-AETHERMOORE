"""
Real World Protocol v3.0 with Sacred Tongue Encoding
====================================================
Integrates: Argon2id KDF → ML-KEM-768 → XChaCha20-Poly1305 → Sacred Tongues

Last Updated: January 18, 2026
Version: 3.0.0

Security Stack:
1. Argon2id KDF (RFC 9106) for password → key derivation
2. ML-KEM-768 for quantum-resistant key exchange (optional)
3. XChaCha20-Poly1305 for AEAD encryption
4. ML-DSA-65 for quantum-resistant signatures (optional)
5. Sacred Tongue encoding for semantic binding

Dependencies:
    pip install argon2-cffi pycryptodome liboqs-python
"""

import os
import secrets
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import struct
import json

# Crypto primitives
try:
    from argon2 import PasswordHasher
    from argon2.low_level import Type as Argon2Type, hash_secret_raw
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False
    print("Warning: argon2-cffi not installed. Install with: pip install argon2-cffi")

try:
    from Crypto.Cipher import ChaCha20_Poly1305
    CHACHA_AVAILABLE = True
except ImportError:
    CHACHA_AVAILABLE = False
    print("Warning: pycryptodome not installed. Install with: pip install pycryptodome")

try:
    import oqs  # liboqs-python for ML-KEM/ML-DSA
    OQS_AVAILABLE = True
except ImportError:
    OQS_AVAILABLE = False
    print("Warning: liboqs-python not installed. Install with: pip install liboqs-python")

from .sacred_tongues import SACRED_TONGUE_TOKENIZER, SECTION_TONGUES


# ============================================================
# RFC 9106 ARGON2ID PARAMETERS (Production-grade)
# ============================================================

ARGON2_PARAMS = {
    'time_cost': 3,        # Iterations (3 = 0.5s on modern CPU)
    'memory_cost': 65536,  # 64 MB memory
    'parallelism': 4,      # 4 threads
    'hash_len': 32,        # 256-bit key output
    'salt_len': 16,        # 128-bit salt
    'type': Argon2Type.ID if ARGON2_AVAILABLE else None,  # Argon2id (hybrid mode)
}


# ============================================================
# RWP v3.0 ENVELOPE STRUCTURE
# ============================================================

@dataclass
class RWPEnvelope:
    """
    Real World Protocol v3.0 envelope with Sacred Tongue encoding.
    
    Structure (all fields encoded as Sacred Tongue tokens):
    - aad: Additional Authenticated Data (Avali)
    - salt: Argon2id salt (Runethic)
    - nonce: XChaCha20 24-byte nonce (Kor'aelin)
    - ct: Ciphertext (Cassisivadan)
    - tag: Poly1305 MAC tag (Draumric)
    - ml_kem_ct: ML-KEM-768 encapsulated shared secret (optional, Umbroth)
    - ml_dsa_sig: ML-DSA-65 signature (optional, Draumric)
    """
    aad: List[str]           # Avali tokens
    salt: List[str]          # Runethic tokens
    nonce: List[str]         # Kor'aelin tokens
    ct: List[str]            # Cassisivadan tokens
    tag: List[str]           # Draumric tokens
    ml_kem_ct: Optional[List[str]] = None  # Umbroth (if PQC enabled)
    ml_dsa_sig: Optional[List[str]] = None # Draumric (if signed)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        d = {
            'version': ['rwp', 'v3', 'alpha'],  # Version marker
            'aad': self.aad,
            'salt': self.salt,
            'nonce': self.nonce,
            'ct': self.ct,
            'tag': self.tag,
        }
        if self.ml_kem_ct:
            d['ml_kem_ct'] = self.ml_kem_ct
        if self.ml_dsa_sig:
            d['ml_dsa_sig'] = self.ml_dsa_sig
        return d
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'RWPEnvelope':
        """Deserialize from dict."""
        return cls(
            aad=d['aad'],
            salt=d['salt'],
            nonce=d['nonce'],
            ct=d['ct'],
            tag=d['tag'],
            ml_kem_ct=d.get('ml_kem_ct'),
            ml_dsa_sig=d.get('ml_dsa_sig'),
        )


# ============================================================
# RWP v3.0 ENCRYPTION/DECRYPTION
# ============================================================

class RWPv3Protocol:
    """
    Real World Protocol v3.0 with post-quantum hybrid encryption.
    
    Security stack:
    1. Argon2id KDF (RFC 9106) for password → key derivation
    2. ML-KEM-768 for quantum-resistant key exchange (optional)
    3. XChaCha20-Poly1305 for AEAD encryption
    4. ML-DSA-65 for quantum-resistant signatures (optional)
    5. Sacred Tongue encoding for semantic binding
    """
    
    def __init__(self, enable_pqc: bool = False):
        if not ARGON2_AVAILABLE:
            raise ImportError("argon2-cffi required. Install with: pip install argon2-cffi")
        if not CHACHA_AVAILABLE:
            raise ImportError("pycryptodome required. Install with: pip install pycryptodome")
        
        self.tokenizer = SACRED_TONGUE_TOKENIZER
        self.enable_pqc = enable_pqc
        
        if enable_pqc:
            if not OQS_AVAILABLE:
                raise ImportError("liboqs-python required for PQC. Install with: pip install liboqs-python")
            self.kem = oqs.KeyEncapsulation("Kyber768")  # ML-KEM-768
            self.sig = oqs.Signature("Dilithium3")       # ML-DSA-65
    
    def _derive_key(self, password: bytes, salt: bytes) -> bytes:
        """Derive 256-bit key using Argon2id (RFC 9106)."""
        return hash_secret_raw(
            secret=password,
            salt=salt,
            time_cost=ARGON2_PARAMS['time_cost'],
            memory_cost=ARGON2_PARAMS['memory_cost'],
            parallelism=ARGON2_PARAMS['parallelism'],
            hash_len=ARGON2_PARAMS['hash_len'],
            type=ARGON2_PARAMS['type'],
        )
    
    def encrypt(
        self,
        password: bytes,
        plaintext: bytes,
        aad: bytes = b'',
        ml_kem_public_key: Optional[bytes] = None,
        ml_dsa_private_key: Optional[bytes] = None,
    ) -> RWPEnvelope:
        """
        Encrypt plaintext using RWP v3.0 protocol.
        
        Args:
            password: User password for Argon2id KDF
            plaintext: Data to encrypt
            aad: Additional Authenticated Data (e.g., metadata, timestamp)
            ml_kem_public_key: ML-KEM-768 public key (if PQC enabled)
            ml_dsa_private_key: ML-DSA-65 private key (if signing)
        
        Returns:
            RWPEnvelope with all sections encoded as Sacred Tongue tokens
        """
        # Generate cryptographic material
        salt = secrets.token_bytes(ARGON2_PARAMS['salt_len'])
        nonce = secrets.token_bytes(24)  # XChaCha20 requires 24 bytes
        
        # Derive encryption key
        key = self._derive_key(password, salt)
        
        # Optional: Hybrid PQC key exchange
        ml_kem_ct_bytes = None
        if self.enable_pqc and ml_kem_public_key:
            ml_kem_shared_secret, ml_kem_ct_bytes = self.kem.encap_secret(ml_kem_public_key)
            # XOR shared secret into key (hybrid mode)
            key = bytes(a ^ b for a, b in zip(key, ml_kem_shared_secret[:32]))
        
        # AEAD encryption: XChaCha20-Poly1305
        cipher = ChaCha20_Poly1305.new(key=key, nonce=nonce)
        cipher.update(aad)
        ct, tag = cipher.encrypt_and_digest(plaintext)
        
        # Optional: Sign the envelope
        ml_dsa_sig_bytes = None
        if self.enable_pqc and ml_dsa_private_key:
            # Sign concatenation of AAD || salt || nonce || ct || tag
            message = aad + salt + nonce + ct + tag
            ml_dsa_sig_bytes = self.sig.sign(message, ml_dsa_private_key)
        
        # Encode all sections as Sacred Tongue tokens
        envelope = RWPEnvelope(
            aad=self.tokenizer.encode_section('aad', aad),
            salt=self.tokenizer.encode_section('salt', salt),
            nonce=self.tokenizer.encode_section('nonce', nonce),
            ct=self.tokenizer.encode_section('ct', ct),
            tag=self.tokenizer.encode_section('tag', tag),
            ml_kem_ct=self.tokenizer.encode_section('redact', ml_kem_ct_bytes) if ml_kem_ct_bytes else None,
            ml_dsa_sig=self.tokenizer.encode_section('tag', ml_dsa_sig_bytes) if ml_dsa_sig_bytes else None,
        )
        
        return envelope
    
    def decrypt(
        self,
        password: bytes,
        envelope: RWPEnvelope,
        ml_kem_secret_key: Optional[bytes] = None,
        ml_dsa_public_key: Optional[bytes] = None,
    ) -> bytes:
        """
        Decrypt RWP v3.0 envelope.
        
        Args:
            password: User password for Argon2id KDF
            envelope: RWPEnvelope with Sacred Tongue encoded sections
            ml_kem_secret_key: ML-KEM-768 secret key (if PQC enabled)
            ml_dsa_public_key: ML-DSA-65 public key (if signature verification required)
        
        Returns:
            Decrypted plaintext
        
        Raises:
            ValueError: On authentication failure or invalid envelope
        """
        # Decode Sacred Tongue tokens → bytes
        aad = self.tokenizer.decode_section('aad', envelope.aad)
        salt = self.tokenizer.decode_section('salt', envelope.salt)
        nonce = self.tokenizer.decode_section('nonce', envelope.nonce)
        ct = self.tokenizer.decode_section('ct', envelope.ct)
        tag = self.tokenizer.decode_section('tag', envelope.tag)
        
        # Derive decryption key
        key = self._derive_key(password, salt)
        
        # Optional: Hybrid PQC key exchange
        if self.enable_pqc and envelope.ml_kem_ct and ml_kem_secret_key:
            ml_kem_ct_bytes = self.tokenizer.decode_section('redact', envelope.ml_kem_ct)
            ml_kem_shared_secret = self.kem.decap_secret(ml_kem_ct_bytes, ml_kem_secret_key)
            # XOR shared secret into key
            key = bytes(a ^ b for a, b in zip(key, ml_kem_shared_secret[:32]))
        
        # Optional: Verify signature
        if self.enable_pqc and envelope.ml_dsa_sig and ml_dsa_public_key:
            ml_dsa_sig_bytes = self.tokenizer.decode_section('tag', envelope.ml_dsa_sig)
            message = aad + salt + nonce + ct + tag
            is_valid = self.sig.verify(message, ml_dsa_sig_bytes, ml_dsa_public_key)
            if not is_valid:
                raise ValueError("ML-DSA-65 signature verification failed")
        
        # AEAD decryption: XChaCha20-Poly1305
        cipher = ChaCha20_Poly1305.new(key=key, nonce=nonce)
        cipher.update(aad)
        try:
            plaintext = cipher.decrypt_and_verify(ct, tag)
        except ValueError as e:
            raise ValueError(f"AEAD authentication failed: {e}")
        
        return plaintext


# ============================================================
# CONVENIENCE API
# ============================================================

def rwp_encrypt_message(
    password: str,
    message: str,
    metadata: Optional[Dict] = None,
    enable_pqc: bool = False,
) -> Dict:
    """
    High-level API: Encrypt a message with RWP v3.0.
    
    Example:
        envelope = rwp_encrypt_message("my-password", "Hello, Mars!")
        # Returns: {'version': [...], 'aad': [...], 'salt': [...], ...}
    """
    protocol = RWPv3Protocol(enable_pqc=enable_pqc)
    
    aad = json.dumps(metadata or {}).encode('utf-8')
    envelope = protocol.encrypt(
        password=password.encode('utf-8'),
        plaintext=message.encode('utf-8'),
        aad=aad,
    )
    
    return envelope.to_dict()


def rwp_decrypt_message(
    password: str,
    envelope_dict: Dict,
    enable_pqc: bool = False,
) -> str:
    """
    High-level API: Decrypt an RWP v3.0 envelope.
    
    Example:
        message = rwp_decrypt_message("my-password", envelope_dict)
        # Returns: "Hello, Mars!"
    """
    protocol = RWPv3Protocol(enable_pqc=enable_pqc)
    envelope = RWPEnvelope.from_dict(envelope_dict)
    
    plaintext = protocol.decrypt(
        password=password.encode('utf-8'),
        envelope=envelope,
    )
    
    return plaintext.decode('utf-8')
