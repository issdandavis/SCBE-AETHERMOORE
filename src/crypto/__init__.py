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

Heavy modules (scipy, matplotlib) are lazy-loaded to avoid import hangs on Windows.
"""

import importlib as _importlib
from typing import TYPE_CHECKING

# ═══════════════════════════════════════════════════════════
# Eager imports — lightweight modules first, numpy-dependent guarded
# ═══════════════════════════════════════════════════════════

# Sacred Eggs (hashlib/hmac only — no numpy)
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

# Guard numpy-dependent modules so the package still loads without numpy
# (e.g. when only sacred_tongues tokenizer is needed).
try:
    # Dual Lattice (Kyber/Dilithium + Sacred Tongues)
    from .dual_lattice import (
        SacredTongue,
        FluxState,
        LatticeVector,
        TongueContext,
        CrossStitchPattern,
        KyberTongueEncryptor,
        DilithiumTongueSigner,
        DualLatticeCrossStitch,
        TongueLatticeGovernor,
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
except ImportError:
    # numpy (or another native dep) is not installed — degrade gracefully.
    # Callers that need these symbols will get an ImportError on direct use.
    pass

# ═══════════════════════════════════════════════════════════
# Lazy imports — heavy modules (scipy, matplotlib)
# These are loaded on first access, not at import time.
# ═══════════════════════════════════════════════════════════

# Module-level lazy loader
_LAZY_MODULES = {
    # Visualization (matplotlib)
    "classical_mds": ".hyperbolic_viz",
    "poincare_geodesic": ".hyperbolic_viz",
    "visualize_poincare_disk": ".hyperbolic_viz",
    "visualize_3d_voxels": ".hyperbolic_viz",
    # Symphonic Waveform (scipy.io.wavfile)
    "SymphonicIntent": ".symphonic_waveform",
    "HarmonicFingerprint": ".symphonic_waveform",
    "position_to_intent": ".symphonic_waveform",
    "hyperpath_to_intents": ".symphonic_waveform",
    "hyperpath_to_waveform": ".symphonic_waveform",
    "geodesic_to_waveform": ".symphonic_waveform",
    "export_wav": ".symphonic_waveform",
    "compute_harmonic_fingerprint": ".symphonic_waveform",
    "RealTimeRenderer": ".symphonic_waveform",
    # Dual Lattice 14-Layer Integration (scipy.cluster, scipy.spatial)
    "authorize_pqc_level": ".dual_lattice_integration",
    "build_lattice_point_gated": ".dual_lattice_integration",
    "GeoContext": ".dual_lattice_integration",
    "RealmType": ".dual_lattice_integration",
    "realify_with_sign": ".dual_lattice_integration",
    "project_to_poincare_with_realm": ".dual_lattice_integration",
    "layers_2_4_process": ".dual_lattice_integration",
    "governance_aware_distance": ".dual_lattice_integration",
    "layer_5_evaluate": ".dual_lattice_integration",
    "breathing_transform": ".dual_lattice_integration",
    "apply_realm_breathing": ".dual_lattice_integration",
    "hierarchical_realm_clustering": ".dual_lattice_integration",
    "layer_8_cluster": ".dual_lattice_integration",
    "spectral_coherence": ".dual_lattice_integration",
    "triadic_temporal_distance": ".dual_lattice_integration",
    "validate_hyperpath": ".dual_lattice_integration",
    "harmonic_scaling": ".dual_lattice_integration",
    "compute_path_cost": ".dual_lattice_integration",
    "layer_12_13_evaluate": ".dual_lattice_integration",
    "coord_to_frequency": ".dual_lattice_integration",
    "hyperpath_to_audio": ".dual_lattice_integration",
    "layer_14_sonify": ".dual_lattice_integration",
    "DualLatticeIntegrator": ".dual_lattice_integration",
    "IntegratedResult": ".dual_lattice_integration",
    "LayerDecision": ".dual_lattice_integration",
    # Quasicrystal Lattice (scipy.fft)
    "QuasicrystalLattice": ".quasicrystal_lattice",
    "LatticePoint": ".quasicrystal_lattice",
    "DefectReport": ".quasicrystal_lattice",
    "fibonacci_gates": ".quasicrystal_lattice",
    "tongue_fibonacci_gates": ".quasicrystal_lattice",
}


def __getattr__(name: str):
    """Lazy-load heavy modules on first attribute access."""
    if name in _LAZY_MODULES:
        module_path = _LAZY_MODULES[name]
        try:
            mod = _importlib.import_module(module_path, package=__name__)
            return getattr(mod, name)
        except (ImportError, AttributeError) as e:
            raise ImportError(
                f"Cannot import {name} from {module_path}: {e}. "
                f"This module requires scipy or matplotlib."
            ) from e
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__version__ = "3.3.0"
