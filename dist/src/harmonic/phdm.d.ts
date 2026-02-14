/**
 * Polyhedral Hamiltonian Defense Manifold (PHDM)
 *
 * @file phdm.ts
 * @module harmonic/phdm
 * @layer Layer 8
 * @component PHDM — Polyhedral Hamiltonian Defense Manifold
 * @version 3.3.0
 *
 * Unified security + governance system built on 16 canonical polyhedra:
 *
 * 1. INTRUSION DETECTION — Monitors state deviations from the expected
 *    geodesic curve through 6D polyhedral space via cubic spline interpolation.
 *    Deviation or curvature anomalies trigger intrusion flags.
 *
 * 2. HMAC KEY CHAIN — Traverses the polyhedra in a Hamiltonian path,
 *    generating K_{i+1} = HMAC-SHA256(K_i, Serialize(P_i)) at each step.
 *    Path integrity verified via timingSafeEqual.
 *
 * 3. FLUX GOVERNANCE — Polyhedra are classified by family (Platonic, Archimedean,
 *    Kepler-Poinsot, Toroidal, Johnson, Rhombic). Flux states restrict which
 *    families are active:
 *      POLLY (full) → all 16 polyhedra
 *      QUASI (defensive) → Platonic + Archimedean (8)
 *      DEMI (survival) → Platonic only (5)
 *
 * 4. PHASON SHIFT — Rotates the 6D→3D projection matrix (quasicrystal key
 *    rotation), invalidating cached geodesic positions. Defense mechanism
 *    against persistent adversaries.
 *
 * Merges the security manifold (formerly phdm.ts) and cognitive lattice
 * (formerly python/scbe/brain.py) into a single canonical module.
 *
 * Canonical name: Polyhedral Hamiltonian Defense Manifold
 * (All other expansions — "Dynamic Mesh", "Half-plane Drift Monitor",
 *  "Piecewise Hamiltonian Distance Metric" — are retired.)
 */
/** Polyhedra family classification */
export type PolyhedronFamily = 'platonic' | 'archimedean' | 'kepler-poinsot' | 'toroidal' | 'johnson' | 'rhombic';
/**
 * Polyhedron representation with topological properties
 */
export interface Polyhedron {
    name: string;
    vertices: number;
    edges: number;
    faces: number;
    genus: number;
    family: PolyhedronFamily;
}
/**
 * Flux state — controls which polyhedra families are active.
 * Maps to the POLLY/QUASI/DEMI containment postures.
 */
export type FluxState = 'POLLY' | 'QUASI' | 'DEMI';
/**
 * Compute Euler characteristic: χ = V - E + F = 2(1-g)
 */
export declare function eulerCharacteristic(poly: Polyhedron): number;
/**
 * Verify topological validity: χ = 2(1-g)
 */
export declare function isValidTopology(poly: Polyhedron): boolean;
/**
 * Generate topological hash (SHA256) for tamper detection
 */
export declare function topologicalHash(poly: Polyhedron): string;
/**
 * Serialize polyhedron for HMAC input
 */
export declare function serializePolyhedron(poly: Polyhedron): Buffer;
/**
 * 16 Canonical Polyhedra — classified by family for flux governance.
 *
 * Platonic (5): Core axioms — always available, even in DEMI mode
 * Archimedean (3): Processing layer — available in QUASI and POLLY
 * Kepler-Poinsot (2): High-risk zone — POLLY only
 * Toroidal (2): Recursive/self-diagnostic — POLLY only
 * Johnson (2): Domain connectors — POLLY only
 * Rhombic (2): Space-filling logic — POLLY only
 */
export declare const CANONICAL_POLYHEDRA: Polyhedron[];
/**
 * Hamiltonian Path through polyhedra with HMAC chaining
 */
export declare class PHDMHamiltonianPath {
    private polyhedra;
    private keys;
    constructor(polyhedra?: Polyhedron[]);
    /**
     * Compute Hamiltonian path with sequential HMAC chaining
     * K_{i+1} = HMAC-SHA256(K_i, Serialize(P_i))
     */
    computePath(masterKey: Buffer): Buffer[];
    /**
     * Verify path integrity
     */
    verifyPath(masterKey: Buffer, expectedFinalKey: Buffer): boolean;
    /**
     * Get key at specific step
     */
    getKey(step: number): Buffer | null;
    /**
     * Get polyhedron at specific step
     */
    getPolyhedron(step: number): Polyhedron | null;
}
/**
 * 6D point in Langues space
 */
export interface Point6D {
    x1: number;
    x2: number;
    x3: number;
    x4: number;
    x5: number;
    x6: number;
}
/**
 * Euclidean distance in 6D space
 */
export declare function distance6D(p1: Point6D, p2: Point6D): number;
/**
 * Compute centroid of polyhedron in 6D space
 * Maps topological properties to 6D coordinates
 */
export declare function computeCentroid(poly: Polyhedron): Point6D;
/**
 * Cubic spline interpolation in 6D
 */
export declare class CubicSpline6D {
    private points;
    private t;
    constructor(points: Point6D[]);
    /**
     * Evaluate spline at parameter t ∈ [0, 1]
     */
    evaluate(t: number): Point6D;
    /**
     * Compute tangent at point i using finite differences
     */
    private getTangent;
    /**
     * Compute first derivative γ'(t)
     */
    derivative(t: number, h?: number): Point6D;
    /**
     * Compute second derivative γ''(t)
     */
    secondDerivative(t: number, h?: number): Point6D;
    /**
     * Compute curvature κ(t) = |γ''(t)| / |γ'(t)|²
     */
    curvature(t: number): number;
}
/**
 * Intrusion detection via manifold deviation
 */
export interface IntrusionResult {
    isIntrusion: boolean;
    deviation: number;
    threatVelocity: number;
    curvature: number;
    rhythmPattern: string;
    timestamp: number;
}
export declare class PHDMDeviationDetector {
    private geodesic;
    private snapThreshold;
    private curvatureThreshold;
    private deviationHistory;
    constructor(polyhedra?: Polyhedron[], snapThreshold?: number, curvatureThreshold?: number);
    /**
     * Detect intrusion at time t
     */
    detect(state: Point6D, t: number): IntrusionResult;
    /**
     * Simulate attack scenarios
     */
    simulateAttack(attackType: 'deviation' | 'skip' | 'curvature', intensity?: number): IntrusionResult[];
    /**
     * Generate full rhythm pattern from results
     */
    static getRhythmPattern(results: IntrusionResult[]): string;
}
/**
 * Get the active polyhedra for a given flux state.
 *
 * POLLY: all 16 — full capability
 * QUASI: Platonic + Archimedean (8) — defensive posture
 * DEMI: Platonic only (5) — survival mode
 */
export declare function getActivePolyhedra(fluxState: FluxState, polyhedra?: Polyhedron[]): Polyhedron[];
/**
 * Generate the default 6D→3D icosahedral projection matrix.
 * Based on golden ratio for quasicrystal symmetry.
 */
export declare function generateProjectionMatrix(): number[][];
/**
 * Apply a phason shift: rotate the 6D→3D projection by angle theta
 * in the (dim0, dim1) plane. This changes which 3D slice of the 6D
 * lattice is visible, effectively rotating the quasicrystal tiling.
 *
 * @param matrix - Current 3x6 projection matrix
 * @param theta - Rotation angle (radians)
 * @param dim0 - First dimension of rotation plane (default: 0)
 * @param dim1 - Second dimension of rotation plane (default: 1)
 * @returns New projection matrix
 */
export declare function phasonShift(matrix: number[][], theta: number, dim0?: number, dim1?: number): number[][];
/**
 * Polyhedral Hamiltonian Defense Manifold — unified security + governance.
 *
 * Combines:
 * - HMAC key chain (PHDMHamiltonianPath)
 * - Geodesic deviation intrusion detection (PHDMDeviationDetector)
 * - Flux state governance (POLLY/QUASI/DEMI)
 * - Phason shift defense (6D projection rotation)
 */
export declare class PolyhedralHamiltonianDefenseManifold {
    private path;
    private detector;
    private _fluxState;
    private _projectionMatrix;
    private _allPolyhedra;
    constructor(polyhedra?: Polyhedron[], snapThreshold?: number, curvatureThreshold?: number);
    /**
     * Initialize with master key — computes HMAC key chain
     */
    initialize(masterKey: Buffer): Buffer[];
    /**
     * Monitor state at time t — intrusion detection
     */
    monitor(state: Point6D, t: number): IntrusionResult;
    /**
     * Simulate attack scenarios
     */
    simulateAttack(attackType: 'deviation' | 'skip' | 'curvature', intensity?: number): IntrusionResult[];
    /**
     * Get all 16 canonical polyhedra
     */
    getPolyhedra(): Polyhedron[];
    /**
     * Get the current flux state.
     */
    get fluxState(): FluxState;
    /**
     * Set flux state — restricts which polyhedra families are active.
     * Rebuilds the detector geodesic with only the active polyhedra.
     */
    setFluxState(state: FluxState, snapThreshold?: number, curvatureThreshold?: number): void;
    /**
     * Get polyhedra active under the current flux state.
     */
    getActivePolyhedra(): Polyhedron[];
    /**
     * Get count of active polyhedra.
     */
    get activeCount(): number;
    /**
     * Execute a phason shift — rotates the 6D→3D projection matrix.
     * This is a defense mechanism that invalidates cached positions.
     *
     * @param theta - Rotation angle (radians). Default: random.
     * @param dim0 - First dimension of rotation plane
     * @param dim1 - Second dimension of rotation plane
     */
    executePhasonShift(theta?: number, dim0?: number, dim1?: number): void;
    /**
     * Get the current projection matrix.
     */
    getProjectionMatrix(): number[][];
    /**
     * Project a 6D point to 3D using the current projection matrix.
     */
    projectTo3D(point: Point6D): [number, number, number];
}
//# sourceMappingURL=phdm.d.ts.map