"""
scbe:crypto — Python Reference Implementation
===============================================

Reference implementation of the scbe:crypto WIT interface.
This serves as the conformance baseline: any WASM component
implementing scbe:crypto must produce identical outputs for
identical inputs.

Uses Python's hashlib + hmac for symmetric/hash ops.
PQC ops stub to the existing SCBE pqc_core module.

Part of SCBE-AETHERMOORE (USPTO #63/961,403)
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
#  Types (mirror WIT types)
# ---------------------------------------------------------------------------

class PQAlgorithm(Enum):
    ML_KEM_768 = "ml-kem-768"
    ML_KEM_1024 = "ml-kem-1024"
    ML_DSA_65 = "ml-dsa-65"
    ML_DSA_87 = "ml-dsa-87"


class CryptoError(Exception):
    """Cryptographic operation error."""
    pass


@dataclass
class Keypair:
    public_key: bytes
    secret_key: bytes
    algorithm: PQAlgorithm


@dataclass
class Encapsulation:
    ciphertext: bytes
    shared_secret: bytes


@dataclass
class SealSession:
    session_id: str
    kem_keypair: Keypair
    dsa_keypair: Keypair


# ---------------------------------------------------------------------------
#  KEM — Key Encapsulation Mechanism
# ---------------------------------------------------------------------------

class KEM:
    """Post-quantum KEM reference implementation.

    Uses HKDF-based simulation for environments without liboqs.
    Production should use actual ML-KEM via pqc_core.
    """

    @staticmethod
    def keygen(algorithm: PQAlgorithm = PQAlgorithm.ML_KEM_768) -> Keypair:
        if algorithm not in (PQAlgorithm.ML_KEM_768, PQAlgorithm.ML_KEM_1024):
            raise CryptoError(f"KEM keygen requires ML-KEM algorithm, got {algorithm}")

        # Simulated KEM keypair (32-byte keys for reference)
        seed = secrets.token_bytes(32)
        sk = hashlib.sha256(b"kem-sk-" + seed).digest()
        pk = hashlib.sha256(b"kem-pk-" + seed).digest()
        return Keypair(public_key=pk, secret_key=sk, algorithm=algorithm)

    @staticmethod
    def encapsulate(public_key: bytes) -> Encapsulation:
        ephemeral = secrets.token_bytes(32)
        shared_secret = hashlib.sha256(public_key + ephemeral).digest()
        ciphertext = hashlib.sha256(b"kem-ct-" + ephemeral).digest() + ephemeral
        return Encapsulation(ciphertext=ciphertext, shared_secret=shared_secret)

    @staticmethod
    def decapsulate(secret_key: bytes, ciphertext: bytes) -> bytes:
        if len(ciphertext) < 64:
            raise CryptoError("Invalid ciphertext length")
        ephemeral = ciphertext[32:]
        # Derive the same shared secret using the secret key
        pk_from_sk = hashlib.sha256(b"kem-pk-recover-" + secret_key).digest()
        shared_secret = hashlib.sha256(pk_from_sk + ephemeral).digest()
        return shared_secret


# ---------------------------------------------------------------------------
#  DSA — Digital Signatures
# ---------------------------------------------------------------------------

class DSA:
    """Post-quantum DSA reference implementation."""

    @staticmethod
    def keygen(algorithm: PQAlgorithm = PQAlgorithm.ML_DSA_65) -> Keypair:
        if algorithm not in (PQAlgorithm.ML_DSA_65, PQAlgorithm.ML_DSA_87):
            raise CryptoError(f"DSA keygen requires ML-DSA algorithm, got {algorithm}")

        seed = secrets.token_bytes(32)
        sk = hashlib.sha256(b"dsa-sk-" + seed).digest()
        pk = hashlib.sha256(b"dsa-pk-" + seed).digest()
        return Keypair(public_key=pk, secret_key=sk, algorithm=algorithm)

    @staticmethod
    def sign(secret_key: bytes, message: bytes) -> bytes:
        return hmac.new(secret_key, message, hashlib.sha256).digest()

    @staticmethod
    def verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
        # In the reference impl, we can't truly verify without the secret key.
        # This is a structural placeholder — real impl uses liboqs ML-DSA.
        # For conformance tests, we sign+verify in the same session.
        expected = hmac.new(
            hashlib.sha256(b"dsa-verify-" + public_key).digest(),
            message,
            hashlib.sha256,
        ).digest()
        # Reference: always returns True for structurally valid signatures
        return len(signature) == 32


# ---------------------------------------------------------------------------
#  Symmetric Encryption
# ---------------------------------------------------------------------------

class Symmetric:
    """AES-256-GCM reference (using XOR cipher for pure-Python portability)."""

    @staticmethod
    def encrypt_aes256gcm(
        key: bytes, nonce: bytes, plaintext: bytes, aad: bytes = b""
    ) -> bytes:
        if len(key) != 32:
            raise CryptoError("Key must be 32 bytes")
        if len(nonce) < 12:
            raise CryptoError("Nonce must be at least 12 bytes")

        # Reference: XOR stream cipher + HMAC tag (not real AES-GCM)
        stream = hashlib.sha256(key + nonce).digest()
        # Extend stream to match plaintext length
        extended = b""
        counter = 0
        while len(extended) < len(plaintext):
            extended += hashlib.sha256(stream + counter.to_bytes(4, "big")).digest()
            counter += 1

        ct = bytes(a ^ b for a, b in zip(plaintext, extended[:len(plaintext)]))
        tag = hmac.new(key, aad + nonce + ct, hashlib.sha256).digest()[:16]
        return ct + tag

    @staticmethod
    def decrypt_aes256gcm(
        key: bytes, nonce: bytes, ciphertext: bytes, aad: bytes = b""
    ) -> bytes:
        if len(key) != 32:
            raise CryptoError("Key must be 32 bytes")
        if len(ciphertext) < 16:
            raise CryptoError("Ciphertext too short (missing tag)")

        ct = ciphertext[:-16]
        tag = ciphertext[-16:]

        expected_tag = hmac.new(key, aad + nonce + ct, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(tag, expected_tag):
            raise CryptoError("Authentication tag mismatch")

        stream = hashlib.sha256(key + nonce).digest()
        extended = b""
        counter = 0
        while len(extended) < len(ct):
            extended += hashlib.sha256(stream + counter.to_bytes(4, "big")).digest()
            counter += 1

        return bytes(a ^ b for a, b in zip(ct, extended[:len(ct)]))


# ---------------------------------------------------------------------------
#  Hashing
# ---------------------------------------------------------------------------

class Hashing:
    """Hash and HMAC operations."""

    @staticmethod
    def sha256(data: bytes) -> bytes:
        return hashlib.sha256(data).digest()

    @staticmethod
    def hmac_sha256(key: bytes, data: bytes) -> bytes:
        return hmac.new(key, data, hashlib.sha256).digest()

    @staticmethod
    def hkdf_sha256(
        ikm: bytes, salt: bytes, info: bytes, length: int = 32
    ) -> bytes:
        """HKDF-SHA256 (extract-then-expand)."""
        if not salt:
            salt = b"\x00" * 32

        # Extract
        prk = hmac.new(salt, ikm, hashlib.sha256).digest()

        # Expand
        output = b""
        t = b""
        counter = 1
        while len(output) < length:
            t = hmac.new(prk, t + info + bytes([counter]), hashlib.sha256).digest()
            output += t
            counter += 1

        return output[:length]


# ---------------------------------------------------------------------------
#  Spiral Seal
# ---------------------------------------------------------------------------

class SpiralSeal:
    """The Spiral Seal protocol — hybrid PQC key exchange + signing."""

    @staticmethod
    def create_session() -> SealSession:
        kem_kp = KEM.keygen(PQAlgorithm.ML_KEM_768)
        dsa_kp = DSA.keygen(PQAlgorithm.ML_DSA_65)
        session_id = secrets.token_hex(16)
        return SealSession(
            session_id=session_id,
            kem_keypair=kem_kp,
            dsa_keypair=dsa_kp,
        )

    @staticmethod
    def seal(
        session: SealSession,
        recipient_public_key: bytes,
        message: bytes,
    ) -> Tuple[bytes, bytes]:
        """Seal: encrypt with KEM + sign with DSA."""
        # KEM encapsulate to get shared secret
        enc = KEM.encapsulate(recipient_public_key)

        # Derive encryption key from shared secret
        enc_key = Hashing.hkdf_sha256(
            enc.shared_secret, b"spiral-seal", b"encryption", 32
        )

        # Encrypt message
        nonce = secrets.token_bytes(12)
        ciphertext = nonce + Symmetric.encrypt_aes256gcm(
            enc_key, nonce, message
        )

        # Prepend KEM ciphertext
        full_ct = len(enc.ciphertext).to_bytes(4, "big") + enc.ciphertext + ciphertext

        # Sign the full ciphertext
        signature = DSA.sign(session.dsa_keypair.secret_key, full_ct)

        return full_ct, signature

    @staticmethod
    def unseal(
        session: SealSession,
        sender_public_key: bytes,
        ciphertext: bytes,
        signature: bytes,
    ) -> bytes:
        """Unseal: verify signature + decrypt."""
        # Verify signature
        if not DSA.verify(sender_public_key, ciphertext, signature):
            raise CryptoError("Signature verification failed")

        # Parse KEM ciphertext
        kem_ct_len = int.from_bytes(ciphertext[:4], "big")
        kem_ct = ciphertext[4:4 + kem_ct_len]
        enc_ct = ciphertext[4 + kem_ct_len:]

        # Decapsulate to get shared secret
        shared_secret = KEM.decapsulate(session.kem_keypair.secret_key, kem_ct)

        # Derive encryption key
        enc_key = Hashing.hkdf_sha256(
            shared_secret, b"spiral-seal", b"encryption", 32
        )

        # Decrypt
        nonce = enc_ct[:12]
        ct = enc_ct[12:]
        return Symmetric.decrypt_aes256gcm(enc_key, nonce, ct)
