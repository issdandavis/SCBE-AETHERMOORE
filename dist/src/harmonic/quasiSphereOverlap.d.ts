/**
 * @file quasiSphereOverlap.ts
 * @module harmonic/quasiSphereOverlap
 * @layer Layer 5, Layer 10, Layer 11, Layer 13
 * @component Quasi-Sphere Squad Overlap & Pad Geodesic Constraints
 * @version 3.2.4
 *
 * Formalizes the 6D quasi-sphere as an operational geometric object:
 *
 * 1. Squad Overlaps: Two quasi-spheres may share context when their
 *    trust-bounded hyperbolic shells intersect AND coherence is above
 *    threshold. Intersection requires geometric agreement, not central control.
 *
 * 2. Pad Geodesic Constraints: Each PadMode is allowed only certain curvature
 *    bands within the quasi-sphere. Engineering pads can reach deep (low d*)
 *    but must stay on-axis; Science pads can explore high curvature but
 *    are bounded in execution capability.
 *
 * 3. Consensus-Gradient Paths: Squad motion direction is the vector resultant
 *    of individual unit gradients. Byzantine agreement amplifies; disagreement
 *    shrinks magnitude → near-zero velocity.
 */
import type { Vector6D } from './constants.js';
import type { PadMode, Lang } from './scbe_voxel_types.js';
import { type CHSFNState, type TongueImpedance } from './chsfn.js';
/**
 * A 6D quasi-sphere: trust-bounded hyperbolic shell centered on a unit.
 *
 * Not a hard boundary — the "edge" is asymptotic.
 * Cost grows as π^(φ·d*) from the center.
 */
export interface QuasiSphere {
    /** Center position in Poincaré ball */
    center: Vector6D;
    /** Phase alignment per tongue */
    phase: Vector6D;
    /** Trust radius: the effective reach before cost explodes */
    trustRadius: number;
    /** Coherence of this sphere's owner */
    coherence: number;
    /** Owner unit identifier */
    unitId: string;
}
/**
 * Create a quasi-sphere from a CHSFN state.
 *
 * Trust radius is derived from coherence: higher coherence → wider reach.
 * trustRadius = -ln(1 - coherence) (maps [0, 1) → [0, ∞))
 */
export declare function createQuasiSphere(unitId: string, state: CHSFNState, coherence: number): QuasiSphere;
/**
 * Result of computing overlap between two quasi-spheres.
 */
export interface OverlapResult {
    /** Whether the spheres geometrically overlap */
    overlaps: boolean;
    /** Hyperbolic distance between centers */
    distance: number;
    /** Combined trust radius */
    combinedRadius: number;
    /** Phase coherence between the two spheres (0-1) */
    phaseCoherence: number;
    /** Whether shared context is possible (overlap + coherence) */
    canShareContext: boolean;
    /** Shared access cost at the midpoint */
    midpointCost: number;
}
/**
 * Compute the overlap between two quasi-spheres.
 *
 * Two units may share context when:
 * 1. Their trust radii overlap: d_H(center_a, center_b) < r_a + r_b
 * 2. Phase coherence exceeds threshold: avg phase difference < maxPhaseDiff
 *
 * This is how you get "shared context without shared memory" and
 * "coordination without central control."
 *
 * @param a - First quasi-sphere
 * @param b - Second quasi-sphere
 * @param minPhaseCoherence - Min phase coherence for context sharing (default 0.5)
 * @returns Overlap result
 */
export declare function computeOverlap(a: QuasiSphere, b: QuasiSphere, minPhaseCoherence?: number): OverlapResult;
/**
 * Compute the full overlap matrix for a squad of quasi-spheres.
 *
 * Returns which pairs can share context and the coherence between them.
 *
 * @param spheres - Array of quasi-spheres
 * @param minPhaseCoherence - Min phase coherence threshold
 * @returns Map from "unitA:unitB" → OverlapResult
 */
export declare function squadOverlapMatrix(spheres: QuasiSphere[], minPhaseCoherence?: number): Map<string, OverlapResult>;
/**
 * Compute the squad's shared context zone: the region reachable by all members.
 *
 * @param spheres - Array of quasi-spheres
 * @returns Effective shared radius (0 if no shared zone exists)
 */
export declare function sharedContextRadius(spheres: QuasiSphere[]): number;
/**
 * Geodesic constraint for a PadMode within the quasi-sphere.
 *
 * Each pad is allowed only certain curvature bands:
 * - maxReachDistance: how deep into the quasi-sphere the pad can operate
 * - allowedCurvatureBand: [min, max] curvature range (controls which
 *   "types" of voxels this pad can access)
 * - tongueWeights: which tongues this pad's geodesics favor
 */
export interface GeodesicConstraint {
    /** Pad mode this constraint applies to */
    mode: PadMode;
    /** Max hyperbolic distance this pad can reach from unit center */
    maxReachDistance: number;
    /** Allowed curvature band [min, max] — lower = flatter, higher = steeper */
    allowedCurvatureBand: [number, number];
    /** Tongue impedance weights for this pad's geodesics */
    tongueWeights: TongueImpedance;
    /** Primary tongue for this pad */
    primaryTongue: Lang;
}
/**
 * Default geodesic constraints per PadMode.
 *
 * Design rationale:
 * - ENGINEERING: deep reach (low d*), on-axis (tight curvature), CA-dominant
 * - NAVIGATION: wide reach, moderate curvature, AV-dominant (contextual)
 * - SYSTEMS: moderate reach, tight curvature, DR-dominant (structural)
 * - SCIENCE: shallow reach, wide curvature (exploratory), UM-dominant
 * - COMMS: moderate reach, moderate curvature, KO-dominant (flow)
 * - MISSION: deepest reach, widest curvature, RU-dominant (binding)
 */
export declare const PAD_GEODESIC_CONSTRAINTS: Record<PadMode, GeodesicConstraint>;
/**
 * Compute local curvature at a position in the Poincaré ball.
 *
 * In hyperbolic space, curvature increases toward the boundary:
 * κ(p) = 2 / (1 - ‖p‖²)²
 *
 * @param position - 6D position
 * @returns Local curvature value
 */
export declare function localCurvature(position: Vector6D): number;
/**
 * Check if a state is within a pad's geodesic constraints.
 *
 * A pad can access a position only if:
 * 1. Hyperbolic distance from center < maxReachDistance
 * 2. Local curvature is within allowedCurvatureBand
 * 3. Primary tongue impedance is below threshold
 *
 * @param state - Current CHSFN state
 * @param center - Unit's center position
 * @param constraint - Geodesic constraint for this pad
 * @param maxImpedance - Max impedance for primary tongue (default 0.4)
 * @returns Whether the position is geodesically accessible to this pad
 */
export declare function isWithinGeodesicConstraint(state: CHSFNState, center: Vector6D, constraint: GeodesicConstraint, maxImpedance?: number): boolean;
/**
 * Compute the effective geodesic reach for each pad of a unit.
 *
 * Returns the fraction of sampled points within the unit's quasi-sphere
 * that each pad can access, given its geodesic constraints.
 *
 * @param center - Unit center position
 * @param coherence - Unit coherence
 * @param sampleCount - Number of random probe points (default 100)
 * @returns Map from PadMode → accessibility fraction [0, 1]
 */
export declare function padAccessibilityMap(center: Vector6D, coherence: number, sampleCount?: number): Map<PadMode, number>;
/**
 * Compute the consensus gradient direction for a squad.
 *
 * Each unit contributes its own gradient (drift direction).
 * The resultant vector is the only allowed squad motion direction.
 *
 * If gradients disagree → magnitude shrinks (near-zero velocity).
 * If ≥4/6 agree → strong, coherent motion.
 *
 * This is Byzantine fault tolerance expressed as continuous geometry.
 *
 * @param gradients - Array of 6D gradient vectors (one per unit)
 * @returns Consensus gradient (magnitude reflects agreement)
 */
export declare function consensusGradient(gradients: Vector6D[]): Vector6D;
/**
 * Compute agreement strength from a set of gradient vectors.
 *
 * @returns Value in [0, 1] where 1 = perfect agreement
 */
export declare function gradientAgreement(gradients: Vector6D[]): number;
//# sourceMappingURL=quasiSphereOverlap.d.ts.map