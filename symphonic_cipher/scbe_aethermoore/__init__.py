"""
SCBE-AETHERMOORE: Phase-Breath Hyperbolic Governance System

A 9D Quantum Hyperbolic Manifold Memory for AI governance where:
- Truthful actions trace smooth geodesics
- Lies/threats manifest as geometric discontinuities (snaps)
- Governance is geometric shape, not rule-based policy

Core Components:
- unified.py: Complete 9D system with all integrations
- full_system.py: End-to-end governance with 14-layer pipeline
- manifold/: Hyper-torus geometry
- governance/: Phase-breath transforms and snap protocol
- quantum/: PQC integration via liboqs
- layers/: 14-layer mapping system

Central Thesis:
    AI safety = geometric + temporal + entropic + quantum continuity
    Invalid states physically cannot exist on the manifold
"""

__version__ = "2.1.0"
__author__ = "SCBE-AETHERMOORE"

# CPSE - Cryptographic Physics Simulation Engine
from .cpse import (
    CPSEEngine,
    CPSEState,
    VirtualGravityThrottler,
    FluxGenerator,
    # Metric Tensor
    build_metric_tensor,
    metric_distance,
    behavioral_cost,
    # Harmonic Scaling
    harmonic_cost,
    security_level_cost,
    # Virtual Gravity
    lorentz_factor,
    compute_latency_delay,
    # Soliton
    soliton_evolution,
    soliton_stability,
    compute_soliton_key,
    # Spin Rotation
    rotation_matrix_2d,
    rotation_matrix_nd,
    context_spin_angles,
    spin_transform,
    spin_mismatch,
    # Flux
    flux_noise,
    jittered_target,
)

# Full System (recommended entry point)
from .full_system import (
    SCBEFullSystem,
    GovernanceMode,
    GovernanceMetrics,
    SystemState,
    quick_evaluate,
    verify_all_theorems,
)

from .unified import (
    # Main system class
    SCBEAethermoore,

    # State representation
    State9D,
    GovernanceDecision,
    Polyhedron,

    # Core functions
    governance_9d,
    generate_context,
    compute_entropy,

    # Extended Entropy Math (negentropy support)
    compute_negentropy,
    compute_relative_entropy,
    compute_mutual_information,
    entropy_rate_estimate,
    fisher_information,

    # Time axis
    tau_dot,
    tau_curvature,

    # Entropy axis
    eta_dot,
    eta_curvature,

    # Quantum dimension
    quantum_evolution,
    quantum_fidelity,
    von_neumann_entropy,

    # Geometry
    ManifoldController,
    hyperbolic_distance,
    triadic_distance,
    harmonic_scaling,
    stable_hash,

    # PHDM
    hamiltonian_path_deviation,

    # Signal processing
    phase_modulated_intent,
    extract_phase,

    # HMAC chain
    hmac_chain_tag,
    verify_hmac_chain,

    # Constants
    PHI,
    EPSILON,
    TAU_COH,
    ETA_TARGET,
    ETA_MIN,
    ETA_MAX,
    ETA_NEGENTROPY_THRESHOLD,
    ETA_HIGH_ENTROPY_THRESHOLD,
    KAPPA_MAX,
    LAMBDA_BOUND,
    H_MAX,
    TONGUES,
    TONGUE_WEIGHTS,
    CONLANG,
    REV_CONLANG,
    MODALITY_MASKS,
)

__all__ = [
    # CPSE - Cryptographic Physics Simulation Engine
    "CPSEEngine",
    "CPSEState",
    "VirtualGravityThrottler",
    "FluxGenerator",
    "build_metric_tensor",
    "metric_distance",
    "behavioral_cost",
    "harmonic_cost",
    "security_level_cost",
    "lorentz_factor",
    "compute_latency_delay",
    "soliton_evolution",
    "soliton_stability",
    "compute_soliton_key",
    "rotation_matrix_2d",
    "rotation_matrix_nd",
    "context_spin_angles",
    "spin_transform",
    "spin_mismatch",
    "flux_noise",
    "jittered_target",

    # Full System (recommended entry point)
    "SCBEFullSystem",
    "GovernanceMode",
    "GovernanceMetrics",
    "SystemState",
    "quick_evaluate",
    "verify_all_theorems",

    # Legacy system
    "SCBEAethermoore",
    "State9D",
    "GovernanceDecision",
    "Polyhedron",

    # Core functions
    "governance_9d",
    "generate_context",
    "compute_entropy",

    # Extended Entropy Math (negentropy support)
    "compute_negentropy",
    "compute_relative_entropy",
    "compute_mutual_information",
    "entropy_rate_estimate",
    "fisher_information",

    # Time
    "tau_dot",
    "tau_curvature",

    # Entropy
    "eta_dot",
    "eta_curvature",

    # Quantum
    "quantum_evolution",
    "quantum_fidelity",
    "von_neumann_entropy",

    # Geometry
    "ManifoldController",
    "hyperbolic_distance",
    "triadic_distance",
    "harmonic_scaling",
    "stable_hash",

    # PHDM
    "hamiltonian_path_deviation",

    # Signal
    "phase_modulated_intent",
    "extract_phase",

    # HMAC
    "hmac_chain_tag",
    "verify_hmac_chain",

    # Constants
    "PHI",
    "EPSILON",
    "TAU_COH",
    "ETA_TARGET",
    "ETA_MIN",
    "ETA_MAX",
    "ETA_NEGENTROPY_THRESHOLD",
    "ETA_HIGH_ENTROPY_THRESHOLD",
    "KAPPA_MAX",
    "LAMBDA_BOUND",
    "H_MAX",
    "TONGUES",
    "TONGUE_WEIGHTS",
    "CONLANG",
    "REV_CONLANG",
    "MODALITY_MASKS",
]
