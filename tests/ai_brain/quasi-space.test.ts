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
  UnifiedBrainState,
  brainStateToPenrose,
  classifyVoxelRealm,
  createOctreeRoot,
  icosahedralProjection,
  octreeInsert,
  quasicrystalPotential,
} from '../../src/ai_brain/index';

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
});

// ═══════════════════════════════════════════════════════════════
// Voxel Realm Classification
// ═══════════════════════════════════════════════════════════════

describe('classifyVoxelRealm', () => {
  it('should classify origin as gold (safe)', () => {
    const realm = classifyVoxelRealm([0, 0, 0]);
    expect(realm).toBe('gold');
  });

  it('should classify near-boundary as red', () => {
    const realm = classifyVoxelRealm([0.96, 0, 0]);
    expect(realm).toBe('red');
  });

  it('should classify mid-range as purple', () => {
    const realm = classifyVoxelRealm([0.5, 0.5, 0]);
    expect(realm).toBe('purple');
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
});

describe('quasicrystalPotential', () => {
  it('should return a finite number', () => {
    const point = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6];
    const potential = quasicrystalPotential(point);
    expect(Number.isFinite(potential)).toBe(true);
  });

  it('should be non-negative', () => {
    const point = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6];
    const potential = quasicrystalPotential(point);
    expect(potential).toBeGreaterThanOrEqual(0);
  });
});
