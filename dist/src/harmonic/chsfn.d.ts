/**
 * @file chsfn.ts
 * @module harmonic/chsfn
 * @layer Layer 4, Layer 5, Layer 6, Layer 7, Layer 11, Layer 12
 * @component Cymatic-Hyperbolic Semantic Field Network
 * @version 3.2.4
 *
 * CHSFN — a governed geometric computation substrate where:
 *   - Nodes are cymatic nodal voxels (zero-sets of 6D Chladni field)
 *   - Connectivity is implied by shared zero-sets
 *   - Propagation is geodesic drift in negatively curved space
 *   - Memory lives in anti-nodes (negative space)
 *   - Governance is enforced by hyperbolic distance + harmonic scaling
 *
 * State space: S = H^6 × T^6 × R+
 *   H^6 = hyperbolic position (trust/realm geometry)
 *   T^6 = phase torus (one phase per tongue)
 *   R+  = latent mass / entropy budget
 */
import type { Vector6D } from './constants.js';
/**
 * Modal indices for the 6D cymatic field.
 * Each dimension has an (n, m) pair controlling nodal pattern.
 */
export interface CymaticModes {
    /** Mode indices n_i per dimension (cosine term) */
    n: Vector6D;
    /** Mode indices m_j per dimension (sine product) */
    m: Vector6D;
}
/**
 * Default modes — chosen so zero-sets are well-distributed.
 * Higher n/m = finer nodal structure = more addressable loci.
 */
export declare const DEFAULT_MODES: CymaticModes;
/**
 * Compute 6D Chladni-style cymatic field value.
 *
 * Φ(x) = Σ_{i=1}^{6} cos(π·n_i·x_i) · Π_{j≠i} sin(π·m_j·x_j)
 *
 * Properties:
 * - Zero-sets (Φ = 0) are deterministic, reproducible access points
 * - Anti-nodes (|∇Φ| >> 0) are high-energy latent storage basins
 * - Small perturbations destroy access → natural tamper resistance
 * - Orthogonality is preserved across dimensions
 *
 * @param x - 6D position vector (each component in [0, 1])
 * @param modes - Modal indices (default: DEFAULT_MODES)
 * @returns Cymatic field value Φ(x)
 */
export declare function cymaticField(x: Vector6D, modes?: CymaticModes): number;
/**
 * Compute the gradient ∇Φ of the cymatic field at position x.
 *
 * Used for:
 * - Detecting anti-nodes (|∇Φ| >> 0)
 * - Computing drift direction
 * - Phase sensitivity analysis
 *
 * @param x - 6D position vector
 * @param modes - Modal indices
 * @returns Gradient vector [∂Φ/∂x_0, ..., ∂Φ/∂x_5]
 */
export declare function cymaticGradient(x: Vector6D, modes?: CymaticModes): Vector6D;
/**
 * Check if a position is near a cymatic zero-set (nodal surface).
 *
 * @param x - 6D position
 * @param tolerance - Threshold for |Φ(x)| ≈ 0 (default 0.01)
 * @param modes - Modal indices
 * @returns true if position is on or near a nodal surface
 */
export declare function isNearZeroSet(x: Vector6D, tolerance?: number, modes?: CymaticModes): boolean;
/**
 * Compute anti-node strength (gradient magnitude).
 *
 * High values → latent mass basins suitable for concealed storage.
 * Low values → near nodal surfaces (addressable access points).
 *
 * @param x - 6D position
 * @param modes - Modal indices
 * @returns |∇Φ(x)|
 */
export declare function antiNodeStrength(x: Vector6D, modes?: CymaticModes): number;
/**
 * CHSFN state: position + phase + latent mass.
 *
 * σ = (p, θ, μ) where:
 *   p ∈ H^6 (hyperbolic position)
 *   θ ∈ T^6 (phase torus, one per tongue)
 *   μ ∈ R+  (latent mass / entropy budget)
 */
export interface CHSFNState {
    /** Position in 6D hyperbolic space (‖p‖ < 1 in Poincaré ball) */
    position: Vector6D;
    /** Phase per Sacred Tongue [KO, AV, RU, CA, UM, DR] */
    phase: Vector6D;
    /** Latent mass / entropy budget (> 0) */
    mass: number;
}
/**
 * Tongue impedance weights for metric modulation.
 * Each tongue alters the local curvature of the quasi-sphere.
 */
export interface TongueImpedance {
    /** KO: flow orientation / nonce — flattens or steepens drift */
    KO: number;
    /** AV: boundary condition — anchors context */
    AV: number;
    /** RU: constraint field — binding curvature (commitment cost) */
    RU: number;
    /** CA: active operator — enables computation at nodes */
    CA: number;
    /** DR: structural tensor — preserves topological integrity */
    DR: number;
    /** UM: entropic sink — increases decay / redaction */
    UM: number;
}
/** Default impedance — neutral (unity weights) */
export declare const DEFAULT_IMPEDANCE: Readonly<TongueImpedance>;
/**
 * Compute the norm of a position within the Poincaré ball.
 *
 * @param p - 6D position
 * @returns ‖p‖ (Euclidean norm, always < 1 in valid state)
 */
export declare function poincareNorm(p: Vector6D): number;
/**
 * Project a point into the Poincaré ball (clamp ‖p‖ < 1 - ε).
 *
 * @param p - 6D position (may be outside ball)
 * @param maxNorm - Maximum allowed norm (default 0.999)
 * @returns Projected position inside the ball
 */
export declare function projectIntoBall(p: Vector6D, maxNorm?: number): Vector6D;
/**
 * Hyperbolic distance in the 6D Poincaré ball.
 *
 * d_H(u, v) = arcosh(1 + 2‖u-v‖² / ((1-‖u‖²)(1-‖v‖²)))
 *
 * @param u - First point (‖u‖ < 1)
 * @param v - Second point (‖v‖ < 1)
 * @returns Hyperbolic distance d_H
 */
export declare function hyperbolicDistance6D(u: Vector6D, v: Vector6D): number;
/**
 * Compute tongue impedance at a position.
 *
 * impedance_tongue(θ, p) = |θ_tongue - expected_phase(p)| / π
 *
 * Returns a value in [0, 1]. Below threshold ε → node is decodable.
 * Above ε → node is semantically inaccessible.
 *
 * @param state - CHSFN state
 * @param tongueIndex - Which tongue (0=KO, 1=AV, 2=RU, 3=CA, 4=DR, 5=UM)
 * @param impedance - Tongue impedance weights
 * @returns Impedance in [0, 1]
 */
export declare function tongueImpedanceAt(state: CHSFNState, tongueIndex: number, impedance?: TongueImpedance): number;
/**
 * Check if a node is semantically accessible (decodable).
 *
 * A node is accessible only when:
 * 1. The correct tongue is applied (impedance < threshold)
 * 2. Hyperbolic distance from origin is below threshold
 * 3. Cymatic phase is coherent (field value near zero-set)
 *
 * @param state - Current CHSFN state
 * @param tongueIndex - Tongue to apply
 * @param maxImpedance - Max allowed impedance (default 0.3)
 * @param maxDistance - Max hyperbolic distance from origin (default 3.0)
 * @param cymaticTolerance - Tolerance for zero-set check (default 0.1)
 * @param modes - Cymatic modes
 * @returns true if node is accessible
 */
export declare function isAccessible(state: CHSFNState, tongueIndex: number, maxImpedance?: number, maxDistance?: number, cymaticTolerance?: number, modes?: CymaticModes): boolean;
/**
 * Energy functional E(p, θ, μ) for drift computation.
 *
 * Combines:
 * - Hyperbolic distance from origin (trust cost)
 * - Phase misalignment (tongue impedance)
 * - Cymatic field intensity (nodal accessibility)
 * - Latent mass contribution
 *
 * @param state - Current CHSFN state
 * @param impedance - Tongue weights
 * @param modes - Cymatic modes
 * @returns Energy value E
 */
export declare function energyFunctional(state: CHSFNState, impedance?: TongueImpedance, modes?: CymaticModes): number;
/**
 * Compute energy gradient ∇_H E for adiabatic drift.
 *
 * dp/dτ = -∇_H E(p, θ, μ)
 *
 * This is not signal passing — it is geodesic drift.
 * States evolve by flowing down the energy landscape.
 *
 * @param state - Current CHSFN state
 * @param impedance - Tongue weights
 * @param modes - Cymatic modes
 * @returns Gradient of E with respect to position
 */
export declare function energyGradient(state: CHSFNState, impedance?: TongueImpedance, modes?: CymaticModes): Vector6D;
/**
 * Perform one step of adiabatic drift.
 *
 * dp/dτ = -∇_H E(p, θ, μ)
 *
 * The state drifts toward lower energy (safer, more coherent regions).
 * Drift intersecting cymatic zero-sets reveals stored semantics.
 *
 * @param state - Current state
 * @param stepSize - Integration step size (default 0.01)
 * @param impedance - Tongue weights
 * @param modes - Cymatic modes
 * @returns New state after one drift step
 */
export declare function driftStep(state: CHSFNState, stepSize?: number, impedance?: TongueImpedance, modes?: CymaticModes): CHSFNState;
/**
 * Compute triadic temporal distance.
 *
 * d_tri(t) = (λ₁·d₁^φ + λ₂·d₂^φ + λ₃·d_G^φ)^(1/φ)
 *
 * Three independent distances (past, present, governance) are
 * aggregated with golden-ratio exponents. This ensures:
 * - No linear temporal collapse
 * - Governance time is irreducible
 * - Temporal attacks explode geometrically
 *
 * @param d1 - Past distance
 * @param d2 - Present distance
 * @param dG - Governance distance
 * @param lambda1 - Weight for past (default 0.3)
 * @param lambda2 - Weight for present (default 0.5)
 * @param lambda3 - Weight for governance (default 0.2)
 * @returns Aggregated triadic distance
 */
export declare function triadicTemporalDistance(d1: number, d2: number, dG: number, lambda1?: number, lambda2?: number, lambda3?: number): number;
/**
 * Hyperbolic volume growth in 6D: V(r) ~ e^{5r}
 *
 * @param radius - Hyperbolic radius
 * @returns Approximate volume proportional to e^{5r}
 */
export declare function quasiSphereVolume(radius: number): number;
/**
 * Effective storage capacity of the quasi-sphere.
 *
 * C ~ e^{5r} × tongueEntropy × temporalLayers
 *
 * Negative space doubles effective capacity because anti-nodes
 * encode latent superpositions, and dormant voxels cost nothing.
 *
 * @param radius - Hyperbolic radius
 * @param tongueEntropy - Entropy per tongue (default 8 bits)
 * @param temporalLayers - Number of temporal layers (default 3)
 * @returns Effective capacity (arbitrary units)
 */
export declare function effectiveCapacity(radius: number, tongueEntropy?: number, temporalLayers?: number): number;
/**
 * Access cost at a given hyperbolic distance.
 *
 * H(d*, R) = R · π^(φ·d*)
 *
 * This is the Layer-12 event horizon. Unauthorized semantic access
 * requires global phase coherence across tongues and traversal of
 * exponentially expensive hyperbolic distances.
 *
 * @param dStar - Hyperbolic realm distance
 * @param R - Base cost ratio (default 1.5)
 * @returns Access cost
 */
export declare function accessCost(dStar: number, R?: number): number;
//# sourceMappingURL=chsfn.d.ts.map