/**
 * L4-PROPERTY: Spectral Coherence Property Tests
 *
 * @tier L4
 * @category property
 * @description Property-based testing with fast-check
 * @level Staff Engineer
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import {
  computeSpectralCoherence,
  generateTestSignal,
  verifySpectralCoherenceBounds
} from '../../src/spectral/index.js';

describe('L4-PROPERTY: Spectral Coherence Properties', () => {
  describe('S_spec Bounds Property', () => {
    it('S_spec is always in [0, 1] for any valid signal (property)', () => {
      fc.assert(
        fc.property(
          fc.double({ min: 1, max: 400, noNaN: true }),  // frequency
          fc.double({ min: 0.1, max: 5, noNaN: true }),  // amplitude
          fc.double({ min: 10, max: 200, noNaN: true }), // cutoff
          (freq, amplitude, cutoff) => {
            const signal = generateTestSignal(1000, 0.5, [{ freq, amplitude }]);
            const result = computeSpectralCoherence(signal, 1000, cutoff);
            return verifySpectralCoherenceBounds(result.S_spec);
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  describe('Energy Partition Property', () => {
    it('E_total = E_low + E_high (property)', () => {
      fc.assert(
        fc.property(
          fc.double({ min: 10, max: 300, noNaN: true }),
          fc.double({ min: 0.5, max: 3, noNaN: true }),
          (freq, amplitude) => {
            const signal = generateTestSignal(1000, 0.5, [{ freq, amplitude }]);
            const result = computeSpectralCoherence(signal, 1000, 100);
            const error = Math.abs(result.E_total - (result.E_low + result.E_high));
            return error < 1e-10;
          }
        ),
        { numRuns: 50 }
      );
    });
  });

  describe('Monotonicity Property', () => {
    it('Higher cutoff -> higher S_spec for low-freq signals (property)', () => {
      fc.assert(
        fc.property(
          fc.double({ min: 50, max: 150, noNaN: true }),
          fc.double({ min: 150, max: 300, noNaN: true }),
          (cutoff1, cutoff2) => {
            if (cutoff1 >= cutoff2) return true;

            // Low frequency signal (10 Hz)
            const signal = generateTestSignal(1000, 0.5, [{ freq: 10, amplitude: 1 }]);
            const result1 = computeSpectralCoherence(signal, 1000, cutoff1);
            const result2 = computeSpectralCoherence(signal, 1000, cutoff2);

            // Higher cutoff should include more energy in E_low
            return result2.S_spec >= result1.S_spec - 0.01;
          }
        ),
        { numRuns: 50 }
      );
    });
  });
});
