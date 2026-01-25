/**
 * SCBE Vacuum-Acoustics Kernel (Layer 14)
 *
 * Cymatic and acoustic simulation functions:
 * - Nodal surface calculations
 * - Cymatic resonance checking
 * - Bottle beam intensity (acoustic trapping)
 * - Flux redistribution
 */

import { CONSTANTS, Vector3D, Vector6D } from './constants.js';

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
export function nodalSurface(
  x: [number, number],
  n: number,
  m: number,
  L: number = CONSTANTS.DEFAULT_L,
): number {
  const [x1, x2] = x;
  const a = Math.cos((n * Math.PI * x1) / L) * Math.cos((m * Math.PI * x2) / L);
  const b = Math.cos((m * Math.PI * x1) / L) * Math.cos((n * Math.PI * x2) / L);
  return a - b;
}

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
export function checkCymaticResonance(
  agentVector: Vector6D,
  targetPosition: [number, number],
  tolerance: number = CONSTANTS.DEFAULT_TOLERANCE,
  L: number = CONSTANTS.DEFAULT_L,
): boolean {
  const v_ref = 1;
  const n = Math.abs(agentVector[3]) / v_ref;
  const m = agentVector[5];
  const N = nodalSurface(targetPosition, n, m, L);
  return Math.abs(N) < tolerance;
}

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
export function bottleBeamIntensity(
  position: Vector3D,
  sources: AcousticSource[],
  wavelength: number,
): number {
  const k = (2 * Math.PI) / wavelength;
  let re = 0, im = 0;

  for (const s of sources) {
    const dx = position[0] - s.pos[0];
    const dy = position[1] - s.pos[1];
    const dz = position[2] - s.pos[2];
    const r = Math.sqrt(dx * dx + dy * dy + dz * dz) + 1e-12;
    const theta = k * r + s.phase;
    re += Math.cos(theta);
    im += Math.sin(theta);
  }

  return re * re + im * im;
}

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
export function fluxRedistribution(
  amplitude: number,
  phaseOffset: number,
): { canceled: number; corners: [number, number, number, number] } {
  const E_total = 2 * amplitude * amplitude;
  const central = 4 * amplitude * amplitude * Math.cos(phaseOffset / 2) ** 2;
  const canceled = Math.max(0, E_total - central);
  const each = canceled / 4;
  return { canceled, corners: [each, each, each, each] };
}

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
export function standingWaveAmplitude(
  x: number,
  t: number,
  A0: number,
  k: number,
  omega: number,
): number {
  return 2 * A0 * Math.sin(k * x) * Math.cos(omega * t);
}

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
export function cavityResonance(
  n: number,
  m: number,
  l: number,
  dimensions: Vector3D,
  c: number = 343,
): number {
  const [Lx, Ly, Lz] = dimensions;
  const term = (n / Lx) ** 2 + (m / Ly) ** 2 + (l / Lz) ** 2;
  return (c / 2) * Math.sqrt(term);
}
