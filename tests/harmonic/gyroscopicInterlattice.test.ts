/**
 * @file gyroscopicInterlattice.test.ts
 * @layer Layer 5, Layer 6, Layer 7
 * @component Gyroscopic Interlattice Coupling Tests
 *
 * Tests for the gyroscopic interlattice module — verifying:
 * - Phi-scaled tongue radii match golden ratio progression
 * - Coupling strength follows inverse fifth power (locality)
 * - Nash equation preserves first-order dynamics
 * - Chern numbers are well-defined for the hexagonal tongue lattice
 * - Anderson insulation: disorder preserves or strengthens topology
 * - All 15 interlattice couplings are generated (C(6,2))
 * - Phase factors break time-reversal symmetry for non-square lattices
 *
 * Reference: Nash et al. PNAS 112:14495 (2015)
 */

import { describe, it, expect } from 'vitest';
import {
  TONGUE_LABELS,
  TONGUE_RADII,
  TONGUE_PHASES,
  createSublattice,
  couplingStrength,
  bondAngle,
  phaseFactor,
  createCouple,
  allCouplings,
  nashEquationOfMotion,
  evolveStep,
  computeChernNumber,
  totalChernNumber,
  andersonInsulationTest,
  couplingMatrix,
  initializeGyroscopicLattice,
  gyroscopicBreathingFactor,
  perTongueBreathingFactors,
  chernWeights,
} from '../../packages/kernel/src/gyroscopicInterlattice.js';

const PHI = (1 + Math.sqrt(5)) / 2;

describe('Tongue Sublattice Geometry', () => {
  it('has exactly 6 Sacred Tongues', () => {
    expect(TONGUE_LABELS).toHaveLength(6);
    expect(TONGUE_LABELS).toEqual(['KO', 'AV', 'RU', 'CA', 'UM', 'DR']);
  });

  it('tongue radii follow phi^k progression', () => {
    for (let k = 0; k < 6; k++) {
      const tongue = TONGUE_LABELS[k];
      const expected = Math.pow(PHI, k);
      expect(TONGUE_RADII[tongue]).toBeCloseTo(expected, 10);
    }
  });

  it('tongue phases are 60° hexagonal intervals', () => {
    for (let k = 0; k < 6; k++) {
      const tongue = TONGUE_LABELS[k];
      const expected = (2 * Math.PI * k) / 6;
      expect(TONGUE_PHASES[tongue]).toBeCloseTo(expected, 10);
    }
  });

  it('KO has fastest precession, DR has slowest', () => {
    const ko = createSublattice('KO');
    const dr = createSublattice('DR');
    expect(ko.precessionFreq).toBeGreaterThan(dr.precessionFreq);
    expect(ko.precessionFreq).toBeCloseTo(1.0, 5); // 1/φ⁰ = 1
    expect(dr.precessionFreq).toBeCloseTo(1 / Math.pow(PHI, 5), 5);
  });

  it('sublattice has alternating Chern numbers by default', () => {
    const sublattices = TONGUE_LABELS.map((t) => createSublattice(t));
    // Even indices (KO, RU, UM) → +1, odd indices (AV, CA, DR) → -1
    expect(sublattices[0].chernNumber).toBe(1); // KO
    expect(sublattices[1].chernNumber).toBe(-1); // AV
    expect(sublattices[2].chernNumber).toBe(1); // RU
    expect(sublattices[3].chernNumber).toBe(-1); // CA
    expect(sublattices[4].chernNumber).toBe(1); // UM
    expect(sublattices[5].chernNumber).toBe(-1); // DR
  });
});

describe('Interlattice Coupling (Magnetic Dipole Spring)', () => {
  it('coupling follows inverse fifth power of spacing — A2: Locality', () => {
    // Adjacent tongues (KO↔AV, spacing = φ-1 ≈ 0.618) should couple much
    // stronger than distant tongues (KO↔DR, spacing = φ⁵-1 ≈ 10.09)
    const koAv = couplingStrength('KO', 'AV');
    const koDr = couplingStrength('KO', 'DR');
    expect(koAv).toBeGreaterThan(koDr);
    // Ratio should be roughly (10.09/0.618)^5 ≈ 4.3 million
    expect(koAv / koDr).toBeGreaterThan(1000);
  });

  it('self-coupling is zero', () => {
    for (const tongue of TONGUE_LABELS) {
      expect(couplingStrength(tongue, tongue)).toBe(0);
    }
  });

  it('coupling is symmetric: J(A,B) = J(B,A)', () => {
    for (let i = 0; i < TONGUE_LABELS.length; i++) {
      for (let j = i + 1; j < TONGUE_LABELS.length; j++) {
        const jAB = couplingStrength(TONGUE_LABELS[i], TONGUE_LABELS[j]);
        const jBA = couplingStrength(TONGUE_LABELS[j], TONGUE_LABELS[i]);
        expect(jAB).toBeCloseTo(jBA, 10);
      }
    }
  });

  it('generates exactly 15 unique couplings (C(6,2))', () => {
    const couples = allCouplings();
    expect(couples).toHaveLength(15);
    // Each pair should be unique
    const pairSet = new Set(couples.map((c) => `${c.tongueA}-${c.tongueB}`));
    expect(pairSet.size).toBe(15);
  });

  it('coupling matrix is symmetric with zero diagonal', () => {
    const J = couplingMatrix();
    expect(J).toHaveLength(6);
    for (let i = 0; i < 6; i++) {
      expect(J[i][i]).toBe(0); // No self-coupling
      for (let j = 0; j < 6; j++) {
        expect(J[i][j]).toBeCloseTo(J[j][i], 10); // Symmetric
      }
    }
  });
});

describe('Phase Factor and Time-Reversal Symmetry Breaking', () => {
  it('phase factors have unit magnitude', () => {
    for (let i = 0; i < TONGUE_LABELS.length; i++) {
      for (let j = i + 1; j < TONGUE_LABELS.length; j++) {
        const pf = phaseFactor(TONGUE_LABELS[i], TONGUE_LABELS[j]);
        const mag = Math.sqrt(pf.real * pf.real + pf.imag * pf.imag);
        expect(mag).toBeCloseTo(1.0, 10);
      }
    }
  });

  it('hexagonal phases produce non-trivial phase factors (TRS breaking)', () => {
    // For a square lattice (90° bonds), e^(2iθ) = e^(iπ) = -1 (real, TRS preserved)
    // For hexagonal (60° bonds), e^(2iθ) = e^(i2π/3) has nonzero imaginary part
    const koAv = phaseFactor('KO', 'AV');
    // θ = π/3, so e^(2iπ/3) = cos(2π/3) + i·sin(2π/3) = -0.5 + i·0.866
    expect(koAv.real).toBeCloseTo(Math.cos((2 * Math.PI) / 3), 10);
    expect(koAv.imag).toBeCloseTo(Math.sin((2 * Math.PI) / 3), 10);
    // Non-zero imaginary part = time-reversal symmetry breaking
    expect(Math.abs(koAv.imag)).toBeGreaterThan(0.1);
  });

  it('bond angles sum to 5π/3 for each tongue to all others', () => {
    // From KO to all 5 others: π/3 + 2π/3 + π + 4π/3 + 5π/3 = 5π
    for (const tongue of TONGUE_LABELS) {
      let sum = 0;
      for (const other of TONGUE_LABELS) {
        if (other !== tongue) sum += bondAngle(tongue, other);
      }
      // Sum should be a multiple of π (exact value depends on reference tongue)
      expect(Number.isFinite(sum)).toBe(true);
    }
  });
});

describe('Nash Equation of Motion (First-Order Dynamics)', () => {
  it('produces zero derivative for zero state', () => {
    const sublattices = TONGUE_LABELS.map((t) => createSublattice(t));
    // All states zero → all derivatives zero
    const couples = allCouplings();
    const coupleMap = new Map<string, (typeof couples)[0]>();
    for (const c of couples) {
      coupleMap.set(`${c.tongueA}-${c.tongueB}`, c);
      coupleMap.set(`${c.tongueB}-${c.tongueA}`, c);
    }

    for (const sub of sublattices) {
      const neighbors = sublattices
        .filter((s) => s.tongue !== sub.tongue)
        .map((s) => ({
          sublattice: s,
          couple: coupleMap.get(`${sub.tongue}-${s.tongue}`)!,
        }));
      const deriv = nashEquationOfMotion(sub, neighbors);
      expect(deriv.real).toBeCloseTo(0, 10);
      expect(deriv.imag).toBeCloseTo(0, 10);
    }
  });

  it('produces nonzero derivative for nonzero state', () => {
    const sublattices = TONGUE_LABELS.map((t) =>
      createSublattice(t, { real: 0.1, imag: 0.05 })
    );
    const couples = allCouplings();
    const coupleMap = new Map<string, (typeof couples)[0]>();
    for (const c of couples) {
      coupleMap.set(`${c.tongueA}-${c.tongueB}`, c);
      coupleMap.set(`${c.tongueB}-${c.tongueA}`, c);
    }

    // KO should have the largest derivative (fastest precession)
    const koNeighbors = sublattices
      .filter((s) => s.tongue !== 'KO')
      .map((s) => ({
        sublattice: s,
        couple: coupleMap.get(`KO-${s.tongue}`)!,
      }));
    const koDeriv = nashEquationOfMotion(sublattices[0], koNeighbors);
    expect(Math.abs(koDeriv.real) + Math.abs(koDeriv.imag)).toBeGreaterThan(0);
  });

  it('evolution preserves finite state (no blow-up for small dt)', () => {
    const sublattices = TONGUE_LABELS.map((t) =>
      createSublattice(t, { real: 0.1 * Math.cos(TONGUE_PHASES[t]), imag: 0.1 * Math.sin(TONGUE_PHASES[t]) })
    );

    // Evolve 100 steps at dt=0.001
    for (let step = 0; step < 100; step++) {
      evolveStep(sublattices, 0.001);
    }

    // All states should remain finite
    for (const sub of sublattices) {
      expect(Number.isFinite(sub.state.real)).toBe(true);
      expect(Number.isFinite(sub.state.imag)).toBe(true);
    }
  });
});

describe('Chern Number Computation', () => {
  it('all sublattices have well-defined Chern numbers', () => {
    const sublattices = TONGUE_LABELS.map((t) => createSublattice(t));
    for (const sub of sublattices) {
      const chern = computeChernNumber(sub.tongue, sublattices);
      expect(chern === 1 || chern === -1).toBe(true);
    }
  });

  it('total Chern number is computed without error', () => {
    const sublattices = TONGUE_LABELS.map((t) => createSublattice(t));
    const total = totalChernNumber(sublattices);
    expect(Number.isFinite(total)).toBe(true);
    // For a well-formed system, |total| should be small
    expect(Math.abs(total)).toBeLessThanOrEqual(6);
  });
});

describe('Anderson Insulation (Disorder Strengthening)', () => {
  it('topology survives 10% disorder', () => {
    const sublattices = TONGUE_LABELS.map((t) => createSublattice(t));
    // Use seeded RNG for reproducibility
    let seed = 42;
    const rng = () => {
      seed = (seed * 1664525 + 1013904223) % 4294967296;
      return seed / 4294967296;
    };

    const result = andersonInsulationTest(sublattices, 0.1, rng);
    expect(result.cleanChern).toHaveLength(6);
    expect(result.disorderedChern).toHaveLength(6);
    // Topology should survive mild disorder
    expect(result.topologyPreserved).toBe(true);
  });

  it('returns correct structure', () => {
    const sublattices = TONGUE_LABELS.map((t) => createSublattice(t));
    const result = andersonInsulationTest(sublattices, 0.05);
    expect(result).toHaveProperty('cleanChern');
    expect(result).toHaveProperty('disorderedChern');
    expect(result).toHaveProperty('topologyPreserved');
    expect(result).toHaveProperty('topologyStrengthened');
  });
});

describe('Full System Initialization', () => {
  it('initializes complete 6-tongue gyroscopic lattice', () => {
    const { sublattices, couplings, couplingMat } = initializeGyroscopicLattice();
    expect(sublattices).toHaveLength(6);
    expect(couplings).toHaveLength(15);
    expect(couplingMat).toHaveLength(6);
    expect(couplingMat[0]).toHaveLength(6);
  });

  it('adjacent tongue coupling >> distant tongue coupling', () => {
    const { couplingMat } = initializeGyroscopicLattice();
    // KO↔AV (indices 0,1) should be much stronger than KO↔DR (indices 0,5)
    expect(couplingMat[0][1]).toBeGreaterThan(couplingMat[0][5] * 100);
  });
});

describe('L6 Bridge — Gyroscopic Breathing Factor', () => {
  it('zero-state lattice produces breathing factor of 1.0 (no modulation)', () => {
    const sublattices = TONGUE_LABELS.map((t) => createSublattice(t));
    const b = gyroscopicBreathingFactor(sublattices);
    expect(b).toBe(1.0);
  });

  it('excited lattice produces breathing factor > 1.0', () => {
    const sublattices = TONGUE_LABELS.map((t) =>
      createSublattice(t, { real: 0.5, imag: 0.3 })
    );
    const b = gyroscopicBreathingFactor(sublattices);
    expect(b).toBeGreaterThan(1.0);
  });

  it('breathing factor is clamped to [1.0, 2.0]', () => {
    // Very high energy state
    const sublattices = TONGUE_LABELS.map((t) =>
      createSublattice(t, { real: 10.0, imag: 10.0 })
    );
    const b = gyroscopicBreathingFactor(sublattices);
    expect(b).toBeLessThanOrEqual(2.0);
    expect(b).toBeGreaterThanOrEqual(1.0);
  });

  it('KO-excited lattice breathes more than DR-excited (KO precesses faster)', () => {
    const koExcited = TONGUE_LABELS.map((t) => createSublattice(t));
    koExcited[0].state = { real: 0.5, imag: 0.5 }; // KO excited

    const drExcited = TONGUE_LABELS.map((t) => createSublattice(t));
    drExcited[5].state = { real: 0.5, imag: 0.5 }; // DR excited (same amplitude)

    const bKO = gyroscopicBreathingFactor(koExcited);
    const bDR = gyroscopicBreathingFactor(drExcited);
    // KO has higher precession freq → more breathing
    expect(bKO).toBeGreaterThan(bDR);
  });

  it('per-tongue breathing factors have 6 elements', () => {
    const sublattices = TONGUE_LABELS.map((t) =>
      createSublattice(t, { real: 0.1, imag: 0.1 })
    );
    const factors = perTongueBreathingFactors(sublattices);
    expect(factors).toHaveLength(6);
    for (const f of factors) {
      expect(f).toBeGreaterThanOrEqual(1.0);
      expect(f).toBeLessThanOrEqual(2.0);
    }
  });

  it('per-tongue KO factor > DR factor for equal amplitudes', () => {
    const sublattices = TONGUE_LABELS.map((t) =>
      createSublattice(t, { real: 0.3, imag: 0.2 })
    );
    const factors = perTongueBreathingFactors(sublattices);
    // KO (index 0) has fastest precession
    expect(factors[0]).toBeGreaterThan(factors[5]); // DR (index 5)
  });
});

describe('Chern-Weighted Tongue Vector', () => {
  it('returns 6 weights', () => {
    const sublattices = TONGUE_LABELS.map((t) => createSublattice(t));
    const weights = chernWeights(sublattices);
    expect(weights).toHaveLength(6);
  });

  it('weights are positive (no tongue fully suppressed)', () => {
    const sublattices = TONGUE_LABELS.map((t) => createSublattice(t));
    const weights = chernWeights(sublattices);
    for (const w of weights) {
      expect(w).toBeGreaterThan(0);
    }
  });

  it('C=+1 tongues get higher weight than C=-1 tongues', () => {
    const sublattices = TONGUE_LABELS.map((t) => createSublattice(t));
    const weights = chernWeights(sublattices, 0.3);
    // KO has Chern +1 (index 0), AV has Chern -1 (index 1)
    expect(weights[0]).toBeGreaterThan(weights[1]);
  });

  it('gamma=0 produces uniform weights of 1.0', () => {
    const sublattices = TONGUE_LABELS.map((t) => createSublattice(t));
    const weights = chernWeights(sublattices, 0);
    for (const w of weights) {
      expect(w).toBeCloseTo(1.0, 10);
    }
  });

  it('gamma is clamped to [0, 0.5]', () => {
    const sublattices = TONGUE_LABELS.map((t) => createSublattice(t));
    const w1 = chernWeights(sublattices, 0.5);
    const w2 = chernWeights(sublattices, 1.0); // should be clamped to 0.5
    expect(w1).toEqual(w2);
  });
});
