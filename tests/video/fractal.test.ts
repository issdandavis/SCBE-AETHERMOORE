/**
 * Fractal Renderer Tests
 * ======================
 *
 * Tests for Mandelbrot, Julia, and Burning Ship fractal rendering
 * with hyperbolic modulation.
 */

import { describe, it, expect } from 'vitest';
import {
  mandelbrotIteration,
  juliaIteration,
  burningShipIteration,
  modulateFractalParams,
  renderFractalFrame,
  applyColormap,
} from '../../src/video/fractal.js';
import { TONGUE_FRACTAL_CONFIGS } from '../../src/video/types.js';
import type { PoincarePoint, Complex } from '../../src/video/types.js';

describe('Fractal Renderer', () => {
  describe('Mandelbrot Iteration', () => {
    it('should return max iterations for points in main cardioid', () => {
      const c: Complex = { re: 0, im: 0 };
      const result = mandelbrotIteration(c, 100, 2);
      expect(result).toBe(100);
    });

    it('should escape quickly for points far from set', () => {
      const c: Complex = { re: 2, im: 2 };
      const result = mandelbrotIteration(c, 100, 2);
      expect(result).toBeLessThan(10);
    });

    it('should return smooth iteration count at boundary', () => {
      const c: Complex = { re: -0.75, im: 0.1 };
      const result = mandelbrotIteration(c, 100, 2);
      expect(result).toBeGreaterThan(0);
      expect(result).toBeLessThan(100);
      // Should be fractional for smooth coloring
      expect(result % 1).not.toBe(0);
    });

    it('should handle extreme inputs safely', () => {
      // Very large c
      const c1: Complex = { re: 1e10, im: 1e10 };
      expect(() => mandelbrotIteration(c1, 100, 2)).not.toThrow();

      // Negative iterations (should be clamped)
      const c2: Complex = { re: 0, im: 0 };
      const result = mandelbrotIteration(c2, -10, 2);
      expect(result).toBeGreaterThanOrEqual(0);

      // Very high iterations (should be clamped to limit)
      const result2 = mandelbrotIteration(c2, 1e10, 2);
      expect(result2).toBeLessThanOrEqual(10000);
    });

    it('should handle NaN/Infinity inputs', () => {
      const c: Complex = { re: NaN, im: Infinity };
      expect(() => mandelbrotIteration(c, 100, 2)).not.toThrow();
    });
  });

  describe('Julia Iteration', () => {
    it('should return higher iterations for stable regions', () => {
      // Test that points in stable regions iterate longer than unstable ones
      const z0Stable: Complex = { re: 0, im: 0 };
      const z0Unstable: Complex = { re: 1.5, im: 1.5 };
      const c: Complex = { re: -0.4, im: 0.6 };

      const stableResult = juliaIteration(z0Stable, c, 200, 2);
      const unstableResult = juliaIteration(z0Unstable, c, 200, 2);

      // Stable should iterate longer (higher count = more stable)
      expect(stableResult).toBeGreaterThan(unstableResult);
      // Both should be in valid range
      expect(stableResult).toBeGreaterThanOrEqual(0);
      expect(stableResult).toBeLessThanOrEqual(200);
    });

    it('should escape for unstable points', () => {
      const z0: Complex = { re: 1.5, im: 1.5 };
      const c: Complex = { re: -0.4, im: 0.6 };
      const result = juliaIteration(z0, c, 200, 2);
      expect(result).toBeLessThan(50);
    });

    it('should clamp extreme inputs', () => {
      const z0: Complex = { re: 100, im: 100 };
      const c: Complex = { re: 100, im: 100 };
      expect(() => juliaIteration(z0, c, 100, 2)).not.toThrow();
    });
  });

  describe('Burning Ship Iteration', () => {
    it('should converge for points in the set', () => {
      const c: Complex = { re: -1.8, im: 0 };
      const result = burningShipIteration(c, 200, 10);
      expect(result).toBeGreaterThan(50);
    });

    it('should escape for distant points', () => {
      const c: Complex = { re: 5, im: 5 };
      const result = burningShipIteration(c, 100, 2);
      expect(result).toBeLessThan(10);
    });

    it('should produce different results than Mandelbrot', () => {
      const c: Complex = { re: -1.5, im: 0.1 };
      const mandelbrot = mandelbrotIteration(c, 100, 2);
      const burningShip = burningShipIteration(c, 100, 2);
      // They should differ due to absolute value operation
      expect(Math.abs(mandelbrot - burningShip)).toBeGreaterThan(0.01);
    });
  });

  describe('Fractal Parameter Modulation', () => {
    const origin: PoincarePoint = [0, 0, 0, 0, 0, 0];
    const nearBoundary: PoincarePoint = [0.8, 0.3, 0.2, 0.1, 0.1, 0.5];

    it('should not modify parameters when chaos strength is 0', () => {
      const config = TONGUE_FRACTAL_CONFIGS.av;
      const result = modulateFractalParams(config, origin, 0, 0, 0);
      expect(result.c.re).toBeCloseTo(config.c.re, 5);
      expect(result.c.im).toBeCloseTo(config.c.im, 5);
      expect(result.zoom).toBeCloseTo(1, 5);
    });

    it('should increase zoom for points near boundary', () => {
      const config = TONGUE_FRACTAL_CONFIGS.av;
      const result = modulateFractalParams(config, nearBoundary, 0.5, 0, 0);
      expect(result.zoom).toBeGreaterThan(1);
    });

    it('should return valid modulated parameters', () => {
      const config = TONGUE_FRACTAL_CONFIGS.av;
      // Test that modulation returns valid parameters
      const result = modulateFractalParams(config, nearBoundary, 0.5, 0.1, 0.25);

      // Check c is valid
      expect(Number.isFinite(result.c.re)).toBe(true);
      expect(Number.isFinite(result.c.im)).toBe(true);

      // Check zoom is positive
      expect(result.zoom).toBeGreaterThan(0);

      // Check rotation is finite
      expect(Number.isFinite(result.rotation)).toBe(true);
    });

    it('should clamp breathing amplitude to A4 spec', () => {
      const config = TONGUE_FRACTAL_CONFIGS.av;
      // Even with extreme amplitude, should be bounded
      const result = modulateFractalParams(config, nearBoundary, 0.5, 10, 0);
      expect(result.zoom).toBeLessThan(10); // Bounded result
    });

    it('should return valid c parameter', () => {
      const config = TONGUE_FRACTAL_CONFIGS.ru;
      const result = modulateFractalParams(config, nearBoundary, 1, 0.1, 5);
      expect(Number.isFinite(result.c.re)).toBe(true);
      expect(Number.isFinite(result.c.im)).toBe(true);
      // Magnitude should be bounded
      const mag = Math.sqrt(result.c.re ** 2 + result.c.im ** 2);
      expect(mag).toBeLessThanOrEqual(4);
    });
  });

  describe('Frame Rendering', () => {
    it('should render frame with correct dimensions', () => {
      const config = TONGUE_FRACTAL_CONFIGS.ko;
      const state: PoincarePoint = [0.1, 0.1, 0, 0, 0.5, 0];
      const frame = renderFractalFrame(100, 100, config, state, 0.3, 0.05, 0);
      expect(frame.length).toBe(100 * 100);
    });

    it('should return normalized values in [0, 1]', () => {
      const config = TONGUE_FRACTAL_CONFIGS.av;
      const state: PoincarePoint = [0, 0, 0, 0, 0, 0];
      const frame = renderFractalFrame(50, 50, config, state, 0.2, 0, 0);

      for (const val of frame) {
        expect(val).toBeGreaterThanOrEqual(0);
        expect(val).toBeLessThanOrEqual(1);
      }
    });

    it('should clamp dimensions to safe limits', () => {
      const config = TONGUE_FRACTAL_CONFIGS.ko;
      const state: PoincarePoint = [0, 0, 0, 0, 0, 0];

      // Very large dimensions should be clamped
      const frame = renderFractalFrame(10000, 10000, config, state, 0, 0, 0);
      expect(frame.length).toBeLessThanOrEqual(4096 * 4096);

      // Zero dimensions should become 1
      const frame2 = renderFractalFrame(0, 0, config, state, 0, 0, 0);
      expect(frame2.length).toBe(1);
    });

    it('should produce different results for different tongues', () => {
      const state: PoincarePoint = [0.3, 0.2, 0.1, 0, 0.5, 0.1];
      const koFrame = renderFractalFrame(30, 30, TONGUE_FRACTAL_CONFIGS.ko, state, 0.3, 0.05, 0);
      const ruFrame = renderFractalFrame(30, 30, TONGUE_FRACTAL_CONFIGS.ru, state, 0.3, 0.05, 0);

      // Compute average to compare
      const koAvg = Array.from(koFrame).reduce((a, b) => a + b, 0) / koFrame.length;
      const ruAvg = Array.from(ruFrame).reduce((a, b) => a + b, 0) / ruFrame.length;

      expect(Math.abs(koAvg - ruAvg)).toBeGreaterThan(0.01);
    });
  });

  describe('Colormap Application', () => {
    const testNormalized = new Float32Array([0, 0.25, 0.5, 0.75, 1.0]);

    it('should return RGBA data with correct length', () => {
      const rgba = applyColormap(testNormalized, 'plasma', 5, 1);
      expect(rgba.length).toBe(5 * 4); // 5 pixels * 4 channels
    });

    it('should set alpha to 255 for all pixels', () => {
      const rgba = applyColormap(testNormalized, 'viridis', 5, 1);
      for (let i = 0; i < 5; i++) {
        expect(rgba[i * 4 + 3]).toBe(255);
      }
    });

    it('should produce valid RGB values', () => {
      const colormaps = ['plasma', 'viridis', 'inferno', 'magma', 'bone', 'twilight'];

      for (const colormap of colormaps) {
        const rgba = applyColormap(testNormalized, colormap, 5, 1);
        for (let i = 0; i < rgba.length; i++) {
          expect(rgba[i]).toBeGreaterThanOrEqual(0);
          expect(rgba[i]).toBeLessThanOrEqual(255);
        }
      }
    });

    it('should produce different colors for different values', () => {
      const rgba = applyColormap(testNormalized, 'plasma', 5, 1);

      // First and last pixels should be different
      const first = [rgba[0], rgba[1], rgba[2]];
      const last = [rgba[16], rgba[17], rgba[18]];

      const diff = Math.abs(first[0] - last[0]) + Math.abs(first[1] - last[1]) + Math.abs(first[2] - last[2]);
      expect(diff).toBeGreaterThan(0);
    });

    it('should handle unknown colormap gracefully', () => {
      const rgba = applyColormap(testNormalized, 'unknown_colormap', 5, 1);
      expect(rgba.length).toBe(20);
      // Should fall back to grayscale
      expect(rgba[0]).toBe(0); // t=0 -> black
      expect(rgba[16]).toBe(255); // t=1 -> white
    });
  });
});
