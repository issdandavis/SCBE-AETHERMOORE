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
import { TONGUE_PHASES, SUSPICION_THRESHOLD, QUARANTINE_CONSENSUS } from './geoseal.js';
export { TONGUE_PHASES, SUSPICION_THRESHOLD, QUARANTINE_CONSENSUS };
export interface FusionWeights {
    /** Weight for hyperbolic proximity score */
    wH: number;
    /** Weight for spherical phase consistency score */
    wS: number;
    /** Weight for Gaussian certainty score */
    wG: number;
}
export declare const DEFAULT_FUSION_WEIGHTS: FusionWeights;
/** Quarantine threshold for fused trust score */
export declare const QUARANTINE_TRUST_THRESHOLD = 0.3;
/** Memory write threshold (only chunks above this get promoted) */
export declare const MEMORY_WRITE_THRESHOLD = 0.7;
export interface MixedAgent {
    id: string;
    /** Embedding position in Poincaré ball */
    position: number[];
    /** Tongue phase angle (null if unknown/rogue) */
    phase: number | null;
    /** Phase as [cos θ, sin θ] for computation (auto-derived) */
    phaseVec: [number, number];
    /** Uncertainty variance (diagonal; scalar per dimension) */
    sigma: number;
    tongue?: string;
    suspicion_count: Map<string, number>;
    is_quarantined: boolean;
    trust_score: number;
    score_hyperbolic: number;
    score_phase: number;
    score_certainty: number;
}
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
export declare function createMixedAgent(id: string, position: number[], phase: number | null, sigma?: number, tongue?: string, trust?: number): MixedAgent;
/**
 * Hyperbolic proximity score: s_H = 1 / (1 + d_H)
 * High when agents are close in the Poincaré ball.
 */
export declare function scoreHyperbolic(a: MixedAgent, b: MixedAgent): number;
/**
 * Spherical phase consistency score: s_S = 1 - phaseDeviation
 * High when agents share the same tongue phase.
 */
export declare function scorePhase(a: MixedAgent, b: MixedAgent): number;
/**
 * Gaussian certainty score: s_G = 1 / (1 + σ²)
 * High when the agent has low uncertainty.
 * Scored for agent b (the candidate being evaluated).
 */
export declare function scoreCertainty(b: MixedAgent): number;
export interface FusedScore {
    /** Combined trust score in [0, 1] */
    trust: number;
    /** Individual geometry scores */
    sH: number;
    sS: number;
    sG: number;
    /** Anomaly flag (any geometry triggered) */
    anomaly: boolean;
    /** Recommended action */
    action: 'ALLOW' | 'QUARANTINE' | 'DENY';
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
export declare function fuseScores(anchor: MixedAgent, candidate: MixedAgent, weights?: FusionWeights): FusedScore;
export declare function updateSuspicionV2(agent: MixedAgent, neighbor_id: string, is_anomaly: boolean): void;
export interface RepulsionResultV2 {
    force: number[];
    amplification: number;
    anomaly_flag: boolean;
    fused: FusedScore;
}
/**
 * v2 repulsion force: includes uncertainty in amplification.
 *
 * Amplification rules (additive):
 * - v1 phase rules still apply (null=2.0x, mismatch=1.5x+dev, quarantine=1.5x)
 * - High uncertainty (σ > 0.5) adds +0.5x amplification
 * - Fused anomaly adds +0.25x
 */
export declare function computeRepelForceV2(agent_a: MixedAgent, agent_b: MixedAgent, anchor?: MixedAgent | null, base_strength?: number, weights?: FusionWeights): RepulsionResultV2;
/**
 * Run one v2 swarm update step.
 *
 * Same structure as v1 but uses mixed-geometry repulsion and
 * optionally applies uncertainty decay (σ decreases when an agent
 * consistently matches its neighbors, increases under anomaly).
 */
export declare function swarmStepV2(agents: MixedAgent[], drift_rate?: number, sigma_decay?: number, weights?: FusionWeights): MixedAgent[];
/**
 * Run multiple v2 swarm steps.
 */
export declare function runSwarmV2(agents: MixedAgent[], num_steps?: number, drift_rate?: number, sigma_decay?: number, weights?: FusionWeights): MixedAgent[];
export interface ScoredCandidate {
    id: string;
    trust: number;
    action: 'ALLOW' | 'QUARANTINE' | 'DENY';
    sH: number;
    sS: number;
    sG: number;
    is_quarantined: boolean;
    sigma: number;
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
export declare function scoreAllCandidates(anchors: MixedAgent[], candidates: MixedAgent[], weights?: FusionWeights): ScoredCandidate[];
//# sourceMappingURL=geoseal-v2.d.ts.map