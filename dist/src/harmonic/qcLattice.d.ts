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
import { Vector6D } from './constants.js';
/** Golden ratio φ = (1+√5)/2 ≈ 1.618033988749895 */
export declare const PHI: number;
/** Inverse golden ratio 1/φ = φ - 1 ≈ 0.618033988749895 */
export declare const PHI_INV: number;
/** Silver ratio δ = 1 + √2 ≈ 2.414213562373095 */
export declare const SILVER_RATIO: number;
/** π/5 for 5-fold symmetry */
export declare const PI_5: number;
/** π/4 for 8-fold symmetry */
export declare const PI_4: number;
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
    k: Point2D;
    intensity: number;
    order: number;
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
/**
 * Generate Fibonacci numbers up to n
 */
export declare function fibonacciSequence(n: number): number[];
/**
 * Generate Fibonacci word (S -> SL, L -> S)
 * Starting with S, produces: S, SL, SLS, SLSSL, SLSSLSLS, ...
 */
export declare function fibonacciWord(generations: number): string;
/**
 * Generate 1D Fibonacci quasilattice
 *
 * Points are placed according to Fibonacci word:
 * S -> short interval (1)
 * L -> long interval (φ)
 */
export declare function fibonacci1D(generations: number, a?: number): number[];
/**
 * Generate 2D Fibonacci lattice
 * Uses two 1D Fibonacci lattices rotated by golden angle
 */
export declare function fibonacci2D(n: number, a?: number): LatticePoint[];
/**
 * Generate vertices for a Penrose rhombus (P3 tiling)
 *
 * Thick rhombus: angles 72° and 108°
 * Thin rhombus: angles 36° and 144°
 */
export declare function penroseRhombus(center: Point2D, angle: number, size: number, isThick: boolean): Point2D[];
/**
 * Penrose substitution rules
 * Deflates tiles into smaller tiles
 */
export declare function penroseDeflate(tiles: PenroseTile[]): PenroseTile[];
/**
 * Generate initial Penrose tiles (decagon)
 */
export declare function penroseInitial(center: Point2D, size: number): PenroseTile[];
/**
 * Generate Penrose tiling with n deflation steps
 */
export declare function penroseTiling(center: Point2D, size: number, generations: number): PenroseTile[];
/**
 * Extract lattice points from Penrose tiling
 */
export declare function penroseToLattice(tiles: PenroseTile[]): LatticePoint[];
/**
 * Generate Ammann-Beenker square tile
 */
export declare function ammannBeenkerSquare(center: Point2D, angle: number, size: number): Point2D[];
/**
 * Generate Ammann-Beenker rhombus (45° acute angle)
 */
export declare function ammannBeenkerRhombus(center: Point2D, angle: number, size: number): Point2D[];
/**
 * Generate quasicrystal via cut-and-project method
 *
 * Projects points from a higher-dimensional lattice (Z^n)
 * onto a lower-dimensional irrational subspace.
 */
export declare function cutAndProject2D(nDimensions: number, range: number, windowRadius?: number): LatticePoint[];
/**
 * Generate 5D -> 2D quasicrystal (Penrose-like)
 */
export declare function quasicrystal5to2(range: number, windowRadius?: number): LatticePoint[];
/**
 * Generate 4D -> 2D quasicrystal (Ammann-Beenker-like)
 */
export declare function quasicrystal4to2(range: number, windowRadius?: number): LatticePoint[];
/**
 * Calculate diffraction pattern for a set of lattice points
 *
 * The structure factor is: S(k) = |Σⱼ exp(i k·rⱼ)|²
 */
export declare function diffractionPattern(points: LatticePoint[], kRange: number, resolution: number): DiffractionPeak[];
/**
 * Check for n-fold rotational symmetry in diffraction pattern
 */
export declare function checkRotationalSymmetry(peaks: DiffractionPeak[], n: number, tolerance?: number): {
    hasSymmetry: boolean;
    score: number;
};
/**
 * Convert 6D SCBE vector to quasicrystal position
 * Uses golden ratio projection
 */
export declare function scbeToQuasicrystal(v: Vector6D): LatticePoint;
/**
 * Find nearest quasicrystal vertex to a point
 */
export declare function nearestQCVertex(point: Point2D, lattice: LatticePoint[]): {
    nearest: LatticePoint;
    distance: number;
};
/**
 * Calculate quasicrystal potential energy
 * Used for multi-well potential in SCBE Layer 8
 */
export declare function quasicrystalPotential(position: Point2D, lattice: LatticePoint[], sigma?: number): number;
/**
 * Quasicrystal-based hash function
 * Maps input bytes to quasicrystal lattice positions
 */
export declare function quasicrystalHash(input: Uint8Array, lattice: LatticePoint[]): {
    hash: Point2D;
    path: LatticePoint[];
};
/**
 * Quasicrystal Lattice Provider
 */
export declare class QCLatticeProvider {
    private lattice;
    private config;
    constructor(config?: QCLatticeConfig);
    /**
     * Generate the quasicrystal lattice
     */
    private generateLattice;
    /**
     * Get all lattice points
     */
    getPoints(): LatticePoint[];
    /**
     * Map SCBE 6D vector to quasicrystal position
     */
    mapVector(v: Vector6D): LatticePoint;
    /**
     * Find nearest vertex
     */
    findNearest(point: Point2D): {
        nearest: LatticePoint;
        distance: number;
    };
    /**
     * Calculate potential at position
     */
    potential(position: Point2D, sigma?: number): number;
    /**
     * Compute diffraction pattern
     */
    diffraction(kRange: number): DiffractionPeak[];
    /**
     * Check rotational symmetry
     */
    checkSymmetry(n: number): {
        hasSymmetry: boolean;
        score: number;
    };
    /**
     * Hash input using quasicrystal walk
     */
    hash(input: Uint8Array): {
        hash: Point2D;
        path: LatticePoint[];
    };
}
/**
 * Default QC lattice provider instance
 */
export declare const defaultQCLattice: QCLatticeProvider;
//# sourceMappingURL=qcLattice.d.ts.map