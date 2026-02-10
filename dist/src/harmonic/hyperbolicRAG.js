"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.HyperbolicRAGEngine = void 0;
exports.accessCost = accessCost;
exports.trustFromPosition = trustFromPosition;
exports.createHyperbolicRAG = createHyperbolicRAG;
const hyperbolic_js_1 = require("./hyperbolic.js");
const harmonicScaling_js_1 = require("./harmonicScaling.js");
const adaptiveNavigator_js_1 = require("./adaptiveNavigator.js");
// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
const PHI = (1 + Math.sqrt(5)) / 2;
const EPSILON = 1e-10;
// ═══════════════════════════════════════════════════════════════
// Access Cost Function
// ═══════════════════════════════════════════════════════════════
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
function accessCost(d, base = PHI, riskAmplification = 1.0) {
    if (d < 0)
        throw new RangeError('Distance must be non-negative');
    if (d < EPSILON)
        return 1.0;
    const baseCost = Math.pow(base, d);
    const safetyDecay = 1 - (0, harmonicScaling_js_1.harmonicScale)(d);
    return baseCost * (1 + riskAmplification * safetyDecay);
}
/**
 * Compute trust from a position's distance to the origin.
 * Mirrors geo_seal.py trust_from_position.
 *
 * @param point - Position in Poincaré ball
 * @returns Trust in (0, 1]
 */
function trustFromPosition(point) {
    const n = norm(point);
    if (n < EPSILON)
        return 1.0;
    // Hyperbolic distance from origin: 2 * arctanh(||p||)
    const d = 2 * Math.atanh(Math.min(n, 1 - EPSILON));
    return 1.0 / (1.0 + d);
}
// ═══════════════════════════════════════════════════════════════
// HyperbolicRAG Engine
// ═══════════════════════════════════════════════════════════════
/**
 * Retrieval-Augmented Generation engine using Poincaré ball geometry.
 *
 * Documents are embedded in the Poincaré ball. Retrieval uses hyperbolic
 * distance + phase alignment for relevance, and the harmonic wall
 * (accessCost) to gate what enters context. A fixed context budget
 * ensures that including adversarial (boundary-positioned) documents
 * exhausts the budget, protecting the downstream model.
 */
class HyperbolicRAGEngine {
    config;
    index = new Map();
    constructor(config) {
        this.config = {
            contextBudget: 20.0,
            maxResults: 10,
            minRelevance: 0.1,
            phaseWeight: 2.0,
            costBase: PHI,
            riskAmplification: 1.0,
            maxAge: 0,
            dimension: 6,
            ...config,
        };
    }
    // ─────────────────────────────────────────────────────────────
    // Index Management
    // ─────────────────────────────────────────────────────────────
    /**
     * Add a document to the index. The embedding must be inside the
     * Poincaré ball (norm < 1). If not, it is projected via
     * projectEmbeddingToBall.
     */
    addDocument(doc) {
        const emb = this.ensureInBall(doc.embedding);
        const n = norm(emb);
        this.index.set(doc.id, {
            doc: { ...doc, embedding: emb },
            norm: n,
        });
    }
    /**
     * Add multiple documents at once.
     */
    addDocuments(docs) {
        for (const doc of docs) {
            this.addDocument(doc);
        }
    }
    /**
     * Remove a document by id.
     * @returns true if the document was found and removed
     */
    removeDocument(id) {
        return this.index.delete(id);
    }
    /**
     * Get the number of indexed documents.
     */
    get size() {
        return this.index.size;
    }
    /**
     * Clear all documents from the index.
     */
    clear() {
        this.index.clear();
    }
    /**
     * Retrieve a document by id (or undefined if not found).
     */
    getDocument(id) {
        return this.index.get(id)?.doc;
    }
    // ─────────────────────────────────────────────────────────────
    // Retrieval
    // ─────────────────────────────────────────────────────────────
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
    retrieve(queryEmbedding, queryPhase) {
        const query = this.ensureInBall(queryEmbedding);
        const queryNorm = norm(query);
        const now = Date.now();
        // Score all candidates
        const candidates = [];
        let filteredOut = 0;
        for (const [id, entry] of this.index) {
            // Age filter
            if (this.config.maxAge > 0 && (now - entry.doc.insertedAt) > this.config.maxAge) {
                filteredOut++;
                continue;
            }
            // Compute hyperbolic distance
            const d = (0, hyperbolic_js_1.hyperbolicDistance)(query, entry.doc.embedding);
            // Compute relevance via phase-distance score
            const relevance = (0, hyperbolic_js_1.phaseDistanceScore)(query, entry.doc.embedding, queryPhase, entry.doc.phase, this.config.phaseWeight);
            // Filter low relevance
            if (relevance < this.config.minRelevance) {
                filteredOut++;
                continue;
            }
            // Compute access cost
            const cost = accessCost(d, this.config.costBase, this.config.riskAmplification);
            candidates.push({
                id,
                doc: entry.doc,
                distance: d,
                relevanceScore: relevance,
                accessCost: cost,
                rankScore: relevance / cost,
            });
        }
        // Sort by rankScore descending (best value first)
        candidates.sort((a, b) => b.rankScore - a.rankScore);
        // Greedily fill context budget
        const results = [];
        let totalCost = 0;
        let budgetExhausted = 0;
        for (const c of candidates) {
            if (results.length >= this.config.maxResults)
                break;
            if (totalCost + c.accessCost > this.config.contextBudget) {
                budgetExhausted++;
                continue;
            }
            totalCost += c.accessCost;
            results.push({
                id: c.id,
                trustScore: trustFromPosition(c.doc.embedding),
                accessCost: c.accessCost,
                relevanceScore: c.relevanceScore,
                rankScore: c.rankScore,
                document: c.doc,
            });
        }
        return {
            results,
            totalCost,
            remainingBudget: this.config.contextBudget - totalCost,
            candidatesConsidered: this.index.size,
            filteredOut,
            budgetExhausted,
            queryNorm,
        };
    }
    /**
     * Retrieve using tongue-aligned query — projects the query toward
     * the specified Sacred Tongue realm center before retrieval.
     *
     * @param queryEmbedding - Raw query vector
     * @param queryPhase - Query phase
     * @param tongue - Sacred Tongue code (KO, AV, RU, CA, UM, DR)
     * @param tongueInfluence - How much to bias toward tongue center (0-1, default: 0.3)
     */
    retrieveByTongue(queryEmbedding, queryPhase, tongue, tongueInfluence = 0.3) {
        const center = adaptiveNavigator_js_1.REALM_CENTERS[tongue];
        if (!center) {
            throw new Error(`Unknown tongue: ${tongue}. Valid: ${Object.keys(adaptiveNavigator_js_1.REALM_CENTERS).join(', ')}`);
        }
        // Blend query toward tongue center in tangent space
        const query = this.ensureInBall(queryEmbedding);
        const padded = padToLength(query, center.length);
        const blended = padded.map((q, i) => q * (1 - tongueInfluence) + center[i] * tongueInfluence);
        const projected = (0, hyperbolic_js_1.clampToBall)(blended, 0.95);
        return this.retrieve(projected, queryPhase);
    }
    /**
     * Compute the maximum number of documents retrievable from a given
     * position before exhausting the context budget. Useful for capacity
     * planning.
     *
     * @param position - Position in the Poincaré ball
     * @param avgDocDistance - Average hyperbolic distance to docs (default: 1.0)
     */
    estimateCapacity(position, avgDocDistance = 1.0) {
        const cost = accessCost(avgDocDistance, this.config.costBase, this.config.riskAmplification);
        return Math.floor(this.config.contextBudget / cost);
    }
    // ─────────────────────────────────────────────────────────────
    // Nearest Neighbors (raw, without cost gating)
    // ─────────────────────────────────────────────────────────────
    /**
     * Find k nearest neighbors by hyperbolic distance (no cost gating).
     * Useful for diagnostics and visualization.
     */
    kNearest(queryEmbedding, k) {
        const query = this.ensureInBall(queryEmbedding);
        const scored = [];
        for (const [id, entry] of this.index) {
            const d = (0, hyperbolic_js_1.hyperbolicDistance)(query, entry.doc.embedding);
            scored.push({ id, distance: d, doc: entry.doc });
        }
        scored.sort((a, b) => a.distance - b.distance);
        return scored.slice(0, k);
    }
    // ─────────────────────────────────────────────────────────────
    // Internals
    // ─────────────────────────────────────────────────────────────
    /**
     * Ensure a vector is inside the Poincaré ball. If norm >= 1,
     * project using the smooth tanh mapping.
     */
    ensureInBall(v) {
        const dim = this.config.dimension;
        const padded = padToLength(v, dim);
        const n = norm(padded);
        if (n >= 1 - EPSILON) {
            return (0, hyperbolic_js_1.projectEmbeddingToBall)(padded);
        }
        return padded;
    }
}
exports.HyperbolicRAGEngine = HyperbolicRAGEngine;
// ═══════════════════════════════════════════════════════════════
// Utility Helpers
// ═══════════════════════════════════════════════════════════════
function norm(v) {
    return Math.sqrt(v.reduce((s, x) => s + x * x, 0));
}
function padToLength(v, length) {
    if (v.length >= length)
        return v.slice(0, length);
    const padded = new Array(length).fill(0);
    for (let i = 0; i < v.length; i++)
        padded[i] = v[i];
    return padded;
}
// ═══════════════════════════════════════════════════════════════
// Factory
// ═══════════════════════════════════════════════════════════════
/**
 * Create a pre-configured HyperbolicRAG engine.
 */
function createHyperbolicRAG(config) {
    return new HyperbolicRAGEngine(config);
}
//# sourceMappingURL=hyperbolicRAG.js.map