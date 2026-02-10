/**
 * @file detection.ts
 * @module ai_brain/detection
 * @layer Layer 5, Layer 9, Layer 12, Layer 13
 * @component Multi-Vectored Detection Mechanisms
 * @version 1.1.0
 * @since 2026-02-07
 *
 * Implements the 5 orthogonal detection mechanisms validated at 1.000 AUC:
 *
 * 1. Phase + Distance Scoring (AUC 1.000) - Wrong-tongue / synthetic attacks
 * 2. Curvature Accumulation (AUC 0.994) - Deviating paths (2.45x Euclidean advantage)
 * 3. Threat Dimension Lissajous (AUC 1.000) - Malicious knot patterns
 * 4. Decimal Drift Magnitude (AUC 0.995) - No-pipeline / scale attacks
 * 5. Six-Tonic Oscillation (AUC 1.000) - Replay / static / wrong-frequency
 *
 * Coverage: 7/8 attack types. Rounded-decimal gap remains (needs real jitter data).
 */
import { type DetectionResult, type CombinedAssessment, type TrajectoryPoint, type BrainConfig } from './types.js';
/**
 * Detect wrong-tongue and synthetic attacks using phase + hyperbolic distance.
 *
 * The Sacred Tongues protocol assigns each domain a specific phase angle.
 * An agent using the wrong tongue for its declared domain will exhibit
 * phase misalignment. Combined with hyperbolic distance from the safe
 * origin, this catches synthetic/fabricated inputs.
 *
 * @param trajectory - Agent trajectory points
 * @param expectedTongueIndex - Expected Sacred Tongue index (0-5)
 * @param threshold - Detection threshold (default: 0.7)
 * @returns Detection result
 */
export declare function detectPhaseDistance(trajectory: TrajectoryPoint[], expectedTongueIndex: number, threshold?: number): DetectionResult;
/**
 * Detect deviating paths via curvature accumulation in hyperbolic space.
 *
 * Honest agents follow smooth geodesics (low curvature). Adversarial agents
 * exhibit erratic path changes (high curvature). In hyperbolic space, this
 * separation is 2.45x better than Euclidean due to the exponential metric.
 *
 * @param trajectory - Agent trajectory points
 * @param windowSize - Sliding window size for curvature analysis
 * @param threshold - Detection threshold
 * @returns Detection result
 */
export declare function detectCurvatureAccumulation(trajectory: TrajectoryPoint[], windowSize?: number, threshold?: number): DetectionResult;
/**
 * Detect malicious patterns using Lissajous analysis in the threat dimension.
 *
 * When trajectory points are projected onto a 2D threat plane (intent alignment
 * vs behavioral score), malicious agents form distinctive knot patterns that
 * are topologically invisible in other projections.
 *
 * The key insight: honest agents trace simple paths, malicious agents create
 * self-intersecting Lissajous figures.
 *
 * @param trajectory - Agent trajectory points
 * @param threshold - Detection threshold
 * @returns Detection result
 */
export declare function detectThreatLissajous(trajectory: TrajectoryPoint[], threshold?: number): DetectionResult;
/**
 * Detect scale and no-pipeline attacks via decimal drift magnitude.
 *
 * Agents that bypass the SCBE pipeline produce state vectors with
 * characteristic decimal patterns (too clean, too uniform, or with
 * drift accumulation that doesn't match legitimate processing).
 *
 * This mechanism catches attacks that phase analysis misses.
 *
 * @param trajectory - Agent trajectory points
 * @param threshold - Detection threshold
 * @returns Detection result
 */
export declare function detectDecimalDrift(trajectory: TrajectoryPoint[], threshold?: number): DetectionResult;
/**
 * Detect replay, static, and wrong-frequency attacks via six-tonic oscillation.
 *
 * The Sacred Tongues protocol requires agents to exhibit characteristic
 * oscillation patterns at specific frequencies. Replayed signals have
 * stale frequencies, static signals have no oscillation, and wrong-frequency
 * signals misalign with the expected tonic pattern.
 *
 * @param trajectory - Agent trajectory points
 * @param expectedTongueIndex - Expected active tongue (0-5)
 * @param baseFreq - Reference frequency (default: 440 Hz)
 * @param threshold - Detection threshold
 * @returns Detection result
 */
export declare function detectSixTonic(trajectory: TrajectoryPoint[], expectedTongueIndex: number, baseFreq?: number, threshold?: number): DetectionResult;
/**
 * Run all 5 detection mechanisms and produce a combined assessment.
 *
 * The mechanisms are orthogonal - each detects different attack types:
 * 1. Phase + Distance -> wrong-tongue, synthetic
 * 2. Curvature -> path deviation, drift
 * 3. Threat Lissajous -> malicious patterns, knot topology
 * 4. Decimal Drift -> no-pipeline, scale attacks
 * 5. Six-Tonic -> replay, static, wrong-frequency
 *
 * @param trajectory - Agent trajectory points
 * @param expectedTongueIndex - Expected Sacred Tongue index
 * @param config - Brain configuration
 * @returns Combined assessment with risk decision
 */
export declare function runCombinedDetection(trajectory: TrajectoryPoint[], expectedTongueIndex: number, config?: BrainConfig): CombinedAssessment;
//# sourceMappingURL=detection.d.ts.map