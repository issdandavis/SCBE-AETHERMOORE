"""
SCBE-AETHERMOORE: Phase-Breath Hyperbolic Governance System
============================================================

A 9D Quantum Hyperbolic Manifold Memory for AI governance where:
- Truthful actions trace smooth geodesics
- Lies/threats manifest as geometric discontinuities (snaps)
- Governance is geometric shape, not rule-based policy

Architecture (v2.1):
    Input State ξ(t)
         │
    ┌────▼────┐
    │ 9D State │  (context, tau, eta, quantum)
    └────┬────┘
         │
    ┌────▼────┐
    │ Harmonic │  (phase modulation, conlang encoding)
    │ Cipher   │
    └────┬────┘
         │
    ┌────▼────┐
    │ QASI    │  (Poincaré embed → hyperbolic distance → realm)
    │ Core    │
    └────┬────┘
         │
    ┌────▼────────┐
    │ L1-L3.5-L14 │  (coherence → quasicrystal → risk → scaling)
    │ Pipeline    │
    └────┬────────┘
         │
    ┌────▼────┐
    │ CPSE    │  (Lorentz throttling, soliton dynamics, spin)
    │ Physics │
    └────┬────┘
         │
    ┌────▼────┐
    │ Grok    │  (truth-seeking tie-breaker if marginal)
    │ Oracle  │
    └────┬────┘
         │
    ┌────▼────┐
    │ Decision│  → ALLOW / QUARANTINE / DENY
    └─────────┘

Core Components:
- production_v2_1.py: Complete v2.1 system with CPSE Physics Engine
- unified.py: Legacy 9D system with all integrations
- full_system.py: End-to-end governance with 14-layer pipeline
- qasi_core.py: Axiom-verified SCBE primitives
- cpse.py: Cryptographic Physics Simulation Engine
- layer_tests.py: Comprehensive 61-test validation suite
- mass_system_grok.py: Grok-integrated mass governance

Subdirectories:
- manifold/: Hyper-torus geometry
- governance/: Phase-breath transforms and snap protocol
- quantum/: PQC integration via liboqs
- layers/: 14-layer mapping system
- pqc/: Post-Quantum Cryptography (Kyber768 + Dilithium3)
- qc_lattice/: Quasicrystal Lattice + PHDM (16 polyhedra)
- spiral_seal/: SpiralSeal SS1 encryption with Sacred Tongues

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

# QASI Core - Quantized/Quasi-Adaptive Security Interface
from .qasi_core import (
    realify,
    complex_norm,
    apply_spd_weights,
    poincare_embed,
    clamp_ball,
    mobius_add,
    phase_transform,
    breathing_transform,
    realm_distance,
    spectral_stability,
    spin_coherence,
    harmonic_scaling as qasi_harmonic_scaling,
    risk_base,
    risk_prime,
    decision_from_risk,
    RiskWeights,
    self_test as qasi_self_test,
)

# PHDM - Polyhedral Hamiltonian Defense Manifold (Claims 63-80)
from .phdm_module import (
    # Polyhedra definitions
    POLYHEDRA as CANONICAL_POLYHEDRA,
    HAMILTONIAN_PATH,
    Polyhedron as PHDMPolyhedron,

    # Core classes
    GeodesicCurve,
    IntrusionDetector,

    # Key derivation
    hmac_key_chain as derive_phdm_key_chain,
    derive_session_key,
    create_golden_path,
    compute_phdm_subscore as phdm_subscore,

    # Integration helpers
    integrate_with_layer1,
    integrate_with_layer7_swarm,
    integrate_with_layer13_risk,

    # Self-test
    self_test as phdm_self_test,
)

# PQC - Post-Quantum Cryptography (Claims 2-3)
from .pqc_module import (
    # Interfaces
    KEMInterface,
    SignatureInterface,

    # Implementations
    SimulatedKEM,
    SimulatedSignature,

    # High-level API
    PQCKeyPair,
    PQCEnvelope,
    PQCManager,

    # Factory functions
    get_kem,
    get_signature,

    # Self-test
    self_test as pqc_self_test,
)

# Organic Hyperbolic Embeddings - Unified 4-Pillar System
from .organic_hyperbolic import (
    # Pillar 1: Input
    InputEncoder,

    # Pillar 2: State
    State9D as OrganicState9D,
    StateGenerator,

    # Pillar 3: Hyperbolic
    HyperbolicEngine,

    # Pillar 4: Governance
    RealmConfig,
    GovernanceEngine,

    # Integrated System
    OrganicSCBE,

    # Self-test
    self_test as organic_self_test,
)

# Layers 9-12: Signal Aggregation Pillar
from .layers_9_12 import (
    # Layer 9: Spectral Coherence
    SpectralAnalysis,
    compute_spectral_coherence,
    spectral_stability,

    # Layer 10: Spin Coherence
    SpinAnalysis,
    compute_spin_coherence,
    compute_spin_from_signal,

    # Layer 11: Triadic Distance
    TriadicWeights,
    TriadicAnalysis,
    compute_triadic_distance,
    triadic_gradient,

    # Layer 12: Harmonic Scaling & Risk
    RiskWeights as L12RiskWeights,
    RiskAnalysis,
    harmonic_scaling as l12_harmonic_scaling,
    compute_risk,
    risk_gradient,

    # Integrated Pipeline
    AggregatedSignals,
    process_layers_9_12,

    # Self-test
    self_test as layers_9_12_self_test,
)

# Layer 13: Risk Decision Engine (Lemma 13.1)
from .layer_13 import (
    # Decision enum
    Decision,

    # Harmonic scaling (Lemma 13.1)
    HarmonicParams,
    harmonic_H,
    harmonic_derivative,
    harmonic_vertical_wall,

    # Multipliers
    TimeMultiplier,
    IntentMultiplier,

    # Composite Risk
    RiskComponents,
    CompositeRisk,
    compute_composite_risk,
    verify_north_star,

    # Decision Response
    DecisionResponse,
    execute_decision,
    batch_evaluate,

    # Verification
    verify_lemma_13_1,
    self_test as layer_13_self_test,
)

# Living Metric Engine: Tensor Heartbeat / Claim 61
from .living_metric import (
    # States
    PressureState,

    # Shock Absorber
    ShockAbsorberParams,
    shock_absorber,
    shock_absorber_derivative,

    # Pressure
    PressureMetrics,
    compute_pressure,

    # Living Metric Engine
    MetricResult,
    LivingMetricEngine,

    # Anti-fragile
    AntifragileAnalysis,
    verify_antifragile,

    # Integration
    integrate_with_risk_engine,

    # Self-test
    self_test as living_metric_self_test,
)

# Fractional Dimension Flux: Claim 16
from .fractional_flux import (
    # States
    ParticipationState,

    # Parameters
    FluxParams,
    FluxState,

    # Engine
    FractionalFluxEngine,

    # Weighting
    compute_weighted_metric,
    compute_weighted_distance,

    # Snap detection
    SnapResult,
    detect_snap,

    # Integration
    integrate_with_living_metric,

    # Breathing patterns
    BreathingPattern,
    apply_breathing_pattern,

    # Self-test
    self_test as fractional_flux_self_test,
)

# Production v2.1 - Complete System with CPSE Physics Engine
from .production_v2_1 import (
    # Quasicrystal Lattice (L3.5)
    QuasicrystalLattice,

    # CPSE Physics Engine
    SolitonPacket,
    CPSEThrottler,
    lorentz_factor as cpse_lorentz_factor,
    compute_latency_delay as cpse_latency_delay,
    soliton_evolve,
    spin_rotation_matrix,
    flux_jitter,

    # State & Governance
    State9D as ProductionState9D,
    Polyhedron as ProductionPolyhedron,
    GrokResult,
    GovernanceResult,
    governance_pipeline,

    # Byzantine Resistance
    SwarmAgent,
    simulate_byzantine_attack,

    # Testing
    self_test as production_self_test,
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

    # SpiralSeal SS1 (Sacred Tongue Encryption)
    "SpiralSeal",
    "VeiledSeal",
    "PQCSpiralSeal",
    "SpiralSealResult",
    "quick_seal",
    "quick_unseal",
    "SacredTongue",
    "SacredTongueTokenizer",
    # QASI Core
    "realify",
    "complex_norm",
    "apply_spd_weights",
    "poincare_embed",
    "clamp_ball",
    "mobius_add",
    "phase_transform",
    "breathing_transform",
    "realm_distance",
    "spectral_stability",
    "spin_coherence",
    "qasi_harmonic_scaling",
    "risk_base",
    "risk_prime",
    "decision_from_risk",
    "RiskWeights",
    "qasi_self_test",

    # Production v2.1 - Quasicrystal (L3.5)
    "QuasicrystalLattice",

    # Production v2.1 - CPSE Physics Engine
    "SolitonPacket",
    "CPSEThrottler",
    "cpse_lorentz_factor",
    "cpse_latency_delay",
    "soliton_evolve",
    "spin_rotation_matrix",
    "flux_jitter",

    # Production v2.1 - Governance
    "ProductionState9D",
    "ProductionPolyhedron",
    "GrokResult",
    "GovernanceResult",
    "governance_pipeline",

    # Production v2.1 - Byzantine
    "SwarmAgent",
    "simulate_byzantine_attack",
    "production_self_test",

    # PHDM - Polyhedral Hamiltonian Defense Manifold (Claims 63-80)
    "CANONICAL_POLYHEDRA",
    "HAMILTONIAN_PATH",
    "PHDMPolyhedron",
    "GeodesicCurve",
    "IntrusionDetector",
    "derive_phdm_key_chain",
    "derive_session_key",
    "create_golden_path",
    "phdm_subscore",
    "integrate_with_layer1",
    "integrate_with_layer7_swarm",
    "integrate_with_layer13_risk",
    "phdm_self_test",

    # PQC - Post-Quantum Cryptography (Claims 2-3)
    "KEMInterface",
    "SignatureInterface",
    "SimulatedKEM",
    "SimulatedSignature",
    "PQCKeyPair",
    "PQCEnvelope",
    "PQCManager",
    "get_kem",
    "get_signature",
    "pqc_self_test",

    # Organic Hyperbolic Embeddings
    "InputEncoder",
    "OrganicState9D",
    "StateGenerator",
    "HyperbolicEngine",
    "GovernanceDecision",
    "RealmConfig",
    "GovernanceEngine",
    "OrganicSCBE",
    "organic_self_test",

    # Layers 9-12: Signal Aggregation Pillar
    "SpectralAnalysis",
    "compute_spectral_coherence",
    "spectral_stability",
    "SpinAnalysis",
    "compute_spin_coherence",
    "compute_spin_from_signal",
    "TriadicWeights",
    "TriadicAnalysis",
    "compute_triadic_distance",
    "triadic_gradient",
    "L12RiskWeights",
    "RiskAnalysis",
    "l12_harmonic_scaling",
    "compute_risk",
    "risk_gradient",
    "AggregatedSignals",
    "process_layers_9_12",
    "layers_9_12_self_test",

    # Layer 13: Risk Decision Engine (Lemma 13.1)
    "Decision",
    "HarmonicParams",
    "harmonic_H",
    "harmonic_derivative",
    "harmonic_vertical_wall",
    "TimeMultiplier",
    "IntentMultiplier",
    "RiskComponents",
    "CompositeRisk",
    "compute_composite_risk",
    "verify_north_star",
    "DecisionResponse",
    "execute_decision",
    "batch_evaluate",
    "verify_lemma_13_1",
    "layer_13_self_test",

    # Living Metric Engine: Tensor Heartbeat / Claim 61
    "PressureState",
    "ShockAbsorberParams",
    "shock_absorber",
    "shock_absorber_derivative",
    "PressureMetrics",
    "compute_pressure",
    "MetricResult",
    "LivingMetricEngine",
    "AntifragileAnalysis",
    "verify_antifragile",
    "integrate_with_risk_engine",
    "living_metric_self_test",

    # Fractional Dimension Flux: Claim 16
    "ParticipationState",
    "FluxParams",
    "FluxState",
    "FractionalFluxEngine",
    "compute_weighted_metric",
    "compute_weighted_distance",
    "SnapResult",
    "detect_snap",
    "integrate_with_living_metric",
    "BreathingPattern",
    "apply_breathing_pattern",
    "fractional_flux_self_test",
]

# SpiralSeal SS1 - Sacred Tongue Encryption Envelope
try:
    from .spiral_seal import (
        SpiralSeal,
        VeiledSeal,
        PQCSpiralSeal,
        SpiralSealResult,
        quick_seal,
        quick_unseal,
        SacredTongue,
        SacredTongueTokenizer,
    )
except ImportError:
    # Graceful degradation if spiral_seal not available
    SpiralSeal = None
    VeiledSeal = None
    PQCSpiralSeal = None
    SpiralSealResult = None
    quick_seal = None
    quick_unseal = None
    SacredTongue = None
    SacredTongueTokenizer = None

# AETHERMOORE Core Constants
from .constants import (
    # Mathematical Constants
    PI, E, PHI as PHI_GOLDEN, SQRT2, SQRT5,
    # Harmonic Ratios
    R_FIFTH, R_FOURTH, R_THIRD, R_SIXTH, R_OCTAVE, R_PHI,
    # AETHERMOORE Constants
    PHI_AETHER, LAMBDA_ISAAC, OMEGA_SPIRAL, ALPHA_ABH,
    # Physical Constants
    C_LIGHT, PLANCK_LENGTH, PLANCK_TIME, PLANCK_CONSTANT,
    # Defaults
    DEFAULT_R, DEFAULT_D_MAX, DEFAULT_L, DEFAULT_TOLERANCE, DEFAULT_BASE_BITS,
    # Core Functions
    harmonic_scale, security_bits, security_level, harmonic_distance, octave_transpose,
    # Data Types
    AethermooreDimension, DIMENSIONS, CONSTANTS,
    # Reference
    get_harmonic_scale_table, HARMONIC_SCALE_TABLE,
)

# HAL-Attention (Harmonic Associative Lattice)
from .hal_attention import (
    HALConfig,
    AttentionOutput,
    harmonic_coupling_matrix,
    assign_dimension_depths,
    hal_attention,
    multi_head_hal_attention,
    HALAttentionLayer,
)

# Vacuum-Acoustics Kernel
from .vacuum_acoustics import (
    VacuumAcousticsConfig,
    WaveSource,
    FluxResult,
    BottleBeamResult,
    nodal_surface,
    check_cymatic_resonance,
    bottle_beam_intensity,
    flux_redistribution,
    is_on_nodal_line,
    find_nodal_points,
    compute_chladni_pattern,
    resonance_strength,
    create_bottle_beam_sources,
    analyze_bottle_beam,
)

# Cymatic Voxel Storage
from .cymatic_storage import (
    StorageMode,
    Voxel,
    KDTree,
    HolographicQRCube,
)

# Extend __all__ with new AETHERMOORE modules
__all__.extend([
    # Constants
    "PI", "E", "PHI_GOLDEN", "SQRT2", "SQRT5",
    "R_FIFTH", "R_FOURTH", "R_THIRD", "R_SIXTH", "R_OCTAVE", "R_PHI",
    "PHI_AETHER", "LAMBDA_ISAAC", "OMEGA_SPIRAL", "ALPHA_ABH",
    "C_LIGHT", "PLANCK_LENGTH", "PLANCK_TIME", "PLANCK_CONSTANT",
    "DEFAULT_R", "DEFAULT_D_MAX", "DEFAULT_L", "DEFAULT_TOLERANCE", "DEFAULT_BASE_BITS",
    "harmonic_scale", "security_bits", "security_level", "harmonic_distance", "octave_transpose",
    "AethermooreDimension", "DIMENSIONS", "CONSTANTS",
    "get_harmonic_scale_table", "HARMONIC_SCALE_TABLE",
    # HAL-Attention
    "HALConfig", "AttentionOutput",
    "harmonic_coupling_matrix", "assign_dimension_depths",
    "hal_attention", "multi_head_hal_attention", "HALAttentionLayer",
    # Vacuum-Acoustics
    "VacuumAcousticsConfig", "WaveSource", "FluxResult", "BottleBeamResult",
    "nodal_surface", "check_cymatic_resonance", "bottle_beam_intensity",
    "flux_redistribution", "is_on_nodal_line", "find_nodal_points",
    "compute_chladni_pattern", "resonance_strength", "create_bottle_beam_sources", "analyze_bottle_beam",
    # Cymatic Storage
    "StorageMode", "Voxel", "KDTree", "HolographicQRCube",
])
