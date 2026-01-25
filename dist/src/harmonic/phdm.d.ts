/**
 * Polyhedral Hamiltonian Defense Manifold (PHDM)
 *
 * Topological intrusion detection using graph theory and differential geometry.
 * Traverses 16 canonical polyhedra in a Hamiltonian path, generating cryptographic
 * keys while monitoring for deviations from the expected geodesic curve in 6D space.
 *
 * @module harmonic/phdm
 */
/// <reference types="node" />
/// <reference types="node" />
/**
 * Polyhedron representation with topological properties
 */
export interface Polyhedron {
    name: string;
    vertices: number;
    edges: number;
    faces: number;
    genus: number;
}
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
 * 16 Canonical Polyhedra
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
 * Complete PHDM system
 */
export declare class PolyhedralHamiltonianDefenseManifold {
    private path;
    private detector;
    constructor(polyhedra?: Polyhedron[], snapThreshold?: number, curvatureThreshold?: number);
    /**
     * Initialize with master key
     */
    initialize(masterKey: Buffer): Buffer[];
    /**
     * Monitor state at time t
     */
    monitor(state: Point6D, t: number): IntrusionResult;
    /**
     * Simulate attack
     */
    simulateAttack(attackType: 'deviation' | 'skip' | 'curvature', intensity?: number): IntrusionResult[];
    /**
     * Get polyhedra
     */
    getPolyhedra(): Polyhedron[];
}
//# sourceMappingURL=phdm.d.ts.map