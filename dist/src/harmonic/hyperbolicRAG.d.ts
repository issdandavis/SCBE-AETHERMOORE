/**
 * @file hyperbolicRAG.ts
 * @module harmonic/hyperbolicRAG
 * @layer Layer 5, Layer 7, Layer 12, Layer 13
 * @component HyperbolicRAG — Poincaré Ball Retrieval-Augmented Generation
 * @version 3.2.4
 *
 * Nearest-neighbor retrieval in the Poincaré ball where access cost
 * (harmonic wall) gates what enters context. Documents closer to the
 * origin (trust center) are cheaper to retrieve; documents near the
 * boundary are exponentially expensive, making adversarial injection
 * into context computationally infeasible.
 *
 * Key invariants:
 *   1. accessCost(d*) >= 1 for all retrievals (minimum cost = 1)
 *   2. accessCost grows as phi^d / (1 + e^{-R}) near boundary
 *   3. Context budget enforces a hard cap on total retrieval cost
 *   4. Phase alignment gates relevance — wrong-phase docs are filtered
 *
 * Builds on:
 *   - hyperbolic.ts: Poincaré ball ops (L5-L7)
 *   - harmonicScaling.ts: harmonicScale (L12)
 *   - adaptiveNavigator.ts: realm centers, trajectoryEntropy (L5, L13)
 */
/** A document embedded in the Poincaré ball for retrieval. */
export interface RAGDocument {
    /** Unique identifier */
    id: string;
    /** Position in Poincaré ball (any dimension, must match query) */
    embedding: number[];
    /** Phase angle for tongue alignment (radians, or null if unclassified) */
    phase: number | null;
    /** Optional metadata */
    metadata?: Record<string, unknown>;
    /** Timestamp of insertion (ms since epoch) */
    insertedAt: number;
}
/** Result of a single retrieval with cost accounting. */
export interface RetrievalResult {
    /** Document id */
    id: string;
    /** Trust-distance score in (0, 1] — higher is more trusted */
    trustScore: number;
    /** Access cost for this retrieval — phi^d gated */
    accessCost: number;
    /** Phase-distance score from scoreRetrievals */
    relevanceScore: number;
    /** Combined rank score (relevance / accessCost) */
    rankScore: number;
    /** The original document */
    document: RAGDocument;
}
/** Configuration for the RAG engine. */
export interface HyperbolicRAGConfig {
    /** Maximum total access cost budget per query (default: 20.0) */
    contextBudget: number;
    /** Maximum number of documents to return (default: 10) */
    maxResults: number;
    /** Minimum relevance score to include (default: 0.1) */
    minRelevance: number;
    /** Phase weight for scoring (default: 2.0) */
    phaseWeight: number;
    /** Access cost base — controls exponential steepness (default: PHI) */
    costBase: number;
    /** Risk amplification factor for boundary documents (default: 1.0) */
    riskAmplification: number;
    /** Maximum age for documents in ms (0 = no limit, default: 0) */
    maxAge: number;
    /** Dimension of the Poincaré ball (default: 6) */
    dimension: number;
}
/** Summary of a retrieval batch. */
export interface RetrievalSummary {
    /** Documents returned, ranked by rankScore descending */
    results: RetrievalResult[];
    /** Total access cost consumed */
    totalCost: number;
    /** Remaining budget */
    remainingBudget: number;
    /** Number of candidates considered */
    candidatesConsidered: number;
    /** Number of candidates rejected by phase/relevance filter */
    filteredOut: number;
    /** Number of candidates rejected by budget exhaustion */
    budgetExhausted: number;
    /** Query position norm (distance from trust center) */
    queryNorm: number;
}
/**
 * Compute the access cost for retrieving a document at hyperbolic
 * distance `d` from the query. Cost grows exponentially with distance,
 * making adversarial documents near the boundary infeasible to include.
 *
 * Formula: accessCost = base^d * (1 + riskAmp * (1 - harmonicScale(d)))
 *
 * @param d - Hyperbolic distance from query to document
 * @param base - Exponential base (default: PHI)
 * @param riskAmplification - Risk scaling factor (default: 1.0)
 * @returns Access cost >= 1
 */
export declare function accessCost(d: number, base?: number, riskAmplification?: number): number;
/**
 * Compute trust from a position's distance to the origin.
 * Mirrors geo_seal.py trust_from_position.
 *
 * @param point - Position in Poincaré ball
 * @returns Trust in (0, 1]
 */
export declare function trustFromPosition(point: number[]): number;
/**
 * Retrieval-Augmented Generation engine using Poincaré ball geometry.
 *
 * Documents are embedded in the Poincaré ball. Retrieval uses hyperbolic
 * distance + phase alignment for relevance, and the harmonic wall
 * (accessCost) to gate what enters context. A fixed context budget
 * ensures that including adversarial (boundary-positioned) documents
 * exhausts the budget, protecting the downstream model.
 */
export declare class HyperbolicRAGEngine {
    private readonly config;
    private readonly index;
    constructor(config?: Partial<HyperbolicRAGConfig>);
    /**
     * Add a document to the index. The embedding must be inside the
     * Poincaré ball (norm < 1). If not, it is projected via
     * projectEmbeddingToBall.
     */
    addDocument(doc: RAGDocument): void;
    /**
     * Add multiple documents at once.
     */
    addDocuments(docs: RAGDocument[]): void;
    /**
     * Remove a document by id.
     * @returns true if the document was found and removed
     */
    removeDocument(id: string): boolean;
    /**
     * Get the number of indexed documents.
     */
    get size(): number;
    /**
     * Clear all documents from the index.
     */
    clear(): void;
    /**
     * Retrieve a document by id (or undefined if not found).
     */
    getDocument(id: string): RAGDocument | undefined;
    /**
     * Retrieve documents relevant to a query, gated by access cost.
     *
     * Algorithm:
     *   1. Project query into the Poincaré ball
     *   2. Compute hyperbolic distance + phase-distance score for each doc
     *   3. Filter by minimum relevance and max age
     *   4. Compute access cost for each candidate
     *   5. Rank by rankScore = relevanceScore / accessCost
     *   6. Greedily fill context budget in rank order
     *
     * @param queryEmbedding - Query vector (will be projected to ball)
     * @param queryPhase - Query phase angle (radians, or null)
     * @returns RetrievalSummary with ranked, cost-gated results
     */
    retrieve(queryEmbedding: number[], queryPhase: number | null): RetrievalSummary;
    /**
     * Retrieve using tongue-aligned query — projects the query toward
     * the specified Sacred Tongue realm center before retrieval.
     *
     * @param queryEmbedding - Raw query vector
     * @param queryPhase - Query phase
     * @param tongue - Sacred Tongue code (KO, AV, RU, CA, UM, DR)
     * @param tongueInfluence - How much to bias toward tongue center (0-1, default: 0.3)
     */
    retrieveByTongue(queryEmbedding: number[], queryPhase: number | null, tongue: string, tongueInfluence?: number): RetrievalSummary;
    /**
     * Compute the maximum number of documents retrievable from a given
     * position before exhausting the context budget. Useful for capacity
     * planning.
     *
     * @param position - Position in the Poincaré ball
     * @param avgDocDistance - Average hyperbolic distance to docs (default: 1.0)
     */
    estimateCapacity(position: number[], avgDocDistance?: number): number;
    /**
     * Find k nearest neighbors by hyperbolic distance (no cost gating).
     * Useful for diagnostics and visualization.
     */
    kNearest(queryEmbedding: number[], k: number): Array<{
        id: string;
        distance: number;
        doc: RAGDocument;
    }>;
    /**
     * Ensure a vector is inside the Poincaré ball. If norm >= 1,
     * project using the smooth tanh mapping.
     */
    private ensureInBall;
}
/**
 * Create a pre-configured HyperbolicRAG engine.
 */
export declare function createHyperbolicRAG(config?: Partial<HyperbolicRAGConfig>): HyperbolicRAGEngine;
//# sourceMappingURL=hyperbolicRAG.d.ts.map