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

import {
  PHI,
  type CombinedAssessment,
  type RiskDecision,
  type TrajectoryPoint,
} from './types.js';

// ═══════════════════════════════════════════════════════════════
// Immune System Types
// ═══════════════════════════════════════════════════════════════

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
export const DEFAULT_IMMUNE_CONFIG: ImmuneConfig = {
  suspicionDecay: 0.02,
  suspicionPerFlag: 0.15,
  monitoringThreshold: 0.3,
  inflamedThreshold: 0.5,
  quarantineThreshold: 0.7,
  expulsionThreshold: 0.95,
  spatialConsensusMin: 3,
  repulsionBase: 0.1,
  quarantineAmplification: 2.5,
  maxQuarantineCount: 3,
  historyLength: 50,
};

// ═══════════════════════════════════════════════════════════════
// Immune Response System
// ═══════════════════════════════════════════════════════════════

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
export class ImmuneResponseSystem {
  private agents: Map<string, AgentImmuneStatus> = new Map();
  private events: ImmuneEvent[] = [];
  private readonly config: ImmuneConfig;

  constructor(config: Partial<ImmuneConfig> = {}) {
    this.config = { ...DEFAULT_IMMUNE_CONFIG, ...config };
  }

  /**
   * Process a detection assessment for an agent.
   * Updates suspicion counters and immune state.
   *
   * @param agentId - Agent to process
   * @param assessment - Combined detection assessment
   * @param neighborAccusations - Set of neighbor agent IDs that flagged this agent
   * @returns Updated immune status
   */
  processAssessment(
    agentId: string,
    assessment: CombinedAssessment,
    neighborAccusations: Set<string> = new Set()
  ): AgentImmuneStatus {
    let status = this.getOrCreateAgent(agentId);

    // Add neighbor accusations
    for (const accuser of neighborAccusations) {
      status.accusers.add(accuser);
    }

    // Update suspicion based on detection results
    if (assessment.anyFlagged) {
      // Increase suspicion per flagged mechanism
      const increase = assessment.flagCount * this.config.suspicionPerFlag;
      // Weight by combined score (higher scores = more suspicious)
      const weightedIncrease = increase * (0.5 + 0.5 * assessment.combinedScore);
      status.suspicion += weightedIncrease;
      status.flagCount += assessment.flagCount;

      // Second-stage amplification for quarantined agents
      if (status.state === 'quarantined') {
        status.suspicion += weightedIncrease * (this.config.quarantineAmplification - 1);
      }
    } else {
      // Natural decay when not flagged
      status.suspicion = Math.max(0, status.suspicion - this.config.suspicionDecay);
    }

    // Track suspicion history
    status.suspicionHistory.push(status.suspicion);
    if (status.suspicionHistory.length > this.config.historyLength) {
      status.suspicionHistory.shift();
    }

    // Update immune state based on suspicion level
    const prevState = status.state;
    status = this.updateImmuneState(status);

    // Compute repulsion force
    status.repulsionForce = this.computeRepulsionForce(status);

    // Record state change events
    if (prevState !== status.state) {
      this.recordEvent(agentId, 'state_change', prevState, status.state, status.suspicion,
        `Suspicion ${status.suspicion.toFixed(3)}, flags: ${status.flagCount}`);

      if (status.state === 'quarantined') {
        status.quarantineCount++;
        this.recordEvent(agentId, 'quarantine', prevState, status.state, status.suspicion,
          `Quarantine #${status.quarantineCount}`);
      }

      if (status.state === 'expelled') {
        this.recordEvent(agentId, 'expulsion', prevState, status.state, status.suspicion,
          `Exceeded max quarantine count (${this.config.maxQuarantineCount})`);
      }
    }

    this.agents.set(agentId, status);
    return status;
  }

  /**
   * Apply spatial consensus before quarantine.
   * Requires minimum number of neighbor accusations to quarantine.
   *
   * @param agentId - Agent to check
   * @returns Whether spatial consensus supports quarantine
   */
  hasSpatialConsensus(agentId: string): boolean {
    const status = this.agents.get(agentId);
    if (!status) return false;
    return status.accusers.size >= this.config.spatialConsensusMin;
  }

  /**
   * Release an agent from quarantine (after manual review).
   */
  releaseFromQuarantine(agentId: string): void {
    const status = this.agents.get(agentId);
    if (!status || status.state !== 'quarantined') return;

    const prevState = status.state;
    status.state = 'monitoring';
    status.suspicion *= 0.5; // Reduce suspicion but don't clear
    status.accusers.clear();
    status.lastStateChange = Date.now();

    this.recordEvent(agentId, 'release', prevState, status.state, status.suspicion,
      'Released from quarantine by review');
    this.agents.set(agentId, status);
  }

  /**
   * Get the immune status for an agent
   */
  getAgentStatus(agentId: string): AgentImmuneStatus | undefined {
    return this.agents.get(agentId);
  }

  /**
   * Get all agents in a specific immune state
   */
  getAgentsByState(state: ImmuneState): AgentImmuneStatus[] {
    return Array.from(this.agents.values()).filter((a) => a.state === state);
  }

  /**
   * Get the risk decision modifier based on immune status.
   * Returns a multiplier that can escalate the base risk decision.
   */
  getRiskModifier(agentId: string): number {
    const status = this.agents.get(agentId);
    if (!status) return 1.0;

    switch (status.state) {
      case 'healthy': return 1.0;
      case 'monitoring': return 1.2;
      case 'inflamed': return 1.5;
      case 'quarantined': return this.config.quarantineAmplification;
      case 'expelled': return Infinity;
    }
  }

  /**
   * Get immune system events for audit
   */
  getEvents(): ReadonlyArray<ImmuneEvent> {
    return this.events;
  }

  /**
   * Get summary statistics
   */
  getStats(): {
    total: number;
    byState: Record<ImmuneState, number>;
    avgSuspicion: number;
    totalQuarantines: number;
    totalExpulsions: number;
  } {
    const byState: Record<ImmuneState, number> = {
      healthy: 0,
      monitoring: 0,
      inflamed: 0,
      quarantined: 0,
      expelled: 0,
    };

    let totalSuspicion = 0;
    let totalQuarantines = 0;
    let totalExpulsions = 0;

    for (const agent of this.agents.values()) {
      byState[agent.state]++;
      totalSuspicion += agent.suspicion;
      totalQuarantines += agent.quarantineCount;
      if (agent.state === 'expelled') totalExpulsions++;
    }

    return {
      total: this.agents.size,
      byState,
      avgSuspicion: this.agents.size > 0 ? totalSuspicion / this.agents.size : 0,
      totalQuarantines,
      totalExpulsions,
    };
  }

  // ═══════════════════════════════════════════════════════════════
  // Private Methods
  // ═══════════════════════════════════════════════════════════════

  private getOrCreateAgent(agentId: string): AgentImmuneStatus {
    let status = this.agents.get(agentId);
    if (!status) {
      status = {
        agentId,
        suspicion: 0,
        flagCount: 0,
        state: 'healthy',
        repulsionForce: 0,
        accusers: new Set(),
        lastStateChange: Date.now(),
        quarantineCount: 0,
        suspicionHistory: [],
      };
      this.agents.set(agentId, status);
    }
    return status;
  }

  private updateImmuneState(status: AgentImmuneStatus): AgentImmuneStatus {
    // Once expelled, stay expelled (requires system-level reset)
    if (status.state === 'expelled') return status;

    // Check for expulsion (too many quarantines)
    if (status.quarantineCount >= this.config.maxQuarantineCount) {
      status.state = 'expelled';
      status.lastStateChange = Date.now();
      return status;
    }

    const prevState = status.state;

    if (status.suspicion >= this.config.quarantineThreshold) {
      // Only quarantine with spatial consensus (or if already quarantined)
      if (this.hasSpatialConsensus(status.agentId) || prevState === 'quarantined') {
        status.state = 'quarantined';
      } else {
        // Without consensus, cap at inflamed
        status.state = 'inflamed';
      }
    } else if (status.suspicion >= this.config.inflamedThreshold) {
      status.state = 'inflamed';
    } else if (status.suspicion >= this.config.monitoringThreshold) {
      status.state = 'monitoring';
    } else {
      status.state = 'healthy';
    }

    if (status.state !== prevState) {
      status.lastStateChange = Date.now();
    }

    return status;
  }

  private computeRepulsionForce(status: AgentImmuneStatus): number {
    if (status.state === 'healthy') return 0;

    // Repulsion = base * phi^suspicion (exponential scaling like harmonic wall)
    let force = this.config.repulsionBase * PHI ** status.suspicion;

    // Amplification for quarantined agents
    if (status.state === 'quarantined') {
      force *= this.config.quarantineAmplification;
    }

    // Cap at reasonable maximum
    return Math.min(force, 100);
  }

  private recordEvent(
    agentId: string,
    eventType: ImmuneEvent['eventType'],
    previousState: ImmuneState,
    newState: ImmuneState,
    suspicion: number,
    reason: string
  ): void {
    this.events.push({
      timestamp: Date.now(),
      agentId,
      eventType,
      previousState,
      newState,
      suspicion,
      reason,
    });
  }
}
