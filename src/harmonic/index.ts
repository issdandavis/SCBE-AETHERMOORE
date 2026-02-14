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
  CONSTANTS,
  type Tensor2D,
  type Tensor3D,
  type Vector3D,
  type Vector6D,
} from './constants.js';

export { assertFinite, assertIntGE, log2 } from './assertions.js';

// ═══════════════════════════════════════════════════════════════
// Layer 12: Harmonic Scaling
// ═══════════════════════════════════════════════════════════════

export {
  harmonicDistance,
  harmonicScale,
  octaveTranspose,
  securityBits,
  securityLevel,
} from './harmonicScaling.js';

// ═══════════════════════════════════════════════════════════════
// HAL - Harmonic Attention Layer
// ═══════════════════════════════════════════════════════════════

export { halAttention, harmonicCouplingMatrix, type HALConfig } from './halAttention.js';

// ═══════════════════════════════════════════════════════════════
// Layer 14: Vacuum-Acoustics Kernel
// ═══════════════════════════════════════════════════════════════

export {
  bottleBeamIntensity,
  cavityResonance,
  checkCymaticResonance,
  fluxRedistribution,
  nodalSurface,
  standingWaveAmplitude,
  type AcousticSource,
  type VacuumAcousticsConfig,
} from './vacuumAcoustics.js';

// ═══════════════════════════════════════════════════════════════
// Langues Metric - 6D Governance Cost Function
// ═══════════════════════════════════════════════════════════════

export {
  FluxingLanguesMetric,
  LanguesMetric,
  TONGUES,
  getFluxState,
  type Decision,
  type DimensionFlux,
  type FluxState,
  type LanguesMetricConfig,
  type Tongue,
} from './languesMetric.js';

// ═══════════════════════════════════════════════════════════════
// Layer 14: Audio Axis (FFT Telemetry)
// ═══════════════════════════════════════════════════════════════

export {
  AudioAxisProcessor,
  generateNoise,
  generateTestSignal,
  type AudioAxisConfig,
  type AudioFeatures,
} from './audioAxis.js';

// ═══════════════════════════════════════════════════════════════
// Hamiltonian CFI - Control Flow Integrity
// ═══════════════════════════════════════════════════════════════

export {
  ControlFlowGraph,
  HamiltonianCFI,
  createVertex,
  type BipartiteResult,
  type CFGVertex,
  type CFIResult,
  type HamiltonianCheck,
} from './hamiltonianCFI.js';

// ═══════════════════════════════════════════════════════════════
// Layers 5-8: Hyperbolic Geometry (Poincaré Ball)
// ═══════════════════════════════════════════════════════════════

export {
  // Layer 5: Invariant Metric + Configurable Audit Epsilon
  EPSILON as HYPERBOLIC_EPSILON,
  applyHyperbolicPipeline,
  artanh,
  breathTransform,
  clampToBall,
  expMap0,
  exponentialMap,
  getAuditEpsilon,
  hyperbolicDistance,
  inverseBreathTransform,
  logMap0,
  logarithmicMap,
  mobiusAdd,
  mobiusAddition,
  multiPhaseModulation,
  multiWellGradient,
  multiWellPotential,
  phaseDeviation as hyperbolicPhaseDeviation,
  phaseDistanceScore as hyperbolicPhaseDistanceScore,
  phaseModulation,
  projectEmbeddingToBall,
  projectToBall,
  scoreRetrievals,
  setAuditEpsilon,
  // Layer 6: Breath Transform
  type BreathConfig,
  // Layer 8: Multi-Well Potential
  type Well,
} from './hyperbolic.js';

// ═══════════════════════════════════════════════════════════════
// Sacred Tongues - Definitions
// ═══════════════════════════════════════════════════════════════

export {
  AVALI,
  CASSISIVADAN,
  DRAUMRIC,
  KOR_AELIN,
  RUNETHIC,
  TONGUES as SACRED_TONGUES,
  SECTION_TONGUES,
  UMBROTH,
  getTongueForSection,
  type SS1Section,
  type TongueCode,
  type TongueSpec,
} from './sacredTongues.js';

// ═══════════════════════════════════════════════════════════════
// SpiralSeal SS1 - Sacred Tongue Cryptographic Encoding
// ═══════════════════════════════════════════════════════════════

export {
  // Tokenizer
  SacredTongueTokenizer,
  SpiralSealSS1,
  computeLWSScore,
  // LWS Integration
  computeLWSWeights,
  decodeFromSpelltext,
  encodeToSpelltext,
  formatSS1Blob,
  parseSS1Blob,

  // Crypto
  randomBytes,
  seal,
  unseal,
  // SS1 Format
  type SS1Blob,
} from './spiralSeal.js';

// ═══════════════════════════════════════════════════════════════
// Post-Quantum Cryptography (PQC)
// ═══════════════════════════════════════════════════════════════

export {
  // High-level API
  PQCProvider,
  defaultPQCProvider,
  invNtt,
  // ML-DSA (Dilithium) - Digital Signatures
  mldsaKeyGen,
  mldsaSign,
  mldsaVerify,
  mlkemDecapsulate,
  mlkemEncapsulate,
  // ML-KEM (Kyber) - Key Encapsulation
  mlkemKeyGen,
  ntt,
  // Utilities
  secureRandomBytes,
  shake128,
  shake256,
  type EncapsulationResult,
  type HybridEncryptionResult,
  type MLDSAKeyPair,
  type MLDSALevel,
  type MLKEMKeyPair,
  // Types
  type MLKEMLevel,
  type PQCConfig,
} from './pqc.js';

// ═══════════════════════════════════════════════════════════════
// Quasicrystal Lattice
// ═══════════════════════════════════════════════════════════════

export {
  // Constants
  PHI,
  PHI_INV,
  // Provider
  QCLatticeProvider,
  SILVER_RATIO,
  ammannBeenkerRhombus,
  // Ammann-Beenker
  ammannBeenkerSquare,
  checkRotationalSymmetry,
  // Cut-and-Project
  cutAndProject2D,
  defaultQCLattice,
  // Diffraction
  diffractionPattern,
  fibonacci1D,
  fibonacci2D,
  // Fibonacci
  fibonacciSequence,
  fibonacciWord,
  nearestQCVertex,
  penroseDeflate,
  penroseInitial,
  // Penrose Tiling
  penroseRhombus,
  penroseTiling,
  penroseToLattice,
  quasicrystal4to2,
  quasicrystal5to2,
  quasicrystalHash,
  quasicrystalPotential,
  // SCBE Integration
  scbeToQuasicrystal,
  type DiffractionPeak,
  type LatticePoint,
  type PenroseTile,
  type PenroseTileType,
  // Types
  type Point2D,
  type QCLatticeConfig,
} from './qcLattice.js';

// ═══════════════════════════════════════════════════════════════
// Polyhedral Hamiltonian Defense Manifold (PHDM)
// ═══════════════════════════════════════════════════════════════

export {
  // Canonical Polyhedra
  CANONICAL_POLYHEDRA,
  CubicSpline6D,

  // Intrusion Detection
  PHDMDeviationDetector,
  // Hamiltonian Path
  PHDMHamiltonianPath,
  // Complete System
  PolyhedralHamiltonianDefenseManifold,
  computeCentroid,
  // 6D Geometry
  distance6D,
  // Topology
  eulerCharacteristic,
  isValidTopology,
  serializePolyhedron,
  topologicalHash,
  // Flux Governance
  getActivePolyhedra,
  // Phason Shift
  generateProjectionMatrix,
  phasonShift,
  type IntrusionResult,
  type Point6D,
  // Types
  type FluxState as PHDMFluxState,
  type Polyhedron,
  type PolyhedronFamily,
} from './phdm.js';

// ═══════════════════════════════════════════════════════════════
// Spectral Identity - Rainbow Chromatic Fingerprinting
// ═══════════════════════════════════════════════════════════════

export {
  // Constants
  SPECTRAL_BANDS,
  // Generator
  SpectralIdentityGenerator,
  TONGUE_COLORS,
  spectralGenerator,
  type HSL,
  // Types
  type RGB,
  type SpectralBand,
  type SpectralIdentity,
} from './spectral-identity.js';

// ═══════════════════════════════════════════════════════════════
// Sacred Eggs — Ritual-Based Conditional Secret Distribution
// ═══════════════════════════════════════════════════════════════

export {
  // Egg creation and hatching
  createEgg,
  hatch,
  // Predicates
  predicateTongue,
  predicateGeo,
  predicatePath,
  predicateQuorum,
  predicateCrypto,
  // Key derivation
  deriveKey,
  // Utilities
  getRingLevel,
  // Constants
  ALL_TONGUES,
  RING_BOUNDARIES,
  DEFAULT_TONGUE_WEIGHTS,
  // Types
  type SacredEgg,
  type EggPolicy,
  type VerifierState,
  type Approval,
  type HatchResult,
  type RingLevel,
} from './sacredEggs.js';

// ═══════════════════════════════════════════════════════════════
// Three-Mechanism Adversarial Detection
// ═══════════════════════════════════════════════════════════════

export {
  // Core detector
  TriMechanismDetector,
  // Mechanism functions
  computeDriftSignature,
  driftAuthScore,
  driftDistanceToBaseline,
  hyperbolicDistance as triHyperbolicDistance,
  phaseDeviation,
  phaseDistanceScore,
  tonicCoherence,
  // Constants
  DEFAULT_CONFIG,
  TONGUE_INDEX,
  TONGUE_PHASES,
  // Types
  type DetectionDecision,
  type PipelineMetrics,
  type PositionSample,
  type TriDetectionResult,
  type TriDetectorConfig,
} from './triMechanismDetector.js';

// ═══════════════════════════════════════════════════════════════
// HyperbolicRAG — Poincaré Ball Retrieval-Augmented Generation
// ═══════════════════════════════════════════════════════════════

export {
  // Engine
  HyperbolicRAGEngine,
  createHyperbolicRAG,
  // Access cost
  accessCost,
  trustFromPosition,
  // Types
  type HyperbolicRAGConfig,
  type RAGDocument,
  type RetrievalResult,
  type RetrievalSummary,
} from './hyperbolicRAG.js';

// ═══════════════════════════════════════════════════════════════
// Entropic Layer — Escape Detection, Adaptive-k, Expansion Tracking
// ═══════════════════════════════════════════════════════════════

export {
  // Monitor
  EntropicMonitor,
  createEntropicMonitor,
  // Escape detection
  detectEscape,
  // Adaptive k
  computeAdaptiveK,
  computeLocalEntropy,
  computeTrustDensity,
  // Expansion tracking
  computeExpansionRate,
  estimateReachableVolume,
  trackExpansion,
  // Utilities
  defaultBasins,
  verifyEntropicInvariants,
  // Types
  type AdaptiveKResult,
  type EntropicConfig,
  type EntropicSample,
  type EntropicState,
  type EscapeResult,
  type ExpansionResult,
  type TrustBasin,
} from './entropic.js';

// ═══════════════════════════════════════════════════════════════
// Sacred Eggs Genesis Gate — Agent-Only Scope (v1)
// ═══════════════════════════════════════════════════════════════

export {
  // Genesis gate
  genesis,
  evaluateGenesis,
  // Hatch weight
  computeHatchWeight as genesisHatchWeight,
  geoSealDistance,
  // Certificate
  verifyCertificateSeal,
  // Constants
  GENESIS_THRESHOLD,
  DEFAULT_GEOSEAL_MAX_DISTANCE,
  DEFAULT_GENESIS_CONFIG,
  // Types
  type GenesisConfig,
  type GenesisCertificate,
  type GenesisResult,
  type GenesisEvaluation,
} from './sacredEggsGenesis.js';

// ═══════════════════════════════════════════════════════════════
// Decimal Drift Tracker — Entropy Harvesting Engine
// ═══════════════════════════════════════════════════════════════

export {
  // Tracker class
  DriftTracker,
  // Core functions
  captureStepDrift,
  estimateFractalDimension,
  deriveHarmonicKey,
  assessAuthenticity,
  sonifyDrift,
  // Constants
  TONGUE_HARMONICS,
  DEFAULT_BUFFER_CAPACITY,
  SYNTHETIC_CV_THRESHOLD,
  GENUINE_FRACTAL_MIN,
  // Types
  type DriftCapture,
  type ShadowBufferConfig,
  type FractalEstimate,
  type HarmonicKey,
  type DriftAuthenticity,
  type DriftSonification,
  type DriftTrackerStats,
} from './driftTracker.js';

// ═══════════════════════════════════════════════════════════════
// Sheaf Cohomology — Tarski Laplacian on Lattice-Valued Sheaves
// ═══════════════════════════════════════════════════════════════

export {
  // Lattice implementations
  BooleanLattice,
  IntervalLattice,
  PowerSetLattice,
  UnitIntervalLattice,
  ProductLattice,
  // Galois connections
  identityConnection,
  constantConnection,
  thresholdConnection,
  scalingConnection,
  // Cell complex builders
  graphComplex,
  simplicialComplex,
  // Sheaf constructors
  constantSheaf,
  thresholdSheaf,
  twistedSheaf,
  // Cochains
  topCochain,
  bottomCochain,
  // Tarski Laplacian
  tarskiLaplacian,
  // Cohomology
  tarskiCohomology,
  globalSections,
  // Hodge Laplacians
  upLaplacian,
  downLaplacian,
  hodgeLaplacian,
  hodgeCohomology,
  // Diagnostics
  analyseCohomology,
  detectObstructions,
  // SCBE Engine
  SheafCohomologyEngine,
  defaultSheafEngine,
  // Types
  type CompleteLattice,
  type GaloisConnection,
  type Cell,
  type CellComplex,
  type CellularSheaf,
  type Cochain,
  type CohomologyResult,
  type CohomologyDiagnostics,
  type Obstruction,
  type SheafCohomologyConfig,
  type SheafAnalysisResult,
} from './sheafCohomology.js';

