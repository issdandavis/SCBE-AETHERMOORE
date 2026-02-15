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
import { type CymaticModes } from './chsfn.js';
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
export declare function computeSlice(axes: SliceAxes, resolution?: number, range?: [number, number], modes?: CymaticModes, zeroTolerance?: number): SliceData;
/**
 * Extract zero-set contour points from a slice.
 *
 * Returns coordinates where the cymatic field crosses zero —
 * these are the addressable semantic loci.
 *
 * @param slice - Computed slice data
 * @returns Array of [a, b] coordinates on zero-sets
 */
export declare function extractZeroSets(slice: SliceData): [number, number][];
/**
 * Compute a cost heat map from a slice.
 *
 * Returns a 2D array of normalized access costs [0, 1],
 * suitable for visualization as a heat map.
 *
 * @param slice - Computed slice data
 * @returns 2D array of normalized costs [row][col]
 */
export declare function costHeatMap(slice: SliceData): number[][];
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
export declare function simulateDrift2D(axes: SliceAxes, startA: number, startB: number, steps?: number, stepSize?: number, modes?: CymaticModes): [number, number][];
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
export declare function renderSliceASCII(slice: SliceData, driftPath?: [number, number][]): string;
//# sourceMappingURL=quasiSphereSlice.d.ts.map