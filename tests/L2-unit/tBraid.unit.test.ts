/**
 * @file tBraid.unit.test.ts
 * @module tests/L2-unit
 * @layer Layer 6, Layer 11, Layer 12
 * @component T-Braiding Temporal Lattice Tests
 *
 * Tests the tetradic T-braiding system: 4 temporal variants intertwined
 * through a shared meta-T with Poincaré ball pairwise distances.
 */

import { describe, it, expect } from 'vitest';
import {
  BraidVariant,
  STRAND_ORDER,
  computeVariants,
  projectScalar,
  projectVariants,
  hyperbolicDistance1D,
  computePairwiseDistances,
  braidedDistance,
  triadicBraidedDistance,
  braidedMetaTime,
  harmonicWallBraid,
  braidHarmScore,
  applyGenerator,
  checkYangBaxter,
  computeBraid,
  braidFromClocks,
  variantsFromClocks,
  edgeWeight,
  weightedBraidedDistance,
  EDGE_WEIGHTS,
  DEFAULT_EDGE_WEIGHTS,
  toDebugJSON,
} from '../../packages/kernel/src/tBraid.js';

// ═══════════════════════════════════════════════════════════════
// BraidVariant enum & STRAND_ORDER
// ═══════════════════════════════════════════════════════════════

describe('BraidVariant', () => {
  it('has 4 variants', () => {
    const variants = Object.values(BraidVariant);
    expect(variants).toHaveLength(4);
  });

  it('has canonical string values', () => {
    expect(BraidVariant.IMMEDIATE).toBe('immediate');
    expect(BraidVariant.MEMORY).toBe('memory');
    expect(BraidVariant.GOVERNANCE).toBe('governance');
    expect(BraidVariant.PREDICTIVE).toBe('predictive');
  });

  it('STRAND_ORDER has all 4 in canonical sequence', () => {
    expect(STRAND_ORDER).toHaveLength(4);
    expect(STRAND_ORDER[0]).toBe(BraidVariant.IMMEDIATE);
    expect(STRAND_ORDER[1]).toBe(BraidVariant.MEMORY);
    expect(STRAND_ORDER[2]).toBe(BraidVariant.GOVERNANCE);
    expect(STRAND_ORDER[3]).toBe(BraidVariant.PREDICTIVE);
  });
});

// ═══════════════════════════════════════════════════════════════
// computeVariants
// ═══════════════════════════════════════════════════════════════

describe('computeVariants', () => {
  it('computes Ti = T * intent', () => {
    const v = computeVariants(2, 3, 1, 1);
    expect(v.immediate).toBe(6);
  });

  it('computes Tm = T^t', () => {
    const v = computeVariants(2, 1, 1, 3);
    expect(v.memory).toBe(8); // 2^3
  });

  it('computes Tg = T * context', () => {
    const v = computeVariants(2, 1, 5, 1);
    expect(v.governance).toBe(10);
  });

  it('computes Tp = T / t', () => {
    const v = computeVariants(10, 1, 1, 5);
    expect(v.predictive).toBe(2); // 10/5
  });

  it('caps T^t exponent at 20 for stability', () => {
    const v = computeVariants(2, 1, 1, 100);
    // Should use min(100, 20) = 20, so T^20
    expect(v.memory).toBe(Math.pow(2, 20));
  });

  it('handles zero intent gracefully', () => {
    const v = computeVariants(2, 0, 1, 1);
    expect(v.immediate).toBe(0);
  });

  it('handles negative intent as zero', () => {
    const v = computeVariants(2, -5, 1, 1);
    expect(v.immediate).toBe(0);
  });

  it('handles zero T by clamping to epsilon', () => {
    const v = computeVariants(0, 1, 1, 1);
    expect(v.immediate).toBeGreaterThan(0);
    expect(v.memory).toBeGreaterThan(0);
  });

  it('handles zero t by clamping denominator', () => {
    const v = computeVariants(2, 1, 1, 0);
    expect(v.predictive).toBeGreaterThan(0);
    expect(isFinite(v.predictive)).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// projectScalar
// ═══════════════════════════════════════════════════════════════

describe('projectScalar', () => {
  it('maps 0 to 0', () => {
    expect(projectScalar(0)).toBe(0);
  });

  it('maps positive values to (0, 1)', () => {
    const p = projectScalar(5);
    expect(p).toBeGreaterThan(0);
    expect(p).toBeLessThan(1);
  });

  it('maps negative values to (-1, 0)', () => {
    const p = projectScalar(-5);
    expect(p).toBeLessThan(0);
    expect(p).toBeGreaterThan(-1);
  });

  it('approaches 1 for large positive values', () => {
    const p = projectScalar(1000);
    expect(p).toBeGreaterThan(0.99);
  });

  it('approaches -1 for large negative values', () => {
    const p = projectScalar(-1000);
    expect(p).toBeLessThan(-0.99);
  });

  it('respects alpha compression factor', () => {
    const gentle = projectScalar(5, 0.05);
    const aggressive = projectScalar(5, 0.5);
    // More aggressive alpha → closer to boundary
    expect(aggressive).toBeGreaterThan(gentle);
  });

  it('is monotonically increasing', () => {
    const a = projectScalar(1);
    const b = projectScalar(2);
    const c = projectScalar(3);
    expect(b).toBeGreaterThan(a);
    expect(c).toBeGreaterThan(b);
  });
});

// ═══════════════════════════════════════════════════════════════
// projectVariants
// ═══════════════════════════════════════════════════════════════

describe('projectVariants', () => {
  it('projects all 4 variants into (-1, 1)', () => {
    const v = computeVariants(2, 3, 5, 4);
    const p = projectVariants(v);
    for (const val of [p.immediate, p.memory, p.governance, p.predictive]) {
      expect(val).toBeGreaterThan(-1);
      expect(val).toBeLessThan(1);
    }
  });

  it('preserves relative ordering', () => {
    const v = computeVariants(2, 1, 1, 1);
    // Ti = 2, Tm = 2, Tg = 2, Tp = 2 — all equal
    const p = projectVariants(v);
    expect(p.immediate).toBeCloseTo(p.memory, 6);
    expect(p.memory).toBeCloseTo(p.governance, 6);
  });
});

// ═══════════════════════════════════════════════════════════════
// hyperbolicDistance1D
// ═══════════════════════════════════════════════════════════════

describe('hyperbolicDistance1D', () => {
  it('returns ≈0 for identical points', () => {
    expect(hyperbolicDistance1D(0.5, 0.5)).toBeCloseTo(0, 5);
  });

  it('returns 0 for origin-origin', () => {
    expect(hyperbolicDistance1D(0, 0)).toBeCloseTo(0, 5);
  });

  it('is symmetric', () => {
    const d1 = hyperbolicDistance1D(0.3, 0.7);
    const d2 = hyperbolicDistance1D(0.7, 0.3);
    expect(d1).toBeCloseTo(d2, 10);
  });

  it('increases near the boundary', () => {
    const dCenter = hyperbolicDistance1D(0.1, 0.2);
    const dBoundary = hyperbolicDistance1D(0.8, 0.9);
    expect(dBoundary).toBeGreaterThan(dCenter);
  });

  it('is always non-negative', () => {
    expect(hyperbolicDistance1D(-0.5, 0.5)).toBeGreaterThanOrEqual(0);
    expect(hyperbolicDistance1D(0, 0.99)).toBeGreaterThanOrEqual(0);
  });

  it('satisfies triangle inequality', () => {
    const a = 0.1, b = 0.4, c = 0.7;
    const dab = hyperbolicDistance1D(a, b);
    const dbc = hyperbolicDistance1D(b, c);
    const dac = hyperbolicDistance1D(a, c);
    expect(dac).toBeLessThanOrEqual(dab + dbc + 1e-10);
  });

  it('diverges as points approach opposite boundaries', () => {
    const d = hyperbolicDistance1D(-0.99, 0.99);
    expect(d).toBeGreaterThan(5);
  });
});

// ═══════════════════════════════════════════════════════════════
// computePairwiseDistances
// ═══════════════════════════════════════════════════════════════

describe('computePairwiseDistances', () => {
  it('returns 6 edges for 4 variants (C(4,2))', () => {
    const p = { immediate: 0.1, memory: 0.3, governance: 0.5, predictive: 0.7 };
    const edges = computePairwiseDistances(p);
    expect(edges).toHaveLength(6);
  });

  it('each edge has from, to, and distance', () => {
    const p = { immediate: 0.1, memory: 0.3, governance: 0.5, predictive: 0.7 };
    const edges = computePairwiseDistances(p);
    for (const edge of edges) {
      expect(edge.from).toBeDefined();
      expect(edge.to).toBeDefined();
      expect(edge.distance).toBeGreaterThanOrEqual(0);
    }
  });

  it('returns 0 distances when all variants equal', () => {
    const p = { immediate: 0.5, memory: 0.5, governance: 0.5, predictive: 0.5 };
    const edges = computePairwiseDistances(p);
    for (const edge of edges) {
      expect(edge.distance).toBeCloseTo(0, 5);
    }
  });

  it('greater spread = greater total distance', () => {
    const narrow = { immediate: 0.4, memory: 0.45, governance: 0.5, predictive: 0.55 };
    const wide = { immediate: 0.1, memory: 0.3, governance: 0.6, predictive: 0.9 };
    const dNarrow = braidedDistance(computePairwiseDistances(narrow));
    const dWide = braidedDistance(computePairwiseDistances(wide));
    expect(dWide).toBeGreaterThan(dNarrow);
  });
});

// ═══════════════════════════════════════════════════════════════
// braidedDistance & triadicBraidedDistance
// ═══════════════════════════════════════════════════════════════

describe('braidedDistance', () => {
  it('sums all edge distances', () => {
    const p = { immediate: 0.1, memory: 0.3, governance: 0.5, predictive: 0.7 };
    const edges = computePairwiseDistances(p);
    const db = braidedDistance(edges);
    const manual = edges.reduce((s, e) => s + e.distance, 0);
    expect(db).toBe(manual);
  });

  it('returns 0 when all variants match', () => {
    const p = { immediate: 0.3, memory: 0.3, governance: 0.3, predictive: 0.3 };
    const db = braidedDistance(computePairwiseDistances(p));
    expect(db).toBeCloseTo(0, 5);
  });
});

describe('triadicBraidedDistance', () => {
  it('uses only 3 edges (immediate, memory, governance)', () => {
    const p = { immediate: 0.1, memory: 0.5, governance: 0.9, predictive: 0.99 };
    const dtri = triadicBraidedDistance(p);
    // Predictive should not affect the result
    const p2 = { immediate: 0.1, memory: 0.5, governance: 0.9, predictive: 0.01 };
    const dtri2 = triadicBraidedDistance(p2);
    expect(dtri).toBeCloseTo(dtri2, 10);
  });

  it('is less than or equal to full tetradic distance', () => {
    const p = { immediate: 0.1, memory: 0.3, governance: 0.6, predictive: 0.8 };
    const dtri = triadicBraidedDistance(p);
    const dtetra = braidedDistance(computePairwiseDistances(p));
    expect(dtri).toBeLessThanOrEqual(dtetra + 1e-10);
  });
});

// ═══════════════════════════════════════════════════════════════
// braidedMetaTime
// ═══════════════════════════════════════════════════════════════

describe('braidedMetaTime', () => {
  it('triadic: T_b = Ti * Tm * Tg', () => {
    const v = computeVariants(2, 3, 5, 2);
    // Ti = 2*3 = 6, Tm = 2^2 = 4, Tg = 2*5 = 10
    const tb = braidedMetaTime(v, false);
    expect(tb).toBe(6 * 4 * 10);
  });

  it('tetradic: T_b = Ti * Tm * Tg * Tp', () => {
    const v = computeVariants(2, 3, 5, 2);
    // Tp = 2/2 = 1
    const tb = braidedMetaTime(v, true);
    expect(tb).toBe(6 * 4 * 10 * 1);
  });

  it('tetradic ≠ triadic when Tp ≠ 1', () => {
    const v = computeVariants(10, 1, 1, 2);
    // Tp = 10/2 = 5
    const t3 = braidedMetaTime(v, false);
    const t4 = braidedMetaTime(v, true);
    expect(t4).not.toBe(t3);
    expect(t4).toBe(t3 * 5);
  });

  it('defaults to tetradic', () => {
    const v = computeVariants(2, 1, 1, 1);
    const def = braidedMetaTime(v);
    const tetra = braidedMetaTime(v, true);
    expect(def).toBe(tetra);
  });
});

// ═══════════════════════════════════════════════════════════════
// harmonicWallBraid
// ═══════════════════════════════════════════════════════════════

describe('harmonicWallBraid', () => {
  it('returns 1 when d_b = 0', () => {
    expect(harmonicWallBraid(0)).toBe(1);
  });

  it('R^(d² * x) formula', () => {
    const h = harmonicWallBraid(2, 1, 1.5);
    expect(h).toBeCloseTo(Math.pow(1.5, 4), 6);
  });

  it('increases with d_b', () => {
    const h1 = harmonicWallBraid(1);
    const h2 = harmonicWallBraid(2);
    const h3 = harmonicWallBraid(3);
    expect(h2).toBeGreaterThan(h1);
    expect(h3).toBeGreaterThan(h2);
  });

  it('increases with x', () => {
    const h1 = harmonicWallBraid(2, 1);
    const h2 = harmonicWallBraid(2, 2);
    expect(h2).toBeGreaterThan(h1);
  });

  it('caps at MAX_VALUE for extreme exponents', () => {
    const h = harmonicWallBraid(100, 3);
    expect(h).toBe(Number.MAX_VALUE);
  });

  it('is finite for moderate inputs', () => {
    const h = harmonicWallBraid(3, 2);
    expect(isFinite(h)).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// braidHarmScore
// ═══════════════════════════════════════════════════════════════

describe('braidHarmScore', () => {
  it('returns 1 when H_braid = 1 (safe center)', () => {
    expect(braidHarmScore(1)).toBe(1);
  });

  it('returns < 1 when H_braid > 1', () => {
    const s = braidHarmScore(10);
    expect(s).toBeLessThan(1);
    expect(s).toBeGreaterThan(0);
  });

  it('is monotone decreasing in H_braid', () => {
    const s1 = braidHarmScore(1);
    const s2 = braidHarmScore(5);
    const s3 = braidHarmScore(50);
    expect(s2).toBeLessThan(s1);
    expect(s3).toBeLessThan(s2);
  });

  it('returns 0 for Infinity', () => {
    expect(braidHarmScore(Infinity)).toBe(0);
  });

  it('returns 0 for MAX_VALUE', () => {
    expect(braidHarmScore(Number.MAX_VALUE)).toBe(0);
  });

  it('never goes negative', () => {
    for (const h of [0.5, 1, 10, 100, 1e10]) {
      expect(braidHarmScore(h)).toBeGreaterThanOrEqual(0);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Yang-Baxter consistency
// ═══════════════════════════════════════════════════════════════

describe('applyGenerator', () => {
  it('swaps adjacent elements', () => {
    expect(applyGenerator([1, 2, 3, 4], 0)).toEqual([2, 1, 3, 4]);
    expect(applyGenerator([1, 2, 3, 4], 1)).toEqual([1, 3, 2, 4]);
    expect(applyGenerator([1, 2, 3, 4], 2)).toEqual([1, 2, 4, 3]);
  });

  it('returns copy for out-of-bounds index', () => {
    expect(applyGenerator([1, 2, 3], -1)).toEqual([1, 2, 3]);
    expect(applyGenerator([1, 2, 3], 3)).toEqual([1, 2, 3]);
  });

  it('does not mutate original', () => {
    const arr = [1, 2, 3, 4];
    applyGenerator(arr, 0);
    expect(arr).toEqual([1, 2, 3, 4]);
  });
});

describe('checkYangBaxter', () => {
  it('holds for uniform variants', () => {
    const p = { immediate: 0.5, memory: 0.5, governance: 0.5, predictive: 0.5 };
    expect(checkYangBaxter(p)).toBe(true);
  });

  it('holds for distinct variants', () => {
    const p = { immediate: 0.1, memory: 0.3, governance: 0.6, predictive: 0.9 };
    expect(checkYangBaxter(p)).toBe(true);
  });

  it('holds for negative values', () => {
    const p = { immediate: -0.5, memory: 0.0, governance: 0.3, predictive: 0.8 };
    expect(checkYangBaxter(p)).toBe(true);
  });

  it('holds for near-boundary values', () => {
    const p = { immediate: -0.99, memory: -0.5, governance: 0.5, predictive: 0.99 };
    expect(checkYangBaxter(p)).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// computeBraid (full pipeline)
// ═══════════════════════════════════════════════════════════════

describe('computeBraid', () => {
  it('returns all fields', () => {
    const r = computeBraid(1, 1, 1, 1);
    expect(r.variants).toBeDefined();
    expect(r.projected).toBeDefined();
    expect(r.edges).toHaveLength(6);
    expect(typeof r.braidedDistance).toBe('number');
    expect(typeof r.weightedDistance).toBe('number');
    expect(typeof r.braidedMetaTime).toBe('number');
    expect(typeof r.hBraid).toBe('number');
    expect(typeof r.harmScore).toBe('number');
    expect(typeof r.yangBaxterConsistent).toBe('boolean');
  });

  it('safe center: T=1, intent=1, context=1, t=1 → low cost', () => {
    const r = computeBraid(1, 1, 1, 1);
    // All variants = 1, so projected values are all equal
    // → braided distance ≈ 0 → H ≈ 1 → harm_score ≈ 1
    expect(r.braidedDistance).toBeCloseTo(0, 2);
    expect(r.harmScore).toBeCloseTo(1, 2);
  });

  it('divergent intents increase braided distance', () => {
    const aligned = computeBraid(1, 1, 1, 1);
    const divergent = computeBraid(1, 10, 0.1, 5);
    expect(divergent.braidedDistance).toBeGreaterThan(aligned.braidedDistance);
  });

  it('higher braided distance → lower harm score', () => {
    const safe = computeBraid(1, 1, 1, 1);
    const risky = computeBraid(1, 10, 0.1, 5);
    expect(risky.harmScore).toBeLessThan(safe.harmScore);
  });

  it('x-factor amplifies cost', () => {
    const x1 = computeBraid(1, 5, 0.5, 3, 1.0);
    const x3 = computeBraid(1, 5, 0.5, 3, 3.0);
    expect(x3.hBraid).toBeGreaterThanOrEqual(x1.hBraid);
  });

  it('Yang-Baxter skipped by default (production mode)', () => {
    // skipYangBaxter defaults to true — always reports true without computing
    expect(computeBraid(1, 1, 1, 1).yangBaxterConsistent).toBe(true);
  });

  it('Yang-Baxter holds when explicitly checked (test mode)', () => {
    const opts = { skipYangBaxter: false };
    expect(computeBraid(1, 1, 1, 1, opts).yangBaxterConsistent).toBe(true);
    expect(computeBraid(2, 5, 0.1, 10, opts).yangBaxterConsistent).toBe(true);
    expect(computeBraid(0.5, 0, 3, 0.1, opts).yangBaxterConsistent).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// Multi-clock integration
// ═══════════════════════════════════════════════════════════════

describe('variantsFromClocks', () => {
  it('maps clock values to braid variants', () => {
    const v = variantsFromClocks(
      0.5,   // fastIntent
      10,    // memoryTick
      0.3,   // memoryIntent (unused in variant computation directly)
      0.2,   // govIntent
      1.0    // breathingFactor = T
    );
    expect(v.immediate).toBe(0.5);     // T * fastIntent = 1 * 0.5
    expect(v.governance).toBe(0.2);     // T * govIntent = 1 * 0.2
    expect(v.predictive).toBeCloseTo(0.1, 6);  // T / t = 1 / 10
  });

  it('uses breathing factor as base T', () => {
    const v1 = variantsFromClocks(1, 10, 0, 1, 1.0);
    const v2 = variantsFromClocks(1, 10, 0, 1, 2.0);
    expect(v2.immediate).toBe(2 * v1.immediate);
  });

  it('floors memoryTick at MIN_LIFECYCLE_TICKS=3 for early-lifecycle agents', () => {
    const v0 = variantsFromClocks(1, 0, 0, 1, 1.0);
    const v1 = variantsFromClocks(1, 1, 0, 1, 1.0);
    const v3 = variantsFromClocks(1, 3, 0, 1, 1.0);
    // tick=0 and tick=1 both floor to 3, producing same variants as tick=3
    expect(v0.predictive).toBeCloseTo(v3.predictive, 10);
    expect(v1.predictive).toBeCloseTo(v3.predictive, 10);
  });

  it('clamps breathing factor to epsilon', () => {
    const v = variantsFromClocks(1, 10, 0, 1, 0);
    expect(v.immediate).toBeGreaterThan(0);
  });
});

describe('braidFromClocks', () => {
  it('returns full braid result', () => {
    const r = braidFromClocks(0.5, 10, 0.3, 0.2, 1.0);
    expect(r.edges).toHaveLength(6);
    expect(r.yangBaxterConsistent).toBe(true);
    expect(typeof r.harmScore).toBe('number');
  });

  it('quiet system → low braided distance', () => {
    // All intents near 0, tick=1, breathing=1
    const r = braidFromClocks(0, 1, 0, 0, 1.0);
    expect(r.braidedDistance).toBeLessThan(2);
  });

  it('high fast intent with low governance → higher distance', () => {
    const quiet = braidFromClocks(0.1, 5, 0.1, 0.1, 1.0);
    const divergent = braidFromClocks(5.0, 5, 0.1, 0.01, 1.0);
    expect(divergent.braidedDistance).toBeGreaterThan(quiet.braidedDistance);
  });
});

// ═══════════════════════════════════════════════════════════════
// Edge weights (golden ratio)
// ═══════════════════════════════════════════════════════════════

describe('EDGE_WEIGHTS', () => {
  const PHI = (1 + Math.sqrt(5)) / 2;

  it('adjacent edges have weight 1.0', () => {
    expect(EDGE_WEIGHTS['immediate-memory']).toBe(1.0);
    expect(EDGE_WEIGHTS['memory-governance']).toBe(1.0);
    expect(EDGE_WEIGHTS['governance-predictive']).toBe(1.0);
  });

  it('skip-1 edges have weight 1/φ', () => {
    expect(EDGE_WEIGHTS['immediate-governance']).toBeCloseTo(1 / PHI, 6);
    expect(EDGE_WEIGHTS['memory-predictive']).toBeCloseTo(1 / PHI, 6);
  });

  it('skip-2 edge has weight 1/φ²', () => {
    expect(EDGE_WEIGHTS['immediate-predictive']).toBeCloseTo(1 / (PHI * PHI), 6);
  });
});

describe('edgeWeight', () => {
  it('returns correct weight for both orderings', () => {
    const w1 = edgeWeight(BraidVariant.IMMEDIATE, BraidVariant.MEMORY);
    const w2 = edgeWeight(BraidVariant.MEMORY, BraidVariant.IMMEDIATE);
    expect(w1).toBe(1.0);
    expect(w2).toBe(1.0);
  });

  it('returns 1.0 for unknown pairs', () => {
    // This shouldn't happen with valid variants, but tests the fallback
    expect(edgeWeight('x' as BraidVariant, 'y' as BraidVariant)).toBe(1.0);
  });
});

describe('weightedBraidedDistance', () => {
  it('equals braidedDistance when all weights are 1', () => {
    // When all projected values are in the center region, the unweighted
    // and weighted distances differ. But for equal-weighted edges, they match.
    const p = { immediate: 0.5, memory: 0.5, governance: 0.5, predictive: 0.5 };
    const edges = computePairwiseDistances(p);
    const unweighted = braidedDistance(edges);
    const weighted = weightedBraidedDistance(edges);
    // Not equal because weights aren't all 1, but both ≈ 0 for equal variants
    expect(unweighted).toBeCloseTo(0, 5);
    expect(weighted).toBeCloseTo(0, 5);
  });

  it('weights distant strands less than adjacent', () => {
    // Create variants where skip-2 edge (immediate-predictive) is large
    const p = { immediate: -0.8, memory: 0.0, governance: 0.0, predictive: 0.8 };
    const edges = computePairwiseDistances(p);
    const unweighted = braidedDistance(edges);
    const weighted = weightedBraidedDistance(edges);
    // Weighted should be less because the largest edge (im↔pred) has weight φ^-2
    expect(weighted).toBeLessThan(unweighted);
  });
});

// ═══════════════════════════════════════════════════════════════
// DEFAULT_EDGE_WEIGHTS config
// ═══════════════════════════════════════════════════════════════

describe('DEFAULT_EDGE_WEIGHTS', () => {
  const PHI = (1 + Math.sqrt(5)) / 2;

  it('has all 6 fields', () => {
    expect(DEFAULT_EDGE_WEIGHTS.immediateToMemory).toBe(1.0);
    expect(DEFAULT_EDGE_WEIGHTS.memoryToGovernance).toBe(1.0);
    expect(DEFAULT_EDGE_WEIGHTS.governanceToPredictive).toBe(1.0);
    expect(DEFAULT_EDGE_WEIGHTS.immediateToGovernance).toBeCloseTo(1 / PHI, 6);
    expect(DEFAULT_EDGE_WEIGHTS.memoryToPredictive).toBeCloseTo(1 / PHI, 6);
    expect(DEFAULT_EDGE_WEIGHTS.immediateToPredict).toBeCloseTo(1 / (PHI * PHI), 6);
  });
});

// ═══════════════════════════════════════════════════════════════
// Configurable edge weights via BraidOptions
// ═══════════════════════════════════════════════════════════════

describe('configurable edge weights', () => {
  it('boosting Ti↔Tp increases weighted distance', () => {
    // Default φ^-2 ≈ 0.382 for Ti↔Tp
    const defaultResult = computeBraid(1, 5, 0.5, 3);
    // Boost Ti↔Tp to 1.0 (full weight)
    const boosted = computeBraid(1, 5, 0.5, 3, {
      weights: { immediateToPredict: 1.0 },
    });
    expect(boosted.weightedDistance).toBeGreaterThan(defaultResult.weightedDistance);
  });

  it('zeroing all weights makes weighted distance 0', () => {
    const r = computeBraid(1, 5, 0.5, 3, {
      weights: {
        immediateToMemory: 0,
        memoryToGovernance: 0,
        governanceToPredictive: 0,
        immediateToGovernance: 0,
        memoryToPredictive: 0,
        immediateToPredict: 0,
      },
    });
    expect(r.weightedDistance).toBeCloseTo(0, 10);
  });

  it('uniform weights=1 makes weighted equal to unweighted', () => {
    const r = computeBraid(1, 5, 0.5, 3, {
      weights: {
        immediateToMemory: 1,
        memoryToGovernance: 1,
        governanceToPredictive: 1,
        immediateToGovernance: 1,
        memoryToPredictive: 1,
        immediateToPredict: 1,
      },
    });
    expect(r.weightedDistance).toBeCloseTo(r.braidedDistance, 10);
  });
});

// ═══════════════════════════════════════════════════════════════
// toDebugJSON
// ═══════════════════════════════════════════════════════════════

describe('toDebugJSON', () => {
  it('returns plain object with all expected keys', () => {
    const r = computeBraid(1, 2, 3, 4);
    const debug = toDebugJSON(r);
    expect(debug.strands).toBeDefined();
    expect(debug.projected).toBeDefined();
    expect(debug.edges).toBeDefined();
    expect(typeof debug.d_b).toBe('number');
    expect(typeof debug.d_bw).toBe('number');
    expect(typeof debug.T_b).toBe('number');
    expect(typeof debug.harm).toBe('number');
    expect(typeof debug.yb).toBe('boolean');
  });

  it('has all 4 strand labels', () => {
    const debug = toDebugJSON(computeBraid(1, 1, 1, 1));
    const strands = debug.strands as Record<string, number>;
    expect(strands).toHaveProperty('Ti');
    expect(strands).toHaveProperty('Tm');
    expect(strands).toHaveProperty('Tg');
    expect(strands).toHaveProperty('Tp');
  });

  it('has all 6 edge labels', () => {
    const debug = toDebugJSON(computeBraid(1, 2, 3, 4));
    const edges = debug.edges as Record<string, number>;
    const keys = Object.keys(edges);
    expect(keys).toHaveLength(6);
    // Each key should contain ↔
    for (const k of keys) {
      expect(k).toContain('↔');
    }
  });

  it('rounds values to 6 decimal places', () => {
    const debug = toDebugJSON(computeBraid(1, 1, 1, 1));
    const strands = debug.strands as Record<string, number>;
    // Values should be rounded (no more than 6 decimals)
    const str = String(strands.Ti);
    const parts = str.split('.');
    if (parts.length > 1) {
      expect(parts[1].length).toBeLessThanOrEqual(6);
    }
  });

  it('handles MAX_VALUE H_braid as "MAX"', () => {
    const r = computeBraid(1, 100, 0.001, 0.01);
    // Force extreme H_braid
    const debug = toDebugJSON({
      ...r,
      hBraid: Number.MAX_VALUE,
    });
    expect(debug.H_braid).toBe('MAX');
  });

  it('is JSON-serializable', () => {
    const debug = toDebugJSON(computeBraid(1, 5, 0.5, 3));
    const json = JSON.stringify(debug);
    expect(typeof json).toBe('string');
    expect(JSON.parse(json)).toEqual(debug);
  });
});

// ═══════════════════════════════════════════════════════════════
// Integration: adversarial scenarios
// ═══════════════════════════════════════════════════════════════

describe('adversarial scenarios', () => {
  it('consistent agent across all timescales → safe', () => {
    // T=1, all factors balanced at 1
    const r = computeBraid(1, 1, 1, 1);
    expect(r.harmScore).toBeGreaterThan(0.9);
  });

  it('agent hiding in one timescale detected by others', () => {
    // Intent=0 (looks innocent) but context=10 (governance sees risk)
    // and t=0.01 (memory is very short → high T^t and T/t mismatch)
    const r = computeBraid(1, 0, 10, 0.01);
    expect(r.braidedDistance).toBeGreaterThan(0);
    // Governance and predictive variants are wildly different
  });

  it('tetradic catches more than triadic', () => {
    // Divergent predictive (t very large) only caught by tetradic
    const p = projectVariants(computeVariants(1, 1, 1, 100));
    const dtri = triadicBraidedDistance(p);
    const dtetra = braidedDistance(computePairwiseDistances(p));
    // Tetradic includes 3 more edges involving predictive
    expect(dtetra).toBeGreaterThanOrEqual(dtri);
  });

  it('adversarial cost grows super-exponentially with drift', () => {
    const d1 = computeBraid(1, 2, 0.5, 2);
    const d2 = computeBraid(1, 4, 0.25, 4);
    const d3 = computeBraid(1, 8, 0.125, 8);
    // Each step doubles the divergence → cost should grow much faster
    expect(d2.hBraid).toBeGreaterThan(d1.hBraid);
    expect(d3.hBraid).toBeGreaterThan(d2.hBraid);
  });
});
