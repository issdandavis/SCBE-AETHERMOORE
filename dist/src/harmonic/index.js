"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.scoreRetrievals = exports.projectToBall = exports.projectEmbeddingToBall = exports.phaseModulation = exports.hyperbolicPhaseDistanceScore = exports.hyperbolicPhaseDeviation = exports.multiWellPotential = exports.multiWellGradient = exports.multiPhaseModulation = exports.mobiusAddition = exports.mobiusAdd = exports.logarithmicMap = exports.logMap0 = exports.inverseBreathTransform = exports.hyperbolicDistance = exports.getAuditEpsilon = exports.exponentialMap = exports.expMap0 = exports.clampToBall = exports.breathTransform = exports.artanh = exports.applyHyperbolicPipeline = exports.HYPERBOLIC_EPSILON = exports.createVertex = exports.HamiltonianCFI = exports.ControlFlowGraph = exports.generateTestSignal = exports.generateNoise = exports.AudioAxisProcessor = exports.getFluxState = exports.TONGUES = exports.LanguesMetric = exports.FluxingLanguesMetric = exports.standingWaveAmplitude = exports.nodalSurface = exports.fluxRedistribution = exports.checkCymaticResonance = exports.cavityResonance = exports.bottleBeamIntensity = exports.harmonicCouplingMatrix = exports.halAttention = exports.securityLevel = exports.securityBits = exports.octaveTranspose = exports.harmonicScale = exports.harmonicDistance = exports.log2 = exports.assertIntGE = exports.assertFinite = exports.CONSTANTS = void 0;
exports.penroseDeflate = exports.nearestQCVertex = exports.fibonacciWord = exports.fibonacciSequence = exports.fibonacci2D = exports.fibonacci1D = exports.diffractionPattern = exports.defaultQCLattice = exports.cutAndProject2D = exports.checkRotationalSymmetry = exports.ammannBeenkerSquare = exports.ammannBeenkerRhombus = exports.SILVER_RATIO = exports.QCLatticeProvider = exports.PHI_INV = exports.PHI = exports.shake256 = exports.shake128 = exports.secureRandomBytes = exports.ntt = exports.mlkemKeyGen = exports.mlkemEncapsulate = exports.mlkemDecapsulate = exports.mldsaVerify = exports.mldsaSign = exports.mldsaKeyGen = exports.invNtt = exports.defaultPQCProvider = exports.PQCProvider = exports.unseal = exports.seal = exports.randomBytes = exports.parseSS1Blob = exports.formatSS1Blob = exports.encodeToSpelltext = exports.decodeFromSpelltext = exports.computeLWSWeights = exports.computeLWSScore = exports.SpiralSealSS1 = exports.SacredTongueTokenizer = exports.getTongueForSection = exports.UMBROTH = exports.SECTION_TONGUES = exports.SACRED_TONGUES = exports.RUNETHIC = exports.KOR_AELIN = exports.DRAUMRIC = exports.CASSISIVADAN = exports.AVALI = exports.setAuditEpsilon = void 0;
exports.TONGUE_PHASES = exports.TONGUE_INDEX = exports.DEFAULT_CONFIG = exports.tonicCoherence = exports.phaseDistanceScore = exports.phaseDeviation = exports.triHyperbolicDistance = exports.driftDistanceToBaseline = exports.driftAuthScore = exports.computeDriftSignature = exports.TriMechanismDetector = exports.DEFAULT_TONGUE_WEIGHTS = exports.RING_BOUNDARIES = exports.ALL_TONGUES = exports.getRingLevel = exports.deriveKey = exports.predicateCrypto = exports.predicateQuorum = exports.predicatePath = exports.predicateGeo = exports.predicateTongue = exports.hatch = exports.createEgg = exports.spectralGenerator = exports.TONGUE_COLORS = exports.SpectralIdentityGenerator = exports.SPECTRAL_BANDS = exports.phasonShift = exports.generateProjectionMatrix = exports.getActivePolyhedra = exports.topologicalHash = exports.serializePolyhedron = exports.isValidTopology = exports.eulerCharacteristic = exports.distance6D = exports.computeCentroid = exports.PolyhedralHamiltonianDefenseManifold = exports.PHDMHamiltonianPath = exports.PHDMDeviationDetector = exports.CubicSpline6D = exports.CANONICAL_POLYHEDRA = exports.scbeToQuasicrystal = exports.quasicrystalPotential = exports.quasicrystalHash = exports.quasicrystal5to2 = exports.quasicrystal4to2 = exports.penroseToLattice = exports.penroseTiling = exports.penroseRhombus = exports.penroseInitial = void 0;
exports.tarskiLaplacian = exports.bottomCochain = exports.topCochain = exports.twistedSheaf = exports.thresholdSheaf = exports.constantSheaf = exports.simplicialComplex = exports.graphComplex = exports.scalingConnection = exports.thresholdConnection = exports.constantConnection = exports.identityConnection = exports.ProductLattice = exports.UnitIntervalLattice = exports.PowerSetLattice = exports.IntervalLattice = exports.BooleanLattice = exports.GENUINE_FRACTAL_MIN = exports.SYNTHETIC_CV_THRESHOLD = exports.DEFAULT_BUFFER_CAPACITY = exports.TONGUE_HARMONICS = exports.sonifyDrift = exports.assessAuthenticity = exports.deriveHarmonicKey = exports.estimateFractalDimension = exports.captureStepDrift = exports.DriftTracker = exports.DEFAULT_GENESIS_CONFIG = exports.DEFAULT_GEOSEAL_MAX_DISTANCE = exports.GENESIS_THRESHOLD = exports.verifyCertificateSeal = exports.geoSealDistance = exports.genesisHatchWeight = exports.evaluateGenesis = exports.genesis = exports.verifyEntropicInvariants = exports.defaultBasins = exports.trackExpansion = exports.estimateReachableVolume = exports.computeExpansionRate = exports.computeTrustDensity = exports.computeLocalEntropy = exports.computeAdaptiveK = exports.detectEscape = exports.createEntropicMonitor = exports.EntropicMonitor = exports.trustFromPosition = exports.accessCost = exports.createHyperbolicRAG = exports.HyperbolicRAGEngine = void 0;
exports.defaultGovernanceRouter = exports.requiredFluxState = exports.trustDistanceMatrix = exports.polyhedralEulerCharacteristic = exports.computePolyhedralTrust = exports.buildGovernanceSheaf = exports.buildPolyhedralGraph = exports.PHDMGovernanceRouter = exports.defaultSheafEngine = exports.SheafCohomologyEngine = exports.detectObstructions = exports.analyseCohomology = exports.hodgeCohomology = exports.hodgeLaplacian = exports.downLaplacian = exports.upLaplacian = exports.globalSections = exports.tarskiCohomology = void 0;
// ═══════════════════════════════════════════════════════════════
// Constants and Types
// ═══════════════════════════════════════════════════════════════
var constants_js_1 = require("./constants.js");
Object.defineProperty(exports, "CONSTANTS", { enumerable: true, get: function () { return constants_js_1.CONSTANTS; } });
var assertions_js_1 = require("./assertions.js");
Object.defineProperty(exports, "assertFinite", { enumerable: true, get: function () { return assertions_js_1.assertFinite; } });
Object.defineProperty(exports, "assertIntGE", { enumerable: true, get: function () { return assertions_js_1.assertIntGE; } });
Object.defineProperty(exports, "log2", { enumerable: true, get: function () { return assertions_js_1.log2; } });
// ═══════════════════════════════════════════════════════════════
// Layer 12: Harmonic Scaling
// ═══════════════════════════════════════════════════════════════
var harmonicScaling_js_1 = require("./harmonicScaling.js");
Object.defineProperty(exports, "harmonicDistance", { enumerable: true, get: function () { return harmonicScaling_js_1.harmonicDistance; } });
Object.defineProperty(exports, "harmonicScale", { enumerable: true, get: function () { return harmonicScaling_js_1.harmonicScale; } });
Object.defineProperty(exports, "octaveTranspose", { enumerable: true, get: function () { return harmonicScaling_js_1.octaveTranspose; } });
Object.defineProperty(exports, "securityBits", { enumerable: true, get: function () { return harmonicScaling_js_1.securityBits; } });
Object.defineProperty(exports, "securityLevel", { enumerable: true, get: function () { return harmonicScaling_js_1.securityLevel; } });
// ═══════════════════════════════════════════════════════════════
// HAL - Harmonic Attention Layer
// ═══════════════════════════════════════════════════════════════
var halAttention_js_1 = require("./halAttention.js");
Object.defineProperty(exports, "halAttention", { enumerable: true, get: function () { return halAttention_js_1.halAttention; } });
Object.defineProperty(exports, "harmonicCouplingMatrix", { enumerable: true, get: function () { return halAttention_js_1.harmonicCouplingMatrix; } });
// ═══════════════════════════════════════════════════════════════
// Layer 14: Vacuum-Acoustics Kernel
// ═══════════════════════════════════════════════════════════════
var vacuumAcoustics_js_1 = require("./vacuumAcoustics.js");
Object.defineProperty(exports, "bottleBeamIntensity", { enumerable: true, get: function () { return vacuumAcoustics_js_1.bottleBeamIntensity; } });
Object.defineProperty(exports, "cavityResonance", { enumerable: true, get: function () { return vacuumAcoustics_js_1.cavityResonance; } });
Object.defineProperty(exports, "checkCymaticResonance", { enumerable: true, get: function () { return vacuumAcoustics_js_1.checkCymaticResonance; } });
Object.defineProperty(exports, "fluxRedistribution", { enumerable: true, get: function () { return vacuumAcoustics_js_1.fluxRedistribution; } });
Object.defineProperty(exports, "nodalSurface", { enumerable: true, get: function () { return vacuumAcoustics_js_1.nodalSurface; } });
Object.defineProperty(exports, "standingWaveAmplitude", { enumerable: true, get: function () { return vacuumAcoustics_js_1.standingWaveAmplitude; } });
// ═══════════════════════════════════════════════════════════════
// Langues Metric - 6D Governance Cost Function
// ═══════════════════════════════════════════════════════════════
var languesMetric_js_1 = require("./languesMetric.js");
Object.defineProperty(exports, "FluxingLanguesMetric", { enumerable: true, get: function () { return languesMetric_js_1.FluxingLanguesMetric; } });
Object.defineProperty(exports, "LanguesMetric", { enumerable: true, get: function () { return languesMetric_js_1.LanguesMetric; } });
Object.defineProperty(exports, "TONGUES", { enumerable: true, get: function () { return languesMetric_js_1.TONGUES; } });
Object.defineProperty(exports, "getFluxState", { enumerable: true, get: function () { return languesMetric_js_1.getFluxState; } });
// ═══════════════════════════════════════════════════════════════
// Layer 14: Audio Axis (FFT Telemetry)
// ═══════════════════════════════════════════════════════════════
var audioAxis_js_1 = require("./audioAxis.js");
Object.defineProperty(exports, "AudioAxisProcessor", { enumerable: true, get: function () { return audioAxis_js_1.AudioAxisProcessor; } });
Object.defineProperty(exports, "generateNoise", { enumerable: true, get: function () { return audioAxis_js_1.generateNoise; } });
Object.defineProperty(exports, "generateTestSignal", { enumerable: true, get: function () { return audioAxis_js_1.generateTestSignal; } });
// ═══════════════════════════════════════════════════════════════
// Hamiltonian CFI - Control Flow Integrity
// ═══════════════════════════════════════════════════════════════
var hamiltonianCFI_js_1 = require("./hamiltonianCFI.js");
Object.defineProperty(exports, "ControlFlowGraph", { enumerable: true, get: function () { return hamiltonianCFI_js_1.ControlFlowGraph; } });
Object.defineProperty(exports, "HamiltonianCFI", { enumerable: true, get: function () { return hamiltonianCFI_js_1.HamiltonianCFI; } });
Object.defineProperty(exports, "createVertex", { enumerable: true, get: function () { return hamiltonianCFI_js_1.createVertex; } });
// ═══════════════════════════════════════════════════════════════
// Layers 5-8: Hyperbolic Geometry (Poincaré Ball)
// ═══════════════════════════════════════════════════════════════
var hyperbolic_js_1 = require("./hyperbolic.js");
// Layer 5: Invariant Metric + Configurable Audit Epsilon
Object.defineProperty(exports, "HYPERBOLIC_EPSILON", { enumerable: true, get: function () { return hyperbolic_js_1.EPSILON; } });
Object.defineProperty(exports, "applyHyperbolicPipeline", { enumerable: true, get: function () { return hyperbolic_js_1.applyHyperbolicPipeline; } });
Object.defineProperty(exports, "artanh", { enumerable: true, get: function () { return hyperbolic_js_1.artanh; } });
Object.defineProperty(exports, "breathTransform", { enumerable: true, get: function () { return hyperbolic_js_1.breathTransform; } });
Object.defineProperty(exports, "clampToBall", { enumerable: true, get: function () { return hyperbolic_js_1.clampToBall; } });
Object.defineProperty(exports, "expMap0", { enumerable: true, get: function () { return hyperbolic_js_1.expMap0; } });
Object.defineProperty(exports, "exponentialMap", { enumerable: true, get: function () { return hyperbolic_js_1.exponentialMap; } });
Object.defineProperty(exports, "getAuditEpsilon", { enumerable: true, get: function () { return hyperbolic_js_1.getAuditEpsilon; } });
Object.defineProperty(exports, "hyperbolicDistance", { enumerable: true, get: function () { return hyperbolic_js_1.hyperbolicDistance; } });
Object.defineProperty(exports, "inverseBreathTransform", { enumerable: true, get: function () { return hyperbolic_js_1.inverseBreathTransform; } });
Object.defineProperty(exports, "logMap0", { enumerable: true, get: function () { return hyperbolic_js_1.logMap0; } });
Object.defineProperty(exports, "logarithmicMap", { enumerable: true, get: function () { return hyperbolic_js_1.logarithmicMap; } });
Object.defineProperty(exports, "mobiusAdd", { enumerable: true, get: function () { return hyperbolic_js_1.mobiusAdd; } });
Object.defineProperty(exports, "mobiusAddition", { enumerable: true, get: function () { return hyperbolic_js_1.mobiusAddition; } });
Object.defineProperty(exports, "multiPhaseModulation", { enumerable: true, get: function () { return hyperbolic_js_1.multiPhaseModulation; } });
Object.defineProperty(exports, "multiWellGradient", { enumerable: true, get: function () { return hyperbolic_js_1.multiWellGradient; } });
Object.defineProperty(exports, "multiWellPotential", { enumerable: true, get: function () { return hyperbolic_js_1.multiWellPotential; } });
Object.defineProperty(exports, "hyperbolicPhaseDeviation", { enumerable: true, get: function () { return hyperbolic_js_1.phaseDeviation; } });
Object.defineProperty(exports, "hyperbolicPhaseDistanceScore", { enumerable: true, get: function () { return hyperbolic_js_1.phaseDistanceScore; } });
Object.defineProperty(exports, "phaseModulation", { enumerable: true, get: function () { return hyperbolic_js_1.phaseModulation; } });
Object.defineProperty(exports, "projectEmbeddingToBall", { enumerable: true, get: function () { return hyperbolic_js_1.projectEmbeddingToBall; } });
Object.defineProperty(exports, "projectToBall", { enumerable: true, get: function () { return hyperbolic_js_1.projectToBall; } });
Object.defineProperty(exports, "scoreRetrievals", { enumerable: true, get: function () { return hyperbolic_js_1.scoreRetrievals; } });
Object.defineProperty(exports, "setAuditEpsilon", { enumerable: true, get: function () { return hyperbolic_js_1.setAuditEpsilon; } });
// ═══════════════════════════════════════════════════════════════
// Sacred Tongues - Definitions
// ═══════════════════════════════════════════════════════════════
var sacredTongues_js_1 = require("./sacredTongues.js");
Object.defineProperty(exports, "AVALI", { enumerable: true, get: function () { return sacredTongues_js_1.AVALI; } });
Object.defineProperty(exports, "CASSISIVADAN", { enumerable: true, get: function () { return sacredTongues_js_1.CASSISIVADAN; } });
Object.defineProperty(exports, "DRAUMRIC", { enumerable: true, get: function () { return sacredTongues_js_1.DRAUMRIC; } });
Object.defineProperty(exports, "KOR_AELIN", { enumerable: true, get: function () { return sacredTongues_js_1.KOR_AELIN; } });
Object.defineProperty(exports, "RUNETHIC", { enumerable: true, get: function () { return sacredTongues_js_1.RUNETHIC; } });
Object.defineProperty(exports, "SACRED_TONGUES", { enumerable: true, get: function () { return sacredTongues_js_1.TONGUES; } });
Object.defineProperty(exports, "SECTION_TONGUES", { enumerable: true, get: function () { return sacredTongues_js_1.SECTION_TONGUES; } });
Object.defineProperty(exports, "UMBROTH", { enumerable: true, get: function () { return sacredTongues_js_1.UMBROTH; } });
Object.defineProperty(exports, "getTongueForSection", { enumerable: true, get: function () { return sacredTongues_js_1.getTongueForSection; } });
// ═══════════════════════════════════════════════════════════════
// SpiralSeal SS1 - Sacred Tongue Cryptographic Encoding
// ═══════════════════════════════════════════════════════════════
var spiralSeal_js_1 = require("./spiralSeal.js");
// Tokenizer
Object.defineProperty(exports, "SacredTongueTokenizer", { enumerable: true, get: function () { return spiralSeal_js_1.SacredTongueTokenizer; } });
Object.defineProperty(exports, "SpiralSealSS1", { enumerable: true, get: function () { return spiralSeal_js_1.SpiralSealSS1; } });
Object.defineProperty(exports, "computeLWSScore", { enumerable: true, get: function () { return spiralSeal_js_1.computeLWSScore; } });
// LWS Integration
Object.defineProperty(exports, "computeLWSWeights", { enumerable: true, get: function () { return spiralSeal_js_1.computeLWSWeights; } });
Object.defineProperty(exports, "decodeFromSpelltext", { enumerable: true, get: function () { return spiralSeal_js_1.decodeFromSpelltext; } });
Object.defineProperty(exports, "encodeToSpelltext", { enumerable: true, get: function () { return spiralSeal_js_1.encodeToSpelltext; } });
Object.defineProperty(exports, "formatSS1Blob", { enumerable: true, get: function () { return spiralSeal_js_1.formatSS1Blob; } });
Object.defineProperty(exports, "parseSS1Blob", { enumerable: true, get: function () { return spiralSeal_js_1.parseSS1Blob; } });
// Crypto
Object.defineProperty(exports, "randomBytes", { enumerable: true, get: function () { return spiralSeal_js_1.randomBytes; } });
Object.defineProperty(exports, "seal", { enumerable: true, get: function () { return spiralSeal_js_1.seal; } });
Object.defineProperty(exports, "unseal", { enumerable: true, get: function () { return spiralSeal_js_1.unseal; } });
// ═══════════════════════════════════════════════════════════════
// Post-Quantum Cryptography (PQC)
// ═══════════════════════════════════════════════════════════════
var pqc_js_1 = require("./pqc.js");
// High-level API
Object.defineProperty(exports, "PQCProvider", { enumerable: true, get: function () { return pqc_js_1.PQCProvider; } });
Object.defineProperty(exports, "defaultPQCProvider", { enumerable: true, get: function () { return pqc_js_1.defaultPQCProvider; } });
Object.defineProperty(exports, "invNtt", { enumerable: true, get: function () { return pqc_js_1.invNtt; } });
// ML-DSA (Dilithium) - Digital Signatures
Object.defineProperty(exports, "mldsaKeyGen", { enumerable: true, get: function () { return pqc_js_1.mldsaKeyGen; } });
Object.defineProperty(exports, "mldsaSign", { enumerable: true, get: function () { return pqc_js_1.mldsaSign; } });
Object.defineProperty(exports, "mldsaVerify", { enumerable: true, get: function () { return pqc_js_1.mldsaVerify; } });
Object.defineProperty(exports, "mlkemDecapsulate", { enumerable: true, get: function () { return pqc_js_1.mlkemDecapsulate; } });
Object.defineProperty(exports, "mlkemEncapsulate", { enumerable: true, get: function () { return pqc_js_1.mlkemEncapsulate; } });
// ML-KEM (Kyber) - Key Encapsulation
Object.defineProperty(exports, "mlkemKeyGen", { enumerable: true, get: function () { return pqc_js_1.mlkemKeyGen; } });
Object.defineProperty(exports, "ntt", { enumerable: true, get: function () { return pqc_js_1.ntt; } });
// Utilities
Object.defineProperty(exports, "secureRandomBytes", { enumerable: true, get: function () { return pqc_js_1.secureRandomBytes; } });
Object.defineProperty(exports, "shake128", { enumerable: true, get: function () { return pqc_js_1.shake128; } });
Object.defineProperty(exports, "shake256", { enumerable: true, get: function () { return pqc_js_1.shake256; } });
// ═══════════════════════════════════════════════════════════════
// Quasicrystal Lattice
// ═══════════════════════════════════════════════════════════════
var qcLattice_js_1 = require("./qcLattice.js");
// Constants
Object.defineProperty(exports, "PHI", { enumerable: true, get: function () { return qcLattice_js_1.PHI; } });
Object.defineProperty(exports, "PHI_INV", { enumerable: true, get: function () { return qcLattice_js_1.PHI_INV; } });
// Provider
Object.defineProperty(exports, "QCLatticeProvider", { enumerable: true, get: function () { return qcLattice_js_1.QCLatticeProvider; } });
Object.defineProperty(exports, "SILVER_RATIO", { enumerable: true, get: function () { return qcLattice_js_1.SILVER_RATIO; } });
Object.defineProperty(exports, "ammannBeenkerRhombus", { enumerable: true, get: function () { return qcLattice_js_1.ammannBeenkerRhombus; } });
// Ammann-Beenker
Object.defineProperty(exports, "ammannBeenkerSquare", { enumerable: true, get: function () { return qcLattice_js_1.ammannBeenkerSquare; } });
Object.defineProperty(exports, "checkRotationalSymmetry", { enumerable: true, get: function () { return qcLattice_js_1.checkRotationalSymmetry; } });
// Cut-and-Project
Object.defineProperty(exports, "cutAndProject2D", { enumerable: true, get: function () { return qcLattice_js_1.cutAndProject2D; } });
Object.defineProperty(exports, "defaultQCLattice", { enumerable: true, get: function () { return qcLattice_js_1.defaultQCLattice; } });
// Diffraction
Object.defineProperty(exports, "diffractionPattern", { enumerable: true, get: function () { return qcLattice_js_1.diffractionPattern; } });
Object.defineProperty(exports, "fibonacci1D", { enumerable: true, get: function () { return qcLattice_js_1.fibonacci1D; } });
Object.defineProperty(exports, "fibonacci2D", { enumerable: true, get: function () { return qcLattice_js_1.fibonacci2D; } });
// Fibonacci
Object.defineProperty(exports, "fibonacciSequence", { enumerable: true, get: function () { return qcLattice_js_1.fibonacciSequence; } });
Object.defineProperty(exports, "fibonacciWord", { enumerable: true, get: function () { return qcLattice_js_1.fibonacciWord; } });
Object.defineProperty(exports, "nearestQCVertex", { enumerable: true, get: function () { return qcLattice_js_1.nearestQCVertex; } });
Object.defineProperty(exports, "penroseDeflate", { enumerable: true, get: function () { return qcLattice_js_1.penroseDeflate; } });
Object.defineProperty(exports, "penroseInitial", { enumerable: true, get: function () { return qcLattice_js_1.penroseInitial; } });
// Penrose Tiling
Object.defineProperty(exports, "penroseRhombus", { enumerable: true, get: function () { return qcLattice_js_1.penroseRhombus; } });
Object.defineProperty(exports, "penroseTiling", { enumerable: true, get: function () { return qcLattice_js_1.penroseTiling; } });
Object.defineProperty(exports, "penroseToLattice", { enumerable: true, get: function () { return qcLattice_js_1.penroseToLattice; } });
Object.defineProperty(exports, "quasicrystal4to2", { enumerable: true, get: function () { return qcLattice_js_1.quasicrystal4to2; } });
Object.defineProperty(exports, "quasicrystal5to2", { enumerable: true, get: function () { return qcLattice_js_1.quasicrystal5to2; } });
Object.defineProperty(exports, "quasicrystalHash", { enumerable: true, get: function () { return qcLattice_js_1.quasicrystalHash; } });
Object.defineProperty(exports, "quasicrystalPotential", { enumerable: true, get: function () { return qcLattice_js_1.quasicrystalPotential; } });
// SCBE Integration
Object.defineProperty(exports, "scbeToQuasicrystal", { enumerable: true, get: function () { return qcLattice_js_1.scbeToQuasicrystal; } });
// ═══════════════════════════════════════════════════════════════
// Polyhedral Hamiltonian Defense Manifold (PHDM)
// ═══════════════════════════════════════════════════════════════
var phdm_js_1 = require("./phdm.js");
// Canonical Polyhedra
Object.defineProperty(exports, "CANONICAL_POLYHEDRA", { enumerable: true, get: function () { return phdm_js_1.CANONICAL_POLYHEDRA; } });
Object.defineProperty(exports, "CubicSpline6D", { enumerable: true, get: function () { return phdm_js_1.CubicSpline6D; } });
// Intrusion Detection
Object.defineProperty(exports, "PHDMDeviationDetector", { enumerable: true, get: function () { return phdm_js_1.PHDMDeviationDetector; } });
// Hamiltonian Path
Object.defineProperty(exports, "PHDMHamiltonianPath", { enumerable: true, get: function () { return phdm_js_1.PHDMHamiltonianPath; } });
// Complete System
Object.defineProperty(exports, "PolyhedralHamiltonianDefenseManifold", { enumerable: true, get: function () { return phdm_js_1.PolyhedralHamiltonianDefenseManifold; } });
Object.defineProperty(exports, "computeCentroid", { enumerable: true, get: function () { return phdm_js_1.computeCentroid; } });
// 6D Geometry
Object.defineProperty(exports, "distance6D", { enumerable: true, get: function () { return phdm_js_1.distance6D; } });
// Topology
Object.defineProperty(exports, "eulerCharacteristic", { enumerable: true, get: function () { return phdm_js_1.eulerCharacteristic; } });
Object.defineProperty(exports, "isValidTopology", { enumerable: true, get: function () { return phdm_js_1.isValidTopology; } });
Object.defineProperty(exports, "serializePolyhedron", { enumerable: true, get: function () { return phdm_js_1.serializePolyhedron; } });
Object.defineProperty(exports, "topologicalHash", { enumerable: true, get: function () { return phdm_js_1.topologicalHash; } });
// Flux Governance
Object.defineProperty(exports, "getActivePolyhedra", { enumerable: true, get: function () { return phdm_js_1.getActivePolyhedra; } });
// Phason Shift
Object.defineProperty(exports, "generateProjectionMatrix", { enumerable: true, get: function () { return phdm_js_1.generateProjectionMatrix; } });
Object.defineProperty(exports, "phasonShift", { enumerable: true, get: function () { return phdm_js_1.phasonShift; } });
// ═══════════════════════════════════════════════════════════════
// Spectral Identity - Rainbow Chromatic Fingerprinting
// ═══════════════════════════════════════════════════════════════
var spectral_identity_js_1 = require("./spectral-identity.js");
// Constants
Object.defineProperty(exports, "SPECTRAL_BANDS", { enumerable: true, get: function () { return spectral_identity_js_1.SPECTRAL_BANDS; } });
// Generator
Object.defineProperty(exports, "SpectralIdentityGenerator", { enumerable: true, get: function () { return spectral_identity_js_1.SpectralIdentityGenerator; } });
Object.defineProperty(exports, "TONGUE_COLORS", { enumerable: true, get: function () { return spectral_identity_js_1.TONGUE_COLORS; } });
Object.defineProperty(exports, "spectralGenerator", { enumerable: true, get: function () { return spectral_identity_js_1.spectralGenerator; } });
// ═══════════════════════════════════════════════════════════════
// Sacred Eggs — Ritual-Based Conditional Secret Distribution
// ═══════════════════════════════════════════════════════════════
var sacredEggs_js_1 = require("./sacredEggs.js");
// Egg creation and hatching
Object.defineProperty(exports, "createEgg", { enumerable: true, get: function () { return sacredEggs_js_1.createEgg; } });
Object.defineProperty(exports, "hatch", { enumerable: true, get: function () { return sacredEggs_js_1.hatch; } });
// Predicates
Object.defineProperty(exports, "predicateTongue", { enumerable: true, get: function () { return sacredEggs_js_1.predicateTongue; } });
Object.defineProperty(exports, "predicateGeo", { enumerable: true, get: function () { return sacredEggs_js_1.predicateGeo; } });
Object.defineProperty(exports, "predicatePath", { enumerable: true, get: function () { return sacredEggs_js_1.predicatePath; } });
Object.defineProperty(exports, "predicateQuorum", { enumerable: true, get: function () { return sacredEggs_js_1.predicateQuorum; } });
Object.defineProperty(exports, "predicateCrypto", { enumerable: true, get: function () { return sacredEggs_js_1.predicateCrypto; } });
// Key derivation
Object.defineProperty(exports, "deriveKey", { enumerable: true, get: function () { return sacredEggs_js_1.deriveKey; } });
// Utilities
Object.defineProperty(exports, "getRingLevel", { enumerable: true, get: function () { return sacredEggs_js_1.getRingLevel; } });
// Constants
Object.defineProperty(exports, "ALL_TONGUES", { enumerable: true, get: function () { return sacredEggs_js_1.ALL_TONGUES; } });
Object.defineProperty(exports, "RING_BOUNDARIES", { enumerable: true, get: function () { return sacredEggs_js_1.RING_BOUNDARIES; } });
Object.defineProperty(exports, "DEFAULT_TONGUE_WEIGHTS", { enumerable: true, get: function () { return sacredEggs_js_1.DEFAULT_TONGUE_WEIGHTS; } });
// ═══════════════════════════════════════════════════════════════
// Three-Mechanism Adversarial Detection
// ═══════════════════════════════════════════════════════════════
var triMechanismDetector_js_1 = require("./triMechanismDetector.js");
// Core detector
Object.defineProperty(exports, "TriMechanismDetector", { enumerable: true, get: function () { return triMechanismDetector_js_1.TriMechanismDetector; } });
// Mechanism functions
Object.defineProperty(exports, "computeDriftSignature", { enumerable: true, get: function () { return triMechanismDetector_js_1.computeDriftSignature; } });
Object.defineProperty(exports, "driftAuthScore", { enumerable: true, get: function () { return triMechanismDetector_js_1.driftAuthScore; } });
Object.defineProperty(exports, "driftDistanceToBaseline", { enumerable: true, get: function () { return triMechanismDetector_js_1.driftDistanceToBaseline; } });
Object.defineProperty(exports, "triHyperbolicDistance", { enumerable: true, get: function () { return triMechanismDetector_js_1.hyperbolicDistance; } });
Object.defineProperty(exports, "phaseDeviation", { enumerable: true, get: function () { return triMechanismDetector_js_1.phaseDeviation; } });
Object.defineProperty(exports, "phaseDistanceScore", { enumerable: true, get: function () { return triMechanismDetector_js_1.phaseDistanceScore; } });
Object.defineProperty(exports, "tonicCoherence", { enumerable: true, get: function () { return triMechanismDetector_js_1.tonicCoherence; } });
// Constants
Object.defineProperty(exports, "DEFAULT_CONFIG", { enumerable: true, get: function () { return triMechanismDetector_js_1.DEFAULT_CONFIG; } });
Object.defineProperty(exports, "TONGUE_INDEX", { enumerable: true, get: function () { return triMechanismDetector_js_1.TONGUE_INDEX; } });
Object.defineProperty(exports, "TONGUE_PHASES", { enumerable: true, get: function () { return triMechanismDetector_js_1.TONGUE_PHASES; } });
// ═══════════════════════════════════════════════════════════════
// HyperbolicRAG — Poincaré Ball Retrieval-Augmented Generation
// ═══════════════════════════════════════════════════════════════
var hyperbolicRAG_js_1 = require("./hyperbolicRAG.js");
// Engine
Object.defineProperty(exports, "HyperbolicRAGEngine", { enumerable: true, get: function () { return hyperbolicRAG_js_1.HyperbolicRAGEngine; } });
Object.defineProperty(exports, "createHyperbolicRAG", { enumerable: true, get: function () { return hyperbolicRAG_js_1.createHyperbolicRAG; } });
// Access cost
Object.defineProperty(exports, "accessCost", { enumerable: true, get: function () { return hyperbolicRAG_js_1.accessCost; } });
Object.defineProperty(exports, "trustFromPosition", { enumerable: true, get: function () { return hyperbolicRAG_js_1.trustFromPosition; } });
// ═══════════════════════════════════════════════════════════════
// Entropic Layer — Escape Detection, Adaptive-k, Expansion Tracking
// ═══════════════════════════════════════════════════════════════
var entropic_js_1 = require("./entropic.js");
// Monitor
Object.defineProperty(exports, "EntropicMonitor", { enumerable: true, get: function () { return entropic_js_1.EntropicMonitor; } });
Object.defineProperty(exports, "createEntropicMonitor", { enumerable: true, get: function () { return entropic_js_1.createEntropicMonitor; } });
// Escape detection
Object.defineProperty(exports, "detectEscape", { enumerable: true, get: function () { return entropic_js_1.detectEscape; } });
// Adaptive k
Object.defineProperty(exports, "computeAdaptiveK", { enumerable: true, get: function () { return entropic_js_1.computeAdaptiveK; } });
Object.defineProperty(exports, "computeLocalEntropy", { enumerable: true, get: function () { return entropic_js_1.computeLocalEntropy; } });
Object.defineProperty(exports, "computeTrustDensity", { enumerable: true, get: function () { return entropic_js_1.computeTrustDensity; } });
// Expansion tracking
Object.defineProperty(exports, "computeExpansionRate", { enumerable: true, get: function () { return entropic_js_1.computeExpansionRate; } });
Object.defineProperty(exports, "estimateReachableVolume", { enumerable: true, get: function () { return entropic_js_1.estimateReachableVolume; } });
Object.defineProperty(exports, "trackExpansion", { enumerable: true, get: function () { return entropic_js_1.trackExpansion; } });
// Utilities
Object.defineProperty(exports, "defaultBasins", { enumerable: true, get: function () { return entropic_js_1.defaultBasins; } });
Object.defineProperty(exports, "verifyEntropicInvariants", { enumerable: true, get: function () { return entropic_js_1.verifyEntropicInvariants; } });
// ═══════════════════════════════════════════════════════════════
// Sacred Eggs Genesis Gate — Agent-Only Scope (v1)
// ═══════════════════════════════════════════════════════════════
var sacredEggsGenesis_js_1 = require("./sacredEggsGenesis.js");
// Genesis gate
Object.defineProperty(exports, "genesis", { enumerable: true, get: function () { return sacredEggsGenesis_js_1.genesis; } });
Object.defineProperty(exports, "evaluateGenesis", { enumerable: true, get: function () { return sacredEggsGenesis_js_1.evaluateGenesis; } });
// Hatch weight
Object.defineProperty(exports, "genesisHatchWeight", { enumerable: true, get: function () { return sacredEggsGenesis_js_1.computeHatchWeight; } });
Object.defineProperty(exports, "geoSealDistance", { enumerable: true, get: function () { return sacredEggsGenesis_js_1.geoSealDistance; } });
// Certificate
Object.defineProperty(exports, "verifyCertificateSeal", { enumerable: true, get: function () { return sacredEggsGenesis_js_1.verifyCertificateSeal; } });
// Constants
Object.defineProperty(exports, "GENESIS_THRESHOLD", { enumerable: true, get: function () { return sacredEggsGenesis_js_1.GENESIS_THRESHOLD; } });
Object.defineProperty(exports, "DEFAULT_GEOSEAL_MAX_DISTANCE", { enumerable: true, get: function () { return sacredEggsGenesis_js_1.DEFAULT_GEOSEAL_MAX_DISTANCE; } });
Object.defineProperty(exports, "DEFAULT_GENESIS_CONFIG", { enumerable: true, get: function () { return sacredEggsGenesis_js_1.DEFAULT_GENESIS_CONFIG; } });
// ═══════════════════════════════════════════════════════════════
// Decimal Drift Tracker — Entropy Harvesting Engine
// ═══════════════════════════════════════════════════════════════
var driftTracker_js_1 = require("./driftTracker.js");
// Tracker class
Object.defineProperty(exports, "DriftTracker", { enumerable: true, get: function () { return driftTracker_js_1.DriftTracker; } });
// Core functions
Object.defineProperty(exports, "captureStepDrift", { enumerable: true, get: function () { return driftTracker_js_1.captureStepDrift; } });
Object.defineProperty(exports, "estimateFractalDimension", { enumerable: true, get: function () { return driftTracker_js_1.estimateFractalDimension; } });
Object.defineProperty(exports, "deriveHarmonicKey", { enumerable: true, get: function () { return driftTracker_js_1.deriveHarmonicKey; } });
Object.defineProperty(exports, "assessAuthenticity", { enumerable: true, get: function () { return driftTracker_js_1.assessAuthenticity; } });
Object.defineProperty(exports, "sonifyDrift", { enumerable: true, get: function () { return driftTracker_js_1.sonifyDrift; } });
// Constants
Object.defineProperty(exports, "TONGUE_HARMONICS", { enumerable: true, get: function () { return driftTracker_js_1.TONGUE_HARMONICS; } });
Object.defineProperty(exports, "DEFAULT_BUFFER_CAPACITY", { enumerable: true, get: function () { return driftTracker_js_1.DEFAULT_BUFFER_CAPACITY; } });
Object.defineProperty(exports, "SYNTHETIC_CV_THRESHOLD", { enumerable: true, get: function () { return driftTracker_js_1.SYNTHETIC_CV_THRESHOLD; } });
Object.defineProperty(exports, "GENUINE_FRACTAL_MIN", { enumerable: true, get: function () { return driftTracker_js_1.GENUINE_FRACTAL_MIN; } });
// ═══════════════════════════════════════════════════════════════
// Sheaf Cohomology — Tarski Laplacian on Lattice-Valued Sheaves
// ═══════════════════════════════════════════════════════════════
var sheafCohomology_js_1 = require("./sheafCohomology.js");
// Lattice implementations
Object.defineProperty(exports, "BooleanLattice", { enumerable: true, get: function () { return sheafCohomology_js_1.BooleanLattice; } });
Object.defineProperty(exports, "IntervalLattice", { enumerable: true, get: function () { return sheafCohomology_js_1.IntervalLattice; } });
Object.defineProperty(exports, "PowerSetLattice", { enumerable: true, get: function () { return sheafCohomology_js_1.PowerSetLattice; } });
Object.defineProperty(exports, "UnitIntervalLattice", { enumerable: true, get: function () { return sheafCohomology_js_1.UnitIntervalLattice; } });
Object.defineProperty(exports, "ProductLattice", { enumerable: true, get: function () { return sheafCohomology_js_1.ProductLattice; } });
// Galois connections
Object.defineProperty(exports, "identityConnection", { enumerable: true, get: function () { return sheafCohomology_js_1.identityConnection; } });
Object.defineProperty(exports, "constantConnection", { enumerable: true, get: function () { return sheafCohomology_js_1.constantConnection; } });
Object.defineProperty(exports, "thresholdConnection", { enumerable: true, get: function () { return sheafCohomology_js_1.thresholdConnection; } });
Object.defineProperty(exports, "scalingConnection", { enumerable: true, get: function () { return sheafCohomology_js_1.scalingConnection; } });
// Cell complex builders
Object.defineProperty(exports, "graphComplex", { enumerable: true, get: function () { return sheafCohomology_js_1.graphComplex; } });
Object.defineProperty(exports, "simplicialComplex", { enumerable: true, get: function () { return sheafCohomology_js_1.simplicialComplex; } });
// Sheaf constructors
Object.defineProperty(exports, "constantSheaf", { enumerable: true, get: function () { return sheafCohomology_js_1.constantSheaf; } });
Object.defineProperty(exports, "thresholdSheaf", { enumerable: true, get: function () { return sheafCohomology_js_1.thresholdSheaf; } });
Object.defineProperty(exports, "twistedSheaf", { enumerable: true, get: function () { return sheafCohomology_js_1.twistedSheaf; } });
// Cochains
Object.defineProperty(exports, "topCochain", { enumerable: true, get: function () { return sheafCohomology_js_1.topCochain; } });
Object.defineProperty(exports, "bottomCochain", { enumerable: true, get: function () { return sheafCohomology_js_1.bottomCochain; } });
// Tarski Laplacian
Object.defineProperty(exports, "tarskiLaplacian", { enumerable: true, get: function () { return sheafCohomology_js_1.tarskiLaplacian; } });
// Cohomology
Object.defineProperty(exports, "tarskiCohomology", { enumerable: true, get: function () { return sheafCohomology_js_1.tarskiCohomology; } });
Object.defineProperty(exports, "globalSections", { enumerable: true, get: function () { return sheafCohomology_js_1.globalSections; } });
// Hodge Laplacians
Object.defineProperty(exports, "upLaplacian", { enumerable: true, get: function () { return sheafCohomology_js_1.upLaplacian; } });
Object.defineProperty(exports, "downLaplacian", { enumerable: true, get: function () { return sheafCohomology_js_1.downLaplacian; } });
Object.defineProperty(exports, "hodgeLaplacian", { enumerable: true, get: function () { return sheafCohomology_js_1.hodgeLaplacian; } });
Object.defineProperty(exports, "hodgeCohomology", { enumerable: true, get: function () { return sheafCohomology_js_1.hodgeCohomology; } });
// Diagnostics
Object.defineProperty(exports, "analyseCohomology", { enumerable: true, get: function () { return sheafCohomology_js_1.analyseCohomology; } });
Object.defineProperty(exports, "detectObstructions", { enumerable: true, get: function () { return sheafCohomology_js_1.detectObstructions; } });
// SCBE Engine
Object.defineProperty(exports, "SheafCohomologyEngine", { enumerable: true, get: function () { return sheafCohomology_js_1.SheafCohomologyEngine; } });
Object.defineProperty(exports, "defaultSheafEngine", { enumerable: true, get: function () { return sheafCohomology_js_1.defaultSheafEngine; } });
// ── PHDM Sheaf Lattice (constraint-based governance routing) ──
var phdmSheafLattice_js_1 = require("./phdmSheafLattice.js");
Object.defineProperty(exports, "PHDMGovernanceRouter", { enumerable: true, get: function () { return phdmSheafLattice_js_1.PHDMGovernanceRouter; } });
Object.defineProperty(exports, "buildPolyhedralGraph", { enumerable: true, get: function () { return phdmSheafLattice_js_1.buildPolyhedralGraph; } });
Object.defineProperty(exports, "buildGovernanceSheaf", { enumerable: true, get: function () { return phdmSheafLattice_js_1.buildGovernanceSheaf; } });
Object.defineProperty(exports, "computePolyhedralTrust", { enumerable: true, get: function () { return phdmSheafLattice_js_1.computePolyhedralTrust; } });
Object.defineProperty(exports, "polyhedralEulerCharacteristic", { enumerable: true, get: function () { return phdmSheafLattice_js_1.polyhedralEulerCharacteristic; } });
Object.defineProperty(exports, "trustDistanceMatrix", { enumerable: true, get: function () { return phdmSheafLattice_js_1.trustDistanceMatrix; } });
Object.defineProperty(exports, "requiredFluxState", { enumerable: true, get: function () { return phdmSheafLattice_js_1.requiredFluxState; } });
Object.defineProperty(exports, "defaultGovernanceRouter", { enumerable: true, get: function () { return phdmSheafLattice_js_1.defaultGovernanceRouter; } });
//# sourceMappingURL=index.js.map