/**
 * SCBE Harmonic Constants
 * Core mathematical constants for the harmonic scaling system.
 */
export declare const CONSTANTS: {
    /** Default R value (golden ratio approximation) */
    readonly DEFAULT_R: 1.5;
    /** Fifth root of R for weighted dimensions */
    readonly R_FIFTH: number;
    /** Default box size for nodal surfaces */
    readonly DEFAULT_L: 1;
    /** Default tolerance for resonance checks */
    readonly DEFAULT_TOLERANCE: 0.000001;
};
/** 6D vector type */
export type Vector6D = [number, number, number, number, number, number];
/** 3D vector type */
export type Vector3D = [number, number, number];
/** 2D tensor (matrix) */
export type Tensor2D = number[][];
/** 3D tensor (batch of matrices) */
export type Tensor3D = number[][][];
//# sourceMappingURL=constants.d.ts.map