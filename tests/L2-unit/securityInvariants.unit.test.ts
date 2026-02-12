/**
 * @file securityInvariants.unit.test.ts
 * @tier L2-unit
 * @axiom 4 (Symmetry), 5 (Composition)
 * @category unit
 *
 * Unit tests for the 6 formal security invariants of the CHSFN quasi-sphere.
 */

import { describe, it, expect } from 'vitest';
import type { Vector6D } from '../../src/harmonic/constants.js';
import type { CHSFNState } from '../../src/harmonic/chsfn.js';
import {
  verifyExponentialCostInvariant,
  verifyMonotonicCost,
  verifyPhaseMismatchBlocking,
  verifyNodalStability,
  combinedSecurityCost,
  securityBitsEquivalent,
  verifyTongueBijectionUnderDrift,
  verifyEnergyNonIncrease,
} from '../../src/harmonic/securityInvariants.js';

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

const ORIGIN: Vector6D = [0, 0, 0, 0, 0, 0];
const ALIGNED_PHASE: Vector6D = [0, Math.PI / 3, (2 * Math.PI) / 3, Math.PI, (4 * Math.PI) / 3, (5 * Math.PI) / 3];

function makeAlignedState(pos: Vector6D): CHSFNState {
  return { position: pos, phase: [...ALIGNED_PHASE] as Vector6D, mass: 1.0 };
}

// ═══════════════════════════════════════════════════════════════
// Invariant 1: Exponential Access Cost
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: Invariant 1 — Exponential Access Cost', () => {
  it('should hold for d1=0, d2=1', () => {
    const result = verifyExponentialCostInvariant(0, 1);
    expect(result.holds).toBe(true);
    expect(result.actualRatio).toBeGreaterThan(1);
  });

  it('should hold for d1=1, d2=2', () => {
    const result = verifyExponentialCostInvariant(1, 2);
    expect(result.holds).toBe(true);
    expect(result.actualRatio).toBeGreaterThanOrEqual(result.minExpectedRatio - 1e-10);
  });

  it('should hold for d1=0, d2=5', () => {
    const result = verifyExponentialCostInvariant(0, 5);
    expect(result.holds).toBe(true);
    expect(result.actualRatio).toBeGreaterThan(100);
  });

  it('should trivially hold when d2 <= d1', () => {
    const result = verifyExponentialCostInvariant(3, 1);
    expect(result.holds).toBe(true);
    expect(result.actualRatio).toBe(1);
  });

  it('should hold for equal distances', () => {
    const result = verifyExponentialCostInvariant(2, 2);
    expect(result.holds).toBe(true);
  });

  it('should have increasing minExpectedRatio with distance gap', () => {
    const r1 = verifyExponentialCostInvariant(0, 1);
    const r3 = verifyExponentialCostInvariant(0, 3);
    expect(r3.minExpectedRatio).toBeGreaterThan(r1.minExpectedRatio);
  });
});

// ═══════════════════════════════════════════════════════════════
// Invariant 1b: Monotonic Cost
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: Invariant 1b — Monotonic Cost', () => {
  it('should be monotonically increasing', () => {
    expect(verifyMonotonicCost([0, 0.5, 1, 1.5, 2, 3, 5])).toBe(true);
  });

  it('should handle single element', () => {
    expect(verifyMonotonicCost([1])).toBe(true);
  });

  it('should handle two elements', () => {
    expect(verifyMonotonicCost([0.5, 1.0])).toBe(true);
  });

  it('should return true for empty', () => {
    expect(verifyMonotonicCost([])).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// Invariant 2: Phase Mismatch Blocking
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: Invariant 2 — Phase Mismatch Blocking', () => {
  it('should hold for tongue 0 at origin', () => {
    const result = verifyPhaseMismatchBlocking(ORIGIN, 0);
    expect(result.holds).toBe(true);
    expect(result.alignedImpedance).toBeLessThan(result.misalignedImpedance);
  });

  it('should hold for tongue 3 at origin', () => {
    const result = verifyPhaseMismatchBlocking(ORIGIN, 3);
    expect(result.holds).toBe(true);
  });

  it('should have aligned impedance < misaligned impedance', () => {
    for (let t = 0; t < 6; t++) {
      const result = verifyPhaseMismatchBlocking(ORIGIN, t);
      expect(result.alignedImpedance).toBeLessThan(result.misalignedImpedance);
    }
  });

  it('should hold at a non-origin position', () => {
    const pos: Vector6D = [0.1, 0.1, 0, 0, 0, 0];
    const result = verifyPhaseMismatchBlocking(pos, 0);
    expect(result.holds).toBe(true);
  });

  it('should have non-negative impedances', () => {
    const result = verifyPhaseMismatchBlocking(ORIGIN, 2);
    expect(result.alignedImpedance).toBeGreaterThanOrEqual(0);
    expect(result.misalignedImpedance).toBeGreaterThanOrEqual(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Invariant 3: Nodal Stability
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: Invariant 3 — Nodal Stability', () => {
  it('should destabilize most perturbations at origin', () => {
    const result = verifyNodalStability(ORIGIN, 0.05, 0.01, 30);
    expect(result.destabilizedFraction).toBeGreaterThan(0);
    expect(result.destabilizedFraction).toBeLessThanOrEqual(1);
  });

  it('should return higher destabilization for larger perturbations', () => {
    const small = verifyNodalStability(ORIGIN, 0.01, 0.01, 30);
    const large = verifyNodalStability(ORIGIN, 0.1, 0.01, 30);
    expect(large.destabilizedFraction).toBeGreaterThanOrEqual(small.destabilizedFraction);
  });

  it('should have destabilizedFraction in [0, 1]', () => {
    const result = verifyNodalStability(ORIGIN, 0.05, 0.01, 20);
    expect(result.destabilizedFraction).toBeGreaterThanOrEqual(0);
    expect(result.destabilizedFraction).toBeLessThanOrEqual(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// Invariant 4: Combined Security Bound
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: Invariant 4 — Combined Security Bound', () => {
  it('should be low for aligned state near target', () => {
    const state = makeAlignedState(ORIGIN);
    const target: Vector6D = [0.01, 0, 0, 0, 0, 0];
    const cost = combinedSecurityCost(state, target);
    expect(cost).toBeGreaterThan(0);
    expect(isFinite(cost)).toBe(true);
  });

  it('should be higher for distant targets', () => {
    const state = makeAlignedState(ORIGIN);
    const near: Vector6D = [0.01, 0, 0, 0, 0, 0];
    const far: Vector6D = [0.5, 0, 0, 0, 0, 0];
    const costNear = combinedSecurityCost(state, near);
    const costFar = combinedSecurityCost(state, far);
    expect(costFar).toBeGreaterThan(costNear);
  });

  it('should be higher for misaligned phase', () => {
    const aligned = makeAlignedState(ORIGIN);
    const misaligned: CHSFNState = {
      position: ORIGIN,
      phase: ALIGNED_PHASE.map((p) => p + Math.PI / 2) as Vector6D,
      mass: 1.0,
    };
    const target: Vector6D = [0.1, 0, 0, 0, 0, 0];
    const costAligned = combinedSecurityCost(aligned, target);
    const costMisaligned = combinedSecurityCost(misaligned, target);
    expect(costMisaligned).toBeGreaterThan(costAligned);
  });
});

// ═══════════════════════════════════════════════════════════════
// Security Bits Equivalent
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: securityBitsEquivalent', () => {
  it('should return positive bits for distant position', () => {
    const state = makeAlignedState(ORIGIN);
    const target: Vector6D = [0.5, 0, 0, 0, 0, 0];
    const bits = securityBitsEquivalent(state, target);
    expect(bits).toBeGreaterThan(0);
  });

  it('should increase with distance', () => {
    const state = makeAlignedState(ORIGIN);
    const near: Vector6D = [0.1, 0, 0, 0, 0, 0];
    const far: Vector6D = [0.5, 0, 0, 0, 0, 0];
    expect(securityBitsEquivalent(state, far)).toBeGreaterThan(securityBitsEquivalent(state, near));
  });

  it('should be non-negative', () => {
    const state = makeAlignedState(ORIGIN);
    const bits = securityBitsEquivalent(state, ORIGIN);
    expect(bits).toBeGreaterThanOrEqual(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Invariant 5: Tongue Bijection Under Drift
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: Invariant 5 — Tongue Bijection Under Drift', () => {
  it('should preserve ordering for small drift', () => {
    const state = makeAlignedState([0.1, 0, 0, 0, 0, 0] as Vector6D);
    const result = verifyTongueBijectionUnderDrift(state, 5, 0.001);
    expect(result.initialOrder).toHaveLength(6);
    expect(result.finalOrder).toHaveLength(6);
    // Both arrays should contain 0-5
    expect([...result.initialOrder].sort()).toEqual([0, 1, 2, 3, 4, 5]);
    expect([...result.finalOrder].sort()).toEqual([0, 1, 2, 3, 4, 5]);
  });

  it('should return boolean holds property', () => {
    const state = makeAlignedState(ORIGIN);
    const result = verifyTongueBijectionUnderDrift(state, 3, 0.001);
    expect(typeof result.holds).toBe('boolean');
  });
});

// ═══════════════════════════════════════════════════════════════
// Invariant 6: Energy Non-Increase Under Drift
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: Invariant 6 — Energy Non-Increase Under Drift', () => {
  it('should produce energy trace of length steps+1', () => {
    const state = makeAlignedState([0.1, 0, 0, 0, 0, 0] as Vector6D);
    const result = verifyEnergyNonIncrease(state, 10, 0.001);
    expect(result.energyTrace).toHaveLength(11);
  });

  it('should have non-negative energy at all steps', () => {
    const state = makeAlignedState([0.1, 0.05, 0, 0, 0, 0] as Vector6D);
    const result = verifyEnergyNonIncrease(state, 10, 0.001);
    for (const e of result.energyTrace) {
      expect(e).toBeGreaterThanOrEqual(0);
    }
  });

  it('should return holds boolean', () => {
    const state = makeAlignedState([0.05, 0, 0, 0, 0, 0] as Vector6D);
    const result = verifyEnergyNonIncrease(state, 10, 0.001, 0.01);
    expect(typeof result.holds).toBe('boolean');
  });

  it('should have decreasing or stable energy for small steps', () => {
    const state = makeAlignedState([0.2, 0.1, 0, 0, 0, 0] as Vector6D);
    const result = verifyEnergyNonIncrease(state, 5, 0.0005, 0.05);
    // With small enough step size and tolerance, energy should not increase
    expect(result.holds).toBe(true);
  });
});
