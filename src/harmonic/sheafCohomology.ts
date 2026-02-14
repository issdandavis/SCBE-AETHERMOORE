/**
 * @file sheafCohomology.ts
 * @module harmonic/sheafCohomology
 * @layer Layer 13 (governance consensus), Layer 9-10 (spectral coherence)
 * @component Tarski Sheaf Cohomology for Agent Lattices
 * @version 1.0.0
 *
 * Implements cellular sheaf cohomology valued in complete lattices,
 * using Tarski's fixed-point theorem for consensus detection and
 * obstruction analysis in agent networks.
 *
 * Mathematical foundation:
 *   - Cell complex X = agent network (vertices = agents, edges = links)
 *   - Sheaf F assigns a complete lattice stalk F_σ to each cell σ
 *   - Galois connections (lower ⊣ upper) for face restrictions
 *   - Tarski Laplacian L_k: meet-based diffusion operator
 *   - Harmonic flow Φ_t = (id ∧ L_k)^t converges to greatest post-fixed point
 *   - TH^0(X; F) = Γ(X; F) = global sections = consensus
 *   - Higher TH^k = obstruction to extending local agreement
 *
 * References:
 *   - Tarski, "A lattice-theoretical fixpoint theorem" (1955)
 *   - Curry, Ghrist et al., "Sheaves, Cosheaves, and Applications" (2014)
 *   - Hansen & Ghrist, "Laplacians and Cohomology of Cellular Sheaves" (2019)
 */

// =============================================================================
// COMPLETE LATTICE INTERFACE
// =============================================================================

/**
 * A complete lattice: every subset has a meet (∧) and join (∨).
 *
 * For finite lattices, we require:
 *   - elements(): all elements in ascending order
 *   - leq(a, b): partial order a ≤ b
 *   - meet(a, b): greatest lower bound
 *   - join(a, b): least upper bound
 *   - top: greatest element (⊤)
 *   - bot: least element (⊥)
 */
export interface CompleteLattice<T> {
  /** All elements in ascending order */
  readonly elements: readonly T[];
  /** Top element (⊤) */
  readonly top: T;
  /** Bottom element (⊥) */
  readonly bot: T;
  /** Partial order: a ≤ b */
  leq(a: T, b: T): boolean;
  /** Meet (greatest lower bound): a ∧ b */
  meet(a: T, b: T): T;
  /** Join (least upper bound): a ∨ b */
  join(a: T, b: T): T;
  /** Meet of an array (fold with ∧, identity = ⊤) */
  meetAll(xs: T[]): T;
  /** Join of an array (fold with ∨, identity = ⊥) */
  joinAll(xs: T[]): T;
  /** Equality */
  eq(a: T, b: T): boolean;
}

// =============================================================================
// CONCRETE LATTICES
// =============================================================================

/** Risk decision lattice: ALLOW ≤ QUARANTINE ≤ ESCALATE ≤ DENY */
export type RiskDecision = 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';

const RISK_ORDER: readonly RiskDecision[] = ['ALLOW', 'QUARANTINE', 'ESCALATE', 'DENY'];
const RISK_INDEX = new Map<RiskDecision, number>(
  RISK_ORDER.map((r, i) => [r, i])
);

export const RiskLattice: CompleteLattice<RiskDecision> = {
  elements: RISK_ORDER,
  top: 'DENY',
  bot: 'ALLOW',
  leq: (a, b) => RISK_INDEX.get(a)! <= RISK_INDEX.get(b)!,
  meet: (a, b) => RISK_ORDER[Math.min(RISK_INDEX.get(a)!, RISK_INDEX.get(b)!)],
  join: (a, b) => RISK_ORDER[Math.max(RISK_INDEX.get(a)!, RISK_INDEX.get(b)!)],
  meetAll: (xs) =>
    xs.length === 0 ? 'DENY' : RISK_ORDER[Math.min(...xs.map((x) => RISK_INDEX.get(x)!))],
  joinAll: (xs) =>
    xs.length === 0 ? 'ALLOW' : RISK_ORDER[Math.max(...xs.map((x) => RISK_INDEX.get(x)!))],
  eq: (a, b) => a === b,
};

/** Governance tier lattice: KO ≤ AV ≤ RU ≤ CA ≤ UM ≤ DR */
export type GovernanceTier = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';

const GOV_ORDER: readonly GovernanceTier[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
const GOV_INDEX = new Map<GovernanceTier, number>(
  GOV_ORDER.map((g, i) => [g, i])
);

export const GovernanceLattice: CompleteLattice<GovernanceTier> = {
  elements: GOV_ORDER,
  top: 'DR',
  bot: 'KO',
  leq: (a, b) => GOV_INDEX.get(a)! <= GOV_INDEX.get(b)!,
  meet: (a, b) => GOV_ORDER[Math.min(GOV_INDEX.get(a)!, GOV_INDEX.get(b)!)],
  join: (a, b) => GOV_ORDER[Math.max(GOV_INDEX.get(a)!, GOV_INDEX.get(b)!)],
  meetAll: (xs) =>
    xs.length === 0 ? 'DR' : GOV_ORDER[Math.min(...xs.map((x) => GOV_INDEX.get(x)!))],
  joinAll: (xs) =>
    xs.length === 0 ? 'KO' : GOV_ORDER[Math.max(...xs.map((x) => GOV_INDEX.get(x)!))],
  eq: (a, b) => a === b,
};

/** Dimensional state lattice: COLLAPSED ≤ DEMI ≤ QUASI ≤ POLLY */
export type DimensionalState = 'COLLAPSED' | 'DEMI' | 'QUASI' | 'POLLY';

const DIM_ORDER: readonly DimensionalState[] = ['COLLAPSED', 'DEMI', 'QUASI', 'POLLY'];
const DIM_INDEX = new Map<DimensionalState, number>(
  DIM_ORDER.map((d, i) => [d, i])
);

export const DimensionalLattice: CompleteLattice<DimensionalState> = {
  elements: DIM_ORDER,
  top: 'POLLY',
  bot: 'COLLAPSED',
  leq: (a, b) => DIM_INDEX.get(a)! <= DIM_INDEX.get(b)!,
  meet: (a, b) => DIM_ORDER[Math.min(DIM_INDEX.get(a)!, DIM_INDEX.get(b)!)],
  join: (a, b) => DIM_ORDER[Math.max(DIM_INDEX.get(a)!, DIM_INDEX.get(b)!)],
  meetAll: (xs) =>
    xs.length === 0 ? 'POLLY' : DIM_ORDER[Math.min(...xs.map((x) => DIM_INDEX.get(x)!))],
  joinAll: (xs) =>
    xs.length === 0 ? 'COLLAPSED' : DIM_ORDER[Math.max(...xs.map((x) => DIM_INDEX.get(x)!))],
  eq: (a, b) => a === b,
};

/**
 * Unit interval lattice [0, 1] with meet = min, join = max.
 * Discretized to N levels for finite computation.
 */
export function createUnitIntervalLattice(levels: number = 101): CompleteLattice<number> {
  const step = 1 / (levels - 1);
  const elements = Array.from({ length: levels }, (_, i) => Math.round(i * step * 1e10) / 1e10);

  const clamp = (x: number): number => Math.max(0, Math.min(1, x));
  const snap = (x: number): number => {
    const v = clamp(x);
    return Math.round(v / step) * step;
  };

  return {
    elements,
    top: 1,
    bot: 0,
    leq: (a, b) => a <= b + 1e-12,
    meet: (a, b) => snap(Math.min(a, b)),
    join: (a, b) => snap(Math.max(a, b)),
    meetAll: (xs) => (xs.length === 0 ? 1 : snap(Math.min(...xs))),
    joinAll: (xs) => (xs.length === 0 ? 0 : snap(Math.max(...xs))),
    eq: (a, b) => Math.abs(a - b) < 1e-10,
  };
}

// =============================================================================
// CELL COMPLEX
// =============================================================================

/** A vertex (0-cell) in the complex */
export interface Vertex {
  id: string;
}

/** An edge (1-cell) connecting two vertices */
export interface Edge {
  id: string;
  source: string;
  target: string;
}

/**
 * Cell complex: vertices (0-cells) and edges (1-cells).
 * Represents an agent network graph.
 */
export interface CellComplex {
  vertices: Vertex[];
  edges: Edge[];
}

/**
 * Build a cell complex from an adjacency description.
 */
export function buildComplex(
  vertexIds: string[],
  edgePairs: [string, string][]
): CellComplex {
  const vertices: Vertex[] = vertexIds.map((id) => ({ id }));
  const edges: Edge[] = edgePairs.map(([s, t], i) => ({
    id: `e-${s}-${t}`,
    source: s,
    target: t,
  }));
  return { vertices, edges };
}

// =============================================================================
// GALOIS CONNECTION
// =============================================================================

/**
 * A Galois connection between two complete lattices (L, M):
 *   lower: L → M  (meet-preserving, left adjoint)
 *   upper: M → L  (join-preserving, right adjoint)
 *
 * Adjunction: lower(a) ≤_M b  ⟺  a ≤_L upper(b)
 */
export interface GaloisConnection<L, M> {
  /** Left adjoint: L → M (meet-preserving) */
  lower: (a: L) => M;
  /** Right adjoint: M → L (join-preserving) */
  upper: (b: M) => L;
}

/**
 * Identity Galois connection (same lattice, identity maps).
 */
export function identityConnection<T>(): GaloisConnection<T, T> {
  return {
    lower: (a) => a,
    upper: (b) => b,
  };
}

/**
 * Build a Galois connection from an order-preserving map and its adjoint.
 */
export function galoisFromMaps<L, M>(
  lower: (a: L) => M,
  upper: (b: M) => L
): GaloisConnection<L, M> {
  return { lower, upper };
}

// =============================================================================
// CELLULAR SHEAF
// =============================================================================

/**
 * Cellular sheaf F on a cell complex X, valued in complete lattices.
 *
 * Assigns:
 *   - To each vertex v: a complete lattice F_v (the stalk)
 *   - To each edge e: a complete lattice F_e (the stalk)
 *   - For each (vertex v, incident edge e): a Galois connection F_{v→e}
 *
 * For uniform sheaves (constant stalk), all stalks share the same lattice.
 */
export interface CellularSheaf<T> {
  /** The underlying lattice (for uniform sheaves) */
  lattice: CompleteLattice<T>;
  /** The cell complex */
  complex: CellComplex;
  /** Restriction map: vertex stalk → edge stalk (lower adjoint of Galois connection) */
  restrict(vertexId: string, edgeId: string, value: T): T;
  /** Extension map: edge stalk → vertex stalk (upper adjoint) */
  extend(edgeId: string, vertexId: string, value: T): T;
}

/**
 * Build a constant sheaf: same lattice L on every cell, identity restrictions.
 */
export function constantSheaf<T>(
  lattice: CompleteLattice<T>,
  complex: CellComplex
): CellularSheaf<T> {
  return {
    lattice,
    complex,
    restrict: (_v, _e, value) => value,
    extend: (_e, _v, value) => value,
  };
}

/**
 * Build a sheaf with custom restriction maps per edge.
 * Each edge gets a Galois connection from source stalk and target stalk.
 */
export function customSheaf<T>(
  lattice: CompleteLattice<T>,
  complex: CellComplex,
  restrictions: Map<string, GaloisConnection<T, T>>
): CellularSheaf<T> {
  return {
    lattice,
    complex,
    restrict: (vertexId, edgeId, value) => {
      const conn = restrictions.get(edgeId);
      return conn ? conn.lower(value) : value;
    },
    extend: (edgeId, vertexId, value) => {
      const conn = restrictions.get(edgeId);
      return conn ? conn.upper(value) : value;
    },
  };
}

// =============================================================================
// COCHAINS
// =============================================================================

/**
 * A 0-cochain: assignment of a lattice value to each vertex.
 */
export type Cochain0<T> = Map<string, T>;

/**
 * A 1-cochain: assignment of a lattice value to each edge.
 */
export type Cochain1<T> = Map<string, T>;

/**
 * Create a 0-cochain from vertex assignments.
 */
export function cochain0<T>(assignments: Record<string, T>): Cochain0<T> {
  return new Map(Object.entries(assignments));
}

/**
 * Create a constant 0-cochain (all vertices get the same value).
 */
export function constantCochain0<T>(
  complex: CellComplex,
  value: T
): Cochain0<T> {
  const m = new Map<string, T>();
  for (const v of complex.vertices) m.set(v.id, value);
  return m;
}

/**
 * Create a top-valued 0-cochain (all vertices get ⊤).
 */
export function topCochain0<T>(
  sheaf: CellularSheaf<T>
): Cochain0<T> {
  return constantCochain0(sheaf.complex, sheaf.lattice.top);
}

// =============================================================================
// TARSKI LAPLACIAN
// =============================================================================

/**
 * Compute the Tarski Laplacian L_0 on a 0-cochain.
 *
 * For each vertex v:
 *   (L_0 x)_v = ∧_{e ∈ δv} F^upper_{v→e}( ∧_{v' ∈ ∂e} F^lower_{v'→e}(x_{v'}) )
 *
 * In English: for each incident edge, restrict all endpoint values down to the
 * edge stalk (meet them), then extend back up to v's stalk. Meet all results.
 *
 * This is a monotone operator on the product lattice ∏_v F_v.
 */
export function tarskiLaplacian0<T>(
  sheaf: CellularSheaf<T>,
  x: Cochain0<T>
): Cochain0<T> {
  const L = sheaf.lattice;
  const result = new Map<string, T>();

  for (const v of sheaf.complex.vertices) {
    // Find all edges incident to v
    const incidentEdges = sheaf.complex.edges.filter(
      (e) => e.source === v.id || e.target === v.id
    );

    if (incidentEdges.length === 0) {
      // Isolated vertex: L_0 x_v = ⊤ (vacuous meet)
      result.set(v.id, L.top);
      continue;
    }

    // For each incident edge, compute the diffused value
    const edgeContributions: T[] = [];

    for (const e of incidentEdges) {
      // Get both endpoints of the edge
      const endpoints = [e.source, e.target];

      // Restrict each endpoint's value to the edge stalk and meet them
      const restrictedValues = endpoints.map((vId) =>
        sheaf.restrict(vId, e.id, x.get(vId) ?? L.top)
      );
      const edgeMeet = L.meetAll(restrictedValues);

      // Extend back to v's stalk
      const extended = sheaf.extend(e.id, v.id, edgeMeet);
      edgeContributions.push(extended);
    }

    // Meet all edge contributions
    result.set(v.id, L.meetAll(edgeContributions));
  }

  return result;
}

/**
 * Compute (id ∧ L_0): the harmonic step operator.
 * At each vertex: take the meet of the current value and the Laplacian value.
 */
export function harmonicStep0<T>(
  sheaf: CellularSheaf<T>,
  x: Cochain0<T>
): Cochain0<T> {
  const L = sheaf.lattice;
  const lx = tarskiLaplacian0(sheaf, x);
  const result = new Map<string, T>();

  for (const v of sheaf.complex.vertices) {
    const current = x.get(v.id) ?? L.top;
    const laplacian = lx.get(v.id) ?? L.top;
    result.set(v.id, L.meet(current, laplacian));
  }

  return result;
}

// =============================================================================
// HARMONIC FLOW & TARSKI COHOMOLOGY
// =============================================================================

/** Result of running the harmonic flow */
export interface HarmonicFlowResult<T> {
  /** The converged cochain (greatest post-fixed point) */
  fixedPoint: Cochain0<T>;
  /** Number of iterations to converge */
  iterations: number;
  /** Whether convergence was reached within max iterations */
  converged: boolean;
}

/**
 * Run the harmonic flow: iterate Φ_t = (id ∧ L_0)^t from an initial cochain
 * until convergence (fixed point reached).
 *
 * By Tarski's fixed-point theorem, this converges to the greatest post-fixed point
 * of L_0 that is ≤ the initial cochain. Starting from ⊤ gives TH^0.
 *
 * For finite lattices with descending chain condition, terminates in finite steps.
 */
export function harmonicFlow<T>(
  sheaf: CellularSheaf<T>,
  initial: Cochain0<T>,
  maxIterations: number = 1000
): HarmonicFlowResult<T> {
  const L = sheaf.lattice;
  let current = new Map(initial);
  let iterations = 0;

  for (let t = 0; t < maxIterations; t++) {
    const next = harmonicStep0(sheaf, current);
    iterations = t + 1;

    // Check convergence: all values unchanged
    let converged = true;
    for (const v of sheaf.complex.vertices) {
      if (!L.eq(current.get(v.id) ?? L.top, next.get(v.id) ?? L.top)) {
        converged = false;
        break;
      }
    }

    if (converged) {
      return { fixedPoint: current, iterations, converged: true };
    }

    current = next;
  }

  return { fixedPoint: current, iterations, converged: false };
}

/**
 * Compute TH^0(X; F) — the 0th Tarski cohomology.
 *
 * This equals the global sections Γ(X; F): assignments of values to vertices
 * that are consistent across all edges.
 *
 * Algorithm: start from ⊤ cochain, run harmonic flow to convergence.
 */
export function tarskiCohomology0<T>(
  sheaf: CellularSheaf<T>,
  maxIterations?: number
): HarmonicFlowResult<T> {
  const initial = topCochain0(sheaf);
  return harmonicFlow(sheaf, initial, maxIterations);
}

// =============================================================================
// 1-COCHAINS & TARSKI LAPLACIAN L_1
// =============================================================================

/**
 * Pseudo-coboundary δ~: C^0 → C^1
 * For each edge e = (s → t):
 *   (δ~ x)_e = F_{s→e}^lower(x_s) ∧ F_{t→e}^lower(x_t)
 *
 * This restricts both endpoint values to the edge stalk and meets them.
 * Non-zero δ~ indicates local agreement on the edge.
 */
export function pseudoCoboundary<T>(
  sheaf: CellularSheaf<T>,
  x: Cochain0<T>
): Cochain1<T> {
  const L = sheaf.lattice;
  const result = new Map<string, T>();

  for (const e of sheaf.complex.edges) {
    const sVal = sheaf.restrict(e.source, e.id, x.get(e.source) ?? L.top);
    const tVal = sheaf.restrict(e.target, e.id, x.get(e.target) ?? L.top);
    result.set(e.id, L.meet(sVal, tVal));
  }

  return result;
}

/**
 * Compute the Tarski Laplacian L_1 on a 1-cochain.
 *
 * For each edge e:
 *   (L_1 y)_e = ∧_{v ∈ ∂e} F^lower_{v→e}( ∧_{e' ∈ δv} F^upper_{v→e'}(y_{e'}) )
 *
 * "For each endpoint of e, collect all incident edges, extend their values
 *  to the vertex, meet them, then restrict back to e. Meet the results."
 */
export function tarskiLaplacian1<T>(
  sheaf: CellularSheaf<T>,
  y: Cochain1<T>
): Cochain1<T> {
  const L = sheaf.lattice;
  const result = new Map<string, T>();

  for (const e of sheaf.complex.edges) {
    const endpoints = [e.source, e.target];
    const endpointContributions: T[] = [];

    for (const vId of endpoints) {
      // All edges incident to v
      const incidentEdges = sheaf.complex.edges.filter(
        (e2) => e2.source === vId || e2.target === vId
      );

      // Extend each edge value to v, then meet
      const extended = incidentEdges.map((e2) =>
        sheaf.extend(e2.id, vId, y.get(e2.id) ?? L.top)
      );
      const vMeet = L.meetAll(extended);

      // Restrict back to edge e
      const restricted = sheaf.restrict(vId, e.id, vMeet);
      endpointContributions.push(restricted);
    }

    result.set(e.id, L.meetAll(endpointContributions));
  }

  return result;
}

/**
 * Compute TH^1(X; F) — obstruction to extending local agreement to global sections.
 *
 * Non-trivial TH^1 means there exist edge-level consistent assignments
 * that cannot be lifted to a global consensus.
 *
 * Algorithm: start from ⊤ on edges, run L_1 harmonic flow.
 */
export function tarskiCohomology1<T>(
  sheaf: CellularSheaf<T>,
  maxIterations: number = 1000
): { fixedPoint: Cochain1<T>; iterations: number; converged: boolean } {
  const L = sheaf.lattice;
  let current = new Map<string, T>();
  for (const e of sheaf.complex.edges) current.set(e.id, L.top);

  for (let t = 0; t < maxIterations; t++) {
    const l1 = tarskiLaplacian1(sheaf, current);
    const next = new Map<string, T>();
    for (const e of sheaf.complex.edges) {
      next.set(e.id, L.meet(current.get(e.id) ?? L.top, l1.get(e.id) ?? L.top));
    }

    // Check convergence
    let converged = true;
    for (const e of sheaf.complex.edges) {
      if (!L.eq(current.get(e.id) ?? L.top, next.get(e.id) ?? L.top)) {
        converged = false;
        break;
      }
    }

    if (converged) {
      return { fixedPoint: current, iterations: t + 1, converged: true };
    }
    current = next;
  }

  return { fixedPoint: current, iterations: maxIterations, converged: false };
}

// =============================================================================
// CONSENSUS & OBSTRUCTION ANALYSIS
// =============================================================================

/** Consensus analysis result */
export interface ConsensusAnalysis<T> {
  /** Whether global consensus was reached (flow converged with no disagreement) */
  hasConsensus: boolean;
  /** The consensus value per vertex (fixed point) */
  consensusValues: Record<string, T>;
  /** Whether all vertices agree on the same value */
  isUnanimous: boolean;
  /** The unanimous value if isUnanimous, otherwise undefined */
  unanimousValue?: T;
  /** Number of distinct values in the consensus */
  distinctValues: number;
  /** Disagreement edges: edges where restricted endpoint values differ */
  disagreementEdges: string[];
  /** Convergence iterations */
  iterations: number;
  /** Edge-level agreement (TH^1 analysis) */
  edgeAgreement: Record<string, T>;
  /** Whether there are obstructions (TH^1 non-trivial beyond TH^0 image) */
  hasObstruction: boolean;
}

/**
 * Analyze consensus in an agent network using sheaf cohomology.
 *
 * Given initial opinions (or starting from ⊤), computes:
 *   - TH^0: global consensus (greatest post-fixed point)
 *   - TH^1: edge-level agreement / obstruction
 *   - Disagreement detection
 */
export function analyzeConsensus<T>(
  sheaf: CellularSheaf<T>,
  initialOpinions?: Cochain0<T>,
  maxIterations?: number
): ConsensusAnalysis<T> {
  const L = sheaf.lattice;

  // Compute TH^0
  const initial = initialOpinions ?? topCochain0(sheaf);
  const th0 = harmonicFlow(sheaf, initial, maxIterations);

  // Extract consensus values
  const consensusValues: Record<string, T> = {};
  const values: T[] = [];
  for (const v of sheaf.complex.vertices) {
    const val = th0.fixedPoint.get(v.id) ?? L.bot;
    consensusValues[v.id] = val;
    values.push(val);
  }

  // Check unanimity
  const distinctSet = new Set<string>();
  for (const val of values) {
    distinctSet.add(JSON.stringify(val));
  }
  const isUnanimous = distinctSet.size <= 1;
  const unanimousValue = isUnanimous && values.length > 0 ? values[0] : undefined;

  // Detect disagreement edges
  const disagreementEdges: string[] = [];
  for (const e of sheaf.complex.edges) {
    const sRestricted = sheaf.restrict(
      e.source,
      e.id,
      th0.fixedPoint.get(e.source) ?? L.top
    );
    const tRestricted = sheaf.restrict(
      e.target,
      e.id,
      th0.fixedPoint.get(e.target) ?? L.top
    );
    if (!L.eq(sRestricted, tRestricted)) {
      disagreementEdges.push(e.id);
    }
  }

  // Compute TH^1
  const th1 = tarskiCohomology1(sheaf, maxIterations);
  const edgeAgreement: Record<string, T> = {};
  for (const e of sheaf.complex.edges) {
    edgeAgreement[e.id] = th1.fixedPoint.get(e.id) ?? L.bot;
  }

  // Obstruction: TH^1 values that are above the coboundary image
  const coboundary = pseudoCoboundary(sheaf, th0.fixedPoint);
  let hasObstruction = false;
  for (const e of sheaf.complex.edges) {
    const th1Val = th1.fixedPoint.get(e.id) ?? L.bot;
    const cobVal = coboundary.get(e.id) ?? L.bot;
    // Obstruction if TH^1 > δ~(TH^0) on some edge
    if (!L.eq(th1Val, cobVal) && L.leq(cobVal, th1Val)) {
      hasObstruction = true;
      break;
    }
  }

  return {
    hasConsensus: th0.converged && disagreementEdges.length === 0,
    consensusValues,
    isUnanimous,
    unanimousValue,
    distinctValues: distinctSet.size,
    disagreementEdges,
    iterations: th0.iterations,
    edgeAgreement,
    hasObstruction,
  };
}

// =============================================================================
// AGENT NETWORK HELPERS
// =============================================================================

/**
 * Build a sheaf for an agent network where each agent proposes a risk decision.
 * Uses the RiskLattice with identity restrictions (constant sheaf).
 */
export function riskConsensusSheaf(
  agentIds: string[],
  links: [string, string][]
): CellularSheaf<RiskDecision> {
  return constantSheaf(RiskLattice, buildComplex(agentIds, links));
}

/**
 * Build a sheaf for governance tier consensus.
 */
export function governanceConsensusSheaf(
  agentIds: string[],
  links: [string, string][]
): CellularSheaf<GovernanceTier> {
  return constantSheaf(GovernanceLattice, buildComplex(agentIds, links));
}

/**
 * Run risk consensus: given agent opinions, compute the agreed-upon risk decision.
 */
export function riskConsensus(
  agentIds: string[],
  links: [string, string][],
  opinions: Record<string, RiskDecision>
): ConsensusAnalysis<RiskDecision> {
  const sheaf = riskConsensusSheaf(agentIds, links);
  const initial = cochain0(opinions);
  return analyzeConsensus(sheaf, initial);
}

/**
 * Compact summary string for a consensus analysis.
 */
export function consensusSummary<T>(analysis: ConsensusAnalysis<T>): string {
  const lines: string[] = [];
  lines.push(`Consensus: ${analysis.hasConsensus ? 'YES' : 'NO'}`);
  lines.push(`Unanimous: ${analysis.isUnanimous ? `YES (${JSON.stringify(analysis.unanimousValue)})` : 'NO'}`);
  lines.push(`Distinct values: ${analysis.distinctValues}`);
  lines.push(`Disagreement edges: ${analysis.disagreementEdges.length}`);
  lines.push(`Obstruction (TH^1): ${analysis.hasObstruction ? 'YES' : 'NO'}`);
  lines.push(`Iterations: ${analysis.iterations}`);
  return lines.join('\n');
}
