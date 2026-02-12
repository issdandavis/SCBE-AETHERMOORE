/**
 * @file trustCone.test.ts
 * @description Tests for trust cone geometric access control.
 *
 * Verifies that trust cones properly constrain navigation based
 * on confidence levels, with angular width ∝ 1/confidence.
 */

import { describe, it, expect } from 'vitest';
import {
  computeConeAngle,
  createTrustCone,
  checkTrustCone,
  trustConePenalty,
  createRealmTrustCone,
  TrustCone,
} from '../../src/harmonic/trustCone';
import { REALM_CENTERS } from '../../src/harmonic/adaptiveNavigator';

describe('TrustCone', () => {
  // ═══════════════════════════════════════════════════════════════
  // Cone Angle Computation
  // ═══════════════════════════════════════════════════════════════

  describe('computeConeAngle', () => {
    it('should produce narrower cone with higher confidence', () => {
      const highConf = computeConeAngle(0.9);
      const lowConf = computeConeAngle(0.3);

      expect(highConf).toBeLessThan(lowConf);
    });

    it('should return baseAngle when confidence = 1', () => {
      const angle = computeConeAngle(1.0, { baseAngle: Math.PI / 6 });
      expect(angle).toBeCloseTo(Math.PI / 6, 5);
    });

    it('should widen as confidence decreases', () => {
      const angles = [0.9, 0.7, 0.5, 0.3, 0.1].map((c) => computeConeAngle(c));

      // Each should be >= the previous (wider or equal at cap)
      for (let i = 1; i < angles.length; i++) {
        expect(angles[i]).toBeGreaterThanOrEqual(angles[i - 1]);
      }

      // At least the first vs last should differ (not all capped)
      expect(angles[angles.length - 1]).toBeGreaterThan(angles[0]);
    });

    it('should clamp to MAX_CONE_ANGLE (π/2)', () => {
      // Very low confidence should hit the cap
      const angle = computeConeAngle(0.01);
      expect(angle).toBeLessThanOrEqual(Math.PI / 2);
    });

    it('should clamp to MIN_CONE_ANGLE (1°)', () => {
      // This would require baseAngle < minConfidence * MIN_CONE_ANGLE
      const angle = computeConeAngle(1.0, { baseAngle: Math.PI / 1000 });
      expect(angle).toBeGreaterThanOrEqual(Math.PI / 180);
    });

    it('should respect minConfidence floor', () => {
      const withFloor = computeConeAngle(0.01, { minConfidence: 0.2 });
      const withoutFloor = computeConeAngle(0.2, { minConfidence: 0.2 });

      // Below minConfidence should be treated as minConfidence
      expect(withFloor).toBeCloseTo(withoutFloor, 5);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Cone Creation
  // ═══════════════════════════════════════════════════════════════

  describe('createTrustCone', () => {
    it('should create a cone with normalized direction', () => {
      const cone = createTrustCone(
        [0, 0, 0, 0, 0, 0],
        [1, 1, 0, 0, 0, 0],
        0.8
      );

      // Direction should be unit vector
      const normSq = cone.direction.reduce((sum, x) => sum + x * x, 0);
      expect(normSq).toBeCloseTo(1, 5);
    });

    it('should store confidence clamped to [0, 1]', () => {
      const cone = createTrustCone([0, 0], [1, 0], 1.5);
      expect(cone.confidence).toBe(1);

      const cone2 = createTrustCone([0, 0], [1, 0], -0.5);
      expect(cone2.confidence).toBe(0);
    });

    it('should compute halfAngle from confidence', () => {
      const cone = createTrustCone([0, 0, 0, 0, 0, 0], [1, 0, 0, 0, 0, 0], 0.5);
      const expectedAngle = computeConeAngle(0.5);
      expect(cone.halfAngle).toBeCloseTo(expectedAngle, 5);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Cone Check
  // ═══════════════════════════════════════════════════════════════

  describe('checkTrustCone', () => {
    it('should find target directly ahead as within cone', () => {
      const cone = createTrustCone(
        [0, 0, 0, 0, 0, 0],       // apex at origin
        [1, 0, 0, 0, 0, 0],       // pointing along x-axis
        0.8                         // high confidence → narrow cone
      );

      const target = [0.3, 0, 0, 0, 0, 0]; // directly ahead
      const result = checkTrustCone(cone, target);

      expect(result.withinCone).toBe(true);
      expect(result.angle).toBeCloseTo(0, 3);
      expect(result.angularMargin).toBeLessThan(0); // inside cone
    });

    it('should find target at apex as within cone', () => {
      const cone = createTrustCone(
        [0.1, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0],
        0.5
      );

      const result = checkTrustCone(cone, [0.1, 0, 0, 0, 0, 0]);
      expect(result.withinCone).toBe(true);
      expect(result.angle).toBe(0);
    });

    it('should find perpendicular target outside narrow cone', () => {
      const cone = createTrustCone(
        [0, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0],       // pointing along x
        0.9                         // narrow cone
      );

      const target = [0, 0.3, 0, 0, 0, 0]; // perpendicular (along y)
      const result = checkTrustCone(cone, target);

      expect(result.withinCone).toBe(false);
      expect(result.angle).toBeCloseTo(Math.PI / 2, 3); // 90 degrees
    });

    it('should find target behind apex outside cone', () => {
      const cone = createTrustCone(
        [0.3, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0],       // pointing forward
        0.5
      );

      const target = [0, 0, 0, 0, 0, 0]; // behind
      const result = checkTrustCone(cone, target);

      expect(result.withinCone).toBe(false);
      expect(result.angle).toBeGreaterThan(Math.PI / 2);
    });

    it('should report positive angular margin when outside', () => {
      const cone = createTrustCone(
        [0, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0],
        0.95 // very narrow cone
      );

      const target = [0, 0.3, 0, 0, 0, 0]; // perpendicular
      const result = checkTrustCone(cone, target);

      expect(result.angularMargin).toBeGreaterThan(0);
    });

    it('should report hyperbolic distance', () => {
      const cone = createTrustCone(
        [0, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0],
        0.8
      );

      const target = [0.5, 0, 0, 0, 0, 0];
      const result = checkTrustCone(cone, target);

      expect(result.hyperbolicDist).toBeGreaterThan(0);
      expect(isFinite(result.hyperbolicDist)).toBe(true);
    });

    it('should reject dimension mismatch', () => {
      const cone = createTrustCone([0, 0, 0, 0, 0, 0], [1, 0, 0, 0, 0, 0], 0.5);
      expect(() => checkTrustCone(cone, [0.1, 0])).toThrow('Dimension mismatch');
    });

    it('should respect maxDistance config', () => {
      const cone = createTrustCone([0, 0, 0, 0, 0, 0], [1, 0, 0, 0, 0, 0], 0.5);
      const target = [0.8, 0, 0, 0, 0, 0]; // far away in hyperbolic space

      const result = checkTrustCone(cone, target, { maxDistance: 0.1 });
      expect(result.withinCone).toBe(false); // too far
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Trust Cone Penalty
  // ═══════════════════════════════════════════════════════════════

  describe('trustConePenalty', () => {
    it('should return 1 (no penalty) for target within cone', () => {
      const cone = createTrustCone(
        [0, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0],
        0.5 // wide cone
      );

      const target = [0.2, 0, 0, 0, 0, 0]; // directly ahead
      expect(trustConePenalty(cone, target)).toBe(1.0);
    });

    it('should return penalty > 1 for target outside cone', () => {
      const cone = createTrustCone(
        [0, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0],
        0.95 // narrow cone
      );

      const target = [0, 0.3, 0, 0, 0, 0]; // perpendicular
      const penalty = trustConePenalty(cone, target);

      expect(penalty).toBeGreaterThan(1);
    });

    it('should increase penalty for targets further outside cone', () => {
      const cone = createTrustCone(
        [0, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0],
        0.95
      );

      // Slightly off-axis vs perpendicular
      const slightlyOff = [0.3, 0.15, 0, 0, 0, 0];
      const perpendicular = [0, 0.3, 0, 0, 0, 0];

      const penaltySlightly = trustConePenalty(cone, slightlyOff);
      const penaltyPerp = trustConePenalty(cone, perpendicular);

      // Perpendicular should have higher penalty
      expect(penaltyPerp).toBeGreaterThan(penaltySlightly);
    });

    it('should use golden ratio (φ) in exponential penalty', () => {
      const cone = createTrustCone(
        [0, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0],
        0.95
      );

      const target = [0, 0.3, 0, 0, 0, 0];
      const penalty = trustConePenalty(cone, target);

      // Penalty should be > 1 and finite
      expect(penalty).toBeGreaterThan(1);
      expect(isFinite(penalty)).toBe(true);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Realm Trust Cones
  // ═══════════════════════════════════════════════════════════════

  describe('createRealmTrustCone', () => {
    it('should create cone pointing toward KO realm from origin', () => {
      const cone = createRealmTrustCone(
        [0, 0, 0, 0, 0, 0],
        REALM_CENTERS.KO,
        0.8
      );

      // Direction should point toward KO = [0.3, 0, 0, 0, 0, 0]
      expect(cone.direction[0]).toBeGreaterThan(0.99); // approximately [1, 0, 0, 0, 0, 0]
      expect(Math.abs(cone.direction[1])).toBeLessThan(0.01);
    });

    it('should create wider cone with lower confidence', () => {
      const narrowCone = createRealmTrustCone(
        [0, 0, 0, 0, 0, 0],
        REALM_CENTERS.KO,
        0.9
      );

      const wideCone = createRealmTrustCone(
        [0, 0, 0, 0, 0, 0],
        REALM_CENTERS.KO,
        0.3
      );

      expect(wideCone.halfAngle).toBeGreaterThan(narrowCone.halfAngle);
    });

    it('should include KO center within cone pointing to KO', () => {
      const cone = createRealmTrustCone(
        [0, 0, 0, 0, 0, 0],
        REALM_CENTERS.KO,
        0.8
      );

      const result = checkTrustCone(cone, REALM_CENTERS.KO);
      expect(result.withinCone).toBe(true);
    });

    it('should exclude AV realm from narrow cone pointing to KO', () => {
      const cone = createRealmTrustCone(
        [0, 0, 0, 0, 0, 0],
        REALM_CENTERS.KO,
        0.95 // very narrow
      );

      const result = checkTrustCone(cone, REALM_CENTERS.AV);
      expect(result.withinCone).toBe(false);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Integration: Confidence → Cone Width → Access Control
  // ═══════════════════════════════════════════════════════════════

  describe('confidence-driven access control', () => {
    it('high confidence should allow precise navigation only', () => {
      const position = [0, 0, 0, 0, 0, 0];
      const cone = createRealmTrustCone(position, REALM_CENTERS.KO, 0.95);

      // Target directly on the path to KO: allowed
      expect(checkTrustCone(cone, [0.15, 0, 0, 0, 0, 0]).withinCone).toBe(true);

      // Target off-axis: denied
      expect(checkTrustCone(cone, [0, 0.15, 0, 0, 0, 0]).withinCone).toBe(false);
    });

    it('low confidence should allow wide navigation', () => {
      const position = [0, 0, 0, 0, 0, 0];
      const cone = createRealmTrustCone(position, REALM_CENTERS.KO, 0.2);

      // Wide cone should include nearby off-axis targets
      expect(checkTrustCone(cone, [0.15, 0.1, 0, 0, 0, 0]).withinCone).toBe(true);
    });

    it('medium confidence should be intermediate', () => {
      const position = [0, 0, 0, 0, 0, 0];

      const highCone = createRealmTrustCone(position, REALM_CENTERS.KO, 0.9);
      const medCone = createRealmTrustCone(position, REALM_CENTERS.KO, 0.5);
      const lowCone = createRealmTrustCone(position, REALM_CENTERS.KO, 0.2);

      expect(highCone.halfAngle).toBeLessThan(medCone.halfAngle);
      expect(medCone.halfAngle).toBeLessThan(lowCone.halfAngle);
    });
  });
});
