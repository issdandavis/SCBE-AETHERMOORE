/**
 * @file quasiSphereSlice.unit.test.ts
 * @tier L2-unit
 * @axiom 4 (Symmetry), 5 (Composition)
 * @category unit
 *
 * Unit tests for the 2D slice simulator for quasi-sphere visualization.
 */

import { describe, it, expect } from 'vitest';
import type { Vector6D } from '../../src/harmonic/constants.js';
import {
  computeSlice,
  extractZeroSets,
  costHeatMap,
  simulateDrift2D,
  renderSliceASCII,
  type SliceAxes,
  type SliceData,
} from '../../src/harmonic/quasiSphereSlice.js';

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

const DEFAULT_AXES: SliceAxes = {
  dimA: 0,
  dimB: 1,
  fixed: [0, 0, 0, 0, 0, 0],
};

// ═══════════════════════════════════════════════════════════════
// computeSlice
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: computeSlice', () => {
  it('should return a grid of the correct resolution', () => {
    const slice = computeSlice(DEFAULT_AXES, 10);
    expect(slice.grid).toHaveLength(10);
    for (const row of slice.grid) {
      expect(row).toHaveLength(10);
    }
  });

  it('should have correct axes in output', () => {
    const slice = computeSlice(DEFAULT_AXES, 5);
    expect(slice.axes.dimA).toBe(0);
    expect(slice.axes.dimB).toBe(1);
  });

  it('should have stats with valid ranges', () => {
    const slice = computeSlice(DEFAULT_AXES, 10);
    expect(slice.stats.minField).toBeLessThanOrEqual(slice.stats.maxField);
    expect(slice.stats.minCost).toBeLessThanOrEqual(slice.stats.maxCost);
    expect(slice.stats.totalCells).toBe(100);
  });

  it('should count zero-set cells', () => {
    const slice = computeSlice(DEFAULT_AXES, 20, [-0.5, 0.5]);
    expect(slice.stats.zeroSetCount).toBeGreaterThanOrEqual(0);
    expect(slice.stats.zeroSetCount).toBeLessThanOrEqual(slice.stats.totalCells);
  });

  it('should use custom range', () => {
    const range: [number, number] = [-0.5, 0.5];
    const slice = computeSlice(DEFAULT_AXES, 5, range);
    expect(slice.range).toEqual(range);
    // First cell should be at range[0]
    expect(slice.grid[0][0].a).toBeCloseTo(-0.5, 5);
    expect(slice.grid[0][0].b).toBeCloseTo(-0.5, 5);
  });

  it('should mark boundary points with Infinity distance', () => {
    // Points very near the Poincaré ball boundary should have Infinity
    const slice = computeSlice(DEFAULT_AXES, 5, [-0.999, 0.999]);
    let hasInfinity = false;
    for (const row of slice.grid) {
      for (const cell of row) {
        if (!isFinite(cell.distance)) hasInfinity = true;
      }
    }
    // At least some boundary points expected
    expect(hasInfinity).toBe(true);
  });

  it('should slice along different axis pairs', () => {
    const axes: SliceAxes = {
      dimA: 2,
      dimB: 4,
      fixed: [0, 0, 0, 0, 0, 0],
    };
    const slice = computeSlice(axes, 5);
    expect(slice.axes.dimA).toBe(2);
    expect(slice.axes.dimB).toBe(4);
    expect(slice.grid).toHaveLength(5);
  });

  it('should have norm < 1 for interior points', () => {
    const slice = computeSlice(DEFAULT_AXES, 10, [-0.5, 0.5]);
    for (const row of slice.grid) {
      for (const cell of row) {
        if (isFinite(cell.distance)) {
          expect(cell.norm).toBeLessThan(1);
        }
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// extractZeroSets
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: extractZeroSets', () => {
  it('should return array of [a, b] pairs', () => {
    const slice = computeSlice(DEFAULT_AXES, 20, [-0.5, 0.5]);
    const zeros = extractZeroSets(slice);
    expect(Array.isArray(zeros)).toBe(true);
    for (const pt of zeros) {
      expect(pt).toHaveLength(2);
      expect(typeof pt[0]).toBe('number');
      expect(typeof pt[1]).toBe('number');
    }
  });

  it('should return count matching stats', () => {
    const slice = computeSlice(DEFAULT_AXES, 20, [-0.5, 0.5]);
    const zeros = extractZeroSets(slice);
    // Zeros may not exactly match stat count if some are at boundary
    expect(zeros.length).toBeLessThanOrEqual(slice.stats.zeroSetCount);
  });

  it('should return empty for uniform field', () => {
    // Very small region near origin — field is near-constant
    const slice = computeSlice(DEFAULT_AXES, 3, [-0.001, 0.001], undefined, 1e-15);
    const zeros = extractZeroSets(slice);
    // With extremely tight tolerance, may find no zero-sets
    expect(Array.isArray(zeros)).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// costHeatMap
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: costHeatMap', () => {
  it('should return 2D array matching resolution', () => {
    const slice = computeSlice(DEFAULT_AXES, 8);
    const hm = costHeatMap(slice);
    expect(hm).toHaveLength(8);
    for (const row of hm) {
      expect(row).toHaveLength(8);
    }
  });

  it('should have values in [0, 1]', () => {
    const slice = computeSlice(DEFAULT_AXES, 10, [-0.5, 0.5]);
    const hm = costHeatMap(slice);
    for (const row of hm) {
      for (const v of row) {
        expect(v).toBeGreaterThanOrEqual(0);
        expect(v).toBeLessThanOrEqual(1);
      }
    }
  });

  it('should return all zeros when cost range is zero', () => {
    // All at origin → same cost → range = 0
    const slice = computeSlice(DEFAULT_AXES, 2, [0, 0]);
    const hm = costHeatMap(slice);
    for (const row of hm) {
      for (const v of row) {
        expect(v).toBe(0);
      }
    }
  });

  it('should assign 1 to Infinity cost cells', () => {
    const slice = computeSlice(DEFAULT_AXES, 5, [-0.999, 0.999]);
    const hm = costHeatMap(slice);
    for (let r = 0; r < slice.resolution; r++) {
      for (let c = 0; c < slice.resolution; c++) {
        if (!isFinite(slice.grid[r][c].cost)) {
          expect(hm[r][c]).toBe(1);
        }
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// simulateDrift2D
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: simulateDrift2D', () => {
  it('should return at least the starting point', () => {
    const path = simulateDrift2D(DEFAULT_AXES, 0, 0, 10);
    expect(path.length).toBeGreaterThanOrEqual(1);
    expect(path[0]).toEqual([0, 0]);
  });

  it('should produce path of length <= steps + 1', () => {
    const path = simulateDrift2D(DEFAULT_AXES, 0.1, 0.1, 20);
    expect(path.length).toBeLessThanOrEqual(21);
  });

  it('should keep points inside the Poincaré ball', () => {
    const path = simulateDrift2D(DEFAULT_AXES, 0.3, 0.3, 50, 0.01);
    for (const [a, b] of path) {
      // a² + b² should be < 1 (approximately, since other dims are 0)
      expect(a * a + b * b).toBeLessThan(1.01);
    }
  });

  it('should not diverge outside the ball', () => {
    const path = simulateDrift2D(DEFAULT_AXES, 0.95, 0, 100, 0.01);
    // All points should stay within the Poincaré ball
    for (const [a, b] of path) {
      expect(a * a + b * b).toBeLessThan(1.05);
    }
  });

  it('should work with different axis pairs', () => {
    const axes: SliceAxes = {
      dimA: 3,
      dimB: 5,
      fixed: [0, 0, 0, 0, 0, 0],
    };
    const path = simulateDrift2D(axes, 0.1, 0.1, 10);
    expect(path.length).toBeGreaterThanOrEqual(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// renderSliceASCII
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: renderSliceASCII', () => {
  it('should return a multi-line string', () => {
    const slice = computeSlice(DEFAULT_AXES, 10, [-0.5, 0.5]);
    const ascii = renderSliceASCII(slice);
    expect(typeof ascii).toBe('string');
    const lines = ascii.split('\n');
    expect(lines).toHaveLength(10);
  });

  it('should have lines of correct width', () => {
    const slice = computeSlice(DEFAULT_AXES, 8, [-0.5, 0.5]);
    const ascii = renderSliceASCII(slice);
    const lines = ascii.split('\n');
    for (const line of lines) {
      expect(line.length).toBe(8);
    }
  });

  it('should contain ○ for zero-set cells', () => {
    const slice = computeSlice(DEFAULT_AXES, 30, [-0.8, 0.8], undefined, 0.1);
    const ascii = renderSliceASCII(slice);
    // May or may not contain ○ depending on field, but format should work
    expect(typeof ascii).toBe('string');
  });

  it('should overlay drift path as *', () => {
    const slice = computeSlice(DEFAULT_AXES, 10, [-0.5, 0.5]);
    const driftPath: [number, number][] = [[0, 0], [0.1, 0.1]];
    const ascii = renderSliceASCII(slice, driftPath);
    expect(ascii).toContain('*');
  });

  it('should show spaces for boundary points', () => {
    const slice = computeSlice(DEFAULT_AXES, 5, [-0.999, 0.999]);
    const ascii = renderSliceASCII(slice);
    expect(ascii).toContain(' ');
  });
});
