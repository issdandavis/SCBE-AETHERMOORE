"""
SpiralSeal SS1 - Post-Quantum Hybrid Encryption
================================================
Kyber768 key encapsulation + Dilithium3 signatures + AES-256-GCM
This module provides the high-level API for the 14-layer SCBE pipeline's
cryptographic operations using post-quantum resistant algorithms.
"""
from .spiral_seal import (
    SacredTongue,
    SacredTongueTokenizer,
    Token,
    TONGUE_WORDLISTS,
    DOMAIN_TONGUE_MAP,
    get_tongue_for_domain,
    get_tokenizer,
    get_combined_alphabet,
    get_magical_signature,
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
    SS1_VERSION,
    SALT_SIZE,
    TAG_SIZE,
)

__all__ = [
    'SacredTongue',
    'SacredTongueTokenizer',
    'Token',
    'TONGUE_WORDLISTS',
    'DOMAIN_TONGUE_MAP',
    'get_tongue_for_domain',
    'get_tokenizer',
    'get_combined_alphabet',
    'get_magical_signature',
    'SpiralSeal',
    'SpiralSealSS1',
    'VeiledSeal',
    'PQCSpiralSeal',
    'SpiralSealResult',
    'VeiledSealResult',
    'KDFType',
    'AEADType',
    'quick_seal',
    'quick_unseal',
    'get_crypto_backend_info',
    'SS1_VERSION',
    'SALT_SIZE',
    'TAG_SIZE',
]

__version__ = '0.1.0'
