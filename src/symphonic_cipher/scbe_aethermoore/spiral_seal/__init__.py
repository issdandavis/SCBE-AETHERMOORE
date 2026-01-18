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
