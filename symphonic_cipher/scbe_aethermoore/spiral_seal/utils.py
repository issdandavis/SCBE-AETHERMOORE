"""
SpiralSeal SS1 Cryptographic Utilities

Low-level crypto functions for AES-GCM and key derivation.
"""

import os
import hmac
import hashlib
from typing import Tuple

# Try to import from the main spiral_seal module
try:
    from .spiral_seal import (
        derive_key as _derive_key,
        derive_key_hkdf,
        encrypt_hmac_ctr,
        decrypt_hmac_ctr,
        TAG_SIZE,
        SALT_SIZE,
        _try_load_cryptography,
        _CRYPTOGRAPHY_AVAILABLE,
        AESGCM,
    )
    _SPIRAL_SEAL_AVAILABLE = True
except ImportError:
    _SPIRAL_SEAL_AVAILABLE = False


def derive_key(password: bytes, salt: bytes, key_len: int = 32) -> bytes:
    """Derive encryption key from password and salt.

    Uses the best available KDF (Argon2id > scrypt > HKDF).

    Args:
        password: Password bytes
        salt: Salt bytes (should be random, at least 16 bytes)
        key_len: Desired key length (default 32 for AES-256)

    Returns:
        Derived key bytes
    """
    if _SPIRAL_SEAL_AVAILABLE:
        return _derive_key(password, salt)
    else:
        # Fallback to HKDF
        prk = hmac.new(salt, password, hashlib.sha256).digest()
        return hmac.new(prk, b"\x01", hashlib.sha256).digest()[:key_len]


def aes_gcm_encrypt(key: bytes, plaintext: bytes, aad: bytes = b"") -> Tuple[bytes, bytes, bytes]:
    """Encrypt using AES-256-GCM.

    Args:
        key: 32-byte encryption key
        plaintext: Data to encrypt
        aad: Associated authenticated data (optional)

    Returns:
        Tuple of (nonce, ciphertext, tag)
    """
    nonce = os.urandom(12)  # AES-GCM uses 12-byte nonce

    _try_load_cryptography()
    if _CRYPTOGRAPHY_AVAILABLE and AESGCM is not None:
        aesgcm = AESGCM(key)
        ct_with_tag = aesgcm.encrypt(nonce, plaintext, aad)
        ct = ct_with_tag[:-16]
        tag = ct_with_tag[-16:]
        return nonce, ct, tag
    else:
        # Fallback to HMAC-CTR (not as secure but works without external deps)
        ct, tag = encrypt_hmac_ctr(key, nonce, plaintext, aad)
        return nonce, ct, tag


def aes_gcm_decrypt(key: bytes, nonce: bytes, ciphertext: bytes, tag: bytes,
                    aad: bytes = b"") -> bytes:
    """Decrypt using AES-256-GCM.

    Args:
        key: 32-byte encryption key
        nonce: 12-byte nonce used during encryption
        ciphertext: Encrypted data
        tag: 16-byte authentication tag
        aad: Associated authenticated data (must match encryption)

    Returns:
        Decrypted plaintext

    Raises:
        ValueError: If authentication fails
    """
    _try_load_cryptography()
    if _CRYPTOGRAPHY_AVAILABLE and AESGCM is not None:
        aesgcm = AESGCM(key)
        ct_with_tag = ciphertext + tag
        try:
            return aesgcm.decrypt(nonce, ct_with_tag, aad)
        except Exception as e:
            raise ValueError(f"Authentication failed: {e}")
    else:
        # Fallback
        try:
            return decrypt_hmac_ctr(key, nonce, ciphertext, tag, aad)
        except Exception as e:
            raise ValueError(f"Authentication failed: {e}")


def generate_key_id(prefix: str = "k") -> str:
    """Generate a random key ID.

    Args:
        prefix: Key ID prefix (default "k")

    Returns:
        Key ID string like "k01" or "k1a2b3c"
    """
    random_part = os.urandom(3).hex()
    return f"{prefix}{random_part}"


def constant_time_compare(a: bytes, b: bytes) -> bool:
    """Compare two byte strings in constant time.

    Prevents timing attacks when comparing secrets.
    """
    return hmac.compare_digest(a, b)
