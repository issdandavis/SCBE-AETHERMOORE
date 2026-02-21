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
/** Fixed phases for the 6 Sacred Tongues (evenly spaced on unit circle) */
export declare const TONGUE_PHASES: Record<string, number>;
export interface Agent {
    id: string;
    position: number[];
    phase: number | null;
    tongue?: string;
    suspicion_count: Map<string, number>;
    is_quarantined: boolean;
    trust_score: number;
}
/** Create a new agent with sensible defaults */
export declare function createAgent(id: string, position: number[], phase: number | null, tongue?: string, trust_score?: number): Agent;
export interface RepulsionResult {
    force: number[];
    amplification: number;
    anomaly_flag: boolean;
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
export declare function computeRepelForce(agent_a: Agent, agent_b: Agent, base_strength?: number): RepulsionResult;
/** Suspicion decay rate when no anomaly is detected */
export declare const SUSPICION_DECAY = 0.5;
/** Number of suspicion hits before a neighbor is considered suspicious */
export declare const SUSPICION_THRESHOLD = 3;
/** Number of suspicious neighbors required for quarantine */
export declare const QUARANTINE_CONSENSUS = 3;
/** Trust score denominator (total suspicion / this = trust loss) */
export declare const TRUST_DENOMINATOR = 20;
/**
 * Update suspicion counters and quarantine status for an agent.
 *
 * Requires 3+ neighbors with suspicion >= 3 for quarantine.
 * Suspicion decays by 0.5 per non-anomalous interaction (filters transient flukes).
 */
export declare function updateSuspicion(agent: Agent, neighbor_id: string, is_anomaly: boolean): void;
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
export declare function swarmStep(agents: Agent[], drift_rate?: number): Agent[];
/**
 * Run multiple swarm steps (convenience wrapper).
 *
 * @param agents - Initial agent set
 * @param num_steps - Number of swarm iterations
 * @param drift_rate - Force application rate
 * @returns Agents after all steps
 */
export declare function runSwarm(agents: Agent[], num_steps?: number, drift_rate?: number): Agent[];
//# sourceMappingURL=geoseal.d.ts.map