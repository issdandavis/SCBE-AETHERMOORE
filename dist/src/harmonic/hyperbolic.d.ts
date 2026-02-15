/**
 * @file hyperbolic.ts
 * @module harmonic/hyperbolic
 * @layer Layer 5, Layer 6, Layer 7
 * @component Poincaré Ball Operations
 * @version 3.0.0
 * @since 2026-01-20
 *
 * SCBE Hyperbolic Geometry - Core mathematical operations for the 14-layer pipeline.
 * The invariant hyperbolic metric NEVER changes - all dynamics come from
 * transforming points within the Poincaré ball.
 *
 * Layer 5: Invariant Metric d_ℍ(u,v) = arcosh(1 + 2‖u-v‖²/((1-‖u‖²)(1-‖v‖²)))
 * Layer 6: Breathing Transform B(p,t) = tanh(‖p‖ + A·sin(ωt))·p/‖p‖
 * Layer 7: Phase Modulation Φ(p,θ) = Möbius rotation in tangent space
 */
/** Small epsilon for numerical stability (norm checks, zero-vector guards) */
export declare const EPSILON = 1e-10;
/**
 * Set the audit epsilon for boundary clamping in artanh/distance calculations.
 * Allows Layer 13 telemetry to tune precision for attack simulation or audit sweeps.
 * @param eps - New epsilon value (must be positive and < 1e-6)
 */
export declare function setAuditEpsilon(eps: number): void;
/** Get current audit epsilon */
export declare function getAuditEpsilon(): number;
/**
 * Inverse hyperbolic tangent with configurable boundary clamping.
 *
 * artanh(z) = 0.5 * ln((1+z)/(1-z))
 *
 * Clamps z to [-1 + ε, 1 - ε] where ε = AUDIT_EPSILON to prevent
 * singularities at the Poincaré ball boundary.
 *
 * @layer Layer 5
 * @param z - Input value
 * @param eps - Override epsilon (defaults to AUDIT_EPSILON)
 * @returns artanh(z)
 */
export declare function artanh(z: number, eps?: number): number;
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
 * Project a point onto the Poincaré ball (simple clamp to ‖p‖ < 1)
 *
 * Use this for points already near the ball. For real embeddings with
 * arbitrary norms, use projectEmbeddingToBall instead.
 *
 * @param p - Point to project
 * @param maxNorm - Maximum norm (default 1 - ε)
 * @returns Projected point inside ball
 */
export declare function projectToBall(p: number[], maxNorm?: number): number[];
/**
 * Project real embeddings into the Poincaré ball using tanh mapping.
 *
 * CRITICAL: Real embeddings from models have norms >> 1. Simple clamping
 * causes the hyperbolicDistance denominator to go negative, returning Infinity,
 * which makes rogue items invisible instead of expelled.
 *
 * This function maps R^n → B^n (unit ball) smoothly via:
 *   u = tanh(α‖x‖) · x/‖x‖
 *
 * @param x - Embedding vector (any norm)
 * @param eps - Boundary margin (default 1e-6)
 * @param alpha - Compression factor (default 0.15, tune for your embedding scale)
 * @returns Point strictly inside unit ball
 */
export declare function projectEmbeddingToBall(x: number[], eps?: number, alpha?: number): number[];
/**
 * Clamp a point to stay inside the Poincaré ball (in-place style, returns new array)
 *
 * CRITICAL: The old swarmStep clamped inside the per-dimension loop, causing
 * weird distortions. This function should be called ONCE after all force
 * updates are applied.
 *
 * @param u - Point to clamp
 * @param rMax - Maximum radius (default 0.99)
 * @returns Clamped point
 */
export declare function clampToBall(u: number[], rMax?: number): number[];
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
 * General exponential map at any base point p
 *
 * exp_p(v) = p ⊕ (tanh(λ_p‖v‖/2) · v/‖v‖)
 * where λ_p = 2/(1-‖p‖²) and ⊕ is Möbius addition
 *
 * @param p - Base point in Poincaré ball
 * @param v - Tangent vector at p
 * @returns Point in Poincaré ball
 */
export declare function exponentialMap(p: number[], v: number[]): number[];
/**
 * General logarithmic map from q to tangent space at p
 *
 * log_p(q) = (2/λ_p) · arctanh(‖-p ⊕ q‖) · (-p ⊕ q)/‖-p ⊕ q‖
 * where λ_p = 2/(1-‖p‖²) and ⊕ is Möbius addition
 *
 * @param p - Base point in Poincaré ball
 * @param q - Target point in Poincaré ball
 * @returns Tangent vector at p
 */
export declare function logarithmicMap(p: number[], q: number[]): number[];
export { mobiusAdd as mobiusAddition };
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
 * Phase deviation between two phase values
 *
 * Measures how different two phases are, normalized to [0, 1].
 * 0 = identical phases, 1 = maximally different
 *
 * @param phase1 - First phase value (or null for unknown)
 * @param phase2 - Second phase value (or null for unknown)
 * @returns Deviation in [0, 1]
 */
export declare function phaseDeviation(phase1: number | null, phase2: number | null): number;
/**
 * Phase-augmented distance scoring for adversarial detection.
 *
 * VALIDATED RESULT: Achieves AUC = 0.9999 on adversarial RAG detection.
 *
 * The key insight: hyperbolic distance alone (AUC = 0.667) ties with cosine
 * and Euclidean. But adding phase deviation breaks the tie and dominates.
 *
 * Formula: score = 1 / (1 + d_H + phaseWeight * phase_dev)
 *
 * Higher score = more trustworthy (closer in space AND aligned in phase)
 * Lower score = suspicious (far away OR phase mismatch)
 *
 * @param u - First point in Poincaré ball
 * @param v - Second point in Poincaré ball
 * @param phase1 - Phase of first point (Sacred Tongue assignment)
 * @param phase2 - Phase of second point
 * @param phaseWeight - Weight for phase deviation (default 2.0)
 * @returns Trust score in (0, 1]
 */
export declare function phaseDistanceScore(u: number[], v: number[], phase1: number | null, phase2: number | null, phaseWeight?: number): number;
/**
 * Batch scoring for RAG retrieval filtering.
 *
 * Given a query embedding and phase, score all candidate retrievals.
 * Returns scores sorted descending (most trustworthy first).
 *
 * @param query - Query embedding (will be projected to ball)
 * @param queryPhase - Query phase (Sacred Tongue)
 * @param candidates - Array of {embedding, phase, id}
 * @param phaseWeight - Weight for phase deviation
 * @returns Sorted array of {id, score}
 */
export declare function scoreRetrievals(query: number[], queryPhase: number | null, candidates: Array<{
    embedding: number[];
    phase: number | null;
    id: string;
}>, phaseWeight?: number): Array<{
    id: string;
    score: number;
}>;
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