/**
 * @file hyperbolicRAG.ts
 * @module harmonic/hyperbolicRAG
 * @layer Layer 5, Layer 12, Layer 13
 * @component Hyperbolic Retrieval-Augmented Generation — GeoSeal v2 Scorer
 * @version 3.2.4
 *
 * Retrieval scoring in the Poincaré ball where trust-distance gates what enters
 * context. Replaces hand-tuned "repulsion + suspicion counters" with a
 * geometry-aware three-signal fusion:
 *
 *   1. Hyperbolic proximity: d_H(query, chunk), d_H(anchor, chunk)
 *   2. Phase consistency:    phase deviation across 6 tongues
 *   3. Uncertainty:          variance proxy for retrieval confidence
 *
 * Output per chunk: { trustScore, anomalyProb, quarantineFlag, attentionWeight }
 *
 * Design: This is a *scoring engine*, not the whole security system.
 * Crypto gates (RWP), dialect grammar, and audio axis remain unchanged.
 */
import type { Vector6D } from './constants.js';
import { type TongueImpedance } from './chsfn.js';
/**
 * A retrieval chunk projected into the Poincaré ball.
 *
 * Raw embeddings (e.g. 768-dim) are projected via tanh mapping
 * before entering this pipeline. The 6D projection aligns with
 * the Sacred Tongue basis.
 */
export interface HyperbolicChunk {
    /** Unique chunk identifier */
    chunkId: string;
    /** Position in 6D Poincaré ball (‖p‖ < 1) */
    position: Vector6D;
    /** Phase features per tongue [cos(θ), sin(θ)] flattened to 6 values */
    phase: Vector6D;
    /** Uncertainty estimate (higher = less confident). Variance proxy. */
    uncertainty: number;
    /** Optional: original embedding norm before projection (for calibration) */
    originalNorm?: number;
}
/**
 * Trust score output for a single retrieval chunk.
 */
export interface ChunkTrustScore {
    /** Chunk identifier */
    chunkId: string;
    /** Trust score in [0, 1]: 1 = fully trusted, 0 = adversarial */
    trustScore: number;
    /** Anomaly probability in [0, 1]: likelihood this is foreign/poisoned */
    anomalyProb: number;
    /** Whether this chunk should be quarantined (blocked from context) */
    quarantineFlag: boolean;
    /** Attention weight for context assembly (higher = more influence) */
    attentionWeight: number;
    /** Individual signal components for interpretability */
    signals: {
        /** Hyperbolic proximity score [0, 1] */
        proximityScore: number;
        /** Phase consistency score [0, 1] */
        phaseScore: number;
        /** Uncertainty penalty [0, 1] */
        uncertaintyPenalty: number;
        /** Hyperbolic distance to query */
        distanceToQuery: number;
        /** Hyperbolic distance to nearest tongue anchor */
        distanceToAnchor: number;
    };
}
/**
 * Configuration for the RAG scorer.
 */
export interface RAGScorerConfig {
    /** Hyperbolic distance above which trust drops to near-zero (default 3.0) */
    maxTrustDistance: number;
    /** Phase coherence threshold below which anomaly is flagged (default 0.4) */
    minPhaseCoherence: number;
    /** Uncertainty threshold above which quarantine is triggered (default 0.7) */
    maxUncertainty: number;
    /** Weight for proximity signal in fusion (default 0.5) */
    weightProximity: number;
    /** Weight for phase signal in fusion (default 0.3) */
    weightPhase: number;
    /** Weight for uncertainty signal in fusion (default 0.2) */
    weightUncertainty: number;
    /** Trust score below which quarantine is triggered (default 0.3) */
    quarantineThreshold: number;
    /** Tongue impedance weights for phase scoring */
    impedance: TongueImpedance;
}
export declare const DEFAULT_RAG_CONFIG: Readonly<RAGScorerConfig>;
/**
 * Project an arbitrary-dimensional embedding into the 6D Poincaré ball.
 *
 * Uses tanh mapping: u = tanh(α·‖x‖) · x / (‖x‖ + ε)
 *
 * For high-dim embeddings (768, 1536, etc.), we first reduce to 6D
 * by chunked averaging (each of the 6 dims gets avg of dim/6 components).
 *
 * @param embedding - Raw embedding vector of any dimension >= 6
 * @param scale - Contraction factor α (default 0.5) — controls how
 *                compressed the projection is. Lower = more centered.
 * @returns 6D position inside the Poincaré ball
 */
export declare function projectToBall(embedding: number[], scale?: number): Vector6D;
/**
 * Extract phase features from an embedding.
 *
 * Maps each tongue's chunk of the embedding to an angle via atan2
 * of even/odd component averages.
 *
 * @param embedding - Raw embedding vector
 * @returns Phase vector [θ_KO, θ_AV, θ_RU, θ_CA, θ_DR, θ_UM]
 */
export declare function extractPhase(embedding: number[]): Vector6D;
/**
 * Estimate uncertainty from an embedding using variance of components.
 *
 * Higher variance ≈ more spread-out representation ≈ less confident.
 * Normalized to [0, 1] via sigmoid.
 *
 * @param embedding - Raw embedding vector
 * @returns Uncertainty in [0, 1]
 */
export declare function estimateUncertainty(embedding: number[]): number;
/**
 * Build a HyperbolicChunk from a raw embedding.
 *
 * Convenience function that runs projection + phase extraction + uncertainty.
 *
 * @param chunkId - Unique identifier
 * @param embedding - Raw embedding vector (any dimension >= 6)
 * @param scale - Poincaré ball projection scale
 * @returns HyperbolicChunk ready for scoring
 */
export declare function buildChunk(chunkId: string, embedding: number[], scale?: number): HyperbolicChunk;
/**
 * The 6 tongue anchors in the Poincaré ball.
 *
 * Each tongue occupies a canonical position along its primary axis.
 * These are the "safe poles" — trusted retrieval should cluster near these.
 */
export declare const TONGUE_ANCHORS: Readonly<Record<string, Vector6D>>;
/**
 * Find the nearest tongue anchor to a position.
 *
 * @param position - 6D position in Poincaré ball
 * @returns { tongue, distance } of nearest anchor
 */
export declare function nearestTongueAnchor(position: Vector6D): {
    tongue: string;
    distance: number;
};
/**
 * Compute hyperbolic proximity score.
 *
 * Score = 1 / (1 + accessCost(d_H(query, chunk)))
 *
 * Near query → high score; far → near-zero (exponential decay).
 *
 * @param queryPos - Query position in ball
 * @param chunkPos - Chunk position in ball
 * @param maxDist - Distance at which score is effectively zero
 * @returns Proximity score in [0, 1]
 */
export declare function proximityScore(queryPos: Vector6D, chunkPos: Vector6D, maxDist?: number): number;
/**
 * Compute phase consistency score.
 *
 * Average cosine similarity between chunk phase and expected tongue phases.
 * Measures whether the chunk "speaks the right language."
 *
 * @param chunkPhase - Phase vector of the chunk
 * @param queryPhase - Phase vector of the query (or expected alignment)
 * @returns Phase score in [0, 1]
 */
export declare function phaseConsistencyScore(chunkPhase: Vector6D, queryPhase: Vector6D): number;
/**
 * Compute uncertainty penalty.
 *
 * Higher uncertainty → higher penalty → lower trust.
 *
 * @param uncertainty - Chunk uncertainty in [0, 1]
 * @returns Penalty in [0, 1] where 0 = no penalty, 1 = max penalty
 */
export declare function uncertaintyPenalty(uncertainty: number): number;
/**
 * Score a single retrieval chunk against a query.
 *
 * Three-signal fusion:
 *   trustScore = w_p · proximity + w_φ · phase - w_u · uncertainty
 *   anomalyProb = 1 - trustScore
 *   quarantine if trustScore < threshold
 *   attentionWeight = trustScore² (soft gating)
 *
 * @param query - Query state (position + phase)
 * @param chunk - Retrieval chunk
 * @param config - Scorer configuration
 * @returns ChunkTrustScore
 */
export declare function scoreChunk(query: {
    position: Vector6D;
    phase: Vector6D;
}, chunk: HyperbolicChunk, config?: RAGScorerConfig): ChunkTrustScore;
/**
 * Score all retrieval candidates and return trust-gated results.
 *
 * @param query - Query state
 * @param chunks - Candidate chunks (pre-projected into ball)
 * @param topK - Max results to return (default 10)
 * @param config - Scorer configuration
 * @returns Sorted array of trust scores (highest trust first), quarantined removed
 */
export declare function scoreAndFilter(query: {
    position: Vector6D;
    phase: Vector6D;
}, chunks: HyperbolicChunk[], topK?: number, config?: RAGScorerConfig): ChunkTrustScore[];
/**
 * Full retrieval pipeline: project raw embeddings → score → filter → return.
 *
 * @param queryEmbedding - Raw query embedding
 * @param candidateEmbeddings - Array of { id, embedding } pairs
 * @param topK - Number of results
 * @param config - Scorer config
 * @param scale - Projection scale
 * @returns Trust-gated scored results
 */
export declare function retrieveWithTrust(queryEmbedding: number[], candidateEmbeddings: Array<{
    id: string;
    embedding: number[];
}>, topK?: number, config?: RAGScorerConfig, scale?: number): ChunkTrustScore[];
/**
 * Score all chunks and return quarantine analytics.
 *
 * @param query - Query state
 * @param chunks - All chunks
 * @param config - Config
 * @returns { trusted, quarantined, stats }
 */
export declare function quarantineReport(query: {
    position: Vector6D;
    phase: Vector6D;
}, chunks: HyperbolicChunk[], config?: RAGScorerConfig): {
    trusted: ChunkTrustScore[];
    quarantined: ChunkTrustScore[];
    stats: {
        total: number;
        trustedCount: number;
        quarantinedCount: number;
        avgTrustScore: number;
        avgAnomalyProb: number;
        quarantineRate: number;
    };
};
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