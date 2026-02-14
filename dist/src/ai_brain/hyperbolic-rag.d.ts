/**
 * @file hyperbolic-rag.ts
 * @module ai_brain/hyperbolic-rag
 * @layer Layer 5, Layer 12, Layer 13
 * @version 1.0.0
 *
 * HyperbolicRAG: Nearest-neighbor retrieval in the Poincare ball with d* cost gating.
 *
 * Turns the Poincare ball into a governed retrieval engine:
 * - k-NN search via hyperbolic distance (arcosh metric)
 * - d* cost gating: high-cost candidates are quarantined (Layer 12 wall)
 * - Phase alignment: tongue-phase consistency filters off-grammar chunks
 * - Realm overlap: octree-based spatial overlap scoring from quasi-space
 *
 * Integrates with GeoSeal (immune dynamics) and the 14-layer pipeline
 * (Layer 12 harmonic wall provides cost threshold, Layer 13 risk decision).
 */
/** A candidate chunk for RAG retrieval */
export interface RAGCandidate {
    id: string;
    embedding: number[];
    tongue?: string;
    metadata?: Record<string, unknown>;
}
/** Scored retrieval result after d* gating */
export interface RAGResult {
    id: string;
    /** Hyperbolic distance to query */
    distance: number;
    /** Trust score: inverse of normalized cost */
    trust_score: number;
    /** Phase alignment score [0, 1] */
    phase_score: number;
    /** Whether this candidate was gated (quarantined) */
    gated: boolean;
    metadata?: Record<string, unknown>;
}
/** Configuration for HyperbolicRAG retrieval */
export interface HyperbolicRAGConfig {
    /** Maximum candidates to return */
    maxK: number;
    /** d* cost threshold - candidates above this are gated (Layer 12 wall) */
    costThreshold: number;
    /** Minimum phase alignment to pass (0 = accept all, 1 = exact match only) */
    minPhaseAlignment: number;
    /** Weight for phase in combined scoring (0 = ignore phase) */
    phaseWeight: number;
}
export declare const DEFAULT_RAG_CONFIG: HyperbolicRAGConfig;
export declare class HyperbolicRAG {
    private config;
    constructor(config?: Partial<HyperbolicRAGConfig>);
    /**
     * Perform hyperbolic k-NN retrieval with cost gating.
     *
     * 1. Project all embeddings to Poincare ball
     * 2. Compute hyperbolic distances from query
     * 3. Sort by distance, take top-k
     * 4. Gate by d* cost threshold (Layer 12 harmonic wall)
     * 5. Filter by phase alignment (tongue discipline)
     * 6. Return scored results
     *
     * @param queryEmbedding - Query vector (will be projected to ball)
     * @param candidates - Candidate chunks with embeddings
     * @param queryTongue - Optional tongue for phase-based filtering
     * @returns Sorted RAGResult array (trusted candidates only)
     */
    retrieve(queryEmbedding: number[], candidates: RAGCandidate[], queryTongue?: string): RAGResult[];
    /**
     * Retrieve and return all results (including gated), for diagnostics.
     */
    retrieveAll(queryEmbedding: number[], candidates: RAGCandidate[], queryTongue?: string): RAGResult[];
    /**
     * Update configuration at runtime (e.g., adjust cost threshold).
     */
    updateConfig(partial: Partial<HyperbolicRAGConfig>): void;
    /**
     * Get current configuration.
     */
    getConfig(): Readonly<HyperbolicRAGConfig>;
}
//# sourceMappingURL=hyperbolic-rag.d.ts.map