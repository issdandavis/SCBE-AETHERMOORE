"""Triangulated PHDM Lattice — governance-as-geometry on 21D polyhedral mesh."""
from .triangulated_phdm import (
    TriangulatedPHDMLattice,
    LatticeNode,
    TokenizerEdge,
    Triangle,
    ALL_DIMS,
    TONGUE_DIMS,
    PHASE_DIMS,
    TELEMETRY_DIMS,
)

__all__ = [
    "TriangulatedPHDMLattice",
    "LatticeNode",
    "TokenizerEdge",
    "Triangle",
    "ALL_DIMS",
    "TONGUE_DIMS",
    "PHASE_DIMS",
    "TELEMETRY_DIMS",
]
