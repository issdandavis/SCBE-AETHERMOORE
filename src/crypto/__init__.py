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
- h_lwe: Hyperbolic LWE vector encryption (Poincaré ball containment)
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

# Hyperbolic Octree (Sparse Voxel Storage + Spectral Clustering)
from .octree import (
    SpectralVoxel,
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

# H-LWE (Hyperbolic LWE Vector Encryption)
from .h_lwe import (
    HLWESymmetric,
    HLWECiphertext,
    ContainmentBreach,
    InvalidVector,
    AuthenticationError,
    HLWEError,
    exp_map_zero,
    log_map_zero,
    mobius_add,
    mobius_neg,
    project_to_ball as hlwe_project_to_ball,
    key_vector_from_secret,
)

# Dual Lattice 14-Layer Integration (requires scipy — lazy import)
try:
    from .dual_lattice_integration import (
        # Layer 1: PQC Gating
        authorize_pqc_level,
        build_lattice_point_gated,
        # Layer 2-4: Projection
        GeoContext,
        RealmType,
        realify_with_sign,
        project_to_poincare_with_realm,
        layers_2_4_process,
        # Layer 5: Governance Distance
        governance_aware_distance,
        layer_5_evaluate,
        # Layer 6-7: Breathing
        breathing_transform,
        apply_realm_breathing,
        # Layer 8: Clustering
        hierarchical_realm_clustering,
        layer_8_cluster,
        # Layer 9-11: Path Validation
        spectral_coherence,
        triadic_temporal_distance,
        validate_hyperpath,
        # Layer 12-13: Harmonic Scaling
        harmonic_scaling,
        compute_path_cost,
        layer_12_13_evaluate,
        # Layer 14: Sonification
        coord_to_frequency,
        hyperpath_to_audio,
        layer_14_sonify,
        # Complete Integrator
        DualLatticeIntegrator,
        IntegratedResult,
        LayerDecision,
    )
except ImportError:
    pass  # scipy not available — dual lattice integration disabled

# Sacred Eggs (Cryptographic Secret Containers)
from .sacred_eggs import (
    SacredEgg,
    EggCarton,
    EggRing,
    SacredRituals,
    IncubationResult,
    TriadicBindingResult,
    RingDescentResult,
    FailToNoiseResult,
    flux_state_to_ring,
    create_session_egg,
    ring_allows,
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
    "SpectralVoxel",
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
    # === 14-Layer Integration ===
    "authorize_pqc_level",
    "build_lattice_point_gated",
    "GeoContext",
    "RealmType",
    "realify_with_sign",
    "project_to_poincare_with_realm",
    "layers_2_4_process",
    "governance_aware_distance",
    "layer_5_evaluate",
    "breathing_transform",
    "apply_realm_breathing",
    "hierarchical_realm_clustering",
    "layer_8_cluster",
    "spectral_coherence",
    "triadic_temporal_distance",
    "validate_hyperpath",
    "harmonic_scaling",
    "compute_path_cost",
    "layer_12_13_evaluate",
    "coord_to_frequency",
    "hyperpath_to_audio",
    "layer_14_sonify",
    "DualLatticeIntegrator",
    "IntegratedResult",
    "LayerDecision",
    # === H-LWE ===
    "HLWESymmetric",
    "HLWECiphertext",
    "ContainmentBreach",
    "InvalidVector",
    "AuthenticationError",
    "HLWEError",
    "exp_map_zero",
    "log_map_zero",
    "mobius_add",
    "mobius_neg",
    "hlwe_project_to_ball",
    "key_vector_from_secret",
    # === Sacred Eggs ===
    "SacredEgg",
    "EggCarton",
    "EggRing",
    "SacredRituals",
    "IncubationResult",
    "TriadicBindingResult",
    "RingDescentResult",
    "FailToNoiseResult",
    "flux_state_to_ring",
    "create_session_egg",
    "ring_allows",
]

__version__ = "3.2.5"  # Bumped for H-LWE vector encryption

