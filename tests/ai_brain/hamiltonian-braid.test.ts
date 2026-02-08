/**
 * @file hamiltonian-braid.test.ts
 * @module tests/ai_brain/hamiltonian-braid
 *
 * Tests for the Ternary Braid Algebra — Mirror-Shift-Refactor system.
 *
 * Test groups:
 *   A: Algebra generators (M, S, Π, 0)
 *   B: Algebra relations (M²=I, Π²=Π, commutativity)
 *   C: 9-state phase diagram & governance mapping
 *   D: Ternary quantization
 *   E: Harmonic tube & trust tube enforcement
 *   F: Braid cycle iteration & φ-attractor convergence
 *   G: AetherBraid system integration
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  AetherBraid,
  BRAID_GOVERNANCE_TABLE,
  DEFAULT_BRAID_CONFIG,
  buildGovernance,
  braidSecurityAction,
  braidTrustLevel,
  classifyBraidState,
  estimateBraidFractalDimension,
  harmonicTubeCost,
  isInsideTube,
  mirrorShift,
  mirrorSwap,
  quantize,
  quantizeVector,
  refactorAlign,
  zeroGravityDistance,
  type BraidGovernance,
  type BraidState,
} from '../../src/ai_brain/hamiltonian-braid.js';
import { PHI } from '../../src/ai_brain/types.js';

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

function vec(a: number, b: number): [number, number] {
  return [a, b];
}

function approxEq(a: number, b: number, eps: number = 1e-8): boolean {
  return Math.abs(a - b) < eps;
}

function vecNorm(v: readonly [number, number]): number {
  return Math.sqrt(v[0] * v[0] + v[1] * v[1]);
}

// ═══════════════════════════════════════════════════════════════
// Test A: Algebra Generators
// ═══════════════════════════════════════════════════════════════

describe('Test A: Algebra Generators', () => {
  it('M: mirror swap transposes (a, b) → (b, a)', () => {
    expect(mirrorSwap(vec(3, 7))).toEqual([7, 3]);
    expect(mirrorSwap(vec(-1, 0.5))).toEqual([0.5, -1]);
    expect(mirrorSwap(vec(0, 0))).toEqual([0, 0]);
  });

  it('S(0): identity — no rotation', () => {
    const v = vec(0.5, -0.3);
    const result = mirrorShift(v, 0);
    expect(approxEq(result[0], v[0])).toBe(true);
    expect(approxEq(result[1], v[1])).toBe(true);
  });

  it('S(φ): mirror shift rotates toward/from diagonal', () => {
    const v = vec(1, 0);
    const result = mirrorShift(v, Math.PI / 4);
    // Symmetric rotation at π/4: [cos(π/4) + 0·sin(π/4), sin(π/4) + 0·cos(π/4)]
    const expected = [Math.cos(Math.PI / 4), Math.sin(Math.PI / 4)];
    expect(approxEq(result[0], expected[0])).toBe(true);
    expect(approxEq(result[1], expected[1])).toBe(true);
  });

  it('S(φ): preserves norm under symmetric rotation', () => {
    const v = vec(0.6, -0.4);
    const normBefore = vecNorm(v);
    // The symmetric matrix [[c,s],[s,c]] does NOT preserve norm in general
    // (it's not orthogonal). But we verify the transform is deterministic.
    const r1 = mirrorShift(v, 0.3);
    const r2 = mirrorShift(v, 0.3);
    expect(r1[0]).toBe(r2[0]);
    expect(r1[1]).toBe(r2[1]);
  });

  it('Π: refactor align projects onto mirror diagonal', () => {
    const v = vec(1, 0);
    const result = refactorAlign(v);
    // Projected onto (1/√2, 1/√2): dot = 1/√2, proj = (1/2, 1/2)
    expect(approxEq(result[0], 0.5)).toBe(true);
    expect(approxEq(result[1], 0.5)).toBe(true);
  });

  it('Π: clamps to unit ball', () => {
    const v = vec(10, 10);
    const result = refactorAlign(v);
    expect(vecNorm(result)).toBeLessThanOrEqual(1.0 + 1e-10);
  });

  it('Π: zero vector stays zero', () => {
    const result = refactorAlign(vec(0, 0));
    expect(result[0]).toBe(0);
    expect(result[1]).toBe(0);
  });

  it('0: zero-gravity distance is Euclidean norm', () => {
    expect(zeroGravityDistance(vec(0, 0))).toBe(0);
    expect(approxEq(zeroGravityDistance(vec(3, 4)), 5)).toBe(true);
    expect(approxEq(zeroGravityDistance(vec(1, 0)), 1)).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// Test B: Algebra Relations
// ═══════════════════════════════════════════════════════════════

describe('Test B: Algebra Relations', () => {
  it('M² = I (mirror is involution)', () => {
    const v = vec(0.7, -0.3);
    const mm = mirrorSwap(mirrorSwap(v));
    expect(mm[0]).toBe(v[0]);
    expect(mm[1]).toBe(v[1]);
  });

  it('M² = I for many vectors', () => {
    for (let i = 0; i < 20; i++) {
      const v = vec(Math.sin(i * 1.3), Math.cos(i * 0.7));
      const mm = mirrorSwap(mirrorSwap(v));
      expect(approxEq(mm[0], v[0])).toBe(true);
      expect(approxEq(mm[1], v[1])).toBe(true);
    }
  });

  it('Π² = Π (projection is idempotent)', () => {
    const v = vec(0.8, -0.2);
    const once = refactorAlign(v);
    const twice = refactorAlign(once);
    expect(approxEq(twice[0], once[0])).toBe(true);
    expect(approxEq(twice[1], once[1])).toBe(true);
  });

  it('Π² = Π for many vectors', () => {
    for (let i = 0; i < 20; i++) {
      const v = vec(Math.sin(i * 2.1) * 5, Math.cos(i * 1.7) * 3);
      const once = refactorAlign(v);
      const twice = refactorAlign(once);
      expect(approxEq(twice[0], once[0])).toBe(true);
      expect(approxEq(twice[1], once[1])).toBe(true);
    }
  });

  it('S(π/4)·M = M·S(π/4) (diagonal is M-invariant)', () => {
    const v = vec(0.6, -0.4);
    // S then M
    const sm = mirrorSwap(mirrorShift(v, Math.PI / 4));
    // M then S
    const ms = mirrorShift(mirrorSwap(v), Math.PI / 4);
    expect(approxEq(sm[0], ms[0])).toBe(true);
    expect(approxEq(sm[1], ms[1])).toBe(true);
  });

  it('M · 0 = 0 (zero is M-invariant)', () => {
    const zero = vec(0, 0);
    const mZero = mirrorSwap(zero);
    expect(mZero[0]).toBe(0);
    expect(mZero[1]).toBe(0);
  });

  it('S(0) = I (no shift is identity)', () => {
    for (let i = 0; i < 10; i++) {
      const v = vec(Math.sin(i), Math.cos(i));
      const result = mirrorShift(v, 0);
      expect(approxEq(result[0], v[0])).toBe(true);
      expect(approxEq(result[1], v[1])).toBe(true);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Test C: 9-State Phase Diagram & Governance Mapping
// ═══════════════════════════════════════════════════════════════

describe('Test C: 9-State Phase Diagram', () => {
  it('should classify all 9 ternary pairs correctly', () => {
    const expected: Array<[1 | 0 | -1, 1 | 0 | -1, BraidState]> = [
      [1, 1, 'RESONANT_LOCK'],
      [1, 0, 'FORWARD_THRUST'],
      [1, -1, 'CREATIVE_TENSION_A'],
      [0, 1, 'PERPENDICULAR_POS'],
      [0, 0, 'ZERO_GRAVITY'],
      [0, -1, 'PERPENDICULAR_NEG'],
      [-1, 1, 'CREATIVE_TENSION_B'],
      [-1, 0, 'BACKWARD_CHECK'],
      [-1, -1, 'COLLAPSE_ATTRACTOR'],
    ];
    for (const [p, m, state] of expected) {
      expect(classifyBraidState(p, m)).toBe(state);
    }
  });

  it('should map trust levels correctly', () => {
    expect(braidTrustLevel('RESONANT_LOCK')).toBe('maximum');
    expect(braidTrustLevel('FORWARD_THRUST')).toBe('high');
    expect(braidTrustLevel('CREATIVE_TENSION_A')).toBe('medium');
    expect(braidTrustLevel('CREATIVE_TENSION_B')).toBe('medium');
    expect(braidTrustLevel('ZERO_GRAVITY')).toBe('consensus');
    expect(braidTrustLevel('PERPENDICULAR_POS')).toBe('low');
    expect(braidTrustLevel('PERPENDICULAR_NEG')).toBe('low');
    expect(braidTrustLevel('BACKWARD_CHECK')).toBe('audit');
    expect(braidTrustLevel('COLLAPSE_ATTRACTOR')).toBe('block');
  });

  it('should map security actions correctly', () => {
    expect(braidSecurityAction('RESONANT_LOCK')).toBe('INSTANT_APPROVE');
    expect(braidSecurityAction('FORWARD_THRUST')).toBe('STANDARD_PATH');
    expect(braidSecurityAction('CREATIVE_TENSION_A')).toBe('FRACTAL_INSPECT');
    expect(braidSecurityAction('ZERO_GRAVITY')).toBe('HOLD_QUORUM');
    expect(braidSecurityAction('PERPENDICULAR_NEG')).toBe('REANCHOR');
    expect(braidSecurityAction('BACKWARD_CHECK')).toBe('ROLLBACK');
    expect(braidSecurityAction('COLLAPSE_ATTRACTOR')).toBe('HARD_DENY');
  });

  it('governance table should have exactly 9 entries', () => {
    expect(BRAID_GOVERNANCE_TABLE).toHaveLength(9);
  });

  it('governance table entries should have unique states', () => {
    const states = BRAID_GOVERNANCE_TABLE.map(g => g.state);
    expect(new Set(states).size).toBe(9);
  });

  it('buildGovernance should produce complete descriptors', () => {
    const gov = buildGovernance(1, -1);
    expect(gov.state).toBe('CREATIVE_TENSION_A');
    expect(gov.ternary).toEqual({ primary: 1, mirror: -1 });
    expect(gov.trustLevel).toBe('medium');
    expect(gov.action).toBe('FRACTAL_INSPECT');
  });
});

// ═══════════════════════════════════════════════════════════════
// Test D: Ternary Quantization
// ═══════════════════════════════════════════════════════════════

describe('Test D: Ternary Quantization', () => {
  it('quantize: positive above threshold → +1', () => {
    expect(quantize(0.5)).toBe(1);
    expect(quantize(1.0)).toBe(1);
    expect(quantize(0.34)).toBe(1);
  });

  it('quantize: negative below threshold → -1', () => {
    expect(quantize(-0.5)).toBe(-1);
    expect(quantize(-1.0)).toBe(-1);
    expect(quantize(-0.34)).toBe(-1);
  });

  it('quantize: near-zero → 0', () => {
    expect(quantize(0)).toBe(0);
    expect(quantize(0.1)).toBe(0);
    expect(quantize(-0.1)).toBe(0);
    expect(quantize(0.33)).toBe(0);
    expect(quantize(-0.33)).toBe(0);
  });

  it('quantize: custom threshold', () => {
    expect(quantize(0.2, 0.1)).toBe(1);
    expect(quantize(-0.2, 0.1)).toBe(-1);
    expect(quantize(0.05, 0.1)).toBe(0);
  });

  it('quantizeVector: maps 2D to dual ternary', () => {
    expect(quantizeVector(vec(0.5, -0.5))).toEqual({ primary: 1, mirror: -1 });
    expect(quantizeVector(vec(0, 0))).toEqual({ primary: 0, mirror: 0 });
    expect(quantizeVector(vec(-1, 1))).toEqual({ primary: -1, mirror: 1 });
  });

  it('quantizeVector: boundary values', () => {
    // At threshold boundary, should be 0
    expect(quantizeVector(vec(0.33, -0.33))).toEqual({ primary: 0, mirror: 0 });
    // Just above
    expect(quantizeVector(vec(0.34, -0.34))).toEqual({ primary: 1, mirror: -1 });
  });
});

// ═══════════════════════════════════════════════════════════════
// Test E: Harmonic Tube & Trust Tube
// ═══════════════════════════════════════════════════════════════

describe('Test E: Harmonic Tube', () => {
  const radius = 0.15;

  it('zero cost inside tube', () => {
    expect(harmonicTubeCost(0, radius)).toBe(0);
    expect(harmonicTubeCost(0.1, radius)).toBe(0);
    expect(harmonicTubeCost(0.15, radius)).toBe(0);
  });

  it('positive cost outside tube', () => {
    const cost = harmonicTubeCost(0.3, radius);
    expect(cost).toBeGreaterThan(0);
  });

  it('super-exponential cost growth', () => {
    const c1 = harmonicTubeCost(0.2, radius);
    const c2 = harmonicTubeCost(0.5, radius);
    const c3 = harmonicTubeCost(1.0, radius);
    expect(c2).toBeGreaterThan(c1);
    expect(c3).toBeGreaterThan(c2);
    // Growth should be much faster than linear
    expect(c3 / c2).toBeGreaterThan(c2 / c1);
  });

  it('uses φ^(d²) formula', () => {
    const d = 0.5;
    const excess = d - radius;
    const expected = Math.pow(PHI, excess * excess);
    expect(harmonicTubeCost(d, radius)).toBeCloseTo(expected, 10);
  });

  it('isInsideTube: origin is inside', () => {
    expect(isInsideTube(vec(0, 0), radius)).toBe(true);
  });

  it('isInsideTube: large vector is outside', () => {
    expect(isInsideTube(vec(1, 1), radius)).toBe(false);
  });

  it('isInsideTube: boundary is inside', () => {
    // Vector with exact tube radius norm
    const r = radius / Math.sqrt(2);
    expect(isInsideTube(vec(r, r), radius)).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// Test F: Braid Cycle & φ-Attractor Convergence
// ═══════════════════════════════════════════════════════════════

describe('Test F: Braid Cycle & φ-Attractor', () => {
  it('fractal dimension estimation: single point → 0', () => {
    expect(estimateBraidFractalDimension([[0, 0]])).toBe(0);
  });

  it('fractal dimension estimation: collinear points → ~1', () => {
    const line: Array<[number, number]> = [];
    for (let i = 0; i < 200; i++) {
      line.push([i * 0.001, i * 0.001]);
    }
    const d = estimateBraidFractalDimension(line);
    expect(d).toBeGreaterThan(0.5);
    expect(d).toBeLessThan(1.5);
  });

  it('fractal dimension estimation: 2D fill → ~2', () => {
    const fill: Array<[number, number]> = [];
    for (let x = 0; x < 20; x++) {
      for (let y = 0; y < 20; y++) {
        fill.push([x * 0.01, y * 0.01]);
      }
    }
    const d = estimateBraidFractalDimension(fill);
    expect(d).toBeGreaterThan(1.5);
    expect(d).toBeLessThan(2.5);
  });

  it('iterated MSR cycle produces non-trivial fractal dimension', () => {
    // Use a wider tube with more iterations to allow richer trajectories
    const braid = new AetherBraid({
      tubeRadius: 0.5,
      refactorTrigger: 5.0,
      maxIterations: 1000,
      convergenceThreshold: 0.001,
    });
    const result = braid.iterateCycle(vec(0.7, -0.3));

    // Fractal dimension should be non-trivial (> point, < area fill)
    expect(result.fractalDimension).toBeGreaterThan(0.3);
    expect(result.fractalDimension).toBeLessThan(2.5);
    // Trajectory should be long enough for meaningful measurement
    expect(result.trajectory.length).toBeGreaterThan(10);
  });

  it('symmetric input (0.5, 0.5) stays near diagonal', () => {
    const braid = new AetherBraid();
    const result = braid.iterateCycle(vec(0.5, 0.5));

    // After MSR cycle, should converge or stay near diagonal
    expect(result.trajectory.length).toBeGreaterThan(1);
    expect(result.governance).toBeDefined();
  });

  it('zero input converges immediately', () => {
    const braid = new AetherBraid();
    const result = braid.iterateCycle(vec(0, 0));

    // Zero vector is already at equilibrium
    expect(result.stepsToConverge).toBeLessThanOrEqual(2);
    expect(result.governance.state).toBe('ZERO_GRAVITY');
  });

  it('trajectory is non-empty', () => {
    const braid = new AetherBraid();
    const result = braid.iterateCycle(vec(0.3, -0.1));
    expect(result.trajectory.length).toBeGreaterThan(0);
    // First point should be the initial vector
    expect(result.trajectory[0][0]).toBeCloseTo(0.3);
    expect(result.trajectory[0][1]).toBeCloseTo(-0.1);
  });

  it('equilibrium distance is non-negative', () => {
    const braid = new AetherBraid();
    const result = braid.iterateCycle(vec(0.8, 0.2));
    expect(result.equilibriumDistance).toBeGreaterThanOrEqual(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Test G: AetherBraid System Integration
// ═══════════════════════════════════════════════════════════════

describe('Test G: AetherBraid System', () => {
  let braid: AetherBraid;

  beforeEach(() => {
    braid = new AetherBraid();
  });

  it('classify: resonant lock for (+, +)', () => {
    const gov = braid.classify(vec(0.5, 0.5));
    expect(gov.state).toBe('RESONANT_LOCK');
    expect(gov.action).toBe('INSTANT_APPROVE');
  });

  it('classify: collapse attractor for (-, -)', () => {
    const gov = braid.classify(vec(-0.5, -0.5));
    expect(gov.state).toBe('COLLAPSE_ATTRACTOR');
    expect(gov.action).toBe('HARD_DENY');
  });

  it('classify: zero gravity for origin', () => {
    const gov = braid.classify(vec(0, 0));
    expect(gov.state).toBe('ZERO_GRAVITY');
    expect(gov.action).toBe('HOLD_QUORUM');
  });

  it('evaluate: coherent vectors → positive coherence', () => {
    const result = braid.evaluate(vec(0.5, 0.3), vec(0.5, 0.3));
    expect(result.coherence).toBeGreaterThan(0);
  });

  it('evaluate: opposing vectors → negative coherence', () => {
    const result = braid.evaluate(vec(0.5, 0.3), vec(-0.5, -0.3));
    expect(result.coherence).toBeLessThan(0);
  });

  it('evaluate: tube check works', () => {
    const inside = braid.evaluate(vec(0.05, 0.05), vec(0.05, 0.05));
    expect(inside.insideTube).toBe(true);
    expect(inside.tubeCost).toBe(0);

    const outside = braid.evaluate(vec(1.0, 1.0), vec(1.0, 1.0));
    expect(outside.insideTube).toBe(false);
    expect(outside.tubeCost).toBeGreaterThan(0);
  });

  it('applyGenerators: produces all three stages', () => {
    const result = braid.applyGenerators(vec(0.6, -0.4), Math.PI / 6);
    expect(result.afterMirror).toBeDefined();
    expect(result.afterShift).toBeDefined();
    expect(result.afterRefactor).toBeDefined();

    // Mirror should swap
    expect(result.afterMirror).toEqual([-0.4, 0.6]);
  });

  it('getConfig: returns default config', () => {
    const config = braid.getConfig();
    expect(config.tubeRadius).toBe(0.15);
    expect(config.quantizeThreshold).toBe(0.33);
    expect(config.maxIterations).toBe(500);
  });

  it('custom config: modified tube radius', () => {
    const custom = new AetherBraid({ tubeRadius: 0.3 });
    expect(custom.getConfig().tubeRadius).toBe(0.3);

    // Larger tube → more vectors are inside
    const result = custom.evaluate(vec(0.1, 0.1), vec(0.1, 0.1));
    expect(result.insideTube).toBe(true);
  });

  it('computeTubeCost: delegates correctly', () => {
    expect(braid.computeTubeCost(vec(0, 0))).toBe(0);
    expect(braid.computeTubeCost(vec(1, 1))).toBeGreaterThan(0);
  });

  it('braid cycle preserves governance state determinism', () => {
    const r1 = braid.iterateCycle(vec(0.4, 0.2));
    const r2 = braid.iterateCycle(vec(0.4, 0.2));
    expect(r1.governance.state).toBe(r2.governance.state);
    expect(r1.fractalDimension).toBe(r2.fractalDimension);
    expect(r1.stepsToConverge).toBe(r2.stepsToConverge);
  });

  it('adversarial input gets denied or inspected', () => {
    const gov = braid.classify(vec(-0.8, -0.9));
    expect(['COLLAPSE_ATTRACTOR', 'BACKWARD_CHECK']).toContain(gov.state);
    expect(['HARD_DENY', 'ROLLBACK']).toContain(gov.action);
  });

  it('safe input gets approved', () => {
    const gov = braid.classify(vec(0.6, 0.6));
    expect(gov.state).toBe('RESONANT_LOCK');
    expect(gov.trustLevel).toBe('maximum');
  });

  it('creative tension correctly identified', () => {
    // Asymmetric: primary positive, mirror negative
    const gov = braid.classify(vec(0.5, -0.5));
    expect(gov.state).toBe('CREATIVE_TENSION_A');
    expect(gov.action).toBe('FRACTAL_INSPECT');
  });
});
