"use strict";
/**
 * Space Tor Trust Manager with Langues Weighting System
 *
 * Implements Layer 3 (Langues Metric Tensor) for trust scoring across
 * the Six Sacred Tongues (KO, AV, RU, CA, UM, DR).
 *
 * Mathematical Foundation:
 * L(x,t) = Σ(l=1 to 6) w_l * exp[β_l * (d_l + sin(ω_l*t + φ_l))]
 * where d_l = |x_l - μ_l|
 *
 * @module spaceTor/trust-manager
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.languesMetricFlux = exports.languesMetric = exports.TrustManager = exports.DEFAULT_LANGUES_PARAMS = exports.SacredTongue = void 0;
/**
 * Sacred Tongue identifiers
 */
var SacredTongue;
(function (SacredTongue) {
    SacredTongue[SacredTongue["KORAELIN"] = 0] = "KORAELIN";
    SacredTongue[SacredTongue["AVALI"] = 1] = "AVALI";
    SacredTongue[SacredTongue["RUNETHIC"] = 2] = "RUNETHIC";
    SacredTongue[SacredTongue["CASSISIVADAN"] = 3] = "CASSISIVADAN";
    SacredTongue[SacredTongue["UMBROTH"] = 4] = "UMBROTH";
    SacredTongue[SacredTongue["DRAUMRIC"] = 5] = "DRAUMRIC"; // DR - Harmonic 5 (w=1.667)
})(SacredTongue || (exports.SacredTongue = SacredTongue = {}));
/**
 * Default Langues parameters (production-ready)
 */
exports.DEFAULT_LANGUES_PARAMS = {
    // Golden ratio scaling: w_l = φ^(l-1) where φ ≈ 1.618
    w: [1.0, 1.125, 1.25, 1.333, 1.5, 1.667],
    // Growth coefficients (moderate amplification)
    beta: [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
    // Temporal frequencies (2π/T_l)
    omega: [1, 2, 3, 4, 5, 6],
    // Phase offsets (2πk/6)
    phi: [0, Math.PI / 3, 2 * Math.PI / 3, Math.PI, 4 * Math.PI / 3, 5 * Math.PI / 3],
    // Ideal values (neutral trust)
    mu: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
    // Full dimensional participation (polly mode)
    nu: [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
};
/**
 * Trust Manager for Space Tor network
 *
 * Implements Langues Weighting System (Layer 3) for trust scoring
 * across the Six Sacred Tongues.
 */
class TrustManager {
    params;
    nodes;
    maxScore;
    constructor(params = exports.DEFAULT_LANGUES_PARAMS) {
        this.params = params;
        this.nodes = new Map();
        this.maxScore = this.computeMaxScore();
    }
    /**
     * Compute Langues metric L(x,t)
     *
     * L(x,t) = Σ(l=1 to 6) ν_l * w_l * exp[β_l * (d_l + sin(ω_l*t + φ_l))]
     *
     * @param x - 6D trust vector
     * @param t - Current time
     * @returns Raw Langues metric
     */
    computeLanguesMetric(x, t) {
        const { w, beta, omega, phi, mu, nu } = this.params;
        const nuVec = nu || Array(6).fill(1.0);
        let L = 0;
        for (let l = 0; l < 6; l++) {
            // Deviation from ideal
            const d_l = Math.abs(x[l] - mu[l]);
            // Temporal oscillation
            const s_l = d_l + Math.sin(omega[l] * t + phi[l]);
            // Exponential amplification with flux
            L += nuVec[l] * w[l] * Math.exp(beta[l] * s_l);
        }
        return L;
    }
    /**
     * Compute gradient field ∇L
     *
     * ∂L/∂x_l = ν_l * w_l * β_l * exp[β_l * (d_l + sin(...))] * sgn(x_l - μ_l)
     *
     * @param x - 6D trust vector
     * @param t - Current time
     * @returns Gradient vector
     */
    computeGradient(x, t) {
        const { w, beta, omega, phi, mu, nu } = this.params;
        const nuVec = nu || Array(6).fill(1.0);
        const gradient = [];
        for (let l = 0; l < 6; l++) {
            const d_l = Math.abs(x[l] - mu[l]);
            const s_l = d_l + Math.sin(omega[l] * t + phi[l]);
            const sign = Math.sign(x[l] - mu[l]);
            gradient[l] = nuVec[l] * w[l] * beta[l] * Math.exp(beta[l] * s_l) * sign;
        }
        return gradient;
    }
    /**
     * Compute per-tongue contributions
     *
     * @param x - 6D trust vector
     * @param t - Current time
     * @returns Array of 6 contributions
     */
    computeContributions(x, t) {
        const { w, beta, omega, phi, mu, nu } = this.params;
        const nuVec = nu || Array(6).fill(1.0);
        const contributions = [];
        for (let l = 0; l < 6; l++) {
            const d_l = Math.abs(x[l] - mu[l]);
            const s_l = d_l + Math.sin(omega[l] * t + phi[l]);
            contributions[l] = nuVec[l] * w[l] * Math.exp(beta[l] * s_l);
        }
        return contributions;
    }
    /**
     * Compute maximum possible score (for normalization)
     *
     * L_max occurs when all d_l = 1 and sin(...) = 1
     *
     * @returns Maximum Langues metric
     */
    computeMaxScore() {
        const { w, beta, nu } = this.params;
        const nuVec = nu || Array(6).fill(1.0);
        let maxScore = 0;
        for (let l = 0; l < 6; l++) {
            // Maximum deviation (d_l = 1) + maximum oscillation (sin = 1)
            maxScore += nuVec[l] * w[l] * Math.exp(beta[l] * 2.0);
        }
        return maxScore;
    }
    /**
     * Classify trust level based on normalized score
     *
     * @param normalized - Normalized score ∈ [0,1]
     * @returns Trust level
     */
    classifyTrustLevel(normalized) {
        if (normalized <= 0.3)
            return 'HIGH'; // Low deviation = high trust
        if (normalized <= 0.5)
            return 'MEDIUM'; // Moderate deviation
        if (normalized <= 0.7)
            return 'LOW'; // High deviation = low trust
        return 'CRITICAL'; // Critical deviation
    }
    /**
     * Compute trust score for a node
     *
     * @param nodeId - Node identifier
     * @param trustVector - 6D trust vector (one per Sacred Tongue)
     * @param t - Current time (default: Date.now() / 1000)
     * @returns Trust score with classification
     */
    computeTrustScore(nodeId, trustVector, t = Date.now() / 1000) {
        if (trustVector.length !== 6) {
            throw new Error('Trust vector must have 6 dimensions (one per Sacred Tongue)');
        }
        // Validate trust vector values ∈ [0,1]
        for (let i = 0; i < 6; i++) {
            if (trustVector[i] < 0 || trustVector[i] > 1) {
                throw new Error(`Trust vector[${i}] must be in [0,1], got ${trustVector[i]}`);
            }
        }
        // Compute Langues metric
        const raw = this.computeLanguesMetric(trustVector, t);
        const normalized = raw / this.maxScore;
        const contributions = this.computeContributions(trustVector, t);
        const gradient = this.computeGradient(trustVector, t);
        const level = this.classifyTrustLevel(normalized);
        // Update node trust state
        this.updateNodeTrust(nodeId, trustVector, raw);
        return {
            raw,
            normalized,
            contributions,
            gradient,
            level
        };
    }
    /**
     * Update node trust state
     *
     * @param nodeId - Node identifier
     * @param trustVector - 6D trust vector
     * @param score - Raw trust score
     */
    updateNodeTrust(nodeId, trustVector, score) {
        const existing = this.nodes.get(nodeId);
        if (existing) {
            existing.trustVector = trustVector;
            existing.lastUpdate = Date.now();
            existing.history.push(score);
            // Keep last 100 scores
            if (existing.history.length > 100) {
                existing.history.shift();
            }
            // Detect anomalies (sudden trust drops)
            if (existing.history.length >= 2) {
                const prev = existing.history[existing.history.length - 2];
                const curr = score;
                const drop = (prev - curr) / prev;
                if (drop > 0.3) {
                    existing.anomalies.push(`Trust drop: ${(drop * 100).toFixed(1)}% at ${new Date().toISOString()}`);
                }
            }
        }
        else {
            this.nodes.set(nodeId, {
                nodeId,
                trustVector,
                lastUpdate: Date.now(),
                history: [score],
                anomalies: []
            });
        }
    }
    /**
     * Get node trust state
     *
     * @param nodeId - Node identifier
     * @returns Node trust state or undefined
     */
    getNodeTrust(nodeId) {
        return this.nodes.get(nodeId);
    }
    /**
     * Get all nodes with trust level
     *
     * @param level - Trust level filter
     * @returns Array of node IDs
     */
    getNodesByTrustLevel(level) {
        const result = [];
        const t = Date.now() / 1000;
        for (const [nodeId, node] of this.nodes.entries()) {
            const score = this.computeTrustScore(nodeId, node.trustVector, t);
            if (score.level === level) {
                result.push(nodeId);
            }
        }
        return result;
    }
    /**
     * Update dimension flux coefficients (breathing)
     *
     * Allows dynamic adjustment of dimensional participation:
     * - ν_l = 1.0: Full participation (polly)
     * - 0.5 < ν_l < 1.0: Partial participation (demi)
     * - ν_l < 0.5: Weak participation (quasi)
     *
     * @param nu - New flux coefficients [6]
     */
    updateFluxCoefficients(nu) {
        if (nu.length !== 6) {
            throw new Error('Flux coefficients must have 6 dimensions');
        }
        for (let i = 0; i < 6; i++) {
            if (nu[i] < 0 || nu[i] > 1) {
                throw new Error(`Flux coefficient[${i}] must be in [0,1], got ${nu[i]}`);
            }
        }
        this.params.nu = nu;
        this.maxScore = this.computeMaxScore(); // Recompute max score
    }
    /**
     * Get trust statistics
     *
     * @returns Statistics object
     */
    getStatistics() {
        const t = Date.now() / 1000;
        let totalScore = 0;
        let highTrust = 0;
        let mediumTrust = 0;
        let lowTrust = 0;
        let criticalTrust = 0;
        for (const [nodeId, node] of this.nodes.entries()) {
            const score = this.computeTrustScore(nodeId, node.trustVector, t);
            totalScore += score.normalized;
            switch (score.level) {
                case 'HIGH':
                    highTrust++;
                    break;
                case 'MEDIUM':
                    mediumTrust++;
                    break;
                case 'LOW':
                    lowTrust++;
                    break;
                case 'CRITICAL':
                    criticalTrust++;
                    break;
            }
        }
        return {
            totalNodes: this.nodes.size,
            highTrust,
            mediumTrust,
            lowTrust,
            criticalTrust,
            averageScore: this.nodes.size > 0 ? totalScore / this.nodes.size : 0
        };
    }
    /**
     * Clear all node trust data
     */
    clear() {
        this.nodes.clear();
    }
}
exports.TrustManager = TrustManager;
/**
 * Standalone Langues metric function (for external use)
 *
 * @param x - 6D trust vector
 * @param mu - Ideal values [6]
 * @param w - Harmonic weights [6]
 * @param beta - Growth coefficients [6]
 * @param omega - Temporal frequencies [6]
 * @param phi - Phase offsets [6]
 * @param t - Current time
 * @param nu - Flux coefficients [6] (optional)
 * @returns Langues metric L(x,t)
 */
function languesMetric(x, mu, w, beta, omega, phi, t, nu) {
    const nuVec = nu || Array(6).fill(1.0);
    let L = 0;
    for (let l = 0; l < 6; l++) {
        const d_l = Math.abs(x[l] - mu[l]);
        const s_l = d_l + Math.sin(omega[l] * t + phi[l]);
        L += nuVec[l] * w[l] * Math.exp(beta[l] * s_l);
    }
    return L;
}
exports.languesMetric = languesMetric;
/**
 * Langues metric with flux (breathing dimensions)
 *
 * @param x - 6D trust vector
 * @param mu - Ideal values [6]
 * @param w - Harmonic weights [6]
 * @param beta - Growth coefficients [6]
 * @param omega - Temporal frequencies [6]
 * @param phi - Phase offsets [6]
 * @param t - Current time
 * @param nu - Flux coefficients [6]
 * @returns Langues metric L_f(x,t)
 */
function languesMetricFlux(x, mu, w, beta, omega, phi, t, nu) {
    return languesMetric(x, mu, w, beta, omega, phi, t, nu);
}
exports.languesMetricFlux = languesMetricFlux;
/**
 * Export all functions for Layer 3 integration
 */
exports.default = {
    TrustManager,
    languesMetric,
    languesMetricFlux,
    DEFAULT_LANGUES_PARAMS: exports.DEFAULT_LANGUES_PARAMS,
    SacredTongue
};
//# sourceMappingURL=trust-manager.js.map