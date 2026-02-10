/**
 * @file unified-state.ts
 * @module ai_brain/unified-state
 * @layer Layer 1-14 (Unified Manifold)
 * @component Unified Brain State
 * @version 1.1.0
 * @since 2026-02-07
 *
 * Implements the 21D unified brain state vector that integrates all SCBE-AETHERMOORE
 * components into a single coherent manifold. Each component contributes specific
 * dimensions, and the golden ratio weighting creates a hierarchical importance structure.
 *
 * The 21D vector is:
 *   [scbe(6) | navigation(6) | cognitive(3) | semantic(3) | swarm(3)]
 *
 * After golden ratio weighting, the vector is embedded into a Poincare ball
 * for hyperbolic geometry operations.
 */
import { type BrainStateComponents, type SCBEContext, type NavigationVector, type CognitivePosition, type SemanticPhase, type SwarmCoordination, type TrajectoryPoint } from './types.js';
/**
 * Compute the corrected golden ratio product for validation
 * Product of phi^0 * phi^1 * ... * phi^20 = phi^(0+1+...+20) = phi^210
 */
export declare function goldenWeightProduct(): number;
/**
 * Apply golden ratio weighting to a 21D vector.
 * Creates hierarchical importance: higher dimensions receive
 * exponentially more weight (swarm > semantic > cognitive > navigation > SCBE).
 *
 * @param vector - Raw 21D brain state vector
 * @returns Weighted 21D vector
 */
export declare function applyGoldenWeighting(vector: number[]): number[];
/**
 * Embed a vector into the Poincare ball with numerically stable boundary clamping.
 *
 * Uses the exponential map from the origin: exp_0(v) = tanh(||v|| / 2) * v / ||v||.
 * This naturally maps R^n -> B^n (open unit ball) while preserving direction.
 *
 * The function is designed for raw state vectors (components typically in [0, 1]).
 * For golden-ratio-weighted vectors, use applyGoldenWeighting separately for
 * importance scoring — do not embed the weighted vector directly, as the
 * exponential weights would saturate all points at the boundary.
 *
 * This fixes the Theorem 3 boundary failure identified in the security review.
 *
 * @param vector - Input vector (any dimension)
 * @param epsilon - Boundary epsilon (default: 1e-8)
 * @returns Point strictly inside the Poincare ball
 */
export declare function safePoincareEmbed(vector: number[], epsilon?: number): number[];
/**
 * Compute hyperbolic distance in the Poincare ball model.
 *
 * d_H(u,v) = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))
 *
 * @param u - First point in Poincare ball (||u|| < 1)
 * @param v - Second point in Poincare ball (||v|| < 1)
 * @returns Hyperbolic distance
 */
export declare function hyperbolicDistanceSafe(u: number[], v: number[]): number;
/**
 * Mobius addition in the Poincare ball.
 *
 * u + v = ((1 + 2<u,v> + ||v||^2)u + (1 - ||u||^2)v) / (1 + 2<u,v> + ||u||^2||v||^2)
 *
 * @param u - First point
 * @param v - Second point
 * @returns Mobius sum
 */
export declare function mobiusAddSafe(u: number[], v: number[]): number[];
/**
 * UnifiedBrainState - The 21D manifold integrating all SCBE-AETHERMOORE components.
 *
 * This class maintains a coherent state across:
 * - SCBE Core (6D context)
 * - Dual Lattice (6D navigation)
 * - PHDM (3D cognitive)
 * - Sacred Tongues (3D semantic)
 * - Swarm (3D coordination)
 *
 * The state can be represented as a raw 21D vector, a weighted vector,
 * or an embedded Poincare ball point.
 */
export declare class UnifiedBrainState {
    private components;
    constructor(components?: Partial<BrainStateComponents>);
    /**
     * Get the structured components
     */
    getComponents(): Readonly<BrainStateComponents>;
    /**
     * Update SCBE context
     */
    updateSCBEContext(updates: Partial<SCBEContext>): void;
    /**
     * Update navigation vector
     */
    updateNavigation(updates: Partial<NavigationVector>): void;
    /**
     * Update cognitive position
     */
    updateCognitivePosition(updates: Partial<CognitivePosition>): void;
    /**
     * Update semantic phase
     */
    updateSemanticPhase(updates: Partial<SemanticPhase>): void;
    /**
     * Update swarm coordination
     */
    updateSwarmCoordination(updates: Partial<SwarmCoordination>): void;
    /**
     * Flatten to raw 21D vector
     */
    toVector(): number[];
    /**
     * Apply golden ratio weighting to the state vector
     */
    toWeightedVector(): number[];
    /**
     * Embed into Poincare ball (normalized and contained).
     *
     * Uses the raw 21D vector (not golden-weighted) for geometric embedding.
     * Golden ratio weighting is available via toWeightedVector() for importance
     * scoring, but the exponential weights would saturate the Poincare embedding.
     */
    toPoincarePoint(): number[];
    /**
     * Compute hyperbolic distance to another brain state
     */
    distanceTo(other: UnifiedBrainState): number;
    /**
     * Compute distance from the safe origin (center of Poincare ball)
     */
    distanceFromOrigin(): number;
    /**
     * Compute boundary distance (how close to the Poincare ball edge)
     */
    boundaryDistance(): number;
    /**
     * Create a trajectory point from the current state
     */
    toTrajectoryPoint(step: number): TrajectoryPoint;
    /**
     * Reconstruct from a raw 21D vector
     */
    static fromVector(vector: number[]): UnifiedBrainState;
    /**
     * Create a safe origin state (center of manifold)
     */
    static safeOrigin(): UnifiedBrainState;
}
/**
 * Compute Euclidean distance between two 21D state vectors
 */
export declare function euclideanDistance(a: number[], b: number[]): number;
/**
 * Compute the norm of a vector
 */
export declare function vectorNorm(v: number[]): number;
//# sourceMappingURL=unified-state.d.ts.map