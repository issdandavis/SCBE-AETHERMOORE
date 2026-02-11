/**
 * @file entropic-layer.test.ts
 * @module tests/ai_brain/entropic-layer
 * @layer Layer 12, Layer 13
 *
 * Tests for EntropicLayer: escape detection, adaptive-k, and expansion tracking.
 */

import { describe, it, expect } from 'vitest';
import {
  EntropicLayer,
  DEFAULT_MAX_VOLUME,
  MIN_K,
  MAX_K,
  DEFAULT_ENTROPIC_CONFIG,
  type EntropicState,
  type EntropicConfig,
  type EscapeAssessment,
} from '../../src/ai_brain/entropic-layer.js';

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

function makeState(position: number[], velocity: number[]): EntropicState {
  return { position, velocity };
}

function originState(dim: number = 6): EntropicState {
  return makeState(new Array(dim).fill(0), new Array(dim).fill(0));
}

// ═══════════════════════════════════════════════════════════════
// Construction & Configuration
// ═══════════════════════════════════════════════════════════════

describe('EntropicLayer', () => {
  describe('construction', () => {
    it('should use default config', () => {
      const layer = new EntropicLayer();
      const config = layer.getConfig();
      expect(config.maxVolume).toBe(DEFAULT_MAX_VOLUME);
      expect(config.baseK).toBe(5);
      expect(config.cQuantum).toBe(1.0);
      expect(config.n0).toBe(100);
    });

    it('should accept partial config', () => {
      const layer = new EntropicLayer({ maxVolume: 500, baseK: 10 });
      const config = layer.getConfig();
      expect(config.maxVolume).toBe(500);
      expect(config.baseK).toBe(10);
      expect(config.cQuantum).toBe(1.0); // default preserved
    });

    it('should support runtime config update', () => {
      const layer = new EntropicLayer();
      layer.updateConfig({ maxVolume: 999 });
      expect(layer.getConfig().maxVolume).toBe(999);
    });

    it('should return config copy (not reference)', () => {
      const layer = new EntropicLayer();
      const c1 = layer.getConfig();
      layer.updateConfig({ maxVolume: 123 });
      const c2 = layer.getConfig();
      expect(c1.maxVolume).toBe(DEFAULT_MAX_VOLUME);
      expect(c2.maxVolume).toBe(123);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Expansion Volume
  // ═══════════════════════════════════════════════════════════════

  describe('computeExpansionVolume', () => {
    it('should return 0 for origin', () => {
      const layer = new EntropicLayer();
      const vol = layer.computeExpansionVolume([0, 0, 0, 0, 0, 0]);
      expect(vol).toBe(0);
    });

    it('should increase with radius', () => {
      const layer = new EntropicLayer();
      const vol1 = layer.computeExpansionVolume([0.1, 0, 0, 0, 0, 0]);
      const vol2 = layer.computeExpansionVolume([0.5, 0, 0, 0, 0, 0]);
      const vol3 = layer.computeExpansionVolume([0.9, 0, 0, 0, 0, 0]);
      expect(vol2).toBeGreaterThan(vol1);
      expect(vol3).toBeGreaterThan(vol2);
    });

    it('should be positive for non-zero positions', () => {
      const layer = new EntropicLayer();
      const vol = layer.computeExpansionVolume([0.3, 0.2, 0.1, 0.0, 0.0, 0.0]);
      expect(vol).toBeGreaterThan(0);
    });

    it('should handle different dimensions', () => {
      const layer = new EntropicLayer();
      // 2D
      const vol2d = layer.computeExpansionVolume([0.5, 0.5]);
      expect(vol2d).toBeGreaterThan(0);
      // 3D
      const vol3d = layer.computeExpansionVolume([0.5, 0.5, 0.5]);
      expect(vol3d).toBeGreaterThan(0);
      // 6D (Sacred Tongues manifold)
      const vol6d = layer.computeExpansionVolume([0.3, 0.3, 0.3, 0.3, 0.3, 0.3]);
      expect(vol6d).toBeGreaterThan(0);
    });

    it('should grow exponentially (hyperbolic expansion)', () => {
      const layer = new EntropicLayer();
      const vol1 = layer.computeExpansionVolume([0.1, 0, 0, 0, 0, 0]);
      const vol2 = layer.computeExpansionVolume([1.0, 0, 0, 0, 0, 0]);
      // Growth should be super-linear due to exp((d-1)*r)
      const ratio = vol2 / vol1;
      expect(ratio).toBeGreaterThan(100); // exponential growth
    });

    it('should not overflow for large radius (cap at exp(50))', () => {
      const layer = new EntropicLayer();
      // Large radius - exp factor is capped
      const vol = layer.computeExpansionVolume([10, 0, 0, 0, 0, 0]);
      expect(Number.isFinite(vol)).toBe(true);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Escape Detection
  // ═══════════════════════════════════════════════════════════════

  describe('detectEscape', () => {
    it('should not escape at origin', () => {
      const layer = new EntropicLayer();
      const assessment = layer.detectEscape(originState());
      expect(assessment.escaped).toBe(false);
      expect(assessment.volume).toBe(0);
      expect(assessment.radialVelocity).toBe(0);
    });

    it('should detect volume-based escape', () => {
      const layer = new EntropicLayer({ maxVolume: 0.001 });
      const state = makeState([0.5, 0.5, 0.5, 0.5, 0.5, 0.5], [0, 0, 0, 0, 0, 0]);
      const assessment = layer.detectEscape(state);
      expect(assessment.escaped).toBe(true);
      expect(assessment.volume).toBeGreaterThan(0.001);
      expect(assessment.volumeRatio).toBeGreaterThan(1.0);
    });

    it('should detect velocity-based escape', () => {
      const layer = new EntropicLayer({ cQuantum: 0.01, n0: 100 });
      // High radial velocity (velocity pointing same direction as position)
      const state = makeState([0.5, 0, 0, 0, 0, 0], [10.0, 0, 0, 0, 0, 0]);
      const assessment = layer.detectEscape(state);
      expect(assessment.radialVelocity).toBeGreaterThan(0);
      expect(assessment.escaped).toBe(true);
    });

    it('should not escape for small volume and low velocity', () => {
      const layer = new EntropicLayer();
      const state = makeState(
        [0.01, 0.01, 0.01, 0.01, 0.01, 0.01],
        [0.001, 0.001, 0.001, 0.001, 0.001, 0.001]
      );
      const assessment = layer.detectEscape(state);
      expect(assessment.escaped).toBe(false);
    });

    it('should compute escape velocity bound correctly', () => {
      const layer = new EntropicLayer({ cQuantum: 2.0, n0: 16 });
      const assessment = layer.detectEscape(originState());
      // bound = 2 * 2.0 / sqrt(16) = 4.0 / 4.0 = 1.0
      expect(assessment.escapeVelocityBound).toBeCloseTo(1.0, 6);
    });

    it('should handle tangential velocity (no radial component)', () => {
      const layer = new EntropicLayer();
      // Position along x, velocity along y (perpendicular)
      const state = makeState([0.5, 0, 0, 0, 0, 0], [0, 1.0, 0, 0, 0, 0]);
      const assessment = layer.detectEscape(state);
      expect(assessment.radialVelocity).toBeCloseTo(0, 6);
    });

    it('should handle negative radial velocity (inward motion)', () => {
      const layer = new EntropicLayer();
      // Position outward, velocity inward
      const state = makeState([0.5, 0, 0, 0, 0, 0], [-1.0, 0, 0, 0, 0, 0]);
      const assessment = layer.detectEscape(state);
      expect(assessment.radialVelocity).toBeLessThan(0);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Adaptive K
  // ═══════════════════════════════════════════════════════════════

  describe('adaptiveK', () => {
    it('should return 1 for zero coherence', () => {
      const layer = new EntropicLayer({ baseK: 5 });
      expect(layer.adaptiveK(0)).toBe(1);
    });

    it('should return baseK+1 for full coherence', () => {
      const layer = new EntropicLayer({ baseK: 5 });
      expect(layer.adaptiveK(1.0)).toBe(6);
    });

    it('should clamp coherence to [0,1]', () => {
      const layer = new EntropicLayer({ baseK: 5 });
      expect(layer.adaptiveK(-0.5)).toBe(1); // clamped to 0
      expect(layer.adaptiveK(2.0)).toBe(6); // clamped to 1
    });

    it('should respect MIN_K', () => {
      const layer = new EntropicLayer({ baseK: 0 });
      const k = layer.adaptiveK(0.5);
      expect(k).toBeGreaterThanOrEqual(MIN_K);
    });

    it('should respect MAX_K', () => {
      const layer = new EntropicLayer({ baseK: 100 });
      const k = layer.adaptiveK(1.0);
      expect(k).toBeLessThanOrEqual(MAX_K);
    });

    it('should increase monotonically with coherence', () => {
      const layer = new EntropicLayer({ baseK: 10 });
      let prevK = 0;
      for (let c = 0; c <= 1.0; c += 0.1) {
        const k = layer.adaptiveK(c);
        expect(k).toBeGreaterThanOrEqual(prevK);
        prevK = k;
      }
    });

    it('should produce integer values', () => {
      const layer = new EntropicLayer({ baseK: 7 });
      for (let c = 0; c <= 1.0; c += 0.05) {
        const k = layer.adaptiveK(c);
        expect(Number.isInteger(k)).toBe(true);
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Escape Velocity Bound
  // ═══════════════════════════════════════════════════════════════

  describe('escapeVelocityBoundSatisfied', () => {
    it('should satisfy bound for high k', () => {
      const layer = new EntropicLayer({ cQuantum: 1.0, n0: 100 });
      // bound = 2 * 1.0 / sqrt(100) = 0.2
      expect(layer.escapeVelocityBoundSatisfied(1)).toBe(true);
    });

    it('should not satisfy bound for k below threshold', () => {
      const layer = new EntropicLayer({ cQuantum: 10.0, n0: 1 });
      // bound = 2 * 10.0 / sqrt(1) = 20.0
      expect(layer.escapeVelocityBoundSatisfied(5)).toBe(false);
    });

    it('should be consistent with formula', () => {
      const layer = new EntropicLayer({ cQuantum: 3.0, n0: 9 });
      // bound = 2 * 3.0 / sqrt(9) = 6.0 / 3.0 = 2.0
      expect(layer.escapeVelocityBoundSatisfied(2)).toBe(false); // k = bound, not >
      expect(layer.escapeVelocityBoundSatisfied(3)).toBe(true);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Integration scenarios
  // ═══════════════════════════════════════════════════════════════

  describe('integration', () => {
    it('should combine escape detection with adaptive-k', () => {
      const layer = new EntropicLayer({ baseK: 10, cQuantum: 1.0, n0: 100 });

      // Safe state: low coherence should still satisfy escape velocity
      const assessment = layer.detectEscape(originState());
      const k = layer.adaptiveK(0.5);
      const satisfied = layer.escapeVelocityBoundSatisfied(k);

      expect(assessment.escaped).toBe(false);
      expect(k).toBeGreaterThanOrEqual(1);
      expect(satisfied).toBe(true); // k=6 > 0.2
    });

    it('should flag danger when volume explodes', () => {
      const layer = new EntropicLayer({ maxVolume: 1e-10 });
      // Even small position has volume above tiny threshold
      const state = makeState([0.1, 0.1, 0.1, 0.1, 0.1, 0.1], [0, 0, 0, 0, 0, 0]);
      const assessment = layer.detectEscape(state);
      expect(assessment.escaped).toBe(true);
      expect(assessment.volumeRatio).toBeGreaterThan(1.0);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Constants
  // ═══════════════════════════════════════════════════════════════

  describe('constants', () => {
    it('should have correct default max volume', () => {
      expect(DEFAULT_MAX_VOLUME).toBe(1e6);
    });

    it('should have correct k bounds', () => {
      expect(MIN_K).toBe(1);
      expect(MAX_K).toBe(50);
    });

    it('should have correct default config', () => {
      expect(DEFAULT_ENTROPIC_CONFIG.maxVolume).toBe(1e6);
      expect(DEFAULT_ENTROPIC_CONFIG.baseK).toBe(5);
      expect(DEFAULT_ENTROPIC_CONFIG.cQuantum).toBe(1.0);
      expect(DEFAULT_ENTROPIC_CONFIG.n0).toBe(100);
    });
  });
});
