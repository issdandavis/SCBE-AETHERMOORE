/**
 * @file asymmetricMovement.ts
 * @module fleet/asymmetric-movement
 * @layer Layer 5, Layer 8, Layer 13
 * @component Asymmetric Movement Model — Human vs AI Navigation
 * @version 3.2.4
 *
 * Formalises the fundamental asymmetry between human and AI movement
 * in the 6D Poincaré ball governance space.
 *
 * ─── THE INSIGHT ─────────────────────────────────────────────
 * Humans move in a 2D planar submanifold (left/right, forward/back).
 * AI agents move in the full 6D hyperbolic space — including the
 * "vertical" trust/governance depth axis that humans cannot reach.
 *
 * This is not a limitation — it's complementarity:
 *   • Humans provide LATERAL coverage (breadth, context, judgment)
 *   • AI provides VERTICAL coverage (depth, speed, parallelism)
 *   • Together they span the full manifold
 *
 * ─── COST MODEL ──────────────────────────────────────────────
 * AI movement cost:    C_ai(d)  = H_eff(d, R, x) = 1/(1+d+2pd(1-x/R))
 *   → exponential in all 6 dimensions, but reachable
 *
 * Human movement cost: C_human(d_lateral, d_vertical)
 *   → low/free in lateral plane (physical space, decisions)
 *   → infinite in vertical axis (cannot change trust tier directly)
 *   → humans DELEGATE vertical movement to AI
 *
 * ─── FLEET PAIRING ───────────────────────────────────────────
 * Every fleet unit pairs a human operator (2D) with AI agents (6D).
 * The human sets direction and intent; the AI navigates depth.
 * Quorum requires both: human lateral OK + AI vertical OK.
 */

import type { Lang, Voxel6, Decision } from '../harmonic/scbe_voxel_types.js';

// ═══════════════════════════════════════════════════════════════
// Movement Spaces
// ═══════════════════════════════════════════════════════════════

/** 2D lateral vector — human navigation plane */
export type Lateral2D = [number, number];

/** 3D physical vector — human spatial position */
export type Physical3D = [number, number, number];

/** 6D Poincaré ball vector — AI governance position */
export type Hyperbolic6D = Voxel6;

/**
 * Movement axes classified by accessibility.
 *
 * LATERAL (human-accessible):
 *   X — left/right (spatial or decision branch)
 *   Y — forward/back (temporal or progress)
 *
 * VERTICAL (AI-exclusive):
 *   Z — trust depth (governance tier: closer to origin = more trusted)
 *   V — coherence phase (spectral alignment)
 *   P — policy tension (constraint field pressure)
 *   S — stability index (entropic state)
 */
export const AXIS_LABELS = ['X', 'Y', 'Z', 'V', 'P', 'S'] as const;
export type AxisLabel = (typeof AXIS_LABELS)[number];

export const LATERAL_AXES: readonly AxisLabel[] = ['X', 'Y'];
export const VERTICAL_AXES: readonly AxisLabel[] = ['Z', 'V', 'P', 'S'];

/** Sacred Tongue → primary axis mapping */
export const TONGUE_AXIS: Record<Lang, AxisLabel> = {
  KO: 'X',  // flow orientation → lateral
  AV: 'Y',  // boundary condition → lateral
  RU: 'Z',  // constraint field → vertical (trust depth)
  CA: 'V',  // active operator → vertical (coherence)
  UM: 'P',  // entropic sink → vertical (policy)
  DR: 'S',  // structural tensor → vertical (stability)
};

// ═══════════════════════════════════════════════════════════════
// Agent Type Classification
// ═══════════════════════════════════════════════════════════════

export type AgentKind = 'HUMAN' | 'AI' | 'HYBRID';

/**
 * Movement capabilities per agent kind.
 *
 * HUMAN:
 *   - lateralDims = 2 (X, Y — physical plane)
 *   - verticalDims = 0 (cannot directly navigate depth)
 *   - maxParallel = 1 (serial attention: "1 head, 2 hands")
 *   - depthDelegate = true (must delegate vertical to AI)
 *
 * AI:
 *   - lateralDims = 2 (same X, Y access)
 *   - verticalDims = 4 (Z, V, P, S — full depth access)
 *   - maxParallel = 6 (one per tongue, simultaneous)
 *   - depthDelegate = false (navigates depth directly)
 *
 * HYBRID (human + AI pair):
 *   - Covers all 6 dimensions
 *   - Human lateral judgment + AI depth navigation
 */
export interface MovementCapability {
  kind: AgentKind;
  lateralDims: number;
  verticalDims: number;
  maxParallel: number;
  depthDelegate: boolean;
}

export const HUMAN_CAPABILITY: MovementCapability = {
  kind: 'HUMAN',
  lateralDims: 2,
  verticalDims: 0,
  maxParallel: 1,
  depthDelegate: true,
};

export const AI_CAPABILITY: MovementCapability = {
  kind: 'AI',
  lateralDims: 2,
  verticalDims: 4,
  maxParallel: 6,
  depthDelegate: false,
};

export const HYBRID_CAPABILITY: MovementCapability = {
  kind: 'HYBRID',
  lateralDims: 2,
  verticalDims: 4,
  maxParallel: 6,
  depthDelegate: false,
};

// ═══════════════════════════════════════════════════════════════
// Cost Functions
// ═══════════════════════════════════════════════════════════════

/** Squared Euclidean norm */
function norm2(v: number[]): number {
  let s = 0;
  for (let i = 0; i < v.length; i++) s += v[i] * v[i];
  return s;
}

/** Euclidean norm */
function norm(v: number[]): number {
  return Math.sqrt(norm2(v));
}

/**
 * AI movement cost in the full 6D Poincaré ball.
 *
 * Uses the standard SCBE harmonic effective cost:
 *   H_eff = 1 / (1 + d + 2pd(1 - x/R))
 *
 * where d is hyperbolic distance, p is phase deviation, x is coherence,
 * R is adaptive scaling radius.
 *
 * Returns cost ∈ (0, 1] — lower means more expensive movement.
 */
export function aiMovementCost(
  from: Hyperbolic6D,
  to: Hyperbolic6D,
  coherence: number,
  R: number = 1.5,
): number {
  // Hyperbolic distance in Poincaré ball
  const delta: number[] = [];
  for (let i = 0; i < 6; i++) delta.push(to[i] - from[i]);
  const fromNorm2 = norm2(Array.from(from));
  const toNorm2 = norm2(Array.from(to));
  const deltaNorm2 = norm2(delta);

  // Poincaré distance: d_H = acosh(1 + 2|u-v|² / ((1-|u|²)(1-|v|²)))
  const denom = Math.max((1 - fromNorm2) * (1 - toNorm2), 1e-12);
  const arg = 1 + 2 * deltaNorm2 / denom;
  const d = Math.acosh(Math.max(arg, 1));

  // Phase deviation from coherence
  const p = 1 - Math.max(0, Math.min(1, coherence));

  // H_eff: bounded in (0, 1]
  const x = coherence;
  const hEff = 1 / (1 + d + 2 * p * d * (1 - x / R));
  return hEff;
}

/**
 * Human movement cost — asymmetric by dimension.
 *
 * Lateral (X, Y): Low cost — humans navigate physical/decision space easily.
 *   C_lateral = |delta_xy| (linear, cheap)
 *
 * Vertical (Z, V, P, S): Infinite cost — humans cannot directly change
 * trust depth, coherence phase, policy tension, or stability index.
 *   C_vertical = Infinity if any vertical component changed
 *
 * Returns { lateral, vertical, total, reachable }
 */
export function humanMovementCost(
  from: Hyperbolic6D,
  to: Hyperbolic6D,
): { lateral: number; vertical: number; total: number; reachable: boolean } {
  // Lateral displacement (X, Y) — first 2 dims
  const dLat = Math.sqrt((to[0] - from[0]) ** 2 + (to[1] - from[1]) ** 2);

  // Vertical displacement (Z, V, P, S) — last 4 dims
  let dVert = 0;
  for (let i = 2; i < 6; i++) dVert += (to[i] - from[i]) ** 2;
  dVert = Math.sqrt(dVert);

  const hasVerticalMovement = dVert > 1e-9;
  return {
    lateral: dLat,
    vertical: hasVerticalMovement ? Infinity : 0,
    total: hasVerticalMovement ? Infinity : dLat,
    reachable: !hasVerticalMovement,
  };
}

// ═══════════════════════════════════════════════════════════════
// Fleet Unit (Human + AI pairing)
// ═══════════════════════════════════════════════════════════════

/** Human operator state — 2D lateral position + authority */
export interface HumanState {
  id: string;
  /** Lateral position in the X-Y plane */
  lateral: Lateral2D;
  /** Physical 3D position (for physical fleet units) */
  physical: Physical3D;
  /** Authorization tier — determines which vertical depths AI can reach */
  authTier: Lang;
  /** Attention budget ∈ (0, 1] — models serial human processing */
  attention: number;
  /** Decision latency in ms — humans are slower but wiser */
  latencyMs: number;
}

/** AI agent state — full 6D hyperbolic position */
export interface AIState {
  id: string;
  /** Full 6D position in Poincaré ball */
  position: Hyperbolic6D;
  /** NK coherence ∈ [0, 1] */
  coherence: number;
  /** Current active tongue (which depth dimension is primary) */
  activeTongue: Lang;
  /** Number of parallel depth probes active */
  activeProbes: number;
}

/**
 * FleetUnit — the fundamental human-AI pairing.
 *
 * One human (lateral) + one or more AI agents (vertical).
 * The human provides direction, the AI navigates depth.
 * Together they cover the full 6D manifold.
 */
export interface FleetUnit {
  unitId: string;
  human: HumanState;
  agents: AIState[];
  /** Combined 6D position (human lateral + AI vertical median) */
  compositePosition: Hyperbolic6D;
  /** Last decision from composite evaluation */
  decision: Decision;
}

/**
 * Compute the composite 6D position for a fleet unit.
 *
 * Lateral dims (X, Y): taken from the human's lateral position.
 * Vertical dims (Z, V, P, S): median of all AI agent positions.
 *
 * This ensures:
 *   - Human controls direction (where to go)
 *   - AI consensus controls depth (how deep to go)
 *   - No single AI can drag the unit to an unsafe depth
 */
export function compositePosition(unit: FleetUnit): Hyperbolic6D {
  const { human, agents } = unit;

  if (agents.length === 0) {
    // Human alone — stays on the lateral plane (vertical = 0)
    return [human.lateral[0], human.lateral[1], 0, 0, 0, 0];
  }

  // Lateral from human
  const x = human.lateral[0];
  const y = human.lateral[1];

  // Vertical from AI median (robust to single outlier)
  const medians: number[] = [];
  for (let dim = 2; dim < 6; dim++) {
    const vals = agents.map((a) => a.position[dim]).sort((a, b) => a - b);
    const mid = Math.floor(vals.length / 2);
    const median =
      vals.length % 2 === 0 ? (vals[mid - 1] + vals[mid]) / 2 : vals[mid];
    medians.push(median);
  }

  return [x, y, medians[0], medians[1], medians[2], medians[3]];
}

// ═══════════════════════════════════════════════════════════════
// Movement Validation
// ═══════════════════════════════════════════════════════════════

/** Result of a movement validation check */
export interface MovementCheck {
  /** Is this movement allowed? */
  allowed: boolean;
  /** Human lateral movement cost */
  humanCost: number;
  /** AI vertical movement cost (H_eff) */
  aiCost: number;
  /** Which dimensions were moved */
  movedAxes: AxisLabel[];
  /** Reason for denial (if any) */
  reason?: string;
}

/**
 * Validate a proposed movement for a fleet unit.
 *
 * Rules:
 * 1. Human can only propose lateral changes (X, Y)
 * 2. AI agents can move in any dimension
 * 3. Vertical movement requires AI consensus (median)
 * 4. Human authTier limits maximum vertical depth:
 *    KO = shallowest (most restricted), DR = deepest (most trusted)
 * 5. AI movement cost must stay above decision threshold
 */
export function validateMovement(
  unit: FleetUnit,
  proposedPosition: Hyperbolic6D,
  proposer: 'HUMAN' | 'AI',
): MovementCheck {
  const current = unit.compositePosition;
  const movedAxes: AxisLabel[] = [];

  for (let i = 0; i < 6; i++) {
    if (Math.abs(proposedPosition[i] - current[i]) > 1e-9) {
      movedAxes.push(AXIS_LABELS[i]);
    }
  }

  // Check human constraints
  if (proposer === 'HUMAN') {
    const verticalMoved = movedAxes.filter((a) =>
      (VERTICAL_AXES as readonly string[]).includes(a),
    );
    if (verticalMoved.length > 0) {
      return {
        allowed: false,
        humanCost: Infinity,
        aiCost: 0,
        movedAxes,
        reason: `Human cannot move vertical axes: ${verticalMoved.join(', ')}. Delegate to AI.`,
      };
    }
  }

  // Human lateral cost
  const hCost = humanMovementCost(current, proposedPosition);

  // AI vertical cost (use median coherence)
  const medianCoherence =
    unit.agents.length > 0
      ? unit.agents
          .map((a) => a.coherence)
          .sort((a, b) => a - b)
          [Math.floor(unit.agents.length / 2)]
      : 0;

  const aiCost = aiMovementCost(current, proposedPosition, medianCoherence);

  // Depth limit based on human auth tier
  const tierDepthLimit = authTierDepthLimit(unit.human.authTier);
  const proposedDepth = norm(Array.from(proposedPosition).slice(2));
  if (proposedDepth > tierDepthLimit) {
    return {
      allowed: false,
      humanCost: hCost.lateral,
      aiCost,
      movedAxes,
      reason: `Vertical depth ${proposedDepth.toFixed(3)} exceeds auth tier ${unit.human.authTier} limit ${tierDepthLimit.toFixed(3)}`,
    };
  }

  // AI cost check — if H_eff too low, movement is too expensive
  if (aiCost < 0.05) {
    return {
      allowed: false,
      humanCost: hCost.lateral,
      aiCost,
      movedAxes,
      reason: `AI movement cost too high (H_eff=${aiCost.toFixed(4)} < 0.05). Target is adversarially far.`,
    };
  }

  return {
    allowed: true,
    humanCost: hCost.lateral,
    aiCost,
    movedAxes,
  };
}

/**
 * Maximum vertical depth allowed per human authorization tier.
 *
 * Lower tier (KO) = restricted to shallow depths (safe, supervised).
 * Higher tier (DR) = can authorize deep vertical movement (full trust).
 *
 * Values are Poincaré ball radii for the vertical subspace.
 */
export function authTierDepthLimit(tier: Lang): number {
  const limits: Record<Lang, number> = {
    KO: 0.3, // Flow — shallow, supervised
    AV: 0.5, // Boundary — moderate depth
    RU: 0.65, // Constraint — substantial depth
    CA: 0.8, // Operator — deep access
    UM: 0.9, // Entropic — near-full depth
    DR: 0.95, // Structural — maximum authorized depth
  };
  return limits[tier];
}

// ═══════════════════════════════════════════════════════════════
// Complementarity Score
// ═══════════════════════════════════════════════════════════════

/**
 * Compute how well a fleet unit's human and AI complement each other.
 *
 * Perfect complementarity = 1.0:
 *   - Human covers full lateral range
 *   - AI covers full vertical range
 *   - No blind spots in the 6D manifold
 *
 * Low complementarity < 0.5:
 *   - Human and AI are redundant (both in same subspace)
 *   - Or one side is inactive / low-coherence
 */
export function complementarityScore(unit: FleetUnit): number {
  if (unit.agents.length === 0) return 0;

  // Lateral coverage: human attention models their effective range
  const lateralCoverage = Math.min(1, unit.human.attention);

  // Vertical coverage: how many depth dimensions are actively probed?
  // Each AI agent with coherence > 0.3 contributes to coverage
  const activeAgents = unit.agents.filter((a) => a.coherence > 0.3);
  const uniqueTongues = new Set(activeAgents.map((a) => a.activeTongue));
  // 4 vertical dimensions possible
  const verticalCoverage = Math.min(1, uniqueTongues.size / 4);

  // Combined: geometric mean (both must be nonzero for good score)
  return Math.sqrt(lateralCoverage * verticalCoverage);
}

/**
 * Identify blind spots — which dimensions have no active navigator.
 */
export function blindSpots(unit: FleetUnit): AxisLabel[] {
  const covered = new Set<AxisLabel>();

  // Human covers lateral
  if (unit.human.attention > 0.1) {
    covered.add('X');
    covered.add('Y');
  }

  // AI covers vertical via active tongues
  for (const agent of unit.agents) {
    if (agent.coherence > 0.3) {
      covered.add(TONGUE_AXIS[agent.activeTongue]);
    }
  }

  return AXIS_LABELS.filter((a) => !covered.has(a));
}
