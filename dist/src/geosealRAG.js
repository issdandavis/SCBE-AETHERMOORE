"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.getTongueDomain = getTongueDomain;
exports.initTongueAgents = initTongueAgents;
exports.retrievalsToAgents = retrievalsToAgents;
exports.geoSealFilter = geoSealFilter;
exports.filterRetrievals = filterRetrievals;
const geoseal_js_1 = require("./geoseal.js");
const hyperbolic_js_1 = require("./harmonic/hyperbolic.js");
// ═══════════════════════════════════════════════════════════════
// Tongue domain text (for generating tongue agent embeddings)
// ═══════════════════════════════════════════════════════════════
const TONGUE_DOMAINS = {
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
function getTongueDomain(tongue) {
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
async function initTongueAgents(embedFn) {
    const tongues = Object.keys(geoseal_js_1.TONGUE_PHASES);
    const agents = [];
    for (const tongue of tongues) {
        const domain_text = getTongueDomain(tongue);
        const rawEmbedding = await embedFn(domain_text);
        const position = (0, hyperbolic_js_1.projectEmbeddingToBall)(rawEmbedding);
        agents.push((0, geoseal_js_1.createAgent)(`tongue-${tongue}`, position, geoseal_js_1.TONGUE_PHASES[tongue], tongue, 1.0));
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
async function retrievalsToAgents(retrievals, embedFn, assigned_tongue) {
    const agents = [];
    for (const retrieval of retrievals) {
        const rawEmbedding = await embedFn(retrieval.text);
        const position = (0, hyperbolic_js_1.projectEmbeddingToBall)(rawEmbedding);
        const tongue = assigned_tongue || retrieval.tongue;
        const phase = tongue ? (geoseal_js_1.TONGUE_PHASES[tongue] ?? null) : null;
        agents.push((0, geoseal_js_1.createAgent)(retrieval.envelopeId, position, phase, tongue, 0.5));
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
function geoSealFilter(context, num_steps = 10, drift_rate = 0.01) {
    // Combine all agents
    const all_agents = [
        ...context.tongue_agents,
        ...context.retrieval_agents,
        ...context.memory_agents,
    ];
    // Run swarm dynamics
    (0, geoseal_js_1.runSwarm)(all_agents, num_steps, drift_rate);
    // Extract final trust scores for non-tongue agents
    const attention_weights = new Map();
    const quarantined_ids = [];
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
async function filterRetrievals(query, retrievals, embedFn, tongue, num_steps = 10) {
    const [tongue_agents, retrieval_agents] = await Promise.all([
        initTongueAgents(embedFn),
        retrievalsToAgents(retrievals, embedFn, tongue),
    ]);
    const query_raw = await embedFn(query);
    const query_embedding = (0, hyperbolic_js_1.projectEmbeddingToBall)(query_raw);
    const context = {
        query_embedding,
        tongue_agents,
        retrieval_agents,
        memory_agents: [],
    };
    return geoSealFilter(context, num_steps);
}
//# sourceMappingURL=geosealRAG.js.map