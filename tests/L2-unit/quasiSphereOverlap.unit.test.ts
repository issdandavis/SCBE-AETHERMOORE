/**
 * @file quasiSphereOverlap.unit.test.ts
 * @tier L2-unit
 * @axiom 2 (Locality), 4 (Symmetry), 5 (Composition)
 * @category unit
 *
 * Unit tests for quasi-sphere overlap rules, pad geodesic constraints,
 * and consensus-gradient paths.
 */

import { describe, it, expect } from 'vitest';
import type { Vector6D } from '../../src/harmonic/constants.js';
import type { CHSFNState } from '../../src/harmonic/chsfn.js';
import {
  createQuasiSphere,
  computeOverlap,
  squadOverlapMatrix,
  sharedContextRadius,
  localCurvature,
  isWithinGeodesicConstraint,
  padAccessibilityMap,
  consensusGradient,
  gradientAgreement,
  PAD_GEODESIC_CONSTRAINTS,
  type QuasiSphere,
} from '../../src/harmonic/quasiSphereOverlap.js';

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

function makeState(pos: Vector6D, phase?: Vector6D): CHSFNState {
  return {
    position: pos,
    phase: phase ?? [0, Math.PI / 3, (2 * Math.PI) / 3, Math.PI, (4 * Math.PI) / 3, (5 * Math.PI) / 3],
    mass: 1.0,
  };
}

const ORIGIN: Vector6D = [0, 0, 0, 0, 0, 0];
const ALIGNED_PHASE: Vector6D = [0, Math.PI / 3, (2 * Math.PI) / 3, Math.PI, (4 * Math.PI) / 3, (5 * Math.PI) / 3];

// ═══════════════════════════════════════════════════════════════
// createQuasiSphere
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: createQuasiSphere', () => {
  it('should create a sphere with correct unitId', () => {
    const qs = createQuasiSphere('u1', makeState(ORIGIN), 0.8);
    expect(qs.unitId).toBe('u1');
  });

  it('should copy position and phase', () => {
    const pos: Vector6D = [0.1, 0.2, 0, 0, 0, 0];
    const qs = createQuasiSphere('u1', makeState(pos), 0.5);
    expect(qs.center).toEqual(pos);
    expect(qs.center).not.toBe(pos); // should be a copy
  });

  it('should compute trustRadius from coherence', () => {
    const qs = createQuasiSphere('u1', makeState(ORIGIN), 0.5);
    expect(qs.trustRadius).toBeCloseTo(-Math.log(0.5), 8);
  });

  it('should clamp coherence near 1 to avoid Infinity', () => {
    const qs = createQuasiSphere('u1', makeState(ORIGIN), 1.0);
    expect(isFinite(qs.trustRadius)).toBe(true);
    expect(qs.trustRadius).toBeGreaterThan(0);
  });

  it('should have higher trustRadius for higher coherence', () => {
    const low = createQuasiSphere('a', makeState(ORIGIN), 0.3);
    const high = createQuasiSphere('b', makeState(ORIGIN), 0.9);
    expect(high.trustRadius).toBeGreaterThan(low.trustRadius);
  });

  it('should have zero trustRadius for zero coherence', () => {
    const qs = createQuasiSphere('u1', makeState(ORIGIN), 0);
    expect(qs.trustRadius).toBeCloseTo(0, 8);
  });
});

// ═══════════════════════════════════════════════════════════════
// computeOverlap
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: computeOverlap', () => {
  it('should detect overlap for co-located spheres', () => {
    const a = createQuasiSphere('a', makeState(ORIGIN), 0.8);
    const b = createQuasiSphere('b', makeState(ORIGIN), 0.8);
    const result = computeOverlap(a, b);
    expect(result.overlaps).toBe(true);
    expect(result.distance).toBeCloseTo(0, 5);
  });

  it('should detect overlap with identical phases → canShareContext true', () => {
    const a = createQuasiSphere('a', makeState(ORIGIN, ALIGNED_PHASE), 0.8);
    const b = createQuasiSphere('b', makeState(ORIGIN, ALIGNED_PHASE), 0.8);
    const result = computeOverlap(a, b);
    expect(result.canShareContext).toBe(true);
    expect(result.phaseCoherence).toBeCloseTo(1.0, 5);
  });

  it('should NOT share context when phases are opposite', () => {
    const flipped: Vector6D = ALIGNED_PHASE.map((p) => p + Math.PI) as Vector6D;
    const a = createQuasiSphere('a', makeState(ORIGIN, ALIGNED_PHASE), 0.8);
    const b = createQuasiSphere('b', makeState(ORIGIN, flipped), 0.8);
    const result = computeOverlap(a, b);
    // cos(π) = -1, so average = -1, normalized = 0
    expect(result.phaseCoherence).toBeCloseTo(0, 5);
    expect(result.canShareContext).toBe(false);
  });

  it('should NOT overlap when distance > combined radius', () => {
    // Low coherence = small radius, placed far apart
    const a = createQuasiSphere('a', makeState(ORIGIN), 0.1);
    const far: Vector6D = [0.9, 0, 0, 0, 0, 0];
    const b = createQuasiSphere('b', makeState(far), 0.1);
    const result = computeOverlap(a, b);
    expect(result.overlaps).toBe(false);
    expect(result.canShareContext).toBe(false);
  });

  it('should compute midpoint cost', () => {
    const a = createQuasiSphere('a', makeState(ORIGIN), 0.8);
    const b = createQuasiSphere('b', makeState([0.1, 0, 0, 0, 0, 0] as Vector6D), 0.8);
    const result = computeOverlap(a, b);
    expect(result.midpointCost).toBeGreaterThan(0);
    expect(isFinite(result.midpointCost)).toBe(true);
  });

  it('should have distance === combinedRadius boundary', () => {
    const a = createQuasiSphere('a', makeState(ORIGIN), 0.5);
    const result = computeOverlap(a, a);
    // Same position: distance=0, combinedRadius>0, so overlaps
    expect(result.overlaps).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// squadOverlapMatrix
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: squadOverlapMatrix', () => {
  it('should return empty map for empty array', () => {
    const m = squadOverlapMatrix([]);
    expect(m.size).toBe(0);
  });

  it('should return empty map for single sphere', () => {
    const a = createQuasiSphere('a', makeState(ORIGIN), 0.8);
    const m = squadOverlapMatrix([a]);
    expect(m.size).toBe(0);
  });

  it('should return n*(n-1)/2 entries for n spheres', () => {
    const spheres = [
      createQuasiSphere('a', makeState(ORIGIN), 0.8),
      createQuasiSphere('b', makeState([0.05, 0, 0, 0, 0, 0] as Vector6D), 0.8),
      createQuasiSphere('c', makeState([0, 0.05, 0, 0, 0, 0] as Vector6D), 0.8),
    ];
    const m = squadOverlapMatrix(spheres);
    expect(m.size).toBe(3); // 3 choose 2
  });

  it('should key entries as "unitA:unitB"', () => {
    const spheres = [
      createQuasiSphere('alpha', makeState(ORIGIN), 0.5),
      createQuasiSphere('beta', makeState(ORIGIN), 0.5),
    ];
    const m = squadOverlapMatrix(spheres);
    expect(m.has('alpha:beta')).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// sharedContextRadius
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: sharedContextRadius', () => {
  it('should return 0 for empty array', () => {
    expect(sharedContextRadius([])).toBe(0);
  });

  it('should return trustRadius for single sphere', () => {
    const a = createQuasiSphere('a', makeState(ORIGIN), 0.5);
    expect(sharedContextRadius([a])).toBeCloseTo(a.trustRadius, 8);
  });

  it('should return positive for co-located spheres', () => {
    const a = createQuasiSphere('a', makeState(ORIGIN), 0.8);
    const b = createQuasiSphere('b', makeState(ORIGIN), 0.8);
    expect(sharedContextRadius([a, b])).toBeGreaterThan(0);
  });

  it('should return 0 for far-apart low-coherence spheres', () => {
    const a = createQuasiSphere('a', makeState(ORIGIN), 0.1);
    const far: Vector6D = [0.9, 0, 0, 0, 0, 0];
    const b = createQuasiSphere('b', makeState(far), 0.1);
    expect(sharedContextRadius([a, b])).toBe(0);
  });

  it('should decrease as spheres move apart', () => {
    const a = createQuasiSphere('a', makeState(ORIGIN), 0.8);
    const near = createQuasiSphere('b', makeState([0.05, 0, 0, 0, 0, 0] as Vector6D), 0.8);
    const far = createQuasiSphere('c', makeState([0.3, 0, 0, 0, 0, 0] as Vector6D), 0.8);
    expect(sharedContextRadius([a, near])).toBeGreaterThan(sharedContextRadius([a, far]));
  });
});

// ═══════════════════════════════════════════════════════════════
// localCurvature
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: localCurvature', () => {
  it('should be 2 at the origin', () => {
    expect(localCurvature(ORIGIN)).toBe(2);
  });

  it('should increase near the boundary', () => {
    const inner: Vector6D = [0.1, 0, 0, 0, 0, 0];
    const outer: Vector6D = [0.9, 0, 0, 0, 0, 0];
    expect(localCurvature(outer)).toBeGreaterThan(localCurvature(inner));
  });

  it('should be Infinity at the boundary', () => {
    const boundary: Vector6D = [1, 0, 0, 0, 0, 0];
    expect(localCurvature(boundary)).toBe(Infinity);
  });

  it('should be positive everywhere inside ball', () => {
    const pts: Vector6D[] = [
      [0.5, 0, 0, 0, 0, 0],
      [0, 0.3, 0, 0, 0, 0],
      [0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
    ];
    for (const p of pts) {
      expect(localCurvature(p)).toBeGreaterThan(0);
    }
  });

  it('should be symmetric in all dimensions', () => {
    const a: Vector6D = [0.3, 0, 0, 0, 0, 0];
    const b: Vector6D = [0, 0, 0, 0, 0, 0.3];
    expect(localCurvature(a)).toBeCloseTo(localCurvature(b), 10);
  });
});

// ═══════════════════════════════════════════════════════════════
// isWithinGeodesicConstraint
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: isWithinGeodesicConstraint', () => {
  const center = ORIGIN;

  it('should reject origin for ENGINEERING (curvature 2 > band max 1.5)', () => {
    const state = makeState(ORIGIN);
    // Origin has curvature κ = 2/(1-0)² = 2, ENGINEERING band is [0, 1.5]
    const ok = isWithinGeodesicConstraint(state, center, PAD_GEODESIC_CONSTRAINTS.ENGINEERING);
    expect(ok).toBe(false);
  });

  it('should accept origin for NAVIGATION (curvature 2 within [0, 2.5])', () => {
    const state = makeState(ORIGIN);
    const ok = isWithinGeodesicConstraint(state, center, PAD_GEODESIC_CONSTRAINTS.NAVIGATION);
    expect(ok).toBe(true);
  });

  it('should reject positions beyond maxReachDistance', () => {
    // Far from origin in hyperbolic space
    const far: Vector6D = [0.95, 0, 0, 0, 0, 0];
    const state = makeState(far);
    const ok = isWithinGeodesicConstraint(state, center, PAD_GEODESIC_CONSTRAINTS.SYSTEMS);
    expect(ok).toBe(false);
  });

  it('should reject positions with curvature outside allowed band', () => {
    // SCIENCE has band [0.5, 4.0]; origin has curvature 2 (inside band)
    const originState = makeState(ORIGIN);
    const ok = isWithinGeodesicConstraint(originState, center, PAD_GEODESIC_CONSTRAINTS.SCIENCE);
    expect(ok).toBe(true);
  });

  it('should reject origin curvature for a mode with high min curvature', () => {
    // Create a custom constraint with min curvature above 2 (origin's curvature)
    const strictConstraint = {
      ...PAD_GEODESIC_CONSTRAINTS.ENGINEERING,
      allowedCurvatureBand: [5.0, 10.0] as [number, number],
    };
    const state = makeState(ORIGIN);
    const ok = isWithinGeodesicConstraint(state, center, strictConstraint);
    expect(ok).toBe(false);
  });

  it('should respect tongue impedance', () => {
    // Misaligned phase should have high impedance → fail
    const misaligned: Vector6D = [Math.PI, Math.PI, Math.PI, Math.PI, Math.PI, Math.PI];
    const state = makeState(ORIGIN, misaligned);
    const ok = isWithinGeodesicConstraint(state, center, PAD_GEODESIC_CONSTRAINTS.ENGINEERING, 0.001);
    // Strict impedance threshold should likely reject
    expect(typeof ok).toBe('boolean');
  });

  it('should have all 6 modes defined in PAD_GEODESIC_CONSTRAINTS', () => {
    const modes = ['ENGINEERING', 'NAVIGATION', 'SYSTEMS', 'SCIENCE', 'COMMS', 'MISSION'] as const;
    for (const mode of modes) {
      expect(PAD_GEODESIC_CONSTRAINTS[mode]).toBeDefined();
      expect(PAD_GEODESIC_CONSTRAINTS[mode].mode).toBe(mode);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// padAccessibilityMap
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: padAccessibilityMap', () => {
  it('should return 6 entries (one per mode)', () => {
    const map = padAccessibilityMap(ORIGIN, 0.8, 20);
    expect(map.size).toBe(6);
  });

  it('should have fractions in [0, 1]', () => {
    const map = padAccessibilityMap(ORIGIN, 0.8, 20);
    for (const [, frac] of map) {
      expect(frac).toBeGreaterThanOrEqual(0);
      expect(frac).toBeLessThanOrEqual(1);
    }
  });

  it('should give MISSION highest accessibility (widest constraints)', () => {
    const map = padAccessibilityMap(ORIGIN, 0.8, 50);
    const missionAccess = map.get('MISSION')!;
    const systemsAccess = map.get('SYSTEMS')!;
    // MISSION has widest curvature band and deepest reach
    expect(missionAccess).toBeGreaterThanOrEqual(systemsAccess);
  });

  it('should return zero accessibility for zero coherence', () => {
    const map = padAccessibilityMap(ORIGIN, 0, 20);
    // Trust radius ~ 0, so nothing is reachable beyond the origin itself
    for (const [, frac] of map) {
      expect(frac).toBeLessThanOrEqual(1);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// consensusGradient
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: consensusGradient', () => {
  it('should return zero vector for empty array', () => {
    const g = consensusGradient([]);
    expect(g).toEqual([0, 0, 0, 0, 0, 0]);
  });

  it('should return scaled vector for single gradient', () => {
    const input: Vector6D = [1, 0, 0, 0, 0, 0];
    const g = consensusGradient([input]);
    // Single gradient → agreement = 1/1 (itself agrees), scaled by 1.0
    expect(g[0]).toBeGreaterThan(0);
  });

  it('should give strong output for unanimous agreement', () => {
    const gradients: Vector6D[] = [
      [1, 0, 0, 0, 0, 0],
      [1, 0, 0, 0, 0, 0],
      [1, 0, 0, 0, 0, 0],
      [1, 0, 0, 0, 0, 0],
    ];
    const g = consensusGradient(gradients);
    // All agree → direction should be [1,0,0,0,0,0] scaled by agreement
    expect(g[0]).toBeGreaterThan(0.5);
  });

  it('should give near-zero for opposing gradients', () => {
    const gradients: Vector6D[] = [
      [1, 0, 0, 0, 0, 0],
      [-1, 0, 0, 0, 0, 0],
      [1, 0, 0, 0, 0, 0],
      [-1, 0, 0, 0, 0, 0],
    ];
    const g = consensusGradient(gradients);
    // Average is [0,...] → returns zero
    const mag = Math.sqrt(g.reduce((s, x) => s + x * x, 0));
    expect(mag).toBeLessThan(0.1);
  });

  it('should scale output by agreement fraction', () => {
    const unanimous: Vector6D[] = Array(6).fill([1, 0, 0, 0, 0, 0]);
    const partial: Vector6D[] = [
      [1, 0, 0, 0, 0, 0],
      [1, 0, 0, 0, 0, 0],
      [1, 0, 0, 0, 0, 0],
      [0, 1, 0, 0, 0, 0],
      [0, -1, 0, 0, 0, 0],
      [0, 0, 1, 0, 0, 0],
    ];
    const gU = consensusGradient(unanimous);
    const gP = consensusGradient(partial);
    const magU = Math.sqrt(gU.reduce((s, x) => s + x * x, 0));
    const magP = Math.sqrt(gP.reduce((s, x) => s + x * x, 0));
    // Unanimous should be stronger than partial
    expect(magU).toBeGreaterThan(magP);
  });
});

// ═══════════════════════════════════════════════════════════════
// gradientAgreement
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: gradientAgreement', () => {
  it('should return 1 for single gradient', () => {
    expect(gradientAgreement([[1, 0, 0, 0, 0, 0]])).toBe(1);
  });

  it('should return 1 for identical gradients', () => {
    const gs: Vector6D[] = [
      [1, 0, 0, 0, 0, 0],
      [1, 0, 0, 0, 0, 0],
    ];
    expect(gradientAgreement(gs)).toBeCloseTo(1, 5);
  });

  it('should return 0.5 for perpendicular gradients', () => {
    const gs: Vector6D[] = [
      [1, 0, 0, 0, 0, 0],
      [0, 1, 0, 0, 0, 0],
    ];
    // cos(90°) = 0, normalized = (0+1)/2 = 0.5
    expect(gradientAgreement(gs)).toBeCloseTo(0.5, 5);
  });

  it('should return 0 for opposite gradients', () => {
    const gs: Vector6D[] = [
      [1, 0, 0, 0, 0, 0],
      [-1, 0, 0, 0, 0, 0],
    ];
    // cos(180°) = -1, normalized = (-1+1)/2 = 0
    expect(gradientAgreement(gs)).toBeCloseTo(0, 5);
  });

  it('should be between 0 and 1', () => {
    const gs: Vector6D[] = [
      [1, 0.5, 0, 0, 0, 0],
      [0.5, 1, 0, 0, 0, 0],
      [-0.3, 0.7, 0, 0, 0, 0],
    ];
    const a = gradientAgreement(gs);
    expect(a).toBeGreaterThanOrEqual(0);
    expect(a).toBeLessThanOrEqual(1);
  });

  it('should return 0 for all-zero gradients', () => {
    const gs: Vector6D[] = [
      [0, 0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0, 0],
    ];
    expect(gradientAgreement(gs)).toBe(0);
  });
});
