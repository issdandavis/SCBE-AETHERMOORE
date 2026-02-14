"use strict";
/**
 * @file index.ts
 * @module ai_brain
 * @layer Layer 1-14 (Unified)
 * @component AI Brain Mapping Module
 * @version 1.2.0
 * @since 2026-02-07
 *
 * Complete AI Brain Mapping - Multi-Vectored Quasi-Space Architecture
 * with Lattice Mesh Integration.
 *
 * Unifies all SCBE-AETHERMOORE components into a single coherent "AI brain"
 * architecture operating across a 21D manifold.
 *
 * Components:
 * - Unified Brain State (21D): SCBE(6) + Navigation(6) + Cognitive(3) + Semantic(3) + Swarm(3)
 * - 5 Orthogonal Detection Mechanisms (combined AUC: 1.000)
 * - BFT Consensus (corrected: 3f+1 formula)
 * - Quasicrystal Icosahedral Projection
 * - Cryptographic Audit Logger
 * - Trajectory Simulator (multi-profile agent behavior)
 * - Immune Response System (GeoSeal suspicion/quarantine)
 * - Flux State Management (POLLY/QUASI/DEMI/COLLAPSED tiered access)
 * - Swarm Formation Coordination (geometric governance formations)
 * - Brain Integration Pipeline (end-to-end unified pipeline)
 * - PHDM Core (Hamiltonian path + Kyber K₀ + geodesic monitoring + Langues metric)
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.DEFAULT_TOI_CONFIG = exports.meetsGenesisThreshold = exports.computeHatchWeight = exports.evaluateTimeOverIntent = exports.toiTriadicDistance = exports.harmonicWallTOI = exports.computeEffectiveR = exports.positiveKappa = exports.computeTriadicWeights = exports.computeGamma = exports.computeTimeDilation = exports.BLOCK_RANGES = exports.enforceConservationLaws = exports.conservationRefactorAlign = exports.computeGlobalInvariant = exports.projectSpectralBounds = exports.projectFluxNormalization = exports.projectLatticeContinuity = exports.projectEnergyBalance = exports.projectPhaseCoherence = exports.projectContainment = exports.replaceBlock = exports.extractBlock = exports.BrainAuditLogger = exports.quasicrystalPotential = exports.octreeInsert = exports.icosahedralProjection = exports.createOctreeRoot = exports.classifyVoxelRealm = exports.brainStateToPenrose = exports.BFTConsensus = exports.runCombinedDetection = exports.detectThreatLissajous = exports.detectSixTonic = exports.detectPhaseDistance = exports.detectDecimalDrift = exports.detectCurvatureAccumulation = exports.vectorNorm = exports.safePoincareEmbed = exports.mobiusAddSafe = exports.hyperbolicDistanceSafe = exports.goldenWeightProduct = exports.euclideanDistance = exports.applyGoldenWeighting = exports.UnifiedBrainState = exports.POINCARE_MAX_NORM = exports.PHI = exports.DEFAULT_BRAIN_CONFIG = exports.BRAIN_EPSILON = exports.BRAIN_DIMENSIONS = void 0;
exports.dualTernaryTransition = exports.stateIndex = exports.stateFromIndex = exports.estimateTernaryFractalDimension = exports.encodeDualTernarySequence = exports.encodeToDualTernary = exports.computeStateEnergy = exports.computeDualTernarySpectrum = exports.FULL_STATE_SPACE = exports.DualTernarySystem = exports.DEFAULT_DUAL_TERNARY_CONFIG = exports.applyPhasonShift = exports.staticProjection = exports.latticeNorm6D = exports.latticeDistance3D = exports.generateAperiodicMesh = exports.estimateLatticeFractalDimension = exports.dynamicTransform = exports.DualLatticeSystem = exports.DEFAULT_DUAL_LATTICE_CONFIG = exports.HiveImmuneSystem = exports.DEFAULT_HIVE_CONFIG = exports.CASTE_PROFILES = exports.deriveK0 = exports.decomposeLangues = exports.brainStateToLangues = exports.TONGUE_LABELS = exports.TEMPORAL_TONGUES = exports.PHDMCore = exports.INTENT_TONGUES = exports.DEFAULT_PHDM_CORE_CONFIG = exports.DEFAULT_INTEGRATION_CONFIG = exports.BrainIntegrationPipeline = exports.SwarmFormationManager = exports.DEFAULT_SWARM_CONFIG = exports.POLYHEDRA = exports.FluxStateManager = exports.DEFAULT_FLUX_CONFIG = exports.ImmuneResponseSystem = exports.DEFAULT_IMMUNE_CONFIG = exports.generateTrajectory = exports.generateMixedBatch = exports.SeededRNG = exports.AGENT_PROFILES = exports.DEFAULT_ENTROPIC_CONFIG = exports.MAX_K = exports.MIN_K = exports.DEFAULT_MAX_VOLUME = exports.EntropicLayer = exports.HyperbolicRAG = void 0;
exports.estimateNodalDensity = exports.dominantTongue = exports.classifyZone = exports.chladni6D = exports.VOXEL_DIMS = exports.TONGUE_DIMENSION_MAP = exports.SACRED_TONGUES = exports.REALM_CENTERS = exports.NODAL_THRESHOLD = exports.CymaticVoxelNet = exports.triadicPartial = exports.triadicDistance = exports.harmonicScaleTable = exports.harmonicScaleInverse = exports.harmonicScale = exports.TriManifoldLattice = exports.TemporalWindow = exports.MAX_LATTICE_DEPTH = exports.HARMONIC_R = exports.DEFAULT_WINDOW_SIZES = exports.DEFAULT_TRIADIC_WEIGHTS = exports.torusWriteGate = exports.computeMetrics = exports.UnifiedKernel = exports.DEFAULT_KERNEL_CONFIG = exports.zeroGravityDistance = exports.ternaryCenter = exports.braidRefactorAlign = exports.braidQuantizeVector = exports.braidQuantize = exports.phaseDeviation = exports.phaseAwareProject = exports.mirrorSwap = exports.mirrorShift = exports.isValidBraidTransition = exports.isInsideTube = exports.hyperbolicDistance2D = exports.harmonicTubeCost = exports.estimateBraidFractalDimension = exports.dBraid = exports.computeRailCenters = exports.classifyBraidState = exports.buildGovernance = exports.braidTrustLevel = exports.braidStateDistance = exports.braidSecurityAction = exports.DEFAULT_BRAID_CONFIG = exports.BRAID_RAIL_CENTERS = exports.BRAID_GOVERNANCE_TABLE = exports.AetherBraid = void 0;
// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════
var types_js_1 = require("./types.js");
Object.defineProperty(exports, "BRAIN_DIMENSIONS", { enumerable: true, get: function () { return types_js_1.BRAIN_DIMENSIONS; } });
Object.defineProperty(exports, "BRAIN_EPSILON", { enumerable: true, get: function () { return types_js_1.BRAIN_EPSILON; } });
Object.defineProperty(exports, "DEFAULT_BRAIN_CONFIG", { enumerable: true, get: function () { return types_js_1.DEFAULT_BRAIN_CONFIG; } });
Object.defineProperty(exports, "PHI", { enumerable: true, get: function () { return types_js_1.PHI; } });
Object.defineProperty(exports, "POINCARE_MAX_NORM", { enumerable: true, get: function () { return types_js_1.POINCARE_MAX_NORM; } });
// ═══════════════════════════════════════════════════════════════
// Unified Brain State (21D Manifold)
// ═══════════════════════════════════════════════════════════════
var unified_state_js_1 = require("./unified-state.js");
Object.defineProperty(exports, "UnifiedBrainState", { enumerable: true, get: function () { return unified_state_js_1.UnifiedBrainState; } });
Object.defineProperty(exports, "applyGoldenWeighting", { enumerable: true, get: function () { return unified_state_js_1.applyGoldenWeighting; } });
Object.defineProperty(exports, "euclideanDistance", { enumerable: true, get: function () { return unified_state_js_1.euclideanDistance; } });
Object.defineProperty(exports, "goldenWeightProduct", { enumerable: true, get: function () { return unified_state_js_1.goldenWeightProduct; } });
Object.defineProperty(exports, "hyperbolicDistanceSafe", { enumerable: true, get: function () { return unified_state_js_1.hyperbolicDistanceSafe; } });
Object.defineProperty(exports, "mobiusAddSafe", { enumerable: true, get: function () { return unified_state_js_1.mobiusAddSafe; } });
Object.defineProperty(exports, "safePoincareEmbed", { enumerable: true, get: function () { return unified_state_js_1.safePoincareEmbed; } });
Object.defineProperty(exports, "vectorNorm", { enumerable: true, get: function () { return unified_state_js_1.vectorNorm; } });
// ═══════════════════════════════════════════════════════════════
// Detection Mechanisms
// ═══════════════════════════════════════════════════════════════
var detection_js_1 = require("./detection.js");
Object.defineProperty(exports, "detectCurvatureAccumulation", { enumerable: true, get: function () { return detection_js_1.detectCurvatureAccumulation; } });
Object.defineProperty(exports, "detectDecimalDrift", { enumerable: true, get: function () { return detection_js_1.detectDecimalDrift; } });
Object.defineProperty(exports, "detectPhaseDistance", { enumerable: true, get: function () { return detection_js_1.detectPhaseDistance; } });
Object.defineProperty(exports, "detectSixTonic", { enumerable: true, get: function () { return detection_js_1.detectSixTonic; } });
Object.defineProperty(exports, "detectThreatLissajous", { enumerable: true, get: function () { return detection_js_1.detectThreatLissajous; } });
Object.defineProperty(exports, "runCombinedDetection", { enumerable: true, get: function () { return detection_js_1.runCombinedDetection; } });
// ═══════════════════════════════════════════════════════════════
// BFT Consensus
// ═══════════════════════════════════════════════════════════════
var bft_consensus_js_1 = require("./bft-consensus.js");
Object.defineProperty(exports, "BFTConsensus", { enumerable: true, get: function () { return bft_consensus_js_1.BFTConsensus; } });
// ═══════════════════════════════════════════════════════════════
// Quasi-Space Projection
// ═══════════════════════════════════════════════════════════════
var quasi_space_js_1 = require("./quasi-space.js");
Object.defineProperty(exports, "brainStateToPenrose", { enumerable: true, get: function () { return quasi_space_js_1.brainStateToPenrose; } });
Object.defineProperty(exports, "classifyVoxelRealm", { enumerable: true, get: function () { return quasi_space_js_1.classifyVoxelRealm; } });
Object.defineProperty(exports, "createOctreeRoot", { enumerable: true, get: function () { return quasi_space_js_1.createOctreeRoot; } });
Object.defineProperty(exports, "icosahedralProjection", { enumerable: true, get: function () { return quasi_space_js_1.icosahedralProjection; } });
Object.defineProperty(exports, "octreeInsert", { enumerable: true, get: function () { return quasi_space_js_1.octreeInsert; } });
Object.defineProperty(exports, "quasicrystalPotential", { enumerable: true, get: function () { return quasi_space_js_1.quasicrystalPotential; } });
// ═══════════════════════════════════════════════════════════════
// Audit Logger
// ═══════════════════════════════════════════════════════════════
var audit_js_1 = require("./audit.js");
Object.defineProperty(exports, "BrainAuditLogger", { enumerable: true, get: function () { return audit_js_1.BrainAuditLogger; } });
// ═══════════════════════════════════════════════════════════════
// Conservation Law Enforcement (Maximum Build)
// ═══════════════════════════════════════════════════════════════
var conservation_js_1 = require("./conservation.js");
Object.defineProperty(exports, "extractBlock", { enumerable: true, get: function () { return conservation_js_1.extractBlock; } });
Object.defineProperty(exports, "replaceBlock", { enumerable: true, get: function () { return conservation_js_1.replaceBlock; } });
Object.defineProperty(exports, "projectContainment", { enumerable: true, get: function () { return conservation_js_1.projectContainment; } });
Object.defineProperty(exports, "projectPhaseCoherence", { enumerable: true, get: function () { return conservation_js_1.projectPhaseCoherence; } });
Object.defineProperty(exports, "projectEnergyBalance", { enumerable: true, get: function () { return conservation_js_1.projectEnergyBalance; } });
Object.defineProperty(exports, "projectLatticeContinuity", { enumerable: true, get: function () { return conservation_js_1.projectLatticeContinuity; } });
Object.defineProperty(exports, "projectFluxNormalization", { enumerable: true, get: function () { return conservation_js_1.projectFluxNormalization; } });
Object.defineProperty(exports, "projectSpectralBounds", { enumerable: true, get: function () { return conservation_js_1.projectSpectralBounds; } });
Object.defineProperty(exports, "computeGlobalInvariant", { enumerable: true, get: function () { return conservation_js_1.computeGlobalInvariant; } });
Object.defineProperty(exports, "conservationRefactorAlign", { enumerable: true, get: function () { return conservation_js_1.refactorAlign; } });
Object.defineProperty(exports, "enforceConservationLaws", { enumerable: true, get: function () { return conservation_js_1.enforceConservationLaws; } });
var types_js_2 = require("./types.js");
Object.defineProperty(exports, "BLOCK_RANGES", { enumerable: true, get: function () { return types_js_2.BLOCK_RANGES; } });
// ═══════════════════════════════════════════════════════════════
// Time-over-Intent Coupling (Maximum Build)
// ═══════════════════════════════════════════════════════════════
var timeOverIntent_js_1 = require("./timeOverIntent.js");
Object.defineProperty(exports, "computeTimeDilation", { enumerable: true, get: function () { return timeOverIntent_js_1.computeTimeDilation; } });
Object.defineProperty(exports, "computeGamma", { enumerable: true, get: function () { return timeOverIntent_js_1.computeGamma; } });
Object.defineProperty(exports, "computeTriadicWeights", { enumerable: true, get: function () { return timeOverIntent_js_1.computeTriadicWeights; } });
Object.defineProperty(exports, "positiveKappa", { enumerable: true, get: function () { return timeOverIntent_js_1.positiveKappa; } });
Object.defineProperty(exports, "computeEffectiveR", { enumerable: true, get: function () { return timeOverIntent_js_1.computeEffectiveR; } });
Object.defineProperty(exports, "harmonicWallTOI", { enumerable: true, get: function () { return timeOverIntent_js_1.harmonicWallTOI; } });
Object.defineProperty(exports, "toiTriadicDistance", { enumerable: true, get: function () { return timeOverIntent_js_1.triadicDistance; } });
Object.defineProperty(exports, "evaluateTimeOverIntent", { enumerable: true, get: function () { return timeOverIntent_js_1.evaluateTimeOverIntent; } });
Object.defineProperty(exports, "computeHatchWeight", { enumerable: true, get: function () { return timeOverIntent_js_1.computeHatchWeight; } });
Object.defineProperty(exports, "meetsGenesisThreshold", { enumerable: true, get: function () { return timeOverIntent_js_1.meetsGenesisThreshold; } });
Object.defineProperty(exports, "DEFAULT_TOI_CONFIG", { enumerable: true, get: function () { return timeOverIntent_js_1.DEFAULT_TOI_CONFIG; } });
// ═══════════════════════════════════════════════════════════════
// HyperbolicRAG (Layer 12 cost-gated retrieval)
// ═══════════════════════════════════════════════════════════════
var hyperbolic_rag_js_1 = require("./hyperbolic-rag.js");
Object.defineProperty(exports, "HyperbolicRAG", { enumerable: true, get: function () { return hyperbolic_rag_js_1.HyperbolicRAG; } });
// ═══════════════════════════════════════════════════════════════
// EntropicLayer (Layer 12-13 escape detection + adaptive-k)
// ═══════════════════════════════════════════════════════════════
var entropic_layer_js_1 = require("./entropic-layer.js");
Object.defineProperty(exports, "EntropicLayer", { enumerable: true, get: function () { return entropic_layer_js_1.EntropicLayer; } });
Object.defineProperty(exports, "DEFAULT_MAX_VOLUME", { enumerable: true, get: function () { return entropic_layer_js_1.DEFAULT_MAX_VOLUME; } });
Object.defineProperty(exports, "MIN_K", { enumerable: true, get: function () { return entropic_layer_js_1.MIN_K; } });
Object.defineProperty(exports, "MAX_K", { enumerable: true, get: function () { return entropic_layer_js_1.MAX_K; } });
Object.defineProperty(exports, "DEFAULT_ENTROPIC_CONFIG", { enumerable: true, get: function () { return entropic_layer_js_1.DEFAULT_ENTROPIC_CONFIG; } });
// ═══════════════════════════════════════════════════════════════
// Trajectory Simulator
// ═══════════════════════════════════════════════════════════════
var trajectory_simulator_js_1 = require("./trajectory-simulator.js");
Object.defineProperty(exports, "AGENT_PROFILES", { enumerable: true, get: function () { return trajectory_simulator_js_1.AGENT_PROFILES; } });
Object.defineProperty(exports, "SeededRNG", { enumerable: true, get: function () { return trajectory_simulator_js_1.SeededRNG; } });
Object.defineProperty(exports, "generateMixedBatch", { enumerable: true, get: function () { return trajectory_simulator_js_1.generateMixedBatch; } });
Object.defineProperty(exports, "generateTrajectory", { enumerable: true, get: function () { return trajectory_simulator_js_1.generateTrajectory; } });
// ═══════════════════════════════════════════════════════════════
// Immune Response System
// ═══════════════════════════════════════════════════════════════
var immune_response_js_1 = require("./immune-response.js");
Object.defineProperty(exports, "DEFAULT_IMMUNE_CONFIG", { enumerable: true, get: function () { return immune_response_js_1.DEFAULT_IMMUNE_CONFIG; } });
Object.defineProperty(exports, "ImmuneResponseSystem", { enumerable: true, get: function () { return immune_response_js_1.ImmuneResponseSystem; } });
// ═══════════════════════════════════════════════════════════════
// Flux State Management
// ═══════════════════════════════════════════════════════════════
var flux_states_js_1 = require("./flux-states.js");
Object.defineProperty(exports, "DEFAULT_FLUX_CONFIG", { enumerable: true, get: function () { return flux_states_js_1.DEFAULT_FLUX_CONFIG; } });
Object.defineProperty(exports, "FluxStateManager", { enumerable: true, get: function () { return flux_states_js_1.FluxStateManager; } });
Object.defineProperty(exports, "POLYHEDRA", { enumerable: true, get: function () { return flux_states_js_1.POLYHEDRA; } });
// ═══════════════════════════════════════════════════════════════
// Swarm Formation Coordination
// ═══════════════════════════════════════════════════════════════
var swarm_formation_js_1 = require("./swarm-formation.js");
Object.defineProperty(exports, "DEFAULT_SWARM_CONFIG", { enumerable: true, get: function () { return swarm_formation_js_1.DEFAULT_SWARM_CONFIG; } });
Object.defineProperty(exports, "SwarmFormationManager", { enumerable: true, get: function () { return swarm_formation_js_1.SwarmFormationManager; } });
// ═══════════════════════════════════════════════════════════════
// Brain Integration Pipeline
// ═══════════════════════════════════════════════════════════════
var brain_integration_js_1 = require("./brain-integration.js");
Object.defineProperty(exports, "BrainIntegrationPipeline", { enumerable: true, get: function () { return brain_integration_js_1.BrainIntegrationPipeline; } });
Object.defineProperty(exports, "DEFAULT_INTEGRATION_CONFIG", { enumerable: true, get: function () { return brain_integration_js_1.DEFAULT_INTEGRATION_CONFIG; } });
// ═══════════════════════════════════════════════════════════════
// PHDM Core (Polyhedral Hamiltonian Defense Manifold Integration)
// ═══════════════════════════════════════════════════════════════
var phdm_core_js_1 = require("./phdm-core.js");
Object.defineProperty(exports, "DEFAULT_PHDM_CORE_CONFIG", { enumerable: true, get: function () { return phdm_core_js_1.DEFAULT_PHDM_CORE_CONFIG; } });
Object.defineProperty(exports, "INTENT_TONGUES", { enumerable: true, get: function () { return phdm_core_js_1.INTENT_TONGUES; } });
Object.defineProperty(exports, "PHDMCore", { enumerable: true, get: function () { return phdm_core_js_1.PHDMCore; } });
Object.defineProperty(exports, "TEMPORAL_TONGUES", { enumerable: true, get: function () { return phdm_core_js_1.TEMPORAL_TONGUES; } });
Object.defineProperty(exports, "TONGUE_LABELS", { enumerable: true, get: function () { return phdm_core_js_1.TONGUE_LABELS; } });
Object.defineProperty(exports, "brainStateToLangues", { enumerable: true, get: function () { return phdm_core_js_1.brainStateToLangues; } });
Object.defineProperty(exports, "decomposeLangues", { enumerable: true, get: function () { return phdm_core_js_1.decomposeLangues; } });
Object.defineProperty(exports, "deriveK0", { enumerable: true, get: function () { return phdm_core_js_1.deriveK0; } });
// ═══════════════════════════════════════════════════════════════
// Bee-Colony Tiered Immune System
// ═══════════════════════════════════════════════════════════════
var bee_immune_tiers_js_1 = require("./bee-immune-tiers.js");
Object.defineProperty(exports, "CASTE_PROFILES", { enumerable: true, get: function () { return bee_immune_tiers_js_1.CASTE_PROFILES; } });
Object.defineProperty(exports, "DEFAULT_HIVE_CONFIG", { enumerable: true, get: function () { return bee_immune_tiers_js_1.DEFAULT_HIVE_CONFIG; } });
Object.defineProperty(exports, "HiveImmuneSystem", { enumerable: true, get: function () { return bee_immune_tiers_js_1.HiveImmuneSystem; } });
// ═══════════════════════════════════════════════════════════════
// Dual Lattice Architecture (6D↔3D bidirectional projection)
// ═══════════════════════════════════════════════════════════════
var dual_lattice_js_1 = require("./dual-lattice.js");
Object.defineProperty(exports, "DEFAULT_DUAL_LATTICE_CONFIG", { enumerable: true, get: function () { return dual_lattice_js_1.DEFAULT_DUAL_LATTICE_CONFIG; } });
Object.defineProperty(exports, "DualLatticeSystem", { enumerable: true, get: function () { return dual_lattice_js_1.DualLatticeSystem; } });
Object.defineProperty(exports, "dynamicTransform", { enumerable: true, get: function () { return dual_lattice_js_1.dynamicTransform; } });
Object.defineProperty(exports, "estimateLatticeFractalDimension", { enumerable: true, get: function () { return dual_lattice_js_1.estimateFractalDimension; } });
Object.defineProperty(exports, "generateAperiodicMesh", { enumerable: true, get: function () { return dual_lattice_js_1.generateAperiodicMesh; } });
Object.defineProperty(exports, "latticeDistance3D", { enumerable: true, get: function () { return dual_lattice_js_1.latticeDistance3D; } });
Object.defineProperty(exports, "latticeNorm6D", { enumerable: true, get: function () { return dual_lattice_js_1.latticeNorm6D; } });
Object.defineProperty(exports, "staticProjection", { enumerable: true, get: function () { return dual_lattice_js_1.staticProjection; } });
Object.defineProperty(exports, "applyPhasonShift", { enumerable: true, get: function () { return dual_lattice_js_1.applyPhasonShift; } });
// ═══════════════════════════════════════════════════════════════
// Dual Ternary Encoding (Full Negative State Flux)
// ═══════════════════════════════════════════════════════════════
var dual_ternary_js_1 = require("./dual-ternary.js");
Object.defineProperty(exports, "DEFAULT_DUAL_TERNARY_CONFIG", { enumerable: true, get: function () { return dual_ternary_js_1.DEFAULT_DUAL_TERNARY_CONFIG; } });
Object.defineProperty(exports, "DualTernarySystem", { enumerable: true, get: function () { return dual_ternary_js_1.DualTernarySystem; } });
Object.defineProperty(exports, "FULL_STATE_SPACE", { enumerable: true, get: function () { return dual_ternary_js_1.FULL_STATE_SPACE; } });
Object.defineProperty(exports, "computeDualTernarySpectrum", { enumerable: true, get: function () { return dual_ternary_js_1.computeSpectrum; } });
Object.defineProperty(exports, "computeStateEnergy", { enumerable: true, get: function () { return dual_ternary_js_1.computeStateEnergy; } });
Object.defineProperty(exports, "encodeToDualTernary", { enumerable: true, get: function () { return dual_ternary_js_1.encodeToDualTernary; } });
Object.defineProperty(exports, "encodeDualTernarySequence", { enumerable: true, get: function () { return dual_ternary_js_1.encodeSequence; } });
Object.defineProperty(exports, "estimateTernaryFractalDimension", { enumerable: true, get: function () { return dual_ternary_js_1.estimateFractalDimension; } });
Object.defineProperty(exports, "stateFromIndex", { enumerable: true, get: function () { return dual_ternary_js_1.stateFromIndex; } });
Object.defineProperty(exports, "stateIndex", { enumerable: true, get: function () { return dual_ternary_js_1.stateIndex; } });
Object.defineProperty(exports, "dualTernaryTransition", { enumerable: true, get: function () { return dual_ternary_js_1.transition; } });
// ═══════════════════════════════════════════════════════════════
// Hamiltonian Braid (Ternary Spiral Governance)
// ═══════════════════════════════════════════════════════════════
var hamiltonian_braid_js_1 = require("./hamiltonian-braid.js");
Object.defineProperty(exports, "AetherBraid", { enumerable: true, get: function () { return hamiltonian_braid_js_1.AetherBraid; } });
Object.defineProperty(exports, "BRAID_GOVERNANCE_TABLE", { enumerable: true, get: function () { return hamiltonian_braid_js_1.BRAID_GOVERNANCE_TABLE; } });
Object.defineProperty(exports, "BRAID_RAIL_CENTERS", { enumerable: true, get: function () { return hamiltonian_braid_js_1.BRAID_RAIL_CENTERS; } });
Object.defineProperty(exports, "DEFAULT_BRAID_CONFIG", { enumerable: true, get: function () { return hamiltonian_braid_js_1.DEFAULT_BRAID_CONFIG; } });
Object.defineProperty(exports, "braidSecurityAction", { enumerable: true, get: function () { return hamiltonian_braid_js_1.braidSecurityAction; } });
Object.defineProperty(exports, "braidStateDistance", { enumerable: true, get: function () { return hamiltonian_braid_js_1.braidStateDistance; } });
Object.defineProperty(exports, "braidTrustLevel", { enumerable: true, get: function () { return hamiltonian_braid_js_1.braidTrustLevel; } });
Object.defineProperty(exports, "buildGovernance", { enumerable: true, get: function () { return hamiltonian_braid_js_1.buildGovernance; } });
Object.defineProperty(exports, "classifyBraidState", { enumerable: true, get: function () { return hamiltonian_braid_js_1.classifyBraidState; } });
Object.defineProperty(exports, "computeRailCenters", { enumerable: true, get: function () { return hamiltonian_braid_js_1.computeRailCenters; } });
Object.defineProperty(exports, "dBraid", { enumerable: true, get: function () { return hamiltonian_braid_js_1.dBraid; } });
Object.defineProperty(exports, "estimateBraidFractalDimension", { enumerable: true, get: function () { return hamiltonian_braid_js_1.estimateBraidFractalDimension; } });
Object.defineProperty(exports, "harmonicTubeCost", { enumerable: true, get: function () { return hamiltonian_braid_js_1.harmonicTubeCost; } });
Object.defineProperty(exports, "hyperbolicDistance2D", { enumerable: true, get: function () { return hamiltonian_braid_js_1.hyperbolicDistance2D; } });
Object.defineProperty(exports, "isInsideTube", { enumerable: true, get: function () { return hamiltonian_braid_js_1.isInsideTube; } });
Object.defineProperty(exports, "isValidBraidTransition", { enumerable: true, get: function () { return hamiltonian_braid_js_1.isValidBraidTransition; } });
Object.defineProperty(exports, "mirrorShift", { enumerable: true, get: function () { return hamiltonian_braid_js_1.mirrorShift; } });
Object.defineProperty(exports, "mirrorSwap", { enumerable: true, get: function () { return hamiltonian_braid_js_1.mirrorSwap; } });
Object.defineProperty(exports, "phaseAwareProject", { enumerable: true, get: function () { return hamiltonian_braid_js_1.phaseAwareProject; } });
Object.defineProperty(exports, "phaseDeviation", { enumerable: true, get: function () { return hamiltonian_braid_js_1.phaseDeviation; } });
Object.defineProperty(exports, "braidQuantize", { enumerable: true, get: function () { return hamiltonian_braid_js_1.quantize; } });
Object.defineProperty(exports, "braidQuantizeVector", { enumerable: true, get: function () { return hamiltonian_braid_js_1.quantizeVector; } });
Object.defineProperty(exports, "braidRefactorAlign", { enumerable: true, get: function () { return hamiltonian_braid_js_1.refactorAlign; } });
Object.defineProperty(exports, "ternaryCenter", { enumerable: true, get: function () { return hamiltonian_braid_js_1.ternaryCenter; } });
Object.defineProperty(exports, "zeroGravityDistance", { enumerable: true, get: function () { return hamiltonian_braid_js_1.zeroGravityDistance; } });
// ═══════════════════════════════════════════════════════════════
// Unified Kernel (Pipeline Runner / Integration Spine)
// ═══════════════════════════════════════════════════════════════
var unified_kernel_js_1 = require("./unified-kernel.js");
Object.defineProperty(exports, "DEFAULT_KERNEL_CONFIG", { enumerable: true, get: function () { return unified_kernel_js_1.DEFAULT_KERNEL_CONFIG; } });
Object.defineProperty(exports, "UnifiedKernel", { enumerable: true, get: function () { return unified_kernel_js_1.UnifiedKernel; } });
Object.defineProperty(exports, "computeMetrics", { enumerable: true, get: function () { return unified_kernel_js_1.computeMetrics; } });
Object.defineProperty(exports, "torusWriteGate", { enumerable: true, get: function () { return unified_kernel_js_1.torusWriteGate; } });
// ═══════════════════════════════════════════════════════════════
// Tri-Manifold Lattice (Temporal Harmonic Governance)
// ═══════════════════════════════════════════════════════════════
var tri_manifold_lattice_js_1 = require("./tri-manifold-lattice.js");
Object.defineProperty(exports, "DEFAULT_TRIADIC_WEIGHTS", { enumerable: true, get: function () { return tri_manifold_lattice_js_1.DEFAULT_TRIADIC_WEIGHTS; } });
Object.defineProperty(exports, "DEFAULT_WINDOW_SIZES", { enumerable: true, get: function () { return tri_manifold_lattice_js_1.DEFAULT_WINDOW_SIZES; } });
Object.defineProperty(exports, "HARMONIC_R", { enumerable: true, get: function () { return tri_manifold_lattice_js_1.HARMONIC_R; } });
Object.defineProperty(exports, "MAX_LATTICE_DEPTH", { enumerable: true, get: function () { return tri_manifold_lattice_js_1.MAX_LATTICE_DEPTH; } });
Object.defineProperty(exports, "TemporalWindow", { enumerable: true, get: function () { return tri_manifold_lattice_js_1.TemporalWindow; } });
Object.defineProperty(exports, "TriManifoldLattice", { enumerable: true, get: function () { return tri_manifold_lattice_js_1.TriManifoldLattice; } });
Object.defineProperty(exports, "harmonicScale", { enumerable: true, get: function () { return tri_manifold_lattice_js_1.harmonicScale; } });
Object.defineProperty(exports, "harmonicScaleInverse", { enumerable: true, get: function () { return tri_manifold_lattice_js_1.harmonicScaleInverse; } });
Object.defineProperty(exports, "harmonicScaleTable", { enumerable: true, get: function () { return tri_manifold_lattice_js_1.harmonicScaleTable; } });
Object.defineProperty(exports, "triadicDistance", { enumerable: true, get: function () { return tri_manifold_lattice_js_1.triadicDistance; } });
Object.defineProperty(exports, "triadicPartial", { enumerable: true, get: function () { return tri_manifold_lattice_js_1.triadicPartial; } });
// ═══════════════════════════════════════════════════════════════
// Cymatic Voxel Neural Network (6D Chladni Nodal Auto-Propagation)
// ═══════════════════════════════════════════════════════════════
var cymatic_voxel_net_js_1 = require("./cymatic-voxel-net.js");
Object.defineProperty(exports, "CymaticVoxelNet", { enumerable: true, get: function () { return cymatic_voxel_net_js_1.CymaticVoxelNet; } });
Object.defineProperty(exports, "NODAL_THRESHOLD", { enumerable: true, get: function () { return cymatic_voxel_net_js_1.NODAL_THRESHOLD; } });
Object.defineProperty(exports, "REALM_CENTERS", { enumerable: true, get: function () { return cymatic_voxel_net_js_1.REALM_CENTERS; } });
Object.defineProperty(exports, "SACRED_TONGUES", { enumerable: true, get: function () { return cymatic_voxel_net_js_1.SACRED_TONGUES; } });
Object.defineProperty(exports, "TONGUE_DIMENSION_MAP", { enumerable: true, get: function () { return cymatic_voxel_net_js_1.TONGUE_DIMENSION_MAP; } });
Object.defineProperty(exports, "VOXEL_DIMS", { enumerable: true, get: function () { return cymatic_voxel_net_js_1.VOXEL_DIMS; } });
Object.defineProperty(exports, "chladni6D", { enumerable: true, get: function () { return cymatic_voxel_net_js_1.chladni6D; } });
Object.defineProperty(exports, "classifyZone", { enumerable: true, get: function () { return cymatic_voxel_net_js_1.classifyZone; } });
Object.defineProperty(exports, "dominantTongue", { enumerable: true, get: function () { return cymatic_voxel_net_js_1.dominantTongue; } });
Object.defineProperty(exports, "estimateNodalDensity", { enumerable: true, get: function () { return cymatic_voxel_net_js_1.estimateNodalDensity; } });
//# sourceMappingURL=index.js.map