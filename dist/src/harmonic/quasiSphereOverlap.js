"use strict";
/**
 * @file quasiSphereOverlap.ts
 * @module harmonic/quasiSphereOverlap
 * @layer Layer 5, Layer 10, Layer 11, Layer 13
 * @component Quasi-Sphere Squad Overlap & Pad Geodesic Constraints
 * @version 3.2.4
 *
 * Formalizes the 6D quasi-sphere as an operational geometric object:
 *
 * 1. Squad Overlaps: Two quasi-spheres may share context when their
 *    trust-bounded hyperbolic shells intersect AND coherence is above
 *    threshold. Intersection requires geometric agreement, not central control.
 *
 * 2. Pad Geodesic Constraints: Each PadMode is allowed only certain curvature
 *    bands within the quasi-sphere. Engineering pads can reach deep (low d*)
 *    but must stay on-axis; Science pads can explore high curvature but
 *    are bounded in execution capability.
 *
 * 3. Consensus-Gradient Paths: Squad motion direction is the vector resultant
 *    of individual unit gradients. Byzantine agreement amplifies; disagreement
 *    shrinks magnitude → near-zero velocity.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.PAD_GEODESIC_CONSTRAINTS = void 0;
exports.createQuasiSphere = createQuasiSphere;
exports.computeOverlap = computeOverlap;
exports.squadOverlapMatrix = squadOverlapMatrix;
exports.sharedContextRadius = sharedContextRadius;
exports.localCurvature = localCurvature;
exports.isWithinGeodesicConstraint = isWithinGeodesicConstraint;
exports.padAccessibilityMap = padAccessibilityMap;
exports.consensusGradient = consensusGradient;
exports.gradientAgreement = gradientAgreement;
const chsfn_js_1 = require("./chsfn.js");
// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
/** Golden ratio */
const PHI = (1 + Math.sqrt(5)) / 2;
/** Small epsilon */
const EPSILON = 1e-10;
/**
 * Create a quasi-sphere from a CHSFN state.
 *
 * Trust radius is derived from coherence: higher coherence → wider reach.
 * trustRadius = -ln(1 - coherence) (maps [0, 1) → [0, ∞))
 */
function createQuasiSphere(unitId, state, coherence) {
    const trustRadius = -Math.log(1 - Math.min(coherence, 0.999));
    return {
        center: [...state.position],
        phase: [...state.phase],
        coherence,
        trustRadius,
        unitId,
    };
}
/**
 * Compute the overlap between two quasi-spheres.
 *
 * Two units may share context when:
 * 1. Their trust radii overlap: d_H(center_a, center_b) < r_a + r_b
 * 2. Phase coherence exceeds threshold: avg phase difference < maxPhaseDiff
 *
 * This is how you get "shared context without shared memory" and
 * "coordination without central control."
 *
 * @param a - First quasi-sphere
 * @param b - Second quasi-sphere
 * @param minPhaseCoherence - Min phase coherence for context sharing (default 0.5)
 * @returns Overlap result
 */
function computeOverlap(a, b, minPhaseCoherence = 0.5) {
    const distance = (0, chsfn_js_1.hyperbolicDistance6D)(a.center, b.center);
    const combinedRadius = a.trustRadius + b.trustRadius;
    const overlaps = distance < combinedRadius;
    // Phase coherence: average cosine similarity across tongues
    let phaseSum = 0;
    for (let i = 0; i < 6; i++) {
        phaseSum += Math.cos(a.phase[i] - b.phase[i]);
    }
    const phaseCoherence = (phaseSum / 6 + 1) / 2; // Normalize to [0, 1]
    const canShareContext = overlaps && phaseCoherence >= minPhaseCoherence;
    // Midpoint cost: access cost at the halfway point
    const midpointDStar = distance / 2;
    const midpointCost = (0, chsfn_js_1.accessCost)(midpointDStar);
    return {
        overlaps,
        distance,
        combinedRadius,
        phaseCoherence,
        canShareContext,
        midpointCost,
    };
}
/**
 * Compute the full overlap matrix for a squad of quasi-spheres.
 *
 * Returns which pairs can share context and the coherence between them.
 *
 * @param spheres - Array of quasi-spheres
 * @param minPhaseCoherence - Min phase coherence threshold
 * @returns Map from "unitA:unitB" → OverlapResult
 */
function squadOverlapMatrix(spheres, minPhaseCoherence = 0.5) {
    const matrix = new Map();
    for (let i = 0; i < spheres.length; i++) {
        for (let j = i + 1; j < spheres.length; j++) {
            const key = `${spheres[i].unitId}:${spheres[j].unitId}`;
            matrix.set(key, computeOverlap(spheres[i], spheres[j], minPhaseCoherence));
        }
    }
    return matrix;
}
/**
 * Compute the squad's shared context zone: the region reachable by all members.
 *
 * @param spheres - Array of quasi-spheres
 * @returns Effective shared radius (0 if no shared zone exists)
 */
function sharedContextRadius(spheres) {
    if (spheres.length < 2)
        return spheres.length === 1 ? spheres[0].trustRadius : 0;
    // Find the maximum pairwise distance
    let maxDist = 0;
    for (let i = 0; i < spheres.length; i++) {
        for (let j = i + 1; j < spheres.length; j++) {
            const d = (0, chsfn_js_1.hyperbolicDistance6D)(spheres[i].center, spheres[j].center);
            maxDist = Math.max(maxDist, d);
        }
    }
    // Find the minimum trust radius
    const minRadius = Math.min(...spheres.map((s) => s.trustRadius));
    // Shared zone exists if min radius exceeds half the max distance
    const sharedRadius = minRadius - maxDist / 2;
    return Math.max(sharedRadius, 0);
}
/**
 * Default geodesic constraints per PadMode.
 *
 * Design rationale:
 * - ENGINEERING: deep reach (low d*), on-axis (tight curvature), CA-dominant
 * - NAVIGATION: wide reach, moderate curvature, AV-dominant (contextual)
 * - SYSTEMS: moderate reach, tight curvature, DR-dominant (structural)
 * - SCIENCE: shallow reach, wide curvature (exploratory), UM-dominant
 * - COMMS: moderate reach, moderate curvature, KO-dominant (flow)
 * - MISSION: deepest reach, widest curvature, RU-dominant (binding)
 */
exports.PAD_GEODESIC_CONSTRAINTS = {
    ENGINEERING: {
        mode: 'ENGINEERING',
        maxReachDistance: 3.0,
        allowedCurvatureBand: [0.0, 1.5],
        tongueWeights: { KO: 0.5, AV: 0.5, RU: 0.5, CA: 2.0, DR: 1.0, UM: 0.3 },
        primaryTongue: 'CA',
    },
    NAVIGATION: {
        mode: 'NAVIGATION',
        maxReachDistance: 4.0,
        allowedCurvatureBand: [0.0, 2.5],
        tongueWeights: { KO: 0.8, AV: 2.0, RU: 0.5, CA: 0.5, DR: 0.5, UM: 0.5 },
        primaryTongue: 'AV',
    },
    SYSTEMS: {
        mode: 'SYSTEMS',
        maxReachDistance: 2.5,
        allowedCurvatureBand: [0.0, 1.0],
        tongueWeights: { KO: 0.5, AV: 0.5, RU: 1.0, CA: 0.8, DR: 2.0, UM: 0.5 },
        primaryTongue: 'DR',
    },
    SCIENCE: {
        mode: 'SCIENCE',
        maxReachDistance: 2.0,
        allowedCurvatureBand: [0.5, 4.0],
        tongueWeights: { KO: 0.3, AV: 0.5, RU: 0.3, CA: 1.0, DR: 0.5, UM: 2.0 },
        primaryTongue: 'UM',
    },
    COMMS: {
        mode: 'COMMS',
        maxReachDistance: 3.5,
        allowedCurvatureBand: [0.0, 2.0],
        tongueWeights: { KO: 2.0, AV: 1.0, RU: 0.5, CA: 0.5, DR: 0.5, UM: 0.5 },
        primaryTongue: 'KO',
    },
    MISSION: {
        mode: 'MISSION',
        maxReachDistance: 5.0,
        allowedCurvatureBand: [0.0, 5.0],
        tongueWeights: { KO: 1.0, AV: 1.0, RU: 2.0, CA: 1.0, DR: 1.0, UM: 0.5 },
        primaryTongue: 'RU',
    },
};
/**
 * Compute local curvature at a position in the Poincaré ball.
 *
 * In hyperbolic space, curvature increases toward the boundary:
 * κ(p) = 2 / (1 - ‖p‖²)²
 *
 * @param position - 6D position
 * @returns Local curvature value
 */
function localCurvature(position) {
    const normSq = position.reduce((sum, x) => sum + x * x, 0);
    const denom = (1 - normSq);
    if (denom <= 0)
        return Infinity;
    return 2 / (denom * denom);
}
/**
 * Check if a state is within a pad's geodesic constraints.
 *
 * A pad can access a position only if:
 * 1. Hyperbolic distance from center < maxReachDistance
 * 2. Local curvature is within allowedCurvatureBand
 * 3. Primary tongue impedance is below threshold
 *
 * @param state - Current CHSFN state
 * @param center - Unit's center position
 * @param constraint - Geodesic constraint for this pad
 * @param maxImpedance - Max impedance for primary tongue (default 0.4)
 * @returns Whether the position is geodesically accessible to this pad
 */
function isWithinGeodesicConstraint(state, center, constraint, maxImpedance = 0.4) {
    // Distance check
    const dist = (0, chsfn_js_1.hyperbolicDistance6D)(state.position, center);
    if (dist > constraint.maxReachDistance)
        return false;
    // Curvature band check
    const curv = localCurvature(state.position);
    if (curv < constraint.allowedCurvatureBand[0] || curv > constraint.allowedCurvatureBand[1]) {
        return false;
    }
    // Primary tongue impedance check
    const tongueIndex = ['KO', 'AV', 'RU', 'CA', 'DR', 'UM'].indexOf(constraint.primaryTongue);
    if (tongueIndex >= 0) {
        const imp = (0, chsfn_js_1.tongueImpedanceAt)(state, tongueIndex, constraint.tongueWeights);
        if (imp > maxImpedance)
            return false;
    }
    return true;
}
/**
 * Compute the effective geodesic reach for each pad of a unit.
 *
 * Returns the fraction of sampled points within the unit's quasi-sphere
 * that each pad can access, given its geodesic constraints.
 *
 * @param center - Unit center position
 * @param coherence - Unit coherence
 * @param sampleCount - Number of random probe points (default 100)
 * @returns Map from PadMode → accessibility fraction [0, 1]
 */
function padAccessibilityMap(center, coherence, sampleCount = 100) {
    const result = new Map();
    const trustRadius = -Math.log(1 - Math.min(coherence, 0.999));
    const modes = ['ENGINEERING', 'NAVIGATION', 'SYSTEMS', 'SCIENCE', 'COMMS', 'MISSION'];
    for (const mode of modes) {
        const constraint = exports.PAD_GEODESIC_CONSTRAINTS[mode];
        let accessible = 0;
        for (let s = 0; s < sampleCount; s++) {
            // Generate a probe point within trust radius
            const t = (s + 0.5) / sampleCount;
            const r = t * Math.min(trustRadius, 0.95); // Stay inside Poincaré ball
            const angle = s * PHI * 2 * Math.PI; // Golden angle spacing
            const probe = {
                position: [
                    center[0] + r * Math.cos(angle) * 0.3,
                    center[1] + r * Math.sin(angle) * 0.3,
                    center[2] + r * Math.cos(angle * 1.3) * 0.2,
                    center[3] + r * Math.sin(angle * 0.7) * 0.2,
                    center[4] + r * Math.cos(angle * 2.1) * 0.1,
                    center[5] + r * Math.sin(angle * 1.7) * 0.1,
                ],
                phase: [(2 * Math.PI * 0) / 6, (2 * Math.PI * 1) / 6, (2 * Math.PI * 2) / 6,
                    (2 * Math.PI * 3) / 6, (2 * Math.PI * 4) / 6, (2 * Math.PI * 5) / 6],
                mass: 1.0,
            };
            if (isWithinGeodesicConstraint(probe, center, constraint)) {
                accessible++;
            }
        }
        result.set(mode, accessible / sampleCount);
    }
    return result;
}
// ═══════════════════════════════════════════════════════════════
// Consensus-Gradient Paths (Byzantine Geometry)
// ═══════════════════════════════════════════════════════════════
/**
 * Compute the consensus gradient direction for a squad.
 *
 * Each unit contributes its own gradient (drift direction).
 * The resultant vector is the only allowed squad motion direction.
 *
 * If gradients disagree → magnitude shrinks (near-zero velocity).
 * If ≥4/6 agree → strong, coherent motion.
 *
 * This is Byzantine fault tolerance expressed as continuous geometry.
 *
 * @param gradients - Array of 6D gradient vectors (one per unit)
 * @returns Consensus gradient (magnitude reflects agreement)
 */
function consensusGradient(gradients) {
    if (gradients.length === 0)
        return [0, 0, 0, 0, 0, 0];
    const n = gradients.length;
    const avg = [0, 0, 0, 0, 0, 0];
    for (const g of gradients) {
        for (let i = 0; i < 6; i++)
            avg[i] += g[i] / n;
    }
    // Compute agreement: fraction of gradients pointing in same direction as average
    let agreement = 0;
    const avgNorm = Math.sqrt(avg.reduce((s, x) => s + x * x, 0));
    if (avgNorm < EPSILON)
        return [0, 0, 0, 0, 0, 0];
    for (const g of gradients) {
        const gNorm = Math.sqrt(g.reduce((s, x) => s + x * x, 0));
        if (gNorm < EPSILON)
            continue;
        // Cosine similarity
        let dot = 0;
        for (let i = 0; i < 6; i++)
            dot += g[i] * avg[i];
        const cosSim = dot / (gNorm * avgNorm);
        if (cosSim > 0.5)
            agreement++; // More than 60° alignment
    }
    const agreementFraction = agreement / n;
    // Scale the consensus by agreement strength
    // 4/6 = 0.667 → strong motion; 2/6 = 0.333 → weak motion
    return avg.map((x) => x * agreementFraction);
}
/**
 * Compute agreement strength from a set of gradient vectors.
 *
 * @returns Value in [0, 1] where 1 = perfect agreement
 */
function gradientAgreement(gradients) {
    if (gradients.length < 2)
        return 1;
    const n = gradients.length;
    let totalCosSim = 0;
    let pairs = 0;
    for (let i = 0; i < n; i++) {
        const ni = Math.sqrt(gradients[i].reduce((s, x) => s + x * x, 0));
        if (ni < EPSILON)
            continue;
        for (let j = i + 1; j < n; j++) {
            const nj = Math.sqrt(gradients[j].reduce((s, x) => s + x * x, 0));
            if (nj < EPSILON)
                continue;
            let dot = 0;
            for (let k = 0; k < 6; k++)
                dot += gradients[i][k] * gradients[j][k];
            totalCosSim += (dot / (ni * nj) + 1) / 2; // Normalize to [0, 1]
            pairs++;
        }
    }
    return pairs === 0 ? 0 : totalCosSim / pairs;
}
//# sourceMappingURL=quasiSphereOverlap.js.map