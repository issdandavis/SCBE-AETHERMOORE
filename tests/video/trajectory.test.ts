/**
 * Trajectory Generator Tests
 * ==========================
 *
 * Tests for Poincaré ball trajectory generation
 * with hyperbolic operations and Sacred Tongue patterns.
 */

import { describe, it, expect } from 'vitest';
import {
  sanitizePoint,
  contextToPoincarePoint,
  mobiusAdd6D,
  hyperbolicDistance6D,
  expMap0_6D,
  logMap0_6D,
  geodesicInterpolate,
  generateTrajectory,
  validateTrajectory,
} from '../../src/video/trajectory.js';
import type { PoincarePoint, ContextVector } from '../../src/video/types.js';

describe('Trajectory Generator', () => {
  describe('Point Sanitization', () => {
    it('should not modify points inside the ball', () => {
      const point: PoincarePoint = [0.1, 0.2, 0.3, 0.1, 0.1, 0.1];
      const sanitized = sanitizePoint(point);

      for (let i = 0; i < 6; i++) {
        expect(sanitized[i]).toBeCloseTo(point[i], 10);
      }
    });

    it('should project points outside ball onto boundary', () => {
      const point: PoincarePoint = [0.8, 0.8, 0.8, 0.8, 0.8, 0.8];
      const sanitized = sanitizePoint(point);

      // Compute norm
      let normSq = 0;
      for (const v of sanitized) normSq += v * v;
      const norm = Math.sqrt(normSq);

      expect(norm).toBeLessThan(1);
      expect(norm).toBeCloseTo(0.999, 2);
    });

    it('should handle NaN values', () => {
      const point: PoincarePoint = [NaN, 0.1, 0.2, Infinity, -Infinity, 0.3];
      const sanitized = sanitizePoint(point);

      for (const v of sanitized) {
        expect(Number.isFinite(v)).toBe(true);
      }
    });

    it('should preserve direction when projecting', () => {
      const point: PoincarePoint = [1, 0, 0, 0, 0, 0];
      const sanitized = sanitizePoint(point);

      // Should still point in positive x direction
      expect(sanitized[0]).toBeGreaterThan(0);
      expect(Math.abs(sanitized[1])).toBeLessThan(0.01);
    });
  });

  describe('Context to Poincaré', () => {
    it('should map context to valid ball point', () => {
      const ctx: ContextVector = {
        time: 100,
        entropy: 0.5,
        threatLevel: 0.3,
        userId: 12345,
        behavioralStability: 0.8,
        audioPhase: 1.5,
      };

      const point = contextToPoincarePoint(ctx);

      // Check it's inside ball
      let normSq = 0;
      for (const v of point) normSq += v * v;
      expect(Math.sqrt(normSq)).toBeLessThan(1);
    });

    it('should handle extreme context values', () => {
      const ctx: ContextVector = {
        time: 1e10,
        entropy: 100,
        threatLevel: -50,
        userId: Number.MAX_SAFE_INTEGER,
        behavioralStability: 1000,
        audioPhase: 100 * Math.PI,
      };

      const point = contextToPoincarePoint(ctx);

      // Should still be valid
      for (const v of point) {
        expect(Number.isFinite(v)).toBe(true);
        expect(Math.abs(v)).toBeLessThan(1);
      }
    });
  });

  describe('Möbius Addition', () => {
    const origin: PoincarePoint = [0, 0, 0, 0, 0, 0];
    const p1: PoincarePoint = [0.3, 0.2, 0.1, 0, 0, 0];
    const p2: PoincarePoint = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1];

    it('should have identity element at origin', () => {
      const result = mobiusAdd6D(origin, p1);
      for (let i = 0; i < 6; i++) {
        expect(result[i]).toBeCloseTo(p1[i], 5);
      }
    });

    it('should return point inside ball', () => {
      const result = mobiusAdd6D(p1, p2);

      let normSq = 0;
      for (const v of result) normSq += v * v;
      expect(Math.sqrt(normSq)).toBeLessThan(1);
    });

    it('should be non-commutative', () => {
      const ab = mobiusAdd6D(p1, p2);
      const ba = mobiusAdd6D(p2, p1);

      // Generally different (gyrovector space property)
      let diff = 0;
      for (let i = 0; i < 6; i++) {
        diff += Math.abs(ab[i] - ba[i]);
      }
      // Difference should be non-zero for general points
      expect(diff).toBeGreaterThan(0.001);
    });

    it('should handle near-boundary points', () => {
      const nearBoundary: PoincarePoint = [0.9, 0.3, 0.1, 0, 0, 0];
      const result = mobiusAdd6D(nearBoundary, p1);

      let normSq = 0;
      for (const v of result) normSq += v * v;
      expect(Math.sqrt(normSq)).toBeLessThan(1);
    });
  });

  describe('Hyperbolic Distance', () => {
    const origin: PoincarePoint = [0, 0, 0, 0, 0, 0];
    const p1: PoincarePoint = [0.5, 0, 0, 0, 0, 0];
    const p2: PoincarePoint = [0.3, 0.3, 0, 0, 0, 0];

    it('should return 0 for same point', () => {
      const dist = hyperbolicDistance6D(p1, p1);
      expect(dist).toBeCloseTo(0, 10);
    });

    it('should be symmetric', () => {
      const d12 = hyperbolicDistance6D(p1, p2);
      const d21 = hyperbolicDistance6D(p2, p1);
      expect(d12).toBeCloseTo(d21, 10);
    });

    it('should satisfy triangle inequality', () => {
      const d12 = hyperbolicDistance6D(p1, p2);
      const d1o = hyperbolicDistance6D(p1, origin);
      const do2 = hyperbolicDistance6D(origin, p2);

      expect(d12).toBeLessThanOrEqual(d1o + do2 + 1e-10);
    });

    it('should increase as points approach boundary', () => {
      const close: PoincarePoint = [0.3, 0, 0, 0, 0, 0];
      const far: PoincarePoint = [0.9, 0, 0, 0, 0, 0];

      const dClose = hyperbolicDistance6D(origin, close);
      const dFar = hyperbolicDistance6D(origin, far);

      expect(dFar).toBeGreaterThan(dClose);
    });
  });

  describe('Exponential and Logarithmic Maps', () => {
    it('should be inverses at origin', () => {
      const v: PoincarePoint = [0.5, 0.3, 0.2, 0.1, 0.1, 0.1];
      const expV = expMap0_6D(v);
      const logExpV = logMap0_6D(expV);

      for (let i = 0; i < 6; i++) {
        expect(logExpV[i]).toBeCloseTo(v[i], 5);
      }
    });

    it('should map zero to origin', () => {
      const zero: PoincarePoint = [0, 0, 0, 0, 0, 0];
      const result = expMap0_6D(zero);

      for (const v of result) {
        expect(Math.abs(v)).toBeLessThan(1e-10);
      }
    });

    it('should keep expMap result in ball', () => {
      const large: PoincarePoint = [10, 10, 10, 10, 10, 10];
      const result = expMap0_6D(large);

      let normSq = 0;
      for (const v of result) normSq += v * v;
      expect(Math.sqrt(normSq)).toBeLessThan(1);
    });
  });

  describe('Geodesic Interpolation', () => {
    const p1: PoincarePoint = [0.2, 0.1, 0, 0, 0, 0];
    const p2: PoincarePoint = [0.5, 0.4, 0.1, 0.1, 0.1, 0.1];

    it('should return start point at t=0', () => {
      const result = geodesicInterpolate(p1, p2, 0);
      for (let i = 0; i < 6; i++) {
        expect(result[i]).toBeCloseTo(p1[i], 5);
      }
    });

    it('should return end point at t=1', () => {
      const result = geodesicInterpolate(p1, p2, 1);
      for (let i = 0; i < 6; i++) {
        expect(result[i]).toBeCloseTo(p2[i], 5);
      }
    });

    it('should return midpoint at t=0.5', () => {
      const result = geodesicInterpolate(p1, p2, 0.5);

      // Should be between the two points (in hyperbolic sense)
      const d1mid = hyperbolicDistance6D(p1, result);
      const dmid2 = hyperbolicDistance6D(result, p2);
      const d12 = hyperbolicDistance6D(p1, p2);

      // d(p1, mid) + d(mid, p2) ≈ d(p1, p2) for geodesic
      expect(d1mid + dmid2).toBeCloseTo(d12, 3);
    });

    it('should always stay inside ball', () => {
      for (let t = 0; t <= 1; t += 0.1) {
        const result = geodesicInterpolate(p1, p2, t);

        let normSq = 0;
        for (const v of result) normSq += v * v;
        expect(Math.sqrt(normSq)).toBeLessThan(1);
      }
    });

    it('should clamp t to [0, 1]', () => {
      const beforeStart = geodesicInterpolate(p1, p2, -0.5);
      const afterEnd = geodesicInterpolate(p1, p2, 1.5);

      // Should be clamped
      for (let i = 0; i < 6; i++) {
        expect(beforeStart[i]).toBeCloseTo(p1[i], 5);
        expect(afterEnd[i]).toBeCloseTo(p2[i], 5);
      }
    });
  });

  describe('Trajectory Generation', () => {
    it('should generate trajectory with correct frame count', () => {
      const trajectory = generateTrajectory('av', 5, 30, 0.05, 42);

      expect(trajectory.points.length).toBe(150); // 5 seconds * 30 fps
      expect(trajectory.duration).toBe(5);
      expect(trajectory.fps).toBe(30);
      expect(trajectory.tongue).toBe('av');
    });

    it('should generate deterministic trajectory with same seed', () => {
      const t1 = generateTrajectory('ko', 2, 10, 0.05, 12345);
      const t2 = generateTrajectory('ko', 2, 10, 0.05, 12345);

      for (let i = 0; i < t1.points.length; i++) {
        for (let j = 0; j < 6; j++) {
          expect(t1.points[i][j]).toBeCloseTo(t2.points[i][j], 10);
        }
      }
    });

    it('should generate smooth continuous trajectories', () => {
      // Verify that consecutive points in trajectory are not too far apart
      const traj = generateTrajectory('av', 5, 30, 0.05, 42);

      // Check that points transition smoothly (no teleportation)
      for (let i = 1; i < traj.points.length; i++) {
        const prev = traj.points[i - 1];
        const curr = traj.points[i];

        let dist = 0;
        for (let j = 0; j < 6; j++) {
          dist += (curr[j] - prev[j]) ** 2;
        }
        dist = Math.sqrt(dist);

        // Each frame should not jump too far (smooth transition)
        expect(dist).toBeLessThan(0.5);
      }
    });

    it('should keep all points inside ball', () => {
      const trajectory = generateTrajectory('ca', 10, 30, 0.1, 999);

      for (const point of trajectory.points) {
        let normSq = 0;
        for (const v of point) normSq += v * v;
        expect(Math.sqrt(normSq)).toBeLessThan(1);
      }
    });

    it('should validate parameters', () => {
      // Very short duration
      const t1 = generateTrajectory('av', 0.01, 10, 0.05, 42);
      expect(t1.duration).toBeGreaterThanOrEqual(0.1);

      // Very high FPS
      const t2 = generateTrajectory('av', 1, 1000, 0.05, 42);
      expect(t2.fps).toBeLessThanOrEqual(120);

      // Extreme breathing
      const t3 = generateTrajectory('av', 1, 10, 10, 42);
      // Should still have valid points
      for (const point of t3.points) {
        let normSq = 0;
        for (const v of point) normSq += v * v;
        expect(Math.sqrt(normSq)).toBeLessThan(1);
      }
    });
  });

  describe('Trajectory Validation', () => {
    it('should pass for valid trajectory', () => {
      const trajectory = generateTrajectory('av', 2, 30, 0.05, 42);
      const errors = validateTrajectory(trajectory);
      expect(errors).toHaveLength(0);
    });

    it('should detect empty trajectory', () => {
      const trajectory = {
        points: [],
        duration: 1,
        fps: 30,
        tongue: 'av' as const,
      };
      const errors = validateTrajectory(trajectory);
      expect(errors.length).toBeGreaterThan(0);
      expect(errors[0]).toContain('no points');
    });

    it('should detect frame count mismatch', () => {
      const trajectory = generateTrajectory('av', 2, 30, 0.05, 42);
      // Remove some points
      trajectory.points = trajectory.points.slice(0, 10);

      const errors = validateTrajectory(trajectory);
      expect(errors.some(e => e.includes('mismatch'))).toBe(true);
    });

    it('should detect points outside ball', () => {
      const trajectory = generateTrajectory('av', 1, 10, 0.05, 42);
      // Manually corrupt a point
      trajectory.points[0] = [2, 2, 2, 2, 2, 2];

      const errors = validateTrajectory(trajectory);
      expect(errors.some(e => e.includes('outside'))).toBe(true);
    });
  });
});
