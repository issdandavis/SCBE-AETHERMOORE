"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.HyperbolicRAG = exports.DEFAULT_RAG_CONFIG = void 0;
const hyperbolic_js_1 = require("../harmonic/hyperbolic.js");
const geoseal_js_1 = require("../geoseal.js");
exports.DEFAULT_RAG_CONFIG = {
    maxK: 20,
    costThreshold: 1.5,
    minPhaseAlignment: 0.0,
    phaseWeight: 2.0,
};
// ═══════════════════════════════════════════════════════════════
// HyperbolicRAG class
// ═══════════════════════════════════════════════════════════════
class HyperbolicRAG {
    config;
    constructor(config = {}) {
        this.config = { ...exports.DEFAULT_RAG_CONFIG, ...config };
    }
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
    retrieve(queryEmbedding, candidates, queryTongue) {
        const query = (0, hyperbolic_js_1.projectEmbeddingToBall)(queryEmbedding);
        const queryPhase = queryTongue ? (geoseal_js_1.TONGUE_PHASES[queryTongue] ?? null) : null;
        // Compute distances and scores
        const scored = candidates.map((c) => {
            const projected = (0, hyperbolic_js_1.projectEmbeddingToBall)([...c.embedding]);
            const dist = (0, hyperbolic_js_1.hyperbolicDistance)(query, projected);
            // Phase alignment
            const candPhase = c.tongue ? (geoseal_js_1.TONGUE_PHASES[c.tongue] ?? null) : null;
            const phaseDev = (0, hyperbolic_js_1.phaseDeviation)(queryPhase, candPhase);
            const phase_score = 1.0 - phaseDev;
            // Combined trust: inverse cost with phase weighting
            const rawTrust = 1.0 / (1.0 + dist + this.config.phaseWeight * phaseDev);
            // Gating: d* above threshold OR phase below minimum
            const gated = dist > this.config.costThreshold ||
                phase_score < this.config.minPhaseAlignment;
            return {
                id: c.id,
                distance: dist,
                trust_score: gated ? 0 : rawTrust,
                phase_score,
                gated,
                metadata: c.metadata,
            };
        });
        // Sort by distance (ascending)
        scored.sort((a, b) => a.distance - b.distance);
        // Take top-k, exclude gated
        const results = [];
        for (const s of scored) {
            if (results.length >= this.config.maxK)
                break;
            if (!s.gated) {
                results.push(s);
            }
        }
        return results;
    }
    /**
     * Retrieve and return all results (including gated), for diagnostics.
     */
    retrieveAll(queryEmbedding, candidates, queryTongue) {
        const query = (0, hyperbolic_js_1.projectEmbeddingToBall)(queryEmbedding);
        const queryPhase = queryTongue ? (geoseal_js_1.TONGUE_PHASES[queryTongue] ?? null) : null;
        const scored = candidates.map((c) => {
            const projected = (0, hyperbolic_js_1.projectEmbeddingToBall)([...c.embedding]);
            const dist = (0, hyperbolic_js_1.hyperbolicDistance)(query, projected);
            const candPhase = c.tongue ? (geoseal_js_1.TONGUE_PHASES[c.tongue] ?? null) : null;
            const phaseDev = (0, hyperbolic_js_1.phaseDeviation)(queryPhase, candPhase);
            const phase_score = 1.0 - phaseDev;
            const rawTrust = 1.0 / (1.0 + dist + this.config.phaseWeight * phaseDev);
            const gated = dist > this.config.costThreshold ||
                phase_score < this.config.minPhaseAlignment;
            return {
                id: c.id,
                distance: dist,
                trust_score: gated ? 0 : rawTrust,
                phase_score,
                gated,
                metadata: c.metadata,
            };
        });
        scored.sort((a, b) => a.distance - b.distance);
        return scored;
    }
    /**
     * Update configuration at runtime (e.g., adjust cost threshold).
     */
    updateConfig(partial) {
        Object.assign(this.config, partial);
    }
    /**
     * Get current configuration.
     */
    getConfig() {
        return { ...this.config };
    }
}
exports.HyperbolicRAG = HyperbolicRAG;
//# sourceMappingURL=hyperbolic-rag.js.map