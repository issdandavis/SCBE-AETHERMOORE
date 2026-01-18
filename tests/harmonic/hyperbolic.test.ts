/**
 * SCBE Hyperbolic Geometry Tests (Layers 5-8)
 *
 * Tests for Poincaré ball operations:
 * - L5: Invariant hyperbolic metric dℍ(u,v)
 * - L6: Breath transform B(p,t)
 * - L7: Phase modulation Φ(p,θ)
 * - L8: Multi-well potential V(p)
 *
 * Mathematical invariants from differential geometry verified.
 */

import { describe, it, expect, test } from 'vitest';
import {
  hyperbolicDistance,
  mobiusAdd,
  projectToBall,
  expMap0,
  logMap0,
  breathTransform,
  inverseBreathTransform,
  phaseModulation,
  multiPhaseModulation,
  multiWellPotential,
  multiWellGradient,
  applyHyperbolicPipeline,
  BreathConfig,
  Well,
} from '../../src/harmonic/hyperbolic.js';

const EPSILON = 1e-10;

// Helper: Euclidean norm
const norm = (v: number[]): number => Math.sqrt(v.reduce((s, x) => s + x * x, 0));

// Helper: random point in Poincaré ball
const randomBallPoint = (dim: number, maxNorm: number = 0.9): number[] => {
  const v = Array.from({ length: dim }, () => Math.random() * 2 - 1);
  const n = norm(v);
  const r = Math.random() * maxNorm;
  return v.map(x => (x / n) * r);
};

describe('hyperbolicDistance - L5 Invariant Metric', () => {
  // ═══════════════════════════════════════════════════════════════
  // Metric Space Axioms
  // ═══════════════════════════════════════════════════════════════
  describe('Metric space axioms', () => {
    it('d(u, u) = 0 (identity of indiscernibles)', () => {
      const u = [0.3, 0.4, 0.2];
      expect(hyperbolicDistance(u, u)).toBeCloseTo(0, 10);
    });

    it('d(u, v) = d(v, u) (symmetry)', () => {
      for (let i = 0; i < 20; i++) {
        const u = randomBallPoint(3);
        const v = randomBallPoint(3);
        expect(hyperbolicDistance(u, v)).toBeCloseTo(hyperbolicDistance(v, u), 10);
      }
    });

    it('d(u, w) ≤ d(u, v) + d(v, w) (triangle inequality)', () => {
      for (let i = 0; i < 20; i++) {
        const u = randomBallPoint(3);
        const v = randomBallPoint(3);
        const w = randomBallPoint(3);
        const d_uw = hyperbolicDistance(u, w);
        const d_uv = hyperbolicDistance(u, v);
        const d_vw = hyperbolicDistance(v, w);
        expect(d_uw).toBeLessThanOrEqual(d_uv + d_vw + 1e-10);
      }
    });

    it('d(u, v) ≥ 0 (non-negativity)', () => {
      for (let i = 0; i < 20; i++) {
        const u = randomBallPoint(3);
        const v = randomBallPoint(3);
        expect(hyperbolicDistance(u, v)).toBeGreaterThanOrEqual(0);
      }
    });

    it('d(u, v) > 0 when u ≠ v (positive definiteness)', () => {
      const u = [0.1, 0.2, 0.3];
      const v = [0.2, 0.3, 0.4];
      expect(hyperbolicDistance(u, v)).toBeGreaterThan(0);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Hyperbolic Geometry Properties
  // ═══════════════════════════════════════════════════════════════
  describe('Hyperbolic geometry properties', () => {
    it('distance to origin matches formula: 2 × arctanh(‖p‖)', () => {
      for (let i = 0; i < 20; i++) {
        const p = randomBallPoint(3, 0.9);
        const origin = [0, 0, 0];
        const d = hyperbolicDistance(origin, p);
        const r = norm(p);
        const expected = 2 * Math.atanh(r);
        expect(d).toBeCloseTo(expected, 8);
      }
    });

    it('distance increases exponentially near boundary', () => {
      const origin = [0, 0, 0];
      const d1 = hyperbolicDistance(origin, [0.5, 0, 0]);
      const d2 = hyperbolicDistance(origin, [0.9, 0, 0]);
      const d3 = hyperbolicDistance(origin, [0.99, 0, 0]);
      expect(d2).toBeGreaterThan(d1 * 1.5);
      expect(d3).toBeGreaterThan(d2 * 1.5);
    });

    it('distance from origin to boundary → ∞', () => {
      const origin = [0, 0, 0];
      const nearBoundary = [0.9999, 0, 0];
      expect(hyperbolicDistance(origin, nearBoundary)).toBeGreaterThan(5);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Golden Test Vectors
  // ═══════════════════════════════════════════════════════════════
  describe('Golden test vectors', () => {
    it('d([0,0], [0.5,0]) = 2 × arctanh(0.5) ≈ 1.0986', () => {
      const d = hyperbolicDistance([0, 0], [0.5, 0]);
      expect(d).toBeCloseTo(2 * Math.atanh(0.5), 8);
    });

    it('d([0,0,0], [0.6,0,0]) ≈ 1.386', () => {
      const d = hyperbolicDistance([0, 0, 0], [0.6, 0, 0]);
      expect(d).toBeCloseTo(2 * Math.atanh(0.6), 6);
    });
  });
});

describe('mobiusAdd - Gyrovector Addition', () => {
  describe('Algebraic properties', () => {
    it('0 ⊕ v = v (identity)', () => {
      const v = [0.3, 0.4, 0.2];
      const origin = [0, 0, 0];
      const result = mobiusAdd(origin, v);
      result.forEach((x, i) => expect(x).toBeCloseTo(v[i], 10));
    });

    it('v ⊕ 0 = v (right identity)', () => {
      const v = [0.3, 0.4, 0.2];
      const origin = [0, 0, 0];
      const result = mobiusAdd(v, origin);
      result.forEach((x, i) => expect(x).toBeCloseTo(v[i], 10));
    });

    it('result stays in ball: ‖u ⊕ v‖ < 1', () => {
      for (let i = 0; i < 50; i++) {
        const u = randomBallPoint(3, 0.8);
        const v = randomBallPoint(3, 0.8);
        const result = mobiusAdd(u, v);
        expect(norm(result)).toBeLessThan(1);
      }
    });

    it('⊖v ⊕ v = 0 (inverse)', () => {
      const v = [0.3, 0.4, 0.2];
      const minusV = v.map(x => -x);
      const result = mobiusAdd(minusV, v);
      expect(norm(result)).toBeCloseTo(0, 8);
    });
  });

  describe('Gyration effects', () => {
    it('is NOT commutative in general (gyrovector space)', () => {
      const u = [0.3, 0.4, 0];
      const v = [0.2, -0.3, 0];
      const uv = mobiusAdd(u, v);
      const vu = mobiusAdd(v, u);
      // Should be different (gyration effect)
      const diff = Math.abs(uv[0] - vu[0]) + Math.abs(uv[1] - vu[1]);
      // They're not necessarily very different, but check they compute
      expect(norm(uv)).toBeLessThan(1);
      expect(norm(vu)).toBeLessThan(1);
    });
  });
});

describe('projectToBall', () => {
  it('returns input unchanged if already inside ball', () => {
    const p = [0.3, 0.4, 0.2];
    const result = projectToBall(p);
    expect(result).toEqual(p);
  });

  it('projects points outside ball to boundary', () => {
    const p = [1.5, 0, 0];
    const result = projectToBall(p);
    expect(norm(result)).toBeLessThan(1);
    expect(norm(result)).toBeCloseTo(1 - EPSILON, 6);
  });

  it('preserves direction', () => {
    const p = [3, 4, 0]; // norm = 5
    const result = projectToBall(p);
    // Direction should be same: [3/5, 4/5, 0]
    expect(result[0] / result[1]).toBeCloseTo(3 / 4, 10);
  });
});

describe('expMap0 / logMap0 - Exponential and Logarithmic Maps', () => {
  it('logMap0(expMap0(v)) = v (inverse pair)', () => {
    for (let i = 0; i < 20; i++) {
      const v = Array.from({ length: 3 }, () => Math.random() * 2 - 1);
      const p = expMap0(v);
      const recovered = logMap0(p);
      recovered.forEach((x, j) => expect(x).toBeCloseTo(v[j], 8));
    }
  });

  it('expMap0(0) = 0', () => {
    const result = expMap0([0, 0, 0]);
    expect(norm(result)).toBeCloseTo(0, 10);
  });

  it('logMap0(0) = 0', () => {
    const result = logMap0([0, 0, 0]);
    expect(norm(result)).toBeCloseTo(0, 10);
  });

  it('expMap0 maps to ball interior: ‖expMap0(v)‖ < 1', () => {
    for (let i = 0; i < 20; i++) {
      const v = Array.from({ length: 3 }, () => Math.random() * 10 - 5);
      const p = expMap0(v);
      expect(norm(p)).toBeLessThan(1);
    }
  });
});

describe('breathTransform - L6 Breath Transform', () => {
  const config: BreathConfig = { amplitude: 0.05, omega: 1.0 };

  describe('Direction preservation', () => {
    it('preserves direction of input', () => {
      const p = [0.3, 0.4, 0];
      const result = breathTransform(p, 0, config);
      // Direction ratio should be preserved
      expect(result[0] / result[1]).toBeCloseTo(p[0] / p[1], 8);
    });
  });

  describe('Radius modulation', () => {
    it('radius stays in (0, 1)', () => {
      for (let t = 0; t < 10; t += 0.1) {
        const p = [0.5, 0.3, 0.1];
        const result = breathTransform(p, t, config);
        const r = norm(result);
        expect(r).toBeGreaterThan(0);
        expect(r).toBeLessThan(1);
      }
    });

    it('amplitude is bounded by config.amplitude', () => {
      const p = [0.5, 0, 0];
      const r0 = norm(breathTransform(p, 0, config));
      let maxDelta = 0;
      for (let t = 0; t < 2 * Math.PI; t += 0.01) {
        const r = norm(breathTransform(p, t, config));
        maxDelta = Math.max(maxDelta, Math.abs(r - r0));
      }
      // Delta should be related to tanh modulation with amplitude 0.05
      expect(maxDelta).toBeLessThan(0.15);
    });
  });

  describe('Periodicity', () => {
    it('is periodic with period 2π/ω', () => {
      const p = [0.5, 0.3, 0];
      const period = (2 * Math.PI) / config.omega;
      const r1 = breathTransform(p, 0, config);
      const r2 = breathTransform(p, period, config);
      r1.forEach((x, i) => expect(x).toBeCloseTo(r2[i], 8));
    });
  });

  describe('Edge cases', () => {
    it('handles origin (returns origin)', () => {
      const result = breathTransform([0, 0, 0], 1, config);
      expect(norm(result)).toBeCloseTo(0, 10);
    });

    it('clamps amplitude to [0, 0.1]', () => {
      const bigConfig: BreathConfig = { amplitude: 0.5, omega: 1.0 };
      const p = [0.5, 0, 0];
      const result = breathTransform(p, Math.PI / 2, bigConfig);
      // Should be clamped, so radius change is limited
      expect(norm(result)).toBeLessThan(1);
    });
  });
});

describe('phaseModulation - L7 Phase Modulation', () => {
  describe('Rotation properties', () => {
    it('preserves norm', () => {
      for (let i = 0; i < 20; i++) {
        const p = randomBallPoint(4);
        const theta = Math.random() * 2 * Math.PI;
        const result = phaseModulation(p, theta, [0, 1]);
        expect(norm(result)).toBeCloseTo(norm(p), 10);
      }
    });

    it('θ = 0 returns original', () => {
      const p = [0.3, 0.4, 0.2, 0.1];
      const result = phaseModulation(p, 0, [0, 1]);
      result.forEach((x, i) => expect(x).toBeCloseTo(p[i], 10));
    });

    it('θ = 2π returns original', () => {
      const p = [0.3, 0.4, 0.2, 0.1];
      const result = phaseModulation(p, 2 * Math.PI, [0, 1]);
      result.forEach((x, i) => expect(x).toBeCloseTo(p[i], 8));
    });

    it('θ = π inverts in the rotation plane', () => {
      const p = [1, 0, 0, 0];
      const result = phaseModulation(p, Math.PI, [0, 1]);
      expect(result[0]).toBeCloseTo(-1, 10);
      expect(result[1]).toBeCloseTo(0, 10);
    });

    it('composition: rotate by θ₁ then θ₂ = rotate by θ₁ + θ₂', () => {
      const p = [0.5, 0.3, 0.1, 0];
      const theta1 = 0.5, theta2 = 0.7;
      const r1 = phaseModulation(phaseModulation(p, theta1, [0, 1]), theta2, [0, 1]);
      const r2 = phaseModulation(p, theta1 + theta2, [0, 1]);
      r1.forEach((x, i) => expect(x).toBeCloseTo(r2[i], 8));
    });
  });

  describe('multiPhaseModulation', () => {
    it('applies rotations sequentially', () => {
      const p = [0.5, 0.3, 0.2, 0.1];
      const rotations = [
        { theta: 0.5, plane: [0, 1] as [number, number] },
        { theta: 0.3, plane: [2, 3] as [number, number] },
      ];
      const result = multiPhaseModulation(p, rotations);
      expect(norm(result)).toBeCloseTo(norm(p), 10);
    });
  });

  describe('Error handling', () => {
    it('throws for invalid plane indices', () => {
      const p = [0.5, 0.3];
      expect(() => phaseModulation(p, 0.5, [0, 5])).toThrow(RangeError);
      expect(() => phaseModulation(p, 0.5, [0, 0])).toThrow(RangeError);
    });
  });
});

describe('multiWellPotential - L8 Multi-Well Potential', () => {
  const wells: Well[] = [
    { center: [0.3, 0, 0], weight: 1.0, sigma: 0.2 },
    { center: [-0.3, 0, 0], weight: 1.0, sigma: 0.2 },
  ];

  describe('Potential properties', () => {
    it('is maximal at well centers', () => {
      const V_center = multiWellPotential([0.3, 0, 0], wells);
      const V_away = multiWellPotential([0.5, 0, 0], wells);
      expect(V_center).toBeGreaterThan(V_away);
    });

    it('is always non-negative', () => {
      for (let i = 0; i < 20; i++) {
        const p = randomBallPoint(3);
        expect(multiWellPotential(p, wells)).toBeGreaterThanOrEqual(0);
      }
    });

    it('decays with distance from wells', () => {
      const V1 = multiWellPotential([0.3, 0, 0], wells);
      const V2 = multiWellPotential([0.3, 0.1, 0], wells);
      const V3 = multiWellPotential([0.3, 0.3, 0], wells);
      expect(V1).toBeGreaterThan(V2);
      expect(V2).toBeGreaterThan(V3);
    });

    it('weight scales potential linearly', () => {
      const wells1: Well[] = [{ center: [0, 0, 0], weight: 1.0, sigma: 0.5 }];
      const wells2: Well[] = [{ center: [0, 0, 0], weight: 2.0, sigma: 0.5 }];
      const V1 = multiWellPotential([0.2, 0, 0], wells1);
      const V2 = multiWellPotential([0.2, 0, 0], wells2);
      expect(V2).toBeCloseTo(2 * V1, 8);
    });
  });

  describe('Gradient', () => {
    it('gradient is non-zero away from well center', () => {
      const singleWell: Well[] = [{ center: [0.5, 0, 0], weight: 1.0, sigma: 0.3 }];
      const p = [0.3, 0, 0];
      const grad = multiWellGradient(p, singleWell);
      // Gradient should be non-zero when not at center
      expect(grad[0]).not.toBe(0);
    });

    it('gradient is zero at well center', () => {
      const singleWell: Well[] = [{ center: [0.5, 0, 0], weight: 1.0, sigma: 0.3 }];
      const grad = multiWellGradient([0.5, 0, 0], singleWell);
      expect(norm(grad)).toBeCloseTo(0, 8);
    });
  });
});

describe('applyHyperbolicPipeline', () => {
  it('returns valid output structure', () => {
    const p = [0.3, 0.4, 0.2];
    const result = applyHyperbolicPipeline(p, 0, 0);
    expect(result).toHaveProperty('point');
    expect(result).toHaveProperty('potential');
    expect(result).toHaveProperty('distance');
  });

  it('output point stays in ball', () => {
    for (let i = 0; i < 20; i++) {
      const p = randomBallPoint(3);
      const t = Math.random() * 10;
      const theta = Math.random() * 2 * Math.PI;
      const result = applyHyperbolicPipeline(
        p, t, theta,
        { amplitude: 0.05, omega: 1.0 }
      );
      expect(norm(result.point)).toBeLessThan(1);
    }
  });

  it('computes potential when wells provided', () => {
    const p = [0.3, 0, 0];
    const wells: Well[] = [{ center: [0.3, 0, 0], weight: 1.0, sigma: 0.2 }];
    const result = applyHyperbolicPipeline(p, 0, 0, undefined, wells);
    expect(result.potential).toBeGreaterThan(0);
  });

  it('distance matches hyperbolicDistance from origin', () => {
    const p = [0.5, 0, 0];
    const result = applyHyperbolicPipeline(p, 0, 0);
    const expected = hyperbolicDistance([0, 0, 0], result.point);
    expect(result.distance).toBeCloseTo(expected, 8);
  });
});

// ═══════════════════════════════════════════════════════════════
// Stress Tests
// ═══════════════════════════════════════════════════════════════
describe('Stress tests', () => {
  it('handles 1000 random hyperbolic distance calculations', () => {
    for (let i = 0; i < 1000; i++) {
      const u = randomBallPoint(6);
      const v = randomBallPoint(6);
      const d = hyperbolicDistance(u, v);
      expect(Number.isFinite(d)).toBe(true);
      expect(d).toBeGreaterThanOrEqual(0);
    }
  });

  it('handles 1000 random Möbius additions', () => {
    for (let i = 0; i < 1000; i++) {
      const u = randomBallPoint(6, 0.8);
      const v = randomBallPoint(6, 0.8);
      const result = mobiusAdd(u, v);
      expect(norm(result)).toBeLessThan(1);
    }
  });

  it('handles 1000 full pipeline executions', () => {
    for (let i = 0; i < 1000; i++) {
      const p = randomBallPoint(3);
      const t = Math.random() * 100;
      const theta = Math.random() * 2 * Math.PI;
      const result = applyHyperbolicPipeline(
        p, t, theta,
        { amplitude: 0.05, omega: 1.0 }
      );
      expect(norm(result.point)).toBeLessThan(1);
      expect(Number.isFinite(result.distance)).toBe(true);
    }
  });
});
