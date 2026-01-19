/**
 * SCBE Harmonic Module
 *
 * Complete TypeScript implementation of the SCBE 14-layer hyperbolic
 * governance pipeline, including:
 *
 * - Layer 5: Invariant Hyperbolic Metric
 * - Layer 6: Breath Transform
 * - Layer 7: Phase Modulation
 * - Layer 8: Multi-Well Potential / SpiralSeal SS1 Envelope Encoding
 * - Layer 12: Harmonic Scaling H(d, R) = R^(d²)
 * - Layer 14: Audio Axis / Vacuum Acoustics
 *
 * Plus: Langues Metric, HAL Attention, Hamiltonian CFI, Sacred Tongue Tokenizer
 *
 * @module harmonic
 */

// ═══════════════════════════════════════════════════════════════
// Constants and Types
// ═══════════════════════════════════════════════════════════════

export {
    CONSTANTS, type Tensor2D,
    type Tensor3D, type Vector3D,
    type Vector6D
} from './constants.js';

export { assertFinite, assertIntGE, log2 } from './assertions.js';

// ═══════════════════════════════════════════════════════════════
// Layer 12: Harmonic Scaling
// ═══════════════════════════════════════════════════════════════

export {
    harmonicDistance, harmonicScale, octaveTranspose, securityBits,
    securityLevel
} from './harmonicScaling.js';

// ═══════════════════════════════════════════════════════════════
// HAL - Harmonic Attention Layer
// ═══════════════════════════════════════════════════════════════

export {
    halAttention, harmonicCouplingMatrix, type HALConfig
} from './halAttention.js';

// ═══════════════════════════════════════════════════════════════
// Layer 14: Vacuum-Acoustics Kernel
// ═══════════════════════════════════════════════════════════════

export {
    bottleBeamIntensity, cavityResonance, checkCymaticResonance, fluxRedistribution, nodalSurface, standingWaveAmplitude, type AcousticSource, type VacuumAcousticsConfig
} from './vacuumAcoustics.js';

// ═══════════════════════════════════════════════════════════════
// Langues Metric - 6D Governance Cost Function
// ═══════════════════════════════════════════════════════════════

export {
    FluxingLanguesMetric, LanguesMetric, TONGUES, getFluxState, type Decision,
    type DimensionFlux, type FluxState, type LanguesMetricConfig, type Tongue
} from './languesMetric.js';

// ═══════════════════════════════════════════════════════════════
// Layer 14: Audio Axis (FFT Telemetry)
// ═══════════════════════════════════════════════════════════════

export {
    AudioAxisProcessor, generateNoise, generateTestSignal, type AudioAxisConfig, type AudioFeatures
} from './audioAxis.js';

// ═══════════════════════════════════════════════════════════════
// Hamiltonian CFI - Control Flow Integrity
// ═══════════════════════════════════════════════════════════════

export {
    ControlFlowGraph,
    HamiltonianCFI,
    createVertex, type BipartiteResult, type CFGVertex, type CFIResult, type HamiltonianCheck
} from './hamiltonianCFI.js';

// ═══════════════════════════════════════════════════════════════
// Layers 5-8: Hyperbolic Geometry (Poincaré Ball)
// ═══════════════════════════════════════════════════════════════

export {

    // Pipeline utility
    applyHyperbolicPipeline, breathTransform, expMap0,
    // Layer 5: Invariant Metric
    hyperbolicDistance, inverseBreathTransform, logMap0, mobiusAdd, multiPhaseModulation, multiWellGradient, multiWellPotential,
    // Layer 7: Phase Modulation
    phaseModulation, projectToBall,
    // Layer 6: Breath Transform
    type BreathConfig,
    // Layer 8: Multi-Well Potential
    type Well
} from './hyperbolic.js';

// ═══════════════════════════════════════════════════════════════
// Sacred Tongues - Definitions
// ═══════════════════════════════════════════════════════════════

export {
    AVALI, CASSISIVADAN, DRAUMRIC, KOR_AELIN, RUNETHIC, TONGUES as SACRED_TONGUES,
    SECTION_TONGUES, UMBROTH, getTongueForSection, type SS1Section, type TongueCode, type TongueSpec
} from './sacredTongues.js';

// ═══════════════════════════════════════════════════════════════
// SpiralSeal SS1 - Sacred Tongue Cryptographic Encoding
// ═══════════════════════════════════════════════════════════════

export {
    // Tokenizer
    SacredTongueTokenizer, SpiralSealSS1, computeLWSScore,
    // LWS Integration
    computeLWSWeights, decodeFromSpelltext, encodeToSpelltext, formatSS1Blob,
    parseSS1Blob,

    // Crypto
    randomBytes,
    seal,
    unseal,
    // SS1 Format
    type SS1Blob
} from './spiralSeal.js';

// ═══════════════════════════════════════════════════════════════
// Post-Quantum Cryptography (PQC)
// ═══════════════════════════════════════════════════════════════

export {

    // High-level API
    PQCProvider,
    defaultPQCProvider, invNtt,
    // ML-DSA (Dilithium) - Digital Signatures
    mldsaKeyGen,
    mldsaSign,
    mldsaVerify, mlkemDecapsulate, mlkemEncapsulate,
    // ML-KEM (Kyber) - Key Encapsulation
    mlkemKeyGen, ntt,
    // Utilities
    secureRandomBytes,
    shake128,
    shake256, type EncapsulationResult,
    type HybridEncryptionResult, type MLDSAKeyPair, type MLDSALevel,
    type MLKEMKeyPair,
    // Types
    type MLKEMLevel, type PQCConfig
} from './pqc.js';

// ═══════════════════════════════════════════════════════════════
// Quasicrystal Lattice
// ═══════════════════════════════════════════════════════════════

export {
    // Constants
    PHI,
    PHI_INV,
    // Provider
    QCLatticeProvider, SILVER_RATIO, ammannBeenkerRhombus,
    // Ammann-Beenker
    ammannBeenkerSquare, checkRotationalSymmetry,
    // Cut-and-Project
    cutAndProject2D, defaultQCLattice,
    // Diffraction
    diffractionPattern, fibonacci1D,
    fibonacci2D,
    // Fibonacci
    fibonacciSequence,
    fibonacciWord, nearestQCVertex, penroseDeflate,
    penroseInitial,
    // Penrose Tiling
    penroseRhombus, penroseTiling,
    penroseToLattice, quasicrystal4to2, quasicrystal5to2, quasicrystalHash, quasicrystalPotential,
    // SCBE Integration
    scbeToQuasicrystal, type DiffractionPeak, type LatticePoint, type PenroseTile, type PenroseTileType,
    // Types
    type Point2D, type QCLatticeConfig
} from './qcLattice.js';

// ═══════════════════════════════════════════════════════════════
// Polyhedral Hamiltonian Defense Manifold (PHDM)
// ═══════════════════════════════════════════════════════════════

export {

    // Canonical Polyhedra
    CANONICAL_POLYHEDRA, CubicSpline6D,

    // Intrusion Detection
    PHDMDeviationDetector,
    // Hamiltonian Path
    PHDMHamiltonianPath,
    // Complete System
    PolyhedralHamiltonianDefenseManifold, computeCentroid,
    // 6D Geometry
    distance6D,
    // Topology
    eulerCharacteristic,
    isValidTopology, serializePolyhedron, topologicalHash, type IntrusionResult, type Point6D,
    // Types
    type Polyhedron
} from './phdm.js';

