"use strict";
/**
 * @file geoseal-v2.ts
 * @module geoseal-v2
 * @layer Layer 9, Layer 12, Layer 13
 * @version 2.0.0
 *
 * GeoSeal v2: Mixed-Curvature Geometric Access Control Kernel
 *
 * Extends GeoSeal v1 with a product manifold H^a x S^b x R^c where:
 * - Hyperbolic (H^a): hierarchy, trust zones, boundary quarantine
 * - Spherical  (S^b): tongue phase discipline, cyclic role coherence
 * - Gaussian   (R^c): retrieval uncertainty, memory write gating
 *
 * Each agent carries three coordinate families:
 *   u ∈ B^n   (Poincaré ball position)     — hierarchy / containment
 *   p ∈ S^1   (phase as [cos θ, sin θ])    — tongue discipline
 *   (μ, σ²)   (diagonal Gaussian)          — retrieval confidence
 *
 * Scoring fuses three independent geometry scores:
 *   trust = w_H · s_H + w_S · s_S + w_G · s_G
 *
 * where:
 *   s_H = 1 / (1 + d_H)               — hyperbolic proximity
 *   s_S = 1 - phaseDeviation           — phase consistency
 *   s_G = 1 / (1 + trace(Σ))          — uncertainty (low = trustworthy)
 *
 * Quarantine triggers when fused trust drops below threshold OR when
 * spatial consensus (3+ neighbors) flags the agent.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.MEMORY_WRITE_THRESHOLD = exports.QUARANTINE_TRUST_THRESHOLD = exports.DEFAULT_FUSION_WEIGHTS = exports.QUARANTINE_CONSENSUS = exports.SUSPICION_THRESHOLD = exports.TONGUE_PHASES = void 0;
exports.createMixedAgent = createMixedAgent;
exports.scoreHyperbolic = scoreHyperbolic;
exports.scorePhase = scorePhase;
exports.scoreCertainty = scoreCertainty;
exports.fuseScores = fuseScores;
exports.updateSuspicionV2 = updateSuspicionV2;
exports.computeRepelForceV2 = computeRepelForceV2;
exports.swarmStepV2 = swarmStepV2;
exports.runSwarmV2 = runSwarmV2;
exports.scoreAllCandidates = scoreAllCandidates;
const hyperbolic_js_1 = require("./harmonic/hyperbolic.js");
const geoseal_js_1 = require("./geoseal.js");
Object.defineProperty(exports, "TONGUE_PHASES", { enumerable: true, get: function () { return geoseal_js_1.TONGUE_PHASES; } });
Object.defineProperty(exports, "SUSPICION_THRESHOLD", { enumerable: true, get: function () { return geoseal_js_1.SUSPICION_THRESHOLD; } });
Object.defineProperty(exports, "QUARANTINE_CONSENSUS", { enumerable: true, get: function () { return geoseal_js_1.QUARANTINE_CONSENSUS; } });
exports.DEFAULT_FUSION_WEIGHTS = {
    wH: 0.4,
    wS: 0.35,
    wG: 0.25,
};
/** Quarantine threshold for fused trust score */
exports.QUARANTINE_TRUST_THRESHOLD = 0.3;
/** Memory write threshold (only chunks above this get promoted) */
exports.MEMORY_WRITE_THRESHOLD = 0.7;
/**
 * Create a v2 mixed-geometry agent.
 *
 * @param id - Agent identifier
 * @param position - Poincaré ball embedding
 * @param phase - Tongue phase (null = rogue)
 * @param sigma - Uncertainty variance (0 = perfectly certain)
 * @param tongue - Optional tongue code
 * @param trust - Initial trust score
 */
function createMixedAgent(id, position, phase, sigma = 0.0, tongue, trust = 0.5) {
    return {
        id,
        position: [...position],
        phase,
        phaseVec: phase !== null ? [Math.cos(phase), Math.sin(phase)] : [0, 0],
        sigma,
        tongue,
        suspicion_count: new Map(),
        is_quarantined: false,
        trust_score: trust,
        score_hyperbolic: 0,
        score_phase: 0,
        score_certainty: 0,
    };
}
// ═══════════════════════════════════════════════════════════════
// Individual geometry scores
// ═══════════════════════════════════════════════════════════════
/**
 * Hyperbolic proximity score: s_H = 1 / (1 + d_H)
 * High when agents are close in the Poincaré ball.
 */
function scoreHyperbolic(a, b) {
    const dH = (0, hyperbolic_js_1.hyperbolicDistance)(a.position, b.position);
    return 1.0 / (1.0 + dH);
}
/**
 * Spherical phase consistency score: s_S = 1 - phaseDeviation
 * High when agents share the same tongue phase.
 */
function scorePhase(a, b) {
    return 1.0 - (0, hyperbolic_js_1.phaseDeviation)(a.phase, b.phase);
}
/**
 * Gaussian certainty score: s_G = 1 / (1 + σ²)
 * High when the agent has low uncertainty.
 * Scored for agent b (the candidate being evaluated).
 */
function scoreCertainty(b) {
    return 1.0 / (1.0 + b.sigma);
}
/**
 * Fuse three geometry scores into a single trust value.
 *
 * trust = w_H * s_H + w_S * s_S + w_G * s_G
 *
 * Actions:
 * - ALLOW:      trust >= MEMORY_WRITE_THRESHOLD
 * - QUARANTINE: QUARANTINE_TRUST_THRESHOLD <= trust < MEMORY_WRITE_THRESHOLD
 * - DENY:       trust < QUARANTINE_TRUST_THRESHOLD
 *
 * @param anchor - Reference agent (e.g., tongue agent)
 * @param candidate - Agent being evaluated
 * @param weights - Fusion weights (default: 0.4/0.35/0.25)
 */
function fuseScores(anchor, candidate, weights = exports.DEFAULT_FUSION_WEIGHTS) {
    const sH = scoreHyperbolic(anchor, candidate);
    const sS = scorePhase(anchor, candidate);
    const sG = scoreCertainty(candidate);
    const trust = weights.wH * sH + weights.wS * sS + weights.wG * sG;
    // Anomaly: low phase consistency or high uncertainty
    const anomaly = sS < 0.5 || sG < 0.5;
    let action;
    if (trust >= exports.MEMORY_WRITE_THRESHOLD) {
        action = 'ALLOW';
    }
    else if (trust >= exports.QUARANTINE_TRUST_THRESHOLD) {
        action = 'QUARANTINE';
    }
    else {
        action = 'DENY';
    }
    return { trust, sH, sS, sG, anomaly, action };
}
// ═══════════════════════════════════════════════════════════════
// v2 Suspicion (same algorithm as v1, applied to MixedAgent)
// ═══════════════════════════════════════════════════════════════
function updateSuspicionV2(agent, neighbor_id, is_anomaly) {
    if (is_anomaly) {
        const current = agent.suspicion_count.get(neighbor_id) || 0;
        agent.suspicion_count.set(neighbor_id, current + 1);
    }
    else {
        const current = agent.suspicion_count.get(neighbor_id) || 0;
        agent.suspicion_count.set(neighbor_id, Math.max(0, current - geoseal_js_1.SUSPICION_DECAY));
    }
    let suspicious_neighbors = 0;
    for (const count of agent.suspicion_count.values()) {
        if (count >= geoseal_js_1.SUSPICION_THRESHOLD)
            suspicious_neighbors++;
    }
    agent.is_quarantined = suspicious_neighbors >= geoseal_js_1.QUARANTINE_CONSENSUS;
    let total_suspicion = 0;
    for (const count of agent.suspicion_count.values()) {
        total_suspicion += count;
    }
    agent.trust_score = Math.max(0, 1.0 - total_suspicion / geoseal_js_1.TRUST_DENOMINATOR);
}
/**
 * v2 repulsion force: includes uncertainty in amplification.
 *
 * Amplification rules (additive):
 * - v1 phase rules still apply (null=2.0x, mismatch=1.5x+dev, quarantine=1.5x)
 * - High uncertainty (σ > 0.5) adds +0.5x amplification
 * - Fused anomaly adds +0.25x
 */
function computeRepelForceV2(agent_a, agent_b, anchor = null, base_strength = 1.0, weights = exports.DEFAULT_FUSION_WEIGHTS) {
    const d_H = (0, hyperbolic_js_1.hyperbolicDistance)(agent_a.position, agent_b.position);
    const base_repulsion = base_strength / (d_H + 1e-6);
    // v1 phase-based amplification
    let amplification = 1.0;
    let anomaly_flag = false;
    if (agent_b.phase === null) {
        amplification = 2.0;
        anomaly_flag = true;
    }
    else if (agent_a.phase !== null) {
        const deviation = (0, hyperbolic_js_1.phaseDeviation)(agent_a.phase, agent_b.phase);
        if (d_H < 1.0 && deviation > 0.5) {
            amplification = 1.5 + deviation;
            anomaly_flag = true;
        }
    }
    if (agent_b.is_quarantined) {
        amplification *= 1.5;
    }
    // v2: uncertainty amplification
    if (agent_b.sigma > 0.5) {
        amplification += 0.5;
        anomaly_flag = true;
    }
    // v2: fused score (use anchor if provided, else agent_a)
    // Only apply fused anomaly amplification when the source has a valid phase;
    // a null-phase source would always produce sS=0, falsely flagging legit targets.
    const ref = anchor || agent_a;
    const fused = fuseScores(ref, agent_b, weights);
    if (fused.anomaly && ref.phase !== null) {
        amplification += 0.25;
        anomaly_flag = true;
    }
    // Force vector
    const dim = agent_a.position.length;
    const force = new Array(dim);
    for (let i = 0; i < dim; i++) {
        const direction = agent_a.position[i] - agent_b.position[i];
        force[i] = direction * base_repulsion * amplification;
    }
    // Store score breakdown on the candidate
    agent_b.score_hyperbolic = fused.sH;
    agent_b.score_phase = fused.sS;
    agent_b.score_certainty = fused.sG;
    return { force, amplification, anomaly_flag, fused };
}
// ═══════════════════════════════════════════════════════════════
// v2 Swarm dynamics
// ═══════════════════════════════════════════════════════════════
/**
 * Run one v2 swarm update step.
 *
 * Same structure as v1 but uses mixed-geometry repulsion and
 * optionally applies uncertainty decay (σ decreases when an agent
 * consistently matches its neighbors, increases under anomaly).
 */
function swarmStepV2(agents, drift_rate = 0.01, sigma_decay = 0.01, weights = exports.DEFAULT_FUSION_WEIGHTS) {
    const n = agents.length;
    const dim = agents[0]?.position.length ?? 0;
    for (let i = 0; i < n; i++) {
        const net_force = new Array(dim).fill(0);
        for (let j = 0; j < n; j++) {
            if (i === j)
                continue;
            const result = computeRepelForceV2(agents[i], agents[j], null, 1.0, weights);
            for (let k = 0; k < dim; k++) {
                net_force[k] += result.force[k];
            }
            // Update suspicion on the TARGET (j) from the SOURCE (i)
            updateSuspicionV2(agents[j], agents[i].id, result.anomaly_flag);
        }
        // Apply force with drift
        for (let k = 0; k < dim; k++) {
            agents[i].position[k] += net_force[k] * drift_rate;
        }
        agents[i].position = (0, hyperbolic_js_1.clampToBall)(agents[i].position, 0.99);
        // v2: uncertainty evolution
        // Sigma is driven by how much others flag THIS agent (suspicion_count),
        // not by how many anomalies it detects on others.
        let total_incoming_suspicion = 0;
        for (const count of agents[i].suspicion_count.values()) {
            total_incoming_suspicion += count;
        }
        if (total_incoming_suspicion > 3) {
            // Others are flagging this agent: uncertainty grows
            agents[i].sigma = Math.min(10.0, agents[i].sigma + sigma_decay * 2);
        }
        else {
            // Not being flagged: uncertainty decays
            agents[i].sigma = Math.max(0, agents[i].sigma - sigma_decay);
        }
    }
    return agents;
}
/**
 * Run multiple v2 swarm steps.
 */
function runSwarmV2(agents, num_steps = 10, drift_rate = 0.01, sigma_decay = 0.01, weights = exports.DEFAULT_FUSION_WEIGHTS) {
    for (let step = 0; step < num_steps; step++) {
        swarmStepV2(agents, drift_rate, sigma_decay, weights);
    }
    return agents;
}
/**
 * Score all candidates against a set of tongue anchors.
 *
 * For each candidate, computes the best fused score across all anchors
 * (i.e., the tongue that trusts this candidate the most).
 *
 * @param anchors - Tongue agents (trusted references)
 * @param candidates - Retrieval/memory agents to score
 * @param weights - Fusion weights
 * @returns Scored candidates sorted by trust (descending)
 */
function scoreAllCandidates(anchors, candidates, weights = exports.DEFAULT_FUSION_WEIGHTS) {
    const results = [];
    for (const candidate of candidates) {
        // Best score across all anchors
        let bestFused = null;
        for (const anchor of anchors) {
            const fused = fuseScores(anchor, candidate, weights);
            if (!bestFused || fused.trust > bestFused.trust) {
                bestFused = fused;
            }
        }
        if (bestFused) {
            results.push({
                id: candidate.id,
                trust: bestFused.trust,
                action: bestFused.action,
                sH: bestFused.sH,
                sS: bestFused.sS,
                sG: bestFused.sG,
                is_quarantined: candidate.is_quarantined,
                sigma: candidate.sigma,
            });
        }
    }
    // Sort by trust descending
    results.sort((a, b) => b.trust - a.trust);
    return results;
}
//# sourceMappingURL=geoseal-v2.js.map