/**
 * @file entropicLayer.ts
 * @module harmonic/entropicLayer
 * @layer Layer 7, Layer 12, Layer 13
 * @component Entropic Layer — Escape Detection, Adaptive k, Expansion Tracking
 * @version 3.2.4
 *
 * Consolidates the "Entropic / GeoSeal bottom layer" from the DualLatticeStack v2:
 *
 *   1. Escape Detection: Detects when a CHSFN state is leaving its trust basin
 *      (velocity toward boundary exceeds threshold, or state crosses basin lip).
 *
 *   2. Adaptive k: Dynamically adjusts the number of governance nodes (neighbors)
 *      queried for consensus, based on local threat level and state stability.
 *
 *   3. Expansion Tracking: Measures how fast a state's reachable volume grows.
 *      Rapid expansion = the state is "exploring" (possibly adversarial drift).
 *      Contraction = the state is stabilizing toward an attractor.
 *
 *   4. Time Dilation: For hostile loops, increases the effective step cost
 *      so repeated probing becomes exponentially slower.
 *
 * The UM tongue ("entropic sink") acts as the primary driver:
 *   higher UM impedance → more entropy → faster decay / redaction.
 */
import type { Vector6D } from './constants.js';
import { type CHSFNState } from './chsfn.js';
/**
 * Escape status for a CHSFN state.
 */
export interface EscapeStatus {
    /** Whether the state is currently escaping its trust basin */
    escaping: boolean;
    /** Radial velocity (positive = moving toward boundary) */
    radialVelocity: number;
    /** Current Poincaré norm (distance from origin in Euclidean sense) */
    currentNorm: number;
    /** Trust basin radius (based on coherence) */
    basinRadius: number;
    /** Fraction of basin consumed: currentNorm / basinRadius */
    basinFraction: number;
    /** Energy at current position */
    energy: number;
    /** UM impedance (entropic pressure) */
    umImpedance: number;
}
/**
 * Adaptive k result — how many governance nodes to query.
 */
export interface AdaptiveKResult {
    /** Recommended number of governance nodes to query */
    k: number;
    /** Threat level in [0, 1] that drove the k selection */
    threatLevel: number;
    /** Stability score in [0, 1] */
    stability: number;
    /** Whether the state is in a high-alert zone */
    highAlert: boolean;
}
/**
 * Expansion tracking result.
 */
export interface ExpansionResult {
    /** Reachable volume at current position (hyperbolic) */
    currentVolume: number;
    /** Volume growth rate (dV/dτ) over the sample window */
    growthRate: number;
    /** Whether expansion is accelerating (positive second derivative) */
    accelerating: boolean;
    /** Contraction flag: negative growth rate → state is stabilizing */
    contracting: boolean;
    /** Volume history over the sample window */
    volumeTrace: number[];
}
/**
 * Time dilation result for hostile loop detection.
 */
export interface TimeDilationResult {
    /** Effective step cost multiplier (>1 means slowed) */
    dilationFactor: number;
    /** Number of loop repetitions detected */
    loopCount: number;
    /** Whether this is classified as a hostile loop */
    hostile: boolean;
    /** Entropy of the position trace (low = looping) */
    traceEntropy: number;
}
/**
 * Configuration for the entropic layer.
 */
export interface EntropicConfig {
    /** Radial velocity threshold for escape detection (default 0.01) */
    escapeVelocityThreshold: number;
    /** Basin fraction above which escape alarm triggers (default 0.8) */
    basinFractionThreshold: number;
    /** Minimum k for adaptive governance (default 2) */
    minK: number;
    /** Maximum k for adaptive governance (default 6) */
    maxK: number;
    /** Threat level above which high-alert triggers (default 0.7) */
    highAlertThreshold: number;
    /** Number of drift steps for expansion sampling (default 10) */
    expansionSampleSteps: number;
    /** Step size for expansion sampling (default 0.005) */
    expansionStepSize: number;
    /** Loop detection window size (default 20) */
    loopWindowSize: number;
    /** Similarity threshold for loop detection (default 0.95) */
    loopSimilarityThreshold: number;
}
export declare const DEFAULT_ENTROPIC_CONFIG: Readonly<EntropicConfig>;
/**
 * Detect whether a state is escaping its trust basin.
 *
 * A state escapes when:
 * 1. Its radial velocity (projected drift toward boundary) exceeds threshold
 * 2. Its current norm exceeds a fraction of the basin radius
 * 3. UM impedance is high (entropic pressure pushing outward)
 *
 * @param state - Current CHSFN state
 * @param coherence - Unit coherence (determines basin radius)
 * @param config - Entropic configuration
 * @returns EscapeStatus
 */
export declare function detectEscape(state: CHSFNState, coherence: number, config?: EntropicConfig): EscapeStatus;
/**
 * Compute the threat level from a CHSFN state.
 *
 * Threat is a composite of:
 * - Distance from origin (far = more threatening)
 * - Phase misalignment (average tongue impedance)
 * - Energy level (higher = more unstable)
 *
 * @param state - Current CHSFN state
 * @returns Threat level in [0, 1]
 */
export declare function computeThreatLevel(state: CHSFNState): number;
/**
 * Compute stability score from energy gradient magnitude.
 *
 * Low gradient = near equilibrium = stable.
 * High gradient = far from equilibrium = unstable.
 *
 * @param state - Current CHSFN state
 * @returns Stability in [0, 1] where 1 = perfectly stable
 */
export declare function computeStability(state: CHSFNState): number;
/**
 * Adaptively select the number of governance nodes to query.
 *
 * Higher threat → higher k (more nodes for consensus).
 * More stable → lower k (fewer nodes needed).
 *
 * k = minK + round((maxK - minK) · threatLevel · (1 - stability))
 *
 * @param state - Current CHSFN state
 * @param config - Entropic configuration
 * @returns AdaptiveKResult
 */
export declare function adaptiveK(state: CHSFNState, config?: EntropicConfig): AdaptiveKResult;
/**
 * Track the expansion rate of reachable volume around a drifting state.
 *
 * Reachable volume in 6D hyperbolic space grows as V(r) ~ e^{5r}.
 * We measure the "effective radius" via the trust radius derived from
 * the energy level, then track how this changes over drift steps.
 *
 * Rapid expansion → adversarial exploration.
 * Contraction → stabilizing toward attractor.
 *
 * @param state - Initial CHSFN state
 * @param config - Entropic configuration
 * @returns ExpansionResult
 */
export declare function trackExpansion(state: CHSFNState, config?: EntropicConfig): ExpansionResult;
/**
 * Detect hostile loops and compute time dilation factor.
 *
 * If a state is repeatedly visiting similar positions (low position entropy),
 * it's likely probing. Time dilation exponentially increases the effective
 * step cost for each detected repetition.
 *
 * dilationFactor = φ^loopCount
 *
 * @param positionHistory - Array of recent 6D positions
 * @param config - Entropic configuration
 * @returns TimeDilationResult
 */
export declare function detectTimeDilation(positionHistory: Vector6D[], config?: EntropicConfig): TimeDilationResult;
/**
 * Compute Shannon entropy of a position trace.
 *
 * Low entropy → positions cluster (looping).
 * High entropy → positions spread out (exploring or drifting normally).
 *
 * @param positions - Array of 6D positions
 * @returns Normalized entropy in [0, 1]
 */
export declare function computePositionEntropy(positions: Vector6D[]): number;
/**
 * Result of a full entropic layer assessment.
 */
export interface EntropicAssessment {
    escape: EscapeStatus;
    adaptiveK: AdaptiveKResult;
    expansion: ExpansionResult;
    timeDilation: TimeDilationResult;
    /** Overall entropic risk in [0, 1] */
    entropicRisk: number;
    /** Recommended action based on assessment */
    recommendation: 'PROCEED' | 'SLOW' | 'QUARANTINE' | 'DENY';
}
/**
 * Perform a full entropic layer assessment.
 *
 * Combines all four sub-systems into a unified risk score and recommendation.
 *
 * @param state - Current CHSFN state
 * @param coherence - Unit coherence
 * @param positionHistory - Recent position history (for loop detection)
 * @param config - Entropic configuration
 * @returns EntropicAssessment
 */
export declare function assess(state: CHSFNState, coherence: number, positionHistory?: Vector6D[], config?: EntropicConfig): EntropicAssessment;
//# sourceMappingURL=entropicLayer.d.ts.map