"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.verifyExponentialCostInvariant = verifyExponentialCostInvariant;
exports.verifyMonotonicCost = verifyMonotonicCost;
exports.verifyPhaseMismatchBlocking = verifyPhaseMismatchBlocking;
exports.verifyNodalStability = verifyNodalStability;
exports.combinedSecurityCost = combinedSecurityCost;
exports.securityBitsEquivalent = securityBitsEquivalent;
exports.verifyTongueBijectionUnderDrift = verifyTongueBijectionUnderDrift;
exports.verifyEnergyNonIncrease = verifyEnergyNonIncrease;
const chsfn_js_1 = require("./chsfn.js");
// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
const PHI = (1 + Math.sqrt(5)) / 2;
const EPSILON = 1e-10;
// ═══════════════════════════════════════════════════════════════
// Invariant 1: Exponential Access Cost
// ═══════════════════════════════════════════════════════════════
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
function verifyExponentialCostInvariant(d1, d2, R = 1.5) {
    if (d2 <= d1) {
        return { holds: true, actualRatio: 1, minExpectedRatio: 1 };
    }
    const cost1 = (0, chsfn_js_1.accessCost)(d1, R);
    const cost2 = (0, chsfn_js_1.accessCost)(d2, R);
    const actualRatio = cost2 / cost1;
    const minExpectedRatio = Math.pow(Math.PI, PHI * (d2 - d1));
    return {
        holds: actualRatio >= minExpectedRatio - EPSILON,
        actualRatio,
        minExpectedRatio,
    };
}
/**
 * Verify that access cost grows monotonically with distance.
 *
 * @param distances - Array of distances to check (should be sorted ascending)
 * @returns true if cost is strictly increasing
 */
function verifyMonotonicCost(distances) {
    for (let i = 1; i < distances.length; i++) {
        if ((0, chsfn_js_1.accessCost)(distances[i]) <= (0, chsfn_js_1.accessCost)(distances[i - 1])) {
            return false;
        }
    }
    return true;
}
// ═══════════════════════════════════════════════════════════════
// Invariant 2: Phase Mismatch Blocking
// ═══════════════════════════════════════════════════════════════
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
function verifyPhaseMismatchBlocking(position, tongueIndex, maxImpedance = 0.3) {
    const expectedPhase = (2 * Math.PI * tongueIndex) / 6;
    // Aligned state: phase matches expected
    const alignedState = {
        position,
        phase: [0, 1, 2, 3, 4, 5].map((i) => (2 * Math.PI * i) / 6),
        mass: 1.0,
    };
    // Misaligned state: phase offset by π (maximum mismatch)
    const misalignedPhase = [...alignedState.phase];
    misalignedPhase[tongueIndex] = expectedPhase + Math.PI;
    const misalignedState = {
        position,
        phase: misalignedPhase,
        mass: 1.0,
    };
    const alignedImpedance = (0, chsfn_js_1.tongueImpedanceAt)(alignedState, tongueIndex);
    const misalignedImpedance = (0, chsfn_js_1.tongueImpedanceAt)(misalignedState, tongueIndex);
    return {
        holds: alignedImpedance < maxImpedance && misalignedImpedance >= maxImpedance,
        alignedImpedance,
        misalignedImpedance,
    };
}
// ═══════════════════════════════════════════════════════════════
// Invariant 3: Nodal Stability Under Perturbation
// ═══════════════════════════════════════════════════════════════
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
function verifyNodalStability(x, perturbationMagnitude = 0.05, tolerance = 0.01, numTrials = 50, modes = chsfn_js_1.DEFAULT_MODES) {
    let destabilized = 0;
    for (let t = 0; t < numTrials; t++) {
        // Deterministic pseudo-random perturbation using golden angle
        const angle = t * PHI * 2 * Math.PI;
        const perturbation = [
            perturbationMagnitude * Math.cos(angle),
            perturbationMagnitude * Math.sin(angle),
            perturbationMagnitude * Math.cos(angle * 1.3),
            perturbationMagnitude * Math.sin(angle * 0.7),
            perturbationMagnitude * Math.cos(angle * 2.1),
            perturbationMagnitude * Math.sin(angle * 1.7),
        ];
        const perturbed = x.map((v, i) => v + perturbation[i]);
        const fieldValue = Math.abs((0, chsfn_js_1.cymaticField)(perturbed, modes));
        if (fieldValue > tolerance) {
            destabilized++;
        }
    }
    const fraction = destabilized / numTrials;
    return {
        destabilizedFraction: fraction,
        holds: fraction > 0.7, // At least 70% of perturbations should destroy access
    };
}
// ═══════════════════════════════════════════════════════════════
// Invariant 4: Combined Security Bound
// ═══════════════════════════════════════════════════════════════
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
function combinedSecurityCost(state, targetPosition) {
    // Distance cost: π^(φ·d*)
    const dist = (0, chsfn_js_1.hyperbolicDistance6D)(state.position, targetPosition);
    const distanceCost = (0, chsfn_js_1.accessCost)(dist);
    // Phase cost: product of all tongue impedances (higher = harder)
    let phaseCost = 1;
    for (let i = 0; i < 6; i++) {
        const imp = (0, chsfn_js_1.tongueImpedanceAt)(state, i);
        phaseCost *= 1 + imp * 10; // Each misaligned tongue multiplies cost by up to 11x
    }
    // Nodal cost: inverse of probability of landing on zero-set
    const fieldMagnitude = Math.abs((0, chsfn_js_1.cymaticField)(targetPosition));
    const nodalCost = 1 + fieldMagnitude * 100;
    return distanceCost * phaseCost * nodalCost;
}
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
function securityBitsEquivalent(state, targetPosition) {
    const cost = combinedSecurityCost(state, targetPosition);
    return Math.log2(Math.max(cost, 1));
}
// ═══════════════════════════════════════════════════════════════
// Invariant 5: Tongue Bijection Under Drift
// ═══════════════════════════════════════════════════════════════
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
function verifyTongueBijectionUnderDrift(state, steps = 10, stepSize = 0.001) {
    // Compute initial impedance ordering
    const initialImpedances = Array.from({ length: 6 }, (_, i) => (0, chsfn_js_1.tongueImpedanceAt)(state, i));
    const initialOrder = Array.from({ length: 6 }, (_, i) => i)
        .sort((a, b) => initialImpedances[a] - initialImpedances[b]);
    // Drift the state
    let current = state;
    for (let s = 0; s < steps; s++) {
        current = (0, chsfn_js_1.driftStep)(current, stepSize);
    }
    // Compute final impedance ordering
    const finalImpedances = Array.from({ length: 6 }, (_, i) => (0, chsfn_js_1.tongueImpedanceAt)(current, i));
    const finalOrder = Array.from({ length: 6 }, (_, i) => i)
        .sort((a, b) => finalImpedances[a] - finalImpedances[b]);
    // Check if ordering is preserved
    const holds = initialOrder.every((v, i) => v === finalOrder[i]);
    return { holds, initialOrder, finalOrder };
}
// ═══════════════════════════════════════════════════════════════
// Invariant 6: Energy Non-Increase Under Drift
// ═══════════════════════════════════════════════════════════════
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
function verifyEnergyNonIncrease(state, steps = 20, stepSize = 0.001, tolerance = 0.01) {
    const energyTrace = [];
    let current = state;
    energyTrace.push((0, chsfn_js_1.energyFunctional)(current));
    for (let s = 0; s < steps; s++) {
        current = (0, chsfn_js_1.driftStep)(current, stepSize);
        energyTrace.push((0, chsfn_js_1.energyFunctional)(current));
    }
    // Check that energy is non-increasing (with tolerance for numerical noise)
    let holds = true;
    for (let i = 1; i < energyTrace.length; i++) {
        if (energyTrace[i] > energyTrace[i - 1] + tolerance) {
            holds = false;
            break;
        }
    }
    return { holds, energyTrace };
}
//# sourceMappingURL=securityInvariants.js.map