/**
 * @file securityInvariants.ts
 * @module harmonic/securityInvariants
 * @layer Layer 5, Layer 12, Layer 13
 * @component Formal Security Invariants
 * @version 3.2.4
 *
 * Formal security invariants for the CHSFN quasi-sphere.
 *
 * Central claim:
 *   Unauthorized semantic access requires global phase coherence across
 *   multiple tongues AND traversal of a hyperbolic distance whose cost
 *   scales as π^(φ·d*). This is an energy barrier, not a rule.
 *
 * This module provides:
 * 1. Exponential access cost proof (testable invariant)
 * 2. Phase mismatch blocking proof
 * 3. Nodal stability under perturbation
 * 4. Combined security bound
 * 5. Tongue bijection invariant under drift
 */
import type { Vector6D } from './constants.js';
import { type CHSFNState, type CymaticModes } from './chsfn.js';
/**
 * Security Invariant 1: Exponential Access Cost.
 *
 * For any two hyperbolic distances d1 < d2:
 *   accessCost(d2) / accessCost(d1) >= π^(φ·(d2-d1))
 *
 * This proves that moving further from the trust origin costs
 * super-exponentially more. No polynomial-time attacker can
 * brute-force access to distant voxels.
 *
 * @param d1 - Inner distance
 * @param d2 - Outer distance (must be > d1)
 * @param R - Base cost ratio
 * @returns Object with the ratio and whether invariant holds
 */
export declare function verifyExponentialCostInvariant(d1: number, d2: number, R?: number): {
    holds: boolean;
    actualRatio: number;
    minExpectedRatio: number;
};
/**
 * Verify that access cost grows monotonically with distance.
 *
 * @param distances - Array of distances to check (should be sorted ascending)
 * @returns true if cost is strictly increasing
 */
export declare function verifyMonotonicCost(distances: number[]): boolean;
/**
 * Security Invariant 2: Phase Mismatch Blocks Access.
 *
 * If a state's tongue phase does not match the expected phase
 * (impedance > threshold), the node is semantically inaccessible
 * REGARDLESS of distance.
 *
 * Tests that for a given position, changing phase from aligned to
 * misaligned makes the node inaccessible.
 *
 * @param position - 6D position in Poincaré ball
 * @param tongueIndex - Tongue to test
 * @param maxImpedance - Impedance threshold
 * @returns Object describing whether the invariant holds
 */
export declare function verifyPhaseMismatchBlocking(position: Vector6D, tongueIndex: number, maxImpedance?: number): {
    holds: boolean;
    alignedImpedance: number;
    misalignedImpedance: number;
};
/**
 * Security Invariant 3: Nodal Stability.
 *
 * Small perturbations to a position on a zero-set should destroy
 * zero-set membership (natural tamper resistance).
 *
 * Specifically: if Φ(x) ≈ 0, then for random perturbation δ with ‖δ‖ > ε,
 * |Φ(x + δ)| > tolerance with high probability.
 *
 * @param x - Position on or near zero-set
 * @param perturbationMagnitude - Size of perturbation
 * @param tolerance - Zero-set tolerance
 * @param numTrials - Number of random perturbations to try
 * @param modes - Cymatic modes
 * @returns Fraction of perturbations that destroy zero-set membership
 */
export declare function verifyNodalStability(x: Vector6D, perturbationMagnitude?: number, tolerance?: number, numTrials?: number, modes?: CymaticModes): {
    destabilizedFraction: number;
    holds: boolean;
};
/**
 * Combined security bound.
 *
 * Total access cost = distance_cost × phase_cost × nodal_cost
 *
 * An attacker must simultaneously:
 * 1. Be close enough (distance < threshold) → cost π^(φ·d*)
 * 2. Have correct tongue phase (all 6 aligned) → cost proportional to ∏ impedance
 * 3. Hit the cymatic zero-set → cost proportional to 1/P(zero-set)
 *
 * @param state - State attempting access
 * @param targetPosition - Position being accessed
 * @returns Combined security cost (higher = harder to access)
 */
export declare function combinedSecurityCost(state: CHSFNState, targetPosition: Vector6D): number;
/**
 * Compute security bits equivalent for a position.
 *
 * Maps the combined security cost to an equivalent number of
 * cryptographic security bits: bits = log2(combinedCost)
 *
 * @param state - Attacker state
 * @param targetPosition - Target position
 * @returns Equivalent security bits
 */
export declare function securityBitsEquivalent(state: CHSFNState, targetPosition: Vector6D): number;
/**
 * Security Invariant 5: Tongue Impedance Ordering Preserved Under Drift.
 *
 * After N drift steps, the relative impedance ordering of tongues
 * should be preserved. If tongue i had lower impedance than tongue j
 * before drift, it should still have lower impedance after drift.
 *
 * This ensures that drift cannot "swap" which tongue provides access
 * — an attacker cannot drift into a configuration where the wrong
 * tongue grants them access.
 *
 * @param state - Initial state
 * @param steps - Number of drift steps
 * @param stepSize - Drift step size
 * @returns Whether ordering is preserved after drift
 */
export declare function verifyTongueBijectionUnderDrift(state: CHSFNState, steps?: number, stepSize?: number): {
    holds: boolean;
    initialOrder: number[];
    finalOrder: number[];
};
/**
 * Security Invariant 6: Energy Does Not Increase Under Drift.
 *
 * Drift follows -∇E, so energy should monotonically decrease
 * (or stay constant at equilibrium). This ensures that the
 * system naturally evolves toward safer states.
 *
 * @param state - Initial state
 * @param steps - Number of drift steps to verify
 * @param stepSize - Drift step size
 * @param tolerance - Numerical tolerance for comparison
 * @returns Whether energy is non-increasing across all steps
 */
export declare function verifyEnergyNonIncrease(state: CHSFNState, steps?: number, stepSize?: number, tolerance?: number): {
    holds: boolean;
    energyTrace: number[];
};
//# sourceMappingURL=securityInvariants.d.ts.map