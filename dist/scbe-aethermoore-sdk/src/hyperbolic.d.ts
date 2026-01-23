/**
 * SCBE Hyperbolic Geometry (Layers 5-7)
 *
 * Poincaré ball operations for the SCBE 14-layer pipeline.
 * The invariant hyperbolic metric NEVER changes - all dynamics
 * come from transforming points within the ball.
 *
 * L5: Invariant Metric dℍ(u,v) = arcosh(1 + 2‖u-v‖²/((1-‖u‖²)(1-‖v‖²)))
 * L6: Breath Transform B(p,t) = tanh(‖p‖ + A·sin(ωt))·p/‖p‖
 * L7: Phase Modulation Φ(p,θ) = R_θ·p rotation in tangent space
 */
/**
 * Hyperbolic distance in the Poincaré ball model (Layer 5)
 *
 * dℍ(u,v) = arcosh(1 + 2‖u-v‖² / ((1-‖u‖²)(1-‖v‖²)))
 *
 * This metric is INVARIANT - it never changes. Points move; the metric does not.
 *
 * @param u - First point in Poincaré ball (‖u‖ < 1)
 * @param v - Second point in Poincaré ball (‖v‖ < 1)
 * @returns Hyperbolic distance
 */
export declare function hyperbolicDistance(u: number[], v: number[]): number;
/**
 * Möbius addition in the Poincaré ball
 *
 * u ⊕ v = ((1 + 2⟨u,v⟩ + ‖v‖²)u + (1 - ‖u‖²)v) / (1 + 2⟨u,v⟩ + ‖u‖²‖v‖²)
 *
 * This is the gyrovector addition for hyperbolic geometry.
 *
 * @param u - First point
 * @param v - Second point
 * @returns Möbius sum u ⊕ v
 */
export declare function mobiusAdd(u: number[], v: number[]): number[];
/**
 * Project a point onto the Poincaré ball (clamp to ‖p‖ < 1)
 *
 * @param p - Point to project
 * @param maxNorm - Maximum norm (default 1 - ε)
 * @returns Projected point inside ball
 */
export declare function projectToBall(p: number[], maxNorm?: number): number[];
/**
 * Exponential map from tangent space to Poincaré ball at origin
 *
 * exp_0(v) = tanh(‖v‖/2) · v/‖v‖
 *
 * @param v - Tangent vector at origin
 * @returns Point in Poincaré ball
 */
export declare function expMap0(v: number[]): number[];
/**
 * Logarithmic map from Poincaré ball to tangent space at origin
 *
 * log_0(p) = 2 · arctanh(‖p‖) · p/‖p‖
 *
 * @param p - Point in Poincaré ball
 * @returns Tangent vector at origin
 */
export declare function logMap0(p: number[]): number[];
/**
 * Breath Transform configuration
 */
export interface BreathConfig {
    /** Amplitude bound A ∈ [0, 0.1] */
    amplitude: number;
    /** Breathing frequency ω */
    omega: number;
}
/**
 * Breath Transform (Layer 6)
 *
 * B(p, t) = tanh(‖p‖ + A·sin(ωt)) · p/‖p‖
 *
 * Preserves direction, modulates radius. Creates a "breathing" effect
 * where points rhythmically move toward/away from the boundary.
 *
 * @param p - Point in Poincaré ball
 * @param t - Time parameter
 * @param config - Breath configuration
 * @returns Transformed point
 */
export declare function breathTransform(p: number[], t: number, config?: BreathConfig): number[];
/**
 * Inverse breath transform (approximate recovery)
 *
 * @param bp - Breath-transformed point
 * @param t - Time parameter
 * @param config - Breath configuration
 * @returns Approximate original point
 */
export declare function inverseBreathTransform(bp: number[], t: number, config?: BreathConfig): number[];
/**
 * Phase Modulation / Rotation (Layer 7)
 *
 * Φ(p, θ) = R_θ · p - rotation in tangent space
 *
 * For 2D, this is standard rotation. For higher dimensions,
 * we rotate in a chosen plane.
 *
 * @param p - Point in Poincaré ball
 * @param theta - Rotation angle in radians
 * @param plane - Pair of dimension indices to rotate in (default [0,1])
 * @returns Rotated point
 */
export declare function phaseModulation(p: number[], theta: number, plane?: [number, number]): number[];
/**
 * Multi-plane phase modulation
 *
 * Applies rotations in multiple planes sequentially.
 *
 * @param p - Point in Poincaré ball
 * @param rotations - Array of [theta, plane] pairs
 * @returns Transformed point
 */
export declare function multiPhaseModulation(p: number[], rotations: Array<{
    theta: number;
    plane: [number, number];
}>): number[];
/**
 * Well configuration for multi-well potential
 */
export interface Well {
    /** Well center position */
    center: number[];
    /** Well weight */
    weight: number;
    /** Well width (σ) */
    sigma: number;
}
/**
 * Multi-Well Potential (Layer 8)
 *
 * V(p) = Σᵢ wᵢ · exp(-‖p - cᵢ‖² / 2σᵢ²)
 *
 * Creates an energy landscape with multiple attractors (wells).
 *
 * @param p - Point in space
 * @param wells - Array of well configurations
 * @returns Potential energy at point p
 */
export declare function multiWellPotential(p: number[], wells: Well[]): number;
/**
 * Gradient of multi-well potential
 *
 * ∇V(p) = Σᵢ wᵢ · exp(-‖p-cᵢ‖²/2σᵢ²) · (-(p-cᵢ)/σᵢ²)
 *
 * @param p - Point in space
 * @param wells - Array of well configurations
 * @returns Gradient vector
 */
export declare function multiWellGradient(p: number[], wells: Well[]): number[];
/**
 * Apply the L5-L8 transform pipeline
 *
 * @param p - Input point
 * @param t - Time parameter
 * @param theta - Phase rotation angle
 * @param breathConfig - Breath transform config
 * @param wells - Multi-well potential config (optional)
 * @returns Transformed point and potential value
 */
export declare function applyHyperbolicPipeline(p: number[], t: number, theta: number, breathConfig?: BreathConfig, wells?: Well[]): {
    point: number[];
    potential: number;
    distance: number;
};
//# sourceMappingURL=hyperbolic.d.ts.map