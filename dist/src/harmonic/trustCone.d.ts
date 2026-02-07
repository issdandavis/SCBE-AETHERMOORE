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
/** A trust cone in the Poincaré ball */
export interface TrustCone {
    /** Apex of the cone (entity position in the ball) */
    apex: number[];
    /** Direction vector (unit vector pointing toward intent target) */
    direction: number[];
    /** Confidence level [0, 1] that determines cone width */
    confidence: number;
    /** Base half-angle in radians (default π/6 = 30°) */
    baseAngle: number;
    /** Computed half-angle: baseAngle / confidence */
    halfAngle: number;
}
/** Result of checking a point against a trust cone */
export interface ConeCheckResult {
    /** Whether the target is within the cone */
    withinCone: boolean;
    /** Angle between direction and target (radians) */
    angle: number;
    /** Cone half-angle (radians) */
    coneHalfAngle: number;
    /** How far inside/outside the cone (negative = inside, positive = outside) */
    angularMargin: number;
    /** Hyperbolic distance from apex to target */
    hyperbolicDist: number;
}
/** Configuration for trust cone behavior */
export interface TrustConeConfig {
    /** Base half-angle in radians (default π/6) */
    baseAngle: number;
    /** Minimum confidence before cone maxes out (default 0.1) */
    minConfidence: number;
    /** Maximum allowed hyperbolic distance for cone check (default Infinity) */
    maxDistance: number;
}
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
export declare function computeConeAngle(confidence: number, config?: Partial<TrustConeConfig>): number;
/**
 * Create a trust cone at a given position.
 *
 * @param apex - Entity position in the Poincaré ball
 * @param direction - Intent direction (will be normalized)
 * @param confidence - Confidence level [0, 1]
 * @param config - Optional configuration
 * @returns TrustCone object
 */
export declare function createTrustCone(apex: number[], direction: number[], confidence: number, config?: Partial<TrustConeConfig>): TrustCone;
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
export declare function checkTrustCone(cone: TrustCone, target: number[], config?: Partial<TrustConeConfig>): ConeCheckResult;
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
export declare function trustConePenalty(cone: TrustCone, target: number[]): number;
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
export declare function createRealmTrustCone(currentPosition: number[], realmCenter: number[], confidence: number, config?: Partial<TrustConeConfig>): TrustCone;
//# sourceMappingURL=trustCone.d.ts.map