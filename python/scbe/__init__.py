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
    defensive_mesh.py — AI kernel governance wrapper for task gating

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
from .defensive_mesh import (
    DefensiveMeshKernel,
    GovernedJob,
    GovernedTask,
    TaskGateResult,
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
    # Defensive mesh kernel
    "DefensiveMeshKernel",
    "GovernedJob",
    "GovernedTask",
    "TaskGateResult",
]
from .atomic_tokenization import AtomicTokenState, Element as AtomicElement
from .atomic_tokenization import TritVector, element_to_tau, element_to_trit_vector
from .atomic_tokenization import map_token_to_atomic_state, map_token_to_element
from .chemical_fusion import FusionParams, FusionResult, fuse_atomic_states, fuse_tokens
from .ingestion_rights import classify_ingestion_rights_record, get_source_record, load_source_registry
from .rhombic_bridge import rhombic_fusion, rhombic_score

__all__ += [
    "AtomicElement",
    "AtomicTokenState",
    "TritVector",
    "element_to_tau",
    "element_to_trit_vector",
    "map_token_to_element",
    "map_token_to_atomic_state",
    "FusionParams",
    "FusionResult",
    "fuse_atomic_states",
    "fuse_tokens",
    "load_source_registry",
    "get_source_record",
    "classify_ingestion_rights_record",
    "rhombic_fusion",
    "rhombic_score",
]
