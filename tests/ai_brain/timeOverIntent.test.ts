/**
 * @file timeOverIntent.test.ts
 * @module ai_brain/timeOverIntent.test
 * @layer Layer 11, Layer 12
 * Tests for the Time-over-Intent coupling module.
 */

import { describe, it, expect } from 'vitest';
import {
  computeTimeDilation,
  computeGamma,
  computeTriadicWeights,
  positiveKappa,
  computeEffectiveR,
  harmonicWallTOI,
  triadicDistance,
  evaluateTimeOverIntent,
  computeHatchWeight,
  meetsGenesisThreshold,
  DEFAULT_TOI_CONFIG,
  type TemporalObservation,
} from '../../src/ai_brain/timeOverIntent.js';

const PHI = (1 + Math.sqrt(5)) / 2;
const EPSILON = 1e-8;

// ═══════════════════════════════════════════════════════════════
// Time Dilation
// ═══════════════════════════════════════════════════════════════

describe('computeTimeDilation', () => {
  it('returns 1.0 when on-time (elapsed = expected)', () => {
    expect(computeTimeDilation(10, 10)).toBeCloseTo(1.0);
  });

  it('returns > 1 when late (elapsed > expected)', () => {
    expect(computeTimeDilation(20, 10)).toBeCloseTo(2.0);
  });

  it('returns < 1 when early (elapsed < expected)', () => {
    expect(computeTimeDilation(5, 10)).toBeCloseTo(0.5);
  });

  it('returns 1.0 when expected time is zero', () => {
    expect(computeTimeDilation(5, 0)).toBeCloseTo(1.0);
  });

  it('returns 0 when elapsed is 0', () => {
    expect(computeTimeDilation(0, 10)).toBeCloseTo(0.0);
  });

  it('handles negative elapsed gracefully (clamps to 0)', () => {
    expect(computeTimeDilation(-5, 10)).toBeCloseTo(0.0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Dynamic Boost γ(t)
// ═══════════════════════════════════════════════════════════════

describe('computeGamma', () => {
  it('returns 1.0 when δτ = 1 (on-time)', () => {
    expect(computeGamma(1.0)).toBeCloseTo(1.0);
  });

  it('returns > 1 when δτ > 1 (late)', () => {
    const g = computeGamma(2.0);
    expect(g).toBeGreaterThan(1.0);
  });

  it('returns < 1 when δτ < 1 (early)', () => {
    const g = computeGamma(0.5);
    expect(g).toBeLessThan(1.0);
  });

  it('clamps to γ_min when heavily early', () => {
    const g = computeGamma(0.0, 0.4, 0.5, 2.0);
    expect(g).toBeCloseTo(0.6); // 1 + 0.4*(0 - 1) = 0.6
  });

  it('clamps to γ_max when extremely late', () => {
    const g = computeGamma(100.0, 0.4, 0.5, 2.0);
    expect(g).toBeCloseTo(2.0);
  });

  it('respects custom β_τ', () => {
    // δτ = 3, β_τ = 1.0 → 1 + 1.0*(3-1) = 3.0, clamped to γ_max
    const g = computeGamma(3.0, 1.0, 0.5, 5.0);
    expect(g).toBeCloseTo(3.0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Triadic Weights
// ═══════════════════════════════════════════════════════════════

describe('computeTriadicWeights', () => {
  it('preserves weights when γ = 1.0 (no boost)', () => {
    const w = computeTriadicWeights(1.0, [0.4, 0.3, 0.3]);
    expect(w[0]).toBeCloseTo(0.4);
    expect(w[1]).toBeCloseTo(0.3);
    expect(w[2]).toBeCloseTo(0.3);
  });

  it('boosts λ₃ when γ > 1 (late)', () => {
    const w = computeTriadicWeights(2.0, [0.4, 0.3, 0.3]);
    expect(w[2]).toBeGreaterThan(0.3);
    // λ₃ = 0.3 * 2 = 0.6, total = 0.4 + 0.3 + 0.6 = 1.3
    expect(w[2]).toBeCloseTo(0.6 / 1.3);
  });

  it('reduces λ₃ when γ < 1 (early)', () => {
    const w = computeTriadicWeights(0.5, [0.4, 0.3, 0.3]);
    expect(w[2]).toBeLessThan(0.3);
  });

  it('always sums to 1.0 (simplex constraint)', () => {
    for (const g of [0.1, 0.5, 1.0, 1.5, 2.0, 5.0]) {
      const w = computeTriadicWeights(g);
      expect(w[0] + w[1] + w[2]).toBeCloseTo(1.0);
    }
  });

  it('returns uniform weights for degenerate case', () => {
    const w = computeTriadicWeights(0, [0, 0, 0]);
    expect(w[0]).toBeCloseTo(1 / 3);
    expect(w[1]).toBeCloseTo(1 / 3);
    expect(w[2]).toBeCloseTo(1 / 3);
  });
});

// ═══════════════════════════════════════════════════════════════
// Positive Kappa
// ═══════════════════════════════════════════════════════════════

describe('positiveKappa', () => {
  it('returns 0 for negative curvature', () => {
    expect(positiveKappa(-1.5)).toBe(0);
  });

  it('returns 0 for zero curvature', () => {
    expect(positiveKappa(0)).toBe(0);
  });

  it('returns curvature for positive curvature', () => {
    expect(positiveKappa(2.5)).toBe(2.5);
  });
});

// ═══════════════════════════════════════════════════════════════
// Effective R
// ═══════════════════════════════════════════════════════════════

describe('computeEffectiveR', () => {
  it('returns R₀ when κ = 0 and Coh = 1 (baseline)', () => {
    const r = computeEffectiveR(0, 1.0);
    expect(r).toBeCloseTo(1.5);
  });

  it('increases R_eff for positive curvature', () => {
    const r = computeEffectiveR(2.0, 1.0);
    expect(r).toBeGreaterThan(1.5);
  });

  it('increases R_eff for low coherence', () => {
    const r = computeEffectiveR(0, 0.3);
    expect(r).toBeGreaterThan(1.5);
  });

  it('does not penalize for negative curvature', () => {
    const r = computeEffectiveR(-5.0, 1.0);
    // κ⁺ = 0, cohDeficit = 0, so R_eff = R₀
    expect(r).toBeCloseTo(1.5);
  });

  it('caps exponent to prevent overflow', () => {
    // Extreme curvature: κ = 1000
    const r = computeEffectiveR(1000, 0.0);
    expect(Number.isFinite(r)).toBe(true);
    expect(r).toBeLessThanOrEqual(1.5 * Math.exp(10) + 1);
  });

  it('respects custom config', () => {
    const r = computeEffectiveR(1.0, 0.5, { baseR: 2.0, alphaKappa: 1.0, alphaCoherence: 1.0 });
    // R_eff = 2.0 * exp(1.0 * 1.0 + 1.0 * 0.5) = 2.0 * exp(1.5)
    expect(r).toBeCloseTo(2.0 * Math.exp(1.5));
  });
});

// ═══════════════════════════════════════════════════════════════
// Harmonic Wall H_toi
// ═══════════════════════════════════════════════════════════════

describe('harmonicWallTOI', () => {
  it('returns 1.0 at safe center (d* = 0)', () => {
    expect(harmonicWallTOI(0, 2.0)).toBeCloseTo(1.0);
  });

  it('grows with distance', () => {
    const wall1 = harmonicWallTOI(1.0, 2.0);
    const wall2 = harmonicWallTOI(2.0, 2.0);
    expect(wall2).toBeGreaterThan(wall1);
  });

  it('grows with R_eff', () => {
    const wall1 = harmonicWallTOI(1.0, 1.5);
    const wall2 = harmonicWallTOI(1.0, 3.0);
    expect(wall2).toBeGreaterThan(wall1);
  });

  it('returns 1.0 when R_eff ≤ 1', () => {
    expect(harmonicWallTOI(5.0, 0.5)).toBeCloseTo(1.0);
    expect(harmonicWallTOI(5.0, 1.0)).toBeCloseTo(1.0);
  });

  it('is finite for large distances', () => {
    const wall = harmonicWallTOI(100, 1.5);
    expect(Number.isFinite(wall)).toBe(true);
  });

  it('computes R^(d²) correctly', () => {
    // R=2, d=3 → 2^9 = 512
    expect(harmonicWallTOI(3.0, 2.0)).toBeCloseTo(512);
  });
});

// ═══════════════════════════════════════════════════════════════
// Triadic Distance
// ═══════════════════════════════════════════════════════════════

describe('triadicDistance', () => {
  it('computes weighted sum', () => {
    const d = triadicDistance([0.5, 0.3, 0.2], [10, 20, 30]);
    expect(d).toBeCloseTo(0.5 * 10 + 0.3 * 20 + 0.2 * 30);
  });

  it('returns 0 when all distances are 0', () => {
    expect(triadicDistance([0.4, 0.3, 0.3], [0, 0, 0])).toBeCloseTo(0);
  });

  it('returns single distance when weight is concentrated', () => {
    expect(triadicDistance([1.0, 0, 0], [5, 10, 15])).toBeCloseTo(5);
  });
});

// ═══════════════════════════════════════════════════════════════
// Full Evaluation
// ═══════════════════════════════════════════════════════════════

describe('evaluateTimeOverIntent', () => {
  function makeObs(overrides: Partial<TemporalObservation> = {}): TemporalObservation {
    return {
      elapsedTime: 10,
      expectedTime: 10,
      curvature: 0,
      coherence: 1.0,
      distance: 0,
      baseRisk: 0.1,
      ...overrides,
    };
  }

  it('returns baseline values for on-time, zero-curvature, full-coherence, zero-distance', () => {
    const result = evaluateTimeOverIntent(makeObs());
    expect(result.timeDilation).toBeCloseTo(1.0);
    expect(result.gamma).toBeCloseTo(1.0);
    expect(result.effectiveR).toBeCloseTo(1.5);
    expect(result.harmonicWall).toBeCloseTo(1.0);
    expect(result.modulatedRisk).toBeCloseTo(0.1);
  });

  it('increases modulated risk for late governance', () => {
    const baseline = evaluateTimeOverIntent(makeObs({ distance: 1.0 }));
    const late = evaluateTimeOverIntent(makeObs({ distance: 1.0, elapsedTime: 30 }));
    // Late doesn't directly change R_eff but changes triadic weights
    expect(late.gamma).toBeGreaterThan(baseline.gamma);
    expect(late.triadicWeights[2]).toBeGreaterThan(baseline.triadicWeights[2]);
  });

  it('increases R_eff for positive curvature', () => {
    const result = evaluateTimeOverIntent(makeObs({ curvature: 3.0 }));
    expect(result.effectiveR).toBeGreaterThan(1.5);
    expect(result.positiveKappa).toBe(3.0);
  });

  it('increases R_eff for low coherence', () => {
    const result = evaluateTimeOverIntent(makeObs({ coherence: 0.2 }));
    expect(result.effectiveR).toBeGreaterThan(1.5);
  });

  it('amplifies risk at large distances', () => {
    const close = evaluateTimeOverIntent(makeObs({ distance: 0.5, baseRisk: 0.1 }));
    const far = evaluateTimeOverIntent(makeObs({ distance: 3.0, baseRisk: 0.1 }));
    expect(far.modulatedRisk).toBeGreaterThan(close.modulatedRisk);
  });

  it('caps modulated risk at 1.0', () => {
    const result = evaluateTimeOverIntent(makeObs({
      distance: 10.0,
      baseRisk: 0.5,
      curvature: 5.0,
      coherence: 0.1,
    }));
    expect(result.modulatedRisk).toBeLessThanOrEqual(1.0);
  });

  it('preserves triadic weight simplex constraint', () => {
    const result = evaluateTimeOverIntent(makeObs({ elapsedTime: 50 }));
    const sum = result.triadicWeights[0] + result.triadicWeights[1] + result.triadicWeights[2];
    expect(sum).toBeCloseTo(1.0);
  });

  it('returns zero triadic distance at safe center', () => {
    const result = evaluateTimeOverIntent(makeObs({ distance: 0 }));
    expect(result.triadicDistance).toBeCloseTo(0);
  });

  it('accepts custom config', () => {
    const result = evaluateTimeOverIntent(makeObs({ curvature: 1.0, coherence: 0.5 }), {
      baseR: 3.0,
      alphaKappa: 1.0,
      alphaCoherence: 1.0,
    });
    expect(result.effectiveR).toBeCloseTo(3.0 * Math.exp(1.0 + 0.5));
  });
});

// ═══════════════════════════════════════════════════════════════
// Hatch Weight (Bridge to Sacred Eggs)
// ═══════════════════════════════════════════════════════════════

describe('computeHatchWeight', () => {
  it('returns 0 for empty input', () => {
    expect(computeHatchWeight([])).toBe(0);
  });

  it('computes φ^0 * 1 = 1 for single predicate at rank 0', () => {
    expect(computeHatchWeight([{ rank: 0, score: 1 }])).toBeCloseTo(1.0);
  });

  it('computes φ^1 for rank 1', () => {
    expect(computeHatchWeight([{ rank: 1, score: 1 }])).toBeCloseTo(PHI);
  });

  it('sums multiple predicates', () => {
    const W = computeHatchWeight([
      { rank: 0, score: 1 },
      { rank: 1, score: 1 },
      { rank: 2, score: 1 },
    ]);
    expect(W).toBeCloseTo(1 + PHI + PHI * PHI);
  });

  it('ignores predicates with score 0', () => {
    const W = computeHatchWeight([
      { rank: 0, score: 0 },
      { rank: 1, score: 1 },
    ]);
    expect(W).toBeCloseTo(PHI);
  });

  it('supports continuous scores', () => {
    const W = computeHatchWeight([{ rank: 0, score: 0.5 }]);
    expect(W).toBeCloseTo(0.5);
  });
});

describe('meetsGenesisThreshold', () => {
  it('returns true when W ≥ φ³', () => {
    expect(meetsGenesisThreshold(PHI * PHI * PHI)).toBe(true);
    expect(meetsGenesisThreshold(PHI * PHI * PHI + 1)).toBe(true);
  });

  it('returns false when W < φ³', () => {
    expect(meetsGenesisThreshold(PHI * PHI * PHI - 0.01)).toBe(false);
  });

  it('uses custom threshold', () => {
    expect(meetsGenesisThreshold(5.0, 5.0)).toBe(true);
    expect(meetsGenesisThreshold(4.9, 5.0)).toBe(false);
  });
});
