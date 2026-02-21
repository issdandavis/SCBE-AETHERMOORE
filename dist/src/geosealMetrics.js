"use strict";
/**
 * @file geosealMetrics.ts
 * @module geosealMetrics
 * @layer Layer 9, Layer 14
 * @version 1.0.0
 *
 * GeoSeal benchmarking and observability metrics.
 *
 * Tracks quarantine performance, false positive rates,
 * and boundary distance for rogue agents.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.computeMetrics = computeMetrics;
exports.checkPerformanceThresholds = checkPerformanceThresholds;
// ═══════════════════════════════════════════════════════════════
// Metric computation
// ═══════════════════════════════════════════════════════════════
/**
 * Compute the Euclidean norm of a vector.
 */
function vecNorm(v) {
    let sum = 0;
    for (let i = 0; i < v.length; i++) {
        sum += v[i] * v[i];
    }
    return Math.sqrt(sum);
}
/**
 * Compute GeoSeal metrics for a completed swarm run.
 *
 * @param agents - All agents after swarm dynamics
 * @param rogue_id - ID of the rogue agent to measure
 * @returns Metric snapshot
 */
function computeMetrics(agents, rogue_id) {
    const rogue = agents.find((a) => a.id === rogue_id);
    if (!rogue)
        throw new Error(`Rogue agent not found: ${rogue_id}`);
    // Boundary distance (norm in Poincaré ball)
    const norm = vecNorm(rogue.position);
    // Suspicion consensus: fraction of neighbors with high suspicion
    let suspicious = 0;
    let total_neighbors = 0;
    for (const count of rogue.suspicion_count.values()) {
        total_neighbors++;
        if (count >= 3)
            suspicious++;
    }
    const consensus = total_neighbors > 0 ? suspicious / total_neighbors : 0;
    // Collateral flags: legitimate agents (with valid phase) that got quarantined
    const collateral = agents.filter((a) => a.is_quarantined && a.phase !== null).length;
    // Trust scores for all agents
    const trust_scores = new Map();
    for (const agent of agents) {
        trust_scores.set(agent.id, agent.trust_score);
    }
    return {
        time_to_isolation: rogue.is_quarantined ? agents.length : -1,
        boundary_norm: norm,
        suspicion_consensus: consensus,
        collateral_flags: collateral,
        final_trust_scores: trust_scores,
    };
}
/**
 * Check if GeoSeal performance meets production thresholds.
 *
 * @param metrics - Computed metrics
 * @returns Object with pass/fail for each criterion
 */
function checkPerformanceThresholds(metrics) {
    return {
        rogue_quarantined: metrics.time_to_isolation > 0,
        low_collateral: metrics.collateral_flags === 0,
        high_consensus: metrics.suspicion_consensus >= 0.5,
        boundary_pushed: metrics.boundary_norm >= 0.5,
    };
}
//# sourceMappingURL=geosealMetrics.js.map