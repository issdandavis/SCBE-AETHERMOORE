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
    Token,

    # Wordlists and mappings
    TONGUE_WORDLISTS,
    DOMAIN_TONGUE_MAP,
    SPIRALSCRIPT_KEYWORDS,

    # Functions
    get_tongue_for_domain,
    get_tokenizer,
    get_combined_alphabet,
    get_magical_signature,
    get_tongue_keywords,
)

# SpiralSeal Encryption
from .spiral_seal import (
    # Main classes
    SpiralSeal,
    VeiledSeal,
    PQCSpiralSeal,

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

__all__ = [
    # Sacred Tongues
    "SacredTongue",
    "SacredTongueTokenizer",
    "Token",
    "TONGUE_WORDLISTS",
    "DOMAIN_TONGUE_MAP",
    "SPIRALSCRIPT_KEYWORDS",
    "get_tongue_for_domain",
    "get_tokenizer",
    "get_combined_alphabet",
    "get_magical_signature",
    "get_tongue_keywords",

    # SpiralSeal
    "SpiralSeal",
    "VeiledSeal",
    "PQCSpiralSeal",
    "SpiralSealResult",
    "VeiledSealResult",
    "KDFType",
    "AEADType",
    "quick_seal",
    "quick_unseal",
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
