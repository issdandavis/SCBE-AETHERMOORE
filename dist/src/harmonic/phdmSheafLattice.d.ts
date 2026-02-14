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
import { type FluxState, type Polyhedron } from './phdm.js';
import { type CellComplex, type CellularSheaf, type CohomologyResult, type Obstruction, type SheafAnalysisResult } from './sheafCohomology.js';
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
export declare function buildPolyhedralGraph(polyhedra?: Polyhedron[]): {
    edges: PolyhedralEdge[];
    pairs: [number, number][];
};
/**
 * Compute a trust score for each polyhedron based on its family tier
 * and topological properties. Score ∈ [0, 1].
 *
 * Trust = familyTrust * topologicalFactor
 * where topologicalFactor penalises non-zero genus (g > 0 = riskier).
 */
export declare function computePolyhedralTrust(polyhedra?: Polyhedron[]): number[];
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
export declare function buildGovernanceSheaf(polyhedra?: Polyhedron[], latticeSteps?: number): {
    sheaf: CellularSheaf<number>;
    complex: CellComplex;
    edges: PolyhedralEdge[];
};
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
export declare class PHDMGovernanceRouter {
    private readonly config;
    private readonly polyhedra;
    private readonly trustScores;
    private readonly lattice;
    private _fluxState;
    constructor(config?: GovernanceRouterConfig, fluxState?: FluxState);
    /**
     * Get the current flux state.
     */
    get fluxState(): FluxState;
    /**
     * Get the active polyhedra under the current flux state.
     */
    getActivePolyhedra(): Polyhedron[];
    /**
     * Get trust scores for all active polyhedra.
     */
    getTrustScores(): number[];
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
    validatePath(path: number[], customTrust?: number[]): GovernanceRoutingResult;
    /**
     * Quick coherence check: is a path globally consistent?
     */
    isCoherent(path: number[]): boolean;
    /**
     * Validate a transition from one polyhedral region to another.
     * Checks whether a single step between two polyhedra is allowed.
     */
    validateTransition(from: number, to: number): GovernanceRoutingResult;
    /**
     * Analyse the full polyhedral lattice for global coherence.
     * Returns the sheaf analysis for all polyhedra simultaneously.
     */
    analyseFullLattice(): SheafAnalysisResult & {
        decision: GovernanceDecision;
    };
    /**
     * Run a determinism check: same path + same trust → same decision.
     * Returns the fraction of runs that produced identical results.
     *
     * @param path Path to validate
     * @param runs Number of repeated validations (default: 100)
     * @returns Stability ratio ∈ [0, 1] (1.0 = fully deterministic)
     */
    checkDeterminism(path: number[], runs?: number): number;
    /**
     * Test fail-safe: invalid paths must produce DENY, never ALLOW.
     *
     * @param invalidPaths Array of paths that should be rejected
     * @returns Fraction of invalid paths correctly denied
     */
    checkFailSafe(invalidPaths: number[][]): number;
    /**
     * Check if consecutive pairs in the path share an edge.
     */
    private isPathConnected;
    /**
     * Empty path result (trivially allowed).
     */
    private emptyResult;
    /**
     * Immediate deny result (e.g., invalid index).
     */
    private denyResult;
}
/**
 * Compute the Euler characteristic of the polyhedral governance graph.
 * χ = V - E (for 1-dimensional complex)
 */
export declare function polyhedralEulerCharacteristic(polyhedra?: Polyhedron[]): number;
/**
 * Build the trust distance matrix for the polyhedral graph.
 * d(i,j) = 1 - trustScale(edge(i,j)), or Infinity if no edge.
 */
export declare function trustDistanceMatrix(polyhedra?: Polyhedron[]): number[][];
/**
 * Classify which flux state a path requires.
 * Returns the minimum flux state needed to support all polyhedra in the path.
 */
export declare function requiredFluxState(path: number[], polyhedra?: Polyhedron[]): FluxState;
/**
 * Default PHDM governance router with standard configuration.
 */
export declare const defaultGovernanceRouter: PHDMGovernanceRouter;
//# sourceMappingURL=phdmSheafLattice.d.ts.map