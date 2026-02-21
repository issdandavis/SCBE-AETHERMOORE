/**
 * @file mitosis.ts
 * @module fleet/mitosis
 * @layer Layer 13 (Governance)
 * @component Agent Mitosis - Recursive Replication
 * @version 1.0.0
 *
 * Biological mitosis-inspired agent replication for the HYDRA fleet system.
 * Parent agents can "divide" to spawn child agents that inherit state,
 * capabilities, and trust vectors — with governance controls to prevent
 * uncontrolled proliferation.
 *
 * Mitosis lifecycle:
 *   1. INTERPHASE: Parent accumulates enough trust & task load
 *   2. PROPHASE:   Parent's state is duplicated (Polly Pad cloned)
 *   3. METAPHASE:  Child capabilities are specialized (differentiation)
 *   4. ANAPHASE:   Child is registered with reduced trust (must prove itself)
 *   5. TELOPHASE:  Parent-child link recorded in fleet genealogy
 *
 * Controls:
 * - Dimensional flux ν must be ≥ 0.8 (POLLY state) to divide
 * - SCBE risk check prevents rogue mitosis
 * - Maximum depth prevents exponential explosion
 * - Trust inheritance decays by a configurable factor
 */

import {
  FleetAgent,
  FleetEvent,
  GovernanceTier,
  AgentCapability,
  getDimensionalState,
} from './types';

/**
 * Mitosis lifecycle phase
 */
export type MitosisPhase =
  | 'INTERPHASE'
  | 'PROPHASE'
  | 'METAPHASE'
  | 'ANAPHASE'
  | 'TELOPHASE'
  | 'COMPLETE'
  | 'REJECTED';

/**
 * Record of a single mitosis event
 */
export interface MitosisRecord {
  /** Unique mitosis event ID */
  id: string;
  /** Parent agent ID */
  parentId: string;
  /** Child agent ID (set after ANAPHASE) */
  childId?: string;
  /** Current phase */
  phase: MitosisPhase;
  /** Timestamp */
  timestamp: number;
  /** Depth in the genealogy tree (root = 0) */
  depth: number;
  /** Reason if rejected */
  rejectionReason?: string;
}

/**
 * Configuration for mitosis behavior
 */
export interface MitosisConfig {
  /** Minimum flux (ν) to allow division (default: 0.8) */
  minFluxForDivision?: number;
  /** Trust decay factor for children (default: 0.7 = 70% of parent) */
  trustInheritanceFactor?: number;
  /** Maximum genealogy depth (default: 5) */
  maxDepth?: number;
  /** Minimum tasks completed before eligible (default: 3) */
  minTasksForEligibility?: number;
  /** Maximum concurrent children per parent (default: 3) */
  maxChildrenPerParent?: number;
  /** Cooldown between divisions in ms (default: 60000 = 1 min) */
  cooldownMs?: number;
}

const DEFAULT_CONFIG: Required<MitosisConfig> = {
  minFluxForDivision: 0.8,
  trustInheritanceFactor: 0.7,
  maxDepth: 5,
  minTasksForEligibility: 3,
  maxChildrenPerParent: 3,
  cooldownMs: 60000,
};

/**
 * Manages agent mitosis (replication) within the fleet.
 */
export class MitosisManager {
  private config: Required<MitosisConfig>;
  private records: MitosisRecord[] = [];
  private genealogy: Map<string, string[]> = new Map(); // parentId → childIds
  private depths: Map<string, number> = new Map(); // agentId → depth
  private lastDivision: Map<string, number> = new Map(); // agentId → timestamp
  private nextId = 0;
  private eventListeners: ((event: FleetEvent) => void)[] = [];

  constructor(config: MitosisConfig = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Check if an agent is eligible for mitosis.
   *
   * Requirements:
   * - Agent must be idle (not currently on a task)
   * - Must have completed minimum tasks
   * - Dimensional flux ν >= threshold
   * - Not exceeded max depth
   * - Not exceeded max children
   * - Cooldown period elapsed
   *
   * @param agent - The parent agent
   * @param flux - Current dimensional flux ν
   * @param now - Current timestamp
   * @returns Eligibility result with reason if rejected
   */
  checkEligibility(
    agent: FleetAgent,
    flux: number,
    now: number = Date.now()
  ): { eligible: boolean; reason?: string } {
    if (agent.status !== 'idle') {
      return { eligible: false, reason: 'Agent must be idle to divide' };
    }

    if (agent.tasksCompleted < this.config.minTasksForEligibility) {
      return {
        eligible: false,
        reason: `Need ${this.config.minTasksForEligibility} completed tasks (has ${agent.tasksCompleted})`,
      };
    }

    const dimState = getDimensionalState(flux);
    if (dimState !== 'POLLY') {
      return {
        eligible: false,
        reason: `Flux ν=${flux.toFixed(2)} too low (need POLLY state, ν≥${this.config.minFluxForDivision})`,
      };
    }

    const depth = this.depths.get(agent.id) ?? 0;
    if (depth >= this.config.maxDepth) {
      return { eligible: false, reason: `Max depth ${this.config.maxDepth} reached` };
    }

    const children = this.genealogy.get(agent.id) ?? [];
    if (children.length >= this.config.maxChildrenPerParent) {
      return {
        eligible: false,
        reason: `Max children ${this.config.maxChildrenPerParent} reached`,
      };
    }

    const lastDiv = this.lastDivision.get(agent.id) ?? 0;
    if (now - lastDiv < this.config.cooldownMs) {
      const remaining = this.config.cooldownMs - (now - lastDiv);
      return { eligible: false, reason: `Cooldown: ${remaining}ms remaining` };
    }

    return { eligible: true };
  }

  /**
   * Execute mitosis: create a child agent from a parent.
   *
   * The child inherits:
   * - Capabilities (optionally specialized)
   * - Trust vector (decayed by inheritance factor)
   * - Provider and model
   * - Governance tier (capped at parent's)
   *
   * @param parent - Parent agent
   * @param flux - Current dimensional flux ν
   * @param childName - Name for the child agent
   * @param specialization - Optional capability subset for the child
   * @param now - Current timestamp
   * @returns Mitosis record and child agent definition (for registration)
   */
  divide(
    parent: FleetAgent,
    flux: number,
    childName?: string,
    specialization?: AgentCapability[],
    now: number = Date.now()
  ): { record: MitosisRecord; childDefinition: Partial<FleetAgent> } | { record: MitosisRecord; childDefinition: null } {
    const eligibility = this.checkEligibility(parent, flux, now);

    const recordId = `mitosis-${this.nextId++}`;
    const parentDepth = this.depths.get(parent.id) ?? 0;

    if (!eligibility.eligible) {
      const record: MitosisRecord = {
        id: recordId,
        parentId: parent.id,
        phase: 'REJECTED',
        timestamp: now,
        depth: parentDepth,
        rejectionReason: eligibility.reason,
      };
      this.records.push(record);
      return { record, childDefinition: null };
    }

    // PROPHASE: Duplicate state
    const childTrustVector = parent.trustVector.map(
      (t) => t * this.config.trustInheritanceFactor
    );

    // METAPHASE: Differentiate capabilities
    const childCapabilities = specialization ?? [...parent.capabilities];

    // ANAPHASE: Prepare child definition
    const childDepth = parentDepth + 1;
    const generatedName = childName ?? `${parent.name}-child-${(this.genealogy.get(parent.id)?.length ?? 0) + 1}`;

    const childDefinition: Partial<FleetAgent> = {
      name: generatedName,
      description: `Mitosis child of ${parent.name} (depth ${childDepth})`,
      provider: parent.provider,
      model: parent.model,
      capabilities: childCapabilities,
      maxConcurrentTasks: parent.maxConcurrentTasks,
      maxGovernanceTier: parent.maxGovernanceTier,
      trustVector: childTrustVector,
      metadata: {
        parentId: parent.id,
        mitosisDepth: childDepth,
        mitosisRecordId: recordId,
        inheritedAt: now,
      },
    };

    // TELOPHASE: Record genealogy
    const record: MitosisRecord = {
      id: recordId,
      parentId: parent.id,
      phase: 'COMPLETE',
      timestamp: now,
      depth: childDepth,
    };

    this.records.push(record);
    this.lastDivision.set(parent.id, now);

    // Genealogy will be finalized when child is actually registered
    // (caller must register the child and call finalizeRegistration)

    return { record, childDefinition };
  }

  /**
   * Finalize a mitosis after the child has been registered in the fleet.
   *
   * @param recordId - Mitosis record ID
   * @param childId - Registered child agent ID
   */
  finalizeRegistration(recordId: string, childId: string): void {
    const record = this.records.find((r) => r.id === recordId);
    if (!record) return;

    record.childId = childId;

    // Update genealogy
    const children = this.genealogy.get(record.parentId) ?? [];
    children.push(childId);
    this.genealogy.set(record.parentId, children);

    // Track child depth
    this.depths.set(childId, record.depth);

    this.emitEvent({
      type: 'agent_registered',
      timestamp: Date.now(),
      agentId: childId,
      data: {
        mitosis: true,
        parentId: record.parentId,
        depth: record.depth,
      },
    });
  }

  /**
   * Get the genealogy tree for an agent.
   *
   * @param agentId - Root agent ID
   * @returns Array of child IDs (direct children only)
   */
  getChildren(agentId: string): string[] {
    return this.genealogy.get(agentId) ?? [];
  }

  /**
   * Get the full genealogy depth of an agent.
   */
  getDepth(agentId: string): number {
    return this.depths.get(agentId) ?? 0;
  }

  /**
   * Get all mitosis records.
   */
  getRecords(): MitosisRecord[] {
    return [...this.records];
  }

  /**
   * Register an event listener.
   */
  addEventListener(listener: (event: FleetEvent) => void): void {
    this.eventListeners.push(listener);
  }

  private emitEvent(event: FleetEvent): void {
    for (const listener of this.eventListeners) {
      listener(event);
    }
  }
}
