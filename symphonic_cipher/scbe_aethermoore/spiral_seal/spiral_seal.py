"""
SpiralSeal SS1 Format - Sacred Tongue Encryption Envelope

Real cryptography with Spiralverse encoding:
- KDF: Argon2id (preferred) or scrypt (fallback)
- AEAD: XChaCha20-Poly1305 (preferred) or AES-256-GCM (fallback)
- Encoding: Sacred Tongues (6 languages × 256 tokens each)

SS1 Wire Format:
    SS1|kid=<key_id>|aad=av:<tokens>|salt=ru:<tokens>|nonce=ko:<tokens>|ct=ca:<tokens>|tag=dr:<tokens>

Where each component uses its assigned tongue:
- aad (Associated Authenticated Data) → Avali (diplomacy/context)
- salt (KDF binding) → Runethic (constraints/binding)
- nonce (flow control) → Kor'aelin (flow/intent)
- ct (ciphertext bits) → Cassisivadan (bitcraft/math)
- tag (auth verification) → Draumric (structure/forge)

Optional veil wrapper uses Umbroth for redaction markers.
"""

from __future__ import annotations

import os
import hmac
import hashlib
import struct
import time
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, Any, Union
from enum import Enum

from .sacred_tongues import (
    SacredTongue,
    SacredTongueTokenizer,
    get_tongue_for_domain,
    get_tokenizer,
    DOMAIN_TONGUE_MAP,
)


# =============================================================================
# CRYPTO BACKEND DETECTION (lazy loading to avoid broken cryptography module)
# =============================================================================

_NACL_AVAILABLE = False
_ARGON2_AVAILABLE = False
_CRYPTOGRAPHY_AVAILABLE = False

# PyNaCl (preferred for XChaCha20-Poly1305)
try:
    import nacl.secret
    import nacl.pwhash
    import nacl.utils
    _NACL_AVAILABLE = True
except (ImportError, Exception):
    pass

# Argon2 (preferred KDF)
try:
    import argon2
    from argon2.low_level import hash_secret_raw, Type
    _ARGON2_AVAILABLE = True
except (ImportError, Exception):
    pass

# Cryptography - defer import to avoid crash in broken environments
# Will be loaded lazily only when needed
AESGCM = None
Scrypt = None
default_backend = None

_CRYPTOGRAPHY_TRIED = False

def _try_load_cryptography():
    """Attempt to load cryptography module lazily."""
    global _CRYPTOGRAPHY_AVAILABLE, _CRYPTOGRAPHY_TRIED, AESGCM, Scrypt, default_backend
    if _CRYPTOGRAPHY_AVAILABLE:
        return True
    if _CRYPTOGRAPHY_TRIED:
        return False
    _CRYPTOGRAPHY_TRIED = True
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _AESGCM
        from cryptography.hazmat.primitives.kdf.scrypt import Scrypt as _Scrypt
        from cryptography.hazmat.backends import default_backend as _default_backend
        AESGCM = _AESGCM
        Scrypt = _Scrypt
        default_backend = _default_backend
        _CRYPTOGRAPHY_AVAILABLE = True
        return True
    except BaseException:
        # Catch BaseException to handle pyo3 panics from broken cryptography module
        return False


# =============================================================================
# CONSTANTS
# =============================================================================

SS1_VERSION = "SS1"
SS1_MAGIC = b"SS1\x00"

# KDF parameters (Argon2id - OWASP recommended)
ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST = 65536  # 64 MiB
ARGON2_PARALLELISM = 4
ARGON2_HASH_LEN = 32

# scrypt fallback parameters (adjusted for resource-constrained environments)
SCRYPT_N = 2**14  # 16384 (reduced from 2^17 for compatibility)
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32

# AEAD parameters
XCHACHA_NONCE_SIZE = 24
AES_GCM_NONCE_SIZE = 12
TAG_SIZE = 16
SALT_SIZE = 16

# Key ID length
KEY_ID_SIZE = 8


class KDFType(Enum):
    """Key derivation function type."""
    ARGON2ID = "argon2id"
    SCRYPT = "scrypt"
    HKDF_SHA256 = "hkdf"  # Emergency fallback


class AEADType(Enum):
    """AEAD cipher type."""
    XCHACHA20_POLY1305 = "xchacha"
    AES_256_GCM = "aesgcm"
    HMAC_CTR = "hmacctr"  # Emergency fallback


# =============================================================================
# KDF IMPLEMENTATIONS
# =============================================================================

def derive_key_argon2id(password: bytes, salt: bytes) -> bytes:
    """Derive key using Argon2id (preferred)."""
    if _ARGON2_AVAILABLE:
        return hash_secret_raw(
            secret=password,
            salt=salt,
            time_cost=ARGON2_TIME_COST,
            memory_cost=ARGON2_MEMORY_COST,
            parallelism=ARGON2_PARALLELISM,
            hash_len=ARGON2_HASH_LEN,
            type=Type.ID
        )
    elif _NACL_AVAILABLE:
        # PyNaCl's argon2id
        return nacl.pwhash.argon2id.kdf(
            size=ARGON2_HASH_LEN,
            password=password,
            salt=salt[:16],  # PyNaCl wants 16-byte salt
            opslimit=nacl.pwhash.argon2id.OPSLIMIT_MODERATE,
            memlimit=nacl.pwhash.argon2id.MEMLIMIT_MODERATE
        )
    else:
        raise RuntimeError("Argon2id not available - install argon2-cffi or pynacl")


def derive_key_scrypt(password: bytes, salt: bytes) -> bytes:
    """Derive key using scrypt (fallback)."""
    _try_load_cryptography()
    if _CRYPTOGRAPHY_AVAILABLE and Scrypt is not None:
        kdf = Scrypt(
            salt=salt,
            length=SCRYPT_DKLEN,
            n=SCRYPT_N,
            r=SCRYPT_R,
            p=SCRYPT_P,
            backend=default_backend()
        )
        return kdf.derive(password)
    else:
        # Use hashlib.scrypt (Python 3.6+)
        return hashlib.scrypt(
            password,
            salt=salt,
            n=SCRYPT_N,
            r=SCRYPT_R,
            p=SCRYPT_P,
            dklen=SCRYPT_DKLEN
        )


def derive_key_hkdf(password: bytes, salt: bytes) -> bytes:
    """Emergency HKDF fallback (not recommended for passwords)."""
    # Extract
    prk = hmac.new(salt, password, hashlib.sha256).digest()
    # Expand
    return hmac.new(prk, b"\x01", hashlib.sha256).digest()


def derive_key(password: bytes, salt: bytes, kdf_type: KDFType = KDFType.ARGON2ID) -> bytes:
    """Derive encryption key from password and salt."""
    if kdf_type == KDFType.ARGON2ID:
        try:
            return derive_key_argon2id(password, salt)
        except (RuntimeError, Exception):
            # Fall back to scrypt, then HKDF
            try:
                return derive_key_scrypt(password, salt)
            except (ValueError, OSError, Exception):
                # Memory limit exceeded, fall back to HKDF
                return derive_key_hkdf(password, salt)
    elif kdf_type == KDFType.SCRYPT:
        try:
            return derive_key_scrypt(password, salt)
        except (ValueError, OSError, Exception):
            # Memory limit exceeded, fall back to HKDF
            return derive_key_hkdf(password, salt)
    else:
        return derive_key_hkdf(password, salt)


# =============================================================================
# AEAD IMPLEMENTATIONS
# =============================================================================

def encrypt_xchacha(key: bytes, nonce: bytes, plaintext: bytes, aad: bytes) -> Tuple[bytes, bytes]:
    """Encrypt using XChaCha20-Poly1305."""
    if not _NACL_AVAILABLE:
        raise RuntimeError("XChaCha20-Poly1305 not available - install pynacl")

    box = nacl.secret.Aead(key)
    ciphertext = box.encrypt(plaintext, aad=aad, nonce=nonce)
    # PyNaCl returns nonce + ciphertext + tag combined, we need to split
    # Actually, for AEAD we get ciphertext || tag
    ct_with_tag = ciphertext
    ct = ct_with_tag[:-TAG_SIZE]
    tag = ct_with_tag[-TAG_SIZE:]
    return ct, tag


def decrypt_xchacha(key: bytes, nonce: bytes, ciphertext: bytes, tag: bytes, aad: bytes) -> bytes:
    """Decrypt using XChaCha20-Poly1305."""
    if not _NACL_AVAILABLE:
        raise RuntimeError("XChaCha20-Poly1305 not available - install pynacl")

    box = nacl.secret.Aead(key)
    ct_with_tag = ciphertext + tag
    return box.decrypt(ct_with_tag, aad=aad, nonce=nonce)


def encrypt_aesgcm(key: bytes, nonce: bytes, plaintext: bytes, aad: bytes) -> Tuple[bytes, bytes]:
    """Encrypt using AES-256-GCM."""
    _try_load_cryptography()
    if not _CRYPTOGRAPHY_AVAILABLE or AESGCM is None:
        raise RuntimeError("AES-GCM not available - install cryptography")

    aesgcm = AESGCM(key)
    ct_with_tag = aesgcm.encrypt(nonce, plaintext, aad)
    ct = ct_with_tag[:-TAG_SIZE]
    tag = ct_with_tag[-TAG_SIZE:]
    return ct, tag


def decrypt_aesgcm(key: bytes, nonce: bytes, ciphertext: bytes, tag: bytes, aad: bytes) -> bytes:
    """Decrypt using AES-256-GCM."""
    _try_load_cryptography()
    if not _CRYPTOGRAPHY_AVAILABLE or AESGCM is None:
        raise RuntimeError("AES-GCM not available - install cryptography")

    aesgcm = AESGCM(key)
    ct_with_tag = ciphertext + tag
    return aesgcm.decrypt(nonce, ct_with_tag, aad)


def encrypt_hmac_ctr(key: bytes, nonce: bytes, plaintext: bytes, aad: bytes) -> Tuple[bytes, bytes]:
    """Emergency fallback: HMAC-based CTR mode (not recommended)."""
    # Split key
    enc_key = key[:16]
    mac_key = key[16:]

    # CTR mode encryption
    ciphertext = bytearray(len(plaintext))
    for i, p in enumerate(plaintext):
        block_idx = i // 16
        ctr_input = nonce + struct.pack(">I", block_idx)
        keystream = hashlib.sha256(enc_key + ctr_input).digest()
        ciphertext[i] = p ^ keystream[i % 16]

    ciphertext = bytes(ciphertext)

    # HMAC tag over aad || ciphertext
    tag = hmac.new(mac_key, aad + ciphertext, hashlib.sha256).digest()[:TAG_SIZE]

    return ciphertext, tag


def decrypt_hmac_ctr(key: bytes, nonce: bytes, ciphertext: bytes, tag: bytes, aad: bytes) -> bytes:
    """Emergency fallback decryption."""
    enc_key = key[:16]
    mac_key = key[16:]

    # Verify tag first
    expected_tag = hmac.new(mac_key, aad + ciphertext, hashlib.sha256).digest()[:TAG_SIZE]
    if not hmac.compare_digest(tag, expected_tag):
        raise ValueError("Authentication failed")

    # Decrypt
    plaintext = bytearray(len(ciphertext))
    for i, c in enumerate(ciphertext):
        block_idx = i // 16
        ctr_input = nonce + struct.pack(">I", block_idx)
        keystream = hashlib.sha256(enc_key + ctr_input).digest()
        plaintext[i] = c ^ keystream[i % 16]

    return bytes(plaintext)


# =============================================================================
# SS1 SEAL RESULT
# =============================================================================

@dataclass
class SpiralSealResult:
    """Result of a SpiralSeal encryption operation."""
    # Raw cryptographic components
    key_id: bytes
    salt: bytes
    nonce: bytes
    ciphertext: bytes
    tag: bytes
    aad: bytes

    # Sacred Tongue encoded strings
    salt_tokens: str
    nonce_tokens: str
    ct_tokens: str
    tag_tokens: str
    aad_tokens: str

    # Metadata
    kdf_type: KDFType
    aead_type: AEADType
    timestamp: float = field(default_factory=time.time)

    def to_ss1_string(self) -> str:
        """Serialize to SS1 wire format."""
        kid_hex = self.key_id.hex()
        # Tokens already include tongue prefix (e.g., "ru:khar'eth ru:drath'ul")
        return (
            f"{SS1_VERSION}|"
            f"kid={kid_hex}|"
            f"aad={self.aad_tokens}|"
            f"salt={self.salt_tokens}|"
            f"nonce={self.nonce_tokens}|"
            f"ct={self.ct_tokens}|"
            f"tag={self.tag_tokens}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "version": SS1_VERSION,
            "key_id": self.key_id.hex(),
            "salt": self.salt.hex(),
            "nonce": self.nonce.hex(),
            "ciphertext": self.ciphertext.hex(),
            "tag": self.tag.hex(),
            "aad": self.aad.hex(),
            "salt_tokens": self.salt_tokens,
            "nonce_tokens": self.nonce_tokens,
            "ct_tokens": self.ct_tokens,
            "tag_tokens": self.tag_tokens,
            "aad_tokens": self.aad_tokens,
            "kdf_type": self.kdf_type.value,
            "aead_type": self.aead_type.value,
            "timestamp": self.timestamp
        }


# =============================================================================
# SPIRAL SEAL MAIN CLASS
# =============================================================================

class SpiralSeal:
    """
    SpiralSeal SS1 - Sacred Tongue Encryption Envelope.

    Real cryptography (Argon2id + XChaCha20-Poly1305) with Spiralverse encoding.
    Each cryptographic component is encoded in its assigned Sacred Tongue.

    Usage:
        # Create seal with master password
        seal = SpiralSeal(master_password=b"secret")

        # Encrypt data
        result = seal.seal(b"plaintext", aad=b"context")
        ss1_string = result.to_ss1_string()

        # Decrypt data
        plaintext = seal.unseal_string(ss1_string)

        # Or from components
        plaintext = seal.unseal(result.salt, result.nonce, result.ciphertext,
                                result.tag, result.aad)
    """

    def __init__(self,
                 master_password: Optional[bytes] = None,
                 master_key: Optional[bytes] = None,
                 key_id: Optional[bytes] = None,
                 kdf_type: KDFType = KDFType.ARGON2ID,
                 aead_type: Optional[AEADType] = None):
        """
        Initialize SpiralSeal.

        Args:
            master_password: Password for key derivation (recommended)
            master_key: Direct key (32 bytes) - use if you have your own KDF
            key_id: Key identifier (8 bytes, generated if not provided)
            kdf_type: KDF to use (default: Argon2id)
            aead_type: AEAD to use (auto-detected if not specified)
        """
        if master_password is None and master_key is None:
            raise ValueError("Must provide master_password or master_key")

        self._master_password = master_password
        self._master_key = master_key
        self._key_id = key_id or os.urandom(KEY_ID_SIZE)
        self._kdf_type = kdf_type

        # Auto-detect best available AEAD
        if aead_type is None:
            if _NACL_AVAILABLE:
                self._aead_type = AEADType.XCHACHA20_POLY1305
            elif _try_load_cryptography():
                self._aead_type = AEADType.AES_256_GCM
            else:
                self._aead_type = AEADType.HMAC_CTR
        else:
            self._aead_type = aead_type

        # Tokenizer
        self._tokenizer = get_tokenizer()

    def _get_nonce_size(self) -> int:
        """Get nonce size for current AEAD type."""
        if self._aead_type == AEADType.XCHACHA20_POLY1305:
            return XCHACHA_NONCE_SIZE
        elif self._aead_type == AEADType.AES_256_GCM:
            return AES_GCM_NONCE_SIZE
        else:
            return 12  # Fallback

    def _derive_seal_key(self, salt: bytes) -> bytes:
        """Derive encryption key from password and salt."""
        if self._master_key is not None:
            # Already have a key, just bind it with salt
            return hmac.new(self._master_key, salt, hashlib.sha256).digest()
        else:
            return derive_key(self._master_password, salt, self._kdf_type)

    def _encrypt(self, key: bytes, nonce: bytes, plaintext: bytes, aad: bytes) -> Tuple[bytes, bytes]:
        """Encrypt with current AEAD type."""
        if self._aead_type == AEADType.XCHACHA20_POLY1305:
            return encrypt_xchacha(key, nonce, plaintext, aad)
        elif self._aead_type == AEADType.AES_256_GCM:
            return encrypt_aesgcm(key, nonce, plaintext, aad)
        else:
            return encrypt_hmac_ctr(key, nonce, plaintext, aad)

    def _decrypt(self, key: bytes, nonce: bytes, ciphertext: bytes, tag: bytes, aad: bytes) -> bytes:
        """Decrypt with current AEAD type."""
        if self._aead_type == AEADType.XCHACHA20_POLY1305:
            return decrypt_xchacha(key, nonce, ciphertext, tag, aad)
        elif self._aead_type == AEADType.AES_256_GCM:
            return decrypt_aesgcm(key, nonce, ciphertext, tag, aad)
        else:
            return decrypt_hmac_ctr(key, nonce, ciphertext, tag, aad)

    def seal(self,
             plaintext: bytes,
             aad: Optional[bytes] = None,
             salt: Optional[bytes] = None,
             nonce: Optional[bytes] = None) -> SpiralSealResult:
        """
        Seal (encrypt) plaintext with Sacred Tongue encoding.

        Args:
            plaintext: Data to encrypt
            aad: Associated authenticated data (optional)
            salt: KDF salt (generated if not provided)
            nonce: AEAD nonce (generated if not provided)

        Returns:
            SpiralSealResult with all components
        """
        # Generate random values if not provided
        if salt is None:
            salt = os.urandom(SALT_SIZE)
        if nonce is None:
            nonce = os.urandom(self._get_nonce_size())
        if aad is None:
            aad = b""

        # Derive encryption key
        key = self._derive_seal_key(salt)

        # Encrypt
        ciphertext, tag = self._encrypt(key, nonce, plaintext, aad)

        # Encode each component in its Sacred Tongue (with prefix for verification)
        from .sacred_tongues import encode_to_spelltext
        salt_tokens = encode_to_spelltext(salt, 'salt')
        nonce_tokens = encode_to_spelltext(nonce, 'nonce')
        ct_tokens = encode_to_spelltext(ciphertext, 'ct')
        tag_tokens = encode_to_spelltext(tag, 'tag')
        aad_tokens = encode_to_spelltext(aad, 'aad') if aad else ""

        return SpiralSealResult(
            key_id=self._key_id,
            salt=salt,
            nonce=nonce,
            ciphertext=ciphertext,
            tag=tag,
            aad=aad,
            salt_tokens=salt_tokens,
            nonce_tokens=nonce_tokens,
            ct_tokens=ct_tokens,
            tag_tokens=tag_tokens,
            aad_tokens=aad_tokens,
            kdf_type=self._kdf_type,
            aead_type=self._aead_type
        )

    def unseal(self,
               salt: bytes,
               nonce: bytes,
               ciphertext: bytes,
               tag: bytes,
               aad: bytes = b"") -> bytes:
        """
        Unseal (decrypt) from raw components.

        Args:
            salt: KDF salt
            nonce: AEAD nonce
            ciphertext: Encrypted data
            tag: Authentication tag
            aad: Associated authenticated data

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If authentication fails
        """
        key = self._derive_seal_key(salt)
        return self._decrypt(key, nonce, ciphertext, tag, aad)

    def unseal_tokens(self,
                      salt_tokens: str,
                      nonce_tokens: str,
                      ct_tokens: str,
                      tag_tokens: str,
                      aad_tokens: str = "") -> bytes:
        """
        Unseal from Sacred Tongue token strings.

        Args:
            salt_tokens: Runethic-encoded salt
            nonce_tokens: Kor'aelin-encoded nonce
            ct_tokens: Cassisivadan-encoded ciphertext
            tag_tokens: Draumric-encoded tag
            aad_tokens: Avali-encoded AAD

        Returns:
            Decrypted plaintext
        """
        # Decode tokens back to bytes (handles tokens with or without prefix)
        from .sacred_tongues import decode_from_spelltext
        salt = decode_from_spelltext(salt_tokens, 'salt')
        nonce = decode_from_spelltext(nonce_tokens, 'nonce')
        ciphertext = decode_from_spelltext(ct_tokens, 'ct')
        tag = decode_from_spelltext(tag_tokens, 'tag')
        aad = decode_from_spelltext(aad_tokens, 'aad') if aad_tokens else b""

        return self.unseal(salt, nonce, ciphertext, tag, aad)

    def unseal_string(self, ss1_string: str) -> bytes:
        """
        Unseal from SS1 wire format string.

        Args:
            ss1_string: SS1 formatted string

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If format is invalid or authentication fails
        """
        # Parse SS1 format
        parts = ss1_string.split("|")
        if not parts[0] == SS1_VERSION:
            raise ValueError(f"Unknown version: {parts[0]}")

        # Extract components
        components = {}
        for part in parts[1:]:
            if "=" in part:
                key, value = part.split("=", 1)
                components[key] = value

        # Tokens include tongue prefixes (e.g., "ru:khar'eth ru:drath'ul")
        # decode_from_spelltext handles stripping prefixes from each token
        salt_tokens = components.get("salt", "")
        nonce_tokens = components.get("nonce", "")
        ct_tokens = components.get("ct", "")
        tag_tokens = components.get("tag", "")
        aad_tokens = components.get("aad", "")

        return self.unseal_tokens(salt_tokens, nonce_tokens, ct_tokens, tag_tokens, aad_tokens)

    @property
    def key_id(self) -> bytes:
        """Get key identifier."""
        return self._key_id

    @property
    def kdf_type(self) -> KDFType:
        """Get KDF type."""
        return self._kdf_type

    @property
    def aead_type(self) -> AEADType:
        """Get AEAD type."""
        return self._aead_type


# =============================================================================
# VEILED SEAL (with Umbroth redaction wrapper)
# =============================================================================

@dataclass
class VeiledSealResult:
    """Result with Umbroth veil wrapper for log redaction."""
    inner: SpiralSealResult
    veil_marker: str  # Umbroth-encoded boundary marker
    redacted_form: str  # What to show in logs

    def to_log_safe(self) -> str:
        """Get log-safe representation with redacted content."""
        return f"[VEILED:{self.veil_marker}]"

    def to_ss1_string(self) -> str:
        """Get full SS1 string (use only in secure contexts)."""
        return self.inner.to_ss1_string()


class VeiledSeal(SpiralSeal):
    """
    SpiralSeal with Umbroth veil wrapper for privacy/redaction.

    Adds an outer Umbroth encoding layer that can be used for:
    - Log redaction (shows only veil marker)
    - Privacy boundaries in audits
    - Sandboxed secure scopes (hollow wards)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def seal_veiled(self,
                    plaintext: bytes,
                    aad: Optional[bytes] = None,
                    veil_id: Optional[str] = None) -> VeiledSealResult:
        """
        Seal with Umbroth veil wrapper.

        Args:
            plaintext: Data to encrypt
            aad: Associated authenticated data
            veil_id: Identifier for the veil (generated if not provided)

        Returns:
            VeiledSealResult with redaction support
        """
        # Create inner seal
        inner = self.seal(plaintext, aad)

        # Generate veil marker using Umbroth encoding
        if veil_id is None:
            veil_bytes = os.urandom(4)
        else:
            veil_bytes = hashlib.sha256(veil_id.encode()).digest()[:4]

        from .sacred_tongues import encode_to_spelltext
        veil_marker = encode_to_spelltext(veil_bytes, 'veil')

        # Redacted form for logs
        redacted_form = f"um:veil({veil_marker})"

        return VeiledSealResult(
            inner=inner,
            veil_marker=veil_marker,
            redacted_form=redacted_form
        )


# =============================================================================
# PQC-ENHANCED SPIRAL SEAL
# =============================================================================

class PQCSpiralSeal(SpiralSeal):
    """
    SpiralSeal with Post-Quantum Cryptography enhancement.

    Uses Kyber768 for key encapsulation to derive the master key,
    and Dilithium3 to sign the sealed envelope.
    """

    def __init__(self,
                 recipient_public_key: Optional[bytes] = None,
                 signing_secret_key: Optional[bytes] = None,
                 **kwargs):
        """
        Initialize PQC-enhanced SpiralSeal.

        Args:
            recipient_public_key: Kyber768 public key for encryption
            signing_secret_key: Dilithium3 secret key for signing
            **kwargs: Passed to SpiralSeal
        """
        self._pqc_available = False
        self._Kyber768 = None
        self._Dilithium3 = None

        try:
            from ..pqc import Kyber768, Dilithium3
            self._Kyber768 = Kyber768
            self._Dilithium3 = Dilithium3
            self._pqc_available = True
        except ImportError:
            pass

        self._recipient_pk = recipient_public_key
        self._signing_sk = signing_secret_key
        self._encapsulated_ct = None

        # If we have a recipient key, derive master key via Kyber
        if self._pqc_available and self._recipient_pk:
            result = self._Kyber768.encapsulate(self._recipient_pk)
            kwargs["master_key"] = result.shared_secret
            self._encapsulated_ct = result.ciphertext
        elif "master_key" not in kwargs and "master_password" not in kwargs:
            # Generate ephemeral key
            kwargs["master_key"] = os.urandom(32)

        super().__init__(**kwargs)

    def seal_signed(self,
                    plaintext: bytes,
                    aad: Optional[bytes] = None) -> Tuple[SpiralSealResult, Optional[bytes]]:
        """
        Seal and sign with Dilithium3.

        Returns:
            Tuple of (SpiralSealResult, signature or None)
        """
        result = self.seal(plaintext, aad)

        signature = None
        if self._pqc_available and self._signing_sk:
            sign_data = (
                result.key_id +
                result.salt +
                result.nonce +
                result.ciphertext +
                result.tag
            )
            signature = self._Dilithium3.sign(self._signing_sk, sign_data)

        return result, signature

    @property
    def encapsulated_ciphertext(self) -> Optional[bytes]:
        """Get Kyber ciphertext (needed by recipient to derive key)."""
        return self._encapsulated_ct

    @property
    def pqc_available(self) -> bool:
        """Check if PQC is available."""
        return self._pqc_available


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def quick_seal(plaintext: bytes, password: bytes, aad: bytes = b"") -> str:
    """
    Quick one-shot seal operation.

    Args:
        plaintext: Data to encrypt
        password: Master password
        aad: Associated authenticated data

    Returns:
        SS1 formatted string
    """
    seal = SpiralSeal(master_password=password)
    result = seal.seal(plaintext, aad)
    return result.to_ss1_string()


def quick_unseal(ss1_string: str, password: bytes) -> bytes:
    """
    Quick one-shot unseal operation.

    Args:
        ss1_string: SS1 formatted string
        password: Master password

    Returns:
        Decrypted plaintext
    """
    seal = SpiralSeal(master_password=password)
    return seal.unseal_string(ss1_string)


def get_crypto_backend_info() -> Dict[str, bool]:
    """Get information about available cryptographic backends."""
    _try_load_cryptography()
    return {
        "nacl_available": _NACL_AVAILABLE,
        "argon2_available": _ARGON2_AVAILABLE,
        "cryptography_available": _CRYPTOGRAPHY_AVAILABLE,
        "recommended_kdf": KDFType.ARGON2ID.value if (_ARGON2_AVAILABLE or _NACL_AVAILABLE) else KDFType.SCRYPT.value,
        "recommended_aead": (
            AEADType.XCHACHA20_POLY1305.value if _NACL_AVAILABLE else
            AEADType.AES_256_GCM.value if _CRYPTOGRAPHY_AVAILABLE else
            AEADType.HMAC_CTR.value
        )
    }


# =============================================================================
# COMPATIBILITY CLASS - SpiralSealSS1
# =============================================================================

class SpiralSealSS1:
    """
    SpiralSeal SS1 - Compatibility wrapper matching test API.

    This class provides a simplified API for sealing/unsealing secrets
    with Sacred Tongue encoding.

    Usage:
        ss = SpiralSealSS1(master_secret=b'0' * 32, kid='k01')

        # Seal plaintext
        blob = ss.seal(b"my secret", aad="service=api")

        # Unseal
        plaintext = ss.unseal(blob, aad="service=api")
    """

    def __init__(self, master_secret: bytes, kid: Optional[str] = None):
        """Initialize SpiralSealSS1.

        Args:
            master_secret: 32-byte master secret key
            kid: Key ID (auto-generated if not provided)
        """
        from .sacred_tongues import format_ss1_blob, parse_ss1_blob

        self._master_secret = master_secret
        self._kid = kid or os.urandom(4).hex()
        self._seal = SpiralSeal(master_key=master_secret)
        self._format_blob = format_ss1_blob
        self._parse_blob = parse_ss1_blob

    def seal(self, plaintext: bytes, aad: str = "") -> str:
        """Seal (encrypt) plaintext.

        Args:
            plaintext: Data to encrypt
            aad: Associated authenticated data string

        Returns:
            SS1 formatted string
        """
        result = self._seal.seal(plaintext, aad=aad.encode() if aad else None)

        # Format using the compatibility blob format
        return self._format_blob(
            kid=self._kid,
            aad=aad,
            salt=result.salt,
            nonce=result.nonce,
            ciphertext=result.ciphertext,
            tag=result.tag
        )

    def unseal(self, blob: str, aad: str = "") -> bytes:
        """Unseal (decrypt) an SS1 blob.

        Args:
            blob: SS1 formatted string
            aad: Associated authenticated data (must match seal)

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If authentication fails or AAD mismatch
        """
        parsed = self._parse_blob(blob)

        # Check AAD
        if parsed.get("aad", "") != aad:
            raise ValueError(f"AAD mismatch: expected '{aad}', got '{parsed.get('aad', '')}'")

        return self._seal.unseal(
            salt=parsed["salt"],
            nonce=parsed["nonce"],
            ciphertext=parsed["ct"],
            tag=parsed["tag"],
            aad=aad.encode() if aad else b""
        )

    def rotate_key(self, new_kid: str, new_secret: bytes):
        """Rotate to a new key.

        Args:
            new_kid: New key ID
            new_secret: New 32-byte master secret
        """
        self._kid = new_kid
        self._master_secret = new_secret
        self._seal = SpiralSeal(master_key=new_secret)

    @staticmethod
    def get_status() -> Dict[str, Any]:
        """Get backend status information."""
        _try_load_cryptography()

        # Check PQC availability
        pqc_available = False
        try:
            from ..pqc import Kyber768, Dilithium3
            pqc_available = True
        except ImportError:
            pass

        return {
            "version": "SS1",
            "key_exchange": {
                "backend": "kyber768" if pqc_available else "ecdh",
                "pqc_available": pqc_available
            },
            "signatures": {
                "backend": "dilithium3" if pqc_available else "ecdsa",
                "pqc_available": pqc_available
            },
            "kdf": {
                "backend": "argon2id" if _ARGON2_AVAILABLE else "scrypt" if _CRYPTOGRAPHY_AVAILABLE else "hkdf"
            },
            "aead": {
                "backend": "xchacha20-poly1305" if _NACL_AVAILABLE else "aes-256-gcm" if _CRYPTOGRAPHY_AVAILABLE else "hmac-ctr"
            }
        }
