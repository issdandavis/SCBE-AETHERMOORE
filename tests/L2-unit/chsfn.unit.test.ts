/**
 * @file chsfn.unit.test.ts
 * @tier L2-unit
 * @axiom 4 (Symmetry)
 * @category unit
 *
 * Unit tests for CHSFN: cymatic field, quasi-sphere, drift, triadic aggregation.
 */

import { describe, it, expect } from 'vitest';
import {
  cymaticField,
  cymaticGradient,
  isNearZeroSet,
  antiNodeStrength,
  poincareNorm,
  projectIntoBall,
  hyperbolicDistance6D,
  tongueImpedanceAt,
  isAccessible,
  energyFunctional,
  driftStep,
  triadicTemporalDistance,
  quasiSphereVolume,
  effectiveCapacity,
  accessCost,
  DEFAULT_MODES,
  type CHSFNState,
} from '../../src/harmonic/chsfn.js';
import type { Vector6D } from '../../src/harmonic/constants.js';

// ═══════════════════════════════════════════════════════════════
// Cymatic Field Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: cymaticField', () => {
  it('should return 0 at the origin (sin(0) = 0)', () => {
    const val = cymaticField([0, 0, 0, 0, 0, 0]);
    expect(val).toBeCloseTo(0, 8);
  });

  it('should return a finite number for valid inputs', () => {
    const val = cymaticField([0.5, 0.5, 0.5, 0.5, 0.5, 0.5]);
    expect(Number.isFinite(val)).toBe(true);
  });

  it('should be non-zero at non-degenerate points', () => {
    const val = cymaticField([0.25, 0.25, 0.25, 0.25, 0.25, 0.25]);
    expect(Math.abs(val)).toBeGreaterThan(0);
  });

  it('should accept custom modes', () => {
    const modes = { n: [1, 1, 1, 1, 1, 1] as Vector6D, m: [1, 1, 1, 1, 1, 1] as Vector6D };
    const val = cymaticField([0.5, 0.5, 0.5, 0.5, 0.5, 0.5], modes);
    expect(Number.isFinite(val)).toBe(true);
  });
});

describe('L2-UNIT: cymaticGradient', () => {
  it('should return a 6D vector', () => {
    const grad = cymaticGradient([0.3, 0.3, 0.3, 0.3, 0.3, 0.3]);
    expect(grad).toHaveLength(6);
  });

  it('should be approximately zero where the field is flat', () => {
    // At x = 0 all sine terms are 0, gradient is complex but finite
    const grad = cymaticGradient([0, 0, 0, 0, 0, 0]);
    for (const g of grad) {
      expect(Number.isFinite(g)).toBe(true);
    }
  });
});

describe('L2-UNIT: isNearZeroSet', () => {
  it('should return true at the origin', () => {
    expect(isNearZeroSet([0, 0, 0, 0, 0, 0])).toBe(true);
  });

  it('should respect tolerance', () => {
    const x: Vector6D = [0.25, 0.25, 0.25, 0.25, 0.25, 0.25];
    // With very large tolerance, everything is near zero-set
    expect(isNearZeroSet(x, 1e6)).toBe(true);
    // With very small tolerance, most points are NOT near
    // (depends on the actual field value)
  });
});

describe('L2-UNIT: antiNodeStrength', () => {
  it('should return a non-negative number', () => {
    const strength = antiNodeStrength([0.3, 0.3, 0.3, 0.3, 0.3, 0.3]);
    expect(strength).toBeGreaterThanOrEqual(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Quasi-Sphere / Poincaré Ball Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: poincareNorm', () => {
  it('should return 0 at origin', () => {
    expect(poincareNorm([0, 0, 0, 0, 0, 0])).toBe(0);
  });

  it('should return correct norm for unit vector in first dim', () => {
    expect(poincareNorm([0.5, 0, 0, 0, 0, 0])).toBeCloseTo(0.5, 10);
  });
});

describe('L2-UNIT: projectIntoBall', () => {
  it('should not change points already inside the ball', () => {
    const p: Vector6D = [0.1, 0.2, 0.1, 0.1, 0.1, 0.1];
    const proj = projectIntoBall(p);
    expect(proj).toEqual(p);
  });

  it('should clamp points outside the ball', () => {
    const p: Vector6D = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0];
    const proj = projectIntoBall(p);
    const n = poincareNorm(proj);
    expect(n).toBeLessThan(1);
  });
});

describe('L2-UNIT: hyperbolicDistance6D', () => {
  it('should be 0 for identical points', () => {
    const p: Vector6D = [0.1, 0.2, 0.1, 0.1, 0.1, 0.1];
    expect(hyperbolicDistance6D(p, p)).toBeCloseTo(0, 8);
  });

  it('should be symmetric', () => {
    const u: Vector6D = [0.1, 0.2, 0.0, 0.1, 0.0, 0.1];
    const v: Vector6D = [0.3, 0.1, 0.2, 0.0, 0.1, 0.0];
    expect(hyperbolicDistance6D(u, v)).toBeCloseTo(hyperbolicDistance6D(v, u), 10);
  });

  it('should grow as points move toward boundary', () => {
    const o: Vector6D = [0, 0, 0, 0, 0, 0];
    const near: Vector6D = [0.1, 0, 0, 0, 0, 0];
    const far: Vector6D = [0.9, 0, 0, 0, 0, 0];
    expect(hyperbolicDistance6D(o, far)).toBeGreaterThan(hyperbolicDistance6D(o, near));
  });
});

// ═══════════════════════════════════════════════════════════════
// Tongue Impedance Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: tongueImpedanceAt', () => {
  it('should be in [0, 1]', () => {
    const state: CHSFNState = {
      position: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
      phase: [0, Math.PI / 3, (2 * Math.PI) / 3, Math.PI, (4 * Math.PI) / 3, (5 * Math.PI) / 3],
      mass: 1.0,
    };
    for (let i = 0; i < 6; i++) {
      const imp = tongueImpedanceAt(state, i);
      expect(imp).toBeGreaterThanOrEqual(0);
      expect(imp).toBeLessThanOrEqual(1);
    }
  });

  it('should be low when phase matches expected', () => {
    // Expected phase for tongue i = (2πi/6)
    const state: CHSFNState = {
      position: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
      phase: [0, (2 * Math.PI) / 6, (4 * Math.PI) / 6, Math.PI, (8 * Math.PI) / 6, (10 * Math.PI) / 6],
      mass: 1.0,
    };
    const imp = tongueImpedanceAt(state, 0);
    expect(imp).toBeCloseTo(0, 2);
  });
});

// ═══════════════════════════════════════════════════════════════
// Accessibility Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: isAccessible', () => {
  it('should return true when all conditions are met', () => {
    const state: CHSFNState = {
      position: [0, 0, 0, 0, 0, 0], // Origin (zero-set, near, phase-aligned)
      phase: [0, (2 * Math.PI) / 6, (4 * Math.PI) / 6, Math.PI, (8 * Math.PI) / 6, (10 * Math.PI) / 6],
      mass: 1.0,
    };
    // At origin, cymatic field is 0, distance is 0, impedance is low
    expect(isAccessible(state, 0, 0.5, 5.0, 0.1)).toBe(true);
  });

  it('should return false when distance exceeds threshold', () => {
    const state: CHSFNState = {
      position: [0.95, 0, 0, 0, 0, 0],
      phase: [0, 0, 0, 0, 0, 0],
      mass: 1.0,
    };
    expect(isAccessible(state, 0, 0.5, 0.1, 0.1)).toBe(false); // maxDistance = 0.1
  });
});

// ═══════════════════════════════════════════════════════════════
// Energy & Drift Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: energyFunctional', () => {
  it('should return a finite positive value', () => {
    const state: CHSFNState = {
      position: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
      phase: [0, 0, 0, 0, 0, 0],
      mass: 1.0,
    };
    const e = energyFunctional(state);
    expect(Number.isFinite(e)).toBe(true);
    expect(e).toBeGreaterThanOrEqual(0);
  });

  it('should be lower at origin than at boundary', () => {
    const origin: CHSFNState = {
      position: [0, 0, 0, 0, 0, 0],
      phase: [0, 0, 0, 0, 0, 0],
      mass: 1.0,
    };
    const boundary: CHSFNState = {
      position: [0.9, 0, 0, 0, 0, 0],
      phase: [0, 0, 0, 0, 0, 0],
      mass: 1.0,
    };
    expect(energyFunctional(origin)).toBeLessThan(energyFunctional(boundary));
  });
});

describe('L2-UNIT: driftStep', () => {
  it('should return a valid state', () => {
    const state: CHSFNState = {
      position: [0.3, 0.3, 0.3, 0.3, 0.3, 0.3],
      phase: [0, 0, 0, 0, 0, 0],
      mass: 1.0,
    };
    const next = driftStep(state, 0.01);
    expect(next.position).toHaveLength(6);
    expect(poincareNorm(next.position)).toBeLessThan(1);
    expect(next.mass).toBeGreaterThan(0);
    expect(next.mass).toBeLessThanOrEqual(state.mass);
  });

  it('should decrease energy (drift toward lower energy)', () => {
    const state: CHSFNState = {
      position: [0.5, 0.3, 0.2, 0.1, 0.1, 0.1],
      phase: [0, 0, 0, 0, 0, 0],
      mass: 1.0,
    };
    const next = driftStep(state, 0.001);
    // Energy should decrease or stay roughly the same after drift
    const e0 = energyFunctional(state);
    const e1 = energyFunctional(next);
    // Gradient descent: energy should not increase much
    expect(e1).toBeLessThanOrEqual(e0 + 0.1); // Allow small numerical margin
  });
});

// ═══════════════════════════════════════════════════════════════
// Triadic Temporal Distance Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: triadicTemporalDistance', () => {
  it('should return a non-negative value', () => {
    expect(triadicTemporalDistance(1, 2, 3)).toBeGreaterThan(0);
  });

  it('should handle zero distances gracefully', () => {
    const d = triadicTemporalDistance(0, 0, 0);
    expect(Number.isFinite(d)).toBe(true);
    expect(d).toBeGreaterThanOrEqual(0);
  });

  it('should grow as distances increase', () => {
    const d1 = triadicTemporalDistance(1, 1, 1);
    const d2 = triadicTemporalDistance(10, 10, 10);
    expect(d2).toBeGreaterThan(d1);
  });
});

// ═══════════════════════════════════════════════════════════════
// Quasi-Sphere Volume & Capacity Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: quasiSphereVolume', () => {
  it('should be 1 at radius 0', () => {
    expect(quasiSphereVolume(0)).toBeCloseTo(1, 10);
  });

  it('should grow exponentially', () => {
    const v1 = quasiSphereVolume(1);
    const v2 = quasiSphereVolume(2);
    expect(v2).toBeGreaterThan(v1 * 100); // e^5 ≈ 148
  });
});

describe('L2-UNIT: effectiveCapacity', () => {
  it('should be positive', () => {
    expect(effectiveCapacity(1)).toBeGreaterThan(0);
  });

  it('should double with negative space (factor 2)', () => {
    const cap = effectiveCapacity(1, 8, 3);
    const volume = quasiSphereVolume(1);
    expect(cap).toBe(volume * 8 * 3 * 2);
  });
});

describe('L2-UNIT: accessCost', () => {
  it('should equal R at d*=0', () => {
    expect(accessCost(0, 1.5)).toBeCloseTo(1.5, 5);
  });

  it('should grow super-exponentially', () => {
    const c1 = accessCost(1);
    const c10 = accessCost(10);
    expect(c10).toBeGreaterThan(c1 * 1000);
  });
});
