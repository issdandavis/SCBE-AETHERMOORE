"""TernaryHybridEncoder -- Unified 7-module encoding pipeline.

Connects: DualTernary -> GateSwap -> QuasicrystalLattice -> ChemistryAgent
          -> BalancedTernary -> Governance Decision -> SphereGrid feedback.

@layer Layer 5, 9, 12, 13
@component HybridEncoder
"""

from src.hybrid_encoder.types import (
    EncoderInput,
    EncoderResult,
    HybridRepresentation,
    NegativeSpaceEmbedding,
    MolecularBond,
)
from src.hybrid_encoder.pipeline import TernaryHybridEncoder
from src.hybrid_encoder.state_adapter import StateAdapter
from src.hybrid_encoder.negative_space import NegativeSpaceEncoder
from src.hybrid_encoder.molecular_code import MolecularCodeMapper
from src.hybrid_encoder.hamiltonian_path import HamiltonianTraversal

__all__ = [
    "TernaryHybridEncoder",
    "EncoderInput",
    "EncoderResult",
    "HybridRepresentation",
    "NegativeSpaceEmbedding",
    "MolecularBond",
    "StateAdapter",
    "NegativeSpaceEncoder",
    "MolecularCodeMapper",
    "HamiltonianTraversal",
]
