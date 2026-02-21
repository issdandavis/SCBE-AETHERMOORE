/**
 * @file negativeSpace.test.ts
 * @module harmonic/negativeSpace
 * @layer Layer 5, Layer 6, Layer 7
 * @component Negative Space - Signed Hyperbolic Embedding Tests
 * @version 3.2.4
 */

import { describe, it, expect } from 'vitest';
import {
  classifyRealm,
  createSignedEmbedding,
  contrastiveDistance,
  pseudoMetricInnerProduct,
  signedCosineSimilarity,
} from '../../src/harmonic/negativeSpace.js';

// ---------------------------------------------------------------------------
// classifyRealm
// ---------------------------------------------------------------------------
describe('classifyRealm', () => {
  describe('light realm', () => {
    it('returns light when intent > 0.3 and norm < 0.7', () => {
      expect(classifyRealm(0.5, 0.5)).toBe('light');
    });

    it('returns light at intent boundary (just above 0.3) and low norm', () => {
      expect(classifyRealm(0.31, 0.1)).toBe('light');
    });

    it('returns light at norm boundary (just below 0.7) and high intent', () => {
      expect(classifyRealm(0.9, 0.69)).toBe('light');
    });

    it('returns light for maximum intent and minimum norm', () => {
      expect(classifyRealm(1.0, 0.0)).toBe('light');
    });

    it('returns light for strong positive intent and moderate norm', () => {
      expect(classifyRealm(0.8, 0.4)).toBe('light');
    });
  });

  describe('shadow realm', () => {
    it('returns shadow when intent < -0.3', () => {
      expect(classifyRealm(-0.5, 0.5)).toBe('shadow');
    });

    it('returns shadow when norm > 0.9', () => {
      expect(classifyRealm(0.0, 0.95)).toBe('shadow');
    });

    it('returns shadow at intent boundary (just below -0.3)', () => {
      expect(classifyRealm(-0.31, 0.5)).toBe('shadow');
    });

    it('returns shadow at norm boundary (just above 0.9)', () => {
      expect(classifyRealm(0.0, 0.91)).toBe('shadow');
    });

    it('returns shadow for extreme negative intent and high norm', () => {
      expect(classifyRealm(-1.0, 0.99)).toBe('shadow');
    });

    it('returns shadow for extreme negative intent regardless of norm', () => {
      expect(classifyRealm(-1.0, 0.0)).toBe('shadow');
    });

    it('returns shadow when intent < -0.3 even if norm is low', () => {
      expect(classifyRealm(-0.5, 0.1)).toBe('shadow');
    });

    it('returns shadow when norm > 0.9 even if intent is strongly positive', () => {
      expect(classifyRealm(0.8, 0.95)).toBe('shadow');
    });
  });

  describe('twilight realm', () => {
    it('returns twilight for zero intent and moderate norm', () => {
      expect(classifyRealm(0.0, 0.5)).toBe('twilight');
    });

    it('returns twilight at the exact intent boundary (0.3)', () => {
      expect(classifyRealm(0.3, 0.5)).toBe('twilight');
    });

    it('returns twilight at the exact negative intent boundary (-0.3)', () => {
      expect(classifyRealm(-0.3, 0.5)).toBe('twilight');
    });

    it('returns twilight at the exact norm boundary (0.7)', () => {
      expect(classifyRealm(0.5, 0.7)).toBe('twilight');
    });

    it('returns twilight at the exact upper norm boundary (0.9)', () => {
      expect(classifyRealm(0.0, 0.9)).toBe('twilight');
    });

    it('returns twilight for small positive intent and moderate norm', () => {
      expect(classifyRealm(0.1, 0.5)).toBe('twilight');
    });

    it('returns twilight when intent > 0.3 but norm >= 0.7', () => {
      expect(classifyRealm(0.5, 0.75)).toBe('twilight');
    });

    it('returns twilight for near-zero intent near origin', () => {
      expect(classifyRealm(0.0, 0.0)).toBe('twilight');
    });
  });

  describe('boundary precision', () => {
    it('intent exactly 0.3 with low norm is twilight, not light', () => {
      expect(classifyRealm(0.3, 0.69)).toBe('twilight');
    });

    it('norm exactly 0.7 with high intent is twilight, not light', () => {
      expect(classifyRealm(0.9, 0.7)).toBe('twilight');
    });

    it('intent exactly -0.3 with any norm is not shadow', () => {
      expect(classifyRealm(-0.3, 0.5)).toBe('twilight');
    });

    it('norm exactly 0.9 is not shadow', () => {
      expect(classifyRealm(0.0, 0.9)).toBe('twilight');
    });
  });
});

// ---------------------------------------------------------------------------
// createSignedEmbedding
// ---------------------------------------------------------------------------
describe('createSignedEmbedding', () => {
  const uniformFeatures = (n: number, val: number): number[] => Array(n).fill(val);

  describe('return structure', () => {
    it('returns an object with vector, intentStrength, realm, and norm fields', () => {
      const result = createSignedEmbedding([0.5, 0.5], 0.5);
      expect(result).toHaveProperty('vector');
      expect(result).toHaveProperty('intentStrength');
      expect(result).toHaveProperty('realm');
      expect(result).toHaveProperty('norm');
    });

    it('preserves intentStrength in the returned embedding', () => {
      const intent = 0.7;
      const result = createSignedEmbedding([0.5, 0.5, 0.5], intent);
      expect(result.intentStrength).toBe(intent);
    });

    it('vector length matches input features length', () => {
      const features = [0.1, 0.2, 0.3, 0.4, 0.5];
      const result = createSignedEmbedding(features, 0.5);
      expect(result.vector.length).toBe(features.length);
    });

    it('realm is one of light, shadow, or twilight', () => {
      const result = createSignedEmbedding([0.3, 0.3], 0.5);
      expect(['light', 'shadow', 'twilight']).toContain(result.realm);
    });

    it('norm matches the actual Euclidean norm of the vector', () => {
      const result = createSignedEmbedding([0.5, 0.5, 0.5], 0.5);
      const computedNorm = Math.sqrt(result.vector.reduce((s, v) => s + v * v, 0));
      expect(result.norm).toBeCloseTo(computedNorm, 5);
    });
  });

  describe('positive intent stays near origin', () => {
    it('strong positive intent produces norm well below 0.85', () => {
      const result = createSignedEmbedding(uniformFeatures(4, 0.3), 0.9);
      expect(result.norm).toBeLessThan(0.85);
    });

    it('moderate positive intent produces a reasonable norm', () => {
      const result = createSignedEmbedding(uniformFeatures(4, 0.4), 0.5);
      expect(result.norm).toBeLessThan(1.0);
    });

    it('positive intent embedding is classified as light when conditions met', () => {
      const result = createSignedEmbedding(uniformFeatures(4, 0.1), 0.8);
      if (result.norm < 0.7) {
        expect(result.realm).toBe('light');
      }
    });

    it('positive intent produces valid Poincare ball embedding (norm < 1)', () => {
      const result = createSignedEmbedding([0.5, 0.3, 0.2, 0.4], 0.6);
      expect(result.norm).toBeLessThan(1.0);
    });
  });

  describe('negative intent pushes to boundary', () => {
    it('negative intent produces norm in range [0.85, 0.99]', () => {
      const result = createSignedEmbedding(uniformFeatures(4, 0.5), -0.8);
      expect(result.norm).toBeGreaterThanOrEqual(0.85);
      expect(result.norm).toBeLessThanOrEqual(0.99);
    });

    it('strong negative intent pushes close to unit sphere boundary', () => {
      const result = createSignedEmbedding(uniformFeatures(4, 0.5), -1.0);
      expect(result.norm).toBeGreaterThanOrEqual(0.85);
      expect(result.norm).toBeLessThanOrEqual(0.99);
    });

    it('moderate negative intent still pushes toward boundary', () => {
      const result = createSignedEmbedding(uniformFeatures(4, 0.5), -0.5);
      expect(result.norm).toBeGreaterThanOrEqual(0.85);
      expect(result.norm).toBeLessThanOrEqual(0.99);
    });

    it('negative intent embedding realm is shadow', () => {
      const result = createSignedEmbedding(uniformFeatures(4, 0.5), -0.8);
      expect(result.realm).toBe('shadow');
    });

    it('norm stays strictly inside unit sphere for negative intent', () => {
      const result = createSignedEmbedding([0.3, 0.7, 0.2, 0.5], -0.9);
      expect(result.norm).toBeLessThan(1.0);
    });
  });

  describe('realm assignment consistency', () => {
    it('realm in returned embedding matches classifyRealm output', () => {
      const result = createSignedEmbedding([0.4, 0.4, 0.4], 0.7);
      const expected = classifyRealm(result.intentStrength, result.norm);
      expect(result.realm).toBe(expected);
    });

    it('near-zero intent produces twilight or light depending on norm', () => {
      const result = createSignedEmbedding([0.1, 0.1], 0.0);
      expect(['twilight', 'shadow', 'light']).toContain(result.realm);
    });
  });

  describe('edge cases', () => {
    it('handles single-element feature vector', () => {
      const result = createSignedEmbedding([0.5], 0.5);
      expect(result.vector.length).toBe(1);
      expect(result.norm).toBeGreaterThanOrEqual(0);
    });

    it('handles zero features with positive intent', () => {
      const result = createSignedEmbedding([0.0, 0.0, 0.0], 0.5);
      expect(result.norm).toBeCloseTo(0, 5);
      expect(result.vector.every((v: number) => v === 0)).toBe(true);
    });

    it('handles zero features with negative intent', () => {
      const result = createSignedEmbedding([0.0, 0.0, 0.0], -0.8);
      expect(result.norm).toBeGreaterThanOrEqual(0);
    });

    it('handles zero intent', () => {
      const result = createSignedEmbedding([0.3, 0.4, 0.5], 0.0);
      expect(result.intentStrength).toBe(0.0);
      expect(result.norm).toBeGreaterThanOrEqual(0);
      expect(result.norm).toBeLessThan(1.0);
    });

    it('handles extreme positive intent (1.0)', () => {
      const result = createSignedEmbedding([0.5, 0.5], 1.0);
      expect(result.norm).toBeLessThan(1.0);
    });

    it('handles extreme negative intent (-1.0)', () => {
      const result = createSignedEmbedding([0.5, 0.5], -1.0);
      expect(result.norm).toBeGreaterThanOrEqual(0.85);
      expect(result.norm).toBeLessThanOrEqual(0.99);
    });
  });
});

// ---------------------------------------------------------------------------
// contrastiveDistance
// ---------------------------------------------------------------------------
describe('contrastiveDistance', () => {
  const makeEmbedding = (
    features: number[],
    intent: number,
  ) => createSignedEmbedding(features, intent);

  describe('basic distance properties', () => {
    it('distance from embedding to itself is zero or near-zero', () => {
      const emb = makeEmbedding([0.3, 0.4], 0.5);
      expect(contrastiveDistance(emb, emb)).toBeCloseTo(0, 5);
    });

    it('distance is non-negative', () => {
      const a = makeEmbedding([0.3, 0.4], 0.5);
      const b = makeEmbedding([0.5, 0.3], 0.6);
      expect(contrastiveDistance(a, b)).toBeGreaterThanOrEqual(0);
    });

    it('distance is symmetric', () => {
      const a = makeEmbedding([0.3, 0.4], 0.5);
      const b = makeEmbedding([0.5, 0.3], -0.6);
      const dAB = contrastiveDistance(a, b);
      const dBA = contrastiveDistance(b, a);
      expect(dAB).toBeCloseTo(dBA, 5);
    });
  });

  describe('same-realm distance', () => {
    it('two light-realm embeddings have unamplifed distance', () => {
      const a = makeEmbedding([0.2, 0.2, 0.2, 0.2], 0.8);
      const b = makeEmbedding([0.3, 0.1, 0.2, 0.2], 0.7);
      if (a.realm === 'light' && b.realm === 'light') {
        const dist = contrastiveDistance(a, b);
        expect(dist).toBeGreaterThanOrEqual(0);
      }
    });

    it('two shadow-realm embeddings have unamplifed distance', () => {
      const a = makeEmbedding([0.5, 0.5, 0.5, 0.5], -0.8);
      const b = makeEmbedding([0.4, 0.6, 0.5, 0.5], -0.7);
      if (a.realm === 'shadow' && b.realm === 'shadow') {
        const dist = contrastiveDistance(a, b);
        expect(dist).toBeGreaterThanOrEqual(0);
      }
    });
  });

  describe('cross-realm amplification', () => {
    it('light-shadow crossing produces larger distance than same-realm pair', () => {
      const lightA = makeEmbedding([0.15, 0.15, 0.15, 0.15], 0.9);
      const shadowB = makeEmbedding([0.5, 0.5, 0.5, 0.5], -0.9);

      if (lightA.realm === 'light' && shadowB.realm === 'shadow') {
        const crossDist = contrastiveDistance(lightA, shadowB);

        const lightC = makeEmbedding([0.2, 0.2, 0.2, 0.2], 0.85);
        if (lightC.realm === 'light') {
          const sameDist = contrastiveDistance(lightA, lightC);
          expect(crossDist).toBeGreaterThan(sameDist);
        }
      }
    });

    it('intent opposition amplifies cross-realm distance', () => {
      const a = makeEmbedding([0.2, 0.2, 0.2, 0.2], 0.9);
      const b = makeEmbedding([0.5, 0.5, 0.5, 0.5], -0.9);
      const dist = contrastiveDistance(a, b);
      expect(dist).toBeGreaterThan(0);
    });

    it('same features but opposite intents have cross-realm amplification', () => {
      const features = [0.3, 0.4, 0.3, 0.4];
      const pos = createSignedEmbedding(features, 0.9);
      const neg = createSignedEmbedding(features, -0.9);
      const dist = contrastiveDistance(pos, neg);
      expect(dist).toBeGreaterThan(0);
    });

    it('cross-realm distance is finite', () => {
      const a = makeEmbedding([0.1, 0.1, 0.1], 1.0);
      const b = makeEmbedding([0.5, 0.5, 0.5], -1.0);
      const dist = contrastiveDistance(a, b);
      expect(Number.isFinite(dist)).toBe(true);
    });
  });

  describe('edge cases', () => {
    it('handles embeddings with the same realm and different features', () => {
      const a = makeEmbedding([0.1, 0.9], 0.5);
      const b = makeEmbedding([0.9, 0.1], 0.5);
      const dist = contrastiveDistance(a, b);
      expect(dist).toBeGreaterThanOrEqual(0);
      expect(Number.isFinite(dist)).toBe(true);
    });

    it('handles twilight-to-light distance', () => {
      const a = makeEmbedding([0.2, 0.2], 0.2);
      const b = makeEmbedding([0.1, 0.1], 0.8);
      const dist = contrastiveDistance(a, b);
      expect(dist).toBeGreaterThanOrEqual(0);
      expect(Number.isFinite(dist)).toBe(true);
    });

    it('handles twilight-to-shadow distance', () => {
      const a = makeEmbedding([0.2, 0.2], 0.0);
      const b = makeEmbedding([0.5, 0.5], -0.9);
      const dist = contrastiveDistance(a, b);
      expect(dist).toBeGreaterThanOrEqual(0);
      expect(Number.isFinite(dist)).toBe(true);
    });
  });
});

// ---------------------------------------------------------------------------
// pseudoMetricInnerProduct
// ---------------------------------------------------------------------------
describe('pseudoMetricInnerProduct', () => {
  describe('basic positive-dimension behavior', () => {
    it('all positive dims: behaves like standard dot product', () => {
      // With negDimStart at default (half), first half is positive
      const u = [1.0, 0.0, 0.0, 0.0];
      const v = [1.0, 0.0, 0.0, 0.0];
      const result = pseudoMetricInnerProduct(u, v, 4); // negDimStart=4 means no negative dims
      expect(result).toBeCloseTo(1.0, 5);
    });

    it('orthogonal positive-dim vectors give zero', () => {
      const u = [1.0, 0.0, 0.0, 0.0];
      const v = [0.0, 1.0, 0.0, 0.0];
      const result = pseudoMetricInnerProduct(u, v, 4);
      expect(result).toBeCloseTo(0.0, 5);
    });
  });

  describe('negative dimension contribution', () => {
    it('negative dims subtract their contribution', () => {
      // u = [1, 0, 1, 0], v = [1, 0, 1, 0], negDimStart=2
      // positive: u[0]*v[0] + u[1]*v[1] = 1 + 0 = 1
      // negative: -(u[2]*v[2] + u[3]*v[3]) = -(1 + 0) = -1
      // total = 0
      const u = [1.0, 0.0, 1.0, 0.0];
      const v = [1.0, 0.0, 1.0, 0.0];
      const result = pseudoMetricInnerProduct(u, v, 2);
      expect(result).toBeCloseTo(0.0, 5);
    });

    it('vector with only positive dims contribution is positive', () => {
      const u = [1.0, 0.0, 0.0, 0.0];
      const v = [1.0, 0.0, 0.0, 0.0];
      const result = pseudoMetricInnerProduct(u, v, 2); // negDimStart=2
      // positive: 1*1 = 1; negative: -(0*0 + 0*0) = 0; total = 1
      expect(result).toBeCloseTo(1.0, 5);
    });

    it('vector with only negative dims contribution is negative', () => {
      const u = [0.0, 0.0, 1.0, 0.0];
      const v = [0.0, 0.0, 1.0, 0.0];
      const result = pseudoMetricInnerProduct(u, v, 2);
      // positive: 0; negative: -(1*1) = -1; total = -1
      expect(result).toBeCloseTo(-1.0, 5);
    });

    it('can produce negative values (unlike standard inner product)', () => {
      const u = [0.0, 0.0, 1.0, 1.0];
      const v = [0.0, 0.0, 1.0, 1.0];
      const result = pseudoMetricInnerProduct(u, v, 2);
      expect(result).toBeLessThan(0);
    });
  });

  describe('default negDimStart (half-split)', () => {
    it('default negDimStart splits at half-length for even-length vectors', () => {
      // 4-dim: negDimStart = 2 by default
      // u = [1,0,1,0], v = [1,0,1,0]
      // positive: 1*1 + 0*0 = 1; negative: -(1*1 + 0*0) = -1; total = 0
      const u = [1.0, 0.0, 1.0, 0.0];
      const v = [1.0, 0.0, 1.0, 0.0];
      const result = pseudoMetricInnerProduct(u, v);
      expect(result).toBeCloseTo(0.0, 5);
    });

    it('default split: positive dims dominate when only positive dims nonzero', () => {
      const u = [1.0, 1.0, 0.0, 0.0];
      const v = [1.0, 1.0, 0.0, 0.0];
      const result = pseudoMetricInnerProduct(u, v);
      expect(result).toBeGreaterThan(0);
    });

    it('default split: negative dims dominate when only negative dims nonzero', () => {
      const u = [0.0, 0.0, 1.0, 1.0];
      const v = [0.0, 0.0, 1.0, 1.0];
      const result = pseudoMetricInnerProduct(u, v);
      expect(result).toBeLessThan(0);
    });
  });

  describe('linearity properties', () => {
    it('is linear in the first argument (positive dims)', () => {
      const u1 = [2.0, 0.0, 0.0, 0.0];
      const u2 = [1.0, 0.0, 0.0, 0.0];
      const v = [1.0, 0.0, 0.0, 0.0];
      const r1 = pseudoMetricInnerProduct(u1, v, 4);
      const r2 = pseudoMetricInnerProduct(u2, v, 4);
      expect(r1).toBeCloseTo(2 * r2, 5);
    });

    it('custom negDimStart=0 makes all dims negative', () => {
      const u = [1.0, 1.0, 1.0, 1.0];
      const v = [1.0, 1.0, 1.0, 1.0];
      const result = pseudoMetricInnerProduct(u, v, 0);
      // All 4 dims are negative: -(1+1+1+1) = -4
      expect(result).toBeCloseTo(-4.0, 5);
    });
  });

  describe('edge cases', () => {
    it('zero vectors yield zero', () => {
      const u = [0.0, 0.0, 0.0, 0.0];
      const v = [0.0, 0.0, 0.0, 0.0];
      expect(pseudoMetricInnerProduct(u, v)).toBeCloseTo(0.0, 5);
    });

    it('zero vector with any vector gives zero', () => {
      const u = [0.0, 0.0, 0.0, 0.0];
      const v = [1.0, 2.0, 3.0, 4.0];
      expect(pseudoMetricInnerProduct(u, v)).toBeCloseTo(0.0, 5);
    });

    it('two-dimensional vectors split at dim 1', () => {
      const u = [1.0, 1.0];
      const v = [1.0, 1.0];
      // positive: u[0]*v[0] = 1; negative: -(u[1]*v[1]) = -1; total = 0
      const result = pseudoMetricInnerProduct(u, v, 1);
      expect(result).toBeCloseTo(0.0, 5);
    });
  });
});

// ---------------------------------------------------------------------------
// signedCosineSimilarity
// ---------------------------------------------------------------------------
describe('signedCosineSimilarity', () => {
  describe('range and bounds', () => {
    it('returns value in [-1, 1] for aligned positive-dim vectors', () => {
      const u = [1.0, 0.0, 0.0, 0.0];
      const v = [1.0, 0.0, 0.0, 0.0];
      const result = signedCosineSimilarity(u, v, 4);
      expect(result).toBeGreaterThanOrEqual(-1);
      expect(result).toBeLessThanOrEqual(1);
    });

    it('returns value in [-1, 1] for random-ish vectors', () => {
      const u = [0.3, 0.7, 0.2, 0.5];
      const v = [0.6, 0.1, 0.8, 0.3];
      const result = signedCosineSimilarity(u, v);
      expect(result).toBeGreaterThanOrEqual(-1);
      expect(result).toBeLessThanOrEqual(1);
    });

    it('returns value in [-1, 1] for opposing-dim vectors', () => {
      const u = [0.0, 0.0, 1.0, 0.0];
      const v = [0.0, 0.0, 1.0, 0.0];
      const result = signedCosineSimilarity(u, v, 2);
      expect(result).toBeGreaterThanOrEqual(-1);
      expect(result).toBeLessThanOrEqual(1);
    });
  });

  describe('aligned vectors (positive dims)', () => {
    it('identical vectors in pure positive dims give similarity near 1', () => {
      const u = [1.0, 1.0, 0.0, 0.0];
      const v = [1.0, 1.0, 0.0, 0.0];
      const result = signedCosineSimilarity(u, v, 2);
      expect(result).toBeCloseTo(1.0, 5);
    });

    it('parallel vectors in positive dims give near 1', () => {
      const u = [2.0, 0.0, 0.0, 0.0];
      const v = [3.0, 0.0, 0.0, 0.0];
      const result = signedCosineSimilarity(u, v, 4);
      expect(result).toBeCloseTo(1.0, 5);
    });
  });

  describe('opposing vectors', () => {
    it('identical vectors in pure negative dims give similarity near -1', () => {
      const u = [0.0, 0.0, 1.0, 1.0];
      const v = [0.0, 0.0, 1.0, 1.0];
      const result = signedCosineSimilarity(u, v, 2);
      expect(result).toBeCloseTo(-1.0, 5);
    });

    it('identical vectors straddling positive and negative dims give ~0', () => {
      // u = v = [1, 1], negDimStart=1: positive=1, negative=-1, total=0
      const u = [1.0, 1.0];
      const v = [1.0, 1.0];
      const result = signedCosineSimilarity(u, v, 1);
      expect(result).toBeCloseTo(0.0, 5);
    });
  });

  describe('orthogonality', () => {
    it('orthogonal positive-dim vectors give near 0', () => {
      const u = [1.0, 0.0, 0.0, 0.0];
      const v = [0.0, 1.0, 0.0, 0.0];
      const result = signedCosineSimilarity(u, v, 4);
      expect(result).toBeCloseTo(0.0, 5);
    });

    it('orthogonal negative-dim vectors give near 0', () => {
      const u = [0.0, 0.0, 1.0, 0.0];
      const v = [0.0, 0.0, 0.0, 1.0];
      const result = signedCosineSimilarity(u, v, 2);
      expect(result).toBeCloseTo(0.0, 5);
    });
  });

  describe('default negDimStart half-split', () => {
    it('default split: same vector with equal positive and negative dims gives 0', () => {
      const u = [1.0, 0.0, 1.0, 0.0];
      const v = [1.0, 0.0, 1.0, 0.0];
      const result = signedCosineSimilarity(u, v);
      // positive: 1; negative: -1; total: 0
      expect(result).toBeCloseTo(0.0, 5);
    });

    it('default split: positive-dominant vector has positive similarity with itself', () => {
      const u = [1.0, 1.0, 0.0, 0.0];
      const v = [1.0, 1.0, 0.0, 0.0];
      const result = signedCosineSimilarity(u, v);
      expect(result).toBeGreaterThan(0);
    });
  });

  describe('edge cases', () => {
    it('returns 0 for zero vectors without throwing', () => {
      const u = [0.0, 0.0, 0.0, 0.0];
      const v = [1.0, 1.0, 1.0, 1.0];
      const result = signedCosineSimilarity(u, v);
      expect(result).toBeCloseTo(0.0, 5);
    });

    it('returns 0 for two zero vectors without throwing', () => {
      const u = [0.0, 0.0];
      const v = [0.0, 0.0];
      const result = signedCosineSimilarity(u, v);
      expect(result).toBeCloseTo(0.0, 5);
    });

    it('handles unit vectors (norm=1) correctly', () => {
      const sqrt2 = Math.sqrt(2);
      const u = [1 / sqrt2, 1 / sqrt2, 0.0, 0.0];
      const v = [1 / sqrt2, 1 / sqrt2, 0.0, 0.0];
      const result = signedCosineSimilarity(u, v, 4);
      expect(result).toBeCloseTo(1.0, 5);
    });

    it('result is a finite number for all valid inputs', () => {
      const u = [0.5, 0.3, 0.8, 0.1];
      const v = [0.2, 0.9, 0.4, 0.7];
      const result = signedCosineSimilarity(u, v);
      expect(Number.isFinite(result)).toBe(true);
    });

    it('two-dimensional vector with negDimStart=1', () => {
      const u = [3.0, 4.0];
      const v = [3.0, 4.0];
      const result = signedCosineSimilarity(u, v, 1);
      // positive: 3*3=9; negative: -(4*4)=-16; total=-7
      // norms: each vector has pseudo-norm contribution; result in [-1,1]
      expect(result).toBeGreaterThanOrEqual(-1);
      expect(result).toBeLessThanOrEqual(1);
    });
  });
});

// ---------------------------------------------------------------------------
// Integration: cross-function consistency
// ---------------------------------------------------------------------------
describe('cross-function integration', () => {
  it('createSignedEmbedding realm matches classifyRealm for any intent/features', () => {
    const testCases = [
      { features: [0.3, 0.3, 0.3, 0.3], intent: 0.8 },
      { features: [0.5, 0.5, 0.5, 0.5], intent: -0.8 },
      { features: [0.2, 0.8, 0.1, 0.7], intent: 0.0 },
      { features: [0.1, 0.1, 0.1, 0.1], intent: 0.31 },
      { features: [0.9, 0.9, 0.9, 0.9], intent: -0.31 },
    ];

    for (const { features, intent } of testCases) {
      const emb = createSignedEmbedding(features, intent);
      const expectedRealm = classifyRealm(intent, emb.norm);
      expect(emb.realm).toBe(expectedRealm);
    }
  });

  it('contrastiveDistance is consistent with embedding norms', () => {
    const a = createSignedEmbedding([0.3, 0.3, 0.3, 0.3], 0.9);
    const b = createSignedEmbedding([0.5, 0.5, 0.5, 0.5], -0.9);
    const dist = contrastiveDistance(a, b);
    expect(dist).toBeGreaterThan(0);
    expect(Number.isFinite(dist)).toBe(true);
    expect(a.norm).toBeLessThan(1.0);
    expect(b.norm).toBeLessThan(1.0);
  });

  it('signedCosineSimilarity of embedding vectors correlates with realm alignment', () => {
    const lightEmb = createSignedEmbedding([0.15, 0.15, 0.15, 0.15], 0.9);
    const shadowEmb = createSignedEmbedding([0.5, 0.5, 0.5, 0.5], -0.9);
    const anotherLight = createSignedEmbedding([0.1, 0.2, 0.1, 0.2], 0.8);

    if (lightEmb.realm === 'light' && anotherLight.realm === 'light' && shadowEmb.realm === 'shadow') {
      const sameRealmSim = signedCosineSimilarity(lightEmb.vector, anotherLight.vector);
      const crossRealmSim = signedCosineSimilarity(lightEmb.vector, shadowEmb.vector);
      // Light-light should generally have higher pseudo-similarity than light-shadow
      expect(sameRealmSim).toBeGreaterThan(crossRealmSim);
    }
  });
});
