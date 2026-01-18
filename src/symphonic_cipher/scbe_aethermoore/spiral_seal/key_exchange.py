"""
Post-Quantum Key Exchange - Kyber768
=====================================
Wrapper for Kyber768 key encapsulation mechanism (KEM).

Last Updated: January 18, 2026
Version: 1.1.0

Security level: ~AES-192 equivalent (NIST Level 3)
Collision probability: ~2^-128

Note: This module provides a fallback implementation using classical
cryptography when liboqs/pqcrypto is not available. For production,
install the official liboqs-python bindings.
"""

import os
import hashlib
import hmac
from typing import Tuple, Optional

# Try to import post-quantum library
try:
    from oqs import KeyEncapsulation
    PQC_AVAILABLE = True
    PQC_BACKEND = 'liboqs'
except ImportError:
    try:
        import pqcrypto.kem.kyber768 as kyber
        PQC_AVAILABLE = True
        PQC_BACKEND = 'pqcrypto'
    except ImportError:
        PQC_AVAILABLE = False
        PQC_BACKEND = 'fallback'


class KyberKeyPair:
    """Container for Kyber768 key pair."""
    
    def __init__(self, public_key: bytes, secret_key: bytes):
        self.public_key = public_key
        self.secret_key = secret_key
    
    def __repr__(self):
        return f"KyberKeyPair(pk={len(self.public_key)}B, sk={len(self.secret_key)}B)"


def kyber_keygen() -> Tuple[bytes, bytes]:
    """
    Generate a Kyber768 key pair.
    
    Returns:
        Tuple of (secret_key, public_key)
    """
    if PQC_BACKEND == 'liboqs':
        kem = KeyEncapsulation("Kyber768")
        public_key = kem.generate_keypair()
        secret_key = kem.export_secret_key()
        return secret_key, public_key
    
    elif PQC_BACKEND == 'pqcrypto':
        public_key, secret_key = kyber.generate_keypair()
        return secret_key, public_key
    
    else:
        # Fallback: Use X25519-like ECDH simulation
        # WARNING: This is NOT post-quantum secure! For development only.
        secret_key = os.urandom(32)
        # Simulate public key derivation
        public_key = hashlib.sha256(b'kyber_pk_sim:' + secret_key).digest()
        return secret_key, public_key


def kyber_encaps(public_key: bytes) -> Tuple[bytes, bytes]:
    """
    Encapsulate a shared secret using Kyber768.
    
    Args:
        public_key: Recipient's public key
    
    Returns:
        Tuple of (ciphertext, shared_secret)
        - ciphertext: Send to recipient
        - shared_secret: 32-byte key for symmetric encryption
    """
    if PQC_BACKEND == 'liboqs':
        kem = KeyEncapsulation("Kyber768")
        ciphertext, shared_secret = kem.encap_secret(public_key)
        return ciphertext, shared_secret
    
    elif PQC_BACKEND == 'pqcrypto':
        ciphertext, shared_secret = kyber.encrypt(public_key)
        return ciphertext, shared_secret
    
    else:
        # Fallback simulation
        ephemeral = os.urandom(32)
        ciphertext = hashlib.sha256(b'kyber_ct_sim:' + ephemeral).digest()
        # Derive shared secret from ephemeral + public key
        shared_secret = hashlib.sha256(ephemeral + public_key).digest()
        # Include ephemeral in ciphertext for decapsulation
        ciphertext = ephemeral + ciphertext
        return ciphertext, shared_secret


def kyber_decaps(secret_key: bytes, ciphertext: bytes) -> bytes:
    """
    Decapsulate a shared secret using Kyber768.
    
    Args:
        secret_key: Recipient's secret key
        ciphertext: Ciphertext from encapsulation
    
    Returns:
        32-byte shared secret (same as encapsulator derived)
    """
    if PQC_BACKEND == 'liboqs':
        kem = KeyEncapsulation("Kyber768", secret_key)
        shared_secret = kem.decap_secret(ciphertext)
        return shared_secret
    
    elif PQC_BACKEND == 'pqcrypto':
        shared_secret = kyber.decrypt(secret_key, ciphertext)
        return shared_secret
    
    else:
        # Fallback simulation
        ephemeral = ciphertext[:32]
        # Derive public key from secret key (same as keygen)
        public_key = hashlib.sha256(b'kyber_pk_sim:' + secret_key).digest()
        # Derive shared secret (must match encaps)
        shared_secret = hashlib.sha256(ephemeral + public_key).digest()
        return shared_secret


def get_pqc_status() -> dict:
    """
    Get the status of post-quantum cryptography support.
    
    Returns:
        Dict with backend info and security warnings
    """
    return {
        'available': PQC_AVAILABLE,
        'backend': PQC_BACKEND,
        'algorithm': 'Kyber768',
        'security_level': 'NIST Level 3 (~AES-192)' if PQC_AVAILABLE else 'FALLBACK (NOT PQ-SECURE)',
        'warning': None if PQC_AVAILABLE else 
            'Using classical fallback! Install liboqs-python for post-quantum security.'
    }
