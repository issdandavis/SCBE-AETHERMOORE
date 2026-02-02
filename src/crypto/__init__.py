"""
SCBE Cryptographic Primitives
=============================

Post-quantum cryptography integrated with Sacred Tongues.

Modules:
- dual_lattice: Kyber/Dilithium cross-stitch with 10D tongue lattice
- octree: Hyperbolic octree voxel storage in Poincare ball
- hyperpath_finder: A* and Bidirectional A* pathfinding in hyperbolic space
- six_d_navigator: 6D vector navigation (Physical XYZ + Operational VHS)
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

from .octree import (
    # Core octree components
    HyperbolicOctree,
    OctreeNode,
    Voxel,
    # Hyperbolic math functions
    poincare_distance,
    weighted_poincare_distance,
    mobius_addition,
    geodesic_midpoint,
    # Constants
    POINCARE_RADIUS,
    OCTANT_TONGUES,
)

from .hyperpath_finder import (
    # Pathfinding
    HyperpathFinder,
    HyperpathResult,
    PathNode,
    # Cost functions
    standard_cost,
    trust_weighted_cost,
    tongue_affinity_cost,
    harmonic_wall_cost,
)

from .six_d_navigator import (
    # 6D Types
    Position6D,
    PhysicalAxis,
    OperationalAxis,
    SacredTongue6D,
    MessageComplexity,
    PathResult6D,
    DockingLock,
    # Navigation
    SixDNavigator,
    CryptographicDocking,
    # Functions
    calculate_message_complexity,
    encode_6d_message,
    decode_6d_message,
    calculate_bandwidth_savings,
    get_tongue_from_6d,
    # Constants
    TONGUE_WEIGHTS_6D,
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
    # Octree / Voxel Storage
    "HyperbolicOctree",
    "OctreeNode",
    "Voxel",
    "poincare_distance",
    "weighted_poincare_distance",
    "mobius_addition",
    "geodesic_midpoint",
    "POINCARE_RADIUS",
    "OCTANT_TONGUES",
    # Pathfinding (3D)
    "HyperpathFinder",
    "HyperpathResult",
    "PathNode",
    "standard_cost",
    "trust_weighted_cost",
    "tongue_affinity_cost",
    "harmonic_wall_cost",
    # 6D Navigation (Spiralverse)
    "Position6D",
    "PhysicalAxis",
    "OperationalAxis",
    "SacredTongue6D",
    "MessageComplexity",
    "PathResult6D",
    "DockingLock",
    "SixDNavigator",
    "CryptographicDocking",
    "calculate_message_complexity",
    "encode_6d_message",
    "decode_6d_message",
    "calculate_bandwidth_savings",
    "get_tongue_from_6d",
    "TONGUE_WEIGHTS_6D",
]

__version__ = "1.2.0"
