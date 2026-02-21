"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __exportStar = (this && this.__exportStar) || function(m, exports) {
    for (var p in m) if (p !== "default" && !Object.prototype.hasOwnProperty.call(exports, p)) __createBinding(exports, m, p);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.HyperbolicRAGEngine = exports.TONGUE_ANCHORS = exports.DEFAULT_RAG_CONFIG = void 0;
exports.projectToBall = projectToBall;
exports.extractPhase = extractPhase;
exports.estimateUncertainty = estimateUncertainty;
exports.buildChunk = buildChunk;
exports.nearestTongueAnchor = nearestTongueAnchor;
exports.proximityScore = proximityScore;
exports.phaseConsistencyScore = phaseConsistencyScore;
exports.uncertaintyPenalty = uncertaintyPenalty;
exports.scoreChunk = scoreChunk;
exports.scoreAndFilter = scoreAndFilter;
exports.retrieveWithTrust = retrieveWithTrust;
exports.quarantineReport = quarantineReport;
exports.accessCost = accessCost;
exports.trustFromPosition = trustFromPosition;
exports.createHyperbolicRAG = createHyperbolicRAG;
__exportStar(require("../../packages/kernel/src/hyperbolicRAG.js"), exports);
const chsfn_js_1 = require("./chsfn.js");
/**
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
const hyperbolic_js_1 = require("./hyperbolic.js");
const harmonicScaling_js_1 = require("./harmonicScaling.js");
const adaptiveNavigator_js_1 = require("./adaptiveNavigator.js");
// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
const PHI = (1 + Math.sqrt(5)) / 2;
const EPSILON = 1e-10;
exports.DEFAULT_RAG_CONFIG = {
    maxTrustDistance: 3.0,
    minPhaseCoherence: 0.4,
    maxUncertainty: 0.7,
    weightProximity: 0.5,
    weightPhase: 0.3,
    weightUncertainty: 0.2,
    quarantineThreshold: 0.3,
    impedance: chsfn_js_1.DEFAULT_IMPEDANCE,
};
// ═══════════════════════════════════════════════════════════════
// Projection: Arbitrary Embeddings → Poincaré Ball
// ═══════════════════════════════════════════════════════════════
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
function projectToBall(embedding, scale = 0.5) {
    // Reduce to 6D by chunked averaging
    const reduced = [0, 0, 0, 0, 0, 0];
    const chunkSize = Math.max(1, Math.floor(embedding.length / 6));
    for (let dim = 0; dim < 6; dim++) {
        const start = dim * chunkSize;
        const end = dim === 5 ? embedding.length : (dim + 1) * chunkSize;
        let sum = 0;
        let count = 0;
        for (let j = start; j < end; j++) {
            sum += embedding[j];
            count++;
        }
        reduced[dim] = count > 0 ? sum / count : 0;
    }
    // Compute norm of reduced vector
    let normSq = 0;
    for (let i = 0; i < 6; i++)
        normSq += reduced[i] * reduced[i];
    const norm = Math.sqrt(normSq);
    if (norm < EPSILON)
        return [0, 0, 0, 0, 0, 0];
    // tanh mapping: u = tanh(α·‖x‖) · x / ‖x‖
    const mappedNorm = Math.tanh(scale * norm);
    const result = [0, 0, 0, 0, 0, 0];
    for (let i = 0; i < 6; i++) {
        result[i] = mappedNorm * (reduced[i] / norm);
    }
    return result;
}
/**
 * Extract phase features from an embedding.
 *
 * Maps each tongue's chunk of the embedding to an angle via atan2
 * of even/odd component averages.
 *
 * @param embedding - Raw embedding vector
 * @returns Phase vector [θ_KO, θ_AV, θ_RU, θ_CA, θ_DR, θ_UM]
 */
function extractPhase(embedding) {
    const chunkSize = Math.max(2, Math.floor(embedding.length / 6));
    const phase = [0, 0, 0, 0, 0, 0];
    for (let dim = 0; dim < 6; dim++) {
        const start = dim * chunkSize;
        let evenSum = 0;
        let oddSum = 0;
        const end = Math.min(start + chunkSize, embedding.length);
        for (let j = start; j < end; j++) {
            if ((j - start) % 2 === 0)
                evenSum += embedding[j];
            else
                oddSum += embedding[j];
        }
        phase[dim] = Math.atan2(oddSum, evenSum + EPSILON);
    }
    return phase;
}
/**
 * Estimate uncertainty from an embedding using variance of components.
 *
 * Higher variance ≈ more spread-out representation ≈ less confident.
 * Normalized to [0, 1] via sigmoid.
 *
 * @param embedding - Raw embedding vector
 * @returns Uncertainty in [0, 1]
 */
function estimateUncertainty(embedding) {
    if (embedding.length === 0)
        return 1.0;
    let sum = 0;
    let sumSq = 0;
    for (const v of embedding) {
        sum += v;
        sumSq += v * v;
    }
    const mean = sum / embedding.length;
    const variance = sumSq / embedding.length - mean * mean;
    // Sigmoid normalization: maps variance to [0, 1]
    // Calibrated so variance ~0.1 → uncertainty ~0.5
    return 1 / (1 + Math.exp(-10 * (variance - 0.1)));
}
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
function buildChunk(chunkId, embedding, scale = 0.5) {
    const norm = Math.sqrt(embedding.reduce((s, v) => s + v * v, 0));
    return {
        chunkId,
        position: projectToBall(embedding, scale),
        phase: extractPhase(embedding),
        uncertainty: estimateUncertainty(embedding),
        originalNorm: norm,
    };
}
// ═══════════════════════════════════════════════════════════════
// Tongue Anchors
// ═══════════════════════════════════════════════════════════════
/**
 * The 6 tongue anchors in the Poincaré ball.
 *
 * Each tongue occupies a canonical position along its primary axis.
 * These are the "safe poles" — trusted retrieval should cluster near these.
 */
exports.TONGUE_ANCHORS = {
    KO: [0.5, 0, 0, 0, 0, 0],
    AV: [0, 0.5, 0, 0, 0, 0],
    RU: [0, 0, 0.5, 0, 0, 0],
    CA: [0, 0, 0, 0.5, 0, 0],
    DR: [0, 0, 0, 0, 0.5, 0],
    UM: [0, 0, 0, 0, 0, 0.5],
};
/** Tongue names indexed */
const TONGUE_NAMES = ['KO', 'AV', 'RU', 'CA', 'DR', 'UM'];
/**
 * Find the nearest tongue anchor to a position.
 *
 * @param position - 6D position in Poincaré ball
 * @returns { tongue, distance } of nearest anchor
 */
function nearestTongueAnchor(position) {
    let bestTongue = 'KO';
    let bestDist = Infinity;
    for (const tongue of TONGUE_NAMES) {
        const d = (0, chsfn_js_1.hyperbolicDistance6D)(position, exports.TONGUE_ANCHORS[tongue]);
        if (d < bestDist) {
            bestDist = d;
            bestTongue = tongue;
        }
    }
    return { tongue: bestTongue, distance: bestDist };
}
// ═══════════════════════════════════════════════════════════════
// Three-Signal Scoring
// ═══════════════════════════════════════════════════════════════
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
function proximityScore(queryPos, chunkPos, maxDist = 3.0) {
    const dist = (0, chsfn_js_1.hyperbolicDistance6D)(queryPos, chunkPos);
    if (dist > maxDist)
        return 0;
    // Use access cost for exponential decay, but normalize
    const cost = (0, chsfn_js_1.accessCost)(dist);
    const baseCost = (0, chsfn_js_1.accessCost)(0);
    return baseCost / cost; // Ratio: cost at origin / cost at d → decays exponentially
}
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
function phaseConsistencyScore(chunkPhase, queryPhase) {
    let sum = 0;
    for (let i = 0; i < 6; i++) {
        sum += Math.cos(chunkPhase[i] - queryPhase[i]);
    }
    // cos ranges [-1, 1]; normalize to [0, 1]
    return (sum / 6 + 1) / 2;
}
/**
 * Compute uncertainty penalty.
 *
 * Higher uncertainty → higher penalty → lower trust.
 *
 * @param uncertainty - Chunk uncertainty in [0, 1]
 * @returns Penalty in [0, 1] where 0 = no penalty, 1 = max penalty
 */
function uncertaintyPenalty(uncertainty) {
    return Math.min(Math.max(uncertainty, 0), 1);
}
// ═══════════════════════════════════════════════════════════════
// Fusion: Three Signals → Trust Score
// ═══════════════════════════════════════════════════════════════
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
function scoreChunk(query, chunk, config = exports.DEFAULT_RAG_CONFIG) {
    const proxScore = proximityScore(query.position, chunk.position, config.maxTrustDistance);
    const phaseScore = phaseConsistencyScore(chunk.phase, query.phase);
    const uncPenalty = uncertaintyPenalty(chunk.uncertainty);
    // Distances for interpretability
    const distToQuery = (0, chsfn_js_1.hyperbolicDistance6D)(query.position, chunk.position);
    const { distance: distToAnchor } = nearestTongueAnchor(chunk.position);
    // Weighted fusion
    const raw = config.weightProximity * proxScore +
        config.weightPhase * phaseScore -
        config.weightUncertainty * uncPenalty;
    // Clamp to [0, 1]
    const trustScore = Math.max(0, Math.min(1, raw));
    const anomalyProb = 1 - trustScore;
    const quarantineFlag = trustScore < config.quarantineThreshold ||
        chunk.uncertainty > config.maxUncertainty;
    // Soft attention gating: trust² ensures quarantined chunks get near-zero weight
    const attentionWeight = quarantineFlag ? 0 : trustScore * trustScore;
    return {
        chunkId: chunk.chunkId,
        trustScore,
        anomalyProb,
        quarantineFlag,
        attentionWeight,
        signals: {
            proximityScore: proxScore,
            phaseScore,
            uncertaintyPenalty: uncPenalty,
            distanceToQuery: distToQuery,
            distanceToAnchor: distToAnchor,
        },
    };
}
// ═══════════════════════════════════════════════════════════════
// Batch Scoring + kNN Retrieval
// ═══════════════════════════════════════════════════════════════
/**
 * Score all retrieval candidates and return trust-gated results.
 *
 * @param query - Query state
 * @param chunks - Candidate chunks (pre-projected into ball)
 * @param topK - Max results to return (default 10)
 * @param config - Scorer configuration
 * @returns Sorted array of trust scores (highest trust first), quarantined removed
 */
function scoreAndFilter(query, chunks, topK = 10, config = exports.DEFAULT_RAG_CONFIG) {
    const scored = chunks.map((c) => scoreChunk(query, c, config));
    // Partition: trusted vs quarantined
    const trusted = scored.filter((s) => !s.quarantineFlag);
    const quarantined = scored.filter((s) => s.quarantineFlag);
    // Sort by trust score descending
    trusted.sort((a, b) => b.trustScore - a.trustScore);
    // Renormalize attention weights so they sum to 1
    const totalWeight = trusted.reduce((s, t) => s + t.attentionWeight, 0);
    if (totalWeight > 0) {
        for (const t of trusted) {
            t.attentionWeight /= totalWeight;
        }
    }
    return trusted.slice(0, topK);
}
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
function retrieveWithTrust(queryEmbedding, candidateEmbeddings, topK = 10, config = exports.DEFAULT_RAG_CONFIG, scale = 0.5) {
    const queryPos = projectToBall(queryEmbedding, scale);
    const queryPhase = extractPhase(queryEmbedding);
    const chunks = candidateEmbeddings.map((c) => buildChunk(c.id, c.embedding, scale));
    return scoreAndFilter({ position: queryPos, phase: queryPhase }, chunks, topK, config);
}
// ═══════════════════════════════════════════════════════════════
// Quarantine Analytics
// ═══════════════════════════════════════════════════════════════
/**
 * Score all chunks and return quarantine analytics.
 *
 * @param query - Query state
 * @param chunks - All chunks
 * @param config - Config
 * @returns { trusted, quarantined, stats }
 */
function quarantineReport(query, chunks, config = exports.DEFAULT_RAG_CONFIG) {
    const scored = chunks.map((c) => scoreChunk(query, c, config));
    const trusted = scored.filter((s) => !s.quarantineFlag);
    const quarantined = scored.filter((s) => s.quarantineFlag);
    const avgTrust = scored.length > 0
        ? scored.reduce((s, t) => s + t.trustScore, 0) / scored.length
        : 0;
    const avgAnomaly = scored.length > 0
        ? scored.reduce((s, t) => s + t.anomalyProb, 0) / scored.length
        : 0;
    return {
        trusted,
        quarantined,
        stats: {
            total: chunks.length,
            trustedCount: trusted.length,
            quarantinedCount: quarantined.length,
            avgTrustScore: avgTrust,
            avgAnomalyProb: avgAnomaly,
            quarantineRate: chunks.length > 0 ? quarantined.length / chunks.length : 0,
        },
    };
}
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