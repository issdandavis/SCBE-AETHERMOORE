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
import { Agent } from './geoseal.js';
export interface GeoSealMetrics {
    /** Steps until rogue is quarantined (-1 if never quarantined) */
    time_to_isolation: number;
    /** Norm of rogue position (how far pushed toward boundary) */
    boundary_norm: number;
    /** Fraction of neighbors that agree rogue is suspicious */
    suspicion_consensus: number;
    /** Number of false positives (legitimate agents flagged) */
    collateral_flags: number;
    /** Trust scores for all agents */
    final_trust_scores: Map<string, number>;
}
/**
 * Compute GeoSeal metrics for a completed swarm run.
 *
 * @param agents - All agents after swarm dynamics
 * @param rogue_id - ID of the rogue agent to measure
 * @returns Metric snapshot
 */
export declare function computeMetrics(agents: Agent[], rogue_id: string): GeoSealMetrics;
/**
 * Check if GeoSeal performance meets production thresholds.
 *
 * @param metrics - Computed metrics
 * @returns Object with pass/fail for each criterion
 */
export declare function checkPerformanceThresholds(metrics: GeoSealMetrics): {
    rogue_quarantined: boolean;
    low_collateral: boolean;
    high_consensus: boolean;
    boundary_pushed: boolean;
};
//# sourceMappingURL=geosealMetrics.d.ts.map