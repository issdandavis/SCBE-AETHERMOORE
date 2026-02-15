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
