/**
 * SCBE Harmonic Scaling Tests (Layer 12)
 *
 * Tests for score = 1 / (1 + d + 2 * phaseDeviation) with:
 * - Mathematical invariant verification
 * - Boundary conditions
 * - Numerical stability
 * - Property-based testing
 * - Golden test vectors
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

describe('harmonicScale - score = 1 / (1 + d + 2 * phaseDeviation)', () => {
  // ═══════════════════════════════════════════════════════════════
  // Golden Test Vectors
  // ═══════════════════════════════════════════════════════════════
  describe('Golden test vectors', () => {
    const goldenVectors = [
      { d: 0, pd: 0, expected: 1.0 },
      { d: 1, pd: 0, expected: 0.5 },
      { d: 2, pd: 0, expected: 1 / 3 },
      { d: 3, pd: 0, expected: 0.25 },
      { d: 4, pd: 0, expected: 0.2 },
      { d: 9, pd: 0, expected: 0.1 },
      { d: 0, pd: 0.5, expected: 0.5 },
      { d: 1, pd: 1, expected: 0.25 },
      { d: 2, pd: 0.5, expected: 0.25 },
    ];

    goldenVectors.forEach(({ d, pd, expected }) => {
      it(`H(${d}, ${pd}) = ${expected}`, () => {
        expect(harmonicScale(d, pd)).toBeCloseTo(expected, 10);
      });
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Mathematical Properties
  // ═══════════════════════════════════════════════════════════════
  describe('Mathematical invariants', () => {
    it('H(0, 0) = 1 (identity at origin)', () => {
      expect(harmonicScale(0, 0)).toBe(1);
    });

    it('H(d, 0) = 1 / (1 + d) for any d', () => {
      for (let d = 0; d <= 10; d++) {
        expect(harmonicScale(d)).toBeCloseTo(1 / (1 + d), 10);
      }
    });

    it('Monotonicity: H(d1) > H(d2) when d1 < d2 (safety decreases with distance)', () => {
      let prev = 2; // larger than max
      for (let d = 0; d <= 10; d++) {
        const current = harmonicScale(d);
        expect(current).toBeLessThan(prev);
        prev = current;
      }
    });

    it('Bounded: 0 < H(d) <= 1 for all valid inputs', () => {
      for (let d = 0; d <= 100; d++) {
        const h = harmonicScale(d);
        expect(h).toBeGreaterThan(0);
        expect(h).toBeLessThanOrEqual(1);
      }
    });

    it('Phase deviation increases risk: H(d, pd1) > H(d, pd2) when pd1 < pd2', () => {
      const d = 2;
      expect(harmonicScale(d, 0)).toBeGreaterThan(harmonicScale(d, 0.5));
      expect(harmonicScale(d, 0.5)).toBeGreaterThan(harmonicScale(d, 1.0));
    });

    it('Reciprocal relationship: 1 / H(d) = 1 + d + 2*pd', () => {
      for (let d = 0; d <= 5; d++) {
        for (const pd of [0, 0.5, 1.0]) {
          const h = harmonicScale(d, pd);
          expect(1 / h).toBeCloseTo(1 + d + 2 * pd, 10);
        }
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Boundary Conditions
  // ═══════════════════════════════════════════════════════════════
  describe('Boundary conditions', () => {
    it('throws for d < 0', () => {
      expect(() => harmonicScale(-1)).toThrow(RangeError);
      expect(() => harmonicScale(-0.001)).toThrow(RangeError);
    });

    it('throws for phaseDeviation < 0', () => {
      expect(() => harmonicScale(1, -1)).toThrow(RangeError);
    });

    it('d=0 returns 1', () => {
      expect(harmonicScale(0)).toBe(1);
    });

    it('very large d returns near-zero', () => {
      const result = harmonicScale(1e6);
      expect(result).toBeGreaterThan(0);
      expect(result).toBeLessThan(1e-5);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Numerical Stability
  // ═══════════════════════════════════════════════════════════════
  describe('Numerical stability', () => {
    it('returns finite values for all d in [0, 1000]', () => {
      for (let d = 0; d <= 1000; d += 50) {
        const result = harmonicScale(d);
        expect(Number.isFinite(result)).toBe(true);
      }
    });

    it('no overflow for any input (bounded formula)', () => {
      // Unlike R^(d²), this formula can never overflow
      expect(Number.isFinite(harmonicScale(1e10))).toBe(true);
      expect(Number.isFinite(harmonicScale(1e15))).toBe(true);
    });

    it('differentiates small distances (the key fix)', () => {
      // The old R^(d²) mapped d=0.01 and d=0.1 to ~1.0
      // The new formula preserves ranking:
      const h1 = harmonicScale(0.01);
      const h2 = harmonicScale(0.1);
      const h3 = harmonicScale(0.5);

      expect(h1).toBeGreaterThan(h2);
      expect(h2).toBeGreaterThan(h3);

      // And the differences are meaningful, not ~0
      expect(h1 - h2).toBeGreaterThan(0.05);
      expect(h2 - h3).toBeGreaterThan(0.1);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Property-Based Testing (Fuzzing)
  // ═══════════════════════════════════════════════════════════════
  describe('Property-based tests', () => {
    const randomFloat = (min: number, max: number) => Math.random() * (max - min) + min;

    it('0 < H(d, pd) <= 1 for all valid inputs (100 trials)', () => {
      for (let i = 0; i < 100; i++) {
        const d = randomFloat(0, 100);
        const pd = randomFloat(0, 10);
        const h = harmonicScale(d, pd);
        expect(h).toBeGreaterThan(0);
        expect(h).toBeLessThanOrEqual(1);
      }
    });

    it('H(d, pd) is deterministic (50 trials)', () => {
      for (let i = 0; i < 50; i++) {
        const d = randomFloat(0, 50);
        const pd = randomFloat(0, 5);
        expect(harmonicScale(d, pd)).toBe(harmonicScale(d, pd));
      }
    });

    it('1/H(d,pd) = 1 + d + 2*pd (50 trials)', () => {
      for (let i = 0; i < 50; i++) {
        const d = randomFloat(0, 50);
        const pd = randomFloat(0, 5);
        const invH = 1 / harmonicScale(d, pd);
        expect(invH).toBeCloseTo(1 + d + 2 * pd, 10);
      }
    });
  });
});

describe('securityBits', () => {
  it('computes effective bits correctly', () => {
    // S_bits(d, pd) = baseBits + log₂(1 + d + 2*pd)
    const baseBits = 128;
    const d = 6;
    const pd = 0;
    const expected = 128 + Math.log2(1 + 6); // ≈ 128 + 2.807
    expect(securityBits(baseBits, d, pd)).toBeCloseTo(expected, 6);
  });

  it('returns baseBits when d = 0 and pd = 0', () => {
    expect(securityBits(128, 0, 0)).toBe(128);
    expect(securityBits(256, 0, 0)).toBe(256);
  });

  it('grows with distance', () => {
    const base = 128;
    expect(securityBits(base, 1)).toBeGreaterThan(securityBits(base, 0));
    expect(securityBits(base, 10)).toBeGreaterThan(securityBits(base, 1));
  });
});

describe('securityLevel', () => {
  it('computes S = base * (1 + d + 2*pd) correctly', () => {
    const base = 1000;
    const d = 3;
    const pd = 0;
    const expected = base * (1 + 3);
    expect(securityLevel(base, d, pd)).toBeCloseTo(expected, 6);
  });

  it('returns base when d=0 and pd=0', () => {
    expect(securityLevel(1000, 0, 0)).toBe(1000);
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
    const u: Vector6D = [0, 0, 0, 0, 0, 0];
    const v1: Vector6D = [1, 0, 0, 0, 0, 0];
    const v6: Vector6D = [0, 0, 0, 0, 0, 1];
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
    expect(octaveTranspose(100, 0.5)).toBeCloseTo(100 * Math.SQRT2, 10);
  });
});
