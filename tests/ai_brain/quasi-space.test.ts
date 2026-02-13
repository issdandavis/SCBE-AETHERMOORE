/**
 * Quasicrystal Quasi-Space Unit Tests
 *
 * Tests for icosahedral projection, voxel realm classification,
 * octree operations, and Penrose tiling integration.
 *
 * @layer Layer 4, Layer 5, Layer 9
 */

import { describe, expect, it } from 'vitest';

import {
  BRAIN_DIMENSIONS,
  UnifiedBrainState,
  brainStateToPenrose,
  classifyVoxelRealm,
  createOctreeRoot,
  icosahedralProjection,
  octreeInsert,
  quasicrystalPotential,
  type OctreeNode,
} from '../../src/ai_brain/index';

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

function countOctreeChildren(node: OctreeNode): number {
  let count = 0;
  for (const child of node.children) {
    if (child) {
      count += 1 + countOctreeChildren(child);
    }
  }
  return count;
}

function maxOctreeDepth(node: OctreeNode): number {
  let max = node.depth;
  for (const child of node.children) {
    if (child) {
      max = Math.max(max, maxOctreeDepth(child));
    }
  }
  return max;
}

// ═══════════════════════════════════════════════════════════════
// Icosahedral Projection
// ═══════════════════════════════════════════════════════════════

describe('icosahedralProjection', () => {
  it('should project 6D vector to 6D vector', () => {
    const input = [1, 0, 0, 0, 0, 0];
    const projected = icosahedralProjection(input);
    expect(projected).toHaveLength(6);
  });

  it('should handle zero vector', () => {
    const zero = [0, 0, 0, 0, 0, 0];
    const projected = icosahedralProjection(zero);
    for (const v of projected) {
      expect(v).toBeCloseTo(0, 10);
    }
  });

  it('should produce different output for different inputs', () => {
    const a = icosahedralProjection([1, 0, 0, 0, 0, 0]);
    const b = icosahedralProjection([0, 1, 0, 0, 0, 0]);
    const same = a.every((v, i) => Math.abs(v - b[i]) < 1e-10);
    expect(same).toBe(false);
  });

  it('normalizes output to unit sphere', () => {
    const result = icosahedralProjection([1, 2, 3, 4, 5, 6]);
    const norm = Math.sqrt(result.reduce((s, v) => s + v * v, 0));
    expect(norm).toBeCloseTo(1.0, 8);
  });

  it('normalizes for various input magnitudes', () => {
    const inputs = [
      [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
      [10, 20, 30, 40, 50, 60],
      [0.001, 0.002, 0.003, 0.004, 0.005, 0.006],
    ];
    for (const input of inputs) {
      const result = icosahedralProjection(input);
      const norm = Math.sqrt(result.reduce((s, v) => s + v * v, 0));
      expect(norm).toBeCloseTo(1.0, 6);
    }
  });

  it('accepts vectors longer than 6D (ignores extras)', () => {
    const result = icosahedralProjection([1, 0, 0, 0, 0, 0, 99, 99]);
    expect(result).toHaveLength(6);
  });

  it('throws RangeError for vectors shorter than 6D', () => {
    expect(() => icosahedralProjection([1, 0, 0])).toThrow(RangeError);
    expect(() => icosahedralProjection([])).toThrow(RangeError);
    expect(() => icosahedralProjection([1])).toThrow(RangeError);
  });

  it('is deterministic', () => {
    const v = [1, 2, 3, 4, 5, 6];
    const r1 = icosahedralProjection(v);
    const r2 = icosahedralProjection(v);
    for (let i = 0; i < 6; i++) {
      expect(r1[i]).toBe(r2[i]);
    }
  });

  it('all output components are finite', () => {
    const result = icosahedralProjection([1, -2, 3, -4, 5, -6]);
    for (const v of result) {
      expect(Number.isFinite(v)).toBe(true);
    }
  });

  it('collinear inputs produce identical directions', () => {
    const r1 = icosahedralProjection([1, 2, 3, 4, 5, 6]);
    const r2 = icosahedralProjection([2, 4, 6, 8, 10, 12]);
    // Same direction (both normalized to unit sphere)
    for (let i = 0; i < 6; i++) {
      expect(r1[i]).toBeCloseTo(r2[i], 8);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Voxel Realm Classification
// ═══════════════════════════════════════════════════════════════

describe('classifyVoxelRealm', () => {
  it('should classify origin as gold (safe)', () => {
    expect(classifyVoxelRealm([0, 0, 0])).toBe('gold');
  });

  it('should classify near-boundary as red', () => {
    expect(classifyVoxelRealm([0.96, 0, 0])).toBe('red');
  });

  it('should classify mid-range as purple', () => {
    expect(classifyVoxelRealm([0.5, 0.5, 0])).toBe('purple');
  });

  it('r < 0.5 is gold', () => {
    expect(classifyVoxelRealm([0.3, 0.2, 0.1])).toBe('gold');
    expect(classifyVoxelRealm([0.49, 0, 0])).toBe('gold');
  });

  it('0.5 <= r < 0.95 is purple', () => {
    expect(classifyVoxelRealm([0.5, 0, 0])).toBe('purple');
    expect(classifyVoxelRealm([0.7, 0, 0])).toBe('purple');
    expect(classifyVoxelRealm([0.94, 0, 0])).toBe('purple');
  });

  it('r >= 0.95 is red', () => {
    expect(classifyVoxelRealm([0.95, 0, 0])).toBe('red');
    expect(classifyVoxelRealm([0.99, 0, 0])).toBe('red');
    expect(classifyVoxelRealm([1.0, 0, 0])).toBe('red');
  });

  it('works for 6D vectors', () => {
    // norm ~ 0.245
    expect(classifyVoxelRealm([0.1, 0.1, 0.1, 0.1, 0.1, 0.1])).toBe('gold');
  });

  it('boundary: r = 0.5 is purple (not gold)', () => {
    expect(classifyVoxelRealm([0.5, 0, 0])).toBe('purple');
  });

  it('boundary: r = 0.95 is red (not purple)', () => {
    expect(classifyVoxelRealm([0.95, 0, 0])).toBe('red');
  });
});

// ═══════════════════════════════════════════════════════════════
// Octree Operations
// ═══════════════════════════════════════════════════════════════

describe('Octree', () => {
  it('should create root with correct bounds', () => {
    const root = createOctreeRoot();
    expect(root.center).toEqual([0, 0, 0]);
    expect(root.halfWidth).toBe(1);
    expect(root.points).toHaveLength(0);
  });

  it('should insert points', () => {
    const root = createOctreeRoot();
    octreeInsert(root, [0.1, 0.2, 0.3]);
    expect(root.points).toHaveLength(1);
    expect(root.points[0]).toEqual([0.1, 0.2, 0.3]);
  });

  it('should classify realm on insert', () => {
    const root = createOctreeRoot();
    octreeInsert(root, [0.1, 0.1, 0.1]);
    expect(root.realm).toBe('gold');
  });

  it('creates root with default 3D, capacity 8', () => {
    const root = createOctreeRoot();
    expect(root.center).toHaveLength(3);
    expect(root.capacity).toBe(8);
    expect(root.depth).toBe(0);
    expect(root.realm).toBe('gold');
    expect(root.children).toHaveLength(8); // 2^3
  });

  it('creates root with custom dimensions', () => {
    const root = createOctreeRoot(6);
    expect(root.center).toHaveLength(6);
    expect(root.children).toHaveLength(64); // 2^6
  });

  it('creates root with custom capacity', () => {
    const root = createOctreeRoot(3, 16);
    expect(root.capacity).toBe(16);
  });

  it('children are initially null', () => {
    const root = createOctreeRoot();
    for (const child of root.children) {
      expect(child).toBeNull();
    }
  });

  it('inserts multiple points up to capacity', () => {
    const root = createOctreeRoot(3, 4);
    for (let i = 0; i < 4; i++) {
      octreeInsert(root, [i * 0.1, 0, 0]);
    }
    expect(root.points).toHaveLength(4);
  });

  it('subdivides when capacity exceeded', () => {
    const root = createOctreeRoot(3, 2);
    octreeInsert(root, [0.1, 0.1, 0.1]);
    octreeInsert(root, [0.2, 0.2, 0.2]);
    octreeInsert(root, [0.3, 0.3, 0.3]);
    const hasChild = root.children.some((c) => c !== null);
    expect(hasChild).toBe(true);
  });

  it('updates realm based on inserted point', () => {
    const root = createOctreeRoot();
    octreeInsert(root, [0.8, 0, 0]);
    expect(root.realm).toBe('purple');
  });

  it('handles many insertions without error', () => {
    const root = createOctreeRoot();
    for (let i = 0; i < 100; i++) {
      octreeInsert(root, [
        Math.random() * 0.9 - 0.45,
        Math.random() * 0.9 - 0.45,
        Math.random() * 0.9 - 0.45,
      ]);
    }
    expect(root.points.length + countOctreeChildren(root)).toBeGreaterThan(0);
  });

  it('respects maxDepth', () => {
    const root = createOctreeRoot(3, 1);
    for (let i = 0; i < 20; i++) {
      octreeInsert(root, [0.1 + i * 0.001, 0.1, 0.1], 3);
    }
    const maxD = maxOctreeDepth(root);
    expect(maxD).toBeLessThanOrEqual(3);
  });
});

// ═══════════════════════════════════════════════════════════════
// Penrose Tiling Integration
// ═══════════════════════════════════════════════════════════════

describe('brainStateToPenrose', () => {
  it('should produce a 2D Penrose coordinate from a brain state vector', () => {
    const state = UnifiedBrainState.safeOrigin().toVector();
    const penrose = brainStateToPenrose(state);
    expect(penrose).toHaveLength(2);
    expect(Number.isFinite(penrose[0])).toBe(true);
    expect(Number.isFinite(penrose[1])).toBe(true);
  });

  it('throws for vectors shorter than 6D', () => {
    expect(() => brainStateToPenrose([1, 2])).toThrow(RangeError);
  });

  it('accepts exactly 6D vector', () => {
    const [x, y] = brainStateToPenrose([1, 0, 0, 0, 0, 0]);
    expect(Number.isFinite(x)).toBe(true);
    expect(Number.isFinite(y)).toBe(true);
  });

  it('is deterministic', () => {
    const state = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6];
    const [x1, y1] = brainStateToPenrose(state);
    const [x2, y2] = brainStateToPenrose(state);
    expect(x1).toBe(x2);
    expect(y1).toBe(y2);
  });

  it('different states map to different Penrose coordinates', () => {
    const s1 = new Array(BRAIN_DIMENSIONS).fill(0);
    s1[0] = 1;
    const s2 = new Array(BRAIN_DIMENSIONS).fill(0);
    s2[1] = 1;
    const [x1, y1] = brainStateToPenrose(s1);
    const [x2, y2] = brainStateToPenrose(s2);
    expect(Math.abs(x1 - x2) + Math.abs(y1 - y2)).toBeGreaterThan(0.01);
  });

  it('uses golden ratio scaling (output is nontrivial)', () => {
    const state = new Array(BRAIN_DIMENSIONS).fill(0);
    state[0] = 1;
    const [x, y] = brainStateToPenrose(state);
    expect(Math.abs(x) + Math.abs(y)).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Quasicrystal Potential
// ═══════════════════════════════════════════════════════════════

describe('quasicrystalPotential', () => {
  it('should return a finite number', () => {
    const potential = quasicrystalPotential([0.1, 0.2]);
    expect(Number.isFinite(potential)).toBe(true);
  });

  it('V(0, 0) = 1 (maximum potential at origin)', () => {
    const V = quasicrystalPotential([0, 0]);
    expect(V).toBeCloseTo(1.0, 10); // sum of cos(0) = 5, /5 = 1
  });

  it('returns value in [-1, 1]', () => {
    for (let i = 0; i < 100; i++) {
      const x = Math.random() * 10 - 5;
      const y = Math.random() * 10 - 5;
      const V = quasicrystalPotential([x, y]);
      expect(V).toBeGreaterThanOrEqual(-1 - 1e-10);
      expect(V).toBeLessThanOrEqual(1 + 1e-10);
    }
  });

  it('has 5-fold symmetry', () => {
    const r = 1.5;
    const potentials: number[] = [];
    for (let k = 0; k < 5; k++) {
      const angle = (2 * Math.PI * k) / 5;
      potentials.push(quasicrystalPotential([r * Math.cos(angle), r * Math.sin(angle)]));
    }
    for (let i = 1; i < 5; i++) {
      expect(potentials[i]).toBeCloseTo(potentials[0], 8);
    }
  });

  it('is deterministic', () => {
    const p: [number, number] = [2.5, -1.3];
    expect(quasicrystalPotential(p)).toBe(quasicrystalPotential(p));
  });

  it('varies across space', () => {
    const v1 = quasicrystalPotential([0, 0]);
    const v2 = quasicrystalPotential([1, 0]);
    const v3 = quasicrystalPotential([0, 1]);
    const unique = new Set([v1.toFixed(6), v2.toFixed(6), v3.toFixed(6)]);
    expect(unique.size).toBeGreaterThan(1);
  });
});
