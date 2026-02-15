/**
 * @file entropic-layer.ts
 * @module ai_brain/entropic-layer
 * @layer Layer 12, Layer 13
 * @version 1.0.0
 *
 * EntropicLayer: Escape detection, adaptive-k, and expansion tracking.
 *
 * Consolidates entropy-related mechanics into a unified module:
 * - Escape detection: monitors state volume growth (hyperbolic volume proxy)
 * - Adaptive k: dynamically adjusts governance k based on coherence
 * - Expansion volume: approximates hyperbolic volume for 6D manifold
 *
 * Escape velocity theorem: k > 2*C_quantum / sqrt(N0)
 * where C_quantum is the quantum coupling constant and N0 is initial node count.
 *
 * Integration: feeds into Layer 12 (harmonic wall) and Layer 13 (risk decision).
 */
/** Default maximum volume before escape detection triggers */
export declare const DEFAULT_MAX_VOLUME = 1000000;
/** Minimum adaptive k (always at least 1 governance node) */
export declare const MIN_K = 1;
/** Maximum adaptive k (cap to prevent over-governance) */
export declare const MAX_K = 50;
export interface EntropicState {
    /** Position in Poincare ball */
    position: number[];
    /** Velocity / drift vector */
    velocity: number[];
}
export interface EntropicConfig {
    /** Volume threshold for escape detection */
    maxVolume: number;
    /** Base k for adaptive governance */
    baseK: number;
    /** Quantum coupling constant for escape velocity bound */
    cQuantum: number;
    /** Initial node count for escape velocity theorem */
    n0: number;
}
export interface EscapeAssessment {
    /** Whether escape threshold is exceeded */
    escaped: boolean;
    /** Current expansion volume */
    volume: number;
    /** Ratio of volume to threshold */
    volumeRatio: number;
    /** Escape velocity bound: k > 2*C_quantum / sqrt(N0) */
    escapeVelocityBound: number;
    /** Current radial velocity */
    radialVelocity: number;
}
export declare const DEFAULT_ENTROPIC_CONFIG: EntropicConfig;
export declare class EntropicLayer {
    private config;
    constructor(config?: Partial<EntropicConfig>);
    /**
     * Compute approximate hyperbolic volume for a state position.
     *
     * For a point at radius r in the Poincare ball in d dimensions,
     * the hyperbolic volume of the ball of that radius is approximately:
     *   V ~ (pi^(d/2) * r^d / Gamma(d/2+1)) * exp((d-1) * r)
     *
     * For 6D (our Sacred Tongues manifold):
     *   V ~ (pi^3 * r^6 / 6) * exp(5r)
     *
     * @param position - Point in Poincare ball
     * @returns Approximate hyperbolic volume
     */
    computeExpansionVolume(position: number[]): number;
    /**
     * Detect whether a state has escaped the safe operational region.
     *
     * Escape occurs when:
     * 1. Expansion volume exceeds threshold, OR
     * 2. Radial velocity exceeds escape velocity bound
     *
     * @param state - Current position and velocity
     * @returns Escape assessment with diagnostics
     */
    detectEscape(state: EntropicState): EscapeAssessment;
    /**
     * Compute adaptive k (number of governance nodes) based on coherence.
     *
     * Low coherence -> fewer governance nodes (tighter control).
     * High coherence -> more nodes (broader participation).
     *
     * Formula: k = floor(baseK * coherence) + 1
     *
     * @param coherence - NK coherence score [0, 1]
     * @returns Adaptive k value
     */
    adaptiveK(coherence: number): number;
    /**
     * Check if the escape velocity theorem is satisfied.
     *
     * Theorem: For stable operation, k > 2*C_quantum / sqrt(N0)
     *
     * @param currentK - Current number of governance nodes
     * @returns Whether the bound is satisfied
     */
    escapeVelocityBoundSatisfied(currentK: number): boolean;
    /**
     * Update configuration at runtime.
     */
    updateConfig(partial: Partial<EntropicConfig>): void;
    /**
     * Get current configuration.
     */
    getConfig(): Readonly<EntropicConfig>;
    /**
     * Gamma function approximation (Stirling's for non-integers, exact for small integers).
     */
    private gamma;
}
//# sourceMappingURL=entropic-layer.d.ts.map