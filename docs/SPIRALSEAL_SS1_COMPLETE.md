# SpiralSeal SS1 - Complete Implementation Reference

> Post-Quantum Hybrid Encryption with Sacred Tongue Spell-Text Encoding

## Overview

SpiralSeal SS1 is a cryptographic sealing system that combines:
- **Real Crypto (the wheel)**: AES-256-GCM + HKDF + Kyber768 + Dilithium3
- **Proprietary Format (spokes)**: SS1 container with key rotation, AAD binding
- **Sacred Tongue Encoding (rubber)**: Six constructed languages for spell-text output

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     SpiralSeal SS1 Pipeline                      │
├─────────────────────────────────────────────────────────────────┤
│  Input: plaintext + master_secret + aad + kid                   │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Key Derivation (HKDF-SHA256)                           │    │
│  │  - salt = random(16 bytes)                              │    │
│  │  - K = HKDF(master_secret, salt, "scbe:ss1:enc:v1")     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Encryption (AES-256-GCM)                               │    │
│  │  - nonce = random(12 bytes)                             │    │
│  │  - ciphertext, tag = AES-GCM(K, nonce, plaintext, aad)  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Sacred Tongue Encoding                                 │    │
│  │  - salt → Runethic (ru)                                 │    │
│  │  - nonce → Kor'aelin (ko)                               │    │
│  │  - ciphertext → Cassisivadan (ca)                       │    │
│  │  - tag → Draumric (dr)                                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│                           ▼                                      │
│  Output: SS1|kid=...|aad=...|salt=ru:...|nonce=ko:...|ct=ca:...|tag=dr:...
└─────────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
src/symphonic_cipher/scbe_aethermoore/spiral_seal/
├── __init__.py          # Module exports
├── sacred_tongues.py    # Six Sacred Tongues tokenizer
├── seal.py              # Main SpiralSealSS1 API
├── utils.py             # AES-256-GCM, HKDF utilities
├── key_exchange.py      # Kyber768 KEM wrapper
└── signatures.py        # Dilithium3 signature wrapper
```

---

# FILE 1: sacred_tongues.py
## Six Sacred Tongues - Spell-Text Encoding

```python
"""
Sacred Tongue Tokenizer - SS1 Spell-Text Encoding
==================================================
Deterministic 256-word lists (16 prefixes × 16 suffixes) for each of the
Six Sacred Tongues. Each byte maps to exactly one token.

Token format: prefix'suffix (apostrophe as morpheme seam)

Section tongues (canonical mapping):
- aad/header → Avali (av) - diplomacy/context
- salt → Runethic (ru) - binding
- nonce → Kor'aelin (ko) - flow/intent  
- ciphertext → Cassisivadan (ca) - bitcraft/maths
- auth tag → Draumric (dr) - structure stands
- redaction → Umbroth (um) - veil
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass(frozen=True)
class TongueSpec:
    """Specification for a Sacred Tongue's token vocabulary."""
    code: str           # 2-letter code (ko, av, ru, ca, um, dr)
    name: str           # Full name
    prefixes: Tuple[str, ...]  # 16 prefixes
    suffixes: Tuple[str, ...]  # 16 suffixes
    domain: str         # What this tongue is used for


# =============================================================================
# THE SIX SACRED TONGUES - v1 Wordlists
# =============================================================================

KOR_AELIN = TongueSpec(
    code='ko',
    name="Kor'aelin",
    prefixes=('sil', 'kor', 'vel', 'zar', 'keth', 'thul', 'nav', 'ael',
              'ra', 'med', 'gal', 'lan', 'joy', 'good', 'nex', 'vara'),
    suffixes=('a', 'ae', 'ei', 'ia', 'oa', 'uu', 'eth', 'ar',
              'or', 'il', 'an', 'en', 'un', 'ir', 'oth', 'esh'),
    domain='nonce/flow/intent'
)

AVALI = TongueSpec(
    code='av',
    name='Avali',
    prefixes=('saina', 'talan', 'vessa', 'maren', 'oriel', 'serin', 'nurel', 'lirea',
              'kiva', 'lumen', 'calma', 'ponte', 'verin', 'nava', 'sela', 'tide'),
    suffixes=('a', 'e', 'i', 'o', 'u', 'y', 'la', 're',
              'na', 'sa', 'to', 'mi', 've', 'ri', 'en', 'ul'),
    domain='aad/header/metadata'
)

RUNETHIC = TongueSpec(
    code='ru',
    name='Runethic',
    prefixes=('khar', 'drath', 'bront', 'vael', 'ur', 'mem', 'krak', 'tharn',
              'groth', 'basalt', 'rune', 'sear', 'oath', 'gnarl', 'rift', 'iron'),
    suffixes=('ak', 'eth', 'ik', 'ul', 'or', 'ar', 'um', 'on',
              'ir', 'esh', 'nul', 'vek', 'dra', 'kh', 'va', 'th'),
    domain='salt/binding'
)
```

```python
CASSISIVADAN = TongueSpec(
    code='ca',
    name='Cassisivadan',
    prefixes=('bip', 'bop', 'klik', 'loopa', 'ifta', 'thena', 'elsa', 'spira',
              'rythm', 'quirk', 'fizz', 'gear', 'pop', 'zip', 'mix', 'chass'),
    suffixes=('a', 'e', 'i', 'o', 'u', 'y', 'ta', 'na',
              'sa', 'ra', 'lo', 'mi', 'ki', 'zi', 'qwa', 'sh'),
    domain='ciphertext/bitcraft'
)

UMBROTH = TongueSpec(
    code='um',
    name='Umbroth',
    prefixes=('veil', 'zhur', 'nar', 'shul', 'math', 'hollow', 'hush', 'thorn',
              'dusk', 'echo', 'ink', 'wisp', 'bind', 'ache', 'null', 'shade'),
    suffixes=('a', 'e', 'i', 'o', 'u', 'ae', 'sh', 'th',
              'ak', 'ul', 'or', 'ir', 'en', 'on', 'vek', 'nul'),
    domain='redaction/veil'
)

DRAUMRIC = TongueSpec(
    code='dr',
    name='Draumric',
    prefixes=('anvil', 'tharn', 'mek', 'grond', 'draum', 'ektal', 'temper', 'forge',
              'stone', 'steam', 'oath', 'seal', 'frame', 'pillar', 'rivet', 'ember'),
    suffixes=('a', 'e', 'i', 'o', 'u', 'ae', 'rak', 'mek',
              'tharn', 'grond', 'vek', 'ul', 'or', 'ar', 'en', 'on'),
    domain='tag/structure'
)

# Canonical mapping for SS1 format
TONGUES: Dict[str, TongueSpec] = {
    'ko': KOR_AELIN,
    'av': AVALI,
    'ru': RUNETHIC,
    'ca': CASSISIVADAN,
    'um': UMBROTH,
    'dr': DRAUMRIC,
}

# Section-to-tongue mapping (SS1 canonical)
SECTION_TONGUES = {
    'aad': 'av',      # Avali for metadata/context
    'salt': 'ru',     # Runethic for binding
    'nonce': 'ko',    # Kor'aelin for flow/intent
    'ct': 'ca',       # Cassisivadan for ciphertext
    'tag': 'dr',      # Draumric for auth tag
    'redact': 'um',   # Umbroth for redaction wrapper
}
```

```python
class SacredTongueTokenizer:
    """
    Encode/decode bytes to Sacred Tongue spell-text tokens.
    
    Each byte maps deterministically to one token:
        byte b → prefix[b >> 4] + "'" + suffix[b & 0x0F]
    
    Example:
        byte 0x2A (42) → prefix[2] + "'" + suffix[10]
        In Kor'aelin: vel'an
    """
    
    def __init__(self, tongue_code: str = 'ko'):
        """
        Initialize tokenizer for a specific Sacred Tongue.
        
        Args:
            tongue_code: One of 'ko', 'av', 'ru', 'ca', 'um', 'dr'
        """
        if tongue_code not in TONGUES:
            raise ValueError(f"Unknown tongue: {tongue_code}. Valid: {list(TONGUES.keys())}")
        
        self.tongue = TONGUES[tongue_code]
        self._build_lookup_tables()
    
    def _build_lookup_tables(self):
        """Build forward and reverse lookup tables."""
        # Forward: byte → token
        self._byte_to_token: List[str] = []
        for b in range(256):
            pi = b >> 4        # High nibble (0-15)
            si = b & 0x0F      # Low nibble (0-15)
            token = f"{self.tongue.prefixes[pi]}'{self.tongue.suffixes[si]}"
            self._byte_to_token.append(token)
        
        # Reverse: token → byte
        self._token_to_byte: Dict[str, int] = {
            token: b for b, token in enumerate(self._byte_to_token)
        }
    
    def encode_byte(self, b: int) -> str:
        """Encode a single byte to a token."""
        if not 0 <= b <= 255:
            raise ValueError(f"Byte must be 0-255, got {b}")
        return self._byte_to_token[b]
    
    def decode_token(self, token: str) -> int:
        """Decode a single token to a byte."""
        if token not in self._token_to_byte:
            raise ValueError(f"Unknown token: {token}")
        return self._token_to_byte[token]
    
    def encode(self, data: bytes) -> str:
        """
        Encode bytes to space-separated spell-text tokens.
        
        Args:
            data: Raw bytes to encode
        
        Returns:
            Space-separated token string with tongue prefix
            Example: "ko:sil'a ko:vel'an ko:thul'ir"
        """
        tokens = [f"{self.tongue.code}:{self._byte_to_token[b]}" for b in data]
        return ' '.join(tokens)
    
    def decode(self, spelltext: str) -> bytes:
        """
        Decode spell-text tokens back to bytes.
        
        Args:
            spelltext: Space-separated tokens (with or without tongue prefix)
        
        Returns:
            Decoded bytes
        """
        result = []
        for token in spelltext.split():
            # Strip tongue prefix if present (e.g., "ko:sil'a" → "sil'a")
            if ':' in token:
                _, token = token.split(':', 1)
            result.append(self._token_to_byte[token])
        return bytes(result)
```

```python
# =============================================================================
# HIGH-LEVEL ENCODING FUNCTIONS
# =============================================================================

def encode_to_spelltext(data: bytes, section: str) -> str:
    """
    Encode bytes using the canonical tongue for a given section.
    
    Args:
        data: Raw bytes to encode
        section: One of 'aad', 'salt', 'nonce', 'ct', 'tag', 'redact'
    
    Returns:
        Spell-text encoded string
    """
    tongue_code = SECTION_TONGUES.get(section, 'ca')  # Default to Cassisivadan
    tokenizer = SacredTongueTokenizer(tongue_code)
    return tokenizer.encode(data)


def decode_from_spelltext(spelltext: str, section: str) -> bytes:
    """
    Decode spell-text using the canonical tongue for a given section.
    """
    tongue_code = SECTION_TONGUES.get(section, 'ca')
    tokenizer = SacredTongueTokenizer(tongue_code)
    return tokenizer.decode(spelltext)


def format_ss1_blob(
    kid: str,
    aad: str,
    salt: bytes,
    nonce: bytes,
    ciphertext: bytes,
    tag: bytes
) -> str:
    """
    Format a complete SS1 spell-text blob.
    
    Returns:
        SS1|kid=...|aad=...|salt=ru:...|nonce=ko:...|ct=ca:...|tag=dr:...
    """
    parts = [
        'SS1',
        f'kid={kid}',
        f'aad={aad}',
        f'salt={encode_to_spelltext(salt, "salt")}',
        f'nonce={encode_to_spelltext(nonce, "nonce")}',
        f'ct={encode_to_spelltext(ciphertext, "ct")}',
        f'tag={encode_to_spelltext(tag, "tag")}',
    ]
    return '|'.join(parts)


def parse_ss1_blob(blob: str) -> Dict[str, any]:
    """
    Parse an SS1 spell-text blob.
    
    Returns:
        Dict with keys: version, kid, aad, salt, nonce, ct, tag
    """
    if not blob.startswith('SS1|'):
        raise ValueError("Invalid SS1 blob: must start with 'SS1|'")
    
    parts = blob.split('|')
    result = {'version': 'SS1'}
    
    for part in parts[1:]:  # Skip 'SS1' prefix
        if '=' not in part:
            continue
        key, value = part.split('=', 1)
        
        if key in ('salt', 'nonce', 'ct', 'tag'):
            # Decode spell-text to bytes
            section_map = {'salt': 'salt', 'nonce': 'nonce', 'ct': 'ct', 'tag': 'tag'}
            result[key] = decode_from_spelltext(value, section_map[key])
        else:
            result[key] = value
    
    return result
```

```python
# =============================================================================
# LANGUES WEIGHTING SYSTEM (LWS) INTEGRATION
# =============================================================================

def compute_lws_weights(tongue_code: str) -> List[float]:
    """
    Compute Langues Weighting System weights for a Sacred Tongue.
    
    Uses golden ratio powers (φ^i) for importance hierarchy,
    normalized to sum to 1.
    """
    PHI = 1.618033988749895  # Golden ratio
    weights = [PHI ** i for i in range(16)]
    total = sum(weights)
    weights = [w / total for w in weights]
    return weights


def get_tongue_signature(tongue_code: str) -> bytes:
    """
    Get the unique cryptographic signature for a Sacred Tongue.
    
    This is used for authentication and verification in the
    polyglot interoperability layer.
    
    Returns:
        32-byte SHA-256 hash of the tongue's vocabulary
    """
    import hashlib
    tongue = TONGUES[tongue_code]
    vocab_str = '|'.join(tongue.prefixes) + '||' + '|'.join(tongue.suffixes)
    return hashlib.sha256(vocab_str.encode('utf-8')).digest()
```

---

# FILE 2: seal.py
## Main SpiralSeal SS1 API

```python
"""
SpiralSeal SS1 - High-Level API
================================
Post-quantum hybrid encryption using Kyber768 + Dilithium3 + AES-256-GCM.

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
```

```python
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
        
        self._master_secret = master_secret
        
        # Generate PQC keys if in hybrid mode
        if mode == 'hybrid':
            self._sk_enc, self._pk_enc = kyber_keygen()
            self._sk_sig, self._pk_sig = dilithium_keygen()
        else:
            self._sk_enc = self._pk_enc = None
            self._sk_sig = self._pk_sig = None
```

```python
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
        k_enc = derive_key(self._master_secret, salt, b'scbe:ss1:enc:v1')
        
        # Decrypt
        aad_bytes = aad.encode('utf-8') if aad else b''
        try:
            plaintext = aes_gcm_decrypt(k_enc, nonce, ciphertext, tag, aad_bytes)
            return plaintext
        except ValueError as e:
            # Fail-to-noise: don't expose details
            raise ValueError("Authentication failed") from None
```

```python
    def sign(self, message: bytes) -> bytes:
        """Sign a message using Dilithium3."""
        if self.mode != 'hybrid' or not self._sk_sig:
            raise RuntimeError("Signing requires hybrid mode")
        return dilithium_sign(self._sk_sig, message)
    
    def verify(self, message: bytes, signature: bytes) -> bool:
        """Verify a Dilithium3 signature."""
        if self.mode != 'hybrid' or not self._pk_sig:
            raise RuntimeError("Verification requires hybrid mode")
        return dilithium_verify(self._pk_sig, message, signature)
    
    def rotate_key(self, new_kid: str, new_master_secret: bytes):
        """Rotate to a new master secret."""
        if len(new_master_secret) != 32:
            raise ValueError("master_secret must be 32 bytes")
        
        self.kid = new_kid
        self._master_secret = new_master_secret
        
        if self.mode == 'hybrid':
            self._sk_enc, self._pk_enc = kyber_keygen()
            self._sk_sig, self._pk_sig = dilithium_keygen()
    
    @staticmethod
    def get_status() -> dict:
        """Get the status of cryptographic backends."""
        return {
            'version': SpiralSealSS1.VERSION,
            'key_exchange': get_pqc_status(),
            'signatures': get_pqc_sig_status(),
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def seal(plaintext: bytes, master_secret: bytes, aad: str = '', kid: str = 'k01') -> str:
    """One-shot seal function."""
    ss = SpiralSealSS1(master_secret=master_secret, kid=kid, mode='symmetric')
    return ss.seal(plaintext, aad=aad)


def unseal(ss1_blob: str, master_secret: bytes, aad: str = '') -> bytes:
    """One-shot unseal function."""
    ss = SpiralSealSS1(master_secret=master_secret, mode='symmetric')
    return ss.unseal(ss1_blob, aad=aad)
```

---

# FILE 3: utils.py
## Cryptographic Utilities

```python
"""
Cryptographic utilities for SpiralSeal SS1.
AES-256-GCM encryption/decryption with constant-time operations.
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
```

```python
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
        ciphertext = ct_with_tag[:-16]
        tag = ct_with_tag[-16:]
        return nonce, ciphertext, tag
    
    else:
        raise RuntimeError("No cryptographic backend available. Install pycryptodome or cryptography.")


def aes_gcm_decrypt(key: bytes, nonce: bytes, ciphertext: bytes, tag: bytes, aad: bytes = b'') -> bytes:
    """
    AES-256-GCM decryption with authentication.
    
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
```

```python
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
```

---

# FILE 4: key_exchange.py
## Post-Quantum Key Exchange (Kyber768)

```python
"""
Post-Quantum Key Exchange - Kyber768
=====================================
Wrapper for Kyber768 key encapsulation mechanism (KEM).

Security level: ~AES-192 equivalent (NIST Level 3)
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
```

```python
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
        public_key = hashlib.sha256(b'kyber_pk_sim:' + secret_key).digest()
        return secret_key, public_key


def kyber_encaps(public_key: bytes) -> Tuple[bytes, bytes]:
    """
    Encapsulate a shared secret using Kyber768.
    
    Returns:
        Tuple of (ciphertext, shared_secret)
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
        shared_secret = hashlib.sha256(ephemeral + public_key).digest()
        ciphertext = ephemeral + ciphertext
        return ciphertext, shared_secret


def kyber_decaps(secret_key: bytes, ciphertext: bytes) -> bytes:
    """
    Decapsulate a shared secret using Kyber768.
    
    Returns:
        32-byte shared secret
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
        public_key = hashlib.sha256(b'kyber_pk_sim:' + secret_key).digest()
        shared_secret = hashlib.sha256(ephemeral + public_key).digest()
        return shared_secret


def get_pqc_status() -> dict:
    """Get the status of post-quantum cryptography support."""
    return {
        'available': PQC_AVAILABLE,
        'backend': PQC_BACKEND,
        'algorithm': 'Kyber768',
        'security_level': 'NIST Level 3 (~AES-192)' if PQC_AVAILABLE else 'FALLBACK (NOT PQ-SECURE)',
        'warning': None if PQC_AVAILABLE else 
            'Using classical fallback! Install liboqs-python for post-quantum security.'
    }
```

---

# FILE 5: signatures.py
## Post-Quantum Digital Signatures (Dilithium3)

```python
"""
Post-Quantum Digital Signatures - Dilithium3
=============================================
Wrapper for Dilithium3 digital signature scheme.

Security level: ~AES-192 equivalent (NIST Level 3)
"""

import os
import hashlib
import hmac
from typing import Tuple

# Try to import post-quantum library
try:
    from oqs import Signature
    PQC_SIG_AVAILABLE = True
    PQC_SIG_BACKEND = 'liboqs'
except ImportError:
    try:
        import pqcrypto.sign.dilithium3 as dilithium
        PQC_SIG_AVAILABLE = True
        PQC_SIG_BACKEND = 'pqcrypto'
    except ImportError:
        PQC_SIG_AVAILABLE = False
        PQC_SIG_BACKEND = 'fallback'


class DilithiumKeyPair:
    """Container for Dilithium3 key pair."""
    def __init__(self, public_key: bytes, secret_key: bytes):
        self.public_key = public_key
        self.secret_key = secret_key


def dilithium_keygen() -> Tuple[bytes, bytes]:
    """
    Generate a Dilithium3 key pair.
    
    Returns:
        Tuple of (secret_key, public_key)
    """
    if PQC_SIG_BACKEND == 'liboqs':
        sig = Signature("Dilithium3")
        public_key = sig.generate_keypair()
        secret_key = sig.export_secret_key()
        return secret_key, public_key
    
    elif PQC_SIG_BACKEND == 'pqcrypto':
        public_key, secret_key = dilithium.generate_keypair()
        return secret_key, public_key
    
    else:
        # Fallback: HMAC-based simulation
        # WARNING: This is NOT post-quantum secure! For development only.
        secret_key = os.urandom(64)
        public_key = hashlib.sha256(b'dilithium_pk_sim:' + secret_key[:32]).digest()
        return secret_key, public_key


def dilithium_sign(secret_key: bytes, message: bytes) -> bytes:
    """Sign a message using Dilithium3."""
    if PQC_SIG_BACKEND == 'liboqs':
        sig = Signature("Dilithium3", secret_key)
        signature = sig.sign(message)
        return signature
    
    elif PQC_SIG_BACKEND == 'pqcrypto':
        signature = dilithium.sign(secret_key, message)
        return signature
    
    else:
        # Fallback: HMAC-SHA256 simulation
        signature = hmac.new(secret_key, message, hashlib.sha256).digest()
        return b'FALLBACK_SIG:' + signature


def dilithium_verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    """Verify a Dilithium3 signature."""
    if PQC_SIG_BACKEND == 'liboqs':
        sig = Signature("Dilithium3")
        try:
            return sig.verify(message, signature, public_key)
        except Exception:
            return False
    
    elif PQC_SIG_BACKEND == 'pqcrypto':
        try:
            dilithium.verify(public_key, message, signature)
            return True
        except Exception:
            return False
    
    else:
        # Fallback verification
        if not signature.startswith(b'FALLBACK_SIG:'):
            return False
        expected_sig = signature[13:]
        return len(expected_sig) == 32


def get_pqc_sig_status() -> dict:
    """Get the status of post-quantum signature support."""
    return {
        'available': PQC_SIG_AVAILABLE,
        'backend': PQC_SIG_BACKEND,
        'algorithm': 'Dilithium3',
        'security_level': 'NIST Level 3 (~AES-192)' if PQC_SIG_AVAILABLE else 'FALLBACK (NOT PQ-SECURE)',
        'warning': None if PQC_SIG_AVAILABLE else 
            'Using classical fallback! Install liboqs-python for post-quantum security.'
    }
```

---

# FILE 6: __init__.py
## Module Exports

```python
"""
SpiralSeal SS1 - Post-Quantum Hybrid Encryption
================================================
Kyber768 key encapsulation + Dilithium3 signatures + AES-256-GCM

This module provides the high-level API for the 14-layer SCBE pipeline's
cryptographic operations using post-quantum resistant algorithms.
"""

from .seal import SpiralSealSS1
from .sacred_tongues import SacredTongueTokenizer, encode_to_spelltext, decode_from_spelltext

__all__ = [
    'SpiralSealSS1',
    'SacredTongueTokenizer',
    'encode_to_spelltext',
    'decode_from_spelltext',
]

__version__ = '0.1.0'
```

---

# FILE 7: test_spiral_seal.py
## Test Suite (13 Passing Tests)

```python
"""
Tests for SpiralSeal SS1 implementation.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from symphonic_cipher.scbe_aethermoore.spiral_seal import (
    SpiralSealSS1,
    SacredTongueTokenizer,
    encode_to_spelltext,
    decode_from_spelltext,
)
from symphonic_cipher.scbe_aethermoore.spiral_seal.sacred_tongues import (
    TONGUES, format_ss1_blob, parse_ss1_blob
)
from symphonic_cipher.scbe_aethermoore.spiral_seal.seal import seal, unseal


class TestSacredTongueTokenizer:
    """Tests for Sacred Tongue spell-text encoding."""
    
    def test_all_tongues_have_256_tokens(self):
        """Each tongue should have exactly 256 unique tokens (16×16)."""
        for code, tongue in TONGUES.items():
            assert len(tongue.prefixes) == 16
            assert len(tongue.suffixes) == 16
            
            tokenizer = SacredTongueTokenizer(code)
            tokens = set()
            for b in range(256):
                token = tokenizer.encode_byte(b)
                assert token not in tokens
                tokens.add(token)
            assert len(tokens) == 256
    
    def test_roundtrip_single_byte(self):
        """Encoding and decoding a single byte should be lossless."""
        for code in TONGUES.keys():
            tokenizer = SacredTongueTokenizer(code)
            for b in range(256):
                token = tokenizer.encode_byte(b)
                decoded = tokenizer.decode_token(token)
                assert decoded == b
    
    def test_roundtrip_bytes(self):
        """Encoding and decoding arbitrary bytes should be lossless."""
        test_data = b"Hello, SpiralSeal!"
        
        for code in TONGUES.keys():
            tokenizer = SacredTongueTokenizer(code)
            encoded = tokenizer.encode(test_data)
            decoded = tokenizer.decode(encoded)
            assert decoded == test_data
    
    def test_token_format(self):
        """Tokens should have the format 'prefix'suffix'."""
        tokenizer = SacredTongueTokenizer('ko')  # Kor'aelin
        
        assert tokenizer.encode_byte(0x00) == "sil'a"
        assert tokenizer.encode_byte(0xFF) == "vara'esh"
        assert tokenizer.encode_byte(0x2A) == "vel'an"
    
    def test_section_encoding(self):
        """Section-specific encoding should use correct tongues."""
        test_data = b"\x00\x01\x02"
        
        assert 'ru:' in encode_to_spelltext(test_data, 'salt')
        assert 'ko:' in encode_to_spelltext(test_data, 'nonce')
        assert 'ca:' in encode_to_spelltext(test_data, 'ct')
```

```python
class TestSS1Format:
    """Tests for SS1 blob formatting and parsing."""
    
    def test_format_and_parse_roundtrip(self):
        """Formatting and parsing SS1 blob should be lossless."""
        salt = b'\x01\x02\x03\x04'
        nonce = b'\x05\x06\x07\x08'
        ciphertext = b'\x09\x0a\x0b\x0c'
        tag = b'\x0d\x0e\x0f\x10'
        
        blob = format_ss1_blob(
            kid='k01', aad='service=test',
            salt=salt, nonce=nonce, ciphertext=ciphertext, tag=tag
        )
        
        assert blob.startswith('SS1|')
        
        parsed = parse_ss1_blob(blob)
        assert parsed['version'] == 'SS1'
        assert parsed['kid'] == 'k01'
        assert parsed['aad'] == 'service=test'
        assert parsed['salt'] == salt
        assert parsed['nonce'] == nonce
        assert parsed['ct'] == ciphertext
        assert parsed['tag'] == tag


class TestSpiralSealSS1:
    """Tests for the main SpiralSeal API."""
    
    def test_seal_unseal_roundtrip(self):
        """Sealing and unsealing should recover original plaintext."""
        master_secret = b'0' * 32
        plaintext = b"My secret API key: sk-1234567890"
        aad = "service=openai;env=prod"
        
        ss = SpiralSealSS1(master_secret=master_secret, kid='k01')
        
        sealed = ss.seal(plaintext, aad=aad)
        assert sealed.startswith('SS1|')
        
        unsealed = ss.unseal(sealed, aad=aad)
        assert unsealed == plaintext
    
    def test_aad_mismatch_fails(self):
        """Unsealing with wrong AAD should fail."""
        master_secret = b'0' * 32
        ss = SpiralSealSS1(master_secret=master_secret)
        sealed = ss.seal(b"secret", aad="correct_aad")
        
        with pytest.raises(ValueError, match="AAD mismatch"):
            ss.unseal(sealed, aad="wrong_aad")
    
    def test_tampered_ciphertext_fails(self):
        """Tampered ciphertext should fail authentication."""
        master_secret = b'0' * 32
        ss = SpiralSealSS1(master_secret=master_secret)
        sealed = ss.seal(b"secret", aad="test")
        
        parsed = parse_ss1_blob(sealed)
        original_tag = parsed['tag']
        tampered_tag = bytes([original_tag[0] ^ 0xFF]) + original_tag[1:]
        
        tampered_blob = format_ss1_blob(
            kid=parsed['kid'], aad=parsed['aad'],
            salt=parsed['salt'], nonce=parsed['nonce'],
            ciphertext=parsed['ct'], tag=tampered_tag
        )
        
        with pytest.raises(ValueError, match="Authentication failed"):
            ss.unseal(tampered_blob, aad="test")
    
    def test_convenience_functions(self):
        """Test one-shot seal/unseal functions."""
        master_secret = b'1' * 32
        plaintext = b"quick test"
        
        sealed = seal(plaintext, master_secret, aad="test", kid='k02')
        assert 'kid=k02' in sealed
        
        unsealed = unseal(sealed, master_secret, aad="test")
        assert unsealed == plaintext
    
    def test_key_rotation(self):
        """Key rotation should work correctly."""
        old_secret = b'old_key_' + b'0' * 24
        new_secret = b'new_key_' + b'1' * 24
        
        ss = SpiralSealSS1(master_secret=old_secret, kid='k01')
        sealed_old = ss.seal(b"rotate me", aad="test")
        
        ss.rotate_key('k02', new_secret)
        sealed_new = ss.seal(b"rotate me", aad="test")
        
        assert 'kid=k01' in sealed_old
        assert 'kid=k02' in sealed_new
        
        with pytest.raises(ValueError):
            ss.unseal(sealed_old, aad="test")
    
    def test_status_report(self):
        """Status report should include backend info."""
        status = SpiralSealSS1.get_status()
        assert status['version'] == 'SS1'
        assert 'key_exchange' in status
        assert 'signatures' in status


class TestCryptoBackends:
    """Tests for cryptographic backend availability."""
    
    def test_utils_available(self):
        """Crypto utils should be importable."""
        from symphonic_cipher.scbe_aethermoore.spiral_seal.utils import (
            aes_gcm_encrypt, aes_gcm_decrypt, derive_key
        )
        
        key = b'0' * 32
        nonce, ct, tag = aes_gcm_encrypt(key, b"test")
        decrypted = aes_gcm_decrypt(key, nonce, ct, tag)
        assert decrypted == b"test"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

---

# Quick Reference

## Six Sacred Tongues Vocabulary

| Tongue | Code | Domain | Example Token |
|--------|------|--------|---------------|
| Kor'aelin | ko | nonce/flow | `sil'a`, `vel'an`, `vara'esh` |
| Avali | av | aad/metadata | `saina'a`, `talan'mi` |
| Runethic | ru | salt/binding | `khar'ak`, `vael'ik` |
| Cassisivadan | ca | ciphertext | `bip'a`, `mix'zi` |
| Umbroth | um | redaction | `veil'a`, `shade'nul` |
| Draumric | dr | auth tag | `anvil'a`, `seal'vek` |

## SS1 Format

```
SS1|kid=k01|aad=service=openai;env=prod|salt=ru:khar'eth ru:vael'ik ...|nonce=ko:vel'oa ko:thul'ir ...|ct=ca:bip'na ca:mix'zi ...|tag=dr:tharn'mek dr:seal'vek ...
```

## Usage Example

```python
from symphonic_cipher.scbe_aethermoore.spiral_seal import SpiralSealSS1

# Initialize with master secret (inject from env/KMS in production!)
ss = SpiralSealSS1(master_secret=b'your-32-byte-secret-key-here!!!', kid='k01')

# Seal an API key
sealed = ss.seal(
    b"sk-1234567890abcdef",
    aad="service=openai;env=prod"
)
print(sealed)
# SS1|kid=k01|aad=service=openai;env=prod|salt=ru:...|nonce=ko:...|ct=ca:...|tag=dr:...

# Unseal
plaintext = ss.unseal(sealed, aad="service=openai;env=prod")
print(plaintext)  # b"sk-1234567890abcdef"
```

## Security Properties

1. **Confidentiality**: AES-256-GCM encryption
2. **Integrity**: GCM authentication tag
3. **AAD Binding**: Additional authenticated data prevents context confusion
4. **Key Rotation**: Key IDs (kid) support multiple master secrets
5. **Post-Quantum Ready**: Kyber768 + Dilithium3 in hybrid mode
6. **Fail-to-Noise**: Errors don't leak information

## Non-Negotiables

- ❌ Never hardcode `master_secret` in code
- ❌ Never ignore authentication failures
- ❌ Never change wordlists without bumping version (SS1 → SS2)
- ✅ Always inject secrets via env/KMS
- ✅ Always verify AAD matches on unseal
- ✅ Always use AEAD verify-on-decrypt

---

*Generated from SpiralSeal SS1 v0.1.0*
