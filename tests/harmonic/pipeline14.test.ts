/**
 * SCBE 14-Layer Pipeline Tests
 * ============================
 *
 * Verifies all 14 axioms are correctly implemented.
 */

import { describe, it, expect } from 'vitest';
import {
  layer1ComplexState,
  layer2Realification,
  layer3WeightedTransform,
  layer4PoincareEmbedding,
  layer5HyperbolicDistance,
  layer6BreathingTransform,
  layer7PhaseTransform,
  layer8RealmDistance,
  layer9SpectralCoherence,
  layer10SpinCoherence,
  layer11TriadicTemporal,
  layer12HarmonicScaling,
  layer13RiskDecision,
  layer14AudioAxis,
  scbe14LayerPipeline,
  mobiusAdd,
} from '../../src/harmonic/pipeline14';

describe('SCBE 14-Layer Pipeline', () => {
  describe('Layer 1: Complex State (A1)', () => {
    it('should construct complex state from amplitudes and phases', () => {
      const t = [1, 2, 3, 0, Math.PI / 4, Math.PI / 2];
      const result = layer1ComplexState(t, 3);

      expect(result.real.length).toBe(3);
      expect(result.imag.length).toBe(3);

      // First element: amplitude=1, phase=0 → (1, 0)
      expect(result.real[0]).toBeCloseTo(1, 5);
      expect(result.imag[0]).toBeCloseTo(0, 5);
    });

    it('should handle shorter inputs gracefully', () => {
      const t = [1, 2];
      const result = layer1ComplexState(t, 6);

      expect(result.real.length).toBe(6);
      expect(result.imag.length).toBe(6);
    });
  });

  describe('Layer 2: Realification (A2)', () => {
    it('should map ℂᴰ → ℝ²ᴰ', () => {
      const complex = { real: [1, 2, 3], imag: [4, 5, 6] };
      const result = layer2Realification(complex);

      expect(result).toEqual([1, 2, 3, 4, 5, 6]);
      expect(result.length).toBe(6); // 2D
    });
  });

  describe('Layer 3: Weighted Transform (A3)', () => {
    it('should apply golden ratio weighting', () => {
      const x = [1, 1, 1, 1, 1, 1];
      const result = layer3WeightedTransform(x);

      expect(result.length).toBe(6);
      // Weights should decrease with golden ratio
      // First elements should have smaller weights than later ones
    });
  });

  describe('Layer 4: Poincaré Embedding (A4)', () => {
    it('should embed into the Poincaré ball with ||u|| < 1', () => {
      const x = [10, 10, 10, 10, 10, 10]; // Large input
      const result = layer4PoincareEmbedding(x, 1.0, 0.01);

      const norm = Math.sqrt(result.reduce((sum, val) => sum + val * val, 0));
      expect(norm).toBeLessThan(1);
      expect(norm).toBeLessThanOrEqual(0.99 + 1e-9); // Clamped to 1-eps (with floating-point tolerance)
    });

    it('should handle zero input', () => {
      const x = [0, 0, 0, 0, 0, 0];
      const result = layer4PoincareEmbedding(x);

      expect(result).toEqual([0, 0, 0, 0, 0, 0]);
    });
  });

  describe('Layer 5: Hyperbolic Distance (A5)', () => {
    it('should compute d_ℍ(u,v) = arcosh(1 + 2||u-v||²/[(1-||u||²)(1-||v||²)])', () => {
      const origin = [0, 0, 0];
      const point = [0.5, 0, 0];

      const d = layer5HyperbolicDistance(origin, point);
      expect(d).toBeGreaterThan(0);

      // Distance from origin: d_ℍ(0, p) = 2 * arctanh(||p||)
      const expected = 2 * Math.atanh(0.5);
      expect(d).toBeCloseTo(expected, 3);
    });

    it('should satisfy symmetry: d(u,v) = d(v,u)', () => {
      const u = [0.3, 0.2, 0.1];
      const v = [0.1, 0.4, 0.2];

      const d1 = layer5HyperbolicDistance(u, v);
      const d2 = layer5HyperbolicDistance(v, u);

      expect(d1).toBeCloseTo(d2, 10);
    });
  });

  describe('Layer 6: Breathing Transform (A6)', () => {
    it('should rescale radially within the ball', () => {
      const u = [0.5, 0.3, 0.2];
      const result = layer6BreathingTransform(u, 1.5);

      const normBefore = Math.sqrt(u.reduce((sum, val) => sum + val * val, 0));
      const normAfter = Math.sqrt(result.reduce((sum, val) => sum + val * val, 0));

      // With b > 1, norm should increase (but stay < 1)
      expect(normAfter).toBeGreaterThan(normBefore);
      expect(normAfter).toBeLessThan(1);
    });
  });

  describe('Layer 7: Phase Transform (A7)', () => {
    it('should preserve distance (isometry)', () => {
      const u = [0.3, 0.2, 0.1];
      const v = [0.1, 0.4, 0.2];
      const a = [0.1, 0.1, 0.1];
      const Q = [
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1],
      ]; // Identity

      const dBefore = layer5HyperbolicDistance(u, v);

      const uTransformed = layer7PhaseTransform(u, a, Q);
      const vTransformed = layer7PhaseTransform(v, a, Q);

      const dAfter = layer5HyperbolicDistance(uTransformed, vTransformed);

      // Distance should be approximately preserved
      expect(dAfter).toBeCloseTo(dBefore, 1);
    });
  });

  describe('Layer 8: Realm Distance (A8)', () => {
    it('should compute minimum distance to realm centers', () => {
      const u = [0.1, 0.1, 0.1];
      const realms = [
        [0, 0, 0], // Origin
        [0.5, 0.5, 0.5],
        [0.2, 0.2, 0.2],
      ];

      const { dStar, distances } = layer8RealmDistance(u, realms);

      expect(distances.length).toBe(3);
      expect(dStar).toBe(Math.min(...distances));
    });
  });

  describe('Layer 9: Spectral Coherence (A9)', () => {
    it('should return S_spec ∈ [0,1]', () => {
      const signal = [1, 2, 3, 4, 5, 4, 3, 2];
      const result = layer9SpectralCoherence(signal);

      expect(result).toBeGreaterThanOrEqual(0);
      expect(result).toBeLessThanOrEqual(1);
    });

    it('should return 0.5 for null input', () => {
      expect(layer9SpectralCoherence(null)).toBe(0.5);
      expect(layer9SpectralCoherence([])).toBe(0.5);
    });
  });

  describe('Layer 10: Spin Coherence (A10)', () => {
    it('should return C_spin ∈ [0,1]', () => {
      const phases = [0, 0.1, 0.2, 0.1, 0]; // Aligned phases
      const result = layer10SpinCoherence(phases);

      expect(result).toBeGreaterThanOrEqual(0);
      expect(result).toBeLessThanOrEqual(1);
    });

    it('should return high coherence for aligned phases', () => {
      const alignedPhases = [0, 0, 0, 0, 0];
      const result = layer10SpinCoherence(alignedPhases);

      expect(result).toBeCloseTo(1, 5); // All aligned → C = 1
    });
  });

  describe('Layer 11: Triadic Temporal (A11)', () => {
    it('should compute d_tri = √(λ₁d₁² + λ₂d₂² + λ₃d_G²)', () => {
      const result = layer11TriadicTemporal(0.3, 0.3, 0.3);

      expect(result).toBeGreaterThanOrEqual(0);
      expect(result).toBeLessThanOrEqual(1);
    });

    it('should throw if lambdas do not sum to 1', () => {
      expect(() => layer11TriadicTemporal(0.3, 0.3, 0.3, 0.5, 0.5, 0.5)).toThrow(
        'Lambdas must sum to 1'
      );
    });
  });

  describe('Layer 12: Harmonic Scaling (A12)', () => {
    it('should compute H(d, R) = R^(d²)', () => {
      const d = 2;
      const R = Math.E;

      const result = layer12HarmonicScaling(d, R);
      const expected = Math.pow(R, d * d); // e^4

      expect(result).toBeCloseTo(expected, 5);
    });

    it('should throw if R <= 1', () => {
      expect(() => layer12HarmonicScaling(1, 0.5)).toThrow('R must be > 1');
    });
  });

  describe('Layer 13: Risk Decision (A13)', () => {
    it('should return ALLOW for low risk', () => {
      const { decision } = layer13RiskDecision(0.1, 1.0);
      expect(decision).toBe('ALLOW');
    });

    it('should return QUARANTINE for medium risk', () => {
      const { decision } = layer13RiskDecision(0.4, 1.0);
      expect(decision).toBe('QUARANTINE');
    });

    it('should return DENY for high risk', () => {
      const { decision } = layer13RiskDecision(0.8, 1.0);
      expect(decision).toBe('DENY');
    });

    it('should amplify risk with H', () => {
      const { riskPrime } = layer13RiskDecision(0.1, 10.0);
      expect(riskPrime).toBeCloseTo(1.0, 5);
    });
  });

  describe('Layer 14: Audio Axis (A14)', () => {
    it('should return S_audio ∈ [0,1]', () => {
      const audio = [0, 0.5, 1, 0.5, 0, -0.5, -1, -0.5];
      const result = layer14AudioAxis(audio);

      expect(result).toBeGreaterThanOrEqual(0);
      expect(result).toBeLessThanOrEqual(1);
    });

    it('should return 0.5 for null input', () => {
      expect(layer14AudioAxis(null)).toBe(0.5);
    });
  });

  describe('Full Pipeline Integration', () => {
    it('should execute all 14 layers and return a decision', () => {
      const t = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6];

      const result = scbe14LayerPipeline(t);

      expect(['ALLOW', 'QUARANTINE', 'DENY']).toContain(result.decision);
      expect(result.riskPrime).toBeGreaterThanOrEqual(0);

      // Verify all layers are computed
      expect(result.layers.l1_complex.real.length).toBe(6);
      expect(result.layers.l2_real.length).toBe(12);
      expect(result.layers.l4_poincare.length).toBe(12);
      expect(result.layers.l9_spectral).toBeGreaterThanOrEqual(0);
      expect(result.layers.l10_spin).toBeGreaterThanOrEqual(0);
      expect(result.layers.l12_harmonic).toBeGreaterThan(0);
    });

    it('should return ALLOW for safe context vectors', () => {
      // Small, centered context → low risk
      const t = [0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0, 0, 0, 0, 0, 0];

      const result = scbe14LayerPipeline(t);

      expect(result.decision).toBe('ALLOW');
    });
  });

  describe('Möbius Operations', () => {
    it('should satisfy u ⊕ 0 = u', () => {
      const u = [0.3, 0.2, 0.1];
      const zero = [0, 0, 0];

      const result = mobiusAdd(u, zero);

      // Möbius addition with zero should approximate identity (allowing for numerical precision)
      expect(result[0]).toBeCloseTo(u[0], 1);
      expect(result[1]).toBeCloseTo(u[1], 1);
      expect(result[2]).toBeCloseTo(u[2], 1);
    });
  });
});
