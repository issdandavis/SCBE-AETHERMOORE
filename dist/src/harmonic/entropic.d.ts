/**
 * @file entropic.ts
 * @module harmonic/entropic
 * @layer Layer 5, Layer 6, Layer 12, Layer 13
 * @component Entropic Layer — Escape Detection, Adaptive-k, Expansion Tracking
 * @version 3.2.4
 *
 * Consolidates the scattered entropy-related concepts from CHSFN,
 * Dual Lattice, and the immune system into a single module with
 * testable invariants.
 *
 * Three mechanisms:
 *   1. Escape Detection — detects when a state leaves its trust basin
 *      by monitoring hyperbolic velocity and basin boundary crossings
 *   2. Adaptive k — dynamically adjusts the number of nearest governance
 *      nodes based on local entropy and trust density
 *   3. Expansion Tracking — measures how fast a state's reachable volume
 *      grows in the Poincaré ball (Lyapunov-like exponent)
 *
 * Key invariants:
 *   - Escape triggers when velocity exceeds the basin escape threshold
 *   - Adaptive k is monotonically non-decreasing with entropy
 *   - Expansion rate is bounded by the curvature-dependent maximum
 *   - All three mechanisms compose into a single EntropicState
 *
 * Builds on:
 *   - hyperbolic.ts: Poincaré distance, mobiusAdd, expMap0/logMap0 (L5)
 *   - adaptiveNavigator.ts: REALM_CENTERS, trajectoryEntropy (L5, L6)
 *   - harmonicScaling.ts: harmonicScale (L12)
 *   - phdm.ts: deviation detection pattern (L8)
 */
/** Configuration for a trust basin centered at a realm. */
export interface TrustBasin {
    /** Center of the basin in Poincaré ball */
    center: number[];
    /** Hyperbolic radius of the basin */
    radius: number;
    /** Label (e.g., tongue code) */
    label: string;
}
/** A timestamped position sample in the Poincaré ball. */
export interface EntropicSample {
    /** Position in Poincaré ball */
    position: number[];
    /** Timestamp in ms */
    timestamp: number;
}
/** Result of escape detection for a single sample. */
export interface EscapeResult {
    /** Whether the state has escaped its trust basin */
    escaped: boolean;
    /** Nearest basin label */
    nearestBasin: string;
    /** Hyperbolic distance to nearest basin center */
    distanceToCenter: number;
    /** Hyperbolic radius of nearest basin */
    basinRadius: number;
    /** Instantaneous hyperbolic velocity (distance / dt) */
    velocity: number;
    /** Whether velocity exceeds escape threshold */
    velocityExceeded: boolean;
}
/** Result of adaptive-k computation. */
export interface AdaptiveKResult {
    /** Number of governance nodes to consult */
    k: number;
    /** Local Shannon entropy that drove the decision */
    localEntropy: number;
    /** Trust density in the neighborhood */
    trustDensity: number;
    /** Explanation of the k selection */
    reason: string;
}
/** Result of expansion tracking. */
export interface ExpansionResult {
    /** Lyapunov-like expansion rate */
    expansionRate: number;
    /** Reachable volume estimate (hyperbolic) */
    reachableVolume: number;
    /** Whether expansion is accelerating */
    accelerating: boolean;
    /** Number of samples used */
    sampleCount: number;
}
/** Combined entropic state from all three mechanisms. */
export interface EntropicState {
    /** Escape detection result */
    escape: EscapeResult;
    /** Adaptive-k result */
    adaptiveK: AdaptiveKResult;
    /** Expansion tracking result */
    expansion: ExpansionResult;
    /** Combined entropic score in [0, 1] — higher = more entropic/dangerous */
    entropicScore: number;
    /** Risk decision based on entropic score */
    decision: 'STABLE' | 'DRIFTING' | 'ESCAPING' | 'CHAOTIC';
    /** Timestamp of this assessment */
    timestamp: number;
}
/** Configuration for the entropic layer. */
export interface EntropicConfig {
    /** Trust basins (default: derived from REALM_CENTERS) */
    basins: TrustBasin[];
    /** History window size (default: 100) */
    historyWindow: number;
    /** Minimum k (governance nodes, default: 3) */
    kMin: number;
    /** Maximum k (default: 21) */
    kMax: number;
    /** Escape velocity threshold (default: 2.0 hyperbolic units/sec) */
    escapeVelocityThreshold: number;
    /** Entropy bins for local entropy computation (default: 20) */
    entropyBins: number;
    /** Expansion rate alarm threshold (default: 1.5) */
    expansionAlarmThreshold: number;
    /** Decision thresholds */
    thresholds: {
        drifting: number;
        escaping: number;
        chaotic: number;
    };
    /** Dimension of the Poincaré ball (default: 6) */
    dimension: number;
}
/**
 * Detect whether a state has escaped its trust basin.
 *
 * A state "escapes" when:
 *   1. Its hyperbolic distance to the nearest basin center exceeds
 *      the basin radius, OR
 *   2. Its instantaneous hyperbolic velocity exceeds the escape
 *      threshold (fast radial movement away from center)
 *
 * @param current - Current position sample
 * @param previous - Previous position sample (for velocity)
 * @param basins - Trust basins to check against
 * @param escapeVelocityThreshold - Velocity threshold for escape
 */
export declare function detectEscape(current: EntropicSample, previous: EntropicSample | null, basins: TrustBasin[], escapeVelocityThreshold?: number): EscapeResult;
/**
 * Compute Shannon entropy of a set of positions using histogram binning.
 *
 * @param positions - Array of position vectors
 * @param bins - Number of bins per dimension (default: 20)
 * @returns Shannon entropy in bits, normalized to [0, 1]
 */
export declare function computeLocalEntropy(positions: number[][], bins?: number): number;
/**
 * Compute trust density — the fraction of recent positions that are
 * within "trusted" range (harmonicScale > 0.5) of a governance center.
 *
 * @param positions - Recent position history
 * @param basins - Trust basins
 * @returns Trust density in [0, 1]
 */
export declare function computeTrustDensity(positions: number[][], basins: TrustBasin[]): number;
/**
 * Dynamically compute the number of governance nodes (k) to consult
 * based on local entropy and trust density.
 *
 * Higher entropy → more governance nodes needed (more uncertainty)
 * Lower trust density → more governance nodes needed (less coverage)
 *
 * Formula: k = kMin + floor((kMax - kMin) * entropy * (1 - trustDensity))
 *
 * Invariant: k is monotonically non-decreasing with entropy.
 *
 * @param positions - Recent position history
 * @param basins - Trust basins
 * @param kMin - Minimum k (default: 3)
 * @param kMax - Maximum k (default: 21)
 * @param bins - Entropy histogram bins (default: 20)
 */
export declare function computeAdaptiveK(positions: number[][], basins: TrustBasin[], kMin?: number, kMax?: number, bins?: number): AdaptiveKResult;
/**
 * Estimate the Lyapunov-like expansion rate from a trajectory.
 *
 * Measures how fast the "reachable volume" of a state grows by tracking
 * the average rate of hyperbolic distance increase between consecutive
 * samples. In the Poincaré ball, volume grows exponentially with radius,
 * so even moderate distance increases correspond to large volume changes.
 *
 * @param samples - Timestamped position history (at least 3 samples)
 * @returns Expansion rate (positive = expanding, negative = contracting)
 */
export declare function computeExpansionRate(samples: EntropicSample[]): number;
/**
 * Estimate the reachable volume from a set of positions using the
 * hyperbolic volume formula. In the Poincaré ball of dimension n,
 * a ball of hyperbolic radius r has volume proportional to
 * sinh^(n-1)(r).
 *
 * We use the maximum pairwise distance as the "radius" of the
 * reachable region.
 *
 * @param positions - Recent position vectors
 * @param dimension - Ball dimension (default: 6)
 */
export declare function estimateReachableVolume(positions: number[][], dimension?: number): number;
/**
 * Track expansion over time and detect acceleration.
 *
 * @param samples - Position history
 * @param dimension - Ball dimension
 */
export declare function trackExpansion(samples: EntropicSample[], dimension?: number): ExpansionResult;
/**
 * The EntropicMonitor consolidates escape detection, adaptive-k, and
 * expansion tracking into a single stateful monitor that tracks a
 * trajectory over time.
 */
export declare class EntropicMonitor {
    private readonly config;
    private history;
    constructor(config?: Partial<EntropicConfig>);
    /**
     * Record a new position sample and compute the full entropic state.
     *
     * @param position - Current position in Poincaré ball
     * @param timestamp - Timestamp in ms (default: Date.now())
     * @returns Full EntropicState assessment
     */
    observe(position: number[], timestamp?: number): EntropicState;
    /**
     * Get the current history window.
     */
    getHistory(): EntropicSample[];
    /**
     * Get the number of samples in history.
     */
    get historySize(): number;
    /**
     * Reset history.
     */
    reset(): void;
    /**
     * Get the configured trust basins.
     */
    getBasins(): TrustBasin[];
}
/**
 * Create default trust basins from the Sacred Tongue realm centers.
 * Each basin has a radius of 1.0 hyperbolic units.
 */
export declare function defaultBasins(radius?: number): TrustBasin[];
/**
 * Verify the core entropic invariants. Useful for testing and CI.
 *
 * 1. accessCost >= 1 for all non-negative distances
 * 2. adaptive k is monotonically non-decreasing with entropy
 * 3. expansion rate is finite and bounded
 *
 * @returns Array of { name, passed, detail } for each invariant
 */
export declare function verifyEntropicInvariants(): Array<{
    name: string;
    passed: boolean;
    detail: string;
}>;
/**
 * Create a pre-configured EntropicMonitor.
 */
export declare function createEntropicMonitor(config?: Partial<EntropicConfig>): EntropicMonitor;
//# sourceMappingURL=entropic.d.ts.map