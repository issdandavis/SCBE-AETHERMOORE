"use strict";
/**
 * @file geoseal.ts
 * @module geoseal
 * @layer Layer 9, Layer 12, Layer 13
 * @version 1.0.0
 *
 * GeoSeal: Geometric Access Control Kernel
 *
 * Turns vector RAG from a passive similarity-matcher into an active immune
 * system that detects, quarantines, and reweights adversarial or off-grammar
 * retrievals using hyperbolic geometry and phase-discipline consensus.
 *
 * Core mechanisms:
 * - Phase validity -> repulsion amplification (null phase = 2.0x, wrong = 1.5x + deviation)
 * - Per-neighbor suspicion counters (temporal integration, filters transient flukes)
 * - Spatial consensus threshold (3+ neighbors agreeing = quarantine mode)
 * - Second-stage amplification (force x 1.5 when quarantined)
 *
 * Integration: Uses Poincaré ball primitives from harmonic/hyperbolic.ts.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.TRUST_DENOMINATOR = exports.QUARANTINE_CONSENSUS = exports.SUSPICION_THRESHOLD = exports.SUSPICION_DECAY = exports.TONGUE_PHASES = void 0;
exports.createAgent = createAgent;
exports.computeRepelForce = computeRepelForce;
exports.updateSuspicion = updateSuspicion;
exports.swarmStep = swarmStep;
exports.runSwarm = runSwarm;
const hyperbolic_js_1 = require("./harmonic/hyperbolic.js");
// ═══════════════════════════════════════════════════════════════
// Sacred Tongues phase mapping
// ═══════════════════════════════════════════════════════════════
/** Fixed phases for the 6 Sacred Tongues (evenly spaced on unit circle) */
exports.TONGUE_PHASES = {
    KO: 0.0, // Kor'aelin - Control/orchestration
    AV: Math.PI / 3, // Avali - Initialization/transport
    RU: (2 * Math.PI) / 3, // Runethic - Policy/authorization
    CA: Math.PI, // Cassisivadan - Encryption/compute
    UM: (4 * Math.PI) / 3, // Umbroth - Redaction/privacy
    DR: (5 * Math.PI) / 3, // Draumric - Authentication/integrity
};
/** Create a new agent with sensible defaults */
function createAgent(id, position, phase, tongue, trust_score = 0.5) {
    return {
        id,
        position: [...position],
        phase,
        tongue,
        suspicion_count: new Map(),
        is_quarantined: false,
        trust_score,
    };
}
/**
 * Core GeoSeal repulsion force computation.
 *
 * Implements immune-like response: phase-mismatched agents near legitimate
 * agents experience amplified repulsive forces that push them toward the
 * manifold boundary.
 *
 * Amplification rules:
 * - Null phase (unknown/rogue): 2.0x
 * - Phase mismatch at close range (d_H < 1.0, deviation > 0.5): 1.5x + deviation
 * - Quarantined agents: additional 1.5x multiplier
 */
function computeRepelForce(agent_a, agent_b, base_strength = 1.0) {
    const d_H = (0, hyperbolic_js_1.hyperbolicDistance)(agent_a.position, agent_b.position);
    // Base repulsion: inversely proportional to distance
    const base_repulsion = base_strength / (d_H + 1e-6);
    // Compute phase-based amplification
    let amplification = 1.0;
    let anomaly_flag = false;
    if (agent_b.phase === null) {
        // Null phase (unknown/rogue) -> maximum amplification
        amplification = 2.0;
        anomaly_flag = true;
    }
    else if (agent_a.phase !== null) {
        // Both have phases, check for mismatch
        const deviation = (0, hyperbolic_js_1.phaseDeviation)(agent_a.phase, agent_b.phase);
        // Close distance + high phase deviation = suspicious
        if (d_H < 1.0 && deviation > 0.5) {
            amplification = 1.5 + deviation;
            anomaly_flag = true;
        }
    }
    // Quarantined agents get further amplification
    if (agent_b.is_quarantined) {
        amplification *= 1.5;
    }
    // Force vector: direction away from agent_b
    const dim = agent_a.position.length;
    const force = new Array(dim);
    for (let i = 0; i < dim; i++) {
        const direction = agent_a.position[i] - agent_b.position[i];
        force[i] = direction * base_repulsion * amplification;
    }
    return { force, amplification, anomaly_flag };
}
// ═══════════════════════════════════════════════════════════════
// Suspicion tracking and quarantine
// ═══════════════════════════════════════════════════════════════
/** Suspicion decay rate when no anomaly is detected */
exports.SUSPICION_DECAY = 0.5;
/** Number of suspicion hits before a neighbor is considered suspicious */
exports.SUSPICION_THRESHOLD = 3;
/** Number of suspicious neighbors required for quarantine */
exports.QUARANTINE_CONSENSUS = 3;
/** Trust score denominator (total suspicion / this = trust loss) */
exports.TRUST_DENOMINATOR = 20.0;
/**
 * Update suspicion counters and quarantine status for an agent.
 *
 * Requires 3+ neighbors with suspicion >= 3 for quarantine.
 * Suspicion decays by 0.5 per non-anomalous interaction (filters transient flukes).
 */
function updateSuspicion(agent, neighbor_id, is_anomaly) {
    if (is_anomaly) {
        const current = agent.suspicion_count.get(neighbor_id) || 0;
        agent.suspicion_count.set(neighbor_id, current + 1);
    }
    else {
        // Decay suspicion if no anomaly detected
        const current = agent.suspicion_count.get(neighbor_id) || 0;
        agent.suspicion_count.set(neighbor_id, Math.max(0, current - exports.SUSPICION_DECAY));
    }
    // Count how many neighbors are suspicious
    let suspicious_neighbors = 0;
    for (const count of agent.suspicion_count.values()) {
        if (count >= exports.SUSPICION_THRESHOLD)
            suspicious_neighbors++;
    }
    // Quarantine threshold: QUARANTINE_CONSENSUS+ neighbors with high suspicion
    agent.is_quarantined = suspicious_neighbors >= exports.QUARANTINE_CONSENSUS;
    // Update trust score (inverse of suspicion)
    let total_suspicion = 0;
    for (const count of agent.suspicion_count.values()) {
        total_suspicion += count;
    }
    agent.trust_score = Math.max(0, 1.0 - total_suspicion / exports.TRUST_DENOMINATOR);
}
// ═══════════════════════════════════════════════════════════════
// Swarm dynamics
// ═══════════════════════════════════════════════════════════════
/**
 * Run one swarm update step for all agents.
 *
 * Computes pairwise repulsion forces, updates suspicion counters,
 * applies forces with drift rate, and clamps positions to Poincaré ball.
 *
 * @param agents - All agents in the swarm
 * @param drift_rate - Force application rate (default 0.01)
 * @returns Updated agents (new array, agents are mutated in place)
 */
function swarmStep(agents, drift_rate = 0.01) {
    const n = agents.length;
    const dim = agents[0]?.position.length ?? 0;
    // Compute all pairwise forces
    for (let i = 0; i < n; i++) {
        const net_force = new Array(dim).fill(0);
        for (let j = 0; j < n; j++) {
            if (i === j)
                continue;
            const result = computeRepelForce(agents[i], agents[j]);
            // Accumulate force
            for (let k = 0; k < dim; k++) {
                net_force[k] += result.force[k];
            }
            // Update suspicion on the TARGET (j) from the SOURCE (i)
            // When i flags j as anomalous, j's suspicion record grows
            updateSuspicion(agents[j], agents[i].id, result.anomaly_flag);
        }
        // Apply force with drift
        for (let k = 0; k < dim; k++) {
            agents[i].position[k] += net_force[k] * drift_rate;
        }
        // Clamp to Poincaré ball
        agents[i].position = (0, hyperbolic_js_1.clampToBall)(agents[i].position, 0.99);
    }
    return agents;
}
/**
 * Run multiple swarm steps (convenience wrapper).
 *
 * @param agents - Initial agent set
 * @param num_steps - Number of swarm iterations
 * @param drift_rate - Force application rate
 * @returns Agents after all steps
 */
function runSwarm(agents, num_steps = 10, drift_rate = 0.01) {
    for (let step = 0; step < num_steps; step++) {
        swarmStep(agents, drift_rate);
    }
    return agents;
}
//# sourceMappingURL=geoseal.js.map