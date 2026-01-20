/**
 * Dual-Channel Consensus: Watermark Generation
 *
 * Generates challenge-bound acoustic watermarks
 *
 * Part of SCBE-AETHERMOORE v3.0.0
 * Patent: USPTO #63/961,403
 */
import { WatermarkResult } from './types';
/**
 * Generate challenge-bound watermark
 *
 * Formula: s[n] = Σ a_j · (-1)^(c_j) · sin(2π k_j · n/N + φ_j)
 *
 * @param challenge - Challenge bitstring
 * @param bins - Selected bin indices
 * @param phases - Per-bin phases
 * @param N - Frame size (samples)
 * @param gamma - Mix gain
 * @returns Watermark waveform
 */
export declare function generateWatermark(challenge: Uint8Array, bins: number[], phases: number[], N: number, gamma: number): Float32Array;
/**
 * Generate watermark with full result metadata
 */
export declare function generateWatermarkWithMetadata(challenge: Uint8Array, bins: number[], phases: number[], N: number, gamma: number): WatermarkResult;
//# sourceMappingURL=watermark-generator.d.ts.map