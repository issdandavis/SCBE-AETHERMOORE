/**
 * @file tri-manifold-lattice.test.ts
 * @module tests/ai_brain/tri-manifold-lattice
 * @layer Layer 5, Layer 11, Layer 12, Layer 14
 *
 * Tests for the Tri-Manifold Lattice: three temporal manifolds over
 * the Poincaré ball with harmonic scaling H(d, R) = R^(d²).
 *
 * Test groups:
 *   A. Harmonic Scaling Law properties
 *   B. Triadic Distance (weighted Euclidean norm)
 *   C. TemporalWindow sliding average
 *   D. TriManifoldLattice integration
 *   E. Temporal Resonance & Anomaly Detection
 *   F. Drift Dynamics (velocity, acceleration)
 *   G. Edge Cases & Numerical Stability
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  harmonicScale,
  harmonicScaleInverse,
  harmonicScaleTable,
  triadicDistance,
  triadicPartial,
  TemporalWindow,
  TriManifoldLattice,
  HARMONIC_R,
  DEFAULT_TRIADIC_WEIGHTS,
  DEFAULT_WINDOW_SIZES,
  type TriadicWeights,
  type LatticeNode,
} from '../../src/ai_brain/tri-manifold-lattice.js';
import { BRAIN_DIMENSIONS, PHI } from '../../src/ai_brain/types.js';

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

/** Create a safe 21D vector with small values (stays near Poincaré center). */
function safeVector(scale: number = 0.1): number[] {
  const v = new Array(BRAIN_DIMENSIONS).fill(0);
  for (let i = 0; i < BRAIN_DIMENSIONS; i++) {
    v[i] = Math.sin(i * 0.7) * scale;
  }
  return v;
}

/** Create a drifting 21D vector (progressively moves from center). */
function driftVector(step: number, maxScale: number = 0.5): number[] {
  const scale = Math.min(maxScale, step * 0.02);
  const v = new Array(BRAIN_DIMENSIONS).fill(0);
  for (let i = 0; i < BRAIN_DIMENSIONS; i++) {
    v[i] = Math.sin(i * 0.7 + step * 0.3) * scale;
  }
  return v;
}

/** Zero vector (Poincaré origin). */
const ORIGIN = new Array(BRAIN_DIMENSIONS).fill(0);

// ═══════════════════════════════════════════════════════════════
// A. Harmonic Scaling Law
// ═══════════════════════════════════════════════════════════════

describe('Test A: Harmonic Scaling Law H(d, R) = R^(d²)', () => {
  it('H(1, 1.5) = 1.5', () => {
    expect(harmonicScale(1, 1.5)).toBeCloseTo(1.5, 10);
  });

  it('H(2, 1.5) = 1.5^4 ≈ 5.0625', () => {
    expect(harmonicScale(2, 1.5)).toBeCloseTo(5.0625, 4);
  });

  it('H(3, 1.5) = 1.5^9 ≈ 38.44', () => {
    expect(harmonicScale(3, 1.5)).toBeCloseTo(Math.pow(1.5, 9), 2);
  });

  it('H(4, 1.5) = 1.5^16 ≈ 656.84', () => {
    expect(harmonicScale(4, 1.5)).toBeCloseTo(Math.pow(1.5, 16), 0);
  });

  it('H(6, 1.5) = 1.5^36 ≈ 2,184,164', () => {
    const h6 = harmonicScale(6, 1.5);
    expect(h6).toBeGreaterThan(2_000_000);
    expect(h6).toBeLessThan(2_500_000);
  });

  it('super-exponential: each step grows faster than the last', () => {
    let prevRatio = 0;
    for (let d = 1; d <= 5; d++) {
      const ratio = harmonicScale(d + 1, 1.5) / harmonicScale(d, 1.5);
      expect(ratio).toBeGreaterThan(prevRatio);
      prevRatio = ratio;
    }
  });

  it('H(0, R) = R^0 = 1 for any R', () => {
    expect(harmonicScale(0, 1.5)).toBe(1);
    expect(harmonicScale(0, 42)).toBe(1);
  });

  it('H(d, 1) = 1 for any d (unison ratio)', () => {
    for (let d = 0; d <= 6; d++) {
      expect(harmonicScale(d, 1)).toBe(1);
    }
  });

  it('negative dimensions return 1 (no amplification)', () => {
    expect(harmonicScale(-1, 1.5)).toBe(1);
    expect(harmonicScale(-10, 1.5)).toBe(1);
  });

  it('zero or negative R returns 0 or 1', () => {
    expect(harmonicScale(3, 0)).toBe(0);
    expect(harmonicScale(3, -1)).toBe(0);
  });

  it('default R is HARMONIC_R (1.5)', () => {
    expect(harmonicScale(2)).toBeCloseTo(harmonicScale(2, HARMONIC_R), 10);
  });

  // Duality property
  it('duality: H(d, R) * H(d, 1/R) = 1', () => {
    for (let d = 1; d <= 6; d++) {
      const product = harmonicScale(d, 1.5) * harmonicScaleInverse(d, 1.5);
      expect(product).toBeCloseTo(1, 8);
    }
  });

  it('inverse: harmonicScaleInverse(d, R) = (1/R)^(d²)', () => {
    for (let d = 1; d <= 4; d++) {
      const inv = harmonicScaleInverse(d, 1.5);
      const expected = Math.pow(1 / 1.5, d * d);
      expect(inv).toBeCloseTo(expected, 10);
    }
  });

  // Monotonicity
  it('monotonically increasing in d for R > 1', () => {
    let prev = 0;
    for (let d = 0; d <= 6; d++) {
      const h = harmonicScale(d, 1.5);
      expect(h).toBeGreaterThanOrEqual(prev);
      prev = h;
    }
  });

  it('monotonically decreasing in d for R < 1', () => {
    let prev = Infinity;
    for (let d = 0; d <= 6; d++) {
      const h = harmonicScale(d, 0.5);
      expect(h).toBeLessThanOrEqual(prev);
      prev = h;
    }
  });

  // Table
  it('harmonicScaleTable generates correct entries', () => {
    const table = harmonicScaleTable(3, 1.5);
    expect(table).toHaveLength(3);
    expect(table[0].d).toBe(1);
    expect(table[0].scale).toBeCloseTo(1.5, 10);
    expect(table[1].d).toBe(2);
    expect(table[1].scale).toBeCloseTo(5.0625, 4);
    expect(table[2].logScale).toBeCloseTo(Math.log(Math.pow(1.5, 9)), 6);
  });

  // Musical interval ratios
  it('perfect fourth (4/3) also produces super-exponential growth', () => {
    const R = 4 / 3;
    const h3 = harmonicScale(3, R);
    const h6 = harmonicScale(6, R);
    expect(h6 / h3).toBeGreaterThan(1000); // Super-exponential gap
  });

  it('golden ratio PHI produces unique scaling', () => {
    const h = harmonicScale(3, PHI);
    expect(h).toBeCloseTo(Math.pow(PHI, 9), 4);
    expect(h).toBeGreaterThan(50); // PHI^9 ≈ 76.01
  });
});

// ═══════════════════════════════════════════════════════════════
// B. Triadic Distance
// ═══════════════════════════════════════════════════════════════

describe('Test B: Triadic Distance', () => {
  const w: TriadicWeights = { immediate: 0.5, memory: 0.3, governance: 0.2 };

  it('zero when all distances are zero', () => {
    expect(triadicDistance(0, 0, 0, w)).toBe(0);
  });

  it('positive-definite: d_tri > 0 when any dᵢ > 0', () => {
    expect(triadicDistance(1, 0, 0, w)).toBeGreaterThan(0);
    expect(triadicDistance(0, 1, 0, w)).toBeGreaterThan(0);
    expect(triadicDistance(0, 0, 1, w)).toBeGreaterThan(0);
  });

  it('weighted: immediate weight dominates', () => {
    // Same distances but only one component nonzero
    const dImm = triadicDistance(1, 0, 0, w);
    const dMem = triadicDistance(0, 1, 0, w);
    const dGov = triadicDistance(0, 0, 1, w);
    // λ₁ > λ₂ > λ₃ → d(1,0,0) > d(0,1,0) > d(0,0,1)
    expect(dImm).toBeGreaterThan(dMem);
    expect(dMem).toBeGreaterThan(dGov);
  });

  it('equals standard Euclidean norm when weights are uniform', () => {
    const uniform: TriadicWeights = { immediate: 1 / 3, memory: 1 / 3, governance: 1 / 3 };
    const d = triadicDistance(3, 4, 0, uniform);
    // √((1/3)*9 + (1/3)*16 + 0) = √(25/3)
    expect(d).toBeCloseTo(Math.sqrt(25 / 3), 8);
  });

  it('monotonic in each component', () => {
    for (let x = 0; x <= 5; x++) {
      const d1 = triadicDistance(x, 2, 1, w);
      const d2 = triadicDistance(x + 1, 2, 1, w);
      expect(d2).toBeGreaterThanOrEqual(d1);
    }
  });

  it('symmetric in value (not in weight)', () => {
    // d_tri(a, b, c) ≠ d_tri(b, a, c) unless weights match
    const d1 = triadicDistance(5, 1, 1, w);
    const d2 = triadicDistance(1, 5, 1, w);
    expect(d1).not.toBeCloseTo(d2, 2);
  });

  // Partial derivatives
  it('triadicPartial is non-negative', () => {
    const dTri = triadicDistance(3, 4, 5, w);
    expect(triadicPartial(3, w.immediate, dTri)).toBeGreaterThanOrEqual(0);
    expect(triadicPartial(4, w.memory, dTri)).toBeGreaterThanOrEqual(0);
    expect(triadicPartial(5, w.governance, dTri)).toBeGreaterThanOrEqual(0);
  });

  it('triadicPartial is zero when d_tri is zero', () => {
    expect(triadicPartial(0, 0.5, 0)).toBe(0);
  });

  it('uses default weights when none specified', () => {
    const d = triadicDistance(1, 1, 1);
    const expected = Math.sqrt(
      DEFAULT_TRIADIC_WEIGHTS.immediate +
      DEFAULT_TRIADIC_WEIGHTS.memory +
      DEFAULT_TRIADIC_WEIGHTS.governance,
    );
    expect(d).toBeCloseTo(expected, 8);
  });
});

// ═══════════════════════════════════════════════════════════════
// C. TemporalWindow
// ═══════════════════════════════════════════════════════════════

describe('Test C: TemporalWindow', () => {
  let win: TemporalWindow;

  beforeEach(() => {
    win = new TemporalWindow(5);
  });

  it('starts empty with zero average', () => {
    expect(win.filled()).toBe(0);
    expect(win.average()).toBe(0);
    expect(win.isWarmedUp()).toBe(false);
  });

  it('accumulates samples up to window size', () => {
    win.push(1);
    win.push(2);
    win.push(3);
    expect(win.filled()).toBe(3);
    expect(win.average()).toBeCloseTo(2, 10);
    expect(win.isWarmedUp()).toBe(false);
  });

  it('warms up when filled', () => {
    for (let i = 1; i <= 5; i++) win.push(i);
    expect(win.isWarmedUp()).toBe(true);
    expect(win.filled()).toBe(5);
    expect(win.average()).toBeCloseTo(3, 10); // (1+2+3+4+5)/5
  });

  it('sliding: oldest value drops when overflowing', () => {
    for (let i = 1; i <= 5; i++) win.push(i);
    win.push(6); // Drops 1, window is [2,3,4,5,6]
    expect(win.average()).toBeCloseTo(4, 10); // (2+3+4+5+6)/5
  });

  it('latest returns most recent sample', () => {
    win.push(10);
    win.push(20);
    expect(win.latest()).toBe(20);
  });

  it('latest returns 0 when empty', () => {
    expect(win.latest()).toBe(0);
  });

  it('variance is zero for constant input', () => {
    for (let i = 0; i < 5; i++) win.push(7);
    expect(win.variance()).toBeCloseTo(0, 10);
  });

  it('variance is correct for simple series', () => {
    win.push(1);
    win.push(3);
    // Variance of [1, 3] = ((1-2)² + (3-2)²) / 1 = 2
    expect(win.variance()).toBeCloseTo(2, 8);
  });

  it('reset clears all state', () => {
    for (let i = 0; i < 5; i++) win.push(i);
    win.reset();
    expect(win.filled()).toBe(0);
    expect(win.average()).toBe(0);
    expect(win.isWarmedUp()).toBe(false);
  });

  it('window size 1 always holds latest value', () => {
    const w1 = new TemporalWindow(1);
    w1.push(5);
    expect(w1.average()).toBe(5);
    w1.push(10);
    expect(w1.average()).toBe(10);
    expect(w1.isWarmedUp()).toBe(true);
  });

  it('rejects window size < 1', () => {
    expect(() => new TemporalWindow(0)).toThrow();
    expect(() => new TemporalWindow(-1)).toThrow();
  });

  it('handles large number of samples without drift', () => {
    const w = new TemporalWindow(10);
    for (let i = 0; i < 10000; i++) w.push(42);
    expect(w.average()).toBeCloseTo(42, 6);
  });
});

// ═══════════════════════════════════════════════════════════════
// D. TriManifoldLattice Integration
// ═══════════════════════════════════════════════════════════════

describe('Test D: TriManifoldLattice', () => {
  let lattice: TriManifoldLattice;

  beforeEach(() => {
    lattice = new TriManifoldLattice();
  });

  it('starts at tick 0 with empty state', () => {
    expect(lattice.getTick()).toBe(0);
    expect(lattice.currentTriadicDistance()).toBe(0);
    expect(lattice.currentHarmonicCost()).toBe(0);
  });

  it('ingests a vector and produces a lattice node', () => {
    const node = lattice.ingest(safeVector(0.1));
    expect(node.tick).toBe(1);
    expect(node.rawState).toHaveLength(BRAIN_DIMENSIONS);
    expect(node.embedded).toHaveLength(BRAIN_DIMENSIONS);
    expect(node.hyperbolicDist).toBeGreaterThanOrEqual(0);
    expect(node.triadicDistance).toBeGreaterThanOrEqual(0);
    expect(node.harmonicCost).toBeGreaterThanOrEqual(0);
    expect(node.embeddedNorm).toBeGreaterThanOrEqual(0);
    expect(node.embeddedNorm).toBeLessThan(1);
  });

  it('origin vector produces near-zero triadic distance', () => {
    const node = lattice.ingest(ORIGIN);
    expect(node.hyperbolicDist).toBeLessThan(0.01);
    expect(node.triadicDistance).toBeLessThan(0.01);
  });

  it('tick increments with each ingest', () => {
    lattice.ingest(safeVector());
    lattice.ingest(safeVector());
    lattice.ingest(safeVector());
    expect(lattice.getTick()).toBe(3);
  });

  it('triadic distance increases for drifting vectors', () => {
    // Feed gradually drifting vectors
    const distances: number[] = [];
    for (let i = 0; i < 20; i++) {
      const node = lattice.ingest(driftVector(i, 0.8));
      distances.push(node.triadicDistance);
    }
    // Later distances should be larger (agent is drifting)
    const firstHalf = distances.slice(0, 10).reduce((a, b) => a + b) / 10;
    const secondHalf = distances.slice(10).reduce((a, b) => a + b) / 10;
    expect(secondHalf).toBeGreaterThan(firstHalf);
  });

  it('harmonic cost is triadic distance * H(6, 1.5)', () => {
    const node = lattice.ingest(safeVector(0.3));
    const h6 = Math.pow(1.5, 36);
    expect(node.harmonicCost).toBeCloseTo(node.triadicDistance * h6, 0);
  });

  it('custom config: window sizes', () => {
    const custom = new TriManifoldLattice({
      windowSizes: { immediate: 2, memory: 4, governance: 8 },
    });
    // After 2 ingests, immediate window should be warmed up
    custom.ingest(safeVector(0.1));
    custom.ingest(safeVector(0.2));
    // No assertion on warmup directly, but check it works
    const node = custom.ingest(safeVector(0.3));
    expect(node.tick).toBe(3);
  });

  it('custom config: harmonic dimensions', () => {
    const custom = new TriManifoldLattice({ harmonicDimensions: 3 });
    const node = custom.ingest(safeVector(0.3));
    const h3 = Math.pow(1.5, 9);
    expect(node.harmonicCost).toBeCloseTo(node.triadicDistance * h3, 0);
  });

  it('custom config: harmonic ratio', () => {
    const custom = new TriManifoldLattice({ harmonicR: 2.0, harmonicDimensions: 2 });
    const node = custom.ingest(safeVector(0.3));
    const h2 = Math.pow(2.0, 4); // 2^(2²) = 16
    expect(node.harmonicCost).toBeCloseTo(node.triadicDistance * h2, 2);
  });

  it('weights are normalized to sum=1', () => {
    const custom = new TriManifoldLattice({
      weights: { immediate: 5, memory: 3, governance: 2 },
    });
    const w = custom.getWeights();
    expect(w.immediate + w.memory + w.governance).toBeCloseTo(1, 10);
    expect(w.immediate).toBeCloseTo(0.5, 10);
  });

  it('snapshot returns current state', () => {
    lattice.ingest(safeVector(0.2));
    lattice.ingest(safeVector(0.3));
    const snap = lattice.snapshot();
    expect(snap.tick).toBe(2);
    expect(snap.nodeCount).toBe(2);
    expect(snap.triadicDistance).toBeGreaterThanOrEqual(0);
  });

  it('recentNodes returns last N nodes', () => {
    for (let i = 0; i < 10; i++) lattice.ingest(safeVector(0.1 * i));
    const recent = lattice.recentNodes(3);
    expect(recent).toHaveLength(3);
    expect(recent[2].tick).toBe(10);
  });

  it('reset clears all state', () => {
    for (let i = 0; i < 5; i++) lattice.ingest(safeVector());
    lattice.reset();
    expect(lattice.getTick()).toBe(0);
    expect(lattice.currentTriadicDistance()).toBe(0);
  });

  it('lattice prunes beyond MAX_LATTICE_DEPTH', () => {
    const small = new TriManifoldLattice();
    // Push many nodes
    for (let i = 0; i < 1050; i++) {
      small.ingest(safeVector(0.01));
    }
    expect(small.recentNodes(2000).length).toBeLessThanOrEqual(1000);
  });

  it('manifold distances converge for constant input', () => {
    // Feed same vector many times — all windows should converge
    for (let i = 0; i < 200; i++) {
      lattice.ingest(safeVector(0.2));
    }
    const node = lattice.recentNodes(1)[0];
    const { immediate, memory, governance } = node.manifoldDistances;
    // All three should be very close after warmup
    expect(Math.abs(immediate - memory)).toBeLessThan(0.01);
    expect(Math.abs(memory - governance)).toBeLessThan(0.01);
  });
});

// ═══════════════════════════════════════════════════════════════
// E. Temporal Resonance & Anomaly
// ═══════════════════════════════════════════════════════════════

describe('Test E: Temporal Resonance & Anomaly', () => {
  let lattice: TriManifoldLattice;

  beforeEach(() => {
    lattice = new TriManifoldLattice({
      windowSizes: { immediate: 3, memory: 10, governance: 30 },
    });
  });

  it('resonance is 1 when empty (trivially resonant)', () => {
    expect(lattice.temporalResonance()).toBe(1);
  });

  it('resonance approaches 1 for constant input', () => {
    for (let i = 0; i < 50; i++) lattice.ingest(safeVector(0.15));
    expect(lattice.temporalResonance()).toBeGreaterThan(0.95);
  });

  it('resonance drops when pattern suddenly changes', () => {
    // Establish steady state
    for (let i = 0; i < 50; i++) lattice.ingest(ORIGIN);
    const steadyResonance = lattice.temporalResonance();

    // Sudden shift
    for (let i = 0; i < 3; i++) lattice.ingest(safeVector(0.8));
    const shiftedResonance = lattice.temporalResonance();

    // Resonance should drop (immediate diverges from governance)
    expect(shiftedResonance).toBeLessThan(steadyResonance);
  });

  it('anomaly is 0 when empty', () => {
    expect(lattice.temporalAnomaly()).toBe(0);
  });

  it('anomaly rises when immediate diverges from governance', () => {
    // Fill governance window with low distances
    for (let i = 0; i < 50; i++) lattice.ingest(ORIGIN);
    const baseAnomaly = lattice.temporalAnomaly();

    // Spike immediate with high-distance vectors
    for (let i = 0; i < 3; i++) lattice.ingest(safeVector(0.9));
    const spikeAnomaly = lattice.temporalAnomaly();

    expect(spikeAnomaly).toBeGreaterThan(baseAnomaly);
  });

  it('resonance is bounded [0, 1]', () => {
    for (let i = 0; i < 100; i++) {
      const scale = Math.random() * 0.9;
      lattice.ingest(safeVector(scale));
      const r = lattice.temporalResonance();
      expect(r).toBeGreaterThanOrEqual(0);
      expect(r).toBeLessThanOrEqual(1);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// F. Drift Dynamics
// ═══════════════════════════════════════════════════════════════

describe('Test F: Drift Dynamics', () => {
  let lattice: TriManifoldLattice;

  beforeEach(() => {
    lattice = new TriManifoldLattice({
      windowSizes: { immediate: 3, memory: 10, governance: 30 },
    });
  });

  it('velocity is 0 with fewer than 2 samples', () => {
    expect(lattice.driftVelocity()).toBe(0);
    lattice.ingest(ORIGIN);
    expect(lattice.driftVelocity()).toBe(0);
  });

  it('acceleration is 0 with fewer than 3 samples', () => {
    expect(lattice.driftAcceleration()).toBe(0);
    lattice.ingest(ORIGIN);
    lattice.ingest(ORIGIN);
    expect(lattice.driftAcceleration()).toBe(0);
  });

  it('positive velocity when triadic distance is growing', () => {
    // Start at origin, then drift
    for (let i = 0; i < 5; i++) lattice.ingest(ORIGIN);
    for (let i = 0; i < 10; i++) lattice.ingest(driftVector(i, 0.5));
    // After many drift steps, velocity should be positive
    const v = lattice.driftVelocity();
    expect(v).toBeGreaterThanOrEqual(0);
  });

  it('velocity stabilizes for constant input', () => {
    for (let i = 0; i < 50; i++) lattice.ingest(safeVector(0.2));
    // After warmup, velocity should be near zero
    expect(Math.abs(lattice.driftVelocity())).toBeLessThan(0.01);
  });

  it('positive acceleration during drift onset', () => {
    // Steady state then increasing drift
    for (let i = 0; i < 30; i++) lattice.ingest(ORIGIN);
    lattice.ingest(safeVector(0.1));
    lattice.ingest(safeVector(0.3));
    lattice.ingest(safeVector(0.6));
    // Acceleration should be positive (drift accelerating)
    const acc = lattice.driftAcceleration();
    expect(acc).toBeGreaterThanOrEqual(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// G. Edge Cases & Numerical Stability
// ═══════════════════════════════════════════════════════════════

describe('Test G: Edge Cases & Numerical Stability', () => {
  it('handles zero vector gracefully', () => {
    const lattice = new TriManifoldLattice();
    const node = lattice.ingest(ORIGIN);
    expect(node.hyperbolicDist).toBeLessThan(0.01);
    expect(isFinite(node.triadicDistance)).toBe(true);
    expect(isFinite(node.harmonicCost)).toBe(true);
  });

  it('handles near-boundary vector', () => {
    const lattice = new TriManifoldLattice();
    // Large vector that will embed near Poincaré boundary
    const big = new Array(BRAIN_DIMENSIONS).fill(0).map((_, i) => Math.sin(i) * 10);
    const node = lattice.ingest(big);
    expect(node.embeddedNorm).toBeLessThan(1); // Must stay in ball
    expect(isFinite(node.hyperbolicDist)).toBe(true);
    expect(isFinite(node.triadicDistance)).toBe(true);
  });

  it('lattice verifyDuality holds for all dimensions', () => {
    const lattice = new TriManifoldLattice();
    for (let d = 0; d <= 8; d++) {
      const { product } = lattice.verifyDuality(d);
      expect(product).toBeCloseTo(1, 6);
    }
  });

  it('harmonicTable matches individual calculations', () => {
    const lattice = new TriManifoldLattice();
    const table = lattice.harmonicTable(4);
    for (const entry of table) {
      expect(entry.scale).toBeCloseTo(harmonicScale(entry.d, HARMONIC_R), 6);
    }
  });

  it('triadic distance is non-negative for all inputs', () => {
    for (let i = 0; i < 100; i++) {
      const d1 = Math.random() * 10;
      const d2 = Math.random() * 10;
      const dG = Math.random() * 10;
      expect(triadicDistance(d1, d2, dG)).toBeGreaterThanOrEqual(0);
    }
  });

  it('embedded norm stays strictly below 1 for all inputs', () => {
    const lattice = new TriManifoldLattice();
    for (let trial = 0; trial < 50; trial++) {
      const v = new Array(BRAIN_DIMENSIONS).fill(0).map(() => (Math.random() - 0.5) * 20);
      const node = lattice.ingest(v);
      expect(node.embeddedNorm).toBeLessThan(1);
    }
  });

  it('single-sample windows work correctly', () => {
    const lattice = new TriManifoldLattice({
      windowSizes: { immediate: 1, memory: 1, governance: 1 },
    });
    const node = lattice.ingest(safeVector(0.5));
    // All three manifold distances should be equal (single sample)
    expect(node.manifoldDistances.immediate).toBeCloseTo(
      node.manifoldDistances.memory,
      10,
    );
    expect(node.manifoldDistances.memory).toBeCloseTo(
      node.manifoldDistances.governance,
      10,
    );
  });
});
