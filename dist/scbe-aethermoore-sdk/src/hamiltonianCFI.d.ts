/**
 * SCBE Hamiltonian CFI (Control Flow Integrity)
 *
 * Topological Control Flow Integrity via spectral embedding and golden path detection.
 * - Valid execution = traversal along Hamiltonian "golden path"
 * - Attack = deviation from linearized manifold in embedded space
 * - Detection = spectral embedding + principal curve projection
 *
 * Key Insight: Many 3D graphs are non-Hamiltonian (e.g., Rhombic Dodecahedron
 * with bipartite imbalance |6-8|=2), but lifting to 4D/6D resolves obstructions.
 *
 * Dirac's Theorem: If deg(v) ≥ |V|/2 for all v, graph is Hamiltonian.
 * Ore's Theorem: If deg(u) + deg(v) ≥ |V| for all non-adjacent u,v, graph is Hamiltonian.
 */
/**
 * CFI check result types
 */
export type CFIResult = 'VALID' | 'DEVIATION' | 'ATTACK' | 'OBSTRUCTION';
/**
 * Control Flow Graph vertex
 */
export interface CFGVertex {
    /** Unique vertex ID */
    id: number;
    /** Vertex label/name */
    label: string;
    /** Memory address or instruction pointer */
    address: number;
    /** Optional metadata */
    metadata?: Record<string, unknown>;
}
/**
 * Bipartite analysis result
 */
export interface BipartiteResult {
    /** Whether graph is bipartite */
    isBipartite: boolean;
    /** Set A vertices */
    setA: number[];
    /** Set B vertices */
    setB: number[];
    /** Imbalance |A| - |B| */
    imbalance: number;
}
/**
 * Hamiltonicity check result
 */
export interface HamiltonianCheck {
    /** Whether graph satisfies Dirac's theorem */
    satisfiesDirac: boolean;
    /** Whether graph satisfies Ore's theorem */
    satisfiesOre: boolean;
    /** Minimum vertex degree */
    minDegree: number;
    /** Whether graph is likely Hamiltonian */
    likelyHamiltonian: boolean;
    /** Bipartite analysis */
    bipartite: BipartiteResult;
}
/**
 * Control Flow Graph
 */
export declare class ControlFlowGraph {
    private vertices;
    private edges;
    private adjacency;
    /**
     * Add a vertex to the graph
     */
    addVertex(vertex: CFGVertex): void;
    /**
     * Add an edge between two vertices
     */
    addEdge(from: number, to: number): void;
    /**
     * Get vertex by ID
     */
    getVertex(id: number): CFGVertex | undefined;
    /**
     * Get all vertex IDs
     */
    getVertexIds(): number[];
    /**
     * Get neighbors of a vertex
     */
    getNeighbors(id: number): number[];
    /**
     * Get degree of a vertex
     */
    degree(id: number): number;
    /**
     * Get number of vertices
     */
    get vertexCount(): number;
    /**
     * Get number of edges
     */
    get edgeCount(): number;
    /**
     * Check if edge exists
     */
    hasEdge(from: number, to: number): boolean;
    /**
     * Check if graph is bipartite using BFS coloring
     */
    checkBipartite(): BipartiteResult;
    /**
     * Check Dirac's theorem: deg(v) ≥ |V|/2 for all v
     */
    checkDirac(): boolean;
    /**
     * Check Ore's theorem: deg(u) + deg(v) ≥ |V| for all non-adjacent u,v
     */
    checkOre(): boolean;
    /**
     * Comprehensive Hamiltonicity check
     */
    checkHamiltonian(): HamiltonianCheck;
}
/**
 * Hamiltonian CFI Monitor
 */
export declare class HamiltonianCFI {
    private cfg;
    private goldenPath;
    private currentPosition;
    private deviationThreshold;
    constructor(cfg: ControlFlowGraph, deviationThreshold?: number);
    /**
     * Set the expected "golden path" (valid Hamiltonian traversal)
     */
    setGoldenPath(path: number[]): void;
    /**
     * Compute spectral embedding distance (simplified)
     * In production, use proper Laplacian eigenvectors
     */
    private spectralDistance;
    /**
     * Check if a state vector represents valid execution
     *
     * @param stateVector - Current execution state [vertex_id, ...]
     * @returns CFI result
     */
    checkState(stateVector: number[]): CFIResult;
    /**
     * Reset CFI state
     */
    reset(): void;
    /**
     * Get Hamiltonicity analysis of the CFG
     */
    analyzeGraph(): HamiltonianCheck;
    /**
     * Attempt to find a Hamiltonian path (brute force for small graphs)
     * Returns null if no path found or graph too large
     */
    findHamiltonianPath(maxVertices?: number): number[] | null;
    private dfsHamiltonian;
}
/**
 * Create a CFGVertex helper
 */
export declare function createVertex(id: number, label: string, address: number, metadata?: Record<string, unknown>): CFGVertex;
//# sourceMappingURL=hamiltonianCFI.d.ts.map