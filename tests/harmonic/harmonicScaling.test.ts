/**
 * SCBE Harmonic Scaling Tests (Layer 12)
 *
 * Tests for H(d, R) = R^(d²) with:
 * - Mathematical invariant verification
 * - Boundary conditions
 * - Numerical stability
 * - Property-based testing
 * - Golden test vectors from specification
 */

import { describe, it, expect, test } from 'vitest';
import {
  harmonicScale,
  securityBits,
  securityLevel,
  harmonicDistance,
  octaveTranspose,
} from '../../src/harmonic/harmonicScaling.js';
import { CONSTANTS, Vector6D } from '../../src/harmonic/constants.js';

describe('harmonicScale - H(d, R) = R^(d²)', () => {
  // ═══════════════════════════════════════════════════════════════
  // Golden Test Vectors (from AETHERMOORE Specification)
  // ═══════════════════════════════════════════════════════════════
  describe('Golden test vectors', () => {
    const goldenVectors = [
      { d: 1, R: 1.5, expected: 1.5, tolerance: 1e-10 },
      { d: 2, R: 1.5, expected: 5.0625, tolerance: 1e-10 },
      { d: 3, R: 1.5, expected: 38.443359375, tolerance: 1e-10 },
      { d: 4, R: 1.5, expected: 656.840896606445, tolerance: 1e-3 },
      { d: 5, R: 1.5, expected: 25251.16839599609, tolerance: 1e-3 },
      { d: 6, R: 1.5, expected: 2184164.40625, tolerance: 1e-1 },
    ];

    goldenVectors.forEach(({ d, R, expected, tolerance }) => {
      it(`H(${d}, ${R}) ≈ ${expected}`, () => {
        const result = harmonicScale(d, R);
        expect(Math.abs(result - expected)).toBeLessThan(tolerance);
      });
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Mathematical Properties
  // ═══════════════════════════════════════════════════════════════
  describe('Mathematical invariants', () => {
    it('H(d, 1) = 1 for any d (identity)', () => {
      for (let d = 1; d <= 10; d++) {
        expect(harmonicScale(d, 1)).toBe(1);
      }
    });

    it('H(1, R) = R (linear case)', () => {
      const testRatios = [1.25, 1.333, 1.5, 1.6, 2.0];
      for (const R of testRatios) {
        expect(harmonicScale(1, R)).toBeCloseTo(R, 10);
      }
    });

    it('Super-exponential growth: H(d+1, R) / H(d, R) = R^(2d+1)', () => {
      const R = 1.5;
      for (let d = 1; d <= 5; d++) {
        const ratio = harmonicScale(d + 1, R) / harmonicScale(d, R);
        const expected = Math.pow(R, 2 * d + 1);
        expect(ratio).toBeCloseTo(expected, 6);
      }
    });

    it('Inverse duality: H(d, R) × H(d, 1/R) = 1', () => {
      for (let d = 1; d <= 6; d++) {
        const R = 1.5;
        const product = harmonicScale(d, R) * harmonicScale(d, 1 / R);
        expect(product).toBeCloseTo(1, 10);
      }
    });

    it('Monotonicity: H(d, R) increases with d for R > 1', () => {
      const R = 1.5;
      let prev = 0;
      for (let d = 1; d <= 6; d++) {
        const current = harmonicScale(d, R);
        expect(current).toBeGreaterThan(prev);
        prev = current;
      }
    });

    it('Monotonicity: H(d, R) decreases with d for 0 < R < 1', () => {
      const R = 0.8;
      let prev = Infinity;
      for (let d = 1; d <= 6; d++) {
        const current = harmonicScale(d, R);
        expect(current).toBeLessThan(prev);
        prev = current;
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Boundary Conditions
  // ═══════════════════════════════════════════════════════════════
  describe('Boundary conditions', () => {
    it('throws for d < 1', () => {
      expect(() => harmonicScale(0)).toThrow(RangeError);
      expect(() => harmonicScale(-1)).toThrow(RangeError);
    });

    it('throws for non-integer d', () => {
      expect(() => harmonicScale(1.5)).toThrow(RangeError);
      expect(() => harmonicScale(2.7)).toThrow(RangeError);
    });

    it('throws for R <= 0', () => {
      expect(() => harmonicScale(1, 0)).toThrow(RangeError);
      expect(() => harmonicScale(1, -1)).toThrow(RangeError);
    });

    it('handles very small R correctly', () => {
      expect(harmonicScale(1, 0.001)).toBeCloseTo(0.001, 10);
      expect(harmonicScale(2, 0.1)).toBeCloseTo(0.0001, 10);
    });

    it('handles R close to 1 correctly', () => {
      const R = 1.0001;
      expect(harmonicScale(1, R)).toBeCloseTo(R, 10);
      expect(harmonicScale(6, R)).toBeCloseTo(Math.pow(R, 36), 10);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Numerical Stability
  // ═══════════════════════════════════════════════════════════════
  describe('Numerical stability', () => {
    it('returns finite values for d <= 6, R = 1.5', () => {
      for (let d = 1; d <= 6; d++) {
        const result = harmonicScale(d, 1.5);
        expect(Number.isFinite(result)).toBe(true);
      }
    });

    it('detects overflow for large d', () => {
      // d=20, R=1.5 → 1.5^400 ≈ 10^70 (still finite)
      // d=50, R=2.0 → 2^2500 → overflow (Infinity)
      expect(() => harmonicScale(50, 2.0)).toThrow(/overflow/i);
    });

    it('handles IEEE 754 edge cases', () => {
      // Very precise calculation near machine epsilon
      const result = harmonicScale(1, 1 + Number.EPSILON);
      expect(Number.isFinite(result)).toBe(true);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Property-Based Testing (Fuzzing)
  // ═══════════════════════════════════════════════════════════════
  describe('Property-based tests', () => {
    const randomInt = (min: number, max: number) =>
      Math.floor(Math.random() * (max - min + 1)) + min;
    const randomFloat = (min: number, max: number) =>
      Math.random() * (max - min) + min;

    it('H(d, R) > 0 for all valid inputs (100 trials)', () => {
      for (let i = 0; i < 100; i++) {
        const d = randomInt(1, 6);
        const R = randomFloat(0.1, 3.0);
        expect(harmonicScale(d, R)).toBeGreaterThan(0);
      }
    });

    it('H(d, R) is deterministic (50 trials)', () => {
      for (let i = 0; i < 50; i++) {
        const d = randomInt(1, 6);
        const R = randomFloat(0.5, 2.0);
        const result1 = harmonicScale(d, R);
        const result2 = harmonicScale(d, R);
        expect(result1).toBe(result2);
      }
    });

    it('log(H(d, R)) = d² × log(R) (50 trials)', () => {
      for (let i = 0; i < 50; i++) {
        const d = randomInt(1, 5);
        const R = randomFloat(1.1, 2.0);
        const logH = Math.log(harmonicScale(d, R));
        const expected = d * d * Math.log(R);
        expect(logH).toBeCloseTo(expected, 10);
      }
    });
  });
});

describe('securityBits', () => {
  it('computes effective bits correctly', () => {
    // S_bits(d, R, B) = B + d² × log₂(R)
    const baseBits = 128;
    const d = 6;
    const R = 1.5;
    const expected = 128 + 36 * Math.log2(1.5); // ≈ 128 + 21.06 ≈ 149
    expect(securityBits(baseBits, d, R)).toBeCloseTo(expected, 6);
  });

  it('returns baseBits when R = 1', () => {
    expect(securityBits(128, 6, 1)).toBe(128);
    expect(securityBits(256, 3, 1)).toBe(256);
  });

  it('adds ~21 bits at d=6, R=1.5', () => {
    const added = securityBits(0, 6, 1.5);
    expect(added).toBeCloseTo(21.059, 2);
  });
});

describe('securityLevel', () => {
  it('computes S = B × H(d, R) correctly', () => {
    const base = 1000;
    const d = 3;
    const R = 1.5;
    const expected = base * harmonicScale(d, R);
    expect(securityLevel(base, d, R)).toBeCloseTo(expected, 6);
  });
});

describe('harmonicDistance', () => {
  it('returns 0 for identical vectors', () => {
    const v: Vector6D = [1, 2, 3, 4, 5, 6];
    expect(harmonicDistance(v, v)).toBe(0);
  });

  it('is symmetric: d(u, v) = d(v, u)', () => {
    const u: Vector6D = [1, 2, 3, 4, 5, 6];
    const v: Vector6D = [2, 3, 4, 5, 6, 7];
    expect(harmonicDistance(u, v)).toBe(harmonicDistance(v, u));
  });

  it('satisfies triangle inequality: d(u, w) ≤ d(u, v) + d(v, w)', () => {
    const u: Vector6D = [0, 0, 0, 0, 0, 0];
    const v: Vector6D = [1, 1, 1, 1, 1, 1];
    const w: Vector6D = [2, 2, 2, 2, 2, 2];
    const d_uw = harmonicDistance(u, w);
    const d_uv = harmonicDistance(u, v);
    const d_vw = harmonicDistance(v, w);
    expect(d_uw).toBeLessThanOrEqual(d_uv + d_vw + 1e-10);
  });

  it('weights higher dimensions more (R^(1/5) progression)', () => {
    // Distance in dimension 6 should contribute more than dimension 1
    const u: Vector6D = [0, 0, 0, 0, 0, 0];
    const v1: Vector6D = [1, 0, 0, 0, 0, 0]; // Δ in dim 1
    const v6: Vector6D = [0, 0, 0, 0, 0, 1]; // Δ in dim 6
    expect(harmonicDistance(u, v6)).toBeGreaterThan(harmonicDistance(u, v1));
  });
});

describe('octaveTranspose', () => {
  it('doubles frequency for +1 octave', () => {
    expect(octaveTranspose(440, 1)).toBe(880);
    expect(octaveTranspose(100, 1)).toBe(200);
  });

  it('halves frequency for -1 octave', () => {
    expect(octaveTranspose(440, -1)).toBe(220);
    expect(octaveTranspose(100, -1)).toBe(50);
  });

  it('returns original for 0 octaves', () => {
    expect(octaveTranspose(440, 0)).toBe(440);
  });

  it('compounds correctly: +2 octaves = ×4', () => {
    expect(octaveTranspose(100, 2)).toBe(400);
    expect(octaveTranspose(100, 3)).toBe(800);
  });

  it('throws for non-positive frequency', () => {
    expect(() => octaveTranspose(0, 1)).toThrow(RangeError);
    expect(() => octaveTranspose(-440, 1)).toThrow(RangeError);
  });

  it('handles fractional octaves', () => {
    // +0.5 octaves should be ×√2
    expect(octaveTranspose(100, 0.5)).toBeCloseTo(100 * Math.SQRT2, 10);
  });
});
