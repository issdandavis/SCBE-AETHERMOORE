/**
 * AI Brain Unified State Unit Tests
 *
 * Tests for the 21D unified brain state vector, Poincare embedding,
 * and hyperbolic geometry operations.
 *
 * @layer Layer 1-14 (Unified Manifold)
 */

import { describe, expect, it } from 'vitest';

import {
  BRAIN_DIMENSIONS,
  PHI,
  POINCARE_MAX_NORM,
  UnifiedBrainState,
  applyGoldenWeighting,
  euclideanDistance,
  goldenWeightProduct,
  hyperbolicDistanceSafe,
  mobiusAddSafe,
  safePoincareEmbed,
  vectorNorm,
} from '../../src/ai_brain/index';

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

describe('Brain Constants', () => {
  it('should define 21 dimensions', () => {
    expect(BRAIN_DIMENSIONS).toBe(21);
  });

  it('should use correct golden ratio', () => {
    expect(PHI).toBeCloseTo((1 + Math.sqrt(5)) / 2, 10);
  });

  it('should bound Poincare norm below 1', () => {
    expect(POINCARE_MAX_NORM).toBeLessThan(1);
    expect(POINCARE_MAX_NORM).toBeGreaterThan(0.99);
  });
});

// ═══════════════════════════════════════════════════════════════
// UnifiedBrainState
// ═══════════════════════════════════════════════════════════════

describe('UnifiedBrainState', () => {
  const defaultState = new UnifiedBrainState({
    scbeContext: {
      deviceTrust: 0.5,
      locationTrust: 0.3,
      networkTrust: 0.7,
      behaviorScore: 0.9,
      timeOfDay: 0.2,
      intentAlignment: 0.8,
    },
    navigation: { x: 0.1, y: 0.2, z: 0.3, time: 0.4, priority: 0.5, confidence: 0.6 },
    cognitivePosition: { px: 0.1, py: 0.2, pz: 0.3 },
    semanticPhase: { activeTongue: 0, phaseAngle: 1.5, tongueWeight: 0.8 },
    swarmCoordination: { trustScore: 0.9, byzantineVotes: 5, spectralCoherence: 0.5 },
  });

  it('should produce a 21D vector', () => {
    const vec = defaultState.toVector();
    expect(vec).toHaveLength(BRAIN_DIMENSIONS);
  });

  it('should preserve component values in vector', () => {
    const vec = defaultState.toVector();
    // SCBE dimensions 0-5
    expect(vec[0]).toBe(0.5); // deviceTrust
    expect(vec[5]).toBe(0.8); // intentAlignment
    // Navigation dimensions 6-11
    expect(vec[6]).toBe(0.1); // x
    // Cognitive dimensions 12-14
    expect(vec[12]).toBe(0.1); // px
    // Semantic dimensions 15-17
    expect(vec[15]).toBe(0); // activeTongue
    // Swarm dimensions 18-20
    expect(vec[18]).toBe(0.9); // trustScore
  });

  it('should produce a Poincare point inside the ball', () => {
    const poincare = defaultState.toPoincarePoint();
    expect(poincare).toHaveLength(BRAIN_DIMENSIONS);
    const norm = vectorNorm(poincare);
    expect(norm).toBeLessThan(1);
  });

  it('should produce weighted vector with golden ratio scaling', () => {
    const raw = defaultState.toVector();
    const weighted = defaultState.toWeightedVector();
    // Later dimensions should be more heavily weighted
    for (let i = 1; i < BRAIN_DIMENSIONS; i++) {
      if (raw[i] !== 0 && raw[i - 1] !== 0) {
        const ratio = weighted[i] / weighted[i - 1];
        const rawRatio = raw[i] / raw[i - 1];
        // Golden ratio increases weight per dimension
        expect(ratio / rawRatio).toBeCloseTo(PHI, 5);
      }
    }
  });

  it('should reconstruct from vector via fromVector()', () => {
    const vec = defaultState.toVector();
    const reconstructed = UnifiedBrainState.fromVector(vec);
    const vec2 = reconstructed.toVector();
    for (let i = 0; i < BRAIN_DIMENSIONS; i++) {
      expect(vec2[i]).toBeCloseTo(vec[i], 10);
    }
  });

  it('should create a safe origin state with trust values at 1', () => {
    const origin = UnifiedBrainState.safeOrigin();
    const components = origin.getComponents();
    expect(components.scbeContext.deviceTrust).toBe(1);
    expect(components.scbeContext.intentAlignment).toBe(1);
    expect(components.navigation.x).toBe(0);
    expect(components.swarmCoordination.trustScore).toBe(1);
  });

  it('should support mutable updates via updateSCBEContext', () => {
    const state = new UnifiedBrainState();
    state.updateSCBEContext({ deviceTrust: 0.99 });
    expect(state.getComponents().scbeContext.deviceTrust).toBe(0.99);
  });
});

// ═══════════════════════════════════════════════════════════════
// Poincare Embedding
// ═══════════════════════════════════════════════════════════════

describe('safePoincareEmbed', () => {
  it('should map the zero vector to zero', () => {
    const zero = new Array(21).fill(0);
    const embedded = safePoincareEmbed(zero);
    for (const v of embedded) {
      expect(v).toBe(0);
    }
  });

  it('should map all vectors inside the unit ball', () => {
    const largeVec = Array.from({ length: 21 }, (_, i) => i * 10);
    const embedded = safePoincareEmbed(largeVec);
    const norm = vectorNorm(embedded);
    expect(norm).toBeLessThan(1);
  });

  it('should preserve direction', () => {
    const vec = [1, 2, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    const embedded = safePoincareEmbed(vec);
    // Direction should be same: ratios preserved
    const ratio12 = embedded[1] / embedded[0];
    expect(ratio12).toBeCloseTo(2, 5);
    const ratio13 = embedded[2] / embedded[0];
    expect(ratio13).toBeCloseTo(3, 5);
  });

  it('should respect monotonicity (larger norms map further)', () => {
    const small = [0.1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    const large = [0.5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    const embSmall = safePoincareEmbed(small);
    const embLarge = safePoincareEmbed(large);
    expect(vectorNorm(embSmall)).toBeLessThan(vectorNorm(embLarge));
  });
});

// ═══════════════════════════════════════════════════════════════
// Hyperbolic Distance
// ═══════════════════════════════════════════════════════════════

describe('hyperbolicDistanceSafe', () => {
  it('should return 0 for identical points', () => {
    const p = [0.1, 0.2, 0.3];
    expect(hyperbolicDistanceSafe(p, p)).toBeCloseTo(0, 5);
  });

  it('should be symmetric', () => {
    const a = [0.1, 0.2, 0.3];
    const b = [0.4, 0.3, 0.1];
    expect(hyperbolicDistanceSafe(a, b)).toBeCloseTo(hyperbolicDistanceSafe(b, a), 10);
  });

  it('should satisfy triangle inequality', () => {
    const a = [0.1, 0.0, 0.0];
    const b = [0.0, 0.3, 0.0];
    const c = [0.0, 0.0, 0.2];
    const ab = hyperbolicDistanceSafe(a, b);
    const bc = hyperbolicDistanceSafe(b, c);
    const ac = hyperbolicDistanceSafe(a, c);
    expect(ac).toBeLessThanOrEqual(ab + bc + 1e-10);
  });

  it('should be non-negative', () => {
    const a = [0.5, -0.3, 0.1];
    const b = [-0.2, 0.4, 0.3];
    expect(hyperbolicDistanceSafe(a, b)).toBeGreaterThanOrEqual(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Mobius Addition
// ═══════════════════════════════════════════════════════════════

describe('mobiusAddSafe', () => {
  it('should have zero as identity', () => {
    const a = [0.1, 0.2, 0.3];
    const zero = [0, 0, 0];
    const result = mobiusAddSafe(a, zero);
    for (let i = 0; i < 3; i++) {
      expect(result[i]).toBeCloseTo(a[i], 5);
    }
  });

  it('should keep result inside the ball', () => {
    const a = [0.8, 0.0, 0.0];
    const b = [0.0, 0.8, 0.0];
    const result = mobiusAddSafe(a, b);
    const norm = vectorNorm(result);
    expect(norm).toBeLessThan(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// Golden Ratio Weighting
// ═══════════════════════════════════════════════════════════════

describe('Golden Ratio Weighting', () => {
  it('should scale by phi^i for 21D vector', () => {
    const vec = new Array(BRAIN_DIMENSIONS).fill(1);
    const weighted = applyGoldenWeighting(vec);
    for (let i = 0; i < BRAIN_DIMENSIONS; i++) {
      expect(weighted[i]).toBeCloseTo(Math.pow(PHI, i), 5);
    }
  });

  it('should reject non-21D vectors', () => {
    const vec = new Array(5).fill(1);
    expect(() => applyGoldenWeighting(vec)).toThrow(RangeError);
  });

  it('should compute golden weight product (phi^210)', () => {
    const product = goldenWeightProduct();
    // phi^(0+1+...+20) = phi^210, which is astronomically large
    expect(product).toBeGreaterThan(1e40);
    expect(Number.isFinite(product)).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// Euclidean Distance
// ═══════════════════════════════════════════════════════════════

describe('euclideanDistance', () => {
  it('should return 0 for same point', () => {
    const p = [1, 2, 3];
    expect(euclideanDistance(p, p)).toBe(0);
  });

  it('should compute correct distance', () => {
    const a = [0, 0, 0];
    const b = [3, 4, 0];
    expect(euclideanDistance(a, b)).toBeCloseTo(5, 10);
  });
});
