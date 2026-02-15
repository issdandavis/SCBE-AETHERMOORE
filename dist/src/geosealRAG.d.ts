/**
 * @file geosealRAG.ts
 * @module geosealRAG
 * @layer Layer 9, Layer 12, Layer 13
 * @version 1.0.0
 *
 * GeoSeal RAG Integration - Immune filtering for retrieval-augmented generation.
 *
 * Converts retrieved chunks and tool outputs into agents, runs swarm dynamics,
 * and returns trust-weighted attention scores. Integrates with Sacred Tongues
 * phase system and Spiralverse envelope IDs.
 *
 * Three-level integration:
 * 1. Per-retrieval/per-tool-call: Single-step phase validation
 * 2. Within-thought swarm: 5-15 micro-step dynamics per reasoning step
 * 3. Memory layer: Long-term probation for new memories
 */
import { Agent } from './geoseal.js';
/** Embedding function signature (plug in your model) */
export type EmbedFn = (text: string) => Promise<number[]>;
/** Retrieval candidate from a vector store */
export interface RetrievalCandidate {
    text: string;
    envelopeId: string;
    tongue?: string;
}
/** GeoSeal filter context for a single RAG query */
export interface GeoSealRAGContext {
    query_embedding: number[];
    tongue_agents: Agent[];
    retrieval_agents: Agent[];
    memory_agents: Agent[];
}
/** Filter result with trust scores */
export interface GeoSealFilterResult {
    attention_weights: Map<string, number>;
    quarantined_ids: string[];
    total_agents: number;
}
/**
 * Get semantic domain text for a tongue (used to generate embedding).
 */
export declare function getTongueDomain(tongue: string): string;
/**
 * Initialize Sacred Tongues as legitimate agents.
 *
 * Each tongue gets a position based on its semantic domain and its
 * canonical phase from TONGUE_PHASES. These start fully trusted.
 *
 * @param embedFn - Function to embed text into a vector
 * @returns Array of 6 tongue agents
 */
export declare function initTongueAgents(embedFn: EmbedFn): Promise<Agent[]>;
/**
 * Convert retrieved chunks into agents for immune evaluation.
 *
 * Chunks with a known tongue get the corresponding phase;
 * unknown chunks get null phase (maximum suspicion amplification).
 *
 * @param retrievals - Retrieved chunks with text and envelope IDs
 * @param embedFn - Function to embed text into a vector
 * @param assigned_tongue - Optional tongue to assign to all retrievals
 * @returns Array of retrieval agents (trust starts at 0.5)
 */
export declare function retrievalsToAgents(retrievals: RetrievalCandidate[], embedFn: EmbedFn, assigned_tongue?: string): Promise<Agent[]>;
/**
 * Run GeoSeal immune dynamics on RAG context.
 *
 * Combines tongue agents (trusted anchors), retrieval agents (candidates),
 * and memory agents (long-term probation) into a single swarm. After
 * num_steps of repulsion dynamics, returns trust scores for all
 * non-tongue agents.
 *
 * @param context - GeoSeal RAG context with all agent sets
 * @param num_steps - Number of swarm iterations (default 10)
 * @param drift_rate - Force application rate (default 0.01)
 * @returns Filter result with attention weights and quarantined IDs
 */
export declare function geoSealFilter(context: GeoSealRAGContext, num_steps?: number, drift_rate?: number): GeoSealFilterResult;
/**
 * Convenience: Build a full GeoSeal RAG context and run the filter.
 *
 * @param query - Query text
 * @param retrievals - Retrieved chunks
 * @param embedFn - Embedding function
 * @param tongue - Optional tongue for retrieval assignment
 * @param num_steps - Swarm iterations
 * @returns Filter result
 */
export declare function filterRetrievals(query: string, retrievals: RetrievalCandidate[], embedFn: EmbedFn, tongue?: string, num_steps?: number): Promise<GeoSealFilterResult>;
//# sourceMappingURL=geosealRAG.d.ts.map