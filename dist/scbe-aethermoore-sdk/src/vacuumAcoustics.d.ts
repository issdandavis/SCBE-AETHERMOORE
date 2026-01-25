/**
 * SCBE Vacuum-Acoustics Kernel (Layer 14)
 *
 * Cymatic and acoustic simulation functions:
 * - Nodal surface calculations
 * - Cymatic resonance checking
 * - Bottle beam intensity (acoustic trapping)
 * - Flux redistribution
 */
import { Vector3D, Vector6D } from './constants.js';
/**
 * Vacuum-Acoustics configuration
 */
export interface VacuumAcousticsConfig {
    /** Box size */
    L?: number;
    /** Speed of sound */
    c?: number;
    /** Damping coefficient */
    gamma: number;
    /** Base ratio */
    R?: number;
    /** Grid resolution */
    resolution?: number;
}
/**
 * Acoustic source definition
 */
export interface AcousticSource {
    /** Position in 3D space */
    pos: Vector3D;
    /** Phase offset in radians */
    phase: number;
}
/**
 * Nodal surface function for cymatic patterns
 *
 * N(x₁, x₂) = cos(nπx₁/L)cos(mπx₂/L) - cos(mπx₁/L)cos(nπx₂/L)
 *
 * Returns zero on nodal lines where standing waves cancel.
 *
 * @param x - 2D position [x₁, x₂]
 * @param n - First mode number
 * @param m - Second mode number
 * @param L - Box size
 * @returns Nodal surface value
 */
export declare function nodalSurface(x: [number, number], n: number, m: number, L?: number): number;
/**
 * Check if a target position lies on a cymatic resonance nodal line
 *
 * Uses agent's 6D vector to derive mode numbers:
 * - n from dimension 4 (scaled by reference velocity)
 * - m from dimension 6
 *
 * @param agentVector - Agent's 6D phase space vector
 * @param targetPosition - Target 2D position to check
 * @param tolerance - How close to zero counts as "on nodal line"
 * @param L - Box size
 * @returns True if target is on a nodal line
 */
export declare function checkCymaticResonance(agentVector: Vector6D, targetPosition: [number, number], tolerance?: number, L?: number): boolean;
/**
 * Calculate bottle beam intensity at a point
 *
 * Superposition of spherical waves from multiple sources creates
 * acoustic trapping regions. Intensity = |E|² where E is the
 * complex field amplitude.
 *
 * @param position - 3D position to evaluate
 * @param sources - Array of acoustic sources
 * @param wavelength - Acoustic wavelength
 * @returns Intensity (dimensionless)
 */
export declare function bottleBeamIntensity(position: Vector3D, sources: AcousticSource[], wavelength: number): number;
/**
 * Flux redistribution for interference cancellation
 *
 * When two waves interfere destructively at center, energy
 * is redistributed to corners (conservation of energy).
 *
 * @param amplitude - Wave amplitude
 * @param phaseOffset - Phase difference between interfering waves
 * @returns Object with canceled energy and corner distribution
 */
export declare function fluxRedistribution(amplitude: number, phaseOffset: number): {
    canceled: number;
    corners: [number, number, number, number];
};
/**
 * Calculate standing wave amplitude at a point
 *
 * A(x, t) = 2A₀ sin(kx) cos(ωt)
 *
 * @param x - Position
 * @param t - Time
 * @param A0 - Initial amplitude
 * @param k - Wave number (2π/λ)
 * @param omega - Angular frequency (2πf)
 * @returns Amplitude at (x, t)
 */
export declare function standingWaveAmplitude(x: number, t: number, A0: number, k: number, omega: number): number;
/**
 * Find resonant frequencies for a box cavity
 *
 * f_{n,m,l} = (c/2) √((n/Lx)² + (m/Ly)² + (l/Lz)²)
 *
 * @param n - Mode number in x
 * @param m - Mode number in y
 * @param l - Mode number in z
 * @param dimensions - Box dimensions [Lx, Ly, Lz]
 * @param c - Speed of sound
 * @returns Resonant frequency
 */
export declare function cavityResonance(n: number, m: number, l: number, dimensions: Vector3D, c?: number): number;
//# sourceMappingURL=vacuumAcoustics.d.ts.map