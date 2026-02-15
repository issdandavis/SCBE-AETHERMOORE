"""
SCBE Python Module — AI Governance Through Geometry
=====================================================

Crystal Cranium v3.0.0: The Geometric Skull for Safe AI

Modules:
    brain.py          — AetherBrain facade with full think() pipeline
    phdm_polyhedra.py — 16-polyhedra registry with zone-dependent topology
    phdm_router.py    — Hamiltonian path routing with φ-weighted energy
    aether_braid.py   — MSR algebra + FSGS hybrid automaton
    quantum_lattice.py — Quantum lattice superposition extensions
    phdm_embedding.py — 21D PHDM embedding model

Author: Issac Davis
"""

from .brain import (
    AetherBrain,
    PoincareBall,
    PHDMLattice,
    FluxState,
    TrustRing,
    ThoughtStatus,
    ThoughtResult,
    create_brain,
    embed_text,
    embed_to_21d,
    embed_vector_to_21d,
    TONGUES,
    GOLDEN_RATIO,
    GOLDEN_RATIO_INV,
    PYTHAGOREAN_COMMA,
    R_FIFTH,
    DIMENSIONS_21D,
    DIMENSIONS_6D,
    TUBE_RADIUS,
)

__version__ = "3.0.0"
__author__ = "Issac Davis"

__all__ = [
    # Core
    "AetherBrain",
    "PoincareBall",
    "PHDMLattice",
    "FluxState",
    "TrustRing",
    "ThoughtStatus",
    "ThoughtResult",
    "create_brain",
    "embed_text",
    "embed_to_21d",
    "embed_vector_to_21d",
    # Constants
    "TONGUES",
    "GOLDEN_RATIO",
    "GOLDEN_RATIO_INV",
    "PYTHAGOREAN_COMMA",
    "R_FIFTH",
    "DIMENSIONS_21D",
    "DIMENSIONS_6D",
    "TUBE_RADIUS",
]
