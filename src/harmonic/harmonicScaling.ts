/**
 * @file harmonicScaling.ts
 * @module harmonic/harmonicScaling
 * @layer Layer 12
 * @component Risk Amplification Engine
 * @version 3.0.0
 * @since 2026-01-20
 *
 * SCBE Harmonic Scaling - Creates exponential "hard walls" for risk amplification.
 *
 * Layer 12: H(d, R) = R^(d²) - Super-exponential risk amplification
 *
 * Key functions:
 * - harmonicScale(d, R) - Core risk amplifier
 * - securityBits(H) - Convert to security bit equivalent
 * - harmonicDistance6D(a, b) - 6D space distance
 * - octaveTranspose(f, n) - Frequency transposition
 */

import { CONSTANTS, Vector6D } from './constants.js';
import { assertIntGE, assertFinite, log2 } from './assertions.js';

/**
 * Harmonic scale function H(d, R) = exp(d² * ln(R)) = R^(d²)
 *
 * For R=1.5, d=6: H = 1.5^36 ≈ 2.18 × 10⁶
 *
 * @param d - Dimension/deviation parameter (integer >= 1)
 * @param R - Base ratio (default: 1.5)
 * @returns Scaled value
 */
export function harmonicScale(d: number, R: number = CONSTANTS.DEFAULT_R): number {
  assertIntGE('d', d, 1);
  if (!(R > 0)) throw new RangeError('R must be > 0');
  const e = d * d * Math.log(R);
  const y = Math.exp(e);
  assertFinite(y, 'harmonicScale overflow');
  return y;
}

/**
 * Calculate security bits with harmonic amplification
 *
 * @param baseBits - Base security level in bits
 * @param d - Dimension parameter
 * @param R - Base ratio
 * @returns Amplified security bits
 */
export function securityBits(baseBits: number, d: number, R: number = CONSTANTS.DEFAULT_R): number {
  assertIntGE('d', d, 1);
  if (!(R > 0)) throw new RangeError('R must be > 0');
  return baseBits + d * d * log2(R);
}

/**
 * Calculate security level with harmonic scaling
 *
 * @param base - Base security level
 * @param d - Dimension parameter
 * @param R - Base ratio
 * @returns Scaled security level
 */
export function securityLevel(base: number, d: number, R: number = CONSTANTS.DEFAULT_R): number {
  return base * harmonicScale(d, R);
}

/**
 * Harmonic distance in 6D phase space with weighted dimensions
 *
 * Uses R^(1/5) weighting for dimensions 4-6 (the "sacred tongue" dimensions)
 *
 * @param u - First 6D vector
 * @param v - Second 6D vector
 * @returns Weighted Euclidean distance
 */
export function harmonicDistance(u: Vector6D, v: Vector6D): number {
  const R5 = CONSTANTS.R_FIFTH;
  const g: number[] = [1, 1, 1, R5, R5 * R5, R5 * R5 * R5];
  let s = 0;
  for (let i = 0; i < 6; i++) {
    const d = u[i] - v[i];
    s += g[i] * d * d;
  }
  return Math.sqrt(s);
}

/**
 * Transpose a frequency by octaves
 *
 * @param freq - Base frequency (must be > 0)
 * @param octaves - Number of octaves to transpose (can be negative)
 * @returns Transposed frequency
 */
export function octaveTranspose(freq: number, octaves: number): number {
  if (!(freq > 0)) throw new RangeError('freq must be > 0');
  return freq * Math.pow(2, octaves);
}
