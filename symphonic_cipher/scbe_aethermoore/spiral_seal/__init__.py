"""
SpiralSeal SS1 - Sacred Tongue Encryption Envelope

Real cryptography with Spiralverse encoding:
- KDF: Argon2id (preferred) or scrypt (fallback)
- AEAD: XChaCha20-Poly1305 (preferred) or AES-256-GCM (fallback)
- Encoding: Six Sacred Tongues (each with 256 tokens)

Simple Usage:
    from symphonic_cipher.scbe_aethermoore.spiral_seal import quick_seal, quick_unseal

    # Encrypt
    ss1_string = quick_seal(b"Hello, World!", b"my_password")
    print(ss1_string)
    # SS1|kid=...|aad=av:|salt=ru:khar'ak ur'eth...|nonce=ko:sil'a kor'ae...|ct=ca:bip'a bop'e...|tag=dr:anvil'a tharn'e...

    # Decrypt
    plaintext = quick_unseal(ss1_string, b"my_password")

Full Usage:
    from symphonic_cipher.scbe_aethermoore.spiral_seal import SpiralSeal

    seal = SpiralSeal(master_password=b"my_secret_password")

    # Encrypt with context
    result = seal.seal(b"sensitive data", aad=b"user:admin|action:read")

    # Get SS1 string for storage/transmission
    ss1_string = result.to_ss1_string()

    # Later, decrypt
    plaintext = seal.unseal_string(ss1_string)

Compatibility API (matches test expectations):
    from symphonic_cipher.scbe_aethermoore.spiral_seal import SpiralSealSS1, seal, unseal

    ss = SpiralSealSS1(master_secret=b'0' * 32, kid='k01')
    blob = ss.seal(b"secret", aad="service=api")
    plaintext = ss.unseal(blob, aad="service=api")

    # Or one-shot:
    blob = seal(b"secret", master_secret=b'0' * 32, aad="test", kid="k01")
    plaintext = unseal(blob, master_secret=b'0' * 32, aad="test")

The Six Sacred Tongues:
    - Kor'aelin (ko): Flow/Intent → encodes nonce
    - Avali (av): Context/Greeting → encodes aad
    - Runethic (ru): Binding/Constraints → encodes salt
    - Cassisivadan (ca): Bitcraft/Math → encodes ciphertext
    - Umbroth (um): Shadow/Veil → encodes redaction markers
    - Draumric (dr): Structure/Forge → encodes auth tag
"""

# Sacred Tongues Tokenizer
from .sacred_tongues import (
    # Core classes
    SacredTongue,
    SacredTongueTokenizer,
    SacredTongueTokenizerCompat,
    Token,
    TongueInfo,

    # Wordlists and mappings
    TONGUE_WORDLISTS,
    DOMAIN_TONGUE_MAP,
    SPIRALSCRIPT_KEYWORDS,
    TONGUES,  # Compatibility dict

    # Functions
    get_tongue_for_domain,
    get_tokenizer,
    get_combined_alphabet,
    get_magical_signature,
    get_tongue_keywords,

    # Compatibility functions
    encode_to_spelltext,
    decode_from_spelltext,
    format_ss1_blob,
    parse_ss1_blob,
)

# SpiralSeal Encryption
from .spiral_seal import (
    # Main classes
    SpiralSeal,
    VeiledSeal,
    PQCSpiralSeal,
    SpiralSealSS1,  # Compatibility class

    # Result types
    SpiralSealResult,
    VeiledSealResult,

    # Enums
    KDFType,
    AEADType,

    # Convenience functions
    quick_seal,
    quick_unseal,
    get_crypto_backend_info,

    # Key derivation (for advanced use)
    derive_key,
    derive_key_argon2id,
    derive_key_scrypt,

    # Constants
    SS1_VERSION,
    SS1_MAGIC,
    SALT_SIZE,
    TAG_SIZE,
    KEY_ID_SIZE,
)

# Convenience seal/unseal functions
from .seal import seal, unseal

__all__ = [
    # Sacred Tongues
    "SacredTongue",
    "SacredTongueTokenizer",
    "SacredTongueTokenizerCompat",
    "Token",
    "TongueInfo",
    "TONGUE_WORDLISTS",
    "DOMAIN_TONGUE_MAP",
    "SPIRALSCRIPT_KEYWORDS",
    "TONGUES",
    "get_tongue_for_domain",
    "get_tokenizer",
    "get_combined_alphabet",
    "get_magical_signature",
    "get_tongue_keywords",
    "encode_to_spelltext",
    "decode_from_spelltext",
    "format_ss1_blob",
    "parse_ss1_blob",

    # SpiralSeal
    "SpiralSeal",
    "SpiralSealSS1",
    "VeiledSeal",
    "PQCSpiralSeal",
    "SpiralSealResult",
    "VeiledSealResult",
    "KDFType",
    "AEADType",
    "quick_seal",
    "quick_unseal",
    "seal",
    "unseal",
    "get_crypto_backend_info",
    "derive_key",
    "derive_key_argon2id",
    "derive_key_scrypt",
    "SS1_VERSION",
    "SS1_MAGIC",
    "SALT_SIZE",
    "TAG_SIZE",
    "KEY_ID_SIZE",
]

__version__ = "1.0.0"
