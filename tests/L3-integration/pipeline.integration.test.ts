/**
 * L3-INTEGRATION: Pipeline Integration Tests
 *
 * @tier L3
 * @category integration
 * @description Tests component interactions and system flows
 * @level Senior Developer
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { randomBytes } from 'crypto';
import { computeSpectralCoherence, generateTestSignal, fft } from '../../src/spectral/index.js';
import {
  projectToBall,
  hyperbolicDistance,
  breathTransform,
} from '../../src/harmonic/hyperbolic.js';
import { harmonicScale } from '../../src/harmonic/harmonicScaling.js';

// Helper: Euclidean norm
const norm = (v: number[]): number => Math.sqrt(v.reduce((s, x) => s + x * x, 0));

// Helper: check if point is in ball
const isInBall = (p: number[]): boolean => norm(p) < 1;

// Alias for API compatibility
const poincareEmbed = projectToBall;
const breathingTransform = (p: number[], b: number) => breathTransform(p, 0, { amplitude: 0.05 * b, omega: 1.0 });
import {
  signRoundtable,
  verifyRoundtable,
  clearNonceCache,
  type Keyring
} from '../../src/spiralverse/index.js';

describe('L3-INTEGRATION: System Pipeline Tests', () => {
  describe('RWP Envelope Creation and Verification Flow', () => {
    const testKeyring: Keyring = {
      ko: randomBytes(32),
      av: randomBytes(32),
      ru: randomBytes(32),
      ca: randomBytes(32),
      um: randomBytes(32),
      dr: randomBytes(32),
    };

    beforeEach(() => {
      clearNonceCache();
    });

    it('should create and verify envelope end-to-end', () => {
      const payload = { message: 'Hello, SCBE!', timestamp: Date.now() };
      const envelope = signRoundtable(
        payload,
        'ko',
        'test-aad',
        testKeyring,
        ['ko']
      );

      expect(envelope).toBeDefined();
      expect(envelope.sigs.ko).toBeDefined();
      expect(envelope.nonce).toBeDefined();

      const verified = verifyRoundtable(envelope, testKeyring);
      expect(verified.valid).toBe(true);
    });

    it('should detect payload tampering in pipeline', () => {
      const payload = { message: 'Secure Data', level: 'TOP_SECRET' };
      const envelope = signRoundtable(
        payload,
        'ko',
        'secure-aad',
        testKeyring,
        ['ko', 'um']
      );

      // Tamper with payload (signature won't match)
      const tamperedEnvelope = {
        ...envelope,
        payload: { message: 'HACKED', level: 'COMPROMISED' }
      };

      const verified = verifyRoundtable(tamperedEnvelope, testKeyring);
      expect(verified.valid).toBe(false);
    });
  });

  describe('Spectral Analysis Pipeline', () => {
    it('should process signal through FFT and coherence computation', () => {
      // Generate multi-component signal
      const signal = generateTestSignal(1000, 1, [
        { freq: 10, amplitude: 1 },    // Low frequency
        { freq: 50, amplitude: 0.5 },  // Mid frequency
        { freq: 200, amplitude: 0.3 }  // High frequency
      ]);

      // Run through FFT
      const spectrum = fft(signal);
      expect(spectrum.length).toBeGreaterThan(0);

      // Compute coherence
      const coherence = computeSpectralCoherence(signal, 1000, 100);

      // Verify pipeline outputs
      expect(coherence.S_spec).toBeGreaterThanOrEqual(0);
      expect(coherence.S_spec).toBeLessThanOrEqual(1);
      expect(coherence.E_low).toBeGreaterThan(0);
      expect(coherence.E_high).toBeGreaterThan(0);

      // Verify energy partition
      expect(coherence.E_total).toBeCloseTo(coherence.E_low + coherence.E_high, 5);
    });
  });

  describe('Hyperbolic Geometry Pipeline', () => {
    it('should process vector through Poincaré embedding and distance', () => {
      // Input vectors in Euclidean space
      const v1 = [0.5, 0.3, 0.2];
      const v2 = [0.1, 0.4, 0.3];

      // Embed in Poincaré ball
      const p1 = poincareEmbed(v1);
      const p2 = poincareEmbed(v2);

      // Verify embeddings are in ball
      expect(isInBall(p1)).toBe(true);
      expect(isInBall(p2)).toBe(true);

      // Compute hyperbolic distance
      const dist = hyperbolicDistance(p1, p2);

      // Verify distance properties
      expect(dist).toBeGreaterThanOrEqual(0);
      expect(Number.isFinite(dist)).toBe(true);

      // Self-distance should be zero
      const selfDist = hyperbolicDistance(p1, p1);
      expect(selfDist).toBeCloseTo(0, 10);

      // Symmetry
      const reverseDist = hyperbolicDistance(p2, p1);
      expect(dist).toBeCloseTo(reverseDist, 10);
    });

    it('should apply breathing transform and preserve ball containment', () => {
      const point = [0.3, 0.4, 0.2];
      const embedded = poincareEmbed(point);

      // Apply breathing with different factors
      const expanded = breathingTransform(embedded, 1.5);
      const contracted = breathingTransform(embedded, 0.5);

      // All should remain in ball
      expect(isInBall(embedded)).toBe(true);
      expect(isInBall(expanded)).toBe(true);
      expect(isInBall(contracted)).toBe(true);
    });
  });

  describe('Harmonic Scaling Pipeline', () => {
    it('should scale risk through harmonic function with integer distances', () => {
      // harmonicScale requires d >= 1 integer
      const distances = [1, 2, 3, 4, 5];
      const scaleFactor = Math.E;

      const scaledRisks = distances.map(d => harmonicScale(d, scaleFactor));

      // All scaled values should be finite and positive
      scaledRisks.forEach(scaled => {
        expect(Number.isFinite(scaled)).toBe(true);
        expect(scaled).toBeGreaterThan(0);
      });

      // Monotonically increasing with distance
      for (let i = 1; i < scaledRisks.length; i++) {
        expect(scaledRisks[i]).toBeGreaterThan(scaledRisks[i - 1]);
      }
    });

    it('should amplify risk with different scale factors', () => {
      const distance = 2;

      const scale1 = harmonicScale(distance, 2);
      const scale2 = harmonicScale(distance, 3);

      // Higher scale factor -> higher result
      expect(scale2).toBeGreaterThan(scale1);
    });
  });

  describe('Full 14-Layer Simulation', () => {
    it('should simulate complete pipeline flow', async () => {
      // Layer 1-2: Complex state encoding (simulated)
      const inputVector = [0.3, 0.2, 0.1, 0.4];

      // Layer 3-4: Embedding
      const embedded = poincareEmbed(inputVector);
      expect(isInBall(embedded)).toBe(true);

      // Layer 5: Distance computation
      const origin = [0, 0, 0, 0];
      const distFromOrigin = hyperbolicDistance(embedded, poincareEmbed(origin));

      // Layer 6: Breathing
      const breathed = breathingTransform(embedded, 1.2);
      expect(isInBall(breathed)).toBe(true);

      // Layer 9: Spectral coherence (audio simulation)
      const signal = generateTestSignal(1000, 0.5, [
        { freq: 20, amplitude: 1 },
        { freq: 100, amplitude: 0.3 }
      ]);
      const spectral = computeSpectralCoherence(signal, 1000, 50);

      // Layer 12: Harmonic scaling (requires integer d >= 1)
      const riskScale = harmonicScale(Math.max(1, Math.round(distFromOrigin)), Math.E);

      // Layer 13: Risk decision (simulated)
      const finalRisk = spectral.S_spec * riskScale;
      let decision: string;
      if (finalRisk < 0.3) {
        decision = 'ALLOW';
      } else if (finalRisk < 0.7) {
        decision = 'QUARANTINE';
      } else {
        decision = 'DENY';
      }

      // Verify complete pipeline output
      expect(['ALLOW', 'QUARANTINE', 'DENY']).toContain(decision);
      expect(spectral.S_spec).toBeGreaterThanOrEqual(0);
      expect(spectral.S_spec).toBeLessThanOrEqual(1);
      expect(riskScale).toBeGreaterThanOrEqual(1);
    });
  });

  describe('Multi-Module Interaction', () => {
    it('should maintain data integrity across modules', () => {
      const testKeyring: Keyring = {
        ko: randomBytes(32),
        av: randomBytes(32),
        ru: randomBytes(32),
        ca: randomBytes(32),
        um: randomBytes(32),
        dr: randomBytes(32),
      };
      clearNonceCache();

      // Create envelope with payload containing spectral data
      const signal = generateTestSignal(100, 0.1, [{ freq: 10, amplitude: 1 }]);
      const coherence = computeSpectralCoherence(signal, 100, 20);

      const payload = {
        spectralMetrics: {
          S_spec: coherence.S_spec,
          E_low: coherence.E_low,
          E_high: coherence.E_high
        },
        geometryMetrics: {
          point: [0.2, 0.3, 0.1],
          distance: 0.5
        }
      };

      const envelope = signRoundtable(
        payload,
        'ko',
        'spectral-analysis',
        testKeyring,
        ['ko', 'ca']  // Control + Compute
      );

      // Verify envelope integrity
      const verified = verifyRoundtable(envelope, testKeyring);
      expect(verified.valid).toBe(true);
    });
  });
});
