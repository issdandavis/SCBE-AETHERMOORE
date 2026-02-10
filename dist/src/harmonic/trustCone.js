"use strict";
/**
 * @file trustCone.ts
 * @module harmonic/trustCone
 * @layer Layer 5, Layer 13
 * @component Trust Cone Access Control
 * @version 1.0.0
 * @since 2026-02-07
 *
 * Trust Cones: Geometric access control in the Poincaré ball.
 *
 * A Trust Cone is defined at a position in the Poincaré ball with:
 * - An apex (the entity's current position)
 * - A direction (the entity's intent vector)
 * - An angular width proportional to 1/confidence
 *
 * High confidence → narrow cone → precise, restricted navigation
 * Low confidence → wide cone → diffuse, unrestricted but penalized navigation
 *
 * The cone width formula: θ = θ_base / max(confidence, ε)
 *
 * This provides a novel geometric access control mechanism where
 * the entity's confidence in its intent directly constrains the
 * region of the Poincaré ball it can navigate to.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.computeConeAngle = computeConeAngle;
exports.createTrustCone = createTrustCone;
exports.checkTrustCone = checkTrustCone;
exports.trustConePenalty = trustConePenalty;
exports.createRealmTrustCone = createRealmTrustCone;
const hyperbolic_js_1 = require("./hyperbolic.js");
// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
const EPSILON = 1e-10;
/** Maximum cone half-angle (π/2 = hemisphere) */
const MAX_CONE_ANGLE = Math.PI / 2;
/** Minimum cone half-angle (1 degree) */
const MIN_CONE_ANGLE = Math.PI / 180;
const DEFAULT_CONFIG = {
    baseAngle: Math.PI / 6, // 30 degrees
    minConfidence: 0.1,
    maxDistance: Infinity,
};
// ═══════════════════════════════════════════════════════════════
// Vector helpers (local to avoid import cycles)
// ═══════════════════════════════════════════════════════════════
function vecNorm(v) {
    let sum = 0;
    for (const x of v)
        sum += x * x;
    return Math.sqrt(sum);
}
function vecDot(u, v) {
    let sum = 0;
    for (let i = 0; i < u.length; i++)
        sum += u[i] * v[i];
    return sum;
}
function vecSub(u, v) {
    return u.map((x, i) => x - v[i]);
}
function vecScale(v, s) {
    return v.map((x) => x * s);
}
function vecNormalize(v) {
    const n = vecNorm(v);
    if (n < EPSILON)
        return v.map(() => 0);
    return vecScale(v, 1 / n);
}
// ═══════════════════════════════════════════════════════════════
// Trust Cone Operations
// ═══════════════════════════════════════════════════════════════
/**
 * Compute the cone half-angle from confidence.
 *
 * θ = clamp(θ_base / max(confidence, minConfidence), MIN_CONE_ANGLE, MAX_CONE_ANGLE)
 *
 * High confidence → narrow cone (precise navigation)
 * Low confidence → wide cone (diffuse, penalized navigation)
 *
 * @param confidence - Confidence level [0, 1]
 * @param config - Cone configuration
 * @returns Half-angle in radians
 */
function computeConeAngle(confidence, config = {}) {
    const cfg = { ...DEFAULT_CONFIG, ...config };
    const c = Math.max(cfg.minConfidence, Math.min(1, confidence));
    const angle = cfg.baseAngle / c;
    return Math.max(MIN_CONE_ANGLE, Math.min(MAX_CONE_ANGLE, angle));
}
/**
 * Create a trust cone at a given position.
 *
 * @param apex - Entity position in the Poincaré ball
 * @param direction - Intent direction (will be normalized)
 * @param confidence - Confidence level [0, 1]
 * @param config - Optional configuration
 * @returns TrustCone object
 */
function createTrustCone(apex, direction, confidence, config = {}) {
    const cfg = { ...DEFAULT_CONFIG, ...config };
    const halfAngle = computeConeAngle(confidence, cfg);
    return {
        apex: [...apex],
        direction: vecNormalize(direction),
        confidence: Math.max(0, Math.min(1, confidence)),
        baseAngle: cfg.baseAngle,
        halfAngle,
    };
}
/**
 * Check whether a target point falls within a trust cone.
 *
 * The check computes the angle between the cone direction and the
 * vector from apex to target (in Euclidean tangent space approximation).
 *
 * @param cone - The trust cone to check against
 * @param target - Target point in the Poincaré ball
 * @param config - Optional configuration overrides
 * @returns ConeCheckResult with detailed information
 */
function checkTrustCone(cone, target, config = {}) {
    const cfg = { ...DEFAULT_CONFIG, ...config };
    if (cone.apex.length !== target.length) {
        throw new Error(`Dimension mismatch: cone apex is ${cone.apex.length}D, target is ${target.length}D`);
    }
    // Vector from apex to target
    const toTarget = vecSub(target, cone.apex);
    const toTargetNorm = vecNorm(toTarget);
    // Degenerate case: target is at the apex
    if (toTargetNorm < EPSILON) {
        return {
            withinCone: true,
            angle: 0,
            coneHalfAngle: cone.halfAngle,
            angularMargin: -cone.halfAngle,
            hyperbolicDist: 0,
        };
    }
    // Angle between direction and toTarget
    const cosAngle = vecDot(cone.direction, toTarget) / toTargetNorm;
    // Clamp for numerical stability
    const angle = Math.acos(Math.max(-1, Math.min(1, cosAngle)));
    // Hyperbolic distance
    const hyperbolicDist = (0, hyperbolic_js_1.hyperbolicDistance)(cone.apex, target);
    // Distance check
    if (cfg.maxDistance !== Infinity && hyperbolicDist > cfg.maxDistance) {
        return {
            withinCone: false,
            angle,
            coneHalfAngle: cone.halfAngle,
            angularMargin: angle - cone.halfAngle,
            hyperbolicDist,
        };
    }
    const withinCone = angle <= cone.halfAngle;
    const angularMargin = angle - cone.halfAngle; // negative = inside
    return {
        withinCone,
        angle,
        coneHalfAngle: cone.halfAngle,
        angularMargin,
        hyperbolicDist,
    };
}
/**
 * Compute a trust-weighted navigation penalty.
 *
 * If the target is within the cone, the penalty is low (near 1).
 * If outside, the penalty grows exponentially with angular excess.
 *
 * penalty = exp(φ * max(0, angle - halfAngle)²)
 *
 * where φ is the golden ratio (matching the harmonic wall formula).
 *
 * @param cone - Trust cone
 * @param target - Target point
 * @returns Penalty multiplier (>= 1, where 1 = no penalty)
 */
function trustConePenalty(cone, target) {
    const check = checkTrustCone(cone, target);
    if (check.withinCone) {
        return 1.0; // No penalty
    }
    const PHI = (1 + Math.sqrt(5)) / 2;
    const excess = check.angularMargin; // positive when outside cone
    return Math.exp(PHI * excess * excess);
}
/**
 * Create a trust cone pointing from the current position toward a
 * target realm center, with confidence-based width.
 *
 * @param currentPosition - Current position in 6D Poincaré ball
 * @param realmCenter - Target realm center coordinates
 * @param confidence - Confidence level [0, 1]
 * @param config - Optional configuration
 * @returns TrustCone pointing toward the realm
 */
function createRealmTrustCone(currentPosition, realmCenter, confidence, config = {}) {
    const direction = vecSub(realmCenter, currentPosition);
    return createTrustCone(currentPosition, direction, confidence, config);
}
//# sourceMappingURL=trustCone.js.map