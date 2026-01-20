/**
 * Dual-Channel Consensus: Bin Selection
 *
 * Deterministically selects frequency bins and phases from challenge
 *
 * Part of SCBE-AETHERMOORE v3.0.0
 * Patent: USPTO #63/961,403
 */
/// <reference types="node" />
/// <reference types="node" />
import { BinSelection } from './types';
/**
 * Select bins and phases deterministically from challenge
 *
 * @param seed - HMAC-derived seed from (K, τ, n, c)
 * @param b - Number of bits (bins to select)
 * @param k_min - Minimum bin index
 * @param k_max - Maximum bin index
 * @param delta_k_min - Minimum bin spacing
 * @returns Selected bins and phases
 */
export declare function selectBinsAndPhases(seed: Buffer, b: number, k_min: number, k_max: number, delta_k_min: number): BinSelection;
//# sourceMappingURL=bin-selector.d.ts.map