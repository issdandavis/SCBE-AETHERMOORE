"""Compatibility import for repository-root execution.

The packaged implementation lives under ``src/``. This shim prevents the
legacy top-level package tree from shadowing that implementation when commands
are run directly from the repository root.
"""

from src.symphonic_cipher.scbe_aethermoore.axiom_grouped.axiom_lens import (
    AXIOM_INDEX,
    AXIOM_LENS_BASIS_3D,
    AXIOM_ORDER,
    AxiomLensConfig,
    AxiomLensResult,
    build_axiom_lens,
)

__all__ = [
    "AXIOM_ORDER",
    "AXIOM_INDEX",
    "AXIOM_LENS_BASIS_3D",
    "AxiomLensConfig",
    "AxiomLensResult",
    "build_axiom_lens",
]
