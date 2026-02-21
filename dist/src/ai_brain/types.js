"use strict";
/**
 * @file types.ts
 * @module ai_brain/types
 * @layer Layer 1-14 (Unified)
 * @component AI Brain Mapping Type Definitions
 * @version 1.1.0
 * @since 2026-02-07
 *
 * Core type definitions for the Multi-Vectored Quasi-Space Architecture.
 * Defines the 21D unified brain state manifold and supporting types.
 *
 * Dimensions:
 *   SCBE Context (6D): device, location, network, behavior, time, intent
 *   Dual Lattice Navigation (6D): x, y, z, time, priority, confidence
 *   PHDM Cognitive Position (3D): polyhedral x, y, z
 *   Sacred Tongues Semantic Phase (3D): active tongue, phase angle, weight
 *   Swarm Coordination (3D): trust score, byzantine votes, spectral coherence
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.DEFAULT_BRAIN_CONFIG = exports.BLOCK_RANGES = exports.POINCARE_MAX_NORM = exports.BRAIN_EPSILON = exports.PHI = exports.BRAIN_DIMENSIONS = void 0;
/** Total dimensionality of the unified brain manifold */
exports.BRAIN_DIMENSIONS = 21;
/** Golden ratio constant */
exports.PHI = (1 + Math.sqrt(5)) / 2;
/** Small epsilon for numerical stability */
exports.BRAIN_EPSILON = 1e-10;
/** Maximum norm for Poincare ball containment */
exports.POINCARE_MAX_NORM = 1 - 1e-8;
// ═══════════════════════════════════════════════════════════════
// Named Block Structure (Maximum Build)
// ═══════════════════════════════════════════════════════════════
/**
 * Named block index ranges for the 21D state vector.
 * Provides a secondary "conservation law" view of the same vector
 * produced by UnifiedBrainState.toVector().
 *
 * BLOCK_HYPER   [0..5]   — Poincare ball coordinates (scbeContext)
 * BLOCK_PHASE   [6..11]  — Tongue phase angles, Z_6 quantized (navigation)
 * BLOCK_HAM     [12..15] — Hamiltonian momenta (cognitivePosition + activeTongue)
 * BLOCK_LATTICE [16..17] — Lattice path indices (phaseAngle + tongueWeight)
 * BLOCK_FLUX    [18]     — Breathing/flux scalar (trustScore)
 * BLOCK_SPEC    [19..20] — Spectral summary: PR + entropy (byzantineVotes + spectralCoherence)
 */
exports.BLOCK_RANGES = {
    BLOCK_HYPER: { start: 0, end: 6 },
    BLOCK_PHASE: { start: 6, end: 12 },
    BLOCK_HAM: { start: 12, end: 16 },
    BLOCK_LATTICE: { start: 16, end: 18 },
    BLOCK_FLUX: { start: 18, end: 19 },
    BLOCK_SPEC: { start: 19, end: 21 },
};
/**
 * Default brain configuration
 */
exports.DEFAULT_BRAIN_CONFIG = {
    boundaryEpsilon: 1e-8,
    detectionThreshold: 0.7,
    quarantineThreshold: 0.5,
    escalateThreshold: 0.7,
    denyThreshold: 0.9,
    maxByzantineFaults: 1,
    curvatureWindow: 10,
    referenceFrequency: 440,
    harmonicR: 1.5,
};
//# sourceMappingURL=types.js.map