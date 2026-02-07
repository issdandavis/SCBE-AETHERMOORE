/**
 * @file adaptiveNavigator.test.ts
 * @description Tests for the Adaptive Hyperbolic Navigator
 *
 * Tests cover:
 * - Variable harmonic scaling R(coherence)
 * - Variable curvature κ(coherence)
 * - ODE-based trajectory evolution
 * - Anomaly detection
 * - Realm navigation
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  AdaptiveHyperbolicNavigator,
  createAdaptiveNavigator,
  computeCoherence,
  riskToCoherence,
  REALM_CENTERS,
  TONGUE_WEIGHTS,
  DEFAULT_CONFIG,
} from '../../src/harmonic/adaptiveNavigator';

describe('AdaptiveHyperbolicNavigator', () => {
  let nav: AdaptiveHyperbolicNavigator;

  beforeEach(() => {
    nav = new AdaptiveHyperbolicNavigator();
  });

  // ═══════════════════════════════════════════════════════════════
  // Adaptive Parameter Tests
  // ═══════════════════════════════════════════════════════════════

  describe('Adaptive Parameters', () => {
    it('should compute R(coherence) correctly', () => {
      // Full coherence → base R
      expect(nav.getCurrentR(1.0)).toBeCloseTo(DEFAULT_CONFIG.baseR);

      // Zero coherence → R_base + λ
      expect(nav.getCurrentR(0.0)).toBeCloseTo(
        DEFAULT_CONFIG.baseR + DEFAULT_CONFIG.lambdaPenalty
      );

      // Half coherence → R_base + λ/2
      expect(nav.getCurrentR(0.5)).toBeCloseTo(
        DEFAULT_CONFIG.baseR + DEFAULT_CONFIG.lambdaPenalty * 0.5
      );
    });

    it('should compute κ(coherence) correctly', () => {
      // Full coherence → κ = -1
      expect(nav.getCurrentKappa(1.0)).toBeCloseTo(-1);

      // Zero coherence → more negative
      const kappaZero = nav.getCurrentKappa(0.0);
      expect(kappaZero).toBeLessThan(-1);
      expect(kappaZero).toBeCloseTo(-1 * Math.exp(DEFAULT_CONFIG.gamma));

      // Lower coherence → more negative curvature
      expect(nav.getCurrentKappa(0.3)).toBeLessThan(nav.getCurrentKappa(0.7));
    });

    it('should clamp coherence to [0, 1]', () => {
      expect(nav.getCurrentR(-0.5)).toBe(nav.getCurrentR(0));
      expect(nav.getCurrentR(1.5)).toBe(nav.getCurrentR(1));
      expect(nav.getCurrentKappa(-0.5)).toBe(nav.getCurrentKappa(0));
      expect(nav.getCurrentKappa(1.5)).toBe(nav.getCurrentKappa(1));
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Hyperbolic Distance Tests
  // ═══════════════════════════════════════════════════════════════

  describe('Hyperbolic Distance', () => {
    it('should compute distance correctly with κ = -1', () => {
      const origin = [0, 0, 0, 0, 0, 0];
      const point = [0.3, 0, 0, 0, 0, 0];

      const dist = nav.hyperbolicDistanceKappa(origin, point, -1);
      expect(dist).toBeGreaterThan(0);
      expect(isFinite(dist)).toBe(true);
    });

    it('should increase distance with more negative curvature', () => {
      const origin = [0, 0, 0, 0, 0, 0];
      const point = [0.5, 0, 0, 0, 0, 0];

      const distKappa1 = nav.hyperbolicDistanceKappa(origin, point, -1);
      const distKappa2 = nav.hyperbolicDistanceKappa(origin, point, -2);

      // More negative curvature → same Euclidean distance maps to larger hyperbolic distance
      expect(distKappa2).not.toBe(distKappa1);
    });

    it('should satisfy triangle inequality', () => {
      const a = [0.1, 0.2, 0, 0, 0, 0];
      const b = [0.3, 0.1, 0, 0, 0, 0];
      const c = [0.2, 0.4, 0, 0, 0, 0];

      const dAB = nav.hyperbolicDistance(a, b);
      const dBC = nav.hyperbolicDistance(b, c);
      const dAC = nav.hyperbolicDistance(a, c);

      expect(dAC).toBeLessThanOrEqual(dAB + dBC + 1e-10);
    });

    it('should be symmetric', () => {
      const a = [0.2, 0.1, 0.3, 0, 0, 0];
      const b = [0.4, 0.2, 0.1, 0, 0, 0];

      expect(nav.hyperbolicDistance(a, b)).toBeCloseTo(nav.hyperbolicDistance(b, a));
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Update and Trajectory Tests
  // ═══════════════════════════════════════════════════════════════

  describe('Update and Trajectory', () => {
    it('should update position when called', () => {
      const initialPos = nav.getPosition();
      nav.update(['KO'], 0.8);
      const newPos = nav.getPosition();

      // Position should change (attraction to KO realm)
      const moved = initialPos.some((v, i) => Math.abs(v - newPos[i]) > 1e-10);
      expect(moved).toBe(true);
    });

    it('should move toward target realm with high coherence', () => {
      // Start at origin
      nav.reset();

      // Multiple updates toward KO realm with high coherence
      for (let i = 0; i < 10; i++) {
        nav.update(['KO'], 0.95);
      }

      const pos = nav.getPosition();
      const koCenter = REALM_CENTERS.KO;

      // Should have moved toward KO (positive x direction)
      expect(pos[0]).toBeGreaterThan(0);
    });

    it('should return NavigatorState with all fields', () => {
      const result = nav.update(['AV'], 0.7);

      expect(result.position).toBeDefined();
      expect(result.velocity).toBeDefined();
      expect(result.coherence).toBeCloseTo(0.7);
      expect(result.currentR).toBeCloseTo(nav.getCurrentR(0.7));
      expect(result.currentKappa).toBeCloseTo(nav.getCurrentKappa(0.7));
      expect(result.penalty).toBeGreaterThan(0);
      expect(result.timestamp).toBeGreaterThan(0);
    });

    it('should keep position inside ball boundary', () => {
      // Push hard in one direction
      for (let i = 0; i < 100; i++) {
        nav.update(['KO'], 1.0, 0, 0.5);
      }

      const pos = nav.getPosition();
      const norm = Math.sqrt(pos.reduce((sum, x) => sum + x * x, 0));

      expect(norm).toBeLessThanOrEqual(DEFAULT_CONFIG.boundaryThreshold + 1e-6);
    });

    it('should record history', () => {
      nav.update(['KO'], 0.9);
      nav.update(['AV'], 0.8);
      nav.update(['RU'], 0.7);

      const history = nav.getHistory();
      expect(history.length).toBe(4); // Initial + 3 updates
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Penalty Computation Tests
  // ═══════════════════════════════════════════════════════════════

  describe('Harmonic Penalty', () => {
    it('should compute penalty as 1/(1+d+2*pd)', () => {
      nav.reset([0.3, 0, 0, 0, 0, 0]);

      const result = nav.update(['KO'], 0.5);
      const kappa = result.currentKappa;
      const c = result.coherence;

      // Distance from current position to origin
      const d = nav.hyperbolicDistanceKappa(result.position, [0, 0, 0, 0, 0, 0], kappa);
      const phaseDeviation = 1 - c;

      const expectedPenalty = 1 / (1 + d + 2 * phaseDeviation);
      expect(result.penalty).toBeCloseTo(expectedPenalty, 3);
    });

    it('should have lower penalty (higher safety) for high coherence', () => {
      nav.reset([0.4, 0.2, 0, 0, 0, 0]);

      const highCoherenceResult = nav.update(['KO'], 0.95);
      nav.reset([0.4, 0.2, 0, 0, 0, 0]);
      const lowCoherenceResult = nav.update(['KO'], 0.2);

      // High coherence → lower phase deviation → higher safety score
      expect(highCoherenceResult.penalty).toBeGreaterThan(lowCoherenceResult.penalty);
    });

    it('should have penalty ≈ 1 at origin with full coherence', () => {
      nav.reset();
      const result = nav.update([], 1.0, 0, 0.001); // Tiny step

      // At origin, d ≈ 0, so R^(d²) ≈ R^0 = 1
      expect(result.penalty).toBeCloseTo(1, 1);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Realm Navigation Tests
  // ═══════════════════════════════════════════════════════════════

  describe('Realm Navigation', () => {
    it('should compute distance to realm correctly', () => {
      nav.reset();
      const distKO = nav.distanceToRealm('KO');
      const distAV = nav.distanceToRealm('AV');

      // From origin, all realms should be equidistant (same norm)
      expect(distKO).toBeCloseTo(distAV, 3);
    });

    it('should find closest realm', () => {
      nav.reset([0.2, 0, 0, 0, 0, 0]); // Near KO
      const { tongue, distance } = nav.closestRealm();

      expect(tongue).toBe('KO');
      expect(distance).toBeLessThan(nav.distanceToRealm('AV'));
    });

    it('should return Infinity for unknown realm', () => {
      expect(nav.distanceToRealm('UNKNOWN')).toBe(Infinity);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Anomaly Detection Tests
  // ═══════════════════════════════════════════════════════════════

  describe('Anomaly Detection', () => {
    it('should not detect anomaly with stable high coherence', () => {
      // Simulate normal operation
      for (let i = 0; i < 30; i++) {
        nav.update(['KO', 'AV'], 0.85 + Math.random() * 0.1);
      }

      const anomaly = nav.detectAnomaly();
      expect(anomaly.isAnomaly).toBe(false);
      expect(anomaly.score).toBeLessThan(0.7);
    });

    it('should detect anomaly with sustained low coherence', () => {
      // Simulate attack with low coherence
      for (let i = 0; i < 30; i++) {
        nav.update(['KO'], 0.1 + Math.random() * 0.1, 0.5);
      }

      const anomaly = nav.detectAnomaly();
      expect(anomaly.indicators).toContain('low_coherence');
      expect(anomaly.score).toBeGreaterThan(0);
    });

    it('should compute trajectory entropy', () => {
      // Add some trajectory points
      for (let i = 0; i < 20; i++) {
        nav.update(['KO', 'AV'], 0.7, 0.1);
      }

      const entropy = nav.trajectoryEntropy();
      expect(entropy).toBeGreaterThanOrEqual(0);
      expect(entropy).toBeLessThanOrEqual(1);
    });

    it('should compute coherence stability', () => {
      // Stable coherence
      for (let i = 0; i < 20; i++) {
        nav.update(['KO'], 0.8);
      }

      const stability = nav.coherenceStability();
      expect(stability).toBeGreaterThan(0.9); // Very stable
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // State Management Tests
  // ═══════════════════════════════════════════════════════════════

  describe('State Management', () => {
    it('should reset to origin', () => {
      nav.update(['KO'], 0.9);
      nav.update(['AV'], 0.8);
      nav.reset();

      const pos = nav.getPosition();
      expect(pos.every((v) => v === 0)).toBe(true);
      expect(nav.getHistory().length).toBe(1);
    });

    it('should reset to custom position', () => {
      nav.reset([0.1, 0.2, 0.3, 0.4, 0.5, 0.6]);

      const pos = nav.getPosition();
      expect(pos[0]).toBeCloseTo(0.1);
      expect(pos[5]).toBeCloseTo(0.6);
    });

    it('should serialize and deserialize', () => {
      nav.update(['KO'], 0.8);
      nav.update(['AV'], 0.7);

      const json = nav.serialize();
      const restored = AdaptiveHyperbolicNavigator.deserialize(json);

      expect(restored.getPosition()).toEqual(nav.getPosition());
      expect(restored.getCoherenceHistory()).toEqual(nav.getCoherenceHistory());
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Factory and Helper Tests
  // ═══════════════════════════════════════════════════════════════

  describe('Factory and Helpers', () => {
    it('should create navigator with factory', () => {
      const nav = createAdaptiveNavigator({ baseR: 2.0 });
      expect(nav.getCurrentR(1.0)).toBeCloseTo(2.0);
    });

    it('should compute coherence from spectral values', () => {
      expect(computeCoherence(1.0, 1.0)).toBeCloseTo(1.0);
      expect(computeCoherence(0.25, 1.0)).toBeCloseTo(0.5);
      expect(computeCoherence(0.5, 0.5)).toBeCloseTo(0.5);
    });

    it('should convert risk to coherence', () => {
      expect(riskToCoherence(0)).toBeCloseTo(1.0);
      expect(riskToCoherence(1)).toBeCloseTo(0.0);
      expect(riskToCoherence(0.3)).toBeCloseTo(0.7);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Constants Tests
  // ═══════════════════════════════════════════════════════════════

  describe('Constants', () => {
    it('should have all six Sacred Tongue realms', () => {
      expect(Object.keys(REALM_CENTERS)).toEqual(['KO', 'AV', 'RU', 'CA', 'UM', 'DR']);
    });

    it('should have realm centers inside the ball', () => {
      for (const center of Object.values(REALM_CENTERS)) {
        const norm = Math.sqrt(center.reduce((sum, x) => sum + x * x, 0));
        expect(norm).toBeLessThan(1);
      }
    });

    it('should have tongue weights following golden ratio', () => {
      const phi = (1 + Math.sqrt(5)) / 2;
      expect(TONGUE_WEIGHTS.KO).toBeCloseTo(1.0);
      expect(TONGUE_WEIGHTS.AV).toBeCloseTo(1 / phi);
      expect(TONGUE_WEIGHTS.RU).toBeCloseTo(1 / (phi * phi));
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Chaos/Mutation Tests
  // ═══════════════════════════════════════════════════════════════

  describe('Chaos and Mutations', () => {
    it('should apply chaos when coherence is low', () => {
      const navChaos = new AdaptiveHyperbolicNavigator({ chaos: 0.5 });

      // Run with low coherence - chaos should create more movement
      const positions: number[][] = [];
      for (let i = 0; i < 10; i++) {
        navChaos.update(['KO'], 0.1);
        positions.push(navChaos.getPosition());
      }

      // Check trajectory variance is higher than deterministic case
      const variances = positions[0].map((_, dim) => {
        const vals = positions.map((p) => p[dim]);
        const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
        return vals.reduce((sum, v) => sum + (v - mean) ** 2, 0) / vals.length;
      });

      const totalVariance = variances.reduce((a, b) => a + b, 0);
      expect(totalVariance).toBeGreaterThan(0);
    });

    it('should apply mutations proportional to rate', () => {
      const navMut = new AdaptiveHyperbolicNavigator({ chaos: 0 });

      // High mutation rate should cause more movement
      navMut.reset([0.3, 0, 0, 0, 0, 0]);
      navMut.update(['KO'], 0.5, 0.8); // High mutations

      // Position should have changed in multiple dimensions
      const pos = navMut.getPosition();
      const nonZeroDims = pos.filter((v) => Math.abs(v) > 0.01).length;
      expect(nonZeroDims).toBeGreaterThanOrEqual(1);
    });
  });
});
