/**
 * Space Tor Trust Manager with Langues Weighting System
 *
 * Implements Layer 3 (Langues Metric Tensor) for trust scoring across
 * the Six Sacred Tongues (KO, AV, RU, CA, UM, DR).
 *
 * Mathematical Foundation:
 * L(x,t) = Σ(l=1 to 6) w_l * exp[β_l * (d_l + sin(ω_l*t + φ_l))]
 * where d_l = |x_l - μ_l|
 *
 * @module spaceTor/trust-manager
 */
/**
 * Sacred Tongue identifiers
 */
export declare enum SacredTongue {
    KORAELIN = 0,// KO - Base tongue (w=1.0)
    AVALI = 1,// AV - Harmonic 1 (w=1.125)
    RUNETHIC = 2,// RU - Harmonic 2 (w=1.25)
    CASSISIVADAN = 3,// CA - Harmonic 3 (w=1.333)
    UMBROTH = 4,// UM - Harmonic 4 (w=1.5)
    DRAUMRIC = 5
}
/**
 * Langues Weighting System parameters
 */
export interface LanguesParams {
    /** Harmonic weights for each tongue (golden ratio scaling) */
    w: number[];
    /** Growth coefficients (β_l) */
    beta: number[];
    /** Temporal frequencies (ω_l) */
    omega: number[];
    /** Phase offsets (φ_l) */
    phi: number[];
    /** Ideal (trusted) values (μ_l) */
    mu: number[];
    /** Dimension flux coefficients (ν_l) for breathing */
    nu?: number[];
}
/**
 * Trust score result
 */
export interface TrustScore {
    /** Raw Langues metric L(x,t) */
    raw: number;
    /** Normalized score L_N ∈ [0,1] */
    normalized: number;
    /** Per-tongue contributions */
    contributions: number[];
    /** Gradient field ∇L for descent */
    gradient: number[];
    /** Trust level classification */
    level: 'HIGH' | 'MEDIUM' | 'LOW' | 'CRITICAL';
}
/**
 * Node trust state
 */
export interface NodeTrust {
    /** Node identifier */
    nodeId: string;
    /** 6D trust vector (one per Sacred Tongue) */
    trustVector: number[];
    /** Last update timestamp */
    lastUpdate: number;
    /** Historical trust scores */
    history: number[];
    /** Anomaly flags */
    anomalies: string[];
}
/**
 * Default Langues parameters (production-ready)
 */
export declare const DEFAULT_LANGUES_PARAMS: LanguesParams;
/**
 * Trust Manager for Space Tor network
 *
 * Implements Langues Weighting System (Layer 3) for trust scoring
 * across the Six Sacred Tongues.
 */
export declare class TrustManager {
    private params;
    private nodes;
    private maxScore;
    constructor(params?: LanguesParams);
    /**
     * Compute Langues metric L(x,t)
     *
     * L(x,t) = Σ(l=1 to 6) ν_l * w_l * exp[β_l * (d_l + sin(ω_l*t + φ_l))]
     *
     * @param x - 6D trust vector
     * @param t - Current time
     * @returns Raw Langues metric
     */
    private computeLanguesMetric;
    /**
     * Compute gradient field ∇L
     *
     * ∂L/∂x_l = ν_l * w_l * β_l * exp[β_l * (d_l + sin(...))] * sgn(x_l - μ_l)
     *
     * @param x - 6D trust vector
     * @param t - Current time
     * @returns Gradient vector
     */
    private computeGradient;
    /**
     * Compute per-tongue contributions
     *
     * @param x - 6D trust vector
     * @param t - Current time
     * @returns Array of 6 contributions
     */
    private computeContributions;
    /**
     * Compute maximum possible score (for normalization)
     *
     * L_max occurs when all d_l = 1 and sin(...) = 1
     *
     * @returns Maximum Langues metric
     */
    private computeMaxScore;
    /**
     * Classify trust level based on normalized score
     *
     * @param normalized - Normalized score ∈ [0,1]
     * @returns Trust level
     */
    private classifyTrustLevel;
    /**
     * Compute trust score for a node
     *
     * @param nodeId - Node identifier
     * @param trustVector - 6D trust vector (one per Sacred Tongue)
     * @param t - Current time (default: Date.now() / 1000)
     * @returns Trust score with classification
     */
    computeTrustScore(nodeId: string, trustVector: number[], t?: number): TrustScore;
    /**
     * Update node trust state
     *
     * @param nodeId - Node identifier
     * @param trustVector - 6D trust vector
     * @param score - Raw trust score
     */
    private updateNodeTrust;
    /**
     * Get node trust state
     *
     * @param nodeId - Node identifier
     * @returns Node trust state or undefined
     */
    getNodeTrust(nodeId: string): NodeTrust | undefined;
    /**
     * Get all nodes with trust level
     *
     * @param level - Trust level filter
     * @returns Array of node IDs
     */
    getNodesByTrustLevel(level: 'HIGH' | 'MEDIUM' | 'LOW' | 'CRITICAL'): string[];
    /**
     * Update dimension flux coefficients (breathing)
     *
     * Allows dynamic adjustment of dimensional participation:
     * - ν_l = 1.0: Full participation (polly)
     * - 0.5 < ν_l < 1.0: Partial participation (demi)
     * - ν_l < 0.5: Weak participation (quasi)
     *
     * @param nu - New flux coefficients [6]
     */
    updateFluxCoefficients(nu: number[]): void;
    /**
     * Get trust statistics
     *
     * @returns Statistics object
     */
    getStatistics(): {
        totalNodes: number;
        highTrust: number;
        mediumTrust: number;
        lowTrust: number;
        criticalTrust: number;
        averageScore: number;
    };
    /**
     * Clear all node trust data
     */
    clear(): void;
}
/**
 * Standalone Langues metric function (for external use)
 *
 * @param x - 6D trust vector
 * @param mu - Ideal values [6]
 * @param w - Harmonic weights [6]
 * @param beta - Growth coefficients [6]
 * @param omega - Temporal frequencies [6]
 * @param phi - Phase offsets [6]
 * @param t - Current time
 * @param nu - Flux coefficients [6] (optional)
 * @returns Langues metric L(x,t)
 */
export declare function languesMetric(x: number[], mu: number[], w: number[], beta: number[], omega: number[], phi: number[], t: number, nu?: number[]): number;
/**
 * Langues metric with flux (breathing dimensions)
 *
 * @param x - 6D trust vector
 * @param mu - Ideal values [6]
 * @param w - Harmonic weights [6]
 * @param beta - Growth coefficients [6]
 * @param omega - Temporal frequencies [6]
 * @param phi - Phase offsets [6]
 * @param t - Current time
 * @param nu - Flux coefficients [6]
 * @returns Langues metric L_f(x,t)
 */
export declare function languesMetricFlux(x: number[], mu: number[], w: number[], beta: number[], omega: number[], phi: number[], t: number, nu: number[]): number;
/**
 * Export all functions for Layer 3 integration
 */
declare const _default: {
    TrustManager: typeof TrustManager;
    languesMetric: typeof languesMetric;
    languesMetricFlux: typeof languesMetricFlux;
    DEFAULT_LANGUES_PARAMS: LanguesParams;
    SacredTongue: typeof SacredTongue;
};
export default _default;
//# sourceMappingURL=trust-manager.d.ts.map