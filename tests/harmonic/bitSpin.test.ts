/**
 * @file bitSpin.test.ts
 * @module tests/harmonic
 * @layer Layer 9, Layer 10, Layer 12
 * @component P-Bit Spin Field Tests
 * @version 1.0.0
 */

import { describe, it, expect } from 'vitest';
import {
  sigmoid,
  effectiveField,
  computeIsingEnergy,
  computeMagnetization,
  SpinField,
} from '../../src/harmonic/bitSpin.js';
import type { PBit, SpinCoupling } from '../../src/harmonic/bitSpin.js';

// Deterministic PRNG for reproducible tests
function seededRng(seed: number = 42): () => number {
  let s = seed;
  return () => {
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    return s / 0x7fffffff;
  };
}

describe('sigmoid', () => {
  it('returns 0.5 at x = 0', () => {
    expect(sigmoid(0)).toBeCloseTo(0.5, 10);
  });

  it('approaches 1 for large positive x', () => {
    expect(sigmoid(10)).toBeGreaterThan(0.9999);
    expect(sigmoid(500)).toBe(1.0);
  });

  it('approaches 0 for large negative x', () => {
    expect(sigmoid(-10)).toBeLessThan(0.0001);
    expect(sigmoid(-501)).toBe(0.0);
  });

  it('is monotonically increasing', () => {
    for (let x = -5; x < 5; x += 0.5) {
      expect(sigmoid(x + 0.5)).toBeGreaterThan(sigmoid(x));
    }
  });

  it('satisfies σ(x) + σ(-x) = 1', () => {
    for (const x of [-3, -1, 0, 1, 3]) {
      expect(sigmoid(x) + sigmoid(-x)).toBeCloseTo(1.0, 10);
    }
  });
});

describe('effectiveField', () => {
  it('returns just bias when uncoupled', () => {
    const pbit: PBit = { id: 'a', state: 0, bias: 2.0, temperature: 1.0 };
    const states = new Map<string, 0 | 1>([['a', 0]]);
    expect(effectiveField(pbit, [], states, false)).toBe(2.0);
  });

  it('modulates bias by tongue weight when enabled', () => {
    const pbit: PBit = { id: 'a', state: 0, bias: 1.0, tongue: 'AV', temperature: 1.0 };
    const states = new Map<string, 0 | 1>([['a', 0]]);
    const h = effectiveField(pbit, [], states, true);
    // AV weight = φ ≈ 1.618
    expect(h).toBeCloseTo(1.618, 2);
  });

  it('includes coupling contributions from neighbors', () => {
    const pbit: PBit = { id: 'a', state: 0, bias: 0, temperature: 1.0 };
    const couplings: SpinCoupling[] = [{ from: 'a', to: 'b', strength: 1.0 }];
    const states = new Map<string, 0 | 1>([
      ['a', 0],
      ['b', 1],
    ]);
    // Neighbor b is in state 1 → Ising = 2*1-1 = +1
    // h = 0 + 1.0 * 1 = 1.0
    const h = effectiveField(pbit, couplings, states, false);
    expect(h).toBe(1.0);
  });

  it('antiferromagnetic coupling prefers opposite states', () => {
    const pbit: PBit = { id: 'a', state: 0, bias: 0, temperature: 1.0 };
    const couplings: SpinCoupling[] = [{ from: 'a', to: 'b', strength: -1.0 }];
    // When neighbor is 1 (Ising +1), J < 0 → h < 0 → P(s=1) < 0.5
    const states = new Map<string, 0 | 1>([
      ['a', 0],
      ['b', 1],
    ]);
    const h = effectiveField(pbit, couplings, states, false);
    expect(h).toBe(-1.0);
    expect(sigmoid(h)).toBeLessThan(0.5);
  });
});

describe('computeIsingEnergy', () => {
  it('returns 0 for ground state with no couplings and no bias', () => {
    const pbits: PBit[] = [
      { id: 'a', state: 0, bias: 0, temperature: 1.0 },
      { id: 'b', state: 0, bias: 0, temperature: 1.0 },
    ];
    const energy = computeIsingEnergy(pbits, [], false);
    // σ_a = -1, σ_b = -1; no coupling, no bias → E = -0*(-1) - 0*(-1) = 0
    // With Ising convention and bias 0: -h*σ terms are 0
    expect(energy).toBe(0);
  });

  it('has lower energy for aligned spins with ferromagnetic coupling', () => {
    const aligned: PBit[] = [
      { id: 'a', state: 1, bias: 0, temperature: 1.0 },
      { id: 'b', state: 1, bias: 0, temperature: 1.0 },
    ];
    const antiAligned: PBit[] = [
      { id: 'a', state: 1, bias: 0, temperature: 1.0 },
      { id: 'b', state: 0, bias: 0, temperature: 1.0 },
    ];
    const coupling: SpinCoupling[] = [{ from: 'a', to: 'b', strength: 1.0 }];

    const eAligned = computeIsingEnergy(aligned, coupling, false);
    const eAntiAligned = computeIsingEnergy(antiAligned, coupling, false);

    // Ferromagnetic: aligned should have LOWER energy
    expect(eAligned).toBeLessThan(eAntiAligned);
  });
});

describe('computeMagnetization', () => {
  it('returns 0 for empty array', () => {
    expect(computeMagnetization([])).toBe(0);
  });

  it('returns 0.5 for balanced spins', () => {
    const pbits: PBit[] = [
      { id: 'a', state: 0, bias: 0, temperature: 1.0 },
      { id: 'b', state: 1, bias: 0, temperature: 1.0 },
    ];
    expect(computeMagnetization(pbits)).toBe(0.5);
  });

  it('returns 1.0 for all-up spins', () => {
    const pbits: PBit[] = [
      { id: 'a', state: 1, bias: 0, temperature: 1.0 },
      { id: 'b', state: 1, bias: 0, temperature: 1.0 },
    ];
    expect(computeMagnetization(pbits)).toBe(1.0);
  });
});

describe('SpinField', () => {
  it('creates p-bits with addPBit', () => {
    const field = new SpinField();
    const pbit = field.addPBit('test', 0.5, 'KO');
    expect(pbit.id).toBe('test');
    expect(pbit.bias).toBe(0.5);
    expect(pbit.tongue).toBe('KO');
    expect([0, 1]).toContain(pbit.state);
  });

  it('adds couplings between p-bits', () => {
    const field = new SpinField();
    field.addPBit('a', 0);
    field.addPBit('b', 0);
    const coupling = field.addCoupling('a', 'b', 1.5);
    expect(coupling.strength).toBe(1.5);
    expect(field.getCouplings()).toHaveLength(1);
  });

  it('builds tongue hexagon with 6 nodes and 9 couplings', () => {
    const field = new SpinField();
    field.buildTongueHexagon();
    expect(field.getAllPBits()).toHaveLength(6);
    // 6 nearest-neighbor + 3 cross-diagonal = 9
    expect(field.getCouplings()).toHaveLength(9);
  });

  it('steps without error', () => {
    const field = new SpinField();
    field.buildTongueHexagon();
    const rng = seededRng(42);
    expect(() => field.step(rng)).not.toThrow();
    expect(field.getStep()).toBe(1);
  });

  it('produces valid snapshots', () => {
    const field = new SpinField();
    field.buildTongueHexagon();
    const rng = seededRng(42);

    // Run several steps to build history
    for (let i = 0; i < 20; i++) field.step(rng);

    const snap = field.snapshot();
    expect(snap.states.size).toBe(6);
    expect(snap.magnetization).toBeGreaterThanOrEqual(0);
    expect(snap.magnetization).toBeLessThanOrEqual(1);
    expect(snap.anomalyScore).toBeGreaterThanOrEqual(0);
    expect(snap.anomalyScore).toBeLessThanOrEqual(1);
    expect(snap.step).toBe(20);
  });

  it('reset clears all state', () => {
    const field = new SpinField();
    field.buildTongueHexagon();
    field.step(seededRng());
    field.reset();
    expect(field.getStep()).toBe(0);
    // All states should be 0 after reset
    for (const pbit of field.getAllPBits()) {
      expect(pbit.state).toBe(0);
    }
  });

  it('strongly biased field converges to expected magnetization', () => {
    const field = new SpinField({ temperature: 0.1 });
    // Strong positive bias → should converge to all-1
    for (let i = 0; i < 6; i++) {
      field.addPBit(`n${i}`, 5.0); // Strong positive bias
    }
    const rng = seededRng(123);
    for (let i = 0; i < 50; i++) field.step(rng);

    const snap = field.snapshot();
    // With strong bias and low temperature, magnetization should be high
    expect(snap.magnetization).toBeGreaterThan(0.7);
  });

  it('high temperature produces near-random magnetization', () => {
    const field = new SpinField({ temperature: 100 });
    field.buildTongueHexagon();
    const rng = seededRng(42);

    // Collect magnetization samples
    const samples: number[] = [];
    for (let i = 0; i < 100; i++) {
      field.step(rng);
      samples.push(field.snapshot().magnetization);
    }

    // Average should be near 0.5 for high temperature
    const avg = samples.reduce((a, b) => a + b, 0) / samples.length;
    expect(avg).toBeGreaterThan(0.2);
    expect(avg).toBeLessThan(0.8);
  });
});
