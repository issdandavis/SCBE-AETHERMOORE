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
from .atomic_tokenization import TritVector, atomic_drift_scale, element_to_tau, element_to_trit_vector
from .atomic_tokenization import map_token_to_atomic_state, map_token_to_element
from .chemical_fusion import FusionParams, FusionResult, fuse_atomic_states, fuse_tokens
from .ca_opcode_table import (
    CAOpcodeEntry,
    OP_TABLE as CA_OP_TABLE,
    ca_opcode_to_atomic_state,
    ca_opcodes_to_atomic_states,
    fuse_ca_opcodes,
    get_ca_opcode,
    validate_ca_table,
)
from .history_reducer import (
    FibonacciTrustLadder,
    HistoryReducerState,
    HistoryStepResult,
    reduce_atomic_history,
    reduce_years,
)
from .ingestion_rights import classify_ingestion_rights_record, get_source_record, load_source_registry
from .rhombic_bridge import rhombic_fusion, rhombic_score
from .semantic_gate import SemanticBlendPolicy, SemanticGateRecord, SemanticSignal, evaluate_semantic_gate
from .tongue_code_lanes import (
    CODE_LANE_REGISTRY,
    classify_code_lane_alignment,
    default_code_lane_profile,
    expected_code_lanes,
)

__all__ += [
    "AtomicElement",
    "AtomicTokenState",
    "TritVector",
    "atomic_drift_scale",
    "element_to_tau",
    "element_to_trit_vector",
    "map_token_to_element",
    "map_token_to_atomic_state",
    "FusionParams",
    "FusionResult",
    "fuse_atomic_states",
    "fuse_tokens",
    "CAOpcodeEntry",
    "CA_OP_TABLE",
    "validate_ca_table",
    "get_ca_opcode",
    "ca_opcode_to_atomic_state",
    "ca_opcodes_to_atomic_states",
    "fuse_ca_opcodes",
    "FibonacciTrustLadder",
    "HistoryReducerState",
    "HistoryStepResult",
    "reduce_atomic_history",
    "reduce_years",
    "CODE_LANE_REGISTRY",
    "default_code_lane_profile",
    "expected_code_lanes",
    "classify_code_lane_alignment",
    "load_source_registry",
    "get_source_record",
    "classify_ingestion_rights_record",
    "rhombic_fusion",
    "rhombic_score",
    "SemanticSignal",
    "SemanticBlendPolicy",
    "SemanticGateRecord",
    "evaluate_semantic_gate",
]
