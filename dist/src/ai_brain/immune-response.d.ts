/**
 * @file immune-response.ts
 * @module ai_brain/immune-response
 * @layer Layer 12, Layer 13
 * @component GeoSeal Immune Response System
 * @version 1.0.0
 * @since 2026-02-07
 *
 * Implements GeoSeal-like immune system dynamics for the unified brain manifold.
 *
 * The immune response operates as an active defense mechanism:
 * - Per-agent suspicion counters accumulate over time
 * - Phase validity checks trigger repulsion amplification
 * - Spatial consensus requires 3+ neighbors to agree before quarantine
 * - Quarantined agents receive second-stage amplified monitoring
 *
 * This creates an "immune system" where the geometric structure actively
 * repels adversarial inputs, rather than passively filtering them.
 */
import { type CombinedAssessment } from './types.js';
/**
 * Agent immune status maintained by the immune system
 */
export interface AgentImmuneStatus {
    /** Agent identifier */
    agentId: string;
    /** Accumulated suspicion score [0, 1+] */
    suspicion: number;
    /** Number of times flagged by detection mechanisms */
    flagCount: number;
    /** Current immune state */
    state: ImmuneState;
    /** Repulsion force magnitude being applied */
    repulsionForce: number;
    /** Neighbor agents that have flagged this agent */
    accusers: Set<string>;
    /** Timestamp of last state change */
    lastStateChange: number;
    /** Number of quarantine entries */
    quarantineCount: number;
    /** History of suspicion changes for trend analysis */
    suspicionHistory: number[];
}
/**
 * Immune system states
 * - healthy: No concerns, normal operation
 * - monitoring: Elevated suspicion, increased observation
 * - inflamed: High suspicion, repulsion active
 * - quarantined: Isolated, second-stage amplification
 * - expelled: Permanently blocked (requires manual review)
 */
export type ImmuneState = 'healthy' | 'monitoring' | 'inflamed' | 'quarantined' | 'expelled';
/**
 * Immune response event for audit
 */
export interface ImmuneEvent {
    /** Timestamp */
    timestamp: number;
    /** Agent affected */
    agentId: string;
    /** Event type */
    eventType: 'suspicion_increase' | 'suspicion_decrease' | 'state_change' | 'quarantine' | 'release' | 'expulsion';
    /** Previous state */
    previousState: ImmuneState;
    /** New state */
    newState: ImmuneState;
    /** Suspicion level at event time */
    suspicion: number;
    /** Reason for event */
    reason: string;
}
/**
 * Immune system configuration
 */
export interface ImmuneConfig {
    /** Suspicion decay rate per step (how fast suspicion fades) */
    suspicionDecay: number;
    /** Suspicion increase per detection flag */
    suspicionPerFlag: number;
    /** Threshold for monitoring state */
    monitoringThreshold: number;
    /** Threshold for inflamed state */
    inflamedThreshold: number;
    /** Threshold for quarantine */
    quarantineThreshold: number;
    /** Threshold for expulsion (permanent block) */
    expulsionThreshold: number;
    /** Minimum neighbor accusations for spatial consensus */
    spatialConsensusMin: number;
    /** Repulsion base force */
    repulsionBase: number;
    /** Second-stage amplification factor for quarantined agents */
    quarantineAmplification: number;
    /** Maximum quarantine entries before expulsion */
    maxQuarantineCount: number;
    /** Suspicion history length for trend analysis */
    historyLength: number;
}
/**
 * Default immune system configuration
 */
export declare const DEFAULT_IMMUNE_CONFIG: ImmuneConfig;
/**
 * GeoSeal Immune Response System
 *
 * Manages per-agent immune states using geometric principles:
 * - Suspicion accumulates from detection mechanism flags
 * - Spatial consensus prevents false positives (need 3+ neighbor accusations)
 * - Repulsion forces push suspicious agents toward the Poincare boundary
 * - Quarantined agents receive amplified monitoring
 * - Repeated quarantine leads to permanent expulsion
 */
export declare class ImmuneResponseSystem {
    private agents;
    private events;
    private readonly config;
    constructor(config?: Partial<ImmuneConfig>);
    /**
     * Process a detection assessment for an agent.
     * Updates suspicion counters and immune state.
     *
     * @param agentId - Agent to process
     * @param assessment - Combined detection assessment
     * @param neighborAccusations - Set of neighbor agent IDs that flagged this agent
     * @returns Updated immune status
     */
    processAssessment(agentId: string, assessment: CombinedAssessment, neighborAccusations?: Set<string>): AgentImmuneStatus;
    /**
     * Apply spatial consensus before quarantine.
     * Requires minimum number of neighbor accusations to quarantine.
     *
     * @param agentId - Agent to check
     * @returns Whether spatial consensus supports quarantine
     */
    hasSpatialConsensus(agentId: string): boolean;
    /**
     * Release an agent from quarantine (after manual review).
     */
    releaseFromQuarantine(agentId: string): void;
    /**
     * Get the immune status for an agent
     */
    getAgentStatus(agentId: string): AgentImmuneStatus | undefined;
    /**
     * Get all agents in a specific immune state
     */
    getAgentsByState(state: ImmuneState): AgentImmuneStatus[];
    /**
     * Get the risk decision modifier based on immune status.
     * Returns a multiplier that can escalate the base risk decision.
     */
    getRiskModifier(agentId: string): number;
    /**
     * Get immune system events for audit
     */
    getEvents(): ReadonlyArray<ImmuneEvent>;
    /**
     * Get summary statistics
     */
    getStats(): {
        total: number;
        byState: Record<ImmuneState, number>;
        avgSuspicion: number;
        totalQuarantines: number;
        totalExpulsions: number;
    };
    private getOrCreateAgent;
    private updateImmuneState;
    private computeRepulsionForce;
    private recordEvent;
}
//# sourceMappingURL=immune-response.d.ts.map