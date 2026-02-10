/**
 * @file adaptiveNavigator.ts
 * @module harmonic/adaptiveNavigator
 * @layer Layer 5, Layer 6, Layer 7, Layer 9, Layer 13
 * @component Adaptive Hyperbolic Navigator
 * @version 1.0.0
 * @since 2026-02-06
 *
 * SCBE Adaptive Hyperbolic Navigator - Dynamic geometry that evolves with intent validation.
 *
 * Key Innovation: The Poincaré ball becomes a "living manifold" where:
 * - Harmonic scaling R(t) varies with coherence: R(t) = R_base + λ(1 - C)
 * - Curvature κ(t) can adapt: κ(t) = -1 * exp(γ(1 - C))
 * - ODE-based drift with attraction/repulsion modulated by trust
 *
 * Mathematical Foundation:
 * - Generalized Poincaré metric with variable curvature
 * - Distance formula: d_κ(u,v) = (1/√|κ|) arccosh(1 + (2|κ|‖u-v‖²)/((1-|κ|‖u‖²)(1-|κ|‖v‖²)))
 * - Harmonic wall: H(d,R) = R^(d²) where R adapts to coherence
 *
 * Integration:
 * - Layer 9/10: Spectral coherence feeds into C ∈ [0,1]
 * - Layer 13: Intent validation modulates drift velocity
 * - HYDRA: Swarm consensus can trigger geometry evolution
 */
/** Sacred Tongue realm centers in 6D Poincaré ball */
export declare const REALM_CENTERS: Record<string, number[]>;
/** Tongue weights (golden ratio based) */
export declare const TONGUE_WEIGHTS: Record<string, number>;
export interface AdaptiveNavigatorConfig {
    /** Base harmonic scaling factor (default 1.5) */
    baseR: number;
    /** Penalty multiplier for low coherence (default 1.0) */
    lambdaPenalty: number;
    /** Chaos amplitude for Lorenz-like perturbations (default 0.1) */
    chaos: number;
    /** Curvature adaptation rate (default 0.5) */
    gamma: number;
    /** Dimension of the Poincaré ball (default 6 for Sacred Tongues) */
    dimension: number;
    /** Maximum trajectory history length (default 1000) */
    maxHistory: number;
    /** Ball boundary threshold (default 0.98) */
    boundaryThreshold: number;
}
export declare const DEFAULT_CONFIG: AdaptiveNavigatorConfig;
export interface NavigatorState {
    position: number[];
    velocity: number[];
    coherence: number;
    currentR: number;
    currentKappa: number;
    penalty: number;
    timestamp: number;
}
/**
 * Adaptive Hyperbolic Navigator
 *
 * A "living manifold" navigator where the Poincaré ball geometry
 * evolves based on intent validation coherence.
 *
 * @example
 * ```typescript
 * const nav = new AdaptiveHyperbolicNavigator();
 *
 * // Update with intent and coherence from Layer 9/13
 * const result = nav.update(['KO', 'AV'], 0.85);
 *
 * // Check adaptive penalty
 * if (result.penalty > 10) {
 *   console.log('High deviation detected');
 * }
 * ```
 */
export declare class AdaptiveHyperbolicNavigator {
    private config;
    private position;
    private velocity;
    private history;
    private coherenceHistory;
    constructor(config?: Partial<AdaptiveNavigatorConfig>, initialPosition?: number[]);
    /**
     * Compute adaptive harmonic scaling R(t) based on coherence
     *
     * R(t) = R_base + λ(1 - C)
     *
     * Low coherence → higher R → harsher exponential penalties
     *
     * @param coherence - Intent validation coherence [0, 1]
     */
    getCurrentR(coherence: number): number;
    /**
     * Compute adaptive curvature κ(t) based on coherence
     *
     * κ(t) = -1 * exp(γ(1 - C))
     *
     * Low coherence → more negative curvature → distances explode faster
     *
     * @param coherence - Intent validation coherence [0, 1]
     */
    getCurrentKappa(coherence: number): number;
    /**
     * Hyperbolic distance with variable curvature
     *
     * d_κ(u,v) = (1/√|κ|) arccosh(1 + (2|κ|‖u-v‖²)/((1-|κ|‖u‖²)(1-|κ|‖v‖²)))
     *
     * @param u - First point
     * @param v - Second point
     * @param kappa - Curvature (negative for hyperbolic)
     */
    hyperbolicDistanceKappa(u: number[], v: number[], kappa: number): number;
    /**
     * Standard hyperbolic distance (κ = -1)
     */
    hyperbolicDistance(u: number[], v: number[]): number;
    /**
     * Compute drift vector for ODE integration
     *
     * Combines:
     * - Attraction to target realm centers (scaled by coherence and R)
     * - Repulsion/mutations (amplified by low coherence)
     * - Chaos term (Lorenz-like, modulated by coherence)
     *
     * @param pos - Current position
     * @param targets - Target tongue realms
     * @param coherence - Intent validation coherence
     * @param mutations - Mutation rate for lexicon evolution
     */
    private computeDrift;
    /**
     * RK4 integration step for smooth trajectory evolution
     */
    private rk4Step;
    /**
     * Update navigator position with intent and coherence
     *
     * This is the main integration point:
     * - Layer 9/10: coherence = spectral coherence C ∈ [0,1]
     * - Layer 13: coherence = 1 - risk' from intent validation
     * - mutations: from EvolvingLexicon mutation rate
     *
     * @param intentTongues - Target Sacred Tongue realms
     * @param coherence - Intent validation coherence [0, 1]
     * @param mutations - Mutation rate (default 0)
     * @param dt - Time step (default 0.1)
     * @returns Navigator state after update
     */
    update(intentTongues: string[], coherence?: number, mutations?: number, dt?: number): NavigatorState;
    /**
     * Get distance to a specific realm center
     */
    distanceToRealm(tongue: string, coherence?: number): number;
    /**
     * Get the closest realm to current position
     */
    closestRealm(coherence?: number): {
        tongue: string;
        distance: number;
    };
    /**
     * Compute trajectory entropy (measure of chaotic behavior)
     */
    trajectoryEntropy(): number;
    /**
     * Compute coherence stability (variance over recent history)
     */
    coherenceStability(window?: number): number;
    /**
     * Detect potential attack pattern (sustained low coherence + high movement)
     */
    detectAnomaly(thresholds?: {
        coherence: number;
        entropy: number;
        stability: number;
    }): {
        isAnomaly: boolean;
        score: number;
        indicators: string[];
    };
    getPosition(): number[];
    getVelocity(): number[];
    getHistory(): number[][];
    getCoherenceHistory(): number[];
    /**
     * Reset navigator to initial state
     */
    reset(initialPosition?: number[]): void;
    /**
     * Serialize state for persistence
     */
    serialize(): string;
    /**
     * Restore from serialized state
     */
    static deserialize(json: string): AdaptiveHyperbolicNavigator;
}
/**
 * Create an adaptive navigator with sensible defaults
 */
export declare function createAdaptiveNavigator(config?: Partial<AdaptiveNavigatorConfig>, initialPosition?: number[]): AdaptiveHyperbolicNavigator;
/**
 * Compute coherence from Layer 9/10 spectral analysis
 *
 * @param spectralCoherence - Raw coherence from spectral analysis
 * @param spinCoherence - Spin coherence from consensus
 * @returns Combined coherence score
 */
export declare function computeCoherence(spectralCoherence: number, spinCoherence?: number): number;
/**
 * Compute coherence from Layer 13 risk score
 *
 * @param riskScore - Risk' from intent validation [0, 1]
 * @returns Coherence as complement of risk
 */
export declare function riskToCoherence(riskScore: number): number;
//# sourceMappingURL=adaptiveNavigator.d.ts.map