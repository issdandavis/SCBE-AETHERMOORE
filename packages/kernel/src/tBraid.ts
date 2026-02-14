/**
 * @file tBraid.ts
 * @module harmonic/tBraid
 * @layer Layer 6, Layer 11, Layer 12
 * @component T-Braiding Temporal Lattice (Tetradic)
 * @version 3.2.5
 *
 * Formalizes the braiding of multiple temporal variants through a shared meta-T.
 * Each variant of T is modified by a different dependency:
 *
 *   Ti = T · intent        (Immediate: goal-aligned scaling)
 *   Tm = T^t               (Memory: exponential time weighting)
 *   Tg = T · context       (Governance: system context scaling)
 *   Tp = T / t             (Predictive: forecast inverse — future uncertainty)
 *
 * Triadic braided meta-time (3 strands):
 *   T_b3 = Ti · Tm · Tg = T^(t+2) · intent · context
 *
 * Tetradic braided meta-time (4 strands):
 *   T_b4 = Ti · Tm · Tg · Tp = T^(t+3) · intent · context / t
 *
 * Braided distance (tetradic closure in Poincaré ball):
 *   d_b = Σ d_H(Vi, Vj)  for all i < j
 *   Triadic:  3 pairwise distances (triangle)
 *   Tetradic: 6 pairwise distances (tetrahedron)
 *
 * Security cost:
 *   H_braid(d_b, R, x) = R^(d_b² · x)
 *
 * Yang-Baxter invariant:
 *   σ_i σ_{i+1} σ_i = σ_{i+1} σ_i σ_{i+1}
 *   Swapping adjacent temporal strands preserves braided distance.
 *
 * An adversary must maintain consistency across ALL edges simultaneously.
 * Any inconsistency between timescales increases d_b → exponential cost.
 *
 * "T is not one clock. It is a braid of clocks,
 *  and pulling one strand tightens them all."
 */

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

/** Harmonic ratio (perfect fifth) — from temporalIntent */
const R_HARMONIC = 1.5;

/** Golden ratio φ for harmonic exponents */
const PHI = (1 + Math.sqrt(5)) / 2;

/** Numerical stability epsilon */
const EPSILON = 1e-10;

/** Maximum exponent for T^t to prevent overflow */
const MAX_TEMPORAL_EXPONENT = 20;

/** Compression factor for tanh projection into Poincaré ball */
const DEFAULT_ALPHA = 0.15;

// ═══════════════════════════════════════════════════════════════
// Braid Variant Types
// ═══════════════════════════════════════════════════════════════

/** The 4 temporal variant types in the tetradic braid */
export enum BraidVariant {
  /** Ti = T · intent — immediate, goal-aligned */
  IMMEDIATE = 'immediate',
  /** Tm = T^t — memory, exponential time weighting */
  MEMORY = 'memory',
  /** Tg = T · context — governance, system context */
  GOVERNANCE = 'governance',
  /** Tp = T / t — predictive, forecast inverse */
  PREDICTIVE = 'predictive',
}

/** All 4 variants in canonical order (strand ordering) */
export const STRAND_ORDER: readonly BraidVariant[] = [
  BraidVariant.IMMEDIATE,
  BraidVariant.MEMORY,
  BraidVariant.GOVERNANCE,
  BraidVariant.PREDICTIVE,
] as const;

/** Raw temporal variant values before Poincaré projection */
export interface BraidVariants {
  /** Ti = T · intent */
  immediate: number;
  /** Tm = T^t */
  memory: number;
  /** Tg = T · context */
  governance: number;
  /** Tp = T / t (predictive inverse) */
  predictive: number;
}

/** Projected variant values inside Poincaré ball (-1, 1) */
export interface ProjectedVariants {
  immediate: number;
  memory: number;
  governance: number;
  predictive: number;
}

/** A single pairwise edge in the braid lattice */
export interface BraidEdge {
  from: BraidVariant;
  to: BraidVariant;
  distance: number;
}

/** Full result of braid computation */
export interface BraidResult {
  /** Raw temporal variants */
  variants: BraidVariants;
  /** Projected into Poincaré ball */
  projected: ProjectedVariants;
  /** All pairwise hyperbolic distances (6 edges for tetradic) */
  edges: BraidEdge[];
  /** Braided distance d_b = sum of pairwise distances */
  braidedDistance: number;
  /** Braided meta-time T_b */
  braidedMetaTime: number;
  /** H_braid security cost */
  hBraid: number;
  /** Harm score: 1 / (1 + log(max(1, H_braid))) */
  harmScore: number;
  /** Whether Yang-Baxter consistency holds (within tolerance) */
  yangBaxterConsistent: boolean;
}

// ═══════════════════════════════════════════════════════════════
// Core Functions
// ═══════════════════════════════════════════════════════════════

/**
 * Compute raw temporal variants from base T and dependencies.
 *
 * @param T — Base time constant (abstract step counter)
 * @param intent — Intent alignment factor (0 = no intent, 1+ = increasing goal)
 * @param context — System context factor (governance weight)
 * @param t — Temporal exponent (time parameter for memory/prediction)
 */
export function computeVariants(
  T: number,
  intent: number,
  context: number,
  t: number
): BraidVariants {
  // Clamp T to positive
  const safeT = Math.max(EPSILON, Math.abs(T));
  const safeT2 = Math.max(EPSILON, Math.abs(t));

  return {
    immediate: safeT * Math.max(0, intent),
    memory: Math.pow(safeT, Math.min(safeT2, MAX_TEMPORAL_EXPONENT)),
    governance: safeT * Math.max(0, context),
    predictive: safeT / safeT2,
  };
}

/**
 * Project a scalar value into the Poincaré ball (-1, 1) via tanh.
 *
 * Maps ℝ → (-1, 1) smoothly. The compression factor α controls
 * how quickly values approach the boundary:
 *   - Small α (0.05): gentle compression, more resolution near center
 *   - Large α (0.5): aggressive compression, values cluster near boundary
 *
 * @param value — Raw scalar value
 * @param alpha — Compression factor (default 0.15)
 */
export function projectScalar(value: number, alpha: number = DEFAULT_ALPHA): number {
  return Math.tanh(alpha * value);
}

/**
 * Project all 4 variants into the Poincaré ball.
 */
export function projectVariants(
  variants: BraidVariants,
  alpha: number = DEFAULT_ALPHA
): ProjectedVariants {
  return {
    immediate: projectScalar(variants.immediate, alpha),
    memory: projectScalar(variants.memory, alpha),
    governance: projectScalar(variants.governance, alpha),
    predictive: projectScalar(variants.predictive, alpha),
  };
}

/**
 * 1D Poincaré hyperbolic distance between two scalars in (-1, 1).
 *
 * d_H(a, b) = arcosh(1 + 2(a-b)² / ((1-a²)(1-b²)))
 *
 * This is the restriction of the full Poincaré ball metric to 1D.
 * For identical points, returns ≈0 (subject to floating-point epsilon).
 */
export function hyperbolicDistance1D(a: number, b: number): number {
  const diff = a - b;
  const factorA = Math.max(EPSILON, 1 - a * a);
  const factorB = Math.max(EPSILON, 1 - b * b);
  const arg = 1 + (2 * diff * diff) / (factorA * factorB);
  return Math.acosh(Math.max(1, arg));
}

/**
 * Compute all pairwise hyperbolic distances between projected variants.
 *
 * For tetradic (4 variants): C(4,2) = 6 edges forming a tetrahedron.
 * For triadic (3 variants): C(3,2) = 3 edges forming a triangle.
 *
 * Returns edges sorted by the canonical strand ordering.
 */
export function computePairwiseDistances(projected: ProjectedVariants): BraidEdge[] {
  const values: [BraidVariant, number][] = [
    [BraidVariant.IMMEDIATE, projected.immediate],
    [BraidVariant.MEMORY, projected.memory],
    [BraidVariant.GOVERNANCE, projected.governance],
    [BraidVariant.PREDICTIVE, projected.predictive],
  ];

  const edges: BraidEdge[] = [];
  for (let i = 0; i < values.length; i++) {
    for (let j = i + 1; j < values.length; j++) {
      edges.push({
        from: values[i][0],
        to: values[j][0],
        distance: hyperbolicDistance1D(values[i][1], values[j][1]),
      });
    }
  }
  return edges;
}

/**
 * Compute braided distance d_b: sum of all pairwise hyperbolic distances.
 *
 * Triadic closure uses 3 edges; tetradic closure uses 6.
 * Higher d_b = more inconsistency between temporal variants = higher risk.
 */
export function braidedDistance(edges: BraidEdge[]): number {
  let sum = 0;
  for (const edge of edges) {
    sum += edge.distance;
  }
  return sum;
}

/**
 * Compute triadic braided distance using only the 3 core variants.
 * Excludes the predictive variant (original triangle formulation).
 */
export function triadicBraidedDistance(projected: ProjectedVariants): number {
  const d_im = hyperbolicDistance1D(projected.immediate, projected.memory);
  const d_mg = hyperbolicDistance1D(projected.memory, projected.governance);
  const d_gi = hyperbolicDistance1D(projected.governance, projected.immediate);
  return d_im + d_mg + d_gi;
}

/**
 * Compute braided meta-time T_b.
 *
 * Triadic:  T_b = Ti · Tm · Tg = T^(t+2) · intent · context
 * Tetradic: T_b = Ti · Tm · Tg · Tp = T^(t+3) · intent · context / t
 *
 * @param variants — Raw temporal variants
 * @param tetradic — If true, include predictive strand (default true)
 */
export function braidedMetaTime(
  variants: BraidVariants,
  tetradic: boolean = true
): number {
  const triadic = variants.immediate * variants.memory * variants.governance;
  return tetradic ? triadic * variants.predictive : triadic;
}

// ═══════════════════════════════════════════════════════════════
// Security Cost
// ═══════════════════════════════════════════════════════════════

/**
 * Braided harmonic wall: H_braid(d_b, R, x) = R^(d_b² · x)
 *
 * Uses the braided distance instead of single-point distance.
 * Since d_b is a sum of pairwise distances, it grows faster than
 * single-point d — making adversarial cost compound across timescales.
 *
 * @param dBraid — Braided distance (sum of pairwise hyperbolic distances)
 * @param x — Intent persistence factor (from computeXFactor)
 * @param R — Harmonic ratio (default 1.5)
 */
export function harmonicWallBraid(
  dBraid: number,
  x: number = 1.0,
  R: number = R_HARMONIC
): number {
  const exponent = dBraid * dBraid * x;
  // Cap exponent to prevent Infinity (log-safe up to ~700 for doubles)
  if (exponent > 500) return Number.MAX_VALUE;
  return Math.pow(R, exponent);
}

/**
 * Braided harm score: 1 / (1 + log(max(1, H_braid)))
 *
 * Inverts the wall so higher = safer, matching the kernel's convention.
 */
export function braidHarmScore(hBraid: number): number {
  if (!isFinite(hBraid) || hBraid >= Number.MAX_VALUE) return 0;
  return 1.0 / (1.0 + Math.log(Math.max(1.0, hBraid)));
}

// ═══════════════════════════════════════════════════════════════
// Yang-Baxter Consistency Check
// ═══════════════════════════════════════════════════════════════

/**
 * Apply a braid group generator σ_i: swap strands i and i+1.
 * Returns a new array with the swap applied.
 */
export function applyGenerator(values: number[], i: number): number[] {
  if (i < 0 || i >= values.length - 1) return [...values];
  const result = [...values];
  const temp = result[i];
  result[i] = result[i + 1];
  result[i + 1] = temp;
  return result;
}

/**
 * Compute total pairwise distance for an ordered set of scalars.
 * Used to check Yang-Baxter invariance.
 */
function totalPairwiseDistance(values: number[]): number {
  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    for (let j = i + 1; j < values.length; j++) {
      sum += hyperbolicDistance1D(values[i], values[j]);
    }
  }
  return sum;
}

/**
 * Check Yang-Baxter consistency: σ_i σ_{i+1} σ_i = σ_{i+1} σ_i σ_{i+1}
 *
 * For our scalar braid, this means: the braided distance is invariant
 * under the Yang-Baxter relation (reordering preserves total pairwise distance).
 *
 * This is automatically true for unweighted pairwise sums (since the sum
 * of all C(n,2) pairwise distances is permutation-invariant). The check
 * verifies this numerically, catching implementation bugs.
 *
 * @param projected — Projected variant values
 * @param tolerance — Numerical tolerance (default 1e-8)
 */
export function checkYangBaxter(
  projected: ProjectedVariants,
  tolerance: number = 1e-8
): boolean {
  const vals = [
    projected.immediate,
    projected.memory,
    projected.governance,
    projected.predictive,
  ];

  // Check: σ_1 σ_2 σ_1 vs σ_2 σ_1 σ_2
  const lhs = applyGenerator(applyGenerator(applyGenerator(vals, 0), 1), 0);
  const rhs = applyGenerator(applyGenerator(applyGenerator(vals, 1), 0), 1);

  const dLHS = totalPairwiseDistance(lhs);
  const dRHS = totalPairwiseDistance(rhs);

  return Math.abs(dLHS - dRHS) < tolerance;
}

// ═══════════════════════════════════════════════════════════════
// Full Braid Pipeline
// ═══════════════════════════════════════════════════════════════

/**
 * Compute the full T-braid from raw parameters.
 *
 * Pipeline: variants → project → pairwise distances → d_b → H_braid → harm
 *
 * @param T — Base time constant
 * @param intent — Intent alignment factor
 * @param context — System context factor
 * @param t — Temporal exponent
 * @param x — Intent persistence factor for H_eff (default 1.0)
 * @param alpha — Poincaré projection compression (default 0.15)
 * @param R — Harmonic ratio (default 1.5)
 */
export function computeBraid(
  T: number,
  intent: number,
  context: number,
  t: number,
  x: number = 1.0,
  alpha: number = DEFAULT_ALPHA,
  R: number = R_HARMONIC
): BraidResult {
  const variants = computeVariants(T, intent, context, t);
  const projected = projectVariants(variants, alpha);
  const edges = computePairwiseDistances(projected);
  const dBraid = braidedDistance(edges);
  const tBraid = braidedMetaTime(variants);
  const hBraid = harmonicWallBraid(dBraid, x, R);
  const harmScore = braidHarmScore(hBraid);
  const yb = checkYangBaxter(projected);

  return {
    variants,
    projected,
    edges,
    braidedDistance: dBraid,
    braidedMetaTime: tBraid,
    hBraid,
    harmScore,
    yangBaxterConsistent: yb,
  };
}

// ═══════════════════════════════════════════════════════════════
// Integration with Multi-Clock System
// ═══════════════════════════════════════════════════════════════

/**
 * Extract braid variants from a multi-clock state snapshot.
 *
 * Maps the 5 T-phase clocks to the 4 braid strands:
 *   FAST → immediate (intent = accumulated intent)
 *   MEMORY → memory (t = tick count, exponential weighting)
 *   GOVERNANCE → governance (context = accumulated intent)
 *   CIRCADIAN → provides the base T (breathing factor)
 *
 * The predictive strand is derived as T / t_memory.
 *
 * @param fastIntent — FAST clock accumulated intent
 * @param memoryTick — MEMORY clock tick count
 * @param memoryIntent — MEMORY clock accumulated intent
 * @param govIntent — GOVERNANCE clock accumulated intent
 * @param breathingFactor — CIRCADIAN breathing factor (used as base T)
 */
export function variantsFromClocks(
  fastIntent: number,
  memoryTick: number,
  memoryIntent: number,
  govIntent: number,
  breathingFactor: number = 1.0
): BraidVariants {
  const T = Math.max(EPSILON, breathingFactor);
  const t = Math.max(1, memoryTick);

  return computeVariants(
    T,
    fastIntent,      // intent = fast clock's accumulated intent
    govIntent,        // context = governance clock's accumulated intent
    t                 // t = memory clock's tick count
  );
}

/**
 * Compute braided distance from multi-clock state.
 * Convenience wrapper for integration with temporalPhase.ts.
 */
export function braidFromClocks(
  fastIntent: number,
  memoryTick: number,
  memoryIntent: number,
  govIntent: number,
  breathingFactor: number = 1.0,
  x: number = 1.0,
  alpha: number = DEFAULT_ALPHA
): BraidResult {
  const variants = variantsFromClocks(
    fastIntent, memoryTick, memoryIntent, govIntent, breathingFactor
  );
  const projected = projectVariants(variants, alpha);
  const edges = computePairwiseDistances(projected);
  const dBraid = braidedDistance(edges);
  const tBraid = braidedMetaTime(variants);
  const hBraid = harmonicWallBraid(dBraid, x);
  const harmScore = braidHarmScore(hBraid);
  const yb = checkYangBaxter(projected);

  return {
    variants,
    projected,
    edges,
    braidedDistance: dBraid,
    braidedMetaTime: tBraid,
    hBraid,
    harmScore,
    yangBaxterConsistent: yb,
  };
}

// ═══════════════════════════════════════════════════════════════
// Weighted Braided Distance (Golden-Ratio Edge Weights)
// ═══════════════════════════════════════════════════════════════

/**
 * Edge weight assignments for the tetradic braid.
 *
 * The 6 edges are weighted by proximity in the governance hierarchy:
 *   immediate ↔ memory:     φ^0 = 1.000  (adjacent, fast coupling)
 *   memory ↔ governance:    φ^0 = 1.000  (adjacent, medium coupling)
 *   governance ↔ predictive: φ^0 = 1.000  (adjacent, slow coupling)
 *   immediate ↔ governance:  φ^(-1) = 0.618  (skip-1, weaker tie)
 *   memory ↔ predictive:     φ^(-1) = 0.618  (skip-1, weaker tie)
 *   immediate ↔ predictive:  φ^(-2) = 0.382  (skip-2, weakest tie)
 *
 * Adjacent strands are tightly coupled; distant strands less so.
 * This mirrors braid group structure where σ_i and σ_j commute for |i-j| ≥ 2.
 */
export const EDGE_WEIGHTS: Record<string, number> = {
  'immediate-memory': 1.0,
  'memory-governance': 1.0,
  'governance-predictive': 1.0,
  'immediate-governance': 1 / PHI,
  'memory-predictive': 1 / PHI,
  'immediate-predictive': 1 / (PHI * PHI),
};

/**
 * Get the weight for an edge between two variants.
 */
export function edgeWeight(from: BraidVariant, to: BraidVariant): number {
  const key1 = `${from}-${to}`;
  const key2 = `${to}-${from}`;
  return EDGE_WEIGHTS[key1] ?? EDGE_WEIGHTS[key2] ?? 1.0;
}

/**
 * Compute weighted braided distance using golden-ratio edge weights.
 *
 * d_bw = Σ w_ij · d_H(Vi, Vj)  for all i < j
 *
 * Adjacent strands (w=1) dominate; distant strands (w=φ^-2≈0.38)
 * contribute less, reflecting braid group commutativity relations.
 */
export function weightedBraidedDistance(edges: BraidEdge[]): number {
  let sum = 0;
  for (const edge of edges) {
    const w = edgeWeight(edge.from, edge.to);
    sum += w * edge.distance;
  }
  return sum;
}
