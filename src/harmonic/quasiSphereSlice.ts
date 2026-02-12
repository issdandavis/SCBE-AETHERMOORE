/**
 * @file quasiSphereSlice.ts
 * @module harmonic/quasiSphereSlice
 * @layer Layer 4, Layer 5, Layer 12
 * @component 2D Slice Simulator for Quasi-Sphere Visualization
 * @version 3.2.4
 *
 * Renders a 2D cross-section of the 6D quasi-sphere.
 *
 * Purpose:
 * - Show drift → intersection → read in 2D
 * - Visualize zero-sets (nodal surfaces) as contour lines
 * - Display trust gradient (access cost heat map)
 * - Overlay tongue impedance as color channels
 * - Show squad overlaps as intersecting disks
 *
 * The 2D slice is taken along any two of the 6 dimensions,
 * with the other 4 held fixed at specified values.
 */

import type { Vector6D } from './constants.js';
import {
  cymaticField,
  hyperbolicDistance6D,
  accessCost,
  poincareNorm,
  tongueImpedanceAt,
  type CymaticModes,
  DEFAULT_MODES,
  type CHSFNState,
} from './chsfn.js';

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/** Which two dimensions to slice along */
export interface SliceAxes {
  /** First axis index (0-5) */
  dimA: number;
  /** Second axis index (0-5) */
  dimB: number;
  /** Fixed values for the other 4 dimensions */
  fixed: Vector6D;
}

/** A single pixel/cell in the 2D slice */
export interface SliceCell {
  /** Coordinate on axis A */
  a: number;
  /** Coordinate on axis B */
  b: number;
  /** Cymatic field value Φ at this position */
  fieldValue: number;
  /** Hyperbolic distance from origin at this position */
  distance: number;
  /** Access cost H(d*) at this position */
  cost: number;
  /** Whether this is near a zero-set (nodal surface) */
  isZeroSet: boolean;
  /** Poincaré ball norm at this position */
  norm: number;
}

/** Complete 2D slice data */
export interface SliceData {
  /** Axis indices */
  axes: SliceAxes;
  /** Resolution (cells per axis) */
  resolution: number;
  /** Range of coordinates sampled */
  range: [number, number];
  /** 2D grid of cells [row][col] */
  grid: SliceCell[][];
  /** Statistics */
  stats: {
    minField: number;
    maxField: number;
    minCost: number;
    maxCost: number;
    zeroSetCount: number;
    totalCells: number;
  };
}

// ═══════════════════════════════════════════════════════════════
// Slice Computation
// ═══════════════════════════════════════════════════════════════

/**
 * Compute a 2D slice of the 6D quasi-sphere.
 *
 * Samples a grid of points along two chosen axes,
 * evaluating the cymatic field, hyperbolic distance,
 * and access cost at each point.
 *
 * @param axes - Which two dimensions to slice along + fixed values
 * @param resolution - Grid size (resolution × resolution cells)
 * @param range - Coordinate range to sample (default [-0.95, 0.95])
 * @param modes - Cymatic modes
 * @param zeroTolerance - Tolerance for zero-set detection
 * @returns Complete slice data
 */
export function computeSlice(
  axes: SliceAxes,
  resolution: number = 50,
  range: [number, number] = [-0.95, 0.95],
  modes: CymaticModes = DEFAULT_MODES,
  zeroTolerance: number = 0.05
): SliceData {
  const origin: Vector6D = [0, 0, 0, 0, 0, 0];
  const grid: SliceCell[][] = [];

  let minField = Infinity;
  let maxField = -Infinity;
  let minCost = Infinity;
  let maxCost = -Infinity;
  let zeroSetCount = 0;

  const step = (range[1] - range[0]) / (resolution - 1);

  for (let row = 0; row < resolution; row++) {
    const rowCells: SliceCell[] = [];
    const b = range[0] + row * step;

    for (let col = 0; col < resolution; col++) {
      const a = range[0] + col * step;

      // Build 6D position from slice
      const pos = [...axes.fixed] as Vector6D;
      pos[axes.dimA] = a;
      pos[axes.dimB] = b;

      const norm = poincareNorm(pos);

      // Skip points outside the Poincaré ball
      if (norm >= 0.999) {
        rowCells.push({
          a,
          b,
          fieldValue: 0,
          distance: Infinity,
          cost: Infinity,
          isZeroSet: false,
          norm,
        });
        continue;
      }

      const fieldValue = cymaticField(pos, modes);
      const distance = hyperbolicDistance6D(pos, origin);
      const cost = accessCost(distance);
      const isZeroSet = Math.abs(fieldValue) < zeroTolerance;

      if (isZeroSet) zeroSetCount++;
      minField = Math.min(minField, fieldValue);
      maxField = Math.max(maxField, fieldValue);
      if (isFinite(cost)) {
        minCost = Math.min(minCost, cost);
        maxCost = Math.max(maxCost, cost);
      }

      rowCells.push({ a, b, fieldValue, distance, cost, isZeroSet, norm });
    }

    grid.push(rowCells);
  }

  return {
    axes,
    resolution,
    range,
    grid,
    stats: {
      minField,
      maxField,
      minCost: isFinite(minCost) ? minCost : 0,
      maxCost: isFinite(maxCost) ? maxCost : 0,
      zeroSetCount,
      totalCells: resolution * resolution,
    },
  };
}

/**
 * Extract zero-set contour points from a slice.
 *
 * Returns coordinates where the cymatic field crosses zero —
 * these are the addressable semantic loci.
 *
 * @param slice - Computed slice data
 * @returns Array of [a, b] coordinates on zero-sets
 */
export function extractZeroSets(slice: SliceData): [number, number][] {
  const points: [number, number][] = [];

  for (const row of slice.grid) {
    for (const cell of row) {
      if (cell.isZeroSet && isFinite(cell.distance)) {
        points.push([cell.a, cell.b]);
      }
    }
  }

  return points;
}

/**
 * Compute a cost heat map from a slice.
 *
 * Returns a 2D array of normalized access costs [0, 1],
 * suitable for visualization as a heat map.
 *
 * @param slice - Computed slice data
 * @returns 2D array of normalized costs [row][col]
 */
export function costHeatMap(slice: SliceData): number[][] {
  const range = slice.stats.maxCost - slice.stats.minCost;
  if (range <= 0) {
    return slice.grid.map((row) => row.map(() => 0));
  }

  return slice.grid.map((row) =>
    row.map((cell) => {
      if (!isFinite(cell.cost)) return 1;
      return Math.min((cell.cost - slice.stats.minCost) / range, 1);
    })
  );
}

/**
 * Simulate drift on a 2D slice.
 *
 * Takes an initial position within the slice and traces the drift
 * trajectory, returning the path as a sequence of [a, b] coordinates.
 *
 * @param axes - Slice axes configuration
 * @param startA - Starting coordinate on axis A
 * @param startB - Starting coordinate on axis B
 * @param steps - Number of drift steps
 * @param stepSize - Integration step size
 * @param modes - Cymatic modes
 * @returns Array of [a, b] coordinates along drift path
 */
export function simulateDrift2D(
  axes: SliceAxes,
  startA: number,
  startB: number,
  steps: number = 100,
  stepSize: number = 0.005,
  modes: CymaticModes = DEFAULT_MODES
): [number, number][] {
  const origin: Vector6D = [0, 0, 0, 0, 0, 0];
  const path: [number, number][] = [[startA, startB]];

  let pos = [...axes.fixed] as Vector6D;
  pos[axes.dimA] = startA;
  pos[axes.dimB] = startB;

  for (let s = 0; s < steps; s++) {
    const norm = poincareNorm(pos);
    if (norm >= 0.99) break;

    // Numerical gradient along the two slice dimensions
    const h = 1e-5;

    const posA = [...pos] as Vector6D;
    posA[axes.dimA] += h;
    const posB = [...pos] as Vector6D;
    posB[axes.dimB] += h;

    const e0 = cymaticField(pos, modes) ** 2 + hyperbolicDistance6D(pos, origin);
    const eA = cymaticField(posA, modes) ** 2 + hyperbolicDistance6D(posA, origin);
    const eB = cymaticField(posB, modes) ** 2 + hyperbolicDistance6D(posB, origin);

    const gradA = (eA - e0) / h;
    const gradB = (eB - e0) / h;

    // Drift: move against gradient
    pos[axes.dimA] -= stepSize * gradA;
    pos[axes.dimB] -= stepSize * gradB;

    // Clamp inside ball
    const newNorm = poincareNorm(pos);
    if (newNorm >= 0.99) {
      const scale = 0.98 / newNorm;
      for (let i = 0; i < 6; i++) pos[i] *= scale;
    }

    path.push([pos[axes.dimA], pos[axes.dimB]]);
  }

  return path;
}

/**
 * Render a slice as ASCII art for terminal visualization.
 *
 * Uses characters to represent field intensity:
 *   '·' = low field, '○' = zero-set, '█' = high field, ' ' = outside ball
 *
 * @param slice - Computed slice data
 * @param driftPath - Optional drift path to overlay (shown as '*')
 * @returns Multi-line string of ASCII art
 */
export function renderSliceASCII(
  slice: SliceData,
  driftPath?: [number, number][]
): string {
  const chars = [' ', '·', '░', '▒', '▓', '█'];
  const step = (slice.range[1] - slice.range[0]) / (slice.resolution - 1);

  // Build path lookup
  const pathSet = new Set<string>();
  if (driftPath) {
    for (const [a, b] of driftPath) {
      const col = Math.round((a - slice.range[0]) / step);
      const row = Math.round((b - slice.range[0]) / step);
      pathSet.add(`${row},${col}`);
    }
  }

  const lines: string[] = [];
  const fieldRange = slice.stats.maxField - slice.stats.minField;

  for (let row = slice.resolution - 1; row >= 0; row--) {
    let line = '';
    for (let col = 0; col < slice.resolution; col++) {
      const cell = slice.grid[row][col];

      if (pathSet.has(`${row},${col}`)) {
        line += '*';
      } else if (!isFinite(cell.distance)) {
        line += ' ';
      } else if (cell.isZeroSet) {
        line += '○';
      } else if (fieldRange > 0) {
        const normalized = (Math.abs(cell.fieldValue) - 0) / (fieldRange || 1);
        const idx = Math.min(Math.floor(normalized * (chars.length - 1)), chars.length - 1);
        line += chars[idx];
      } else {
        line += '·';
      }
    }
    lines.push(line);
  }

  return lines.join('\n');
}
