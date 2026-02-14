/**
 * @file harmonicScaling.ts
 * @module harmonic/harmonicScaling
 * @layer Layer 12
 * @component Risk Amplification Engine
 * @version 3.3.0
 * @since 2026-01-20
 *
 * SCBE Harmonic Scaling - Bounded risk scoring for the 14-layer pipeline.
 *
 * Layer 12 — **H_score** variant:
 *   H_score = 1 / (1 + d_H + 2 * phaseDeviation)   ∈ (0, 1]
 *
 * The previous super-exponential formula R^(d²) caused numerical collapse:
 * small distances all mapped to ~1.0, destroying ranking (AUC 0.054 on
 * subtle attacks vs baseline 0.984). This bounded formula preserves
 * differentiation at all distance scales.
 *
 * NOTE — Two H formulas coexist in the codebase:
 *   • H_score (this file):  1/(1+d+2·pd)  ∈ (0,1]
 *     Used by the 14-layer pipeline (L12→L13).
 *     L13 divides: Risk' = Risk_base / H_score  (lower → higher risk).
 *   • H_wall (harmonic_scaling_law.py):  1+α·tanh(β·d*)  ∈ [1, 1+α]
 *     Risk amplification multiplier.
 *     L13 multiplies: Final_Risk' = Behavioral_Risk * H_wall.
 *
 * Key functions:
 * - harmonicScale(d, phaseDeviation) - Core risk scorer (bounded 0-1)
 * - securityBits(baseBits, d, phaseDeviation) - Security bit equivalent
 * - harmonicDistance(u, v) - 6D space distance
 * - octaveTranspose(f, n) - Frequency transposition
 */

import { CONSTANTS, Vector6D } from './constants.js';
import { assertFinite, log2 } from './assertions.js';

/**
 * Harmonic scale function: score = 1 / (1 + d + 2 * phaseDeviation)
 *
 * Returns a safety score in (0, 1]:
 *   - d=0, pd=0 → 1.0 (at safe center)
 *   - d=1, pd=0 → 0.5
 *   - d=2, pd=0 → 0.333
 *   - d→∞       → 0.0
 *
 * @param d - Hyperbolic distance / dimension parameter (>= 0)
 * @param phaseDeviation - Phase deviation from expected coherence (>= 0, default: 0)
 * @returns Safety score in (0, 1]
 */
export function harmonicScale(d: number, phaseDeviation: number = 0): number {
  if (d < 0) throw new RangeError('d must be >= 0');
  if (phaseDeviation < 0) throw new RangeError('phaseDeviation must be >= 0');
  const y = 1 / (1 + d + 2 * phaseDeviation);
  assertFinite(y, 'harmonicScale');
  return y;
}

/**
 * Calculate security bits with harmonic scaling
 *
 * S_bits = baseBits + log₂(1 + d + 2 * phaseDeviation)
 *
 * @param baseBits - Base security level in bits
 * @param d - Distance parameter (>= 0)
 * @param phaseDeviation - Phase deviation (>= 0, default: 0)
 * @returns Effective security bits (grows with distance)
 */
export function securityBits(baseBits: number, d: number, phaseDeviation: number = 0): number {
  if (d < 0) throw new RangeError('d must be >= 0');
  if (phaseDeviation < 0) throw new RangeError('phaseDeviation must be >= 0');
  return baseBits + log2(1 + d + 2 * phaseDeviation);
}

/**
 * Calculate security level with harmonic scaling
 *
 * S = base * (1 + d + 2 * phaseDeviation)
 *
 * @param base - Base security level
 * @param d - Distance parameter (>= 0)
 * @param phaseDeviation - Phase deviation (>= 0, default: 0)
 * @returns Scaled security level (grows linearly with distance)
 */
export function securityLevel(base: number, d: number, phaseDeviation: number = 0): number {
  return base * (1 + d + 2 * phaseDeviation);
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
