/**
 * SCBE Layer 9: Spectral Coherence Tests
 *
 * Tests verifying the mathematical properties of spectral coherence:
 * - Parseval's theorem (energy conservation)
 * - Phase invariance
 * - Bounded output [0, 1]
 * - Monotonicity in low-frequency content
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import {
  fft,
  computeSpectralCoherence,
  verifyParseval,
  generateTestSignal,
  generateChirp,
  stft,
  verifySpectralCoherenceBounds,
  checkPhaseInvariance,
  magnitudeSquared,
  Complex
} from '../../src/spectral/index.js';

describe('Layer 9: Spectral Coherence', () => {
  // ============================================================================
  // Core FFT Tests
  // ============================================================================

  describe('FFT Implementation', () => {
    it('should compute FFT of a simple sinusoid', () => {
      const sampleRate = 1000;
      const freq = 50;
      const signal = generateTestSignal(sampleRate, 1, [{ freq, amplitude: 1 }]);

      const X = fft(signal);
      const powerSpectrum = X.map(magnitudeSquared);

      // Find peak frequency
      const halfN = Math.floor(X.length / 2);
      let maxPower = 0;
      let peakIndex = 0;

      for (let i = 0; i < halfN; i++) {
        if (powerSpectrum[i] > maxPower) {
          maxPower = powerSpectrum[i];
          peakIndex = i;
        }
      }

      const peakFreq = peakIndex * sampleRate / X.length;

      // Peak should be near the input frequency (within 2 Hz due to spectral leakage)
      expect(Math.abs(peakFreq - freq)).toBeLessThan(2);
    });

    it('should satisfy conjugate symmetry for real signals', () => {
      const signal = generateTestSignal(1000, 0.5, [
        { freq: 10, amplitude: 1 },
        { freq: 50, amplitude: 0.5 }
      ]);

      const X = fft(signal);
      const N = X.length;

      // For real input, X[k] = conj(X[N-k])
      for (let k = 1; k < N / 2; k++) {
        const conjugate: Complex = { re: X[N - k].re, im: -X[N - k].im };
        expect(Math.abs(X[k].re - conjugate.re)).toBeLessThan(1e-10);
        expect(Math.abs(X[k].im - conjugate.im)).toBeLessThan(1e-10);
      }
    });
  });

  // ============================================================================
  // Parseval's Theorem Tests
  // ============================================================================

  describe("Parseval's Theorem", () => {
    it('should conserve energy between time and frequency domains', () => {
      const signal = generateTestSignal(1000, 1, [
        { freq: 5, amplitude: 1 },
        { freq: 200, amplitude: 0.3 }
      ]);

      const X = fft(signal);
      const { timeEnergy, freqEnergy, relativeError } = verifyParseval(signal, X);

      expect(timeEnergy).toBeGreaterThan(0);
      expect(freqEnergy).toBeGreaterThan(0);
      expect(relativeError).toBeLessThan(0.01); // Within 1%
    });

    it('should hold for random signals (property-based)', () => {
      fc.assert(
        fc.property(
          fc.array(fc.double({ min: -1, max: 1, noNaN: true }), { minLength: 64, maxLength: 256 }),
          (signal) => {
            if (signal.length < 2) return true;

            const X = fft(signal);
            const { relativeError } = verifyParseval(signal, X);

            return relativeError < 0.05; // 5% tolerance for numerical errors
          }
        ),
        { numRuns: 50 }
      );
    });

    it('should work for DC signal (zero frequency)', () => {
      const signal = new Array(256).fill(1.0); // Constant signal
      const X = fft(signal);
      const { timeEnergy, freqEnergy, relativeError } = verifyParseval(signal, X);

      expect(timeEnergy).toBeCloseTo(256, 5);
      expect(relativeError).toBeLessThan(0.01);
    });
  });

  // ============================================================================
  // Spectral Coherence Tests
  // ============================================================================

  describe('Spectral Coherence Computation', () => {
    it('should compute S_spec for low-frequency signal', () => {
      const signal = generateTestSignal(1000, 1, [{ freq: 5, amplitude: 1 }]);
      const result = computeSpectralCoherence(signal, 1000, 50);

      // Low-frequency signal should have high S_spec
      expect(result.S_spec).toBeGreaterThan(0.9);
      expect(verifySpectralCoherenceBounds(result.S_spec)).toBe(true);
    });

    it('should compute S_spec for high-frequency signal', () => {
      const signal = generateTestSignal(1000, 1, [{ freq: 200, amplitude: 1 }]);
      const result = computeSpectralCoherence(signal, 1000, 50);

      // High-frequency signal should have low S_spec
      expect(result.S_spec).toBeLessThan(0.1);
      expect(verifySpectralCoherenceBounds(result.S_spec)).toBe(true);
    });

    it('should compute S_spec for mixed signal', () => {
      const signal = generateTestSignal(1000, 1, [
        { freq: 5, amplitude: 1 },
        { freq: 200, amplitude: 0.3 }
      ]);
      const result = computeSpectralCoherence(signal, 1000, 50);

      // Should be dominated by low-frequency component
      expect(result.S_spec).toBeGreaterThan(0.8);
      expect(result.E_low).toBeGreaterThan(result.E_high);
    });

    it('should always be bounded to [0, 1]', () => {
      fc.assert(
        fc.property(
          fc.array(fc.double({ min: -10, max: 10, noNaN: true }), { minLength: 64, maxLength: 512 }),
          fc.double({ min: 1, max: 500, noNaN: true }),
          (signal, cutoff) => {
            if (signal.length < 2) return true;

            const result = computeSpectralCoherence(signal, 1000, cutoff);
            return result.S_spec >= 0 && result.S_spec <= 1;
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should satisfy energy partition (E_total = E_low + E_high)', () => {
      const signal = generateTestSignal(1000, 1, [
        { freq: 10, amplitude: 1 },
        { freq: 100, amplitude: 0.5 },
        { freq: 300, amplitude: 0.2 }
      ]);
      const result = computeSpectralCoherence(signal, 1000, 50);

      expect(result.E_total).toBeCloseTo(result.E_low + result.E_high, 10);
    });
  });

  // ============================================================================
  // Phase Invariance Tests
  // ============================================================================

  describe('Phase Invariance', () => {
    it('should be invariant to phase shifts', () => {
      const components = [
        { freq: 5, amplitude: 1 },
        { freq: 200, amplitude: 0.3 }
      ];

      const { invariant, maxDifference } = checkPhaseInvariance(
        1000, 1, components, 50, 0.01  // Allow 1% tolerance for windowing effects
      );

      expect(invariant).toBe(true);
      expect(maxDifference).toBeLessThan(0.01);
    });

    it('should produce same S_spec for different phases (property-based)', () => {
      fc.assert(
        fc.property(
          fc.double({ min: 1, max: 100, noNaN: true }),
          fc.double({ min: 0.1, max: 2, noNaN: true }),
          fc.double({ min: 0, max: 2 * Math.PI, noNaN: true }),
          fc.double({ min: 0, max: 2 * Math.PI, noNaN: true }),
          (freq, amp, phase1, phase2) => {
            const signal1 = generateTestSignal(1000, 0.5, [{ freq, amplitude: amp, phase: phase1 }]);
            const signal2 = generateTestSignal(1000, 0.5, [{ freq, amplitude: amp, phase: phase2 }]);

            const result1 = computeSpectralCoherence(signal1, 1000, 50);
            const result2 = computeSpectralCoherence(signal2, 1000, 50);

            return Math.abs(result1.S_spec - result2.S_spec) < 0.01;
          }
        ),
        { numRuns: 50 }
      );
    });
  });

  // ============================================================================
  // Monotonicity Tests
  // ============================================================================

  describe('Monotonicity', () => {
    it('should increase S_spec as low-frequency energy increases', () => {
      const cutoff = 50;
      const results: number[] = [];

      // Gradually increase low-frequency amplitude
      for (let lowAmp = 0.1; lowAmp <= 2.0; lowAmp += 0.3) {
        const signal = generateTestSignal(1000, 1, [
          { freq: 5, amplitude: lowAmp },
          { freq: 200, amplitude: 1 }
        ]);
        const result = computeSpectralCoherence(signal, 1000, cutoff);
        results.push(result.S_spec);
      }

      // Each value should be >= previous (monotonically increasing)
      for (let i = 1; i < results.length; i++) {
        expect(results[i]).toBeGreaterThanOrEqual(results[i - 1] - 0.001);
      }
    });

    it('should decrease S_spec as high-frequency energy increases', () => {
      const cutoff = 50;
      const results: number[] = [];

      // Gradually increase high-frequency amplitude
      for (let highAmp = 0.1; highAmp <= 2.0; highAmp += 0.3) {
        const signal = generateTestSignal(1000, 1, [
          { freq: 5, amplitude: 1 },
          { freq: 200, amplitude: highAmp }
        ]);
        const result = computeSpectralCoherence(signal, 1000, cutoff);
        results.push(result.S_spec);
      }

      // Each value should be <= previous (monotonically decreasing)
      for (let i = 1; i < results.length; i++) {
        expect(results[i]).toBeLessThanOrEqual(results[i - 1] + 0.001);
      }
    });
  });

  // ============================================================================
  // STFT Tests (Layer 14: Audio Axis)
  // ============================================================================

  describe('STFT (Layer 14: Audio Axis)', () => {
    it('should compute time-varying spectral coherence', () => {
      // Generate chirp signal
      const chirp = generateChirp(1000, 1, 10, 200);
      const frames = stft(chirp, 1000, 128, 64, 100);

      expect(frames.length).toBeGreaterThan(0);

      // First frames should have high S_audio (low frequency)
      expect(frames[0].S_audio).toBeGreaterThan(0.5);

      // Last frames should have low S_audio (high frequency)
      expect(frames[frames.length - 1].S_audio).toBeLessThan(0.5);
    });

    it('should show decreasing S_audio for increasing chirp', () => {
      const chirp = generateChirp(1000, 2, 10, 300);
      const frames = stft(chirp, 1000, 256, 128, 100);

      // S_audio should generally decrease over time
      const firstHalf = frames.slice(0, frames.length / 2);
      const secondHalf = frames.slice(frames.length / 2);

      const avgFirst = firstHalf.reduce((s, f) => s + f.S_audio, 0) / firstHalf.length;
      const avgSecond = secondHalf.reduce((s, f) => s + f.S_audio, 0) / secondHalf.length;

      expect(avgFirst).toBeGreaterThan(avgSecond);
    });

    it('should have r_HF + S_audio approximately equal to 1', () => {
      const chirp = generateChirp(1000, 1, 50, 150);
      const frames = stft(chirp, 1000, 128, 64, 100);

      for (const frame of frames) {
        expect(frame.r_HF + frame.S_audio).toBeCloseTo(1, 10);
      }
    });
  });

  // ============================================================================
  // Edge Cases
  // ============================================================================

  describe('Edge Cases', () => {
    it('should handle silent signal (all zeros)', () => {
      const signal = new Array(256).fill(0);
      const result = computeSpectralCoherence(signal, 1000, 50);

      // With epsilon, S_spec should be 0 (no low-frequency energy)
      expect(result.S_spec).toBeCloseTo(0, 5);
      expect(verifySpectralCoherenceBounds(result.S_spec)).toBe(true);
    });

    it('should handle very short signals', () => {
      const signal = [1, -1, 1, -1, 1, -1, 1, -1]; // 8 samples
      const result = computeSpectralCoherence(signal, 1000, 50);

      expect(verifySpectralCoherenceBounds(result.S_spec)).toBe(true);
    });

    it('should handle cutoff at Nyquist frequency', () => {
      const signal = generateTestSignal(1000, 0.5, [{ freq: 100, amplitude: 1 }]);
      const result = computeSpectralCoherence(signal, 1000, 500); // Nyquist = 500 Hz

      // All energy should be "low frequency" relative to Nyquist
      expect(result.S_spec).toBeGreaterThan(0.9);
    });

    it('should handle cutoff at 0 Hz', () => {
      const signal = generateTestSignal(1000, 0.5, [{ freq: 100, amplitude: 1 }]);
      const result = computeSpectralCoherence(signal, 1000, 0);

      // No energy below 0 Hz, so S_spec should be ~0
      expect(result.S_spec).toBeLessThan(0.1);
    });
  });

  // ============================================================================
  // Numerical Stability Tests
  // ============================================================================

  describe('Numerical Stability', () => {
    it('should handle very small amplitudes', () => {
      const signal = generateTestSignal(1000, 0.5, [
        { freq: 10, amplitude: 1e-10 }
      ]);
      const result = computeSpectralCoherence(signal, 1000, 50);

      expect(Number.isFinite(result.S_spec)).toBe(true);
      expect(verifySpectralCoherenceBounds(result.S_spec)).toBe(true);
    });

    it('should handle very large amplitudes', () => {
      const signal = generateTestSignal(1000, 0.5, [
        { freq: 10, amplitude: 1e6 }
      ]);
      const result = computeSpectralCoherence(signal, 1000, 50);

      expect(Number.isFinite(result.S_spec)).toBe(true);
      expect(verifySpectralCoherenceBounds(result.S_spec)).toBe(true);
    });

    it('should produce consistent results across multiple runs', () => {
      const signal = generateTestSignal(1000, 1, [
        { freq: 25, amplitude: 1 },
        { freq: 175, amplitude: 0.5 }
      ]);

      const results = [];
      for (let i = 0; i < 5; i++) {
        results.push(computeSpectralCoherence(signal, 1000, 50).S_spec);
      }

      // All results should be identical
      for (let i = 1; i < results.length; i++) {
        expect(results[i]).toBe(results[0]);
      }
    });
  });
});

// ============================================================================
// Mathematical Property Summary Tests
// ============================================================================

describe('Layer 9 Mathematical Properties Summary', () => {
  it('AC-9.1: Parseval theorem holds', () => {
    const signal = generateTestSignal(1000, 1, [
      { freq: 5, amplitude: 1 },
      { freq: 200, amplitude: 0.3 }
    ]);
    const X = fft(signal);
    const { relativeError } = verifyParseval(signal, X);

    expect(relativeError).toBeLessThan(0.01);
  });

  it('AC-9.2: S_spec is bounded [0, 1]', () => {
    for (let f = 5; f <= 400; f += 50) {
      const signal = generateTestSignal(1000, 0.5, [{ freq: f, amplitude: 1 }]);
      const result = computeSpectralCoherence(signal, 1000, 100);
      expect(verifySpectralCoherenceBounds(result.S_spec)).toBe(true);
    }
  });

  it('AC-9.3: S_spec is phase-invariant', () => {
    const { invariant, maxDifference } = checkPhaseInvariance(
      1000, 1,
      [{ freq: 20, amplitude: 1 }, { freq: 150, amplitude: 0.5 }],
      50,
      0.01  // Allow 1% tolerance for windowing effects
    );
    expect(invariant).toBe(true);
    expect(maxDifference).toBeLessThan(0.01);
  });

  it('AC-9.4: Energy partition is complete (E_total = E_low + E_high)', () => {
    const signal = generateTestSignal(1000, 1, [
      { freq: 10, amplitude: 2 },
      { freq: 200, amplitude: 1 }
    ]);
    const result = computeSpectralCoherence(signal, 1000, 50);

    expect(Math.abs(result.E_total - (result.E_low + result.E_high))).toBeLessThan(1e-10);
  });

  it('AC-9.5: S_spec monotonic in low-frequency content', () => {
    const lowOnly = generateTestSignal(1000, 0.5, [{ freq: 10, amplitude: 1 }]);
    const mixed = generateTestSignal(1000, 0.5, [
      { freq: 10, amplitude: 1 },
      { freq: 200, amplitude: 1 }
    ]);
    const highOnly = generateTestSignal(1000, 0.5, [{ freq: 200, amplitude: 1 }]);

    const sLow = computeSpectralCoherence(lowOnly, 1000, 50).S_spec;
    const sMixed = computeSpectralCoherence(mixed, 1000, 50).S_spec;
    const sHigh = computeSpectralCoherence(highOnly, 1000, 50).S_spec;

    expect(sLow).toBeGreaterThan(sMixed);
    expect(sMixed).toBeGreaterThan(sHigh);
  });
});
