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

import { Agent, TONGUE_PHASES, createAgent, runSwarm } from './geoseal.js';
import { projectEmbeddingToBall } from './harmonic/hyperbolic.js';

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

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

// ═══════════════════════════════════════════════════════════════
// Tongue domain text (for generating tongue agent embeddings)
// ═══════════════════════════════════════════════════════════════

const TONGUE_DOMAINS: Record<string, string> = {
  KO: 'workflow orchestration control coordination command execution',
  AV: 'message transport initialization network communication protocol',
  RU: 'policy authorization access control security rules governance',
  CA: 'computation logic encryption data processing transformation',
  UM: 'privacy redaction security secrets protection renewal',
  DR: 'authentication integrity schema validation verification',
};

/**
 * Get semantic domain text for a tongue (used to generate embedding).
 */
export function getTongueDomain(tongue: string): string {
  return TONGUE_DOMAINS[tongue] || '';
}

// ═══════════════════════════════════════════════════════════════
// Agent construction helpers
// ═══════════════════════════════════════════════════════════════

/**
 * Initialize Sacred Tongues as legitimate agents.
 *
 * Each tongue gets a position based on its semantic domain and its
 * canonical phase from TONGUE_PHASES. These start fully trusted.
 *
 * @param embedFn - Function to embed text into a vector
 * @returns Array of 6 tongue agents
 */
export async function initTongueAgents(embedFn: EmbedFn): Promise<Agent[]> {
  const tongues = Object.keys(TONGUE_PHASES);
  const agents: Agent[] = [];

  for (const tongue of tongues) {
    const domain_text = getTongueDomain(tongue);
    const rawEmbedding = await embedFn(domain_text);
    const position = projectEmbeddingToBall(rawEmbedding);

    agents.push(
      createAgent(`tongue-${tongue}`, position, TONGUE_PHASES[tongue], tongue, 1.0)
    );
  }

  return agents;
}

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
export async function retrievalsToAgents(
  retrievals: RetrievalCandidate[],
  embedFn: EmbedFn,
  assigned_tongue?: string
): Promise<Agent[]> {
  const agents: Agent[] = [];

  for (const retrieval of retrievals) {
    const rawEmbedding = await embedFn(retrieval.text);
    const position = projectEmbeddingToBall(rawEmbedding);
    const tongue = assigned_tongue || retrieval.tongue;
    const phase = tongue ? (TONGUE_PHASES[tongue] ?? null) : null;

    agents.push(createAgent(retrieval.envelopeId, position, phase, tongue, 0.5));
  }

  return agents;
}

// ═══════════════════════════════════════════════════════════════
// Core GeoSeal RAG filter
// ═══════════════════════════════════════════════════════════════

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
export function geoSealFilter(
  context: GeoSealRAGContext,
  num_steps: number = 10,
  drift_rate: number = 0.01
): GeoSealFilterResult {
  // Combine all agents
  const all_agents = [
    ...context.tongue_agents,
    ...context.retrieval_agents,
    ...context.memory_agents,
  ];

  // Run swarm dynamics
  runSwarm(all_agents, num_steps, drift_rate);

  // Extract final trust scores for non-tongue agents
  const attention_weights = new Map<string, number>();
  const quarantined_ids: string[] = [];

  for (const agent of all_agents) {
    if (!agent.id.startsWith('tongue-')) {
      attention_weights.set(agent.id, agent.trust_score);
      if (agent.is_quarantined) {
        quarantined_ids.push(agent.id);
      }
    }
  }

  return {
    attention_weights,
    quarantined_ids,
    total_agents: all_agents.length,
  };
}

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
export async function filterRetrievals(
  query: string,
  retrievals: RetrievalCandidate[],
  embedFn: EmbedFn,
  tongue?: string,
  num_steps: number = 10
): Promise<GeoSealFilterResult> {
  const [tongue_agents, retrieval_agents] = await Promise.all([
    initTongueAgents(embedFn),
    retrievalsToAgents(retrievals, embedFn, tongue),
  ]);

  const query_raw = await embedFn(query);
  const query_embedding = projectEmbeddingToBall(query_raw);

  const context: GeoSealRAGContext = {
    query_embedding,
    tongue_agents,
    retrieval_agents,
    memory_agents: [],
  };

  return geoSealFilter(context, num_steps);
}
