"""
PQC Core Module - Post-Quantum Cryptography Wrapper

Provides quantum-resistant cryptographic primitives using liboqs:
- Kyber768: Key Encapsulation Mechanism (KEM) for secure key exchange
- Dilithium3: Digital signatures for audit chain integrity

Graceful fallback to hashlib-based mock if liboqs is not installed.
"""

import hashlib
import os
import secrets
from dataclasses import dataclass
from typing import Tuple, Optional, Union
from enum import Enum

# Constants
KYBER768_PUBLIC_KEY_SIZE = 1184
KYBER768_SECRET_KEY_SIZE = 2400
KYBER768_CIPHERTEXT_SIZE = 1088
KYBER768_SHARED_SECRET_SIZE = 32

DILITHIUM3_PUBLIC_KEY_SIZE = 1952
DILITHIUM3_SECRET_KEY_SIZE = 4016
DILITHIUM3_SIGNATURE_SIZE = 3293

# Try to import PQC libraries in order of preference:
# 1. kyber-py / dilithium-py (pure Python FIPS 203/204 implementations)
# 2. liboqs (native library with Python bindings)
# 3. Mock implementation (hashlib-based fallback)

_PQC_BACKEND = "mock"
_kyber_py = None
_dilithium_py = None
_oqs = None

# Try kyber-py and dilithium-py first (pure Python, FIPS 203/204 compliant)
try:
    from kyber_py.ml_kem import ML_KEM_768 as _ML_KEM_768
    from dilithium_py.ml_dsa import ML_DSA_65 as _ML_DSA_65
    _kyber_py = _ML_KEM_768
    _dilithium_py = _ML_DSA_65
    _PQC_BACKEND = "fips"
except ImportError:
    pass

# Try liboqs as secondary option
if _PQC_BACKEND == "mock":
    try:
        import oqs
        _oqs = oqs
        _PQC_BACKEND = "liboqs"
    except ImportError:
        pass


class PQCBackend(Enum):
    """Available PQC backends."""

    FIPS = "fips"  # kyber-py / dilithium-py (FIPS 203/204)
    LIBOQS = "liboqs"
    MOCK = "mock"


def get_backend() -> PQCBackend:
    """Return the currently active PQC backend."""
    if _PQC_BACKEND == "fips":
        return PQCBackend.FIPS
    elif _PQC_BACKEND == "liboqs":
        return PQCBackend.LIBOQS
    return PQCBackend.MOCK


def is_liboqs_available() -> bool:
    """Check if liboqs is available."""
    return _PQC_BACKEND == "liboqs"


def is_fips_available() -> bool:
    """Check if FIPS 203/204 implementations are available."""
    return _PQC_BACKEND == "fips"


@dataclass
class KyberKeyPair:
    """Kyber768 key pair for key encapsulation."""

    public_key: bytes
    secret_key: bytes

    def __post_init__(self):
        if not isinstance(self.public_key, bytes):
            raise TypeError("public_key must be bytes")
        if not isinstance(self.secret_key, bytes):
            raise TypeError("secret_key must be bytes")


@dataclass
class DilithiumKeyPair:
    """Dilithium3 key pair for digital signatures."""

    public_key: bytes
    secret_key: bytes

    def __post_init__(self):
        if not isinstance(self.public_key, bytes):
            raise TypeError("public_key must be bytes")
        if not isinstance(self.secret_key, bytes):
            raise TypeError("secret_key must be bytes")


@dataclass
class EncapsulationResult:
    """Result of key encapsulation."""

    ciphertext: bytes
    shared_secret: bytes


@dataclass
class SignatureResult:
    """Result of signing operation."""

    signature: bytes
    message: bytes


# =============================================================================
# Mock Implementation (Fallback when liboqs not available)
# =============================================================================


class _MockKyber:
    """Mock Kyber768 implementation using hashlib for testing/fallback.

    Key structure:
    - secret_key = seed (32 bytes) + derived_sk_data (remaining bytes)
    - public_key = derived from seed using deterministic derivation

    This allows decapsulation to recover the public key from the secret key.
    """

    @staticmethod
    def generate_keypair() -> KyberKeyPair:
        """Generate a mock Kyber768 keypair."""
        seed = secrets.token_bytes(32)
        # Public key derived deterministically from seed
        public_key = hashlib.shake_256(b"kyber_pk:" + seed).digest(
            KYBER768_PUBLIC_KEY_SIZE
        )
        # Secret key embeds the seed at the beginning for key recovery
        sk_data = hashlib.shake_256(b"kyber_sk:" + seed).digest(
            KYBER768_SECRET_KEY_SIZE - 32
        )
        secret_key = seed + sk_data
        return KyberKeyPair(public_key=public_key, secret_key=secret_key)

    @staticmethod
    def encapsulate(public_key: bytes) -> EncapsulationResult:
        """Mock encapsulation - derive shared secret from public key."""
        if len(public_key) != KYBER768_PUBLIC_KEY_SIZE:
            raise ValueError(f"Invalid public key size: {len(public_key)}")

        # Generate random data for encapsulation
        random_data = secrets.token_bytes(32)

        # Derive ciphertext (embed random data at start for decapsulation)
        ct_data = hashlib.shake_256(b"kyber_ct:" + public_key + random_data).digest(
            KYBER768_CIPHERTEXT_SIZE - 32
        )
        ciphertext = random_data + ct_data

        # Derive shared secret from public key and random data
        shared_secret = hashlib.sha3_256(
            b"kyber_ss:" + public_key + random_data
        ).digest()

        return EncapsulationResult(ciphertext=ciphertext, shared_secret=shared_secret)

    @staticmethod
    def decapsulate(secret_key: bytes, ciphertext: bytes) -> bytes:
        """Mock decapsulation - derive shared secret from secret key and ciphertext."""
        if len(secret_key) != KYBER768_SECRET_KEY_SIZE:
            raise ValueError(f"Invalid secret key size: {len(secret_key)}")
        if len(ciphertext) != KYBER768_CIPHERTEXT_SIZE:
            raise ValueError(f"Invalid ciphertext size: {len(ciphertext)}")

        # Extract seed from secret key (first 32 bytes)
        seed = secret_key[:32]

        # Recover public key from seed
        public_key = hashlib.shake_256(b"kyber_pk:" + seed).digest(
            KYBER768_PUBLIC_KEY_SIZE
        )

        # Extract random data from ciphertext (first 32 bytes)
        random_data = ciphertext[:32]

        # Compute same shared secret as encapsulation
        shared_secret = hashlib.sha3_256(
            b"kyber_ss:" + public_key + random_data
        ).digest()

        return shared_secret


class _MockDilithium:
    """Mock Dilithium3 implementation using hashlib for testing/fallback.

    Key structure:
    - secret_key = seed (32 bytes) + derived_sk_data (remaining bytes)
    - public_key = seed (32 bytes) + derived_pk_data (remaining bytes)

    Both keys embed the seed at the beginning, allowing verification to
    check the relationship between public key and signature.
    """

    @staticmethod
    def generate_keypair() -> DilithiumKeyPair:
        """Generate a mock Dilithium3 keypair."""
        seed = secrets.token_bytes(32)
        # Both keys embed the seed at the beginning for verification
        sk_data = hashlib.shake_256(b"dilithium_sk:" + seed).digest(
            DILITHIUM3_SECRET_KEY_SIZE - 32
        )
        secret_key = seed + sk_data

        pk_data = hashlib.shake_256(b"dilithium_pk:" + seed).digest(
            DILITHIUM3_PUBLIC_KEY_SIZE - 32
        )
        public_key = seed + pk_data

        return DilithiumKeyPair(public_key=public_key, secret_key=secret_key)

    @staticmethod
    def sign(secret_key: bytes, message: bytes) -> bytes:
        """Mock signing - create deterministic signature."""
        if len(secret_key) != DILITHIUM3_SECRET_KEY_SIZE:
            raise ValueError(f"Invalid secret key size: {len(secret_key)}")

        # Extract seed from secret key
        seed = secret_key[:32]

        # Create deterministic signature from seed and message
        signature = hashlib.shake_256(b"dilithium_sig:" + seed + message).digest(
            DILITHIUM3_SIGNATURE_SIZE
        )

        return signature

    @staticmethod
    def verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
        """Mock verification - check signature validity."""
        if len(public_key) != DILITHIUM3_PUBLIC_KEY_SIZE:
            raise ValueError(f"Invalid public key size: {len(public_key)}")
        if len(signature) != DILITHIUM3_SIGNATURE_SIZE:
            return False

        # Extract seed from public key (embedded at beginning)
        seed = public_key[:32]

        # Compute expected signature using same derivation as sign()
        expected_sig = hashlib.shake_256(b"dilithium_sig:" + seed + message).digest(
            DILITHIUM3_SIGNATURE_SIZE
        )

        return secrets.compare_digest(signature, expected_sig)


# =============================================================================
# Liboqs Implementation
# =============================================================================


class _LiboqsKyber:
    """Kyber768 implementation using liboqs."""

    @staticmethod
    def generate_keypair() -> KyberKeyPair:
        """Generate a Kyber768 keypair using liboqs."""
        with _oqs.KeyEncapsulation("Kyber768") as kem:
            public_key = kem.generate_keypair()
            secret_key = kem.export_secret_key()
            return KyberKeyPair(public_key=public_key, secret_key=secret_key)

    @staticmethod
    def encapsulate(public_key: bytes) -> EncapsulationResult:
        """Encapsulate using Kyber768 public key."""
        with _oqs.KeyEncapsulation("Kyber768") as kem:
            ciphertext, shared_secret = kem.encap_secret(public_key)
            return EncapsulationResult(
                ciphertext=ciphertext, shared_secret=shared_secret
            )

    @staticmethod
    def decapsulate(secret_key: bytes, ciphertext: bytes) -> bytes:
        """Decapsulate using Kyber768 secret key."""
        with _oqs.KeyEncapsulation("Kyber768", secret_key) as kem:
            shared_secret = kem.decap_secret(ciphertext)
            return shared_secret


class _LiboqsDilithium:
    """Dilithium3 implementation using liboqs."""

    @staticmethod
    def generate_keypair() -> DilithiumKeyPair:
        """Generate a Dilithium3 keypair using liboqs."""
        with _oqs.Signature("Dilithium3") as sig:
            public_key = sig.generate_keypair()
            secret_key = sig.export_secret_key()
            return DilithiumKeyPair(public_key=public_key, secret_key=secret_key)

    @staticmethod
    def sign(secret_key: bytes, message: bytes) -> bytes:
        """Sign message using Dilithium3 secret key."""
        with _oqs.Signature("Dilithium3", secret_key) as sig:
            signature = sig.sign(message)
            return signature

    @staticmethod
    def verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
        """Verify signature using Dilithium3 public key."""
        with _oqs.Signature("Dilithium3") as sig:
            return sig.verify(message, signature, public_key)


# =============================================================================
# FIPS 203/204 Implementation (using kyber-py and dilithium-py)
# =============================================================================


class _FipsKyber:
    """ML-KEM-768 (Kyber) implementation using kyber-py (FIPS 203)."""

    @staticmethod
    def generate_keypair() -> KyberKeyPair:
        """Generate an ML-KEM-768 keypair using kyber-py."""
        ek, dk = _kyber_py.keygen()
        return KyberKeyPair(public_key=bytes(ek), secret_key=bytes(dk))

    @staticmethod
    def encapsulate(public_key: bytes) -> EncapsulationResult:
        """Encapsulate using ML-KEM-768 public key."""
        shared_secret, ciphertext = _kyber_py.encaps(public_key)
        return EncapsulationResult(
            ciphertext=bytes(ciphertext), shared_secret=bytes(shared_secret)
        )

    @staticmethod
    def decapsulate(secret_key: bytes, ciphertext: bytes) -> bytes:
        """Decapsulate using ML-KEM-768 secret key."""
        shared_secret = _kyber_py.decaps(secret_key, ciphertext)
        return bytes(shared_secret)


class _FipsDilithium:
    """ML-DSA-65 (Dilithium) implementation using dilithium-py (FIPS 204)."""

    @staticmethod
    def generate_keypair() -> DilithiumKeyPair:
        """Generate an ML-DSA-65 keypair using dilithium-py."""
        pk, sk = _dilithium_py.keygen()
        return DilithiumKeyPair(public_key=bytes(pk), secret_key=bytes(sk))

    @staticmethod
    def sign(secret_key: bytes, message: bytes) -> bytes:
        """Sign message using ML-DSA-65 secret key."""
        signature = _dilithium_py.sign(secret_key, message)
        return bytes(signature)

    @staticmethod
    def verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
        """Verify signature using ML-DSA-65 public key."""
        return _dilithium_py.verify(public_key, message, signature)


# =============================================================================
# Public API - Unified Interface
# =============================================================================


class Kyber768:
    """
    Kyber768 / ML-KEM-768 Key Encapsulation Mechanism (KEM).

    Provides quantum-resistant key exchange following NIST FIPS 203.

    Backend selection (in order of preference):
    1. kyber-py (FIPS 203 compliant pure Python)
    2. liboqs (native library)
    3. Mock implementation (for testing)

    Usage:
        # Generate keypair
        keypair = Kyber768.generate_keypair()

        # Encapsulate (sender side)
        result = Kyber768.encapsulate(keypair.public_key)
        ciphertext = result.ciphertext
        shared_secret_sender = result.shared_secret

        # Decapsulate (receiver side)
        shared_secret_receiver = Kyber768.decapsulate(keypair.secret_key, ciphertext)

        # Both parties now have the same shared_secret
        assert shared_secret_sender == shared_secret_receiver
    """

    # Select implementation based on available backend
    if _PQC_BACKEND == "fips":
        _impl = _FipsKyber
    elif _PQC_BACKEND == "liboqs":
        _impl = _LiboqsKyber
    else:
        _impl = _MockKyber

    @classmethod
    def generate_keypair(cls) -> KyberKeyPair:
        """Generate a new Kyber768 keypair."""
        return cls._impl.generate_keypair()

    @classmethod
    def encapsulate(cls, public_key: bytes) -> EncapsulationResult:
        """
        Encapsulate a shared secret using the recipient's public key.

        Args:
            public_key: Recipient's Kyber768 public key

        Returns:
            EncapsulationResult containing ciphertext and shared secret
        """
        return cls._impl.encapsulate(public_key)

    @classmethod
    def decapsulate(cls, secret_key: bytes, ciphertext: bytes) -> bytes:
        """
        Decapsulate a shared secret using the secret key.

        Args:
            secret_key: Kyber768 secret key
            ciphertext: Ciphertext from encapsulation

        Returns:
            Shared secret (32 bytes)
        """
        return cls._impl.decapsulate(secret_key, ciphertext)

    @classmethod
    def key_exchange(
        cls, sender_keypair: KyberKeyPair, recipient_public_key: bytes
    ) -> Tuple[bytes, bytes, bytes]:
        """
        Perform full key exchange returning shared secret and ciphertext.

        Args:
            sender_keypair: Sender's keypair (for future use with hybrid schemes)
            recipient_public_key: Recipient's public key

        Returns:
            Tuple of (shared_secret, ciphertext, sender_public_key)
        """
        result = cls.encapsulate(recipient_public_key)
        return result.shared_secret, result.ciphertext, sender_keypair.public_key


class Dilithium3:
    """
    Dilithium3 / ML-DSA-65 Digital Signature Algorithm.

    Provides quantum-resistant digital signatures following NIST FIPS 204.

    Backend selection (in order of preference):
    1. dilithium-py (FIPS 204 compliant pure Python)
    2. liboqs (native library)
    3. Mock implementation (for testing)

    Usage:
        # Generate keypair
        keypair = Dilithium3.generate_keypair()

        # Sign a message
        message = b"Hello, quantum world!"
        signature = Dilithium3.sign(keypair.secret_key, message)

        # Verify the signature
        is_valid = Dilithium3.verify(keypair.public_key, message, signature)
        assert is_valid
    """

    # Select implementation based on available backend
    if _PQC_BACKEND == "fips":
        _impl = _FipsDilithium
    elif _PQC_BACKEND == "liboqs":
        _impl = _LiboqsDilithium
    else:
        _impl = _MockDilithium

    @classmethod
    def generate_keypair(cls) -> DilithiumKeyPair:
        """Generate a new Dilithium3 keypair."""
        return cls._impl.generate_keypair()

    @classmethod
    def sign(cls, secret_key: bytes, message: bytes) -> bytes:
        """
        Sign a message using Dilithium3.

        Args:
            secret_key: Dilithium3 secret key
            message: Message to sign

        Returns:
            Signature bytes
        """
        return cls._impl.sign(secret_key, message)

    @classmethod
    def verify(cls, public_key: bytes, message: bytes, signature: bytes) -> bool:
        """
        Verify a Dilithium3 signature.

        Args:
            public_key: Dilithium3 public key
            message: Original message
            signature: Signature to verify

        Returns:
            True if signature is valid, False otherwise
        """
        try:
            return cls._impl.verify(public_key, message, signature)
        except Exception:
            return False

    @classmethod
    def sign_with_result(cls, secret_key: bytes, message: bytes) -> SignatureResult:
        """
        Sign a message and return structured result.

        Args:
            secret_key: Dilithium3 secret key
            message: Message to sign

        Returns:
            SignatureResult with signature and message
        """
        signature = cls.sign(secret_key, message)
        return SignatureResult(signature=signature, message=message)


# =============================================================================
# Hybrid Schemes
# =============================================================================


def derive_hybrid_key(
    pqc_shared_secret: bytes,
    classical_shared_secret: Optional[bytes] = None,
    salt: Optional[bytes] = None,
    info: bytes = b"scbe-aethermoore-pqc-hybrid",
) -> bytes:
    """
    Derive a hybrid key combining PQC and optional classical shared secrets.

    Uses HKDF-like construction for key derivation.

    Args:
        pqc_shared_secret: Shared secret from Kyber768
        classical_shared_secret: Optional classical DH shared secret
        salt: Optional salt for derivation
        info: Context info for derivation

    Returns:
        32-byte derived key
    """
    if salt is None:
        salt = b"\x00" * 32

    # Combine secrets
    if classical_shared_secret:
        combined = pqc_shared_secret + classical_shared_secret
    else:
        combined = pqc_shared_secret

    # HKDF-Extract
    prk = hashlib.sha3_256(salt + combined).digest()

    # HKDF-Expand
    okm = hashlib.sha3_256(prk + info + b"\x01").digest()

    return okm


def generate_pqc_session_keys(
    initiator_kem_keypair: KyberKeyPair,
    responder_kem_public_key: bytes,
    initiator_sig_keypair: DilithiumKeyPair,
    session_id: Optional[bytes] = None,
) -> dict:
    """
    Generate authenticated session keys using PQC primitives.

    Performs key encapsulation and signs the exchange for authentication.

    Args:
        initiator_kem_keypair: Initiator's Kyber keypair
        responder_kem_public_key: Responder's Kyber public key
        initiator_sig_keypair: Initiator's Dilithium keypair for signing
        session_id: Optional session identifier

    Returns:
        Dict with session keys, ciphertext, and signature
    """
    if session_id is None:
        session_id = secrets.token_bytes(16)

    # Perform key encapsulation
    encap_result = Kyber768.encapsulate(responder_kem_public_key)

    # Sign the exchange (ciphertext + session_id + initiator's public key)
    sign_data = encap_result.ciphertext + session_id + initiator_kem_keypair.public_key
    signature = Dilithium3.sign(initiator_sig_keypair.secret_key, sign_data)

    # Derive session keys
    encryption_key = derive_hybrid_key(
        encap_result.shared_secret, salt=session_id, info=b"encryption"
    )
    mac_key = derive_hybrid_key(
        encap_result.shared_secret, salt=session_id, info=b"mac"
    )

    return {
        "session_id": session_id,
        "encryption_key": encryption_key,
        "mac_key": mac_key,
        "ciphertext": encap_result.ciphertext,
        "signature": signature,
        "initiator_public_key": initiator_kem_keypair.public_key,
        "initiator_sig_public_key": initiator_sig_keypair.public_key,
        "shared_secret": encap_result.shared_secret,
    }


def verify_pqc_session(
    session_data: dict,
    responder_kem_keypair: KyberKeyPair,
    initiator_sig_public_key: bytes,
) -> Optional[dict]:
    """
    Verify and complete PQC session key exchange on responder side.

    Args:
        session_data: Session data from initiator
        responder_kem_keypair: Responder's Kyber keypair
        initiator_sig_public_key: Initiator's Dilithium public key

    Returns:
        Dict with derived keys if verification succeeds, None otherwise
    """
    # Verify signature
    sign_data = (
        session_data["ciphertext"]
        + session_data["session_id"]
        + session_data["initiator_public_key"]
    )

    if not Dilithium3.verify(
        initiator_sig_public_key, sign_data, session_data["signature"]
    ):
        return None

    # Decapsulate shared secret
    shared_secret = Kyber768.decapsulate(
        responder_kem_keypair.secret_key, session_data["ciphertext"]
    )

    # Derive same session keys
    encryption_key = derive_hybrid_key(
        shared_secret, salt=session_data["session_id"], info=b"encryption"
    )
    mac_key = derive_hybrid_key(
        shared_secret, salt=session_data["session_id"], info=b"mac"
    )

    return {
        "session_id": session_data["session_id"],
        "encryption_key": encryption_key,
        "mac_key": mac_key,
        "shared_secret": shared_secret,
    }
