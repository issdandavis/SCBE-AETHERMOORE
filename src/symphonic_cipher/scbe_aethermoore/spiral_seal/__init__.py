"""
SpiralSeal SS1 - Post-Quantum Hybrid Encryption
================================================
Kyber768 key encapsulation + Dilithium3 signatures + AES-256-GCM

This module provides the high-level API for the 14-layer SCBE pipeline's
cryptographic operations using post-quantum resistant algorithms.
"""

# Import from sacred_tongues
from .sacred_tongues import (
    SacredTongue,
    SacredTongueTokenizer,
    Token,
    TongueSpec,
    TONGUES,
    TONGUE_WORDLISTS,
    DOMAIN_TONGUE_MAP,
    SECTION_TONGUES,
    get_tongue_for_domain,
    get_tokenizer,
    get_combined_alphabet,
    get_magical_signature,
    get_tongue_signature,
    encode_to_spelltext,
    decode_from_spelltext,
    format_ss1_blob,
    parse_ss1_blob,
)

# Import from spiral_seal (main implementation)
from .spiral_seal import (
    SpiralSeal,
    SpiralSealSS1,
    VeiledSeal,
    PQCSpiralSeal,
    SpiralSealResult,
    VeiledSealResult,
    KDFType,
    AEADType,
    quick_seal,
    quick_unseal,
    get_crypto_backend_info,
    SALT_SIZE,
    TAG_SIZE,
)

# Constants
SS1_VERSION = 'SS1'

__all__ = [
    # Sacred Tongues
    'SacredTongue',
    'SacredTongueTokenizer',
    'Token',
    'TongueSpec',
    'TONGUES',
    'TONGUE_WORDLISTS',
    'DOMAIN_TONGUE_MAP',
    'SECTION_TONGUES',
    'get_tongue_for_domain',
    'get_tokenizer',
    'get_combined_alphabet',
    'get_magical_signature',
    'get_tongue_signature',
    'encode_to_spelltext',
    'decode_from_spelltext',
    'format_ss1_blob',
    'parse_ss1_blob',
    # Seal classes
    'SpiralSeal',
    'SpiralSealSS1',
    'VeiledSeal',
    'PQCSpiralSeal',
    'SpiralSealResult',
    'VeiledSealResult',
    # Enums
    'KDFType',
    'AEADType',
    # Constants
    'SS1_VERSION',
    'SALT_SIZE',
    'TAG_SIZE',
    # Functions
    'quick_seal',
    'quick_unseal',
    'get_crypto_backend_info',
]

__version__ = '0.1.0'
