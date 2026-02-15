/**
 * SCBE Harmonic Constants
 * Core mathematical constants for the harmonic scaling system.
 */

export const CONSTANTS = {
  /** Default R value (golden ratio approximation) */
  DEFAULT_R: 1.5,
  /** Fifth root of R for weighted dimensions */
  R_FIFTH: Math.pow(1.5, 0.2),
  /** Default box size for nodal surfaces */
  DEFAULT_L: 1.0,
  /** Default tolerance for resonance checks */
  DEFAULT_TOLERANCE: 1e-6,
} as const;

/** 6D vector type */
export type Vector6D = [number, number, number, number, number, number];

/** 3D vector type */
export type Vector3D = [number, number, number];

/** 2D tensor (matrix) */
export type Tensor2D = number[][];

/** 3D tensor (batch of matrices) */
export type Tensor3D = number[][][];
