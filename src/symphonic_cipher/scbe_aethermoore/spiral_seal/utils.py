"""
Cryptographic utilities for SpiralSeal SS1.
AES-256-GCM encryption/decryption with constant-time operations.

Last Updated: January 18, 2026
Version: 1.1.0
"""

import os
import hmac
import hashlib
from typing import Tuple

# Try to use PyCryptodome, fall back to cryptography
try:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
    CRYPTO_BACKEND = 'pycryptodome'
except ImportError:
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        CRYPTO_BACKEND = 'cryptography'
    except ImportError:
        CRYPTO_BACKEND = 'none'


def get_random(n: int) -> bytes:
    """Generate n cryptographically secure random bytes."""
    return os.urandom(n)


def aes_gcm_encrypt(key: bytes, plaintext: bytes, aad: bytes = b'') -> Tuple[bytes, bytes, bytes]:
    """
    AES-256-GCM encryption.
    
    Args:
        key: 32-byte symmetric key
        plaintext: Data to encrypt
        aad: Additional authenticated data (not encrypted, but authenticated)
    
    Returns:
        Tuple of (nonce, ciphertext, tag)
    """
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes for AES-256")
    
    nonce = get_random(12)  # 96-bit nonce for GCM
    
    if CRYPTO_BACKEND == 'pycryptodome':
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        if aad:
            cipher.update(aad)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext)
        return nonce, ciphertext, tag
    
    elif CRYPTO_BACKEND == 'cryptography':
        aesgcm = AESGCM(key)
        ct_with_tag = aesgcm.encrypt(nonce, plaintext, aad if aad else None)
        # cryptography library appends tag to ciphertext
        ciphertext = ct_with_tag[:-16]
        tag = ct_with_tag[-16:]
        return nonce, ciphertext, tag
    
    else:
        raise RuntimeError("No cryptographic backend available. Install pycryptodome or cryptography.")


def aes_gcm_decrypt(key: bytes, nonce: bytes, ciphertext: bytes, tag: bytes, aad: bytes = b'') -> bytes:
    """
    AES-256-GCM decryption with authentication.
    
    Args:
        key: 32-byte symmetric key
        nonce: 12-byte nonce used during encryption
        ciphertext: Encrypted data
        tag: 16-byte authentication tag
        aad: Additional authenticated data (must match encryption)
    
    Returns:
        Decrypted plaintext
    
    Raises:
        ValueError: If authentication fails (tampered data)
    """
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes for AES-256")
    if len(nonce) != 12:
        raise ValueError("Nonce must be 12 bytes")
    if len(tag) != 16:
        raise ValueError("Tag must be 16 bytes")
    
    if CRYPTO_BACKEND == 'pycryptodome':
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        if aad:
            cipher.update(aad)
        try:
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
            return plaintext
        except ValueError:
            raise ValueError("Authentication failed - data may be tampered")
    
    elif CRYPTO_BACKEND == 'cryptography':
        aesgcm = AESGCM(key)
        ct_with_tag = ciphertext + tag
        try:
            plaintext = aesgcm.decrypt(nonce, ct_with_tag, aad if aad else None)
            return plaintext
        except Exception:
            raise ValueError("Authentication failed - data may be tampered")
    
    else:
        raise RuntimeError("No cryptographic backend available.")


def constant_time_compare(a: bytes, b: bytes) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    return hmac.compare_digest(a, b)


def derive_key(master_secret: bytes, salt: bytes, info: bytes, length: int = 32) -> bytes:
    """
    HKDF-SHA256 key derivation.
    
    Args:
        master_secret: Input key material
        salt: Random salt (can be empty)
        info: Context/application-specific info
        length: Desired output length in bytes
    
    Returns:
        Derived key material
    """
    # HKDF-Extract
    if not salt:
        salt = b'\x00' * 32
    prk = hmac.new(salt, master_secret, hashlib.sha256).digest()
    
    # HKDF-Expand
    n = (length + 31) // 32
    okm = b''
    t = b''
    for i in range(1, n + 1):
        t = hmac.new(prk, t + info + bytes([i]), hashlib.sha256).digest()
        okm += t
    
    return okm[:length]


def sha256(data: bytes) -> bytes:
    """SHA-256 hash."""
    return hashlib.sha256(data).digest()


def sha256_hex(data: bytes) -> str:
    """SHA-256 hash as hex string."""
    return hashlib.sha256(data).hexdigest()
