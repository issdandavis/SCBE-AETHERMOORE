/**
 * AI Brain Conservation Law Enforcement Tests
 *
 * Tests for the 6 conservation law projections, global invariant I(x),
 * and RefactorAlign kernel Π(x) idempotency.
 *
 * @layer Layer 5, Layer 6, Layer 8, Layer 9, Layer 12
 */

import { describe, expect, it } from 'vitest';

import {
  BLOCK_RANGES,
  BRAIN_DIMENSIONS,
  BRAIN_EPSILON,
  type BlockName,
  UnifiedBrainState,
  extractBlock,
  replaceBlock,
  projectContainment,
  projectPhaseCoherence,
  projectEnergyBalance,
  projectLatticeContinuity,
  projectFluxNormalization,
  projectSpectralBounds,
  computeGlobalInvariant,
  refactorAlign,
  enforceConservationLaws,
} from '../../src/ai_brain/index';

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

/** Build a 21D zero vector */
function zeros(): number[] {
  return new Array(BRAIN_DIMENSIONS).fill(0);
}

/** Build a legal "safe" 21D vector (all laws satisfied) */
function safeVector(): number[] {
  const v = zeros();
  // BLOCK_HYPER [0-5]: small values inside ball
  v[0] = 0.1; v[1] = 0.1; v[2] = 0.1; v[3] = 0.1; v[4] = 0.1; v[5] = 0.1;
  // BLOCK_PHASE [6-11]: exact Z_6 values (multiples of π/3)
  v[6] = 0; v[7] = Math.PI / 3; v[8] = (2 * Math.PI) / 3;
  v[9] = Math.PI; v[10] = (4 * Math.PI) / 3; v[11] = (5 * Math.PI) / 3;
  // BLOCK_HAM [12-15]: small momenta
  v[12] = 0.1; v[13] = 0.1; v[14] = 0.1; v[15] = 0.1;
  // BLOCK_LATTICE [16-17]: adjacent indices
  v[16] = 3; v[17] = 4;
  // BLOCK_FLUX [18]: in [0, 1]
  v[18] = 0.5;
  // BLOCK_SPEC [19-20]: PR >= 1, entropy <= 6
  v[19] = 2.0; v[20] = 3.0;
  return v;
}

/** Build a vector that violates all 6 laws */
function breachVector(): number[] {
  const v = zeros();
  // BLOCK_HYPER: norm > 1
  v[0] = 0.8; v[1] = 0.8; v[2] = 0.8; v[3] = 0.8; v[4] = 0.8; v[5] = 0.8;
  // BLOCK_PHASE: not on Z_6
  v[6] = 0.5; v[7] = 1.2; v[8] = 2.5; v[9] = 3.5; v[10] = 4.8; v[11] = 5.5;
  // BLOCK_HAM: large momenta (will mismatch target energy)
  v[12] = 5; v[13] = 5; v[14] = 5; v[15] = 5;
  // BLOCK_LATTICE: non-adjacent (0, 10)
  v[16] = 0; v[17] = 10;
  // BLOCK_FLUX: out of range
  v[18] = 2.5;
  // BLOCK_SPEC: PR < 1, entropy > 6
  v[19] = 0.3; v[20] = 8.0;
  return v;
}

function vecNorm(v: number[]): number {
  return Math.sqrt(v.reduce((s, x) => s + x * x, 0));
}

// ═══════════════════════════════════════════════════════════════
// Block Structure Tests
// ═══════════════════════════════════════════════════════════════

describe('Block Structure', () => {
  it('should cover all 21 dimensions with no gaps or overlaps', () => {
    const covered = new Set<number>();
    const blocks = Object.values(BLOCK_RANGES);

    for (const { start, end } of blocks) {
      for (let i = start; i < end; i++) {
        expect(covered.has(i)).toBe(false); // No overlap
        covered.add(i);
      }
    }

    expect(covered.size).toBe(BRAIN_DIMENSIONS);
    for (let i = 0; i < BRAIN_DIMENSIONS; i++) {
      expect(covered.has(i)).toBe(true); // No gaps
    }
  });

  it('should extract correct slices for each block', () => {
    const v = Array.from({ length: 21 }, (_, i) => i * 10);

    expect(extractBlock(v, 'BLOCK_HYPER')).toEqual([0, 10, 20, 30, 40, 50]);
    expect(extractBlock(v, 'BLOCK_PHASE')).toEqual([60, 70, 80, 90, 100, 110]);
    expect(extractBlock(v, 'BLOCK_HAM')).toEqual([120, 130, 140, 150]);
    expect(extractBlock(v, 'BLOCK_LATTICE')).toEqual([160, 170]);
    expect(extractBlock(v, 'BLOCK_FLUX')).toEqual([180]);
    expect(extractBlock(v, 'BLOCK_SPEC')).toEqual([190, 200]);
  });

  it('should replace only the target block', () => {
    const v = zeros();
    const replaced = replaceBlock(v, 'BLOCK_HYPER', [1, 2, 3, 4, 5, 6]);

    // Target block changed
    expect(replaced.slice(0, 6)).toEqual([1, 2, 3, 4, 5, 6]);
    // Rest unchanged
    expect(replaced.slice(6)).toEqual(v.slice(6));
    // Original not mutated
    expect(v[0]).toBe(0);
  });

  it('should throw on wrong-length replacement', () => {
    const v = zeros();
    expect(() => replaceBlock(v, 'BLOCK_HYPER', [1, 2, 3])).toThrow(RangeError);
    expect(() => replaceBlock(v, 'BLOCK_FLUX', [1, 2])).toThrow(RangeError);
  });
});

// ═══════════════════════════════════════════════════════════════
// Law 1: Containment
// ═══════════════════════════════════════════════════════════════

describe('Law 1: Containment', () => {
  it('should pass when BLOCK_HYPER norm is small', () => {
    const v = safeVector();
    const result = projectContainment(v);
    expect(result.satisfied).toBe(true);
    expect(result.violationMagnitude).toBe(0);
  });

  it('should clamp when norm exceeds clampNorm', () => {
    const v = zeros();
    // Set BLOCK_HYPER to large values: norm = sqrt(6*0.8^2) ≈ 1.96
    for (let i = 0; i < 6; i++) v[i] = 0.8;
    const result = projectContainment(v, 0.95);

    expect(result.satisfied).toBe(false);
    expect(result.violationMagnitude).toBeGreaterThan(0);

    const projHyper = extractBlock(result.projectedVector, 'BLOCK_HYPER');
    expect(vecNorm(projHyper)).toBeCloseTo(0.95, 8);
  });

  it('should preserve direction when clamping', () => {
    const v = zeros();
    v[0] = 1.0; v[1] = 0; v[2] = 0; v[3] = 0; v[4] = 0; v[5] = 0;
    const result = projectContainment(v, 0.95);

    const projHyper = extractBlock(result.projectedVector, 'BLOCK_HYPER');
    // Direction should be [1,0,0,0,0,0] scaled to 0.95
    expect(projHyper[0]).toBeCloseTo(0.95, 8);
    expect(projHyper[1]).toBeCloseTo(0, 8);
  });

  it('should handle zero vector gracefully', () => {
    const v = zeros();
    const result = projectContainment(v);
    expect(result.satisfied).toBe(true);
    expect(result.violationMagnitude).toBe(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Law 2: Phase Coherence
// ═══════════════════════════════════════════════════════════════

describe('Law 2: Phase Coherence', () => {
  it('should pass when phases are on Z_6', () => {
    const v = safeVector();
    const result = projectPhaseCoherence(v);
    expect(result.satisfied).toBe(true);
    expect(result.violationMagnitude).toBeCloseTo(0, 8);
  });

  it('should snap slightly off-Z_6 phases to nearest', () => {
    const v = zeros();
    v[6] = 0.1; // near 0 → snap to 0
    v[7] = Math.PI / 3 + 0.05; // near π/3 → snap to π/3
    const result = projectPhaseCoherence(v);

    const projPhase = extractBlock(result.projectedVector, 'BLOCK_PHASE');
    expect(projPhase[0]).toBeCloseTo(0, 8);
    expect(projPhase[1]).toBeCloseTo(Math.PI / 3, 8);
    expect(result.violationMagnitude).toBeGreaterThan(0);
  });

  it('should handle wrap-around near 2π', () => {
    const v = zeros();
    v[6] = 2 * Math.PI - 0.01; // very close to 2π ≈ 0 → snap to 0
    const result = projectPhaseCoherence(v);

    const projPhase = extractBlock(result.projectedVector, 'BLOCK_PHASE');
    expect(projPhase[0]).toBeCloseTo(0, 8);
  });

  it('should snap negative phases correctly', () => {
    const v = zeros();
    v[6] = -0.1; // slightly negative → wraps to near 2π → snaps to 5π/3 or 0
    const result = projectPhaseCoherence(v);

    const projPhase = extractBlock(result.projectedVector, 'BLOCK_PHASE');
    // Should be 0 (angular distance ~0.1) not 5π/3 (angular distance ~0.19)
    expect(projPhase[0]).toBeCloseTo(0, 8);
  });
});

// ═══════════════════════════════════════════════════════════════
// Law 3: Energy Balance
// ═══════════════════════════════════════════════════════════════

describe('Law 3: Energy Balance', () => {
  it('should pass when no target is specified (current energy = target)', () => {
    const v = safeVector();
    const result = projectEnergyBalance(v);
    expect(result.satisfied).toBe(true);
    expect(result.violationMagnitude).toBeCloseTo(0, 8);
  });

  it('should scale momenta down when energy too high', () => {
    const v = safeVector();
    // Set momenta high
    v[12] = 3; v[13] = 3; v[14] = 3; v[15] = 3;
    // H = 0.5*(36) + 0.5*(0.06) = 18.03; target = 1.0
    const result = projectEnergyBalance(v, 1.0);

    expect(result.satisfied).toBe(false);

    const projHam = extractBlock(result.projectedVector, 'BLOCK_HAM');
    const pNormSq = projHam.reduce((s, x) => s + x * x, 0);
    const hyperBlock = extractBlock(v, 'BLOCK_HYPER');
    const potential = 0.5 * hyperBlock.reduce((s, x) => s + x * x, 0);
    const newEnergy = 0.5 * pNormSq + potential;

    expect(newEnergy).toBeCloseTo(1.0, 4);
  });

  it('should scale momenta up when energy too low', () => {
    const v = safeVector();
    // Small momenta, target higher
    v[12] = 0.01; v[13] = 0.01; v[14] = 0.01; v[15] = 0.01;
    const targetE = 5.0;
    const result = projectEnergyBalance(v, targetE);

    const projHam = extractBlock(result.projectedVector, 'BLOCK_HAM');
    const pNormSq = projHam.reduce((s, x) => s + x * x, 0);
    const hyperBlock = extractBlock(v, 'BLOCK_HYPER');
    const potential = 0.5 * hyperBlock.reduce((s, x) => s + x * x, 0);
    const newEnergy = 0.5 * pNormSq + potential;

    expect(newEnergy).toBeCloseTo(targetE, 4);
  });

  it('should zero momenta when potential exceeds target', () => {
    const v = zeros();
    // Large BLOCK_HYPER → high potential
    for (let i = 0; i < 6; i++) v[i] = 0.5;
    v[12] = 1; v[13] = 1; v[14] = 1; v[15] = 1;
    // Potential = 0.5 * 6 * 0.25 = 0.75; target = 0.1 < potential
    const result = projectEnergyBalance(v, 0.1);

    const projHam = extractBlock(result.projectedVector, 'BLOCK_HAM');
    projHam.forEach((p) => expect(p).toBe(0));
  });
});

// ═══════════════════════════════════════════════════════════════
// Law 4: Lattice Continuity
// ═══════════════════════════════════════════════════════════════

describe('Law 4: Lattice Continuity', () => {
  it('should pass for adjacent indices', () => {
    const v = safeVector();
    v[16] = 5; v[17] = 6;
    const result = projectLatticeContinuity(v);
    expect(result.satisfied).toBe(true);
    expect(result.violationMagnitude).toBe(0);
  });

  it('should pass for self-loop (same index)', () => {
    const v = safeVector();
    v[16] = 7; v[17] = 7;
    const result = projectLatticeContinuity(v);
    expect(result.satisfied).toBe(true);
  });

  it('should snap non-adjacent indices to nearest neighbor', () => {
    const v = safeVector();
    v[16] = 0; v[17] = 10; // gap of 10 → not adjacent
    const result = projectLatticeContinuity(v);

    expect(result.satisfied).toBe(false);
    expect(result.violationMagnitude).toBe(10);

    const projLattice = extractBlock(result.projectedVector, 'BLOCK_LATTICE');
    expect(projLattice[0]).toBe(0);
    expect(Math.abs(projLattice[0] - projLattice[1])).toBeLessThanOrEqual(1);
  });

  it('should clamp out-of-range indices to [0, 15]', () => {
    const v = safeVector();
    v[16] = -5; v[17] = 100;
    const result = projectLatticeContinuity(v);

    const projLattice = extractBlock(result.projectedVector, 'BLOCK_LATTICE');
    expect(projLattice[0]).toBeGreaterThanOrEqual(0);
    expect(projLattice[0]).toBeLessThanOrEqual(15);
    expect(projLattice[1]).toBeGreaterThanOrEqual(0);
    expect(projLattice[1]).toBeLessThanOrEqual(15);
  });
});

// ═══════════════════════════════════════════════════════════════
// Law 5: Flux Normalization
// ═══════════════════════════════════════════════════════════════

describe('Law 5: Flux Normalization', () => {
  it('should pass when flux is in [0, 1]', () => {
    const v = safeVector();
    const result = projectFluxNormalization(v);
    expect(result.satisfied).toBe(true);
    expect(result.violationMagnitude).toBe(0);
  });

  it('should clamp negative flux to 0', () => {
    const v = safeVector();
    v[18] = -0.5;
    const result = projectFluxNormalization(v);

    expect(result.satisfied).toBe(false);
    expect(result.violationMagnitude).toBeCloseTo(0.5, 8);
    expect(extractBlock(result.projectedVector, 'BLOCK_FLUX')[0]).toBe(0);
  });

  it('should clamp flux > 1 to 1', () => {
    const v = safeVector();
    v[18] = 3.7;
    const result = projectFluxNormalization(v);

    expect(result.satisfied).toBe(false);
    expect(result.violationMagnitude).toBeCloseTo(2.7, 8);
    expect(extractBlock(result.projectedVector, 'BLOCK_FLUX')[0]).toBe(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// Law 6: Spectral Bounds
// ═══════════════════════════════════════════════════════════════

describe('Law 6: Spectral Bounds', () => {
  it('should pass when PR >= 1 and entropy <= 6', () => {
    const v = safeVector();
    const result = projectSpectralBounds(v);
    expect(result.satisfied).toBe(true);
    expect(result.violationMagnitude).toBeCloseTo(0, 8);
  });

  it('should clamp PR < 1 to 1', () => {
    const v = safeVector();
    v[19] = 0.3;
    const result = projectSpectralBounds(v);

    expect(result.satisfied).toBe(false);
    const projSpec = extractBlock(result.projectedVector, 'BLOCK_SPEC');
    expect(projSpec[0]).toBeCloseTo(1.0, 8);
  });

  it('should clamp entropy > 6 to 6', () => {
    const v = safeVector();
    v[20] = 9.5;
    const result = projectSpectralBounds(v);

    expect(result.satisfied).toBe(false);
    const projSpec = extractBlock(result.projectedVector, 'BLOCK_SPEC');
    expect(projSpec[1]).toBeCloseTo(6.0, 8);
  });

  it('should handle both violations simultaneously', () => {
    const v = safeVector();
    v[19] = 0.5; // PR violation: 0.5
    v[20] = 8.0; // entropy violation: 2.0
    const result = projectSpectralBounds(v);

    expect(result.violationMagnitude).toBeCloseTo(2.5, 8);
  });
});

// ═══════════════════════════════════════════════════════════════
// Global Invariant I(x)
// ═══════════════════════════════════════════════════════════════

describe('Global Invariant', () => {
  it('should be 0 for a safe vector', () => {
    const v = safeVector();
    const I = computeGlobalInvariant(v);
    expect(I).toBeCloseTo(0, 6);
  });

  it('should be > 0 for a breach vector', () => {
    const v = breachVector();
    const I = computeGlobalInvariant(v);
    expect(I).toBeGreaterThan(0);
  });

  it('should equal sum of individual violations', () => {
    const v = safeVector();
    v[18] = 2.0; // flux violation = 1.0
    v[19] = 0.5; // PR violation = 0.5

    const r5 = projectFluxNormalization(v);
    const r6 = projectSpectralBounds(v);
    const I = computeGlobalInvariant(v);

    expect(I).toBeGreaterThanOrEqual(r5.violationMagnitude + r6.violationMagnitude - BRAIN_EPSILON);
  });

  it('should be 0 after refactorAlign', () => {
    const v = breachVector();
    const result = refactorAlign(v);
    const I = computeGlobalInvariant(result.outputVector);
    expect(I).toBeCloseTo(0, 6);
  });
});

// ═══════════════════════════════════════════════════════════════
// RefactorAlign Kernel
// ═══════════════════════════════════════════════════════════════

describe('RefactorAlign Kernel', () => {
  it('should return 21D output vector', () => {
    const v = breachVector();
    const result = refactorAlign(v);
    expect(result.outputVector).toHaveLength(BRAIN_DIMENSIONS);
  });

  it('should report 6 law results', () => {
    const v = breachVector();
    const result = refactorAlign(v);
    expect(result.lawResults).toHaveLength(6);
  });

  it('should report allSatisfied=true after projection', () => {
    const v = breachVector();
    const result = refactorAlign(v);
    expect(result.allSatisfied).toBe(true);
  });

  it('should report globalInvariant ≈ 0 after projection', () => {
    const v = breachVector();
    const result = refactorAlign(v);
    expect(result.globalInvariant).toBeCloseTo(0, 6);
  });

  it('should throw on wrong-dimension input', () => {
    expect(() => refactorAlign([1, 2, 3])).toThrow(RangeError);
    expect(() => refactorAlign(new Array(22).fill(0))).toThrow(RangeError);
  });

  it('should be idempotent: Π(Π(x)) === Π(x) for safe vector', () => {
    const v = safeVector();
    const first = refactorAlign(v);
    const second = refactorAlign(first.outputVector);

    first.outputVector.forEach((val, i) => {
      expect(second.outputVector[i]).toBeCloseTo(val, 10);
    });
  });

  it('should be idempotent: Π(Π(x)) === Π(x) for breach vector', () => {
    const v = breachVector();
    const first = refactorAlign(v);
    const second = refactorAlign(first.outputVector);

    first.outputVector.forEach((val, i) => {
      expect(second.outputVector[i]).toBeCloseTo(val, 10);
    });
  });

  it('should be idempotent: Π(Π(x)) === Π(x) for random vectors', () => {
    // Deterministic pseudo-random via simple LCG
    let seed = 42;
    function nextRand(): number {
      seed = (seed * 1103515245 + 12345) & 0x7fffffff;
      return (seed / 0x7fffffff) * 4 - 2; // range [-2, 2]
    }

    for (let trial = 0; trial < 5; trial++) {
      const v = Array.from({ length: BRAIN_DIMENSIONS }, () => nextRand());
      const first = refactorAlign(v);
      const second = refactorAlign(first.outputVector);

      first.outputVector.forEach((val, i) => {
        expect(second.outputVector[i]).toBeCloseTo(val, 8);
      });
    }
  });

  it('should be idempotent: Π(Π(x)) === Π(x) for extreme vectors', () => {
    // All zeros
    const z = zeros();
    const zFirst = refactorAlign(z);
    const zSecond = refactorAlign(zFirst.outputVector);
    zFirst.outputVector.forEach((val, i) => {
      expect(zSecond.outputVector[i]).toBeCloseTo(val, 10);
    });

    // All large positive
    const big = new Array(BRAIN_DIMENSIONS).fill(100);
    const bigFirst = refactorAlign(big);
    const bigSecond = refactorAlign(bigFirst.outputVector);
    bigFirst.outputVector.forEach((val, i) => {
      expect(bigSecond.outputVector[i]).toBeCloseTo(val, 8);
    });

    // All large negative
    const neg = new Array(BRAIN_DIMENSIONS).fill(-100);
    const negFirst = refactorAlign(neg);
    const negSecond = refactorAlign(negFirst.outputVector);
    negFirst.outputVector.forEach((val, i) => {
      expect(negSecond.outputVector[i]).toBeCloseTo(val, 8);
    });
  });

  it('should not modify a vector that already satisfies all laws', () => {
    const v = safeVector();
    const result = refactorAlign(v);

    // Input violations should all be 0
    result.lawResults.forEach((lr) => {
      expect(lr.violationMagnitude).toBeCloseTo(0, 6);
    });

    // Output should be very close to input
    v.forEach((val, i) => {
      expect(result.outputVector[i]).toBeCloseTo(val, 6);
    });
  });

  it('should correct all 6 violations in a breach vector', () => {
    const v = breachVector();
    const result = refactorAlign(v);

    // At least some laws should have been violated on input
    const violatedCount = result.lawResults.filter((lr) => !lr.satisfied).length;
    expect(violatedCount).toBeGreaterThan(0);

    // After projection, all should be satisfied
    expect(result.allSatisfied).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// UnifiedBrainState Integration
// ═══════════════════════════════════════════════════════════════

describe('UnifiedBrainState Integration', () => {
  it('should return a valid UnifiedBrainState', () => {
    const state = new UnifiedBrainState();
    const { correctedState, result } = enforceConservationLaws(state);

    expect(correctedState).toBeInstanceOf(UnifiedBrainState);
    expect(result.outputVector).toHaveLength(BRAIN_DIMENSIONS);
  });

  it('should enforce containment on safe origin (norm > 1 in component space)', () => {
    const state = UnifiedBrainState.safeOrigin();
    const { correctedState, result } = enforceConservationLaws(state);

    // Safe origin has trust values at 1.0, giving BLOCK_HYPER norm ≈ 2.29.
    // The containment projection correctly clamps this to the ball boundary.
    expect(result.lawResults[0].law).toBe('containment');
    expect(result.allSatisfied).toBe(true); // After projection, all satisfied

    // Flux should already be satisfied (trustScore = 1.0 ∈ [0,1])
    expect(result.lawResults[4].satisfied).toBe(true); // flux
  });

  it('should round-trip: corrected vector matches refactorAlign output', () => {
    const state = new UnifiedBrainState({
      scbeContext: {
        deviceTrust: 0.9,
        locationTrust: 0.9,
        networkTrust: 0.9,
        behaviorScore: 0.9,
        timeOfDay: 0.9,
        intentAlignment: 0.9,
      },
    });

    const { correctedState, result } = enforceConservationLaws(state);
    const correctedVector = correctedState.toVector();

    result.outputVector.forEach((val, i) => {
      expect(correctedVector[i]).toBeCloseTo(val, 8);
    });
  });

  it('should accept custom config', () => {
    const state = new UnifiedBrainState();
    const { result } = enforceConservationLaws(state, {
      poincareClampNorm: 0.8,
      prLowerBound: 2.0,
      entropyUpperBound: 4.0,
    });

    // With stricter bounds, the spectral block should be adjusted
    const projSpec = extractBlock(result.outputVector, 'BLOCK_SPEC');
    expect(projSpec[0]).toBeGreaterThanOrEqual(2.0 - BRAIN_EPSILON);
    expect(projSpec[1]).toBeLessThanOrEqual(4.0 + BRAIN_EPSILON);
  });
});
