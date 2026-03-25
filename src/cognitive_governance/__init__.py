"""
Cognitive Governance Module
===========================

Implements AI governance through double hypercube geometry.
Adversarial intent costs exponentially more the further it drifts
from safe operation, making attacks computationally infeasible.

Core Innovation:
- 54 dimensional faces (3 valences x 3 spatial x 6 tongues)
- Selective dimensional permeability (walls exist in some dimensions but not others)
- H = R^((d*gamma)^2) exponential cost scaling

@module cognitive_governance
@layer L1-L14 (full pipeline integration)
"""

from .dimensional_space import (
    CognitivePoint,
    DimensionalSpace,
    StateValence,
    TongueVector,
)
from .governance_engine import GovernanceDecision, GovernanceEngine
from .hypercube_geometry import DoubleHypercube, Hypercube, PhaseProjection
from .permeability import DimensionalWall, PermeabilityMatrix, WallVisibility

__all__ = [
    "CognitivePoint",
    "DimensionalSpace",
    "StateValence",
    "TongueVector",
    "Hypercube",
    "DoubleHypercube",
    "PhaseProjection",
    "DimensionalWall",
    "PermeabilityMatrix",
    "WallVisibility",
    "GovernanceEngine",
    "GovernanceDecision",
]
