/**
 * SCBE Quasicrystal Lattice Module
 *
 * Implements quasicrystalline structures for the SCBE pipeline:
 * - Penrose tiling (5-fold symmetry)
 * - Fibonacci lattice
 * - Ammann-Beenker tiling (8-fold symmetry)
 * - Diffraction pattern analysis
 *
 * Quasicrystals are aperiodic but ordered structures that provide
 * unique mathematical properties useful for cryptographic applications.
 *
 * Key Properties:
 * - Self-similar at multiple scales
 * - Sharp diffraction peaks despite aperiodicity
 * - Golden ratio relationships (φ = (1+√5)/2)
 * - Higher-dimensional projections
 */

import { CONSTANTS, Vector3D, Vector6D } from './constants.js';

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

/** Golden ratio φ = (1+√5)/2 ≈ 1.618033988749895 */
export const PHI = (1 + Math.sqrt(5)) / 2;

/** Inverse golden ratio 1/φ = φ - 1 ≈ 0.618033988749895 */
export const PHI_INV = PHI - 1;

/** Silver ratio δ = 1 + √2 ≈ 2.414213562373095 */
export const SILVER_RATIO = 1 + Math.sqrt(2);

/** π/5 for 5-fold symmetry */
export const PI_5 = Math.PI / 5;

/** π/4 for 8-fold symmetry */
export const PI_4 = Math.PI / 4;

// ═══════════════════════════════════════════════════════════════
// Type Definitions
// ═══════════════════════════════════════════════════════════════

/**
 * 2D point
 */
export type Point2D = [number, number];

/**
 * Penrose tile types
 */
export type PenroseTileType = 'kite' | 'dart' | 'thick_rhombus' | 'thin_rhombus';

/**
 * Penrose tile
 */
export interface PenroseTile {
  type: PenroseTileType;
  vertices: Point2D[];
  center: Point2D;
  angle: number;
}

/**
 * Lattice point with metadata
 */
export interface LatticePoint {
  position: Point2D;
  index: [number, number];
  weight: number;
}

/**
 * Diffraction peak
 */
export interface DiffractionPeak {
  k: Point2D;           // Wave vector
  intensity: number;    // Peak intensity
  order: number;        // Diffraction order
}

/**
 * Quasicrystal configuration
 */
export interface QCLatticeConfig {
  /** Lattice constant (default: 1.0) */
  a?: number;
  /** Number of generations for inflation */
  generations?: number;
  /** Grid resolution for diffraction */
  resolution?: number;
}

// ═══════════════════════════════════════════════════════════════
// Fibonacci Lattice
// ═══════════════════════════════════════════════════════════════

/**
 * Generate Fibonacci numbers up to n
 */
export function fibonacciSequence(n: number): number[] {
  const fib = [0, 1];
  for (let i = 2; i < n; i++) {
    fib[i] = fib[i - 1] + fib[i - 2];
  }
  return fib.slice(0, n);
}

/**
 * Generate Fibonacci word (S -> SL, L -> S)
 * Starting with S, produces: S, SL, SLS, SLSSL, SLSSLSLS, ...
 */
export function fibonacciWord(generations: number): string {
  let S = 'S';
  let L = 'L';

  for (let i = 0; i < generations; i++) {
    const newS = S + L;
    const newL = S;
    S = newS;
    L = newL;
  }

  return S;
}

/**
 * Generate 1D Fibonacci quasilattice
 *
 * Points are placed according to Fibonacci word:
 * S -> short interval (1)
 * L -> long interval (φ)
 */
export function fibonacci1D(generations: number, a: number = 1): number[] {
  const word = fibonacciWord(generations);
  const points: number[] = [0];
  let x = 0;

  for (const char of word) {
    const step = char === 'S' ? a : a * PHI;
    x += step;
    points.push(x);
  }

  return points;
}

/**
 * Generate 2D Fibonacci lattice
 * Uses two 1D Fibonacci lattices rotated by golden angle
 */
export function fibonacci2D(
  n: number,
  a: number = 1
): LatticePoint[] {
  const points: LatticePoint[] = [];
  const goldenAngle = 2 * Math.PI / (PHI * PHI);

  for (let i = 0; i < n; i++) {
    // Sunflower pattern using golden angle
    const r = a * Math.sqrt(i);
    const theta = i * goldenAngle;
    const x = r * Math.cos(theta);
    const y = r * Math.sin(theta);

    points.push({
      position: [x, y],
      index: [i, 0],
      weight: 1 / (1 + i * 0.01), // Decreasing weight
    });
  }

  return points;
}

// ═══════════════════════════════════════════════════════════════
// Penrose Tiling
// ═══════════════════════════════════════════════════════════════

/**
 * Generate vertices for a Penrose rhombus (P3 tiling)
 *
 * Thick rhombus: angles 72° and 108°
 * Thin rhombus: angles 36° and 144°
 */
export function penroseRhombus(
  center: Point2D,
  angle: number,
  size: number,
  isThick: boolean
): Point2D[] {
  const halfAngle = isThick ? PI_5 : PI_5 / 2;

  const vertices: Point2D[] = [];
  const directions = [angle, angle + halfAngle, angle + Math.PI, angle + Math.PI + halfAngle];

  for (let i = 0; i < 4; i++) {
    const r = i % 2 === 0 ? size : size * (isThick ? PHI : PHI_INV);
    vertices.push([
      center[0] + r * Math.cos(directions[i]),
      center[1] + r * Math.sin(directions[i]),
    ]);
  }

  return vertices;
}

/**
 * Penrose substitution rules
 * Deflates tiles into smaller tiles
 */
export function penroseDeflate(tiles: PenroseTile[]): PenroseTile[] {
  const newTiles: PenroseTile[] = [];

  for (const tile of tiles) {
    if (tile.type === 'thick_rhombus') {
      // Thick rhombus -> 2 thick + 1 thin
      const scale = PHI_INV;
      const [A, B, C, D] = tile.vertices;

      // Calculate midpoints and new vertices
      const E = lerpPoint(A, C, PHI_INV);
      const F = lerpPoint(B, D, PHI_INV);

      newTiles.push(
        createTile('thick_rhombus', [A, E, B, lerpPoint(A, B, 0.5)], tile.angle),
        createTile('thick_rhombus', [E, C, D, F], tile.angle + PI_5),
        createTile('thin_rhombus', [E, F, B, lerpPoint(B, E, 0.5)], tile.angle - PI_5),
      );
    } else if (tile.type === 'thin_rhombus') {
      // Thin rhombus -> 1 thick + 1 thin
      const [A, B, C, D] = tile.vertices;
      const E = lerpPoint(A, C, PHI_INV);

      newTiles.push(
        createTile('thick_rhombus', [A, E, B, lerpPoint(A, B, 0.5)], tile.angle),
        createTile('thin_rhombus', [E, C, D, lerpPoint(C, D, 0.5)], tile.angle + PI_5),
      );
    }
  }

  return newTiles;
}

/**
 * Generate initial Penrose tiles (decagon)
 */
export function penroseInitial(center: Point2D, size: number): PenroseTile[] {
  const tiles: PenroseTile[] = [];

  // Create 5 thick rhombi forming a decagon
  for (let i = 0; i < 5; i++) {
    const angle = i * 2 * PI_5;
    const vertices = penroseRhombus(center, angle, size, true);
    tiles.push(createTile('thick_rhombus', vertices, angle));
  }

  return tiles;
}

/**
 * Generate Penrose tiling with n deflation steps
 */
export function penroseTiling(
  center: Point2D,
  size: number,
  generations: number
): PenroseTile[] {
  let tiles = penroseInitial(center, size);

  for (let i = 0; i < generations; i++) {
    tiles = penroseDeflate(tiles);
  }

  return tiles;
}

/**
 * Extract lattice points from Penrose tiling
 */
export function penroseToLattice(tiles: PenroseTile[]): LatticePoint[] {
  const pointMap = new Map<string, LatticePoint>();

  tiles.forEach((tile, tileIdx) => {
    tile.vertices.forEach((v, vIdx) => {
      const key = `${v[0].toFixed(8)},${v[1].toFixed(8)}`;
      if (!pointMap.has(key)) {
        pointMap.set(key, {
          position: v,
          index: [tileIdx, vIdx],
          weight: tile.type === 'thick_rhombus' ? PHI : 1,
        });
      }
    });
  });

  return Array.from(pointMap.values());
}

// ═══════════════════════════════════════════════════════════════
// Ammann-Beenker Tiling (8-fold symmetry)
// ═══════════════════════════════════════════════════════════════

/**
 * Generate Ammann-Beenker square tile
 */
export function ammannBeenkerSquare(
  center: Point2D,
  angle: number,
  size: number
): Point2D[] {
  const vertices: Point2D[] = [];

  for (let i = 0; i < 4; i++) {
    const theta = angle + i * Math.PI / 2;
    vertices.push([
      center[0] + size * Math.cos(theta),
      center[1] + size * Math.sin(theta),
    ]);
  }

  return vertices;
}

/**
 * Generate Ammann-Beenker rhombus (45° acute angle)
 */
export function ammannBeenkerRhombus(
  center: Point2D,
  angle: number,
  size: number
): Point2D[] {
  const vertices: Point2D[] = [];
  const halfAngle = Math.PI / 8;

  const r1 = size;
  const r2 = size / Math.cos(Math.PI / 8);

  for (let i = 0; i < 4; i++) {
    const isLong = i % 2 === 1;
    const theta = angle + i * Math.PI / 2 + (isLong ? halfAngle : 0);
    const r = isLong ? r2 : r1;
    vertices.push([
      center[0] + r * Math.cos(theta),
      center[1] + r * Math.sin(theta),
    ]);
  }

  return vertices;
}

// ═══════════════════════════════════════════════════════════════
// Cut-and-Project Method
// ═══════════════════════════════════════════════════════════════

/**
 * Generate quasicrystal via cut-and-project method
 *
 * Projects points from a higher-dimensional lattice (Z^n)
 * onto a lower-dimensional irrational subspace.
 */
export function cutAndProject2D(
  nDimensions: number,
  range: number,
  windowRadius: number = 1
): LatticePoint[] {
  const points: LatticePoint[] = [];

  // Projection matrix rows (irrational slopes)
  const projMatrix: number[][] = [];
  for (let d = 0; d < 2; d++) {
    projMatrix[d] = [];
    for (let i = 0; i < nDimensions; i++) {
      projMatrix[d][i] = Math.cos(2 * Math.PI * (d * nDimensions + i + 1) / (2 * nDimensions));
    }
  }

  // Internal space projection
  const intMatrix: number[][] = [];
  for (let d = 0; d < nDimensions - 2; d++) {
    intMatrix[d] = [];
    for (let i = 0; i < nDimensions; i++) {
      intMatrix[d][i] = Math.sin(2 * Math.PI * (d * nDimensions + i + 1) / (2 * nDimensions));
    }
  }

  // Generate points from lattice
  const generateLattice = (indices: number[], dim: number) => {
    if (dim === nDimensions) {
      // Check if point is in acceptance window
      let inWindow = true;
      for (let d = 0; d < nDimensions - 2 && inWindow; d++) {
        let coord = 0;
        for (let i = 0; i < nDimensions; i++) {
          coord += intMatrix[d][i] * indices[i];
        }
        if (Math.abs(coord) > windowRadius) {
          inWindow = false;
        }
      }

      if (inWindow) {
        // Project to physical space
        const pos: Point2D = [0, 0];
        for (let d = 0; d < 2; d++) {
          for (let i = 0; i < nDimensions; i++) {
            pos[d] += projMatrix[d][i] * indices[i];
          }
        }

        points.push({
          position: pos,
          index: [indices[0], indices[1]],
          weight: 1 / (1 + norm2(indices) * 0.01),
        });
      }
      return;
    }

    for (let i = -range; i <= range; i++) {
      generateLattice([...indices, i], dim + 1);
    }
  };

  generateLattice([], 0);
  return points;
}

/**
 * Generate 5D -> 2D quasicrystal (Penrose-like)
 */
export function quasicrystal5to2(range: number, windowRadius: number = 1): LatticePoint[] {
  return cutAndProject2D(5, range, windowRadius);
}

/**
 * Generate 4D -> 2D quasicrystal (Ammann-Beenker-like)
 */
export function quasicrystal4to2(range: number, windowRadius: number = 1): LatticePoint[] {
  return cutAndProject2D(4, range, windowRadius);
}

// ═══════════════════════════════════════════════════════════════
// Diffraction Pattern Analysis
// ═══════════════════════════════════════════════════════════════

/**
 * Calculate diffraction pattern for a set of lattice points
 *
 * The structure factor is: S(k) = |Σⱼ exp(i k·rⱼ)|²
 */
export function diffractionPattern(
  points: LatticePoint[],
  kRange: number,
  resolution: number
): DiffractionPeak[] {
  const peaks: DiffractionPeak[] = [];
  const dk = kRange / resolution;

  for (let kx = -resolution; kx <= resolution; kx++) {
    for (let ky = -resolution; ky <= resolution; ky++) {
      const k: Point2D = [kx * dk, ky * dk];

      // Calculate structure factor
      let re = 0, im = 0;
      for (const p of points) {
        const phase = k[0] * p.position[0] + k[1] * p.position[1];
        re += p.weight * Math.cos(phase);
        im += p.weight * Math.sin(phase);
      }

      const intensity = re * re + im * im;

      if (intensity > 0.1 * points.length) {
        peaks.push({
          k,
          intensity,
          order: Math.round(Math.sqrt(kx * kx + ky * ky)),
        });
      }
    }
  }

  // Sort by intensity
  peaks.sort((a, b) => b.intensity - a.intensity);

  return peaks.slice(0, 100); // Top 100 peaks
}

/**
 * Check for n-fold rotational symmetry in diffraction pattern
 */
export function checkRotationalSymmetry(
  peaks: DiffractionPeak[],
  n: number,
  tolerance: number = 0.1
): { hasSymmetry: boolean; score: number } {
  const angleStep = 2 * Math.PI / n;
  let matchScore = 0;
  let totalScore = 0;

  for (const peak of peaks) {
    const peakAngle = Math.atan2(peak.k[1], peak.k[0]);
    const peakRadius = Math.sqrt(peak.k[0] ** 2 + peak.k[1] ** 2);

    // Check for matching peak at rotated positions
    for (let rot = 1; rot < n; rot++) {
      const targetAngle = peakAngle + rot * angleStep;
      const targetK: Point2D = [
        peakRadius * Math.cos(targetAngle),
        peakRadius * Math.sin(targetAngle),
      ];

      // Find closest peak
      let minDist = Infinity;
      let matchIntensity = 0;

      for (const other of peaks) {
        const dist = Math.sqrt(
          (other.k[0] - targetK[0]) ** 2 + (other.k[1] - targetK[1]) ** 2
        );
        if (dist < minDist) {
          minDist = dist;
          matchIntensity = other.intensity;
        }
      }

      totalScore += peak.intensity;
      if (minDist < tolerance * peakRadius) {
        matchScore += Math.min(peak.intensity, matchIntensity);
      }
    }
  }

  const score = totalScore > 0 ? matchScore / totalScore : 0;
  return { hasSymmetry: score > 0.8, score };
}

// ═══════════════════════════════════════════════════════════════
// Integration with SCBE Pipeline
// ═══════════════════════════════════════════════════════════════

/**
 * Convert 6D SCBE vector to quasicrystal position
 * Uses golden ratio projection
 */
export function scbeToQuasicrystal(v: Vector6D): LatticePoint {
  // Project 6D to 2D using icosahedral projection
  const projMatrix = [
    [1, PHI, 0, PHI, -1, 0],
    [PHI, 0, 1, 0, PHI, -1],
  ];

  const pos: Point2D = [0, 0];
  for (let d = 0; d < 2; d++) {
    for (let i = 0; i < 6; i++) {
      pos[d] += projMatrix[d][i] * v[i] / Math.sqrt(2 + PHI);
    }
  }

  return {
    position: pos,
    index: [0, 0],
    weight: norm6(v),
  };
}

/**
 * Find nearest quasicrystal vertex to a point
 */
export function nearestQCVertex(
  point: Point2D,
  lattice: LatticePoint[]
): { nearest: LatticePoint; distance: number } {
  let minDist = Infinity;
  let nearest = lattice[0];

  for (const lp of lattice) {
    const dist = Math.sqrt(
      (point[0] - lp.position[0]) ** 2 +
      (point[1] - lp.position[1]) ** 2
    );
    if (dist < minDist) {
      minDist = dist;
      nearest = lp;
    }
  }

  return { nearest, distance: minDist };
}

/**
 * Calculate quasicrystal potential energy
 * Used for multi-well potential in SCBE Layer 8
 */
export function quasicrystalPotential(
  position: Point2D,
  lattice: LatticePoint[],
  sigma: number = 0.5
): number {
  let V = 0;

  for (const lp of lattice) {
    const dx = position[0] - lp.position[0];
    const dy = position[1] - lp.position[1];
    const distSq = dx * dx + dy * dy;
    V += lp.weight * Math.exp(-distSq / (2 * sigma * sigma));
  }

  return V;
}

/**
 * Quasicrystal-based hash function
 * Maps input bytes to quasicrystal lattice positions
 */
export function quasicrystalHash(
  input: Uint8Array,
  lattice: LatticePoint[]
): { hash: Point2D; path: LatticePoint[] } {
  const path: LatticePoint[] = [];
  let current: Point2D = [0, 0];

  for (const byte of input) {
    // Map byte to angle and radius
    const angle = (byte / 256) * 2 * Math.PI;
    const radius = ((byte % 16) + 1) * 0.1;

    // Move in quasicrystal space
    current = [
      current[0] + radius * Math.cos(angle) * PHI,
      current[1] + radius * Math.sin(angle),
    ];

    // Snap to nearest lattice point
    const { nearest } = nearestQCVertex(current, lattice);
    path.push(nearest);
    current = nearest.position;
  }

  return { hash: current, path };
}

// ═══════════════════════════════════════════════════════════════
// Helper Functions
// ═══════════════════════════════════════════════════════════════

function lerpPoint(a: Point2D, b: Point2D, t: number): Point2D {
  return [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])];
}

function createTile(type: PenroseTileType, vertices: Point2D[], angle: number): PenroseTile {
  const center: Point2D = [
    vertices.reduce((sum, v) => sum + v[0], 0) / vertices.length,
    vertices.reduce((sum, v) => sum + v[1], 0) / vertices.length,
  ];
  return { type, vertices, center, angle };
}

function norm2(v: number[]): number {
  return Math.sqrt(v.reduce((sum, x) => sum + x * x, 0));
}

function norm6(v: Vector6D): number {
  return Math.sqrt(v.reduce((sum, x) => sum + x * x, 0));
}

// ═══════════════════════════════════════════════════════════════
// QC Lattice Provider for SCBE Integration
// ═══════════════════════════════════════════════════════════════

/**
 * Quasicrystal Lattice Provider
 */
export class QCLatticeProvider {
  private lattice: LatticePoint[] = [];
  private config: Required<QCLatticeConfig>;

  constructor(config: QCLatticeConfig = {}) {
    this.config = {
      a: config.a ?? 1.0,
      generations: config.generations ?? 4,
      resolution: config.resolution ?? 32,
    };

    this.generateLattice();
  }

  /**
   * Generate the quasicrystal lattice
   */
  private generateLattice(): void {
    const tiles = penroseTiling([0, 0], this.config.a, this.config.generations);
    this.lattice = penroseToLattice(tiles);
  }

  /**
   * Get all lattice points
   */
  getPoints(): LatticePoint[] {
    return this.lattice;
  }

  /**
   * Map SCBE 6D vector to quasicrystal position
   */
  mapVector(v: Vector6D): LatticePoint {
    return scbeToQuasicrystal(v);
  }

  /**
   * Find nearest vertex
   */
  findNearest(point: Point2D): { nearest: LatticePoint; distance: number } {
    return nearestQCVertex(point, this.lattice);
  }

  /**
   * Calculate potential at position
   */
  potential(position: Point2D, sigma?: number): number {
    return quasicrystalPotential(position, this.lattice, sigma);
  }

  /**
   * Compute diffraction pattern
   */
  diffraction(kRange: number): DiffractionPeak[] {
    return diffractionPattern(this.lattice, kRange, this.config.resolution);
  }

  /**
   * Check rotational symmetry
   */
  checkSymmetry(n: number): { hasSymmetry: boolean; score: number } {
    const peaks = this.diffraction(10);
    return checkRotationalSymmetry(peaks, n);
  }

  /**
   * Hash input using quasicrystal walk
   */
  hash(input: Uint8Array): { hash: Point2D; path: LatticePoint[] } {
    return quasicrystalHash(input, this.lattice);
  }
}

/**
 * Default QC lattice provider instance
 */
export const defaultQCLattice = new QCLatticeProvider();
