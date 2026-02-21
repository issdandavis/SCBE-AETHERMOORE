"use strict";
/**
 * Agent Types for SCBE-AETHERMOORE
 *
 * Defines agent structures with:
 * - Six Sacred Tongues identity
 * - Three-tier IP classification (Public/Private/Hidden)
 * - Poincaré ball positioning
 * - Quantum-safe cryptographic keys
 *
 * @module agent/types
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.COHERENCE_DECAY_RATE = exports.AGENT_TIMEOUT_MS = exports.HEARTBEAT_INTERVAL_MS = exports.TONGUE_IP_TIERS = exports.TONGUE_INDICES = exports.TONGUE_PHASES = exports.GOLDEN_RATIO = void 0;
exports.calculateTongueWeight = calculateTongueWeight;
exports.phaseToRadians = phaseToRadians;
exports.poincareNorm = poincareNorm;
exports.isValidPoincarePosition = isValidPoincarePosition;
exports.hyperbolicDistance = hyperbolicDistance;
exports.harmonicWallCost = harmonicWallCost;
exports.generateInitialPosition = generateInitialPosition;
exports.calculateBFTQuorum = calculateBFTQuorum;
// ============================================================================
// Constants
// ============================================================================
/** Golden ratio for tongue weight calculations */
exports.GOLDEN_RATIO = 1.6180339887498949;
/** Phase offsets for each tongue (degrees) */
exports.TONGUE_PHASES = {
    KO: 0,
    AV: 60,
    RU: 120,
    CA: 180,
    UM: 240,
    DR: 300,
};
/** Tongue indices for weight calculation (φⁿ) */
exports.TONGUE_INDICES = {
    KO: 0,
    AV: 1,
    RU: 2,
    CA: 3,
    UM: 4,
    DR: 5,
};
/** Default IP tier mapping for tongues */
exports.TONGUE_IP_TIERS = {
    KO: 'public', // Control/Orchestration - public gateway
    AV: 'private', // Transport/Init - internal mesh
    RU: 'private', // Policy/Rules - internal mesh
    CA: 'private', // Compute/Encryption - internal mesh
    UM: 'hidden', // Security/Redaction - air-gapped
    DR: 'hidden', // Schema/Auth - air-gapped
};
/** Heartbeat interval in milliseconds */
exports.HEARTBEAT_INTERVAL_MS = 5000;
/** Agent timeout threshold (no heartbeat) */
exports.AGENT_TIMEOUT_MS = 15000;
/** Coherence decay rate per second */
exports.COHERENCE_DECAY_RATE = 0.001;
// ============================================================================
// Utility Functions
// ============================================================================
/**
 * Calculate tongue weight using golden ratio
 */
function calculateTongueWeight(tongue) {
    return Math.pow(exports.GOLDEN_RATIO, exports.TONGUE_INDICES[tongue]);
}
/**
 * Convert phase from degrees to radians
 */
function phaseToRadians(tongue) {
    return (exports.TONGUE_PHASES[tongue] * Math.PI) / 180;
}
/**
 * Calculate Poincaré ball norm
 */
function poincareNorm(pos) {
    return Math.sqrt(pos.x * pos.x + pos.y * pos.y + pos.z * pos.z);
}
/**
 * Validate position is within Poincaré ball
 */
function isValidPoincarePosition(pos) {
    return poincareNorm(pos) < 1;
}
/**
 * Calculate hyperbolic distance between two points
 */
function hyperbolicDistance(u, v) {
    const uNorm = poincareNorm(u);
    const vNorm = poincareNorm(v);
    if (uNorm >= 1 || vNorm >= 1) {
        return Infinity;
    }
    const diffX = u.x - v.x;
    const diffY = u.y - v.y;
    const diffZ = u.z - v.z;
    const diffNormSq = diffX * diffX + diffY * diffY + diffZ * diffZ;
    const denominator = (1 - uNorm * uNorm) * (1 - vNorm * vNorm);
    const argument = 1 + (2 * diffNormSq) / denominator;
    return Math.acosh(argument);
}
/**
 * Calculate Harmonic Wall cost
 * score = exp(d_H + 2 * phaseDeviation)
 */
function harmonicWallCost(distance, phaseDeviation = 0) {
    return Math.exp(distance + 2 * phaseDeviation);
}
/**
 * Generate initial position for tongue in Poincaré ball
 */
function generateInitialPosition(tongue) {
    const phase = phaseToRadians(tongue);
    const radius = 0.3 + Math.random() * 0.3; // 0.3 to 0.6 from center
    return {
        x: radius * Math.cos(phase),
        y: radius * Math.sin(phase),
        z: (Math.random() - 0.5) * 0.2, // Small z variation
    };
}
/**
 * Calculate BFT quorum from total agents
 */
function calculateBFTQuorum(totalAgents) {
    // BFT requires 3f + 1 agents to tolerate f faults
    // quorum = 2f + 1
    const maxFaulty = Math.floor((totalAgents - 1) / 3);
    const quorum = 2 * maxFaulty + 1;
    return {
        totalAgents,
        maxFaulty,
        quorum,
        timeoutMs: 5000,
    };
}
//# sourceMappingURL=types.js.map