/**
 * @file sheafCohomology.ts
 * @module harmonic/sheaf-cohomology
 * @layer Layer 9, Layer 10, Layer 12
 * @component Sheaf Cohomology for Lattices — Tarski Laplacian
 * @version 3.2.4
 *
 * Implements sheaf cohomology on cellular sheaves valued in complete lattices,
 * using the Tarski fixed-point approach:
 *
 *   TH^k(X; F) = Fix(id ∧ L_k) = Post(L_k)
 *
 * where L_k is the Tarski Laplacian — a meet-based diffusion operator on
 * lattice-valued cochains. This generalises vector-valued cellular sheaf
 * cohomology to non-linear settings (lattices with Galois connections).
 *
 * Key structures:
 *   - CompleteLattice<T>: bounded lattice with meet/join/top/bottom
 *   - GaloisConnection<A,B>: adjoint pair (lower ⊣ upper) between lattices
 *   - CellComplex: abstract cell complex (vertices, edges, faces)
 *   - CellularSheaf<T>: sheaf assigning lattice stalks + restriction maps
 *   - tarskiLaplacian: L_k operator via meet over cofaces
 *   - tarskiCohomology: TH^k via greatest post-fixpoint iteration
 *   - hodgeLaplacians: up/down Laplacians L_k^+, L_k^-
 *   - SheafCohomologyEngine: full pipeline integrating with SCBE lattices
 *
 * Mathematical axioms satisfied:
 *   - Symmetry (L5, L9-10): Galois connections preserve order structure
 *   - Composition (L1, L14): Pipeline integrity via sheaf functoriality
 *   - Unitarity (L2, L4): Norm-like coherence via lattice height
 *
 * @see Tarski's Fixed-Point Theorem (1955)
 * @see Curry, Ghrist, Robinson — "Cellular Sheaves of Lattices" (2023)
 */
import { Vector6D } from './constants.js';
/**
 * Complete lattice with bounded meet and join.
 * A complete lattice (L, ≤) has ∧S and ∨S for every subset S ⊆ L.
 */
export interface CompleteLattice<T> {
    /** Greatest element ⊤ */
    readonly top: T;
    /** Least element ⊥ */
    readonly bottom: T;
    /** Binary meet (greatest lower bound): a ∧ b */
    meet(a: T, b: T): T;
    /** Binary join (least upper bound): a ∨ b */
    join(a: T, b: T): T;
    /** Partial order: a ≤ b */
    leq(a: T, b: T): boolean;
    /** Equality test */
    eq(a: T, b: T): boolean;
    /** Lattice height (for convergence bounds) */
    height(): number;
}
/**
 * Galois connection between two complete lattices.
 * A pair (lower ⊣ upper) where:
 *   lower(a) ≤ b  ⟺  a ≤ upper(b)
 *
 * lower preserves joins, upper preserves meets.
 */
export interface GaloisConnection<A, B> {
    /** Left adjoint (lower): preserves joins, maps A → B */
    lower(a: A): B;
    /** Right adjoint (upper): preserves meets, maps B → A */
    upper(b: B): A;
}
/** A cell in the complex, identified by dimension and index */
export interface Cell {
    /** Cell dimension (0 = vertex, 1 = edge, 2 = face, ...) */
    readonly dim: number;
    /** Unique identifier within its dimension */
    readonly id: number;
}
/**
 * Abstract cell complex supporting arbitrary dimensions.
 * Stores incidence relations: which (k-1)-cells are faces of which k-cells.
 */
export interface CellComplex {
    /** All cells of dimension k */
    cells(dim: number): Cell[];
    /** Maximum dimension of any cell */
    maxDim(): number;
    /** Faces of a cell: (k-1)-cells bounding this k-cell */
    faces(cell: Cell): Cell[];
    /** Cofaces of a cell: (k+1)-cells this k-cell bounds */
    cofaces(cell: Cell): Cell[];
    /** Incidence coefficient σ(face, coface): +1 or -1 for orientation */
    incidence(face: Cell, coface: Cell): number;
}
/**
 * Cellular sheaf valued in a complete lattice.
 * Assigns a lattice stalk F(σ) to each cell σ and Galois connections
 * for each face relation σ ≤ τ.
 */
export interface CellularSheaf<T> {
    /** The target lattice */
    readonly lattice: CompleteLattice<T>;
    /** The underlying cell complex */
    readonly complex: CellComplex;
    /** Stalk at cell σ (same lattice for constant sheaf, may vary) */
    stalk(cell: Cell): CompleteLattice<T>;
    /** Restriction map for face relation: F(σ → τ) as Galois connection */
    restriction(face: Cell, coface: Cell): GaloisConnection<T, T>;
}
/** A k-cochain assigns a lattice element to each k-cell */
export type Cochain<T> = Map<number, T>;
/**
 * Create a cochain assigning top to every cell of dimension k.
 */
export declare function topCochain<T>(sheaf: CellularSheaf<T>, dim: number): Cochain<T>;
/**
 * Create a cochain assigning bottom to every cell of dimension k.
 */
export declare function bottomCochain<T>(sheaf: CellularSheaf<T>, dim: number): Cochain<T>;
/**
 * Tarski Laplacian L_k acting on k-cochains.
 *
 * For each k-cell σ:
 *   (L_k x)_σ = ∧_{τ ∈ δσ} F^q_{σ→τ}( ∧_{σ' ∈ ∂τ} F^q_{σ'→τ} x_{σ'} )
 *
 * where δσ = cofaces of σ, ∂τ = faces of τ, and F^q = upper adjoint.
 *
 * This is a monotone operator on the product lattice of k-cochains,
 * so Tarski's theorem guarantees fixed points exist.
 */
export declare function tarskiLaplacian<T>(sheaf: CellularSheaf<T>, dim: number, x: Cochain<T>): Cochain<T>;
/** Result of a cohomology computation */
export interface CohomologyResult<T> {
    /** The cohomology elements (greatest post-fixpoints) */
    readonly cochains: Cochain<T>;
    /** Number of iterations to converge */
    readonly iterations: number;
    /** Whether convergence was reached */
    readonly converged: boolean;
    /** Dimension k of the cohomology group */
    readonly degree: number;
}
/**
 * Compute Tarski cohomology TH^k(X; F) as the greatest post-fixpoint of L_k.
 *
 * Algorithm:
 *   1. Start with x₀ = ⊤ (top cochain)
 *   2. Iterate x_{t+1} = x_t ∧ L_k(x_t)
 *   3. Converges in ≤ h steps where h = lattice height
 *
 * TH^0(X; F) = Γ(X; F) = global sections.
 *
 * @param sheaf The cellular sheaf
 * @param dim Cochain dimension k
 * @param maxIter Maximum iterations (default: lattice height + 10)
 * @returns CohomologyResult with fixed-point cochains
 */
export declare function tarskiCohomology<T>(sheaf: CellularSheaf<T>, dim: number, maxIter?: number): CohomologyResult<T>;
/**
 * Compute global sections Γ(X; F) = TH^0(X; F).
 * These are assignments to vertices consistent across all edges.
 */
export declare function globalSections<T>(sheaf: CellularSheaf<T>): CohomologyResult<T>;
/**
 * Up-Laplacian L_k^+ (diffusion to cofaces only).
 * Acts on k-cochains using (k+1)-dimensional incidence.
 */
export declare function upLaplacian<T>(sheaf: CellularSheaf<T>, dim: number, x: Cochain<T>): Cochain<T>;
/**
 * Down-Laplacian L_k^- (diffusion from faces only).
 * Acts on k-cochains using (k-1)-dimensional incidence.
 *
 * For each k-cell σ:
 *   (L_k^- x)_σ = ∨_{ρ ∈ ∂σ} F_{ρ→σ}^lower( ∨_{σ' ∈ δρ} F_{σ'→ρ... } )
 *
 * Uses join (∨) instead of meet, giving the dual operator.
 */
export declare function downLaplacian<T>(sheaf: CellularSheaf<T>, dim: number, x: Cochain<T>): Cochain<T>;
/**
 * Hodge Laplacian L_k = L_k^+ ∧ L_k^- (meet of up and down).
 */
export declare function hodgeLaplacian<T>(sheaf: CellularSheaf<T>, dim: number, x: Cochain<T>): Cochain<T>;
/**
 * Hodge cohomology HH^k via greatest post-fixpoint of Hodge Laplacian.
 */
export declare function hodgeCohomology<T>(sheaf: CellularSheaf<T>, dim: number, maxIter?: number): CohomologyResult<T>;
/**
 * Boolean lattice {false, true} with ∧ = AND, ∨ = OR.
 * Height = 1. The simplest complete lattice.
 */
export declare const BooleanLattice: CompleteLattice<boolean>;
/**
 * Bounded integer interval lattice [lo, hi] with min/max.
 * Height = hi - lo.
 */
export declare function IntervalLattice(lo: number, hi: number): CompleteLattice<number>;
/**
 * Power-set lattice over n elements, represented as bitmasks.
 * Meet = intersection, Join = union, ⊤ = full set, ⊥ = empty set.
 * Height = n.
 */
export declare function PowerSetLattice(n: number): CompleteLattice<number>;
/**
 * Unit interval lattice [0, 1] with min/max, discretised to `steps` levels.
 * Useful for fuzzy/probabilistic sheaves.
 * Height = steps.
 */
export declare function UnitIntervalLattice(steps?: number): CompleteLattice<number>;
/**
 * Product lattice L₁ × L₂ with component-wise meet/join.
 */
export declare function ProductLattice<A, B>(l1: CompleteLattice<A>, l2: CompleteLattice<B>): CompleteLattice<[A, B]>;
/** Identity connection: both adjoints are identity */
export declare function identityConnection<T>(): GaloisConnection<T, T>;
/** Constant connection: lower maps everything to a fixed element */
export declare function constantConnection<T>(lattice: CompleteLattice<T>, value: T): GaloisConnection<T, T>;
/**
 * Threshold connection for interval lattices:
 *   lower(a) = a ≥ threshold ? a : bottom
 *   upper(b) = b
 */
export declare function thresholdConnection(threshold: number, lattice: CompleteLattice<number>): GaloisConnection<number, number>;
/**
 * Scaling connection for unit-interval lattice:
 *   lower(a) = clamp(a * scale)
 *   upper(b) = clamp(b / scale)
 */
export declare function scalingConnection(scale: number): GaloisConnection<number, number>;
/**
 * Build a cell complex from an undirected graph (vertices + edges).
 * Vertices are 0-cells, edges are 1-cells.
 */
export declare function graphComplex(numVertices: number, edges: [number, number][]): CellComplex;
/**
 * Build a simplicial complex from triangles (vertices + edges + 2-faces).
 */
export declare function simplicialComplex(numVertices: number, edges: [number, number][], triangles: [number, number, number][]): CellComplex;
/**
 * Constant sheaf: every stalk is the same lattice, every restriction is identity.
 */
export declare function constantSheaf<T>(complex: CellComplex, lattice: CompleteLattice<T>): CellularSheaf<T>;
/**
 * Threshold sheaf on a graph: edges enforce agreement above a threshold.
 * If a vertex value is below threshold, the edge restriction maps it to ⊥.
 */
export declare function thresholdSheaf(complex: CellComplex, lattice: CompleteLattice<number>, threshold: number): CellularSheaf<number>;
/**
 * Twisted sheaf: each edge has a custom scaling factor.
 * Useful for modelling trust decay or risk amplification across graph.
 */
export declare function twistedSheaf(complex: CellComplex, lattice: CompleteLattice<number>, edgeScales: Map<number, number>): CellularSheaf<number>;
/** Diagnostic summary of a cohomology computation */
export interface CohomologyDiagnostics<T> {
    /** Betti-like number: count of non-trivial fixed-point components */
    readonly bettiNumber: number;
    /** Maximum element in the cohomology cochain */
    readonly maxElement: T;
    /** Minimum element in the cohomology cochain */
    readonly minElement: T;
    /** Whether all cells have the same value (globally consistent) */
    readonly isGloballyConsistent: boolean;
    /** Height utilisation: fraction of lattice height used */
    readonly heightUtilisation: number;
}
/**
 * Analyse a cohomology result and produce diagnostics.
 */
export declare function analyseCohomology<T>(result: CohomologyResult<T>, lattice: CompleteLattice<T>): CohomologyDiagnostics<T>;
/** An obstruction to extending local sections to global ones */
export interface Obstruction {
    /** The cells involved in the obstruction */
    readonly cells: Cell[];
    /** Severity: 0 = no obstruction, 1 = total blockage */
    readonly severity: number;
    /** Description */
    readonly description: string;
}
/**
 * Detect obstructions to global consistency in a sheaf.
 * Compares TH^0 (global sections) against vertex assignments to find
 * where local data fails to glue.
 */
export declare function detectObstructions<T>(sheaf: CellularSheaf<T>, localAssignment: Cochain<T>): Obstruction[];
/** Configuration for the SCBE sheaf cohomology engine */
export interface SheafCohomologyConfig {
    /** Number of lattice discretisation steps (default: 100) */
    latticeSteps?: number;
    /** Maximum cohomology iterations (default: lattice height + 10) */
    maxIterations?: number;
    /** Obstruction severity threshold for risk escalation (default: 0.5) */
    obstructionThreshold?: number;
    /** Golden ratio coupling for harmonic scaling (default: PHI) */
    harmonicCoupling?: number;
}
/** Result from the SCBE sheaf cohomology engine */
export interface SheafAnalysisResult {
    /** Tarski cohomology TH^0 (global sections) */
    readonly globalSections: CohomologyResult<number>;
    /** Tarski cohomology TH^1 (first obstruction) */
    readonly firstCohomology: CohomologyResult<number>;
    /** Hodge cohomology HH^0 (for comparison) */
    readonly hodgeSections: CohomologyResult<number>;
    /** Obstructions detected */
    readonly obstructions: Obstruction[];
    /** Diagnostics for TH^0 */
    readonly diagnostics: CohomologyDiagnostics<number>;
    /** Coherence score [0, 1]: 1 = fully consistent, 0 = maximal obstruction */
    readonly coherenceScore: number;
    /** Risk amplification factor from obstructions */
    readonly riskAmplification: number;
}
/**
 * SCBE Sheaf Cohomology Engine.
 *
 * Integrates Tarski cohomology with the 14-layer pipeline:
 * - Builds a graph complex from SCBE 6D vector topology
 * - Assigns lattice-valued stalks capturing safety scores
 * - Computes TH^0 (global consensus) and TH^1 (obstruction detection)
 * - Maps obstructions to risk amplification for Layer 12/13
 *
 * Usage:
 *   const engine = new SheafCohomologyEngine();
 *   const result = engine.analyseVectorField(vectors, edges);
 */
export declare class SheafCohomologyEngine {
    private readonly config;
    private readonly lattice;
    constructor(config?: SheafCohomologyConfig);
    /**
     * Analyse a field of 6D vectors connected by edges.
     * Each vector is projected to a safety score in [0, 1] via its norm.
     * Edges carry scaling connections weighted by PHI-based distances.
     *
     * @param vectors Array of 6D vectors (vertex data)
     * @param edges Pairs of vertex indices forming edges
     * @returns Full sheaf analysis with cohomology and obstructions
     */
    analyseVectorField(vectors: Vector6D[], edges: [number, number][]): SheafAnalysisResult;
    /**
     * Quick coherence check: returns true if the vector field has no
     * significant obstructions (all local data glues globally).
     */
    isCoherent(vectors: Vector6D[], edges: [number, number][]): boolean;
    /**
     * Compute the Euler characteristic of the cohomology:
     *   χ = Σ (-1)^k · |TH^k|
     *
     * For a graph (max dim 1): χ = |TH^0| - |TH^1|
     */
    eulerCharacteristic(analysis: SheafAnalysisResult): number;
}
/**
 * Default sheaf cohomology engine with standard configuration.
 */
export declare const defaultSheafEngine: SheafCohomologyEngine;
//# sourceMappingURL=sheafCohomology.d.ts.map