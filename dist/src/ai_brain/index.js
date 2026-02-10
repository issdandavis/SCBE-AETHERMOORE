"use strict";
/**
 * @file index.ts
 * @module ai_brain
 * @layer Layer 1-14 (Unified)
 * @component AI Brain Mapping Module
 * @version 1.1.0
 * @since 2026-02-07
 *
 * Multi-Vectored Quasi-Space Architecture with Lattice Mesh Integration.
 * Unifies all SCBE-AETHERMOORE components into a single coherent "AI brain"
 * architecture operating across a 21D manifold.
 *
 * Components:
 * - Unified Brain State (21D): SCBE(6) + Navigation(6) + Cognitive(3) + Semantic(3) + Swarm(3)
 * - 5 Orthogonal Detection Mechanisms (combined AUC: 1.000)
 * - BFT Consensus (corrected: 3f+1 formula)
 * - Quasicrystal Icosahedral Projection
 * - Cryptographic Audit Logger
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.BrainAuditLogger = exports.quasicrystalPotential = exports.octreeInsert = exports.icosahedralProjection = exports.createOctreeRoot = exports.classifyVoxelRealm = exports.brainStateToPenrose = exports.BFTConsensus = exports.runCombinedDetection = exports.detectThreatLissajous = exports.detectSixTonic = exports.detectPhaseDistance = exports.detectDecimalDrift = exports.detectCurvatureAccumulation = exports.vectorNorm = exports.safePoincareEmbed = exports.mobiusAddSafe = exports.hyperbolicDistanceSafe = exports.goldenWeightProduct = exports.euclideanDistance = exports.applyGoldenWeighting = exports.UnifiedBrainState = exports.POINCARE_MAX_NORM = exports.PHI = exports.DEFAULT_BRAIN_CONFIG = exports.BRAIN_EPSILON = exports.BRAIN_DIMENSIONS = void 0;
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
//# sourceMappingURL=index.js.map