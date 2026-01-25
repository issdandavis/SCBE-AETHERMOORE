/**
 * L2-UNIT: Spectral Coherence Unit Tests
 *
 * @tier L2
 * @category unit
 * @module spectral
 * @axiom 9 (Spectral Coherence)
 * @description Tests individual functions in isolation
 * @level Junior Developer
 */

import { describe, it, expect } from 'vitest';
import {
  fft,
  magnitudeSquared,
  fftFrequencies,
  computeSpectralCoherence,
  generateTestSignal,
  verifySpectralCoherenceBounds,
  type Complex
} from '../../src/spectral/index.js';

describe('L2-UNIT: Spectral Coherence', () => {
  describe('FFT Function', () => {
    it('should return complex array for real input', () => {
      const signal = [1, 0, -1, 0];
      const result = fft(signal);

      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBeGreaterThanOrEqual(signal.length);
      result.forEach(c => {
        expect(typeof c.re).toBe('number');
        expect(typeof c.im).toBe('number');
      });
    });

    it('should handle power-of-2 input correctly', () => {
      const signal = [1, 2, 3, 4, 5, 6, 7, 8];
      const result = fft(signal);
      expect(result.length).toBe(8);
    });

    it('should pad non-power-of-2 input', () => {
      const signal = [1, 2, 3, 4, 5]; // 5 elements
      const result = fft(signal);
      expect(result.length).toBe(8); // Padded to 8
    });

    it('should handle DC signal (all ones)', () => {
      const signal = [1, 1, 1, 1];
      const result = fft(signal);
      // DC component should have all energy
      expect(magnitudeSquared(result[0])).toBeGreaterThan(0);
    });

    it('should handle alternating signal', () => {
      const signal = [1, -1, 1, -1];
      const result = fft(signal);
      // Nyquist component should have energy
      expect(result.length).toBe(4);
    });
  });

  describe('magnitudeSquared Function', () => {
    it('should compute |z|^2 for complex number', () => {
      const c: Complex = { re: 3, im: 4 };
      expect(magnitudeSquared(c)).toBe(25); // 3^2 + 4^2 = 25
    });

    it('should return 0 for zero complex', () => {
      const c: Complex = { re: 0, im: 0 };
      expect(magnitudeSquared(c)).toBe(0);
    });

    it('should handle purely real numbers', () => {
      const c: Complex = { re: 5, im: 0 };
      expect(magnitudeSquared(c)).toBe(25);
    });

    it('should handle purely imaginary numbers', () => {
      const c: Complex = { re: 0, im: 7 };
      expect(magnitudeSquared(c)).toBe(49);
    });

    it('should handle negative values', () => {
      const c: Complex = { re: -3, im: -4 };
      expect(magnitudeSquared(c)).toBe(25);
    });
  });

  describe('fftFrequencies Function', () => {
    it('should return correct frequency bins', () => {
      const N = 8;
      const sampleRate = 1000;
      const freqs = fftFrequencies(N, sampleRate);

      expect(freqs.length).toBe(N);
      expect(freqs[0]).toBe(0); // DC
      expect(freqs[1]).toBe(125); // 1000/8
    });

    it('should include negative frequencies', () => {
      const freqs = fftFrequencies(8, 1000);
      // Second half should be negative frequencies
      expect(freqs[5]).toBeLessThan(0);
      expect(freqs[6]).toBeLessThan(0);
      expect(freqs[7]).toBeLessThan(0);
    });
  });

  describe('generateTestSignal Function', () => {
    it('should generate signal with correct length', () => {
      const signal = generateTestSignal(1000, 1, [{ freq: 100, amplitude: 1 }]);
      expect(signal.length).toBe(1000); // 1000 Hz * 1 second
    });

    it('should generate silent signal for zero amplitude', () => {
      const signal = generateTestSignal(100, 0.1, [{ freq: 10, amplitude: 0 }]);
      signal.forEach(s => expect(s).toBe(0));
    });

    it('should combine multiple components', () => {
      const signal = generateTestSignal(1000, 0.1, [
        { freq: 100, amplitude: 1 },
        { freq: 200, amplitude: 0.5 }
      ]);
      expect(signal.length).toBe(100);
      // Signal should have non-zero values
      expect(Math.max(...signal.map(Math.abs))).toBeGreaterThan(0);
    });

    it('should handle frequency components correctly', () => {
      const signal1 = generateTestSignal(100, 0.1, [{ freq: 10, amplitude: 1 }]);
      const signal2 = generateTestSignal(100, 0.1, [{ freq: 50, amplitude: 1 }]);

      // Different frequencies should produce different signals
      const diff = signal1.some((v, i) => Math.abs(v - signal2[i]) > 0.001);
      expect(diff).toBe(true);
    });
  });

  describe('computeSpectralCoherence Function', () => {
    it('should return S_spec in [0, 1]', () => {
      const signal = generateTestSignal(1000, 1, [{ freq: 100, amplitude: 1 }]);
      const result = computeSpectralCoherence(signal, 1000, 200);

      expect(result.S_spec).toBeGreaterThanOrEqual(0);
      expect(result.S_spec).toBeLessThanOrEqual(1);
    });

    it('should return high S_spec for low-frequency signal', () => {
      const signal = generateTestSignal(1000, 1, [{ freq: 10, amplitude: 1 }]);
      const result = computeSpectralCoherence(signal, 1000, 100);

      expect(result.S_spec).toBeGreaterThan(0.5);
    });

    it('should return low S_spec for high-frequency signal', () => {
      const signal = generateTestSignal(1000, 1, [{ freq: 400, amplitude: 1 }]);
      const result = computeSpectralCoherence(signal, 1000, 100);

      expect(result.S_spec).toBeLessThan(0.5);
    });

    it('should partition energy completely', () => {
      const signal = generateTestSignal(1000, 1, [{ freq: 50, amplitude: 1 }]);
      const result = computeSpectralCoherence(signal, 1000, 100);

      expect(result.E_total).toBeCloseTo(result.E_low + result.E_high, 10);
    });

    it('should return power spectrum array', () => {
      const signal = generateTestSignal(1000, 0.5, [{ freq: 100, amplitude: 1 }]);
      const result = computeSpectralCoherence(signal, 1000, 200);

      expect(Array.isArray(result.powerSpectrum)).toBe(true);
      expect(result.powerSpectrum.length).toBeGreaterThan(0);
    });

    it('should return frequency array', () => {
      const signal = generateTestSignal(1000, 0.5, [{ freq: 100, amplitude: 1 }]);
      const result = computeSpectralCoherence(signal, 1000, 200);

      expect(Array.isArray(result.frequencies)).toBe(true);
      expect(result.frequencies[0]).toBe(0); // DC component
    });
  });

  describe('verifySpectralCoherenceBounds Function', () => {
    it('should return true for valid S_spec', () => {
      expect(verifySpectralCoherenceBounds(0)).toBe(true);
      expect(verifySpectralCoherenceBounds(0.5)).toBe(true);
      expect(verifySpectralCoherenceBounds(1)).toBe(true);
    });

    it('should return false for S_spec < 0', () => {
      expect(verifySpectralCoherenceBounds(-0.1)).toBe(false);
      expect(verifySpectralCoherenceBounds(-1)).toBe(false);
    });

    it('should return false for S_spec > 1', () => {
      expect(verifySpectralCoherenceBounds(1.1)).toBe(false);
      expect(verifySpectralCoherenceBounds(2)).toBe(false);
    });
  });
});
