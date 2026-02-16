/**
 * @file sheafCohomology.ts
 * @module harmonic/sheafCohomology
 * @layer Layer 5, Layer 9, Layer 11, Layer 13
 * @component Tarski Sheaf Cohomology for Lattice Governance
 * @version 1.0.0
 * @since 2026-02-14
 *
 * Cellular sheaf cohomology valued in complete lattices, using the
 * Tarski fixed-point theorem for consensus detection and obstruction
 * measurement across SCBE governance networks.
 *
 * Theory:
 *   - Cellular sheaf F assigns a complete lattice F_σ to each cell σ
 *   - Galois connections (adjoint pairs) serve as restriction maps
 *   - Tarski Laplacian L₀ = meet-based diffusion on 0-cochains
 *   - TH⁰(X; F) = Fix(id ∧ L₀) = global sections = consensus
 *   - Harmonic flow Φ_t = (id ∧ L₀)^t converges in finite steps
 *     (Tarski fixed-point theorem on descending chains)
 *
 * SCBE integration:
 *   - Temporal complex: vertices = {immediate, memory, governance[, predictive]}
 *   - Edges = temporal braids (intent, context, forecast)
 *   - Stalks = 4-level risk lattice (ALLOW < QUARANTINE < ESCALATE < DENY)
 *   - Obstruction degree feeds into Layer 12 harmonic wall H(d,R)=R^(d²)
 *   - fail-to-noise when obstruction exceeds threshold
 *
 * References:
 *   - Ghrist & Hansen, "Toward a spectral theory of cellular sheaves" (2019)
 *   - Curry, "Sheaves, cosheaves and applications" (2014)
 *   - Tarski, "A lattice-theoretical fixpoint theorem" (1955)
 */

// ============================================================
// COMPLETE LATTICE INTERFACE
// ============================================================

/**
 * A finite complete lattice: poset with all meets (∧) and joins (∨),
 * including top (⊤) and bottom (⊥).
 */
export interface CompleteLattice<T> {
  /** Top element ⊤ (identity for meet) */
  top(): T;
  /** Bottom element ⊥ (identity for join) */
  bottom(): T;
  /** Meet: greatest lower bound (∧) */
  meet(a: T, b: T): T;
  /** Join: least upper bound (∨) */
  join(a: T, b: T): T;
  /** Partial order: a ≤ b */
  leq(a: T, b: T): boolean;
  /** Equality: a = b */
  eq(a: T, b: T): boolean;
  /** Enumerate all elements (finite lattice) */
  elements(): T[];
}

// ============================================================
// GALOIS CONNECTION
// ============================================================

/**
 * A Galois connection between lattices S and T:
 *   f♭ ⊣ f♯  iff  f♭(s) ≤_T t  ⟺  s ≤_S f♯(t)
 *
 * - Lower adjoint f♭: S → T preserves joins
 * - Upper adjoint f♯: T → S preserves meets
 */
export interface GaloisConnection<S, T> {
  /** Lower adjoint f♭: S → T (join-preserving) */
  lower(s: S): T;
  /** Upper adjoint f♯: T → S (meet-preserving) */
  upper(t: T): S;
}

/** Identity Galois connection (for constant sheaves) */
export function identityConnection<T>(): GaloisConnection<T, T> {
  return { lower: (s: T) => s, upper: (t: T) => t };
}

// ============================================================
// CELL COMPLEX (Graph-level, 1-skeleton)
// ============================================================

export interface CellVertex {
  id: string;
  label?: string;
}

export interface CellEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

export interface CellComplex {
  vertices: CellVertex[];
  edges: CellEdge[];
}

// ============================================================
// CELLULAR SHEAF
// ============================================================

/**
 * Cellular sheaf on a 1-complex (graph).
 *
 * Assigns a complete lattice to each vertex and edge,
 * with Galois connections as restriction maps.
 */
export interface CellularSheaf<V, E> {
  complex: CellComplex;
  /** Stalk lattice at vertex */
  vertexLattice(vertexId: string): CompleteLattice<V>;
  /** Stalk lattice at edge */
  edgeLattice(edgeId: string): CompleteLattice<E>;
  /** Galois connection: source vertex → edge */
  sourceRestriction(edgeId: string): GaloisConnection<V, E>;
  /** Galois connection: target vertex → edge */
  targetRestriction(edgeId: string): GaloisConnection<V, E>;
}

/** 0-cochain: assignment of values to vertices */
export type Cochain0<V> = Map<string, V>;

// ============================================================
// BUILT-IN LATTICES
// ============================================================

/** 4-level risk lattice: ALLOW < QUARANTINE < ESCALATE < DENY */
export enum RiskLevel {
  ALLOW = 0,
  QUARANTINE = 1,
  ESCALATE = 2,
  DENY = 3,
}

export const RISK_LATTICE: CompleteLattice<RiskLevel> = {
  top: () => RiskLevel.DENY,
  bottom: () => RiskLevel.ALLOW,
  meet: (a, b) => Math.min(a, b) as RiskLevel,
  join: (a, b) => Math.max(a, b) as RiskLevel,
  leq: (a, b) => a <= b,
  eq: (a, b) => a === b,
  elements: () => [
    RiskLevel.ALLOW,
    RiskLevel.QUARANTINE,
    RiskLevel.ESCALATE,
    RiskLevel.DENY,
  ],
};

/** Boolean lattice: {false, true} with false < true */
export const BOOLEAN_LATTICE: CompleteLattice<boolean> = {
  top: () => true,
  bottom: () => false,
  meet: (a, b) => a && b,
  join: (a, b) => a || b,
  leq: (a, b) => !a || b,
  eq: (a, b) => a === b,
  elements: () => [false, true],
};

/**
 * N-level interval lattice: {0, 1, ..., n-1} with linear order.
 * Useful for discretized trust scores or confidence levels.
 */
export function intervalLattice(n: number): CompleteLattice<number> {
  const max = Math.max(0, n - 1);
  return {
    top: () => max,
    bottom: () => 0,
    meet: (a, b) => Math.min(a, b),
    join: (a, b) => Math.max(a, b),
    leq: (a, b) => a <= b,
    eq: (a, b) => a === b,
    elements: () => Array.from({ length: n }, (_, i) => i),
  };
}

/**
 * Product lattice: L₁ × L₂ with componentwise meet/join.
 * Elements are [a, b] pairs.
 */
export function productLattice<A, B>(
  la: CompleteLattice<A>,
  lb: CompleteLattice<B>,
): CompleteLattice<[A, B]> {
  return {
    top: () => [la.top(), lb.top()],
    bottom: () => [la.bottom(), lb.bottom()],
    meet: (x, y) => [la.meet(x[0], y[0]), lb.meet(x[1], y[1])],
    join: (x, y) => [la.join(x[0], y[0]), lb.join(x[1], y[1])],
    leq: (x, y) => la.leq(x[0], y[0]) && lb.leq(x[1], y[1]),
    eq: (x, y) => la.eq(x[0], y[0]) && lb.eq(x[1], y[1]),
    elements: () => {
      const result: [A, B][] = [];
      for (const a of la.elements()) {
        for (const b of lb.elements()) {
          result.push([a, b]);
        }
      }
      return result;
    },
  };
}

// ============================================================
// TARSKI LAPLACIAN
// ============================================================

/**
 * Tarski Laplacian L₀ on 0-cochains (vertex assignments).
 *
 * For each vertex σ:
 *   (L₀ x)_σ = ∧_{τ ∈ cofaces(σ)} f♯_{σ≤τ}( ∧_{σ' ∈ faces(τ)} f♭_{σ'≤τ}(x_{σ'}) )
 *
 * For each edge τ containing σ:
 *   1. Push all endpoint values to edge stalk via lower adjoint f♭
 *   2. Meet them in the edge stalk
 *   3. Pull back to σ's stalk via upper adjoint f♯
 * Then meet all pulled-back values across all edges containing σ.
 */
export function tarskiLaplacian0<V, E>(
  sheaf: CellularSheaf<V, E>,
  cochain: Cochain0<V>,
): Cochain0<V> {
  const result: Cochain0<V> = new Map();

  for (const v of sheaf.complex.vertices) {
    const vLat = sheaf.vertexLattice(v.id);
    const cofaces = sheaf.complex.edges.filter(
      (e) => e.source === v.id || e.target === v.id,
    );

    if (cofaces.length === 0) {
      // Isolated vertex: L₀ returns ⊤ (neutral under meet with id)
      result.set(v.id, vLat.top());
      continue;
    }

    let accumulated = vLat.top();

    for (const edge of cofaces) {
      const eLat = sheaf.edgeLattice(edge.id);
      const srcRestr = sheaf.sourceRestriction(edge.id);
      const tgtRestr = sheaf.targetRestriction(edge.id);

      // Push both endpoints to edge stalk
      const srcVal = cochain.get(edge.source) ?? sheaf.vertexLattice(edge.source).bottom();
      const tgtVal = cochain.get(edge.target) ?? sheaf.vertexLattice(edge.target).bottom();
      const srcInEdge = srcRestr.lower(srcVal);
      const tgtInEdge = tgtRestr.lower(tgtVal);

      // Meet in edge stalk
      const edgeMeet = eLat.meet(srcInEdge, tgtInEdge);

      // Pull back via the appropriate upper adjoint
      const pulledBack =
        edge.source === v.id ? srcRestr.upper(edgeMeet) : tgtRestr.upper(edgeMeet);

      accumulated = vLat.meet(accumulated, pulledBack);
    }

    result.set(v.id, accumulated);
  }

  return result;
}

// ============================================================
// HARMONIC FLOW
// ============================================================

export interface HarmonicFlowResult<V> {
  /** Fixed point cochain (converged values) */
  fixedPoint: Cochain0<V>;
  /** Number of iterations to converge */
  iterations: number;
  /** Whether flow reached a true fixed point */
  converged: boolean;
}

/**
 * Single harmonic flow step: Φ(x) = x ∧ L₀(x).
 *
 * Monotonically non-increasing in the lattice order — each step
 * can only lower (or maintain) values, never raise them.
 */
export function harmonicFlowStep<V, E>(
  sheaf: CellularSheaf<V, E>,
  cochain: Cochain0<V>,
): Cochain0<V> {
  const lapl = tarskiLaplacian0(sheaf, cochain);
  const result: Cochain0<V> = new Map();

  for (const v of sheaf.complex.vertices) {
    const vLat = sheaf.vertexLattice(v.id);
    const cur = cochain.get(v.id) ?? vLat.bottom();
    const lap = lapl.get(v.id) ?? vLat.bottom();
    result.set(v.id, vLat.meet(cur, lap));
  }

  return result;
}

/**
 * Iterate harmonic flow Φ_t = (id ∧ L₀)^t until convergence.
 *
 * By Tarski's fixed-point theorem, the descending chain must
 * terminate in finitely many steps (for finite lattices).
 *
 * @param sheaf - cellular sheaf on graph
 * @param initial - starting 0-cochain
 * @param maxIterations - safety bound (default: 100)
 */
export function harmonicFlow<V, E>(
  sheaf: CellularSheaf<V, E>,
  initial: Cochain0<V>,
  maxIterations: number = 100,
): HarmonicFlowResult<V> {
  let current = new Map(initial);

  for (let t = 0; t < maxIterations; t++) {
    const next = harmonicFlowStep(sheaf, current);

    let converged = true;
    for (const v of sheaf.complex.vertices) {
      const vLat = sheaf.vertexLattice(v.id);
      const curVal = current.get(v.id) ?? vLat.bottom();
      const nextVal = next.get(v.id) ?? vLat.bottom();
      if (!vLat.eq(curVal, nextVal)) {
        converged = false;
        break;
      }
    }

    if (converged) {
      return { fixedPoint: current, iterations: t, converged: true };
    }

    current = next;
  }

  return { fixedPoint: current, iterations: maxIterations, converged: false };
}

// ============================================================
// GLOBAL SECTIONS  (TH⁰)
// ============================================================

/**
 * Compute global sections TH⁰(X; F) via Tarski descent.
 *
 * Starts from the top cochain (all ⊤) and flows down to the
 * greatest postfixpoint, which equals the global sections.
 *
 * Theorem: TH⁰(X; F) = Γ(X; F) (global sections functor).
 */
export function globalSections<V, E>(
  sheaf: CellularSheaf<V, E>,
  maxIterations: number = 100,
): HarmonicFlowResult<V> {
  const top: Cochain0<V> = new Map();
  for (const v of sheaf.complex.vertices) {
    top.set(v.id, sheaf.vertexLattice(v.id).top());
  }
  return harmonicFlow(sheaf, top, maxIterations);
}

// ============================================================
// OBSTRUCTION MEASUREMENT
// ============================================================

/**
 * Obstruction degree: quantifies how far an initial assignment
 * is from being a global section (consensus).
 *
 * Computed as normalized total "drop" during harmonic flow.
 *
 * @returns [0, 1] where 0 = perfect consensus, 1 = maximal disagreement
 */
export function obstructionDegree<V, E>(
  sheaf: CellularSheaf<V, E>,
  initial: Cochain0<V>,
): number {
  const { fixedPoint } = harmonicFlow(sheaf, initial);

  let totalDrop = 0;
  let vertexCount = 0;

  for (const v of sheaf.complex.vertices) {
    const lat = sheaf.vertexLattice(v.id);
    const elems = lat.elements();
    const maxRank = elems.length - 1;
    if (maxRank === 0) continue;

    const initVal = initial.get(v.id) ?? lat.bottom();
    const fixedVal = fixedPoint.get(v.id) ?? lat.bottom();

    const initRank = elems.findIndex((e) => lat.eq(e, initVal));
    const fixedRank = elems.findIndex((e) => lat.eq(e, fixedVal));

    totalDrop += Math.max(0, initRank - fixedRank) / maxRank;
    vertexCount++;
  }

  return vertexCount > 0 ? totalDrop / vertexCount : 0;
}

/**
 * Check if a 0-cochain is already a global section
 * (consistent across all edges without flow needed).
 */
export function isGlobalSection<V, E>(
  sheaf: CellularSheaf<V, E>,
  cochain: Cochain0<V>,
): boolean {
  const stepped = harmonicFlowStep(sheaf, cochain);
  for (const v of sheaf.complex.vertices) {
    const lat = sheaf.vertexLattice(v.id);
    const cur = cochain.get(v.id) ?? lat.bottom();
    const nxt = stepped.get(v.id) ?? lat.bottom();
    if (!lat.eq(cur, nxt)) return false;
  }
  return true;
}

// ============================================================
// SHEAF BUILDERS
// ============================================================

/**
 * Build a constant sheaf: same lattice L at every cell,
 * identity Galois connections everywhere.
 */
export function constantSheaf<T>(
  complex: CellComplex,
  lattice: CompleteLattice<T>,
): CellularSheaf<T, T> {
  const id = identityConnection<T>();
  return {
    complex,
    vertexLattice: () => lattice,
    edgeLattice: () => lattice,
    sourceRestriction: () => id,
    targetRestriction: () => id,
  };
}

// ============================================================
// SCBE TEMPORAL COMPLEX
// ============================================================

/** Temporal variant identifiers */
export type TemporalVariant = 'immediate' | 'memory' | 'governance' | 'predictive';

/**
 * Build cell complex from temporal variants.
 *
 * - triadic:  3 vertices + 3 edges (triangle)
 * - tetradic: 4 vertices + 6 edges (complete K₄)
 */
export function buildTemporalComplex(
  mode: 'triadic' | 'tetradic' = 'triadic',
): CellComplex {
  const vertices: CellVertex[] = [
    { id: 'immediate', label: 'T_i (Intent-dependent)' },
    { id: 'memory', label: 'T_m (Time-dependent, T^t)' },
    { id: 'governance', label: 'T_g (Context-dependent)' },
  ];

  const edges: CellEdge[] = [
    { id: 'im-mem', source: 'immediate', target: 'memory', label: 'Intent↔Memory braid' },
    { id: 'mem-gov', source: 'memory', target: 'governance', label: 'Memory↔Governance braid' },
    { id: 'gov-im', source: 'governance', target: 'immediate', label: 'Governance↔Intent braid' },
  ];

  if (mode === 'tetradic') {
    vertices.push({ id: 'predictive', label: 'T_p (Forecast, T/t)' });
    edges.push(
      { id: 'im-pred', source: 'immediate', target: 'predictive', label: 'Intent↔Forecast' },
      { id: 'mem-pred', source: 'memory', target: 'predictive', label: 'Memory↔Forecast' },
      {
        id: 'gov-pred',
        source: 'governance',
        target: 'predictive',
        label: 'Governance↔Forecast',
      },
    );
  }

  return { vertices, edges };
}

/**
 * Twist configuration for governance sheaf restriction maps.
 *
 * A twist on an edge adjusts the Galois connection to model
 * directional governance pressure:
 *   - raise > 0: lower adjoint escalates risk (push values up)
 *   - lower > 0: upper adjoint de-escalates (pull values down)
 *
 * Non-zero twist creates a non-constant (twisted) sheaf, which
 * can have non-trivial obstruction even when inputs are close.
 */
export interface EdgeTwist {
  /** How many risk levels f♭ raises (0 = identity) */
  raise: number;
  /** How many risk levels f♯ lowers (0 = identity) */
  lower: number;
}

/**
 * Build a governance sheaf over the temporal complex.
 *
 * Default (no twist): constant sheaf with identity restrictions.
 * With twist: restriction maps shift risk levels per edge,
 * modeling directional governance pressure between temporal variants.
 */
export function buildGovernanceSheaf(
  complex: CellComplex,
  twists?: Map<string, EdgeTwist>,
): CellularSheaf<RiskLevel, RiskLevel> {
  return {
    complex,
    vertexLattice: () => RISK_LATTICE,
    edgeLattice: () => RISK_LATTICE,
    sourceRestriction: (edgeId: string) => {
      const tw = twists?.get(edgeId);
      if (tw && (tw.raise !== 0 || tw.lower !== 0)) {
        return {
          lower: (v: RiskLevel) =>
            Math.min(RiskLevel.DENY, Math.max(RiskLevel.ALLOW, v + tw.raise)) as RiskLevel,
          upper: (e: RiskLevel) =>
            Math.max(RiskLevel.ALLOW, Math.min(RiskLevel.DENY, e - tw.lower)) as RiskLevel,
        };
      }
      return identityConnection<RiskLevel>();
    },
    targetRestriction: (edgeId: string) => {
      const tw = twists?.get(edgeId);
      if (tw && (tw.raise !== 0 || tw.lower !== 0)) {
        return {
          lower: (v: RiskLevel) =>
            Math.min(RiskLevel.DENY, Math.max(RiskLevel.ALLOW, v + tw.raise)) as RiskLevel,
          upper: (e: RiskLevel) =>
            Math.max(RiskLevel.ALLOW, Math.min(RiskLevel.DENY, e - tw.lower)) as RiskLevel,
        };
      }
      return identityConnection<RiskLevel>();
    },
  };
}

// ============================================================
// POLICY OBSTRUCTION DETECTION
// ============================================================

export interface PolicyObstructionResult {
  /** [0,1] obstruction: 0 = perfect consensus, 1 = maximal disagreement */
  obstruction: number;
  /** Risk level all variants converge to under harmonic flow (meet of fixed point) */
  consensus: RiskLevel;
  /** Fixed-point values for each temporal variant */
  fixedPoint: Record<string, RiskLevel>;
  /** Number of harmonic flow iterations to converge */
  iterations: number;
  /** Whether harmonic flow converged (should always be true for finite lattices) */
  converged: boolean;
  /** Whether obstruction exceeds fail-to-noise threshold */
  noiseTriggered: boolean;
}

/**
 * Detect policy obstruction across temporal variants.
 *
 * Given risk assessments from each temporal manifold, uses Tarski
 * sheaf cohomology to determine whether global consensus exists
 * and measures the degree of obstruction.
 *
 * @param assessments - risk level from each temporal T variant
 * @param options - mode (triadic/tetradic), noise threshold, twists
 */
export function detectPolicyObstruction(
  assessments: Partial<Record<TemporalVariant, RiskLevel>>,
  options?: {
    mode?: 'triadic' | 'tetradic';
    noiseThreshold?: number;
    twists?: Map<string, EdgeTwist>;
  },
): PolicyObstructionResult {
  const mode =
    options?.mode ?? (assessments.predictive !== undefined ? 'tetradic' : 'triadic');
  const noiseThreshold = options?.noiseThreshold ?? 0.5;

  const complex = buildTemporalComplex(mode);
  const sheaf = buildGovernanceSheaf(complex, options?.twists);

  // Build initial cochain from assessments
  const initial: Cochain0<RiskLevel> = new Map();
  for (const v of complex.vertices) {
    const key = v.id as TemporalVariant;
    initial.set(v.id, assessments[key] ?? RiskLevel.ALLOW);
  }

  // Run harmonic flow
  const { fixedPoint, iterations, converged } = harmonicFlow(sheaf, initial);

  // Compute obstruction degree
  const obstruction = obstructionDegree(sheaf, initial);

  // Consensus = meet of all fixed-point values
  let consensus = RiskLevel.DENY;
  for (const v of complex.vertices) {
    const val = fixedPoint.get(v.id) ?? RiskLevel.ALLOW;
    consensus = RISK_LATTICE.meet(consensus, val);
  }

  return {
    obstruction,
    consensus,
    fixedPoint: Object.fromEntries(fixedPoint) as Record<string, RiskLevel>,
    iterations,
    converged,
    noiseTriggered: obstruction > noiseThreshold,
  };
}

// ============================================================
// FAIL-TO-NOISE
// ============================================================

/**
 * Fail-to-noise: produce a fixed-size output indistinguishable
 * from legitimate governance data when obstruction is detected.
 *
 * Uses obstruction degree + vertex count as deterministic seed.
 * Output is always `size` bytes regardless of input.
 */
export function failToNoise(obstruction: number, size: number = 256): Uint8Array {
  const buf = new Uint8Array(size);
  // LCG seeded from obstruction — deterministic, reproducible
  let seed = (Math.floor(obstruction * 2147483647) | 1) >>> 0;
  for (let i = 0; i < size; i++) {
    seed = ((seed * 1103515245 + 12345) & 0x7fffffff) >>> 0;
    buf[i] = seed & 0xff;
  }
  return buf;
}

// ============================================================
// BRAIDED TEMPORAL DISTANCE (T-braiding integration)
// ============================================================

/**
 * Braided temporal distance: sum of pairwise hyperbolic distances
 * between temporal T-variants embedded in the Poincaré ball.
 *
 * For triadic (3 variants):
 *   d_b = d_H(T_i, T_m) + d_H(T_m, T_g) + d_H(T_g, T_i)
 *
 * For tetradic (4 variants):
 *   d_b = Σ_{all 6 pairs} d_H(T_a, T_b)
 *
 * Uses arcosh formula: d_H(u,v) = arcosh(1 + 2|u-v|² / ((1-|u|²)(1-|v|²)))
 *
 * @param variants - scalar values for each T in (-1, 1) (Poincaré ball)
 */
export function braidedTemporalDistance(variants: number[]): number {
  const n = variants.length;
  let total = 0;
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      const u = Math.max(-0.999, Math.min(0.999, variants[i]));
      const v = Math.max(-0.999, Math.min(0.999, variants[j]));
      const diff2 = (u - v) * (u - v);
      const denom = (1 - u * u) * (1 - v * v);
      const arg = 1 + (2 * diff2) / Math.max(denom, 1e-15);
      total += Math.acosh(Math.max(1, arg));
    }
  }
  return total;
}

/**
 * Braided meta-time: T_b = T^(t+k) · intent · context · [1/t]
 *
 * Multiplicative braiding of temporal variants through the base T.
 *
 * @param T - base time constant
 * @param t - temporal exponent (memory variant)
 * @param intent - intent alignment scalar
 * @param context - governance context scalar
 * @param includePredictive - if true, includes T/t forecast term
 */
export function braidedMetaTime(
  T: number,
  t: number,
  intent: number,
  context: number,
  includePredictive: boolean = false,
): number {
  const k = includePredictive ? 2 : 2;
  const base = Math.pow(Math.max(1e-10, T), t + k) * intent * context;
  if (includePredictive && Math.abs(t) > 1e-10) {
    return base / t;
  }
  return base;
}

// ============================================================
// COHOMOLOGICAL HARMONIC WALL
// ============================================================

/**
 * Cohomological harmonic wall: combines obstruction degree with
 * the existing H(d, R) = R^(d²) super-exponential scaling.
 *
 * The obstruction degree from Tarski cohomology maps to an
 * effective dimension d*, which feeds into the harmonic wall.
 * Result: adversarial temporal disagreement gets exponentially
 * amplified into governance cost.
 *
 * @param obstruction - [0,1] from detectPolicyObstruction
 * @param maxDimension - maximum effective dimension (default: 6, one per tongue)
 * @param R - harmonic ratio (default: 1.5, perfect fifth)
 */
export function cohomologicalHarmonicWall(
  obstruction: number,
  maxDimension: number = 6,
  R: number = 1.5,
): number {
  // Map obstruction [0,1] → effective dimension [0, maxDimension]
  const dStar = obstruction * maxDimension;
  // H(d*, R) = R^(d*²)
  return Math.pow(R, dStar * dStar);
}
