/**
 * @file dual-lattice.ts
 * @module ai_brain/dual-lattice
 * @layer Layer 4, Layer 5, Layer 9, Layer 12
 * @component Dual Lattice Architecture
 * @version 1.0.0
 * @since 2026-02-08
 *
 * Implements the Dual Lattice Architecture for quasicrystal-based AI security.
 *
 * Both projection modes operate simultaneously:
 *
 *   Static Lattice (6D → 3D): Structure Generation
 *     Creates the aperiodic polyhedral mesh
 *     Defines valid Hamiltonian paths
 *     Establishes the topology that adversaries cannot predict
 *
 *   Dynamic Lattice (3D → 6D → 3D): Runtime Transform
 *     Lifts thought vectors through the 6D space
 *     Applies phason shifts for security response
 *     Projects back with transformed aperiodic structure
 *
 * Key insight: Multiples of 2 and 1 → 3 create interference patterns
 * at 3x frequencies — natural for icosahedral/φ-based symmetry.
 *
 * The dual lattice harmonics produce mutual verification:
 * the static topology constrains the dynamic transform, and the
 * dynamic transform validates the static topology.
 */
/**
 * A point in the 6D hyperspace lattice.
 * Components map to the icosahedral symmetry basis.
 */
export interface Lattice6D {
    readonly components: readonly [number, number, number, number, number, number];
}
/**
 * A point in the 3D projected space.
 * Result of cut-and-project from 6D.
 */
export interface Lattice3D {
    readonly x: number;
    readonly y: number;
    readonly z: number;
}
/**
 * A phason shift vector in 6D perpendicular space.
 * Phasons are collective excitations that rearrange
 * the aperiodic tiling without changing its statistics.
 */
export interface PhasonShift {
    /** Shift components in the 3D perpendicular subspace */
    readonly perpShift: readonly [number, number, number];
    /** Shift magnitude (amplitude of phason excitation) */
    readonly magnitude: number;
    /** Phase angle (direction in perpendicular space) */
    readonly phase: number;
}
/**
 * Result from the static lattice projection (6D → 3D).
 */
export interface StaticProjectionResult {
    /** Projected 3D point */
    point3D: Lattice3D;
    /** Perpendicular (internal) space component */
    perpComponent: readonly [number, number, number];
    /** Acceptance flag (point falls within acceptance domain) */
    accepted: boolean;
    /** Distance to acceptance boundary */
    boundaryDistance: number;
    /** Which Penrose tile type this point maps to (thick/thin rhombus analog) */
    tileType: 'thick' | 'thin';
}
/**
 * Result from the dynamic lattice transform (3D → 6D → 3D).
 */
export interface DynamicTransformResult {
    /** Lifted 6D point */
    lifted6D: Lattice6D;
    /** Phason-shifted 6D point */
    shifted6D: Lattice6D;
    /** Re-projected 3D point */
    projected3D: Lattice3D;
    /** Displacement from original position (security metric) */
    displacement: number;
    /** Interference pattern value at this point */
    interferenceValue: number;
    /** Whether the transform preserved aperiodic structure */
    structurePreserved: boolean;
}
/**
 * Combined result from both lattice modes operating together.
 */
export interface DualLatticeResult {
    /** Static lattice result */
    static: StaticProjectionResult;
    /** Dynamic lattice result */
    dynamic: DynamicTransformResult;
    /** Cross-verification score [0, 1] (how well both lattices agree) */
    coherence: number;
    /** 3x frequency interference pattern */
    tripleFrequencyInterference: number;
    /** Whether the dual lattice validates this point */
    validated: boolean;
}
/**
 * Dual Lattice configuration
 */
export interface DualLatticeConfig {
    /** Acceptance domain radius (Penrose window size) */
    acceptanceRadius: number;
    /** Phason coupling strength (how strongly shifts affect topology) */
    phasonCoupling: number;
    /** Interference detection threshold */
    interferenceThreshold: number;
    /** Maximum phason amplitude before structure breaks */
    maxPhasonAmplitude: number;
    /** Coherence threshold for dual validation */
    coherenceThreshold: number;
}
export declare const DEFAULT_DUAL_LATTICE_CONFIG: DualLatticeConfig;
/**
 * Project from 6D to 3D using the cut-and-project method.
 *
 * The "acceptance domain" in perpendicular space determines which
 * 6D lattice points produce valid 3D quasicrystal vertices.
 * Points outside the acceptance domain are rejected.
 */
export declare function staticProjection(point6D: Lattice6D, config?: DualLatticeConfig): StaticProjectionResult;
/**
 * Generate an aperiodic mesh of valid Hamiltonian path vertices.
 *
 * Scans integer lattice points in 6D and projects only those
 * within the acceptance domain, creating a quasicrystalline mesh.
 *
 * @param radius - Search radius in 6D (default: 3)
 * @param config - Lattice configuration
 * @returns Array of accepted 3D vertices with metadata
 */
export declare function generateAperiodicMesh(radius?: number, config?: DualLatticeConfig): StaticProjectionResult[];
/**
 * Apply a phason shift to a 6D lattice point.
 *
 * Phasons shift points in perpendicular space, causing some
 * to enter or leave the acceptance domain. This changes the
 * local tiling without affecting statistical properties.
 *
 * Security application: phason shifts can dynamically rearrange
 * the quasicrystal structure in response to threats, making
 * the topology a moving target.
 */
export declare function applyPhasonShift(point6D: Lattice6D, phason: PhasonShift): Lattice6D;
/**
 * Execute the full dynamic lattice transform: 3D → 6D → 3D.
 *
 * 1. Lift the 3D thought vector to 6D using pseudoinverse
 * 2. Apply phason shift in 6D perpendicular space
 * 3. Project back to 3D with the transformed structure
 *
 * The displacement between original and re-projected points
 * is a security metric: large displacement = suspicious behavior.
 */
export declare function dynamicTransform(point3D: Lattice3D, phason: PhasonShift, config?: DualLatticeConfig): DynamicTransformResult;
/**
 * Dual Lattice System — both projection modes operating simultaneously.
 *
 * The static lattice provides the structure; the dynamic lattice
 * transforms within that structure. Cross-verification between
 * the two ensures mathematical consistency.
 */
export declare class DualLatticeSystem {
    private readonly config;
    private staticMesh;
    private stepCounter;
    constructor(config?: Partial<DualLatticeConfig>);
    /**
     * Initialize the static mesh (one-time topology generation).
     * Call this once; the mesh defines the Hamiltonian path topology.
     */
    initializeMesh(radius?: number): StaticProjectionResult[];
    /**
     * Get the cached static mesh.
     */
    getMesh(): StaticProjectionResult[] | null;
    /**
     * Process a 21D brain state through the dual lattice system.
     *
     * Both lattice modes run simultaneously:
     * 1. Static: Take 6D subspace, project to 3D, check acceptance
     * 2. Dynamic: Take projected 3D, lift → shift → reproject
     * 3. Cross-verify both results for coherence
     *
     * @param state21D - 21D brain state vector
     * @param phason - Phason shift for dynamic response
     * @returns Combined dual lattice result
     */
    process(state21D: number[], phason: PhasonShift): DualLatticeResult;
    /**
     * Create a security-responsive phason shift based on threat level.
     *
     * Higher threat → larger phason amplitude → more topology rearrangement.
     * This makes the quasicrystal structure a moving target that adapts
     * to the current threat landscape.
     */
    createThreatPhason(threatLevel: number, anomalyDimensions?: number[]): PhasonShift;
    /**
     * Compute cross-verification coherence between static and dynamic results.
     *
     * Checks that the dynamic transform preserves the static topology's
     * essential properties (acceptance, tiling, boundary relationships).
     */
    private computeCoherence;
    /** Get the current step counter */
    getStep(): number;
    /** Reset the system state (keeps mesh) */
    reset(): void;
    /** Full reset including mesh */
    fullReset(): void;
}
/**
 * Compute the Hausdorff (fractal) dimension estimate for a set of
 * projected lattice points using box-counting.
 *
 * For a perfect quasicrystal, D ≈ 2 (fills 2D plane).
 * Phason disorder can push D to non-integer values.
 */
export declare function estimateFractalDimension(points: Lattice3D[], scales?: number[]): number;
/**
 * Compute the lattice norm (L2) of a 6D vector.
 */
export declare function latticeNorm6D(point: Lattice6D): number;
/**
 * Compute the lattice distance between two 3D points.
 */
export declare function latticeDistance3D(a: Lattice3D, b: Lattice3D): number;
//# sourceMappingURL=dual-lattice.d.ts.map