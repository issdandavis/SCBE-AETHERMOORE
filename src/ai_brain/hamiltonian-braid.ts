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

import { PHI, BRAIN_EPSILON, POINCARE_MAX_NORM } from './types.js';
import type { TernaryValue, DualTernaryState } from './dual-ternary.js';

// ═══════════════════════════════════════════════════════════════
// Braid State Types
// ═══════════════════════════════════════════════════════════════

/**
 * The 9 discrete governance states of the Hamiltonian Braid.
 * Maps 1:1 to the dual ternary {-1,0,+1}² phase diagram.
 */
export type BraidState =
  | 'RESONANT_LOCK'      // (+1, +1) — maximum trust, fast path
  | 'FORWARD_THRUST'     // (+1,  0) — high trust, standard path
  | 'CREATIVE_TENSION_A' // (+1, -1) — asymmetric, needs inspection
  | 'PERPENDICULAR_POS'  // ( 0, +1) — low trust, re-anchor (+)
  | 'ZERO_GRAVITY'       // ( 0,  0) — consensus hold
  | 'PERPENDICULAR_NEG'  // ( 0, -1) — low trust, re-anchor (-)
  | 'CREATIVE_TENSION_B' // (-1, +1) — asymmetric, needs inspection
  | 'BACKWARD_CHECK'     // (-1,  0) — audit mode, rollback
  | 'COLLAPSE_ATTRACTOR'; // (-1, -1) — hard denial

/**
 * Trust level associated with each braid state.
 */
export type TrustLevel =
  | 'maximum'
  | 'high'
  | 'medium'
  | 'consensus'
  | 'low'
  | 'audit'
  | 'block';

/**
 * Security action prescribed by each braid state.
 */
export type SecurityAction =
  | 'INSTANT_APPROVE'
  | 'STANDARD_PATH'
  | 'FRACTAL_INSPECT'
  | 'HOLD_QUORUM'
  | 'REANCHOR'
  | 'ROLLBACK'
  | 'HARD_DENY';

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

export const DEFAULT_BRAID_CONFIG: BraidConfig = {
  tubeRadius: 0.15,
  quantizeThreshold: 0.33,
  maxIterations: 500,
  convergenceThreshold: 0.01,
  shiftScale: 0.1,
  refactorTrigger: 3.0,
  lambda: 0.5,
};

// ═══════════════════════════════════════════════════════════════
// Governance Mapping
// ═══════════════════════════════════════════════════════════════

/** Map a dual ternary state to its braid state label. */
export function classifyBraidState(primary: TernaryValue, mirror: TernaryValue): BraidState {
  if (primary === 1 && mirror === 1) return 'RESONANT_LOCK';
  if (primary === 1 && mirror === 0) return 'FORWARD_THRUST';
  if (primary === 1 && mirror === -1) return 'CREATIVE_TENSION_A';
  if (primary === 0 && mirror === 1) return 'PERPENDICULAR_POS';
  if (primary === 0 && mirror === 0) return 'ZERO_GRAVITY';
  if (primary === 0 && mirror === -1) return 'PERPENDICULAR_NEG';
  if (primary === -1 && mirror === 1) return 'CREATIVE_TENSION_B';
  if (primary === -1 && mirror === 0) return 'BACKWARD_CHECK';
  return 'COLLAPSE_ATTRACTOR'; // (-1, -1)
}

/** Map braid state to trust level. */
export function braidTrustLevel(state: BraidState): TrustLevel {
  switch (state) {
    case 'RESONANT_LOCK': return 'maximum';
    case 'FORWARD_THRUST': return 'high';
    case 'CREATIVE_TENSION_A':
    case 'CREATIVE_TENSION_B': return 'medium';
    case 'ZERO_GRAVITY': return 'consensus';
    case 'PERPENDICULAR_POS':
    case 'PERPENDICULAR_NEG': return 'low';
    case 'BACKWARD_CHECK': return 'audit';
    case 'COLLAPSE_ATTRACTOR': return 'block';
  }
}

/** Map braid state to security action. */
export function braidSecurityAction(state: BraidState): SecurityAction {
  switch (state) {
    case 'RESONANT_LOCK': return 'INSTANT_APPROVE';
    case 'FORWARD_THRUST': return 'STANDARD_PATH';
    case 'CREATIVE_TENSION_A':
    case 'CREATIVE_TENSION_B': return 'FRACTAL_INSPECT';
    case 'ZERO_GRAVITY': return 'HOLD_QUORUM';
    case 'PERPENDICULAR_POS':
    case 'PERPENDICULAR_NEG': return 'REANCHOR';
    case 'BACKWARD_CHECK': return 'ROLLBACK';
    case 'COLLAPSE_ATTRACTOR': return 'HARD_DENY';
  }
}

/** Build the full governance descriptor for a dual ternary state. */
export function buildGovernance(primary: TernaryValue, mirror: TernaryValue): BraidGovernance {
  const state = classifyBraidState(primary, mirror);
  return {
    state,
    ternary: { primary, mirror },
    trustLevel: braidTrustLevel(state),
    action: braidSecurityAction(state),
  };
}

// ═══════════════════════════════════════════════════════════════
// Braid Algebra Generators
// ═══════════════════════════════════════════════════════════════

/**
 * Generator M: Mirror swap.
 * (a, b) → (b, a)
 *
 * M is an involution: M² = I.
 */
export function mirrorSwap(v: readonly [number, number]): [number, number] {
  return [v[1], v[0]];
}

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
export function mirrorShift(v: readonly [number, number], phi: number): [number, number] {
  const c = Math.cos(phi);
  const s = Math.sin(phi);
  return [
    v[0] * c + v[1] * s,
    v[0] * s + v[1] * c,
  ];
}

/**
 * Generator Π: Refactor align (projection).
 * Projects onto the valid manifold (trust tube surface along the mirror diagonal).
 *
 * Π² = Π (projection is idempotent).
 */
export function refactorAlign(v: readonly [number, number]): [number, number] {
  const SQRT2_INV = 1 / Math.sqrt(2);
  const basis: [number, number] = [SQRT2_INV, SQRT2_INV]; // mirror diagonal

  // Project onto mirror diagonal
  const dot = v[0] * basis[0] + v[1] * basis[1];
  let px = dot * basis[0];
  let py = dot * basis[1];

  // Clamp to unit ball
  const norm = Math.sqrt(px * px + py * py);
  if (norm > 1.0) {
    px /= norm;
    py /= norm;
  }

  return [px, py];
}

/**
 * Zero-gravity distance: Euclidean distance from the origin (0, 0).
 * The zero-gravity equilibrium is the fixed point where M · 0 = 0.
 */
export function zeroGravityDistance(v: readonly [number, number]): number {
  return Math.sqrt(v[0] * v[0] + v[1] * v[1]);
}

// ═══════════════════════════════════════════════════════════════
// Ternary Quantization
// ═══════════════════════════════════════════════════════════════

/**
 * Quantize a continuous value to ternary {-1, 0, +1}.
 */
export function quantize(x: number, threshold: number = 0.33): TernaryValue {
  if (x > threshold) return 1;
  if (x < -threshold) return -1;
  return 0;
}

/**
 * Quantize a 2D vector to a DualTernaryState.
 */
export function quantizeVector(
  v: readonly [number, number],
  threshold: number = 0.33
): DualTernaryState {
  return {
    primary: quantize(v[0], threshold),
    mirror: quantize(v[1], threshold),
  };
}

// ═══════════════════════════════════════════════════════════════
// Fractal Dimension Estimation
// ═══════════════════════════════════════════════════════════════

/**
 * Estimate the fractal (box-counting) dimension of a 2D trajectory.
 *
 * For well-behaved braids, the dimension converges to φ ≈ 1.618
 * because the golden ratio is the fixed point of the continued
 * fraction expansion — exactly what iterated mirror-shift-refactor produces.
 */
export function estimateBraidFractalDimension(
  trajectory: ReadonlyArray<readonly [number, number]>,
  scales: number[] = [0.2, 0.1, 0.05, 0.025]
): number {
  if (trajectory.length < 2) return 0;

  const counts: Array<{ scale: number; count: number }> = [];

  for (const scale of scales) {
    const boxes = new Set<string>();
    for (const point of trajectory) {
      const bx = Math.floor(point[0] / scale);
      const by = Math.floor(point[1] / scale);
      boxes.add(`${bx},${by}`);
    }
    counts.push({ scale, count: boxes.size });
  }

  // Linear regression in log-log space: log(N) = d * log(1/ε) + c
  const logEps = counts.map(c => Math.log(1 / c.scale));
  const logN = counts.map(c => Math.log(c.count));

  const n = logEps.length;
  const sumX = logEps.reduce((s, x) => s + x, 0);
  const sumY = logN.reduce((s, y) => s + y, 0);
  const sumXY = logEps.reduce((s, x, i) => s + x * logN[i], 0);
  const sumX2 = logEps.reduce((s, x) => s + x * x, 0);

  const denominator = n * sumX2 - sumX * sumX;
  if (Math.abs(denominator) < BRAIN_EPSILON) return 1.0;

  return (n * sumXY - sumX * sumY) / denominator;
}

// ═══════════════════════════════════════════════════════════════
// Harmonic Tube Check
// ═══════════════════════════════════════════════════════════════

/**
 * Compute the Harmonic Wall energy cost for deviation from the trust tube.
 *
 * Inside tube (d ≤ r): cost = 0
 * Outside tube: cost = φ^(d²) — super-exponential penalty
 *
 * This is the geometric "0" from binary — the void where no edge exists.
 */
export function harmonicTubeCost(
  distanceFromCenter: number,
  tubeRadius: number
): number {
  if (distanceFromCenter <= tubeRadius) return 0;
  const excess = distanceFromCenter - tubeRadius;
  return Math.pow(PHI, excess * excess);
}

/**
 * Check whether a vector is inside the trust tube.
 */
export function isInsideTube(
  v: readonly [number, number],
  tubeRadius: number
): boolean {
  return zeroGravityDistance(v) <= tubeRadius;
}

// ═══════════════════════════════════════════════════════════════
// Hyperbolic Distance (2D Poincaré Disk)
// ═══════════════════════════════════════════════════════════════

/**
 * Hyperbolic distance in the 2D Poincaré disk.
 *
 * d_H(u,v) = acosh(1 + 2|u-v|² / ((1-|u|²)(1-|v|²)))
 *
 * Safe version: clamps denominators to avoid division by zero at the boundary.
 */
export function hyperbolicDistance2D(
  u: readonly [number, number],
  v: readonly [number, number]
): number {
  const dx = u[0] - v[0];
  const dy = u[1] - v[1];
  const diffSq = dx * dx + dy * dy;
  const uSq = u[0] * u[0] + u[1] * u[1];
  const vSq = v[0] * v[0] + v[1] * v[1];
  const uFactor = Math.max(BRAIN_EPSILON, 1 - uSq);
  const vFactor = Math.max(BRAIN_EPSILON, 1 - vSq);
  const arg = 1 + (2 * diffSq) / (uFactor * vFactor);
  return Math.acosh(Math.max(1, arg));
}

// ═══════════════════════════════════════════════════════════════
// Phase Deviation
// ═══════════════════════════════════════════════════════════════

/**
 * Compute the center of a ternary quantization zone.
 *
 * +1 zone: [threshold, 1.0] → center at (1 + threshold) / 2
 *  0 zone: [-threshold, threshold] → center at 0
 * -1 zone: [-1.0, -threshold] → center at -(1 + threshold) / 2
 */
export function ternaryCenter(t: TernaryValue, threshold: number = 0.33): number {
  if (t === 1) return (1 + threshold) / 2;
  if (t === -1) return -(1 + threshold) / 2;
  return 0;
}

/**
 * Phase deviation: Euclidean distance from the quantized state center.
 *
 * Measures how far a continuous vector is from the center of its
 * discrete governance region. Small deviation = stable governance;
 * large deviation = near a phase boundary (transition risk).
 */
export function phaseDeviation(
  v: readonly [number, number],
  threshold: number = 0.33
): number {
  const qp = quantize(v[0], threshold);
  const qm = quantize(v[1], threshold);
  const cp = ternaryCenter(qp, threshold);
  const cm = ternaryCenter(qm, threshold);
  const dp = v[0] - cp;
  const dm = v[1] - cm;
  return Math.sqrt(dp * dp + dm * dm);
}

// ═══════════════════════════════════════════════════════════════
// Phase-Aware Projection (Refined Π)
// ═══════════════════════════════════════════════════════════════

/**
 * Compute the constraint range for a ternary value.
 * Returns [min, max] for the continuous region consistent with the phase.
 */
function phaseRange(
  t: TernaryValue,
  threshold: number
): [number, number] {
  if (t === 1) return [threshold, 1.0];
  if (t === -1) return [-1.0, -threshold];
  return [-threshold, threshold];
}

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
export function phaseAwareProject(
  v: readonly [number, number],
  phase?: DualTernaryState,
  threshold: number = 0.33
): [number, number] {
  const q = phase ?? quantizeVector(v, threshold);
  const [xMin, xMax] = phaseRange(q.primary, threshold);
  const [yMin, yMax] = phaseRange(q.mirror, threshold);

  // Clamp to constraint region
  let x = Math.max(xMin, Math.min(xMax, v[0]));
  let y = Math.max(yMin, Math.min(yMax, v[1]));

  // Ensure inside Poincaré disk
  const norm = Math.sqrt(x * x + y * y);
  if (norm >= POINCARE_MAX_NORM) {
    const scale = (POINCARE_MAX_NORM - BRAIN_EPSILON) / norm;
    x *= scale;
    y *= scale;
  }

  return [x, y];
}

// ═══════════════════════════════════════════════════════════════
// Braid Rail Reference Points
// ═══════════════════════════════════════════════════════════════

/**
 * Compute the 9 rail center points (one per braid state) in continuous space.
 *
 * Each center is the midpoint of the constraint region for that state,
 * ensuring all centers are safely inside the Poincaré disk.
 */
export function computeRailCenters(
  threshold: number = 0.33
): ReadonlyArray<readonly [number, number]> {
  const ternaries: TernaryValue[] = [1, 0, -1];
  const centers: Array<[number, number]> = [];
  for (const p of ternaries) {
    for (const m of ternaries) {
      centers.push([ternaryCenter(p, threshold), ternaryCenter(m, threshold)]);
    }
  }
  return centers;
}

/**
 * Default rail centers at threshold 0.33.
 * Centers: ±0.665, 0 → corner norms ≈ 0.94 (safely inside Poincaré disk).
 */
export const BRAID_RAIL_CENTERS: ReadonlyArray<readonly [number, number]> =
  computeRailCenters(0.33);

// ═══════════════════════════════════════════════════════════════
// d_braid Distance (Hyperbolic Tube Distance)
// ═══════════════════════════════════════════════════════════════

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
export function dBraid(
  v: readonly [number, number],
  lambda: number = 0.5,
  threshold: number = 0.33,
  rail: ReadonlyArray<readonly [number, number]> = BRAID_RAIL_CENTERS
): number {
  // Phase-aware projection
  const projected = phaseAwareProject(v, undefined, threshold);

  // Phase deviation
  const phaseDev = phaseDeviation(v, threshold);

  // Find minimum hyperbolic distance to any rail point
  let minDist = Infinity;
  for (const r of rail) {
    // Ensure rail point is inside Poincaré disk
    const rNorm = Math.sqrt(r[0] * r[0] + r[1] * r[1]);
    let rSafe: readonly [number, number];
    if (rNorm >= POINCARE_MAX_NORM) {
      const s = (POINCARE_MAX_NORM - BRAIN_EPSILON) / rNorm;
      rSafe = [r[0] * s, r[1] * s];
    } else {
      rSafe = r;
    }

    const d = hyperbolicDistance2D(projected, rSafe);
    if (d < minDist) minDist = d;
  }

  return minDist + lambda * phaseDev;
}

// ═══════════════════════════════════════════════════════════════
// Braid Transition Validation
// ═══════════════════════════════════════════════════════════════

/**
 * Check whether a transition between two braid states is topologically valid.
 *
 * Valid transitions have Chebyshev distance ≤ 1 in the (primary, mirror) grid.
 * This ensures no "impossible" governance jumps (e.g., RESONANT_LOCK → COLLAPSE_ATTRACTOR).
 *
 * Adjacent transitions include horizontal, vertical, and diagonal moves.
 */
export function isValidBraidTransition(
  from: DualTernaryState,
  to: DualTernaryState
): boolean {
  return (
    Math.abs(from.primary - to.primary) <= 1 &&
    Math.abs(from.mirror - to.mirror) <= 1
  );
}

/**
 * Compute the governance distance between two braid states.
 * Returns Chebyshev distance in the 3×3 ternary grid (0, 1, or 2).
 */
export function braidStateDistance(
  from: DualTernaryState,
  to: DualTernaryState
): number {
  return Math.max(
    Math.abs(from.primary - to.primary),
    Math.abs(from.mirror - to.mirror)
  );
}

// ═══════════════════════════════════════════════════════════════
// The AetherBraid System
// ═══════════════════════════════════════════════════════════════

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
export class AetherBraid {
  private readonly config: BraidConfig;

  constructor(config: Partial<BraidConfig> = {}) {
    this.config = { ...DEFAULT_BRAID_CONFIG, ...config };
  }

  /**
   * Classify a continuous 2D vector to its braid governance state.
   */
  classify(v: readonly [number, number]): BraidGovernance {
    const q = quantizeVector(v, this.config.quantizeThreshold);
    return buildGovernance(q.primary, q.mirror);
  }

  /**
   * Evaluate a trajectory pair (forward vector + perpendicular check).
   *
   * This is the core "Trust Tube" check:
   * - Is the braid coherent?
   * - Is it inside the tube?
   * - What governance state does it map to?
   */
  evaluate(
    primaryVector: readonly [number, number],
    orthogonalVector: readonly [number, number]
  ): {
    governance: BraidGovernance;
    coherence: number;
    distanceFromCenter: number;
    tubeCost: number;
    insideTube: boolean;
  } {
    // Spin coherence: dot product for alignment
    const coherence =
      primaryVector[0] * orthogonalVector[0] +
      primaryVector[1] * orthogonalVector[1];

    // Combined vector for tube check
    const combined: [number, number] = [
      (primaryVector[0] + orthogonalVector[0]) / 2,
      (primaryVector[1] + orthogonalVector[1]) / 2,
    ];

    const dist = zeroGravityDistance(combined);
    const cost = harmonicTubeCost(dist, this.config.tubeRadius);
    const inside = dist <= this.config.tubeRadius;
    const governance = this.classify(combined);

    return { governance, coherence, distanceFromCenter: dist, tubeCost: cost, insideTube: inside };
  }

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
  iterateCycle(
    initial: readonly [number, number],
    maxSteps?: number
  ): BraidCycleResult {
    const steps = maxSteps ?? this.config.maxIterations;
    const trajectory: Array<[number, number]> = [[initial[0], initial[1]]];
    let v: [number, number] = [initial[0], initial[1]];
    let convergedAt = steps;

    for (let i = 0; i < steps; i++) {
      // 1. Mirror shift — golden ratio angle rotation
      const phi = ((i * PHI) % (Math.PI / 2));
      v = mirrorShift(v, phi * this.config.shiftScale);

      // 2. Zero-gravity convergence check
      const dist = zeroGravityDistance(v);
      if (dist < this.config.convergenceThreshold) {
        convergedAt = i + 1;
        trajectory.push([v[0], v[1]]);
        break;
      }

      // 3. Refactor alignment — only if drifting far outside tube
      if (dist > this.config.tubeRadius * this.config.refactorTrigger) {
        v = refactorAlign(v);
      }

      trajectory.push([v[0], v[1]]);
    }

    const fractalDimension = estimateBraidFractalDimension(trajectory);
    const governance = this.classify(v);
    const equilibriumDistance = zeroGravityDistance(v);

    return {
      finalVector: [v[0], v[1]],
      governance,
      trajectory,
      fractalDimension,
      stepsToConverge: convergedAt,
      equilibriumDistance,
    };
  }

  /**
   * Compute the Harmonic Wall energy for a given vector.
   * Returns 0 if inside the tube, φ^(d²) otherwise.
   */
  computeTubeCost(v: readonly [number, number]): number {
    return harmonicTubeCost(zeroGravityDistance(v), this.config.tubeRadius);
  }

  /**
   * Compute the refined d_braid distance.
   *
   * d_braid(x, rail) = min_{r∈Rail} d_H(Π(x), r) + λ·|phase_deviation|
   *
   * Uses the instance's lambda and quantizeThreshold configuration.
   */
  computeDBraid(
    v: readonly [number, number],
    rail?: ReadonlyArray<readonly [number, number]>
  ): number {
    const r = rail ?? computeRailCenters(this.config.quantizeThreshold);
    return dBraid(v, this.config.lambda, this.config.quantizeThreshold, r);
  }

  /**
   * Phase-aware projection using the instance's threshold.
   * Projects v onto the constraint manifold for the given (or auto-detected) phase.
   */
  project(
    v: readonly [number, number],
    phase?: DualTernaryState
  ): [number, number] {
    return phaseAwareProject(v, phase, this.config.quantizeThreshold);
  }

  /**
   * Check if a governance transition is topologically valid.
   */
  isValidTransition(
    from: readonly [number, number],
    to: readonly [number, number]
  ): boolean {
    const qFrom = quantizeVector(from, this.config.quantizeThreshold);
    const qTo = quantizeVector(to, this.config.quantizeThreshold);
    return isValidBraidTransition(qFrom, qTo);
  }

  /**
   * Apply all four generators in sequence and return the result.
   * Useful for testing algebra relations.
   *
   * Order: M → S(φ) → Π
   */
  applyGenerators(
    v: readonly [number, number],
    phi: number
  ): {
    afterMirror: [number, number];
    afterShift: [number, number];
    afterRefactor: [number, number];
  } {
    const afterMirror = mirrorSwap(v);
    const afterShift = mirrorShift(afterMirror, phi);
    const afterRefactor = refactorAlign(afterShift);
    return { afterMirror, afterShift, afterRefactor };
  }

  /** Get the configuration. */
  getConfig(): BraidConfig {
    return { ...this.config };
  }
}

// ═══════════════════════════════════════════════════════════════
// All 9 Braid States (static reference)
// ═══════════════════════════════════════════════════════════════

/**
 * The complete 9-state governance table.
 * Each entry maps a dual ternary (primary, mirror) pair to its
 * trust level and security action.
 */
export const BRAID_GOVERNANCE_TABLE: ReadonlyArray<BraidGovernance> = [
  buildGovernance(1, 1),    // RESONANT_LOCK
  buildGovernance(1, 0),    // FORWARD_THRUST
  buildGovernance(1, -1),   // CREATIVE_TENSION_A
  buildGovernance(0, 1),    // PERPENDICULAR_POS
  buildGovernance(0, 0),    // ZERO_GRAVITY
  buildGovernance(0, -1),   // PERPENDICULAR_NEG
  buildGovernance(-1, 1),   // CREATIVE_TENSION_B
  buildGovernance(-1, 0),   // BACKWARD_CHECK
  buildGovernance(-1, -1),  // COLLAPSE_ATTRACTOR
];
