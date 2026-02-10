"""Symphonic Cipher - Intent-modulated conlang with harmonic verification."""

from .core import (
    SymphonicCipher,
    ConlangDictionary,
    Modality,
    ModalityEncoder,
    HarmonicSynthesizer,
    FeistelPermutation,
    RWPEnvelope,
    derive_msg_key,
    generate_master_key,
    generate_nonce,
)

__all__ = [
    "SymphonicCipher",
    "ConlangDictionary",
    "Modality",
    "ModalityEncoder",
    "HarmonicSynthesizer",
    "FeistelPermutation",
    "RWPEnvelope",
    "derive_msg_key",
    "generate_master_key",
    "generate_nonce",
]

__version__ = "0.1.0"
