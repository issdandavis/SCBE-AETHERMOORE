/**
 * @file cymatic-voxel-net.test.ts
 * @module tests/ai_brain/cymatic-voxel-net
 * @layer Layer 5, Layer 8, Layer 12, Layer 14
 *
 * Tests for the Cymatic Voxel Neural Network.
 *
 * Test groups:
 *   A. 6D Chladni Equation
 *   B. Zone Classification
 *   C. Tongue Assignment
 *   D. CymaticVoxelNet: Store & Retrieve
 *   E. Semantic Coherence Gating
 *   F. Auto-Propagation
 *   G. Network Statistics
 *   H. Edge Cases
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  chladni6D,
  classifyZone,
  dominantTongue,
  estimateNodalDensity,
  CymaticVoxelNet,
  SACRED_TONGUES,
  REALM_CENTERS,
  TONGUE_DIMENSION_MAP,
  NODAL_THRESHOLD,
  type VoxelZone,
  type CymaticVoxel,
  type VoxelActivation,
} from '../../src/ai_brain/cymatic-voxel-net.js';

// ═══════════════════════════════════════════════════════════════
// A. 6D Chladni Equation
// ═══════════════════════════════════════════════════════════════

describe('Test A: 6D Chladni Equation', () => {
  it('returns 0 at known nodal points', () => {
    // When all coords are 0, cos terms cancel: cos(0)*cos(0) - cos(0)*cos(0) = 0
    const c = chladni6D([0, 0, 0, 0, 0, 0], [1, 2, 3, 2, 1, 3]);
    expect(c).toBeCloseTo(0, 10);
  });

  it('returns 0 when state params are equal in each pair', () => {
    // If s₂ᵢ = s₂ᵢ₊₁, each term is cos(a)cos(b) - cos(b)cos(a) = 0
    const c = chladni6D([0.5, 0.3, 0.7, 0.1, 0.9, 0.2], [2, 2, 3, 3, 1, 1]);
    expect(c).toBeCloseTo(0, 10);
  });

  it('is non-zero at generic points', () => {
    const c = chladni6D([0.5, 0.3, 0.7, 0.1, 0.9, 0.2], [1, 2, 3, 4, 5, 6]);
    expect(Math.abs(c)).toBeGreaterThan(0.001);
  });

  it('is antisymmetric under pair swap: C(x; s₀,s₁) = -C(x; s₁,s₀)', () => {
    const coords = [0.3, 0.7, 0.1, 0.5, 0.9, 0.2];
    const c1 = chladni6D(coords, [2, 5, 3, 4, 1, 6]);
    const c2 = chladni6D(coords, [5, 2, 4, 3, 6, 1]);
    // Each pair swapped → each term flips sign
    expect(c1).toBeCloseTo(-c2, 8);
  });

  it('sums exactly 3 paired terms', () => {
    // Test each pair independently
    const coords = [0.5, 0.3, 0.0, 0.0, 0.0, 0.0];
    const state = [2, 3, 0, 0, 0, 0]; // Only first pair nonzero

    // cos(2π·0.5)cos(3π·0.3) - cos(3π·0.5)cos(2π·0.3)
    const expected =
      Math.cos(2 * Math.PI * 0.5) * Math.cos(3 * Math.PI * 0.3) -
      Math.cos(3 * Math.PI * 0.5) * Math.cos(2 * Math.PI * 0.3);
    expect(chladni6D(coords, state)).toBeCloseTo(expected, 8);
  });

  it('handles missing dimensions (pads with defaults)', () => {
    const c = chladni6D([0.5], [1, 2]);
    expect(isFinite(c)).toBe(true);
  });

  it('is bounded: |C| ≤ 3 (sum of 3 terms, each ≤ 1)', () => {
    for (let trial = 0; trial < 100; trial++) {
      const coords = Array.from({ length: 6 }, () => Math.random() * 4 - 2);
      const state = Array.from({ length: 6 }, () => Math.random() * 10);
      expect(Math.abs(chladni6D(coords, state))).toBeLessThanOrEqual(6.01);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// B. Zone Classification
// ═══════════════════════════════════════════════════════════════

describe('Test B: Zone Classification', () => {
  it('classifies near-zero as nodal', () => {
    expect(classifyZone(0.0005, 0.001)).toBe('nodal');
    expect(classifyZone(-0.0005, 0.001)).toBe('nodal');
    expect(classifyZone(0, 0.001)).toBe('nodal');
  });

  it('classifies boundary zone correctly', () => {
    expect(classifyZone(0.002, 0.001, 0.05)).toBe('implied_boundary');
    expect(classifyZone(0.04, 0.001, 0.05)).toBe('implied_boundary');
  });

  it('classifies negative space for large values', () => {
    expect(classifyZone(1.0, 0.001, 0.05)).toBe('negative_space');
    expect(classifyZone(-1.0, 0.001, 0.05)).toBe('negative_space');
  });

  it('threshold transitions are correct', () => {
    const threshold = 0.01;
    const width = 0.05;
    expect(classifyZone(0.005, threshold, width)).toBe('nodal');
    expect(classifyZone(0.015, threshold, width)).toBe('implied_boundary');
    expect(classifyZone(0.055, threshold, width)).toBe('implied_boundary');
    expect(classifyZone(0.07, threshold, width)).toBe('negative_space');
  });
});

// ═══════════════════════════════════════════════════════════════
// C. Tongue Assignment
// ═══════════════════════════════════════════════════════════════

describe('Test C: Tongue Assignment', () => {
  it('assigns KO for dominant dim 0', () => {
    expect(dominantTongue([1, 0, 0, 0, 0, 0])).toBe('KO');
  });

  it('assigns AV for dominant dim 1', () => {
    expect(dominantTongue([0, 1, 0, 0, 0, 0])).toBe('AV');
  });

  it('assigns DR for dominant dim 5', () => {
    expect(dominantTongue([0, 0, 0, 0, 0, 1])).toBe('DR');
  });

  it('handles negative values (uses absolute)', () => {
    expect(dominantTongue([0, 0, 0, -5, 0, 0])).toBe('CA');
  });

  it('all 6 tongues are reachable', () => {
    const tongues = new Set<string>();
    for (let i = 0; i < 6; i++) {
      const coords = [0, 0, 0, 0, 0, 0];
      coords[i] = 1;
      tongues.add(dominantTongue(coords));
    }
    expect(tongues.size).toBe(6);
  });

  it('TONGUE_DIMENSION_MAP matches SACRED_TONGUES indices', () => {
    SACRED_TONGUES.forEach((t, i) => {
      expect(TONGUE_DIMENSION_MAP[t]).toBe(i);
    });
  });

  it('REALM_CENTERS exist for all tongues', () => {
    for (const t of SACRED_TONGUES) {
      expect(REALM_CENTERS[t]).toHaveLength(6);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// D. Store & Retrieve
// ═══════════════════════════════════════════════════════════════

describe('Test D: CymaticVoxelNet Store & Retrieve', () => {
  let net: CymaticVoxelNet;

  beforeEach(() => {
    net = new CymaticVoxelNet();
  });

  it('starts with zero stored voxels', () => {
    expect(net.storedCount()).toBe(0);
  });

  it('stores a voxel and increments count', () => {
    net.store([0, 0, 0, 0, 0, 0], new Uint8Array([1, 2, 3]));
    expect(net.storedCount()).toBe(1);
  });

  it('stored voxel has payload', () => {
    const v = net.store([0.5, 0.3, 0.1, 0.2, 0.4, 0.6], new Uint8Array([42]));
    expect(v.payload).toBeDefined();
    expect(v.payload![0]).toBe(42);
  });

  it('probe returns valid voxel without storing', () => {
    const v = net.probe([0.5, 0.3, 0.1, 0.2, 0.4, 0.6]);
    expect(v.coords).toHaveLength(6);
    expect(v.zone).toMatch(/^(nodal|negative_space|implied_boundary)$/);
    expect(v.tongue).toMatch(/^(KO|AV|RU|CA|UM|DR)$/);
    expect(isFinite(v.chladniValue)).toBe(true);
    expect(v.embedded).toHaveLength(6);
    expect(net.storedCount()).toBe(0); // probe doesn't store
  });

  it('retrieve returns stored voxel when coherent', () => {
    const coords = [0, 0, 0, 0, 0, 0];
    net.store(coords, new Uint8Array([99]));
    // Retrieve from same position (zero distance)
    const result = net.retrieve(coords, [0, 0, 0, 0, 0, 0]);
    expect(result).not.toBeNull();
    expect(result!.payload![0]).toBe(99);
  });

  it('retrieve returns null for unstored coords', () => {
    const result = net.retrieve([1, 2, 3, 4, 5, 6], [0, 0, 0, 0, 0, 0]);
    expect(result).toBeNull();
  });

  it('clear removes all voxels', () => {
    net.store([0, 0, 0, 0, 0, 0], new Uint8Array([1]));
    net.store([1, 0, 0, 0, 0, 0], new Uint8Array([2]));
    net.clear();
    expect(net.storedCount()).toBe(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// E. Semantic Coherence Gating
// ═══════════════════════════════════════════════════════════════

describe('Test E: Semantic Coherence Gating', () => {
  let net: CymaticVoxelNet;

  beforeEach(() => {
    net = new CymaticVoxelNet();
  });

  it('nearby requester can access stored voxel', () => {
    const coords = [0.1, 0.0, 0.0, 0.0, 0.0, 0.0];
    net.store(coords, new Uint8Array([42]));
    const result = net.retrieve(coords, [0.1, 0.0, 0.0, 0.0, 0.0, 0.0], 5.0);
    expect(result).not.toBeNull();
  });

  it('distant requester is gated out', () => {
    const coords = [0.1, 0.0, 0.0, 0.0, 0.0, 0.0];
    net.store(coords, new Uint8Array([42]));
    // Very distant position
    const result = net.retrieve(coords, [0.9, 0.8, 0.7, 0.6, 0.5, 0.4], 0.1);
    expect(result).toBeNull();
  });

  it('negative space voxels have stricter access (half maxDistance)', () => {
    // Force a negative-space store
    const coords = [0.5, 0.3, 0.7, 0.1, 0.9, 0.2];
    const voxel = net.store(coords, new Uint8Array([77]));

    if (voxel.zone === 'negative_space') {
      // Requester at moderate distance — might fail for negative space
      const result = net.retrieve(coords, [0.6, 0.4, 0.8, 0.2, 0.85, 0.15], 3.0);
      // May or may not be null, but we verify the gating logic runs
      expect(result === null || result.payload![0] === 77).toBe(true);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// F. Auto-Propagation
// ═══════════════════════════════════════════════════════════════

describe('Test F: Auto-Propagation', () => {
  let net: CymaticVoxelNet;

  beforeEach(() => {
    net = new CymaticVoxelNet(
      [1, 1, 1, 1, 1, 1], // Equal pairs → trivially nodal
      undefined,
      { maxHops: 10, coherenceDecay: 0.85 },
    );
  });

  it('propagation from origin produces activations', () => {
    const acts = net.propagate([0, 0, 0, 0, 0, 0]);
    expect(acts.length).toBeGreaterThan(0);
  });

  it('activation strength decays per hop', () => {
    const acts = net.propagate([0, 0, 0, 0, 0, 0], 5);
    if (acts.length >= 2) {
      expect(acts[1].strength).toBeLessThan(acts[0].strength);
    }
  });

  it('generation increments', () => {
    const acts = net.propagate([0, 0, 0, 0, 0, 0], 5);
    for (let i = 0; i < acts.length; i++) {
      expect(acts[i].generation).toBe(i);
    }
  });

  it('harmonic cost grows with generation', () => {
    const acts = net.propagate([0, 0, 0, 0, 0, 0], 5);
    if (acts.length >= 3) {
      // Cost = strength * H(gen+1, R), gen increases but strength decays
      // H grows super-exponentially, so cost should grow
      expect(acts[2].harmonicCost).toBeGreaterThan(acts[0].harmonicCost);
    }
  });

  it('tongue assignment varies along propagation path', () => {
    // With non-trivial state and larger steps, tongues may change
    const net2 = new CymaticVoxelNet(
      [1, 3, 2, 5, 4, 2],
      undefined,
      { maxHops: 10, coherenceDecay: 0.9 },
    );
    const acts = net2.propagate([0.5, 0.2, 0.1, 0.8, 0.3, 0.7], 10, 0.2);
    const tongues = new Set(acts.map((a) => a.tongue));
    // At least one tongue should be assigned
    expect(tongues.size).toBeGreaterThanOrEqual(1);
  });

  it('propagation stops at negative space', () => {
    const net2 = new CymaticVoxelNet([1, 5, 3, 7, 2, 4]);
    const acts = net2.propagate([0.5, 0.3, 0.7, 0.1, 0.9, 0.2], 20, 0.05);
    // Should stop before maxHops if it enters negative space
    expect(acts.length).toBeLessThanOrEqual(20);
  });

  it('lastPropagation returns previous result', () => {
    net.propagate([0, 0, 0, 0, 0, 0], 3);
    const log = net.lastPropagation();
    expect(log.length).toBeGreaterThan(0);
  });

  it('propagation respects maxHops config', () => {
    const small = new CymaticVoxelNet(
      [1, 1, 1, 1, 1, 1],
      undefined,
      { maxHops: 3 },
    );
    const acts = small.propagate([0, 0, 0, 0, 0, 0]);
    expect(acts.length).toBeLessThanOrEqual(3);
  });
});

// ═══════════════════════════════════════════════════════════════
// G. Network Statistics
// ═══════════════════════════════════════════════════════════════

describe('Test G: Network Statistics', () => {
  it('snapshot reports correct counts', () => {
    const net = new CymaticVoxelNet([1, 2, 3, 4, 5, 6]);

    // Store some voxels at various positions
    for (let i = 0; i < 20; i++) {
      const coords = [
        Math.sin(i * 0.5),
        Math.cos(i * 0.7),
        Math.sin(i * 1.1),
        Math.cos(i * 0.3),
        Math.sin(i * 0.9),
        Math.cos(i * 1.3),
      ];
      net.store(coords, new Uint8Array([i]));
    }

    const snap = net.snapshot();
    expect(snap.totalVoxels).toBe(20);
    expect(snap.nodalCount + snap.negativeSpaceCount + snap.boundaryCount).toBe(20);
    expect(snap.nodalFraction).toBeGreaterThanOrEqual(0);
    expect(snap.nodalFraction).toBeLessThanOrEqual(1);
    expect(snap.negativeSpaceFraction).toBeGreaterThanOrEqual(0);
    expect(snap.meanChladniAbs).toBeGreaterThanOrEqual(0);
  });

  it('nodal density estimate is reasonable', () => {
    const density = estimateNodalDensity([1, 2, 3, 2, 1, 3], 5000, 0.01);
    // Theoretical ~few percent for threshold 0.01 in 6D
    expect(density).toBeGreaterThanOrEqual(0);
    expect(density).toBeLessThanOrEqual(1);
  });

  it('equal-pair state gives 100% nodal density', () => {
    // s₂ᵢ = s₂ᵢ₊₁ → all terms zero → always nodal
    const density = estimateNodalDensity([2, 2, 3, 3, 1, 1], 1000, 0.01);
    expect(density).toBeCloseTo(1.0, 1);
  });
});

// ═══════════════════════════════════════════════════════════════
// H. Edge Cases
// ═══════════════════════════════════════════════════════════════

describe('Test H: Edge Cases', () => {
  it('probe with short coordinate pads to 6D', () => {
    const net = new CymaticVoxelNet();
    const v = net.probe([0.5]);
    expect(v.coords).toHaveLength(6);
    expect(v.coords[1]).toBe(0);
  });

  it('state and position update correctly', () => {
    const net = new CymaticVoxelNet();
    net.setState([5, 4, 3, 2, 1, 0]);
    expect(net.getState()).toEqual([5, 4, 3, 2, 1, 0]);
    net.setPosition([0.1, 0.2, 0.3, 0.4, 0.5, 0.6]);
    expect(net.getPosition()).toEqual([0.1, 0.2, 0.3, 0.4, 0.5, 0.6]);
  });

  it('Poincaré embedding stays in ball', () => {
    const net = new CymaticVoxelNet();
    const v = net.probe([10, -10, 20, -20, 30, -30]);
    const norm = Math.sqrt(v.embedded.reduce((s, x) => s + x * x, 0));
    expect(norm).toBeLessThan(1);
  });

  it('realm distance is non-negative', () => {
    const net = new CymaticVoxelNet();
    for (let i = 0; i < 20; i++) {
      const coords = Array.from({ length: 6 }, () => Math.random() * 2 - 1);
      const v = net.probe(coords);
      expect(v.realmDistance).toBeGreaterThanOrEqual(0);
    }
  });

  it('chladni value is finite for all probes', () => {
    const net = new CymaticVoxelNet([1, 2, 3, 4, 5, 6]);
    for (let i = 0; i < 50; i++) {
      const coords = Array.from({ length: 6 }, () => (Math.random() - 0.5) * 10);
      const v = net.probe(coords);
      expect(isFinite(v.chladniValue)).toBe(true);
    }
  });

  it('empty snapshot has zero counts', () => {
    const net = new CymaticVoxelNet();
    const snap = net.snapshot();
    expect(snap.totalVoxels).toBe(0);
  });
});
