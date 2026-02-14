/**
 * @file hamiltonian-braid.ts
 * @module ai_brain/hamiltonian-braid
 * @layer Layer 5, Layer 8, Layer 10, Layer 12
 * @component Ternary Braid Algebra — Mirror-Shift-Refactor
 * @version 1.0.0
 * @since 2026-02-08
 *
 * Upgrades the Hamiltonian Path (single 1D rail) into a Hamiltonian Braid
 * (3D trust tube) using the Dual Ternary algebra.
 *
 * Key insight: a single Hamiltonian path is too brittle — "there is never
 * just 1 path in life." By applying the ternary system {-1, 0, +1}² we
 * expand the rail into a trust tube with 9 discrete governance states.
 *
 * Architecture:
 *   1D rail (old)  →  3D trust tube (new)
 *   Binary gate    →  Ternary braid algebra
 *   On/Off         →  9-state phase diagram
 *
 * Generators (the Ternary Braid Algebra):
 *   M      — Mirror swap:    (a, b) ↔ (b, a)
 *   S(φ)   — Mirror shift:   Rotate toward/from mirror diagonal
 *   Π      — Refactor align: Project onto valid manifold (trust tube surface)
 *   0      — Zero gravity:   Fixed-point attractor (consensus hold)
 *
 * Relations:
 *   M² = I                    (Mirror is involution)
 *   S(0) = I                  (No shift = identity)
 *   S(π/4) · M = M · S(π/4)  (Diagonal is M-invariant)
 *   Π² = Π                    (Projection is idempotent)
 *   M · 0 = 0                (Zero is M-invariant)
 *
 * The 9-State Phase Diagram:
 *
 *         ⊥ = -1         ⊥ = 0          ⊥ = +1
 *        ┌─────────────┬─────────────┬─────────────┐
 *  ∥=+1  │  CREATIVE   │   FORWARD   │  RESONANT   │
 *        │  TENSION    │   THRUST    │  LOCK-IN    │
 *        ├─────────────┼─────────────┼─────────────┤
 *  ∥= 0  │  PERPEND.   │   ZERO-G    │  PERPEND.   │
 *        │  DRIFT (-)  │   HOVER     │  DRIFT (+)  │
 *        ├─────────────┼─────────────┼─────────────┤
 *  ∥=-1  │  COLLAPSE   │  BACKWARD   │  CREATIVE   │
 *        │  ATTRACTOR  │   CHECK     │  TENSION    │
 *        └─────────────┴─────────────┴─────────────┘
 *
 * Security Governance Mapping:
 *   RESONANT_LOCK (+1,+1)  → Maximum trust   → Instant approval
 *   FORWARD_THRUST (+1,0)  → High trust      → Standard path
 *   CREATIVE_TENSION (±)   → Medium trust    → Fractal inspection
 *   ZERO_GRAVITY (0,0)     → Consensus       → Hold for quorum
 *   PERPENDICULAR_DRIFT    → Low trust       → Re-anchor required
 *   BACKWARD_CHECK (-1,0)  → Audit mode      → Rollback permitted
 *   COLLAPSE_ATTRACTOR     → Block           → Hard denial
 *
 * Property: iterated mirror-shift-refactor cycles converge to
 * φ-dimensional attractors (fractal dimension ≈ 1.618 ± 0.01).
 */
import type { TernaryValue, DualTernaryState } from './dual-ternary.js';
/**
 * The 9 discrete governance states of the Hamiltonian Braid.
 * Maps 1:1 to the dual ternary {-1,0,+1}² phase diagram.
 */
export type BraidState = 'RESONANT_LOCK' | 'FORWARD_THRUST' | 'CREATIVE_TENSION_A' | 'PERPENDICULAR_POS' | 'ZERO_GRAVITY' | 'PERPENDICULAR_NEG' | 'CREATIVE_TENSION_B' | 'BACKWARD_CHECK' | 'COLLAPSE_ATTRACTOR';
/**
 * Trust level associated with each braid state.
 */
export type TrustLevel = 'maximum' | 'high' | 'medium' | 'consensus' | 'low' | 'audit' | 'block';
/**
 * Security action prescribed by each braid state.
 */
export type SecurityAction = 'INSTANT_APPROVE' | 'STANDARD_PATH' | 'FRACTAL_INSPECT' | 'HOLD_QUORUM' | 'REANCHOR' | 'ROLLBACK' | 'HARD_DENY';
/**
 * Complete governance descriptor for a braid state.
 */
export interface BraidGovernance {
    readonly state: BraidState;
    readonly ternary: DualTernaryState;
    readonly trustLevel: TrustLevel;
    readonly action: SecurityAction;
}
/**
 * Result of a braid cycle iteration.
 */
export interface BraidCycleResult {
    /** Final 2D vector after iteration */
    readonly finalVector: readonly [number, number];
    /** Discrete governance state */
    readonly governance: BraidGovernance;
    /** Trajectory of all intermediate vectors */
    readonly trajectory: ReadonlyArray<readonly [number, number]>;
    /** Estimated fractal dimension of the trajectory */
    readonly fractalDimension: number;
    /** Number of steps until convergence (or max) */
    readonly stepsToConverge: number;
    /** Distance from zero-gravity equilibrium */
    readonly equilibriumDistance: number;
}
/**
 * Configuration for the Hamiltonian Braid system.
 */
export interface BraidConfig {
    /** Trust tube radius — max allowed spiral deviation from center */
    readonly tubeRadius: number;
    /** Ternary quantization threshold */
    readonly quantizeThreshold: number;
    /** Maximum braid cycle iterations */
    readonly maxIterations: number;
    /** Convergence threshold (distance from equilibrium) */
    readonly convergenceThreshold: number;
    /** Shift scale (controls rotation magnitude per step) */
    readonly shiftScale: number;
    /** Refactor trigger (distance multiple of tubeRadius for realignment) */
    readonly refactorTrigger: number;
    /** Phase deviation weight λ in d_braid formula */
    readonly lambda: number;
}
export declare const DEFAULT_BRAID_CONFIG: BraidConfig;
/** Map a dual ternary state to its braid state label. */
export declare function classifyBraidState(primary: TernaryValue, mirror: TernaryValue): BraidState;
/** Map braid state to trust level. */
export declare function braidTrustLevel(state: BraidState): TrustLevel;
/** Map braid state to security action. */
export declare function braidSecurityAction(state: BraidState): SecurityAction;
/** Build the full governance descriptor for a dual ternary state. */
export declare function buildGovernance(primary: TernaryValue, mirror: TernaryValue): BraidGovernance;
/**
 * Generator M: Mirror swap.
 * (a, b) → (b, a)
 *
 * M is an involution: M² = I.
 */
export declare function mirrorSwap(v: readonly [number, number]): [number, number];
/**
 * Generator S(φ): Mirror shift.
 * Rotates toward/away from the mirror diagonal using a symmetric rotation matrix.
 *
 * The rotation matrix is [[cos φ, sin φ], [sin φ, cos φ]] (symmetric,
 * not the standard antisymmetric rotation — this preserves the mirror
 * algebra relation S(π/4)·M = M·S(π/4)).
 *
 * S(0) = I (identity).
 */
export declare function mirrorShift(v: readonly [number, number], phi: number): [number, number];
/**
 * Generator Π: Refactor align (projection).
 * Projects onto the valid manifold (trust tube surface along the mirror diagonal).
 *
 * Π² = Π (projection is idempotent).
 */
export declare function refactorAlign(v: readonly [number, number]): [number, number];
/**
 * Zero-gravity distance: Euclidean distance from the origin (0, 0).
 * The zero-gravity equilibrium is the fixed point where M · 0 = 0.
 */
export declare function zeroGravityDistance(v: readonly [number, number]): number;
/**
 * Quantize a continuous value to ternary {-1, 0, +1}.
 */
export declare function quantize(x: number, threshold?: number): TernaryValue;
/**
 * Quantize a 2D vector to a DualTernaryState.
 */
export declare function quantizeVector(v: readonly [number, number], threshold?: number): DualTernaryState;
/**
 * Estimate the fractal (box-counting) dimension of a 2D trajectory.
 *
 * For well-behaved braids, the dimension converges to φ ≈ 1.618
 * because the golden ratio is the fixed point of the continued
 * fraction expansion — exactly what iterated mirror-shift-refactor produces.
 */
export declare function estimateBraidFractalDimension(trajectory: ReadonlyArray<readonly [number, number]>, scales?: number[]): number;
/**
 * Compute the Harmonic Wall energy cost for deviation from the trust tube.
 *
 * Inside tube (d ≤ r): cost = 0
 * Outside tube: cost = φ^(d²) — super-exponential penalty
 *
 * This is the geometric "0" from binary — the void where no edge exists.
 */
export declare function harmonicTubeCost(distanceFromCenter: number, tubeRadius: number): number;
/**
 * Check whether a vector is inside the trust tube.
 */
export declare function isInsideTube(v: readonly [number, number], tubeRadius: number): boolean;
/**
 * Hyperbolic distance in the 2D Poincaré disk.
 *
 * d_H(u,v) = acosh(1 + 2|u-v|² / ((1-|u|²)(1-|v|²)))
 *
 * Safe version: clamps denominators to avoid division by zero at the boundary.
 */
export declare function hyperbolicDistance2D(u: readonly [number, number], v: readonly [number, number]): number;
/**
 * Compute the center of a ternary quantization zone.
 *
 * +1 zone: [threshold, 1.0] → center at (1 + threshold) / 2
 *  0 zone: [-threshold, threshold] → center at 0
 * -1 zone: [-1.0, -threshold] → center at -(1 + threshold) / 2
 */
export declare function ternaryCenter(t: TernaryValue, threshold?: number): number;
/**
 * Phase deviation: Euclidean distance from the quantized state center.
 *
 * Measures how far a continuous vector is from the center of its
 * discrete governance region. Small deviation = stable governance;
 * large deviation = near a phase boundary (transition risk).
 */
export declare function phaseDeviation(v: readonly [number, number], threshold?: number): number;
/**
 * Phase-aware projection Π: ℝ² × {-1,0,+1}² → M_constraint
 *
 * Projects a vector onto the constraint manifold for a given phase state.
 * Ensures:
 *   1. The continuous position is consistent with the discrete phase
 *   2. The result stays inside the Poincaré disk (||v|| < 1)
 *   3. The Hamiltonian structure is maintained (valid governance region)
 *
 * If no phase is provided, uses the vector's own quantized phase.
 */
export declare function phaseAwareProject(v: readonly [number, number], phase?: DualTernaryState, threshold?: number): [number, number];
/**
 * Compute the 9 rail center points (one per braid state) in continuous space.
 *
 * Each center is the midpoint of the constraint region for that state,
 * ensuring all centers are safely inside the Poincaré disk.
 */
export declare function computeRailCenters(threshold?: number): ReadonlyArray<readonly [number, number]>;
/**
 * Default rail centers at threshold 0.33.
 * Centers: ±0.665, 0 → corner norms ≈ 0.94 (safely inside Poincaré disk).
 */
export declare const BRAID_RAIL_CENTERS: ReadonlyArray<readonly [number, number]>;
/**
 * d_braid(x, rail) = min_{r∈Rail} d_H(Π(x), r) + λ·|phase_deviation|
 *
 * The refined tube distance that combines:
 *   1. Hyperbolic distance from the phase-aware projection to the nearest rail point
 *   2. Phase deviation penalty (how far from the governance center)
 *
 * Properties:
 *   - d_braid = 0 only at exact rail centers (perfect governance alignment)
 *   - d_braid grows exponentially near the Poincaré boundary (hyperbolic distance)
 *   - λ penalizes phase-boundary straddling (governance instability)
 *
 * @param v - Input 2D vector
 * @param lambda - Phase deviation weight (default 0.5)
 * @param threshold - Quantization threshold (default 0.33)
 * @param rail - Rail reference points (default: 9 state centers)
 * @returns The d_braid distance
 */
export declare function dBraid(v: readonly [number, number], lambda?: number, threshold?: number, rail?: ReadonlyArray<readonly [number, number]>): number;
/**
 * Check whether a transition between two braid states is topologically valid.
 *
 * Valid transitions have Chebyshev distance ≤ 1 in the (primary, mirror) grid.
 * This ensures no "impossible" governance jumps (e.g., RESONANT_LOCK → COLLAPSE_ATTRACTOR).
 *
 * Adjacent transitions include horizontal, vertical, and diagonal moves.
 */
export declare function isValidBraidTransition(from: DualTernaryState, to: DualTernaryState): boolean;
/**
 * Compute the governance distance between two braid states.
 * Returns Chebyshev distance in the 3×3 ternary grid (0, 1, or 2).
 */
export declare function braidStateDistance(from: DualTernaryState, to: DualTernaryState): number;
/**
 * The Hamiltonian Braid — ternary spiral governance system.
 *
 * Replaces the single 1D Hamiltonian rail with a 3D trust tube.
 * The AI can spiral around the central axis (exploring options)
 * as long as the net momentum stays within the tube boundaries.
 *
 * Usage:
 *   const braid = new AetherBraid();
 *   const result = braid.iterateCycle([0.7, -0.3]);
 *   // result.governance.action → 'FRACTAL_INSPECT'
 *   // result.fractalDimension  → ~1.618 (φ-attractor)
 */
export declare class AetherBraid {
    private readonly config;
    constructor(config?: Partial<BraidConfig>);
    /**
     * Classify a continuous 2D vector to its braid governance state.
     */
    classify(v: readonly [number, number]): BraidGovernance;
    /**
     * Evaluate a trajectory pair (forward vector + perpendicular check).
     *
     * This is the core "Trust Tube" check:
     * - Is the braid coherent?
     * - Is it inside the tube?
     * - What governance state does it map to?
     */
    evaluate(primaryVector: readonly [number, number], orthogonalVector: readonly [number, number]): {
        governance: BraidGovernance;
        coherence: number;
        distanceFromCenter: number;
        tubeCost: number;
        insideTube: boolean;
    };
    /**
     * Run the Mirror-Shift-Refactor cycle.
     *
     * Iterates the three generators in sequence:
     *   1. S(φ·i): Mirror shift (φ varies with golden ratio for coverage)
     *   2. Zero-gravity check: stop if converged to equilibrium
     *   3. Π: Refactor alignment (if drifting outside tube)
     *
     * The trajectory's fractal dimension naturally converges to φ ≈ 1.618
     * because the golden ratio is the fixed point of the continued fraction
     * expansion, which is exactly what iterated MSR produces.
     */
    iterateCycle(initial: readonly [number, number], maxSteps?: number): BraidCycleResult;
    /**
     * Compute the Harmonic Wall energy for a given vector.
     * Returns 0 if inside the tube, φ^(d²) otherwise.
     */
    computeTubeCost(v: readonly [number, number]): number;
    /**
     * Compute the refined d_braid distance.
     *
     * d_braid(x, rail) = min_{r∈Rail} d_H(Π(x), r) + λ·|phase_deviation|
     *
     * Uses the instance's lambda and quantizeThreshold configuration.
     */
    computeDBraid(v: readonly [number, number], rail?: ReadonlyArray<readonly [number, number]>): number;
    /**
     * Phase-aware projection using the instance's threshold.
     * Projects v onto the constraint manifold for the given (or auto-detected) phase.
     */
    project(v: readonly [number, number], phase?: DualTernaryState): [number, number];
    /**
     * Check if a governance transition is topologically valid.
     */
    isValidTransition(from: readonly [number, number], to: readonly [number, number]): boolean;
    /**
     * Apply all four generators in sequence and return the result.
     * Useful for testing algebra relations.
     *
     * Order: M → S(φ) → Π
     */
    applyGenerators(v: readonly [number, number], phi: number): {
        afterMirror: [number, number];
        afterShift: [number, number];
        afterRefactor: [number, number];
    };
    /** Get the configuration. */
    getConfig(): BraidConfig;
}
/**
 * The complete 9-state governance table.
 * Each entry maps a dual ternary (primary, mirror) pair to its
 * trust level and security action.
 */
export declare const BRAID_GOVERNANCE_TABLE: ReadonlyArray<BraidGovernance>;
//# sourceMappingURL=hamiltonian-braid.d.ts.map