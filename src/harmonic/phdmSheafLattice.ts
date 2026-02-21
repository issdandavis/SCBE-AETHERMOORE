/**
 * @file phdmSheafLattice.ts
 * @module harmonic/phdm-sheaf-lattice
 * @layer Layer 8, Layer 9, Layer 12, Layer 13
 * @component PHDM Sheaf Lattice — Constraint-Based Governance Routing
 * @version 3.2.4
 *
 * Bridges the Polyhedral Hamiltonian Defense Manifold (PHDM) with sheaf
 * cohomology on complete lattices, providing:
 *
 *   1. A cell complex derived from the 16 canonical polyhedra
 *   2. A governance sheaf encoding trust-decay across polyhedral families
 *   3. Sheaf-cohomological obstruction detection for invalid transitions
 *   4. Constraint-based routing: valid actions = paths where local
 *      governance data glues globally (no obstructions)
 *
 * Mathematical foundation:
 *   - The polyhedral graph G = (V, E) where V = 16 polyhedra and
 *     E = intra-family + cross-family adjacencies
 *   - A cellular sheaf F on G valued in the unit-interval lattice [0,1]
 *   - Trust scores propagate via Galois connections weighted by family
 *     proximity (golden ratio decay for cross-family edges)
 *   - Governance decision = TH^0 global section analysis:
 *     * Coherent (no obstructions) → ALLOW
 *     * Moderate obstructions → QUARANTINE
 *     * Severe obstructions → DENY
 *
 * This module positions PHDM as constraint-based governance routing:
 * valid thoughts = paths through polyhedral lattice where sheaf
 * cohomology detects no obstructions to global consistency.
 *
 * @see Tarski's Fixed-Point Theorem
 * @see Curry, Ghrist, Robinson — "Cellular Sheaves of Lattices"
 */

import { Vector6D } from './constants.js';
import { PHI } from './qcLattice.js';
import {
  CANONICAL_POLYHEDRA,
  computeCentroid,
  distance6D,
  getActivePolyhedra,
  type FluxState,
  type Point6D,
  type Polyhedron,
  type PolyhedronFamily,
} from './phdm.js';
import {
  UnitIntervalLattice,
  graphComplex,
  twistedSheaf,
  v2ConstantSheaf as constantSheaf,
  tarskiCohomology,
  hodgeCohomology,
  v2GlobalSections as globalSections,
  detectObstructions,
  analyseCohomology,
  type V2CompleteLattice as CompleteLattice,
  type V2CellComplex as CellComplex,
  type V2CellularSheaf as CellularSheaf,
  type Cochain,
  type CohomologyResult,
  type Obstruction,
  type SheafAnalysisResult,
} from './sheafCohomology.js';

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

/**
 * Family trust tiers — golden ratio decay for cross-family transitions.
 * Platonic (core) = highest trust, Kepler-Poinsot (risk zone) = lowest.
 */
const FAMILY_TRUST: Record<PolyhedronFamily, number> = {
  platonic: 1.0,
  archimedean: 1.0 / PHI, // ≈ 0.618
  johnson: 1.0 / (PHI * PHI), // ≈ 0.382
  rhombic: 1.0 / (PHI * PHI), // ≈ 0.382
  toroidal: 1.0 / (PHI * PHI * PHI), // ≈ 0.236
  'kepler-poinsot': 1.0 / (PHI * PHI * PHI * PHI), // ≈ 0.146
};

/**
 * Family ordering for adjacency (families with adjacent indices
 * are connected; non-adjacent families incur higher trust decay).
 */
const FAMILY_ORDER: PolyhedronFamily[] = [
  'platonic',
  'archimedean',
  'johnson',
  'rhombic',
  'toroidal',
  'kepler-poinsot',
];

/** Risk decision thresholds */
const COHERENCE_ALLOW = 0.8;
const COHERENCE_QUARANTINE = 0.4;

// ═══════════════════════════════════════════════════════════════
// Polyhedral Graph Construction
// ═══════════════════════════════════════════════════════════════

/**
 * Edge in the polyhedral graph with trust-decay weight.
 */
export interface PolyhedralEdge {
  /** Source polyhedron index */
  readonly from: number;
  /** Target polyhedron index */
  readonly to: number;
  /** Trust decay factor for this edge ∈ (0, 1] */
  readonly trustScale: number;
  /** Edge type: intra-family or cross-family */
  readonly edgeType: 'intra' | 'cross';
}

/**
 * Build the polyhedral adjacency graph from PHDM polyhedra.
 *
 * Adjacency rules:
 * 1. Intra-family: all polyhedra within the same family are connected
 *    (trust scale = 1.0, no decay within family)
 * 2. Cross-family: families adjacent in the family order are connected
 *    (trust scale = geometric mean of their trust tiers)
 *
 * @param polyhedra The set of polyhedra (default: CANONICAL_POLYHEDRA)
 * @returns Edges with trust weights and the adjacency pairs
 */
export function buildPolyhedralGraph(
  polyhedra: Polyhedron[] = CANONICAL_POLYHEDRA
): { edges: PolyhedralEdge[]; pairs: [number, number][] } {
  const edges: PolyhedralEdge[] = [];
  const pairs: [number, number][] = [];

  // Group polyhedra by family
  const familyGroups = new Map<PolyhedronFamily, number[]>();
  for (let i = 0; i < polyhedra.length; i++) {
    const fam = polyhedra[i].family;
    if (!familyGroups.has(fam)) familyGroups.set(fam, []);
    familyGroups.get(fam)!.push(i);
  }

  // Intra-family edges (full clique within each family)
  for (const [, indices] of familyGroups) {
    for (let a = 0; a < indices.length; a++) {
      for (let b = a + 1; b < indices.length; b++) {
        edges.push({
          from: indices[a],
          to: indices[b],
          trustScale: 1.0,
          edgeType: 'intra',
        });
        pairs.push([indices[a], indices[b]]);
      }
    }
  }

  // Cross-family edges (adjacent families in the order)
  for (let fi = 0; fi < FAMILY_ORDER.length - 1; fi++) {
    const famA = FAMILY_ORDER[fi];
    const famB = FAMILY_ORDER[fi + 1];
    const groupA = familyGroups.get(famA) ?? [];
    const groupB = familyGroups.get(famB) ?? [];

    // Trust scale = geometric mean of family trusts
    const trustA = FAMILY_TRUST[famA];
    const trustB = FAMILY_TRUST[famB];
    const scale = Math.sqrt(trustA * trustB);

    for (const a of groupA) {
      for (const b of groupB) {
        edges.push({
          from: a,
          to: b,
          trustScale: scale,
          edgeType: 'cross',
        });
        pairs.push([a, b]);
      }
    }
  }

  return { edges, pairs };
}

// ═══════════════════════════════════════════════════════════════
// Polyhedral Trust Scores
// ═══════════════════════════════════════════════════════════════

/**
 * Compute a trust score for each polyhedron based on its family tier
 * and topological properties. Score ∈ [0, 1].
 *
 * Trust = familyTrust * topologicalFactor
 * where topologicalFactor penalises non-zero genus (g > 0 = riskier).
 */
export function computePolyhedralTrust(
  polyhedra: Polyhedron[] = CANONICAL_POLYHEDRA
): number[] {
  return polyhedra.map((p) => {
    const familyBase = FAMILY_TRUST[p.family];
    // Genus penalty: genus 0 = 1.0, genus 1 = 0.7, genus 4 = 0.4
    const genusPenalty = 1.0 / (1.0 + 0.3 * p.genus);
    return Math.max(0, Math.min(1, familyBase * genusPenalty));
  });
}

// ═══════════════════════════════════════════════════════════════
// Governance Sheaf Construction
// ═══════════════════════════════════════════════════════════════

/**
 * Build a governance sheaf over the polyhedral graph.
 *
 * The sheaf assigns:
 * - Stalk at each vertex: UnitIntervalLattice (trust scores in [0, 1])
 * - Restriction maps: scaling Galois connections weighted by edge trust
 *
 * This captures the governance invariant: trust propagates with
 * golden-ratio decay across family boundaries.
 *
 * @param polyhedra Active polyhedra
 * @param latticeSteps Discretisation for the unit-interval lattice
 * @returns The cellular sheaf and the underlying complex
 */
export function buildGovernanceSheaf(
  polyhedra: Polyhedron[] = CANONICAL_POLYHEDRA,
  latticeSteps: number = 100
): { sheaf: CellularSheaf<number>; complex: CellComplex; edges: PolyhedralEdge[] } {
  const { edges, pairs } = buildPolyhedralGraph(polyhedra);
  const complex = graphComplex(polyhedra.length, pairs);
  const lattice = UnitIntervalLattice(latticeSteps);

  const edgeScales = new Map<number, number>();
  for (let e = 0; e < edges.length; e++) {
    edgeScales.set(e, edges[e].trustScale);
  }

  const sheaf = twistedSheaf(complex, lattice, edgeScales);
  return { sheaf, complex, edges };
}

// ═══════════════════════════════════════════════════════════════
// Governance Routing Result
// ═══════════════════════════════════════════════════════════════

/** Risk decision from governance routing */
export type GovernanceDecision = 'ALLOW' | 'QUARANTINE' | 'DENY';

/**
 * Result of a PHDM governance routing check.
 */
export interface GovernanceRoutingResult {
  /** Risk decision */
  readonly decision: GovernanceDecision;
  /** Sheaf coherence score [0, 1] */
  readonly coherenceScore: number;
  /** Obstructions detected (edges where trust data fails to glue) */
  readonly obstructions: Obstruction[];
  /** Global sections (TH^0) — consensus trust values */
  readonly globalSections: CohomologyResult<number>;
  /** First cohomology (TH^1) — obstruction indicators */
  readonly firstCohomology: CohomologyResult<number>;
  /** Per-polyhedron trust assignments used */
  readonly trustAssignment: number[];
  /** Transition path validated (indices into polyhedra array) */
  readonly validatedPath: number[];
  /** Whether the path is a valid Hamiltonian-like trajectory */
  readonly pathValid: boolean;
  /** Risk amplification from obstructions */
  readonly riskAmplification: number;
}

// ═══════════════════════════════════════════════════════════════
// PHDM Governance Router
// ═══════════════════════════════════════════════════════════════

/**
 * Configuration for the PHDM Governance Router.
 */
export interface GovernanceRouterConfig {
  /** Lattice discretisation steps (default: 100) */
  latticeSteps?: number;
  /** Coherence threshold for ALLOW (default: 0.8) */
  allowThreshold?: number;
  /** Coherence threshold for QUARANTINE (default: 0.4) */
  quarantineThreshold?: number;
  /** Maximum cohomology iterations (default: lattice height + 10) */
  maxIterations?: number;
  /** Harmonic coupling constant (default: PHI) */
  harmonicCoupling?: number;
}

const DEFAULT_ROUTER_CONFIG: Required<GovernanceRouterConfig> = {
  latticeSteps: 100,
  allowThreshold: COHERENCE_ALLOW,
  quarantineThreshold: COHERENCE_QUARANTINE,
  maxIterations: 120,
  harmonicCoupling: PHI,
};

/**
 * PHDM Governance Router — constraint-based routing via sheaf cohomology.
 *
 * This is the main integration class. It treats the PHDM polyhedral
 * lattice as a cell complex, assigns governance-aware trust values,
 * and uses sheaf cohomology to detect whether a proposed action path
 * through the polyhedra is globally consistent.
 *
 * Key property: An action is ALLOWED only if its trust assignment
 * produces no sheaf obstructions (local data glues globally).
 *
 * Usage:
 *   const router = new PHDMGovernanceRouter();
 *   const result = router.validatePath([0, 1, 5, 7]); // polyhedra indices
 *   if (result.decision === 'ALLOW') { ... }
 */
export class PHDMGovernanceRouter {
  private readonly config: Required<GovernanceRouterConfig>;
  private readonly polyhedra: Polyhedron[];
  private readonly trustScores: number[];
  private readonly lattice: CompleteLattice<number>;
  private _fluxState: FluxState;

  constructor(
    config?: GovernanceRouterConfig,
    fluxState: FluxState = 'POLLY'
  ) {
    this.config = { ...DEFAULT_ROUTER_CONFIG, ...config };
    this._fluxState = fluxState;
    this.polyhedra = getActivePolyhedra(fluxState);
    this.trustScores = computePolyhedralTrust(this.polyhedra);
    this.lattice = UnitIntervalLattice(this.config.latticeSteps);
  }

  /**
   * Get the current flux state.
   */
  get fluxState(): FluxState {
    return this._fluxState;
  }

  /**
   * Get the active polyhedra under the current flux state.
   */
  getActivePolyhedra(): Polyhedron[] {
    return this.polyhedra;
  }

  /**
   * Get trust scores for all active polyhedra.
   */
  getTrustScores(): number[] {
    return [...this.trustScores];
  }

  /**
   * Validate a proposed transition path through the polyhedral lattice.
   *
   * The path is a sequence of polyhedron indices. The router:
   * 1. Builds a subgraph from the path vertices + their edges
   * 2. Assigns trust scores from family tiers
   * 3. Runs sheaf cohomology to check global consistency
   * 4. Returns ALLOW / QUARANTINE / DENY based on coherence
   *
   * @param path Sequence of polyhedron indices (into active polyhedra)
   * @param customTrust Optional override trust scores for the path vertices
   * @returns Governance routing result
   */
  validatePath(
    path: number[],
    customTrust?: number[]
  ): GovernanceRoutingResult {
    if (path.length === 0) {
      return this.emptyResult(path);
    }

    // Validate indices
    for (const idx of path) {
      if (idx < 0 || idx >= this.polyhedra.length) {
        return this.denyResult(path, `Invalid polyhedron index: ${idx}`);
      }
    }

    // Build the full polyhedral graph
    const { sheaf, complex, edges } = buildGovernanceSheaf(
      this.polyhedra,
      this.config.latticeSteps
    );

    // Assign trust scores
    const assignment: Cochain<number> = new Map();
    for (let i = 0; i < this.polyhedra.length; i++) {
      const trust = customTrust?.[i] ?? this.trustScores[i];
      assignment.set(i, Math.max(0, Math.min(1, trust)));
    }

    // Check path connectivity: each consecutive pair must share an edge
    const pathValid = this.isPathConnected(path, edges);

    // Compute cohomology
    const th0 = tarskiCohomology(sheaf, 0, this.config.maxIterations);
    const th1 = complex.maxDim() >= 1
      ? tarskiCohomology(sheaf, 1, this.config.maxIterations)
      : { cochains: new Map<number, number>(), iterations: 0, converged: true, degree: 1 };

    // Detect obstructions on the local trust assignment
    const obstructions = detectObstructions(sheaf, assignment);

    // Build the set of edge indices that are ON the path
    // (between consecutive path vertices)
    const pathEdgeSet = new Set<number>();
    const edgeLookup = new Map<string, number>();
    for (let e = 0; e < edges.length; e++) {
      edgeLookup.set(`${edges[e].from}-${edges[e].to}`, e);
      edgeLookup.set(`${edges[e].to}-${edges[e].from}`, e);
    }
    for (let i = 0; i < path.length - 1; i++) {
      const key = `${path[i]}-${path[i + 1]}`;
      const edgeIdx = edgeLookup.get(key);
      if (edgeIdx !== undefined) pathEdgeSet.add(edgeIdx);
    }

    // Filter to obstructions on path edges (between consecutive vertices)
    const pathObstructions = obstructions.filter((obs) => {
      const edgeCell = obs.cells.find((c) => c.dim === 1);
      return edgeCell !== undefined && pathEdgeSet.has(edgeCell.id);
    });

    // Also collect neighborhood obstructions (edges touching path vertices
    // but not on the path itself) — used for risk amplification
    const pathSet = new Set(path);
    const neighborhoodObstructions = obstructions.filter((obs) => {
      const edgeCell = obs.cells.find((c) => c.dim === 1);
      const isPathEdge = edgeCell !== undefined && pathEdgeSet.has(edgeCell.id);
      const touchesPath = obs.cells.some((c) => c.dim === 0 && pathSet.has(c.id));
      return !isPathEdge && touchesPath;
    });

    // Coherence score based on path-edge obstructions only
    const pathEdgeCount = Math.max(1, pathEdgeSet.size);
    const totalSeverity = pathObstructions.reduce((s, o) => s + o.severity, 0);
    const coherenceScore = Math.max(0, 1 - totalSeverity / pathEdgeCount);

    // Risk amplification: path obstructions + neighborhood obstructions (weighted lower)
    const allRelevantObs = [
      ...pathObstructions,
      ...neighborhoodObstructions.map((o) => ({ ...o, severity: o.severity * 0.3 })),
    ];
    const significantObs = allRelevantObs.filter((o) => o.severity >= 0.3);
    const riskAmplification = significantObs.length > 0
      ? Math.pow(
          this.config.harmonicCoupling,
          significantObs.reduce((s, o) => s + o.severity * o.severity, 0)
        )
      : 1;

    // Decision
    let decision: GovernanceDecision;
    if (!pathValid) {
      decision = 'DENY';
    } else if (coherenceScore >= this.config.allowThreshold) {
      decision = 'ALLOW';
    } else if (coherenceScore >= this.config.quarantineThreshold) {
      decision = 'QUARANTINE';
    } else {
      decision = 'DENY';
    }

    return {
      decision,
      coherenceScore,
      obstructions: [...pathObstructions, ...neighborhoodObstructions],
      globalSections: th0 as CohomologyResult<number>,
      firstCohomology: th1 as CohomologyResult<number>,
      trustAssignment: Array.from(assignment.values()),
      validatedPath: path,
      pathValid,
      riskAmplification,
    };
  }

  /**
   * Quick coherence check: is a path globally consistent?
   */
  isCoherent(path: number[]): boolean {
    const result = this.validatePath(path);
    return result.decision === 'ALLOW';
  }

  /**
   * Validate a transition from one polyhedral region to another.
   * Checks whether a single step between two polyhedra is allowed.
   */
  validateTransition(from: number, to: number): GovernanceRoutingResult {
    return this.validatePath([from, to]);
  }

  /**
   * Analyse the full polyhedral lattice for global coherence.
   * Returns the sheaf analysis for all polyhedra simultaneously.
   */
  analyseFullLattice(): SheafAnalysisResult & { decision: GovernanceDecision } {
    // Convert trust scores to 6D vectors (use centroid positions)
    const vectors: Vector6D[] = this.polyhedra.map((p) => {
      const c = computeCentroid(p);
      return [c.x1, c.x2, c.x3, c.x4, c.x5, c.x6] as Vector6D;
    });

    const { pairs } = buildPolyhedralGraph(this.polyhedra);

    const complex = graphComplex(vectors.length, pairs);
    const lattice = UnitIntervalLattice(this.config.latticeSteps);
    const { edges } = buildPolyhedralGraph(this.polyhedra);
    const edgeScales = new Map<number, number>();
    for (let e = 0; e < edges.length; e++) {
      edgeScales.set(e, edges[e].trustScale);
    }
    const sheaf = twistedSheaf(complex, lattice, edgeScales);

    // Build local assignment from safety scores
    const localAssignment: Cochain<number> = new Map();
    for (let i = 0; i < vectors.length; i++) {
      const normSq = vectors[i].reduce((s, x) => s + x * x, 0);
      localAssignment.set(i, Math.exp(-normSq));
    }

    // Compute cohomology
    const th0 = tarskiCohomology(sheaf, 0, this.config.maxIterations);
    const th1 = complex.maxDim() >= 1
      ? tarskiCohomology(sheaf, 1, this.config.maxIterations)
      : { cochains: new Map<number, number>(), iterations: 0, converged: true, degree: 1 };
    const hh0 = hodgeCohomology(sheaf, 0, this.config.maxIterations);
    const obstructions = detectObstructions(sheaf, localAssignment);
    const diagnostics = analyseCohomology(th0, lattice);

    const totalSeverity = obstructions.reduce((s, o) => s + o.severity, 0);
    const maxPossibleSeverity = Math.max(1, pairs.length);
    const coherenceScore = Math.max(0, 1 - totalSeverity / maxPossibleSeverity);

    const significantObstructions = obstructions.filter((o) => o.severity >= 0.3);
    const riskAmplification = significantObstructions.length > 0
      ? Math.pow(
          this.config.harmonicCoupling,
          significantObstructions.reduce((s, o) => s + o.severity * o.severity, 0)
        )
      : 1;

    let decision: GovernanceDecision;
    if (coherenceScore >= this.config.allowThreshold) {
      decision = 'ALLOW';
    } else if (coherenceScore >= this.config.quarantineThreshold) {
      decision = 'QUARANTINE';
    } else {
      decision = 'DENY';
    }

    return {
      globalSections: th0,
      firstCohomology: th1,
      hodgeSections: hh0,
      obstructions,
      diagnostics,
      coherenceScore,
      riskAmplification,
      decision,
    };
  }

  // ─────────────────────────────────────────────────────────────
  // Determinism & Stability (Validation Battery Test 1)
  // ─────────────────────────────────────────────────────────────

  /**
   * Run a determinism check: same path + same trust → same decision.
   * Returns the fraction of runs that produced identical results.
   *
   * @param path Path to validate
   * @param runs Number of repeated validations (default: 100)
   * @returns Stability ratio ∈ [0, 1] (1.0 = fully deterministic)
   */
  checkDeterminism(path: number[], runs: number = 100): number {
    if (path.length === 0) return 1.0;

    const baseline = this.validatePath(path);
    let matchCount = 0;

    for (let i = 0; i < runs; i++) {
      const result = this.validatePath(path);
      if (
        result.decision === baseline.decision &&
        Math.abs(result.coherenceScore - baseline.coherenceScore) < 1e-10
      ) {
        matchCount++;
      }
    }

    return matchCount / runs;
  }

  // ─────────────────────────────────────────────────────────────
  // Fail-Safe Behavior (Validation Battery Test 5)
  // ─────────────────────────────────────────────────────────────

  /**
   * Test fail-safe: invalid paths must produce DENY, never ALLOW.
   *
   * @param invalidPaths Array of paths that should be rejected
   * @returns Fraction of invalid paths correctly denied
   */
  checkFailSafe(invalidPaths: number[][]): number {
    if (invalidPaths.length === 0) return 1.0;

    let deniedCount = 0;
    for (const path of invalidPaths) {
      const result = this.validatePath(path);
      if (result.decision === 'DENY') {
        deniedCount++;
      }
    }

    return deniedCount / invalidPaths.length;
  }

  // ─────────────────────────────────────────────────────────────
  // Private helpers
  // ─────────────────────────────────────────────────────────────

  /**
   * Check if consecutive pairs in the path share an edge.
   */
  private isPathConnected(path: number[], edges: PolyhedralEdge[]): boolean {
    if (path.length <= 1) return true;

    // Build adjacency set
    const adj = new Set<string>();
    for (const e of edges) {
      adj.add(`${e.from}-${e.to}`);
      adj.add(`${e.to}-${e.from}`);
    }

    for (let i = 0; i < path.length - 1; i++) {
      if (!adj.has(`${path[i]}-${path[i + 1]}`)) {
        return false;
      }
    }
    return true;
  }

  /**
   * Empty path result (trivially allowed).
   */
  private emptyResult(path: number[]): GovernanceRoutingResult {
    return {
      decision: 'ALLOW',
      coherenceScore: 1.0,
      obstructions: [],
      globalSections: {
        cochains: new Map(),
        iterations: 0,
        converged: true,
        degree: 0,
      },
      firstCohomology: {
        cochains: new Map(),
        iterations: 0,
        converged: true,
        degree: 1,
      },
      trustAssignment: [],
      validatedPath: path,
      pathValid: true,
      riskAmplification: 1,
    };
  }

  /**
   * Immediate deny result (e.g., invalid index).
   */
  private denyResult(path: number[], reason: string): GovernanceRoutingResult {
    return {
      decision: 'DENY',
      coherenceScore: 0,
      obstructions: [
        {
          cells: [],
          severity: 1.0,
          description: reason,
        },
      ],
      globalSections: {
        cochains: new Map(),
        iterations: 0,
        converged: true,
        degree: 0,
      },
      firstCohomology: {
        cochains: new Map(),
        iterations: 0,
        converged: true,
        degree: 1,
      },
      trustAssignment: [],
      validatedPath: path,
      pathValid: false,
      riskAmplification: Infinity,
    };
  }
}

// ═══════════════════════════════════════════════════════════════
// Utility: Polyhedral Lattice Analysis
// ═══════════════════════════════════════════════════════════════

/**
 * Compute the Euler characteristic of the polyhedral governance graph.
 * χ = V - E (for 1-dimensional complex)
 */
export function polyhedralEulerCharacteristic(
  polyhedra: Polyhedron[] = CANONICAL_POLYHEDRA
): number {
  const { pairs } = buildPolyhedralGraph(polyhedra);
  return polyhedra.length - pairs.length;
}

/**
 * Build the trust distance matrix for the polyhedral graph.
 * d(i,j) = 1 - trustScale(edge(i,j)), or Infinity if no edge.
 */
export function trustDistanceMatrix(
  polyhedra: Polyhedron[] = CANONICAL_POLYHEDRA
): number[][] {
  const n = polyhedra.length;
  const dist: number[][] = Array.from({ length: n }, () =>
    Array(n).fill(Infinity)
  );

  for (let i = 0; i < n; i++) dist[i][i] = 0;

  const { edges } = buildPolyhedralGraph(polyhedra);
  for (const e of edges) {
    const d = 1 - e.trustScale;
    dist[e.from][e.to] = Math.min(dist[e.from][e.to], d);
    dist[e.to][e.from] = Math.min(dist[e.to][e.from], d);
  }

  // Floyd-Warshall for shortest paths
  for (let k = 0; k < n; k++) {
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        if (dist[i][k] + dist[k][j] < dist[i][j]) {
          dist[i][j] = dist[i][k] + dist[k][j];
        }
      }
    }
  }

  return dist;
}

/**
 * Classify which flux state a path requires.
 * Returns the minimum flux state needed to support all polyhedra in the path.
 */
export function requiredFluxState(
  path: number[],
  polyhedra: Polyhedron[] = CANONICAL_POLYHEDRA
): FluxState {
  const families = new Set(path.map((i) => polyhedra[i]?.family).filter(Boolean));

  // DEMI supports only platonic
  if (families.size === 0 || (families.size === 1 && families.has('platonic'))) {
    return 'DEMI';
  }

  // QUASI supports platonic + archimedean
  const quasiFamilies = new Set<PolyhedronFamily>(['platonic', 'archimedean']);
  if ([...families].every((f) => quasiFamilies.has(f))) {
    return 'QUASI';
  }

  // POLLY required for anything else
  return 'POLLY';
}

// ═══════════════════════════════════════════════════════════════
// Default Instance
// ═══════════════════════════════════════════════════════════════

/**
 * Default PHDM governance router with standard configuration.
 */
export const defaultGovernanceRouter = new PHDMGovernanceRouter();
