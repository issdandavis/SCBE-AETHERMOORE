"""
SCBE Cryptographic Primitives
=============================

Post-quantum cryptography integrated with Sacred Tongues.

Modules:
- dual_lattice: Kyber/Dilithium cross-stitch with 10D tongue lattice
"""

from .dual_lattice import (
    # Core types
    SacredTongue,
    FluxState,
    LatticeVector,
    TongueContext,
    # Pattern generators
    CrossStitchPattern,
    # Cryptographic layers
    KyberTongueEncryptor,
    DilithiumTongueSigner,
    # Complete system
    DualLatticeCrossStitch,
    # Governance integration
    TongueLatticeGovernor,
    # Constants
    TONGUE_PHASES,
    TONGUE_WEIGHTS,
    PHI,
)

__all__ = [
    # Core types
    "SacredTongue",
    "FluxState",
    "LatticeVector",
    "TongueContext",
    # Pattern generators
    "CrossStitchPattern",
    # Cryptographic layers
    "KyberTongueEncryptor",
    "DilithiumTongueSigner",
    # Complete system
    "DualLatticeCrossStitch",
    # Governance integration
    "TongueLatticeGovernor",
    # Constants
    "TONGUE_PHASES",
    "TONGUE_WEIGHTS",
    "PHI",
]

__version__ = "1.0.0"
