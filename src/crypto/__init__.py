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

Heavy modules (numpy, scipy, matplotlib) are lazy-loaded to avoid import failures
when these dependencies are not installed.
"""

import importlib as _importlib
from typing import TYPE_CHECKING

# ═══════════════════════════════════════════════════════════
# Eager imports — modules with no heavy dependencies
# ═══════════════════════════════════════════════════════════

# Sacred Eggs (Cryptographic Secret Containers — no numpy)
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

# ═══════════════════════════════════════════════════════════
# Lazy imports — heavy modules (scipy, matplotlib)
# These are loaded on first access, not at import time.
# ═══════════════════════════════════════════════════════════

# Module-level lazy loader
_LAZY_MODULES = {
    # Dual Lattice (numpy — not always installed)
    "SacredTongue": ".dual_lattice",
    "FluxState": ".dual_lattice",
    "LatticeVector": ".dual_lattice",
    "TongueContext": ".dual_lattice",
    "CrossStitchPattern": ".dual_lattice",
    "KyberTongueEncryptor": ".dual_lattice",
    "DilithiumTongueSigner": ".dual_lattice",
    "DualLatticeCrossStitch": ".dual_lattice",
    "TongueLatticeGovernor": ".dual_lattice",
    "TONGUE_PHASES": ".dual_lattice",
    "TONGUE_WEIGHTS": ".dual_lattice",
    "PHI": ".dual_lattice",
    # Symphonic Cipher (numpy)
    "SymphonicToken": ".symphonic_cipher",
    "TonguePolarity": ".symphonic_cipher",
    "SACRED_TONGUE_VOCAB": ".symphonic_cipher",
    "BASE_FREQ": ".symphonic_cipher",
    "FREQ_STEP": ".symphonic_cipher",
    "token_to_frequency": ".symphonic_cipher",
    "id_to_frequency": ".symphonic_cipher",
    "generate_tone": ".symphonic_cipher",
    "generate_symphonic_sequence": ".symphonic_cipher",
    "analyze_polarity_balance": ".symphonic_cipher",
    # GeoSeal (numpy)
    "ContextVector": ".geo_seal",
    "SecurityPosture": ".geo_seal",
    "bytes_to_signed_signal": ".geo_seal",
    "signed_signal_to_bytes": ".geo_seal",
    "hyperbolic_distance": ".geo_seal",
    "hyperbolic_midpoint": ".geo_seal",
    "hyperbolic_angle": ".geo_seal",
    "compute_triangle_deficit": ".geo_seal",
    "harmonic_wall_cost": ".geo_seal",
    "trust_from_position": ".geo_seal",
    # Signed Lattice Bridge (numpy)
    "SignedGovernanceResult": ".signed_lattice_bridge",
    "SignedLatticeBridge": ".signed_lattice_bridge",
    # Hyperbolic Octree (numpy)
    "SpectralVoxel": ".octree",
    "OctreeNode": ".octree",
    "HyperbolicOctree": ".octree",
    # Hyperpath Finder (numpy)
    "HyperpathFinder": ".hyperpath_finder",
    "PathResult": ".hyperpath_finder",
    "hyperbolic_distance_safe": ".hyperpath_finder",
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
                f"This module may require numpy, scipy, or matplotlib."
            ) from e
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__version__ = "3.3.0"
