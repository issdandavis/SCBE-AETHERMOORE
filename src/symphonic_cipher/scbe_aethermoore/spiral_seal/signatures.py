"""
ML-DSA-65 / legacy Dilithium3 signature wrapper.

Missing native support fails closed. Explicit isolated test settings may enable
real Ed25519 development signatures, which are labelled and NOT post-quantum.
Algorithm availability is not FIPS module validation.
"""

import os
from typing import Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

_SIG_ALG = "Dilithium3"
_DEV_PREFIX = b"DEV_ED25519:v1:"


def _development_enabled() -> bool:
    return os.getenv("SCBE_ALLOW_MOCK_PQC") == "1" and os.getenv("SCBE_ENV", "").lower() in {"test", "development"}


def _require_development() -> None:
    if not _development_enabled():
        raise RuntimeError("Native PQ signature backend unavailable; development signatures are disabled")


# Try to import post-quantum library
_FORCE_SKIP_LIBOQS = os.getenv("SCBE_FORCE_SKIP_LIBOQS", "").strip().lower() in {
    "1",
    "true",
    "yes",
}

if not _FORCE_SKIP_LIBOQS:
    try:
        from oqs import Signature
        import oqs as _oqs_mod

        PQC_SIG_AVAILABLE = True
        PQC_SIG_BACKEND = "liboqs"
        # Select algorithm: prefer ML-DSA-65 (FIPS 204), fall back to Dilithium3
        _enabled = _oqs_mod.get_enabled_sig_mechanisms()
        _SIG_ALG = "ML-DSA-65" if "ML-DSA-65" in _enabled else "Dilithium3"
    except BaseException:
        # liboqs-python not installed, shared libs missing, or bootstrap errors
        try:
            import pqcrypto.sign.dilithium3 as dilithium

            PQC_SIG_AVAILABLE = True
            PQC_SIG_BACKEND = "pqcrypto"
        except BaseException:
            PQC_SIG_AVAILABLE = False
            PQC_SIG_BACKEND = "fallback"
else:
    PQC_SIG_AVAILABLE = False
    PQC_SIG_BACKEND = "fallback"


class DilithiumKeyPair:
    """Container for Dilithium3 key pair."""

    def __init__(self, public_key: bytes, secret_key: bytes):
        self.public_key = public_key
        self.secret_key = secret_key

    def __repr__(self):
        return f"DilithiumKeyPair(pk={len(self.public_key)}B, sk={len(self.secret_key)}B)"


def dilithium_keygen() -> Tuple[bytes, bytes]:
    """
    Generate a Dilithium3 key pair.

    Returns:
        Tuple of (secret_key, public_key)
    """
    if PQC_SIG_BACKEND == "liboqs":
        sig = Signature(_SIG_ALG)
        public_key = sig.generate_keypair()
        secret_key = sig.export_secret_key()
        return secret_key, public_key

    elif PQC_SIG_BACKEND == "pqcrypto":
        public_key, secret_key = dilithium.generate_keypair()
        return secret_key, public_key

    else:
        _require_development()
        key = Ed25519PrivateKey.generate()
        return (
            key.private_bytes(
                serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
            ),
            key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw),
        )


def dilithium_sign(secret_key: bytes, message: bytes) -> bytes:
    """
    Sign a message using Dilithium3.

    Args:
        secret_key: Signer's secret key
        message: Message to sign

    Returns:
        Digital signature
    """
    if PQC_SIG_BACKEND == "liboqs":
        sig = Signature(_SIG_ALG, secret_key)
        signature = sig.sign(message)
        return signature

    elif PQC_SIG_BACKEND == "pqcrypto":
        signature = dilithium.sign(secret_key, message)
        return signature

    else:
        _require_development()
        return _DEV_PREFIX + Ed25519PrivateKey.from_private_bytes(secret_key).sign(message)


def dilithium_verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    """
    Verify a Dilithium3 signature.

    Args:
        public_key: Signer's public key
        message: Original message
        signature: Signature to verify

    Returns:
        True if signature is valid, False otherwise
    """
    if PQC_SIG_BACKEND == "liboqs":
        sig = Signature(_SIG_ALG)
        try:
            return sig.verify(message, signature, public_key)
        except Exception:
            return False

    elif PQC_SIG_BACKEND == "pqcrypto":
        try:
            return dilithium.verify(public_key, message, signature) is True
        except Exception:
            return False

    else:
        if not _development_enabled() or not isinstance(signature, bytes) or not signature.startswith(_DEV_PREFIX):
            return False
        try:
            Ed25519PublicKey.from_public_bytes(public_key).verify(signature[len(_DEV_PREFIX) :], message)
            return True
        except (InvalidSignature, ValueError, TypeError):
            return False


def get_pqc_sig_status() -> dict:
    """
    Get the status of post-quantum signature support.

    Returns:
        Dict with backend info and security warnings
    """
    return {
        "available": PQC_SIG_AVAILABLE,
        "backend": PQC_SIG_BACKEND,
        "algorithm": _SIG_ALG if PQC_SIG_AVAILABLE else "Ed25519-development",
        "development_enabled": not PQC_SIG_AVAILABLE and _development_enabled(),
        "security_level": (
            "Algorithm category 3; module validation not established" if PQC_SIG_AVAILABLE else "NOT PQ-SECURE"
        ),
        "warning": (
            None
            if PQC_SIG_AVAILABLE
            else "Native PQ signatures unavailable; classical development mode requires explicit opt-in."
        ),
    }
