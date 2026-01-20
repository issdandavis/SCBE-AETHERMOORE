/**
 * Dual-Channel Consensus: Matched Filter Verification
 *
 * Computes matched-filter projections and correlation scores
 *
 * Part of SCBE-AETHERMOORE v3.0.0
 * Patent: USPTO #63/961,403
 */
import { AudioProfile, VerificationResult } from './types';
/**
 * Compute matched-filter projections
 *
 * Formula: p_j = (2/N) · Σ y[n] · sin(2π k_j · n/N + φ_j)
 *
 * @param audio - Received audio samples
 * @param bins - Expected bin indices
 * @param phases - Expected phases
 * @param N - Frame size (samples)
 * @returns Per-bin projections
 */
export declare function computeProjections(audio: Float32Array, bins: number[], phases: number[], N: number): number[];
/**
 * Verify challenge-bound watermark
 *
 * @param audio - Received audio samples
 * @param challenge - Expected challenge bitstring
 * @param bins - Expected bin indices
 * @param phases - Expected phases
 * @param profile - Audio profile with thresholds
 * @returns Verification result
 */
export declare function verifyWatermark(audio: Float32Array, challenge: Uint8Array, bins: number[], phases: number[], profile: AudioProfile): VerificationResult;
//# sourceMappingURL=matched-filter.d.ts.map