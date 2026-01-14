"""
SCBE-AETHERMOORE: Phase-Breath Hyperbolic Governance System

A 9D Quantum Hyperbolic Manifold Memory for AI governance where:
- Truthful actions trace smooth geodesics
- Lies/threats manifest as geometric discontinuities (snaps)
- Governance is geometric shape, not rule-based policy

Core Components:
- unified.py: Complete 9D system with all integrations
- manifold/: Hyper-torus geometry
- governance/: Phase-breath transforms and snap protocol
- quantum/: PQC integration via liboqs
- layers/: 14-layer mapping system

Central Thesis:
    AI safety = geometric + temporal + entropic + quantum continuity
    Invalid states physically cannot exist on the manifold
"""

__version__ = "1.0.0"
__author__ = "SCBE-AETHERMOORE"

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
    # Main system
    "SCBEAethermoore",
    "State9D",
    "GovernanceDecision",
    "Polyhedron",

    # Core functions
    "governance_9d",
    "generate_context",
    "compute_entropy",

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
    "KAPPA_MAX",
    "LAMBDA_BOUND",
    "H_MAX",
    "TONGUES",
    "TONGUE_WEIGHTS",
    "CONLANG",
    "REV_CONLANG",
    "MODALITY_MASKS",
]
