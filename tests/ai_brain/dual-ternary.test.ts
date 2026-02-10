/**
 * Tests for Dual Ternary Encoding with Full Negative State Flux
 *
 * Covers:
 * - Full 9-state space enumeration
 * - State energy computation and phase classification
 * - State transitions with full negative flux
 * - Encoding from continuous values
 * - Spectral analysis of dual ternary sequences
 * - Fractal dimension estimation
 * - Phase anomaly detection (security)
 * - DualTernarySystem end-to-end pipeline
 * - Tensor product representation
 * - Edge cases
 *
 * @module tests/ai_brain/dual-ternary
 */

import { describe, expect, it, beforeEach } from 'vitest';
import {
  DualTernarySystem,
  FULL_STATE_SPACE,
  DEFAULT_DUAL_TERNARY_CONFIG,
  computeStateEnergy,
  stateIndex,
  stateFromIndex,
  transition,
  encodeToDualTernary,
  encodeSequence,
  computeSpectrum,
  estimateFractalDimension,
  type DualTernaryState,
  type TernaryValue,
} from '../../src/ai_brain/dual-ternary';

// ═══════════════════════════════════════════════════════════════
// Test Helpers
// ═══════════════════════════════════════════════════════════════

function safeState21D(base: number = 0.5): number[] {
  return new Array(21).fill(base);
}

function uniformSequence(state: DualTernaryState, length: number): DualTernaryState[] {
  return new Array(length).fill(state);
}

function balancedSequence(length: number): DualTernaryState[] {
  const states: DualTernaryState[] = [];
  for (let i = 0; i < length; i++) {
    states.push(FULL_STATE_SPACE[i % 9]);
  }
  return states;
}

// ═══════════════════════════════════════════════════════════════
// Full 9-State Space
// ═══════════════════════════════════════════════════════════════

describe('Full 9-State Space', () => {
  it('should have exactly 9 states', () => {
    expect(FULL_STATE_SPACE).toHaveLength(9);
  });

  it('should contain all combinations of {-1, 0, 1} × {-1, 0, 1}', () => {
    const values: TernaryValue[] = [-1, 0, 1];
    for (const p of values) {
      for (const m of values) {
        const found = FULL_STATE_SPACE.some(
          (s) => s.primary === p && s.mirror === m
        );
        expect(found).toBe(true);
      }
    }
  });

  it('should have unique indices for all states', () => {
    const indices = FULL_STATE_SPACE.map((s) => stateIndex(s));
    const unique = new Set(indices);
    expect(unique.size).toBe(9);
  });

  it('should round-trip through index ↔ state', () => {
    for (const state of FULL_STATE_SPACE) {
      const idx = stateIndex(state);
      const recovered = stateFromIndex(idx);
      expect(recovered.primary).toBe(state.primary);
      expect(recovered.mirror).toBe(state.mirror);
    }
  });

  it('should allow BOTH positions to have negative state', () => {
    const negNeg = FULL_STATE_SPACE.find(
      (s) => s.primary === -1 && s.mirror === -1
    );
    expect(negNeg).toBeDefined();
  });
});

// ═══════════════════════════════════════════════════════════════
// State Energy & Phase Classification
// ═══════════════════════════════════════════════════════════════

describe('State Energy', () => {
  it('should compute ground state energy as 0', () => {
    const e = computeStateEnergy({ primary: 0, mirror: 0 });
    expect(e.energy).toBe(0);
    expect(e.phase).toBe('neutral');
  });

  it('should compute constructive interference energy', () => {
    const e = computeStateEnergy({ primary: 1, mirror: 1 });
    expect(e.energy).toBe(3); // 1 + 1 + 1
    expect(e.phase).toBe('constructive');
  });

  it('should compute negative resonance energy', () => {
    const e = computeStateEnergy({ primary: -1, mirror: -1 });
    expect(e.energy).toBe(3); // 1 + 1 + 1
    expect(e.phase).toBe('negative_resonance');
  });

  it('should compute destructive interference energy', () => {
    const e1 = computeStateEnergy({ primary: 1, mirror: -1 });
    expect(e1.energy).toBe(1); // 1 + 1 - 1
    expect(e1.phase).toBe('destructive');

    const e2 = computeStateEnergy({ primary: -1, mirror: 1 });
    expect(e2.energy).toBe(1);
    expect(e2.phase).toBe('destructive');
  });

  it('should have symmetric energy for sign-flipped pairs', () => {
    const ePlus = computeStateEnergy({ primary: 1, mirror: 1 });
    const eMinus = computeStateEnergy({ primary: -1, mirror: -1 });
    expect(ePlus.energy).toBe(eMinus.energy);
  });

  it('should compute interaction term correctly', () => {
    const e = computeStateEnergy({ primary: 1, mirror: -1 });
    expect(e.interaction).toBe(-1);
    expect(e.primaryEnergy).toBe(1);
    expect(e.mirrorEnergy).toBe(1);
  });

  it('should classify neutral states correctly', () => {
    expect(computeStateEnergy({ primary: 0, mirror: 1 }).phase).toBe('neutral');
    expect(computeStateEnergy({ primary: 1, mirror: 0 }).phase).toBe('neutral');
    expect(computeStateEnergy({ primary: -1, mirror: 0 }).phase).toBe('neutral');
  });
});

// ═══════════════════════════════════════════════════════════════
// State Transitions
// ═══════════════════════════════════════════════════════════════

describe('State Transitions', () => {
  it('should preserve state with zero delta', () => {
    const state: DualTernaryState = { primary: 1, mirror: -1 };
    const next = transition(state, 0, 0);
    expect(next.primary).toBe(1);
    expect(next.mirror).toBe(-1);
  });

  it('should transition both channels independently', () => {
    const state: DualTernaryState = { primary: 0, mirror: 0 };
    const next = transition(state, 1, -1);
    expect(next.primary).toBe(1);
    expect(next.mirror).toBe(-1);
  });

  it('should clip to ternary range', () => {
    const state: DualTernaryState = { primary: 1, mirror: -1 };
    const next = transition(state, 5, -5); // Way beyond range
    expect(next.primary).toBe(1); // Clipped to max
    expect(next.mirror).toBe(-1); // Clipped to min
  });

  it('should allow transitions from any state to any other', () => {
    // From (-1, -1) to (1, 1) via delta (2, 2)
    const next = transition({ primary: -1, mirror: -1 }, 2, 2);
    expect(next.primary).toBe(1);
    expect(next.mirror).toBe(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// Encoding
// ═══════════════════════════════════════════════════════════════

describe('Encoding', () => {
  it('should encode positive values to +1', () => {
    const state = encodeToDualTernary(0.5, 0.5);
    expect(state.primary).toBe(1);
    expect(state.mirror).toBe(1);
  });

  it('should encode negative values to -1', () => {
    const state = encodeToDualTernary(-0.5, -0.5);
    expect(state.primary).toBe(-1);
    expect(state.mirror).toBe(-1);
  });

  it('should encode small values to 0', () => {
    const state = encodeToDualTernary(0.1, -0.1);
    expect(state.primary).toBe(0);
    expect(state.mirror).toBe(0);
  });

  it('should handle mixed signs (full negative flux)', () => {
    const state = encodeToDualTernary(0.5, -0.5);
    expect(state.primary).toBe(1);
    expect(state.mirror).toBe(-1);
  });

  it('should encode sequence from 21D brain state', () => {
    const states = encodeSequence(safeState21D());
    expect(states.length).toBeGreaterThan(0);
    // 21 values → 11 pairs (10 full + 1 odd)
    expect(states).toHaveLength(11);
  });

  it('should respect custom threshold', () => {
    const strict = encodeToDualTernary(0.3, 0.3, 0.5);
    expect(strict.primary).toBe(0); // Below 0.5 threshold

    const relaxed = encodeToDualTernary(0.3, 0.3, 0.1);
    expect(relaxed.primary).toBe(1); // Above 0.1 threshold
  });

  it('should handle even-length sequences', () => {
    const states = encodeSequence([1, -1, 0, 1]);
    expect(states).toHaveLength(2);
  });
});

// ═══════════════════════════════════════════════════════════════
// Spectral Analysis
// ═══════════════════════════════════════════════════════════════

describe('Spectral Analysis', () => {
  it('should compute spectrum for balanced sequence', () => {
    const seq = balancedSequence(32);
    const spectrum = computeSpectrum(seq);
    expect(spectrum.primaryMagnitudes.length).toBeGreaterThan(0);
    expect(spectrum.mirrorMagnitudes.length).toBeGreaterThan(0);
  });

  it('should detect low phase anomaly for balanced traffic', () => {
    const seq = balancedSequence(64);
    const spectrum = computeSpectrum(seq);
    // Balanced sequence → low anomaly
    expect(spectrum.phaseAnomaly).toBeLessThan(0.5);
  });

  it('should detect high phase anomaly for uniform traffic', () => {
    const seq = uniformSequence({ primary: 1, mirror: 1 }, 32);
    const spectrum = computeSpectrum(seq);
    // All same state → high anomaly (zero entropy → anomaly = 1)
    expect(spectrum.phaseAnomaly).toBeGreaterThan(0.8);
  });

  it('should compute 9-fold symmetry energy', () => {
    const balanced = balancedSequence(36); // 36 = 4 * 9 perfect distribution
    const spectrum = computeSpectrum(balanced);
    // Perfect distribution → low ninefold energy
    expect(spectrum.ninefoldEnergy).toBeLessThan(0.2);
  });

  it('should compute coherence in [0, 1]', () => {
    const seq = balancedSequence(32);
    const spectrum = computeSpectrum(seq);
    expect(spectrum.coherence).toBeGreaterThanOrEqual(0);
    expect(spectrum.coherence).toBeLessThanOrEqual(1);
  });

  it('should return empty spectrum for too-short sequence', () => {
    const seq = [{ primary: 1 as const, mirror: 0 as const }];
    const spectrum = computeSpectrum(seq);
    expect(spectrum.primaryMagnitudes).toHaveLength(0);
  });

  it('should compute cross-correlation', () => {
    const seq = balancedSequence(16);
    const spectrum = computeSpectrum(seq);
    expect(spectrum.crossCorrelation.length).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Fractal Dimension
// ═══════════════════════════════════════════════════════════════

describe('Fractal Dimension', () => {
  it('should have base dimension of 2 (log9/log3)', () => {
    const seq = balancedSequence(32);
    const fractal = estimateFractalDimension(seq);
    expect(fractal.baseDimension).toBeCloseTo(2.0, 10);
  });

  it('should estimate Hausdorff dimension >= base', () => {
    const seq = balancedSequence(64);
    const fractal = estimateFractalDimension(seq);
    expect(fractal.hausdorffDimension).toBeGreaterThanOrEqual(
      fractal.baseDimension - 0.1 // Allow small numerical slack
    );
  });

  it('should compute sign entropy', () => {
    const balanced = balancedSequence(64);
    const fractal = estimateFractalDimension(balanced);
    // Balanced sequence should have moderate sign entropy
    expect(fractal.signEntropy).toBeGreaterThanOrEqual(0);
  });

  it('should detect symmetry breaking', () => {
    // Asymmetric: all primaries positive, all mirrors negative
    const asymmetric: DualTernaryState[] = [];
    for (let i = 0; i < 64; i++) {
      asymmetric.push({ primary: 1, mirror: -1 });
    }
    const fractal = estimateFractalDimension(asymmetric);
    expect(fractal.symmetryBreaking).toBeGreaterThan(0);
  });

  it('should have zero symmetry breaking for symmetric sequence', () => {
    // Perfectly symmetric: each (p,m) has matching (m,p)
    const symmetric: DualTernaryState[] = [];
    for (let i = 0; i < 32; i++) {
      symmetric.push({ primary: 1, mirror: 0 });
      symmetric.push({ primary: 0, mirror: 1 });
    }
    const fractal = estimateFractalDimension(symmetric);
    expect(fractal.symmetryBreaking).toBeLessThan(0.05);
  });

  it('should compute self-similarity', () => {
    const seq = balancedSequence(64);
    const fractal = estimateFractalDimension(seq);
    expect(fractal.selfSimilarity).toBeGreaterThanOrEqual(0);
    expect(fractal.selfSimilarity).toBeLessThanOrEqual(1);
  });

  it('should handle short sequences gracefully', () => {
    const fractal = estimateFractalDimension([{ primary: 1, mirror: 0 }]);
    expect(fractal.baseDimension).toBeCloseTo(2.0, 10);
    expect(fractal.hausdorffDimension).toBeCloseTo(2.0, 8);
  });
});

// ═══════════════════════════════════════════════════════════════
// DualTernarySystem (End-to-End)
// ═══════════════════════════════════════════════════════════════

describe('DualTernarySystem', () => {
  let system: DualTernarySystem;

  beforeEach(() => {
    system = new DualTernarySystem();
  });

  it('should encode 21D brain state', () => {
    const encoded = system.encode(safeState21D());
    expect(encoded.length).toBeGreaterThan(0);
    expect(system.getHistoryLength()).toBeGreaterThan(0);
  });

  it('should accumulate history over multiple encodings', () => {
    system.encode(safeState21D());
    system.encode(safeState21D());
    expect(system.getHistoryLength()).toBeGreaterThan(11); // > one encoding
  });

  it('should analyze spectrum from accumulated history', () => {
    for (let i = 0; i < 5; i++) {
      system.encode(safeState21D(i * 0.2));
    }
    const spectrum = system.analyzeSpectrum();
    expect(spectrum.primaryMagnitudes.length).toBeGreaterThan(0);
  });

  it('should analyze fractal dimension from history', () => {
    for (let i = 0; i < 10; i++) {
      system.encode(safeState21D(i * 0.1));
    }
    const fractal = system.analyzeFractalDimension();
    expect(fractal.baseDimension).toBeCloseTo(2.0, 10);
  });

  it('should perform full analysis with threat scoring', () => {
    for (let i = 0; i < 10; i++) {
      system.encode(safeState21D(Math.sin(i)));
    }
    const analysis = system.fullAnalysis();
    expect(analysis.spectrum).toBeDefined();
    expect(analysis.fractal).toBeDefined();
    expect(analysis.threatScore).toBeGreaterThanOrEqual(0);
    expect(analysis.threatScore).toBeLessThanOrEqual(1);
  });

  it('should detect phase anomaly for attack-like patterns', () => {
    // Encode the same state 50 times (monotonous = suspicious)
    for (let i = 0; i < 50; i++) {
      system.encode(new Array(21).fill(1));
    }
    const analysis = system.fullAnalysis();
    expect(analysis.phaseAnomalyDetected).toBe(true);
  });

  it('should NOT detect phase anomaly for diverse patterns', () => {
    // Encode varied states
    for (let i = 0; i < 50; i++) {
      const state = new Array(21).fill(0).map((_, j) =>
        Math.sin(i * 0.7 + j * 0.3) * 2
      );
      system.encode(state);
    }
    const analysis = system.fullAnalysis();
    expect(analysis.phaseAnomalyDetected).toBe(false);
  });

  it('should increment step counter', () => {
    expect(system.getStep()).toBe(0);
    system.encode(safeState21D());
    expect(system.getStep()).toBe(1);
  });

  it('should reset completely', () => {
    system.encode(safeState21D());
    system.encode(safeState21D());
    system.reset();
    expect(system.getHistoryLength()).toBe(0);
    expect(system.getStep()).toBe(0);
  });

  it('should trim history to 1024', () => {
    // Each encode adds ~11 states, so 100 encodes = ~1100 states
    for (let i = 0; i < 100; i++) {
      system.encode(safeState21D(i * 0.01));
    }
    expect(system.getHistoryLength()).toBeLessThanOrEqual(1024);
  });
});

// ═══════════════════════════════════════════════════════════════
// Tensor Product Representation
// ═══════════════════════════════════════════════════════════════

describe('Tensor Product', () => {
  it('should produce 3×3 matrix for single state', () => {
    const tensor = DualTernarySystem.toTensorProduct({ primary: 1, mirror: -1 });
    expect(tensor).toHaveLength(3);
    expect(tensor[0]).toHaveLength(3);
  });

  it('should have exactly one non-zero entry', () => {
    const tensor = DualTernarySystem.toTensorProduct({ primary: 0, mirror: 0 });
    let nonZero = 0;
    for (const row of tensor) {
      for (const val of row) {
        if (val !== 0) nonZero++;
      }
    }
    expect(nonZero).toBe(1);
    expect(tensor[1][1]).toBe(1); // (0+1, 0+1) = (1,1)
  });

  it('should place (+1,+1) at bottom-right', () => {
    const tensor = DualTernarySystem.toTensorProduct({ primary: 1, mirror: 1 });
    expect(tensor[2][2]).toBe(1);
  });

  it('should place (-1,-1) at top-left', () => {
    const tensor = DualTernarySystem.toTensorProduct({ primary: -1, mirror: -1 });
    expect(tensor[0][0]).toBe(1);
  });

  it('should compute histogram from sequence', () => {
    const seq = balancedSequence(9);
    const hist = DualTernarySystem.tensorHistogram(seq);
    // Each state appears exactly once
    for (const row of hist) {
      for (const val of row) {
        expect(val).toBe(1);
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Edge Cases
// ═══════════════════════════════════════════════════════════════

describe('Edge Cases', () => {
  it('should handle empty state encoding', () => {
    const system = new DualTernarySystem();
    const encoded = system.encode([]);
    expect(encoded).toHaveLength(0);
  });

  it('should handle single-value encoding', () => {
    const encoded = encodeSequence([0.5]);
    expect(encoded).toHaveLength(1);
    expect(encoded[0].mirror).toBe(0); // Padded with 0
  });

  it('should clamp stateFromIndex for out-of-range', () => {
    const s = stateFromIndex(100);
    // 100 → clamp to 8 → floor(8/3)=2 → primary=2-1=1, 8%3=2 → mirror=2-1=1
    expect(s.primary).toBe(1);
    expect(s.mirror).toBe(1);
  });

  it('should handle custom config in DualTernarySystem', () => {
    const system = new DualTernarySystem({
      phaseAnomalyThreshold: 0.5,
      minSequenceLength: 4,
    });
    for (let i = 0; i < 5; i++) {
      system.encode(safeState21D());
    }
    const analysis = system.fullAnalysis();
    expect(analysis).toBeDefined();
  });

  it('should handle all-zero brain state', () => {
    const system = new DualTernarySystem();
    const encoded = system.encode(new Array(21).fill(0));
    // All zeros → all (0, 0) states
    for (const s of encoded) {
      expect(s.primary).toBe(0);
      expect(s.mirror).toBe(0);
    }
  });
});
