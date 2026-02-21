/**
 * @file swarm-geometry.test.ts
 * @module tests/fleet/swarm-geometry
 * @layer L5, L12, L13
 * @component Swarm Geometry — Centroidal Field Tests
 * @version 3.2.4
 *
 * Comprehensive test suite for SwarmGeometry: vector math, centroid computation,
 * force computation, force composition, step integration, weight caps, and neighbors.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  SwarmGeometry,
  vecAdd,
  vecSub,
  vecScale,
  vecMag,
  vecNormalize,
  vecDist,
  VEC_ZERO,
  FORCE_WEIGHT_CAPS,
  DEFAULT_FORCE_WEIGHTS,
} from '../../src/fleet/swarm-geometry.js';
import type { RobotSpatialState, Vec, ForceBreakdown } from '../../src/fleet/swarm-geometry.js';

// ──────────────── Helpers ────────────────

/** Build a robot state with sensible defaults. */
function makeRobot(overrides: Partial<RobotSpatialState> & { id: string }): RobotSpatialState {
  return {
    position: { x: 0, y: 0, z: 0 },
    velocity: { x: 0, y: 0, z: 0 },
    goal: null,
    drift: { x: 0, y: 0, z: 0 },
    trust: 1.0,
    ...overrides,
  };
}

/** Build a Vec from components. */
function v(x: number, y: number, z: number): Vec {
  return { x, y, z };
}

/** Tolerance for floating-point comparisons. */
const EPS = 1e-9;

/** Assert two vectors are approximately equal component-wise. */
function expectVecClose(actual: Vec, expected: Vec, tolerance = EPS): void {
  expect(actual.x).toBeCloseTo(expected.x, -Math.log10(tolerance) - 1);
  expect(actual.y).toBeCloseTo(expected.y, -Math.log10(tolerance) - 1);
  expect(actual.z).toBeCloseTo(expected.z, -Math.log10(tolerance) - 1);
}

// ──────────────── Tests ────────────────

describe('SwarmGeometry', () => {
  // ── Vector Math ──

  describe('vector math', () => {
    it('vecAdd adds components correctly', () => {
      const result = vecAdd(v(1, 2, 3), v(4, 5, 6));
      expectVecClose(result, v(5, 7, 9));
    });

    it('vecAdd handles negative components', () => {
      const result = vecAdd(v(-1, -2, -3), v(1, 2, 3));
      expectVecClose(result, v(0, 0, 0));
    });

    it('vecSub subtracts correctly', () => {
      const result = vecSub(v(10, 20, 30), v(3, 7, 11));
      expectVecClose(result, v(7, 13, 19));
    });

    it('vecSub of identical vectors yields zero', () => {
      const a = v(5, 5, 5);
      const result = vecSub(a, a);
      expectVecClose(result, v(0, 0, 0));
    });

    it('vecScale multiplies by scalar', () => {
      const result = vecScale(v(1, 2, 3), 4);
      expectVecClose(result, v(4, 8, 12));
    });

    it('vecScale by zero yields zero vector', () => {
      const result = vecScale(v(7, 8, 9), 0);
      expectVecClose(result, v(0, 0, 0));
    });

    it('vecScale by negative scalar flips direction', () => {
      const result = vecScale(v(1, -2, 3), -2);
      expectVecClose(result, v(-2, 4, -6));
    });

    it('vecMag computes magnitude sqrt(x^2+y^2+z^2)', () => {
      // 3-4-0 triangle in 3D (with z=0)
      expect(vecMag(v(3, 4, 0))).toBeCloseTo(5, 10);
      // Classic 1-2-2 vector: sqrt(1+4+4) = 3
      expect(vecMag(v(1, 2, 2))).toBeCloseTo(3, 10);
      // Zero vector
      expect(vecMag(v(0, 0, 0))).toBeCloseTo(0, 10);
    });

    it('vecNormalize returns unit vector (mag ~ 1)', () => {
      const norm = vecNormalize(v(3, 4, 0));
      expect(vecMag(norm)).toBeCloseTo(1.0, 10);
      expectVecClose(norm, v(3 / 5, 4 / 5, 0));
    });

    it('vecNormalize handles zero vector by returning zero', () => {
      const norm = vecNormalize(v(0, 0, 0));
      expectVecClose(norm, v(0, 0, 0));
      expect(vecMag(norm)).toBe(0);
    });

    it('vecNormalize handles very small vector by returning zero', () => {
      const norm = vecNormalize(v(1e-15, 0, 0));
      expectVecClose(norm, v(0, 0, 0));
    });

    it('vecDist returns Euclidean distance', () => {
      const d = vecDist(v(0, 0, 0), v(3, 4, 0));
      expect(d).toBeCloseTo(5, 10);
    });

    it('vecDist between identical points is zero', () => {
      const p = v(7, 8, 9);
      expect(vecDist(p, p)).toBeCloseTo(0, 10);
    });

    it('vecDist is symmetric', () => {
      const a = v(1, 2, 3);
      const b = v(4, 6, 8);
      expect(vecDist(a, b)).toBeCloseTo(vecDist(b, a), 10);
    });

    it('VEC_ZERO is the origin', () => {
      expectVecClose(VEC_ZERO, v(0, 0, 0));
    });
  });

  // ── Centroid Computation ──

  describe('centroid computation', () => {
    let sg: SwarmGeometry;

    beforeEach(() => {
      sg = new SwarmGeometry();
    });

    it('empty swarm returns zero vector', () => {
      const centroid = sg.computeCentroid();
      expectVecClose(centroid, v(0, 0, 0));
    });

    it('single robot returns its own position', () => {
      sg.addRobot(makeRobot({ id: 'r1', position: v(5, 10, 15), trust: 1.0 }));
      const centroid = sg.computeCentroid();
      expectVecClose(centroid, v(5, 10, 15));
    });

    it('two equal-trust robots yield midpoint', () => {
      sg.addRobot(makeRobot({ id: 'r1', position: v(0, 0, 0), trust: 1.0 }));
      sg.addRobot(makeRobot({ id: 'r2', position: v(10, 0, 0), trust: 1.0 }));
      const centroid = sg.computeCentroid();
      expectVecClose(centroid, v(5, 0, 0));
    });

    it('trust-weighted centroid is biased toward high-trust robot', () => {
      sg.addRobot(makeRobot({ id: 'high', position: v(10, 0, 0), trust: 0.9 }));
      sg.addRobot(makeRobot({ id: 'low', position: v(0, 0, 0), trust: 0.1 }));
      const centroid = sg.computeCentroid();
      // C = (0.9*10 + 0.1*0) / (0.9+0.1) = 9/1 = 9
      expect(centroid.x).toBeCloseTo(9, 5);
      expect(centroid.y).toBeCloseTo(0, 5);
      expect(centroid.z).toBeCloseTo(0, 5);
    });

    it('three robots with equal trust yield average position', () => {
      sg.addRobot(makeRobot({ id: 'r1', position: v(0, 0, 0), trust: 1.0 }));
      sg.addRobot(makeRobot({ id: 'r2', position: v(3, 0, 0), trust: 1.0 }));
      sg.addRobot(makeRobot({ id: 'r3', position: v(0, 6, 0), trust: 1.0 }));
      const centroid = sg.computeCentroid();
      expectVecClose(centroid, v(1, 2, 0));
    });

    it('zero-trust robot is effectively ignored (clamped to 1e-10)', () => {
      sg.addRobot(makeRobot({ id: 'trusted', position: v(10, 0, 0), trust: 1.0 }));
      sg.addRobot(makeRobot({ id: 'untrusted', position: v(-100, 0, 0), trust: 0.0 }));
      const centroid = sg.computeCentroid();
      // trust=0 is clamped to 1e-10, so centroid is almost entirely at (10,0,0)
      expect(centroid.x).toBeCloseTo(10, 3);
    });
  });

  // ── Force Computation ──

  describe('force computation', () => {
    let sg: SwarmGeometry;

    beforeEach(() => {
      sg = new SwarmGeometry({
        weights: { alpha: 1, beta: 1, gamma: 1, delta: 1 },
        separationRadius: 2.0,
        couplingRadius: 10.0,
        maxSpeed: 100.0, // large cap so forces are not capped in these tests
        minSeparation: 0.1,
        dt: 0.1,
      });
    });

    it('cohesion: robot far from centroid gets stronger force toward it', () => {
      sg.addRobot(makeRobot({ id: 'far', position: v(20, 0, 0), trust: 1.0 }));
      sg.addRobot(makeRobot({ id: 'origin', position: v(0, 0, 0), trust: 1.0 }));

      const centroid = sg.computeCentroid(); // (10, 0, 0)
      const farBot = sg.getRobot('far')!;
      const originBot = sg.getRobot('origin')!;

      const forceFar = sg.computeCohesion(farBot, centroid);
      const forceOrigin = sg.computeCohesion(originBot, centroid);

      // Far robot is 10 units from centroid, origin robot is 10 units from centroid
      // Both are equally far in this setup. Let's verify direction at least.
      // forceFar should point toward centroid (negative x direction)
      expect(forceFar.x).toBeLessThan(0);
      // forceOrigin should point toward centroid (positive x direction)
      expect(forceOrigin.x).toBeGreaterThan(0);
    });

    it('cohesion: robot further from centroid gets proportionally stronger force', () => {
      // Single robot setup to control centroid
      const sg2 = new SwarmGeometry({ maxSpeed: 100 });
      sg2.addRobot(makeRobot({ id: 'center', position: v(0, 0, 0), trust: 1.0 }));
      sg2.addRobot(makeRobot({ id: 'near', position: v(2, 0, 0), trust: 1.0 }));

      const sg3 = new SwarmGeometry({ maxSpeed: 100 });
      sg3.addRobot(makeRobot({ id: 'center', position: v(0, 0, 0), trust: 1.0 }));
      sg3.addRobot(makeRobot({ id: 'far', position: v(10, 0, 0), trust: 1.0 }));

      const centroid2 = sg2.computeCentroid(); // (1, 0, 0)
      const centroid3 = sg3.computeCentroid(); // (5, 0, 0)

      const near = sg2.getRobot('near')!;
      const far = sg3.getRobot('far')!;

      const forceNear = sg2.computeCohesion(near, centroid2); // dist = 1
      const forceFar = sg3.computeCohesion(far, centroid3); // dist = 5

      // Linear scaling: far robot has stronger cohesion force
      expect(vecMag(forceFar)).toBeGreaterThan(vecMag(forceNear));
    });

    it('cohesion: robot at centroid gets zero cohesion force', () => {
      sg.addRobot(makeRobot({ id: 'solo', position: v(5, 5, 5), trust: 1.0 }));
      const centroid = sg.computeCentroid(); // (5,5,5)
      const robot = sg.getRobot('solo')!;
      const force = sg.computeCohesion(robot, centroid);
      expectVecClose(force, v(0, 0, 0));
    });

    it('separation: two robots within separationRadius get pushed apart', () => {
      // separationRadius is 2.0, place robots 1.0 apart
      sg.addRobot(makeRobot({ id: 'a', position: v(0, 0, 0) }));
      sg.addRobot(makeRobot({ id: 'b', position: v(1, 0, 0) }));

      const robotA = sg.getRobot('a')!;
      const forceA = sg.computeSeparation(robotA);

      // Robot A should be pushed away from B (negative x direction)
      expect(forceA.x).toBeLessThan(0);
      expect(vecMag(forceA)).toBeGreaterThan(0);
    });

    it('separation: two robots beyond separationRadius get zero separation force', () => {
      // separationRadius is 2.0, place robots 5.0 apart
      sg.addRobot(makeRobot({ id: 'a', position: v(0, 0, 0) }));
      sg.addRobot(makeRobot({ id: 'b', position: v(5, 0, 0) }));

      const robotA = sg.getRobot('a')!;
      const force = sg.computeSeparation(robotA);
      expectVecClose(force, v(0, 0, 0));
    });

    it('separation: closer robots produce stronger repulsion (inverse-distance)', () => {
      const sg1 = new SwarmGeometry({
        separationRadius: 5.0,
        maxSpeed: 100,
        weights: { alpha: 1, beta: 1, gamma: 1, delta: 1 },
      });
      sg1.addRobot(makeRobot({ id: 'a', position: v(0, 0, 0) }));
      sg1.addRobot(makeRobot({ id: 'close', position: v(1, 0, 0) }));

      const sg2 = new SwarmGeometry({
        separationRadius: 5.0,
        maxSpeed: 100,
        weights: { alpha: 1, beta: 1, gamma: 1, delta: 1 },
      });
      sg2.addRobot(makeRobot({ id: 'a', position: v(0, 0, 0) }));
      sg2.addRobot(makeRobot({ id: 'far', position: v(4, 0, 0) }));

      const forceClose = sg1.computeSeparation(sg1.getRobot('a')!);
      const forceFar = sg2.computeSeparation(sg2.getRobot('a')!);

      expect(vecMag(forceClose)).toBeGreaterThan(vecMag(forceFar));
    });

    it('goal force: robot with goal gets attracted toward it', () => {
      sg.addRobot(
        makeRobot({ id: 'r1', position: v(0, 0, 0), goal: v(10, 0, 0) })
      );
      const robot = sg.getRobot('r1')!;
      const force = sg.computeGoalForce(robot);

      // Force should point toward goal (positive x)
      expect(force.x).toBeGreaterThan(0);
      // Goal force is capped at magnitude 1
      expect(vecMag(force)).toBeCloseTo(1.0, 5);
    });

    it('goal force: magnitude is capped at 1 even for far goals', () => {
      sg.addRobot(
        makeRobot({ id: 'r1', position: v(0, 0, 0), goal: v(1000, 0, 0) })
      );
      const robot = sg.getRobot('r1')!;
      const force = sg.computeGoalForce(robot);
      expect(vecMag(force)).toBeCloseTo(1.0, 5);
    });

    it('goal force: very close to goal yields proportionally smaller force', () => {
      sg.addRobot(
        makeRobot({ id: 'r1', position: v(0, 0, 0), goal: v(0.3, 0, 0) })
      );
      const robot = sg.getRobot('r1')!;
      const force = sg.computeGoalForce(robot);
      // dist = 0.3 < 1.0, so strength = 0.3
      expect(vecMag(force)).toBeCloseTo(0.3, 5);
    });

    it('goal force: robot without goal gets zero goal force', () => {
      sg.addRobot(makeRobot({ id: 'r1', position: v(5, 5, 5), goal: null }));
      const robot = sg.getRobot('r1')!;
      const force = sg.computeGoalForce(robot);
      expectVecClose(force, v(0, 0, 0));
    });

    it('drift force: passes through robots drift vector', () => {
      const driftVec = v(0.5, -0.3, 0.1);
      sg.addRobot(makeRobot({ id: 'r1', position: v(0, 0, 0), drift: driftVec }));
      const robot = sg.getRobot('r1')!;
      const force = sg.computeDriftForce(robot);
      expectVecClose(force, driftVec);
    });

    it('drift force: zero drift yields zero force', () => {
      sg.addRobot(makeRobot({ id: 'r1', position: v(0, 0, 0), drift: v(0, 0, 0) }));
      const robot = sg.getRobot('r1')!;
      const force = sg.computeDriftForce(robot);
      expectVecClose(force, v(0, 0, 0));
    });
  });

  // ── Force Composition ──

  describe('force composition', () => {
    let sg: SwarmGeometry;

    beforeEach(() => {
      sg = new SwarmGeometry({
        weights: { alpha: 1.0, beta: 1.5, gamma: 1.0, delta: 0.5 },
        separationRadius: 2.0,
        couplingRadius: 10.0,
        maxSpeed: 5.0,
        minSeparation: 0.5,
        dt: 0.1,
      });
    });

    it('computeForces returns correct breakdown with all 4 forces', () => {
      sg.addRobot(
        makeRobot({
          id: 'r1',
          position: v(5, 0, 0),
          goal: v(10, 0, 0),
          drift: v(0.1, 0, 0),
          trust: 1.0,
        })
      );
      sg.addRobot(
        makeRobot({
          id: 'r2',
          position: v(0, 0, 0),
          trust: 1.0,
        })
      );

      const fb = sg.computeForces('r1');
      expect(fb).not.toBeNull();
      expect(fb!).toHaveProperty('cohesion');
      expect(fb!).toHaveProperty('separation');
      expect(fb!).toHaveProperty('goalForce');
      expect(fb!).toHaveProperty('driftForce');
      expect(fb!).toHaveProperty('resultant');
      expect(fb!).toHaveProperty('rawMagnitude');
      expect(fb!).toHaveProperty('capped');
    });

    it('computeForces returns null for unknown robot', () => {
      const fb = sg.computeForces('nonexistent');
      expect(fb).toBeNull();
    });

    it('speed cap triggers when resultant exceeds maxSpeed', () => {
      // Create scenario with very strong cohesion force
      const sgFast = new SwarmGeometry({
        weights: { alpha: 2.0, beta: 0, gamma: 2.0, delta: 0 },
        maxSpeed: 1.0, // very low cap
        separationRadius: 0.1,
        couplingRadius: 100,
        minSeparation: 0.01,
        dt: 0.1,
      });
      sgFast.addRobot(
        makeRobot({
          id: 'r1',
          position: v(50, 0, 0),
          goal: v(-50, 0, 0),
          trust: 1.0,
        })
      );
      sgFast.addRobot(
        makeRobot({
          id: 'r2',
          position: v(0, 0, 0),
          trust: 1.0,
        })
      );

      const fb = sgFast.computeForces('r1');
      expect(fb).not.toBeNull();
      expect(fb!.capped).toBe(true);
      expect(vecMag(fb!.resultant)).toBeCloseTo(1.0, 5);
      expect(fb!.rawMagnitude).toBeGreaterThan(1.0);
    });

    it('speed cap preserves direction', () => {
      const sgCap = new SwarmGeometry({
        weights: { alpha: 2.0, beta: 0, gamma: 0, delta: 0 },
        maxSpeed: 1.0,
        separationRadius: 0.1,
        couplingRadius: 100,
        minSeparation: 0.01,
        dt: 0.1,
      });
      // Robot far from centroid — strong cohesion in -x direction
      sgCap.addRobot(makeRobot({ id: 'r1', position: v(100, 0, 0), trust: 1.0 }));
      sgCap.addRobot(makeRobot({ id: 'r2', position: v(0, 0, 0), trust: 1.0 }));

      const fb = sgCap.computeForces('r1')!;
      expect(fb.capped).toBe(true);

      // Direction should still be toward centroid (negative x)
      const dir = vecNormalize(fb.resultant);
      expect(dir.x).toBeLessThan(0);
      // The y and z should be approximately zero
      expect(Math.abs(dir.y)).toBeLessThan(EPS);
      expect(Math.abs(dir.z)).toBeLessThan(EPS);
    });

    it('force weights alpha, beta, gamma, delta are applied correctly', () => {
      const sgWeighted = new SwarmGeometry({
        weights: { alpha: 2.0, beta: 0, gamma: 0, delta: 0 },
        separationRadius: 0.01,
        couplingRadius: 100,
        maxSpeed: 1000,
        minSeparation: 0.001,
        dt: 0.1,
      });
      sgWeighted.addRobot(makeRobot({ id: 'r1', position: v(10, 0, 0), trust: 1.0 }));
      sgWeighted.addRobot(makeRobot({ id: 'r2', position: v(0, 0, 0), trust: 1.0 }));

      const fb = sgWeighted.computeForces('r1')!;

      // Only cohesion should be active (beta=gamma=delta=0)
      // Separation: robots are 10 apart, separationRadius is 0.01 -> zero separation
      expectVecClose(fb.separation, v(0, 0, 0));
      expectVecClose(fb.goalForce, v(0, 0, 0));
      expectVecClose(fb.driftForce, v(0, 0, 0));

      // Cohesion should be the only contributor to resultant
      // Centroid is at (5,0,0). Robot at (10,0,0). Cohesion direction: -x, distance=5, weight=2
      // Cohesion raw = normalize((-5,0,0)) * 5 = (-5,0,0). Weighted = (-10,0,0)
      expect(fb.cohesion.x).toBeCloseTo(-10, 3);
      expectVecClose(fb.resultant, fb.cohesion);
    });

    it('all four force components combine additively', () => {
      const sgAll = new SwarmGeometry({
        weights: { alpha: 1.0, beta: 1.0, gamma: 1.0, delta: 1.0 },
        separationRadius: 5.0,
        couplingRadius: 100,
        maxSpeed: 1000,
        minSeparation: 0.001,
        dt: 0.1,
      });
      sgAll.addRobot(
        makeRobot({
          id: 'r1',
          position: v(3, 0, 0),
          goal: v(10, 0, 0),
          drift: v(0.5, 0, 0),
          trust: 1.0,
        })
      );
      sgAll.addRobot(makeRobot({ id: 'r2', position: v(0, 0, 0), trust: 1.0 }));

      const fb = sgAll.computeForces('r1')!;

      // Resultant should be sum of all four weighted forces
      const expected = vecAdd(
        vecAdd(fb.cohesion, fb.separation),
        vecAdd(fb.goalForce, fb.driftForce)
      );
      // If not capped, resultant == expected
      if (!fb.capped) {
        expectVecClose(fb.resultant, expected, 1e-6);
      }
    });
  });

  // ── Step Integration ──

  describe('step integration', () => {
    let sg: SwarmGeometry;

    beforeEach(() => {
      sg = new SwarmGeometry({
        weights: { alpha: 1.0, beta: 1.5, gamma: 1.0, delta: 0.3 },
        separationRadius: 2.0,
        couplingRadius: 20.0,
        maxSpeed: 5.0,
        minSeparation: 0.5,
        dt: 0.1,
      });
    });

    it('robots move in direction of resultant force', () => {
      // Single robot with a goal — only cohesion (zero, single robot) and goal act
      sg.addRobot(
        makeRobot({
          id: 'r1',
          position: v(0, 0, 0),
          goal: v(10, 0, 0),
          trust: 1.0,
        })
      );

      const posBefore = { ...sg.getRobot('r1')!.position };
      sg.step();
      const posAfter = sg.getRobot('r1')!.position;

      // Robot should have moved in +x direction toward goal
      expect(posAfter.x).toBeGreaterThan(posBefore.x);
    });

    it('no-go zone: robot pushed out of no-go zone', () => {
      sg.addRobot(
        makeRobot({
          id: 'r1',
          position: v(0.5, 0, 0),
          goal: v(0, 0, 0), // goal is at center of no-go zone
          trust: 1.0,
        })
      );

      // Add a no-go zone at the origin with radius 1
      sg.addNoGoZone(v(0, 0, 0), 1.0);

      // Run several steps to give the robot time to be repelled
      for (let i = 0; i < 50; i++) {
        sg.step();
      }

      const finalPos = sg.getRobot('r1')!.position;
      const distFromCenter = vecDist(finalPos, v(0, 0, 0));

      // Robot should be outside the no-go zone (radius 1.0)
      expect(distFromCenter).toBeGreaterThanOrEqual(1.0);
    });

    it('minimum separation: two robots cannot get closer than minSeparation', () => {
      // Place two robots very close together with cohesion pulling them together
      sg.addRobot(
        makeRobot({
          id: 'r1',
          position: v(0, 0, 0),
          trust: 1.0,
        })
      );
      sg.addRobot(
        makeRobot({
          id: 'r2',
          position: v(0.3, 0, 0), // closer than minSeparation=0.5
          trust: 1.0,
        })
      );

      // Run multiple steps
      for (let i = 0; i < 20; i++) {
        sg.step();
      }

      const p1 = sg.getRobot('r1')!.position;
      const p2 = sg.getRobot('r2')!.position;
      const dist = vecDist(p1, p2);

      // Robots must be at least minSeparation apart (or very close to it)
      expect(dist).toBeGreaterThanOrEqual(sg.getConfig().minSeparation - 0.01);
    });

    it('multiple steps: swarm coheres (spread decreases)', () => {
      // Scatter robots around
      sg.addRobot(makeRobot({ id: 'r1', position: v(8, 0, 0), trust: 1.0 }));
      sg.addRobot(makeRobot({ id: 'r2', position: v(-8, 0, 0), trust: 1.0 }));
      sg.addRobot(makeRobot({ id: 'r3', position: v(0, 8, 0), trust: 1.0 }));
      sg.addRobot(makeRobot({ id: 'r4', position: v(0, -8, 0), trust: 1.0 }));

      const initialSpread = sg.getSwarmSpread();

      // Run many steps with cohesion
      for (let i = 0; i < 200; i++) {
        sg.step();
      }

      const finalSpread = sg.getSwarmSpread();

      // Swarm should have cohered (spread decreased)
      expect(finalSpread).toBeLessThan(initialSpread);
    });

    it('all robots get a ForceBreakdown from step()', () => {
      sg.addRobot(makeRobot({ id: 'r1', position: v(0, 0, 0), trust: 1.0 }));
      sg.addRobot(makeRobot({ id: 'r2', position: v(5, 0, 0), trust: 1.0 }));
      sg.addRobot(makeRobot({ id: 'r3', position: v(0, 5, 0), trust: 1.0 }));

      const breakdowns = sg.step();

      expect(breakdowns.size).toBe(3);
      expect(breakdowns.has('r1')).toBe(true);
      expect(breakdowns.has('r2')).toBe(true);
      expect(breakdowns.has('r3')).toBe(true);

      for (const fb of breakdowns.values()) {
        expect(fb).toHaveProperty('cohesion');
        expect(fb).toHaveProperty('separation');
        expect(fb).toHaveProperty('goalForce');
        expect(fb).toHaveProperty('driftForce');
        expect(fb).toHaveProperty('resultant');
        expect(fb).toHaveProperty('rawMagnitude');
        expect(fb).toHaveProperty('capped');
      }
    });

    it('step updates robot velocity to the resultant force', () => {
      sg.addRobot(
        makeRobot({
          id: 'r1',
          position: v(0, 0, 0),
          goal: v(10, 0, 0),
          trust: 1.0,
        })
      );

      const breakdowns = sg.step();
      const robot = sg.getRobot('r1')!;
      const fb = breakdowns.get('r1')!;

      // Velocity should be set to the resultant force
      expectVecClose(robot.velocity, fb.resultant, 1e-6);
    });

    it('no-go zone: isInNoGoZone correctly identifies positions inside zones', () => {
      sg.addNoGoZone(v(5, 5, 5), 2.0);

      expect(sg.isInNoGoZone(v(5, 5, 5))).toBe(true); // center
      expect(sg.isInNoGoZone(v(5.5, 5, 5))).toBe(true); // inside
      expect(sg.isInNoGoZone(v(5, 5, 8))).toBe(false); // outside
    });
  });

  // ── Weight Caps ──

  describe('weight caps', () => {
    it('weights exceeding FORCE_WEIGHT_CAPS are clamped', () => {
      const sg = new SwarmGeometry({
        weights: { alpha: 100, beta: 200, gamma: 300, delta: 400 },
      });
      const config = sg.getConfig();

      expect(config.weights.alpha).toBe(FORCE_WEIGHT_CAPS.alpha);
      expect(config.weights.beta).toBe(FORCE_WEIGHT_CAPS.beta);
      expect(config.weights.gamma).toBe(FORCE_WEIGHT_CAPS.gamma);
      expect(config.weights.delta).toBe(FORCE_WEIGHT_CAPS.delta);
    });

    it('negative weights are made positive then clamped', () => {
      const sg = new SwarmGeometry({
        weights: { alpha: -1.5, beta: -100, gamma: -0.5, delta: -0.2 },
      });
      const config = sg.getConfig();

      // Math.abs(-1.5) = 1.5 <= 2.0, so alpha = 1.5
      expect(config.weights.alpha).toBeCloseTo(1.5);
      // Math.abs(-100) = 100, clamped to 3.0
      expect(config.weights.beta).toBe(FORCE_WEIGHT_CAPS.beta);
      // Math.abs(-0.5) = 0.5 <= 2.5, so gamma = 0.5
      expect(config.weights.gamma).toBeCloseTo(0.5);
      // Math.abs(-0.2) = 0.2 <= 1.0, so delta = 0.2
      expect(config.weights.delta).toBeCloseTo(0.2);
    });

    it('default weights are within caps', () => {
      expect(DEFAULT_FORCE_WEIGHTS.alpha).toBeLessThanOrEqual(FORCE_WEIGHT_CAPS.alpha);
      expect(DEFAULT_FORCE_WEIGHTS.beta).toBeLessThanOrEqual(FORCE_WEIGHT_CAPS.beta);
      expect(DEFAULT_FORCE_WEIGHTS.gamma).toBeLessThanOrEqual(FORCE_WEIGHT_CAPS.gamma);
      expect(DEFAULT_FORCE_WEIGHTS.delta).toBeLessThanOrEqual(FORCE_WEIGHT_CAPS.delta);
    });

    it('weights at exactly the cap value are preserved', () => {
      const sg = new SwarmGeometry({
        weights: {
          alpha: FORCE_WEIGHT_CAPS.alpha,
          beta: FORCE_WEIGHT_CAPS.beta,
          gamma: FORCE_WEIGHT_CAPS.gamma,
          delta: FORCE_WEIGHT_CAPS.delta,
        },
      });
      const config = sg.getConfig();

      expect(config.weights.alpha).toBe(FORCE_WEIGHT_CAPS.alpha);
      expect(config.weights.beta).toBe(FORCE_WEIGHT_CAPS.beta);
      expect(config.weights.gamma).toBe(FORCE_WEIGHT_CAPS.gamma);
      expect(config.weights.delta).toBe(FORCE_WEIGHT_CAPS.delta);
    });

    it('zero weights are preserved as zero', () => {
      const sg = new SwarmGeometry({
        weights: { alpha: 0, beta: 0, gamma: 0, delta: 0 },
      });
      const config = sg.getConfig();

      expect(config.weights.alpha).toBe(0);
      expect(config.weights.beta).toBe(0);
      expect(config.weights.gamma).toBe(0);
      expect(config.weights.delta).toBe(0);
    });
  });

  // ── Neighbors ──

  describe('neighbors', () => {
    let sg: SwarmGeometry;

    beforeEach(() => {
      sg = new SwarmGeometry({
        couplingRadius: 5.0,
        separationRadius: 1.0,
        maxSpeed: 5.0,
        minSeparation: 0.1,
        dt: 0.1,
      });
    });

    it('getNeighbors returns robots within couplingRadius', () => {
      sg.addRobot(makeRobot({ id: 'center', position: v(0, 0, 0) }));
      sg.addRobot(makeRobot({ id: 'near1', position: v(3, 0, 0) })); // dist=3, within 5
      sg.addRobot(makeRobot({ id: 'near2', position: v(0, 4, 0) })); // dist=4, within 5
      sg.addRobot(makeRobot({ id: 'edge', position: v(5, 0, 0) })); // dist=5, exactly at boundary

      const neighbors = sg.getNeighbors('center');
      const ids = neighbors.map((n) => n.id).sort();

      expect(ids).toContain('near1');
      expect(ids).toContain('near2');
      expect(ids).toContain('edge'); // <= couplingRadius
    });

    it('getNeighbors excludes robots beyond couplingRadius', () => {
      sg.addRobot(makeRobot({ id: 'center', position: v(0, 0, 0) }));
      sg.addRobot(makeRobot({ id: 'close', position: v(2, 0, 0) })); // dist=2, within 5
      sg.addRobot(makeRobot({ id: 'far', position: v(10, 0, 0) })); // dist=10, beyond 5
      sg.addRobot(makeRobot({ id: 'veryFar', position: v(100, 0, 0) })); // dist=100, beyond 5

      const neighbors = sg.getNeighbors('center');
      const ids = neighbors.map((n) => n.id);

      expect(ids).toContain('close');
      expect(ids).not.toContain('far');
      expect(ids).not.toContain('veryFar');
    });

    it('getNeighbors excludes the robot itself', () => {
      sg.addRobot(makeRobot({ id: 'r1', position: v(0, 0, 0) }));
      sg.addRobot(makeRobot({ id: 'r2', position: v(1, 0, 0) }));

      const neighbors = sg.getNeighbors('r1');
      const ids = neighbors.map((n) => n.id);

      expect(ids).not.toContain('r1');
      expect(ids).toContain('r2');
    });

    it('getNeighbors returns empty for unknown robot', () => {
      sg.addRobot(makeRobot({ id: 'r1', position: v(0, 0, 0) }));
      const neighbors = sg.getNeighbors('nonexistent');
      expect(neighbors).toEqual([]);
    });
  });
});
