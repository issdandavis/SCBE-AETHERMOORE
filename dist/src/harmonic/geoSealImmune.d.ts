/**
 * @file geoSealImmune.ts
 * @module harmonic/geoSealImmune
 * @layer Layer 5, Layer 8, Layer 13
 * @component GeoSeal Immune System
 * @version 3.2.5
 *
 * Immune-like dynamics for RAG filtering using hyperbolic geometry
 * and phase discipline. Detects and quarantines adversarial or
 * off-grammar retrievals using swarm-based repulsion.
 */
/** Phase angles for the Six Sacred Tongues (radians) */
export declare const TONGUE_PHASES: Record<string, number>;
/** Reverse mapping: phase → tongue name */
export declare const PHASE_TO_TONGUE: Map<number, string>;
/**
 * Agent in the GeoSeal immune swarm.
 *
 * Represents either:
 * - A Sacred Tongue (legitimate, fixed phase)
 * - A retrieval/tool output (candidate, assigned or null phase)
 * - A memory chunk (probationary, builds trust over time)
 */
export interface SwarmAgent {
    id: string;
    position: number[];
    phase: number | null;
    tongue?: string;
    suspicionCount: Map<string, number>;
    isQuarantined: boolean;
    trustScore: number;
}
/** Result of computing repulsion force between two agents */
export interface RepulsionResult {
    force: number[];
    amplification: number;
    anomalyFlag: boolean;
}
/** Metrics from swarm immune dynamics */
export interface SwarmMetrics {
    quarantineCount: number;
    avgTrustScore: number;
    boundaryAgents: number;
    suspiciousPairs: number;
}
/**
 * Compute normalized phase deviation in [0, 1].
 *
 * Returns 1.0 (maximum) if either phase is null (rogue/unknown).
 * Otherwise returns angular difference normalized to [0, 1].
 */
export declare function phaseDeviation(phase1: number | null, phase2: number | null): number;
/**
 * Core GeoSeal repulsion force computation.
 *
 * Implements immune-like response to phase-weird agents:
 * - Null phase (unknown/rogue) → 2.0x force amplification
 * - Wrong phase at close distance → 1.5x + deviation amplification
 * - Quarantined agents → additional 1.5x multiplier
 */
export declare function computeRepelForce(agentA: SwarmAgent, agentB: SwarmAgent, baseStrength?: number): RepulsionResult;
/**
 * Update suspicion counters and quarantine status.
 *
 * Temporal integration filters transient flukes:
 * - Anomaly detection increments suspicion by 1
 * - No anomaly decays suspicion by decayRate
 * - Quarantine requires consensusThreshold+ neighbors with
 *   suspicion >= suspicionThreshold
 */
export declare function updateSuspicion(agent: SwarmAgent, neighborId: string, isAnomaly: boolean, decayRate?: number, suspicionThreshold?: number, consensusThreshold?: number): void;
/**
 * Run one swarm update step for all agents.
 *
 * Computes pairwise repulsion forces, updates positions,
 * tracks suspicion, and enforces Poincaré ball containment.
 */
export declare function swarmStep(agents: SwarmAgent[], driftRate?: number, ballRadius?: number): SwarmAgent[];
/**
 * Run multiple swarm update steps.
 */
export declare function runSwarmDynamics(agents: SwarmAgent[], numSteps?: number, driftRate?: number): SwarmAgent[];
/**
 * Initialize the 6 Sacred Tongues as legitimate agents.
 */
export declare function createTongueAgents(dimension?: number): SwarmAgent[];
/**
 * Create a candidate agent for immune evaluation.
 */
export declare function createCandidateAgent(agentId: string, embedding: number[], assignedTongue?: string, initialTrust?: number): SwarmAgent;
/**
 * Filter agents by trust score, returning only those above threshold.
 */
export declare function filterByTrust(agents: SwarmAgent[], threshold?: number): SwarmAgent[];
/**
 * Extract trust scores as attention weights for RAG reweighting.
 */
export declare function getAttentionWeights(agents: SwarmAgent[]): Map<string, number>;
/**
 * Compute metrics for monitoring swarm health.
 */
export declare function computeSwarmMetrics(agents: SwarmAgent[]): SwarmMetrics;
/**
 * Compute trust score using proven phase + distance formula.
 *
 * This simple formula empirically achieved 0.9999 AUC in adversarial
 * detection tests, outperforming complex swarm dynamics (0.543 AUC).
 *
 * Formula: score = 1 / (1 + d_H + 2 * phase_deviation)
 *
 * - Legitimate agents (matching phase, close to tongues): score → 1.0
 * - Rogue agents (null phase or far from tongues): score → 0.0
 */
export declare function phaseDistanceScore(agent: SwarmAgent, tongueAgents: SwarmAgent[]): number;
/**
 * Batch score candidates using proven phase+distance formula.
 *
 * Returns Map<id, score> where higher scores indicate more trustworthy agents.
 */
export declare function phaseDistanceFilter(candidates: Array<{
    id: string;
    embedding: number[];
    tongue?: string;
}>, dimension?: number): Map<string, number>;
/**
 * Generate position on spherical nodal system with oscillation.
 *
 * Maps a 2D phase circle to multi-dimensional space using spherical
 * harmonics-like oscillation. The 6 Sacred Tongues act as stable
 * nodes while candidate positions oscillate between them.
 *
 * The oscillation allows temporal disambiguation: legitimate agents
 * maintain phase coherence over time, while adversarial agents drift.
 */
export declare function sphericalNodalPosition(phase: number, time: number, oscillationFreq?: number, dimension?: number): number[];
/**
 * Create tongue agents with spherical nodal oscillation.
 *
 * The 6 tongues form a hexagonal nodal pattern that gently
 * oscillates in phase space. This creates a breathing pattern
 * that tests phase coherence over time.
 */
export declare function oscillatingTongueAgents(time: number, dimension?: number, oscillationFreq?: number): SwarmAgent[];
/**
 * Score agent using temporal phase coherence with oscillating tongues.
 *
 * Runs multiple time steps to test if agent maintains phase coherence
 * as the tongue nodal system oscillates. Legitimate agents should
 * track their assigned tongue; adversarial agents will drift.
 */
export declare function temporalPhaseScore(agent: SwarmAgent, timeSteps?: number, dimension?: number): number;
/**
 * GeoSeal filter context for RAG pipeline integration.
 */
export interface GeoSealContext {
    tongueAgents: SwarmAgent[];
    candidateAgents: SwarmAgent[];
}
/**
 * Run GeoSeal immune filtering on a set of candidates.
 *
 * Returns attention weights for each candidate (0.0 to 1.0).
 * Low weights indicate adversarial or off-grammar content.
 */
export declare function geoSealFilter(candidates: Array<{
    id: string;
    embedding: number[];
    tongue?: string;
}>, numSteps?: number, dimension?: number): Map<string, number>;
//# sourceMappingURL=geoSealImmune.d.ts.map