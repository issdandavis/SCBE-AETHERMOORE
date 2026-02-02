"""
SCBE Cryptographic Primitives
=============================

Post-quantum cryptography integrated with Sacred Tongues.

"Moving Past Binary" - Three interconnected systems:

Modules:
- dual_lattice: Kyber/Dilithium cross-stitch with 10D tongue lattice
- symphonic_cipher: Signed frequency mapping (negative IDs = shadow tokens)
- geo_seal: Hyperbolic geometry with signed context vectors
- signed_lattice_bridge: Integration layer connecting all three
"""

# Dual Lattice (Kyber/Dilithium + Sacred Tongues)
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

# Symphonic Cipher (Signed Audio Frequency Mapping)
from .symphonic_cipher import (
    SymphonicToken,
    TonguePolarity,
    SACRED_TONGUE_VOCAB,
    BASE_FREQ,
    FREQ_STEP,
    token_to_frequency,
    id_to_frequency,
    generate_tone,
    generate_symphonic_sequence,
    analyze_polarity_balance,
)

# GeoSeal (Hyperbolic Geometry + Signed Context)
from .geo_seal import (
    ContextVector,
    SecurityPosture,
    bytes_to_signed_signal,
    signed_signal_to_bytes,
    hyperbolic_distance,
    hyperbolic_midpoint,
    hyperbolic_angle,
    compute_triangle_deficit,
    harmonic_wall_cost,
    trust_from_position,
)

# Signed Lattice Bridge (Integration Layer)
from .signed_lattice_bridge import (
    SignedGovernanceResult,
    SignedLatticeBridge,
)

# Hyperbolic Octree (Sparse Voxel Storage)
from .octree import (
    OctreeNode,
    HyperbolicOctree,
)

# Hyperpath Finder (A* and Bidirectional A*)
from .hyperpath_finder import (
    HyperpathFinder,
    PathResult,
    hyperbolic_distance_safe,
)

# Visualization (Poincare Disk + 3D Voxels)
from .hyperbolic_viz import (
    classical_mds,
    poincare_geodesic,
    visualize_poincare_disk,
    visualize_3d_voxels,
)

# Symphonic Waveform Export (Audio Synthesis)
from .symphonic_waveform import (
    SymphonicIntent,
    HarmonicFingerprint,
    position_to_intent,
    hyperpath_to_intents,
    hyperpath_to_waveform,
    geodesic_to_waveform,
    export_wav,
    compute_harmonic_fingerprint,
    RealTimeRenderer,
)

__all__ = [
    # === Dual Lattice ===
    "SacredTongue",
    "FluxState",
    "LatticeVector",
    "TongueContext",
    "CrossStitchPattern",
    "KyberTongueEncryptor",
    "DilithiumTongueSigner",
    "DualLatticeCrossStitch",
    "TongueLatticeGovernor",
    "TONGUE_PHASES",
    "TONGUE_WEIGHTS",
    "PHI",
    # === Symphonic Cipher ===
    "SymphonicToken",
    "TonguePolarity",
    "SACRED_TONGUE_VOCAB",
    "BASE_FREQ",
    "FREQ_STEP",
    "token_to_frequency",
    "id_to_frequency",
    "generate_tone",
    "generate_symphonic_sequence",
    "analyze_polarity_balance",
    # === GeoSeal ===
    "ContextVector",
    "SecurityPosture",
    "bytes_to_signed_signal",
    "signed_signal_to_bytes",
    "hyperbolic_distance",
    "hyperbolic_midpoint",
    "hyperbolic_angle",
    "compute_triangle_deficit",
    "harmonic_wall_cost",
    "trust_from_position",
    # === Signed Lattice Bridge ===
    "SignedGovernanceResult",
    "SignedLatticeBridge",
    # === Hyperbolic Octree ===
    "OctreeNode",
    "HyperbolicOctree",
    # === Hyperpath Finder ===
    "HyperpathFinder",
    "PathResult",
    "hyperbolic_distance_safe",
    # === Visualization ===
    "classical_mds",
    "poincare_geodesic",
    "visualize_poincare_disk",
    "visualize_3d_voxels",
]

__version__ = "3.0.0"

