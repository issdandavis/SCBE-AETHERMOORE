/**
 * SCBE Harmonic Scaling (Layer 12)
 *
 * Core mathematical functions for harmonic scaling:
 * - H(d, R) = R^(d²) - Exponential risk amplification
 * - Security bit calculations
 * - Harmonic distance in 6D space
 * - Octave transposition
 */
import { Vector6D } from './constants.js';
/**
 * Harmonic scale function H(d, R) = exp(d² * ln(R)) = R^(d²)
 *
 * For R=1.5, d=6: H = 1.5^36 ≈ 2.18 × 10⁶
 *
 * @param d - Dimension/deviation parameter (integer >= 1)
 * @param R - Base ratio (default: 1.5)
 * @returns Scaled value
 */
export declare function harmonicScale(d: number, R?: number): number;
/**
 * Calculate security bits with harmonic amplification
 *
 * @param baseBits - Base security level in bits
 * @param d - Dimension parameter
 * @param R - Base ratio
 * @returns Amplified security bits
 */
export declare function securityBits(baseBits: number, d: number, R?: number): number;
/**
 * Calculate security level with harmonic scaling
 *
 * @param base - Base security level
 * @param d - Dimension parameter
 * @param R - Base ratio
 * @returns Scaled security level
 */
export declare function securityLevel(base: number, d: number, R?: number): number;
/**
 * Harmonic distance in 6D phase space with weighted dimensions
 *
 * Uses R^(1/5) weighting for dimensions 4-6 (the "sacred tongue" dimensions)
 *
 * @param u - First 6D vector
 * @param v - Second 6D vector
 * @returns Weighted Euclidean distance
 */
export declare function harmonicDistance(u: Vector6D, v: Vector6D): number;
/**
 * Transpose a frequency by octaves
 *
 * @param freq - Base frequency (must be > 0)
 * @param octaves - Number of octaves to transpose (can be negative)
 * @returns Transposed frequency
 */
export declare function octaveTranspose(freq: number, octaves: number): number;
//# sourceMappingURL=harmonicScaling.d.ts.map